"""Independent experiment evaluator with a bounded, durable numerical ledger.

This adapter never borrows historical campaign grants. Each experiment owns a
frozen task, baseline design/control and an explicit parameter-space grant.
"""
import time
from pathlib import Path
from typing import Literal
from pydantic import Field
from schemas.common import Contract
from schemas.design_spec import DesignSpec
from schemas.exploration import ExplorationControl
from schemas.framework import Evaluation
from tools.task_context import TaskContext
from tools.spec_tools import ROOT
from tools.state_io import atomic_json,read,digest
from tools.artifact_tools import file_hash
from tools.optimization_interfaces import evaluation_from_result


class EvaluationConfig(Contract):
    version: Literal['1.0'] = '1.0'
    authorization: str = Field(min_length=1)
    permissions: list[Literal['simulate']]
    backends: list[Literal['mujoco','matlab']]
    controller_modes: list[Literal['C1','C2']]
    controller_id: str | None = None
    task_context: TaskContext
    design: DesignSpec
    control: ExplorationControl
    bounds: dict[str,tuple[float,float]] = Field(default_factory=dict)
    max_evaluations: int = Field(ge=0)
    max_calls: int = Field(ge=0)
    wall_s: float = Field(gt=0)
    per_evaluation_timeout_s: float = Field(gt=0)


