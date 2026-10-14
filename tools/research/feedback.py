"""Program facts about evidence identity, ownership, cost and legal references."""
from copy import deepcopy
from tools.platform_store import plain
from tools.state_io import digest


def solution_identity(host, result, candidate):
    """Identify effective science and policy bytes, independent of artifact locations."""
    science = deepcopy(result.get('scientific_configuration', candidate['scientific_configuration']))
    design = science['robot']['structure']['data']
    design.pop('metadata', None)  # Contract declares descriptive data, never physics.
    design.pop('id', None)
    # Generator inputs/provenance are not a change to the resolved physical model.
    science['policy'].pop('candidate_builder', None)
    rl = 'run_id' in result and 'independent_evaluation_executed' in result
    if rl:
        configuration = host.store.artifact(result['configuration'])
        for key in ('controller', 'dynamics_model', 'discretization'):
            science['policy'].pop(key, None)  # RL executes the compiled MuJoCo model below.
        effective = {k: deepcopy(configuration[k]) for k in
            ('mode', 'seed', 'observation', 'action', 'control_object', 'task')}
        effective['candidate'] = {k: deepcopy(configuration['candidate'][k]) for k in ('xml', 'assets')}
        reference = configuration.get('reference')
        effective['reference'] = {k: reference[k] for k in
            ('sha256', 'tendon_order', 'control_period_s')} if reference else None
        policy_sha = result.get('policy_sha256')
        # An invalid attempt may never load weights; retain its frozen selection binding.
        if not policy_sha and result.get('role') == 'confirmation' and result.get('selected_execution'):
            policy_sha = host.store.artifact(result['selected_execution']).get('policy_sha256')
        controller = dict(route='rl', configuration=effective, policy_sha256=policy_sha)
    else:
        from extensions.tendon_family.contracts import GVSTrajectoryParameters
        controller_configuration = science['policy']['controller']
        recipe = controller_configuration['parameters']['data']['recipe']
        recipe = plain(GVSTrajectoryParameters.model_validate(recipe))
        if recipe['stopping_policy'] == 'research_work_v1':
            recipe.update(max_cpu_s=None, feasible_return=None)
        controller_configuration['parameters']['data']['recipe'] = recipe
        controller = dict(route='nmpc', configuration=controller_configuration)
    return dict(scientific_configuration=science, controller=controller)


def confirmation_progress(host, selected=None):
    """Retain all solution failures; only current-study launches satisfy fresh repetitions."""
    from tools.research.core import state, confirmation_count
    s=state(host); selected=plain(selected or s.get('selected')); rows={}
    chosen=result_view(host,selected) if selected else None
    for historical, refs in ((True,[*s.get('historical_confirmations',[]), *s.get('linked_selections',[]), *s.get('scoped_context',[])]),
                             (False,[*s.get('results',[]),*s.get('rl_evaluations',[])])):
        for ref in refs:
            r=host.store.artifact(ref)
            if not isinstance(r,dict) or r.get('role')!='confirmation': continue
            v=result_view(host,ref)
            if not chosen or v['solution_identity']!=chosen['solution_identity']: continue
            owner=r.get('evaluation_owner') or r.get('study') or r.get('owning_study')
            is_historical=historical or not v['fresh_current_study']
            execution=(owner, r.get('execution_id') or r.get('operation_key') or ref['artifact_id'])
            previous=rows.get(execution)
            if previous:
                # A second reference to a launch cannot hide incomplete/failing evidence.
                previous['complete'] &= v['complete']
                previous['passed'] &= v['passed']
                previous['historical'] |= is_historical
            else:
                rows[execution]=dict(reference=ref,historical=is_historical,
                    owner=owner,complete=v['complete'],passed=v['passed'])
    values=list(rows.values()); required=confirmation_count(s)
    fresh=[v for v in values if not v['historical']]
    return dict(required_total=required,historical_confirmations=sum(v['historical'] for v in values),
        current_study_confirmations=sum(not v['historical'] for v in values),
        remaining=max(0,required-len(fresh)),failures=sum(v['complete'] and not v['passed'] for v in values),
        invalid_executions=sum(not v['complete'] for v in values),executions=values,
        confirmed=bool(chosen and chosen['fresh_current_study'] and chosen['passed'] and len(fresh)==required
            and all(v['complete'] and v['passed'] for v in values)),
        correct_operation=dict(tool='research_plan',action='confirm',selected_execution=selected))


