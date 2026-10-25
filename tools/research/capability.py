"""B-line adapters: controlled comparisons and projection into unchanged F0 slots."""
from copy import deepcopy
from pydantic import FiniteFloat, Field
from schemas.common import Contract
from schemas.platform import EvidenceRef

CONIC_METHODS = ('sampled-affine-conic-minimax-v1', 'sampled-affine-conic-path-progress-v1')

SCORE_QUANTITY_SEMANTICS = dict(score='Computed signed minimax value within the declared model',
    delta='candidate_score - baseline_score; direct score difference',
    normalized_secant='structural score delta / structural parameter step * normalization_scale',
    control_reoptimization_improvement='fixed-old-control score - reoptimized score on the same candidate')


class CapabilityComparison(Contract):
    baseline_result: EvidenceRef
    variable: str
    normalization_scale: FiniteFloat = Field(gt=0)


def comparison_context(host, candidate, query):
    """Resolve an existing owned result; no baseline solve or budget reset."""
    from tools.research.core import read_evidence
    from tools.research.design import verify_candidate, parameter_value, set_parameter
    from tools.research.state import state
    from tools.platform_store import plain
    request = query.capability_comparison
    reference = plain(request.baseline_result)
    current = state(host)
    if reference not in current.get('analysis_results', []):
        raise ValueError('CAPABILITY_COMPARISON_REQUIRES_REGISTERED_BASELINE')
    baseline = read_evidence(host, dict(reference=reference), record_read=False)
    base_candidate = verify_candidate(host, baseline['candidate'])
    if (baseline.get('operation') != 'task_capability' or baseline.get('status') != 'computed'
            or baseline.get('implementation') != current['freeze']
            or baseline['protocol'] != plain(query.protocol)
            or baseline['requested_operation']['operating_point'] != query.operating_point
            or query.operating_point not in ('controller_start_input', 'standardized_initial_pretension')
            or not baseline.get('trajectory', {}).get('replay', {}).get('numerically_valid')):
        raise ValueError('CAPABILITY_COMPARISON_REQUIRES_MATCHED_VERIFIED_BASELINE')
    variable = request.variable
    if not (variable.startswith('segments.') and variable.split('.')[-1] in ('length_m', 'young_pa')
            and len(variable.split('.')) == 3):
        raise ValueError('CAPABILITY_COMPARISON_REQUIRES_SUPPORTED_CONTINUOUS_PARAMETER')
    a, b = (parameter_value(c['parameters'], variable) for c in (base_candidate, candidate))
    if a is None or b is None or a == b:
        raise ValueError('CAPABILITY_COMPARISON_REQUIRES_NONZERO_NUMERIC_STEP')
    expected = deepcopy(base_candidate['parameters']); set_parameter(expected, variable, b)
    left, right = base_candidate['configuration'], candidate['configuration']
    if (candidate['parameters'] != expected or candidate['source_identity'] != base_candidate['source_identity']
            or candidate['profile_identity'] != base_candidate['profile_identity'] or left['task'] != right['task']
            or any(left['policy'][k] != right['policy'][k] for k in ('controller', 'backend', 'dynamics_model'))):
        raise ValueError('CAPABILITY_COMPARISON_REQUIRES_SINGLE_PARAMETER_AND_FIXED_TASK_MODEL_CONTROL')
    return dict(kind='task_capability_comparison', baseline=baseline, baseline_result=reference,
        variable=variable, baseline_parameter=a, candidate_parameter=b, step=b-a,
        normalization_scale=request.normalization_scale)


def compare_control_response(model, requirements, protocol, optimized, context):
    """Reuse baseline physical commands; current candidate has its own rebuilt model."""
    from extensions.math_analysis.task_capability import task_capability
    import json
    base = context['baseline']
    baseline = base['trajectory']
    if (base['task_analysis']['constraints'] != [c.model_dump() for c in requirements.constraints]
            or base['task_analysis']['physical_inputs'] != requirements.physical_inputs
            or base['model']['binding']['coordinate_order'] != model.binding['coordinate_order']
            or baseline['horizon'] != json.loads(json.dumps(optimized.get('horizon')))):
        raise ValueError('CAPABILITY_COMPARISON_SAMPLING_INPUT_OR_COORDINATE_MISMATCH')
    fixed = task_capability(model, requirements, protocol, applied_input_n=baseline['applied_input_n'])
    before = baseline['best_found_violation']
    comparison = {k: v for k, v in context.items() if k not in ('baseline', 'kind')}
    comparison.update(baseline_violation=before, fixed_control=fixed,
        status='inconclusive', control_alignment='identical physical tensions, tendon order and time grid',
        reoptimization='Both candidates independently solved with the same three starts and iteration budget',
        derivative_scope='Two-design finite secants of computed values; no envelope gradient or descent guarantee',
        attribution='Same frozen source and candidate parameters except the declared continuous parameter',
        quantities={})
    for mode, result in (('fixed_control', fixed), ('reoptimized_control', optimized)):
        if not result.get('replay', {}).get('numerically_valid') or 'best_found_violation' not in result:
            continue
        delta = result['best_found_violation']-before
        comparison['quantities'][mode+'_delta'] = dict(value=delta, status='unverified_estimate')
        comparison['quantities'][mode+'_normalized_secant'] = dict(
            value=delta/context['step']*context['normalization_scale'], status='unverified_estimate')
    if len(comparison['quantities']) == 4:
        comparison['status'] = 'computed_estimate'
    return comparison


