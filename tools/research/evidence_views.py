"""Read-only result cards composed from existing deterministic evidence views.

No persistence, scientific dispatch, report generation or evidence registration.
L0/L2 stay in research_context; L3 stays in core.read_evidence/EvidenceQuery.
"""
from tools.research.budget import mathematical_remaining
from copy import deepcopy
from schemas.research_reporting import (
    ControlSearchEvidence, ControlSearchStep, CriticalObservation, EvidenceLocation,
    MathematicalEvidence, RecordedField, ReportedMetric, ResourceUse, ResultCard,
    ResultIdentity,
)
from tools.platform_store import plain
from tools.research.analysis import decision_result, diagnostic_layers, diagnostic_overview
from tools.research.core import read_evidence
from tools.research.evidence_policy import summarize_evidence
from tools.research.research_context import compact_evidence, physical_diagnostic
from tools.research.task_constraints import SCIENTIFIC_INTERPRETATION


def _location(reference, pointer=''):
    return EvidenceLocation(reference=reference, pointer=pointer)


def coupled_search_summary(value, reference):
    result=value.get('result') or {}
    if result.get('method')!='bounded_coupled_block_v1':return None
    return dict(status=result['status'],method=result['method'],interaction=result.get('interaction'),
        mathematical_analysis=result.get('mathematical_analysis'),interaction_source=result.get('interaction_source'),
        resource_use=result['resource_use'],score_semantics=result['score_semantics'],
        task_acceptance='unmeasured',scientific_citation_eligible=False,
        raw_query=dict(reference=reference,view='full',pointer='/result'))


def task_diagnosis(value, reference, *, detailed=False):
    """Project formal and deterministic diagnostic facts as separate scopes."""
    from tools.research.feedback import diagnostic_task_gap
    diagnostic=diagnostic_task_gap(value,reference)
    research=value.get('structure_research') or {}
    gap=(research.get('baseline') or {}).get('task_gap')
    pointer='/structure_research/baseline/task_gap'
    if gap is None and value.get('task_gap') is not None:
        gap=value['task_gap'];pointer='/task_gap'
    if gap is None and (value.get('acceptance') or {}).get('constraint_observations'):
        from tools.research.feedback import task_gap
        gap=task_gap(value);pointer='/acceptance/constraint_observations'
    formal_gap=gap
    if diagnostic is not None:
        gap=diagnostic
        pointer=('/diagnostic_task_gap' if value.get('diagnostic_task_gap') is not None else
            '/structure_research/records/0/observation/diagnostic_task_gap' if
            (research.get('records',[{}])[0].get('observation') or {}).get('diagnostic_task_gap') is not None else
            '/structure_research/records/0/mechanics/dynamic_execution')
    if gap is None:return None
    rows=gap.get('constraints',[]);conditions={}
    fields=('constraint_id','signal','observed_value','bound','bound_type','unit',
        'normalized_violation','passed','time_window','time_s','frame','material_s','sample_time','missing_reason',
        'source_pointer','source_reference','reference_window','reference_reduction','aggregation')
    for i,row in enumerate(rows):
        condition=row.get('condition_id') or row.get('load_condition') or 'unknown'
        location=pointer+('/'+str(i) if pointer.endswith('constraint_observations') else '/constraints/'+str(i))
        observation={k:deepcopy(row.get(k)) for k in fields}
        observation['source']=dict(reference=row.get('source_reference') or reference,pointer=row.get('source_pointer',location))
        conditions.setdefault(condition,[]).append(observation)
    projected=[]
    for condition,observations in conditions.items():
        # Retain distinct signals and both lower and upper limits. In particular,
        # a ratio must not replace its component observations or a small failure.
        representatives={}
        for row in observations:
            key=(row['signal'],row['bound_type'],row['unit'])
            old=representatives.get(key)
            score=row['normalized_violation']
            if old is None or (score is not None and (old['normalized_violation'] is None or score>old['normalized_violation'])):
                representatives[key]=row
        projected.append(dict(condition_id=condition,constraint_count=len(observations),
            failed_constraint_count=sum(r['passed'] is False for r in observations),
            unknown_constraint_count=sum(r['passed'] is None for r in observations),
            **({'constraints':observations} if detailed else {'observations':list(representatives.values())})))
    numeric=[r for r in rows if isinstance(r.get('normalized_violation'),(int,float))]
    worst=max((r['normalized_violation'] for r in numeric),default=None)
    routes=[]
    for i,record in enumerate(research.get('records',[])):
        execution=(record.get('mechanics') or {}).get('dynamic_execution') or {}
        for j,episode in enumerate(execution.get('episodes',[])):
            route=episode.get('route_geometry')
            if route is None:continue
            routes.append(dict(record_index=i,condition_id=episode.get('load_condition'),
                **{k:deepcopy(route.get(k)) for k in ('status','checked_poses','first_issue')},
                source=dict(reference=reference,pointer=f'/structure_research/records/{i}/mechanics/dynamic_execution/episodes/{j}/route_geometry')))
    qualification=deepcopy((research.get('baseline') or {}).get('qualification_diagnosis'))
    if qualification:
        for item in [qualification,*qualification.get('failed_qualifications',[])]:
            if item.get('source') is not None:item['source']['reference']=reference
    return dict(status='recorded_task_diagnosis',candidate=value.get('candidate'),
        task_identity=(value.get('binding') or {}).get('task_identity'),model_identity=value.get('model_identity'),
        diagnostic_status=diagnostic.get('status') if diagnostic else None,
        diagnostic_maximum_normalized_violation=worst if diagnostic else None,
        diagnostic_worst_constraints=[deepcopy(r) for r in numeric if r['normalized_violation']==worst] if diagnostic else [],
        qualification=qualification,
        formal_task_gap={k:deepcopy((formal_gap or {}).get(k)) for k in ('valid_complete','comparable','signed_task_gap','accepted')},
        valid_complete=(formal_gap or {}).get('valid_complete'),comparable=(formal_gap or {}).get('comparable'),
        maximum_normalized_violation=gap.get('signed_task_gap'),hard_gate_status=gap.get('hard_gate_status'),
        conditions=projected,route_geometry=routes,source=dict(reference=reference,pointer=pointer),
        detail_query=dict(reference=reference,view='working_set',pointer='/task_diagnosis'),
        raw_query=dict(reference=reference,view='full',pointer=pointer),
        numerical_qualification_query=dict(reference=reference,view='full',pointer='/diagnostic_layers')
            if value.get('diagnostic_layers') else None,
        parameter_changes=[dict(record_index=r.get('record_index'),parameter_values=r.get('parameter_values'),
            source=dict(reference=reference,pointer=f'/structure_research/records/{i}/parameter_values'))
            for i,r in enumerate(research.get('records',[])) if r.get('parameter_values')],
        limitations=['Recorded constraints only; absent values, units and exact peak times remain unknown.',
            'A scoring window is not a measured extremum time. Qualification and independent acceptance remain separate.',
            'Compact observations show the worst recorded normalized violation per signal and bound type; exact rows are available on demand.'])


def compact_task_diagnosis(diagnosis):
    """Few numerical ranges for history; complete per-condition facts stay readable."""
    if not diagnosis:return None
    groups={}
    for condition in diagnosis['conditions']:
        for row in condition.get('observations',condition.get('constraints',[])):
            if row['observed_value'] is None:continue
            key=(row['signal'],row['bound_type'],row['unit'])
            groups.setdefault(key,[]).append(row)
    return dict(diagnostic_status=diagnosis.get('diagnostic_status'),
        formal_task_gap=diagnosis.get('formal_task_gap'),
        worst_constraints=diagnosis.get('diagnostic_worst_constraints',[])[:2],
        metrics=[dict(signal=key[0],bound_type=key[1],unit=key[2],
            minimum=min(r['observed_value'] for r in rows),maximum=max(r['observed_value'] for r in rows),
            bounds=list(dict.fromkeys(r['bound'] for r in rows)),scope='per-condition representative observations')
            for key,rows in groups.items()],detail_query=diagnosis['detail_query'])


