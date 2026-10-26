"""Count admission and stage settlement over the existing transactional ledger."""
from tools.platform_store import plain


def backend_capacity(host, db=None, *, evaluation_run=None):
    """Protect each newly admitted PPO stage's evaluation in the shared ledger."""
    s=host.store.session(host.run_id,db)['state']
    held=sum(bool(e.get('evaluation_reserved')) for name,e in s.get('rl_runs',{}).items() if name!=evaluation_run)
    return max(0,host.store.remaining(db=db)['remaining']['backend_solves']-held)


def reserve_evaluation(host, current, db, *, training=False, evaluation_run=None):
    """Invoked inside the existing operation reservation transaction."""
    if not current['spec'].get('reserve_rl_evaluation'):return
    needed=2 if training else 1
    if backend_capacity(host,db,evaluation_run=evaluation_run)<needed:
        raise ValueError('TRAINING_AND_RESERVED_EVALUATION_MUST_FIT_ATOMICALLY')
    entries=current.get('rl_runs',{}).values()
    if training and sum(e['evaluations']+bool(e.get('evaluation_reserved')) for e in entries)>=current['spec']['rl_limits']['evaluation_episodes']:
        raise ValueError('ALL_RL_EVALUATION_CAPACITY_USED_OR_RESERVED')
    if evaluation_run:current['rl_runs'][evaluation_run]['evaluation_reserved']=False


def require_guidance(host, hypothesis):
    from tools.research.state import state
    s=state(host)
    if not s['spec'].get('require_task_guidance') or s.get('charged_starts',0):return
    reads=s.get('guidance_reads',[])
    if (not hypothesis.strip() or s.get('holding_diagnostic_reference') not in reads
            or not any(r in reads for r in s.get('task_math_references',[]))):
        raise ValueError('FIRST_EXPERIMENT_REQUIRES_PUBLIC_HISTORY_AND_TASK_MATH_READS_AND_FALSIFIABLE_HYPOTHESIS')


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
        (s['spec'].get('budget_semantics',{}).get('mode')=='count'
            and s['spec'].get('mode')!='engineering_investigation' and not science_fits(host)))


