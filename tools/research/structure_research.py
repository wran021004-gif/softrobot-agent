"""Bounded structural research in the existing worker; no Store or candidate writes."""
import time
from copy import deepcopy
import numpy as np
from tools.platform_store import plain
from extensions.tendon_family.family_space import resolved_request
from extensions.math_analysis.mechanism_registry import observe,PRIMITIVES
from extensions.math_analysis.differentiation_router import differentiate, stencil, coordinate, physical_value, matched_points, interaction_evidence

METHOD='mechanism_structure_v1'
OPERATIONS=('inspect','differentiate','optimize','compare','interact')
SCALAR_DIRECTION_TARGETS=('mass_balance_residual','total_mass','body_inertia_trace',
    'directional_tendon_row_residual','motion_decoupling','finite_time_task_violation')


class MechanismBudgetError(ValueError):
    """Original admission failure with the cost of Main's actual question."""
    def __init__(self, minimum, dependencies, dynamic_cost_bound=None):
        super().__init__('MECHANISM_QUESTION_BUDGET_CANNOT_FIT: requires '+str(minimum))
        self.minimum_evaluations=minimum
        self.cost_dependencies=dependencies
        self.dynamic_cost_bound=dynamic_cost_bound


def parameters(spec, candidate, local_bounds=None):
    if not spec.get('family_space') or not candidate.get('generation_version'):return []
    from tools.research.optimal_capability import family_analysis_parameters
    rows=family_analysis_parameters(spec,candidate)
    local_bounds=local_bounds or {}
    known={r['parameter_id'] for r in rows if '*' not in r['parameter_id']}
    if set(local_bounds)-known:raise ValueError('LOCAL_BOUNDS_REQUIRE_REGISTERED_PARAMETER')
    for row in rows:
        path=row['parameter_id']
        open_domain=(row['data_type']=='number' and row['effective_in_current_execution'] and
            row['analysis_reason'].startswith('Open physical domain;'))
        row['local_domain_required']=open_domain
        if open_domain:
            row['analysis_status']='conditional'
            if (row['study_authorized'] and 'analysis' in spec.get('capabilities',[]) and
                    spec.get('mathematical_methods',{}).get(METHOD)):
                row['applicable_mathematical_methods'].append(METHOD)
        if path in local_bounds:
            lo,hi=local_bounds[path]
            if (row['data_type']!='number' or not row['effective_in_current_execution'] or
                    not np.isfinite([lo,hi]).all() or not lo<hi or
                    row['minimum'] is not None and (lo<row['minimum'] or row.get('minimum_exclusive') and lo==row['minimum']) or
                    row['maximum'] is not None and hi>row['maximum'] or
                    row['current_value'] is None or not lo<=row['current_value']<=hi):
                raise ValueError('LOCAL_INTERVAL_MUST_CONTAIN_CURRENT_VALUE_WITHIN_PHYSICAL_DOMAIN: '+path)
            row['physical_domain']={k:row[k] for k in ('minimum','maximum','domain_source')}
            row.update(minimum=lo,maximum=hi,local_domain_required=False)
            if open_domain:
                row.update(continuous_perturbation=True,analysis_status='conditional',
                    analysis_reason='Finite request-local interval; original physical domain and rebuild qualification retained.')
        method_reason=('INPUT_FEASIBLE_SET_CHANGE_REQUIRES_SEPARATE_SEMANTICS' if row.get('input_set_changes') else
            'CONTROLLER_OR_NUMERICAL_PARAMETER_NOT_PHYSICAL_STRUCTURE' if row['category'] in ('controller','discretization') else
            'DISCRETE_PARAMETER_REQUIRES_COMPARISON' if row['data_type']!='number' else
            row['analysis_reason'] if not row['continuous_perturbation'] or not row['effective_in_current_execution'] else None)
        reason=method_reason or ('ORIGINAL_FROZEN_PARAMETER_AUTHORIZATION_REQUIRED' if not row['study_authorized'] else None)
        row['mechanism_differentiation']=dict(supported=reason is None,reason=reason,
            method_supported=method_reason is None or open_domain,study_authorized=row['study_authorized'],working_point_admission='not_checked',
            method='normalized_two_scale_native_finite_difference' if reason is None else None)
    return rows


def group_matches(row, group):
    group={'tendon_routing':'routing','material':'material_geometry','payout':'assembly',
        'cross_section':'geometry'}.get(group,group)
    return (row['category']=='segment' and row['unit']=='m') if group=='segment_lengths' else row['category']==group


def select_group_parameters(spec, candidate, group):
    """Program-owned bounded representatives; unexamined coordinates remain explicit."""
    rows=[r for r in parameters(spec,candidate) if r['mechanism_differentiation']['supported'] and group_matches(r,group)]
    # First representative of each physical field, avoiding duplicate stations.
    chosen=[];fields=set()
    for row in rows:
        field=row['parameter_id'].split('.')[-1]
        if field in fields:continue
        fields.add(field);chosen.append(row['parameter_id'])
        if len(chosen)==2:break
    return chosen


def dynamic_protocol(configuration):
    """Compare task/model/fidelity and initialization treatment across structures."""
    task=deepcopy(configuration['task']);initial=task['initializer']['parameters']['data']
    if all(field in initial and all(value==0 for value in initial[field].values()) for field in ('qpos_rad','qvel_rad_s')):
        task['initializer']['parameters']['data']=dict(initial, qpos_rad='all_candidate_dofs_zero',qvel_rad_s='all_candidate_dofs_zero')
    policy={k:deepcopy(configuration['policy'].get(k)) for k in ('backend','controller','dynamics_model','discretization')}
    cells=policy['discretization']['data']['cells']
    if len(set(cells.values()))==1:policy['discretization']['data']['cells']=dict(uniform_cells_per_segment=next(iter(cells.values())))
    return dict(task=task,policy=policy,seed=configuration.get('seed'),
        robot={k:v for k,v in configuration['robot'].items() if k!='structure'})


def dynamic_cost(configuration, evaluations, paired=False,profile=None):
    """Same frozen episode/time-grid bound for discovery, compile and reservation."""
    task=configuration['task'];arms=2 if paired else 1
    episodes=len(task['goal']['data']['load_conditions'])
    duration=episodes*task['timing']['duration_s']
    if profile:
        from schemas.platform import TaskDefinition
        from extensions.reference.passive_program import execution_scope
        scope=execution_scope(TaskDefinition.model_validate(task),plain(profile))
        episodes=len(scope['load_conditions']);duration=sum(scope['end_s'].values())
    if task['goal']['data'].get('execution_protocol')=='phs2d_original_v1':
        duration-=(episodes-1)*next(iter(task['goal']['data']['programs'].values()))[0]['end_s']
    return dict(model_builds=arms*evaluations,episodes=arms*evaluations*episodes,
        physics_steps=arms*evaluations*round(duration/task['timing']['timestep_s']))


def finite_time_discovery(configuration):
    from tools.research_tasks import task_adapter
    cap=task_adapter(configuration).physical_capabilities()
    if not cap['evaluation']['finite_time_structure_response']:return dict(status='not_applicable')
    task=configuration['task'];goal=task['goal']['data']
    paired=bool(task['evaluator']['parameters']['data'].get('mechanism'))
    tendons=list(configuration['robot']['structure']['data'].get('fixed_payout_lengths_m',{}))
    legal=goal.get('allowed_ablation')=='disable_selected_passive_limits' and bool(tendons)
    return dict(status='conditional_on_request_admission',
        effect_semantics='finite_time_task_response',target='finite_time_task_violation',
        operations=list(OPERATIONS),operating_point='frozen_task_initial_state',load_condition='all_frozen_conditions',
        required_inputs=['operation','target','parameter_paths for differentiate/optimize',
            'comparison_candidates for compare'],
        paired_required=False,final_mechanism_requires_pair=paired,actions=['baseline_response','paired_mechanism'],legal_intervention_tendons=tendons if legal else [],
        intervention_rule='Baseline response needs no intervention. For paired_mechanism, Main selects exact passive limits; both arms use the same selected execution scope and matched common states. Only qualified complete pairs support formal mechanism conclusions.',
        per_evaluation_cost=dynamic_cost(configuration,1,False),
        initialization_dependency=('Before integration, repeat the frozen unloaded hard-equilibrium solve, native scene and static solver used by unloaded qualification inspect. Each direction follows its frozen reset and continuity semantics. Finite-time response cannot bypass initialization failure. A static precheck is optional and grants no dynamic acceptance.'
            if goal.get('execution_protocol') in ('phs2d_original_v1','hard_equilibrium_continuous_v1') else 'Independent execution uses the frozen task initializer.'),
        evaluation_cap='Optional explicit maximum; omitted question/diagnose cap uses the legal minimum. An explicit low cap is rejected without execution.',
        cost_rule='Multiply by actual baseline, two-scale stencil, joint check and requested search cap. Original Worker charges actual model/episode/step counts; independent Replay costs extra.',
        execution_profile='Optional exploration: select frozen directions, continuous stage prefix, observation grid, routing, recording and declared fidelity. final_acceptance retains complete frozen scope.',
        evidence_scope='Measured response and qualification are separate; exploration, baseline objectives and static proxies grant no independent acceptance.')