def acceptance_certificate(host, reference):
    """Complete original task-acceptance contract, without copying trajectories.

    Unsupported contracts keep strict whole-result admission. This projection
    runs no evaluator and grants no read credit until its exact delivery on wire.
    """
    from tools.research.state import state
    from tools.research.feedback import result_view
    from tools.research_tasks import _source_issue,_outcome_issue,assemble_acceptance
    from tools.state_io import digest
    s=state(host);raw=host.store.artifact(reference);acceptance=raw.get('acceptance') or {}
    if raw.get('kind')=='joint_condition_result_v1':
        from tools.research.conditions import joint_assessment
        issues=[];checked=None
        try:
            checked=joint_assessment(host,raw['condition_results'],require_reads=False)
            original=deepcopy(raw['aggregation']);recomputed=deepcopy(checked['aggregation'])
            for group in (original,recomputed):group['entries']=sorted(group['entries'],key=lambda row:row['case_id'])
            if original!=recomputed or raw['candidate']!=checked['candidate']:
                issues.append('JOINT_CERTIFICATE_DIFFERS_FROM_FROZEN_CONDITION_SOURCES')
        except (ValueError,KeyError) as exc:issues.append(str(exc))
        members=[acceptance_certificate(host,ref) for ref in raw['condition_results']]
        return dict(version='formal_acceptance_view_v1',status='acceptance_certificate',reference=reference,
            complete_acceptance_view=not issues and all(c['complete_acceptance_view'] for c in members),validation_issues=issues,
            owning_study=raw['owning_study'],current_study=host.run_id,candidate=raw['candidate'],
            aggregation=(checked or raw)['aggregation'],condition_certificates=members,
            limitations=['Every member retains its full evaluator, units, thresholds and independent execution sources. Main must read each member certificate under the original SELECT gate; this view grants no execution or selection permission.'])
    if acceptance.get('contract')!='research.task_acceptance' or not acceptance.get('components') or not raw.get('candidate'):
        return dict(status='acceptance_certificate_not_supported',reference=reference,complete_acceptance_view=False,
            reason='No complete registered physical task-acceptance contract; mathematics and unsupported evaluation types retain original strict admission.')
    candidate=host.store.artifact(raw['candidate']);cfg=candidate['configuration']
    view=result_view(host,reference)
    issues=[v for v in (_source_issue(acceptance),_outcome_issue(acceptance)) if v]
    if acceptance.get('task_identity')!=digest(cfg['task']):issues.append('ACCEPTANCE_TASK_IDENTITY_MISMATCH')
    sources=acceptance.get('sources',{})
    if (raw.get('evaluation_reference')!=sources.get('evaluation') or raw.get('profile_reference')!=sources.get('profile') or
            not sources.get('profile') or host.store.artifact(sources['profile'])!=raw.get('profile') or
            raw.get('profile',{}).get('task')!=cfg['task']):issues.append('ACCEPTANCE_SOURCE_BINDING_MISMATCH')
    if not issues:
        if raw.get('route')=='passive_protocol':
            from tools.research.physical_replay import evaluate_playback,passive_source
            from extensions.tendon_family.passive_execution import source_binding
            source=host.store.artifact(raw['source_reference'])
            simulation=host.store.artifact(raw['raw_reference'])
            expected=passive_source(cfg,raw['candidate'],source.get('execution',{}))
            if (source!=expected or simulation.get('physical_binding')!=source_binding(cfg) or
                    raw.get('model_identity')!=expected['model_identity'] or raw.get('design_identity')!=expected['design_identity']):
                issues.append('PASSIVE_PHYSICAL_SOURCE_BINDING_MISMATCH')
            if simulation.get('kind')=='passive_dynamic_execution_v2':
                from extensions.tendon_family.passive_execution import baseline_arm
                import hashlib
                l2=raw.get('passive_l2',{});pair=simulation.get('paired_ablation') or {}
                for arm,native in pair.get('arm_receipts',{}).items():
                    links=l2.get('arms',{}).get(arm,{})
                    leaf=baseline_arm(simulation) if arm=='baseline' else pair['ablation']
                    if not links:issues.append('PAIRED_ARM_STORE_RECEIPT_MISSING');continue
                    receipt=host.store.artifact(links['receipt_reference'])
                    if (host.store.artifact(links['raw_reference'])!=leaf or receipt.get('raw_reference')!=links['raw_reference']
                            or any(receipt.get(k)!=v for k,v in native.items()) or receipt.get('owning_study')!=raw['owning_study']
                            or receipt.get('parent_request_id')!=raw['request_id'] or receipt.get('parent_boundary')!=raw['boundary']):
                        issues.append('PAIRED_ARM_STORE_RECEIPT_MISMATCH')
                manifests=simulation.get('trace_files',[])
                if len(l2.get('traces',[]))!=len(manifests):issues.append('PASSIVE_TRACE_STORE_MANIFEST_MISSING')
                for original,trace in zip(manifests,l2.get('traces',[])):
                    body=host.store.artifact(trace['reference'],raw=True)
                    if any(trace.get(k)!=v for k,v in original.items()) or hashlib.sha256(body).hexdigest()!=trace['sha256'] or len(body)!=trace['bytes']:
                        issues.append('PASSIVE_TRACE_STORE_BINDING_MISMATCH')
            replayed,profile=evaluate_playback(cfg,simulation,raw['raw_reference'],
                digest(dict(candidate=raw['candidate'],source=raw['source_reference'])))
            profile.update(execution_id=raw['execution_id'],simulation=raw['raw_reference'],evaluation=raw['evaluation_reference'])
            if plain(replayed)!=host.store.artifact(sources['evaluation']) or profile!=raw['profile']:
                issues.append('PASSIVE_EVALUATOR_OR_PROFILE_DIFFERS_FROM_RAW_SAMPLES')
        motion_ref=view['evaluation_evidence'].get('trajectory')
        motion=host.store.artifact(motion_ref) if motion_ref else None
        if motion is None and raw.get('raw_reference'):
            motion=host.store.artifact(raw['raw_reference']).get('samples')
        original=assemble_acceptance(cfg,host.store.artifact(sources['evaluation']),host.store.artifact(sources['profile']),
            evaluation_reference=sources['evaluation'],profile_reference=sources['profile'],motion=motion,protocol_id=acceptance['protocol_id'])
        # Historical certificates predate this optional read-only diagnostic.
        # All original acceptance fields still compare exactly; a present new
        # diagnostic is recomputed and compared too, never trusted as authority.
        if 'constraint_observations' not in acceptance:original.pop('constraint_observations',None)
        if original!=acceptance:issues.append('ACCEPTANCE_DIFFERS_FROM_ORIGINAL_EVALUATOR_AND_PROFILE')
    return dict(version='formal_acceptance_view_v1',status='acceptance_certificate',reference=reference,
        complete_acceptance_view=not issues and view['complete'],validation_issues=issues,
        owning_study=raw.get('evaluation_owner') or raw.get('study') or raw.get('owning_study'),current_study=host.run_id,
        candidate=raw['candidate'],configuration_reference=candidate['configuration_reference'],
        source_control=view['controller'],solution_identity=view['solution_identity_sha256'],
        physical_model=dict(backend=cfg['policy']['backend'],dynamics_model=cfg['policy']['dynamics_model'],
            discretization=cfg['policy']['discretization'],mathematical_model_identity=raw.get('mathematical_model_identity'),
            execution_model_identity=raw.get('execution_model_identity'),profile_identity=raw.get('profile_identity')),
        frozen_task=dict(canonical_identity=s['spec'].get('canonical_task_identity'),effective_identity=acceptance.get('task_identity'),
            definition_query=dict(reference=candidate['configuration_reference'],view='full',pointer='/task'),evaluator=cfg['task']['evaluator']),
        execution=dict(execution_id=raw.get('execution_id'),complete=view['complete'],task_performance=view['task_performance'],
            fresh_current_study=view['fresh_current_study'],role=view['role']),
        condition_id=candidate.get('condition_id'),structure_candidate=candidate.get('structure_candidate'),
        sampling_coverage={k:raw['profile'][k] for k in ('complete','sampled_settling','tracking_sampling_complete','tool_axis_sampling_complete') if k in raw.get('profile',{})},
        acceptance=deepcopy(acceptance),
        detailed_evidence=dict(result=dict(reference=reference,view='full'),evaluation=sources.get('evaluation'),
            profile=sources.get('profile'),simulation=raw.get('raw_reference'),trajectory=view['evaluation_evidence'].get('trajectory')),
        limitations=['Independent registered model execution only; no hardware, cross-model, repeatability or global optimum claim.',
            'Historical/imported evidence, failing or invalid outcomes, incomplete conditions and wrong fidelity remain ineligible under original SELECT/confirm admission.'])


