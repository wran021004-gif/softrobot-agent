"""Trusted fixed-design GVS dynamic transcription and reusable NMPC workspace."""
import time
from contextvars import ContextVar
from contextlib import contextmanager
import casadi as ca
import numpy as np
from schemas.platform import Binding, Objective, Payload
from schemas.platform_math import OptimizationConstraint, OptimizationProblem, SystemContext
from tools.state_io import digest
from extensions.optimization.ipopt import IpoptSolver, expression_payload
from .contracts import GVSModelParameters, GVSTrajectoryParameters
from .gvs import GVSModel, coordinate_order
from .gvs_casadi import expression_from_system, functions_for
from .pcc import quaternion_wxyz_to_rotation
_FUNCTION_PROVIDER = ContextVar('gvs_trajectory_function_provider', default=None)

@contextmanager
def use_trajectory_functions(provider):
    """Execution-scoped experimental evaluator; default production is unchanged."""
    token = _FUNCTION_PROVIDER.set(provider)
    try:
        yield
    finally:
        _FUNCTION_PROVIDER.reset(token)

def trajectory_functions(expression):
    original = functions_for(expression)
    provider = _FUNCTION_PROVIDER.get()
    return original if provider is None else provider(original)

def implicit_step_residual(functions, n, m, h, method='implicit_euler'):
    """Shared shooting and tail-initialization residual in physical coordinates."""
    previous = ca.MX.sym('previous_state', 2 * n)
    following = ca.MX.sym('next_state', 2 * n)
    tension = ca.MX.sym('tension', m)
    if method not in ('implicit_euler', 'implicit_midpoint'):
        raise ValueError('UNKNOWN_INTEGRATION_METHOD')
    evaluation = following if method == 'implicit_euler' else (previous + following) / 2
    return ca.Function('gvs_implicit_step_residual', [previous, following, tension], [ca.vertcat((following[:n] - previous[:n] - h * evaluation[n:]) / 10.0, functions.implicit_residual(evaluation, tension, (following[n:] - previous[n:]) / h) / 0.001)], {'cse': True, 'ad_weight': 1.0})

def trajectory_authorization(robot, space, parameters):
    p = GVSTrajectoryParameters.model_validate(parameters)
    coordinates = coordinate_order(robot.structure.data, p.basis)
    n = len(coordinates)
    result = {}
    for k in range(p.horizon * p.substeps + 1):
        for j in range(2 * n):
            result[f'x/{k}/{j}'] = dict(type='number', bounds=[None, None], units='1', physical_coordinate=coordinates[j % n] + ('.rate' if j >= n else ''), physical_scale=p.curvature_scale_rad_m if j < n else p.rate_scale_rad_m_s, physical_units='rad/m' if j < n else 'rad/(m*s)')
    for k in range(p.horizon):
        for t in robot.structure.data['tendons']:
            result[f"u/{k}/{t['id']}"] = dict(type='number', bounds=[0.0, t['force_limit_n']], units='N')
    for t in robot.structure.data['tendons']:
        result['previous_u/' + t['id']] = dict(type='number', bounds=[0.0, t['force_limit_n']], units='N')
    if p.reference_mode != 'constant':
        for k in range(1, p.horizon*p.substeps+1):
            for field, unit in (('reference', 'm'), ('reference_velocity', 'm/s')):
                for j in range(3):
                    result[f'{field}/{k}/{j}'] = dict(type='number', bounds=[0., 0.], units=unit)
        for field, unit in (('path_anchor', 'm'), ('path_tangent', '1')):
            for j in range(3):
                result[f'{field}/{j}'] = dict(type='number', bounds=[0., 0.], units=unit)
    if p.holding_tip_speed_weight:
        for k in range(1, p.horizon * p.substeps + 1):
            result[f'holding/{k}'] = dict(type='number', bounds=[0.0, 1.0], units='1')
    return result

