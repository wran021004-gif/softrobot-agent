"""Count admission and stage settlement over the existing transactional ledger."""
from tools.platform_store import plain


def protected(host):
    from tools.research.state import state
    s = state(host)
    if s['spec'].get('mode') == 'engineering_numerical':
        return bool(s.get('success_gate'))
    remaining = host.store.remaining()['remaining']
    b = s['spec']['budgets']
    return bool(s.get('success_gate') or s.get('count_closeout') or
        remaining['model_calls'] <= b['protected_provider_requests'] or
        remaining['tool_calls'] <= b.get('protected_public_operations', 0) or
        (s['spec'].get('budget_semantics',{}).get('mode')=='count' and not science_fits(host)))


def science_fits(host):
    """Route counts, rather than the clock, decide when only closeout remains."""
    from tools.research.state import state
    s=state(host)
    spec=s['spec']
    capabilities=set(spec.get('capabilities',[]))
    b=spec['budgets']
    remaining=host.store.remaining()['remaining']
    backend=remaining['backend_solves']
    runs=s.get('rl_runs',{})
    limits=spec['rl_limits']
    evaluations=limits['evaluation_episodes']-sum(e['evaluations'] for e in runs.values())
    return bool(
        ('analysis' in capabilities and s.get('mathematical_evaluations',0)<b['mathematical_evaluations']) or
        ('nmpc' in capabilities and backend>=1 and s.get('nmpc_launches',0)<spec['nmpc_limits']['executions']) or
        ('physical_replay' in capabilities and backend>=1 and s.get('physical_replay_launches',0)<
            (spec.get('physical_replay_limit') if spec.get('physical_replay_limit') is not None else b['physical_launches'])) or
        ('rl' in capabilities and evaluations>0 and ((backend>=2 and
            s.get('admitted_training_stages',len(runs))<limits['training_stages']) or (backend>=1 and runs))) or
        (s.get('local_solves',0)<b['local_solves'] and any(host.store.artifact(r).get('status')=='evaluated' for r in s.get('results',[]))) or
        ('mathematics' in capabilities and s.get('offline_nlp',0)<b['offline_nlp']) or
        ('replay' in capabilities and s.get('bdf_replays',0)<b['bdf_replays']))


def closeout_operations(host):
    from tools.research.state import state
    s = state(host)
    return dict(research_plan=['stop', 'select'],
        research_rl=[a for a in ('status', 'stop', 'evaluate') if s.get('rl_runs') and (a != 'evaluate' or not s.get('success_gate'))])


def admit_closeout(host, name, value):
    if protected(host) and name in ('research_plan', 'research_rl'):
        field = 'action' if name == 'research_plan' else 'operation'
        if value.get(field) not in closeout_operations(host)[name]:
            raise ValueError('PROTECTED_CLOSEOUT_REQUIRES_EVIDENCE_SELECTION_OR_STOP')


def charge_start(s):
    """Physical dispatch statistics are independent of admitted training stages."""
    s['charged_starts'] = s.get('charged_starts', 0) + 1


def allowance(s):
    return s['spec']['nmpc_execution_cap_s']


def repetition_reserve(s):
    return s['spec']['confirmation']['fresh_independent_repetitions']


def nmpc_timing(host, candidate=None):
    from tools.research.state import state
    s = state(host)
    cap = allowance(s)
    return dict(available=True, cap_s=cap, reservation_s=cap,
        complete_execution_s=None, first_use_available=True, evidence_sources=[],
        reason='Finite execution count and physical horizon; elapsed time is measured only',
        design_feasibility='not assessed by admission')


