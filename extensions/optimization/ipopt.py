"""Generic CasADi expression transport and IPOPT Solver implementation."""
from __future__ import annotations

import hashlib
import math

import casadi as ca
import numpy as np

from extensions.optimization.contracts import (
    CasadiNLPExpression,
    CasadiNLPSelector,
    IpoptParameters,
    OptimizationAssemblyResult,
    OptimizationDescription,
    OptimizationTemplateDescription,
)
from schemas.platform import Binding, Payload
from schemas.platform_math import OptimizationProblem, OptimizationResult


BUNDLE_CONTRACT = 'optimization.casadi_nlp_expression'
SELECTOR_CONTRACT = 'optimization.casadi_nlp_selector'
_EXPRESSION_FUNCTIONS = {}


def _violation(x,g,lbx,ubx,lbg,ubg):
    return float(max(np.max(np.maximum(np.asarray(lbx)-x,x-np.asarray(ubx)),initial=0.),
        np.max(np.maximum(np.asarray(lbg)-g,g-np.asarray(ubg)),initial=0.)))


class _FeasibleIterate(ca.Callback):
    """Retain an iterate of this solve, never a plan from another initial state."""
    def __init__(self,nx,ng):
        ca.Callback.__init__(self);self.nx=nx;self.ng=ng
        self.names=ca.nlpsol_out();self.construct('retain_feasible_iterate')

    def get_n_in(self):return ca.nlpsol_n_out()
    def get_n_out(self):return 1
    def get_name_in(self,i):return self.names[i]
    def get_name_out(self,i):return 'stop'
    def get_sparsity_in(self,i):
        name=self.names[i]
        return ca.Sparsity.dense(self.nx if name in ('x','lam_x') else self.ng if name in ('g','lam_g') else 1 if name=='f' else 0,1)

    def reset(self,lbx,ubx,lbg,ubg):
        self.bounds=(lbx,ubx,lbg,ubg);self.best=None;self.iteration=-1

    def eval(self,args):
        self.iteration+=1;items=dict(zip(self.names,args))
        x=np.asarray(items['x']).ravel();g=np.asarray(items['g']).ravel();objective=float(items['f'])
        if np.isfinite(np.r_[x,g,objective]).all() and _violation(x,g,*self.bounds)<=1e-5:
            if self.best is None or objective<self.best['objective']:
                self.best=dict(x=x.copy(),objective=objective,iteration=self.iteration)
        return [0]


def expression_payload(variable_order, objective, constraints):
    """Serialize trusted MX expressions into the one format understood by IPOPT."""
    variable_order = list(variable_order)
    constraint_names = list(constraints)
    x = ca.vertcat(*[objective['variables'][name] for name in variable_order])
    g = ca.vertcat(*constraints.values()) if constraints else ca.MX.zeros(0, 1)
    function = ca.Function(
        'trusted_nlp_expression', [x], [objective['expression'], g],
        ['x'], ['objective', 'constraints'],
    )
    serialized = function.serialize()
    digest = hashlib.sha256(serialized.encode('utf8')).hexdigest()
    # In-process trusted assembly can share the already-built graph. Keep the
    # transport string too, so a claimed digest alone never selects other code.
    _EXPRESSION_FUNCTIONS[digest]=(serialized,function)
    if len(_EXPRESSION_FUNCTIONS)>4:
        del _EXPRESSION_FUNCTIONS[next(iter(_EXPRESSION_FUNCTIONS))]
    bundle = CasadiNLPExpression(
        variable_order=variable_order,
        constraint_order=constraint_names,
        serialized_function=serialized,
        expression_digest=digest,
    )
    selectors = [
        Payload(
            contract=SELECTOR_CONTRACT,
            data=CasadiNLPSelector(
                expression_digest=digest,
                constraint_name=name,
                constraint_index=index,
            ).model_dump(mode='json'),
        )
        for index, name in enumerate(constraint_names)
    ]
    return Payload(contract=BUNDLE_CONTRACT, data=bundle.model_dump(mode='json')), selectors


