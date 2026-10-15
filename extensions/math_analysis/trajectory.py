"""Sampled local affine feasibility, physical input boxes, and independent replay.

No task names, candidate construction, persistence, or physical acceptance live here.
All arrays use physical coordinates. Outputs at a boundary use the preceding hold.
"""
import numpy as np
from scipy.optimize import Bounds, minimize
from extensions.math_analysis.kernels import zoh, _minimum_residual_certificate


SCOPE = 'sampled-affine-trajectory-v1'


def time_scope(requirements, protocol, start_s):
    """Map absolute samples to exact control boundaries, including a zero horizon."""
    dt, tol = protocol.period_s, protocol.horizon_alignment_atol_s
    if start_s is None or not np.isfinite(start_s) or not 0 <= start_s <= requirements.duration_s:
        raise ValueError('KNOWN_ANALYSIS_START_TIME_REQUIRED')
    def boundary(t):
        k = int(round(t / dt))
        if abs(k * dt - t) > tol:
            raise ValueError('SAMPLE_OR_ORIGIN_NOT_ALIGNED_WITH_CONTROL_GRID')
        return k
    origin, end = boundary(start_s), boundary(requirements.duration_s)
    indices = {i: boundary(t) - origin for i, t in enumerate(requirements.time_grid_s) if t >= start_s - tol}
    return dict(start_time_s=float(start_s), remaining_task_s=requirements.duration_s-start_s,
        step_count=end-origin, control_period_s=dt, sample_period_s=requirements.sample_period_s,
        input_hold_s=dt, sample_phase='post_step_preceding_hold', sample_steps=indices)


def sampled_maps(model, steps, dt, initial_delta=None):
    """One recurrence builds all state maps against the same stacked delta inputs."""
    A, B, c = map(lambda x: np.asarray(x, dtype=float), (model.A, model.B, model.drift))
    nx, nu = B.shape
    x = np.zeros(nx) if initial_delta is None else np.asarray(initial_delta, dtype=float)
    if (model.time_domain != 'continuous' or A.shape != (nx, nx) or c.shape != (nx,)
            or x.shape != (nx,) or len(model.u0) != nu
            or not all(np.all(np.isfinite(v)) for v in (A, B, c, x))):
        raise ValueError('INVALID_CONTINUOUS_MODEL_OR_INITIAL_PERTURBATION')
    Ad, Bd, cd = zoh(A, B, c, dt)
    H = np.zeros((nx, steps*nu)); states = [(x.copy(), H.copy())]
    for k in range(steps):
        x = Ad@x + cd; H = Ad@H
        H[:, k*nu:(k+1)*nu] += Bd
        states.append((x.copy(), H.copy()))
    return (Ad, Bd, cd), states


def _output_map(output, state, k, steps, u0, previous):
    C, D, y0 = map(lambda v: np.asarray(v, dtype=float), (output.C, output.D, output.value0))
    a, H = state; nu = len(u0)
    if C.shape != (len(y0), len(a)) or D.shape != (len(y0), nu):
        raise ValueError('OUTPUT_DIMENSION_MISMATCH')
    base, matrix = y0+C@a, C@H
    if np.any(D):
        if k == 0:
            if previous is None:
                raise ValueError('INITIAL_FEEDTHROUGH_REQUIRES_KNOWN_PREVIOUS_INPUT')
            base += D@(previous-u0)
        else:
            matrix[:, (k-1)*nu:k*nu] += D
    if not np.all(np.isfinite(base)) or not np.all(np.isfinite(matrix)):
        raise ValueError('NONFINITE_OUTPUT_MAP')
    return base, matrix


def _margins(c, residual):
    if c.kind == 'norm_bound':
        value = float(np.linalg.norm(residual))
        return np.array([c.radius-value]), value
    margins = np.concatenate((residual-np.asarray(c.lower), np.asarray(c.upper)-residual))
    return margins, residual.tolist()


