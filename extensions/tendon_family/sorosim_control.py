"""SoRoSim controller on the shared projected-state/ideal-tension protocol."""
from pydantic import Field
import time
import numpy as np
from schemas.platform_analysis import ScopedMathematicalClaim
from tools.state_io import digest
from .contracts import SorosimSolver, current_nmpc_recipe
from .gvs_profile import ReachControl


class SorosimReachControl(ReachControl):
    solver: SorosimSolver = Field(default_factory=SorosimSolver)


def checked_control(inp):
    from .generated_serial import checked_reach
    control = checked_reach(inp)
    current_nmpc_recipe(control.recipe)
    if inp.policy.backend.extension_id != 'backend.family_mujoco':
        raise ValueError('SOROSIM_REQUIRES_INDEPENDENT_MUJOCO_EXECUTION')
    if control.recipe.integration_method != 'implicit_euler':
        raise ValueError('SOROSIM_UNSUPPORTED_INTEGRATION_METHOD')
    return control


def resolve_control(inp, physics):
    from .gvs_profile import candidate_numerical
    from .gvs_projection import description
    from .gvs_basis import resolve_basis
    from .sorosim_spec import SorosimModel
    control=checked_control(inp)
    numerical=candidate_numerical(inp,control)
    basis=resolve_basis(inp.robot.structure.data,control.recipe.basis)
    plan=dict(mode='sorosim_nmpc',tension_execution_mode='ideal_tension',
        robot=inp.robot.model_dump(mode='json'),task=inp.task.model_dump(mode='json'),
        reference=numerical['nominal'],numerical_reference=dict(artifact_id=digest(numerical),media_type='application/json'),
        projector=description(physics,basis),effective_parameters=control.recipe.model_dump(mode='json'),
        solver=control.solver.model_dump(mode='json'),settling=control.settling.model_dump(mode='json'),
        specification=SorosimModel(dict(basis=control.recipe.basis,gauss_per_interval=control.solver.gauss_per_interval)).convert(
            inp.robot.structure.data,inp.policy.discretization.data,inp.task.environment.data,solver=control.solver),
        stopping=dict(policy=control.recipe.stopping_policy,iteration_ceiling=control.recipe.max_iterations,
            max_wall_s=None,max_cpu_s=None),
        failure_response='Bounded previous applied tension; stop after configured consecutive unusable updates')
    plan['identity']=digest(plan)
    return plan


