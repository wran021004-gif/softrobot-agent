"""Registered reach task semantics and fixed sampled position evaluator."""
import math
from schemas.platform import SignalSpec,EvaluationResult,Metric,ConstraintResult
from extensions.reference.contracts import Empty
def reach_task(task, reg):
    from extensions.reference.contracts import ReachGoal, ReachEvaluation
    if type(reg.parse(task.goal)) is not ReachGoal or type(reg.parse(task.evaluator.parameters)) is not ReachEvaluation:
        raise ValueError('REACH_GOAL_OR_EVALUATOR_CONTRACT_MISMATCH')
    if task.evaluator.extension_id != 'evaluate.reach':
        raise ValueError('REACH_EVALUATOR_REQUIRED')
    required = [SignalSpec(name='tip_position', entity='tip', dimension=3, units='m', frame='world', phase=phase)
                for phase in ('post_step', 'sampled_state')]
    if not any(spec in task.observations for spec in required):
        raise ValueError('REQUIRED_SIGNAL: tip_position, tip, dimension=3, m, world, declared state phase')
    if task.environment.contract!='experiment.assembly':
        raise ValueError('REACH_ENVIRONMENT_ADAPTER_REQUIRED')
    expected_initializers = ('initialize.family',)
    if task.initializer.extension_id not in expected_initializers:
        raise ValueError('REACH_INITIALIZER_ADAPTER_REQUIRED')
    if any(o.metric != 'position_error' or o.units != 'm' for o in task.objectives):
        raise ValueError('EVALUATOR_METRIC_OR_UNIT_UNAVAILABLE')
    return Empty()

def evaluate_signals(task, result, source, reg, comparison_identity, mode):
    if result.solver_status != 'completed':
        return EvaluationResult(validity='incomplete', task_success=None, metrics=[], constraints=[], source=source,
            evaluator=task.evaluator.extension_id, comparison_identity=comparison_identity, reason='SOLVER_NOT_COMPLETE')
    signal_name = 'tip_position' if mode == 'reach' else 'tendon_length'
    spec = next(s for s in task.observations if s.name == signal_name)
    signal = next((s for s in result.signals if s.spec == spec), None)
    if signal is None or not signal.times_s or abs(signal.times_s[-1] - task.timing.duration_s) > 1e-8:
        return EvaluationResult(validity='incomplete', task_success=None, metrics=[], constraints=[], source=source,
            evaluator=task.evaluator.extension_id, comparison_identity=comparison_identity, reason='MISSING_SIGNAL_OR_DURATION')
    first = 0 if signal.spec.phase == 'sampled_state' else 1
    if any(abs(t - (i + first) * task.timing.sample_period_s) > 1e-8 for i, t in enumerate(signal.times_s)):
        return EvaluationResult(validity='incomplete', task_success=None, metrics=[], constraints=[], source=source,
            evaluator=task.evaluator.extension_id, comparison_identity=comparison_identity, reason='INCOMPLETE_SAMPLING')
    goal = reg.parse(task.goal)
    params = reg.parse(task.evaluator.parameters)
    if mode == 'reach':
        value = math.dist(signal.values[-1], goal.target_m)
        metrics, limit = [Metric(name='position_error', value=value, units='m')], params.tolerance_m
    else:
        errors = [abs(v[0] - goal.length_m) for t, v in zip(signal.times_s, signal.values)
                  if task.sampling.window_s[0] - 1e-9 <= t <= task.sampling.window_s[1] + 1e-9]
        if not errors:
            raise ValueError('EMPTY_EVALUATION_WINDOW')
        value, limit = max(errors), params.max_deviation_m
        metrics = [Metric(name='max_deviation', value=value, units='m'),
                   Metric(name='rms_deviation', value=math.sqrt(sum(e * e for e in errors) / len(errors)), units='m')]
    return EvaluationResult(validity='valid', task_success=value <= limit, metrics=metrics,
        constraints=[ConstraintResult(name='task_bound', satisfied=value <= limit, observed=value, limit=limit, units='m')],
        source=source, evaluator=task.evaluator.extension_id, comparison_identity=comparison_identity)

def evaluate_reach(task, result, source, reg, identity):
    return evaluate_signals(task, result, source, reg, identity, 'reach')

