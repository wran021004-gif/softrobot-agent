"""Thin native mechanism orchestration inside the existing analysis worker.

No Store, candidate registration, optimizer, evaluator or budget owner here.
"""
import time
import numpy as np
from tools.platform_store import plain
from extensions.tendon_family.family_space import resolved_request
from extensions.math_analysis.mechanism_registry import observe
from extensions.math_analysis.differentiation_router import differentiate, stencil

METHOD='mechanism_structure_v1'
EVALUATIONS=dict(inspect=1,differentiate=5,optimize=6,compare=2)


def parameters(spec, candidate):
    if not spec.get('family_space') or not candidate.get('generation_version'):return []
    from tools.research.optimal_capability import family_analysis_parameters
    return family_analysis_parameters(spec,candidate)


def prepare_context(spec, candidate, study, comparisons):
    """Read-only legality/binding checks before the original reservation."""
    rows=parameters(spec,candidate);row=next((r for r in rows if r['parameter_id']==study.parameter_path),None)
    if study.operation in ('differentiate','optimize'):
        if spec.get('fixed_structure_reference'):raise ValueError('FROZEN_FIXED_STRUCTURE_FORBIDS_STRUCTURAL_PROBES')
        if not row:raise ValueError('REGISTERED_STRUCTURAL_PARAMETER_REQUIRED')
        if row['data_type'] in ('integer','enum','routing_topology','route_points'):
            raise ValueError('DISCRETE_PARAMETER_REQUIRES_COMPARISON_NOT_DIFFERENTIATION')
        # M1 intentionally covers one physically effective length group.
        if row['category']!='segment' or not row['parameter_id'].endswith('.length_m'):
            raise ValueError('M1_SUPPORTS_SEGMENT_LENGTH_ONLY_OTHER_GROUPS_DISCOVERABLE')
        if not row['study_authorized']:raise ValueError('ORIGINAL_FROZEN_PARAMETER_AUTHORIZATION_REQUIRED')
        stencil(row)
        if study.target.reduction=='identity' and study.target.quantity!='mass_balance_residual':
            raise ValueError('SCALAR_MECHANISM_REDUCTION_REQUIRED_FOR_DIRECTION')
    if EVALUATIONS[study.operation]>study.max_evaluations:raise ValueError('MECHANISM_QUESTION_BUDGET_CANNOT_FIT')
    if (study.operation=='compare') != bool(comparisons):raise ValueError('COMPARE_REQUIRES_ONE_OWNED_COMPARISON_CANDIDATE_ONLY')
    for ref,c in comparisons:
        if c['task_identity']!=candidate['task_identity']:raise ValueError('MECHANISM_COMPARISON_REQUIRES_SAME_FROZEN_TASK')
    return dict(space=spec.get('family_space'),parameters=candidate['parameters'],parameter=row,
        comparisons=[dict(reference=ref,configuration=c['configuration']) for ref,c in comparisons])


def discovery(spec, candidate, reference, *, latest_direction=None):
    rows=parameters(spec,candidate)
    lengths=[r for r in rows if r['category']=='segment' and r['parameter_id'].endswith('.length_m') and r['continuous_perturbation'] and r['study_authorized']]
    return dict(version='structure_mechanism_discovery_v1',candidate=reference,
        operations=list(EVALUATIONS),mechanism_categories=['geometry','active_drive','inertia','instantaneous_braking'],
        effective_parameter_groups=['segment_lengths'] if lengths else [],
        evidenced_direction=bool(latest_direction),direction_query=latest_direction,
        details_query=dict(reference=reference,view='mathematical_capabilities',pointer='/structure_research'),
        task_scope='Local mechanism only; full task improvement unmeasured.')


