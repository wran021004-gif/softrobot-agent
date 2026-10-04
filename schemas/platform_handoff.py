"""Optional sequential diagnostic handoffs; recommendations confer no authority."""
from typing import Literal, Annotated
from pydantic import Field, model_validator
from schemas.common import Contract
from schemas.platform import EvidenceRef, Budget
from schemas.platform_diagnostics import DiagnosticReport


class SavedStateScope(Contract):
    """Explicit numerical authorization, separate from retained-evidence reading."""
    operations: list[Literal['prediction_braking', 'local_comparison']] = Field(min_length=1)
    model: Literal['model.gvs@1.0.0'] = 'model.gvs@1.0.0'
    horizon_s: float = Field(gt=0, le=.02)
    integration: Literal['implicit_euler'] = 'implicit_euler'
    integration_step_s: float = Field(gt=0, le=.01)
    max_wall_s: float = Field(gt=0, le=300.)
    max_checks: Literal[1] = 1
    numerical_limits: dict[Literal['local_solves', 'prediction_evaluations'], int] = Field(
        description='Maximum numerical units within this request; bounded by the frozen project grant.')
    configuration_scope: Literal['saved_state_or_temporary_analysis'] = 'saved_state_or_temporary_analysis'


class DiagnosisRequest(Contract):
    question: str = Field(min_length=1)
    subject: str
    binding: EvidenceRef
    candidate_id: str
    execution_id: str
    task_identity: str
    controller_identity: str
    evidence_manifest: EvidenceRef
    permitted_tools: list[str]
    scope: list[str] = Field(description='Distinguish retained-evidence reads, explicitly authorized saved-state numerical work, and excluded production changes/backend execution.')
    saved_state_check: SavedStateScope | None = Field(default=None,
        description='Explicit saved-state numerical grant bound to this request execution and binding. Null authorizes no numerical execution. Probes never modify production or baseline; local_comparison additionally requires matched design adoption.')
    budget: Budget
    stopping_conditions: list[str] = Field(min_length=1)


class EvidenceSelector(Contract):
    reference: EvidenceRef
    pointer: str
    value: object


class DiagnosticCheckRequest(Contract):
    check_id: str | None = None
    operation: Literal['prediction_braking','local_comparison'] | None = None
    update_id: int | None = Field(default=None, ge=1)
    integration_step_s: float = Field(default=.002, gt=0, le=.01)
    changed_parameter: Literal['terminal_tip_speed_weight','holding_tip_speed_weight'] | None = None
    changed_value: float | None = Field(default=None, ge=.0001, le=1.)
    prior_result: EvidenceRef | None = None
    additional_need: str | None = None
    diagnosis_request: EvidenceRef
    hypotheses: list[str] = Field(min_length=2)
    initial_state: EvidenceSelector
    input: EvidenceSelector
    fixed_conditions: list[str] = Field(min_length=1)
    changed_factor: str | None = None
    model: str
    horizon_s: float = Field(gt=0, le=.1)
    integration: str
    metrics: list[str]
    work_limits: dict[str, float]
    acceptance_criteria: list[str] = Field(min_length=1)


class Recommendation(Contract):
    recommendation_id: str
    action: Literal['control_parameter', 'defer']
    parameter: str | None = None
    value: float | None = None
    rationale: str
    configuration_scope: EvidenceRef


class DiagnosisSubmission(Contract):
    previous_report: EvidenceRef | None = None
    request: EvidenceRef
    report: DiagnosticReport
    fact_selectors: dict[str, list[EvidenceSelector]]
    missing_evidence: list[str]
    check_results: list[EvidenceRef] = Field(default_factory=list)
    recommendations: list[Recommendation]


class InventoryGap(Contract):
    inventory_id: str | None = None
    source: str | None = Field(default=None, description='For unlisted evidence, identify the source or evidence sought.')
    status: Literal['not_displayed', 'not_read', 'queried', 'not_retained', 'retained_unavailable', 'capability_unavailable', 'execution_unauthorized']
    needed: str = Field(min_length=1, description='Specific missing information or query/calculation capability.')
    basis: str = Field(min_length=1, description='Inventory fact or explicit basis for unlisted evidence; no invented inventory ID.')
    update_ids: list[Annotated[int, Field(ge=0)]] | None = Field(default=None, min_length=1, max_length=35,
        description='Optional explicit subset of controller update IDs. Without coverage fields status applies to the entire inventory entry; describe remaining coverage in needed/basis.')
    time_range_s: list[float] | None = Field(default=None, min_length=2, max_length=2,
        description='Optional inclusive sampled backend-motion time range [start,end]. This is sampled coverage, not a continuous-time claim.')

    @model_validator(mode='after')
    def coverage_scope(self):
        if self.update_ids is not None and self.time_range_s is not None:
            raise ValueError('Choose update_ids or time_range_s, not both')
        if self.time_range_s is not None and self.time_range_s[0]>self.time_range_s[1]:
            raise ValueError('time_range_s requires start <= end')
        return self


class InventoryDiagnosisSubmission(DiagnosisSubmission):
    """Version 2 makes availability declarations reference deterministic inventory."""
    missing_evidence: list[InventoryGap]


