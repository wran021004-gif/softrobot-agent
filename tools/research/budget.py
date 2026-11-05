"""Count admission and stage settlement over the existing transactional ledger."""
from tools.platform_store import plain
from contextlib import contextmanager


def extend_provider_requests(host, approval):
    """Local user addendum to the original Store; never a Main tool or a send.

    Preserves every receipt and scientific limit. Rebinding and the existing
    identity-bound research authorization are still required before continuation.
    """
    from copy import deepcopy
    from tools.state_io import digest
    from tools.platform_store import ROOT,encode
    from tools.research.provider import pending
    identity=digest(approval)
    with host.store.transaction() as db:
        session=host.store.session(host.run_id,db);current=session['state'];spec=current['spec']
        for ref in current.get('provider_request_extensions',[]):
            if host.store.artifact(ref,db=db)['approval_identity']==identity:
                return dict(already_applied=True,reference=ref)
        policy=spec.get('provider_request_extension_policy',{})
        scope=approval.get('scope',{});extra=scope.get('additional_requests')
        limit=spec['budgets']['provider_requests']
        if (approval.get('version')!='provider_request_extension_approval_v1' or approval.get('approved') is not True or
                not approval.get('source') or approval.get('scope_identity')!=digest(scope) or
                set(scope)!={'study_id','resolved_identity','previous_request_limit','additional_requests'} or
                scope['study_id']!=host.run_id or scope['resolved_identity']!=spec['resolved_identity'] or
                scope['previous_request_limit']!=limit or type(extra) is not int or extra<=0 or
                policy.get('version')!='finite_provider_request_extension_v1'):
            raise ValueError('EXACT_USER_APPROVED_FINITE_PROVIDER_EXTENSION_REQUIRED')
        used=sum(host.store.artifact(ref,db=db)['additional_requests'] for ref in current.get('provider_request_extensions',[]))
        if extra>policy.get('maximum_requests_per_extension',policy['maximum_additional_requests']):
            raise ValueError('FROZEN_PROVIDER_EXTENSION_BATCH_CAP_EXCEEDED')
        if used+extra>policy['maximum_additional_requests']:
            raise ValueError('FROZEN_PROVIDER_EXTENSION_CAP_EXCEEDED')
        if (current.get('pending') or pending(host) or current.get('selected') or current.get('success_gate') or
                current['research_status']=='stopped' or
                db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]):
            raise ValueError('SETTLED_NONSUCCESS_BOUNDARY_REQUIRED_FOR_PROVIDER_EXTENSION')
        cfg=host.store.config(db);snapshot=deepcopy(session['snapshot'])
        if cfg['budget']['model_calls']!=limit or snapshot['input']['policy']['budget']['model_calls']!=limit:
            raise ValueError('ORIGINAL_PROVIDER_LIMIT_BINDING_MISMATCH')
        addendum=plain(host.store.put(db,dict(version='provider_request_extension_v1',approval=approval,
            approval_identity=identity,additional_requests=extra,previous_state=plain(host.store.put(db,current)),
            scientific_limits_unchanged=True,all_costs_and_failures_retained=True)))
        updated=deepcopy(spec);updated.pop('resolved_identity')
        updated['budgets']['provider_requests']=limit+extra
        updated['configuration']['policy']['budget']['model_calls']=limit+extra
        updated.setdefault('authorization_addenda',[]).append(addendum)
        updated['resolved_identity']=digest(updated)
        snapshot['input']['policy']['budget']['model_calls']=limit+extra
        snapshot_ref=host.store.put(db,snapshot)
        previous_hash=digest(cfg);cfg['budget']['model_calls']=limit+extra
        db.execute('ATTACH DATABASE ? AS authority',(str(ROOT/'runs/.platform_authorities.sqlite'),))
        changed=db.execute('UPDATE authority.grants SET config_hash=? WHERE grant_id=? AND root=? AND config_hash=?',
            (digest(cfg),cfg['grant_id'],str(host.store.root),previous_hash))
        if changed.rowcount!=1:raise ValueError('EXISTING_STORE_AUTHORITY_REQUIRED')
        db.execute("UPDATE meta SET value=? WHERE key='config'",(encode(cfg),))
        db.execute('UPDATE sessions SET snapshot=? WHERE run_id=?',(snapshot_ref.artifact_id,host.run_id))
        current.update(spec=updated,validation_extension_pending_binding=True)
        current.setdefault('provider_request_extensions',[]).append(addendum)
        host.store.update_state(db,host.run_id,current)
        host.store.event(db,host.run_id,'provider_request_extension','authorized',outputs=[addendum,snapshot_ref])
    return dict(already_applied=False,reference=addendum,request_limit=limit+extra,
        requires_committed_binding=True,requires_current_identity_research_authorization=True,provider_requests_sent=0)


