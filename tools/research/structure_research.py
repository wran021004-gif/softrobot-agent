"""Bounded structural research in the existing worker; no Store or candidate writes."""
import time
import numpy as np
from tools.platform_store import plain
from extensions.tendon_family.family_space import resolved_request
from extensions.math_analysis.mechanism_registry import observe
from extensions.math_analysis.differentiation_router import differentiate, stencil, coordinate, physical_value

METHOD='mechanism_structure_v1'
OPERATIONS=('inspect','differentiate','optimize','compare')


def parameters(spec, candidate):
    if not spec.get('family_space') or not candidate.get('generation_version'):return []
    from tools.research.optimal_capability import family_analysis_parameters
    rows=family_analysis_parameters(spec,candidate)
    for row in rows:
        reason=('INPUT_FEASIBLE_SET_CHANGE_REQUIRES_SEPARATE_SEMANTICS' if row.get('input_set_changes') else
            'CONTROLLER_OR_NUMERICAL_PARAMETER_NOT_PHYSICAL_STRUCTURE' if row['category'] in ('controller','discretization') else
            'DISCRETE_PARAMETER_REQUIRES_COMPARISON' if row['data_type']!='number' else
            row['analysis_reason'] if not row['continuous_perturbation'] or not row['effective_in_current_execution'] else
            'ORIGINAL_FROZEN_PARAMETER_AUTHORIZATION_REQUIRED' if not row['study_authorized'] else None)
        row['mechanism_differentiation']=dict(supported=reason is None,reason=reason,
            method='normalized_two_scale_native_finite_difference' if reason is None else None)
    return rows


def group_matches(row, group):
    return (row['category']=='segment' and row['unit']=='m') if group=='segment_lengths' else row['category']==group


def prepare_context(spec, candidate, study, comparisons):
    """Read-only actual-domain/source admission before the existing reservation."""
    rows={r['parameter_id']:r for r in parameters(spec,candidate)};selected=[]
    if study.operation in ('differentiate','optimize'):
        if spec.get('fixed_structure_reference'):raise ValueError('FROZEN_FIXED_STRUCTURE_FORBIDS_STRUCTURAL_PROBES')
        if not 1<=len(study.paths)<=2:raise ValueError('SELECT_ONE_OR_TWO_REGISTERED_PARAMETERS')
        for path in study.paths:
            if path not in rows:raise ValueError('REGISTERED_STRUCTURAL_PARAMETER_REQUIRED: '+path)
            row=rows[path]
            if not row['mechanism_differentiation']['supported']:raise ValueError(row['mechanism_differentiation']['reason'])
            selected.append(row)
        scalar=(study.target.reduction!='identity' or study.target.quantity in
            ('mass_balance_residual','total_mass','body_inertia_trace','directional_tendon_row_residual','motion_decoupling') or
            study.target.quantity=='directional_drive' and study.target.tendon_channel is not None)
        if not scalar:raise ValueError('SCALAR_MECHANISM_REDUCTION_REQUIRED_FOR_DIRECTION')
    if (study.operation=='compare') != bool(comparisons):raise ValueError('COMPARE_REQUIRES_ONE_OWNED_COMPARISON_CANDIDATE_ONLY')
    for ref,c in comparisons:
        if c['task_identity']!=candidate['task_identity']:raise ValueError('MECHANISM_COMPARISON_REQUIRES_SAME_FROZEN_TASK')
    plans=[stencil(row) for row in selected]
    minimum=(1 if study.operation=='inspect' else 2 if study.operation=='compare' else
        1+sum(len(set(p['coordinates'])) for p in plans)+int(len(plans)==2)+int(study.operation=='optimize'))
    if study.max_evaluations<minimum:raise ValueError('MECHANISM_QUESTION_BUDGET_CANNOT_FIT: requires '+str(minimum))
    return dict(space=spec.get('family_space'),parameters=candidate['parameters'],selected_parameters=selected,
        minimum_evaluations=minimum,evaluations=study.max_evaluations if study.operation=='optimize' else minimum,
        comparisons=[dict(reference=ref,configuration=c['configuration']) for ref,c in comparisons])


