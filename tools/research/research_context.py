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


def compact_evidence(value, reference, pointer=''):
    """Deterministic bounded preview; the exact Store artifact remains authoritative."""
    def preview(v,depth=0,path=pointer):
        if isinstance(v,list):
            items=[]
            for i,x in enumerate(v[:3]):
                if len(v)>3 and isinstance(x,dict):
                    fields=('reference','candidate','source','task_gap','label','time_s','tip_m','speed_m_s','position_error_m')
                    x={k:x[k] for k in fields if k in x} or dict(keys=list(x),read_pointer=path+'/'+str(i))
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
            best={k:best.get(k) for k in ('reference','candidate','source','task_gap','coefficients_n')},
            small_query=dict(pointer=pointer+'/best',view='fields',fields=[k for k in
                ('reference','candidate','source','task_gap','coefficients_n') if k in best]))
    if isinstance(value,dict) and 'acceptance' in value:
        summary.update(task_gap=task_gap(value),constraints=value['acceptance'].get('components',{}),
            limitations=['Only this recorded execution establishes its task outcome'])
    return dict(reference=reference,pointer=pointer,view='deterministic_summary',
        available_keys=list(value) if isinstance(value,dict) else None,summary=summary,
        retrieval='Display value/summary/preview are not Store path prefixes. All read_pointer values are absolute paths in reference. Use evidence_read(view=full,pointer=...). No acceptance transfer.',value=result)


def context(host):
    s=state(host);settings=s['spec'].get('research_decisions',{}).get('context_limits')
    current=legacy_context(host)
    if settings is not None:current=bounded_context(current,settings,s.get('control_initializations',[]))
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
        recent_observations=[compact_evidence(host.store.artifact(r),r)['summary'] | dict(reference=r)
            for r in [*s.get('results',[]),*s.get('physical_replays',[]),*s.get('rl_evaluations',[])][-3:]],
        actions=action_feedback(host,current),
        citation_rule='STOP must explain the outcome and explicitly cite all_fresh_results. This index does not record model reading or understanding.')
    return current


def action_feedback(host,current):
    """Admission prerequisites for parameterized actions, not model decisions."""
    from tools.research.physical_replay import binding
    from tools.research.budget import protected, backend_capacity
    s=state(host);rows=[];capacity=backend_capacity(host)
    closed=s['research_status']=='stopped' or protected(host)
    for entry in current['control_search_starts']:
        candidate=entry['candidate'];source=entry['source'];cfg=host.store.artifact(candidate)['configuration']
        for action in ('physical_replay','control_search'):
            reason=None;status='eligible'
            if closed or action not in current['actions'] or capacity<1:
                status='unavailable';reason='Protected/stopped state, action availability or shared backend capacity'
            elif action=='control_search' and cfg['task']['family']!='task.reach':
                status='not_applicable';reason='Current search requires reach-hold norm constraints'
            else:
                try:binding(cfg,host.store.artifact(source)['trajectory'])
                except ValueError as exc:status='blocked';reason=str(exc)
            rows.append(dict(action=action,status=status,candidate=candidate,source=source,reason=reason,
                remaining_backend_launches=capacity,minimum_new_launches=1,
                requires_agent_fields=['decision','hypothesis','finite search settings'] if action=='control_search' else ['decision','hypothesis'],
                scope='Candidate/source admission only; full typed Plan, budget and scientific preflight remain authoritative'))
    return rows


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
