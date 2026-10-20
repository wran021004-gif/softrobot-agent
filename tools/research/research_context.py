"""Compact trusted research views and declared archive import using the existing Store."""
from copy import deepcopy
from tools.platform_store import plain
from tools.state_io import digest
from tools.research.state import state, save, update
from tools.research.feedback import task_gap
from tools.research.evidence_policy import summarize_evidence, hypothesis_catalog, comparable_task


def import_history(host):
    """Import hash-verified observations only; never promote historical execution IDs."""
    from tools.research.numerics import archived
    from tools.research.design import generate_candidate
    from tools.research.physical_replay import binding, schedule_identity
    s=state(host)
    if s.get('research_history_imported'):return
    entries=[]
    for item in s['spec']['research_decisions'].get('history',[]):
        folder=item['folder'];ref=item['reference'];result=archived(folder,ref)
        old=archived(folder,result['candidate']);cfg=old['configuration']
        if comparable_task(s['spec'],cfg['task'])!=s['spec']['canonical_task']:raise ValueError('HISTORY_TASK_IDENTITY_MISMATCH')
        source=archived(folder,result['source_reference'])
        binding(cfg,source['trajectory'])
        parameters=deepcopy(old['parameters']);parameters['family_space_identity']=s['spec']['family_space_identity']
        candidate=generate_candidate(host,parameters,dict(origin='engineering_history_materialization',source=ref))['candidate']
        new=host.store.artifact(candidate)['configuration']
        if schedule_identity(cfg,source['trajectory'])!=schedule_identity(new,source['trajectory']):
            raise ValueError('HISTORY_PHYSICAL_IDENTITY_MISMATCH')
        binding(new,source['trajectory'])
        for r,v in ((result['candidate'],old),(result['source_reference'],source),(ref,result)):
            if save(host,v,'declared_historical_evidence')!=r:raise ValueError('HISTORY_CONTENT_IDENTITY_MISMATCH')
        from tools.research.feedback import import_experiment
        import_experiment(host,folder,ref,'fixed_tension')
        raw=archived(folder,result['raw_reference'])
        if save(host,raw,'declared_historical_raw')!=result['raw_reference']:raise ValueError('HISTORY_RAW_IDENTITY_MISMATCH')
        entries.append(dict(reference=ref,candidate=candidate,source=result['source_reference'],
            historical_candidate=result['candidate'],folder=folder,historical_only=True))
    mathematics=[]
    for item in s['spec']['research_decisions'].get('mathematics',[]):
        value=archived(item['folder'],item['reference'])
        if value.get('candidate'):
            candidate=archived(item['folder'],value['candidate'])
            if comparable_task(s['spec'],candidate['configuration']['task'])!=s['spec']['canonical_task']:raise ValueError('HISTORY_MATH_TASK_IDENTITY_MISMATCH')
            if save(host,candidate,'declared_historical_math_candidate')!=value['candidate']:raise ValueError('HISTORY_MATH_CANDIDATE_MISMATCH')
        if save(host,value,'declared_historical_mathematics')!=item['reference']:raise ValueError('HISTORY_MATH_IDENTITY_MISMATCH')
        mathematics.append(item['reference'])
    for item in s['spec']['research_decisions'].get('control_seeds',[]):
        # Transfer design/inputs only: the old result is never an observation of this task.
        from tools.research.physical_replay import seed_control
        from tools.research.contracts import ControlSeedRequest
        old=archived(item['folder'],item['candidate'])
        source=archived(item['folder'],item['source'])
        binding(old['configuration'],source['trajectory'])
        parent=save(host,old,'declared_control_parent')
        source_ref=save(host,source,'declared_control_source')
        parameters=deepcopy(old['parameters']);parameters['family_space_identity']=s['spec']['family_space_identity']
        generated=generate_candidate(host,parameters,dict(origin='engineering_control_seed',source=item))
        if generated['status']!='generated':raise ValueError('CONTROL_SEED_DESIGN_NOT_EXECUTABLE: '+str(generated))
        seed_control(host,ControlSeedRequest(candidate=generated['candidate'],parent=parent,source=source_ref))
    update(host,research_history=entries,research_mathematics=mathematics,research_history_imported=True)