def verify_witness(model, dynamics, initial, delta, rows, scope, atol):
    """Replay states and outputs without multiplying the assembled prediction map."""
    Ad, Bd, cd = dynamics; steps = scope['step_count']; nu = len(model.u0)
    z = np.asarray(delta, dtype=float)
    if z.shape != (steps, nu) or not np.all(np.isfinite(z)):
        return dict(passed=False, reason='NONFINITE_OR_INCOMPATIBLE_INPUT_SEQUENCE')
    u0 = np.asarray(model.u0); applied = z+u0; limits = np.asarray(model.binding['tension_limits_n'])
    tension_margin = float(np.min(np.concatenate((applied.ravel(), (limits-applied).ravel())), initial=np.inf))
    x = np.asarray(initial, dtype=float); states = [x.copy()]
    for du in z:
        x = Ad@x+Bd@du+cd; states.append(x.copy())
        if not np.all(np.isfinite(x)):
            return dict(passed=False, finite=False, reason='NONFINITE_REPLAY_STATE')
    previous = model.operating_point.get('previous_applied_input_n')
    records = []; prediction_error = 0.
    for c, index, k, reference, output, base, matrix in rows:
        direct = z[k-1] if k else np.zeros(nu) if previous is None else np.asarray(previous)-u0
        y = np.asarray(output.value0)+np.asarray(output.C)@states[k]+np.asarray(output.D)@direct
        if not np.all(np.isfinite(y)):
            return dict(passed=False, finite=False, reason='NONFINITE_REPLAY_OUTPUT', constraint_id=c.constraint_id, sample_index=index)
        residual = y-reference; margins, value = _margins(c, residual)
        scale = max(c.radius if c.kind == 'norm_bound' else max(np.max(np.abs(c.lower)), np.max(np.abs(c.upper))), atol)
        violation = max(0., -float(np.min(margins)))
        prediction_error = max(prediction_error, float(np.max(np.abs(y-base-matrix@z.ravel()))))
        records.append(dict(constraint_id=c.constraint_id, sample_index=index, control_step=k,
            absolute_time_s=scope['start_time_s']+k*scope['control_period_s'], signal=c.signal.name,
            units=c.signal.units, frame=c.signal.frame, output=y.tolist(), reference=reference.tolist(),
            residual=residual.tolist(), value=value, margins=margins.tolist(),
            violation=violation, normalized_violation=violation/scale, passed=bool(violation <= atol)))
    finite = all(np.all(np.isfinite(v)) for v in states) and all(
        np.all(np.isfinite(r['output'])) and np.all(np.isfinite(r['margins'])) for r in records)
    worst = max(records, key=lambda r: r['normalized_violation'], default=None)
    max_abs = max((r['violation'] for r in records), default=0.)
    return dict(passed=bool(finite and tension_margin >= -atol and max_abs <= atol and prediction_error <= atol),
        finite=bool(finite), records=records, states=[v.tolist() for v in states],
        max_absolute_violation=max_abs, max_normalized_violation=max((r['normalized_violation'] for r in records), default=0.),
        worst_violation=worst if worst and worst['violation'] > 0 else None,
        minimum_tension_margin_n=None if steps == 0 else tension_margin,
        max_prediction_replay_error=prediction_error, absolute_tolerance=atol)


