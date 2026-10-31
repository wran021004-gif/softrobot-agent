"""Compact trusted research views and declared archive import using the existing Store."""
from copy import deepcopy
import json
from tools.platform_store import plain
from tools.state_io import digest
from tools.research.state import state, save, update
from tools.research.feedback import task_gap
from tools.research.evidence_policy import summarize_evidence, hypothesis_catalog, comparable_task, citation_inventory
from tools.research.scientific_intent import INTERFACES


def import_history(host):
    """Import hash-verified observations only; never promote historical execution IDs."""
    from tools.research.numerics import archived
    from tools.research.design import generate_candidate
    from tools.research.physical_replay import binding, schedule_identity
    s=state(host)
    if s.get('research_history_imported'):return
    # Background is read-only, including different-task evidence. It grants no
    # candidate, execution, acceptance, or current-task inference identity.
    background=list(s.get('scoped_context',[]))
    for item in s['spec']['research_decisions'].get('background',[]):
        for ref in [item['reference'],*item.get('dependencies',[])]:
            value=archived(item['folder'],ref,raw=ref.get('media_type','application/json')!='application/json')
            if save(host,value,'declared_historical_background')!=ref:raise ValueError('HISTORY_BACKGROUND_IDENTITY_MISMATCH')
            if ref==item['reference'] and ref not in background:background.append(ref)
    update(host,scoped_context=background)
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


def history_index(host,candidate=None,query=None):
    """Derived L1 conclusions over declared Store evidence, never a second ledger."""
    from tools.research.config import same_robot_structure
    s=state(host);rows=[]
    refs=[*[e['reference'] for e in s.get('research_history',[])],
        *s.get('research_mathematics',[]),*s.get('scoped_context',[]),
        *[r for e in s['spec'].get('research_decisions',{}).get('background',[]) for r in e.get('dependencies',[])
          if r.get('media_type','application/json')=='application/json']]
    current=host.store.artifact(candidate) if candidate else None
    for ref in {r['artifact_id']:r for r in refs}.values():
        value=host.store.artifact(ref)
        if not isinstance(value,dict) or not value.get('candidate'):continue
        tr=value.get('trajectory') or {};acceptance=value.get('acceptance') or {}
        if not acceptance.get('components') and not value.get('requested_operation'):continue
        old=host.store.artifact(value['candidate']);cfg=old['configuration']
        same_design=same_robot_structure(current['configuration'],cfg) if current else None
        if current and not same_design and current['configuration']['task']['goal']!=cfg['task']['goal']:continue
        same_task=comparable_task(s['spec'],cfg['task'])==s['spec'].get('canonical_task',s['base_configuration']['task'])
        recorded=value.get('requested_operation')
        method=tr.get('method_version') or ((recorded.get('capability_method') or recorded['operation']) if recorded else
            'fixed_tension' if value.get('source_reference') else 'ppo' if value.get('run_id') else 'nmpc')
        control=host.store.artifact(value['source_reference']) if value.get('source_reference') else {}
        provenance=control.get('provenance',{})
        if provenance.get('control_initialization'):method+=':'+provenance['control_initialization']
        scope=summarize_evidence(value,ref)
        equivalence='unknown'
        # A request/configuration match is a useful repeat hint, not proof of
        # identical rebuilt matrices, numerical environment, or control witness.
        if query and recorded and current:
            def request(q):
                from tools.research.contracts import AnalysisRequest
                return {k:v for k,v in plain(AnalysisRequest.model_validate(q)).items() if k!='candidate'}
            aligned=same_task and same_design and all(current['configuration']['policy'][k]==cfg['policy'][k]
                for k in ('controller','backend','discretization','dynamics_model'))
            if aligned and request(plain(query))==request(recorded):equivalence='same_configuration_and_request'
        if acceptance:
            result=dict(metrics=acceptance.get('metrics'),components=acceptance.get('components'),
                status=acceptance.get('status'),accepted=acceptance.get('accepted'))
        else:
            records=tr.get('replay',{}).get('records',[])
            result=dict(status=value.get('status'),conclusion=value.get('scoped_claim',{}).get('conclusion'),
                violation=tr.get('replayed_violation'),sampled_maxima={k:max(r['value'] for r in records if r['constraint_id']==k)
                    for k in dict.fromkeys(r['constraint_id'] for r in records)},control_witness=bool(tr.get('applied_input_n')))
        declarations=s['spec'].get('research_decisions',{})
        source=next((e for k in ('background','history','mathematics') for e in declarations.get(k,[]) if e['reference']==ref),{})
        intent=host.store.artifact(source['plan'])['original_plan'].get('hypothesis') if source.get('plan') else None
        rows.append(dict(candidate=value['candidate'],method=method,actual_result=result,
            research_question=(recorded or {}).get('operation','Independent reach/hold task evaluation'),
            original_agent_intent_excerpt=intent[:240] if intent else None,
            owning_study=value.get('owning_study'),historical_only=True,evidence_scope=scope['claim_kind'],
            cost=dict(accounting_scope='Historical reference only; no charge to the current Study',
                native=deepcopy(value.get('native_dynamics',{}).get('cost')),
                source_query=dict(reference=ref,view='summary')),
            task_match=same_task,design_match=same_design,repeat_hint=equivalence,experimental_equivalence='unknown',recorded_request=recorded,
            unresolved_question='Realization, aligned GVS/MuJoCo prediction, terminal braking and structural contributions remain unresolved; different controls cannot establish model error.',
            limitations=scope['unsupported_inferences'],control_source=value.get('source_reference'),
            mathematical_source=provenance.get('mathematical_result'),
            source=dict(reference=ref,view='full',pointer='',folder=source.get('folder'),plan=source.get('plan'),
                execution_files_query=dict(reference=ref,view='working_set',pointer='/historical_execution_files') if source.get('folder') and value.get('execution') else None)))
    return sorted(rows,key=lambda r:r['design_match'] is not True)


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


def legacy_context(host, *, evidence_references=None):
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
    references=([*s.get('research_mathematics',[]),*s.get('analysis_results',[]),*s.get('mechanics_results',[])]
        if evidence_references is None else evidence_references)
    evidence=[summarize_evidence(host.store.artifact(r),r) for r in references]
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
        control_search_usage='action=control_search, control_search={candidate,source,settings,adaptation_from?}; decision fields required. v2 dimensions come from schedule. Optional correction_window_s masks all changes outside the window. Registered Reach/Hold and timed Tracking norm constraints are supported; other tasks return not_applicable. Full original task always evaluated.')


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


def context(host, *, evidence_references=None):
    s=state(host);settings=s['spec'].get('research_decisions',{}).get('context_limits')
    current=legacy_context(host,evidence_references=evidence_references)
    if settings is not None:current=bounded_context(current,settings,s.get('control_initializations',[]))
    from tools.research.budget import decision_budget, closeout_operations
    current['budget']=decision_budget(host)
    if s['spec'].get('mode')!='engineering_numerical' and current['budget']['closeout']['next_request_will_protect']:
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
    analysis_metadata=[(r,host.store.artifact(r,paths=('candidate','operation','source_kind')))
        for r in s.get('analysis_results',[])]
    current['decision_feedback']=dict(
        recent_searches=[dict(reference=r,**compact_evidence(host.store.artifact(r),r)['summary'])
            for r in reversed(s.get('control_search_results',[])[-2:])],
        recent_observations=[compact_evidence(host.store.artifact(r),r)['summary'] | dict(reference=r)
            for r in reversed([*s.get('results',[]),*s.get('physical_replays',[]),*s.get('rl_evaluations',[])][-3:])],
        actions=action_feedback(host,current,analysis_metadata=analysis_metadata),
        citation_rule='STOP must explain the outcome and explicitly cite all_fresh_results. This index does not record model reading or understanding.')
    from tools.research.budget import decision_budget
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
                'owning_study','static_input_observation','input_response_observation','control_handoff','scoped_claim','analysis_applicability')}
            current['latest_scientific_feedback']['scientific_scope']={k:result['evidence_summary'][k]
                for k in ('claim_kind','verification_status','supported_inferences','unresolved')}
        else:
            current['latest_scientific_feedback']=dict(reference=latest,**compact_evidence(value,latest)['summary'])
            if value.get('acceptance'):
                current['latest_scientific_feedback']['physical_diagnostic']=physical_diagnostic(host,latest)
    current['evidence_working_set']=working_set(host,current,citation_references=evidence_references,analysis_metadata=analysis_metadata)
    return current


def confirmed_tool_deliveries(host):
    """Reuse confirmed Provider wires for exact tool feedback and summary markers."""
    import json
    from tools.research.session_handoff import packet_feedback
    events=host.store.events(host.run_id);deliveries={};summaries={}
    confirmed={e['request_id'] for e in events if e['kind']=='r3_response' and 200<=host.store.artifact(e['outputs'][0]).get('http_status',0)<300}
    for event in events:
        if event['kind']!='r3_request' or event['request_id'] not in confirmed:continue
        wire=host.store.artifact(host.store.artifact(event['outputs'][0])['request'])
        for message in wire.get('messages',[]):
            if message.get('role')=='tool':deliveries.setdefault(message.get('tool_call_id'),[]).append(message.get('content'))
            content=message.get('content')
            if message.get('role')=='user' and isinstance(content,str) and content.startswith('CURRENT_RESEARCH_PACKET\n'):
                packet=json.loads(content.split('\n',1)[1])
                research=packet.get('research',{})
                delivery=packet_feedback(research) or {}
                for item in delivery.get('items',[]):
                    if item['delivery']=='exact_feedback':
                        deliveries.setdefault(item['tool_id'],[]).append(''.join(b.get('text','') for b in item['result']['content']))
                    else:summaries.setdefault(item['tool_id'],[]).append(item.get('facts',{}))
    return deliveries,summaries


def read_coverage(host):
    """Only paired successful feedback counts as delivery; summary is never full."""
    import json
    from tools.research.contracts import EvidenceQuery
    rows=[];events=host.store.events(host.run_id)
    deliveries,summaries=confirmed_tool_deliveries(host)
    for event in events:
        if event['kind']!='model_original_tool_feedback':continue
        saved=host.store.artifact(event['outputs'][0]);use=saved['tool_use'];result=saved['result']
        if use['name']!='evidence_read' or result.get('status')!='success' or result.get('toolUseId')!=use['toolUseId']:continue
        try:
            default='summary' if state(host)['spec'].get('research_decisions',{}).get('context_limits') else 'full'
            q=EvidenceQuery.model_validate({'view':default,**use['input']})
            delivered=json.loads(''.join(b.get('text','') for b in result['content']))
            provided=any(content==''.join(b.get('text','') for b in result['content']) for content in deliveries.get(use['toolUseId'],[]))
            # Index metadata describes this read, not a change in scientific content.
            if q.view=='working_set' and q.pointer=='/all_fresh_results' and isinstance(delivered,dict) and delivered.get('index_kind')=='all_fresh_results':
                delivered=delivered['results']
            expected=None
            if q.view=='acceptance_certificate':
                from tools.research.core import read_evidence
                expected=read_evidence(host,plain(q),record_read=False)
            if q.view in ('full','summary','fields','range'):
                expected=host.store.artifact(q.reference)
                if isinstance(expected,bytes):expected=json.loads(expected)
                for part in q.pointer[1:].split('/') if q.pointer else []:
                    part=part.replace('~1','/').replace('~0','~');expected=expected[int(part)] if isinstance(expected,list) else expected[part]
                if q.view=='fields':expected={k:expected[k] for k in q.fields}
                elif q.view=='range':expected=dict(total=len(expected),start=q.start,items=expected[q.start:q.start+q.count])
            complete=provided and q.view in ('full','fields','range') and delivered==expected
            certificate=provided and q.view=='acceptance_certificate' and delivered==expected and expected.get('complete_acceptance_view') is True
        except (ValueError,KeyError,IndexError,TypeError):continue
        retained=delivered if provided and isinstance(delivered,dict) else {}
        if q.view=='mathematical_capabilities':
            for facts in summaries.get(use['toolUseId'],[]):
                retained={**retained,**facts.get('selected_value',{})}
            retained={k:v for k,v in retained.items() if isinstance(delivered,dict) and k in delivered and v==delivered[k]}
        query=plain(q);classification='new_query'
        for prior in reversed(rows):
            if query==prior['query'] and (prior['successfully_provided'] or prior.get('confirmed_field_identities')):
                classification='exact_repeat' if prior['delivery_identity']==digest(delivered) else 'changed_content';break
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
            retrieval_view=q.view in ('working_set','mathematical_capabilities','capabilities'),delivery_identity=digest(delivered),
            source_state_identity=saved.get('source_state_identity'),
            **(dict(confirmed_field_identities={k:digest(v) for k,v in retained.items()}) if q.view=='mathematical_capabilities' else {}),
            delivery_status=('complete_acceptance_certificate' if certificate else 'complete_fields' if complete else 'summary_or_derived_view') if provided else
                'summary_only' if use['toolUseId'] in summaries else 'not_confirmed_in_provider_request',
            successfully_provided=provided,complete_data=complete,item_count=len(delivered.get('items',[])) if q.view=='range' and isinstance(delivered,dict) else None,
            full_artifact=complete and q.view=='full' and not q.pointer,
            **(dict(formal_acceptance_view=certificate) if q.view=='acceptance_certificate' else {}),
            classification=classification))
    return rows


def result_index_progress(references, coverage):
    """Projection of original confirmed reads; index delivery grants no body credit."""
    reads=[r for r in coverage if r['query']['view']=='working_set' and r['query']['pointer']=='/all_fresh_results']
    confirmed=[r for r in reads if r['successfully_provided']]
    same=[r for r in confirmed if r['delivery_identity']==digest(references)]
    status='read_unchanged' if same else 'new_results' if confirmed else 'unread'
    bodies=[ref for ref in references if any(r['query']['reference']==ref and r['full_artifact'] for r in coverage)]
    return dict(status=status,last_confirmed_read=confirmed[-1]['classification'] if confirmed else None,
        current_index_confirmed=bool(same),pending_confirmation=bool(reads and not reads[-1]['successfully_provided']),
        result_count=len(references),complete_body_reads=bodies,unread_bodies=[r for r in references if r not in bodies],
        **(dict(formal_acceptance_reads=[r['query']['reference'] for r in coverage if r.get('formal_acceptance_view')]) if any(r.get('formal_acceptance_view') for r in coverage) else {}),
        scope='Index delivery is not a full scientific result read or independent SELECT qualification.')