def observation(host,ref,historical=False):
    from tools.research_tasks import task_adapter
    result=host.store.artifact(ref);cfg=host.store.artifact(result['candidate'])['configuration']
    raw_ref=result.get('raw_reference');adapter=task_adapter(cfg)
    return dict(reference=plain(ref),candidate=result['candidate'],source=result.get('source_reference'),
        task_identity=digest(cfg['task']),historical_only=historical,task_gap=task_gap(result),
        constraints=(result.get('acceptance') or {}).get('components',{}),
        execution_status=result.get('status'),execution=result.get('execution'),
        violations=adapter.violation_samples(host.store.artifact(raw_ref)) if raw_ref else dict(status='unavailable',samples=[]),
        raw_reference=raw_ref,evidence=summarize_evidence(result,ref))


def physical_diagnostic(host,reference):
    """Select measured extrema from the existing adapter, never infer a cause."""
    row=observation(host,reference);raw_ref=row['raw_reference']
    raw=host.store.artifact(raw_ref) if raw_ref else {};samples=raw.get('samples',[])
    extrema={}
    for violation in row['violations']['samples']:
        key=violation['constraint']
        if key not in extrema or violation['normalized_excess']>extrema[key]['normalized_excess']:extrema[key]=violation
    chosen={len(samples)-1:[]} if samples else {}
    for violation in extrema.values():chosen.setdefault(int(violation['raw_pointer'].split('/')[2]),[]).append(violation)
    observed=('tip_m','tip_velocity_m_s','position_error_m','speed_m_s','actual_tension_n')
    inputs=[s['actual_tension_n'] for s in samples if s.get('actual_tension_n') is not None]
    return dict(task_passed=row['task_gap']['accepted'],valid_complete=row['task_gap']['valid_complete'],
        owning_study=host.store.artifact(reference).get('owning_study'),
        violated_constraints={k:v for k,v in row['constraints'].items() if v['passed'] is False},
        critical_samples=[dict(time_s=samples[i]['time_s'],observed={k:samples[i][k] for k in observed if k in samples[i]},
            constraints=chosen[i],raw_reference=raw_ref,read_pointer='/samples/'+str(i)) for i in sorted(chosen)],
        input_bounds_summary=dict(measured_min_n=[min(x) for x in zip(*inputs)],measured_max_n=[max(x) for x in zip(*inputs)],
            acceptance_component=row['constraints'].get('force_bounds')) if inputs else dict(status='unavailable'),
        limitations=['These are measured facts, not a proven failure cause',row['violations']['status'],
            'Only the original registered acceptance establishes this execution outcome'])