class IpoptSolver:
    """Solver for explicit differentiable NLPs; contains no robot semantics."""

    def __init__(self, parameters=None):
        self.parameters = IpoptParameters.model_validate(parameters or {})
        self.last_diagnostics = None
        self._compiled = {}

    @staticmethod
    def _bounds(problem, order):
        lower, upper, initial = [], [], []
        for name in order:
            spec = problem.variables[name]
            if spec.get('type') != 'number':
                raise ValueError('IPOPT_REQUIRES_CONTINUOUS_NUMBER_VARIABLE: ' + name)
            bounds = spec.get('bounds', [None, None])
            if len(bounds) != 2:
                raise ValueError('IPOPT_VARIABLE_BOUNDS_REQUIRE_TWO_VALUES: ' + name)
            lo = -math.inf if bounds[0] is None else float(bounds[0])
            hi = math.inf if bounds[1] is None else float(bounds[1])
            if lo > hi:
                raise ValueError('IPOPT_VARIABLE_BOUNDS_REVERSED: ' + name)
            value = float(problem.initial_guess.get(name, 0.0))
            lower.append(lo)
            upper.append(hi)
            initial.append(min(max(value, lo), hi))
        return lower, upper, initial

    def solve(self, problem: OptimizationProblem) -> OptimizationResult:
        problem = OptimizationProblem.model_validate(problem)
        payload = problem.objective_function
        if not isinstance(payload, Payload) or payload.contract != BUNDLE_CONTRACT:
            raise ValueError('IPOPT_REQUIRES_CASADI_NLP_EXPRESSION')
        bundle = CasadiNLPExpression.model_validate(payload.data)
        if set(bundle.variable_order) != set(problem.variables) or len(bundle.variable_order) != len(problem.variables):
            raise ValueError('IPOPT_EXPRESSION_VARIABLE_MISMATCH')
        if len(bundle.constraint_order) != len(problem.constraints):
            raise ValueError('IPOPT_EXPRESSION_CONSTRAINT_MISMATCH')
        for index, constraint in enumerate(problem.constraints):
            selector_payload = constraint.expression
            if not isinstance(selector_payload, Payload) or selector_payload.contract != SELECTOR_CONTRACT:
                raise ValueError('IPOPT_REQUIRES_CASADI_NLP_SELECTOR')
            selector = CasadiNLPSelector.model_validate(selector_payload.data)
            if (
                selector.expression_digest != bundle.expression_digest
                or selector.constraint_index != index
                or selector.constraint_name != constraint.name
                or bundle.constraint_order[index] != constraint.name
            ):
                raise ValueError('IPOPT_CONSTRAINT_SELECTOR_MISMATCH')

        import time
        construction_start = time.perf_counter()
        options = {
            'ipopt.print_level': self.parameters.print_level,
            'ipopt.max_iter': self.parameters.max_iterations,
            'ipopt.tol': float(self.parameters.tolerance),
            'ipopt.acceptable_tol': float(self.parameters.acceptable_tolerance),
            'ipopt.hessian_approximation': self.parameters.hessian_approximation,
            'print_time': False,
        }
        if self.parameters.max_cpu_s is not None:
            options['ipopt.max_cpu_time']=float(self.parameters.max_cpu_s)
        cache_key=(bundle.expression_digest,bundle.serialized_function,problem.objective.direction)
        cached=cache_key in self._compiled
        if not cached:
            if self.parameters.print_level:print('IPOPT constructing solver',flush=True)
            shared=_EXPRESSION_FUNCTIONS.get(bundle.expression_digest)
            function=(shared[1] if shared is not None and shared[0]==bundle.serialized_function
                      else ca.Function.deserialize(bundle.serialized_function))
            x = ca.MX.sym('x', len(bundle.variable_order))
            # Inline only the transport wrapper. Otherwise the objective-only
            # adjoint also evaluates the expensive constraint graph with zero
            # seeds. Inner model functions retain their own AD boundaries.
            raw_objective, constraint_expression = function.call([x],True,False)
            signed_objective = raw_objective if problem.objective.direction == 'minimize' else -raw_objective
            nlp = {'x': x, 'f': signed_objective, 'g': constraint_expression}
            selector=_FeasibleIterate(len(bundle.variable_order),len(problem.constraints)) if self.parameters.retain_feasible_iterate else None
            if selector is not None:options['iteration_callback']=selector
            solver = ca.nlpsol('ipopt_solver', 'ipopt', nlp, options)
            self._compiled[cache_key]=(function,solver,selector)
        function,solver,selector=self._compiled[cache_key]
        construction_s=time.perf_counter()-construction_start
        if self.parameters.print_level:print('IPOPT solver ready',construction_s,'cached',cached,flush=True)
        lbx, ubx, x0 = self._bounds(problem, bundle.variable_order)
        lbg = [-math.inf if item.lower is None else item.lower for item in problem.constraints]
        ubg = [math.inf if item.upper is None else item.upper for item in problem.constraints]
        if selector is not None:selector.reset(lbx,ubx,lbg,ubg)
        solve_start=time.perf_counter()
        solution = solver(x0=x0, lbx=lbx, ubx=ubx, lbg=lbg, ubg=ubg)
        solve_s=time.perf_counter()-solve_start
        stats = solver.stats()
        values = np.asarray(solution['x'], dtype=float).reshape(-1)
        returned_values=values.copy();selected_iteration=None
        if not stats.get('success') and selector is not None and selector.best is not None:
            values=selector.best['x'];selected_iteration=selector.best['iteration']
        independent=function(x=values)
        constraint_values = np.asarray(independent['constraints'], dtype=float).reshape(-1)
        raw_value = float(independent['objective'])
        violation=_violation(values,constraint_values,lbx,ubx,lbg,ubg)
        returned_g=constraint_values if np.array_equal(values,returned_values) else np.asarray(function(x=returned_values)['constraints']).ravel()
        returned_violation=_violation(returned_values,returned_g,lbx,ubx,lbg,ubg)
        if not np.isfinite(np.r_[values,constraint_values,raw_value,returned_values,returned_g]).all():
            raise ValueError('IPOPT_NONFINITE_SOLUTION')
        return_status = str(stats.get('return_status', ''))
        if bool(stats.get('success')):
            status = 'converged'
        elif return_status in ('Maximum_Iterations_Exceeded', 'Maximum_CpuTime_Exceeded'):
            status = 'iteration_limit'
        elif 'Infeasible' in return_status:
            status = 'infeasible'
        elif 'Unbounded' in return_status or 'Diverging_Iterates' in return_status:
            status = 'unbounded'
        else:
            status = 'failed'
        self.last_diagnostics = {
            'solver': 'solver.ipopt',
            'return_status': return_status,
            'success': bool(stats.get('success')),
            'iterations': int(stats.get('iter_count', 0)),
            'variable_order': bundle.variable_order,
            'constraint_order': bundle.constraint_order,
            'constraint_values': constraint_values.tolist(),
            'constraint_lower': lbg,
            'constraint_upper': ubg,
            'options': self.parameters.model_dump(mode='json'),
            'construction_s':construction_s, 'solve_s':solve_s, 'cached_solver':cached,
            'selected_feasible_iteration':selected_iteration,
            'returned_iterate_constraint_violation':returned_violation,
        }
        return OptimizationResult(
            status=status,
            optimum=dict(zip(bundle.variable_order, values.tolist())),
            objective_value=raw_value,
            constraint_violation=float(violation),
            iterations=int(stats.get('iter_count', 0)),
        )