def result_view(host, reference):
    """Organize original evidence once, without recomputing task metrics."""
    from tools.research.core import state
    from tools.research.design import full_science
    r=host.store.artifact(reference); c=host.store.artifact(r['candidate'])
    # Historical reads stay valid after the active profile/selection changes.
    if c['scientific_configuration']!=full_science(c['configuration']):
        raise ValueError('IMPORTED_CONFIGURATION_IDENTITY_MISMATCH')
    rl='run_id' in r and 'independent_evaluation_executed' in r
    episodes=r.get('episodes',[]) if rl else []
    complete=bool(r.get('independent_evaluation_executed') and episodes and all(e['complete'] for e in episodes)) if rl else r.get('status')=='evaluated'
    passed=bool(complete and (r.get('passed') if rl else (r.get('acceptance') or {}).get('accepted')))
    controller=dict(route='rl',configuration=r['configuration'],checkpoint=r.get('checkpoint'),policy_sha256=r.get('policy_sha256')) if rl else dict(route='nmpc',configuration=c['scientific_configuration']['policy']['controller'])
    identity=solution_identity(host,r,c)
    owner=r.get('evaluation_owner') or r.get('study') or r.get('owning_study')
    s=state(host);current_refs=[*s.get('results',[]),*s.get('rl_evaluations',[])]
    fresh=bool(plain(reference) in current_refs and plain(reference) not in s.get('historical_confirmations',[])
        and plain(reference) not in s.get('linked_selections',[]) and owner==host.run_id and not r.get('imported_historical_evidence')
        and r.get('fresh_execution',True) and not r.get('cached_operation_receipt'))
    metrics=episodes if rl else (r.get('acceptance') or {}).get('metrics')
    failed_metrics=[]
    acceptance=r.get('acceptance') or {}
    if not rl:
        profile=r.get('profile') or {};motion=host.store.artifact(profile['motion']) if profile.get('motion') else []
        for name,component in acceptance.get('components',{}).items():
            if component.get('passed') is not False:continue
            key={'holding_speed':'tip_speed_m_s','holding_position':'tip_error_m','evaluator:task_bound':'tip_error_m'}.get(name)
            samples=[v for v in motion if name not in ('holding_speed','holding_position') or v['time_s']>=.30-1e-12]
            worst=max(samples,key=lambda v:v[key]) if key and samples else {}
            failed_metrics.append(dict(metric=name,value=component.get('value'),threshold=component.get('limit'),unit=component.get('unit'),
                time_s=(motion[-1]['time_s'] if name=='evaluator:task_bound' and motion else worst.get('time_s'))))
    for episode in episodes:
        for metric,limit in (('terminal_position_error_m','terminal_position_limit_m'),('holding_max_position_error_m','position_limit_m'),('holding_max_speed_m_s','holding_speed_limit_m_s')):
            if episode.get(metric) is not None and acceptance.get(limit) is not None and episode[metric]>acceptance[limit]:
                failed_metrics.append(dict(metric=metric,value=episode[metric],threshold=acceptance[limit],time_s='not recorded in evaluation summary'))
    return dict(failed_metrics=failed_metrics,solver_outcome={k:(r.get('profile') or {}).get(k) for k in
        ('optimization_status_counts','raw_termination_counts','policy_stop_reason_counts','unusable_plans')},
        execution_timing=acceptance.get('timing'),failure_state_analysis=mathematical_context(host,r['candidate']),
        evaluation_evidence=dict(trajectory=r.get('trajectory') or (r.get('profile') or {}).get('motion'),reference=plain(reference)),candidate=r['candidate'],task=r.get('task',c['configuration']['task']),controller_route=controller['route'],controller=controller,
        mathematical_provenance=mechanics_context(host,r['candidate']),mathematical_evidence=mathematical_context(host,r['candidate']),metrics=metrics,complete=complete,passed=passed,
        task_performance='passed' if passed else 'failed' if complete else 'unmeasured',
        failure_stage=r.get('failure_stage') or ('task criteria unmet' if complete and not passed else r.get('failure_reason')),
        costs=dict(evaluation_elapsed_s=r.get('evaluation_elapsed_s'),numerical_s=r.get('numerical_s'),counts=r.get('counts')),
        evidence=plain(reference),role=r.get('role','development'),selected_execution=r.get('selected_execution'),
        fresh_current_study=fresh,solution_identity=identity,solution_identity_sha256=digest(identity))