def mathematical_read_progress(host, candidate, coverage, intent, *, method_view=None):
    """Current-candidate delivery facts from existing receipts/wires; no saved memory."""
    from tools.research.task_constraints import mathematical_method_view,mathematical_action_view
    latest=intent.get('latest_decision') or {};decision=(latest.get('agent_hypothesis') or {}).get('decision') or {}
    selected=decision.get('selected_method') if latest.get('candidate')==candidate else None
    reads=[r for r in coverage if r['query']['reference']==candidate and
        r['query']['view']=='mathematical_capabilities' and r['query']['pointer'].startswith('/methods/')]
    names=list(dict.fromkeys(r['query']['pointer'].split('/')[2] for r in reversed(reads)))
    if selected:names=[selected,*[k for k in names if k!=selected]]
    events=host.store.events(host.run_id)
    bindings=[host.store.artifact(e['outputs'][0]) for e in events if e['kind']=='analysis_request_binding']
    compiled=[b for b in bindings if b.get('version') in INTERFACES and
        b['full_request']['candidate']==candidate and (b.get('field_sources',{}).get('candidate') or {}).get('reference')==latest.get('plan_reference')]
    if compiled:
        selected=compiled[-1]['method'];names=[selected,*[k for k in names if k!=selected and k!=decision.get('selected_method')]]
    if not names:return []
    methods=(method_view if method_view is not None else mathematical_method_view(host,candidate))['methods']
    feedback={host.store.artifact(e['outputs'][0])['tool_use']['toolUseId']:host.store.artifact(e['outputs'][0])['result']['status']
        for e in events if e['kind']=='model_original_tool_feedback'}
    progress=[]
    for name in names[:3]:
        if name not in methods:continue
        detail=methods[name];action=mathematical_action_view(detail);fields={};template=False;confirmed=False
        for row in reads:
            if row['query']['pointer'].split('/')[2]!=name:continue
            hashes=row.get('confirmed_field_identities',{})
            confirmed=confirmed or row['successfully_provided'] or row['delivery_status']=='summary_only'
            if row['query']['pointer']=='/methods/'+name:fields.update(hashes)
            if row['query']['pointer']=='/methods/'+name+'/request_template':
                template=template or row['successfully_provided'] or all(hashes.get(k)==digest(v) for k,v in detail['request_template'].items())
        core=['method','scientific_purpose','planning_status','missing','next_submission','request_template_query',
            'required_parameters','estimated_evaluations','limitations']+(['scientific_inputs'] if 'scientific_inputs' in action else [])
        delivered=all(k in fields for k in core)
        changed=[k for k,v in fields.items() if k in action and v!=digest(action[k])]
        matching=[b for b in bindings if b['method']==name and b['full_request']['candidate']==candidate]
        result=any((v:=host.store.artifact(r,paths=('candidate','operation'))).get('candidate')==candidate and v.get('operation')==detail['operation']
            for r in state(host).get('analysis_results',[]))
        progress.append(dict(method=name,selected=selected==name,
            selection_source='ScientificQuestion compilation' if compiled and selected==name else 'Main Plan or method read',
            action_view='delivered' if delivered else 'summary_only' if confirmed else 'unconfirmed',
            control_source_prerequisites=('delivered' if 'scientific_inputs' in fields else 'unconfirmed') if 'scientific_inputs' in action else 'not_required',
            request_template='delivered' if template else 'unconfirmed',
            diagnose='completed' if selected==name and latest.get('action')=='diagnose' and latest.get('execution_status')=='completed' else 'not_submitted',
            mathematical_request='result_recorded' if result else 'rejected' if matching and feedback.get(matching[-1]['tool_use_id'])=='error' else 'submitted' if matching else 'not_submitted',
            relevant_content='changed_fields' if changed else 'delivered_fields_unchanged' if fields else 'unconfirmed',changed_fields=changed,
            scope='Confirmed action-field delivery, not full method text, understanding or scientific evidence. Rechecks remain optional.'))
    return progress


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