def observed_task_improvement(records, rows=(), bounds=None):
    """Reproject recorded full-task facts; derivative quality grants no eligibility."""
    from tools.research_tasks import constraint_gap
    gaps=[constraint_gap(r['observation']['task_gap']['constraints'],
        valid_complete=r['observation']['status']=='computed' and r['observation']['task_gap']['valid_complete']) for r in records]
    eligible=[]
    for record,gap in zip(records,gaps):
        if not gap['comparable'] or dynamic_protocol(record['configuration'])!=dynamic_protocol(records[0]['configuration']):continue
        if record is not records[0]:
            if not record['compiled_physical_changes'] or record['physics_identity']==records[0]['physics_identity']:continue
            if rows:
                values=[record['parameter_values'].get(row['parameter_id']) for row in rows]
                if any(v is None or not np.isfinite(v) or not row['minimum']<=v<=row['maximum'] for row,v in zip(rows,values)):continue
                z=[coordinate({**row,'current_value':v})['origin'] for row,v in zip(rows,values)]
                if bounds and not all(lo-1e-14<=v<=hi+1e-14 for v,(lo,hi) in zip(z,bounds)):continue
        eligible.append(record['record_index'])
    best=min(eligible,key=lambda i:gaps[i]['signed_task_gap']) if eligible else None
    base=gaps[0] if gaps else None
    comparable=base is not None and base['comparable'] and best is not None
    delta=base['signed_task_gap']-gaps[best]['signed_task_gap'] if comparable else None
    floor=max(1e-12,abs(base['signed_task_gap'])*1e-9) if comparable else None
    improved=comparable and best!=0 and delta>floor
    return dict(candidate_improvement_status=('observed_baseline_response_improvement' if records[0]['observation']['task_gap'].get('scope')=='baseline_response' else 'observed_full_task_improvement') if improved else 'not_observed' if comparable else 'not_comparable',
        best_valid_record_index=best,improved_record_index=best if improved else None,
        observed_reduction=delta,resolution_floor=floor,gaps=gaps,
        scope='Best recorded complete task objective under the same frozen protocol; no strict descent or global optimum.')


def prepare_context(spec, candidate, study, comparisons, *, minimum_budget=False):
    """Read-only actual-domain/source admission before the existing reservation."""
    from tools.research_tasks import task_adapter
    capabilities=task_adapter(candidate['configuration']).physical_capabilities()
    if capabilities['status']=='unsupported':raise ValueError('UNSUPPORTED_PHYSICAL_CAPABILITIES: '+','.join(capabilities['missing']))
    dynamic=study.effect_semantics=='finite_time_task_response'
    execution_configuration=candidate['configuration'];execution_parameters=candidate['parameters']
    if study.execution_profile:
        from extensions.reference.passive_program import execution_scope
        from tools.research.contracts import fidelity_levels
        from schemas.platform import TaskDefinition
        execution_scope(TaskDefinition.model_validate(execution_configuration['task']),plain(study.execution_profile))
        name=study.execution_profile.fidelity
        if name:
            levels=fidelity_levels(spec['fidelity_policy'])
            if name not in levels:raise ValueError('UNDECLARED_EXECUTION_FIDELITY')
            if study.execution_profile.purpose=='final_acceptance' and levels[name]!=spec['fidelity_policy']['final_evaluation']:raise ValueError('FINAL_FIDELITY_REQUIRED')
            from tools.research.design import fidelity_configuration
            execution_configuration,execution_parameters=fidelity_configuration(spec,candidate,name)
    if study.execution_profile and study.execution_profile.purpose=='final_acceptance':
        if study.execution_checks!='full' or set(execution_configuration['policy']['discretization']['data']['cells'].values())!={spec['fidelity_policy']['final_evaluation']['cells_per_segment']}:raise ValueError('FINAL_ACCEPTANCE_REQUIRES_FROZEN_FIDELITY_AND_CHECKS')
    if study.execution_checks=='screening' and not study.execution_profile:
        if spec.get('research_execution_checks')!={'version':'sparse_route_screening_v1'}:
            raise ValueError('FROZEN_SPARSE_RESEARCH_CHECK_AUTHORIZATION_REQUIRED')
        goal=candidate['configuration']['task']['goal']['data']
        if goal.get('version')!='passive_response_v2' or goal.get('route_check')!='every_physics_step':
            raise ValueError('SCREENING_REQUIRES_PASSIVE_V2_WITH_ORIGINAL_DENSE_ROUTE_CHECKS')
    if study.passive_ablation and not dynamic:raise ValueError('PAIRED_LIMIT_INTERVENTION_REQUIRES_FINITE_TIME_RESPONSE')
    if dynamic:
        if not capabilities['evaluation']['finite_time_structure_response']:raise ValueError('REGISTERED_FINITE_TIME_STRUCTURE_RESPONSE_REQUIRED')
        if study.point_semantics!='frozen_task_initial_state' or study.target.quantity!='finite_time_task_violation':
            raise ValueError('DYNAMIC_TASK_REQUIRES_FROZEN_INITIAL_STATE_AND_COMPLETE_TASK_TARGET')
        if study.load_condition is not None or study.comparison_load_conditions or study.load_aggregation:
            raise ValueError('DYNAMIC_TASK_ALWAYS_REQUIRES_ALL_FROZEN_LOADS')
    problem=candidate['configuration']['task'].get('physical_problem')
    mode=problem['mode'] if problem else 'active_ideal_tension'
    metadata=PRIMITIVES[study.target.quantity]
    if mode not in metadata['physical_modes']:raise ValueError('MECHANISM_PHYSICAL_MODE_MISMATCH')
    if study.operation not in metadata['operations']:raise ValueError('MECHANISM_OPERATION_NOT_IMPLEMENTED: '+metadata['unavailable_operation_reason'])
    if problem and not dynamic:
        if study.point_semantics!='re_equilibrated' or study.load_condition not in [x['name'] for x in problem['loads']]:
            raise ValueError('FROZEN_PASSIVE_LOAD_AND_RE_EQUILIBRATION_REQUIRED')
        if study.target.quantity=='re_equilibrated_position_response' and study.effect_semantics!='re_equilibrated_passive_response':
            raise ValueError('RELATIVE_POSITION_REQUIRES_RE_EQUILIBRATED_EFFECT')
    loads=study.comparison_load_conditions
    if loads or study.load_aggregation:
        if not problem or study.operation!='compare' or comparisons or not loads:
            raise ValueError('LOAD_COMPARISON_REQUIRES_PASSIVE_COMPARE_WITHOUT_COMPARISON_CANDIDATE')
        names=[study.load_condition,*loads]
        if len(set(names))!=len(names) or not set(names)<={x['name'] for x in problem['loads']}:
            raise ValueError('DISTINCT_FROZEN_LOAD_CONDITIONS_REQUIRED')
        if study.load_aggregation and study.target.reduction=='identity' and metadata['shape']:
            raise ValueError('LOAD_AGGREGATION_REQUIRES_SCALAR_REDUCTION')
    if set(study.parameter_bounds)-set(study.paths):raise ValueError('LOCAL_BOUNDS_ONLY_FOR_SELECTED_PARAMETER_PATHS')
    rows={r['parameter_id']:r for r in parameters(spec,candidate,study.parameter_bounds)};selected=[]
    if study.operation in ('differentiate','optimize','interact'):
        if spec.get('fixed_structure_reference'):raise ValueError('FROZEN_FIXED_STRUCTURE_FORBIDS_STRUCTURAL_PROBES')
        if not 1<=len(study.paths)<=2:raise ValueError('SELECT_ONE_OR_TWO_REGISTERED_PARAMETERS')
        for path in study.paths:
            if path not in rows:raise ValueError('REGISTERED_STRUCTURAL_PARAMETER_REQUIRED: '+path)
            row=rows[path]
            if not row['mechanism_differentiation']['supported']:raise ValueError(row['mechanism_differentiation']['reason'])
            selected.append(row)
        scalar=(study.target.reduction!='identity' or study.target.quantity in SCALAR_DIRECTION_TARGETS or
            study.target.quantity=='directional_drive' and study.target.tendon_channel is not None)
        if not scalar:raise ValueError('SCALAR_MECHANISM_REDUCTION_REQUIRED_FOR_DIRECTION')
    if (study.operation=='compare') != bool(comparisons or loads):raise ValueError('COMPARE_REQUIRES_OWNED_CANDIDATE_OR_FROZEN_LOAD_CONDITIONS')
    for ref,c in comparisons:
        if c['task_identity']!=candidate['task_identity']:raise ValueError('MECHANISM_COMPARISON_REQUIRES_SAME_FROZEN_TASK')
        if dynamic and dynamic_protocol(c['configuration'])!=dynamic_protocol(candidate['configuration']):
            raise ValueError('DYNAMIC_COMPARISON_REQUIRES_SAME_FROZEN_MODEL_PROTOCOL')
    plans=[stencil(row) for row in selected]
    minimum=(4 if study.operation=='interact' else 1 if study.operation=='inspect' or loads else 2 if study.operation=='compare' else
        1+sum(len(set(p['coordinates'])) for p in plans)+int(len(plans)==2)+int(study.operation=='optimize'))
    cost_dependencies=dict(operation=study.operation,baseline_evaluations=1,
        parameter_stencil_evaluations={row['parameter_id']:len(set(plan['coordinates'])) for row,plan in zip(selected,plans)},
        joint_check_evaluations=int(len(plans)==2),local_search=study.operation=='optimize',
        rule='Actual legal stencil coordinates depend on selected parameter domains and operating values; two paths add a joint check; optimize adds a trial and uses the requested cap.')
    if study.operation=='interact':
        cost_dependencies=dict(operation='interact',baseline_evaluations=1,matched_contrasts=3,rule='All four matched evaluations require admission before any execution.')
    cost=dynamic_cost(execution_configuration,minimum,bool(study.passive_ablation),study.execution_profile) if dynamic else None
    if not minimum_budget and study.max_evaluations<minimum:
        raise MechanismBudgetError(minimum,cost_dependencies,cost)
    cap=minimum if minimum_budget else study.max_evaluations
    result=dict(space=spec.get('family_space'),parameters=execution_parameters,selected_parameters=selected,execution_configuration=execution_configuration,
        minimum_evaluations=minimum,evaluation_cap=cap,
        evaluations=cap if study.operation=='optimize' else minimum,cost_dependencies=cost_dependencies,
        comparisons=[dict(reference=ref,configuration=fidelity_configuration(spec,c,study.execution_profile.fidelity)[0]
            if study.execution_profile and study.execution_profile.fidelity else c['configuration']) for ref,c in comparisons])
    from extensions.math_analysis.differentiation_router import select_method
    route=select_method(effect_semantics=study.effect_semantics,capabilities=capabilities,
        target=study.target.quantity,operation=study.operation)
    result['parameterized_problem']=dict(version='parameterized_physical_research_v1',
        research_question=dict(operation=study.operation,target=plain(study.target)),
        task_identity=candidate.get('task_identity'),candidate_identity=candidate.get('physical_design_identity'),
        task_source=dict(reference=candidate.get('configuration_reference'),pointer='/task'),
        model=candidate['configuration']['policy']['dynamics_model'],
        parameter_space=dict(source='FamilySpace/parameter_capabilities',selected=selected,
            unselected='Held fixed; this bounded request does not exhaust the parameter group.'),
        physical_problem=problem,observable=dict(id=study.target.quantity,**PRIMITIVES[study.target.quantity]),
        working_point=dict(semantics=study.point_semantics,load_condition=study.load_condition),
        control_treatment='no_active_control' if problem else 'fixed_absolute_tensions',
        fixed_conditions='Same frozen task, model protocol, initial-state treatment, environment and all unselected physical parameters.',
        sensitivity_problem=dict(level='M1' if dynamic else 'M0',target=plain(study.target),
            effect_semantics=study.effect_semantics,parameter_paths=study.paths),
        differentiation_router=route)
    if dynamic:
        result['dynamic_cost_bound']=dynamic_cost(execution_configuration,result['evaluations'],bool(study.passive_ablation),study.execution_profile)
        if study.execution_checks=='screening':
            result['execution_checks']=dict(version='sparse_route_screening_v1',level='screening',
                route_period_s=candidate['configuration']['task']['timing']['sample_period_s'],
                task_acceptance='unmeasured',full_validation_required=True)
    return result