def eligibility(host, reference, *, revise_selection=False):
    from tools.research.core import state, capacity, verify_candidate
    from tools.research.rl import evaluation_capacity
    s=state(host);ref=plain(reference);reasons=[];refs=[*s['results'],*s.get('rl_evaluations',[]),*s.get('linked_selections',[])]
    if ref not in refs:
        return dict(eligible=False,reasons=['not a current-study controller result'],required_field='selected_execution')
    r=host.store.artifact(ref);count=0;progress=None;fit=None
    try:
        v=result_view(host,ref)
        if not v['fresh_current_study']: reasons.append('historical or imported result is not fresh development evidence')
        if r.get('role','development')=='confirmation': reasons.append('selection requires a passing development evaluation')
        if not v['passed']: reasons.append('result did not pass complete original task evaluation')
        c=verify_candidate(host,r['candidate'])
        if v['controller_route']=='nmpc' and (r.get('profile_identity')!=s['profile']['identity'] or r['scientific_configuration']!=c['scientific_configuration']):
            reasons.append('selected scientific configuration mismatch')
        if v['controller_route']=='rl' and (not r.get('checkpoint') or not r.get('policy_sha256')): reasons.append('exact evaluated checkpoint identity missing')
        if s.get('selected') and s['selected']!=ref:
            old=confirmation_progress(host,s['selected'])
            if not revise_selection: reasons.append('confirmation selection already frozen; explicit revise_selection required')
            if not (old['failures'] or old['invalid_executions']): reasons.append('selection remains immutable during its confirmation attempt')
            if result_view(host,s['selected'])['solution_identity']==v['solution_identity']:
                reasons.append('revision requires a scientifically changed solution; relabeling cannot erase failure')
        elif revise_selection:
            reasons.append('revision requires a different failed selection')
        progress=confirmation_progress(host,ref);count=progress['required_total']-progress['remaining']
        required=progress['required_total']
        if progress['failures'] or progress['invalid_executions']: reasons.append('confirmation failed or invalid for this scientific solution; inspect evidence, no automatic retry')
        if count>=required: reasons.append('declared confirmations already recorded')
        if revise_selection and count: reasons.append('revised solution already has a confirmation attempt; allowance cannot restart')
        remaining=required if revise_selection else required-count
        fit=evaluation_capacity(host,remaining,confirmation=True) if v['controller_route']=='rl' else capacity(host,remaining,True,root_operation=True,candidate=r['candidate'])
        if fit['admitted']<remaining: reasons.append('remaining required confirmations do not fit route budget')
    except (ValueError,KeyError) as exc:
        reasons.append(str(exc));count=0
    if s['research_status']=='stopped':reasons.append('study sealed after STOP')
    if s.get('selected') and confirmation_progress(host)['confirmed']: reasons.append('solution confirmed; close study')
    return dict(eligible=not reasons,reasons=reasons,required_field='selected_execution',selected_execution=ref,
        owning_study=r.get('study',r.get('owning_study')),historical_input=ref in s.get('linked_selections',[]),
        completed_confirmations=count,progress=progress,confirmation_reservation=fit)


def facts(host):
    from tools.research.core import state
    s = state(host)
    if s['spec'].get('mode')=='rl_interface':
        return dict(owning_study=host.run_id,rl_runs=s.get('rl_runs',{}),rl_evaluations=s.get('rl_evaluations',[]),
            frozen_task=s.get('rl_task'),closeout='Explicit evaluation evidence read and cited next-step decision; no second trial')
    progress=confirmation_progress(host)
    options=[*s['results'],*s.get('rl_evaluations',[]),*s.get('linked_selections',[])]
    return dict(owning_study=host.run_id,
        identity_rules=dict(candidate='immutable full configuration; may be shared by identical constructions',
            execution='fresh independent launch with separate execution_id and owner_run_id',
            historical='imported evidence has its original ownership and previous cost; no new execution',
            receipt='reusing an operation ID returns a cached receipt; additional execution cost is zero',
            role='origin, role and phase are metadata, not scientific configuration changes',
            solution='effective scientific configuration and policy content; artifact labels and checkpoint paths excluded'),
        confirmation_progress=progress,selection_history=s.get('selection_history',[]),
        confirmation_options=[dict(execution_reference=r, **eligibility(host,r)) for r in options],
        revision_options=[dict(execution_reference=r,revise_selection=True,**eligibility(host,r,revise_selection=True))
            for r in options if r!=s.get('selected')] if s.get('selected') and (progress['failures'] or progress['invalid_executions']) else [],
        confirmation_reference_shape={'selected_execution':{'artifact_id':'exact passing result artifact_id','media_type':'application/json'}})