def working_set(host,current, *, citation_references=None, analysis_metadata=None):
    """Recomputable bounded Store projection; science and next-method choice stay separate."""
    from tools.research.candidate_portfolio import ranking_key
    from tools.research.evidence_policy import registered_references
    s=state(host);candidates=ordered_candidates(host,s);index=[];links=[];facts=[];comparisons=[]
    references=current['all_fresh_results'];coverage=read_coverage(host)
    metadata={r['artifact_id']:v for r,v in (analysis_metadata or [])}
    owners=[(ref,metadata[ref['artifact_id']] if ref['artifact_id'] in metadata and metadata[ref['artifact_id']].get('candidate')
        else host.store.artifact(ref,paths=('candidate','design_candidate'))) for ref in references]
    shown=candidates[-3:];best=current.get('best_valid') or {};important=best.get('executable_candidate',best.get('candidate'))
    if important in candidates and important not in shown:shown=[*shown[-2:],important]
    selected=decision_candidate(host,current,research_intent(host))
    if selected in candidates and selected not in shown:shown=[*shown[-2:],selected]
    for candidate in shown:
        c=host.store.artifact(candidate);results=[];math=[]
        controls=[e['source'] for e in s.get('control_initializations',[]) if e['candidate']==candidate]
        for ref,value in owners:
            if value.get('candidate',value.get('design_candidate'))!=candidate:continue
            if ref in [*s.get('analysis_results',[]),*s.get('mechanics_results',[])]:math.append(ref)
            if ref in [*s.get('results',[]),*s.get('physical_replays',[]),*s.get('rl_evaluations',[])]:results.append((ref,host.store.artifact(ref)))
        sources=[e['source'] for e in current['control_search_starts'] if e['candidate']==candidate and e['source'] not in controls]
        sources=[*sources,*controls]
        for source in sources[-3:]:
            control=host.store.artifact(source);tr=control['trajectory']
            provenance=control.get('provenance',{})
            prediction=next((r for r in math if host.store.artifact(r).get('control_schedule_reference')==source),None)
            historical=next((e for e in s.get('research_history',[]) if e['source'] in (source,provenance.get('source')) or e['reference']==provenance.get('source')),None)
            links.append(dict(candidate=candidate,source=source,source_kind=control.get('source_kind'),
                initialized=source in controls,full_control_sequence=True,task_acceptance=control.get('task_acceptance','unmeasured'),
                origin_reference=prediction or provenance.get('source') or provenance.get('mathematical_result'),
                origin_kind=provenance.get('source_kind') or provenance.get('method') or provenance.get('control_initialization'),
                origin_status='mathematical_prediction' if prediction else 'historical_measured_execution' if historical else 'measured_execution' if provenance.get('source_kind')=='measured_nmpc_execution_v1' else 'unmeasured_control_plan',
                historical_origin=bool(historical) or any(e['source']==provenance.get('source') for e in s['spec'].get('research_decisions',{}).get('control_seeds',[])),
                trajectory_query=dict(reference=source,view='full',pointer='/trajectory'),
                grid=dict(intervals=len(tr['tensions_n']),start_s=tr['times_s'][0],end_s=tr['times_s'][-1],tendon_order=tr['tendon_order']),
                execution_references=[r for r,v in results if v.get('source_reference')==source]))
        for ref in math[-3:]:
            value=host.store.artifact(ref)
            links.append(dict(candidate=candidate,source=ref,evaluation_reference=ref,source_kind='mathematical_prediction',
                initialized=value.get('control_schedule_reference') in controls if value.get('control_schedule_reference') else False,
                full_control_sequence=bool(value.get('control_schedule_reference')),
                control_source=value.get('control_schedule_reference'),
                status=value.get('status'),operation=value.get('operation'),trajectory_query=dict(reference=ref,pointer='/trajectory') if value.get('trajectory') else None,
                task_acceptance='unmeasured'))
        valid=sorted((dict(reference=r,task_gap=task_gap(v)) for r,v in results if task_gap(v)['valid_complete']),key=ranking_key)
        residual=[r for r in s.get('compatible_residual_references',[]) if r['candidate']==candidate and r.get('available')]
        index.append(dict(candidate=candidate,structure_identity=c.get('physical_design_identity',c['identity']),
            profile_identity=c.get('profile_identity'),current_profile_identity=s['profile']['identity'],
            executable_under_current_profile=c.get('profile_identity')==s['profile']['identity'],
            resolved_facts=resolved_candidate_facts(c,candidate),
            parameters_query=dict(reference=candidate,view='full',pointer='/parameters'),
            provenance_query=dict(reference=candidate,view='full',pointer='/provenance'),
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
            nmpc_sequence=False
            if not value.get('source_reference') and not value.get('run_id'):
                from tools.research.rl import measured_nmpc_trajectory
                try:measured_nmpc_trajectory(host,ref,bind_model=False);nmpc_sequence=True
                except (ValueError,KeyError):pass  # As in compatible_references, missing records are unavailable.
            links.append(dict(candidate=candidate,source=source,evaluation_reference=ref,
                data_access=__import__('tools.research.evidence_views',fromlist=['data_access']).data_access(host,ref,value),
                source_kind='fixed_tension' if value.get('source_reference') else 'policy' if value.get('run_id') else 'nmpc_actual_execution',
                initialized=source in controls,
                full_control_sequence=bool(tr) or nmpc_sequence,
                requires_initialization=nmpc_sequence,
                initialization_request=dict(action='initialize_control',control_seed=dict(candidate=candidate,parent=candidate,source=ref)) if nmpc_sequence else None,
                trajectory_query=dict(reference=source,view='full',pointer='/trajectory') if tr else None,
                grid=dict(intervals=len(tr.get('tensions_n',[])),start_s=tr['times_s'][0],end_s=tr['times_s'][-1],tendon_order=tr.get('tendon_order')) if tr else dict(reference=ref,pointer='/profile'),
                task_gap=task_gap(value),original_acceptance=value.get('acceptance'),
                scope='Recorded execution; cross-structure differences cannot be attributed to control alone'))
        facts.extend(dict(reference=r,task_gap=task_gap(v),pointer='/acceptance',claim_kind='PHYSICAL_OBSERVATION') for r,v in results[-3:])
        recent=results[-6:]
        for (a,x),(b,y) in zip(recent,recent[1:]):
            xc=(x.get('acceptance') or {}).get('components',{});yc=(y.get('acceptance') or {}).get('components',{})
            # Older fixed-tension receipts omitted the version of their bound candidate.
            versions=[v.get('evaluation_version',c.get('evaluation_version') if v.get('source_reference')
                and v.get('profile_identity')==c.get('profile_identity') else None) for v in (x,y)]
            comparable=bool(task_gap(x)['valid_complete'] and task_gap(y)['valid_complete'] and xc and
                {k:v.get('limit') for k,v in xc.items()}=={k:v.get('limit') for k,v in yc.items()} and
                x.get('profile_identity')==y.get('profile_identity') and versions[0] is not None and versions[0]==versions[1])
            comparisons.append(dict(candidate=candidate,baseline=a,variant=b,comparable=comparable,
                normalized_violation_change={k:v-task_gap(x)['components'][k] for k,v in task_gap(y)['components'].items()
                    if k in task_gap(x)['components']} if comparable else None,
                scope='Same candidate and recorded evaluation settings only; negative is improvement, no causal or global claim'))
    known=list({r['artifact_id']:r for r in registered_references(host)}.values())
    citation_totals={}
    if citation_references is not None:
        from tools.research.evidence_policy import citation_role
        last=known[-1:]
        citation_references=list({r['artifact_id']:r for r in citation_references if r not in last}.values())+last
        citation_totals=dict(citation_eligibility_counts=dict(registered_count=len(known),
            scientific_result_count=sum(citation_role(host,r,current=s,known=known) in
                ('scientific_result','independent_evaluation') for r in known)))
    return dict(version='evidence_working_set_v2',candidate_index=index,candidate_count=len(candidates),
        candidate_index_query='All candidate references remain in source_references; previews retain the latest three',
        control_result_links=links,control_comparisons=comparisons,measured_facts=facts,read_coverage=coverage,read_coverage_count=len(coverage),
        source_state_identity=digest(s),
        read_counts={k:sum(r['successfully_provided'] and r['classification']==k for r in coverage) for k in ('exact_repeat','covered_subnode','changed_content','new_query')},
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
        source_references=known,all_fresh_results=references,
        citation_eligibility=citation_inventory(host,references=citation_references),**citation_totals,
        research_history_index={r['source']['reference']['artifact_id']:r for r in history_index(host)},action_trace=research_action_trace(host,limit=None),
        recent_searches=current['decision_feedback']['recent_searches'],
        scientific_scope='No model-authored hypotheses are promoted to measured causes; only original independent acceptance establishes success')


def action_feedback(host,current, *, analysis_metadata=None):
    """Admission prerequisites for parameterized actions, not model decisions."""
    from tools.research.physical_replay import binding, verified_input_response, explicit_control_source, numerically_verified_source
    from tools.research.design import verify_candidate
    from tools.research.budget import protected, backend_capacity, decision_budget
    from tools.research.evidence_policy import registered_references
    s=state(host);rows=[];capacity=backend_capacity(host);known=registered_references(host)
    closed=s['research_status']=='stopped' or protected(host) or (current.get('budget') or decision_budget(host))['closeout']['next_request_will_protect']
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
    # warm_start rejects every other source kind before reading a trajectory.
    # Filter that invariant once, instead of decoding every large math result
    # again for each candidate and initialization mode. Admission stays below.
    if analysis_metadata is None:
        analysis_metadata=[(r,host.store.artifact(r,paths=('candidate','operation','source_kind'))) for r in s.get('analysis_results',[])]
    metadata={r['artifact_id']:v for r,v in analysis_metadata}
    warm_sources=[ref for ref in known if ref in s.get('mechanics_results',[]) or
        (metadata[ref['artifact_id']] if ref['artifact_id'] in metadata else host.store.artifact(ref,paths=('source_kind',))).get('source_kind') in ('verified_mathematical_trajectory',
            'historical_mathematical_trajectory','independently_integrated_control_v1')]
    for candidate in candidates:
        from tools.research.contracts import MechanicsRequest
        from tools.research.mechanics import warm_start
        from tools.research_tasks import task_adapter
        cfg=host.store.artifact(candidate)['configuration']
        execution=task_adapter(cfg).execution_requirements()
        unsupported=execution.get('unsupported_control_methods',[])
        from tools.research.rl import allocation_feedback, compatible_references
        rl_budget=allocation_feedback(host);refs=compatible_references(host,publish=False)
        for mode in ('direct','residual'):
            available=[r for r in refs if r['candidate']==candidate and r.get('available')]
            missing=[] if mode=='direct' or available else ['complete_exact_candidate_reference']
            rows.append(dict(action='research_rl',method=mode,candidate=candidate,
                status='not_applicable' if 'ppo' in unsupported else 'unavailable' if closed or 'rl' not in s['spec']['capabilities']
                    or rl_budget['remaining_stages']==0 or rl_budget['remaining_allocatable_actions']==0
                    else 'blocked' if missing else 'prerequisites_only',
                reason=execution.get('ppo',{}).get('reason',execution['applicability']) if 'ppo' in unsupported else missing or None,references=available if mode=='residual' else [],budget=rl_budget,
                remaining_checks=['full_RLRequest','ideal_tension_task_environment','aligned_allocation','training_capacity'],
                scope='Training/checkpoint is not task acceptance; direct PPO needs no reference'))
        rows.append(dict(action='initialize_control',method='baseline',candidate=candidate,
            status='preflight_eligible' if not closed and 'initialize_control' in current['actions'] else 'unavailable',
            task_acceptance='unmeasured',new_physical_evaluations=0,
            remaining_checks=['full_plan_admission','selected_control_settings'],
            requires_agent_fields=['decision','hypothesis','control_seed']))
        rows.append(dict(action='execute',method='nmpc',candidate=candidate,
            status='not_applicable' if 'nmpc' in unsupported else 'preflight_eligible' if not closed and 'execute' in current['actions'] and capacity>0 else 'unavailable',
            reason=execution['applicability'] if 'nmpc' in unsupported else None,
            remaining_checks=['full_plan_admission','method_budget','replication_admission','scientific_preflight'],
            task_acceptance='unmeasured'))
        requirements=task_adapter(cfg).analysis_requirements({})
        applicable=all(c.kind=='norm_bound' and c.signal.name in ('tip_position','tip_velocity') for c in requirements.constraints)
        modes=MechanicsRequest.model_json_schema()['properties']['initialization']['enum'];warm=[]
        for source in warm_sources:
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
        references=[r for r,value in analysis_metadata if value.get('candidate')==candidate
            and value.get('operation')=='input_sensitivity']
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
    anchor=current.get('structure_domain') or next(iter(ws['source_references']),None)
    brief['evidence_access']=dict(reference=anchor,view='working_set',pointer='',
        scope='Derived retrieval view, never scientific proof. JSON pointers select candidate_index, control_result_links, eligible_methods, read_coverage, source_references or citation_eligibility. Original references support full/fields/range reads.')
    brief['citation_eligibility']=dict(query=dict(reference=anchor,view='working_set',pointer='/citation_eligibility'),
        registered_count=ws.get('citation_eligibility_counts',{}).get('registered_count',len(ws['citation_eligibility'])),latest_registered=deepcopy(ws['citation_eligibility'][-1:]),
        scientific_result_count=ws.get('citation_eligibility_counts',{}).get('scientific_result_count',
            sum(r['role'] in ('scientific_result','independent_evaluation') for r in ws['citation_eligibility'])),
        empty_reference_rule='With no scientific results, exploratory empirical_search may use supporting_evidence=[]. Domain references and procedural knowledge do not support scientific conclusions. SELECT/STOP keep their original evidence gates.',
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
    brief['evidence_working_set']['read_state']=dict(completed_reads=len(ws['read_coverage']),
        read_counts=ws['read_counts'],recent=[dict(query=r['query'],delivery=r['delivery_status'],
            classification=r['classification'],content_identity=r['delivery_identity'],
            source_state_identity=r['source_state_identity'],
            source_state_status=('unchanged' if r['source_state_identity']==ws['source_state_identity'] else 'Query content change unverified; counters alone do not require rereading')
                if r['source_state_identity'] else 'immutable source or unrecorded state') for r in ws['read_coverage'][-3:]],
        full_list_query=dict(reference=anchor,view='working_set',pointer='/read_coverage'),
        rule='Exact repeats refer to previously delivered unchanged content. A changed whole-session identity alone does not require rereading: Provider counters, read markers and handoff metadata also change it. Read for a specific missing fact or to verify a relevant change. Dynamic views may change. For control identity use current_candidate.control_sources queries; read trajectories/ranges for needed detail. Rechecks remain allowed; delivery is not understanding.')
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


def tool_continuation(host):
    """Reconstruct navigation intent from existing events, separately from science."""
    recent=[];selection=None;plan_action=None;plan_selection=None
    for event in host.store.events(host.run_id):
        if event['kind']=='research_tool_route':
            route=host.store.artifact(event['outputs'][0])
            selection=dict(tool=route['tool'],action=route.get('action'),tool_use_id=route['tool_use_id'],sequence=event['sequence'],
                source=event['outputs'][0],status='selected_not_submitted')
            if route['tool']=='research_plan':
                plan_action=route['action'];plan_selection=deepcopy(selection)
        elif event['kind']=='model_original_tool_feedback':
            value=host.store.artifact(event['outputs'][0]);use=value['tool_use'];result=value['result']
            if use['name']=='research_route':continue
            if selection and use['name']==selection['tool']:
                selection={**selection,'status':'tool_feedback_recorded','feedback':event['outputs'][0]}
            if plan_selection and use['name']=='research_plan' and use['input'].get('action')==plan_action:
                plan_selection={**plan_selection,'status':'submission_feedback_recorded',
                    'feedback_status':result['status'],'feedback':event['outputs'][0]}
            entry=dict(tool=use['name'],tool_use_id=use['toolUseId'],status=result['status'],source=event['outputs'][0])
            if use['name']=='evidence_read':
                if len(json.dumps(use['input']).encode())<=700:entry['query']=use['input']
                else:entry['original_input_query']=dict(reference=event['outputs'][0],view='full',pointer='/tool_use/input')
            if result['status']=='error':
                try:detail=json.loads(''.join(b.get('text','') for b in result['content']))
                except ValueError:detail={}
                entry.update({k:detail[k] for k in ('error_code','expected') if k in detail})
            recent.append(entry);recent=recent[-4:]
    return dict(selection=selection,plan_action=plan_action,plan_selection=plan_selection,recent=recent,
        scope='Tool selection and navigation feedback only. No Plan submission or scientific execution is inferred.')


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
                'interpretation','stopping_condition','supporting_evidence','next_research_action')},
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


def decision_candidate(host,current,intent):
    """Display the recorded decision candidate, then feedback/latest construction."""
    return (next((r['candidate'] for r in (intent['latest_decision'],intent['last_research']) if r and r.get('candidate')),None)
        or (current.get('latest_scientific_feedback') or {}).get('candidate')
        or next(iter(reversed(ordered_candidates(host,state(host)))),None))


def compact_intent(intent):
    """Retain the explicit current question once; no automatic truth/lifecycle claim."""
    value=deepcopy(intent)
    if value['latest_decision'] and value['last_research'] and value['latest_decision']['plan_reference']==value['last_research']['plan_reference']:
        value['last_research']=dict(same_as='research_intent.latest_decision',plan_reference=value['latest_decision']['plan_reference'])
    return value


def compact_action_trace(trace):
    value=deepcopy(trace);rows=value['recent'];indices={0} if rows else set()
    for actions in (('generate','search','propose'),('research_analysis','mechanics'),
            ('physical_replay','execute'),('initialize_control','control_search','research_rl')):
        first=next((i for i,r in enumerate(rows) if r['action'] in actions and r['execution_status'] not in ('rejected','failed')),None)
        if first is not None:indices.add(first)
    indices.update(range(max(0,len(rows)-3),len(rows)))
    value['recent']=[{k:r[k] for k in ('action','method','execution_status','execution_kind','candidate','result_references','source','outcome') if k in r}
        for i,r in enumerate(rows) if i in indices]
    value['selection_scope']='First route, first recorded structure/math/physics/control outcomes and latest three; no causal interpretation'
    return value


def trace_entry(row):
    """One short factual line; original hypotheses and receipts stay in Store."""
    outcome=row['outcome'];execution=outcome.get('execution_feedback') or {}
    status=execution.get('status') or outcome.get('status') or row['execution_status']
    return dict(step=row['step'],action=row['action'],
        text='#'+str(row['step'])+' '+row['action']+((': '+row['method']) if row.get('method') else '')+'; '+str(status),
        execution_status=row['execution_status'],execution_kind=row['execution_kind'],
        scientific_result=bool(row['result_references']),
        scientific_execution=('not_started' if execution.get('scientific_execution_started') is False
            or outcome.get('scientific_execution_started') is False
            or row['execution_status']=='rejected' or row['execution_kind']=='read_only_diagnosis' else
            'result_recorded' if row['result_references'] else 'unknown; inspect original receipt'),
        unresolved=row['execution_status'] in ('failed','rejected','pending')
            or outcome.get('task_passed') is False or status in ('failed','unsupported','inconclusive','unresolved'))


def bounded_action_trace(trace, limit=8):
    rows=trace['recent'];recent=rows[-limit:];steps={r['step'] for r in recent}
    unresolved=[r for r in rows[:-limit] if r['execution_status'] in ('failed','rejected','pending')][-2:]
    return dict(version='research_trace_v1',total=trace['total'],recent=[trace_entry(r) for r in recent],
        unresolved=[trace_entry(r) for r in unresolved if r['step'] not in steps],
        page_query=dict(view='summary',offset=max(0,len(rows)-limit),limit=limit),
        recall='research_recall(step=<stable step>, view="summary" or "details"); omit step for paginated history.',
        scope='Recorded actions and actual statuses only. Request acceptance, computation, verification and physical acceptance are distinct.')


def milestone_trace(trace):
    """Select original event rows, never manufacture a narrative or causal link."""
    selected=[];seen=set()
    for row in trace['recent']:
        action=row['action'];status=row['execution_status']
        failure=status in ('failed','rejected','pending') or row['outcome'].get('task_passed') is False
        first=action in ('generate','propose','search','initialize_control') and status=='completed'
        key=(action,(row.get('candidate') or {}).get('artifact_id'))
        if row['result_references'] or failure or (first and key not in seen) or (action in ('select','stop') and status=='completed'):
            selected.append(row)
        if first:seen.add(key)
    return dict(total=len(selected),recent=selected,source_total=trace['total'])


def research_recall(host, query):
    """Navigate existing trace/source readers; never award formal evidence credit."""
    from tools.research.contracts import ResearchRecallQuery
    from tools.research.core import read_tool_evidence
    q=ResearchRecallQuery.model_validate(query);trace=research_action_trace(host,limit=None)
    rows=trace['recent']
    if q.trace=='milestones' and q.step is None:rows=milestone_trace(trace)['recent']
    if q.step is None:
        page=rows[q.offset:q.offset+q.limit]
        return dict(total=len(rows),items=[dict(**trace_entry(r),source=r['source'],
            receipt_output=r['receipt_output'],result_references=r['result_references']) for r in page],
            next_offset=q.offset+q.limit if q.offset+q.limit<len(rows) else None,formal_read_credit=False)
    row=next((r for r in rows if r['step']==q.step),None)
    if row is None:raise ValueError('RESEARCH_STEP_NOT_FOUND: use research_recall without step to list saved steps')
    source=row.get('feedback_source') or row['source']
    result=dict(**trace_entry(row),candidate=row.get('candidate'),source=source,
        receipt_output=row['receipt_output'],scientific_results=row['result_references'],formal_read_credit=False,
        detail_query=dict(step=q.step,view='details'),
        original_read_query=dict(reference=source['reference'],view='full',pointer=source['pointer']),
        scope='History navigation only. SELECT requires an explicit original whole-result evidence_read; STOP retains original admission.')
    if row['outcome'].get('error'):result['failure_excerpt']=str(row['outcome']['error'])[:400]
    if q.view=='details':
        if q.pointer and not q.pointer.startswith('/'):raise ValueError('JSON_POINTER_REQUIRED')
        original=(dict(reference=row['result_references'][0],pointer='') if row['result_references'] else source)
        read=dict(reference=original['reference'],view='full',pointer=original['pointer']+q.pointer)
        result['detail_source']=original
        if q.fields:read['fields']=q.fields;read['view']='fields'
        result['details']=read_tool_evidence(host,read,record_read=False)
    return result


def research_action_trace(host, limit=5):
    """Project original plans/receipts and rejected native actions; never infer causes."""
    import json
    from tools.research.reporter import RESULT_KEYS
    s=state(host);events=host.store.events(host.run_id);rows={}
    positions={r['artifact_id']:i for i,e in enumerate(events) for r in e['outputs']}
    requests={};feedback={}
    for event in events:
        if event['kind'] not in ('model_original_tool_request','model_original_tool_feedback'):continue
        value=host.store.artifact(event['outputs'][0]);use=value['tool_use']
        key='native-'+use['toolUseId']+('-analysis' if use['name']=='research_analysis' else '')
        if event['kind']=='model_original_tool_request':requests[key]=event['sequence']
        else:feedback[key]=dict(reference=event['outputs'][0],pointer='/result')
    known=[r for key in RESULT_KEYS for r in s.get(key,[])]
    def item(request_id,plan,source,position):
        row=host.store.lookup(host.run_id,request_id)
        if row is None and request_id.endswith('-analysis'):
            row=host.store.lookup(host.run_id,request_id.removesuffix('-analysis'))
        receipt=json.loads(row['receipt']) if row and row['receipt'] else None
        output=host.store.artifact(receipt['output']) if receipt and receipt.get('output') else {}
        if 'toolUseId' in output and 'content' in output:
            try:output=json.loads(''.join(b.get('text','') for b in output['content']))
            except ValueError:output={}
        result=output.get('result',output)
        refs=output.get('scientific_results',[])
        if not refs and result.get('reference') in known:refs=[result['reference']]
        if not refs and receipt and receipt.get('output') in known:refs=[receipt['output']]
        decision=plan.get('decision') or {}
        return dict(request_id=request_id,step=requests.get(request_id,events[position]['sequence']),
            **(dict(feedback_source=feedback[request_id]) if request_id in feedback else {}),
            action=plan.get('action',plan.get('operation')),
            method=decision.get('selected_method',('controlled-capability-sensitivity-v1' if plan.get('optimal_sensitivity') else plan.get('capability_method')) or plan.get('operation')),
            candidate=plan_candidate(plan) or result.get('candidate'),task_protocol_identity=digest(plan['protocol']) if plan.get('protocol') else None,
            agent_hypothesis={k:plan[k] for k in ('hypothesis','decision','expected_observation',
                'weakening_observation','supporting_evidence','interpretation','fixed_conditions','stopping_condition') if k in plan},
            execution_status=receipt['execution_status'] if receipt else 'pending',
            result_references=refs,receipt_output=receipt.get('output') if receipt else None,
            execution_id=receipt['execution_id'] if receipt else None,
            outcome={**{k:result[k] for k in ('status','task_passed','stop_reason','error','execution_feedback','scientific_execution_started','worker_started','error_code') if k in result},
                **(dict(local_diagnostic_completed=True) if result.get('local_comparison') else {})},
            source=source,_position=position)
    for ref in s.get('plans',[]):
        saved=host.store.artifact(ref);key=saved['request_id']
        rows[key]=item(key,saved['original_plan'],dict(reference=ref,pointer='/original_plan'),positions[ref['artifact_id']])
    for i,event in enumerate(events):
        if event['kind'] not in ('tool_request_error','model_original_tool_feedback','model_original_tool_request'):continue
        value=host.store.artifact(event['outputs'][0]);use=value['tool_use']
        if use['name'] not in ('research_plan','research_analysis','research_rl','research_investigate'):continue
        key='native-'+use['toolUseId']+('-analysis' if use['name']=='research_analysis' else '')
        if event['kind']=='model_original_tool_request' and key in feedback:continue
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
            if event['kind']=='tool_request_error' and 'message' in value:
                rows[key]['outcome']['error']=value['message'][:1000]
                rows[key]['outcome']['error_reference']=event['outputs'][0]
    ordered=sorted(rows.values(),key=lambda r:r['step'])
    for row in ordered:
        row.pop('_position')
        row['execution_kind']=('request_rejected_before_science' if row['execution_status']=='rejected' else
            'scientific_result_recorded' if row['result_references'] else
            'failed_request; inspect worker receipt/progress for actual computation' if row['execution_status']=='failed' else
            'local_diagnostic_completed' if row['outcome'].get('local_diagnostic_completed') or row['outcome'].get('execution_feedback',{}).get('status')=='local_diagnostic_completed' else
            'read_only_diagnosis' if row['action']=='diagnose' and row['outcome'].get('status')=='read_only_diagnosis' else
            'pending_receipt' if row['execution_status']=='pending' else 'protocol_receipt_only; no scientific result recorded')
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
    valid=[(e,a) for e,a in approvals if a.get('user_approval') and a.get('scope_identity')==digest(a.get('scope'))
        and a.get('scope',{}).get('study_id')==host.run_id and a['scope'].get('resolved_identity')==s['spec']['resolved_identity']]
    approval=valid[-1] if valid else None
    methods=s['spec'].get('mathematical_methods',{})
    return dict(registered_study_scope_authorized=('registered mathematics' in approval[1]['scope'].get('execution_scopes',[])
        or 'analysis' in approval[1]['scope'].get('capabilities',[])) if approval else None,
        approval_reference=approval[0]['outputs'][0] if approval else None,
        methods=[dict(method=key,frozen_method_grant=bool(value),configuration_description=value) for key,value in methods.items()],
        proposal_text_is_current_execution_gate=False,
        method_preconditions='Candidate/model-group/dependency and remaining-budget admission still required; authorization does not supply missing prerequisites.')


def controller_capabilities(host):
    """Existing frozen controller owner; large schema is retrieved through L1."""
    from tools.research_tasks import task_adapter
    spec=state(host)['spec'];controller=spec['configuration']['policy']['controller']
    return dict(recipe_defaults=controller['parameters']['data']['recipe'],
        frozen_replan_period_s=spec.get('nmpc_replan_period_s'),
        task_reference=task_adapter(spec['configuration']).control_reference(),
        ppo=task_adapter(spec['configuration']).ppo_applicability(),
        parameter_schema=host.reg.get(controller['extension_id'],controller['version'],'controller').input_schema.model_json_schema(),
        solver_defaults=controller['parameters']['data'].get('solver'),
        patch='Generation v2 controller_recipe/controller_solver sparse patches use registered owner validation; settling remains task-owned')


def current_research_state(host, brief, intent, trace, coverage=None, *, method_view=None):
    """Describe existing provenance/receipts; never select a scientific direction."""
    s=state(host);candidate=brief.get('current_candidate') or {};ref=candidate.get('candidate')
    provenance=host.store.artifact(ref).get('provenance',{}) if ref else {}
    owner=provenance.get('decision_owner')
    if owner not in ('Main','Operator','historical'):
        owner=('Main' if provenance.get('origin')=='model' and provenance.get('plan') in s.get('plans',[]) else
            'historical' if provenance.get('origin') in ('engineering_history_materialization','initial_controller_reference') else 'unknown')
    completed=[]
    for key,label in (('compiled','legal_candidate_compiled'),('control_initialized','control_initialized'),
            ('mathematically_evaluated','mathematical_result_recorded'),('physically_evaluated','independent_task_evaluated')):
        if candidate.get(key):completed.append(label)
    if brief.get('experience_read_progress'):completed.append('Knowledge_read_receipt_recorded')
    latest=intent.get('latest_decision') or {};hypothesis=latest.get('agent_hypothesis') or {}
    if hypothesis.get('hypothesis'):completed.append('Main_hypothesis_recorded')
    if latest.get('action')=='diagnose' and latest.get('execution_status')=='completed':completed.append('diagnose_plan_completed')
    continuation=brief.get('tool_continuation') or {};selection=continuation.get('selection') or {}
    rows=trace['recent'];last=rows[-1] if rows else {}
    status=('request_rejected' if last.get('execution_status') in ('rejected','failed') else
        'pending' if last.get('execution_status')=='pending' else 'request_submitted' if last else None)
    if last.get('result_references'):
        physical=[*s.get('results',[]),*s.get('physical_replays',[]),*s.get('rl_evaluations',[])]
        status='physical_result_recorded' if any(r in physical for r in last['result_references']) else 'mathematical_result_recorded'
    source=last.get('source')
    if selection.get('status')=='selected_not_submitted' and selection.get('sequence',0)>last.get('step',0):
        status='tool_selected_not_submitted';source=selection.get('source')
    closeout=brief['budget'].get('closeout',{}).get('next_request_will_protect',False)
    phase='pending' if s.get('pending') else 'budget_closeout' if closeout else 'research'
    if s.get('pending'):status='pending'
    unresolved=[]
    if hypothesis.get('weakening_observation') and not latest.get('actual_result'):
        unresolved.append(dict(text=hypothesis['weakening_observation'][:240],source=latest['plan_reference'],
            scope='Main falsification target; unresolved until Main assesses evidence'))
    if last.get('execution_status') in ('rejected','failed'):
        outcome=last['outcome']
        unresolved.append(dict(tool_feedback=outcome.get('error') or outcome.get('error_code') or outcome.get('status'),source=last['source']))
    progress=mathematical_read_progress(host,ref,coverage if coverage is not None else read_coverage(host),intent,method_view=method_view) if ref else []
    from tools.research.state import protected,readable_results
    provenance_readable=ref and (not (closeout or protected(host)) or ref in readable_results(s,host))
    return dict(phase=phase,object=dict(candidate=ref,origin=owner,
            provenance_query=dict(reference=ref,view='full',pointer='/provenance') if provenance_readable else None,
            compiled=bool(candidate.get('compiled')),control_initialized=bool(candidate.get('control_initialized')),
            mathematical_result=bool(candidate.get('mathematically_evaluated')),
            independently_evaluated=bool(candidate.get('physically_evaluated')),
            task_acceptance='accepted' if candidate.get('accepted') else 'not_accepted' if candidate.get('physically_evaluated') else 'unmeasured'),
        completed=completed,methods_read=[r['method'] for r in progress if r['action_view']!='unconfirmed'],
        mathematical_read_progress=progress,
        last_effective_action=dict(status=status or phase,action=selection.get('action') if status=='tool_selected_not_submitted' else last.get('action'),source=source),
        unresolved=unresolved,
        scope='Descriptive current-Study facts, not a required research sequence. Historical Knowledge is not current task evidence.')


def mathematical_discovery_observations(host, current, candidate):
    """Read existing scoped results and frozen-task observations, without a solve.

    Native extrema reuse the original task proxy on saved outputs. This is a
    descriptive read: no integration, score optimization or acceptance credit.
    """
    from tools.research.evidence_views import result_card
    from tools.research.nonlinear_capability import sampled_constraints
    from schemas.platform_analysis import TaskAnalysisRequirement
    s=state(host);observations=[];latest=None
    for reference in reversed(s.get('analysis_results',[])):
        raw=host.store.artifact(reference,paths=('candidate','status','scoped_claim'))
        if raw.get('candidate')!=candidate or raw.get('status')!='computed' or not raw.get('scoped_claim'):continue
        raw=host.store.artifact(reference)
        card=plain(result_card(host,reference));summary=card['deterministic_summary']
        outputs=(raw.get('native_dynamics',{}).get('optimization',{}).get('best') or {}).get('outputs')
        if outputs:
            samples=sampled_constraints(outputs,TaskAnalysisRequirement.model_validate(raw['task_analysis']))
            for key in dict.fromkeys(r['constraint_id'] for r in samples):
                r=max((r for r in samples if r['constraint_id']==key),key=lambda r:r['normalized_signed_excess'])
                observations.append(dict(constraint_id=key,value=r['value'],unit=r['units'],threshold=r['limit'],
                    passed=r['normalized_signed_excess']<=0,scope='model_sample',time_s=r['time_s'],
                    source=dict(reference=reference,pointer='/native_dynamics/optimization/best/outputs')))
        else:
            constraints={c['constraint_id'] for c in raw.get('task_analysis',{}).get('constraints',[])}
            observations=[dict(constraint_id=r['name'],value=r['value'],unit=r['unit'],threshold=r['threshold'],
                passed=r['passed'],scope=r['scope'],source=r['source']) for r in card['metrics'] if r['name'] in constraints]
        observed={r['constraint_id'] for r in observations}
        for i,c in enumerate(raw.get('task_analysis',{}).get('constraints',[])):
            if c['constraint_id'] not in observed:
                observations.append(dict(constraint_id=c['constraint_id'],passed=None,scope='unmeasured',
                    source=dict(reference=reference,pointer='/task_analysis/constraints/'+str(i))))
        nonlinear=summary.get('nonlinear_capability') or summary.get('nonlinear_response')
        latest=dict(reference=reference,operation=summary['operation'],status=summary['status'],
            conclusion=summary['conclusion'],task_acceptance=raw.get('task_acceptance','unmeasured'),
            observations=observations[:4],
            observation_scope='Only saved supported outputs; unmeasured constraints remain unresolved. No independent task acceptance is inferred.',
            quantities={k:nonlinear[k] for k in ('J','initial_J','improvement','direction_status','evidence_level','stop_reason') if k in nonlinear} if nonlinear else
                (card.get('mathematics') or {}).get('quantities',[])[:4],
            directional_quantities=(card.get('mathematics') or {}).get('quantities',[])[:4] if summary.get('nonlinear_response') else [],
            reliability={k:v for k,v in (raw.get('nonlinear_capability',{}).get('search_quality') or {}).items()
                if k in ('global_optimality','convergence')},
            scientific_scope=dict(model=raw['scoped_claim'].get('model_declaration'),
                horizon={k:v for k,v in raw['scoped_claim'].get('horizon',{}).items() if k in
                    ('task_duration_s','analysis_horizon_s','remaining_task_s','origin','period_s','interpretation')},
                claim_kind=summary['evidence_summary']['claim_kind'],verification_status=summary['evidence_summary']['verification_status']),
            unresolved=summary['decision_relevance']['unresolved_questions'][:2],
            detail_query=dict(reference=reference,view='working_set',pointer='/mathematical_decision_view'))
        search=raw.get('native_dynamics',{}).get('optimization',{})
        optimized=raw.get('native_dynamics',{}).get('optimized_schedule',{})
        if optimized:
            latest['actual_experiment']=dict(operation=raw['operation'],
                initial_control_source=optimized.get('provenance',{}).get('source'),
                evaluated_optimized_control_query=dict(reference=reference,view='full',pointer='/native_dynamics/optimized_schedule/provenance'),
                scope='Control reoptimization evaluates changed inputs; it is distinct from an independent test of the initial schedule. The Main Plan owns the original hypothesis.')
        dimension=search.get('search_dimension')
        if dimension is not None:
            latest['search_cost']=dict(active_coefficients=dimension,first_complete_response_callbacks=dimension+2,
                requested_callbacks=search.get('cost_feedback',{}).get('request_budget'),
                completed_response_steps=raw.get('nonlinear_capability',{}).get('response_steps_completed'),
                scope='One baseline + D finite-difference probes + one proposal for one response update. Clipping, inactive directions, failures and additional starts/updates change actual cost; saved callback counts are authoritative.')
        break
    # A measured failure stays a physical observation, distinct from a model
    # sample. Do not borrow a different candidate's or historical task outcome.
    physical=(current.get('latest_scientific_feedback') or {}).get('physical_diagnostic')
    best=current.get('best_valid') or {}
    if not physical and not best.get('historical_only'):physical=best.get('physical_diagnostic')
    if physical and physical.get('candidate_reference')==candidate and physical.get('valid_complete'):
        measured=[]
        for sample in physical.get('critical_samples',[]):
            for r in sample['constraints']:
                if r['normalized_excess']>0 and r['constraint'] not in [m['constraint_id'] for m in measured]:
                    measured.append(dict(constraint_id=r['constraint'],passed=False,scope='physical_task',
                        source=dict(reference=r.get('raw_reference',sample['raw_reference']),pointer=r['raw_pointer'])))
        if measured:observations=measured
    return observations,latest


def agent_decision_brief(host):
    """A-line compact input; existing L0/L2 retrieval contracts remain unchanged."""
    from tools.research.reporter import current_reports, reporter_handoff_summary
    from tools.research.feedback import scientific_result_delivery
    delivery=scientific_result_delivery(host)
    s=state(host);selected=[]
    latest=(delivery.get('latest_search') or {}).get('fixed_result') or {}
    facts=[fact for row in delivery['study_best_mathematical']
        for fact in ([row['fact']] if row.get('fact') else latest.get('best_mathematical',[]))]
    facts.extend(latest.get('best_mathematical',[]))
    for fact in facts:
        if fact.get('profile_identity')==s['profile']['identity'] and fact['reference'] not in selected:
            selected.append(fact['reference'])
    for row in delivery.get('critical_failures',[]):
        if row.get('profile_identity')==s['profile']['identity'] and row.get('reference') and row['reference'] not in selected:
            selected.append(row['reference'])
    latest_evaluation=delivery.get('latest_evaluation') or {}
    if latest_evaluation.get('reference') and latest_evaluation['reference'] not in selected:selected.append(latest_evaluation['reference'])
    cap=s['spec'].get('research_decisions',{}).get('context_limits',{}).get('evidence',3)
    current=context(host,evidence_references=selected[:max(1,cap)]);brief=decision_brief(current)
    brief['scientific_results']=delivery
    from tools.research.candidate_portfolio import ranking_key
    physical=[r for r in current['observations'] if not r['historical_only'] and r['task_gap']['valid_complete']]
    brief['scientific_results']['best_independent_physical']=min(physical,key=ranking_key) if physical else None
    intent=research_intent(host)
    brief['research_intent']=compact_intent(intent)
    if state(host).get('probe_lifecycle'):brief['probe_lifecycle']=state(host)['probe_lifecycle']
    trace=current['evidence_working_set']['action_trace']
    from tools.research.config import conversation_policy
    policy=conversation_policy(state(host)['spec'])
    brief['action_trace']=bounded_action_trace(trace,policy['trace_limit']) if policy else compact_action_trace(trace)
    if policy:
        from tools.research.session_handoff import recent_round
        brief['recent_round']=recent_round(host)
        brief['tool_continuation']=tool_continuation(host)
    from tools.research.session_handoff import pending_feedback_delivery
    delivery=pending_feedback_delivery(host)
    from tools.research.config import bounded_evidence_enabled
    if not delivery and bounded_evidence_enabled(state(host)['spec']):
        # After a pass the SDK stays in its current session and may offload a
        # certificate. Reuse the existing exact-feedback channel until real wire
        # confirms it; never restore a blocked raw array as a formal read.
        pending_certificates={r['query']['reference']['artifact_id']:r['tool_call_id']
            for r in current['evidence_working_set']['read_coverage']
            if r['query']['view']=='acceptance_certificate' and not r['successfully_provided']}
        if pending_certificates:
            from tools.research.session_handoff import feedback_delivery
            delivery=feedback_delivery(host,list(pending_certificates.values()),compact=True)
    if delivery:brief['pending_feedback_delivery']=delivery
    s=state(host)
    if s['spec'].get('start_mode')=='family_space' and s['spec'].get('initial_structure_strategy') in (None,'agent_choice'):
        actions=brief.get('actions',[])
        brief['research_intent_choices']={
            'design_modification':[a for a in actions if a in ('generate','propose','search')],
            'control_optimization':[a for a in actions if a in ('initialize_control','control_search','execute')],
            'diagnosis':[a for a in actions if a in ('diagnose','mechanics','nmpc_prediction_diagnostic')]+(['research_analysis'] if 'analysis' in s['spec'].get('capabilities',[]) else []),
            'validation_or_stop':[a for a in actions if a in ('physical_replay','replay','cross_replay','refine','select','stop')],
            'scope':'Choose freely among currently admitted actions; method details and resource admission remain available on request.'}
    from tools.research.experience import retrieval_hint,read_progress
    hint=retrieval_hint(host)
    if hint:brief['experience_guidance']=hint
    progress=read_progress(host)
    if progress:brief['experience_read_progress']=progress
    if s['spec'].get('task_conditions'):
        brief['task_conditions']=dict(frozen=[dict(condition_id=c['condition_id'],
            task={k:c['task'][k] for k in ('task_id','task_version','family','timing')},
            query=dict(reference=s['family_space_reference'],view='working_set',pointer='/task_conditions/'+str(i)))
            for i,c in enumerate(s['spec']['task_conditions'])],
            initialization='initialize_control with control_seed.condition_id and the generated structure candidate; use the returned candidate and source for this condition.',
            selection='SELECT selected_execution=[one publicly read passing independent physical_replay result per frozen condition]. Same structure and discretization required; order irrelevant. Partial results resume in this Store.',
            completed_results=s.get('physical_replays',[]))
    brief['mathematics_authorization']=mathematics_authorization(host,s)
    if s.get('research_continuations'):
        ref=s['research_continuations'][-1];continuation=host.store.artifact(ref)
        brief['authorized_continuation']=dict(reference=ref,previous_stop=continuation['previous_final_disposition'],
            scope='Explicit user-authorized additional segment in the same Study. Previous STOP is historical; all evidence and cumulative costs retained. No additional scientific allowance.')
    if s['spec'].get('family_search'):
        from tools.research.search import request_guidance
        brief['structure_actions']=request_guidance(s['spec'])
        if 'mujoco_control' in s['spec']['family_search'].get('evaluation_modes',[]):
            conditions=len(s['spec'].get('task_conditions',[])) or 1
            remaining=max(0,s['spec']['budgets']['mathematical_evaluations']-s.get('mathematical_evaluations',0))
            brief['structure_actions']['native_budget']=dict(remaining_analysis_entries=remaining, analysis_entries_per_structure=conditions,
                per_condition_control_limits=s['spec'].get('native_control_limits'), scope='Shared analysis allowance; independent replay has a separate physical budget.')
        from tools.research.core import initial_structure_action
        from tools.research.search import initial_search_progress
        if s['spec'].get('initial_structure_strategy') in ('math_search','native_search'):
            brief['structure_actions']['initial_search_progress']=initial_search_progress(host)
        initial=initial_structure_action(host)
        if initial:
            brief['actions']=[a for a in brief['actions'] if a in (initial,'diagnose','stop')]
            brief['available_research_actions']=[r for r in brief['available_research_actions'] if r['action'] in brief['actions']]
            brief['structure_actions'].pop('search' if initial=='generate' else 'generate',None)
            brief['structure_actions']['first_structure_requirement']=dict(action=initial,
                objective='task_violation' if initial=='search' else None,
                evaluation_mode=('mujoco_control' if s['spec'].get('initial_structure_strategy')=='native_search' else 'mathematical_proxy') if initial=='search' else None,release='After first legal generate / completed finite mathematical search, including unresolved results')
    if s.get('engineering_feedback_correction'):
        ref=s['engineering_feedback_correction']
        brief['recorded_evidence_corrections']=current_evidence_corrections(host.store.artifact(ref),ref)
    if s.get('public_prior_manifest'):
        brief['public_prior_manifest']=dict(reference=s['public_prior_manifest'],view='full',
            scope='Frozen engineering priors; no historical experimental feedback')
    candidate=decision_candidate(host,current,intent)
    if candidate:
        ws=current['evidence_working_set'];anchor=brief['evidence_access']['reference']
        row=next(r for r in ws['candidate_index'] if r['candidate']==candidate)
        facts={k:deepcopy(row[k]) for k in ('candidate','structure_identity','executable_under_current_profile',
            'generated','compiled','control_initialized','has_completed_nmpc_execution','methods_used',
            'mathematically_evaluated','physically_evaluated','accepted')}
        facts['best_valid_reference']=(row['best_valid'] or {}).get('reference')
        sources=[];seen=set()
        relevant=[(i,r) for i,r in enumerate(ws['control_result_links']) if r['candidate']==candidate]
        # Initialized schedules precede observations/predictions, without choosing one.
        for i,r in sorted(reversed(relevant),key=lambda pair:(bool(pair[1].get('initialized')),bool(pair[1].get('origin_status'))),reverse=True):
            if r['source']['artifact_id'] in seen:continue
            seen.add(r['source']['artifact_id'])
            fields=[k for k in ('source','source_kind','origin_kind','origin_status','historical_origin','origin_reference','initialized',
                'full_control_sequence','requires_initialization','initialization_request','task_acceptance','task_gap','control_source','trajectory_query','execution_references') if k in r]
            sources.append({**{k:deepcopy(r[k]) for k in fields if k not in ('trajectory_query','execution_references')},
                'query':dict(reference=anchor,view='working_set',pointer='/control_result_links/'+str(i),fields=fields)})
            if len(sources)==3:break
        facts.update(control_sources=sources,
            parameters_query=row['parameters_query'],provenance_query=row['provenance_query'],
            control_source_status='complete_sequence_recorded' if any(r.get('full_control_sequence') for _,r in relevant) else 'no_complete_bound_sequence_recorded',
            details_query=dict(reference=anchor,view='working_set',pointer='/candidate_index/'+str(ws['candidate_index'].index(row))),
            control_source_scope='Initialized schedules are not physical passes. Measured inputs, predictions and unmeasured plans retain their origin; historical evidence grants no current execution permission. No source is selected.')
        brief['current_candidate']=facts
        from tools.research.task_constraints import mathematical_method_view, mathematical_catalog, mathematical_opportunity_summary
        view=mathematical_method_view(host,candidate,budget_snapshot=brief['budget'])
        brief['mathematical_capabilities']=mathematical_catalog(view)
        selected=((intent['latest_decision'] or {}).get('agent_hypothesis',{}).get('decision') or {}).get('selected_method')
        if selected in view['methods']:brief['selected_mathematical_method']=view['methods'][selected]
    else:
        from tools.research.math_capability_catalog import OPERATION_CATEGORIES, capability_inventory
        inventory=capability_inventory()
        brief['mathematical_research']=dict(status='requires_owned_candidate',
            operation_categories=list(OPERATION_CATEGORIES),methods=[],
            known_capabilities=dict(formally_integrated=sum(r['has_formal_execution_entry'] for r in inventory.values()),
                unintegrated=sum(not r['has_formal_execution_entry'] for r in inventory.values())),
            parameters_query=dict(reference=s['family_space_reference'],view='full') if s.get('family_space_reference') else None,
            full_catalog_query=dict(reference=s['family_space_reference'],view='mathematical_capabilities',pointer='/capability_inventory') if s.get('family_space_reference') else None,
            model_capabilities_query=dict(reference=brief['evidence_access']['reference'],view='working_set',pointer='/method_scope'),
            initial_entries=[dict(tool='research_plan',action=a,request_admission='not_checked') for a in brief['actions'] if a in ('generate','search')],
            query_format='evidence_read(reference=<owned candidate>, view="mathematical_capabilities", pointer="/research_opportunities")')
        brief['mathematical_capabilities']=dict(status='candidate_selection_required',
            query_format='evidence_read(reference=<owned candidate>, view="mathematical_capabilities", pointer="/methods/<method>")')
        brief['current_candidate']=dict(status='not_generated',control_sources=[],control_source_status='missing')
    brief['scientific_execution']=dict(pending={k:s['pending'][k] for k in ('kind','worker_request_id') if k in s['pending']} if s.get('pending') else None,
        scope='Receipts/results establish execution. Plan selected_method is intent; read-only diagnosis starts no selected mathematical worker. Independent evaluation alone establishes task acceptance.')
    brief['analysis_interface']=s['spec'].get('research_decisions',{}).get('analysis_interface')
    from tools.research.scientific_intent import explicit_actions, scientific_actions, parameter_catalog, completed_question_plan
    if explicit_actions(s['spec']):
        brief['scientific_actions']=scientific_actions(s['spec'])
        diagnosis=completed_question_plan(host)
        if diagnosis:
            brief['scientific_parameter_catalog']=parameter_catalog(s['spec'],host.store.artifact(diagnosis['candidate']))
    from tools.research.config import bounded_evidence_enabled
    brief['bounded_evidence']=bounded_evidence_enabled(s['spec'])
    selected=current_reports(host)[-2:]
    brief['latest_reports']=[reporter_handoff_summary(host,r,saved) for r,saved in selected]
    for report in brief['latest_reports']:
        for finding in report.get('findings',[]):
            if finding.get('mathematics'):
                ref=finding['result']['reference']
                scope=summarize_evidence(host.store.artifact(ref),ref)
                finding['mathematics']['unresolved']={**(finding['mathematics'].get('unresolved') or {}),
                    'evidence_limits':scope['unresolved']}
    from tools.research.evidence_views import result_card
    shown=[ref for r in brief['latest_reports'] for ref in r['result_references']]
    brief['additional_mathematical_evidence']=[dict(reference=r,
        mathematics=mathematical_decision_view(plain(result_card(host,r))))
        for r in [*s.get('analysis_results',[]),*s.get('mechanics_results',[])][-3:] if r not in shown]
    latest=brief.get('latest_scientific_feedback')
    if latest and latest.get('reference') in shown:
        delivery=next(r for r in brief['latest_reports'] if latest['reference'] in r['result_references'])
        brief['latest_scientific_feedback']={k:latest[k] for k in
            ('reference','operation','status','candidate','source','control_handoff','owning_study','scientific_scope') if k in latest}
        brief['latest_scientific_feedback']['report_reference']=delivery['report_reference']
    elif latest and latest.get('reference') in [r['reference'] for r in brief['additional_mathematical_evidence']]:
        brief['latest_scientific_feedback']={k:latest[k] for k in
            ('reference','operation','status','control_handoff','owning_study','scientific_scope') if k in latest}
    anchor=brief.get('evidence_access',{}).get('reference')
    if anchor:
        history=history_index(host,candidate)
        if history:
            brief['research_history']=dict(query=dict(reference=anchor,view='working_set',pointer='/research_history_index'),
                conclusions=[dict(study=r['owning_study'],method=r['method'],scope=r['evidence_scope'],l1_pointer='/research_history_index/'+r['source']['reference']['artifact_id'],
                    historical_only=True,cost=r['cost'],task_match=r['task_match'],result=(dict(violation=r['actual_result']['violation'],
                        sampled_maxima=r['actual_result']['sampled_maxima']) if 'violation' in r['actual_result'] else
                        dict(accepted=r['actual_result']['accepted'],metrics=r['actual_result']['metrics']))) for r in history[:5]],
                decision_hint='Existing work: read L1 before repeating. State new information or a reproducibility/numerical check purpose. Exact experimental equivalence is unknown until model, point, inputs and grid align. Historical results grant no current execution/SELECT credit; braking and model-physics mechanisms remain unresolved.')
        diagnostic_anchor=(brief.get('best_valid') or {}).get('reference') or (brief.get('latest_scientific_feedback') or {}).get('reference') or anchor
        brief['diagnostic_relations']=dict(status='available_on_demand',
            query=dict(reference=diagnostic_anchor,view='working_set',pointer='/diagnostic_relations'),
            scope='Comparison alignment and numerical credibility require L1 read; no model-error or causal conclusion from different controllers.')
        brief['action_trace']['full_trace_query']=dict(reference=anchor,view='working_set',pointer='/action_trace')
        refs=brief.pop('all_fresh_results',[])
        brief['stop_result_index']=dict(count=len(refs),query=dict(reference=anchor,
            view='working_set',pointer='/all_fresh_results'),
            read_progress=result_index_progress(refs,current['evidence_working_set']['read_coverage']),
            rule='Exact complete STOP citation index; retrieve on demand. Reports give no formal read credit.')
        # Keep the compact registration rule/query in L0; the inventory stays in L1.
        ws=brief.get('evidence_working_set',{})
        for key in ('candidate_index','control_result_links','control_comparisons'):
            if key in ws:
                rows=ws.pop(key);ws[key+'_access']=dict(count=len(rows),
                    query=dict(reference=anchor,view='working_set',pointer='/'+key))
    from tools.research.config import information_flow_v1
    if information_flow_v1(s['spec']):
        brief['focus_hypothesis']=deepcopy(intent.get('latest_decision'))
        brief['flow_facts']=[]
        seen_results=set()
        for report in reversed(brief.get('latest_reports',[])):
            for finding in report.get('findings',[]):
                key=finding['result']['reference']['artifact_id']
                if key in seen_results:continue
                seen_results.add(key)
                brief['flow_facts'].append(dict(result_reference=finding['result']['reference'],
                    metrics=finding.get('metrics',[]),quantitative_facts=finding.get('quantitative_facts'),
                    comparisons=finding.get('comparisons',[]),mathematics=finding.get('mathematics')))
        milestones=milestone_trace(trace)
        brief['milestone_trace']=bounded_action_trace(milestones,4)
        brief['milestone_trace']['action_total']=trace['total']
        brief['milestone_trace']['page_query']['trace']='milestones'
    brief['route_review']=route_review(host,current,brief,trace)
    brief['current_research_state']=current_research_state(host,brief,intent,trace,current['evidence_working_set']['read_coverage'],method_view=view if candidate else None)
    if not brief['current_research_state']['object']['provenance_query']:
        for key in ('provenance_query','parameters_query'):brief['current_candidate'].pop(key,None)
    if brief.get('selected_mathematical_method'):
        from tools.research.task_constraints import mathematical_action_view
        brief['analysis_handoff']=mathematical_action_view(brief['selected_mathematical_method'])
        guide=brief['selected_mathematical_method'].get('operating_point_guidance',{})
        brief['analysis_handoff']['operating_point_sources']={k:guide[k] for k in
            ('operating_points','available_source_references','unavailable_sources') if k in guide}
    if candidate:
        observations,latest_math=mathematical_discovery_observations(host,current,candidate)
        brief['mathematical_research']=mathematical_opportunity_summary(view,observations=observations,
            latest_result=latest_math,control_sources=brief['current_candidate']['control_sources'],
            execution_block='protected_closeout' if brief['budget'].get('closeout',{}).get('next_request_will_protect') else None)
        latest_intent=intent.get('latest_decision') or {}
        if latest_math:
            completed=next((r for r in reversed(trace['recent']) if latest_math['reference'] in r.get('result_references',[])),None)
            if completed and (completed.get('prior_intent_source') or {}).get('reference')==latest_intent.get('plan_reference'):
                brief['post_result_source']=completed['source']
        if not brief['current_research_state']['object']['provenance_query']:
            discovery=brief['mathematical_research']
            for key in ('method_directory_query','full_catalog_query','detail_query'):discovery.pop(key,None)
            for item in discovery['unavailable_examples']:item.pop('detail_query',None)
            discovery.update(catalog_read_status='deferred_by_original_candidate_read_admission',
                legal_evidence_query=brief['stop_result_index']['query'])
    return compact_scientific_delivery(brief,decision_only=True,complete_interpretations=
        s['spec'].get('research_decisions',{}).get('role_policy',{}).get('version')=='research_roles_v2')


def research_decision_brief_v3(brief, *, complete_interpretations=False):
    """Bounded presentation of existing deterministic state; no action admission."""
    task=brief.get('task') or {}
    best=brief.get('best_valid') or {}
    latest=brief.get('latest_scientific_feedback') or {}
    reports=brief.get('latest_reports') or []
    report=reports[-1] if reports else {}
    facts=[]
    for finding in report.get('findings',[]):
        for metric in finding.get('metrics',[]):
            facts.append({k:metric.get(k) for k in ('name','value','unit','threshold','passed','scope','source')})
        for quantity in (finding.get('mathematics') or {}).get('quantities',[]):
            if quantity.get('name') in ('best_found_violation','optimal_task_violation'):
                facts.append({k:quantity.get(k) for k in ('name','value','unit','status','source','control_reoptimization')})
    if not facts and best.get('task_gap'):
        facts.append(dict(name='task_gap',value=best['task_gap'],source=best.get('reference')))
    actions=[]
    science=(brief.get('budget') or {}).get('science_budget') or {}
    candidate=brief.get('current_candidate') or {}
    catalog=brief.get('mathematical_capabilities') or {}
    rows=brief.get('available_research_actions',[])
    for action in brief.get('actions',[]):
        matching=[r for r in rows if r.get('action')==action]
        active=[r for r in matching if r.get('status') in ('available','preflight_eligible','prerequisites_only')]
        direct=action in ('generate','search','diagnose','stop')
        actions.append(dict(action=action,status='available' if active or (not matching and direct) else 'conditional',
            reason=('Candidate-bound diagnose records a hypothesis and candidate for ScientificQuestion; no solver selection is required.' if action=='diagnose' and brief.get('analysis_interface') in INTERFACES else
                'Candidate-bound diagnose selects an owned candidate and registered method; legacy read-only diagnose follows its frozen contract. research_investigate only reads saved evidence.'
                if action=='diagnose' else 'Full request admission and budget checks apply.' if active or (not matching and direct)
                else 'A suitable candidate, source, read, or other prerequisite is required.'),
            cost='See remaining allowances; exact cost depends on the requested operation.'))
        if action=='diagnose' and brief.get('analysis_interface')=='bound_scientific_variables_v2':
            actions[-1]['read_only_investigation']=dict(tool='research_investigate',scientific_execution=False)
            actions[-1]['analysis_selection']=dict(
                status='requires_owned_candidate' if not candidate.get('candidate') else
                    'insufficient_mathematical_budget' if science.get('remaining_mathematical',0)<1 else 'requires_registered_method_and_authorization',
                candidate_query=candidate.get('details_query'),
                methods_query=dict(reference=candidate['candidate'],view='mathematical_capabilities',pointer='/methods') if candidate.get('candidate') else None,
                required_fields=['decision.selected_candidate','decision.selected_method'],
                scope='Method selection only; research_analysis separately checks registration, authorization, sources and budget. No candidate or hypothesis is selected here.')
    if 'analysis' in (brief.get('capabilities') or []):
        science=(brief.get('budget') or {}).get('science_budget') or {}
        closed=(brief.get('budget') or {}).get('closeout',{}).get('next_request_will_protect')
        blocked=closed or science.get('remaining_mathematical',0)<1
        actions.append(dict(action='research_analysis',status='blocked' if blocked else 'conditional',
            methods_at='mathematical_research',
            reason=('Protected closeout or no mathematical allowance.' if blocked else
                'Record hypothesis and candidate in diagnose, then submit ScientificQuestion to research_analysis.' if brief.get('analysis_interface') in INTERFACES else
                'Select an owned candidate and registered method in a diagnose decision; execution is separately admitted.'),
            cost='Uses the shared mathematical allowance; inspect the method detail.'))
    interpretation=([dict(kind=i['kind'],text=i['text'],sources=i['sources'])
        for i in (report.get('interpretations') or [])] if complete_interpretations else
        [dict(kind=i['kind'],excerpt=i['text'][:240],sources=i['sources'])
        for i in (report.get('interpretations') or [])[:3]])
    budget=brief.get('budget') or {};provider=budget.get('provider_budget') or {};public=budget.get('public_operation_budget') or {};science=budget.get('science_budget') or {}
    result=dict(version='research_decision_brief_v3',
        scientific_results=brief.get('scientific_results'),
        research_state=dict(task_identity=brief.get('task_identity'),task={k:task.get(k) for k in ('family','reference','evaluator','holding','timing','metrics') if k in task},
            task_conditions=(brief.get('task_conditions') or {}).get('frozen',[]),
            candidate_status=brief.get('candidate_status'),current_candidate=(brief.get('current_candidate') or {}).get('candidate'),
            task_accepted=brief.get('task_accepted'),latest_result={k:latest[k] for k in ('reference','operation','status','scientific_scope','report_reference') if k in latest}, pending=(brief.get('scientific_execution') or {}).get('pending'),
            pending_feedback=brief.get('pending_feedback_delivery')),
        current_research_state=brief.get('current_research_state'),analysis_handoff=brief.get('analysis_handoff'),
        verified_facts=facts[:8],mathematical_research=brief.get('mathematical_research'),
        reporter_summary=dict(status=report.get('reporter_status','unavailable'),
            report_reference=report.get('report_reference'),interpretations=interpretation,
            interpretation_query=report.get('restore_query'),
            summary_query=report.get('summary_query'),
            excerpt_scope=('Complete source-grounded final conclusions; Reporter internal reasoning and reads are excluded.' if complete_interpretations else 'First 240 characters of each cited interpretation; use interpretation_query for complete text.'),
            unresolved=report.get('unresolved',[])[:3]),
        action_menu=actions,
        evidence_access=dict(working_set=brief.get('evidence_access'),
            method_query=catalog.get('detail_query'),stop_index=brief.get('stop_result_index'),
            select_requirement='A fresh, complete, independently evaluated passing result must be formally read by the Main Agent before SELECT. Multi-condition tasks require a passing result for every frozen condition on the same structure. Reporter reads do not count.',
            stop_requirement='Retrieve and cite the complete new result index; original admission checks remain in force.',
            knowledge='Optional experience_retrieve provides procedural guidance only; it is not scientific evidence.'),
        budget=dict(model_calls=provider.get('remaining_total'),model_closeout_reserve=provider.get('reserved_for_closeout'),
            public_operations=public.get('remaining_total'),public_closeout_reserve=public.get('reserved_for_closeout'),
            physical= science.get('remaining_physical'),mathematical=science.get('remaining_mathematical'),
            closeout=budget.get('closeout')))
    math_result=(brief.get('mathematical_research') or {}).get('latest_result') or {}
    if math_result:
        reference=math_result['reference']
        result['verified_facts']=[f for f in result['verified_facts'] if (f.get('source') or {}).get('reference')!=reference]
        result['verified_facts'].append(dict(result_reference=reference,facts_at='mathematical_research.latest_result'))
        latest=result['research_state']['latest_result']
        if latest.get('reference')==reference:
            latest.pop('scientific_scope',None);latest['facts_at']='mathematical_research.latest_result'
    if brief.get('experience_guidance'):
        result['experience_guidance']=brief['experience_guidance']
    if brief.get('experience_read_progress'):
        result['experience_read_progress']=brief['experience_read_progress']
    if 'recent_round' in brief:
        recent=deepcopy(brief['recent_round'])
        if recent and recent['feedback']==brief.get('pending_feedback_delivery'):
            recent.pop('feedback');recent['feedback_at']='research_state.pending_feedback'
        result.update(recent_round=recent,history_trace=brief['action_trace'],
            tool_continuation=brief.get('tool_continuation'),
            current_intent=brief.get('research_intent',{}).get('latest_decision'),
            current_control=brief.get('current_candidate'),
            lifecycle=brief.get('probe_lifecycle'))
    if brief.get('bounded_evidence'):
        result['evidence_access']['select_requirement']='Read acceptance_certificate for each exact fresh independently evaluated passing result; only complete deterministic certificate delivery on actual Provider wire or an exact full result read qualifies. Original source, fidelity, condition and confirmation admission still applies.'
        result['evidence_access']['acceptance_query_format']=dict(reference='<independent result reference>',view='acceptance_certificate')
    return result



def information_flow_brief(brief, delivered):
    """P6.1 projection of the existing brief: each L0 fact has one owner."""
    value=deepcopy(delivered);current=value.get('research_state',{})
    intent=brief.get('focus_hypothesis') or value.get('current_intent') or {}
    hypothesis=intent.get('agent_hypothesis') or {}
    control=deepcopy(value.get('current_control') or {})
    control.pop('candidate',None)
    continuation=value.get('tool_continuation') or {}
    continuation['switch_tool']='Use research_route only to change the loaded tool/action. Direct reads preserve the loaded Plan; selecting an entry alone executes nothing.'
    loaded=continuation.get('loaded') or {}
    if intent.get('action')=='initialize_control' and intent.get('execution_status')=='completed':
        continuation['control_initialization_handoff']=dict(candidate=intent.get('candidate'),
            control_sources=control.get('control_sources',[]),task_acceptance='unmeasured',
            next='Use the initialization result source reference, not candidate. Submit a new diagnose Plan with your chosen hypothesis, candidate and registered method before research_analysis; initialization superseded the previous diagnose.')
    if loaded.get('plan_action'):
        continuation['direct_plan']=dict(tool='research_plan',action=loaded['plan_action'],
            instruction='This Plan Schema is already available: submit the Plan object directly to act; no research_route call is needed for this action.')
        if loaded['plan_action']=='generate' and value.get('generation_contract'):
            continuation['direct_plan']['generation_inputs']=value['generation_contract']['generation_inputs']
        if loaded['plan_action']=='diagnose':
            continuation['direct_plan'].update(status='tool_selected_not_submitted' if
                (continuation.get('plan_selection') or {}).get('status')=='selected_not_submitted' else 'loaded',
                scientific_fields=['hypothesis','decision.selected_candidate','decision.selected_method',
                    'expected_observation','weakening_observation','fixed_conditions'],
                current_hypothesis=hypothesis.get('hypothesis'),candidate=current.get('current_candidate'),
                instruction='Diagnose is loaded; tool selection has not submitted scientific choices. Submit research_plan(action=diagnose) directly with your hypothesis, candidate and registered method; no research_route call is needed.')
            if intent.get('action')=='diagnose' and intent.get('execution_status')=='completed' and loaded.get('tool')=='research_analysis':
                continuation['direct_plan'].update(status='completed',instruction='Your diagnose is complete; submit scientific inputs to loaded research_analysis. A new Plan is optional when changing your research choice.')
    handoff=value.get('analysis_handoff')
    if handoff:
        continuation['analysis_handoff']={k:handoff[k] for k in ('method','operation','already_bound','required_parameters',
            'required_sources','missing','planning_status','formal_execution_authorized','execution_status','estimated_evaluations','request_template_query')}
        continuation['analysis_handoff'].update(tool='research_analysis',loaded=loaded.get('tool')=='research_analysis',
            selected_method=(hypothesis.get('decision') or {}).get('selected_method'),
            diagnose_status='completed' if intent.get('action')=='diagnose' and intent.get('execution_status')=='completed' else 'not_submitted',
            remaining_scientific_fields=handoff.get('remaining_scientific_fields',[]),
            remaining_scientific_fields_scope='Top-level required fields in the current Provider Schema only; conditional sources are listed separately. All original AnalysisRequest admission applies.',
            conditional_scientific_inputs=handoff.get('conditional_scientific_inputs',[]),
            operating_point_sources=handoff.get('operating_point_sources',{}),
            control_input_guidance=handoff.get('control_input_guidance'),
            scientific_inputs=handoff.get('scientific_inputs'),
            next='Submit scientific variables directly to loaded research_analysis; source, parameter and budget admission still applies.' if loaded.get('tool')=='research_analysis' else 'research_analysis is not loaded; consult current tool directory and method prerequisites.')
    for key,source in (('pending_execution',current.get('pending')),
            ('pending_feedback',current.get('pending_feedback')),('lifecycle',value.get('lifecycle'))):
        if source:continuation[key]=source
    if brief.get('analysis_interface') in INTERFACES:
        if continuation.get('control_initialization_handoff'):
            continuation['control_initialization_handoff']['next']=(
                'Use the new initialization result as the legal control source, not the structure candidate. '
                'Initialization superseded the latest diagnose: submit a new candidate-bound diagnose Plan with your hypothesis; '
                'no underlying mathematical method name is required. After diagnose completes, submit ScientificQuestion directly '
                'to research_analysis. Original AnalysisRequest and execution admission still apply; initialization is not a mathematical result.')
        settled=intent.get('action')=='diagnose' and intent.get('execution_status')=='completed' and bool(intent.get('candidate'))
        if continuation.get('direct_plan',{}).get('action')=='diagnose':
            continuation['direct_plan'].update(scientific_fields=['hypothesis','decision.selected_candidate'],
                instruction='Your diagnose is complete; submit ScientificQuestion directly to research_analysis.' if settled else
                    'Submit diagnose with your hypothesis and owned candidate; a solver name is not required. After completion submit ScientificQuestion directly to research_analysis.')
        continuation['analysis_handoff']=dict(tool='research_analysis',interface=brief['analysis_interface'],
            loaded=loaded.get('tool')=='research_analysis',
            status='diagnose_completed' if settled else 'requires_completed_candidate_bound_diagnose',
            already_bound=['hypothesis','candidate','frozen task and protocol'] if settled else ['frozen task and protocol'],
            next='Submit scientific question fields to the loaded tool. Original execution admission applies.' if settled else 'Complete diagnose with your hypothesis and owned candidate first.')
    reports=brief.get('latest_reports',[])
    findings=[]
    for report in reports:
        findings.append(dict(report_reference=report['report_reference'],question=report.get('question'),
            reference_role='reporter_report',scientific_citation_eligible=False,
            result_references=report.get('result_references',[]),status=report['reporter_status'],
            interpretation_query=report.get('restore_query'),
            summary_query=report.get('summary_query'),
            reading_guidance='Use compact facts and interpretation_query for ordinary investigation; full reads remain available for formal requirements.',
            interpretations=report.get('interpretations',[]),
            unresolved=report.get('unresolved',[])[:3]))
    # Values are owned by verified_facts; explanations carry references only.
    facts=deepcopy(brief.get('flow_facts') or value.get('verified_facts',[]))
    for result in brief.get('additional_mathematical_evidence',[]):
        for quantity in (result.get('mathematics') or {}).get('quantities',[])[:3]:
            if quantity.get('source') and quantity not in facts:facts.append(quantity)
    math_result=(value.get('mathematical_research') or {}).get('latest_result') or {}
    if math_result:
        reference=math_result['reference']
        facts=[f for f in facts if f.get('result_reference')!=reference and (f.get('source') or {}).get('reference')!=reference]
        facts.append(dict(result_reference=reference,facts_at='mathematical_research.latest_result'))
    groups={
        'Design':('generate','propose','search'),
        'Control':('initialize_control','control_search','execute','research_rl'),
        'Mathematical Research':('diagnose','mechanics','research_analysis','refine','matched_state','nmpc_prediction_diagnostic'),
        'Physical Validation':('physical_replay','replay','cross_replay','select','confirm','stop'),
        'Evidence & Knowledge':('evidence_read','research_recall','experience_retrieve','research_investigate')}
    directory=value.get('tool_directory',[]);action_rows=[]
    for tool in directory:
        if tool['tool']=='research_plan':action_rows.extend(dict(**r,tool='research_plan') for r in tool.get('actions',[]))
        else:action_rows.append(dict(action=tool['tool'],tool=tool['tool'],status=tool['status']))
    action_rows.extend(value.get('additional_action_requirements',[]))
    for row in action_rows:
        if row.get('cost')=='See remaining allowances; exact cost depends on the requested operation.':row.pop('cost')
        if row.get('reason')=='Full request admission and budget checks apply.':row.pop('reason')
    capabilities=[dict(category=name,actions=[r for r in action_rows if r['action'] in names])
        for name,names in groups.items()]
    access=value.get('evidence_access',{})
    access.pop('knowledge',None)
    if access.get('working_set'):access['working_set'].pop('scope',None)
    if access.get('stop_index'):access['stop_index'].pop('rule',None)
    eligibility=brief.get('citation_eligibility') or {}
    access['citation_eligibility']={k:eligibility[k] for k in ('query','registered_count','scientific_result_count') if k in eligibility}
    access['citation_eligibility']['rule']='supporting_evidence requires registered result_reference matching inference, candidate, task and model scope. report_reference only restores Reporter text; Knowledge is procedural context; Domain Reference defines the problem; tool receipts record operations. None gains scientific eligibility by being read.'
    access['citation_eligibility']['recent_registered']=eligibility.get('latest_registered',[])
    scopes=[scope for report in reports for scope in report.get('scope',[])]
    if scopes:access['result_scopes']=scopes[-3:]
    if eligibility.get('scientific_result_count')==0:
        access['citation_eligibility'].update(registered_scientific_results=[],
            exploration='Exploratory empirical_search may use supporting_evidence=[]. SELECT/STOP gates still apply.')
    if value.get('generation_contract'):
        access['domain']=dict(query=value['generation_contract']['domain_query'],role='domain_reference')
    access['delegated_read']=dict(tool='research_investigate',
        arguments='question and existing result references; optional exact reads',
        scope='Preferred for detailed numerical reading and comparison. Reporter reads never grant SELECT/STOP credit.')
    focus=dict(candidate=current.get('current_candidate'),candidate_status=current.get('candidate_status'),
        task_accepted=current.get('task_accepted'),control=control,
        latest_result=current.get('latest_result'))
    if intent:
        focus['formal_hypothesis']=dict(plan_reference=intent.get('plan_reference'),
            pointer='/original_plan',hypothesis_id=(hypothesis.get('decision') or {}).get('hypothesis_id'),
            hypothesis=(hypothesis.get('hypothesis') or '')[:240],expected_observation=(hypothesis.get('expected_observation') or '')[:240],
            status='Main intent excerpts; not verified facts. Restore full text from the Plan.')
    # Only recorded unresolved questions are exposed; no program-authored hypothesis.
    focus['open_questions']=[dict(reference=report['report_reference'],pointer='/report/interpretations/'+str(n),kind=i['kind'])
        for report in reports for n,i in enumerate(report.get('interpretations',[])) if i['kind'] in ('unresolved_question','further_investigation')][-3:]
    if hypothesis.get('weakening_observation'):
        focus['open_questions'].append(dict(text=hypothesis['weakening_observation'][:240],kind='Main falsification target excerpt',
            source=dict(reference=intent['plan_reference'],pointer='/original_plan/weakening_observation')))
    post_result=None
    if math_result and brief.get('post_result_source'):
        continuation['analysis_handoff']=dict(tool='research_analysis',loaded=loaded.get('tool')=='research_analysis',
            status='result_completed',result_reference=math_result['reference'],decision_at='post_result_decision')
        if continuation.get('direct_plan',{}).get('action')=='diagnose':
            continuation['direct_plan'].update(status='completed',instruction='Previous mathematical request completed; current decision context is post_result_decision. A new scientific request remains optional.')
        post_result=dict(status='awaiting_Main_judgment',prior_Main_question_at='research_focus.formal_hypothesis',
            completed_action=brief['post_result_source'],facts_and_limits_at='mathematical_research.latest_result',
            interpretations_at='reporter_findings',interpretation_role='Non-authoritative source-linked explanations; fixed facts remain available without Reporter.',
            read_progress_at='evidence_access.stop_index.read_progress',legal_actions_at='capabilities',remaining_resources_at='budget',
            decision='Assess the original hypothesis and choose further evidence, a new hypothesis or legal research action, or a justified STOP. No outcome or next action is selected by this projection.')
    if brief.get('scientific_actions'):
        continuation.pop('analysis_handoff',None)
        settled=intent.get('action')=='diagnose' and intent.get('execution_status')=='completed'
        choice=hypothesis.get('next_research_action') if settled else None
        entry=next((r for r in brief['scientific_actions'] if r['scientific_goal']==choice),None)
        continuation['scientific_action_handoff']=dict(diagnose_choice=choice,
            status='result_completed' if post_result else 'diagnose_completed' if settled else 'requires_candidate_bound_diagnose',
            loaded=loaded,choices=brief['scientific_actions'],selection_executes_science=False,
            next='Submit scientific choices to the loaded interface; selection alone produces no scientific result.' if entry and loaded.get('tool')==entry['tool'] else
                'Choose an action with research_route or record next_research_action in a new diagnose. Main owns the research choice.')
        if loaded.get('tool')=='research_analysis':
            continuation['analysis_handoff']=dict(tool='research_analysis',interface=brief['analysis_interface'],loaded=True,
                status='result_completed' if post_result else 'diagnose_completed' if settled else 'requires_completed_candidate_bound_diagnose',
                parameter_catalog=brief.get('scientific_parameter_catalog',[]),
                next='Select a parameter group and registered physical parameter for effects, or control scope and effort for current-structure T1. T2 only reuses saved comparable T1 evidence.')
            if post_result:
                continuation['analysis_handoff'].update(result_reference=math_result['reference'],
                    next='Interpret the completed result at post_result_decision; Main chooses whether to pursue a new scientific question.')
        if continuation.get('direct_plan',{}).get('action')=='diagnose':
            continuation['direct_plan'].update(scientific_fields=['hypothesis','decision.selected_candidate','next_research_action'],
                instruction='Record hypothesis and candidate; optionally choose next_research_action. No action is inferred from hypothesis or method text; omitted choice keeps discovery neutral.')
        continuation.pop('control_initialization_handoff',None)
        for category in capabilities:
            for row in category['actions']:
                if row['action']=='diagnose':row['reason']='Record hypothesis/candidate and optionally next_research_action; loads an interface only.'
                if row['action']=='research_analysis':row['reason']='Current-structure T1 or single-parameter comparison; T2 reuses saved T1 results.'
    trace=brief.get('milestone_trace',value.get('history_trace'))
    if trace and trace['total']==0:trace=dict(total=0,action_total=trace.get('action_total',0),recall=dict(trace='actions'))
    return dict(version='research_information_flow_v1',
        scientific_results=value.get('scientific_results'),
        study_goal={k:current[k] for k in ('task_identity','task','task_conditions') if k in current},
        research_focus=focus,current_research_state=value.get('current_research_state'),
        verified_facts=facts[:8],mathematical_research=value.get('mathematical_research'),
        research_trace=trace,**(dict(post_result_decision=post_result) if post_result else {}),
        capabilities=capabilities,tool_continuation=continuation,
        knowledge=dict(role='procedural_knowledge',access=value.get('experience_guidance'),read_progress=value.get('experience_read_progress')),
        reporter_findings=findings,evidence_access=access,budget=value['budget'])



def compact_tool_delivery(brief):
    """Give overlapping L0/tool fields one owner; retain original L1 queries."""
    menu=brief.pop('action_menu',[])
    directory=brief['tool_directory']
    plan=next((r for r in directory if r['tool']=='research_plan'),None)
    if plan is not None:
        plan['actions']=[r for r in menu if r['action'] in plan['actions']]
    extra=[r for r in menu if r['action'] not in (a['action'] for a in (plan or {}).get('actions',[]))]
    if extra:brief['additional_action_requirements']=extra
    continuation=brief.get('tool_continuation') or {}
    continuation['loaded']=brief.pop('loaded_tool')
    feedback=(brief.get('research_state') or {}).get('pending_feedback') or {}
    delivered={r['tool_id'] for r in feedback.get('items',[])}
    continuation['recent']=[r for r in continuation.get('recent',[]) if r['tool_use_id'] not in delivered]
    brief['tool_continuation']=continuation
    trace=brief.get('history_trace') or {}
    intent=brief.get('current_intent') or {}
    for step in trace.get('recent',[]):
        if step.get('agent_hypothesis') and step['agent_hypothesis']==intent.get('agent_hypothesis'):
            step.pop('agent_hypothesis');step['intent_at']='current_intent'
    if trace.get('total')==0:
        brief['history_trace']={'total':0,'full_trace_query':trace.get('full_trace_query')}
    control=brief.get('current_control') or {}
    if control.get('status')=='not_generated' and not control.get('control_sources'):
        brief.pop('current_control',None)
    report=brief.get('reporter_summary') or {}
    if not report.get('report_reference') and not report.get('interpretations') and not report.get('unresolved'):
        brief['reporter_summary']={'status':report.get('status','unavailable')}
    # Version and identity are now actual generate Schema constants. The source
    # query remains here; neither constants nor retrieval choose a structure.
    generation=brief.get('generation_contract')
    if generation and continuation['loaded'].get('plan_action')=='generate':
        generation.pop('version',None);generation.pop('family_space_identity',None)
    return brief


def route_review(host,current,brief,trace):
    """Small evidence projection, not a route selector or convergence test."""
    import math
    groups={};seen=set();s=state(host)
    for step in trace['recent']:
        for ref in step['result_references']:
            if ref['artifact_id'] in seen:continue
            seen.add(ref['artifact_id'])
            independent=ref in [*s.get('results',[]),*s.get('physical_replays',[]),*s.get('rl_evaluations',[])]
            raw=host.store.artifact(ref) if independent else host.store.artifact(ref,paths=(
                'candidate','design_candidate','native_dynamics.optimization.best.measure.signed_maximum_excess',
                'trajectory.replayed_violation','model_identity','model','analysis_applicability','task_analysis',
                'native_analysis.basis','requested_operation'))
            candidate=raw.get('candidate',raw.get('design_candidate'))
            if not candidate:continue
            gap=task_gap(raw) if independent else {}
            pointer='/acceptance';scope='independent_task';score=gap.get('normalized_gap') if gap.get('valid_complete') else None
            if not independent:
                score=(raw.get('native_dynamics',{}).get('optimization',{}).get('best') or {}).get('measure',{}).get('signed_maximum_excess')
                pointer='/native_dynamics/optimization/best/measure/signed_maximum_excess';scope='native_finite_search'
                if score is None:
                    score=(raw.get('trajectory') or {}).get('replayed_violation')
                    pointer='/trajectory/replayed_violation';scope='sampled_mathematical_model'
            if not isinstance(score,(int,float)) or not math.isfinite(score):continue
            domain={k:raw.get(k) for k in ('model_identity','model','analysis_applicability','task_analysis')}
            key=(step['method'],candidate['artifact_id'],scope,digest(domain))
            row=groups.setdefault(key,dict(method=step['method'],candidate=candidate,scope=scope,
                best_score=score,consecutive_nonimprovements=0,observations=0,recent=[]))
            previous=row['best_score'];delta=previous-score if row['observations'] else None
            row['consecutive_nonimprovements']=row['consecutive_nonimprovements']+1 if delta is not None and delta<=0 else 0
            row['best_score']=min(previous,score);row['observations']+=1
            basis=raw.get('native_analysis',{}).get('basis',{})
            row['recent']=[*row['recent'][-1:],dict(reference=ref,pointer=pointer,score=score,improvement_over_previous_best=delta,
                local_scope={k:basis[k] for k in ('model','state_time_s','window_s','search_dimension','sample_count') if k in basis},
                scope_query=dict(reference=ref,view='fields',fields=[k for k in ('model','model_identity','analysis_applicability','requested_operation') if k in raw])
                    if any(k in raw for k in ('model','model_identity','analysis_applicability','requested_operation')) else dict(reference=ref,view='full'))]
            groups[key]=groups.pop(key)
    rows=list(groups.values())[-4:]
    attempted={r['action'] for r in trace['recent'] if r['result_references']}
    methods=(brief.get('mathematical_capabilities') or {}).get('methods',{})
    used={r['method'] for r in trace['recent'] if r['result_references']}
    return dict(required=not current.get('task_accepted') and any(r['consecutive_nonimprovements']>1 for r in rows),observed_routes=rows,
        untried_actions=[a for a in ('search','generate','control_search','execute') if a in brief['actions'] and a not in attempted],
        untried_mathematical_methods=[k for k,v in methods.items() if k not in used and v.get('execution_status')!='blocked'],
        evidence_owner='best_valid, latest_reports, action_trace and budget retain exact facts, unresolved hypotheses and remaining units.',
        decision_obligation='After repeated non-improvement, compare continuing control, changing structure, joint optimization and Reporter diagnosis in interpretation. '
            'Name legal prerequisites, expected new information and a weakening observation. Choose freely; an untried route is not automatically admissible. '
            'A STOP must distinguish exhausted budget, engineering unavailability, scoped local stagnation and a verified scientific conclusion, and acknowledge untried routes.',
        scope='Lower scores improve only within the identical candidate/method/model/task scope shown. Exact repeated scores are observations, '
            'not a convergence or infeasibility proof. Mathematical improvement needs independent physics; no parameter or route is selected here.')


def compact_scientific_delivery(brief,*,decision_only=False,complete_interpretations=False):
    """Pure L0 projection; exact reports and immutable SDK history stay intact."""
    brief=deepcopy(brief)
    for report in brief.get('latest_reports',[]):
        # Every interpretation already carries its own exact sources.
        report.pop('interpretation_sources',None)
        for finding in report.get('findings',[]):
            diagnostics=(finding.get('recorded_summary') or {}).get('recorded_control_diagnostics')
            if diagnostics:
                for row in diagnostics.get('relevant_updates',[]):
                    row.pop('actual_input_n',None);row.pop('planned_first_input_n',None)
                    if row.get('recovery'):
                        row['recovery']={k:row['recovery'][k] for k in ('attempted','selected','error') if k in row['recovery']}
    if decision_only:
        candidate=(brief.get('current_candidate') or {}).get('candidate')
        if candidate:
            brief['available_research_actions']=[r for r in brief.get('available_research_actions',[]) if r.get('candidate') in (None,candidate)]
            brief['research_actions_query']=dict(reference=brief['evidence_access']['reference'],view='working_set',pointer='/eligible_methods')
        catalog=brief.get('mathematical_capabilities',{})
        if catalog.get('methods'):
            catalog['request_template_query_format']=dict(reference=catalog['candidate'],view='mathematical_capabilities',
                pointer='/methods/<exact method key>',fields=['candidate','operation','request_template',
                    'required_parameters','formal_execution_authorized','missing','cost_scope'])
        for method,row in catalog.get('methods',{}).items():
            # Detailed model/coverage/template information has one query owner.
            for key in list(row):
                if key not in ('planning_status','execution_status','missing','estimated_evaluations',
                        'study_authorized','formal_execution_authorized','detail_pointer','registered','authorized','applicable','executable',
                        'execution_limits','cost_scope','control_initialization_query','preparation_query','preparation_hint','request_template_query','action_prerequisites'):
                    row.pop(key)
            if not row.get('action_prerequisites'):row.pop('request_template_query',None)
        if brief.get('selected_mathematical_method'):
            selected=brief['selected_mathematical_method']
            fields=[k for k in ('candidate','operation','request_template','required_parameters','formal_execution_authorized',
                'execution_limits','cost_scope','missing','action_prerequisites','operating_point_guidance') if k in selected]
            brief['selected_mathematical_method']=dict(query={**catalog['detail_query'],
                'pointer':'/methods/'+selected['method'],**(dict(fields=fields) if fields else {})})
        intent=brief.get('research_intent',{})
        if isinstance(intent.get('unresolved_question'),str):
            intent['unresolved_question']=intent['unresolved_question'][:240]
            intent['question_scope']='Prior falsification target excerpt (at most 240 characters); original Plan remains authoritative. Main Agent chooses the next question.'
        for key in ('latest_decision','last_research'):
            item=intent.get(key)
            if item and item.get('agent_hypothesis'):
                original=item.pop('agent_hypothesis')
                if key=='latest_decision':
                    item['agent_hypothesis']={k:original[k][:240] for k in ('hypothesis','expected_observation','weakening_observation') if isinstance(original.get(k),str)}
                    item['excerpt_scope']='Original Agent text excerpts, at most 240 characters per field; not a complete hypothesis or Reporter rewrite'
                item['original_plan_query']=dict(reference=item['plan_reference'],view='full',pointer='/original_plan')
        # Older mathematical results remain in L2. Deliver only the latest
        # unreported result, rather than a second rolling evidence inventory.
        reported_math=any(f.get('mathematics') for r in brief.get('latest_reports',[]) for f in r.get('findings',[]))
        extra=brief.get('additional_mathematical_evidence',[])[-1:]
        latest=(brief.get('latest_scientific_feedback') or {}).get('reference')
        brief['additional_mathematical_evidence']=extra if not reported_math or any(r['reference']==latest for r in extra) else []
        math_views=[(r['mathematics'],r['reference']) for r in brief.get('additional_mathematical_evidence',[]) if r.get('mathematics')]
        math_views += [(f['mathematics'],f['result']['reference']) for r in brief.get('latest_reports',[])
            for f in r.get('findings',[]) if f.get('mathematics')]
        for math,ref in math_views:
            if math.get('nonlinear_response') or math.get('nonlinear_capability'):
                key='nonlinear_response' if math.get('nonlinear_response') else 'nonlinear_capability'
                compact=math[key];cost=math.get('cost')
                scope={k:math[k] for k in ('owning_study','scope','unresolved','cost_scope') if k in math}
                math.clear()
                math.update({key:compact},**scope,cost=cost,
                    detail_query=dict(reference=ref,view='working_set',pointer='/mathematical_decision_view/'+key))
            if math.get('optimal_sensitivity'):
                t2=math['optimal_sensitivity']
                math.clear()
                math.update(optimal_sensitivity=dict(parameter=t2['parameter']['path'],direction_status=t2['direction_status'],
                    preferred_parameter_direction=t2['preferred_parameter_direction'],physical_acceptance='unmeasured'),
                    detail_query=dict(reference=ref,view='working_set',pointer='/mathematical_decision_view/optimal_sensitivity'))
        for report in brief.get('latest_reports',[]):
            interpretations=report.get('interpretations',[])
            if not complete_interpretations:interpretations=interpretations[:3]
            report['interpretations']=[{k:i[k] for k in ('kind','text','sources')} for i in interpretations]
            for finding in report.get('findings',[]):
                finding['metrics']=finding.get('metrics',[])[:3]
                best=brief.get('best_valid')
                if best and finding['result']['reference']==best['reference']:
                    finding['metrics']=[]
                    finding['physical_facts']=dict(same_as='best_valid/physical_diagnostic')
                    finding.get('recorded_summary',{}).pop('task_gap',None)
                math=finding.get('mathematics') or {}
                native=math.get('native_analysis') or {}
                if native.get('comparison'):
                    math['quantities']=[]
                    native['comparison']={k:dict(worst_constraint=v.get('worst_constraint'))
                        for k,v in native['comparison'].items()}
                for task in (finding.get('mathematics',{}) or {}).get('original_predicate_diagnostics',{}).values():
                    task.pop('samples',None)
        best=brief.get('best_valid')
        if best and best.get('physical_diagnostic'):
            best.pop('violated_constraints',None)
        anchor=brief.get('evidence_access',{}).get('reference')
        if anchor:
            ws=brief.get('evidence_working_set',{})
            if ws.get('method_scope'):ws['method_scope']=dict(query=dict(reference=anchor,view='working_set',pointer='/method_scope'))
            for key,pointer in (('recent_searches','/recent_searches'),('method_requirements','/method_requirements')):
                if brief.get(key):
                    brief[key]=dict(query=dict(reference=anchor,view='working_set',pointer=pointer))
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
        capability=compact,owning_study=card['identity']['study'],
        unresolved={**(summary.get('decision_relevance') or {}),
            'evidence_limits':card['evidence_summary']['unresolved']})
    if summary.get('native_analysis'):
        result['cost_scope']='Costs belong to owning_study, unknown if unrecorded. Native physics_steps includes prefix reconstruction and rollouts; callbacks are not additional rollouts. Independent physical replay is separate.'
    if summary.get('optimal_sensitivity'):result['optimal_sensitivity']=summary['optimal_sensitivity']
    for key in ('nonlinear_capability','nonlinear_response'):
        if summary.get(key):result[key]=summary[key]
    if summary.get('nonlinear_response'):
        result['cost_scope']='Costs belong to owning_study, unknown if unrecorded. T2 aggregates saved T1 results with zero new rollouts or physics steps; referenced T1 costs were previously charged and are not charged again. Preparation and worker time are additional; independent physical acceptance is separate.'
    if summary.get('native_analysis'):
        result['native_analysis']={k:v for k,v in summary['native_analysis'].items() if k!='quantities'}
    if summary.get('recorded_static_construction'):
        result['recorded_static_construction']={k:v for k,v in summary['recorded_static_construction'].items() if k!='initializer_source'}
        result['recorded_static_construction']['initializer_query']=dict(reference=card['identity']['result']['reference'],view='full',pointer='/construction/initializer_source')
    if summary.get('optimal_sensitivity') or summary.get('nonlinear_capability') or summary.get('nonlinear_response') or (capability and capability.get('method_version')):
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
    execution=result.get('execution_feedback') if isinstance(result,dict) else None
    if isinstance(result,dict) and result.get('status')=='not_applicable' and not reference:
        execution=dict(status='not_applicable',scientific_execution_started=False,worker_started=False,
            additional_analysis_evaluations=result.get('additional_analysis_evaluations'),
            reasons=(result.get('analysis_applicability') or {}).get('reasons',[]) or [result.get('reason') or result.get('admission')],
            horizon=(result.get('analysis_applicability') or {}).get('horizon'))
    return dict(wrapper_reference=wrapper,wrapper_role='Retrieval only; not supporting_evidence',
        execution_feedback=execution,
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
