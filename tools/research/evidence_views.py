"""Read-only result cards composed from existing deterministic evidence views.

No persistence, scientific dispatch, report generation or evidence registration.
L0/L2 stay in research_context; L3 stays in core.read_evidence/EvidenceQuery.
"""
from copy import deepcopy
from schemas.research_reporting import (
    ControlSearchEvidence, ControlSearchStep, CriticalObservation, EvidenceLocation,
    MathematicalEvidence, RecordedField, ReportedMetric, ResourceUse, ResultCard,
    ResultIdentity,
)
from tools.platform_store import plain
from tools.research.analysis import decision_result
from tools.research.core import read_evidence
from tools.research.evidence_policy import summarize_evidence
from tools.research.research_context import compact_evidence, physical_diagnostic


def _location(reference, pointer=''):
    return EvidenceLocation(reference=reference, pointer=pointer)


def _token(key):
    return key.replace('~', '~0').replace('/', '~1')


def recorded_math_summary(value,reference):
    """Project recorded strict predicates and magnitudes without changing acceptance."""
    facts=value.get('mathematical_facts') or {}
    if not facts:return None
    requirements={r['constraint_id']:r for r in (value.get('task_requirements') or {}).get('constraints',[])}
    samples={}
    for name,task in (('returned',(facts.get('raw_returned') or {}).get('task')),('recomputed',facts.get('task'))):
        if not task:continue
        rows=[]
        for i,(key,time,margin) in enumerate(zip(task.get('constraint_ids',[]),task.get('times_s',[]),task.get('signed_margin',[]))):
            requirement=requirements.get(key,{})
            rows.append(dict(constraint_id=key,time_s=time,signed_margin=margin,positive_violation=max(0.,-margin),
                unit=(requirement.get('signal') or {}).get('units'),limit=requirement.get('radius'),
                actual_norm=task.get('actual_norm',[None]*len(task.get('constraint_ids',[])))[i],
                source=dict(reference=reference,pointer=('/mathematical_facts/raw_returned/task' if name=='returned' else '/mathematical_facts/task')+'/signed_margin/'+str(i))))
        maxima=[]
        for key in dict.fromkeys(r['constraint_id'] for r in rows):
            row=max((r for r in rows if r['constraint_id']==key),key=lambda r:r['positive_violation'])
            maxima.append({k:row[k] for k in ('constraint_id','positive_violation','unit','time_s','limit','source')})
        samples[name]=dict(strict_satisfied=task.get('original_sampled_requirements_satisfied'),maxima_by_constraint=maxima,
            samples=rows,required_slacks=task.get('required_slacks'))
    slacks=(value.get('trajectory') or {}).get('slacks',(facts.get('raw_returned') or {}).get('slacks'))
    claims=value.get('verified_conclusions',[])
    return dict(version='recorded_mathematics_v2',source=dict(reference=reference,pointer='/mathematical_facts'),
        status=facts.get('status'),
        solver={k:facts.get(k) for k in ('status','converged','exitflag','iterations','function_evaluations','objective','initial_objective','scaled_violation')},
        original_feasible=facts.get('original_feasible'),relaxed_feasible=facts.get('relaxed_feasible'),
        returned_slacks=slacks,original_predicate_diagnostics=samples,
        zero_slack_with_positive_recorded_violation=bool(isinstance(slacks,dict) and slacks and all(x==0 for x in slacks.values())
            and any(r['positive_violation']>0 for task in samples.values() for r in task['samples'])),
        predicate_tolerance='Strict recorded comparison; no added acceptance tolerance',
        kkt={k:(facts.get('kkt') or {}).get(k) for k in ('primal_inf','stationarity_inf','global_optimality')},
        conclusion=[c.get('conclusion') if isinstance(c,dict) else c for c in claims],
        scope=[dict(conclusion=c.get('conclusion'),supported_interpretation=c.get('supported_interpretation'),
            unsupported_conclusions=c.get('unsupported_conclusions'),verification_status=c.get('verification_status')) for c in claims if isinstance(c,dict)],
        physical_validation=value.get('physical_validation'),task_acceptance=value.get('task_acceptance',facts.get('physical_task_acceptance')),
        independent_physical_acceptance_established=False)


