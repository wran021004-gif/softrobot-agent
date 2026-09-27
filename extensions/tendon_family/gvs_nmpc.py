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
        goal=task.goal.model_dump(mode='json'),timing=task.timing.model_dump(mode='json'),
        evaluator=task.evaluator.model_dump(mode='json'),parameters=parameters.model_dump(mode='json')))


def resolve_gvs_nmpc_control(inp,physics):
    if inp.policy.controller.version == '3.0.0':
        from .gvs_profile import checked_reach, reach_numerical
        p=checked_reach(inp).recipe
        numerical=reach_numerical(inp)
        point=numerical['nominal']
    elif inp.policy.controller.version == '2.0.0':
        from .gvs_profile import checked_profile
        profile=checked_profile(inp)
        p=GVSTrajectoryParameters.model_validate(profile['parameters'])
        point=profile['numerical']['nominal']
    else:
        p=GVSTrajectoryParameters.model_validate(inp.policy.controller.parameters.data)
        from .gvs_lqr import _candidate_operating_point
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
        plan_acceptance='Independently feasible converged, iteration-limited or intentional early-stop plans. Early stops are suboptimal, not convergence or solver errors; raw termination is retained.',
        failure_response='Hold last bounded tension on an unusable solve (clipped nominal initially); stop after max_unusable_updates consecutive unusable updates. Every applied hold is recorded.')
    if inp.policy.controller.version == '2.0.0':
        plan['profile_id']=profile['profile_id']
        plan['numerical_reference']=profile['numerical_reference']
    elif inp.policy.controller.version == '3.0.0':
        plan['reference']['kind']='numerical_guess_metadata_not_current_target_equilibrium'
        plan['reference'].pop('target_world_m')
        plan['reference']['provenance']=numerical['provenance']
        plan['numerical_reference']=dict(artifact_id=digest(numerical),media_type='application/json')
        plan['settling']=checked_reach(inp).settling.model_dump(mode='json')
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
        if hasattr(self,'profile'):
            self.workspace=TrajectoryWorkspace(task,robot,self.parameters,
                [*plan['reference']['q0'],*([0.]*len(self.coordinate_order))],plan['reference']['u0'],settling=plan.get('settling'))
            from copy import deepcopy
            self.seed=deepcopy(self.profile['numerical']['warm_guess'])
        else:
            if key not in _WORKSPACES:
                _WORKSPACES[key]=TrajectoryWorkspace(task,robot,self.parameters,
                    [*plan['reference']['q0'],*([0.]*len(self.coordinate_order))],plan['reference']['u0'])
            self.workspace=_WORKSPACES[key];self.seed=_SEEDS.get(key)
        # A failed first update must not discard the available offline seed.
        # It remains only an optimization guess, never a fallback command.
        self.workspace.last=self.seed
        self.observations=[];self.last={};self.u=None;self.unusable_updates=0;self.stop_requested=False

    def command(self,t,geometry,q,v):
        start=time.perf_counter();x=np.r_[q,v];error=None;solved=None
        try:
            solved=self.workspace.solve(x,self.previous,warm=self.seed,elapsed_s=t)
            success=solved['accepted']
        except (RuntimeError,ValueError) as exc:
            success=False;error=str(exc)
        self.seed=None
        self.unusable_updates=0 if success else self.unusable_updates+1
        self.stop_requested=self.unusable_updates>=self.parameters.max_unusable_updates
        requested=np.asarray(solved['tensions'][0]) if success else self.previous.copy()
        command,bridge=execute_ideal_tension(self.physics,requested)
        self.previous=np.asarray(command).copy();elapsed=time.perf_counter()-start
        converged=solved is not None and solved['optimization_converged']
        intentional=solved is not None and solved['result']['status']=='feasible_early_stop'
        self.last={**bridge,'plan_accepted':success,'solver_failed':not success or (not converged and not intentional),
            'optimization_nonconverged':not converged,'failure_response_used':not success and not self.stop_requested,
            'feasible_suboptimal_update':success and not converged,
            'solver_error':error,'optimization_status':None if solved is None else solved['result']['status'],
            'optimization_constraint_violation':None if solved is None else solved['result']['constraint_violation'],
            'optimization_selected_iteration':None if solved is None or solved['recovery']['selected'] else solved['diagnostics']['selected_feasible_iteration'],
            'plan_source':None if solved is None else ('reintegrated_returned_iterate' if solved['recovery']['selected'] else 'ipopt_selected'),
            'feasibility_recovery':None if solved is None else solved['recovery'],
            'feedback':None if solved is None else solved.get('feedback'),
            'prediction_timing':None if solved is None else solved['prediction_timing'],
            'recovery_wall_s':None if solved is None else solved['recovery']['wall_s'],
            'recovery_integration_s':None if solved is None else solved['recovery'].get('integration_s',0.),
            'recovery_validation_s':None if solved is None else solved['recovery'].get('validation_s',0.),
            'optimization_returned_violation':None if solved is None else solved['diagnostics']['returned_iterate_constraint_violation'],
            'update_wall_s':elapsed,'deadline_missed':elapsed>self.period_s,
            'solver_construction_s':None if solved is None else solved['diagnostics']['construction_s'],
            'optimization_solve_s':None if solved is None else solved['diagnostics']['solve_s'],
            'policy_stop_reason':None if solved is None else solved['diagnostics']['policy_stop_reason'],
            'plan_validation_s':None if solved is None else solved['diagnostics']['validation_s']+solved['recovery'].get('validation_s',0.),
            'warm_preparation_s':None if solved is None else solved['warm_start']['preparation_s'],
            'optimization_raw_status':None if solved is None else solved['diagnostics']['return_status'],
            'unusable_updates':self.unusable_updates,'stop_requested':self.stop_requested,
            'gvs_projection_residual_max_rad_m':geometry['gvs_projection']['projection_residual_max_rad_m']}
        self.observations.append(dict(time_s=t,phase='current_state_before_integration',
            tip_position_m=geometry['tip'].tolist(),gvs_q=list(q),gvs_qdot=list(v),
            measured_initial_state=x.tolist(),graph_construction_s=self.workspace.graph_s,**self.last))
        return command


class ProfileNMPCController(GVSNMPCController):
    """Explicit v2 identity: declarative preparation and execution-local workspace."""
    def __init__(self,parameters,period_s):
        from .gvs_profile import ProfileControl, load_profile
        ProfileControl.model_validate(parameters)
        self.profile=load_profile()
        super().__init__(self.profile['parameters'],period_s)


class ReachNMPCController(GVSNMPCController):
    """v3 task parameters, public preparation, execution-local mutable workspace."""
    def __init__(self,parameters,period_s):
        from .gvs_profile import ReachControl
        self.control=ReachControl.model_validate(parameters)
        super().__init__(self.control.recipe,period_s)

    def configure(self,physics,plan):
        if not hasattr(self,'preparation'):
            raise ValueError('GVS_REACH_PUBLIC_PREPARATION_REQUIRED')
        if digest(self.profile['numerical'])!=plan['numerical_reference']['artifact_id']:
            raise ValueError('GVS_REACH_PREPARATION_IDENTITY_MISMATCH')
        super().configure(physics,plan)