def diagnostic_relations(host, reference):
    """L1 only: relate the selected candidate's saved evidence, without solving."""
    from tools.research.state import state
    from tools.research.task_constraints import describe_analysis_requirements, analysis_capabilities
    from tools.research.capability import recorded_score_resolution
    from tools.research.research_context import measured_samples, recorded_changes
    from tools.research_tasks import task_adapter
    from tools.state_io import digest
    s=state(host);selected=host.store.artifact(reference,paths=('candidate',))
    candidate=selected.get('candidate',reference if reference in s['candidates'].values() else None)
    if candidate is None:return dict(status='candidate_selection_required',relations=[])
    c=host.store.artifact(candidate);cfg=c['configuration']
    mathematics=[(r,host.store.artifact(r,paths=('candidate','trajectory'))) for r in s.get('analysis_results',[])]
    math=[(r,v) for r,v in mathematics if v.get('candidate')==candidate and v.get('trajectory')][-3:]
    math=[(r,host.store.artifact(r)) for r,v in math]
    physics=[(r,host.store.artifact(r)) for r in [*s.get('physical_replays',[]),*s.get('results',[])]]
    physics=[(r,v) for r,v in physics if v.get('candidate')==candidate][-6:]
    selected_physics=next((row for row in physics if row[0]==reference),physics[-1] if physics else None)
    if physics:
        # Keep the original mathematical-control replay plus the requested/latest
        # result, rather than repeating every historical search perturbation.
        physics=list({r['artifact_id']:(r,v) for r,v in [physics[0],selected_physics,physics[-1]]}.values())
    relations=[]
    for mr,m in math:
        tr=m['trajectory'];grid=tr.get('horizon',{});model=m.get('model',{})
        for pr,p in physics:
            source=host.store.artifact(p['source_reference']) if p.get('source_reference') else {}
            commands=source.get('trajectory',{});raw,measurement=measured_samples(host,p)
            samples=raw.get('samples',[]);origin=source.get('provenance',{})
            prediction=source.get('mathematical_outputs') or {}
            same_control=origin.get('mathematical_result')==mr and commands.get('tensions_n')==tr.get('applied_input_n')
            checks=dict(candidate=m.get('candidate')==p.get('candidate'),
                task=commands.get('task_identity')==digest(cfg['task']),
                source_control=same_control,
                tendon_order=commands.get('tendon_order')==m.get('binding',{}).get('tendon_order'),
                actual_tensions=bool(samples) and len(samples)==len(commands.get('tensions_n',[]))+1 and
                    all(v.get('actual_tension_n')==u for v,u in zip(samples[1:],commands.get('tensions_n',[]))),
                time_grid=bool(samples) and len(samples)==len(commands.get('times_s',[])) and
                    all(abs(v['time_s']-t)<=m['protocol']['horizon_alignment_atol_s'] for v,t in zip(samples,commands.get('times_s',[]))),
                initial_state=bool(samples) and m.get('operating_point',{}).get('actual_time_s')==samples[0]['time_s']
                    and all(v==0 for k in ('qpos_rad','qvel_rad_s') for v in samples[0].get(k,[]))
                    and bool(samples[0].get('qpos_rad')) and all(v==0 for v in model.get('x0',[]))
                    and bool(model.get('x0')) and all(v==0 for v in tr.get('initial_delta_state',[])),
                saved_prediction_samples=bool(samples) and all(len(prediction.get(k,[]))==len(samples)
                    for k in ('times_s','tip_positions_m','tip_velocities_m_s')) and
                    prediction.get('times_s')==commands.get('times_s') and prediction.get('model_identity')==commands.get('model_identity'),
                recorded_aligned_difference=bool(p.get('comparison',{}).get('aligned')) and
                    p['comparison'].get('available_samples')==len(samples)==len(p['comparison'].get('samples',[])),
                numerical_replay=bool(tr.get('replay',{}).get('numerically_valid')))
            aligned=all(checks.values())
            aggregates={}
            for row in tr.get('replay',{}).get('records',[]):
                key=row['constraint_id']
                if key not in aggregates or row['value']>aggregates[key]['value']:
                    aggregates[key]={k:row[k] for k in ('value','units','absolute_time_s','radius') if k in row}
            relations.append(dict(kind='same_control_math_physics' if same_control else 'descriptive_different_control_conditions',
                status='comparable' if aligned else 'partial_comparison' if same_control else 'not_comparable',
                left=mr,right=pr,candidate=candidate,structure_identity=c.get('physical_design_identity',c['identity']),
                task_identity=digest(cfg['task']),task_requirements=dict(reference=mr,pointer='/task_analysis'),
                mathematical_model_identity=model.get('binding',{}).get('model_identity'),physical_model_identity=raw.get('execution_model_identity',p.get('model_identity')),
                method=tr.get('method_version'),control_source=p.get('source_reference'),
                solver=dict(status=tr.get('solver',{}).get('status'),optimality=tr.get('optimality_status'),
                    support_gap=tr.get('dual_checks',{}).get('replayed_support_gap')),
                physical_validity=p.get('acceptance',{}).get('status'),independent_physical_observation=True,
                control_sequence_identity=digest(commands) if commands else None,tendon_order=commands.get('tendon_order'),
                initial_state=dict(mathematics=dict(reference=mr,pointer='/model/x0'),physics=dict(reference=measurement.get('reference'),pointer='/samples/0' if p.get('raw_reference') else '/0')),
                operating_point=m.get('operating_point'),time_scope=grid,alignment=checks,
                missing_conditions=[k for k,v in checks.items() if not v],
                prediction_error_comparability=dict(status='comparable' if aligned else 'not_comparable_as_model_prediction_error',
                    reasons=[k for k,v in checks.items() if not v]),
                temporal_support=dict(kind='discrete_samples',physics_sample_count=len(samples),
                    scope=SCIENTIFIC_INTERPRETATION['time_scope']),
                mathematical_aggregates=aggregates,physical_aggregates=p.get('acceptance',{}).get('metrics'),
                sample_differences=p['comparison'] if aligned else None,
                supported_scope='Saved aligned prediction differences' if aligned else 'Recorded task aggregates only; no sample differences reconstructed',
                unsupported_conclusions=['Global nonlinear feasibility','Failure cause','Different-control difference as model error']))
    for (lr,l),(rr,r) in zip(physics,physics[1:]):
        relations.append(dict(kind='same_candidate_different_controllers',status='descriptive_comparison',left=lr,right=rr,
            candidate=candidate,task_identity=digest(cfg['task']),
            structure_identity=c.get('physical_design_identity',c['identity']),
            task_conditions=task_adapter(cfg).condition_view(),time_grid=cfg['task']['timing'],
            model_sources=[v.get('model_identity',v.get('scientific_identity')) for v in (l,r)],
            initial_conditions=dict(configuration=c['configuration_reference'],pointer='/task/initializer'),
            tendon_order=[t['id'] for t in cfg['robot']['structure']['data']['tendons']],
            numerical_validity=[v.get('acceptance',{}).get('status') for v in (l,r)],
            controls=[l.get('source_reference',lr),r.get('source_reference',rr)],
            physical_aggregates=[v.get('acceptance',{}).get('metrics') for v in (l,r)],
            unsupported_conclusions=['GVS/MuJoCo model error','Single-factor causal attribution']))
    # A search's neighbouring evidence is read only here, never in every L0.
    comparisons=[]
    for mr,m in math[-1:]:
        if m['trajectory'].get('replayed_violation') is None:continue
        peers=[(r,v) for r,v in mathematics if v.get('candidate')!=candidate and v.get('trajectory')
            and v['trajectory'].get('replayed_violation') is not None
            and v.get('protocol')==m.get('protocol') and v.get('binding',{}).get('task_identity')==m.get('binding',{}).get('task_identity')
            and v['trajectory'].get('method_version')==m['trajectory'].get('method_version')
            and v.get('task_analysis',{}).get('constraints')==m.get('task_analysis',{}).get('constraints')]
        if peers:
            lr,l=min(peers,key=lambda rv:abs(rv[1]['trajectory'].get('replayed_violation',float('inf'))-m['trajectory'].get('replayed_violation',0)))
            comparisons.append(dict(kind='different_structure_task_results',left=lr,right=mr,
                candidates=[l['candidate'],candidate],resolution=recorded_score_resolution(l,m),
                changed_parameters=recorded_changes(host.store.artifact(l['candidate'])['parameters'],c['parameters']),
                verified_constraints=[dict(reference=r,pointer='/trajectory/coverage') for r in (lr,mr)],
                independent_physical_support=dict(left=[r for r in [*s.get('physical_replays',[]),*s.get('results',[])]
                    if host.store.artifact(r).get('candidate')==l['candidate']],right=[r for r,v in physics]),
                causal_attribution='Unavailable: independently reoptimized control and distinct structures'))
    diagnosis=None
    chosen=next(((r,v) for r,v in physics if r==reference),physics[-1] if physics else None)
    if chosen:
        pr,p=chosen;diagnosis=physical_diagnostic(host,pr)
        req=describe_analysis_requirements(cfg,{})
        methods=analysis_capabilities(cfg,req,s['spec']['analysis_protocol'],remaining_evaluations=mathematical_remaining(s['spec'],s.get('mathematical_evaluations',0)))
        diagnosis.update(task_conditions=task_adapter(cfg).condition_view(),
            temporal_support=dict(kind='selected_discrete_observations',
                times_s=[r['time_s'] for r in diagnosis['critical_samples']],
                scope=SCIENTIFIC_INTERPRETATION['time_scope']),
            saved_controller_predictions=dict(reference=pr,pointer='/profile/one_step_prediction_evidence',
                evidence=p.get('profile',{}).get('one_step_prediction_evidence'),
                scope='Saved NMPC predictions are distinct from the earlier CONIC control witness; inspect per-update alignment before error claims') if not p.get('source_reference') else None,
            bound_mathematical_prediction=next((r for r in relations if r.get('right')==pr and r['kind']=='same_control_math_physics'),None),
            competing_hypotheses=[dict(kind='hypothesis',text=t) for t in (
                'Finite-horizon control or braking limitation','Local affine prediction disagreement','Structure/input authority limitation')],
            discriminating_methods=[{k:v[k] for k in ('operation','reasons','status','evaluations','prerequisites','limitations') if k in v}
                for v in methods if v['operation'] in ('instantaneous_braking_v1','native_dynamics_v1','short_input_response_v1','task_capability')],
            braking_scope='Exact saved state/input required. Instantaneous min velocity-direction acceleration is not a remaining-horizon stop guarantee; no physical experiment launched.')
    return dict(version='diagnostic_relations_v2',candidate=candidate,relations=relations,search_comparisons=comparisons,
        scientific_interpretation=SCIENTIFIC_INTERPRETATION,
        task_diagnosis=diagnosis,raw_evidence='Original Store references only; query trajectories/models on demand',
        authority='Derived L1 relations; Reporter explanations remain hypotheses; independent evaluator owns acceptance')


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
        # An invalid objective can still own complete recorded trajectories.
        # Advertise exact raw reads, never substitute observations for acceptance.
        executions=[]
        fields=('time_s','force_world_n','material_positions_m','tip_m','material_velocities_m_s',
            'tip_velocity_m_s','static_balance_inf_nm','actual_tension_n','tendon_length_m',
            'length_residual_m','ncon')
        for i,record in enumerate((value.get('structure_research') or {}).get('records',[])):
            raw=(record.get('mechanics') or {}).get('dynamic_execution')
            if not raw:continue
            pointer=f'/structure_research/records/{i}/mechanics/dynamic_execution'
            episodes=[]
            for j,episode in enumerate(raw.get('episodes',[])):
                path=pointer+f'/episodes/{j}';samples=episode.get('samples',[])
                row=dict(load_condition=episode.get('load_condition'),sample_count=len(samples),
                    qualifications_query=dict(reference=reference,view='full',pointer=path+'/qualifications'))
                if 'route_geometry' in episode:
                    row['route_geometry_query']=dict(reference=reference,view='full',pointer=path+'/route_geometry')
                if samples:
                    row['sample_queries']={name:dict(reference=reference,view='fields',pointer=path+f'/samples/{index}',
                        fields=[key for key in fields if key in samples[index]]) for name,index in (('first',0),('last',len(samples)-1))}
                    row['sample_range_query']=dict(reference=reference,view='range',pointer=path+'/samples',start=0,count=1)
                episodes.append(row)
            executions.append(dict(source=dict(reference=reference,pointer=pointer),status=raw.get('status'),episodes=episodes))
        if executions:
            access['recorded_executions']=executions
            access['observation_scope']='Saved samples only, including unqualified executions. First/last samples do not replace frozen scoring/reference windows or establish task acceptance.'
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


