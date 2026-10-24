"""Compact trusted research views and declared archive import using the existing Store."""
from copy import deepcopy
from tools.platform_store import plain
from tools.state_io import digest
from tools.research.state import state, save, update
from tools.research.feedback import task_gap
from tools.research.evidence_policy import summarize_evidence, hypothesis_catalog, comparable_task, citation_inventory


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


def measured_samples(host,result):
    """Adapt sealed measurements only; never use optimizer states or predictions."""
    raw_ref=result.get('raw_reference')
    if raw_ref:return host.store.artifact(raw_ref),dict(reference=raw_ref,pointer='/samples',fields={})
    motion_ref=(result.get('profile') or {}).get('motion')
    if not motion_ref:return {},dict(status='unavailable',reason='No saved measured motion')
    motion=host.store.artifact(motion_ref);updates=[];input_ref=None
    try:
        from extensions.tendon_family.control_evidence import ControlEvidence
        reader=ControlEvidence(host.store);source=reader.resolve(result['execution_id'])
        input_ref=source['files'].get('controller_observations.json')
        updates=reader.read_file(source,'controller_observations.json',[])
    except (ValueError,KeyError):pass
    fields=dict(tip_m='tip_position_m',position_error_m='tip_error_m',speed_m_s='tip_speed_m_s')
    samples=[]
    for m in motion:
        # Normalize names for the existing task adapter; endpoint uses the preceding interval.
        row={**m,**{k:m[v] for k,v in fields.items() if v in m}}
        previous=[(i,u) for i,u in enumerate(updates) if u['time_s']<m['time_s']-1e-12]
        if previous:
            i,u=previous[-1];row.update(actual_tension_n=u.get('actual_tension_n'),
                input_query=dict(reference=input_ref,pointer='/'+str(i)+'/actual_tension_n'),input_time_s=u['time_s'])
        samples.append(row)
    return dict(samples=samples),dict(reference=motion_ref,pointer='',fields=fields,input_reference=input_ref,
        input_rows=[u['actual_tension_n'] for u in updates if u.get('actual_tension_n') is not None],
        input_phase='Measured pre-step input of the interval ending at the motion sample')


def observation(host,ref,historical=False):
    from tools.research_tasks import task_adapter
    result=host.store.artifact(ref);cfg=host.store.artifact(result['candidate'])['configuration']
    raw_ref=result.get('raw_reference');adapter=task_adapter(cfg);raw,measurement=measured_samples(host,result)
    violations=adapter.violation_samples(raw) if raw.get('samples') else dict(status='unavailable',samples=[])
    if not task_gap(result)['valid_complete']:
        violations=dict(status='partial_measurements_not_complete_task_failure',samples=[v for v in violations['samples']
            if v['constraint']!='terminal_error_m' or abs(v['time_s']-cfg['task']['timing']['duration_s'])<=1e-9])
    return dict(reference=plain(ref),candidate=result['candidate'],source=result.get('source_reference'),
        task_identity=digest(cfg['task']),historical_only=historical,task_gap=task_gap(result),
        constraints=(result.get('acceptance') or {}).get('components',{}),
        execution_status=result.get('status'),execution=result.get('execution'),
        violations=violations,
        raw_reference=raw_ref,evidence=summarize_evidence(result,ref))