def discovery(spec, candidate, reference, *, latest_direction=None, formal_candidate_created=False,
              method_detail=None, remaining_evaluations=None, execution_block=None):
    rows=parameters(spec,candidate);detail=method_detail or {}
    probes={r['parameter_id']:len(set(stencil(r)['coordinates'])) for r in rows if r['mechanism_differentiation']['supported']}
    minima=[1+n for n in probes.values()]
    problem=candidate['configuration']['task'].get('physical_problem')
    minimum=dict(inspect=1,compare=1 if problem and len(problem['loads'])>1 else 2,differentiate=min(minima) if minima else None,
        optimize=min(minima)+1 if minima else None,interact=4 if len(probes)>=2 else None)
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
    from tools.research.math_capability_catalog import research_semantics
    return dict(version='structure_mechanism_discovery_v2',candidate=reference,operations=list(OPERATIONS),
        research_semantics=research_semantics(),
        **(dict(execution_checks=dict(default='full',screening=dict(operation='inspect',
            effect_semantics='finite_time_task_response',route_sampling='score_grid',
            route_period_s=candidate['configuration']['task']['timing']['sample_period_s'],
            physics_and_qualification='unchanged',task_acceptance='unmeasured',
            full_validation='Use original full checks and independently registered PhysicalReplay before SELECT.')))
            if spec.get('research_execution_checks')=={'version':'sparse_route_screening_v1'} else {}),
        operation_admission=operations,remaining_evaluations=remaining_evaluations,
        evaluation_cost_preview=dict(baseline_evaluations=1,parameter_stencil_evaluations=probes,
            two_parameter_joint_check_evaluations=1,matched_interaction_evaluations=4,optimize_additional_minimum=1,
            rule='differentiate = baseline + selected path probes + one joint check for two paths. optimize adds at least one trial. Request compilation validates the actual method, point, intervention and budgets; finite-time physical cost multiplies this count by per_evaluation_cost.'),
        method_admission={k:detail[k] for k in ('planning_status','execution_status','formal_execution_authorized','missing') if k in detail},
        mechanism_categories=['constraint_geometry','taut_slack_activity','tangent_compliance','re_equilibrated_response'] if candidate['configuration']['task'].get('physical_problem') else
            ['directional_drive','bounded_directional_acceleration','routing_geometry','inertia','stiffness','instantaneous_braking'],
        effective_parameter_groups=sorted({r['category'] for r in rows if r['mechanism_differentiation']['supported']}),
        evidenced_direction=bool(latest_direction),direction_proposed=bool(latest_direction),direction_query=latest_direction,
        formal_candidate_created=formal_candidate_created,
        details_query=dict(reference=reference,view='mathematical_capabilities',pointer='/structure_research'),
        finite_time_response=finite_time_discovery(candidate['configuration']),
        unloaded_qualification=(dict(operation='inspect',target=dict(quantity='constraint_active_set',reduction='identity',goal='increase'),
            load_condition=problem['baseline_load'],operating_point='re_equilibrated',effect_semantics='mechanism_effect',
            cost='One mathematical evaluation; frozen initialization only, zero loading episodes or integration steps.',
            output_facts='Includes position-only initial contact pairs and tendon-length versus payout facts even when the subsequent full forward fails; initial geometry is separate from equilibrium qualification.',
            strategy='Frozen unloaded_static_solver and unloaded_multistart, native task scene and original qualification. Optional diagnostic; Main chooses.') if problem else None),
        task_scope='Fixed-state mechanisms, qualified re-equilibrated passive response and registered full finite-time response have distinct validity; full task improvement unmeasured until actual complete response. Independent task acceptance remains separate.')


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
    if changed['observation']['value'] is None or any(r['normalized_derivatives'][-1] is None for r in responses):
        return dict(record_index=changed['record_index'],passed=False,reason='INELIGIBLE_STENCIL_OR_JOINT_OBSERVATION')
    z=[coordinate({**row,'current_value':v})['origin'] for row,v in zip(rows,changed['parameter_values'].values())]
    center=[coordinate(row)['origin'] for row in rows]
    predicted=sum(r['normalized_derivatives'][-1]*(v-origin) for r,v,origin in zip(responses,z,center))
    actual=changed['observation']['value']-baseline['observation']['value']
    relative=abs(actual-predicted)/max(abs(actual),abs(predicted),1e-15)
    passed=all(r['consistency']['passed'] for r in responses) and relative<=.25 and actual*predicted>0
    return dict(record_index=changed['record_index'],actual_change=actual,predicted_change=predicted,
        relative_difference=relative,passed=bool(passed))