def decision_budget(host):
    """Derived counts only; the next Provider request is charged before its tools."""
    from tools.research.state import state
    s=state(host);remaining=host.store.remaining()['remaining'];b=s['spec']['budgets']
    total=remaining['model_calls'];reserve=b['protected_provider_requests']
    active=protected(host)
    from tools.research.reporter import current_reports
    reporter_used=sum(e['kind']=='r3_request' and host.store.artifact(e['outputs'][0]).get('purpose')=='reporter'
        for e in host.store.events(host.run_id))
    reporter_pending=sum(v['interpretation_status']=='deferred' for _,v in current_reports(host))
    public_total=remaining['tool_calls'];public_reserve=b.get('protected_public_operations',0)
    native=[(r,v) for r in s.get('analysis_results',[]) if (v:=host.store.artifact(r)).get('requested_operation',{}).get('model_source')=='mujoco']
    native_costs=[(r,v['native_dynamics']['cost']) for r,v in native if v.get('native_dynamics',{}).get('cost')]
    return dict(public_operation_budget=dict(remaining_total=public_total,reserved_for_closeout=public_reserve,
            available_for_exploration=max(0,public_total-public_reserve),
            scope='Shared ledger includes public requests and charged child operations; a scientific action may cost multiple operations.'),
        provider_budget=dict(remaining_total=total,reserved_for_closeout=reserve,
        reporter_requests_used=reporter_used,pending_reporter_requests_upper_bound=reporter_pending,
        science_capable_main_requests=0 if active else max(0,total-reserve-1),
        science_capable_after_pending_reporters=0 if active else max(0,total-reserve-1-reporter_pending),
        supervisor_review_due=not active and total-reserve-1<=4+reporter_pending,
        supervisor_rule='Review finite authorized addendum at a verified settled boundary before protection/STOP; no Agent reset. Reporter shares this total.',
        available_for_exploration=max(0,total-reserve),
        next_request_exploration_remaining=max(0,total-reserve-1),
        exploration_after_additional_read_requests={str(n):max(0,total-reserve-1-n) for n in (1,3,5)}),
        science_budget=dict(remaining_physical=backend_capacity(host),
            owning_study=host.run_id,
            charged_mathematical_evaluations=s.get('mathematical_evaluations',0),
            remaining_mathematical=max(0,b['mathematical_evaluations']-s.get('mathematical_evaluations',0)),
            remaining_full_replays=max(0,(s['spec'].get('physical_replay_limit') if s['spec'].get('physical_replay_limit') is not None else b['physical_launches'])-s.get('physical_replay_launches',0)),
            native=dict(per_request_control_limits=s['spec'].get('native_control_limits'),
                accounting_scope='Current Study registered analysis_results only; imported historical results and proposed actions are excluded.',
                recorded_rollouts=sum(v['rollouts'] for _,v in native_costs if v.get('rollouts') is not None),
                recorded_physics_steps=sum(v['physics_steps'] for _,v in native_costs if v.get('physics_steps') is not None),
                latest_cost_query=dict(reference=native_costs[-1][0],view='full',pointer='/native_dynamics/cost') if native_costs else None,
                attempts_without_cost_record=len(native)-len(native_costs),
                cost_record_complete=all(all(v.get(k) is not None for k in ('rollouts','physics_steps')) for _,v in native_costs) and len(native)==len(native_costs),
                integration_scope='Recorded physics_steps already includes prefix reconstruction and suffix rollouts. Callback counts describe these rollouts, not additional integrations. Independent full replay is separate; zero independent physical evaluations does not imply zero native integration.',
                allowance_scope='Recorded totals are known subtotals; incomplete records leave actual total unknown. Native analysis shares remaining_mathematical; per-request limits are not a separate cumulative allowance. Missing costs are unknown, not zero.'),
            any_scientific_route_fits=science_fits(host) and not (active or total-1<=reserve)),
        closeout=dict(active=active,next_request_will_protect=active or total-1<=reserve,
            reason='Existing success/count/resource protection' if active else None))


def science_fits(host):
    """Route counts, rather than the clock, decide when only closeout remains."""
    from tools.research.state import state
    s=state(host)
    spec=s['spec']
    capabilities=set(spec.get('capabilities',[]))
    b=spec['budgets']
    remaining=host.store.remaining()['remaining']
    backend=backend_capacity(host)
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
    actions=['select'] if s.get('spec',{}).get('research_decisions') and s.get('success_gate') and not s.get('selected') else ['stop','select']
    if s['spec'].get('mode')=='engineering_investigation':actions=['stop']
    if s.get('selected'):
        from tools.research.feedback import confirmation_progress
        progress=confirmation_progress(host)
        if progress['remaining'] and not (progress['failures'] or progress['invalid_executions']):actions.append('confirm')
    return dict(research_plan=actions,
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


def capacity(host, requested=1, confirmation=False, *, root_operation=False, candidate=None, route='nmpc'):
    from tools.research.state import state
    s = state(host)
    remaining = host.store.remaining()['remaining']
    reserve = 0 if confirmation else repetition_reserve(s)
    slots = s['spec']['nmpc_limits']['executions'] - s.get('nmpc_launches', 0)
    if route=='fixed_tension':
        limit=s['spec'].get('physical_replay_limit')
        slots=(s['spec']['budgets']['physical_launches'] if limit is None else limit)-s.get('physical_replay_launches',0)
    operations = max(0, remaining['tool_calls'] - (0 if confirmation else s['spec']['budgets'].get('protected_public_operations', 0)))
    # Fixed replay has one public Plan and no charged child tool calls. Inside
    # that admitted Plan, its current public call has already been paid.
    operation_slots=operations+int(not root_operation) if route=='fixed_tension' else (operations-int(root_operation))//3
    fit = max(0, min(requested, slots-reserve, backend_capacity(host)-reserve, operation_slots))
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
