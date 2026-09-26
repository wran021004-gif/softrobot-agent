"""Generic CasADi expression transport and IPOPT Solver implementation."""
from __future__ import annotations

import hashlib
import math
import time

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
from schemas.platform import Binding, EvidenceRef, Payload
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

    def reset(self,lbx,ubx,lbg,ubg,start,policy=None,seed_objective=None,seed_settled=False):
        self.bounds=(lbx,ubx,lbg,ubg);self.best=None;self.first=None;self.latest=None
        self.iteration=-1;self.start=start
        self.policy=policy;self.seed_objective=seed_objective;self.seed_settled=seed_settled
        self.stop_reason=None;self.stop_s=None

    def eval(self,args):
        elapsed=time.perf_counter()-self.start
        self.iteration+=1;items=dict(zip(self.names,args))
        x=np.asarray(items['x']).ravel();g=np.asarray(items['g']).ravel();objective=float(items['f'])
        violation=_violation(x,g,*self.bounds)
        self.latest=None
        if np.isfinite(np.r_[x,g,objective]).all() and violation<=1e-5:
            candidate=dict(x=x.copy(),objective=objective,iteration=self.iteration,
                elapsed_s=elapsed,scaled_violation=violation,
                iteration_zero=self.iteration==0)
            self.latest=candidate
            if self.first is None:self.first=candidate
            if self.best is None or objective<self.best['objective'] or (self.best.get('initialization_only') and objective==self.best['objective']):
                self.best=candidate
        if self.policy is not None and self.best is not None:
            base=self.seed_objective
            improvement=(base-self.best['objective'])/max(abs(base),1e-12) if base is not None else None
            if self.seed_settled and base is not None and self.best['objective']<=base+1e-12:
                self.stop_reason='verified_settled_seed'
            elif elapsed>=self.policy.minimum_s and improvement is not None and improvement>=self.policy.relative_improvement:
                self.stop_reason='relative_seed_improvement'
            elif elapsed>=self.policy.budget_s and (base is None or self.best['objective']<=base+1e-12):
                self.stop_reason='budget_best_feasible'
            if self.stop_reason is not None:
                self.stop_s=elapsed
                return [1]
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

    def solve(self, problem: OptimizationProblem, *, seed_settled=False) -> OptimizationResult:
        self.last_diagnostics=None
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
        cache_key=(bundle.expression_digest,bundle.serialized_function,problem.objective.direction,
                   self.parameters.constraint_jacobian_mode)
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
            if self.parameters.constraint_jacobian_mode == 'reverse':
                # Keep exact AD, but color the constraint Jacobian in reverse
                # mode instead of propagating wide forward seed batches.
                constraints = ca.Function('constraint_values', [x],
                    [constraint_expression], {'ad_weight':1.})
                jacobian = constraints.jacobian()(x, ca.DM.zeros(constraint_expression.numel()))
                p = ca.MX.sym('p', 0)
                options['jac_g'] = ca.Function('nlp_jac_g', [x,p],
                    [constraint_expression, jacobian])
                # OptimizationResult does not request solution sensitivities.
                options['no_nlp_grad'] = True
                options['calc_lam_p'] = False
            selector=_FeasibleIterate(len(bundle.variable_order),len(problem.constraints)) if self.parameters.retain_feasible_iterate or self.parameters.feasible_return is not None else None
            if selector is not None:options['iteration_callback']=selector
            solver = ca.nlpsol('ipopt_solver', 'ipopt', nlp, options)
            self._compiled[cache_key]=(function,solver,selector)
        function,solver,selector=self._compiled[cache_key]
        construction_s=time.perf_counter()-construction_start
        if self.parameters.print_level:print('IPOPT solver ready',construction_s,'cached',cached,flush=True)
        lbx, ubx, x0 = self._bounds(problem, bundle.variable_order)
        lbg = [-math.inf if item.lower is None else item.lower for item in problem.constraints]
        ubg = [math.inf if item.upper is None else item.upper for item in problem.constraints]
        initial_check_start=time.perf_counter()
        initial_check=function(x=x0)
        initial_violation=_violation(np.asarray(x0),np.asarray(initial_check['constraints']).ravel(),lbx,ubx,lbg,ubg)
        initial_check_s=time.perf_counter()-initial_check_start
        solve_start=time.perf_counter()
        initial_finite=np.isfinite(np.r_[x0,np.asarray(initial_check['constraints']).ravel(),float(initial_check['objective'])]).all()
        seed_objective=float(initial_check['objective']) if initial_finite and initial_violation<=1e-5 else None
        if seed_objective is not None and problem.objective.direction!='minimize':seed_objective=-seed_objective
        if selector is not None:selector.reset(lbx,ubx,lbg,ubg,solve_start,self.parameters.feasible_return,seed_objective,seed_settled)
        if selector is not None and seed_objective is not None and self.parameters.feasible_return is not None:
            selector.best=dict(x=np.asarray(x0),objective=seed_objective,iteration=-1,
                elapsed_s=0.,scaled_violation=initial_violation,iteration_zero=False,
                initialization_only=True)
        solution = solver(x0=x0, lbx=lbx, ubx=ubx, lbg=lbg, ubg=ubg)
        solve_s=time.perf_counter()-solve_start
        stats = solver.stats()
        validation_start=time.perf_counter()
        values = np.asarray(solution['x'], dtype=float).reshape(-1)
        returned_values=values.copy();selected_iteration=None;selected_candidate=None
        if not stats.get('success') and selector is not None and selector.best is not None:
            values=selector.best['x'];selected_iteration=selector.best['iteration']
            selected_candidate=selector.best
        elif selector is not None and selector.latest is not None and np.array_equal(values,selector.latest['x']):
            selected_candidate=selector.latest
            selected_iteration=selected_candidate['iteration']
        # At most one model evaluation per distinct first/selected/raw vector.
        verified={}
        def verify(vector):
            key=np.asarray(vector,dtype=float).tobytes()
            if key not in verified:
                check=function(x=vector)
                g=np.asarray(check['constraints'],dtype=float).ravel()
                verified[key]=(float(check['objective']),g,_violation(vector,g,lbx,ubx,lbg,ubg))
            return verified[key]
        raw_value,constraint_values,violation=verify(values)
        returned_objective,returned_g,returned_violation=verify(returned_values)
        def candidate_record(candidate):
            if candidate is None:return None
            objective,g,error=verify(candidate['x'])
            return {**candidate,'x':candidate['x'].tolist(),
                'objective':candidate['objective'] if problem.objective.direction=='minimize' else -candidate['objective'],
                'independent_objective':objective,'independent_scaled_violation':error,
                'independently_feasible':bool(error<=1e-5 and np.isfinite(np.r_[candidate['x'],g,objective]).all())}
        first_record=candidate_record(None if selector is None else selector.first)
        selected_record=candidate_record(selected_candidate)
        if not np.isfinite(np.r_[values,constraint_values,raw_value,returned_values,returned_g]).all():
            raise ValueError('IPOPT_NONFINITE_SOLUTION')
        return_status = str(stats.get('return_status', ''))
        if bool(stats.get('success')):
            status = 'converged'
        elif selector is not None and selector.stop_reason is not None and violation<=1e-5:
            status = 'feasible_early_stop'
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
            'first_feasible_candidate':first_record,
            'selected_feasible_candidate':selected_record,
            'candidate_timer_origin':'perf_counter immediately before numerical solver call; callback entry timestamps; iteration zero is the initial iterate, not convergence',
            'initial_scaled_violation':initial_violation,
            'initial_objective':float(initial_check['objective']),
            'policy_stop_reason':None if selector is None else selector.stop_reason,
            'policy_stop_s':None if selector is None else selector.stop_s,
            'initial_check_s':initial_check_s,
            'returned_iterate_constraint_violation':returned_violation,
            'returned_iterate_objective':returned_objective,
            'validation_s':time.perf_counter()-validation_start,
            'function_statistics':{k:v for k,v in stats.items()
                if k.startswith(('n_call_', 't_proc_', 't_wall_'))},
            'constraint_derivative':'CasADi exact AD ('+self.parameters.constraint_jacobian_mode+')',
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
    context = args.context
    if isinstance(context, EvidenceRef):
        context = SystemContext.model_validate(ctx.artifact(context))
    if context is None:
        # Static assemblers do not need state/input vectors. Dynamic assemblers
        # must reject these empty vectors, never infer an initial condition.
        context = SystemContext(x0=[], u0=[])
    scene = context.scene
    if isinstance(scene, EvidenceRef):
        scene = Payload.model_validate(ctx.artifact(scene))
    if scene is not None and scene != ctx.input.task.environment:
        raise ValueError('OPTIMIZATION_CONTEXT_SCENE_MUST_MATCH_TASK')
    context = context.model_copy(update={'scene': ctx.input.task.environment})
    problem = assemble_optimization(
        ctx.reg, args.assembler,
        task=ctx.input.task,
        robot=ctx.input.robot,
        space=space,
        mathematical_model=model_contract,
        specification=args.specification,
        context=context,
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
