"""Signed sampled minimax diagnostics on the existing frozen affine trajectory.

Replay checks a control, never optimality. No task names, Store or Agent policy.
"""
import time
import numpy as np
from scipy.optimize import Bounds, minimize
from extensions.math_analysis.trajectory import prepare_trajectory, verify_witness, _margins, _margin_jacobian


def normalization(constraint):
    """Physical scale; zero-radius norms have no dimensionless relative excess."""
    scale = (constraint.radius if constraint.kind in ('norm_bound','path_bound') else
             max(np.max(np.abs(constraint.lower)), np.max(np.abs(constraint.upper))))
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError('SIGNED_VIOLATION_REQUIRES_POSITIVE_PHYSICAL_SCALE')
    return float(scale)


def task_capability(model, requirements, protocol, *, applied_input_n=None, initial_delta=None):
    """Optimize from three deterministic starts, or replay one fixed physical input.

    Norm excess is ||y-reference||/radius - 1. Interval excesses are
    (lower-residual)/scale and (residual-upper)/scale, where scale is the
    maximum absolute component bound. All quantities concern analyzed samples.
    """
    started = time.perf_counter()
    result = dict(solver_scope='sampled-affine-signed-minimax-v1', status='not_applicable',
        coverage=[], certificate=None, all_requested_checked=False,
        control_reoptimization='required' if applied_input_n is None else 'fixed_control',
        problem_definition=dict(ideal='V_tau(d) = inf_{U in physical input box} max_i g_i(d,U)',
            computed='Best discovered signed maximum over explicitly analyzed samples',
            norm='norm(output-reference)/radius - 1',
            interval='max(lower-residual, residual-upper)/max(abs(lower),abs(upper))',
            bounds_scope='Analyzed sampled subproblem only; missing samples are not certified',
            optimality='unverified; solver convergence is not an optimality certificate'),
        model_scope='Frozen local affine model, exact ZOH, preceding hold at sample boundaries; no physical acceptance.',
        quantities={}, starts=[])
    try:
        scope, dynamics, initial, rows, lower, upper, _ = prepare_trajectory(
            model, requirements, protocol, result, initial_delta)
        if not rows:
            result['reason'] = 'No compatible future sampled constraints.'
            return result
        scales = [normalization(c) for c, *_ in rows]
        steps, nu = scope['step_count'], len(model.u0)
        u0 = np.asarray(model.u0)
        atol = protocol.endpoint_check_atol
        result['status'] = 'inconclusive'
        result['solver_settings'] = dict(name='scipy.optimize.SLSQP', formulation='signed epigraph',
            maxiter=protocol.endpoint_max_iterations, ftol=1e-12,
            starts='nominal, 25% and 75% of physical tension box',
            input_coordinates='physical delta tensions in N', check_atol=atol,
            optimality_certificate=False)

        def excess(z):
            return np.concatenate([-_margins(c, base+matrix@z-ref)[0]/s
                for (c, _, _, ref, _, base, matrix), s in zip(rows, scales)])

        def jacobian(z):
            return np.concatenate([-_margin_jacobian(c, base+matrix@z-ref, matrix, 0.)
                for c, _, _, ref, _, base, matrix in rows], axis=0)

        def replay(z):
            checked = verify_witness(model, dynamics, initial, z.reshape(steps, nu), rows, scope, atol)
            # Task violation is independent of validity of the physical input/replay.
            valid = (checked.get('finite') is True and len(checked.get('records', [])) == len(rows)
                and np.all(z >= lower) and np.all(z <= upper)
                and checked.get('max_prediction_replay_error', float('inf')) <= atol)
            checked['numerically_valid'] = bool(valid)
            for record, (c, *_), scale in zip(checked.get('records', []), rows, scales):
                signed = -np.asarray(record['margins'])/scale
                record.update(signed_excesses=signed.tolist(), signed_violation=float(np.max(signed)),
                    normalization_scale=scale, lower=c.lower, upper=c.upper, radius=c.radius)
            return checked

        best_z, best_value, best_origin = None, float('inf'), None

        def consider(z, origin):
            nonlocal best_z, best_value, best_origin
            z = np.asarray(z, dtype=float)
            if z.shape != lower.shape or not np.all(np.isfinite(z)):
                return None
            if np.any(z < lower) or np.any(z > upper):
                return None
            value = float(np.max(excess(z)))
            if np.isfinite(value) and value < best_value:
                best_z, best_value, best_origin = z.copy(), value, origin
            return value if np.isfinite(value) else None

        if applied_input_n is not None:
            applied = np.asarray(applied_input_n, dtype=float)
            if applied.size == 0 and steps == 0:
                applied = applied.reshape(0, nu)
            if applied.shape != (steps, nu):
                raise ValueError('FIXED_INPUT_SEQUENCE_SHAPE_MISMATCH')
            consider((applied-u0).ravel(), 'fixed_control')
        else:
            seeds = [np.clip(np.zeros_like(lower), lower, upper),
                     lower+.25*(upper-lower), lower+.75*(upper-lower)] if steps else [lower]
            for index, seed in enumerate(seeds):
                baseline = consider(seed, f'start_{index}')
                attempt = dict(start_index=index, initial_violation=baseline,
                    initial_applied_input_n=(seed.reshape(steps, nu)+u0).tolist())
                result['starts'].append(attempt)
                if not steps:
                    attempt.update(success=True, message='zero horizon direct check', iterations=0)
                    continue
                if baseline is None:
                    attempt.update(success=False, message='nonfinite initial score', iterations=0)
                    continue
                tick = time.perf_counter()
                solved = minimize(lambda v: v[-1], np.r_[seed, baseline],
                    jac=lambda v: np.r_[np.zeros(len(lower)), 1.], method='SLSQP',
                    bounds=Bounds(np.r_[lower, -np.inf], np.r_[upper, np.inf]),
                    constraints=[dict(type='ineq', fun=lambda v: v[-1]-excess(v[:-1]),
                        jac=lambda v: np.column_stack((-jacobian(v[:-1]), np.ones(len(excess(v[:-1]))))))],
                    callback=lambda v: consider(v[:-1], f'iterate_{index}'),
                    options=dict(maxiter=protocol.endpoint_max_iterations, ftol=1e-12, disp=False))
                z = np.asarray(solved.x)
                finite = z.shape == (len(lower)+1,) and np.all(np.isfinite(z))
                final = consider(z[:-1], f'final_{index}') if finite else None
                attempt.update(success=bool(solved.success), status=int(solved.status), message=str(solved.message),
                    iterations=int(solved.nit), objective_evaluations=getattr(solved, 'nfev', None),
                    elapsed_s=time.perf_counter()-tick, returned_violation=final,
                    epigraph_residual=float(max(0., final-z[-1])) if final is not None else None,
                    finite_return=bool(finite))
        if best_z is None:
            result['reason'] = 'No finite legal input with a finite task score.'
            return result
        checked = replay(best_z)
        result.update(replay=checked, selected_control_source=best_origin,
            delta_input_n=best_z.reshape(steps, nu).tolist(),
            applied_input_n=(best_z.reshape(steps, nu)+u0).tolist())
        result['all_requested_checked'] = bool(result['full_requested_coverage'] and checked['numerically_valid'])
        if not checked['numerically_valid']:
            result['reason'] = 'Independent physical-input/output replay check failed; scores withheld.'
            return result
        records = checked['records']
        applied = best_z.reshape(steps, nu)+u0
        result['input_diagnostics'] = dict(
            minimum_lower_margin_n=np.min(applied, axis=0).tolist() if steps else None,
            minimum_upper_margin_n=np.min(np.asarray(model.binding['tension_limits_n'])-applied, axis=0).tolist() if steps else None,
            tendon_order=model.binding.get('tendon_order'),
            near_bound_samples=int(np.sum((applied <= atol) | (np.asarray(model.binding['tension_limits_n'])-applied <= atol))))
        result['locality_diagnostics'] = dict(max_absolute_delta_state=np.max(np.abs(checked['states']), axis=0).tolist(),
            validated_locality_radius=None, interpretation='State excursions are recorded, but local nonlinear agreement is unvalidated.')
        value = max(r['signed_violation'] for r in records)
        worst = max(range(len(records)), key=lambda i: records[i]['signed_violation'])
        result.update(best_found_violation=value, bottleneck_record=worst,
            near_active_records=[i for i, r in enumerate(records) if abs(r['signed_violation']) <= .05],
            co_bottleneck_records=[i for i, r in enumerate(records) if value-r['signed_violation'] <= .05])
        # -1 follows analytically from nonnegative norms / the interval halfwidth
        # being no greater than its maximum absolute bound; no solver is involved.
        result['quantities'] = dict(
            best_found_violation=dict(value=value, status='unverified_estimate'),
            replayed_violation=dict(value=value, status='verified'),
            lower_bound=dict(value=-1., status='verified'),
            witness_upper_bound_estimate=dict(value=value, status='unverified_estimate'),
            upper_bound=dict(value=None, status='unavailable'),
            optimal_task_violation=dict(value=None, status='unavailable'))
        result['verification_scope'] = dict(input_legality=True, discrete_replay=True, sampled_score=True,
            optimality=False, rigorous_floating_point_upper_bound=False,
            lower_bound='Analytic -1 from the signed constraint definitions, for analyzed samples',
            tolerances='Replay agreement uses check_atol; witness additionally requires signed_violation <= 0')
        if value <= 0 and checked['passed']:
            result['status'] = 'feasible_witness'
        values = [r['returned_violation'] for r in result['starts'] if r.get('returned_violation') is not None]
        result['start_value_spread'] = max(values)-min(values) if values else None
        result['research_diagnostics'] = dict(
            bottleneck=dict(constraint_id=records[worst]['constraint_id'], sample_index=records[worst]['sample_index'],
                absolute_time_s=records[worst]['absolute_time_s'], signed_violation=value),
            competing_explanations=['Limited authority in this frozen model', 'Incomplete numerical control search',
                'Local model may differ from nonlinear or physical execution'],
            discriminating_checks=['Compare starts and solver termination at the same model and budget',
                'Compare fixed control and separately reoptimized controls after a supported structural perturbation',
                'Compare this replay with compatible nonlinear or recorded execution'],
            unsupported_inferences=['Global optimality', 'Structural necessity', 'Physical task acceptance',
                'Envelope gradient or regional descent guarantee'])
        return result
    except (ValueError, FloatingPointError, np.linalg.LinAlgError) as exc:
        result['reason'] = str(exc)
        return result
    finally:
        result['kernel_elapsed_s'] = time.perf_counter()-started
