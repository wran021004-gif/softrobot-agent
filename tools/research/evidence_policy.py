"""Deterministic evidence scopes. Inputs must be resolved trusted tool artifacts.

No category orders global credibility; none certifies an unvisited physical
candidate. Policy checks are not resource grants or replacements for acceptance.
"""
from copy import deepcopy
import math
from tools.research.contracts import EvidenceSummary
from tools.research.feedback import task_gap
from tools.platform_store import plain

FORBIDDEN=['global_nonlinear_feasibility','global_nonlinear_infeasibility',
    'structural_infeasibility','whole_horizon_from_instantaneous_braking',
    'adapted_dynamic_improvement_from_static_sensitivity','unvisited_simulation_descent_guarantee',
    'continuous_time_compliance','hardware_performance','robustness','repeatability']
HYPOTHESES={
    'CONTROL_SEARCH_INCOMPLETE':(['PHYSICAL_OBSERVATION','NUMERICAL_DIAGNOSTIC'],
        ['additional_bounded_starts','paired_control_search'], 'Only searched starts, controls and budgets.'),
    'MODEL_PREDICTION_UNRELIABLE':(['EMPIRICAL_COMPARISON','NUMERICAL_DIAGNOSTIC'],
        ['aligned_model_physics_pairs','fixed_input_grid_refinement'], 'Only checked operating points and input sequences.'),
    'CONTROL_PARAMETERIZATION_LIMITED':(['PHYSICAL_OBSERVATION','EMPIRICAL_COMPARISON'],
        ['paired_basis_comparison_with_equal_budget'], 'Only declared bases and coefficient domains.'),
    'DESIGN_LIMITATION_POSSIBLE':(['MODEL_EXCLUSION','EMPIRICAL_COMPARISON'],
        ['paired_designs_with_equal_control_adaptation'], 'Only tested designs; a local model exclusion is not physical exclusion.'),
    'SOLVER_OR_NUMERICAL_ISSUE':(['NUMERICAL_DIAGNOSTIC'],
        ['derivative_checks','same_input_refinement','alternative_initialization'], 'Only measured solver/model/grid conditions.')}


def hypothesis_catalog():
    return {name:dict(claim_kind='UNVERIFIED_HYPOTHESIS',acceptable_evidence=kinds,
        discriminating_experiments=checks,forbidden_inferences=FORBIDDEN+['identified_root_cause'],
        scope=scope,probability=None) for name,(kinds,checks,scope) in HYPOTHESES.items()}


def _pointer_exists(value,pointer):
    if not pointer.startswith('/'):return False
    try:
        for part in pointer[1:].split('/'):
            key=part.replace('~1','/').replace('~0','~')
            value=value[int(key)] if isinstance(value,list) else value[key]
        return value is not None
    except (KeyError,IndexError,ValueError,TypeError):return False


def summarize_evidence(value,reference=None,*,refinement=None):
    """Add a view without rewriting a sealed scoped_claim or raw result.

    Existing deterministic scoped verification remains authoritative. Conflicting
    independent refinement downgrades the new view, not the historical record.
    """
    claim=value.get('scoped_claim') or {};binding=claim.get('binding') or value.get('binding') or {}
    applicability=value.get('analysis_applicability') or {}
    kind='UNVERIFIED_HYPOTHESIS';status='unverified';supported=[];unresolved=[]
    pointer=claim.get('numerical_result_pointer','')
    candidate=value.get('candidate',binding.get('candidate'));task=binding.get('task_identity',value.get('task_identity'))
    model=claim.get('model_identity',value.get('model_identity',value.get('mathematical_model_identity')))
    design=binding.get('physical_design_identity',value.get('design_identity'))
    coverage=dict(horizon=claim.get('horizon',{}),constraints=claim.get('constraint_coverage',[]),
        full_task_supported=applicability.get('full_task_supported',False))
    if claim or any(k in value for k in ('kkt','sensitivity','instantaneous_braking','raw','solver_status')):
        kind='NUMERICAL_DIAGNOSTIC';status=claim.get('verification_status',value.get('status','unverified'))
        supported=['local_diagnostic'];conclusion=claim.get('conclusion')
        verified=bool(reference and model and candidate and task and value.get('status')=='computed'
            and applicability.get('status')!='not_applicable' and _pointer_exists(value,pointer))
        if verified and conclusion=='feasible_witness' and status in (
                'independent_discrete_replay_passed','kernel_independent_checks_passed'):
            kind='MODEL_WITNESS';supported=['model_sampled_feasibility']
        elif verified and conclusion=='model_infeasibility_certificate' and status in (
                'necessary_constraint_box_exclusion_verified','kernel_separating_lower_bound_verified'):
            kind='MODEL_EXCLUSION';supported=['model_input_box_exclusion']
        unresolved+=['Nonlinear realization and constraints outside declared model/sample coverage remain unresolved.']
    if 'acceptance' in value:
        gap=task_gap(value);pointer='/acceptance'
        task=task or value['acceptance'].get('task_identity')
        if reference and candidate and task and gap['valid_complete']:
            kind='PHYSICAL_OBSERVATION';status='complete_registered_execution';supported=['observed_task_outcome']
            if gap['accepted']:supported.append('observed_task_pass')
            coverage=dict(timing=value['acceptance'].get('timing'),
                components=value['acceptance'].get('components'),episodes=value.get('episodes'),
                execution_id=value.get('execution_id'),scope='Only this completed independent execution')
        else:kind='NUMERICAL_DIAGNOSTIC';status='incomplete_or_unbound_execution';supported=['local_diagnostic']
    if refinement is not None and kind in ('MODEL_WITNESS','NUMERICAL_DIAGNOSTIC'):
        if not (refinement.get('complete') is True and refinement.get('original_task_satisfied') is True):
            if kind=='MODEL_WITNESS':kind='NUMERICAL_DIAGNOSTIC';supported=['local_diagnostic']
            status='refinement_failed_or_unverified'
            unresolved.append('Coarse sampled feasibility does not survive or lacks independent finer integration verification.')
    if not reference:
        kind='UNVERIFIED_HYPOTHESIS';status='missing_evidence_reference';supported=[]
    if kind!='PHYSICAL_OBSERVATION':unresolved.append('Original independent physical task acceptance is unmeasured by this evidence.')
    return plain(EvidenceSummary(claim_kind=kind,verification_status=status,model_identity=model,
        candidate_identity=candidate,task_identity=task,design_identity=design,
        operating_point=claim.get('operating_point',value.get('operating_point',{})),covered_samples=coverage,
        assumptions=dict(model=claim.get('model_declaration',{}),physical_inputs=claim.get('physical_inputs',{}),
            legacy_applicability=applicability,source='Trusted resolved tool artifact; not arbitrary LLM assertions'),
        supported_inferences=supported,unsupported_inferences=FORBIDDEN+([] if 'observed_task_pass' in supported else ['observed_task_pass']),
        evidence_reference=reference,numerical_evidence_pointer=pointer,unresolved=unresolved,
        next_checks=['independent_legal_physical_evaluation','matched_input_refinement','paired_local_response_check']))


