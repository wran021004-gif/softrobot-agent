"""Program facts about evidence identity, ownership, cost and legal references."""
from tools.platform_store import plain


def eligibility(host, reference):
    from tools.research_core import state, capacity, verify_candidate
    s = state(host); ref = plain(reference); reasons = []
    if ref not in s['results']:
        return dict(eligible=False, reasons=['not a current-study execution result'],
                    required_field='selected_execution', required_shape={'artifact_id':'passing result hash','media_type':'application/json'})
    r = host.store.artifact(ref)
    if not (r.get('acceptance') or {}).get('accepted'): reasons.append('execution did not pass joint task acceptance')
    if r.get('profile_identity') != s['profile']['identity']: reasons.append('execution uses an earlier evaluation profile')
    try:
        c = verify_candidate(host, r['candidate'])
        if r['scientific_configuration'] != c['scientific_configuration']: reasons.append('full scientific configuration mismatch')
    except (ValueError, KeyError) as exc: reasons.append(str(exc))
    if s.get('selected') and s['selected'] != ref: reasons.append('confirmation selection is already frozen to another execution')
    count = sum(host.store.artifact(v).get('role') == 'confirmation' and
                host.store.artifact(v).get('selected_execution') == ref for v in s['results'])
    if count >= 2: reasons.append('two post-selection confirmations already recorded')
    if capacity(host, 1, True, root_operation=True)['admitted'] < 1: reasons.append('fresh confirmation allowance does not fit')
    if s['research_status'] == 'stopped': reasons.append('study is sealed after STOP')
    return dict(eligible=not reasons, reasons=reasons, required_field='selected_execution',
                selected_execution=ref, owning_study=host.run_id, completed_confirmations=count,
                candidate_is_not_execution=True)


def facts(host):
    from tools.research_core import state
    s = state(host)
    if s['spec'].get('mode')=='rl_interface':
        return dict(owning_study=host.run_id,rl_runs=s.get('rl_runs',{}),rl_evaluations=s.get('rl_evaluations',[]),
            frozen_task=s.get('rl_task'),closeout='Explicit evaluation evidence read and cited next-step decision; no second trial')
    return dict(owning_study=host.run_id,
        identity_rules=dict(candidate='immutable full configuration; may be shared by identical constructions',
            execution='fresh independent launch with separate execution_id and owner_run_id',
            historical='imported evidence has its original ownership and previous cost; no new execution',
            receipt='reusing an operation ID returns a cached receipt; additional execution cost is zero',
            role='origin, role and phase are metadata, not scientific configuration changes'),
        confirmation_options=[dict(execution_reference=r, **eligibility(host,r)) for r in s['results']],
        confirmation_reference_shape={'selected_execution':{'artifact_id':'exact passing result artifact_id','media_type':'application/json'}})


def cached(output):
    """Keep saved facts intact while describing the additional cost of this call."""
    return dict(output, operation_reuse=dict(cached_operation_receipt=True,
        additional_numerical_s=0., additional_scientific_executions=0,
        prior_result_costs='retained in saved result numerical_s; not newly incurred by receipt retrieval'))


def mechanics_context(host, candidate):
    from tools.research_core import state
    s=state(host); relations=[host.store.artifact(r) for r in s.get('handoffs',[])
        if host.store.artifact(r)['candidate']==plain(candidate)]
    rows=[]
    for relation in relations:
        source=relation['mechanics_attempt']
        replays=[dict(reference=r,**{k:host.store.artifact(r).get(k) for k in ('status','replay')})
            for r in s.get('mechanics_results',[]) if host.store.artifact(r).get('source_mechanics')==source]
        rows.append(dict(mechanics_attempt=source,offline_trajectory=relation['offline_trajectory'],
            original_offline_task_accepted=relation['original_task_feasible'],relaxed_nlp_feasible=relation['relaxed_nlp_feasible'],
            independent_model_replays=replays,
            exploratory_closed_loop=not relation['original_task_feasible'] or not replays or
                any(not (r.get('replay') or {}).get('gates_passed',False) for r in replays),
            qualification='Offline task, independent model replay, and MuJoCo acceptance are separate gates.'))
    # Repeated handoffs are provenance relations, not additional NLPs or replays.
    unique={r['mechanics_attempt']['artifact_id']:r for r in rows}
    return list(unique.values())


def compact_local(row):
    keys=('execution_id','historical_input','source_update_id','first_input_n','original_applied_action_n',
          'exact_initialized_vector_equal','exact_bounds_equal','charged_numerical_s','diagnostic_trace_enabled')
    result={k:row.get(k) for k in keys};i=dict(row.get('problem_inspection') or {})
    recovery=i.get('original_recovery_selection') or {}
    i['original_recovery_selection']={k:recovery.get(k) for k in ('attempted','selected','objective','parent_iteration')}
    result.update(problem_inspection=i,local_iterations=(row.get('diagnostics') or {}).get('iterations'),
        local_recovery_selection={k:(row.get('recovery') or {}).get(k) for k in ('attempted','selected','objective','parent_iteration')})
    return result