def reusable_execution(store,sources,identity,*,independent_replay=False,matching_baseline=None):
    """Look up immutable Result metadata, loading only an exact matching execution."""
    if independent_replay:return None
    from extensions.tendon_family.passive_execution import baseline_arm
    for reference in reversed(sources):
        metadata=store.artifact(reference,paths=('physical_execution_index','raw_reference'))
        entries=metadata.get('physical_execution_index',[])
        if metadata.get('raw_reference'):
            raw_ref=metadata['raw_reference'];raw_meta=store.artifact(raw_ref,paths=('execution_identity','status'))
            if raw_meta.get('execution_identity')==identity:entries=[dict(identity=identity['identity'],pointer='',reference=raw_ref,directory=None)]
        for entry in entries:
            if entry['identity']!=identity['identity']:continue
            ref=entry.get('reference',reference);pointer=entry['pointer']
            raw=store.artifact(ref,pointers=(pointer,))[pointer]
            if raw.get('paired_ablation',{}).get('baseline_cost'):raw=baseline_arm(raw)
            if raw.get('execution_identity')!=identity or raw.get('status')!='completed':continue
            if not raw.get('episodes') or not all(e.get('complete') for e in raw['episodes']):continue
            if matching_baseline and any(a.get('integration_initial')!=b.get('integration_initial') or a.get('qualified_state')!=b.get('qualified_state')
                    for a,b in zip(matching_baseline['episodes'],raw['episodes'])):continue
            return dict(raw=raw,execution_directory=entry.get('directory'),source=dict(reference=ref,pointer=pointer),
                actual_new_cost=dict(physics_steps=0,model_builds=0,episodes_started=0))
    return None


class EvaluationLimit(ValueError):
    pass