def cached(output):
    """Keep saved facts intact while describing the additional cost of this call."""
    return dict(output, operation_reuse=dict(cached_operation_receipt=True,
        additional_numerical_s=0., additional_scientific_executions=0,
        prior_result_costs='retained in saved result numerical_s; not newly incurred by receipt retrieval'))


def mechanics_context(host, candidate):
    from tools.research.core import state
    s=state(host); relations=[host.store.artifact(r) for r in s.get('handoffs',[])
        if host.store.artifact(r)['candidate']==plain(candidate)]
    rows=[]
    for relation in relations:
        source=relation['mechanics_attempt']
        replays=[dict(reference=r,**{k:host.store.artifact(r).get(k) for k in ('status','replay','original_request','log_reference')})
            for r in [*s.get('mechanics_results',[]),*s.get('imported_mechanics_results',[])] if host.store.artifact(r).get('source_mechanics')==source]
        verification='not performed' if not replays else 'passed' if all((r.get('replay') or {}).get('gates_passed',False) for r in replays) else 'failed' if any((r.get('replay') or {}).get('status')=='completed' and not (r.get('replay') or {}).get('gates_passed',False) for r in replays) else 'inconclusive'
        failed=[]
        for r in replays:
            replay=r.get('replay') or {}; check=replay.get('integration_consistency') or {}
            for metric,threshold,time_key in (('node_max_tip_disagreement_m','tip_limit_m','node_max_tip_disagreement_at_s'),('node_max_speed_disagreement_m_s','velocity_vector_limit_m_s','node_max_speed_disagreement_at_s')):
                if replay.get(metric) is not None and check.get(threshold) is not None and replay[metric]>check[threshold]:
                    failed.append(dict(metric=metric,value=replay[metric],threshold=check[threshold],time_s=replay.get(time_key),reference=r['reference']))
        mathematical=host.store.artifact(source)
        rows.append(dict(mechanics_attempt=source,offline_trajectory=relation['offline_trajectory'],
            original_request=mathematical.get('original_request'),relaxed_conditions=relation.get('relaxation'),failed_verification_metrics=failed,
            solver_status=host.store.artifact(source).get('status'),
            independent_mathematical_verification=verification,
            original_offline_task_accepted=relation['original_task_feasible'],relaxed_nlp_feasible=relation['relaxed_nlp_feasible'],
            independent_model_replays=replays,
            exploratory_closed_loop=not relation['original_task_feasible'] or not replays or
                any(not (r.get('replay') or {}).get('gates_passed',False) for r in replays),
            qualification='Offline task, independent model replay, and MuJoCo acceptance are separate gates.'))
    # Repeated handoffs are provenance relations, not additional NLPs or replays.
    unique={r['mechanics_attempt']['artifact_id']:r for r in rows}
    return list(unique.values())


def mathematical_context(host,candidate):
    """Exact candidate links to calculated evidence; no recomputation or interpretation."""
    from tools.research.core import state
    records=[]
    for ref in state(host).get('analysis_results',[]):
        value=host.store.artifact(ref)
        if value['candidate']!=plain(candidate):continue
        records.append(dict(reference=ref,**{k:value.get(k) for k in
            ('operation','origin','status','operating_point','proxy_values','local_model_constraints','charged_numerical_s')}))
    return records


def compact_local(row):
    keys=('execution_id','historical_input','source_update_id','first_input_n','original_applied_action_n',
          'exact_initialized_vector_equal','exact_bounds_equal','charged_numerical_s','diagnostic_trace_enabled')
    result={k:row.get(k) for k in keys};i=dict(row.get('problem_inspection') or {})
    recovery=i.get('original_recovery_selection') or {}
    i['original_recovery_selection']={k:recovery.get(k) for k in ('attempted','selected','objective','parent_iteration')}
    result.update(problem_inspection=i,local_iterations=(row.get('diagnostics') or {}).get('iterations'),
        stopping_controls=row.get('stopping_controls'),verification=row.get('verification'),
        raw_termination=(row.get('diagnostics') or {}).get('return_status'),
        selected_iteration=(row.get('diagnostics') or {}).get('selected_feasible_iteration'),
        local_recovery_selection={k:(row.get('recovery') or {}).get(k) for k in ('attempted','selected','objective','parent_iteration')})
    return result