def optimization_describe_tool(ctx, args):
    return OptimizationDescription(templates=[
        OptimizationTemplateDescription(
            template_id='pcc_reach',
            assembler_id='optimization_assembler.pcc_reach',
            objective_templates=['tip_position_error_squared'],
            constraint_templates=['authorized_design_bounds'],
            variables='one authorized family.design flexible-segment length path',
            target_source='frozen Task goal target_m; transformed by the frozen mount',
            assembler_parameters=(
                'family.pcc_reach_assembler_parameters: configuration.segments.<segment>.'
                '{curvature_y_rad_m,curvature_z_rad_m}; no target coordinates'
            ),
        ),
        OptimizationTemplateDescription(
            template_id='inverse_shape',
            assembler_id='optimization_assembler.gvs_inverse',
            objective_templates=['inverse_shape_static'],
            constraint_templates=['tendon_force_bounds'],
            variables='all robot-derived tendon_tensions_n/<tendon> variables',
            target_source='q_target in registered assembler parameters',
            assembler_parameters=(
                'family.gvs_inverse_assembler_parameters@2.0.0: template=inverse_shape, '
                'explicit basis.strategy and ordered q_target; '
                'no tendon order or force limits'
            ),
        ),
        OptimizationTemplateDescription(
            template_id='inverse_tip_static',
            assembler_id='optimization_assembler.gvs_inverse',
            objective_templates=['tip_position_error_squared', 'tendon_effort'],
            constraint_templates=['static_equilibrium', 'tendon_force_bounds'],
            variables='all q/<coordinate> and robot-derived tendon_tensions_n/<tendon> variables',
            target_source='frozen Task goal target_m; assembler parameters cannot override it',
            assembler_parameters=(
                'family.gvs_inverse_assembler_parameters@2.0.0: template=inverse_tip_static, '
                'explicit basis.strategy; q_target forbidden'
            ),
        ),
    ])