def authorize_unmetered_mathematics(host, approval):
    """Apply an explicit user quota change without resetting any computation.

    Uses the existing None quota semantics. Physics, Provider limits, individual
    requests, method grants and watchdogs remain independently owned.
    """
    from copy import deepcopy
    from tools.state_io import digest
    from tools.research.provider import pending
    identity=digest(approval)
    with host.store.transaction() as db:
        current=host.store.session(host.run_id,db)['state'];spec=current['spec']
        for ref in current.get('mathematical_quota_authorizations',[]):
            if host.store.artifact(ref,db=db)['approval_identity']==identity:
                return dict(already_applied=True,reference=ref)
        scope=approval.get('scope',{});old=spec['budgets']['mathematical_evaluations']
        if (approval.get('version')!='unmetered_mathematics_approval_v1' or approval.get('approved') is not True
                or not approval.get('source') or approval.get('scope_identity')!=digest(scope)
                or set(scope)!={'study_id','resolved_identity','previous_limit','new_limit'}
                or scope['study_id']!=host.run_id or scope['resolved_identity']!=spec['resolved_identity']
                or scope['previous_limit']!=old or type(old) is not int or scope['new_limit'] is not None
                or spec['mode']!='formal_research' or 'analysis' not in spec.get('capabilities',[])):
            raise ValueError('EXACT_EXPLICIT_UNMETERED_MATHEMATICS_AUTHORIZATION_REQUIRED')
        if (current.get('pending') or pending(host) or current['pilot'].get('unconsumed_response')
                or current.get('selected') or current.get('success_gate') or current['research_status']=='stopped'
                or any(v.get('active_reservation') or v.get('status',{}).get('worker_alive',True) for v in current.get('rl_runs',{}).values())
                or db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]):
            raise ValueError('SETTLED_NONSUCCESS_BOUNDARY_REQUIRED_FOR_MATHEMATICAL_QUOTA')
        ref=plain(host.store.put(db,dict(version='unmetered_mathematics_addendum_v1',approval=approval,
            approval_identity=identity,previous_state=plain(host.store.put(db,current)),
            all_costs_and_failures_retained=True,other_limits_unchanged=True)))
        updated=deepcopy(spec);updated.pop('resolved_identity')
        updated['budgets']['mathematical_evaluations']=None
        updated.setdefault('authorization_addenda',[]).append(ref)
        updated['resolved_identity']=digest(updated)
        current.update(spec=updated,validation_extension_pending_binding=True)
        current.setdefault('mathematical_quota_authorizations',[]).append(ref)
        host.store.update_state(db,host.run_id,current)
        host.store.event(db,host.run_id,'mathematical_quota_authorization','authorized',outputs=[ref])
    return dict(already_applied=False,reference=ref,resolved_identity=updated['resolved_identity'],
        requires_committed_binding=True,requires_current_identity_research_authorization=True,provider_requests_sent=0)


def mathematical_remaining(spec, used=0):
    """None is an authorized absence of a count quota; usage is still recorded."""
    limit=spec['budgets']['mathematical_evaluations']
    return None if limit is None else max(0,limit-used)


def mathematics_fits(spec, used=0, requested=1):
    remaining=mathematical_remaining(spec,used)
    return remaining is None or remaining>=requested


def provider_allowance(host, db=None):
    """One count boundary; frozen legacy Studies retain the pre-debit margin.

    last_requests_v2 buys the current request's phase before its single debit.
    Its last N requests are closeout-only; an already bought exploration request
    retains that phase while its tools run. No extra persistent budget is used.
    """
    s=host.store.session(host.run_id,db)['state'];b=s['spec']['budgets']
    total=host.store.remaining(db=db)['remaining']['model_calls'];reserve=b['protected_provider_requests']
    current=b.get('provider_reserve_policy')=='last_requests_v2'
    phase=getattr(host,'_provider_request_phase',None) if current else None
    return dict(remaining_total=total,reserved_for_closeout=reserve,
        protected_current_request=(phase=='closeout' if phase is not None else total<=reserve),
        next_request_will_protect=total<=reserve if current else total-1<=reserve,
        science_capable_main_requests=max(0,total-reserve-(0 if current else 1)),
        request_phase=('closeout' if total<=reserve else 'exploration') if current else None)


@contextmanager
def provider_request_scope(host, phase):
    """Only the synchronous native tool call uses its paid Provider phase."""
    previous=getattr(host,'_provider_request_phase',None)
    host._provider_request_phase=phase
    try:yield
    finally:host._provider_request_phase=previous