def recorded_static_summary(value,reference):
    construction=value.get('construction')
    if not construction:return None
    return dict(source=dict(reference=reference,pointer='/construction'),
        **{k:v for k,v in construction.items() if k!='provenance'},
        local_model_constraints=value.get('local_model_constraints'),tension_margins_n=value.get('tension_margins_n'),
        task_acceptance=value.get('task_acceptance'))


def recorded_control_diagnostics(host,value):
    """Project update-bound solver/selection facts; never replay or rescore physics."""
    if not value.get('execution_id'):return None
    from extensions.tendon_family.control_evidence import ControlEvidence
    from extensions.tendon_family.gvs_reporting import vector3
    import numpy as np
    reader=ControlEvidence(host.store)
    try:source=reader.resolve(value['execution_id'])
    except ValueError as exc:return dict(status='unavailable',reason=str(exc))
    observations=reader.read_file(source,'controller_observations.json',[])
    if not observations:return None
    rows=[]
    for i,o in enumerate(observations):
        facts=o.get('mathematical_facts') or {};planned=facts.get('tensions')
        first=planned if facts.get('horizon')==1 and planned and not isinstance(planned[0],list) else planned[0] if planned else None
        actual=o.get('actual_tension_n');prediction=o.get('one_step_prediction')
        invalid=prediction is not None and (not vector3(prediction.get('tip_position_m')) or
            (prediction.get('tip_velocity_m_s') is not None and not vector3(prediction['tip_velocity_m_s'])))
        matched=None if first is None or actual is None else bool(np.asarray(first).shape==np.asarray(actual).shape
            and np.allclose(first,actual,rtol=0,atol=1e-10))
        rows.append(dict(update_id=i,time_s=o['time_s'],source=dict(reference=source['files']['controller_observations.json'],pointer='/'+str(i)),
            optimization_status=o.get('optimization_status'),optimization_raw_status=o.get('optimization_raw_status'),
            plan_accepted=o.get('plan_accepted'),plan_source=o.get('plan_source'),
            recovery=o.get('feasibility_recovery'),failure_response_used=o.get('failure_response_used'),
            planned_first_input_n=first,actual_input_n=actual,accepted_plan_matches_actual_input=matched if o.get('plan_accepted') else None,
            prediction_diagnostic_available=bool(prediction and not invalid and matched is not False),
            prediction_shape_invalid=invalid,complete_update_available=bool(o.get('complete_update_record')),
            solver_request_available=bool(o.get('solver_request_record'))))
    invalid=[r['update_id'] for r in rows if r['prediction_shape_invalid']]
    mismatches=[r['update_id'] for r in rows if r['accepted_plan_matches_actual_input'] is False]
    return dict(version='recorded_control_diagnostics_v1',updates=len(rows),
        prediction_aggregate_available=not invalid and not mismatches,
        invalid_prediction_updates=invalid,accepted_plan_input_mismatch_updates=mismatches,
        relevant_updates=[r for r in rows if r['update_id']>=len(rows)-6 or r['update_id'] in invalid+mismatches],
        full_observations_query=dict(reference=source['files']['controller_observations.json'],view='range',pointer='',start=0,count=100),
        scope='Historical applied-input observations and original independent acceptance retained. Invalid prediction aggregates cannot diagnose model error. No fallback mechanism or counterfactual physical success inferred.')


def data_access(host,reference,value):
    """Executable original-artifact reads; working-set paths remain a distinct view."""
    access=dict(reference=reference,view_scope='original_artifact',queries=[])
    if isinstance(value,list):
        access.update(items=len(value),queries=[dict(reference=reference,view='range',pointer='',start=0,count=min(100,max(1,len(value))))])
    elif isinstance(value,dict):
        access['queries']=[dict(reference=reference,view='full',pointer='/'+_token(k)) for k in
            ('trajectory','mathematical_facts','task_requirements','acceptance') if k in value]
        from tools.research.state import state
        if reference in state(host).get('results',[]) and value.get('execution_id'):
            from extensions.tendon_family.control_evidence import ControlEvidence
            reader=ControlEvidence(host.store)
            try:source=reader.resolve(value['execution_id'])
            except ValueError as exc:
                access['execution_files']=dict(status='unavailable',reason=str(exc));return access
            files=source['files']
            for key in ('controller_observations.json','trajectory.json.gz','control_spec.json','nmpc_updates.json'):
                if key in files:access['queries'].append(dict(reference=files[key],view='full' if key=='control_spec.json' else 'range',pointer='',start=0,count=100))
            if value.get('profile',{}).get('motion'):
                access['queries'].append(dict(reference=value['profile']['motion'],view='range',pointer='',start=0,count=100))
            observations=reader.read_file(source,'controller_observations.json',[])
            access['updates']=[dict(update_id=i,time_s=o['time_s'],
                observation_query=dict(reference=files['controller_observations.json'],view='full',pointer='/'+str(i)),
                complete_update_available=bool(o.get('complete_update_record')),
                solver_request_available=bool(o.get('solver_request_record')),
                mathematical_facts_query=dict(reference=files['controller_observations.json'],view='full',pointer=f'/{i}/mathematical_facts') if o.get('mathematical_facts') else None)
                for i,o in enumerate(observations)]
    return access