class SorosimNMPCController:
    def __init__(self, parameters, period_s):
        self.control = SorosimReachControl.model_validate(parameters)
        self.parameters = self.control.recipe
        self.period_s = period_s

    def configure(self, physics, plan):
        # MATLAB Engine prepends DLL paths. Load the shared XML compiler first
        # so Conda's _elementtree resolves its own dependencies before that change.
        from . import mjcf
        from .contracts import ResolvedGVSBasis
        from .sorosim_session import SorosimSession
        if not hasattr(self,'preparation'):
            raise ValueError('SOROSIM_PUBLIC_PREPARATION_REQUIRED')
        if digest(self.profile['numerical'])!=plan['numerical_reference']['artifact_id']:
            raise ValueError('SOROSIM_PREPARATION_IDENTITY_MISMATCH')
        self.physics=physics;self.plan=plan
        self.resolved_basis=ResolvedGVSBasis.model_validate(plan['projector']['resolved_basis'])
        self.projector_id=plan['projector']['id'];self.coordinate_order=self.resolved_basis.coordinate_order
        self.limits=np.array([t['force_limit_n'] for t in physics['tendons']])
        self.previous=np.clip(plan['reference']['u0'],0,self.limits)
        self.warm=None;self.observations=[];self.last={};self.control_snapshots=[]
        self.unusable_updates=0;self.stop_requested=False;self.u=None
        self.session=SorosimSession(options=self.control.solver.engine_options)
        self.session.__enter__()
        try:
            self.construction=self.session.construct(plan['specification'])
        except BaseException:
            self.close();raise

    def request(self, t, state, *, check_only=False):
        task=self.plan['task'];timing=task['timing']
        return dict(recipe=self.parameters.model_dump(mode='json'),elapsed_s=float(t),
            measured_state=list(state),previous_input=self.previous.tolist(),warm=self.warm,
            period_s=timing['control_period_s'],duration_s=timing['duration_s'],target=task['goal']['data']['target_m'],
            position_tolerance_m=task['evaluator']['parameters']['data']['tolerance_m'],
            settling=self.plan['settling'],check_only=check_only)

    def command(self, t, geometry, q, v):
        from .control import execute_ideal_tension
        started=time.perf_counter();state=np.r_[q,v];solved=None;error=None
        try:
            solved=self.session.evaluate('nmpc',self.request(t,state))
            success=solved['accepted']
        except Exception as exc:
            success=False;error=str(exc)
        self.unusable_updates=0 if success else self.unusable_updates+1
        self.stop_requested=self.unusable_updates>=self.parameters.max_unusable_updates
        command,bridge=execute_ideal_tension(self.physics,solved['tensions'][0] if success else self.previous)
        previous=self.previous.copy();self.previous=command.copy()
        if success:
            self.warm={k:solved[k] for k in ('states','tensions')}
        flag=None if solved is None else solved['exitflag']
        elapsed=time.perf_counter()-started
        self.last=dict(**bridge,plan_accepted=success,solver_failed=not success,solver_error=error,
            solver_outcome='numerical_error' if error else 'unusable_solve' if not success else 'convergence' if flag>0 else 'iteration_limit_feasible',
            optimization_status=None if solved is None else 'converged' if flag>0 else 'iteration_limit' if flag==0 else 'failed',
            optimization_raw_status=None if flag is None else f'fmincon_exitflag_{flag}',
            optimization_nonconverged=flag is None or flag<=0,feasible_suboptimal_update=success and flag==0,
            optimization_constraint_violation=None if solved is None else solved['constraint_violation'],
            optimization_selected_iteration=None if solved is None else solved['selected_iteration'],
            optimization_returned_violation=None if solved is None else solved['returned_constraint_violation'],
            failure_response_used=not success and not self.stop_requested,
            plan_source=None if not success else 'reintegrated_returned_iterate' if solved['recovery']['selected'] else 'fmincon_selected',
            feasibility_recovery=None if solved is None else solved['recovery'],
            update_wall_s=elapsed,deadline_missed=elapsed>self.period_s,unusable_updates=self.unusable_updates,
            stop_requested=self.stop_requested,solver_construction_s=self.construction['construction_s'] if not self.observations else 0.,
            optimization_solve_s=None if solved is None else solved['optimization_s'],
            warm_preparation_s=None if solved is None else solved['warm_preparation_s'],
            plan_validation_s=None if solved is None else solved['validation_s'],
            recovery_wall_s=None if solved is None else solved['recovery']['wall_s'],
            policy_stop_reason='iteration_convergence_policy_no_time_limit',
            gvs_projection_residual_max_rad_m=geometry['gvs_projection']['projection_residual_max_rad_m'])
        if success:
            node=self.parameters.substeps
            self.last['one_step_prediction']=dict(time_s=t+self.period_s,state=solved['states'][node],
                tip_position_m=solved['tip_positions'][node-1],tip_velocity_m_s=solved['tip_velocities'][node-1],
                frame='world',prediction_source='accepted_plan',applied_tension_n=list(command),
                integration=self.parameters.integration_method,substeps=node)
        claim=ScopedMathematicalClaim(conclusion='feasible_witness' if success else 'inconclusive',
            binding=dict(controller_identity=self.plan['identity'],physical_identity=self.physics['identity']),
            requirement_identity=digest(self.plan['task']),model_identity=self.plan['specification']['identity'],
            model_declaration=dict(model='model.sorosim_gvs@1.0.0',solver='MATLAB fmincon SQP'),
            protocol_identity=digest(dict(recipe=self.parameters.model_dump(mode='json'),solver=self.plan['solver'])),
            operating_point=dict(time_s=t,measured_state=state.tolist(),previous_input=previous.tolist()),
            horizon=dict(intervals=None if solved is None else solved['horizon'],period_s=self.period_s),
            physical_inputs=dict(tendon_order=self.plan['specification']['tendon_order'],force_limits_n=self.limits.tolist()),
            constraint_coverage=[dict(kind=k,verified=success) for k in ('initial_state','implicit_dynamics','tension_bounds')],
            numerical_result_pointer='/mathematical_facts/independent_validation',computation_status='error' if error else 'returned',
            verification_status='passed' if success else 'not_accepted',
            supported_interpretation='Model-local numerically feasible plan' if success else 'This update has no accepted plan; failure does not establish infeasibility',
            unsupported_conclusions=['physical task success','nonlinear stability','global optimality','100 Hz real-time control','S4 analysis'])
        self.observations.append(dict(time_s=float(t),phase='current_state_before_integration',
            tip_position_m=geometry['tip'].tolist(),gvs_q=list(q),gvs_qdot=list(v),
            measured_initial_state=state.tolist(),graph_construction_s=self.construction['construction_s'],
            mathematical_facts=solved,verified_conclusions=[claim.model_dump(mode='json')],
            research_interpretations=[],matlab_call_timing=self.session.timings['calls'][-1],**self.last))
        elapsed=time.perf_counter()-started
        self.last.update(update_wall_s=elapsed,deadline_missed=elapsed>self.period_s)
        self.observations[-1].update(update_wall_s=elapsed,deadline_missed=elapsed>self.period_s)
        return command

    def close(self):
        if getattr(self, 'session', None) is not None:
            self.session.close()