def metric_semantics(value, name):
    """Direction comes from the recorded constraint/evaluator, never the number."""
    constraint=next((c for c in (value.get('task_analysis') or {}).get('constraints',[])
        if c['constraint_id']==name),None)
    if constraint and constraint['kind']=='norm_bound':
        return dict(preference='lower',definition='Norm of recorded signal minus reference',
            signal=constraint['signal'],source_pointer='/task_analysis/constraints/'+str(value['task_analysis']['constraints'].index(constraint)))
    acceptance=value.get('acceptance') or {}
    if acceptance.get('task_family')=='task.reach' and name in (
            'evaluator:task_bound','holding_position','holding_speed','force_bounds','solver_errors'):
        labels={'evaluator:task_bound':'terminal_position_error',
            'holding_position':'holding_max_position_error','holding_speed':'holding_max_speed',
            'force_bounds':'force_bound_violation','solver_errors':'solver_error_count'}
        return dict(preference='lower',definition=labels[name],source_pointer='/acceptance/components/'+_token(name))
    return dict(preference='unknown',definition='No registered ordering for this metric')


def _replay_metrics(value, reference):
    """One extremum per recorded constraint; retain every strict failed sample."""
    if value.get('operation')=='task_capability' and not (value.get('trajectory') or {}).get('replay',{}).get('numerically_valid'):
        return []
    records=(value.get('trajectory') or {}).get('replay',{}).get('records',[])
    constraints=(value.get('task_analysis') or {}).get('constraints',[])
    metrics=[]
    for j,c in enumerate(constraints):
        rows=[(i,r) for i,r in enumerate(records) if r['constraint_id']==c['constraint_id']]
        if not rows or c['kind']!='norm_bound' or any(type(r.get('value')) not in (int,float) for _,r in rows):continue
        i,row=max(rows,key=lambda pair:pair[1]['value'])
        times=[r['absolute_time_s'] for _,r in rows]
        metrics.append(ReportedMetric(name=c['constraint_id'],value=row['value'],unit=c['signal']['units'],
            threshold=c['radius'],passed=all(r['value']<=c['radius'] for _,r in rows),
            scope='model_sample',time_s=row['absolute_time_s'],window_s=(min(times),max(times)),
            source=_location(reference,f'/trajectory/replay/records/{i}/value'),
            threshold_source=_location(reference,f'/task_analysis/constraints/{j}/radius')))
    return metrics