def legacy_context(host):
    from tools.research.candidate_portfolio import ranking_key
    from tools.research_tasks import task_adapter
    from tools.research.budget import protected, closeout_operations, stage_usage
    s=state(host);spec=s['spec']
    rows=[observation(host,e['reference'],True) for e in s.get('research_history',[])]
    rows += [observation(host,r) for r in [*s.get('results',[]),*s.get('physical_replays',[]),*s.get('rl_evaluations',[])]]
    valid=sorted((r for r in rows if r['task_gap']['valid_complete']),key=ranking_key)
    best=valid[0] if valid else None
    mapped={e['reference']['artifact_id']:e for e in s.get('research_history',[])}
    if best and best['reference']['artifact_id'] in mapped:
        best={**best,'executable_candidate':mapped[best['reference']['artifact_id']]['candidate']}
    # Pareto coordinates come from registered normalized task components.
    def dominates(a,b):
        def axes(r):
            return {k:v['value']/v['limit'] for k,v in r['constraints'].items()
                if type(v.get('value')) in (int,float) and type(v.get('limit')) in (int,float) and v['limit']>0}
        x=axes(a);y=axes(b)
        return x.keys()==y.keys() and all(x[k]<=y[k] for k in x) and any(x[k]<y[k] for k in x)
    pareto=[r['reference'] for r in valid if not any(dominates(q,r) for q in valid)]
    evidence=[summarize_evidence(host.store.artifact(r),r) for r in [*s.get('research_mathematics',[]),*s.get('analysis_results',[]),*s.get('mechanics_results',[])]]
    evidence=[{k:v[k] for k in ('claim_kind','verification_status','model_identity','candidate_identity','task_identity',
        'supported_inferences','unsupported_inferences','evidence_reference','numerical_evidence_pointer','prospective_guarantee')} for v in evidence]
    return dict(version='research_context_v1',task_identity=spec.get('canonical_task_identity',digest(s['base_configuration']['task'])),
        task=task_adapter(s['base_configuration']).describe(),structure_domain=s.get('family_space_reference'),
        capabilities=spec['capabilities'],best_valid=best,pareto_candidates=pareto,
        observations=[{k:r[k] for k in ('reference','candidate','task_identity','historical_only','task_gap')} for r in rows],
        evidence=evidence,unresolved_hypotheses=hypothesis_catalog(),history=s.get('research_history',[]),
        control_search_starts=[dict(candidate=e['candidate'],source=e['source'],historical_observation=e['reference'],
            ownership='Current executable candidate; observation retains sealed historical ownership') for e in sorted(
                s.get('research_history',[]),key=lambda e:ranking_key(dict(task_gap=task_gap(host.store.artifact(e['reference'])))))],
        actions=[] if s['research_status']=='stopped' else closeout_operations(host)['research_plan'] if protected(host) else spec['allowed_plan_actions'],
        budget=host.store.remaining(),completed_decisions=s.get('plans',[]),
        method_limits=dict(mathematical_evaluations=spec['budgets']['mathematical_evaluations'],offline_nlp=spec['budgets']['offline_nlp'],
            bdf_replays=spec['budgets']['bdf_replays'],nmpc=spec['nmpc_limits'],rl=spec['rl_limits']),
        method_used={k:s.get(k,0) for k in ('mathematical_evaluations','offline_nlp','bdf_replays','nmpc_launches','admitted_training_stages','physical_replay_launches')},
        method_remaining={k:max(0,total-used) for k,total,used in (
            ('mathematical_evaluations',spec['budgets']['mathematical_evaluations'],s.get('mathematical_evaluations',0)),
            ('offline_nlp',spec['budgets']['offline_nlp'],s.get('offline_nlp',0)),('bdf_replays',spec['budgets']['bdf_replays'],s.get('bdf_replays',0)),
            ('nmpc',spec['nmpc_limits']['executions'],s.get('nmpc_launches',0)),('rl_stages',spec['rl_limits']['training_stages'],s.get('admitted_training_stages',0)))},
        rl_accounting=stage_usage(s),
        control_search_usage='action=control_search, control_search={candidate,source,settings,adaptation_from?}; decision fields required. v2 dimensions come from schedule. Optional correction_window_s masks all changes outside the window. Current optimizer supports registered reach-hold norm constraints only; other tasks return unsupported. Full original task always evaluated.')