def _certificate(c, index, base, matrix, reference, lower, upper, atol):
    """Check a necessary constraint against the complete box, independently of SLSQP."""
    if c.kind == 'norm_bound':
        if len(lower) and np.all(upper > lower):
            proposed = _minimum_residual_certificate(matrix, base, reference, lower, upper, c.radius, atol)
            direction = np.asarray(proposed['separating_direction']['direction'])
        else:
            r = base+matrix@lower-reference
            direction = r/max(float(np.linalg.norm(r)), np.finfo(float).tiny)
        norm = float(np.linalg.norm(direction))
        if not np.isfinite(norm) or norm == 0:
            return None
        # Recompute support bound using our arrays, never the helper's success/bound.
        direction = direction/max(1., norm)
        coefficients = matrix.T@direction
        terms = np.minimum(coefficients*lower, coefficients*upper)
        raw = float(direction@(base-reference)+sum(terms))
        allowance = atol+32*np.finfo(float).eps*(1+abs(float(direction@(base-reference)))+sum(abs(terms)))
        margin = raw-c.radius-allowance
        data = dict(kind='separating_direction', direction=direction.tolist(), direction_norm=float(np.linalg.norm(direction)),
            lower_bound=raw, limit=c.radius, numerical_allowance=float(allowance), margin=float(margin))
    else:
        lo = base-reference+np.sum(np.minimum(matrix*lower, matrix*upper), axis=1)
        hi = base-reference+np.sum(np.maximum(matrix*lower, matrix*upper), axis=1)
        allowance = atol+32*np.finfo(float).eps*(1+np.abs(base-reference)+np.sum(np.abs(matrix)*np.maximum(abs(lower),abs(upper)), axis=1))
        gaps = np.maximum(lo-np.asarray(c.upper), np.asarray(c.lower)-hi)-allowance
        component = int(np.argmax(gaps)); margin = float(gaps[component])
        data = dict(kind='component_box_range', component=component, residual_lower=lo.tolist(), residual_upper=hi.tolist(),
            permitted_lower=c.lower, permitted_upper=c.upper, numerical_allowance=allowance.tolist(), margin=margin)
    if not np.isfinite(margin) or margin <= 0:
        return None
    return dict(verified=True, constraint_id=c.constraint_id, sample_index=index, **data,
        base=base.tolist(), matrix=matrix.tolist(), reference=reference.tolist(),
        delta_lower=lower.tolist(), delta_upper=upper.tolist(), scope='Necessary sampled constraint under the complete physical input box only.')