def quantitative_facts(value, reference):
    """Small deterministic state view; no language-model interpretation or new score."""
    trajectory=value.get('trajectory') or {};claim=value.get('scoped_claim') or {}
    acceptance=value.get('acceptance') or {};construction=value.get('construction') or {}
    facts=dict(computation_status=value.get('status'),solver=trajectory.get('solver'),
        mathematical_conclusion=claim.get('conclusion'),verification_status=claim.get('verification_status'),
        task_acceptance=acceptance.get('status',value.get('task_acceptance')),
        source=dict(reference=reference,pointer=''))
    facts['diagnostic_layers']=diagnostic_layers(value)
    facts['diagnostic_overview']=diagnostic_overview(facts['diagnostic_layers'])
    if claim:
        model=value.get('model') or {};binding=claim.get('binding') or {}
        facts['model_context']=dict(basis=binding.get('basis'),model_scope=trajectory.get('model_scope'),
            solver_scope=trajectory.get('solver_scope'),
            state_dimension=sum(s['dimension'] for s in model.get('state_definition',[])) or None,
            generalized_coordinate_count=len(binding.get('coordinate_order',[])) or None,
            physical_inputs=claim.get('physical_inputs'),source=dict(reference=reference,pointer='/scoped_claim'))
    if acceptance:
        settling=((value.get('profile') or {}).get('control_parameters') or {}).get('data',{}).get('settling',{})
        duration=acceptance.get('timing',{}).get('duration_s');window=settling.get('window_s')
        facts['acceptance']=dict(accepted=acceptance.get('accepted'),components=acceptance.get('components',{}),
            holding_window_s=[duration-window,duration] if duration is not None and window is not None else None,
            timing={k:v for k,v in acceptance.get('timing',{}).items() if k!='termination'},
            termination_conditions=acceptance.get('timing',{}).get('termination'),
            termination_conditions_role='configured conditions, not observed termination reason',
            source=dict(reference=reference,pointer='/acceptance'))
        facts['evaluation_valid']= (acceptance.get('components',{}).get('evaluation_validity') or {}).get('passed')
    if construction:
        facts['operating_point']=dict(static_equilibrium=construction.get('static_equilibrium'),
            target_position_distance_m=construction.get('position_residual_m'),
            residual_semantics='distance to task target; not force or mechanical equilibrium residual',
            source=dict(reference=reference,pointer='/construction'))
    replay=trajectory.get('replay') or {}
    if replay.get('records'):
        facts['replay_checks']={k:v for k,v in replay.items() if k not in ('records','states','outputs') and not isinstance(v,(dict,list))}
        times=sorted({r['absolute_time_s'] for r in replay['records']})
        facts['sampled_constraints']=dict(checked_constraint_sample_records=len(replay['records']),
            checked_unique_times_s=times,checked_time_range_s=[min(times),max(times)],
            failed_samples=[dict(constraint_id=r['constraint_id'],time_s=r['absolute_time_s'],
                value=r['value'],unit=r.get('units'),violation=r.get('violation'),
                source=dict(reference=reference,pointer=f'/trajectory/replay/records/{i}'))
                for i,r in enumerate(replay['records']) if r.get('passed') is False],
            all_requested_checked=trajectory.get('all_requested_checked'),
            full_requested_coverage=trajectory.get('full_requested_coverage'),
            source=dict(reference=reference,pointer='/trajectory/replay'))
    t1=value.get('nonlinear_capability')
    if t1:
        quality=deepcopy(t1['search_quality'])
        if 'active_coefficients' in quality:
            indices=quality.pop('active_coefficients')
            quality['active_coefficient_count']=len(indices) if indices is not None else quality.get('search_dimension')
            quality['active_coefficients_query']=dict(reference=reference,view='full',pointer='/nonlinear_capability/search_quality/active_coefficients')
        facts['nonlinear_research']=dict(
            metrics=[dict(name=key,value=t1['best_metrics'][key],unit=unit,
                source=dict(reference=reference,pointer='/nonlinear_capability/best_metrics/'+key))
                for key,unit in t1.get('metric_units',{}).items()],
            best_found_J=dict(value=t1['best_found_J'],unit='1',
                source=dict(reference=reference,pointer='/nonlinear_capability/best_found_J')),
            reliability=dict(stop_reason=t1['stop_reason'],search_quality=quality,
                source=dict(reference=reference,pointer='/nonlinear_capability')),
            detail_query=dict(reference=reference,view='full',pointer='/nonlinear_capability'),
            scope='Finite-budget native model observations; task acceptance remains independent.')
    t2=value.get('nonlinear_response')
    if t2:
        facts['nonlinear_research']=dict(directions=[dict(
            direction_id=d.get('direction_id','parameter'),status=d['direction_status'],reasons=d.get('reasons',[]),
            source=dict(reference=reference,pointer='/nonlinear_response'+('/directions/'+str(i) if 'directions' in t2 else '')),
            detail_query=dict(reference=reference,view='full',pointer='/nonlinear_response'+('/directions/'+str(i) if 'directions' in t2 else '')))
            for i,d in enumerate(t2.get('directions',[t2]))],
            referenced_costs_query=dict(reference=reference,view='full',pointer='/nonlinear_response/referenced_t1_costs'),
            scope='Fixed-control and reoptimized quantities retain their separate source pointers in mathematics.quantities; prior T1 costs are referenced, not charged again.')
    return facts


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


def native_control_domain(value, *, detailed=False):
    """Actual saved input ranges and declared local box; no physics or coverage claim."""
    import numpy as np
    from tools.research.contracts import LocalControlSearchSettings
    from tools.research.control_correction import corrected_tensions
    raw=value.get('native_dynamics') or {};search=raw.get('optimization') or {}
    settings=(value.get('requested_operation',{}).get('control_optimization') or {}).get('settings')
    tr=(raw.get('original_schedule') or {}).get('trajectory') or {}
    bounds=value.get('binding',{}).get('tension_bounds_n')
    if not settings or not tr.get('tensions_n') or not bounds or not search.get('best') or not raw.get('optimized_schedule'):return None
    cfg=LocalControlSearchSettings.model_validate(settings);base=np.asarray(tr['tensions_n']);limits=np.asarray(bounds)
    best=np.asarray(raw.get('best_schedule',raw['optimized_schedule'])['trajectory']['tensions_n'])
    def ranges(u):return np.stack([u.min(axis=0),u.max(axis=0)],axis=1).tolist()
    visited=None
    if detailed and all('coefficients_n' in r for r in search.get('candidates',[])):
        lo=base.min(axis=0);hi=base.max(axis=0)
        for row in search.get('candidates',[]):
            start=next((r['schedule']['trajectory'] for r in raw.get('start_sources',[]) if r['start']==row['start']),tr)
            u=corrected_tensions(start['tensions_n'],start['times_s'][:-1],cfg.knots_s,row['coefficients_n'],limits[:,1],cfg.correction_window_s)
            lo=np.minimum(lo,u.min(axis=0));hi=np.maximum(hi,u.max(axis=0))
        visited=np.stack([lo,hi],axis=1).tolist()
    return dict(tendon_order=tr['tendon_order'],physical_bounds_n=bounds,
        method=cfg.method,knot_count=len(cfg.knots_s),active_coefficient_count=search.get('search_dimension'),
        final_search_radii_n=list(search.get('trust_radii_n',{}).values()),
        initial_range_n=ranges(base),best_range_n=ranges(best),recorded_schedule_range_n=visited,
        local_envelope_n=np.stack([np.maximum(limits[:,0],base.min(axis=0)-cfg.coefficient_limit_n),
            np.minimum(limits[:,1],base.max(axis=0)+cfg.coefficient_limit_n)],axis=1).tolist(),
        settings={k:getattr(cfg,k) for k in ('coefficient_limit_n','initial_radius_n','minimum_radius_n','difference_step_n')},
        coefficient_boundary=bool(max(abs(x) for x in search['best']['coefficients_n'])>=cfg.coefficient_limit_n-1e-10),
        input_saturation=dict(lower=bool(np.any(best<=limits[:,0]+1e-10)),upper=bool(np.any(best>=limits[:,1]-1e-10))),
        scope='Per-channel extrema of saved schedules, not joint control-space coverage. The temporal basis can further restrict the envelope. Local failure does not establish structural inability. Main may choose a wider correction domain, another explicit/Native/Conic/NMPC start, or another experiment; no fixed order.')


def native_search_summary(value, reference, *, detailed=False):
    """Recorded effort and termination, without controls or a convergence claim."""
    search=(value.get('native_dynamics') or {}).get('optimization')
    if not search:return None
    baseline=next((r for r in search.get('candidates',[]) if r.get('label')=='baseline'),{})
    cost=search.get('cost_feedback') or {}
    def metrics(row):
        measure=row.get('measure') or {}
        return {k:measure[k] for k in ('normalized_gap','terminal_position_error_m',
            'holding_max_position_error_m','holding_max_speed_m_s','signed_maximum_excess') if k in measure}
    domain=native_control_domain(value,detailed=detailed);stop=search.get('stop_reason','');termination=[]
    if stop=='evaluation_request_budget':termination.append('recorded_callback_cap')
    if stop=='iteration_limit':termination.append('recorded_iteration_cap')
    if domain and domain['final_search_radii_n'] and all(r<domain['settings']['minimum_radius_n'] for r in domain['final_search_radii_n']):
        termination.append('local_radii_below_declared_minimum')
    if any(r.get('diagnostic')=='no_effective_response' for r in search.get('local_responses',[])):
        termination.append('recorded_degenerate_local_response')
    if domain and domain['coefficient_boundary']:termination.append('best_coefficients_at_declared_boundary')
    if domain and any(domain['input_saturation'].values()):termination.append('best_inputs_at_physical_bound')
    if stop.startswith('numerical_failure'):termination.append('recorded_local_numerical_failure')
    if stop=='local_target_reached':termination.append('sampled_model_target_reached_without_independent_acceptance')
    return dict(source=dict(reference=reference,pointer='/native_dynamics/optimization'),
        algorithm=search.get('algorithm'),stop_reason=search.get('stop_reason'),
        iterations_started=search.get('iterations_started'),search_dimension=search.get('search_dimension'),
        callbacks=cost.get('evaluation_callbacks'),requested_callbacks=cost.get('request_budget'),
        starts=dict(selected=search.get('start_count',1),unique_executed_sequences=cost.get('unique_input_sequences'),
            duplicate_sequence_reuses=cost.get('cache_reuses',0),
            outcomes=[dict(start=r['start'],initial_gap=r.get('initial_gap'),
                best_gap=(r.get('best') or {}).get('measure',{}).get('normalized_gap')) for r in search.get('start_feedback',[])]),
        baseline=metrics(baseline),best=metrics(search.get('best') or {}),
        control_domain=domain,termination_facts=termination,
        bottleneck_query=dict(reference=reference,view='working_set',pointer='/bottleneck_diagnosis'),
        model_predicates_passed=(search.get('best') or {}).get('task_gap',{}).get('accepted'),
        interpretation='Recorded finite search only. Iteration/callback limits are not convergence or structural infeasibility. Model predicates are not independent acceptance.')