def compact_evidence(value, reference, pointer='', *, facts_only=False):
    """Deterministic bounded preview; the exact Store artifact remains authoritative."""
    def preview(v,depth=0,path=pointer):
        if isinstance(v,list):
            items=[]
            for i,x in enumerate(v[:3]):
                if len(v)>3 and isinstance(x,dict):
                    fields=('reference','candidate','source','task_gap','label','time_s','tip_m','speed_m_s','position_error_m')
                    shown={k:x[k] for k in fields if k in x}
                    if not shown:
                        items.append(dict(keys=list(x),read_pointer=path+'/'+str(i)));continue
                    x=shown
                items.append(preview(x,depth+1,path+'/'+str(i)))
            return dict(total=len(v),read_pointer=path,item_keys=list(v[0]) if isinstance(v[0],dict) else None,preview=items) if len(v)>3 else items
        if isinstance(v,dict):
            if depth>5:return dict(keys=list(v))
            return {k:(dict(available=True,read_pointer=path+'/'+k) if k in (
                'configuration','scientific_configuration','resolved','trajectory','outputs','samples','request','original_result')
                else preview(x,depth+1,path+'/'+k.replace('~','~0').replace('/','~1'))) for k,x in v.items()}
        return v
    # Acceptance contains all original thresholds and validity components, never truncate it.
    result=preview(value)
    if isinstance(value,dict) and 'acceptance' in value:result['acceptance']=value['acceptance']
    summary={}
    if isinstance(value,dict) and 'best' in value and 'candidates' in value:
        best=value.get('best') or {}
        summary=dict(stop_reason=value.get('stop_reason'),search_dimension=value.get('search_dimension'),
            finite_difference_evaluations=value.get('finite_difference_evaluations'),
            cost_feedback=value.get('cost_feedback'),local_responses=value.get('local_responses',[])[-3:],
            starts=[dict(start=s['start'],initial_gap=s['initial_gap'],best={k:(s.get('best') or {}).get(k)
                for k in ('reference','candidate','source','task_gap')}) for s in value.get('start_feedback',[])],
            best={k:best.get(k) for k in ('reference','candidate','source','task_gap','coefficients_n')},
            small_query=dict(pointer=pointer+'/best',view='fields' if isinstance(value.get('best'),dict) else 'full',fields=[k for k in
                ('reference','candidate','source','task_gap','coefficients_n') if k in best]))
    if isinstance(value,dict) and 'acceptance' in value:
        summary.update(task_gap=task_gap(value),constraints=(value['acceptance'] or {}).get('components',{}),
            limitations=['Only this recorded execution establishes its task outcome'])
    if facts_only and summary:result=dict(read_pointer=pointer,available_keys=list(value))
    return dict(reference=reference,pointer=pointer,view='deterministic_summary',
        available_keys=list(value) if isinstance(value,dict) else None,summary=summary,
        retrieval='Display value/summary/preview are not Store path prefixes. All read_pointer values are absolute paths in reference. Use evidence_read(view=full,pointer=...). No acceptance transfer.',value=result)