class EvaluationSession:
    def __init__(self,root,backends=None):
        from tools.reach_dynamics import DynamicsBackends
        self.root=Path(root).resolve();runs=(ROOT/'runs').resolve()
        if not self.root.is_relative_to(runs) or self.root==runs:raise ValueError('INVALID_EVALUATION_ROOT')
        self.backends=backends or DynamicsBackends()

    def create(self,config):
        from tools.workbench import source_hashes,runtime
        config=EvaluationConfig.model_validate(config)
        self._candidate(config,{})
        self.root.mkdir(parents=True,exist_ok=False)
        value=config.model_dump(mode='json');atomic_json(self.root/'evaluation_config.json',value)
        state=dict(version='evaluation_runtime_v1',config_hash=digest(value),sources=source_hashes(),runtime=runtime(),
            used=dict(evaluations=0,calls=0,wall_s=0.),trials={},evidence={})
        atomic_json(self.root/'state.json',state)
        return state

    def load(self):
        from tools.workbench import source_hashes,runtime
        state=read(self.root/'state.json');value=read(self.root/'evaluation_config.json')
        if state['config_hash']!=digest(value):raise ValueError('PERMISSION_CONFIG_CHANGED')
        if state['sources']!=source_hashes() or state['runtime']!=runtime():raise ValueError('SOURCE_OR_RUNTIME_CHANGED: new experiment required')
        return state,EvaluationConfig.model_validate(value)

    @staticmethod
    def _candidate(config,changes):
        import math
        design=config.design.model_dump(mode='json');control=config.control.model_dump(mode='json')
        # Field scope is explicit: task, environment and material definitions
        # cannot enter an optimizer vector. Future spaces need their own adapter.
        allowed={'design.total_length_m','design.tendon_routing_radius_m','control.bend_y_rad',
                 'control.bend_z_rad','control.bias_fraction','control.gain_rad2_per_m2'}
        if any(k not in allowed for k in config.bounds):raise ValueError('DESIGN_SPACE_ADAPTER_REQUIRED')
        for lo,hi in config.bounds.values():
            if not all(math.isfinite(v) for v in (lo,hi)) or lo>=hi:raise ValueError('INVALID_PARAMETER_BOUNDS')
        for key,value in changes.items():
            if key not in config.bounds:raise ValueError('PARAMETER_NOT_AUTHORIZED: '+key)
            lo,hi=config.bounds[key]
            if type(value) not in (int,float) or not math.isfinite(value) or not lo<=value<=hi:raise ValueError('PARAMETERS_OUT_OF_BOUNDS')
            group,name=key.split('.')
            (design if group=='design' else control)[name]=value
        return DesignSpec.model_validate(design),ExplorationControl.model_validate(control)

    def evaluate(self,candidate,purpose='validation',*,backend='mujoco'):
        from tools.workbench import owner
        with owner(self.root):return self._evaluate(candidate,purpose,backend)

    def _evaluate(self,candidate,purpose,backend):
        from controllers.registry import check_backend
        from tools.design_compiler import build_robot_ir
        from tools.public_services import checked_path
        state,cfg=self.load()
        if 'simulate' not in cfg.permissions or backend not in cfg.backends:raise ValueError('PERMISSION_DENIED')
        design,control=self._candidate(cfg,candidate)
        if control.mode not in cfg.controller_modes:raise ValueError('CONTROLLER_NOT_AUTHORIZED')
        check_backend(control.mode,backend,cfg.task_context,controller_id=cfg.controller_id)
        ir=build_robot_ir(design)
        key=digest(dict(config=state['config_hash'],sources=state['sources'],runtime=state['runtime'],
                        design=design.model_dump(mode='json'),control=control.model_dump(mode='json'),backend=backend))
        row=state['trials'].get(key)
        if state['used']['calls']>=cfg.max_calls:raise ValueError('BUDGET_EXHAUSTED: evaluation calls')
        state['used']['calls']+=1
        atomic_json(self.root/'state.json',state)
        folder=self.root/'evaluations'/key
        if row:
            # Sealed bundle may predate final ledger commit. Never execute again.
            seal=folder/'seal.json'
            if row['status']=='reserved' and seal.exists():
                saved=read(seal)
                if saved['identity']!=key:raise ValueError('EVIDENCE_IDENTITY_MISMATCH')
                for ref,sha in saved['hashes'].items():
                    path=(self.root/ref).resolve()
                    if not path.is_relative_to(folder) or not path.is_file() or file_hash(path)!=sha:raise ValueError('EVIDENCE_CHANGED_DURING_RECOVERY')
                    state['evidence'][ref]=dict(sha256=sha)
                row.update(status='sealed',outcome=saved['outcome'],hashes=saved['hashes'],recovered=True)
            if row['status']=='sealed':
                for ref in row['hashes']:checked_path(self.root,state['evidence'],ref)
                atomic_json(self.root/'state.json',state)
                return Evaluation.model_validate({**row['outcome'],'actual_evaluations':0})
            row['status']='interrupted';atomic_json(self.root/'state.json',state)
            return Evaluation(status='INCOMPLETE',reason='INTERRUPTED: charged evaluation cannot automatically replay')
        cap=min(cfg.per_evaluation_timeout_s,cfg.wall_s-state['used']['wall_s'])
        if state['used']['evaluations']>=cfg.max_evaluations or cap<=0:raise ValueError('BUDGET_EXHAUSTED: numerical evaluation')
        state['used']['evaluations']+=1;state['used']['wall_s']+=cap
        row=dict(status='reserved',purpose=purpose,backend=backend,wall_reserved_s=cap)
        state['trials'][key]=row;atomic_json(self.root/'state.json',state)
        folder.mkdir(parents=True);started=time.monotonic()
        try:
            out=self.backends.simulate(backend,ir,control,folder,timeout_s=cap,task_context=cfg.task_context,controller_id=cfg.controller_id)
        except Exception as exc:
            out=dict(backend=backend,complete=False,computation_status='failed',reason=str(exc),position_error_m=None)
        out.update(result_ref=(folder/'result.json').relative_to(self.root).as_posix(),task_context_hash=cfg.task_context.identity)
        atomic_json(folder/'result.json',out)
        outcome=evaluation_from_result(out,1).model_dump(mode='json')
        hashes={p.relative_to(self.root).as_posix():file_hash(p) for p in folder.iterdir() if p.is_file()}
        atomic_json(folder/'seal.json',dict(identity=key,outcome=outcome,hashes=hashes))
        state['evidence'].update({ref:dict(sha256=sha) for ref,sha in hashes.items()})
        row.update(status='sealed',outcome=outcome,hashes=hashes,elapsed_s=time.monotonic()-started)
        state['used']['wall_s']-=max(0,cap-row['elapsed_s'])
        atomic_json(self.root/'state.json',state)
        return Evaluation.model_validate(outcome)

    def close(self):self.backends.close()

    @property
    def identity(self):
        state,_=self.load()
        return digest(dict(root=str(self.root),config=state['config_hash'],sources=state['sources'],runtime=state['runtime']))

    def charged_evaluations(self,purpose):
        state,_=self.load()
        return sum(row['purpose']==purpose for row in state['trials'].values())