class ScopedDiagnosticCheckRequest(DiagnosticCheckRequest):
    """Version 2 requires a question that the existing local probe can answer."""
    local_question: str = Field(min_length=1)
    discriminating_observations: list[str] = Field(min_length=1)
    unresolved: list[str] = Field(min_length=1, description='Hypotheses this probe cannot separate, and limits independent of outcome.')


class DesignResponse(Contract):
    report: EvidenceRef
    disposition: Literal['adopt', 'defer', 'reject'] = Field(description='adopt accepts the named recommendation within its permitted scope; defer postpones pending evidence; reject declines. This does not decide diagnostic continuation.')
    recommendation_id: str | None = Field(default=None, description='An existing report recommendation ID; required for adoption.')
    reasoning: str
    next_action: Literal['bounded_verification', 'stop'] = Field(description='defer/reject requires stop. bounded_verification requires adopt and a named recommendation. stop declines recommendation verification, not the independently authorized diagnostic check phase. Adoption records intent and does not execute a backend comparison.')


class HandoffResult(Contract):
    reference: EvidenceRef
    status: str


class WorkflowDesignResponse(Contract):
    """Version 2: recommendation disposition and workflow control are independent."""
    report: EvidenceRef
    disposition: Literal['adopt', 'defer', 'reject']
    recommendation_id: str | None = None
    reasoning: str = Field(min_length=1)
    next_action: Literal['request_check', 'verify_adopted_change', 'finish']


class DiagnosticReview(Contract):
    response: EvidenceRef
    verification: EvidenceRef
    improvement_supported: bool
    adopt_into_baseline: bool
    reasoning: str
    unresolved: list[str]
    next_parameter_group: str
    prerequisites: list[str]


class AssessmentEvidence(Contract):
    assessment_id: str = Field(min_length=1)
    relationship: Literal['supporting', 'contradicting']
    references: list[str] = Field(min_length=1, description='Exact current-context F aliases.')
    relevance: str = Field(min_length=1)


class ExpectedObservation(Contract):
    assessment_id: str = Field(min_length=1)
    observation: str = Field(min_length=1)
    effect: Literal['retain', 'weaken', 'reject', 'unresolved']


class CheckProposal(Contract):
    """Recorded before a retained-evidence query or the existing numerical request."""
    contract: Literal['platform.diagnostic_check_proposal'] = 'platform.diagnostic_check_proposal'
    version: Literal['1.0.0'] = '1.0.0'
    question: str = Field(min_length=1)
    assessment_ids: list[str] = Field(min_length=1)
    relationships: list[AssessmentEvidence] = Field(min_length=1)
    missing_information: list[str] = Field(min_length=1)
    operation: Literal['evidence_query', 'prediction_braking', 'local_comparison']
    view: Literal['prediction', 'plans', 'motion'] | None = None
    update_ids: list[int] = Field(default_factory=list, max_length=8)
    units: list[str] = Field(min_length=1)
    expected: list[ExpectedObservation] = Field(min_length=1)
    distinguishes: str = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)
    work_limits: dict[str, float]
    stopping_conditions: list[str] = Field(min_length=1)
    changed_parameter: Literal['terminal_tip_speed_weight', 'holding_tip_speed_weight'] | None = None
    changed_value: float | None = Field(default=None, ge=.0001, le=1.)


class SearchBatchPlan(Contract):
    contract: Literal['platform.search_batch_plan'] = 'platform.search_batch_plan'
    version: Literal['1.0.0'] = '1.0.0'
    hypothesis: str = Field(min_length=1)
    evidence: list[str] = Field(min_length=1, description='Exact current F aliases only, including at least one performed-check result alias. Put explanations in rationale.')
    weakening_observations: list[str] = Field(min_length=1)
    variables: dict[str, list[float]] = Field(description='Exact builder paths mapped to [lower, upper] numeric bounds.')
    fixed_conditions: list[str] = Field(min_length=1, description='Bare identifiers: robot, task, acceptance, controller_implementation, other_numerical_settings. Put descriptions in rationale, not in these identifiers.')
    fixed_controller: str = Field(description='Exact extension_id@version, fixed implementation.')
    objectives: list[str] = Field(min_length=1)
    constraints: list[str] = Field(min_length=1)
    method: str = Field(description='Registered search extension_id@version.')
    max_candidates: int = Field(ge=1, le=12)
    max_backend_attempts: int | None = Field(default=None,ge=1,le=12,
        description='Separate new full backend attempt cap. Omitted legacy plans retain backend_solves=max_candidates.')
    target_changed_configurations: int | None = Field(default=None,ge=1,le=12,
        description='Stop normally after this many distinct changed configurations have complete evaluation and profile.')
    failure_policy: Literal['stop_on_material_failure'] = 'stop_on_material_failure'
    step: float = Field(gt=0, le=1)
    planned_budget: Budget
    fidelity_limits: list[str] = Field(min_length=1)
    verification: list[str] = Field(min_length=1)
    stopping_conditions: list[str] = Field(min_length=1)
    scientific_promise: Literal['promising', 'uncertain', 'unlikely']
    rationale: str = Field(min_length=1)