def context(host):
    s=state(host);settings=s['spec'].get('research_decisions',{}).get('context_limits')
    current=legacy_context(host)
    if settings is not None:current=bounded_context(current,settings,s.get('control_initializations',[]))
    from tools.research.budget import decision_budget, closeout_operations
    if s['spec'].get('mode')!='engineering_numerical' and decision_budget(host)['closeout']['next_request_will_protect']:
        current['actions']=[] if s['research_status']=='stopped' else closeout_operations(host)['research_plan']
    if s['spec'].get('tool_readiness') or s.get('tool_failures'):
        from tools.research.tool_readiness import availability, MATLAB_ACTIONS
        status=availability(host)
        current['tool_readiness']={k:status.get(k) for k in ('status','checked_unix','failed_stage','reason','failure_reference','log_reference')}
        if status['status']!='ready':current['actions']=[a for a in current['actions'] if a not in MATLAB_ACTIONS]
        exhausted=[a for a,k in (('execute','nmpc'),('mechanics','offline_nlp'),('replay','bdf_replays'),('refine','bdf_replays')) if current['method_remaining'][k]<1]
        current['actions']=[a for a in current['actions'] if a not in exhausted]
    # New valid observations are executable starts, with exact same-task bindings.
    starts=[dict(candidate=host.store.artifact(r)['candidate'],source=host.store.artifact(r)['source_reference'],
        observation=r) for r in reversed(s.get('physical_replays',[])) if task_gap(host.store.artifact(r))['valid_complete']]
    starts += list(reversed(s.get('control_initializations',[])))+current['control_search_starts']
    best=current['best_valid']
    if best and best.get('raw_reference'):best['physical_diagnostic']=physical_diagnostic(host,best['reference'])
    if best and best.get('source'):
        starts.insert(0,dict(candidate=best.get('executable_candidate',best['candidate']),source=best['source'],observation=best['reference']))
    seen=set();unique=[]
    for entry in starts:
        key=(entry['candidate']['artifact_id'],entry['source']['artifact_id'])
        if key not in seen:unique.append(entry);seen.add(key)
    current['control_search_starts']=unique[:(settings or {}).get('candidates',3)]
    domains=[]
    remaining=host.store.remaining()['remaining']['backend_solves']
    for entry in current['control_search_starts']:
        tr=host.store.artifact(entry['source'])['trajectory'];channels=len(tr['tendon_order'])
        domains.append(dict(candidate=entry['candidate'],source=entry['source'],tendon_order=tr['tendon_order'],
            intervals=len(tr['tensions_n']),horizon_s=tr['times_s'][-1],
            full_two_knot_response_requests=2*channels+2,
            one_coefficient_response_requests=3,remaining_backend_launches=remaining,
            full_two_knot_response_fits=remaining>=2*channels+2))
    current['control_start_domains']=domains
    current['control_initialization_methods']=dict(baseline='Pretension, explicit tensions_n, or source+parent with optional channel_map',
        mathematical_response='response_evidence must be a current verified input_sensitivity analysis; optional channels, trust_radius_n, regularization',
        physical_response='Optional baseline source+parent; channels, difference_step_n, trust_radius_n, regularization, evaluation_requests; one baseline plus one full rollout per channel, charged to shared budget')
    current['control_search_domain']=dict(coefficient_order='knot_index * tendon_count + tendon_index',
        active_coefficients='Optional unique flat indices; inactive coefficients remain zero relative to each start',
        response_cost='baseline per start + active coefficient count probes + one proposal per local response iteration; all share one cap',
        time_constraint='0 <= window_start <= knots[0] < knots[-1] <= window_end <= task duration',
        multi_start='additional_starts=[{candidate,source,adaptation_from?}]; same task, tendon order and time grid required')
    # One authoritative STOP index, including results absent from observation previews.
    current['all_fresh_results']=[r for key in ('results','mechanics_results','physical_replays',
        'matched_state_results','rl_evaluations','analysis_results') for r in s.get(key,[])]
    current['decision_feedback']=dict(
        recent_searches=[dict(reference=r,**compact_evidence(host.store.artifact(r),r)['summary'])
            for r in reversed(s.get('control_search_results',[])[-2:])],
        recent_observations=[compact_evidence(host.store.artifact(r),r)['summary'] | dict(reference=r)
            for r in reversed([*s.get('results',[]),*s.get('physical_replays',[]),*s.get('rl_evaluations',[])][-3:])],
        actions=action_feedback(host,current),
        citation_rule='STOP must explain the outcome and explicitly cite all_fresh_results. This index does not record model reading or understanding.')
    from tools.research.budget import decision_budget
    current['budget']=decision_budget(host)
    current['task_accepted']=bool(s.get('success_gate'))
    refs=[*current['all_fresh_results'],*s.get('control_search_results',[])]
    ids={r['artifact_id'] for r in refs}
    latest=next((r for e in reversed(host.store.events(host.run_id)) for r in e.get('outputs',[]) if r['artifact_id'] in ids),None)
    current['latest_scientific_feedback']=None
    if latest:
        value=host.store.artifact(latest)
        if latest in s.get('analysis_results',[]):
            from tools.research.analysis import compact_result
            result=compact_result(value,latest)
            current['latest_scientific_feedback']={k:result.get(k) for k in ('reference','operation','status',
                'static_input_observation','input_response_observation','control_handoff','scoped_claim','analysis_applicability')}
        else:
            current['latest_scientific_feedback']=dict(reference=latest,**compact_evidence(value,latest)['summary'])
            if value.get('acceptance') and value.get('raw_reference'):
                current['latest_scientific_feedback']['physical_diagnostic']=physical_diagnostic(host,latest)
    return current