def trajectory_feasibility(model, requirements, protocol, *, initial_delta=None):
    """One convex bounded sequence; only replay or a checked separation decides."""
    result = dict(solver_scope=SCOPE, status='not_applicable', coverage=[], certificate=None,
        all_requested_checked=False,
        model_scope='Frozen local affine dynamics, exact ZOH; sampled constraints only, no nonlinear/physical acceptance.')
    try:
        scope = time_scope(requirements, protocol, model.operating_point.get('actual_time_s'))
        result['horizon'] = scope
        remaining = model.operating_point.get('remaining_task_s')
        if remaining is None or abs(remaining-scope['remaining_task_s']) > protocol.horizon_alignment_atol_s:
            raise ValueError('MODEL_REMAINING_TIME_DISAGREES_WITH_ABSOLUTE_GRID')
        steps = scope['step_count']; u0 = np.asarray(model.u0, dtype=float); nu = len(u0)
        limits = np.asarray(model.binding['tension_limits_n'], dtype=float)
        if (limits.shape != u0.shape or not np.all(np.isfinite(limits)) or not np.all(np.isfinite(u0))
                or np.any(limits <= 0) or np.any(u0 < 0) or np.any(u0 > limits)):
            raise ValueError('INVALID_PHYSICAL_INPUT_BOX_OR_NOMINAL_INPUT')
        if (requirements.physical_inputs.get('lower') != [0.]*nu
                or requirements.physical_inputs.get('upper') != limits.tolist()):
            raise ValueError('REQUIREMENT_AND_MODEL_PHYSICAL_INPUT_BOX_MISMATCH')
        previous = model.operating_point.get('previous_applied_input_n')
        if previous is not None:
            previous = np.asarray(previous, dtype=float)
            if previous.shape != u0.shape or not np.all(np.isfinite(previous)) or np.any(previous < 0) or np.any(previous > limits):
                raise ValueError('INVALID_PREVIOUS_PHYSICAL_INPUT')
        dynamics, states = sampled_maps(model, steps, protocol.period_s, initial_delta)
        result['discrete_dynamics'] = dict(zip(('A_d','B_d','drift_d'), (v.tolist() for v in dynamics)))
        initial = states[0][0]; outputs = {o.name:o for o in model.endpoint_outputs}; rows = []
        for c in requirements.constraints:
            output = outputs.get(c.signal.name); indices = []; reasons = []
            compatible = (c.kind in ('norm_bound','component_interval') and output is not None
                and (output.units,output.frame,len(output.value0)) == (c.signal.units,c.signal.frame,c.signal.dimension)
                and c.signal.phase == 'post_step')
            for index, reference in zip(c.indices, c.reference):
                if not compatible:
                    reasons.append('Unsupported kind or output identity/units/frame/phase.'); continue
                if index not in scope['sample_steps']:
                    reasons.append('Sample precedes analysis start; no prior evidence supplied.'); continue
                k = scope['sample_steps'][index]
                try:
                    base, matrix = _output_map(output, states[k], k, steps, u0, previous)
                except ValueError as exc:
                    reasons.append(str(exc)); continue
                rows.append((c,index,k,np.asarray(reference),output,base,matrix)); indices.append(index)
            result['coverage'].append(dict(constraint_id=c.constraint_id, analyzed_indices=indices,
                unchecked_indices=[i for i in c.indices if i not in indices], reasons=sorted(set(reasons))))
        result['full_requested_coverage'] = all(not c['unchecked_indices'] for c in result['coverage'])
        if not rows:
            result['reason'] = 'No compatible future sampled constraints.'; return result
        lower, upper = np.tile(-u0, steps), np.tile(limits-u0, steps)
        atol = protocol.endpoint_check_atol
        result['physical_bounds_n'] = dict(lower=[0.]*nu, upper=limits.tolist(), nominal=u0.tolist())
        result['initial_delta_state'] = initial.tolist()
        scale = np.tile(np.asarray(model.input_scales, dtype=float), steps)
        if scale.shape != lower.shape or np.any(scale <= 0) or not np.all(np.isfinite(scale)):
            raise ValueError('INVALID_INPUT_SCALES')
        def objective(z): return float(protocol.period_s*np.sum((z/scale)**2))
        def margins(z):
            return np.concatenate([_margins(c,base+matrix@z-ref)[0]/max(
                c.radius if c.kind == 'norm_bound' else max(np.max(np.abs(c.lower)),np.max(np.abs(c.upper))),atol)
                for c,_,_,ref,_,base,matrix in rows])
        z = np.clip(np.zeros(steps*nu), lower, upper)
        result['status'] = 'inconclusive'
        if steps:
            solved = minimize(objective,z,jac=lambda v: 2*protocol.period_s*v/scale**2,
                bounds=Bounds(lower,upper),constraints=[dict(type='ineq',fun=margins)],method='SLSQP',
                options=dict(maxiter=protocol.endpoint_max_iterations,ftol=1e-12,disp=False))
            z = np.asarray(solved.x)
            result['solver'] = dict(name='scipy.optimize.SLSQP', success=bool(solved.success), status=int(solved.status),
                message=str(solved.message), iterations=int(solved.nit), maximum_iterations=protocol.endpoint_max_iterations,
                constraint_scaling='radius or maximum absolute component bound, floored by check atol; physical residuals replayed')
        else:
            result['solver'] = dict(name='zero_horizon_direct_check', iterations=0)
        if z.shape != lower.shape or not np.all(np.isfinite(z)):
            result['reason'] = 'NONFINITE_OR_INCOMPATIBLE_SOLVER_SEQUENCE'
            return result
        replay = verify_witness(model,dynamics,initial,z.reshape(steps,nu),rows,scope,atol)
        result.update(replay=replay, delta_input_n=z.reshape(steps,nu).tolist(), applied_input_n=(z.reshape(steps,nu)+u0).tolist())
        result['all_requested_checked'] = result['full_requested_coverage'] and len(replay.get('records',[])) == len(rows)
        if replay['passed']:
            result['status'] = 'feasible_witness'
        else:
            result.update(status='inconclusive', reason='No replay-verified shared sequence or verified necessary-condition exclusion.')
            for c,index,_,ref,_,base,matrix in rows:
                certificate = _certificate(c,index,base,matrix,ref,lower,upper,atol)
                if certificate:
                    result.update(status='model_infeasibility_certificate', certificate=certificate,
                        reason='Verified necessary sampled constraint exclusion under the complete physical input box.'); break
        return result
    except (ValueError, FloatingPointError, np.linalg.LinAlgError) as exc:
        result['reason'] = str(exc)
        return result