def capability_summary(trajectory):
    if trajectory.get('method_version') in CONIC_METHODS:
        dual=trajectory.get('dual_checks',{})
        return dict(method_version=trajectory['method_version'],
            replayed_violation=trajectory.get('replayed_violation'),optimality_status=trajectory.get('optimality_status'),
            support_lower_estimate=dual.get('support_lower_estimate'),gap=dual.get('replayed_support_gap'),
            full_requested_coverage=trajectory.get('full_requested_coverage',False),
            numerical_feasibility=trajectory.get('numerical_feasibility'),
            dominant_constraints=list(dict.fromkeys(r['constraint_id'] for r in dual.get('constraint_multipliers',[]) if r['epigraph_active'])),
            kernel_elapsed_s=trajectory.get('kernel_elapsed_s'),solver=trajectory.get('solver'),
            score_semantics='Signed sampled minimax; smaller is better. Float support estimate and gap are not rigorous bounds.',
            strict_optimality='unavailable',physical_failure_relation=dict(status='not_assessed'),
            problem_pointer='/trajectory/problem_definition',solver_starts_pointer='/trajectory/solver',
            sample_records_pointer='/trajectory/replay/records' if trajectory.get('replay') else '/trajectory/coverage',quantities_pointer='/trajectory/quantities',
            checks_pointer='/trajectory/dual_checks',scope='Local sampled affine model; physical acceptance unmeasured',
            control_reoptimization='required',
            **{k:trajectory[k] for k in ('status','coverage','coverage_counts','all_requested_checked','model_scope',
                'path_progress','path_assignment','path_assignment_comparison','path_assignment_ties',
                'internal_conic_solves','untimed_scope','auxiliary_coordinates','reason') if k in trajectory},
            sources={k:'/trajectory/'+k for k in ('replayed_violation','optimality_status','coverage',
                'path_progress','path_assignment_comparison','internal_conic_solves','model_scope') if k in trajectory})
    keys = ('best_found_violation', 'status', 'control_reoptimization', 'verification_scope',
        'start_value_spread', 'research_diagnostics', 'input_diagnostics', 'locality_diagnostics', 'kernel_elapsed_s',
        'near_active_records', 'co_bottleneck_records', 'solver_scope')
    summary = {k: trajectory[k] for k in keys if k in trajectory}
    summary['solver_starts'] = [{k: s.get(k) for k in ('start_index', 'success', 'status', 'iterations', 'returned_violation', 'epigraph_residual')} for s in trajectory.get('starts', [])]
    summary['solver_starts_pointer'] = '/trajectory/starts'
    summary['score_semantics'] = ('Signed maximum normalized constraint residual over analyzed samples; '
        'negative means positive normalized margin inside those bounds. Smaller is better; a negative score moving '
        'toward zero worsens this minimax score. A score is not a delta or secant.')
    summary['quantity_semantics'] = dict(SCORE_QUANTITY_SEMANTICS)
    summary['reason'] = trajectory.get('reason')
    summary['problem_pointer'] = '/trajectory/problem_definition'
    summary['quantities_pointer'] = '/trajectory/quantities'
    summary['sample_records_pointer'] = '/trajectory/replay/records'
    comparison = trajectory.get('structural_comparison')
    if comparison:
        summary['structural_comparison'] = {k: comparison[k] for k in (
            'status', 'variable', 'step', 'normalization_scale', 'quantities', 'baseline_result', 'derivative_scope',
            'control_alignment', 'reoptimization', 'attribution')}
        summary['structural_comparison'].update(baseline_violation=comparison['baseline_violation'],
            fixed_control_violation=comparison['fixed_control'].get('best_found_violation'),
            comparison_pointer='/trajectory/structural_comparison',
            fixed_control_value_pointer='/trajectory/structural_comparison/fixed_control/best_found_violation',
            fixed_control_pointer='/trajectory/structural_comparison/fixed_control',
            fixed_control_verification=comparison['fixed_control'].get('verification_scope'))
    return summary