def paired_evidence(left,right,reference):
    """Only two complete, same-task observations support a paired comparison."""
    a=EvidenceSummary.model_validate(left);b=EvidenceSummary.model_validate(right)
    def protocol(e):return {k:(v.get('limit'),v.get('unit')) for k,v in (e.covered_samples.get('components') or {}).items()}
    comparable=(a.claim_kind==b.claim_kind=='PHYSICAL_OBSERVATION' and a.task_identity is not None and
        a.task_identity==b.task_identity and a.evidence_reference!=b.evidence_reference and
        a.covered_samples.get('timing')==b.covered_samples.get('timing') and
        bool(protocol(a)) and protocol(a)==protocol(b))
    value=deepcopy(left);value.update(claim_kind='EMPIRICAL_COMPARISON',
        verification_status='paired_observations' if comparable else 'incompatible_or_incomplete_pair',
        evidence_reference=reference,candidate_identity={'left':a.candidate_identity,'right':b.candidate_identity},
        covered_samples=dict(left=plain(a.evidence_reference),right=plain(b.evidence_reference)),
        supported_inferences=['paired_observed_difference'] if comparable else [],
        unsupported_inferences=FORBIDDEN+['observed_task_pass','population_superiority'],numerical_evidence_pointer='')
    return plain(EvidenceSummary.model_validate(value))


def statistical_evidence(samples,method,uncertainty,reference):
    """Typed reported statistics; method correctness/population inference unverified."""
    valid=bool(samples and method and uncertainty and reference and all(
        math.isfinite(x) for x in uncertainty.values() if isinstance(x,(int,float))))
    return plain(EvidenceSummary(claim_kind='STATISTICAL_EVIDENCE',verification_status='reported_not_independently_verified',
        evidence_reference=reference,covered_samples=dict(sample_references=samples,count=len(samples)),
        assumptions=dict(method=method,reported_uncertainty=uncertainty),
        supported_inferences=['reported_sample_statistic'] if valid else [],
        unsupported_inferences=FORBIDDEN+['population_superiority','observed_task_pass'],
        unresolved=['Sampling assumptions, dependence and statistical calculation require a dedicated verifier.']))


def check_inference(summary,inference,*,target=None,legal_candidate=False):
    """P3 can call after resolving evidence; existing budgets/Plan guards still apply."""
    evidence=EvidenceSummary.model_validate(summary);reason='unsupported_by_scoped_evidence'
    allowed=inference in evidence.supported_inferences and inference not in evidence.unsupported_inferences
    if inference=='empirical_search':
        return dict(allowed=legal_candidate,reason='Independent legal search needs no model certificate; existing grants still required.')
    if target is not None:
        for key in ('task_identity','candidate_identity','model_identity','design_identity','operating_point','covered_samples'):
            actual=getattr(evidence,key)
            if actual is None or key not in target or actual!=target[key]:
                return dict(allowed=False,reason='evidence_identity_or_scope_mismatch:'+key)
    if allowed:reason='supported_only_within_declared_evidence_scope'
    return dict(allowed=allowed,reason=reason)