def discovery(spec, candidate, reference, *, latest_direction=None, formal_candidate_created=False,
              method_detail=None, remaining_evaluations=None, execution_block=None):
    rows=parameters(spec,candidate);detail=method_detail or {}
    minima=[1+len(set(stencil(r)['coordinates'])) for r in rows if r['mechanism_differentiation']['supported']]
    minimum=dict(inspect=1,compare=2,differentiate=min(minima) if minima else None,
        optimize=min(minima)+1 if minima else None)
    unavailable=execution_block or (detail.get('planning_status') if detail.get('planning_status') in
        ('unauthorized','unsupported','insufficient_budget','blocked') else None)
    operations={}
    for operation,count in minimum.items():
        reason=unavailable or ('no_effective_authorized_continuous_parameter' if count is None else
            'insufficient_budget' if remaining_evaluations is not None and remaining_evaluations<count else None)
        ready=bool(detail and not reason)
        operations[operation]=dict(can_prepare=ready,execution_status='blocked' if reason else
            'conditional_on_original_request_admission' if ready else 'not_checked',reason=reason,
            minimum_evaluations=count,inputs_required=True)
    return dict(version='structure_mechanism_discovery_v2',candidate=reference,operations=list(OPERATIONS),
        operation_admission=operations,remaining_evaluations=remaining_evaluations,
        method_admission={k:detail[k] for k in ('planning_status','execution_status','formal_execution_authorized','missing') if k in detail},
        mechanism_categories=['directional_drive','bounded_directional_acceleration','routing_geometry','inertia','stiffness','instantaneous_braking'],
        effective_parameter_groups=sorted({r['category'] for r in rows if r['mechanism_differentiation']['supported']}),
        evidenced_direction=bool(latest_direction),direction_proposed=bool(latest_direction),direction_query=latest_direction,
        formal_candidate_created=formal_candidate_created,
        details_query=dict(reference=reference,view='mathematical_capabilities',pointer='/structure_research'),
        task_scope='Instantaneous mechanism; full task improvement unmeasured. Short responses use the existing M1 methods.')


def matches_direction(spec, baseline, generated, direction):
    """Compare actual resolved generation parameters, not Plan citations or prose."""
    from tools.research.design import set_parameter
    if baseline['task_identity']!=generated['task_identity']:return False
    rows={r['parameter_id']:r for r in parameters(spec,baseline)}
    changes=direction.get('parameter_changes') or [dict(parameter_path=direction.get('parameter_path'),
        suggested_value=direction.get('suggested_value'))]
    expected=resolved_request(spec['family_space'],baseline['parameters'])
    for change in changes:
        path=change['parameter_path'];value=change['suggested_value'];row=rows.get(path)
        if not row or not row['mechanism_differentiation']['supported'] or value is None:return False
        if not row['minimum']<=value<=row['maximum']:return False
        set_parameter(expected,path,value)
    return expected==resolved_request(spec['family_space'],generated['parameters'])


def physical_changes(base, changed):
    """Observe actual compiled coefficients; parameter names alone establish no effect."""
    fields={**base.get('components',{}),**{k:base[k] for k in
        ('mass_matrix_kg_m2','input_force_map_nm_n','tip_jacobian_m_rad','tendon_jacobian_m_rad') if k in base}}
    other={**changed.get('components',{}),**changed};differences={}
    for key,value in fields.items():
        if key not in other:continue
        a=np.asarray(value);b=np.asarray(other[key])
        if a.shape!=b.shape:continue
        delta=float(np.max(abs(a-b))) if a.size else 0.
        if delta>1e-12*max(1.,float(np.max(abs(a))) if a.size else 0.):differences[key]=delta
    return differences


def joint_consistency(rows, responses, baseline, changed):
    """Compare one actual combined perturbation with its local linear prediction."""
    z=[coordinate({**row,'current_value':v})['origin'] for row,v in zip(rows,changed['parameter_values'].values())]
    center=[coordinate(row)['origin'] for row in rows]
    predicted=sum(r['normalized_derivatives'][-1]*(v-origin) for r,v,origin in zip(responses,z,center))
    actual=changed['observation']['value']-baseline['observation']['value']
    relative=abs(actual-predicted)/max(abs(actual),abs(predicted),1e-15)
    passed=all(r['consistency']['passed'] for r in responses) and relative<=.25 and actual*predicted>0
    return dict(record_index=changed['record_index'],actual_change=actual,predicted_change=predicted,
        relative_difference=relative,passed=bool(passed))