def bottleneck_diagnosis(host, reference, *, detailed=False):
    """Compose source-linked explanations from saved evidence; never run physics."""
    import numpy as np
    from tools.research.state import state
    from tools.state_io import digest
    s=state(host);anchor=host.store.artifact(reference)
    candidate=anchor.get('candidate') or reference
    record=host.store.artifact(candidate);cfg=record.get('configuration')
    if cfg is None:raise ValueError('CANDIDATE_OR_CANDIDATE_BOUND_RESULT_REQUIRED')
    controls=[];mechanisms=[]
    for ref in s.get('analysis_results',[]):
        meta=host.store.artifact(ref,paths=('candidate','status','operation'))
        if meta.get('candidate')!=candidate or meta.get('status')!='computed':continue
        if meta.get('operation') in ('mujoco_direct_control_v1','mujoco_nonlinear_task_capability_v1'):
            controls.append((ref,meta))
        elif meta.get('operation')=='mechanism_structure_v1':mechanisms.append((ref,host.store.artifact(ref)))
    chosen=next((r for r in controls if r[0]==reference),controls[-1] if controls else None)
    explanations=[];missing=[];facts=None;mechanism_facts=[];questions=[]
    if chosen:
        ref=chosen[0];value=host.store.artifact(ref);search=value['native_dynamics']['optimization'];best=search['best']
        facts=native_search_summary(value,ref,detailed=detailed)
        measure=best['measure'];failed=measure['signed_maximum_excess']>0
        facts.update(worst_constraint=measure.get('worst_constraint'),start_count=search.get('start_count',1),
            source_control=value.get('requested_operation',{}).get('control_optimization',{}).get('source'),
            best_control_query=dict(reference=ref,view='full',pointer='/best_control_schedule_reference' if value.get('best_control_schedule_reference') else '/control_schedule_reference'))
        if detailed:
            facts.update(start_feedback=[dict(start=r['start'],initial_gap=r.get('initial_gap'),
                best_metrics=(r.get('best') or {}).get('measure'),best_sequence_hash=(r.get('best') or {}).get('sequence_hash'))
                for r in search.get('start_feedback',[])],settings=value['requested_operation']['control_optimization']['settings'],
                local_responses=search.get('local_responses'),cost=value['native_dynamics'].get('cost'),
                best_metrics=measure,baseline_metrics=search['candidates'][0]['measure'])
        if failed:
            reasons=['Finite local search found no passing control; existence of another legal control remains untested.']
            if search.get('start_count',1)==1:reasons.append('One recorded starting sequence in this request.')
            if search['stop_reason'] in ('evaluation_request_budget','iteration_limit','stagnation','degenerate_local_response'):
                reasons.append('Recorded stop: '+search['stop_reason'])
            explanations.append(dict(status='control_search_evidence_insufficient',reasons=reasons,
                source=dict(reference=ref,pointer='/native_dynamics/optimization')))
            questions.append('Would another explicitly chosen start, knot basis or legal search scale change the full-task result?')
        comparable=[]
        for other_ref,_ in controls:
            if other_ref==ref:continue
            other=host.store.artifact(other_ref,paths=('binding','protocol','native_dynamics.initial_state',
                'requested_operation.control_optimization','native_dynamics.optimization.best.measure'))
            same=all(other.get('binding',{}).get(k)==value.get('binding',{}).get(k)
                for k in ('effective_configuration_identity','task_identity'))
            same=same and other.get('protocol')==value.get('protocol') and digest(other['native_dynamics']['initial_state'])==digest(value['native_dynamics']['initial_state'])
            if same:comparable.append(dict(reference=other_ref,source=other['requested_operation']['control_optimization']['source'],
                settings=other['requested_operation']['control_optimization']['settings'],
                best_metrics=other['native_dynamics']['optimization']['best']['measure']))
        facts['comparable_search_count']=len(comparable)
        if detailed:facts['comparable_searches']=comparable
        for mr,m in mechanisms:
            study=m.get('structure_research',{});records=study.get('records',[])
            if not records:continue
            point=m.get('operating_point',{});origin=point.get('source') or {};target=study.get('target',{})
            relevant=(origin.get('analysis')==ref and origin.get('sequence_hash')==best['sequence_hash'])
            row=records[0];mechanics=row.get('mechanics',{});velocity=mechanics.get('tip_velocity_m_s')
            interval=mechanics.get('function_metrics',{}).get('instantaneous_speed_derivative_range_m_s2')
            observation=row.get('observation') or {}
            fact=dict(reference=mr,target=target,observation={k:observation[k] for k in ('status','value','unit','reason') if k in observation},
                operating_point={k:point[k] for k in ('name','actual_time_s','remaining_task_s','phase','input_units') if k in point},
                operating_point_query=dict(reference=mr,view='full',pointer='/operating_point'),
                from_selected_best_control=relevant,remaining_task_s=origin.get('remaining_task_s'),
                scope='Local instantaneous mechanics; not a certificate for the complete task.')
            if interval is not None:
                fact.update(speed_derivative_range_m_s2=interval,interpretation='Minimum and maximum signed d(speed)/dt over the recorded legal tension box; a negative minimum permits instantaneous slowing at this state.')
                if (relevant and failed and interval[0]>=0 and origin.get('remaining_task_s',0)>0):
                    explanations.append(dict(status='structural_drive_concern',
                        reason='At this best-control state the saved legal tension box provides no negative instantaneous speed derivative.',
                        source=dict(reference=mr,pointer='/structure_research/records/0/mechanics/function_metrics/instantaneous_speed_derivative_range_m_s2')))
            if detailed:fact['raw_query']=dict(reference=mr,view='full',pointer='/structure_research/records/0')
            mechanism_facts.append(fact)
        if not any(r['from_selected_best_control'] for r in mechanism_facts):
            missing.append('No saved mechanism result bound to the selected best-control trajectory; baseline mechanisms cannot explain its failure.')
            questions.append('What drive or braking authority exists at a selected real best-control state with remaining task time?')
    else:missing.append('No completed Native control search for this exact candidate and condition.')
    explanations.append(dict(status='unresolved',reason='Saved finite search and local mechanisms do not distinguish global structural infeasibility from unexplored controls.'))
    return dict(version='structure_control_diagnosis_v1',candidate=candidate,
        candidate_profile_current=(record['profile_identity']==s.get('profile',{}).get('identity')) if record.get('profile_identity') else None,
        selected_result_implementation_current=(value.get('implementation')==s.get('freeze')) if chosen else None,
        condition_id=record.get('condition_id') or next((r['condition_id'] for r in s['spec'].get('task_conditions',[]) if record.get('task_identity')==digest(r['task'])),None),
        task_identity=digest(cfg['task']),selected_result=chosen[0] if chosen else None,
        control_search=facts,mechanisms=mechanism_facts[-3:],explanations=explanations,missing_evidence=missing,
        optional_scientific_questions=questions,
        detail_query=dict(reference=reference,view='working_set',pointer='/bottleneck_diagnosis'),
        scope='On-demand interpretation of original evidence; no action selection, elimination rule or new scientific acceptance.')


