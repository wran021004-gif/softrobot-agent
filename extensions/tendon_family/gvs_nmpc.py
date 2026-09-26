"""Projected-state NMPC with one bounded, explicitly recorded failure response."""
import time
import numpy as np
from schemas.platform import RobotDescription, TaskDefinition
from tools.state_io import digest
from .contracts import ResolvedGVSBasis
from .control import execute_ideal_tension
from .gvs_basis import resolve_basis
from .gvs_projection import description
from .gvs_trajectory import GVSTrajectoryParameters, TrajectoryWorkspace

_WORKSPACES={}
_SEEDS={}


def workspace_key(task,robot,parameters):
    return digest(dict(robot=robot.model_dump(mode='json'),environment=task.environment.model_dump(mode='json'),
        goal=task.goal.model_dump(mode='json'),period=task.timing.control_period_s,
        evaluator=task.evaluator.model_dump(mode='json'),parameters=parameters.model_dump(mode='json')))


def resolve_gvs_nmpc_control(inp,physics):
    p=GVSTrajectoryParameters.model_validate(inp.policy.controller.parameters.data)
    from .gvs_lqr import _candidate_operating_point
    # Operating point supplies a nominal reference and initial seed only.
    nominal_parameters=inp.policy.controller.parameters.model_copy(update={'data':{'basis':p.basis.model_dump(mode='json')}})
    nominal_controller=inp.policy.controller.model_copy(update={'parameters':nominal_parameters})
    nominal=inp.model_copy(update={'policy':inp.policy.model_copy(update={'controller':nominal_controller})})
    point=_candidate_operating_point(nominal)
    basis=resolve_basis(inp.robot.structure.data,p.basis)
    plan=dict(mode='gvs_nmpc',tension_execution_mode='ideal_tension',
        robot=inp.robot.model_dump(mode='json'),task=inp.task.model_dump(mode='json'),
        reference=dict(kind='gvs_nominal_metadata',target_world_m=inp.task.goal.data['target_m'],
            q0=point['q0'],u0=point['u0'],derivation=point),
        projector=description(physics,basis),effective_parameters=p.model_dump(mode='json'),
        timing=dict(period_s=inp.task.timing.control_period_s,prediction_interval_s=inp.task.timing.control_period_s,
            physics_step_s=inp.task.timing.timestep_s,observation='interval_start_pre_step'),
        plan_acceptance='Independently feasible converged or iteration-limited plans; nonconverged feasible updates are explicitly marked suboptimal and counted as solver failures.',
        failure_response='If no usable feasible plan is returned, hold last bounded tension; use clipped nominal tension initially. Every use is recorded.')
    plan['identity']=digest(plan)
    return plan


class GVSNMPCController:
    def __init__(self,parameters,period_s):
        self.parameters=GVSTrajectoryParameters.model_validate(parameters);self.period_s=period_s

    def configure(self,physics,plan):
        self.physics=physics;self.plan=plan
        self.resolved_basis=ResolvedGVSBasis.model_validate(plan['projector']['resolved_basis'])
        self.projector_id=plan['projector']['id']
        self.coordinate_order=self.resolved_basis.coordinate_order
        self.limits=np.array([t['force_limit_n'] for t in physics['tendons']])
        self.previous=np.clip(plan['reference']['u0'],0,self.limits)
        robot=RobotDescription.model_validate(plan['robot']);task=TaskDefinition.model_validate(plan['task'])
        key=workspace_key(task,robot,self.parameters)
        if key not in _WORKSPACES:
            _WORKSPACES[key]=TrajectoryWorkspace(task,robot,self.parameters,
                [*plan['reference']['q0'],*([0.]*len(self.coordinate_order))],plan['reference']['u0'])
        self.workspace=_WORKSPACES[key];self.workspace.last=None
        self.seed=_SEEDS.get(key);self.observations=[];self.last={};self.u=None

    def command(self,t,geometry,q,v):
        start=time.perf_counter();x=np.r_[q,v];error=None;solved=None
        try:
            solved=self.workspace.solve(x,self.previous,warm=self.seed)
            success=solved['accepted']
        except (RuntimeError,ValueError) as exc:
            success=False;error=str(exc)
        self.seed=None
        requested=np.asarray(solved['tensions'][0]) if success else self.previous.copy()
        command,bridge=execute_ideal_tension(self.physics,requested)
        self.previous=np.asarray(command).copy();elapsed=time.perf_counter()-start
        converged=solved is not None and solved['optimization_converged']
        self.last={**bridge,'solver_failed':not success or not converged,'failure_response_used':not success,
            'feasible_suboptimal_update':success and not converged,
            'solver_error':error,'optimization_status':None if solved is None else solved['result']['status'],
            'optimization_constraint_violation':None if solved is None else solved['result']['constraint_violation'],
            'update_wall_s':elapsed,'deadline_missed':elapsed>self.period_s,
            'solver_construction_s':None if solved is None else solved['diagnostics']['construction_s'],
            'optimization_solve_s':None if solved is None else solved['diagnostics']['solve_s'],
            'gvs_projection_residual_max_rad_m':geometry['gvs_projection']['projection_residual_max_rad_m']}
        self.observations.append(dict(time_s=t,phase='current_state_before_integration',
            tip_position_m=geometry['tip'].tolist(),gvs_q=list(q),gvs_qdot=list(v),
            measured_initial_state=x.tolist(),graph_construction_s=self.workspace.graph_s,**self.last))
        return command