def calculate(configuration, binding, query, point, context, *, checkpoint=None):
    from extensions.tendon_family.mujoco_analysis import NativeModel
    from tools.research.design import family_configuration, set_parameter
    from tools.platform_tasks import compile_input
    from tools.platform_registry import registry
    from extensions.tendon_family.family_space import parse_build
    configuration=context.get('execution_configuration',configuration)
    started=time.perf_counter();study=query.mechanism_study;records=[];models=[];failures=[];cache={}
    rows=context['selected_parameters'];mappings=[coordinate(row) for row in rows]
    center=np.asarray([m['origin'] for m in mappings]);base_values=[r['current_value'] for r in rows]
    attempts=0;baseline_point=None
    passive=bool(configuration['task'].get('physical_problem'))
    dynamic=study.effect_semantics=='finite_time_task_response'

    def bind_matching_conditions(record):
        if study.operation!='interact':return
        from tools.state_io import digest
        fixed=resolved_request(context['space'],record['parameters'] or context['parameters'])
        for row,value in zip(rows,base_values):set_parameter(fixed,row['parameter_id'],value)
        cfg=record['configuration'];mechanics=record['mechanics']
        policy=deepcopy(cfg['policy'])
        # Builder request records the intentional intervention. Compare its
        # resolved fixed coordinates, while retaining builder/model versions.
        policy['candidate_builder']['parameters']['data']['request']=fixed
        initial=(mechanics.get('dynamic_execution') or {}).get('initial_state') if dynamic else mechanics
        initial=initial or {}
        record['matching_identity']=digest(dict(task=cfg['task'],model_protocol=policy,
            robot_conditions={k:v for k,v in cfg['robot'].items() if k!='structure'},
            fixed_parameters=fixed,point_semantics=study.point_semantics,
            initial_state={k:initial.get(k) for k in ('qpos_rad','qvel_rad_s')} if not passive or dynamic else 'same frozen initialization and re-equilibration procedure',
            control=mechanics.get('actual_tensions_n') if not passive else 'no_active_control'))

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
        if dynamic:
            from types import SimpleNamespace
            from schemas.platform import SessionInput
            from extensions.tendon_family.passive_execution import execute,execute_pair
            from extensions.reference.passive_response import task_metrics
            from tools.research_tasks import task_adapter,constraint_gap
            directory=getattr(checkpoint,'directory',None)
            folder=directory/('dynamic_'+str(index)) if directory else None
            checks=dict(execution_checks=study.execution_checks) if study.execution_checks!='full' else {}
            if study.execution_profile:checks['execution_profile']=plain(study.execution_profile)
            from extensions.reference.passive_program import execution_identity
            from tools.platform_store import Store
            identity=execution_identity(cfg,profile=plain(study.execution_profile) if study.execution_profile else None,execution_checks=study.execution_checks)
            reuse=reusable_execution(Store(context['result_store']),context['result_sources'],identity) if context.get('result_store') else None
            other_reuse=None
            if study.passive_ablation and context.get('result_store'):
                other_identity=execution_identity(cfg,profile=plain(study.execution_profile) if study.execution_profile else None,execution_checks=study.execution_checks,intervention=study.passive_ablation)
                other_reuse=reusable_execution(Store(context['result_store']),context['result_sources'],other_identity,matching_baseline=reuse['raw'] if reuse else None)
            if reuse and not study.passive_ablation:raw=reuse['raw']
            else:
                backend=(execute_pair(SessionInput.model_validate(cfg),folder,study.passive_ablation,baseline=reuse,ablation=other_reuse,**checks) if study.passive_ablation else execute(SessionInput.model_validate(cfg),folder,**checks))
                raw=backend.data.data
            task=SessionInput.model_validate(cfg).task
            if task.goal.data.get('version')=='passive_response_v2':
                from extensions.reference.passive_evaluation_v2 import metrics
                # Mathematical response measures the qualified program/pair.
                # The registered evaluator still requires independent confirmation.
                measured=metrics(task,raw,check_confirmation=False,check_mechanism=bool(study.passive_ablation))
            else:measured=task_metrics(task,raw)
            components={'evaluator:'+c.name:dict(value=c.observed,passed=c.satisfied,limit=c.limit,unit=c.units)
                for c in measured['constraints']}
            objective_rows=task_adapter(cfg).constraint_observations(components)
            if not study.passive_ablation:objective_rows=[r for r in objective_rows if r.get('signal')!='paired_mechanism']
            gap=constraint_gap(objective_rows,valid_complete=measured['validity']=='valid')
            gap.update(scope='paired_response' if study.passive_ablation else 'baseline_response',
                acceptance_components_excluded=['independent_numerical_confirmation']+([] if study.passive_ablation else ['paired_mechanism']))
            observation=dict(status='computed' if measured['validity']=='valid' else 'unavailable',
                value=gap['signed_task_gap'],unit='1',reason=measured.get('reason'),
                objective_status=gap['objective_status'],
                task_gap=gap,task_acceptance='unmeasured',independent_numerical_confirmation='unmeasured')
            observation['diagnostic_task_gap']=task_adapter(cfg).diagnostic_task_gap(raw,plain(query.candidate),
                pointer='/structure_research/records/'+str(len(records))+'/mechanics/dynamic_execution',evaluation=measured)
            if study.execution_checks=='screening':
                complete=raw.get('status')=='completed' and all(e.get('complete') for e in raw.get('episodes',[]))
                observation.update(status='computed' if complete else 'unavailable',value=None,
                    reason='SCREENING_REQUIRES_ORIGINAL_FULL_VALIDATION',
                    screening=raw['execution_checks'],
                    scope='Diagnostic observations from unchanged physics and dense qualification; sparse route coverage cannot establish full-task validity or acceptance.')
            diagnosis=observation['diagnostic_task_gap'].get('qualification')
            if diagnosis:observation['qualification_diagnosis']=diagnosis
            mechanics=dict(dynamic_execution=raw,task_constraints=gap['constraints'],
                reference_semantics=dict(initial='frozen_dynamic_initial_state',displacement='same_episode_unloaded_sample',
                    unloaded_tip_drift='same_episode_initial_sample',constraint_model='mujoco_unilateral_soft_limits',
                    reference_time_s=(cfg['task']['goal']['data']['programs'][cfg['task']['goal']['data']['load_conditions'][0]][0]['end_s']
                        if cfg['task']['goal']['data'].get('version')=='passive_response_v2' else cfg['task']['goal']['data']['unloaded_until_s']),
                    time_grid=cfg['task']['timing'],protocol_version=cfg['task']['goal']['data'].get('version','passive_response_v1')),
                task_observations=[],constraint_state=dict(status='finite_time_soft_constraints',qualified=False),
                point_binding=dict(reference='frozen_dynamic_initial_state'))
            new_cost={k:0 for k in raw['cost']} if reuse and not study.passive_ablation else deepcopy(raw['cost'])
            native=SimpleNamespace(cost=new_cost,physics=dict(identity=raw['physical_binding']['model_identity']))
            models.append(native)
            record=dict(record_index=len(records),parameter_values=dict(zip(study.paths,values)),parameters=params,
                configuration=cfg,execution_directory=str(folder.resolve()) if folder else None,observation=observation,mechanics=mechanics,state=dict(reference='frozen_dynamic_initial_state'),
                physics_identity=native.physics['identity'],source_comparison=comparison['reference'] if comparison else None,
                compiled_physical_changes=dict(model_recompiled=True) if records and native.physics['identity']!=records[0]['physics_identity'] else {})
            record['response_action']='paired_mechanism' if study.passive_ablation else 'baseline_response'
            if reuse:record['reuse']={k:v for k,v in reuse.items() if k!='raw'}
            if other_reuse:record['ablation_reuse']={k:v for k,v in other_reuse.items() if k!='raw'}
            bind_matching_conditions(record)
            records.append(record);cache[key]=record
            if checkpoint:checkpoint('mechanism_return_'+str(index),dict(index=index,cost=native.cost,observation=observation,raw_execution=raw))
            if observation['status']!='computed':failures.append(dict(record_index=record['record_index'],reason=measured.get('reason')))
            return record
        if passive:
            from extensions.tendon_family.passive import PassiveModel
            from extensions.tendon_family.passive_equilibrium import mechanics as constrained_mechanics
            from extensions.tendon_family.compiler import resolve
            goal=cfg['task']['goal']['data'];original=goal.get('execution_protocol') in ('phs2d_original_v1','hard_equilibrium_continuous_v1')
            scene=None
            if original:
                from schemas.platform import SessionInput
                from extensions.tendon_family.scene import assemble_physical
                from extensions.tendon_family.backends import physics_for
                inp=SessionInput.model_validate(cfg);physics=physics_for(inp);scene=assemble_physical(inp,physics)
                scene['control']=dict(tension_execution_mode='passive_fixed_payout_v1',
                    solreflimit=goal['solreflimit'],solimplimit=goal['solimplimit'])
            else:physics=resolve(cfg['robot']['structure']['data'],cfg['policy']['discretization']['data'])
            native=PassiveModel(physics,cfg['task']['physical_problem'],scene=scene)
            if original:native.protocol['static_solver'].update(goal['unloaded_static_solver'])
            seed=None
            if not original and records and records[0]['mechanics']['equilibrium'] is not None and native.physics['dofs']==models[0].physics['dofs']:
                seed=[records[0]['mechanics'][k]['equilibrium']['qpos'] for k in ('baseline_equilibrium','equilibrium')]
            qualification_only=(study.operation=='inspect' and study.target.quantity=='constraint_active_set'
                and study.load_condition==native.problem.baseline_load)
            mechanics=constrained_mechanics(native,study.load_condition,getattr(study.target,'material_s',.5),seed,
                study.target.direction_world if study.target.quantity=='directional_material_response' else None,
                unloaded_multistart=goal.get('unloaded_multistart',False),qualification_only=qualification_only)
            from tools.research_tasks import task_adapter
            if mechanics['equilibrium'] is not None:
                mechanics['task_observations']=task_adapter(cfg).constrained_observations(mechanics)
            data=dict(equilibrium=mechanics['equilibrium']['equilibrium'] if mechanics['equilibrium'] else None)
        else:native=NativeModel(cfg)
        models.append(native)
        if passive:pass
        elif baseline_point is None:
            baseline_point,data=native.reconstruct(point) if point.get('native_replay') else (point,native.restore(point))
            if study.point_semantics!='saved_native_state':
                if study.point_semantics=='fixed_generalized_pose':baseline_point={**baseline_point,'qvel_rad_s':[0.]*len(native.order)}
                data=native.restore(baseline_point,comparable=True)
        elif study.point_semantics=='frozen_task_initial_state':
            own={**baseline_point,'dof_order':native.order,'tendon_order':native.tendons,
                'qpos_rad':native.scene['qpos_rad'],'qvel_rad_s':native.scene['qvel_rad_s'],'actual_time_s':0.}
            data=native.restore(own,comparable=True)
        else:data=native.restore(baseline_point,comparable=True)
        if not passive:
            u=point['u'] if query.native.tensions_n is None else query.native.tensions_n
            mechanics=native.mechanics(data,u,material_s=study.target.material_s) if study.target.quantity=='material_point_jacobian' else native.mechanics(data,u)
        observation=(dict(status='computed',value=None,unit='1',qualification_diagnosis=mechanics['qualification_diagnosis'],
            reason='Initialization diagnosis completed; no qualified working point.') if passive and mechanics['equilibrium'] is None else observe(mechanics,study.target))
        record=dict(record_index=len(records),parameter_values=dict(zip(study.paths,values)),parameters=params,
            configuration=cfg,observation=observation,mechanics=mechanics,state=data if passive else native.checkpoint(data),
            physics_identity=native.physics['identity'],source_comparison=comparison['reference'] if comparison else None)
        if not passive and not records and study.point_semantics=='saved_native_state':
            record['state'].update(candidate=binding['candidate'],configuration_identity=binding['effective_configuration_identity'],
                provenance=baseline_point.get('provenance'),prefix_tensions_n=baseline_point.get('prefix_tensions_n'),
                remaining_task_s=point.get('remaining_task_s'))
        record['compiled_physical_changes']=physical_changes(records[0]['mechanics'],mechanics) if records else {}
        bind_matching_conditions(record)
        records.append(record);cache[key]=record
        if checkpoint:checkpoint('mechanism_return_'+str(index),dict(index=index,cost=native.cost,observation=observation))
        if observation['status']!='computed':raise ValueError(observation['reason'])
        return record

    def at_normalized(z):return evaluate([physical_value(m,float(v)) for m,v in zip(mappings,z)])

    result=dict(status='computed',operation=METHOD,binding=binding,protocol=plain(query.protocol),
        task_acceptance='unmeasured',proxy_values={},operating_point=dict(name=query.operating_point,
            actual_time_s=point['actual_time_s'],semantics=study.point_semantics,
            source=point.get('provenance') or point.get('source'),
            control_treatment='No active control; same frozen load condition and fixed assembly payout across load cases.' if passive else 'Same legal absolute tensions in every model; no control reoptimization.'))
    evidence=dict(operation=study.operation,target=plain(study.target),records=records,
        model_source='Constrained native equilibrium' if passive else 'NativeModel.mechanics',point_semantics=study.point_semantics,
        scope='Task initial state, fixed generalized pose and saved native state are distinct. Changed structures use named-coordinate transfer/reset, not equal Cartesian state, energy or equilibrium.',
        unsupported_conclusions=['full task improvement','task success','strict derivative','structural descent certificate',
            'passive constraint nullspace','hardware performance'])
    if context.get('parameterized_problem'):evidence['parameterized_problem']=context['parameterized_problem']
    evidence['effect_semantics']=study.effect_semantics
    if study.execution_checks=='screening':
        evidence['execution_checks']=context['execution_checks']
    from tools.research_tasks import task_adapter
    from extensions.math_analysis.differentiation_router import select_method
    evidence['method_selection']=select_method(effect_semantics=study.effect_semantics,
        capabilities=task_adapter(configuration).physical_capabilities(),target=study.target.quantity,operation=study.operation)
    evidence['reference_semantics']=(dict(initial='frozen_dynamic_initial_state',displacement='same_episode_unloaded_sample',
        constraint_model='mujoco_unilateral_soft_limits') if dynamic else
        dict(baseline='re_equilibrated_unloaded',loaded='re_equilibrated_loaded',constraint_model='ideal_hard_unilateral') if passive else
        dict(initial='saved_active_execution_state' if study.point_semantics=='saved_native_state' else 'frozen_dynamic_initial_state',constraint_model='active_ideal_tension'))
    if passive:
        from tools.research_tasks import task_adapter
        evidence['scope']=('All frozen load episodes, identical named initial reset and complete dynamic sampling. Research observation grants no certificate or SELECT eligibility.' if dynamic else
            'Each rebuilt legal assembly solves both frozen zero-load and selected loaded equilibria. Payout is fixed across load cases; hard equilibrium is separate from native soft-limit dynamics.')
        evidence['unsupported_conclusions'].remove('passive constraint nullspace')
    try:
        base=evaluate();evidence['baseline']=base['observation'];selected=None;responses=[]
        # Missing formal scalar does not suppress explicitly requested diagnostics.
        if passive:evidence.update(physical_problem='passive_unilateral_equilibrium',
            constraint_state=base['mechanics']['constraint_state'],point_binding=base['mechanics']['point_binding'],
            task_observations=base['mechanics']['task_observations'],
            qualification_diagnosis=base['mechanics'].get('qualification_diagnosis'),
            registered_acceptance=task_adapter(configuration).execution_requirements()['registered_acceptance'])
        if study.operation=='compare':
            if study.comparison_load_conditions:
                from extensions.tendon_family.passive_equilibrium import mechanics as constrained_mechanics
                from tools.research_tasks import task_adapter
                cases=[dict(load_condition=study.load_condition,observation=base['observation'],
                    task_observations=base['mechanics']['task_observations'],mechanics=base['mechanics'])]
                for condition in study.comparison_load_conditions:
                    mechanics=constrained_mechanics(models[0],condition,study.target.material_s,
                        direction_world=study.target.direction_world if study.target.quantity=='directional_material_response' else None,
                        baseline_result=base['mechanics']['baseline_equilibrium'],
                        unloaded_multistart=configuration['task']['goal']['data'].get('unloaded_multistart',False))
                    observation=observe(mechanics,study.target)
                    if observation['status']!='computed':raise ValueError(observation['reason'])
                    cases.append(dict(load_condition=condition,observation=observation,
                        task_observations=task_adapter(configuration).constrained_observations(mechanics),mechanics=mechanics))
                evidence['load_comparison']=dict(cases=cases,assembly_unchanged=True,
                    scope='Identical structure, payout, material, mounting and gravity; same unloaded reference. Local static comparison only.')
                if study.load_aggregation:
                    values=[c['observation']['value'] for c in cases]
                    if any(np.asarray(v).ndim for v in values):raise ValueError('LOAD_AGGREGATION_REQUIRES_SCALAR_REDUCTION')
                    choose=min if study.load_aggregation=='minimum' else max
                    case=choose(cases,key=lambda c:c['observation']['value'])
                    evidence['load_comparison']['aggregate']=dict(operation=study.load_aggregation,
                        value=case['observation']['value'],unit=case['observation']['unit'],load_condition=case['load_condition'])
            else:
                other=evaluate(comparison=context['comparisons'][0])
                evidence['comparison']=dict(baseline=base['observation']['value'],other=other['observation']['value'],
                    delta=(np.asarray(other['observation']['value'])-np.asarray(base['observation']['value'])).tolist()
                        if other['observation']['value'] is not None and base['observation']['value'] is not None else None)
        elif dynamic and base['observation']['value'] is None and study.operation!='interact':
            evidence.update(derivative_status='not_defined',direction_status='diagnostic_comparison')
            if study.operation in ('differentiate','optimize'):
                for i,row in enumerate(rows):
                    for value in set(stencil(row)['coordinates']):
                        values=list(base_values);values[i]=value;evaluate(values)
                if len(rows)==2:evaluate(list(matched_points(rows)[-1]['parameter_values'].values()))
        elif study.operation=='interact':
            for matched in matched_points(rows)[1:]:
                record=evaluate(list(matched['parameter_values'].values()))
                if not dynamic and record['observation']['status']!='computed':raise ValueError('INCOMPLETE_MATCHED_INTERACTION')
        elif study.operation in ('differentiate','optimize'):
            for i,row in enumerate(rows):
                first=len(records)
                def probe(value):
                    values=list(base_values);values[i]=value
                    return evaluate(values)
                response=differentiate(row,base,probe,goal=study.target.goal,allow_ineligible=dynamic or passive)
                if evidence['method_selection']['method']=='passive_kkt_implicit' and response['consistency']['passed']:
                    from extensions.math_analysis.differentiation_router import re_equilibrated
                    response['implicit_sensitivity']=re_equilibrated(row,base,records,models,response,study)
                if dynamic:
                    active=lambda record:{r['constraint_id'] for r in record['observation']['task_gap']['dominant_constraints']}
                    switch=any(active(record)!=active(base) for record in records[first:])
                    gate_switch=any(record['observation']['task_gap']['hard_gate_status']!=base['observation']['task_gap']['hard_gate_status'] for record in records[first:])
                    response.update(direction_status='directional_comparison',maximum_constraint_switch=switch,strict_derivative=False)
                    if switch or gate_switch:
                        response.update(suggested_delta=None,selected_record_index=None,
                            derivative_status='discontinuous_hard_gate' if gate_switch else 'nonsmooth_maximum_switch')
                        response['consistency'].update(passed=False,reason='HARD_GATE_SWITCH' if gate_switch else 'NONSMOOTH_MAXIMUM_CONSTRAINT_SWITCH')
                if passive and not dynamic:
                    branch=base['mechanics']['equilibrium']['equilibrium']
                    changed=any(r['mechanics']['equilibrium']['equilibrium'][key]!=branch[key]
                        for r in records[first:] for key in ('active','positive'))
                    qualified=all(r['mechanics']['constraint_state']['qualified'] for r in [base,*records[first:]])
                    smooth=all(r['mechanics']['constraint_state']['status']=='smooth_fixed_active_set' for r in [base,*records[first:]])
                    response['branch_status']='active_set_switch' if changed else 'unqualified' if not qualified else 'nonsmooth_or_degenerate' if not smooth else 'same_active_set'
                    if changed or not qualified or not smooth:
                        from extensions.math_analysis.differentiation_router import withhold_gradient
                        withhold_gradient(response,response['branch_status'])
                response.update(parameter_path=row['parameter_id'],parameter_unit=row['unit'],
                    model_effect_observed=any(r['compiled_physical_changes'] for r in records[first:]))
                if not response['model_effect_observed']:
                    response.update(direction_status='unresolved',suggested_delta=None,selected_record_index=None)
                    if dynamic:response['derivative_status']='no_observed_physical_effect'
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
                    try:
                        value=at_normalized(z)['observation']['value']
                        return -preference*float(value) if value is not None else float('inf')
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
                if not dynamic and eligible and all(r['consistency']['passed'] for r in responses):
                    best=max(eligible,key=lambda r:preference*r['observation']['value'])
                    if preference*(best['observation']['value']-base['observation']['value'])>max(1e-12,abs(base['observation']['value'])*1e-9):selected=best
            if dynamic:
                observed=observed_task_improvement(records,rows,bounds if study.operation=='optimize' else None)
                selected=records[observed['improved_record_index']] if observed['improved_record_index'] is not None else None
            if selected and len(rows)==2 and not dynamic:
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
                if passive:
                    # Frozen defaults have no passive control effect; the public
                    # passive generation Schema deliberately omits this field.
                    generation.pop('control_weights',None)
                direction=dict(version='structure_direction_v2',candidate=binding['candidate'],parameter_changes=changes,
                    baseline_metric=base['observation'],perturbed_metric=selected['observation'],
                    numerical_consistency=[r['consistency'] for r in responses],
                    tradeoffs=('All frozen dynamic observations retained; independent task acceptance remains unmeasured.' if dynamic else
                        'All frozen task constraints, finite response and task acceptance remain unmeasured.'),
                    model_scope='Finite-time fixed-payout MuJoCo soft limits under every frozen load.' if dynamic else 'Contact-free fixed-payout equilibrium under frozen loads.' if passive else 'Contact-free native ideal tension, declared state and absolute input only.',
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
            evidence['direction_status']=('observed_improvement_proposal' if dynamic else 'locally_supported_proposal') if selected else 'unresolved'
    except ValueError as exc:
        incomplete=dynamic and records and records[-1]['observation']['status']!='computed'
        result.update(status='execution_incomplete' if incomplete else 'not_applicable',reason=str(exc))
        evidence['failure']=dict(reason=str(exc),attempted_evaluations=attempts)
    if study.operation=='interact':
        evidence['interaction']=interaction_evidence(matched_points(rows),records)
        if dynamic and any(r['observation']['value'] is None for r in records):
            evidence['interaction'].update(status='diagnostic_comparison',formal_causal_conclusion=False,
                observations=[dict(record_index=r['record_index'],parameter_values=r['parameter_values'],
                    task_gap=r['observation'].get('diagnostic_task_gap'),qualification=r['observation'].get('qualification_diagnosis')) for r in records])
        evidence['interaction']['sources']=[f'/structure_research/records/{r["record_index"]}' for r in records]
    if dynamic and records and any(r['observation']['value'] is None for r in records):
        baseline={r['constraint_id']:r for r in records[0]['observation']['diagnostic_task_gap']['constraints']}
        comparisons=[]
        for record in records[1:]:
            changes=[]
            for row in record['observation']['diagnostic_task_gap']['constraints']:
                base_row=baseline[row['constraint_id']];a=base_row['observed_value'];b=row['observed_value']
                changes.append(dict(constraint_id=row['constraint_id'],baseline=a,value=b,unit=row['unit'],
                    delta=b-a if a is not None and b is not None and row['unit']==base_row['unit'] else None,
                    baseline_source=base_row['source_pointer'],source=row['source_pointer']))
            comparisons.append(dict(record_index=record['record_index'],changes=changes,qualification=record['observation'].get('qualification_diagnosis')))
        evidence['diagnostic_comparison']=dict(status='diagnostic_comparison',comparisons=comparisons,
            formal_gradient=None,formal_descent=None,scope='Recorded component changes only; qualifications and missing measurements remain explicit.')
    if dynamic:
        observed=observed_task_improvement(records,rows,evidence.get('local_search',{}).get('bounds_normalized'))
        evidence.update({k:v for k,v in observed.items() if k!='gaps'})
        evidence['unsupported_conclusions']=[x for x in evidence['unsupported_conclusions'] if x!='full task improvement']
        evidence['unsupported_conclusions'].append('independent task acceptance')
        active=[{r['constraint_id'] for r in g['dominant_constraints']} for g in observed['gaps'] if g['comparable']]
        switch=any(a!=active[0] for a in active[1:])
        gate_switch=bool(observed['gaps'] and any(g['hard_gate_status']!=observed['gaps'][0]['hard_gate_status'] for g in observed['gaps'][1:]))
        evidence['maximum_constraint_switch']=switch
        evidence.setdefault('derivative_status','discontinuous_hard_gate' if gate_switch else 'nonsmooth_maximum_switch' if switch else
            [r['derivative_status'] for r in evidence.get('parameter_sensitivities',[])] or 'not_requested')
    cost={key:sum(m.cost[key] for m in models) for key in (models[0].cost if models else [])}
    cost.update(evaluation_attempts=attempts,kernel_wall_s=time.perf_counter()-started)
    evidence.update(cost=cost,invalid_local_probes=failures)
    evidence['method_selection'].update(actual_cost=cost,working_point=evidence['reference_semantics'],
        parameter=study.paths,evidence_source='/structure_research/records',
        numerical_consistency=[r['consistency'] for r in evidence.get('parameter_sensitivities',[])])
    if passive or study.operation=='interact':
        evidence['sensitivity_evidence']=dict(version='physical_sensitivity_evidence_v1',
            problem='/structure_research/parameterized_problem',
            parameter_paths=study.paths,method=evidence['method_selection'],
            sensitivities=evidence.get('parameter_sensitivities',[]),
            **(dict(interaction_source='/structure_research/interaction') if study.operation=='interact' else {}),
            active_set_and_kkt_sources=[f'/structure_research/records/{i}/mechanics/constraint_state' for i in range(len(records)) if passive],
            scope=evidence['scope'],cost=cost,task_acceptance='unmeasured')
    if evidence.get('structure_direction'):evidence['structure_direction']['actual_cost']=cost
    execution_index=[]
    from pathlib import Path
    for i,record in enumerate(records):
        raw=record.get('mechanics',{}).get('dynamic_execution') or {}
        directory=record.get('execution_directory');pointer=f'/structure_research/records/{i}/mechanics/dynamic_execution'
        arms=[(raw,pointer,str(Path(directory)/'baseline') if directory and raw.get('paired_ablation') else directory)]
        if raw.get('paired_ablation',{}).get('ablation'):arms.append((raw['paired_ablation']['ablation'],pointer+'/paired_ablation/ablation',str(Path(directory)/'ablation') if directory else None))
        execution_index.extend(dict(identity=arm['execution_identity']['identity'],pointer=source,directory=folder) for arm,source,folder in arms if arm.get('execution_identity'))
    if execution_index:result['physical_execution_index']=execution_index
    result.update(structure_research=evidence,model_identity=records[0]['physics_identity'] if records else None,
        internal_calculations=[dict(purpose='native_mechanism_structure',**cost)])
    return result


def dynamic_summary(raw, reference):
    """First-delivery facts only; full per-probe constraints stay in the Store."""
    observed=observed_task_improvement(raw['records'])
    observed.update({k:raw[k] for k in observed if k!='gaps' and k in raw})
    gaps=observed.pop('gaps');best=observed['best_valid_record_index']
    fields=('constraint_id','condition_id','observed_value','bound','bound_type','unit','normalized_violation','passed')
    def compact(gap):
        return dict(signed_task_gap=gap['signed_task_gap'],normalized_gap=gap['normalized_gap'],
            objective_status=gap['objective_status'],valid_complete=gap['valid_complete'],
            observation_feasible=gap['observation_feasible'],hard_gate_status=gap['hard_gate_status'],
            dominant_constraints=[{k:r[k] for k in fields if k in r} for r in gap['dominant_constraints']])
    gates=[]
    for key in dict.fromkeys(key for gap in gaps for key in gap['hard_gate_constraints']):
        facts=[r for gap in gaps for r in gap['constraints'] if r['constraint_id']==key]
        failed=[r for r in facts if r['passed'] is False]
        gates.append(dict(constraint_id=key,condition_id=facts[0].get('condition_id'),bound=facts[0]['bound'],
            unit=facts[0]['unit'],baseline_passed=facts[0]['passed'],
            best_passed=next((r['passed'] for r in gaps[best]['constraints'] if r['constraint_id']==key),None) if best is not None else None,
            failed_observations=len(failed),failed_values=list(dict.fromkeys(r['observed_value'] for r in failed))))
    direction=raw.get('structure_direction');handoff=None
    if direction and direction.get('generation_handoff'):
        handoff=dict(tool='research_plan',action='generate',agent_decision_required=True,
            if_action_not_loaded=dict(tool='research_route',input=dict(tool='research_plan',action='generate')),
            alternatives=direction['generation_handoff']['alternatives'],supporting_evidence=[reference],
            generation_query=dict(reference=reference,pointer='/structure_research/structure_direction/generation_handoff/generation'),
            direction_source=dict(reference=reference,pointer='/structure_research/structure_direction'))
    diagnosis=(raw.get('baseline') or {}).get('qualification_diagnosis')
    if diagnosis:
        diagnosis=deepcopy(diagnosis)
        diagnosis['source']['reference']=reference
        for failure in diagnosis['failed_qualifications']:failure['source']['reference']=reference
    executions=[dict(response_action=r.get('response_action'),identity=r.get('mechanics',{}).get('dynamic_execution',{}).get('execution_identity',{}).get('identity'),
        execution_profile=r.get('mechanics',{}).get('dynamic_execution',{}).get('execution_profile'),
        reuse=r.get('reuse'),ablation_reuse=r.get('ablation_reuse'),
        source=dict(reference=reference,pointer='/structure_research/records/'+str(i))) for i,r in enumerate(raw['records'])]
    return dict(operation=raw['operation'],effect_semantics=raw['effect_semantics'],executions=executions,
        **(dict(execution_checks=raw['execution_checks']) if raw.get('execution_checks') else {}),
        **(dict(interaction={**raw['interaction'],
            'source':dict(reference=reference,pointer='/structure_research/interaction')}) if raw.get('interaction') else {}),
        qualification_diagnosis=diagnosis,diagnostic_comparison=raw.get('diagnostic_comparison'),
        baseline=compact(gaps[0]) if gaps else None,best_valid=compact(gaps[best]) if best is not None else None,
        hard_gates=gates,parameter_changes=direction['parameter_changes'] if direction else [],
        direction_status=raw.get('direction_status','not_requested'),derivative_status=raw.get('derivative_status','not_requested'),
        maximum_constraint_switch=raw.get('maximum_constraint_switch',False),
        parameter_sensitivities=[{k:r[k] for k in ('parameter_path','derivative_status','maximum_constraint_switch','strict_derivative') if k in r}
            for r in raw.get('parameter_sensitivities',[])],
        **observed,task_acceptance='unmeasured',reference_semantics=raw.get('reference_semantics'),
        observation_counts=dict(total=len(gaps),invalid_or_incomplete=sum(not g['valid_complete'] for g in gaps),
            hard_gate_failed=sum(g['hard_gate_status']=='failed' for g in gaps)),
        cost=raw['cost'],generation_handoff=handoff,
        source=dict(reference=reference,pointer='/structure_research'),
        records_query=dict(reference=reference,pointer='/structure_research/records'),
        unsupported_conclusions=raw['unsupported_conclusions'],
        projection='Read-only TaskGap reduction of saved constraint observations; original records and acceptance unchanged.')


def summary(value, reference):
    """Read-only projection of immutable evidence, with a source-bound Plan fragment."""
    raw=value['structure_research'];direction=raw.get('structure_direction');baseline=raw.get('baseline',{}).get('value')
    if raw.get('effect_semantics')=='finite_time_task_response':return dynamic_summary(raw,reference)
    handoff=None
    if direction and direction.get('generation_handoff'):
        handoff=dict(tool='research_plan',action='generate',agent_decision_required=True,
            if_action_not_loaded=dict(tool='research_route',input=dict(tool='research_plan',action='generate')),
            alternatives=direction['generation_handoff']['alternatives'],supporting_evidence=[reference],
            generation_query=dict(reference=reference,pointer='/structure_research/structure_direction/generation_handoff/generation'),
            direction_source=dict(reference=reference,pointer='/structure_research/structure_direction'))
    compact=({k:direction[k] for k in ('parameter_changes','parameter_path','parameter_unit','delta','suggested_value',
        'full_task_improvement_verified','formal_candidate_created','proposal_only','other_parameters_unchanged') if k in direction} if direction else None)
    if compact and compact.get('parameter_changes'):
        for key in ('parameter_path','parameter_unit','delta','suggested_value'):compact.pop(key,None)
    def observation_summary(item):
        array=np.asarray(item) if item is not None else None
        if array is not None and array.ndim and not array.size:return dict(shape=list(array.shape),minimum=None,maximum=None,norm=0.)
        return item if array is None or array.ndim==0 else dict(shape=list(array.shape),
            minimum=float(np.min(array)),maximum=float(np.max(array)),norm=float(np.linalg.norm(array)))
    if compact is not None and direction.get('baseline_metric') and direction.get('perturbed_metric'):
        compact['metric_comparison']=dict(
            baseline=observation_summary(direction['baseline_metric'].get('value')),
            proposed=observation_summary(direction['perturbed_metric'].get('value')),
            unit=direction['perturbed_metric'].get('unit'),
            scope='Metrics correspond to the proposed parameter_changes. Numerical consistency may describe different stencil coordinates; its observed_change is not the proposed-step gain.',
            baseline_source=dict(reference=reference,pointer='/structure_research/structure_direction/baseline_metric'),
            proposed_source=dict(reference=reference,pointer='/structure_research/structure_direction/perturbed_metric'))
    baseline_summary=observation_summary(baseline)
    tendon_order=(raw.get('baseline',{}).get('metadata') or {}).get('tendon_order')
    if (raw['target'].get('quantity')=='constraint_multiplier' and raw['target'].get('reduction')=='identity'
            and tendon_order and isinstance(baseline_summary,dict) and baseline_summary.get('shape')==[len(tendon_order)]):
        baseline_summary.update(tendon_values=[dict(tendon=name,value=value) for name,value in zip(tendon_order,baseline)],
            values_source=dict(reference=reference,pointer='/structure_research/baseline/value'),
            channel_order_source=dict(reference=reference,pointer='/structure_research/baseline/metadata/tendon_order'))
    comparison=({k:observation_summary(v) for k,v in raw['comparison'].items() if k!='baseline'} if raw.get('comparison') else None)
    sensitivity=[{k:row[k] for k in ('parameter_path','derivatives','derivative_unit','consistency','direction_status','derivative_status','branch_status','strict_derivative') if k in row}
        for row in raw.get('parameter_sensitivities',[])]
    for compact_sensitivity,row in zip(sensitivity,raw.get('parameter_sensitivities',[])):
        if row.get('implicit_sensitivity'):
            compact_sensitivity['implicit_sensitivity']={k:row['implicit_sensitivity'][k] for k in
                ('status','baseline_included','relative_error','gradient_trustworthy','strict_derivative','reason') if k in row['implicit_sensitivity']}
    def constraint_summary(state):
        if not state:return state
        compact={k:v for k,v in state.items() if k!='native_soft_length_residual_m'}
        if 'native_soft_length_residual_m' in state:
            compact['native_soft_length_excess_m']=max(0.,max(state['native_soft_length_residual_m']))
        return compact
    constraint_state=constraint_summary(raw.get('constraint_state'))
    failed_observations=[]
    for i,record in enumerate(raw.get('records',[])):
        observation=record.get('observation') or {};mechanics=record.get('mechanics') or {}
        qualification=mechanics.get('qualification_diagnosis') or {};constraints=mechanics.get('constraint_state') or {}
        if (observation.get('status') not in (None,'computed','available')
                or qualification.get('qualified') is False or constraints.get('qualified') is False):
            failed_observations.append(dict(record_index=i,parameter_values=record.get('parameter_values'),
                observation={k:observation[k] for k in ('status','reason') if k in observation},
                qualification_diagnosis={k:qualification[k] for k in ('status','qualified','stability_qualified','failure_layers') if k in qualification},
                constraint_state=constraint_summary(constraints),
                source=dict(reference=reference,pointer=f'/structure_research/records/{i}')))
    task_observations=deepcopy(raw.get('task_observations',[])[:4])
    diagnosis=raw.get('qualification_diagnosis')
    if diagnosis:
        from extensions.tendon_family.passive_equilibrium import qualification_projection
        diagnosis=qualification_projection(diagnosis)
        if diagnosis.get('initial_qualification'):
            diagnosis['initial_qualification']['source']=dict(reference=reference,pointer='/structure_research/qualification_diagnosis/initial_qualification')
        if raw['qualification_diagnosis'].get('numerical_failure'):
            diagnosis['numerical_failure_pointer']='/structure_research/qualification_diagnosis/numerical_failure'
    if raw.get('physical_problem'):
        definitions={o['name']:o for o in raw['records'][0]['configuration']['task']['physical_problem'].get('observations',[])}
        for row in task_observations:
            metric=definitions[row['name']]
            if (raw['target']['quantity']=='re_equilibrated_position_response' and raw['target']['reduction']=='norm' and metric.get('reduction','norm')=='norm' and
                    metric['quantity']=='material_displacement' and metric.get('material_s',.5)==raw['target'].get('material_s',.5)):
                row.pop('value',None);row['value_at']='structure_research.baseline'
            row['observation']={k:v for k,v in row.get('observation',{}).items() if k not in ('name','load_condition','minimum','maximum','unit')}
    return dict(operation=raw['operation'],target=raw['target'],baseline=baseline_summary,baseline_unit=raw.get('baseline',{}).get('unit'),
        **(dict(interaction={**raw['interaction'],
            'source':dict(reference=reference,pointer='/structure_research/interaction')}) if raw.get('interaction') else {}),
        physical_problem=raw.get('physical_problem'),constraint_state=constraint_state,point_binding=raw.get('point_binding'),
        constraint_state_load_condition=((raw.get('point_binding') or {}).get('load') or {}).get('name'),
        qualification_diagnosis=diagnosis,
        qualification_scope='Top-level qualification describes the baseline equilibrium, not every perturbed observation. Failed observations retain their own recorded coordinates and qualification; failure alone does not demonstrate an interface or method-routing defect.',
        failure=raw.get('failure'),failed_observations=failed_observations,
        registered_acceptance=raw.get('registered_acceptance','unmeasured'),
        task_observations=task_observations,
        direction_status=raw.get('direction_status',raw.get('sensitivity',{}).get('direction_status','not_requested')),
        structure_direction=compact,generation_handoff=handoff,
        comparison=comparison,parameter_sensitivities=sensitivity,local_search=raw.get('local_search'),
        load_comparison=({**{k:v for k,v in raw['load_comparison'].items() if k!='cases'},
            'scope':'Top-level constraint_state describes the baseline load only. Each case owns its constraint state; aggregate applies only to the requested target.',
            'cases':[dict(load_condition=c['load_condition'],status=c['observation']['status'],
                value=observation_summary(c['observation']['value']),unit=c['observation']['unit'],
                qualified=c['mechanics']['constraint_state']['qualified'],
                constraint_state=constraint_summary(c['mechanics']['constraint_state']),
                source=dict(reference=reference,pointer=f'/structure_research/load_comparison/cases/{i}'))
                for i,c in enumerate(raw['load_comparison']['cases'])]} if raw.get('load_comparison') else None),
        source=dict(reference=reference,pointer='/structure_research'),
        direction_source=dict(reference=reference,pointer='/structure_research/structure_direction') if direction else None,
        effect_semantics=raw.get('effect_semantics'),reference_semantics=raw.get('reference_semantics'),
        method_selection=raw.get('method_selection'),
        **(dict(sensitivity_evidence=dict(version=raw['sensitivity_evidence']['version'],
            parameter_paths=raw['sensitivity_evidence']['parameter_paths'],
            raw_query=dict(reference=reference,view='full',pointer='/structure_research/sensitivity_evidence')))
            if raw.get('sensitivity_evidence') else {}),
        cost=raw['cost'],task_acceptance='unmeasured',unsupported_conclusions=raw['unsupported_conclusions'])