def _resources(value, reference):
    resources=[]
    def add(data, key, unit, prefix='', time_basis=None):
        if key in data:
            resources.append(ResourceUse(name=key, amount=data[key], unit=unit,
                time_basis=time_basis, source=_location(reference, prefix+'/'+_token(key))))

    for key,unit in (('physical_launches','evaluations'), ('physics_steps','steps'), ('physics_steps_lower_bound','steps'),
            ('charged_analysis_evaluations','analyses'), ('mathematical_reintegrations','reintegrations'),
            ('nmpc_updates','updates'), ('rl_actions','actions'), ('finite_difference_evaluations','evaluations')):
        add(value,key,unit)
    for key in ('charged_numerical_s','numerical_s','evaluation_elapsed_s'):
        add(value,key,'s',time_basis='recorded_elapsed_unspecified')
    actual=value.get('actual_resource_consumption') or {}
    uncertain=value.get('physical_cost_status',{}).get('unobserved_work_possible',False)
    for key,unit in (('model_builds','models'),('physics_steps','steps'),('attempted_steps','steps'),
            ('native_forward_calls','evaluations'),('episodes_started','episodes'),('episodes_completed','episodes')):
        if key in actual:
            resources.append(ResourceUse(name=key+('_lower_bound' if uncertain else ''),amount=actual[key],unit=unit,
                source=_location(reference,'/actual_resource_consumption/'+key)))
    boundary=value.get('boundary') or {}
    add(boundary,'elapsed_s','s','/boundary','worker_wall')
    add(value,'cpu_time_s','s',time_basis='cpu')
    add(boundary,'cpu_time_s','s','/boundary','cpu')
    add((value.get('acceptance') or {}).get('timing') or {},'simulation_wall_s','s',
        '/acceptance/timing','recorded_elapsed_unspecified')
    costs=value.get('cost_feedback') or {}
    for key in ('new_physical_evaluations','evaluation_callbacks','cache_reuses'):
        add(costs,key,'evaluations','/cost_feedback')
    add(costs,'charged_numerical_s','s','/cost_feedback','recorded_elapsed_unspecified')
    native=value.get('native_dynamics')
    if native is not None:
        cost=native.get('cost') or {}
        for key,unit in (('model_builds','models'),('rollouts','rollouts'),('physics_steps','steps'),('optimization_evaluations','evaluations')):
            resources.append(ResourceUse(name='native_'+key,amount=cost.get(key),unit=unit,
                source=_location(reference,'/native_dynamics/cost/'+key) if key in cost else None))
    if value.get('nonlinear_response'):
        costs=value['nonlinear_response']['cost']
        for field,unit in [('model_builds','models'),('rollouts','rollouts'),('physics_steps','steps'),('optimization_evaluations','evaluations')]:
            add(costs,field,unit,'/nonlinear_response/cost')
    add(value,'admission_preparation_numerical_s','s',time_basis='parent_action_wall')
    # No cost computation: each entry is a recorded quantity, never additive by default.
    resources.extend([ResourceUse(name='provider_cost',unit='USD'),
        ResourceUse(name='parent_action_elapsed',unit='s',time_basis='parent_action_wall'),
        ResourceUse(name='cpu_time',unit='s',time_basis='cpu')])
    return resources


def passive_search_summary(host, reference, result):
    """One bounded projection of saved passive search facts for Main/Reporter."""
    from tools.research.state import state
    from tools.research.search import design_counts
    query=host.store.artifact(result['search_state'],paths=('problem.query',))['problem']['query']
    structures=[]
    for i,row in enumerate(result['evaluated']):
        conditions={}
        for name,condition in row.get('evidence',{}).get('conditions',{}).items():
            facts=condition.get('facts') or {};diagnosis=facts.get('qualification_diagnosis') or {}
            conditions[name]=dict(analysis=condition.get('analysis'),status=condition.get('status'),score=condition.get('score'),
                constraint_state=facts.get('constraint_state'),baseline_qualification=diagnosis.get('status'),
                failure_layers=diagnosis.get('failure_layers',[]),
                initial_qualification=(diagnosis.get('initial_qualification') or {}).get('status'))
            if query.get('evaluation_mode')=='passive_task_response' and condition.get('analysis'):
                # The immutable child owns full-task failure layers and costs;
                # legacy batch facts retained only a score and validity string.
                child=host.store.artifact(condition['analysis'],paths=('diagnostic_layers','internal_calculations',
                    'structure_research.baseline.reason','structure_research.baseline.task_gap.valid_complete',
                    'structure_research.baseline.task_gap.dominant_constraints'))
                baseline=child.get('structure_research',{}).get('baseline',{});layers=child.get('diagnostic_layers') or {}
                initial=layers.get('geometry',{}).get('facts',{}).get('initial_qualification') or {}
                failed=[t for t in (initial.get('checks') or {}).get('tendons',[]) if t.get('status')=='failed']
                conditions[name]['finite_time_response']=dict(reason=baseline.get('reason'),
                    valid_complete=(baseline.get('task_gap') or {}).get('valid_complete'),
                    dominant_constraints=(baseline.get('task_gap') or {}).get('dominant_constraints',[]),
                    layers={k:dict(status=v['status'],failure_reasons=v.get('failure_reasons',[])) for k,v in layers.items()},
                    initial_tendon_failure_count=len(failed) if initial else None,
                    initial_tendon_failure_examples=[{k:t[k] for k in ('tendon_id','path_length_m','payout_length_m','signed_residual_m','status') if k in t} for t in failed[:3]],
                    recorded_costs=child.get('internal_calculations',[]),
                    diagnosis_query=dict(reference=condition['analysis'],view='full',pointer='/diagnostic_layers'))
        structures.append(dict(candidate=row.get('evidence',{}).get('candidate'),
            segment_count=row['parameters']['segment_count'],tendon_count=row['parameters']['tendon_count'],
            changed_coordinates=(row.get('lineage') or {}).get('variables_or_topology_changed',[]),
            status=row.get('computation_status'),scores=row.get('proxy_values'),conditions=conditions,
            construction=row.get('construction'),
            source=dict(reference=reference,pointer='/result/evaluated/'+str(i))))
    best=result.get('best_passive_candidate') or {}
    return dict(status=result['status'],method=query['method'],plan=result.get('requesting_plan'),
        problem=result['physical_problem'],score_semantics=result['score_semantics'],
        termination_reason=result['termination_reason'],actual_counts={**result['resource_use'],**design_counts(result['evaluated'])},
        recorded_counts_query=dict(reference=reference,view='full',pointer='/result/resource_use'),
        best_passive_candidate=(best.get('evidence') or {}).get('candidate'),best_scores=best.get('proxy_values'),
        search_scope={k:query[k] for k in ('variable_groups','segment_counts','tendon_counts','span_strategies','bounds',
            'diagnostic_load_conditions','objective','evaluation_mode','max_proposals','max_evaluations') if k in query},
        structures=structures,unsearched_parameter_groups=[g for g in state(host)['spec']['family_search']['variable_groups'] if g not in query['variable_groups']],
        cost=dict(attributed_numerical_s=sum(r.get('mathematical_numerical_s',0.) for r in result['evaluated']),
            scope='Recorded child receipts only; parent and child elapsed times overlap.'),
        task_acceptance='unmeasured',scientific_citation_eligible=False,
        results_query=dict(reference=reference,view='full',pointer='/result'),
        source=dict(reference=reference,pointer='/result'),
        scope='Finite passive screening under the recorded evaluation model. Rejected constructions are not numerically evaluated designs; saved legacy counts remain at recorded_counts_query. Scores do not establish independent task acceptance, global feasibility or optimum. Only recorded coordinates and conditions were explored.')