class GVSTrajectoryAssembler:

    def __init__(self, parameters):
        self.parameters = GVSTrajectoryParameters.model_validate(parameters)

    def assemble(self, task, robot, space, mathematical_model, specification, context):
        p = self.parameters
        from tools.research_tasks import ResearchTaskAdapter
        adapter = ResearchTaskAdapter(dict(task=task.model_dump(mode='json')))
        reference = adapter.control_reference()
        tracking = reference['kind'] != 'constant'
        if p.reference_mode != reference['kind']:
            raise ValueError('CONTROL_REFERENCE_MODE_MUST_MATCH_TASK')
        if tracking and any((p.holding_tip_speed_weight, p.terminal_tip_speed_weight,
                             p.velocity_weight, p.terminal_velocity_weight)):
            raise ValueError('TRACKING_HAS_NO_ABSOLUTE_SPEED_HOLDING_COST')
        if p.relative_velocity_weight and p.reference_mode != 'timed':
            raise ValueError('RELATIVE_VELOCITY_REQUIRES_TIMED_REFERENCE')
        if (p.progress_weight or p.regression_weight) and p.reference_mode != 'free_progress':
            raise ValueError('PROGRESS_COST_REQUIRES_FREE_PROGRESS')
        expected = trajectory_authorization(robot, {}, p)
        if specification.variables != list(expected) or space != expected:
            raise ValueError('GVS_TRAJECTORY_REQUIRES_FIXED_DESIGN_ORDER_AND_PHYSICAL_BOUNDS')
        if specification.horizon != p.horizon or [s.template_id for s in specification.objectives] != ['dynamic_tip_tracking']:
            raise ValueError('GVS_TRAJECTORY_SPECIFICATION_MISMATCH')
        if {s.template_id for s in specification.constraints} != {'initial_state', 'implicit_dynamics', 'tendon_force_bounds'}:
            raise ValueError('GVS_TRAJECTORY_CONSTRAINTS_REQUIRED')
        n = len(coordinate_order(robot.structure.data, p.basis))
        m = len(robot.structure.data['tendons'])
        if len(context.x0) != 2 * n or len(context.u0) != m:
            raise ValueError(f'GVS_TRAJECTORY_INITIAL_STATE_AND_PREVIOUS_TENSION_REQUIRED: context.x0 requires {2 * n} [q,qdot] values; context.u0 requires {m} tendon tensions')
        model_params = GVSModelParameters(basis=p.basis)
        system = GVSModel(model_params).build_system(robot, model_params, None, SystemContext(x0=context.x0, u0=context.u0, scene=task.environment))
        functions = trajectory_functions(expression_from_system(system))
        steps = p.horizon * p.substeps
        decision_symbols = {name: ca.MX.sym('v_' + str(i)) for i, name in enumerate(expected)}
        symbols = {name: value * expected[name].get('physical_scale', 1.0) for name, value in decision_symbols.items()}
        X = [ca.vertcat(*[symbols[f'x/{k}/{j}'] for j in range(2 * n)]) for k in range(steps + 1)]
        tendons = [t['id'] for t in robot.structure.data['tendons']]
        U = [ca.vertcat(*[symbols[f'u/{k}/{t}'] for t in tendons]) for k in range(p.horizon)]
        previous = ca.vertcat(*[symbols['previous_u/' + t] for t in tendons])
        assembly = task.environment.data
        rotation = quaternion_wxyz_to_rotation(assembly['mount']['quaternion_wxyz'])
        local_tip = ca.Function('local_tip', [functions.q_symbol], [functions.tip_position_expression])
        tip_rate = ca.MX.sym('tip_rate', n)
        local_velocity = ca.Function('local_tip_velocity', [functions.q_symbol, tip_rate], [ca.jacobian(functions.tip_position_expression, functions.q_symbol) @ tip_rate]) if p.relative_velocity_weight or p.terminal_tip_speed_weight or p.holding_tip_speed_weight else None
        target = None if tracking else ca.DM(adapter.reference_at([0.])[0][0])
        mount = ca.DM(assembly['mount']['position_m'])
        dt = task.timing.control_period_s
        h = dt / p.substeps
        constraints = {}
        objective = 0
        if task.evaluator.extension_id != ('evaluate.tracking' if tracking else 'evaluate.reach'):
            raise ValueError('GVS_TRAJECTORY_TASK_EVALUATOR_MISMATCH')
        tolerance = p.position_error_scale_m or task.evaluator.parameters.data['max_error_m' if tracking else 'tolerance_m']
        step_residual = implicit_step_residual(functions, n, m, h, p.integration_method)
        mapped = step_residual.map(steps, 'thread', p.evaluation_threads)
        residuals = mapped(ca.horzcat(*X[:-1]), ca.horzcat(*X[1:]), ca.horzcat(*[U[k // p.substeps] for k in range(steps)]))
        for k in range(steps):
            x, y, u = (X[k], X[k + 1], U[k // p.substeps])
            residual = residuals[:, k]
            for j in range(2 * n):
                constraints[f'dynamics_{k}_{j}'] = residual[j]
            tip = ca.mtimes(ca.DM(rotation), local_tip(y[:n])) + mount
            if tracking:
                target = ca.vertcat(*[symbols[f'reference/{k+1}/{j}'] for j in range(3)])
            objective += h * (p.tracking_weight * ca.sumsqr((tip - target) / tolerance) + p.velocity_weight * ca.sumsqr(y[n:]))
            if p.relative_velocity_weight:
                reference_velocity = ca.vertcat(*[symbols[f'reference_velocity/{k+1}/{j}'] for j in range(3)])
                velocity = ca.DM(rotation) @ local_velocity(y[:n], y[n:])
                objective += h*p.relative_velocity_weight*ca.sumsqr((velocity-reference_velocity)/p.tip_speed_scale_m_s)
            if p.reference_mode == 'free_progress':
                anchor = ca.vertcat(*[symbols[f'path_anchor/{j}'] for j in range(3)])
                tangent = ca.vertcat(*[symbols[f'path_tangent/{j}'] for j in range(3)])
                advance = ca.dot(tip-anchor, tangent)/tolerance
                objective += h*(-p.progress_weight*advance+p.regression_weight*ca.fmax(-advance, 0)**2)
            if p.holding_tip_speed_weight:
                speed = ca.mtimes(ca.DM(rotation), local_velocity(y[:n], y[n:]))
                normalization = p.holding_speed_cost_window_s if p.holding_speed_cost_mode == 'window_normalized_v1' else 1.0
                objective += h * p.holding_tip_speed_weight / normalization * symbols[f'holding/{k + 1}'] * ca.sumsqr(speed / p.tip_speed_scale_m_s)
        for k, u in enumerate(U):
            objective += dt * (p.tension_weight * ca.sumsqr(u) + p.variation_weight * ca.sumsqr(u - (previous if k == 0 else U[k - 1])))
        objective += p.terminal_weight * ca.sumsqr((tip - target) / tolerance) + p.terminal_velocity_weight * ca.sumsqr(X[-1][n:])
        if p.terminal_tip_speed_weight:
            world_velocity = ca.mtimes(ca.DM(rotation), local_velocity(X[-1][:n], X[-1][n:]))
            objective += p.terminal_tip_speed_weight * ca.sumsqr(world_velocity / p.tip_speed_scale_m_s)
        objective *= specification.objectives[0].weight
        bundle, selectors = expression_payload(list(expected), dict(variables=decision_symbols, expression=objective), constraints)
        variables = {name: dict(spec) for name, spec in expected.items()}
        for j, value in enumerate(context.x0):
            scale = variables[f'x/0/{j}']['physical_scale']
            variables[f'x/0/{j}']['bounds'] = [value / scale, value / scale]
        for t, value in zip(tendons, context.u0):
            variables['previous_u/' + t]['bounds'] = [value, value]
        if p.holding_tip_speed_weight:
            for k in range(1, steps + 1):
                variables[f'holding/{k}']['bounds'] = [0.0, 0.0]
        guess = dict(specification.initial_guess)
        if tracking:
            for name in expected:
                if name.startswith(('reference/', 'reference_velocity/', 'path_anchor/', 'path_tangent/')):
                    guess[name] = 0.
        if p.holding_tip_speed_weight:
            for k in range(1, steps + 1):
                guess[f'holding/{k}'] = 0.0
        for t, value in zip(tendons, context.u0):
            guess['previous_u/' + t] = value
        for k in range(steps + 1):
            for j, value in enumerate(context.x0):
                guess.setdefault(f'x/{k}/{j}', value / variables[f'x/{k}/{j}']['physical_scale'])
        for k in range(p.horizon):
            for t, value in zip(tendons, context.u0):
                guess.setdefault(f'u/{k}/{t}', value)
        return OptimizationProblem(variables=variables, objective=Objective(metric='gvs_dynamic_tracking_cost', direction='minimize', units='dimensionless'), objective_function=bundle, constraints=[OptimizationConstraint(name=name, expression=selector, units='scaled_residual', lower=0.0, upper=0.0) for name, selector in zip(constraints, selectors)], initial_guess=guess, horizon=p.horizon, model_reference=Binding(extension_id='model.gvs', parameters=Payload(contract='family.gvs_model', data=model_params.model_dump(mode='json'))))

class TrajectoryWorkspace:
    """One graph and IPOPT instance; each update changes fixed initial bounds."""

    def __init__(self, task, robot, parameters, nominal_x, nominal_u, *, settling=None):
        from tools.platform_registry import registry
        from tools.platform_optimization import assemble_optimization
        from schemas.platform_math import OptimizationSpecification, ObjectiveSelection, ConstraintSelection
        self.parameters = GVSTrajectoryParameters.model_validate(parameters)
        self.n = len(nominal_x) // 2
        from tools.research_tasks import ResearchTaskAdapter
        self.reference = ResearchTaskAdapter(dict(task=task.model_dump(mode='json')))
        self.tracking = self.reference.control_reference()['kind'] != 'constant'
        self.path_segment = 0
        self.duration = task.timing.duration_s
        self.holding_start = None
        if self.parameters.holding_tip_speed_weight:
            if settling is None:
                raise ValueError('GVS_HOLDING_COST_REQUIRES_SETTLING_CONFIGURATION')
            from .gvs_profile import SampledSettling
            self.holding_start = self.duration - SampledSettling.model_validate(settling).window_s
            if self.parameters.holding_speed_cost_mode == 'window_normalized_v1' and abs(self.parameters.holding_speed_cost_window_s - SampledSettling.model_validate(settling).window_s) > 1e-12:
                raise ValueError('HOLDING_COST_NORMALIZATION_MUST_MATCH_DECLARED_TASK_WINDOW')
        self.state_scales = np.r_[np.full(self.n, self.parameters.curvature_scale_rad_m), np.full(self.n, self.parameters.rate_scale_rad_m_s)]
        self.m = len(nominal_u)
        self.nominal_x = list(nominal_x)
        self.nominal_u = list(nominal_u)
        self.tendons = [t['id'] for t in robot.structure.data['tendons']]
        self.period = task.timing.control_period_s
        self.target = None if self.tracking else self.reference.reference_at([0.])[0][0]
        self.goal_tolerance = task.evaluator.parameters.data['max_error_m' if self.tracking else 'tolerance_m']
        reg = registry()
        start = time.perf_counter()
        binding = Binding(extension_id='optimization_assembler.gvs_trajectory', parameters=Payload(contract='family.gvs_trajectory_parameters', data=self.parameters.model_dump(mode='json')))
        space = trajectory_authorization(robot, {}, self.parameters)
        self.problem = assemble_optimization(reg, binding, task=task, robot=robot, space=space, mathematical_model=GVSModelParameters(basis=self.parameters.basis).mathematical_model, specification=OptimizationSpecification(variables=list(space), horizon=self.parameters.horizon, objectives=[ObjectiveSelection(template_id='dynamic_tip_tracking')], constraints=[ConstraintSelection(template_id=k) for k in ('initial_state', 'implicit_dynamics', 'tendon_force_bounds')]), context=SystemContext(x0=nominal_x, u0=nominal_u, scene=task.environment))
        self.graph_s = time.perf_counter() - start
        research = self.parameters.stopping_policy == 'research_work_v1'
        self.solver = IpoptSolver(dict(max_iterations=self.parameters.max_iterations, tolerance=self.parameters.tolerance, max_cpu_s=None if research else self.parameters.max_cpu_s, max_wall_s=None, retain_feasible_iterate=True, feasible_return=None if research else self.parameters.feasible_return, constraint_jacobian_mode=self.parameters.constraint_jacobian_mode))
        self.robot = robot
        self.scene = task.environment
        self._tail_solver = None
        self.last = None

    def _prepare_tail(self):
        construction = time.perf_counter()
        if self._tail_solver is None:
            p = GVSModelParameters(basis=self.parameters.basis)
            system = GVSModel(p).build_system(self.robot, p, None, SystemContext(x0=self.nominal_x, u0=self.nominal_u, scene=self.scene))
            functions = trajectory_functions(expression_from_system(system))
            q = functions.q_symbol
            v = ca.MX.sym('motion_rate', self.n)
            local_tip = functions.tip_position_expression
            assembly = self.scene.data
            world_tip = ca.mtimes(ca.DM(quaternion_wxyz_to_rotation(assembly['mount']['quaternion_wxyz'])), local_tip) + ca.DM(assembly['mount']['position_m'])
            self._motion = ca.Function('warm_tip_motion', [q, v], [world_tip, ca.jacobian(world_tip, q) @ v])
            self._tail_residual = implicit_step_residual(functions, self.n, self.m, self.period / self.parameters.substeps, self.parameters.integration_method)
            y = ca.MX.sym('scaled_next', 2 * self.n)
            old = ca.MX.sym('old', 2 * self.n)
            u = ca.MX.sym('u', self.m)
            residual = ca.Function('tail_residual', [y, old, u], [self._tail_residual(old, y * self.state_scales, u)], {'ad_weight': 1.0})
            self._tail_solver = ca.rootfinder('tail_step', 'newton', residual, {'abstol': self.parameters.root_tolerance, 'max_iter': 30, 'error_on_fail': True})
        return time.perf_counter() - construction

    def _extend_tail(self, state, tension, guess=None):
        construction_s = self._prepare_tail()
        start = time.perf_counter()
        repeated_defect = None
        if self.parameters.stopping_policy != 'research_work_v1' or not self.parameters.regenerate_warm_states:
            repeated_defect = float(np.max(abs(np.asarray(self._tail_residual(state, state, tension)))))
        following = np.asarray(self._tail_solver(np.asarray(state if guess is None else guess) / self.state_scales, state, tension)).ravel() * self.state_scales
        defect = float(np.max(abs(np.asarray(self._tail_residual(state, following, tension)))))
        if not np.isfinite(following).all() or not np.isfinite(defect) or defect > 1e-05:
            raise RuntimeError('REGENERATED_STEP_FAILED_ORIGINAL_FEASIBILITY_CHECK')
        return (following, dict(construction_s=construction_s, integration_s=time.perf_counter() - start, repeated_terminal_scaled_defect=repeated_defect, extended_tail_scaled_defect=defect))

    def _set_prediction_time(self, elapsed_s):
        if self.holding_start is None:
            return None
        if elapsed_s is None or not np.isfinite(elapsed_s) or elapsed_s < 0:
            raise ValueError('GVS_HOLDING_COST_REQUIRES_CURRENT_EXECUTION_TIME')
        times = elapsed_s + np.arange(1, self.parameters.horizon * self.parameters.substeps + 1) * self.period / self.parameters.substeps
        braking_start = max(0.0, self.holding_start - self.parameters.holding_brake_lead_s)
        weights = (times >= braking_start - 1e-09).astype(float)
        for k, weight in enumerate(weights, 1):
            self.problem.variables[f'holding/{k}']['bounds'] = [float(weight)] * 2
            self.problem.initial_guess[f'holding/{k}'] = float(weight)
        return dict(current_time_s=float(elapsed_s), node_times_s=times.tolist(), holding_active=weights.tolist(), task_endpoint_s=self.duration, holding_start_s=self.holding_start, braking_start_s=braking_start, holding_brake_lead_s=self.parameters.holding_brake_lead_s, beyond_task='Holding continues beyond the task endpoint inside the prediction only; execution duration is unchanged.')

    def _set_reference(self, measured_x, elapsed_s):
        self._prepare_tail()
        p = self.parameters
        times = elapsed_s + np.arange(1, p.horizon*p.substeps+1)*self.period/p.substeps
        local = None
        if p.reference_mode == 'free_progress':
            tip, _ = self._motion(measured_x[:self.n], measured_x[self.n:])
            local = self.reference.local_path_reference(np.asarray(tip).ravel(), self.path_segment,
                                                       p.path_lookahead_m, p.path_capture_m)
            self.path_segment = local['segment']
            positions = np.tile(local['position_m'], (len(times), 1))
            velocities = np.zeros_like(positions)
            for field, values in (('path_anchor', local['anchor_m']), ('path_tangent', local['tangent'])):
                for j, value in enumerate(values):
                    self.problem.variables[f'{field}/{j}']['bounds'] = [value]*2
                    self.problem.initial_guess[f'{field}/{j}'] = value
        else:
            # No extrapolation or silent time clamping; callers must shorten the
            # offline timed horizon before it exceeds the declared reference.
            positions, velocities = self.reference.reference_at(times)
        for k, (position, velocity) in enumerate(zip(positions, velocities), 1):
            for field, values in (('reference', position), ('reference_velocity', velocity)):
                for j, value in enumerate(values):
                    value = float(value)
                    self.problem.variables[f'{field}/{k}/{j}']['bounds'] = [value]*2
                    self.problem.initial_guess[f'{field}/{k}/{j}'] = value
        self.target = positions[-1]
        return dict(reference_kind=p.reference_mode, current_time_s=float(elapsed_s),
                    node_times_s=times.tolist(), positions_m=positions.tolist(),
                    velocities_m_s=velocities.tolist(), local_progress=local,
                    horizon_is_task_deadline=False if local is not None else None)

    def solve(self, measured_x, previous_u, warm=None, *, elapsed_s=None):
        update_start = time.perf_counter()
        prediction_timing = (self._set_reference(measured_x, 0. if elapsed_s is None else elapsed_s)
                             if self.tracking else self._set_prediction_time(elapsed_s))
        for j, value in enumerate(measured_x):
            self.problem.variables[f'x/0/{j}']['bounds'] = [float(value) / self.state_scales[j]] * 2
        for t, value in zip(self.tendons, previous_u):
            self.problem.variables['previous_u/' + t]['bounds'] = [float(value)] * 2
        source = warm if warm is not None else self.last
        recording = None
        if self.solver.diagnostic_trace or getattr(self.solver, 'complete_record', False):
            from copy import deepcopy
            recording = dict(warm_source='explicit' if warm is not None else 'previous_selected', warm_before_preparation=None if source is None else deepcopy({k: source[k] for k in ('states', 'tensions')}))
        tails = []
        if source is not None:
            X = np.asarray(source['states'])
            U = np.asarray(source['tensions'])
            s = 0 if warm is not None else self.parameters.substeps
            if s:
                X = np.concatenate([X[s:], np.repeat(X[-1:], s, axis=0)])
                U = np.concatenate([U[1:], U[-1:]])
                if not self.parameters.regenerate_warm_states:
                    for k in range(len(X) - s, len(X)):
                        X[k], diagnostic = self._extend_tail(X[k - 1], U[-1])
                        tails.append(diagnostic)
            if self.parameters.regenerate_warm_states:
                X = X.copy()
                X[0] = measured_x
                for k in range(1, len(X)):
                    X[k], diagnostic = self._extend_tail(X[k - 1], U[(k - 1) // self.parameters.substeps], X[k])
                    tails.append(diagnostic)
            for k in range(len(X)):
                for j in range(2 * self.n):
                    self.problem.initial_guess[f'x/{k}/{j}'] = float(X[k, j]) / self.state_scales[j]
            for k in range(len(U)):
                for j, t in enumerate(self.tendons):
                    self.problem.initial_guess[f'u/{k}/{t}'] = float(U[k, j])
        elif self.parameters.regenerate_warm_states:
            state = np.asarray(measured_x)
            for k in range(self.parameters.horizon):
                for t, value in zip(self.tendons, previous_u):
                    self.problem.initial_guess[f'u/{k}/{t}'] = float(value)
            for k in range(1, self.parameters.horizon * self.parameters.substeps + 1):
                state, diagnostic = self._extend_tail(state, previous_u)
                tails.append(diagnostic)
                for j, value in enumerate(state):
                    self.problem.initial_guess[f'x/{k}/{j}'] = float(value) / self.state_scales[j]
        for j, value in enumerate(measured_x):
            self.problem.initial_guess[f'x/0/{j}'] = float(value) / self.state_scales[j]
        for t, value in zip(self.tendons, previous_u):
            self.problem.initial_guess['previous_u/' + t] = float(value)
        preparation_s = time.perf_counter() - update_start
        seed_settled = False
        if not self.tracking and self.parameters.feasible_return is not None and (self._tail_solver is not None):
            metrics = []
            for k in range(self.parameters.horizon * self.parameters.substeps + 1):
                state = np.array([self.problem.initial_guess[f'x/{k}/{j}'] for j in range(2 * self.n)]) * self.state_scales
                tip, speed = self._motion(state[:self.n], state[self.n:])
                metrics.append((np.linalg.norm(np.asarray(tip).ravel() - self.target), np.linalg.norm(np.asarray(speed))))
            seed_settled = all((e <= self.parameters.seed_position_tolerance_fraction * self.goal_tolerance and v <= self.parameters.seed_speed_limit_m_s for e, v in metrics))
        preparation_s = time.perf_counter() - update_start
        start = time.perf_counter()
        result = self.solver.solve(self.problem, seed_settled=seed_settled)
        total = time.perf_counter() - start
        selected_before_recovery = dict(result.optimum) if getattr(self.solver, 'complete_record', False) else None
        recovery = dict(enabled=self.parameters.recover_returned_tensions, attempted=False, selected=False, wall_s=0.0)
        if self.parameters.recover_returned_tensions and result.status in ('converged', 'iteration_limit', 'feasible_early_stop'):
            result, recovery = self._recover_returned(result, measured_x)
        values = result.optimum
        steps = self.parameters.horizon * self.parameters.substeps
        X = np.array([[values[f'x/{k}/{j}'] * self.state_scales[j] for j in range(2 * self.n)] for k in range(steps + 1)])
        U = np.array([[values[f'u/{k}/{t}'] for t in self.tendons] for k in range(self.parameters.horizon)])
        output = dict(states=X.tolist(), tensions=U.tolist(), result=result.model_dump(mode='json'), prediction_timing=prediction_timing, decision_state_scales=self.state_scales.tolist(), diagnostics=self.solver.last_diagnostics, total_s=total, graph_s=self.graph_s, recovery=recovery, warm_start=dict(executed_intervals=int(source is not None and warm is None), root_settings=dict(abstol=self.parameters.root_tolerance, max_iterations=30, error_on_fail=True), preparation_s=preparation_s, regenerated_all_states=self.parameters.regenerate_warm_states, seed_settled=seed_settled, tail_initialization=tails), nominal_operating_state=self.nominal_x, measured_initial_state=list(measured_x), previous_tensions_n=list(previous_u), period_s=self.period, substeps=self.parameters.substeps, integration=self.parameters.integration_method, stopping_policy=self.parameters.stopping_policy, cost='Stage weights per second on squared tip/position scale, curvature rate/(1 rad/(m*s)), tension/(1 N) and delta tension/(1 N); terminal weights on squared tip/position scale, curvature rate and world tip speed/speed scale. Optional holding speed cost starts at max(0, task duration minus settling window minus holding_brake_lead_s), using absolute prediction-node times. Acceptance timing is unchanged. Position scale defaults to task tolerance. Smoothing is a design penalty.', cost_scales=dict(position_m=self.parameters.position_error_scale_m or self.goal_tolerance, tip_speed_m_s=self.parameters.tip_speed_scale_m_s))
        accepted = result.status in ('converged', 'iteration_limit', 'feasible_early_stop') and result.constraint_violation <= 1e-05
        output['accepted'] = accepted
        output['optimization_converged'] = result.status == 'converged'
        if self.parameters.recover_returned_tensions:

            def terminal_motion(values):
                state = np.array([values[f'x/{steps}/{j}'] for j in range(2 * self.n)]) * self.state_scales
                tip, speed = self._motion(state[:self.n], state[self.n:])
                return dict(error_m=float(np.linalg.norm(np.asarray(tip).ravel() - self.target)), speed_m_s=float(np.linalg.norm(np.asarray(speed))), velocity_error_m_s=None)
            output['feedback'] = dict(initial_objective=self.solver.last_diagnostics['initial_objective'], delivered_objective=result.objective_value, first_command_change_from_initialization_n=float(max((abs(values[f'u/0/{t}'] - self.problem.initial_guess[f'u/0/{t}']) for t in self.tendons))), initial_terminal=terminal_motion(self.problem.initial_guess), delivered_terminal=terminal_motion(values))
        if result.status in ('converged', 'iteration_limit', 'feasible_early_stop'):
            self.last = output
        output['update_wall_s'] = time.perf_counter() - update_start
        if recording is not None:
            output['recording'] = recording
        if getattr(self.solver, 'complete_record', False):
            from copy import deepcopy
            complete_capture_start = time.perf_counter()
            output['complete_update'] = dict(warm=recording, resolved_problem=self.problem.model_dump(mode='json'), nominal_workspace=dict(x=self.nominal_x, u=self.nominal_u), diagnostic_trace_enabled=self.solver.diagnostic_trace, initialization=deepcopy(self.solver.last_input_record), problem_variables=deepcopy(self.problem.variables), initial_guess=deepcopy(self.problem.initial_guess), raw_returned_plan=deepcopy(self.solver.last_returned_optimum), selected_feasible_plan=selected_before_recovery, recovery_candidate=deepcopy(recovery.get('candidate_optimum')), delivered_plan=dict(result.optimum), measured_state=list(measured_x), previous_applied_input_n=list(previous_u), state_scales=self.state_scales.tolist(), tendon_order=list(self.tendons), effective_horizon=self.parameters.horizon, prediction_timing=prediction_timing, mutable_workspace=dict(last_plan_source='explicit' if warm is not None else 'workspace_last', cached_solver=self.solver.last_diagnostics['cached_solver'], tail_solver_ready=self._tail_solver is not None), initialization_provenance='execution-local initial_state_pretension then shifted delivered plan; regenerate from measured state', warm_preparation=deepcopy(output['warm_start']), robot_identity=digest(self.robot.model_dump(mode='json')), model_binding=self.problem.model_reference.model_dump(mode='json'), model_identity=digest(self.problem.objective_function.model_dump(mode='json')), controller_identity=digest(self.parameters.model_dump(mode='json')), solver_identity=digest(self.solver.last_input_record['solver_options']), initialization_identity=digest(dict(warm=recording, initialization=self.solver.last_input_record)), diagnostics=deepcopy(self.solver.last_diagnostics), recovery=deepcopy(recovery))
            output['complete_update']['record_capture_s'] = time.perf_counter() - complete_capture_start
        return output

    def regenerate_tensions(self, raw, measured_x, *, deadline=None):
        """Reuse the live implicit root solve; never launch an NLP or reuse defects."""
        start = time.perf_counter()
        repaired = dict(raw)
        state = np.asarray(measured_x)
        steps = []
        error = None
        for j, v in enumerate(state):
            repaired[f'x/0/{j}'] = float(v / self.state_scales[j])
        try:
            for k in range(1, self.parameters.horizon * self.parameters.substeps + 1):
                if deadline is not None and time.perf_counter() >= deadline:
                    raise RuntimeError('REGENERATION_TIME_ALLOWANCE')
                u = np.array([raw[f'u/{(k - 1) // self.parameters.substeps}/{t}'] for t in self.tendons])
                guess = np.array([raw[f'x/{k}/{j}'] for j in range(2 * self.n)]) * self.state_scales
                state, diagnostic = self._extend_tail(state, u, guess)
                steps.append(dict(node=k, **diagnostic))
                for j, v in enumerate(state):
                    repaired[f'x/{k}/{j}'] = float(v / self.state_scales[j])
        except RuntimeError as exc:
            error = str(exc)
        return dict(optimum=repaired if error is None else None, partial_states=[[repaired[f'x/{k}/{j}'] * self.state_scales[j] for j in range(2 * self.n)] for k in range(len(steps) + 1)], steps=steps, error=error, integration_s=time.perf_counter() - start)

    def _recover_returned(self, result, measured_x):
        """One feasibility recovery, with unchanged objective and constraints.

        IPOPT can lower tracking cost before its shooting defects meet delivery
        tolerance. Reintegrate that returned control once; never force selection
        or discard the already verified feasible candidate on a failed recovery.
        """
        start = time.perf_counter()
        d = self.solver.last_diagnostics
        recovery = dict(enabled=True, attempted=False, selected=False, wall_s=0.0, source='returned_ipopt_tensions_reintegrated_from_current_measurement', parent_iteration=result.iterations, selected_before_objective=result.objective_value, initial_objective=d['initial_objective'], error=None)
        raw = self.solver.last_returned_optimum
        if raw is None or d['returned_iterate_objective'] >= result.objective_value:
            return (result, recovery)
        recovery['attempted'] = True
        try:
            regenerated = self.regenerate_tensions(raw, measured_x)
            recovery.update({k: v for k, v in regenerated.items() if k not in ('optimum', 'partial_states', 'steps')})
            if self.solver.diagnostic_trace or getattr(self.solver, 'complete_record', False):
                recovery['partial_regenerated_states'] = regenerated['partial_states']
                recovery['root_trace'] = regenerated['steps']
            recovery['root_solve_attempts'] = len(regenerated['steps']) + int(regenerated['error'] is not None)
            if regenerated['error']:
                raise RuntimeError(regenerated['error'])
            repaired = regenerated['optimum']
            validation_start = time.perf_counter()
            check = self.solver.evaluate_candidate(self.problem, repaired)
            recovery.update({k: v for k, v in check.items() if k != 'constraint_values'}, validation_s=time.perf_counter() - validation_start)
            if self.solver.diagnostic_trace or getattr(self.solver, 'complete_record', False):
                recovery['candidate_optimum'] = repaired
            if check['feasible'] and check['objective'] < result.objective_value:
                recovery['selected'] = True
                recovery['first_command_change_n'] = float(max((abs(repaired[f'u/0/{t}'] - result.optimum[f'u/0/{t}']) for t in self.tendons)))
                result = result.model_copy(update=dict(optimum=repaired, objective_value=check['objective'], constraint_violation=check['scaled_violation']))
        except RuntimeError as exc:
            recovery['error'] = str(exc)
        recovery['wall_s'] = time.perf_counter() - start
        return (result, recovery)