def recorded_score_resolution(left, right):
    """Compare recorded SOCP support intervals, never add an acceptance tolerance."""
    intervals=[]
    for value in (left,right):
        tr=value.get('trajectory',{});dual=tr.get('dual_checks',{})
        hi=tr.get('replayed_violation');lo=dual.get('support_lower_estimate')
        if (hi is None or lo is None or lo>hi or not tr.get('replay',{}).get('numerically_valid')
                or tr.get('optimality_status')!='numerically_checked'):
            return dict(status='unknown',reason='Valid recorded primal replay and ordered numerical support estimates required')
        intervals.append([lo,hi])
    overlap=max(i[0] for i in intervals)<=min(i[1] for i in intervals)
    return dict(status='indistinguishable_at_recorded_numerical_precision' if overlap else 'separated_numerical_estimates',
        score_delta=intervals[1][1]-intervals[0][1],recorded_support_intervals=intervals,
        strict_structure_ranking_supported=False,
        scope='Floating support/replay estimates, not rigorous bounds; independent physics is separate. Historical incumbent unchanged.')


def signed_score_comparisons(summary, reference):
    """Direction of B's recorded controlled comparisons, never optimal ranking.

    computed_estimate is established by comparison_context/compare_control_response:
    matched task, model family, input coordinates, horizon, sampling and solve budget.
    All locations below name raw B fields, not projection aliases.
    """
    comparison=summary.get('structural_comparison')
    if not comparison or comparison['status']!='computed_estimate':
        return dict(status='not_comparable',reason='No recorded controlled computed comparison')
    candidate=summary['best_found_violation'];baseline=comparison['baseline_violation']
    fixed=comparison['fixed_control_violation']
    scope={k:comparison[k] for k in ('variable','step','normalization_scale','baseline_result','control_alignment','reoptimization','attribution','derivative_scope')}
    def location(pointer):return dict(reference=reference,pointer=pointer)
    def direction(name,before,after,pointer):
        delta=after-before
        return dict(comparison=name,baseline_score=before,candidate_score=after,delta=delta,
            smaller_is_better=True,computed_score_direction='worse' if delta>0 else 'better' if delta<0 else 'unchanged',
            source_references=[location(pointer),location('/trajectory/best_found_violation')])
    fixed_loss=fixed-baseline;recovery=fixed-candidate;residual=candidate-baseline
    decomposition=dict(fixed_control_degradation=fixed_loss,
        control_reoptimization_improvement=recovery,residual_reoptimized_degradation=residual,
        source_references=[location('/trajectory/structural_comparison/baseline_violation'),
            location('/trajectory/structural_comparison/fixed_control/best_found_violation'),
            location('/trajectory/best_found_violation')])
    if fixed_loss>0 and recovery>=0 and residual>=0:
        decomposition.update(fraction_denominator='fixed_control_degradation',
            recovery_fraction=recovery/fixed_loss,residual_fraction=residual/fixed_loss)
    secants={mode:dict(**comparison['quantities'][mode+'_normalized_secant'],
        source=location('/trajectory/structural_comparison/quantities/'+mode+'_normalized_secant/value'))
        for mode in ('fixed_control','reoptimized_control')}
    return dict(status='computed_estimate',definition='G = max(normalized_constraint_violation); smaller is better',
        quantity_semantics=dict(SCORE_QUANTITY_SEMANTICS),normalized_secants=secants,decomposition=decomposition,
        comparisons=[direction('reoptimized_candidate_vs_reoptimized_baseline',baseline,candidate,
                '/trajectory/structural_comparison/baseline_violation'),
            direction('candidate_reoptimized_vs_candidate_fixed_old_control',fixed,candidate,
                '/trajectory/structural_comparison/fixed_control/best_found_violation')],
        comparison_scope=scope,scope_source=location('/trajectory/structural_comparison'),
        optimality_status='uncertified',limitation='Computed local-model scores only; no optimal structural ranking or MuJoCo task acceptance')