def calculate(configuration, binding, query, point, context, *, checkpoint=None):
    from extensions.tendon_family.mujoco_analysis import NativeModel
    from tools.research.design import family_configuration, set_parameter
    from tools.platform_tasks import compile_input
    from tools.platform_registry import registry
    started=time.perf_counter();study=query.mechanism_study;records=[];models=[]
    attempts=0;baseline_point=None

    def evaluate(value=None, *, comparison=None):
        nonlocal attempts,baseline_point
        if attempts>=study.max_evaluations:raise ValueError('MECHANISM_LOCAL_EVALUATION_CAP')
        index=attempts;attempts+=1
        if checkpoint:checkpoint('mechanism_attempt_'+str(index),dict(index=index,value=value))
        cfg=configuration;params=None
        if value is not None:
            params=resolved_request(context['space'],context['parameters'])
            set_parameter(params,study.parameter_path,value)
            cfg,_,_=family_configuration(configuration,context['space'],params,configuration['run_id'])
            compile_input(cfg,registry())
        elif comparison is not None:cfg=comparison['configuration']
        native=NativeModel(cfg);models.append(native)
        if baseline_point is None:
            baseline_point,data=native.reconstruct(point) if point.get('native_replay') else (point,native.restore(point))
            # Same history reset in baseline and every structure, including saved states.
            data=native.restore(baseline_point,comparable=True)
        elif study.point_semantics=='same_generalized_coordinates':
            data=native.restore(baseline_point,comparable=True)
        else:
            own={**baseline_point,'dof_order':native.order,'tendon_order':native.tendons,
                'qpos_rad':native.scene['qpos_rad'],'qvel_rad_s':native.scene['qvel_rad_s'],'actual_time_s':0.}
            data=native.restore(own,comparable=True)
        u=point['u'] if query.native.tensions_n is None else query.native.tensions_n
        mechanics=native.mechanics(data,u);observation=observe(mechanics,study.target)
        if observation['status']!='computed':raise ValueError(observation['reason'])
        record=dict(record_index=len(records),coordinate=value,parameters=params,configuration=cfg,observation=observation,mechanics=mechanics,
            state=native.checkpoint(data),physics_identity=native.physics['identity'],
            source_comparison=comparison['reference'] if comparison else None)
        records.append(record)
        if checkpoint:checkpoint('mechanism_return_'+str(index),dict(index=index,cost=native.cost,observation=observation))
        return record

    result=dict(status='computed',operation=METHOD,binding=binding,protocol=plain(query.protocol),
        task_acceptance='unmeasured',proxy_values={},operating_point=dict(name=query.operating_point,
            actual_time_s=point['actual_time_s'],semantics=study.point_semantics,
            control_treatment='fixed absolute tensions and reset solver history in every model'))
    evidence=dict(operation=study.operation,target=plain(study.target),records=records,
        model_source='NativeModel.mechanics',point_semantics=study.point_semantics,
        scope='Same generalized coordinates do not mean equal Cartesian pose, equilibrium, energy or preserved physical state.',
        unsupported_conclusions=['full task improvement','task success','strict derivative','structural descent certificate',
            'passive constraint nullspace','hardware performance'])
    try:
        base=evaluate();evidence['baseline']=base['observation']
        if study.operation=='compare':
            other=evaluate(comparison=context['comparisons'][0])
            evidence['comparison']=dict(baseline=base['observation']['value'],other=other['observation']['value'],
                delta=(np.asarray(other['observation']['value'])-np.asarray(base['observation']['value'])).tolist())
        elif study.operation in ('differentiate','optimize'):
            response=differentiate(context['parameter'],base,evaluate,goal=study.target.goal)
            evidence['sensitivity']=response
            selected=records[response['selected_record_index']] if response['selected_record_index'] is not None else None
            if selected and study.operation=='optimize':
                checked=evaluate(context['parameter']['current_value']+response['suggested_delta'])
                repeat=np.isclose(checked['observation']['value'],selected['observation']['value'],rtol=1e-8,atol=1e-12)
                evidence['local_proposal_recheck']=dict(passed=bool(repeat),record_index=checked['record_index'],
                    scope='Fresh native mechanism recomputation, not structural optimization or complete task evaluation.')
                selected=checked if repeat else None
            if selected:
                delta=response['suggested_delta'];row=context['parameter']
                evidence['structure_direction']=dict(version='structure_direction_v1',candidate=binding['candidate'],
                    parameter_path=row['parameter_id'],parameter_unit=row['unit'],baseline_parameter=row['current_value'],
                    delta=delta,suggested_value=row['current_value']+delta,
                    baseline_metric=base['observation'],perturbed_metric=selected['observation'],
                    numerical_consistency=response['consistency'],
                    tradeoffs='Other frozen task constraints, input requirements and Cartesian pose may worsen; none were evaluated.',
                    model_scope='Contact-free native ideal tension; instantaneous declared state only.',
                    point_semantics=study.point_semantics,full_task_improvement_verified=False,
                    formal_candidate_created=False,proposal_only=True,
                    next_action='Main may use research_plan(generate/propose); original legality, budget and independent evaluation remain required.',
                    raw_evidence_pointer='/structure_research/records')
    except ValueError as exc:
        result.update(status='not_applicable',reason=str(exc))
        evidence['failure']=dict(reason=str(exc),attempted_evaluations=attempts)
    cost={key:sum(m.cost[key] for m in models) for key in (models[0].cost if models else [])}
    cost.update(evaluation_attempts=attempts,kernel_wall_s=time.perf_counter()-started)
    evidence['cost']=cost
    if evidence.get('structure_direction'):evidence['structure_direction']['actual_cost']=cost
    result.update(structure_research=evidence,model_identity=records[0]['physics_identity'] if records else None,
        internal_calculations=[dict(purpose='native_mechanism_structure',**cost)])
    return result


def summary(value, reference):
    """Small deterministic facts with exact sources; Reporter cannot replace them."""
    raw=value['structure_research'];direction=raw.get('structure_direction')
    baseline=raw.get('baseline',{}).get('value')
    return dict(operation=raw['operation'],target=raw['target'],baseline=baseline if np.asarray(baseline).ndim==0 else None,
        direction_status=raw.get('sensitivity',{}).get('direction_status','not_requested'),
        structure_direction={k:direction[k] for k in ('parameter_path','parameter_unit','delta','suggested_value',
            'full_task_improvement_verified','formal_candidate_created','proposal_only')} if direction else None,
        source=dict(reference=reference,pointer='/structure_research'),
        direction_source=dict(reference=reference,pointer='/structure_research/structure_direction') if direction else None,
        cost=raw['cost'],task_acceptance='unmeasured',unsupported_conclusions=raw['unsupported_conclusions'])
