"""Offline SOCP/LP comparison for the existing sampled signed minimax problem.

No registration or physical acceptance. Floating-point checks are not certificates.
CVXPY is optional and imported only by this entry point.
"""
import hashlib
import json
import time
from importlib.metadata import version
from numbers import Real

import numpy as np

from extensions.math_analysis.task_capability import normalization
from extensions.math_analysis.trajectory import prepare_conic_trajectory, verify_witness


METHOD = 'sampled-affine-conic-minimax-v1'
PATH_METHOD = 'sampled-affine-conic-path-progress-v1'
DEFAULT_OPTIONS = dict(max_iter=200, tol_gap_abs=1e-9, tol_gap_rel=1e-9, tol_feas=1e-9)


def _plain(value):
    if hasattr(value, 'model_dump'):
        return value.model_dump(mode='json')
    if hasattr(value, '__dict__'):
        return {k: _plain(v) for k, v in vars(value).items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


def _identity(value):
    return hashlib.sha256(json.dumps(_plain(value), sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def _maxabs(value):
    return float(np.max(np.abs(value), initial=0.))


def _blocks(cp, rows, scales, z, t):
    """Explicit normalized cones keep public dual variables tied to task rows."""
    blocks = []
    for row_index, ((c, index, k, ref, _, base, matrix), scale) in enumerate(zip(rows, scales)):
        b, M = (base-ref)/scale, matrix/scale
        if not all(np.all(np.isfinite(v)) for v in (b, M)):
            raise ValueError('NONFINITE_NORMALIZED_CONSTRAINT')
        residual = b + M@z if z is not None else cp.Constant(b)
        identity = dict(row_index=row_index, constraint_id=c.constraint_id, sample_index=index,
                        control_step=k, normalization_scale=scale, provenance=c.provenance,
                        signal=_plain(c.signal))
        if c.kind == 'norm_bound':
            blocks.append(dict(**identity, kind='soc', M=M, b=b,
                               constraint=cp.SOC(t+1, residual)))
        else:
            for side, sign, bound in (('lower', -1., -np.asarray(c.lower)/scale),
                                      ('upper', 1., np.asarray(c.upper)/scale)):
                for j in range(len(b)):
                    a, offset = sign*M[j], sign*b[j]-bound[j]
                    expression = a@z+offset if z is not None else offset
                    blocks.append(dict(**identity, kind='linear', side=side, component=j,
                                       M=a, b=offset, constraint=expression <= t))
    return blocks


def _dual_checks(blocks, box, z, t, lower, upper, tolerance, hard=None, hard_matrix=None, hard_upper=None):
    """Recompute unscaled task/box KKT and a repaired box-support lower estimate.

    SOC dual (alpha,v) contributes -alpha*(t+1)-v@(M*z+b).
    Thus lambda=alpha and signed norm direction=-v/alpha. Linear lambda is
    already in original signed coordinates. No division by a residual norm.
    """
    gradient = np.zeros_like(z); constant = 0.; mass = 0.
    support_gradient = np.zeros_like(z); support_constant = 0.; support_mass = 0.
    cone_error = 0.; complementarity = []; records = []
    for block in blocks:
        con = block['constraint']; M, b = block['M'], block['b']
        record = {k: v for k, v in block.items() if k not in ('constraint', 'M', 'b')}
        if con.dual_value is None:
            raise ValueError('DUAL_VARIABLE_UNAVAILABLE')
        if block['kind'] == 'soc':
            alpha = float(np.asarray(con.dual_value[0]).item())
            v = np.asarray(con.dual_value[1], dtype=float).ravel()
            if not np.isfinite(alpha) or not np.all(np.isfinite(v)):
                raise ValueError('NONFINITE_DUAL_VARIABLE')
            cone_error = max(cone_error, float(np.linalg.norm(v))-alpha, -alpha)
            gradient -= M.T@v; constant += -alpha-float(v@b); mass += alpha
            comp = alpha*(t+1)+float(v@(M@z+b))
            signed = float(np.linalg.norm(M@z+b))-1
            weight = max(0., alpha)
            direction = -v/max(weight, float(np.linalg.norm(v)), np.finfo(float).tiny)
            support_gradient += weight*(M.T@direction)
            support_constant += weight*(float(direction@b)-1)
            record.update(soc_scalar=alpha, soc_vector=v.tolist(), signed_multiplier=alpha,
                          support_direction=direction.tolist())
        else:
            alpha = float(np.asarray(con.dual_value).item())
            if not np.isfinite(alpha):
                raise ValueError('NONFINITE_DUAL_VARIABLE')
            cone_error = max(cone_error, -alpha)
            gradient += alpha*M; constant += alpha*b; mass += alpha
            signed = float(M@z+b); comp = alpha*(t-signed)
            weight = max(0., alpha)
            support_gradient += weight*M; support_constant += weight*b
            record.update(signed_multiplier=alpha)
        support_mass += weight
        record.update(signed_value=signed, epigraph_slack=t-signed,
                      epigraph_active=bool(abs(t-signed) <= tolerance*(1+abs(t))),
                      task_boundary_active=bool(abs(signed) <= tolerance),
                      complementarity=comp, support_weight_before_normalization=weight,
                      physical_excess_multiplier=alpha/block['normalization_scale'])
        complementarity.append(comp); records.append(record)
    if len(z):
        if any(c.dual_value is None for c in box):
            raise ValueError('BOX_DUAL_UNAVAILABLE')
        mu_lower, mu_upper = [np.asarray(c.dual_value, dtype=float).ravel() for c in box]
    else:
        mu_lower = mu_upper = np.zeros(0)
    if not all(np.all(np.isfinite(v)) for v in (mu_lower, mu_upper)):
        raise ValueError('NONFINITE_BOX_DUAL')
    cone_error = max(cone_error, float(np.max(-mu_lower, initial=0.)),
                     float(np.max(-mu_upper, initial=0.)))
    hard_mu=np.zeros(0)
    if hard is not None:
        hard_mu=np.asarray(hard.dual_value,dtype=float).ravel()
        if not np.isfinite(hard_mu).all():raise ValueError('NONFINITE_PROGRESS_DUAL')
        cone_error=max(cone_error,float(np.max(-hard_mu,initial=0.)))
        gradient+=hard_matrix.T@hard_mu;constant-=float(hard_upper@hard_mu)
        support_gradient+=hard_matrix.T@np.maximum(0.,hard_mu)
        support_constant-=float(hard_upper@np.maximum(0.,hard_mu))
        complementarity.extend((hard_mu*(hard_upper-hard_matrix@z)).tolist())
    stationarity = gradient-mu_lower+mu_upper
    raw_objective = float(constant+mu_lower@lower-mu_upper@upper)
    complementarity.extend((mu_lower*(z-lower)).tolist()+(mu_upper*(upper-z)).tolist())
    if not np.isfinite(support_mass) or support_mass <= 0:
        raise ValueError('NO_POSITIVE_TASK_DUAL_MASS')
    support_gradient /= support_mass; support_constant /= support_mass
    support_value = float(support_constant+np.minimum(support_gradient*lower, support_gradient*upper).sum())
    for record in records:
        record['support_weight'] = record['support_weight_before_normalization']/support_mass
    checks = dict(source='independent_from_public_primal_and_dual_variables',
        stationarity_inf=_maxabs(stationarity), epigraph_stationarity_abs=abs(1-mass),
        dual_cone_violation=max(0., cone_error), complementarity_abs=_maxabs(complementarity),
        dual_objective_estimate=raw_objective, raw_duality_gap=float(t-raw_objective),
        support_lower_estimate=support_value, support_stationarity_correction=float(
            np.minimum(support_gradient*lower, support_gradient*upper).sum()),
        support_weight_sum=float(sum(r['support_weight'] for r in records)),
        stationarity_vector=stationarity.tolist(),
        box_lower_multipliers=mu_lower.tolist(), box_upper_multipliers=mu_upper.tolist(),
        hard_constraint_multipliers=hard_mu.tolist(),
        constraint_multipliers=records,
        strength='floating_point_numerically_checked_estimates_not_rigorous_bounds')
    if not all(np.isfinite(checks[k]) for k in ('stationarity_inf', 'epigraph_stationarity_abs',
            'dual_cone_violation', 'complementarity_abs', 'dual_objective_estimate',
            'raw_duality_gap', 'support_lower_estimate')):
        raise ValueError('NONFINITE_DUAL_CHECK')
    return checks


def conic_capability(model, requirements, protocol, *, initial_delta=None,
                     solver_options=None, check_tolerance=1e-7, path_assignment=None):
    """Same analyzed subproblem as task_capability, with independent numeric checks.

    Local options tune numerics only; task data still belongs to the existing
    model/requirements/protocol. Nonconvergence never establishes infeasibility.
    """
    paths=[c for c in requirements.constraints if c.kind=='path_bound']
    if paths and len(paths[0].path_vertices_m)==3 and path_assignment is None:
        return _path_assignments(model,requirements,protocol,initial_delta,solver_options,check_tolerance)
    started = time.perf_counter()
    result = dict(method_version=PATH_METHOD if paths else METHOD, status='not_applicable', coverage=[], certificate=None,
        all_requested_checked=False, optimality_status='unknown', quantities={},
        numerical_feasibility='unknown',
        model_scope='Frozen local affine model; exact ZOH and preceding hold; analyzed samples only.',
        unsupported_inferences=['Strict floating-point certification', 'Continuous-time feasibility',
            'Nonlinear or MuJoCo feasibility', 'Physical task acceptance', 'Global structural ordering'],
        solver=dict(name='CVXPY/CLARABEL', status='not_run', error=None,
                    reported_primal_residual=None, reported_dual_residual=None,
                    reported_dual_objective=None,
                    unavailable_reason='CVXPY public Clarabel SolverStats does not expose these fields.'),
        problem_definition=dict(objective='min t subject to g_i(z) <= t and lower <= z <= upper',
            norm='norm(output-reference)/radius - 1',
            interval='(lower-residual)/scale, (residual-upper)/scale; scale=max(abs(bounds))',
            bounds_scope='Analyzed sampled subproblem only'))
    try:
        if not np.isfinite(check_tolerance) or check_tolerance <= 0:
            raise ValueError('POSITIVE_FINITE_NUMERICAL_CHECK_TOLERANCE_REQUIRED')
        options = {**DEFAULT_OPTIONS, **(solver_options or {})}
        if set(options)-set(DEFAULT_OPTIONS):
            raise ValueError('UNSUPPORTED_LOCAL_SOLVER_OPTION')
        if (type(options['max_iter']) is not int or options['max_iter'] < 1
                or any(not isinstance(options[k], Real) or not np.isfinite(options[k]) or options[k] <= 0
                       for k in options if k != 'max_iter')):
            raise ValueError('INVALID_LOCAL_SOLVER_OPTION')
        result['numerical_options'] = dict(effective=options, overrides=solver_options or {},
            source='conic_capability v1 local defaults plus explicit caller overrides; not frozen task data',
            check_tolerance=check_tolerance, replay_atol=protocol.endpoint_check_atol)
        scope, dynamics, initial, rows, lower, upper, _ = prepare_conic_trajectory(
            model, requirements, protocol, result, initial_delta,path_assignment)
        physical=scope.get('physical_variable_count',len(lower))
        if paths:
            result.update(method_version=PATH_METHOD,path_assignment=path_assignment,
                auxiliary_coordinates=dict(kind='normalized_path_progress',units='dimensionless',physical_tendon_count=len(model.u0)),
                untimed_scope=scope['untimed_scope'],internal_conic_solves=0)
        requested = sum(len(c.indices) for c in requirements.constraints)
        result['coverage_counts'] = dict(requested=requested, analyzed=len(rows), fraction=len(rows)/requested)
        if not rows:
            result['reason'] = 'No compatible future sampled constraints.'
            return result
        scales = [normalization(c) for c, *_ in rows]
        result['provenance'] = dict(model_identity=_identity(model), requirement_identity=_identity(requirements),
            protocol_identity=_identity(protocol), identity_encoding='sha256 sorted compact JSON UTF-8',
            model_binding=_plain(model.binding), operating_point=_plain(model.operating_point),
            model_protocol_identity=getattr(model, 'protocol_identity', None),
            task_binding=_plain(requirements.binding), protocol=_plain(protocol),
            required_physics=requirements.required_physics,
            applicability='Caller supplies an applicable frozen affine model; this kernel does not assess physics support.',
            state_definition=_plain(getattr(model, 'state_definition', None)),
            input_definition=_plain(getattr(model, 'input_definition', None)))
        import cvxpy as cp
        result['versions'] = {name: version(name) for name in ('cvxpy', 'clarabel', 'numpy', 'scipy')}
        result['status'] = 'inconclusive'
        zvar = cp.Variable(len(lower), name='physical_and_progress' if paths else 'physical_delta_tensions_n') if len(lower) else None
        tvar = cp.Variable(name='signed_minimax')
        blocks = _blocks(cp, rows, scales, zvar, tvar)
        box = [zvar >= lower, zvar <= upper] if zvar is not None else []
        hard_matrix=np.asarray(scope.get('hard_matrix',[]),dtype=float)
        hard_upper=np.asarray(scope.get('hard_upper',[]),dtype=float)
        hard=hard_matrix@zvar<=hard_upper if len(hard_upper) else None
        problem = cp.Problem(cp.Minimize(tvar), box+[b['constraint'] for b in blocks]+([hard] if hard is not None else []))
        tick = time.perf_counter()
        try:
            if paths:result['internal_conic_solves']=1
            problem.solve(solver='CLARABEL', **options)
        except cp.error.SolverError as exc:
            result['solver'].update(status='solver_error', error=str(exc))
            return result
        finally:
            result['solver']['wall_s'] = time.perf_counter()-tick
        stats = problem.solver_stats
        result['solver'].update(status=problem.status, objective=problem.value,
            iterations=stats.num_iters, solve_time_s=stats.solve_time, setup_time_s=stats.setup_time,
            extra_stats_available=stats.extra_stats is not None)
        raw = np.asarray(zvar.value, dtype=float).ravel() if zvar is not None else np.zeros(0)
        if (tvar.value is None or raw.shape != lower.shape or not np.all(np.isfinite(raw))
                or not np.isfinite(tvar.value)):
            result['solver']['objective'] = None
            result['reason'] = 'NO_FINITE_PRIMAL_SOLUTION'
            return result
        t = float(tvar.value); steps, nu = scope['step_count'], len(model.u0)
        result['raw_primal'] = dict(delta_input_n=raw[:physical].reshape(steps, nu).tolist(),
            applied_input_n=(raw[:physical].reshape(steps, nu)+model.u0).tolist(), epigraph=t)
        if paths:result['raw_primal']['path_progress']=raw[physical:].tolist()
        raw_excess = []
        for block in blocks:
            residual = block['M']@raw+block['b']
            raw_excess.append(float(np.linalg.norm(residual))-1 if block['kind'] == 'soc' else float(residual))
        if not np.all(np.isfinite(raw_excess)):
            result['reason'] = 'NONFINITE_PRIMAL_CONSTRAINT_SCORE'
            return result
        box_error = max(0., float(np.max(lower-raw, initial=0.)), float(np.max(raw-upper, initial=0.)))
        result['primal_checks'] = dict(source='independent_from_original_sample_maps',
            epigraph_violation=max(0., max(raw_excess)-t),
            box_violation_n=max(0.,float(np.max(lower[:physical]-raw[:physical],initial=0.)),float(np.max(raw[:physical]-upper[:physical],initial=0.))))
        hard_error=max(0.,float(np.max(hard_matrix@raw-hard_upper,initial=0.))) if hard is not None else 0.
        if paths:result['primal_checks']['progress_constraint_violation']=max(hard_error,
            float(np.max(lower[physical:]-raw[physical:],initial=0.)),float(np.max(raw[physical:]-upper[physical:],initial=0.)))
        try:
            dual = _dual_checks(blocks, box, raw, t, lower, upper, check_tolerance,hard,hard_matrix,hard_upper)
            result['dual_checks'] = dual
        except ValueError as exc:
            dual = None
            result['dual_checks'] = dict(status='unavailable', reason=str(exc))
        # Retain raw solver values; only tiny box excursions may be repaired.
        if max(box_error,hard_error) > protocol.endpoint_check_atol:
            result['reason'] = 'SOLVER_CONTROL_OUTSIDE_PHYSICAL_BOX'
            return result
        z = np.clip(raw, lower, upper)
        replay = verify_witness(model, dynamics, initial, z[:physical].reshape(steps, nu), rows, scope,
                                protocol.endpoint_check_atol,z[physical:])
        valid = bool(replay.get('finite') and len(replay.get('records', [])) == len(rows)
            and replay['max_prediction_replay_error'] <= protocol.endpoint_check_atol
            and replay.get('path_progress_valid',True) and np.all(z >= lower) and np.all(z <= upper))
        replay['numerically_valid'] = valid
        result.update(replay=replay, delta_input_n=z[:physical].reshape(steps, nu).tolist(),
            applied_input_n=(z[:physical].reshape(steps, nu)+model.u0).tolist(), box_repair_inf_n=_maxabs(z[:physical]-raw[:physical]))
        if paths:result['path_progress']=z[physical:].tolist()
        result['all_requested_checked'] = bool(valid and result['full_requested_coverage'])
        if not valid:
            result['reason'] = 'INDEPENDENT_REPLAY_FAILED_SCORES_WITHHELD'
            return result
        for record, scale, (c, *_) in zip(replay['records'], scales, rows):
            excess = -np.asarray(record['margins'])/scale
            record.update(signed_excesses=excess.tolist(), signed_violation=float(max(excess)),
                          normalization_scale=scale, radius=c.radius, lower=c.lower, upper=c.upper)
        score = max(r['signed_violation'] for r in replay['records'])
        if not np.isfinite(score):
            result['reason'] = 'NONFINITE_REPLAY_SCORE'
            return result
        result['replayed_violation'] = score
        result['quantities'] = dict(analytic_lower_bound=dict(value=-1., strength='strict_analytic'),
            witness_upper_estimate=dict(value=score, strength='independently_replayed_float'),
            rigorous_upper_bound=dict(value=None, strength='unavailable'),
            optimal_value=dict(value=None, strength='unavailable'))
        if score <= 0 and replay['passed']:
            result['status'] = 'feasible_witness'
            result['numerical_feasibility'] = 'sampled_feasible_witness'
        if dual is not None:
            gap = score-dual['support_lower_estimate']
            dual['replayed_support_gap'] = gap
            tol = check_tolerance*(1+max(abs(score), abs(t)))
            passed = bool(problem.status == cp.OPTIMAL
                and result['primal_checks']['epigraph_violation'] <= tol
                and hard_error<=tol
                and dual['stationarity_inf'] <= check_tolerance
                and dual['epigraph_stationarity_abs'] <= check_tolerance
                and dual['dual_cone_violation'] <= check_tolerance
                and dual['complementarity_abs'] <= tol
                and abs(dual['raw_duality_gap']) <= tol and -tol <= gap <= tol)
            result['optimality_status'] = 'numerically_checked' if passed else 'unknown'
            result['quantities']['support_lower_estimate'] = dict(value=dual['support_lower_estimate'],
                strength='numerically_checked_float_not_rigorous')
            result['numerical_feasibility'] = ('sampled_feasible_witness' if result['status'] == 'feasible_witness'
                else 'positive_optimum_numerical_evidence' if passed and dual['support_lower_estimate'] > tol
                else 'unknown')
        return result
    except (ValueError, FloatingPointError, np.linalg.LinAlgError, ImportError) as exc:
        result['reason'] = str(exc)
        result['solver']['error'] = str(exc)
        return result
    finally:
        result['kernel_elapsed_s'] = time.perf_counter()-started


def _path_assignments(model,requirements,protocol,initial_delta,solver_options,tolerance):
    """Enumerate the free sampled corner, never replace a bend by its convex hull."""
    path=next(c for c in requirements.constraints if c.kind=='path_bound')
    choices=path.indices[1:-1]
    if not choices:return dict(status='not_applicable',method_version=PATH_METHOD,optimality_status='unknown',
        coverage=[],reason='PATH_CORNER_REQUIRES_INTERIOR_SAMPLE',kernel_elapsed_s=0.)
    branches=[conic_capability(model,requirements,protocol,initial_delta=initial_delta,solver_options=solver_options,
        check_tolerance=tolerance,path_assignment=j) for j in choices]
    valid=[b for b in branches if b.get('replay',{}).get('numerically_valid')]
    best=min(valid,key=lambda b:b['replayed_violation']) if valid else branches[0]
    summaries=[dict(corner_sample=j,status=b['status'],score=b.get('replayed_violation'),
        optimality=b['optimality_status'],support_lower_estimate=b.get('dual_checks',{}).get('support_lower_estimate')) for j,b in zip(choices,branches)]
    best['path_assignment_comparison']=summaries
    best['internal_conic_solves']=sum(b.get('internal_conic_solves',0) for b in branches)
    best['kernel_elapsed_s']=sum(b['kernel_elapsed_s'] for b in branches)
    if len(valid)==len(branches) and all(b['optimality_status']=='numerically_checked' for b in branches):
        lower=min(r['support_lower_estimate'] for r in summaries)
        best['dual_checks']['selected_branch_support_lower_estimate']=best['dual_checks']['support_lower_estimate']
        best['dual_checks']['support_lower_estimate']=lower
        best['dual_checks']['replayed_support_gap']=best['replayed_violation']-lower
        best['optimality_status']='numerically_checked' if best['replayed_violation']-lower<=tolerance*(1+abs(lower)) else 'unknown'
        best['path_assignment_ties']=[r['corner_sample'] for r in summaries if abs(r['score']-best['replayed_violation'])<=tolerance*(1+abs(lower))]
    else:best['optimality_status']='unknown'
    return best