def backend_capacity(host, db=None, *, evaluation_run=None):
    """Protect each newly admitted PPO stage's evaluation in the shared ledger."""
    s=host.store.session(host.run_id,db)['state']
    held=sum(bool(e.get('evaluation_reserved')) for name,e in s.get('rl_runs',{}).items() if name!=evaluation_run)
    remaining=host.store.remaining(db=db)['remaining']['backend_solves']
    return None if remaining is None else max(0,remaining-held)


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
        provider_allowance(host)['protected_current_request'] or
        remaining['tool_calls'] <= b.get('protected_public_operations', 0) or
        (s['spec'].get('budget_semantics',{}).get('mode')=='count'
            and s['spec'].get('mode')!='engineering_investigation' and not science_fits(host)))


def decision_budget(host):
    """Derived counts only; the next Provider request is charged before its tools."""
    from tools.research.state import state
    s=state(host);remaining=host.store.remaining()['remaining'];b=s['spec']['budgets']
    total=remaining['model_calls'];reserve=b['protected_provider_requests']
    provider=provider_allowance(host)
    active=protected(host)
    from tools.research.reporter import current_reports
    reporter_used=sum(e['kind']=='r3_request' and host.store.artifact(e['outputs'][0]).get('purpose')=='reporter'
        for e in host.store.events(host.run_id))
    reporter_pending=sum(v['interpretation_status']=='deferred' for _,v in current_reports(host))
    public_total=remaining['tool_calls'];public_reserve=b.get('protected_public_operations',0)
    native=[(r,v) for r in s.get('analysis_results',[]) if (v:=host.store.artifact(r,paths=(
        'requested_operation.model_source','status','native_dynamics.cost','nonlinear_response.cost',
        'native_progress.cost','native_diagnostic.cost','structure_research.cost'))).get('requested_operation',{}).get('model_source')=='mujoco']
    native_costs=[]
    for r,v in native:
        for key in ('native_dynamics','nonlinear_response','structure_research','native_progress','native_diagnostic'):
            cost=(v.get(key) or {}).get('cost')
            if cost:
                native_costs.append((r,cost,'/'+key+'/cost',
                    key in ('native_dynamics','nonlinear_response','structure_research') and v.get('status') in ('computed','not_comparable')))
                break
    return dict(public_operation_budget=dict(remaining_total=public_total,reserved_for_closeout=public_reserve,
            available_for_exploration=max(0,public_total-public_reserve),
            scope='Shared ledger includes public requests and charged child operations; a scientific action may cost multiple operations.'),
        provider_budget=dict(remaining_total=total,reserved_for_closeout=reserve,
        reporter_requests_used=reporter_used,pending_reporter_requests_upper_bound=reporter_pending,
        science_capable_main_requests=0 if active else provider['science_capable_main_requests'],
        science_capable_after_pending_reporters=0 if active else max(0,provider['science_capable_main_requests']-reporter_pending),
        supervisor_review_due=not active and provider['science_capable_main_requests']<=4+reporter_pending,
        supervisor_rule='Review finite authorized addendum at a verified settled boundary before protection/STOP; no Agent reset. Reporter shares this total.',
        available_for_exploration=max(0,total-reserve),
        next_request_exploration_remaining=max(0,total-reserve-1),
        exploration_after_additional_read_requests={str(n):max(0,total-reserve-1-n) for n in (1,3,5)}),
        science_budget=dict(remaining_physical=backend_capacity(host),
            owning_study=host.run_id,
            charged_mathematical_evaluations=s.get('mathematical_evaluations',0),
            mathematical_quota_scope='No cumulative mathematical count quota; actual costs remain recorded.' if b['mathematical_evaluations'] is None else 'Frozen cumulative mathematical count quota.',
            remaining_mathematical=mathematical_remaining(s['spec'],s.get('mathematical_evaluations',0)),
            remaining_full_replays=max(0,(s['spec'].get('physical_replay_limit') if s['spec'].get('physical_replay_limit') is not None else b['physical_launches'])-s.get('physical_replay_launches',0)),
            available_full_replays=capacity(host,b['physical_launches'] if b['physical_launches'] is not None else s['spec']['physical_replay_limit'],root_operation=True,route='fixed_tension')['admitted'],
            full_replay_scope='remaining_full_replays is the method sublimit, not an additional shared pool. available_full_replays also applies shared launches, confirmation reserve and public-operation capacity; full request admission still applies.',
            plan_control_search=dict(callback_unit='full physical replay request; exact cached baselines can avoid a new launch',
                declared_callback_maximum=None if b['physical_launches'] is None else b['physical_launches']+1,
                scope='Frozen request cap, not remaining launches. Native analysis callbacks use native_control_limits and the mathematical allowance instead.'),
            native=dict(per_request_control_limits=s['spec'].get('native_control_limits'),
                research_effort=('Mathematical search has no cumulative count quota. Main may deepen control optimization, change parameterization or choose another legal method; finite search failure is not structural infeasibility. Main chooses useful effort, not necessarily the maximum.' if b['mathematical_evaluations'] is None else None),
                accounting_scope='Current Study registered analysis_results only; imported historical results and proposed actions are excluded.',
                recorded_rollouts=sum(v['rollouts'] for _,v,_,_ in native_costs if v.get('rollouts') is not None),
                recorded_physics_steps=sum(v['physics_steps'] for _,v,_,_ in native_costs if v.get('physics_steps') is not None),
                latest_cost_query=dict(reference=native_costs[-1][0],view='full',pointer=native_costs[-1][2]) if native_costs else None,
                attempts_without_cost_record=len(native)-len(native_costs),
                cost_record_complete=all(complete and all(v.get(k) is not None for k in ('rollouts','physics_steps')) for _,v,_,complete in native_costs) and len(native)==len(native_costs),
                integration_scope='Recorded physics_steps already includes prefix reconstruction and suffix rollouts. Callback counts describe these rollouts, not additional integrations. Independent full replay is separate; zero independent physical evaluations does not imply zero native integration.',
                allowance_scope='Recorded totals are known subtotals; incomplete records leave actual total unknown. Native analysis shares remaining_mathematical; per-request limits are not a separate cumulative allowance. Missing costs are unknown, not zero.'),
            any_scientific_route_fits=science_fits(host) and not (active or provider['next_request_will_protect'])),
        closeout=dict(active=active,next_request_will_protect=active or provider['next_request_will_protect'],
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
        (not capabilities and spec.get('start_mode')=='family_space'
            and 'generate' in spec.get('allowed_plan_actions',[])
            and set(spec['allowed_plan_actions'])<={'generate','stop'} and not s.get('candidates')) or
        ('analysis' in capabilities and mathematics_fits(spec,s.get('mathematical_evaluations',0))) or
        ('nmpc' in capabilities and backend>=1 and s.get('nmpc_launches',0)<spec['nmpc_limits']['executions']) or
        ('physical_replay' in capabilities and (backend is None or backend>=1) and s.get('physical_replay_launches',0)<
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
    if route in ('fixed_tension','passive_protocol'):
        limit=s['spec'].get('physical_replay_limit')
        slots=(s['spec']['budgets']['physical_launches'] if limit is None else limit)-s.get('physical_replay_launches',0)
    operations = max(0, remaining['tool_calls'] - (0 if confirmation else s['spec']['budgets'].get('protected_public_operations', 0)))
    # Fixed replay has one public Plan and no charged child tool calls. Inside
    # that admitted Plan, its current public call has already been paid.
    operation_slots=operations+int(not root_operation) if route in ('fixed_tension','passive_protocol') else (operations-int(root_operation))//3
    shared=backend_capacity(host)
    bounds=[requested,slots-reserve,operation_slots]
    if shared is not None:bounds.append(shared-reserve)
    fit = max(0, min(bounds))
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
    if s['spec'].get('task_conditions'):
        from tools.research.conditions import joint_assessment
        from tools.research.config import same_robot_structure
        candidate=host.store.artifact(view['candidate'])
        completed={}
        for ref in s.get('physical_replays',[]):
            result=host.store.artifact(ref);other=host.store.artifact(result['candidate'])
            if (same_robot_structure(candidate['configuration'],other['configuration']) and
                    candidate['configuration']['policy']['discretization']==other['configuration']['policy']['discretization'] and
                    result_view(host,ref)['passed']):
                key=other.get('condition_id',s['spec']['task_conditions'][0]['condition_id'])
                completed[key]=ref
        try:joint=joint_assessment(host,list(completed.values()),require_reads=False)
        except (ValueError,KeyError):return
        if not s.get('success_gate'):
            update(host,success_gate=dict(evidence=joint['condition_results'],candidate=joint['candidate'],
                observed_task_pass=True,model_selection_complete=False,engineering=s['spec'].get('mode')=='engineering_numerical'))
        return
    if view['fresh_current_study'] and view['complete'] and view['passed']:
        import math
        from tools.research_tasks import task_adapter
        limits = task_adapter(host.store.artifact(view['candidate'])['configuration']).ranking_limits()
        result = host.store.artifact(reference)
        if view['controller_route'] in ('nmpc','fixed_tension'):
            metrics = (result.get('acceptance') or {}).get('metrics', {})
            if any(not isinstance(metrics.get(k), (float, int)) or not math.isfinite(metrics[k]) or metrics[k] > limit for k, limit in limits.items()):
                return
        elif view['controller_route']=='rl':
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