def capacity(host, requested=1, confirmation=False, *, root_operation=False, candidate=None):
    from tools.research.state import state
    s = state(host)
    remaining = host.store.remaining()['remaining']
    reserve = 0 if confirmation else repetition_reserve(s)
    slots = s['spec']['nmpc_limits']['executions'] - s.get('nmpc_launches', 0)
    operations = max(0, remaining['tool_calls'] - (0 if confirmation else s['spec']['budgets'].get('protected_public_operations', 0)))
    fit = max(0, min(requested, slots-reserve, remaining['backend_solves']-reserve, (operations-int(root_operation))//3))
    return dict(requested=requested, admitted=fit, internal_launches=fit,
        numerical_reservation_s=0., confirmation_launch_reserve=reserve,
        per_execution_s=allowance(s), remaining_numerical_s=None, remaining_activity_s=None)


def admit_stage(s):
    """Called in the same Store transaction as its durable operation admission."""
    admitted = s.get('admitted_training_stages', len(s.get('rl_runs', {})))
    if admitted >= s['spec']['rl_limits']['training_stages']:
        raise ValueError('TRAINING_STAGE_LIMIT_EXHAUSTED')
    s['admitted_training_stages'] = admitted + 1


def stage_usage(s):
    entries = list(s.get('rl_runs', {}).values())
    statuses = [e.get('status', {}) for e in entries]
    upper = sum(e.get('consumed', {}).get('attempted_actions', 0) for e in statuses)
    uncertain = any(e.get('consumption_uncertain') for e in statuses)
    lower = sum((e.get('known_consumption_lower_bound') or {}).get('attempted_actions', 0)
        if e.get('consumption_uncertain') else e.get('consumed', {}).get('attempted_actions', 0) for e in statuses)
    return dict(admitted=s.get('admitted_training_stages', len(entries)),
        limit=s['spec']['rl_limits'].get('training_stages', s['spec']['rl_limits'].get('training_runs')),
        actual_actions=None if uncertain else upper,
        verified_actions_lower_bound=lower, accounted_actions_upper_bound=upper,
        actual_active_seconds=sum(e.get('status', {}).get('consumed', {}).get('active_seconds', 0) for e in entries),
        outstanding=[dict(run_id=k, reservation=e['active_reservation']) for k,e in s.get('rl_runs', {}).items() if e.get('active_reservation')])


def observe_pass(host, reference):
    """Persist a qualifying backend pass before any subsequent science admission."""
    from tools.research.state import state, update
    from tools.research.feedback import result_view
    s = state(host)
    from tools.research.design import final_fidelity_matches
    result=host.store.artifact(reference)
    if not final_fidelity_matches(s['spec'],host.store.artifact(result['candidate'])):
        return
    view = result_view(host, reference)
    if view['fresh_current_study'] and view['complete'] and view['passed']:
        import math
        from tools.research_tasks import task_adapter
        limits = task_adapter(host.store.artifact(view['candidate'])['configuration']).ranking_limits()
        result = host.store.artifact(reference)
        if view['controller_route'] in ('nmpc','fixed_tension'):
            metrics = (result.get('acceptance') or {}).get('metrics', {})
            if any(not isinstance(metrics.get(k), (float, int)) or not math.isfinite(metrics[k]) or metrics[k] > limit for k, limit in limits.items()):
                return
        else:
            keys = ('terminal_position_error_m', 'holding_max_position_error_m', 'holding_max_speed_m_s')
            if any(not e.get('holding_coverage_complete') or any(not isinstance(e.get(k), (float, int)) or not math.isfinite(e[k]) or e[k] > limit for k,limit in zip(keys,limits.values())) for e in result['episodes']):
                return
        if view['controller_route'] == 'rl' and (not view['controller'].get('checkpoint') or not view['controller'].get('policy_sha256')):
            return
        if not s.get('success_gate'):
            update(host, success_gate=dict(evidence=plain(reference), candidate=view['candidate'],
                engineering=s['spec'].get('mode') == 'engineering_numerical',
                observed_task_pass=True, model_selection_complete=False))


def engineering_closeout(host, reason):
    from tools.research.state import state, update, save
    import time
    s = state(host)
    if s['research_status'] == 'stopped':
        return
    ref = save(host, dict(kind='engineering_count_budget_closure', reason=reason,
        model_stop=False, selected=s.get('selected'), observed_pass=s.get('success_gate')),
        'engineering_count_budget_closure')
    update(host, research_status='stopped', final_disposition=ref, closed_unix=time.time())
