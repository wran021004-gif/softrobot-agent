"""Explicit task/environment/execution boundary; no candidate or campaign IDs."""
from typing import Literal
from pydantic import Field, model_validator
from schemas.common import Contract
from schemas.task_spec import TaskSpec
from schemas.environment_spec import EnvironmentSpec
from schemas.settings import RunSettings
from tools.state_io import digest


class TaskContext(Contract):
    version: Literal['1.0'] = '1.0'
    task: TaskSpec
    environment: EnvironmentSpec
    run_settings: RunSettings
    timestep_s: float = Field(gt=0)
    initial_state: Literal['compiled_default_qpos_zero_qvel'] = 'compiled_default_qpos_zero_qvel'
    evaluator_id: Literal['reach_v1'] = 'reach_v1'
    authority: str = Field(min_length=1)

    @model_validator(mode='after')
    def compatible(self):
        if self.task.environment_id!=self.environment.environment_id:raise ValueError('TASK_ENVIRONMENT_MISMATCH')
        if self.task.task_type not in ('reach','reach_window'):raise ValueError('TASK_ADAPTER_REQUIRED')
        return self

    @property
    def duration_s(self):return self.run_settings.steps*self.timestep_s

    @property
    def identity(self):return digest(self.model_dump(mode='json'))

    def evaluator(self):
        from metrics.reach import evaluate_reach
        return evaluate_reach


def legacy_context():
    from tools.spec_tools import load_task_package,load_run_settings,load_simulator
    task,env=load_task_package()
    return TaskContext(task=task,environment=env,run_settings=load_run_settings(),
        timestep_s=load_simulator().timestep_s,authority='Frozen task package and configs/run.yaml')


def development_context(path):
    """Configuration can vary a reach target and duration, never source physics."""
    from tools.spec_tools import load_yaml
    from schemas.common import Contract
    class Development(Contract):
        task_id: str
        target_m: tuple[float,float,float]
        steps: int = Field(gt=0,strict=True)
        authority: str
    cfg=Development.model_validate(load_yaml(path));base=legacy_context()
    task=TaskSpec.model_validate({**base.task.model_dump(mode='json'), 'task_id':cfg.task_id,'target_m':cfg.target_m})
    settings=RunSettings(steps=cfg.steps,random_seed=base.run_settings.random_seed,provenance=cfg.authority)
    return TaskContext(task=task,environment=base.environment,run_settings=settings,
        timestep_s=base.timestep_s,authority=cfg.authority)