def action_feedback(host,current):
    """Admission prerequisites for parameterized actions, not model decisions."""
    from tools.research.physical_replay import binding, verified_input_response, explicit_control_source, numerically_verified_source
    from tools.research.design import verify_candidate
    from tools.research.budget import protected, backend_capacity
    from tools.research.evidence_policy import registered_references
    s=state(host);rows=[];capacity=backend_capacity(host);known=registered_references(host)
    closed=s['research_status']=='stopped' or protected(host)
    for entry in current['control_search_starts']:
        candidate=entry['candidate'];source=entry['source'];cfg=host.store.artifact(candidate)['configuration']
        for action in ('physical_replay','control_search'):
            reason=None;status='preflight_eligible'
            if closed or action not in current['actions'] or action not in s['spec']['capabilities'] or capacity<1:
                status='unavailable';reason='Protected/stopped state, action availability or shared backend capacity'
            elif action=='control_search' and cfg['task']['family']!='task.reach':
                status='not_applicable';reason='Current search requires reach-hold norm constraints'
            else:
                try:
                    verify_candidate(host,candidate)
                    control=host.store.artifact(source)
                    if not (explicit_control_source(control) or numerically_verified_source(control)):
                        raise ValueError('VERIFIED_OR_EXPLICIT_CONTROL_START_REQUIRED')
                    binding(cfg,control['trajectory'])
                except ValueError as exc:status='blocked';reason=str(exc)
            rows.append(dict(action=action,status=status,candidate=candidate,source=source,reason=reason,
                supporting_evidence=[r for r in (entry.get('observation',entry.get('historical_observation')),source) if r and r in known],
                remaining_checks=['full_plan_admission','requested_budget','scientific_preflight'],
                remaining_backend_launches=capacity,minimum_new_launches=1,
                requires_agent_fields=['decision','hypothesis','finite search settings'] if action=='control_search' else ['decision','hypothesis'],
                scope='Candidate/source admission only; full typed Plan, budget and scientific preflight remain authoritative'))
    candidates=list({e['candidate']['artifact_id']:e['candidate'] for e in current['control_search_starts']}.values())
    candidates += [r for r in list(s.get('candidates',{}).values())[-3:] if r not in candidates]
    for candidate in candidates:
        from tools.research.contracts import MechanicsRequest
        from tools.research.mechanics import warm_start
        from tools.research_tasks import task_adapter
        cfg=host.store.artifact(candidate)['configuration']
        requirements=task_adapter(cfg).analysis_requirements({})
        applicable=all(c.kind=='norm_bound' and c.signal.name in ('tip_position','tip_velocity') for c in requirements.constraints)
        modes=MechanicsRequest.model_json_schema()['properties']['initialization']['enum'];warm=[]
        for source in known:
            for mode in modes[2:]:
                try:
                    request=MechanicsRequest(candidate=candidate,initialization=mode,warm_source=source)
                    trajectory=warm_start(host,request);binding(cfg,trajectory)
                    warm.append(dict(initialization=mode,warm_source=source,objective_mode=request.objective_mode))
                except (ValueError,KeyError,TypeError):continue
        rows.append(dict(action='mechanics',candidate=candidate,status='preflight_eligible' if applicable and 'mechanics' in current['actions'] else 'unavailable',
            task_applicable=applicable,cold_initializations=modes[:2],warm_sources=warm,
            warm_source_scope='Advertised defaults: substeps=1, objective_mode=task_gap; other objectives/grids require full preflight',
            missing_warm_source=None if warm else 'No eligible bound mathematical source for advertised defaults; explicit physical schedules do not qualify',
            check_only='Mathematical checking uses the analysis allowance; it is not an optimized or physically accepted result',
            remaining_checks=['full_plan_admission','requested_budget','model/coordinate/state/substeps/grid preflight'],
            example=dict(action='mechanics',mechanics=dict(candidate=candidate,initialization=modes[0],check_only=False))))
        references=[r for r in s.get('analysis_results',[]) if host.store.artifact(r).get('candidate')==candidate
            and host.store.artifact(r).get('operation')=='input_sensitivity']
        status='blocked';reason='verified_input_sensitivity_required';ref=None
        for ref in reversed(references):
            try:verified_input_response(host,candidate,ref);status='preflight_eligible';reason=None;break
            except ValueError as exc:reason=str(exc)
        cfg=host.store.artifact(candidate)['configuration']
        if cfg['task']['family']!='task.reach':status='not_applicable';reason='Endpoint-target seed required'
        elif closed or 'initialize_control' not in current['actions'] or 'control_correction' not in s['spec']['capabilities']:
            status='unavailable';reason='Initialization unavailable in current stage'
        rows.append(dict(action='initialize_control',method='mathematical_response',status=status,reason=reason,
            candidate=candidate,response_evidence=ref,task_acceptance='unmeasured',new_physical_evaluations=0,
            requires_agent_fields=['decision','hypothesis','initialization settings']))
    return rows