class EvaluationLimit(ValueError):
    pass


def calculate(configuration, binding, query, point, context, *, checkpoint=None):
    from extensions.tendon_family.mujoco_analysis import NativeModel
    from tools.research.design import family_configuration, set_parameter
    from tools.platform_tasks import compile_input
    from tools.platform_registry import registry
    from extensions.tendon_family.family_space import parse_build
    started=time.perf_counter();study=query.mechanism_study;records=[];models=[];failures=[];cache={}
    rows=context['selected_parameters'];mappings=[coordinate(row) for row in rows]
    center=np.asarray([m['origin'] for m in mappings]);base_values=[r['current_value'] for r in rows]
    attempts=0;baseline_point=None

    def evaluate(values=None, *, comparison=None):
        nonlocal attempts,baseline_point
        values=base_values if values is None else list(values)
        key=tuple(values) if comparison is None else ('comparison',)
        if key in cache:return cache[key]
        if attempts>=context['evaluations']:raise EvaluationLimit('MECHANISM_LOCAL_EVALUATION_CAP')
        index=attempts;attempts+=1
        if checkpoint:checkpoint('mechanism_attempt_'+str(index),dict(index=index,parameter_values=values))
        cfg=configuration;params=None
        if values!=base_values:
            params=resolved_request(context['space'],context['parameters'])
            for row,value in zip(rows,values):set_parameter(params,row['parameter_id'],float(value))
            cfg,build,_=family_configuration(configuration,context['space'],params,configuration['run_id'])
            params=plain(build.request);compile_input(cfg,registry())
        elif comparison is not None:cfg=comparison['configuration']
        native=NativeModel(cfg);models.append(native)
        if baseline_point is None:
            baseline_point,data=native.reconstruct(point) if point.get('native_replay') else (point,native.restore(point))
            if study.point_semantics!='saved_native_state':
                if study.point_semantics=='fixed_generalized_pose':baseline_point={**baseline_point,'qvel_rad_s':[0.]*len(native.order)}
                data=native.restore(baseline_point,comparable=True)
        elif study.point_semantics=='frozen_task_initial_state':
            own={**baseline_point,'dof_order':native.order,'tendon_order':native.tendons,
                'qpos_rad':native.scene['qpos_rad'],'qvel_rad_s':native.scene['qvel_rad_s'],'actual_time_s':0.}
            data=native.restore(own,comparable=True)
        else:data=native.restore(baseline_point,comparable=True)
        u=point['u'] if query.native.tensions_n is None else query.native.tensions_n
        mechanics=native.mechanics(data,u);observation=observe(mechanics,study.target)
        if observation['status']!='computed':raise ValueError(observation['reason'])
        record=dict(record_index=len(records),parameter_values=dict(zip(study.paths,values)),parameters=params,
            configuration=cfg,observation=observation,mechanics=mechanics,state=native.checkpoint(data),
            physics_identity=native.physics['identity'],source_comparison=comparison['reference'] if comparison else None)
        record['compiled_physical_changes']=physical_changes(records[0]['mechanics'],mechanics) if records else {}
        records.append(record);cache[key]=record
        if checkpoint:checkpoint('mechanism_return_'+str(index),dict(index=index,cost=native.cost,observation=observation))
        return record

    def at_normalized(z):return evaluate([physical_value(m,float(v)) for m,v in zip(mappings,z)])

    result=dict(status='computed',operation=METHOD,binding=binding,protocol=plain(query.protocol),
        task_acceptance='unmeasured',proxy_values={},operating_point=dict(name=query.operating_point,
            actual_time_s=point['actual_time_s'],semantics=study.point_semantics,
            source=point.get('provenance') or point.get('source'),
            control_treatment='Same legal absolute tensions in every model; no control reoptimization.'))
    evidence=dict(operation=study.operation,target=plain(study.target),records=records,
        model_source='NativeModel.mechanics',point_semantics=study.point_semantics,
        scope='Task initial state, fixed generalized pose and saved native state are distinct. Changed structures use named-coordinate transfer/reset, not equal Cartesian state, energy or equilibrium.',
        unsupported_conclusions=['full task improvement','task success','strict derivative','structural descent certificate',
            'passive constraint nullspace','hardware performance'])
    try:
        base=evaluate();evidence['baseline']=base['observation'];selected=None;responses=[]
        if study.operation=='compare':
            other=evaluate(comparison=context['comparisons'][0])
            evidence['comparison']=dict(baseline=base['observation']['value'],other=other['observation']['value'],
                delta=(np.asarray(other['observation']['value'])-np.asarray(base['observation']['value'])).tolist())
        elif study.operation in ('differentiate','optimize'):
            for i,row in enumerate(rows):
                first=len(records)
                def probe(value):
                    values=list(base_values);values[i]=value
                    return evaluate(values)
                response=differentiate(row,base,probe,goal=study.target.goal)
                response.update(parameter_path=row['parameter_id'],parameter_unit=row['unit'],
                    model_effect_observed=any(r['compiled_physical_changes'] for r in records[first:]))
                if not response['model_effect_observed']:
                    response.update(direction_status='unresolved',suggested_delta=None,selected_record_index=None)
                    response['consistency']['passed']=False
                responses.append(response)
            evidence['parameter_sensitivities']=responses
            # Retain the original single-path result layout for existing readers.
            if len(responses)==1:
                evidence['sensitivity']=responses[0]
                idx=responses[0]['selected_record_index'];selected=records[idx] if idx is not None else None
            else:
                values=[base_values[i]+r['suggested_delta'] if r['suggested_delta'] is not None else
                    physical_value(mappings[i],center[i]+stencil(rows[i])['offsets'][-1]) for i,r in enumerate(responses)]
                joint=evaluate(values);check=joint_consistency(rows,responses,base,joint)
                evidence['joint_direction_check']=check
                if check['passed'] and (1 if study.target.goal=='increase' else -1)*check['actual_change']>max(1e-12,abs(base['observation']['value'])*1e-9):selected=joint
            if study.operation=='optimize':
                selected=None
                from scipy.optimize import minimize
                preference=1 if study.target.goal=='increase' else -1
                bounds=[(max(0.,z-study.local_radius_fraction),min(1.,z+study.local_radius_fraction)) for z in center]
                def objective(z):
                    try:return -preference*float(at_normalized(z)['observation']['value'])
                    except EvaluationLimit:raise
                    except ValueError as exc:
                        failures.append(dict(normalized_parameters=list(map(float,z)),reason=str(exc)));return float('inf')
                remaining=context['evaluations']-attempts
                try:
                    solved=minimize(objective,center,method='Powell',bounds=bounds,
                        options=dict(maxfev=max(1,remaining),maxiter=16,xtol=1e-4,ftol=1e-8))
                    evidence['local_search']=dict(method='scipy.optimize.minimize/Powell',bounds_normalized=bounds,
                        function_calls=int(solved.nfev),status=int(solved.status),message=str(solved.message),
                        success=bool(solved.success),scope='Bounded local best-found mechanism search; no optimum or task certificate.')
                except EvaluationLimit:
                    evidence['local_search']=dict(method='scipy.optimize.minimize/Powell',status='evaluation_cap',bounds_normalized=bounds)
                eligible=[]
                for record in records[1:]:
                    values=list(record['parameter_values'].values())
                    z=[coordinate({**row,'current_value':v})['origin'] for row,v in zip(rows,values)]
                    within=all(lo-1e-14<=v<=hi+1e-14 for v,(lo,hi) in zip(z,bounds))
                    if within and record['compiled_physical_changes']:eligible.append(record)
                # Flat or inconsistent derivatives remain unresolved even if a noisy probe ranks first.
                if eligible and all(r['consistency']['passed'] for r in responses):
                    best=max(eligible,key=lambda r:preference*r['observation']['value'])
                    if preference*(best['observation']['value']-base['observation']['value'])>max(1e-12,abs(base['observation']['value'])*1e-9):selected=best
            if selected and len(rows)==2:
                check=joint_consistency(rows,responses,base,selected)
                evidence['selected_joint_direction_check']=check
                if not check['passed']:selected=None
            if selected:
                changes=[]
                for row,value in zip(rows,selected['parameter_values'].values()):
                    if value==row['current_value']:continue
                    changes.append(dict(parameter_path=row['parameter_id'],unit=row['unit'],baseline=row['current_value'],
                        suggested_value=value,delta=value-row['current_value'],bounds=[row['minimum'],row['maximum']]))
                generation=selected['parameters']
                # Uses the same generation contract as the evaluated model; no candidate is saved.
                generation=plain(parse_build(dict(space=context['space'],request=generation)).request)
                direction=dict(version='structure_direction_v2',candidate=binding['candidate'],parameter_changes=changes,
                    baseline_metric=base['observation'],perturbed_metric=selected['observation'],
                    numerical_consistency=[r['consistency'] for r in responses],
                    tradeoffs='All frozen task constraints, finite response and task acceptance remain unmeasured.',
                    model_scope='Contact-free native ideal tension, declared state and absolute input only.',
                    point_semantics=study.point_semantics,full_task_improvement_verified=False,
                    formal_candidate_created=False,proposal_only=True,other_parameters_unchanged=True,
                    generation_handoff=dict(tool='research_plan',action='generate',generation=generation,
                        if_action_not_loaded=dict(tool='research_route',input=dict(tool='research_plan',action='generate')),
                        source_pointer='/structure_research/records/'+str(selected['record_index']),
                        agent_decision_required=True,alternatives=['adopt','reject','inspect_further','change_hypothesis']),
                    next_action='Main reads evidence and independently chooses whether to submit the original generate/propose Plan.',
                    raw_evidence_pointer='/structure_research/records')
                if len(changes)==1:
                    c=changes[0];direction.update(parameter_path=c['parameter_path'],parameter_unit=c['unit'],
                        baseline_parameter=c['baseline'],delta=c['delta'],suggested_value=c['suggested_value'])
                evidence['structure_direction']=direction
            evidence['direction_status']='locally_supported_proposal' if selected else 'unresolved'
    except ValueError as exc:
        result.update(status='not_applicable',reason=str(exc));evidence['failure']=dict(reason=str(exc),attempted_evaluations=attempts)
    cost={key:sum(m.cost[key] for m in models) for key in (models[0].cost if models else [])}
    cost.update(evaluation_attempts=attempts,kernel_wall_s=time.perf_counter()-started)
    evidence.update(cost=cost,invalid_local_probes=failures)
    if evidence.get('structure_direction'):evidence['structure_direction']['actual_cost']=cost
    result.update(structure_research=evidence,model_identity=records[0]['physics_identity'] if records else None,
        internal_calculations=[dict(purpose='native_mechanism_structure',**cost)])
    return result


