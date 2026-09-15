"""Algorithm-neutral ask/tell driver; Host owns evaluation and request identity."""
from schemas.platform import EvaluationResult, Objective, Payload
from tools.platform_store import plain
from tools.state_io import digest


def score(evaluation, objectives):
    evaluation = EvaluationResult.model_validate(evaluation)
    if len(objectives) != 1:
        raise ValueError('MULTIOBJECTIVE_RANKING_ADAPTER_REQUIRED')
    if evaluation.validity != 'valid':
        return None
    objective = Objective.model_validate(objectives[0])
    metric = next((m for m in evaluation.metrics if m.name == objective.metric), None)
    if metric is None or metric.units != objective.units:
        raise ValueError('METRIC_MISSING_OR_UNIT_MISMATCH')
    return metric.value if objective.direction == 'minimize' else -metric.value


def rank(evaluations, objectives):
    parsed = [EvaluationResult.model_validate(e) for e in evaluations]
    if len({e.comparison_identity for e in parsed}) > 1:
        raise ValueError('INCOMPARABLE_TASK_INSTANCE_BACKEND_OR_MODEL')
    rows = [(score(e, objectives), e) for e in parsed]
    return [plain(e) for s, e in sorted((r for r in rows if r[0] is not None), key=lambda r: r[0])]


def run_search(host):
    inp = host.store.session(host.run_id)['snapshot']['input']
    binding = inp['policy']['search']
    if binding is None:
        raise ValueError('SEARCH_NOT_CONFIGURED')
    definition, parameters = host.reg.bind(binding, 'search')
    if len(inp['task']['objectives']) != 1 and not definition.capabilities.get('multiobjective'):
        raise ValueError('MULTIOBJECTIVE_SEARCH_ADAPTER_REQUIRED')
    algorithm = definition.resolve()(parameters)
    saved = host.store.session(host.run_id)['state'].get('search')
    if saved:
        algorithm.restore(host.reg.parse(saved['algorithm']).model_dump(mode='json'))
    else:
        saved = dict(algorithm=plain(algorithm.save()), pending=None, trials=[])
    while not algorithm.stopped():
        if saved['pending'] is None:
            saved['pending'] = dict(index=len(saved['trials']), candidate=algorithm.propose())
            _save(host, saved)
        pending = saved['pending']
        prefix = 'search-' + str(pending['index'])
        simulation = host.invoke(dict(request_id=prefix + '-simulation', tool_id='simulation.run',
            arguments=dict(candidate_id=prefix, changes=pending['candidate']), reason='搜索候选', cache='reuse'))
        if simulation['execution_status'] != 'completed':
            return dict(status=simulation['execution_status'], pending=pending, trials=saved['trials'])
        evaluation = host.invoke(dict(request_id=prefix + '-evaluation', tool_id='evaluation.run',
            arguments=dict(result=simulation['output']), reason='固定任务评价器评价候选'))
        if evaluation['execution_status'] != 'completed':
            return dict(status=evaluation['execution_status'], pending=pending, trials=saved['trials'])
        result = EvaluationResult.model_validate(host.store.artifact(evaluation['output']))
        scalar = score(result, inp['task']['objectives'])
        algorithm.feedback(scalar)
        saved['trials'].append(dict(candidate=pending['candidate'], evaluation=evaluation['output'], score=scalar))
        saved.update(algorithm=plain(algorithm.save()), pending=None)
        _save(host, saved)
    return dict(status='completed', trials=saved['trials'], algorithm=saved['algorithm'])


def _save(host, saved):
    host.reg.parse(saved['algorithm'])
    with host.store.transaction() as db:
        state = host.store.session(host.run_id, db)['state']
        state['search'] = saved
        host.store.update_state(db, host.run_id, state)
