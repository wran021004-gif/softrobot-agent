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
    from .gvs_profile import checked_reach,reach_numerical
    p=checked_reach(inp).recipe;numerical=reach_numerical(inp);point=numerical['nominal']
    basis=resolve_basis(inp.robot.structure.data,p.basis)
    plan=dict(mode='gvs_nmpc',tension_execution_mode='ideal_tension',
        robot=inp.robot.model_dump(mode='json'),task=inp.task.model_dump(mode='json'),
        reference=dict(kind='gvs_nominal_metadata',target_world_m=inp.task.goal.data.get('target_m'),
            q0=point['q0'],u0=point['u0'],derivation=point),
        projector=description(physics,basis),effective_parameters=p.model_dump(mode='json'),
        stopping=dict(policy=p.stopping_policy,iteration_ceiling=p.max_iterations,numerical_tolerance=p.tolerance,
            feasible_return=None if p.stopping_policy=='research_work_v1' or p.feasible_return is None else p.feasible_return.model_dump(mode='json'),
            max_cpu_s=None if p.stopping_policy=='research_work_v1' else p.max_cpu_s,
            max_wall_s=None,
            external_watchdog='Enclosing execution interruption is incomplete/timeout, never a successful timed command'),
        timing=dict(period_s=inp.task.timing.control_period_s,prediction_interval_s=inp.task.timing.control_period_s,
            physics_step_s=inp.task.timing.timestep_s,observation='interval_start_pre_step'),
        plan_acceptance='Independently feasible converged, iteration-limited or intentional early-stop plans. Early stops are suboptimal, not convergence or solver errors; raw termination is retained.',
        failure_response='Hold last bounded tension on an unusable solve (clipped nominal initially); stop after max_unusable_updates consecutive unusable updates. Every applied hold is recorded.')
    plan['reference']['kind']='numerical_guess_metadata_not_current_target_equilibrium'
    plan['reference'].pop('target_world_m')
    plan['reference']['provenance']=numerical['provenance']
    plan['numerical_reference']=dict(artifact_id=digest(numerical),media_type='application/json')
    if checked_reach(inp).settling is not None:
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
        self.control_snapshots=[]
        from .control_evidence import RECORD_UPDATE_IDS
        self.record_update_ids=RECORD_UPDATE_IDS.get()

    def command(self,t,geometry,q,v):
        start=time.perf_counter();x=np.r_[q,v];error=None;solved=None
        update_id=len(self.observations)
        self.workspace.solver.diagnostic_trace=update_id in self.record_update_ids
        from .control_evidence import COMPLETE_UPDATE_INPUTS
        self.workspace.solver.complete_record=COMPLETE_UPDATE_INPUTS.get()
        before_solve=None
        if self.workspace.solver.complete_record:
            from copy import deepcopy
            self.workspace.solver.last_input_record=None
            source=self.seed if self.seed is not None else self.workspace.last
            before_solve=dict(measured_state=x.tolist(),previous_applied_input_n=self.previous.tolist(),
                warm_source=None if source is None else deepcopy({k:source[k] for k in ('states','tensions')}),
                source_kind='explicit' if self.seed is not None else 'workspace_last',
                controller_identity=self.plan['identity'])
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
        raw_status=None if solved is None else solved['diagnostics']['return_status']
        outcome=('numerical_error' if error else 'unusable_solve' if not success else
            'acceptable_convergence' if raw_status=='Solved_To_Acceptable_Level' else
            'convergence' if converged else 'iteration_limit_feasible' if solved['result']['status']=='iteration_limit' else 'feasible_early_stop')
        self.last={**bridge,'plan_accepted':success,'solver_failed':not success,'solver_outcome':outcome,
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
        if success and (self.workspace.tracking or 'settling' in self.plan):
            node=self.parameters.substeps
            predicted=np.asarray(solved['states'][node])
            tip,velocity=self.workspace._motion(predicted[:len(q)],predicted[len(q):])
            self.last['one_step_prediction']=dict(time_s=t+self.period_s,state=predicted.tolist(),
                tip_position_m=np.asarray(tip).ravel().tolist(),tip_velocity_m_s=np.asarray(velocity).ravel().tolist(),
                frame='world',prediction_source='accepted_plan',applied_tension_n=list(command),integration=self.parameters.integration_method,substeps=node)
        self.observations.append(dict(time_s=t,phase='current_state_before_integration',
            tip_position_m=geometry['tip'].tolist(),gvs_q=list(q),gvs_qdot=list(v),
            measured_initial_state=x.tolist(),graph_construction_s=self.workspace.graph_s,**self.last))
        if solved is not None and 'complete_update' in solved:
            capture_start=time.perf_counter()
            record=solved['complete_update']
            record.update(update_id=update_id, time_s=float(t), actual_applied_action_n=list(command),
                plan_identity=self.plan['identity'], coordinate_order=list(self.coordinate_order),
                selection=dict(accepted=success, source=self.last['plan_source'],
                    reason=self.last['policy_stop_reason'], failure_response=self.last['failure_response_used']))
            self.observations[-1]['complete_update_record']=record
            self.observations[-1]['complete_record_capture_s']=time.perf_counter()-capture_start
        elif before_solve is not None:
            self.observations[-1]['failed_update_input_record']=dict(**before_solve,
                initialization=getattr(self.workspace.solver,'last_input_record',None),
                error=error,actual_applied_action_n=list(command),
                missing='No completed optimization result; missing solver inputs are not invented')
        if self.workspace.solver.diagnostic_trace and solved is not None:
            from .control_evidence import capture_snapshot
            capture_start=time.perf_counter()
            snapshot=capture_snapshot(self.workspace,solved,update_id,t,command,geometry)
            snapshot['capture_wall_s']=time.perf_counter()-capture_start
            self.control_snapshots.append(snapshot)
            self.observations[-1]['control_snapshot_id']=snapshot['snapshot_id']
            self.observations[-1]['snapshot_capture_wall_s']=snapshot['capture_wall_s']
        # Prediction evaluation and observation construction are operational work.
        elapsed=time.perf_counter()-start
        self.last.update(update_wall_s=elapsed,deadline_missed=elapsed>self.period_s)
        self.observations[-1].update(update_wall_s=elapsed,deadline_missed=elapsed>self.period_s)
        return command




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




def deadline_horizon(duration_s, time_s, period_s, maximum):
    remaining=(duration_s-time_s)/period_s
    if not np.isfinite(remaining) or abs(remaining-round(remaining))>1e-7 or round(remaining)<1:
        raise ValueError('DEADLINE_HORIZON_REQUIRES_ALIGNED_PREDEADLINE_UPDATE')
    return min(maximum,round(remaining))


class DeadlineReachNMPCController(ReachNMPCController):
    """v7: shrink the prediction horizon when the official deadline enters it.

    Same transcription, objective weights, bounds, stopping and selection rules.
    The terminal objective moves to the actual deadline; settling is separate.
    Graph construction remains part of complete-update timing.
    """
    def command(self,t,geometry,q,v):
        start=time.perf_counter()
        horizon=deadline_horizon(self.workspace.duration,t,self.period_s,self.parameters.horizon)
        if horizon!=self.workspace.parameters.horizon:
            old=self.workspace;source=self.seed if self.seed is not None else old.last
            shift=0 if self.seed is not None else self.parameters.substeps
            seed=None if source is None else dict(
                states=source['states'][shift:shift+horizon*self.parameters.substeps+1],
                tensions=source['tensions'][int(bool(shift)):int(bool(shift))+horizon])
            parameters=self.parameters.model_copy(update={'horizon':horizon})
            self.workspace=TrajectoryWorkspace(TaskDefinition.model_validate(self.plan['task']),
                RobotDescription.model_validate(self.plan['robot']),parameters,
                old.nominal_x,old.nominal_u,settling=self.plan.get('settling'))
            self.seed=seed;self.workspace.last=seed
        construction_s=time.perf_counter()-start
        command=super().command(t,geometry,q,v)
        elapsed=time.perf_counter()-start
        timing=dict(update_wall_s=elapsed,deadline_missed=elapsed>self.period_s,
            effective_horizon=horizon,deadline_horizon_preparation_s=construction_s)
        self.last.update(timing);self.observations[-1].update(timing)
        return command


class TaskConditionedNMPCController(DeadlineReachNMPCController):
    """Development route: legacy Reach or ordered local-progress Tracking."""
    def command(self, t, geometry, q, v):
        if self.workspace.tracking:
            return GVSNMPCController.command(self, t, geometry, q, v)
        return super().command(t, geometry, q, v)