def physical_diagnostic(host,reference):
    """Select measured extrema from the existing adapter, never infer a cause."""
    result=host.store.artifact(reference);row=observation(host,reference)
    raw,measurement=measured_samples(host,result);raw_ref=measurement.get('reference');samples=raw.get('samples',[])
    extrema={}
    for violation in row['violations']['samples']:
        key=violation['constraint']
        if key not in extrema or violation['normalized_excess']>extrema[key]['normalized_excess']:extrema[key]=violation
    chosen={len(samples)-1:[]} if samples else {}
    for violation in extrema.values():chosen.setdefault(int(violation['raw_pointer'].split('/')[2]),[]).append(violation)
    observed=('tip_m','tip_velocity_m_s','position_error_m','speed_m_s','actual_tension_n')
    inputs=measurement.get('input_rows',[s['actual_tension_n'] for s in samples if s.get('actual_tension_n') is not None])
    cfg=host.store.artifact(result['candidate'])['configuration']
    limits=[t['force_limit_n'] for t in cfg['robot']['structure']['data']['tendons']]
    evaluation=result.get('evaluation_reference') or (result.get('execution',{}).get('receipts',{}).get('evaluation') or {}).get('output')
    evaluator=dict(status='unavailable',reference=evaluation)
    if evaluation:
        try:evaluator=dict(reference=evaluation,result=host.store.artifact(evaluation))
        except (ValueError,KeyError):evaluator['reason']='Original evaluator artifact unavailable in this readable snapshot'
    for violations in chosen.values():
        for v in violations:
            _,_,i,field=v['raw_pointer'].split('/')
            v.update(raw_reference=raw_ref,raw_pointer=measurement.get('pointer','')+'/'+i+'/'+measurement.get('fields',{}).get(field,field))
    return dict(evaluation_reference=reference,candidate_reference=result['candidate'],
        control_source_reference=result.get('source_reference',reference),execution_status=result.get('status'),
        original_acceptance=result.get('acceptance'),original_evaluation=evaluator,
        task_passed=row['task_gap']['accepted'],valid_complete=row['task_gap']['valid_complete'],
        owning_study=host.store.artifact(reference).get('owning_study'),
        violated_constraints={k:v for k,v in row['constraints'].items() if v['passed'] is False},
        critical_samples=[dict(time_s=samples[i]['time_s'],observed={k:samples[i].get(k) if samples[i].get(k) is not None else dict(status='unavailable') for k in observed},
            constraints=chosen[i],raw_reference=raw_ref,read_pointer=measurement.get('pointer','')+'/'+str(i),
            input_query=samples[i].get('input_query'),input_time_s=samples[i].get('input_time_s')) for i in sorted(chosen)],
        input_bounds_summary=dict(measured_min_n=[min(x) for x in zip(*inputs)],measured_max_n=[max(x) for x in zip(*inputs)],
            limits_n=limits,touches_upper_bound=[any(abs(u[j]-hi)<=1e-9 for u in inputs) for j,hi in enumerate(limits)],
            raw_query=dict(reference=measurement.get('input_reference',raw_ref),pointer='' if measurement.get('input_reference') else '/samples'),
            phase=measurement.get('input_phase','Saved replay sample input'),acceptance_component=row['constraints'].get('force_bounds')) if inputs else dict(status='unavailable'),
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
            if depth>5:return dict(keys=list(v),read_pointer=path)
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
        read_queries=[dict(reference=reference,pointer=pointer+'/'+k.replace('~','~0').replace('/','~1'),
            view='range' if isinstance(v,list) else 'summary') for k,v in value.items()
            if isinstance(v,(dict,list)) and (not facts_only or k in ('parameters','acceptance','best'))][:6] if isinstance(value,dict) else [],
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
    if best:best['physical_diagnostic']=physical_diagnostic(host,best['reference'])
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
        measured_nmpc='Optional NMPC can control directly or supply a starting schedule for MuJoCo-direct. Use initialize_control method=baseline, candidate=current candidate, parent=same candidate, source=complete current-Study same-candidate NMPC result, without channel_map. Complete valid task failures remain useful. Only actually applied SI tensions are used, never unexecuted predictions or stitched incomplete traces. The new open-loop ZOH schedule is task_acceptance=unmeasured and needs full independent evaluation. NMPC is not a prerequisite for mathematics or control optimization.',
        capability_sequence='Current candidate-bound complete task_capability sequence via response_evidence; inherits no physical acceptance.',
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
    from tools.research.rl import allocation_feedback
    training=allocation_feedback(host)
    current['training_budget_details']=training
    current['training_budget']=dict(remaining_stages=training['remaining_stages'],
        remaining_allocatable_actions=training['remaining_allocatable_actions'],
        actions_per_trial=training['authorized_limits']['actions_per_trial'],
        remaining_evaluation_episodes=training['evaluation_capacity']['remaining_episodes'])
    current['task_accepted']=bool(s.get('success_gate'))
    current['candidate_status']=dict(generated_valid=len(s['candidates']),
        control_sources_initialized=len(s.get('control_initializations',[])),
        mathematical_evaluations=len(s.get('analysis_results',[]))+len(s.get('mechanics_results',[])),
        independent_physical_evaluations=sum(len(s.get(k,[])) for k in ('results','physical_replays','rl_evaluations')),
        has_executable_candidate=bool(s['candidates']),task_passed=current['task_accepted'])
    current['candidate_status']['has_measured_task_feedback']=bool(current['candidate_status']['independent_physical_evaluations'])
    current['research_information']='Compilation establishes structure validity only. Creating structures adds candidate information; completed mathematical analysis or independent physical evaluation adds task-performance evidence. Neither compilation nor control initialization establishes task success.'
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
            if value.get('acceptance'):
                current['latest_scientific_feedback']['physical_diagnostic']=physical_diagnostic(host,latest)
    current['evidence_working_set']=working_set(host,current)
    return current


def read_coverage(host):
    """Only paired successful feedback counts as delivery; summary is never full."""
    import json
    from tools.research.contracts import EvidenceQuery
    rows=[];events=host.store.events(host.run_id);deliveries={}
    confirmed={e['request_id'] for e in events if e['kind']=='r3_response' and 200<=host.store.artifact(e['outputs'][0]).get('http_status',0)<300}
    for event in events:
        if event['kind']!='r3_request' or event['request_id'] not in confirmed:continue
        wire=host.store.artifact(host.store.artifact(event['outputs'][0])['request'])
        for message in wire.get('messages',[]):
            if message.get('role')=='tool':deliveries.setdefault(message.get('tool_call_id'),[]).append(message.get('content'))
    for event in events:
        if event['kind']!='model_original_tool_feedback':continue
        saved=host.store.artifact(event['outputs'][0]);use=saved['tool_use'];result=saved['result']
        if use['name']!='evidence_read' or result.get('status')!='success' or result.get('toolUseId')!=use['toolUseId']:continue
        try:
            default='summary' if state(host)['spec'].get('research_decisions',{}).get('context_limits') else 'full'
            q=EvidenceQuery.model_validate({'view':default,**use['input']})
            delivered=json.loads(''.join(b.get('text','') for b in result['content']))
            provided=any(content==''.join(b.get('text','') for b in result['content']) for content in deliveries.get(use['toolUseId'],[]))
            expected=None
            if q.view!='working_set':
                expected=host.store.artifact(q.reference)
                if isinstance(expected,bytes):expected=json.loads(expected)
                for part in q.pointer[1:].split('/') if q.pointer else []:
                    part=part.replace('~1','/').replace('~0','~');expected=expected[int(part)] if isinstance(expected,list) else expected[part]
                if q.view=='fields':expected={k:expected[k] for k in q.fields}
                elif q.view=='range':expected=dict(total=len(expected),start=q.start,items=expected[q.start:q.start+q.count])
            complete=provided and q.view in ('full','fields','range') and delivered==expected
        except (ValueError,KeyError,IndexError,TypeError):continue
        query=plain(q);classification='new_query'
        for prior in rows:
            if query==prior['query'] and prior['successfully_provided'] and (q.view!='working_set' or prior['delivery_identity']==digest(delivered)):classification='exact_repeat';break
            if plain(q.reference)!=prior['query']['reference'] or not prior['complete_data']:continue
            p=prior['query'];prefix=p['pointer']
            if p['view']=='full' and (q.pointer==prefix or q.pointer.startswith(prefix+'/')):classification='covered_subnode'
            if p['view']=='fields' and any(q.pointer==prefix+'/'+k.replace('~','~0').replace('/','~1') or
                q.pointer.startswith(prefix+'/'+k.replace('~','~0').replace('/','~1')+'/') for k in p['fields']):classification='covered_subnode'
            if p['view']=='fields' and q.view=='fields' and q.pointer==prefix and set(q.fields)<=set(p['fields']):classification='covered_subnode'
            if p['view']=='range' and q.pointer==prefix and q.view=='range' and p['start']<=q.start and q.start+len(delivered.get('items',[]))<=p['start']+prior['item_count']:
                classification='covered_subnode'
            if p['view']=='range' and q.pointer.startswith(prefix+'/'):
                index=q.pointer[len(prefix)+1:].split('/')[0]
                if index.isdecimal() and p['start']<=int(index)<p['start']+prior['item_count']:classification='covered_subnode'
        rows.append(dict(query=query,owning_study=host.run_id,tool_call_id=use['toolUseId'],feedback_reference=event['outputs'][0],
            retrieval_view=q.view=='working_set',delivery_identity=digest(delivered),
            successfully_provided=provided,complete_data=complete,item_count=len(delivered.get('items',[])) if q.view=='range' and isinstance(delivered,dict) else None,
            full_artifact=complete and q.view=='full' and not q.pointer,
            classification=classification))
    return rows


def ordered_candidates(host,s):
    known=list(s['candidates'].values());ordered=[]
    for event in host.store.events(host.run_id):
        if event['kind']=='candidate_constructed':
            for ref in event['outputs']:
                if ref in known and ref not in ordered:ordered.append(ref)
    return [*ordered,*[ref for ref in known if ref not in ordered]]


def resolved_candidate_facts(candidate,reference):
    cfg=candidate['configuration'];robot=cfg['robot']['structure']['data']
    return dict(candidate=reference,source=dict(reference=reference,pointer='/configuration'),
        segments=[{k:c.get(k) for k in ('id','length_m','physics','sections','natural_curvature_rad_m','connection')}
            for c in robot['components'] if c['kind']=='flexible_segment'],
        tendon_order=[t['id'] for t in robot['tendons']],
        frame=cfg['robot'].get('frame'),mount=cfg['task']['environment']['data'].get('mount'),
        target_world_m=cfg['task']['goal']['data'].get('target_m'),
        coordinate_scope='Mount pose maps the robot base into world; world origin and mounted base are distinct.',
        units=dict(length='m',density='kg/m^3',young_modulus='Pa',bending_viscosity='N*m^2*s'))


def recorded_changes(before,after,path=''):
    if before==after:return []
    if isinstance(before,dict) and isinstance(after,dict):
        return [r for key in sorted(before.keys()|after.keys())
            for r in recorded_changes(before.get(key),after.get(key),path+'/'+key.replace('~','~0').replace('/','~1'))]
    if isinstance(before,list) and isinstance(after,list) and len(before)==len(after):
        return [r for i,(a,b) in enumerate(zip(before,after)) for r in recorded_changes(a,b,path+'/'+str(i))]
    return [dict(pointer=path,before=before,after=after)]


def working_set(host,current):
    """Recomputable bounded Store projection; science and next-method choice stay separate."""
    from tools.research.candidate_portfolio import ranking_key
    from tools.research.evidence_policy import registered_references
    s=state(host);candidates=ordered_candidates(host,s);index=[];links=[];facts=[];comparisons=[]
    references=current['all_fresh_results'];coverage=read_coverage(host)
    shown=candidates[-3:];best=current.get('best_valid') or {};important=best.get('executable_candidate',best.get('candidate'))
    if important in candidates and important not in shown:shown=[*shown[-2:],important]
    for candidate in shown:
        c=host.store.artifact(candidate);results=[];math=[]
        controls=[e['source'] for e in s.get('control_initializations',[]) if e['candidate']==candidate]
        for ref in references:
            value=host.store.artifact(ref)
            if value.get('candidate',value.get('design_candidate'))!=candidate:continue
            if ref in [*s.get('analysis_results',[]),*s.get('mechanics_results',[])]:math.append(ref)
            if ref in [*s.get('results',[]),*s.get('physical_replays',[]),*s.get('rl_evaluations',[])]:results.append((ref,value))
        for source in controls[-3:]:
            control=host.store.artifact(source);tr=control['trajectory']
            links.append(dict(candidate=candidate,source=source,source_kind=control.get('source_kind'),
                trajectory_query=dict(reference=source,pointer='/trajectory'),
                grid=dict(intervals=len(tr['tensions_n']),start_s=tr['times_s'][0],end_s=tr['times_s'][-1],tendon_order=tr['tendon_order']),
                execution_references=[r for r,v in results if v.get('source_reference')==source]))
        for ref in math[-3:]:
            value=host.store.artifact(ref)
            links.append(dict(candidate=candidate,source=ref,evaluation_reference=ref,source_kind='mathematical_prediction',
                control_source=value.get('control_schedule_reference'),
                status=value.get('status'),operation=value.get('operation'),trajectory_query=dict(reference=ref,pointer='/trajectory') if value.get('trajectory') else None,
                task_acceptance='unmeasured'))
        valid=sorted((dict(reference=r,task_gap=task_gap(v)) for r,v in results if task_gap(v)['valid_complete']),key=ranking_key)
        residual=[r for r in s.get('compatible_residual_references',[]) if r['candidate']==candidate and r.get('available')]
        index.append(dict(candidate=candidate,structure_identity=c.get('physical_design_identity',c['identity']),
            profile_identity=c.get('profile_identity'),current_profile_identity=s['profile']['identity'],
            executable_under_current_profile=c.get('profile_identity')==s['profile']['identity'],
            resolved_facts=resolved_candidate_facts(c,candidate),
            parameters_query=dict(reference=candidate,pointer='/parameters'),
            structure=dict(segments=sum(p['kind']=='flexible_segment' for p in c['configuration']['robot']['structure']['data']['components']),
                tendons=len(c['configuration']['robot']['structure']['data']['tendons'])),
            generated=True,compiled=True,control_initialized=bool(controls),control_sources=controls,
            has_executable_control_source=bool(controls),has_explicit_control_schedule=bool(controls),
            has_completed_nmpc_execution=any(v.get('execution_id') and not v.get('source_reference') and not v.get('run_id') and task_gap(v)['valid_complete'] for r,v in results),
            has_measured_nmpc_reference=any(r['source_kind']=='nmpc' for r in residual),
            has_local_search_start=any(r.get('candidate')==candidate and r['action']=='control_search' and r['status']=='preflight_eligible' for r in current['decision_feedback']['actions']),
            has_residual_ppo_reference=bool(residual),methods_used=sorted({host.store.artifact(r).get('operation','mathematics') for r in math} |
                {'fixed_tension' if v.get('source_reference') else 'ppo' if v.get('run_id') else 'nmpc' for r,v in results}),
            mathematically_evaluated=any(host.store.artifact(r).get('status')=='computed' for r in math),mathematical_records=math,
            physically_evaluated=bool(valid),physical_records=[r for r,v in results],accepted=any(r['task_gap']['accepted'] for r in valid),
            best_valid=valid[0] if valid else None))
        for ref,value in results[-6:]:
            source=value.get('source_reference',ref);control=host.store.artifact(source);tr=control.get('trajectory') or {}
            links.append(dict(candidate=candidate,source=source,evaluation_reference=ref,
                data_access=__import__('tools.research.evidence_views',fromlist=['data_access']).data_access(host,ref,value),
                source_kind='fixed_tension' if value.get('source_reference') else 'policy' if value.get('run_id') else 'nmpc_actual_execution',
                trajectory_query=dict(reference=source,pointer='/trajectory') if tr else None,
                grid=dict(intervals=len(tr.get('tensions_n',[])),start_s=tr['times_s'][0],end_s=tr['times_s'][-1],tendon_order=tr.get('tendon_order')) if tr else dict(reference=ref,pointer='/profile'),
                task_gap=task_gap(value),original_acceptance=value.get('acceptance'),
                scope='Recorded execution; cross-structure differences cannot be attributed to control alone'))
        facts.extend(dict(reference=r,task_gap=task_gap(v),pointer='/acceptance',claim_kind='PHYSICAL_OBSERVATION') for r,v in results[-3:])
        recent=results[-6:]
        for (a,x),(b,y) in zip(recent,recent[1:]):
            xc=(x.get('acceptance') or {}).get('components',{});yc=(y.get('acceptance') or {}).get('components',{})
            comparable=bool(task_gap(x)['valid_complete'] and task_gap(y)['valid_complete'] and xc and
                {k:v.get('limit') for k,v in xc.items()}=={k:v.get('limit') for k,v in yc.items()} and
                x.get('profile_identity')==y.get('profile_identity') and x.get('evaluation_version')==y.get('evaluation_version'))
            comparisons.append(dict(candidate=candidate,baseline=a,variant=b,comparable=comparable,
                normalized_violation_change={k:v-task_gap(x)['components'][k] for k,v in task_gap(y)['components'].items()
                    if k in task_gap(x)['components']} if comparable else None,
                scope='Same candidate and recorded evaluation settings only; negative is improvement, no causal or global claim'))
    return dict(version='evidence_working_set_v2',candidate_index=index,candidate_count=len(candidates),
        candidate_index_query='All candidate references remain in source_references; previews retain the latest three',
        control_result_links=links,control_comparisons=comparisons,measured_facts=facts,read_coverage=coverage,read_coverage_count=len(coverage),
        read_counts={k:sum(r['successfully_provided'] and r['classification']==k for r in coverage) for k in ('exact_repeat','covered_subnode','new_query')},
        method_requirements={r['action']+('/'+r['method'] if r.get('method') else ''):
            {k:r[k] for k in ('remaining_checks','scope','requires_agent_fields') if k in r} for r in current['decision_feedback']['actions']},
        coverage_scope='Delivery is not understanding. Repeated queries remain legal; scientific question/intent is not inferred.',
        method_scope=dict(static_analysis='Constructs and checks operating points; local mathematical assumptions only. AnalysisRequest validates operation/point/window before workers.',
            offline_nlp='Predicted tension trajectories and search starts; independent physics still required.',
            nmpc='Optional closed-loop control and soft screening; numerical convergence, prediction and MuJoCo acceptance are separate. No verified model error bound means no structural hard veto. Cost is measured, not presumed low.',
            response_search='Finite differences of full physical rollouts; local information near evaluated coefficients.',
            pattern_search='Finite nongradient physical search; budget and full original acceptance remain authoritative.',
            direct_ppo='Independent optional policy training, without an NMPC prerequisite; published policies require separate evaluation.',
            residual_ppo='Requires a complete compatible reference, including failed-but-complete NMPC execution; predicted and measured references retain their origin.'),
        eligible_methods=[{k:v for k,v in r.items() if k not in ('remaining_checks','scope','requires_agent_fields','budget','remaining_backend_launches')}
            for r in current['decision_feedback']['actions']],budget=dict(current['budget'],training=current['training_budget_details'],
                method_remaining={k:v for k,v in current['method_remaining'].items() if k not in ('mathematical_evaluations','rl_stages')}),
        control_search_domain=current.get('control_search_domain'),
        source_references=list({r['artifact_id']:r for r in registered_references(host)}.values()),all_fresh_results=references,
        citation_eligibility=citation_inventory(host),action_trace=research_action_trace(host,limit=None),
        scientific_scope='No model-authored hypotheses are promoted to measured causes; only original independent acceptance establishes success')


def action_feedback(host,current):
    """Admission prerequisites for parameterized actions, not model decisions."""
    from tools.research.physical_replay import binding, verified_input_response, explicit_control_source, numerically_verified_source
    from tools.research.design import verify_candidate
    from tools.research.budget import protected, backend_capacity, decision_budget
    from tools.research.evidence_policy import registered_references
    s=state(host);rows=[];capacity=backend_capacity(host);known=registered_references(host)
    closed=s['research_status']=='stopped' or protected(host) or decision_budget(host)['closeout']['next_request_will_protect']
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
        from tools.research.rl import allocation_feedback, compatible_references
        rl_budget=allocation_feedback(host);refs=compatible_references(host,publish=False)
        for mode in ('direct','residual'):
            available=[r for r in refs if r['candidate']==candidate and r.get('available')]
            missing=[] if mode=='direct' or available else ['complete_exact_candidate_reference']
            rows.append(dict(action='research_rl',method=mode,candidate=candidate,
                status='unavailable' if closed or 'rl' not in s['spec']['capabilities']
                    or rl_budget['remaining_stages']==0 or rl_budget['remaining_allocatable_actions']==0
                    else 'blocked' if missing else 'prerequisites_only',
                reason=missing or None,references=available if mode=='residual' else [],budget=rl_budget,
                remaining_checks=['full_RLRequest','ideal_tension_reach_environment','aligned_allocation','training_capacity'],
                scope='Training/checkpoint is not task acceptance; direct PPO needs no reference'))
        rows.append(dict(action='initialize_control',method='baseline',candidate=candidate,
            status='preflight_eligible' if not closed and 'initialize_control' in current['actions'] else 'unavailable',
            task_acceptance='unmeasured',new_physical_evaluations=0,
            remaining_checks=['full_plan_admission','selected_control_settings'],
            requires_agent_fields=['decision','hypothesis','control_seed']))
        rows.append(dict(action='execute',method='nmpc',candidate=candidate,
            status='preflight_eligible' if not closed and 'execute' in current['actions'] and capacity>0 else 'unavailable',
            remaining_checks=['full_plan_admission','method_budget','replication_admission','scientific_preflight'],
            task_acceptance='unmeasured'))
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
    for row in rows:
        candidate=row.get('candidate')
        if candidate and host.store.artifact(candidate).get('profile_identity')!=s['profile']['identity']:
            row.update(status='blocked',reason='CANDIDATE_PROFILE_CHANGED: historical candidate retained under its original implementation profile',
                current_profile_compatible=False)
    return rows


def decision_brief(current):
    """Layer-one facts only; layer two is an exact recomputable Store view."""
    if 'evidence_working_set' not in current:return legacy_decision_brief(current)
    keys=('task_identity','task','capabilities','actions','task_accepted','candidate_status',
        'tool_readiness','all_fresh_results','control_initialization_methods')
    brief={k:deepcopy(current[k]) for k in keys if k in current}
    ws=current['evidence_working_set'];feedback=current['decision_feedback']
    anchor=next(iter(ws['source_references']),current.get('structure_domain'))
    brief['evidence_access']=dict(reference=anchor,view='working_set',pointer='',
        scope='Derived retrieval view, never scientific proof. JSON pointers select candidate_index, control_result_links, eligible_methods, read_coverage, source_references or citation_eligibility. Original references support full/fields/range reads.')
    brief['citation_eligibility']=dict(query=dict(reference=anchor,view='working_set',pointer='/citation_eligibility'),
        registered_count=len(ws['citation_eligibility']),latest_registered=deepcopy(ws['citation_eligibility'][-1:]),
        rule='supporting_evidence requires registration AND matching inference/candidate/task/model scope. Candidate/control identity is not task success. FamilySpace and unregistered raw motion samples are readable only; reading never registers evidence.',
        required_observations='Physical claims need a complete bound independent evaluation; mathematical claims need verified scoped results. STOP cites all_fresh_results; SELECT requires a read fresh pass.')
    brief['budget']=deepcopy(current['budget'])
    brief['budget']['method_remaining']={k:v for k,v in current['method_remaining'].items() if k not in ('mathematical_evaluations','rl_stages')}
    brief['budget']['training']=deepcopy(current['training_budget'])
    brief['best_valid']=None
    best=current.get('best_valid')
    if best:
        brief['best_valid']={k:deepcopy(best[k]) for k in ('reference','candidate','source','executable_candidate',
            'task_identity','historical_only','task_gap') if k in best}
        brief['best_valid']['violated_constraints']={k:v for k,v in best['constraints'].items() if not v['passed']}
        brief['best_valid']['physical_diagnostic']=diagnostic_brief(best['physical_diagnostic'])
    latest=deepcopy(current.get('latest_scientific_feedback'))
    if latest and latest.get('physical_diagnostic'):
        latest['physical_diagnostic']=dict(same_as='best_valid/physical_diagnostic') if best and latest['reference']==best['reference'] else diagnostic_brief(latest['physical_diagnostic'])
        latest.pop('constraints',None)
    brief['latest_scientific_feedback']=latest
    links=[]
    for row in ws['control_result_links']:
        item={k:row[k] for k in ('candidate','source','source_kind','evaluation_reference','status','operation','task_acceptance','task_gap','data_access') if k in row}
        if 'task_gap' in item:item['task_gap']={k:v for k,v in item['task_gap'].items() if k!='interpretation'}
        if row.get('original_acceptance'):
            item['constraints']={k:{f:v[f] for f in ('passed','value','limit') if f in v}
                for k,v in row['original_acceptance'].get('components',{}).items()}
        links.append(item)
    brief['evidence_working_set']=dict(version='evidence_working_set_summary_v2',
        candidate_count=ws['candidate_count'],candidate_index=deepcopy(ws['candidate_index']),
        control_result_links=links,control_comparisons=ws['control_comparisons'],
        method_scope=ws['method_scope'],scientific_scope=ws['scientific_scope'])
    definitions={};actions=[]
    for row in feedback['actions']:
        method=row['action']+('/'+row['method'] if row.get('method') else '')
        definitions.setdefault(method,{k:row[k] for k in ('remaining_checks','scope','requires_agent_fields') if k in row})
        item={k:row[k] for k in ('action','method','candidate','source','status','reason','response_evidence') if k in row}
        # References remain independently selectable without duplicating allocations or file paths.
        if row.get('references'):item['references']=[{k:r[k] for k in ('source','source_kind','available')} for r in row['references']]
        actions.append(item)
    brief.update(version='decision_brief_v2',method_requirements=definitions,available_research_actions=actions,
        recent_searches=feedback['recent_searches'],citation_rule=feedback['citation_rule'])
    return brief


def legacy_decision_brief(current):
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
        if domain and row['action']=='control_search':
            row['domain']={k:v for k,v in domain.items() if k not in ('candidate','source')}
    brief['citation_rule']=feedback['citation_rule']
    brief['version']='decision_brief_v1'
    return brief


def diagnostic_brief(value):
    return {k:deepcopy(value[k]) for k in ('evaluation_reference','candidate_reference','control_source_reference',
        'execution_status','task_passed','valid_complete','violated_constraints','critical_samples','limitations') if k in value}


def research_intent(host):
    """Rebuild the last decision and experiment from original plans and receipts."""
    import json
    s=state(host);latest=None;experiment=None
    for reference in reversed(s.get('plans',[])):
        saved=host.store.artifact(reference);plan=saved['original_plan']
        row=host.store.lookup(host.run_id,saved['request_id'])
        receipt=json.loads(row['receipt']) if row and row['receipt'] else None
        output=host.store.artifact(receipt['output']) if receipt and receipt.get('output') else {}
        result=output.get('result',output)
        item=dict(plan_reference=reference,action=plan['action'],
            candidate=plan_candidate(plan) or result.get('candidate'),
            agent_hypothesis={k:deepcopy(plan.get(k)) for k in ('hypothesis','decision',
                'expected_observation','weakening_observation','fixed_conditions',
                'interpretation','stopping_condition','supporting_evidence')},
            scope='Previous Agent intent and interpretation; not confirmed scientific facts',
            execution_status=receipt['execution_status'] if receipt else 'pending',
            actual_result=result.get('reference'),failure=output.get('error') or output.get('message'))
        if latest is None:latest=item
        if plan['action'] not in ('stop','select','diagnose'):
            experiment=item;break
    return dict(latest_decision=latest,last_research=experiment,
        unresolved_question=(experiment or latest or {}).get('agent_hypothesis',{}).get('weakening_observation'),
        question_scope='Prior falsification target; main Agent decides the next scientific question')


def plan_candidate(plan):
    return (plan.get('decision') or {}).get('selected_candidate') or plan.get('candidate') or next((
        plan[k]['candidate'] for k in ('control_search','physical_replay','cross_replay','mechanics','control_seed')
        if plan.get(k) and plan[k].get('candidate')),None)


def compact_intent(intent):
    """Retain the explicit current question once; no automatic truth/lifecycle claim."""
    value=deepcopy(intent)
    if value['latest_decision'] and value['last_research'] and value['latest_decision']['plan_reference']==value['last_research']['plan_reference']:
        value['last_research']=dict(same_as='research_intent.latest_decision',plan_reference=value['latest_decision']['plan_reference'])
    return value


def compact_action_trace(trace):
    value=deepcopy(trace)
    for row in value['recent']:
        for key in ('agent_hypothesis','interpretation_status','hypothesis_effect','task_protocol_identity'):
            row.pop(key,None)
    return value


def research_action_trace(host, limit=5):
    """Project original plans/receipts and rejected native actions; never infer causes."""
    import json
    from tools.research.reporter import RESULT_KEYS
    s=state(host);events=host.store.events(host.run_id);rows={}
    positions={r['artifact_id']:i for i,e in enumerate(events) for r in e['outputs']}
    known=[r for key in RESULT_KEYS for r in s.get(key,[])]
    def item(request_id,plan,source,position):
        row=host.store.lookup(host.run_id,request_id)
        receipt=json.loads(row['receipt']) if row and row['receipt'] else None
        output=host.store.artifact(receipt['output']) if receipt and receipt.get('output') else {}
        result=output.get('result',output)
        refs=output.get('scientific_results',[])
        if not refs and result.get('reference') in known:refs=[result['reference']]
        if not refs and receipt and receipt.get('output') in known:refs=[receipt['output']]
        decision=plan.get('decision') or {}
        return dict(request_id=request_id,action=plan.get('action',plan.get('operation')),
            method=decision.get('selected_method',('controlled-capability-sensitivity-v1' if plan.get('optimal_sensitivity') else plan.get('capability_method')) or plan.get('operation')),
            candidate=plan_candidate(plan) or result.get('candidate'),task_protocol_identity=digest(plan['protocol']) if plan.get('protocol') else None,
            agent_hypothesis={k:plan[k] for k in ('hypothesis','decision','expected_observation',
                'weakening_observation','supporting_evidence','interpretation','fixed_conditions','stopping_condition') if k in plan},
            execution_status=receipt['execution_status'] if receipt else 'pending',
            result_references=refs,receipt_output=receipt.get('output') if receipt else None,
            execution_id=receipt['execution_id'] if receipt else None,
            outcome={k:result[k] for k in ('status','task_passed','stop_reason','error') if k in result},
            source=source,_position=position)
    for ref in s.get('plans',[]):
        saved=host.store.artifact(ref);key=saved['request_id']
        rows[key]=item(key,saved['original_plan'],dict(reference=ref,pointer='/original_plan'),positions[ref['artifact_id']])
    for i,event in enumerate(events):
        if event['kind'] not in ('tool_request_error','model_original_tool_feedback'):continue
        value=host.store.artifact(event['outputs'][0]);use=value['tool_use']
        if use['name'] not in ('research_plan','research_analysis','research_rl','research_investigate'):continue
        key='native-'+use['toolUseId']+('-analysis' if use['name']=='research_analysis' else '')
        if key in rows:continue
        source=dict(reference=event['outputs'][0],pointer='/tool_use/input')
        rows[key]=item(key,{'action':use['name'],**use['input']},source,i)
        if use['name']=='research_analysis':
            prior=[r for r in rows.values() if r['_position']<i and r['agent_hypothesis']]
            rows[key]['prior_intent_source']=max(prior,key=lambda r:r['_position'])['source'] if prior else None
            rows[key]['hypothesis_effect']='unassessed; subsequent explicit Agent decision required'
        if event['kind']=='tool_request_error' or value.get('result',{}).get('status')=='error':
            # after_tool may persist a completed *protocol* receipt for a request
            # rejected before science admission. That is not a failed worker.
            rows[key]['execution_status']='failed' if rows[key]['execution_status']=='failed' else 'rejected'
    ordered=sorted(rows.values(),key=lambda r:r['_position'])
    for row in ordered:
        row.pop('_position')
        row['interpretation_status']='Agent interpretation or mechanism hypothesis; no causal verification inferred'
        row['distinguishing_observation_status']='saved_scientific_evidence_available' if row['result_references'] else 'no_saved_scientific_result_for_this_action'
    return dict(total=len(ordered),failed_or_rejected=sum(r['execution_status'] in ('failed','rejected') for r in ordered),
        recent=ordered[-limit:] if limit is not None else ordered,
        scope='Original Agent intent and recorded execution only; hypotheses are not confirmed or falsified by Reporter prose')


def public_prior_manifest(spec):
    """Frozen public engineering priors, separate from experimental observations."""
    contents=dict(family_space=spec['family_space'],task=spec['canonical_task'],
        control=spec['control'],analysis_protocol=spec['analysis_protocol'],
        mathematical_methods=spec.get('mathematical_methods',{}),
        models={k:spec['configuration']['policy'][k] for k in
            ('backend','dynamics_model','discretization','controller')})
    return dict(version='public_prior_manifest_v1',code_commit=spec['base_commit'],
        sources=spec['configuration_provenance'],contents=contents,content_identity=digest(contents),
        interpretation='Engineering defaults may carry historical design knowledge; initialization is not random or information-free. No historical experimental feedback is supplied.',
        comparison_rule='Comparison Agents must receive the same frozen public priors and resource conditions')


def mathematics_authorization(host,s):
    """Separate the frozen method grant, formal approval and input readiness."""
    approvals=[(e,host.store.artifact(e['outputs'][0])) for e in host.store.events(host.run_id)
        if e['kind']=='formal_study_authorization']
    valid=[(e,a) for e,a in approvals if a.get('user_approval') is True and a.get('scope_identity')==digest(a.get('scope'))
        and a.get('scope',{}).get('study_id')==host.run_id and a['scope'].get('resolved_identity')==s['spec']['resolved_identity']]
    approval=valid[-1] if valid else None
    methods=s['spec'].get('mathematical_methods',{})
    return dict(registered_study_scope_authorized=('registered mathematics' in approval[1]['scope'].get('execution_scopes',[])) if approval else None,
        approval_reference=approval[0]['outputs'][0] if approval else None,
        methods=[dict(method=key,frozen_method_grant=bool(value),configuration_description=value) for key,value in methods.items()],
        proposal_text_is_current_execution_gate=False,
        method_preconditions='Candidate/model-group/dependency and remaining-budget admission still required; authorization does not supply missing prerequisites.')


def agent_decision_brief(host):
    """A-line compact input; existing L0/L2 retrieval contracts remain unchanged."""
    from tools.research.reporter import current_reports, reporter_handoff_summary
    brief=decision_brief(context(host))
    intent=research_intent(host)
    brief['research_intent']=compact_intent(intent)
    brief['action_trace']=compact_action_trace(research_action_trace(host))
    s=state(host)
    brief['mathematics_authorization']=mathematics_authorization(host,s)
    if s.get('engineering_feedback_correction'):
        ref=s['engineering_feedback_correction']
        brief['recorded_evidence_corrections']=current_evidence_corrections(host.store.artifact(ref),ref)
    if s.get('public_prior_manifest'):
        brief['public_prior_manifest']=dict(reference=s['public_prior_manifest'],view='full',
            scope='Frozen engineering priors; no historical experimental feedback')
    if s['spec'].get('family_sensitivity_variables'):
        brief['family_sensitivity_conditions']=dict(
            authorized_variables=s['spec']['family_sensitivity_variables']['variables'],
            prerequisites=['Legal indices in the actual candidate','Authorized continuous variable',
                'Complete registered symmetric model group with exact bindings','Sufficient model-preparation and kernel budget'],
            scope='Generation legality alone does not establish mathematical method support')
    candidate=next((r['candidate'] for r in (intent['latest_decision'],intent['last_research']) if r and r.get('candidate')),None)
    candidate=candidate or (brief.get('latest_scientific_feedback') or {}).get('candidate')
    if candidate is None and len(s.get('candidates',{}))==1:candidate=next(iter(s['candidates'].values()))
    if candidate:
        from tools.research.task_constraints import mathematical_method_view, mathematical_catalog
        view=mathematical_method_view(host,candidate)
        brief['mathematical_capabilities']=mathematical_catalog(view)
        selected=((intent['latest_decision'] or {}).get('agent_hypothesis',{}).get('decision') or {}).get('selected_method')
        if selected in view['methods']:brief['selected_mathematical_method']=view['methods'][selected]
    else:
        brief['mathematical_capabilities']=dict(status='candidate_selection_required',
            query_format='evidence_read(reference=<owned candidate>, view="mathematical_capabilities", pointer="/methods/<method>")')
    selected=current_reports(host)[-2:]
    brief['latest_reports']=[reporter_handoff_summary(host,r,saved) for r,saved in selected]
    from tools.research.evidence_views import result_card
    shown=[ref for r in brief['latest_reports'] for ref in r['result_references']]
    brief['additional_mathematical_evidence']=[dict(reference=r,
        mathematics=mathematical_decision_view(plain(result_card(host,r))))
        for r in [*s.get('analysis_results',[]),*s.get('mechanics_results',[])][-3:] if r not in shown]
    latest=brief.get('latest_scientific_feedback')
    if latest and latest.get('reference') in shown:
        delivery=next(r for r in brief['latest_reports'] if latest['reference'] in r['result_references'])
        brief['latest_scientific_feedback']={k:latest[k] for k in
            ('reference','operation','status','candidate','source','control_handoff') if k in latest}
        brief['latest_scientific_feedback']['report_reference']=delivery['report_reference']
    elif latest and latest.get('reference') in [r['reference'] for r in brief['additional_mathematical_evidence']]:
        brief['latest_scientific_feedback']={k:latest[k] for k in
            ('reference','operation','status','control_handoff') if k in latest}
    anchor=brief.get('evidence_access',{}).get('reference')
    if anchor:
        brief['action_trace']['full_trace_query']=dict(reference=anchor,view='working_set',pointer='/action_trace')
        refs=brief.pop('all_fresh_results',[])
        brief['stop_result_index']=dict(count=len(refs),query=dict(reference=anchor,
            view='working_set',pointer='/all_fresh_results'),
            rule='Exact complete STOP citation index; retrieve on demand. Reports give no formal read credit.')
        brief.pop('citation_eligibility',None)
        ws=brief.get('evidence_working_set',{})
        for key in ('candidate_index','control_result_links','control_comparisons'):
            if key in ws:
                rows=ws.pop(key);ws[key+'_access']=dict(count=len(rows),
                    query=dict(reference=anchor,view='working_set',pointer='/'+key))
    return brief


def current_evidence_corrections(value, reference):
    """Current numerical corrections only; full history stays at its exact source."""
    mathematics=[]
    for row in value.get('mathematics',[]):
        summary=deepcopy(row['summary'])
        for diagnostic in summary.get('original_predicate_diagnostics',{}).values():
            diagnostic.pop('samples',None)
        mathematics.append(dict(reference=row['reference'],summary=summary,
            current_conclusion='Strict false with recorded residual magnitudes is not a proof of infeasibility; physical acceptance remains independent.'))
    controls=[]
    for row in value.get('historical_control_updates',[]):
        terminal=row.get('terminal_update',{})
        controls.append({k:deepcopy(row[k]) for k in ('reference','prediction_aggregate_available',
            'invalid_prediction_updates','accepted_plan_input_mismatch_updates','full_observations_query')} |
            dict(terminal_update={k:deepcopy(terminal.get(k)) for k in ('source','update_id',
                'optimization_raw_status','plan_accepted','failure_response_used','prediction_shape_invalid',
                'accepted_plan_matches_actual_input')},
                current_conclusion='Historical prediction aggregate unavailable for model-error analysis. Applied-input mismatch is distinct from fallback; configuration termination options are not observed solver outcomes.'))
    return dict(version='current_evidence_corrections_v1',source=reference,
        full_history_query=dict(reference=reference,pointer='',view='full'),
        mathematics=mathematics,historical_control_updates=controls,
        static_constructions=deepcopy(value.get('static_constructions',[])),
        reporter_saved_output_revalidation=deepcopy(value.get('reporter_saved_output_revalidation',[])),
        scope=value['scope'],
        interpretation='These corrections supersede conflicting prior Agent interpretations only. Original numbers, acceptance, task identities and past delivery history are unchanged. Mechanisms and counterfactual performance remain unknown.')


def mathematical_decision_view(card):
    """Core computed numbers and scope; all starts/samples remain in L2/L3."""
    math=card.get('mathematics')
    if not math:
        return card.get('deterministic_summary',{}).get('recorded_mathematics')
    claim=math['claim']
    summary=card['deterministic_summary']
    from tools.research.capability import signed_score_comparisons
    capability=summary.get('task_capability');compact=None
    if capability and capability.get('method_version'):
        compact={k:v for k,v in capability.items() if k!='solver'}
        compact['solver']={k:capability.get('solver',{}).get(k) for k in ('status','iterations','solve_time_s')}
    elif capability:
        starts=capability['solver_starts']
        compact={k:capability[k] for k in ('best_found_violation','score_semantics','verification_scope','solver_scope') if k in capability}
        compact['solver_termination']=dict(starts=len(starts),converged=sum(bool(s['success']) for s in starts),
            statuses=list(dict.fromkeys(s['status'] for s in starts)),
            max_iterations=max((s['iterations'] or 0 for s in starts),default=0),
            source=dict(reference=card['identity']['result']['reference'],pointer=capability['solver_starts_pointer']))
        compact['bottleneck']=capability.get('research_diagnostics',{}).get('bottleneck')
        compact['score_comparisons']=signed_score_comparisons(capability,card['identity']['result']['reference'])
    horizon=deepcopy(claim['horizon'])
    if 'trajectory_grid' in horizon:horizon['trajectory_grid'].pop('sample_steps',None)
    coverage=[{k:v for k,v in row.items() if not k.endswith('_indices')} |
        {k+'_count':len(v) for k,v in row.items() if k.endswith('_indices')} for row in claim['constraint_coverage']]
    result=dict(claim_source=math['claim_source'],requirement_source=math['requirement_source'],
        problem_definition=math['problem_definition'],
        scope=dict({k:claim[k] for k in ('model_declaration','computation_status','verification_status',
            'supported_interpretation','unsupported_conclusions')},horizon=horizon,constraint_coverage=coverage),
        operating_point={k:v for k,v in claim['operating_point'].items() if k in
            ('name','actual_time_s','time_s','remaining_task_s','phase','input_units')},
        quantities=[{k:v for k,v in q.items() if k!='conditions'} for q in math['quantities']
            if not capability or capability.get('method_version') or q['name'] in ('best_found_violation','optimal_task_violation')],
        capability=compact,unresolved=summary.get('decision_relevance'))
    if summary.get('optimal_sensitivity'):result['optimal_sensitivity']=summary['optimal_sensitivity']
    if summary.get('native_analysis'):
        result['native_analysis']={k:v for k,v in summary['native_analysis'].items() if k!='quantities'}
    if summary.get('recorded_static_construction'):result['recorded_static_construction']=summary['recorded_static_construction']
    if summary.get('optimal_sensitivity') or (capability and capability.get('method_version')):
        result['cost']=dict(evaluations=summary.get('evaluations'),numerical_s=summary.get('numerical_s'),
            sources=[dict(reference=card['identity']['result']['reference'],pointer='/'+key)
                for key in ('charged_analysis_evaluations','charged_numerical_s')])
    return result


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
    if isinstance(result,dict) and result.get('status')=='generated':
        candidate=host.store.artifact(result['candidate']);resolved=candidate['resolved_parameters']
        robot=candidate['configuration']['robot']['structure']['data']
        guides={c['id']:c for c in robot['components'] if c['kind']=='guide'}
        layout=[]
        for tendon in resolved['tendons'][:12]:
            p=tendon['points'][0];a=p['attachment']
            position=guides[a['part']]['guide_holes'][p['hole']] if p.get('hole') else a['position_m']
            layout.append(dict(tendon=tendon['id'],start_part=a['part'],start_position_m=position))
        spans=candidate['parameters'].get('spans') or [dict(first_segment=0,last_segment=len(resolved['segments'])-1,count=len(resolved['tendons']))]
        span_layout=[];offset=0
        for span in spans[:12]:
            span_layout.append(dict(first_segment=span.get('first_segment',0),last_segment=span['last_segment'],
                tendons=[t['id'] for t in resolved['tendons'][offset:offset+span['count']]]))
            offset+=span['count']
        view['structure_facts']=dict(candidate=result['candidate'],construction='compiled_valid',
            resolved_facts=resolved_candidate_facts(candidate,result['candidate']),
            scientific_acceptance='unmeasured',segment_count=len(resolved['segments']),
            tendon_count=len(resolved['tendons']),lengths_m=[p['length_m'] for p in resolved['segments']],
            spans=span_layout,layout=layout,layout_limit=12,
            checks_passed=['family_domain','section_route_clearance','tendon_attachment_clearance',
                'ordered_route_stations','guide_hole_clearance','guide_envelope','resolved_nonzero_spans'],
            minimum_clearance=dict(status='unavailable',reason='Not retained by original successful checks'),
            full_routes=dict(reference=result['candidate'],pointer='/resolved_parameters/tendons'),
            full_structure=dict(reference=candidate['configuration_reference'],pointer='/robot/structure/data'),
            control_source_initialized=any(e['candidate']==result['candidate'] for e in state(host).get('control_initializations',[])),
            mathematical_observations=[r for k in ('analysis_results','mechanics_results') for r in state(host).get(k,[]) if host.store.artifact(r).get('candidate')==result['candidate']],
            physical_observations=[r for k in ('results','physical_replays','rl_evaluations') for r in state(host).get(k,[]) if host.store.artifact(r).get('candidate')==result['candidate']])
        ordered=ordered_candidates(host,state(host));position=ordered.index(result['candidate'])
        if position:
            prior=ordered[position-1];old=host.store.artifact(prior)
            changes=recorded_changes(old['configuration']['robot']['structure']['data'],robot)
            view['structure_facts']['previous_candidate_comparison']=dict(candidate=prior,changed_paths=changes,
                changed_leaf_count=len(changes),causal_attribution='Unassessed; parameter differences do not establish single-factor causality')
    if reference in known and isinstance(raw,dict) and raw.get('acceptance'):
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