def result_card(host, reference):
    """L1 ResultCard from one trusted Store result; no formal read markers.

    The ordinary read boundary still enforces protected-result admission. Only
    saved candidate/measurement metadata used by existing projections is read.
    Copies isolate nested dicts from the underlying saved artifacts.
    """
    reference=deepcopy(plain(reference))
    # The evidence boundary already returns an isolated Store copy.
    value=read_evidence(host, dict(reference=reference), record_read=False)
    if not isinstance(value,dict):
        raise ValueError('RESULT_CARD_REQUIRES_RESULT_OBJECT')
    control=value.get('control_schedule_reference',value.get('source_reference'))
    if control:
        trajectory=host.store.artifact(control).get('trajectory') or {}
        for key in ('model_identity','design_identity'):
            if value.get(key) is None and trajectory.get(key):value[key]=trajectory[key]
    evidence=summarize_evidence(value,reference)
    binding=(value.get('scoped_claim') or {}).get('binding') or value.get('binding') or {}
    identity=ResultIdentity(result=_location(reference),
        study=value.get('owning_study') or value.get('study'),
        task_identity=evidence['task_identity'], candidate=value.get('candidate',value.get('design_candidate',binding.get('candidate'))),
        control_source=value.get('control_schedule_reference',value.get('source_reference',value.get('source'))),
        operation=value.get('operation'), model_identity=evidence['model_identity'] or value.get('numerical_failure',{}).get('model_identity'),
        design_identity=evidence['design_identity'],
        evaluation_profile_identity=value.get('profile_identity'),evaluation_identity=value.get('execution_id'))
    summary=compact_evidence(value,reference,facts_only=True)['summary']
    native_search=native_search_summary(value,reference)
    if native_search:summary['control_search']=native_search
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
        if value.get('structure_research'):
            from schemas.research_reporting import MathematicalQuantity
            raw=value['structure_research'];quantities=[]
            for i,row in enumerate(raw['records']):
                observation=row['observation']
                if isinstance(observation['value'],(int,float)):
                    quantities.append(MathematicalQuantity(name='mechanism_probe_'+str(i),value=observation['value'],
                        unit=observation['unit'],status='unverified_estimate',control_reoptimization='fixed_control',
                        source=_location(reference,f'/structure_research/records/{i}/observation/value')))
            direction=raw.get('structure_direction')
            if direction:
                changes=direction.get('parameter_changes') or [dict(parameter_path=direction['parameter_path'],unit=direction['parameter_unit'],delta=direction['delta'])]
                for i,change in enumerate(changes):
                    quantities.append(MathematicalQuantity(name='suggested_parameter_delta/'+change['parameter_path'],value=change['delta'],
                        unit=change['unit'],status='unverified_estimate',structural_parameters=[change['parameter_path']],control_reoptimization='fixed_control',
                        source=_location(reference,'/structure_research/structure_direction/'+('parameter_changes/'+str(i)+'/delta' if direction.get('parameter_changes') else 'delta'))))
            mathematics=mathematics.model_copy(update=dict(problem_definition=_location(reference,'/structure_research'),quantities=quantities))
            details.append(_location(reference,'/structure_research'))
        if value.get('native_analysis'):
            from schemas.research_reporting import MathematicalQuantity
            if value['operation'] in ('mujoco_direct_control_v1','mujoco_nonlinear_task_capability_v1'):
                fields=dict(terminal_position=('terminal_error_m','terminal_position_error_m'),
                    holding_position=('holding_max_error_m','holding_max_position_error_m'),
                    holding_speed=('holding_max_speed_m_s','holding_max_speed_m_s'))
                for label,measure in summary['native_analysis']['comparison'].items():
                    worst=measure['worst_constraint'];key,field=fields[worst['kind']]
                    i,c=next((i,c) for i,c in enumerate(value['task_analysis']['constraints']) if c['constraint_id']==key)
                    path='/native_dynamics/optimization/'+('candidates/0' if label=='baseline' else 'best')+'/measure/'+field
                    worst.update(constraint_id=key,value=measure[field],limit=c['radius'],unit=c['signal']['units'],
                        scope='model_sample',source=plain(_location(reference,path)),
                        threshold_source=plain(_location(reference,f'/task_analysis/constraints/{i}/radius')))
            mathematics=mathematics.model_copy(update=dict(
                problem_definition=_location(reference,'/native_analysis/basis'),
                quantities=[MathematicalQuantity(name=q['name'],value=q['value'],unit=q['unit'],
                    status='unverified_estimate',control_reoptimization='required' if value['operation'] in ('mujoco_direct_control_v1','mujoco_nonlinear_task_capability_v1') else 'fixed_control',
                    source=_location(reference,q['source_pointer'])) for q in summary['native_analysis']['quantities']]))
            details.append(_location(reference,'/native_dynamics'))
            if value.get('control_schedule_reference'):details.append(_location(value['control_schedule_reference']))
        if value.get('operation') == 'task_capability' and (value.get('trajectory', {}).get('problem_definition') or value.get('trajectory',{}).get('method_version')):
            from tools.research.capability import populate_mathematics
            mathematics=populate_mathematics(mathematics,value['trajectory'],reference)
            if value['trajectory'].get('structural_comparison'):
                details.append(_location(value['trajectory']['structural_comparison']['baseline_result']))
        if value.get('nonlinear_response'):
            from schemas.research_reporting import MathematicalQuantity
            t=value['nonlinear_response'];quantities=[]
            for i,d in enumerate(t.get('directions',[t])):
                prefix='/nonlinear_response'+('/directions/'+str(i) if 'directions' in t else '')
                for key in ('fixed_control','reoptimized'):
                    if d.get(key):quantities.append(MathematicalQuantity(name=d.get('direction_id','parameter')+'/'+key+'/central',
                        value=d[key]['central'],unit=d.get('secant_unit'),status='unverified_estimate',
                        control_reoptimization='required' if key=='reoptimized' else 'fixed_control',
                        source=_location(reference,prefix+'/'+key+'/central')))
            mathematics=mathematics.model_copy(update=dict(problem_definition=_location(reference,'/nonlinear_response'),quantities=quantities))
            details.extend([_location(reference,'/nonlinear_response'),_location(reference,'/nonlinear_response/referenced_t1_costs')])
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
        replay_metrics=_replay_metrics(value,reference)
        if replay_metrics:
            names={m.name for m in replay_metrics}
            metrics=[m for m in metrics if m.name not in names]+replay_metrics
            violations=list(dict.fromkeys([*violations,*[m.name for m in replay_metrics if m.passed is False]]))
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
            raw_ref=value['raw_reference'];raw=host.store.artifact(raw_ref,paths=('model_identity','mathematical_model_identity',
                'physical_backend','scene_identity','tendon_order','physics_timestep_s','physics_steps'))
            details.append(_location(raw_ref))
            context.extend(RecordedField(name=key,value=raw[key],source=_location(raw_ref,'/'+key))
                for key in ('model_identity','mathematical_model_identity','physical_backend','scene_identity',
                    'tendon_order','physics_timestep_s') if key in raw)
            # Physics steps and model identities may live only in the saved measurement.
            if 'physics_steps' in raw and (value.get('actual_resource_consumption') or {}).get('physics_steps') is None:
                resources.append(ResourceUse(name='physics_steps',amount=raw['physics_steps'],
                    unit='steps',source=_location(raw_ref,'/physics_steps')))
    elif 'best' in value and 'candidates' in value:
        search=_search(value,reference)
        # compact_evidence already owns search summaries. Response matrices stay in Store.
        summary={k:v for k,v in summary.items() if k not in ('local_responses',)}
        details.extend([_location(reference,'/candidates'),_location(reference,'/starts')])
    elif value.get('result',{}).get('physical_problem'):
        result=value['result']
        summary['passive_family_search']=passive_search_summary(host,reference,result)
        details.append(_location(reference,'/result'))
    construction=recorded_static_summary(value,reference)
    if construction:summary['recorded_static_construction']=construction
    summary['scientific_interpretation']=SCIENTIFIC_INTERPRETATION
    diagnosis=task_diagnosis(value,reference)
    if diagnosis:
        summary['task_diagnosis']=diagnosis
        details.append(EvidenceLocation.model_validate(diagnosis['source']))
    return ResultCard(identity=identity,evidence_summary=evidence,
        recorded_context=context,metrics=metrics,main_violations=violations,critical_observations=critical,
        deterministic_summary=summary,mathematics=mathematics,control_search=search,
        resources=resources,detail_sources=details)


def scoped_feedback(host, references):
    """Expose only supplied, versioned feedback packets; preserve their provenance."""
    packets = []
    for reference in references:
        value = host.store.artifact(reference)
        if isinstance(value, dict) and value.get("schema") in (
                "sorosim_s55_s5t_feedback_v1", "sorosim_s56_s5t2_feedback_v1", "sorosim_s57_prediction_feedback_v1"):
            packets.append(dict(reference=reference, evidence=value))
    return packets
