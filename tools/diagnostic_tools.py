"""Deterministic evidence arithmetic. No retuning, causal inference or gate override."""
import math
from schemas.tool_result import ToolResult


def _number(value, *, nonnegative=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Expected finite numeric evidence')
    if nonnegative and value < 0:
        raise ValueError('Expected nonnegative evidence')
    return value


def _vector(value, size=None, positive=False):
    if not isinstance(value, (tuple, list)) or not value or (size is not None and len(value) != size):
        raise ValueError('Missing or inconsistent vector evidence')
    for v in value:
        _number(v)
        if positive and v <= 0:
            raise ValueError('Expected positive lengths')
    return value


def _count(value):
    if type(value) is not int or value < 0:
        raise ValueError('Expected nonnegative integer count')
    return value


def _boolean(value):
    if type(value) is not bool:
        raise ValueError('Expected boolean observation')
    return value


def _result(name, paths, metrics=None, error=None):
    return ToolResult(tool=name, status='fail' if error else 'pass', failure_code='UNKNOWN' if error else None,
                      metrics={'evidence_status': 'unavailable' if error else 'available',
                               'failure_attribution': 'UNKNOWN', **(metrics or {})},
                      artifacts={'evidence_paths': list(paths)}, message=str(error) if error else None)


def compare_model_sim(model_result: ToolResult, simulation_result: ToolResult, task, *, evidence_paths=()) -> ToolResult:
    """Compare a same-run M1 prediction with actual tip; no approved mismatch threshold."""
    try:
        m, s = model_result.metrics, simulation_result.metrics
        context = m['comparison_context']
        if (not isinstance(context, dict) or context != s['comparison_context']
                or any(not isinstance(context.get(k), str) or not context[k]
                       for k in ('run_id', 'task_hash', 'environment_hash', 'robot_ir_hash', 'coordinate_frame'))):
            raise ValueError('Insufficient evidence: matching Harness input/run identities required')
        if model_result.status != 'pass' or 'task_success' not in s:
            raise ValueError('Insufficient evidence: completed model and simulation required')
        predicted, actual = _vector(m['predicted_tip_m'], 3), _vector(s['tip_position_m'], 3)
        for result in (m, s):
            if list(_vector(result['target_position_m'], 3)) != list(task.target_m):
                raise ValueError('Incomparable task targets')
        commands = _vector(m['tendon_target_lengths_m'], positive=True)
        if list(commands) != list(_vector(s['tendon_target_lengths_m'], len(commands), positive=True)):
            raise ValueError('Model and executed commands differ')
        # On instrumented runs verify commands were held throughout, not just final.
        execution = s.get('execution_evidence')
        if execution:
            rows = execution['actuators']
            if len(rows) != len(commands) or any(r['active_samples'] != execution['steps_completed']
                    or r['command_min_m'] != c or r['command_max_m'] != c for r, c in zip(rows, commands)):
                raise ValueError('Execution did not hold the model command throughout')
        pe, se = math.dist(predicted, task.target_m), math.dist(actual, task.target_m)
        _number(pe)
        _number(se)
        for recorded, measured in ((m['predicted_position_error_m'], pe), (s['position_error_m'], se)):
            if not math.isclose(_number(recorded, nonnegative=True), measured, abs_tol=1e-12, rel_tol=1e-10):
                raise ValueError('Recorded error contradicts tip/target evidence')
        if (_boolean(m['model_task_success']) != (pe <= task.position_error_max_m)
                or _boolean(s['task_success']) != (se <= task.position_error_max_m)
                or s['position_error_max_m'] != task.position_error_max_m):
            raise ValueError('Recorded task decision contradicts canonical metric')
        metrics = {'predicted_tip_m': list(predicted), 'predicted_position_error_m': pe,
                   'actual_tip_m': list(actual), 'actual_position_error_m': se,
                   'tip_discrepancy_m': _number(math.dist(predicted, actual)),
                   'model_predicts_tolerance_failure': pe > task.position_error_max_m,
                   'mismatch_criterion': None,
                   'comparison_context': context,
                   'unresolved': 'PHYSICS_ASSUMPTION_REQUIRED: Human-approved mismatch criterion absent; discrepancy alone does not establish MODEL_MISMATCH.'}
        return _result('compare_model_sim', evidence_paths, metrics)
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as exc:
        return _result('compare_model_sim', evidence_paths, error=exc)


def check_actuator_limits(simulation_result: ToolResult, *, evidence_paths=()) -> ToolResult:
    try:
        evidence = simulation_result.metrics['execution_evidence']
        steps = _count(evidence['steps_completed'])
        dt = _number(evidence['timestep_s'])
        if steps == 0 or dt <= 0 or not evidence['actuators']:
            raise ValueError('No observed actuator samples')
        if not _boolean(evidence['numerics']['actuator_force_all_finite']):
            raise ValueError('Nonfinite force evidence cannot establish force-limit statistics')
        rows = []
        for i, row in enumerate(evidence['actuators']):
            if row['index'] != i or row['tendon_index'] != i or not isinstance(row['name'], str) or not row['name']:
                raise ValueError('Invalid actuator identity/order')
            lo, hi = _vector(row['force_range_n'], 2)
            if lo >= 0 or hi != 0:
                raise ValueError('Diagnostic supports V1 pull-only force range [negative, 0]')
            limited = _boolean(row['force_limited'])
            count = _count(row['active_samples'])
            lower, upper = _count(row['lower_limit_samples']), _count(row['upper_limit_samples'])
            if count == 0 or count > steps or lower + upper > count or (not limited and (lower or upper)):
                raise ValueError('Missing or inconsistent active sample counts')
            peak = _number(row['peak_abs_force_n'], nonnegative=True)
            minimum, maximum = _number(row['min_force_n']), _number(row['max_force_n'])
            if (minimum > maximum or peak != max(abs(minimum), abs(maximum))
                    or (limited and (minimum < lo or maximum > hi))
                    or (limited and ((minimum == lo) != bool(lower) or (maximum == hi) != bool(upper)))):
                raise ValueError('Contradictory force extrema/counts')
            rows.append({'index': i, 'name': row['name'], 'force_limited': limited, 'force_range_n': [lo, hi],
                         'observed_peak_abs_force_n': peak, 'max_pull_limit_reached': bool(lower),
                         'max_pull_limit_samples': lower, 'active_samples': count,
                         'max_pull_limit_fraction': lower / count,
                         'max_pull_limit_sampled_duration_s': _number(lower * dt),
                         'upper_zero_bound_samples': upper, 'upper_zero_bound_fraction': upper / count})
        return _result('check_actuator_limits', evidence_paths,
                       {'actuators': rows, 'max_pull_limit_observed': any(r['max_pull_limit_reached'] for r in rows),
                        'supported_evidence_category': 'ACTUATOR_LIMIT' if any(r['max_pull_limit_reached'] for r in rows) else None,
                        'limitation': 'Counts concern sampled active steps; reaching the 0 N no-push bound does not prove active clipping, cable slack or maximum-pull saturation. No causal attribution.'})
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as exc:
        return _result('check_actuator_limits', evidence_paths, error=exc)


def check_tendon_tracking(simulation_result: ToolResult, *, evidence_paths=()) -> ToolResult:
    try:
        m = simulation_result.metrics
        commands = _vector(m['tendon_target_lengths_m'], positive=True)
        lengths = _vector(m['final_tendon_lengths_m'], len(commands), positive=True)
        controls = _vector(m['actuator_controls'], len(commands), positive=True)
        if list(commands) != list(controls):
            raise ValueError('Applied controls disagree with recorded targets')
        rows = [{'index': i, 'name': f'tendon_{i}', 'target_length_m': command, 'actual_length_m': actual,
                 'signed_error_m': actual - command, 'absolute_error_m': abs(actual - command),
                 'relative_error': _number(abs(actual - command) / command)}
                for i, (command, actual) in enumerate(zip(commands, lengths))]
        return _result('check_tendon_tracking', evidence_paths,
                       {'tendons': rows, 'max_absolute_error_m': max(r['absolute_error_m'] for r in rows),
                        'tracking_acceptance_threshold': None,
                        'limitation': 'Final length differences only; no approved tracking tolerance or causal controller/actuator verdict.'})
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as exc:
        return _result('check_tendon_tracking', evidence_paths, error=exc)


def inspect_numerics(simulation_result: ToolResult, *, evidence_paths=()) -> ToolResult:
    try:
        m = simulation_result.metrics
        execution = m['execution_evidence']
        n = execution['numerics']
        completed, requested = _count(execution['steps_completed']), _count(execution['steps_requested'])
        if not requested or completed > requested:
            raise ValueError('Inconsistent step counts')
        if not completed:
            raise ValueError('Insufficient evidence: no completed state observations')
        finite = {key: _boolean(n[key]) for key in ('qpos_all_finite', 'qvel_all_finite',
                                                   'actuator_force_all_finite', 'tendon_length_all_finite')}
        warnings = n['warnings']
        if not isinstance(warnings, dict) or not warnings:
            raise ValueError('Missing simulator warning counters')
        warning_count = sum(_count(v) for v in warnings.values())
        time_anomaly = _boolean(n['time_advance_anomaly'])
        anomalies = [key for key, value in finite.items() if not value]
        if warning_count:
            anomalies.append('simulator_warnings')
        if time_anomaly:
            anomalies.append('time_advance_anomaly')
        if simulation_result.failure_code in ('NONFINITE_STATE', 'PHYSICS_ERROR'):
            anomalies.append(simulation_result.failure_code)
        return _result('inspect_numerics', evidence_paths,
                       {**finite, 'max_abs_qpos_rad': _number(n['max_abs_qpos_rad'], nonnegative=True),
                        'max_abs_qvel_rad_s': _number(n['max_abs_qvel_rad_s'], nonnegative=True),
                        'warning_counts': warnings, 'anomaly_indicators': anomalies,
                        'steps_completed': completed, 'steps_requested': requested,
                        'termination_code': simulation_result.failure_code,
                        'observation_complete': completed == requested,
                        'qvel_threshold_status': 'unavailable: no approved anomaly threshold',
                        'stability_validated': False,
                        'limitation': 'Sanity observations only; finite states and absent warnings do not establish stability, convergence, or physical validity.'})
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as exc:
        return _result('inspect_numerics', evidence_paths, error=exc)


def save_diagnostic_summary(run, model_result, simulation_result, task):
    """Harness-only persistence through its existing artifact service."""
    from tools.artifact_tools import save_tool_result
    paths = ('mujoco_result.json', 'robot.xml', 'run_settings.yaml')
    results = [compare_model_sim(model_result, simulation_result, task,
                                 evidence_paths=('model_result.json', 'mujoco_result.json', 'task.yaml', 'robot_ir.yaml'))]
    for tool in (check_actuator_limits, check_tendon_tracking, inspect_numerics):
        results.append(tool(simulation_result, evidence_paths=paths))
    for result in results:
        save_tool_result(run, result.tool + '.json', result)
    summary = {
        'task_gate': 'PASS' if simulation_result.metrics.get('task_success') is True else
                     ('FAIL' if simulation_result.metrics.get('task_success') is False else 'not_run'),
        'confirmed_outcome': simulation_result.failure_code or simulation_result.status,
        'failure_attribution': 'UNKNOWN',
        'diagnostics': {r.tool: r.model_dump(mode='json') for r in results},
        'unresolved': ['Human-approved model mismatch criterion', 'Human-approved tracking/anomaly thresholds',
                       'Material/EI, damping and tendon/actuator physical laws and calibration',
                       'Causal explanation of observed discrepancy; diagnostic observations are not causal proof'],
    }
    run.save('diagnostic_summary.json', summary)
    return summary