def decision_brief(current):
    """Pure current-state projection; raw evidence and conversation are untouched."""
    brief=deepcopy(current)
    for key in ('observations','pareto_candidates','recent_decisions','control_search_usage',
                'control_search_starts','control_start_domains','structure_domain'):
        brief.pop(key,None)
    best=brief.get('best_valid')
    if best:
        brief['best_valid']={k:best[k] for k in ('reference','candidate','source','executable_candidate',
            'task_identity','historical_only','task_gap','physical_diagnostic') if k in best}
        brief['best_valid']['violated_constraints']={k:v for k,v in best['constraints'].items() if not v['passed']}
    brief['task_accepted']=current.get('task_accepted',bool(best and best['task_gap']['accepted'] and not best['historical_only']))
    brief['unresolved_hypotheses']={k:dict(scope=v['scope'],claim_kind=v['claim_kind'])
        for k,v in brief.get('unresolved_hypotheses',{}).items()}
    feedback=brief.pop('decision_feedback')
    brief['recent_searches']=feedback['recent_searches']
    brief['available_research_actions']=feedback['actions']
    domains=current.get('control_start_domains',[])
    for row in brief['available_research_actions']:
        domain=next((d for d in domains if d['candidate']==row.get('candidate') and d['source']==row.get('source')),None)
        if domain:row['domain']={k:v for k,v in domain.items() if k not in ('candidate','source')}
    brief['citation_rule']=feedback['citation_rule']
    brief['version']='decision_brief_v1'
    return brief


def tool_feedback(host,value):
    """Return new facts once, distinguishing the wrapper from registered evidence."""
    from tools.research.evidence_policy import registered_references
    wrapper=save(host,value,'complete_tool_output');result=value.get('result',value)
    reference=result.get('reference') if isinstance(result,dict) else None
    known=registered_references(host)
    if reference in known:
        raw=host.store.artifact(reference)
        view=compact_evidence(raw,reference,facts_only=True)
        if reference in state(host).get('analysis_results',[]):
            from tools.research.analysis import compact_result
            view=compact_result(raw,reference)
    else:view=compact_evidence(result,wrapper,'/result' if 'result' in value else '')
    if reference in known and isinstance(raw,dict) and raw.get('acceptance') and raw.get('raw_reference'):
        view['physical_diagnostic']=physical_diagnostic(host,reference)
    return dict(wrapper_reference=wrapper,wrapper_role='Retrieval only; not supporting_evidence',
        scientific_reference=reference if reference in known else None,new_facts=view)


def bounded_context(current,settings,initializations=()):
    """Pure projection also used for exact saved-decision offline comparisons."""
    current=deepcopy(current)
    n=lambda key,default:settings.get(key,default)
    best=current['best_valid']
    if best:
        best=deepcopy(best)
        samples=best['violations'].get('samples',[])
        best['violations'].update(total=len(samples),samples=sorted(samples,key=lambda r:r['normalized_excess'],reverse=True)[:n('samples',6)])
        best['evidence']={k:v for k,v in best['evidence'].items() if k in (
            'claim_kind','verification_status','supported_inferences','unsupported_inferences','evidence_reference','prospective_guarantee')}
    all_rows=current['observations']
    fresh=[r for r in all_rows if not r['historical_only']]
    current.update(version='research_context_v2',best_valid=best,
        observations=all_rows[-n('recent',4):],all_fresh_results=[r['reference'] for r in fresh],
        observation_count=len(all_rows),pareto_candidates=current['pareto_candidates'][:n('pareto',3)],
        evidence=current['evidence'][-n('evidence',3):],history_count=len(current.pop('history')),
        control_search_starts=[*initializations,*current['control_search_starts']][:n('candidates',3)],
        completed_decision_count=len(current['completed_decisions']),
        recent_decisions=current.pop('completed_decisions')[-n('recent',4):],
        evidence_access='Full artifacts remain in Store. all_fresh_results is the complete STOP citation index; observations is a bounded recent view.')
    return current