def _acceptance_metrics(acceptance, reference):
    metrics=[]
    for name,row in acceptance.get('components',{}).items():
        if type(row.get('value')) not in (int,float):continue
        pointer='/acceptance/components/'+_token(name)
        metrics.append(ReportedMetric(name=name,value=row['value'],unit=row.get('unit'),
            threshold=row.get('limit'),threshold_source=_location(reference,pointer+'/limit') if 'limit' in row else None,
            passed=row.get('passed'),scope='physical_task',source=_location(reference,pointer+'/value')))
    return metrics


def _search(value, reference):
    def step(row, pointer):
        return ControlSearchStep(label=row['label'], source=_location(reference, pointer),
            evaluation=row['reference'], candidate=row.get('candidate'),
            control_source=row.get('source'), prediction_base=row.get('prediction_base'),
            predicted_improvement=row.get('predicted_improvement'),
            actual_improvement=row.get('actual_improvement'), task_gap=row['task_gap'],
            metrics=_acceptance_metrics(row.get('original_acceptance') or {},row['reference']))

    rows=value['candidates']
    baselines=[step(r, f'/candidates/{i}') for i,r in enumerate(rows) if r['label']=='baseline']
    proposals=[step(r, f'/candidates/{i}') for i,r in enumerate(rows)
        if r['label'] in ('local_response_proposal', 'coordinate')][-3:]
    # The original best row may be a finite-difference probe, not a proposal.
    return ControlSearchEvidence(
        stop_reason=RecordedField(name='stop_reason', value=value['stop_reason'],
            source=_location(reference, '/stop_reason')) if 'stop_reason' in value else None,
        baselines=baselines, proposals=proposals,
        best=step(value['best'], '/best') if value.get('best') else None,
        all_steps=_location(reference, '/candidates'))


def _resources(value, reference):
    resources=[]
    def add(data, key, unit, prefix='', time_basis=None):
        if key in data:
            resources.append(ResourceUse(name=key, amount=data[key], unit=unit,
                time_basis=time_basis, source=_location(reference, prefix+'/'+_token(key))))

    for key,unit in (('physical_launches','evaluations'), ('physics_steps','steps'),
            ('charged_analysis_evaluations','analyses'), ('mathematical_reintegrations','reintegrations'),
            ('nmpc_updates','updates'), ('rl_actions','actions'), ('finite_difference_evaluations','evaluations')):
        add(value,key,unit)
    for key in ('charged_numerical_s','numerical_s','evaluation_elapsed_s'):
        add(value,key,'s',time_basis='recorded_elapsed_unspecified')
    boundary=value.get('boundary') or {}
    add(boundary,'elapsed_s','s','/boundary','worker_wall')
    costs=value.get('cost_feedback') or {}
    for key in ('new_physical_evaluations','evaluation_callbacks','cache_reuses'):
        add(costs,key,'evaluations','/cost_feedback')
    add(costs,'charged_numerical_s','s','/cost_feedback','recorded_elapsed_unspecified')
    # No cost computation: each entry is a recorded quantity, never additive by default.
    resources.extend([ResourceUse(name='provider_cost',unit='USD'),
        ResourceUse(name='parent_action_elapsed',unit='s',time_basis='parent_action_wall'),
        ResourceUse(name='cpu_time',unit='s',time_basis='cpu')])
    return resources