def summary(value, reference):
    """Read-only projection of immutable evidence, with a source-bound Plan fragment."""
    raw=value['structure_research'];direction=raw.get('structure_direction');baseline=raw.get('baseline',{}).get('value')
    handoff=None
    if direction and direction.get('generation_handoff'):
        handoff=dict(tool='research_plan',action='generate',agent_decision_required=True,
            if_action_not_loaded=dict(tool='research_route',input=dict(tool='research_plan',action='generate')),
            alternatives=direction['generation_handoff']['alternatives'],supporting_evidence=[reference],
            generation_query=dict(reference=reference,pointer='/structure_research/structure_direction/generation_handoff/generation'),
            direction_source=dict(reference=reference,pointer='/structure_research/structure_direction'))
    compact=({k:direction[k] for k in ('parameter_changes','parameter_path','parameter_unit','delta','suggested_value',
        'full_task_improvement_verified','formal_candidate_created','proposal_only','other_parameters_unchanged') if k in direction} if direction else None)
    return dict(operation=raw['operation'],target=raw['target'],baseline=baseline if np.asarray(baseline).ndim==0 else None,
        direction_status=raw.get('direction_status',raw.get('sensitivity',{}).get('direction_status','not_requested')),
        structure_direction=compact,generation_handoff=handoff,
        source=dict(reference=reference,pointer='/structure_research'),
        direction_source=dict(reference=reference,pointer='/structure_research/structure_direction') if direction else None,
        cost=raw['cost'],task_acceptance='unmeasured',unsupported_conclusions=raw['unsupported_conclusions'])