def _base_space(ctx):
    candidate = ctx.input.policy.candidate_builder
    parsed = ctx.reg.parse(candidate.parameters)
    if candidate.extension_id != 'candidate.family' or not hasattr(parsed, 'parameters'):
        return {}
    result = dict(parsed.parameters)
    result.update(parsed.control_parameters)
    result.update(parsed.model_parameters)
    result.update(parsed.discretization_parameters)
    return result


def optimization_assemble_tool(ctx, args):
    from schemas.platform_math import SystemContext
    from tools.platform_optimization import assemble_optimization

    definition, parameters = ctx.reg.bind(args.assembler, 'optimization_assembler')
    model_id = definition.capabilities['model']
    model_definition = ctx.reg.get(model_id, definition.capabilities.get('model_version', '1.0.0'), 'dynamics_model')
    from schemas.platform_math import MathematicalModel
    model_contract = MathematicalModel.model_validate(
        model_definition.capabilities['mathematical_model']
    )
    space = _base_space(ctx)
    authorization = definition.hook('authorization')
    if authorization is not None:
        space = authorization(ctx.input.robot, space, parameters)
    problem = assemble_optimization(
        ctx.reg, args.assembler,
        task=ctx.input.task,
        robot=ctx.input.robot,
        space=space,
        mathematical_model=model_contract,
        specification=args.specification,
        context=SystemContext(x0=[], u0=[], scene=ctx.input.task.environment),
    )
    reference = ctx.save_artifact(problem, 'optimization_problem')
    return OptimizationAssemblyResult(
        problem=reference,
        assembler_id=definition.extension_id,
        objective_metric=problem.objective.metric,
        variables=list(problem.variables),
        constraint_count=len(problem.constraints),
        target_source=definition.capabilities['target_source'],
    )


def optimization_solve_tool(ctx, args):
    problem_reference = args.problem
    problem = OptimizationProblem.model_validate(ctx.artifact(problem_reference))
    definition, parameters = ctx.reg.bind(Binding(
        extension_id=args.solver,
        parameters=Payload(
            contract='optimization.ipopt_parameters',
            data=args.options.model_dump(mode='json'),
        ),
    ), 'solver')
    solver = definition.resolve()(parameters)
    result = solver.solve(problem)
    diagnostic_reference = ctx.save_artifact(solver.last_diagnostics, 'optimization_solver_diagnostics')
    return result.model_copy(update={
        'problem_reference': problem_reference,
        'solver_evidence': diagnostic_reference,
        'evidence': [diagnostic_reference],
    })