def populate_mathematics(mathematics, trajectory, reference):
    """F0 quantity statuses describe the exact checked object, not stronger claims."""
    from schemas.research_reporting import EvidenceLocation, MathematicalQuantity, RecordedField
    def location(pointer):
        return EvidenceLocation(reference=reference, pointer=pointer)
    if trajectory.get('method_version') in CONIC_METHODS:
        quantities=[MathematicalQuantity(name=name,value=row['value'],
            status='unavailable' if row['value'] is None else 'verified' if name=='analytic_lower_bound' else 'unverified_estimate',
            control_reoptimization='required',
            unit='dimensionless',source=location('/trajectory/quantities/'+name+'/value') if row['value'] is not None else None,
            conditions=[RecordedField(name='strength',value=row['strength'],source=location('/trajectory/quantities/'+name+'/strength'))])
            for name,row in trajectory.get('quantities',{}).items()]
        return mathematics.model_copy(update=dict(problem_definition=location('/trajectory/problem_definition'),quantities=quantities))
    quantities = []
    groups = [(trajectory.get('quantities', {}), '/trajectory/quantities', [],
        trajectory.get('control_reoptimization', 'not_assessed'))]
    comparison = trajectory.get('structural_comparison')
    if comparison:
        for name, value in comparison['quantities'].items():
            groups.append(({name: value}, '/trajectory/structural_comparison/quantities', [comparison['variable']],
                'fixed_control' if name.startswith('fixed_control') else 'required'))
    for values, pointer, parameters, control in groups:
        for name, row in values.items():
            quantities.append(MathematicalQuantity(name=name, value=row['value'], status=row['status'],
                unit='dimensionless', source=location(pointer+'/'+name+'/value') if row['value'] is not None else None,
                structural_parameters=parameters, control_reoptimization=control,
                conditions=[RecordedField(name='problem_and_scope', value=trajectory['problem_definition'],
                    source=location('/trajectory/problem_definition')),
                    RecordedField(name='verification_scope', value=trajectory.get('verification_scope'),
                        source=location('/trajectory/verification_scope'))] if trajectory.get('verification_scope') else []))
    if comparison:
        for quantity in quantities:
            if quantity.structural_parameters:
                quantity.conditions.extend(RecordedField(name=key, value=comparison[key],
                    source=location('/trajectory/structural_comparison/'+key)) for key in
                    ('step','normalization_scale','reoptimization','control_alignment','derivative_scope','baseline_result'))
    return mathematics.model_copy(update=dict(problem_definition=location('/trajectory/problem_definition'), quantities=quantities))


def sensitivity_summary(value):
    """Finite differences remain diagnostics; unresolved dual faces stay visible."""
    rows=value.get('reoptimized_finite_difference',[])
    return dict(method_version=value['method_version'],direction_status=value['direction_status'],
        parameter=value['parameter_identity'],preferred_parameter_direction=value.get('preferred_parameter_direction','unresolved'),
        differences=[dict(step=r['step'],reoptimized=r['reoptimized'],interval=r['numerical_slope_interval'],
            dual_face_status=r['dual_face']['status'],source_pointer=f'/optimal_sensitivity/reoptimized_finite_difference/{i}') for i,r in enumerate(rows)],
        dominant_constraints=value.get('summary',{}).get('dominant_constraints'),
        scope=value['model_scope'],strict_gradient='unavailable',cost=value.get('computation_cost'),
        unsupported_inferences=value['unsupported_inferences']+[
            'Shortening length necessarily improves holding speed.',
            'Numerically flat modulus means stiffness has no physical effect.'],
        physical_failure_relation=dict(status='not_assessed',reason='No aligned physical evidence assessed in this numerical kernel.'),
        unresolved=['General near-optimal dual-face extrema may be unresolved; inspect each status.',
            'Finite differences do not establish a strict gradient or nonlinear performance.'],
        detail_pointer='/optimal_sensitivity',reason=value.get('reason'))


def populate_sensitivity(mathematics, value, reference):
    from schemas.research_reporting import EvidenceLocation, MathematicalQuantity
    quantities=[MathematicalQuantity(name='reoptimized_finite_difference_'+str(i),value=r['reoptimized'],
        status='unverified_estimate',unit='score/'+value['parameter_units'],
        structural_parameters=[value['parameter_identity']['path']],control_reoptimization='required',
        source=EvidenceLocation(reference=reference,pointer=f'/optimal_sensitivity/reoptimized_finite_difference/{i}/reoptimized'))
        for i,r in enumerate(value.get('reoptimized_finite_difference',[]))]
    return mathematics.model_copy(update=dict(quantities=quantities,
        problem_definition=EvidenceLocation(reference=reference,pointer='/optimal_sensitivity/parameter_identity')))
