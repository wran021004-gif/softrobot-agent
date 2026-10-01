"""Optional sequential diagnostic handoffs; recommendations confer no authority."""
from typing import Literal
from pydantic import Field
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


class DesignResponse(Contract):
    report: EvidenceRef
    disposition: Literal['adopt', 'defer', 'reject'] = Field(description='adopt accepts the named recommendation within its permitted scope; defer postpones pending evidence; reject declines. This does not decide diagnostic continuation.')
    recommendation_id: str | None = Field(default=None, description='An existing report recommendation ID; required for adoption.')
    reasoning: str
    next_action: Literal['bounded_verification', 'stop'] = Field(description='defer/reject requires stop. bounded_verification requires adopt and a named recommendation. stop declines recommendation verification, not the independently authorized diagnostic check phase. Adoption records intent and does not execute a backend comparison.')


class HandoffResult(Contract):
    reference: EvidenceRef
    status: str


class DiagnosticReview(Contract):
    response: EvidenceRef
    verification: EvidenceRef
    improvement_supported: bool
    adopt_into_baseline: bool
    reasoning: str
    unresolved: list[str]
    next_parameter_group: str
    prerequisites: list[str]