def result_card(host, reference):
    """L1 ResultCard from one trusted Store result; no formal read markers.

    The ordinary read boundary still enforces protected-result admission. Only
    saved candidate/measurement metadata used by existing projections is read.
    Copies isolate nested dicts from the underlying saved artifacts.
    """
    reference=deepcopy(plain(reference))
    value=deepcopy(read_evidence(host, dict(reference=reference), record_read=False))
    if not isinstance(value,dict):
        raise ValueError('RESULT_CARD_REQUIRES_RESULT_OBJECT')
    evidence=summarize_evidence(value,reference)
    binding=(value.get('scoped_claim') or {}).get('binding') or value.get('binding') or {}
    identity=ResultIdentity(result=_location(reference),
        study=value.get('owning_study') or value.get('study'),
        task_identity=evidence['task_identity'], candidate=value.get('candidate',value.get('design_candidate',binding.get('candidate'))),
        control_source=value.get('control_schedule_reference',value.get('source_reference',value.get('source'))),
        operation=value.get('operation'), model_identity=evidence['model_identity'],
        design_identity=evidence['design_identity'],
        evaluation_profile_identity=value.get('profile_identity'),evaluation_identity=value.get('execution_id'))
    summary=compact_evidence(value,reference,facts_only=True)['summary']
    recorded=recorded_math_summary(value,reference)
    if recorded is not None:summary['recorded_mathematics']=recorded
    metrics=[];violations=[];critical=[];mathematics=None;search=None
    resources=_resources(value,reference)
    details=[_location(reference)]
    context=[RecordedField(name=k,value=value[k],source=_location(reference,'/'+_token(k)))
        for k in ('purpose','rationale','hypothesis','fixed_conditions','changed_parameters','plan_decision') if k in value]
    for key in ('protocol','binding','analysis_applicability','score_semantics','provenance','configuration','proxy_values'):
        if key in value:details.append(_location(reference,'/'+key))
    if identity.candidate is not None:
        candidate=host.store.artifact(identity.candidate)
        identity=identity.model_copy(update=dict(canonical_task_identity=candidate.get('task_identity'),
            evaluation_profile_identity=identity.evaluation_profile_identity or candidate.get('profile_identity')))
        details.extend(_location(identity.candidate,'/'+key) for key in
            ('configuration','parameters','provenance') if key in candidate)
    if identity.control_source is not None:details.append(_location(identity.control_source))

    if value.get('scoped_claim'):
        summary=decision_result(value,reference)
        mathematics=MathematicalEvidence(claim=value['scoped_claim'],
            claim_source=_location(reference,'/scoped_claim'),
            requirement_source=_location(reference,'/task_analysis') if 'task_analysis' in value else None)
        if value.get('native_analysis'):
            from schemas.research_reporting import MathematicalQuantity
            mathematics=mathematics.model_copy(update=dict(
                problem_definition=_location(reference,'/native_analysis/basis'),
                quantities=[MathematicalQuantity(name=q['name'],value=q['value'],unit=q['unit'],
                    status='unverified_estimate',control_reoptimization='required' if value['operation']=='mujoco_direct_control_v1' else 'fixed_control',
                    source=_location(reference,q['source_pointer'])) for q in summary['native_analysis']['quantities']]))
            details.append(_location(reference,'/native_dynamics'))
            if value.get('control_schedule_reference'):details.append(_location(value['control_schedule_reference']))
        if value.get('operation') == 'task_capability' and (value.get('trajectory', {}).get('problem_definition') or value.get('trajectory',{}).get('method_version')):
            from tools.research.capability import populate_mathematics
            mathematics=populate_mathematics(mathematics,value['trajectory'],reference)
            if value['trajectory'].get('structural_comparison'):
                details.append(_location(value['trajectory']['structural_comparison']['baseline_result']))
        if value.get('optimal_sensitivity'):
            from tools.research.capability import populate_sensitivity
            mathematics=populate_sensitivity(mathematics,value['optimal_sensitivity'],reference)
            summary.pop('task_capability',None)
        if value.get('optimal_sensitivity') or value.get('trajectory',{}).get('method_version'):
            from tools.research.evidence_policy import mathematical_physical_relation
            from tools.research.state import state
            current=state(host)
            physical=[(r,host.store.artifact(r)) for key in ('results','physical_replays','rl_evaluations') for r in current.get(key,[])]
            relation=mathematical_physical_relation(value,physical)
            key='optimal_sensitivity' if value.get('optimal_sensitivity') else 'task_capability'
            summary[key]['physical_failure_relation']=relation
            details.extend(_location(s['reference'],s['pointer']) for s in relation.get('sources',[]))
            for i,output in enumerate(value.get('model',{}).get('endpoint_outputs',[])):
                if (output['name']=='tip_position' and output['frame']=='world'
                        and all(x==0 for x in output['C'][0]+output['D'][0])):
                    sources=[_location(reference,f'/model/endpoint_outputs/{i}/{k}/0') for k in ('C','D')]
                    summary[key]['local_output_limitation']=dict(world_x_first_order_state_and_input_coefficients='zero',
                        scope='This stored local linearization only; not nonlinear controllability or physical invariance.',
                        sources=[plain(s) for s in sources])
                    details.extend(sources)
        details.append(_location(reference,value['scoped_claim']['numerical_result_pointer']))
        for row in summary['margins']:
            constraint=next(c for c in value['task_analysis']['constraints'] if c['constraint_id']==row['constraint_id'])
            index=value['task_analysis']['constraints'].index(constraint)
            metrics.append(ReportedMetric(name=row['constraint_id'],value=row['observed_value'],
                unit=row['units'],threshold=row['bound'] if constraint['kind'] in ('norm_bound','path_bound') else None,
                threshold_source=_location(reference,f'/task_analysis/constraints/{index}/radius') if constraint['kind'] in ('norm_bound','path_bound')
                    else _location(reference,f'/task_analysis/constraints/{index}'),
                passed=row['status']=='satisfied_sample',scope='model_sample',time_s=row['absolute_time_s'],
                source=_location(reference,row['source_pointer']+'/value')))
            if row['status']!='satisfied_sample':violations.append(row['constraint_id'])
    elif 'acceptance' in value:
        summary['recorded_control_diagnostics']=recorded_control_diagnostics(host,value)
        components=(value['acceptance'] or {}).get('components',{})
        metrics=_acceptance_metrics(value['acceptance'] or {},reference)
        # Reuse existing task ranking and measured-extrema selection; do not rescore.
        gap=summary.get('task_gap',{})
        violations=sorted((k for k in gap.get('components',{}) if components.get(k,{}).get('passed') is False),
            key=lambda k:gap['components'][k],reverse=True)
        violations.extend(k for k,r in components.items() if r.get('passed') is False and k not in violations)
        diagnostic=physical_diagnostic(host,reference)
        critical=[CriticalObservation(time_s=r['time_s'],observed=deepcopy(r['observed']),
            source=_location(r['raw_reference'],r['read_pointer']),
            input_source=EvidenceLocation.model_validate(r['input_query']) if r.get('input_query') else None)
            for r in diagnostic['critical_samples']]
        if value.get('raw_reference'):
            raw_ref=value['raw_reference'];raw=host.store.artifact(raw_ref)
            details.append(_location(raw_ref))
            context.extend(RecordedField(name=key,value=raw[key],source=_location(raw_ref,'/'+key))
                for key in ('model_identity','mathematical_model_identity','physical_backend','scene_identity',
                    'tendon_order','physics_timestep_s') if key in raw)
            # Physics steps and model identities may live only in the saved measurement.
            if 'physics_steps' in raw:
                resources.append(ResourceUse(name='physics_steps',amount=raw['physics_steps'],
                    unit='steps',source=_location(raw_ref,'/physics_steps')))
    elif 'best' in value and 'candidates' in value:
        search=_search(value,reference)
        # compact_evidence already owns search summaries. Response matrices stay in Store.
        summary={k:v for k,v in summary.items() if k not in ('local_responses',)}
        details.extend([_location(reference,'/candidates'),_location(reference,'/starts')])
    construction=recorded_static_summary(value,reference)
    if construction:summary['recorded_static_construction']=construction
    return ResultCard(identity=identity,evidence_summary=evidence,
        recorded_context=context,metrics=metrics,main_violations=violations,critical_observations=critical,
        deterministic_summary=summary,mathematics=mathematics,control_search=search,
        resources=resources,detail_sources=details)
