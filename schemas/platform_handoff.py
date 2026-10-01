"""Optional sequential diagnostic handoffs; recommendations confer no authority."""
from typing import Literal
from pydantic import Field
from schemas.common import Contract
from schemas.platform import EvidenceRef, Budget
from schemas.platform_diagnostics import DiagnosticReport


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
    scope: list[str]
    budget: Budget
    stopping_conditions: list[str] = Field(min_length=1)


class EvidenceSelector(Contract):
    reference: EvidenceRef
    pointer: str
    value: object


class DiagnosticCheckRequest(Contract):
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
    request: EvidenceRef
    report: DiagnosticReport
    fact_selectors: dict[str, list[EvidenceSelector]]
    missing_evidence: list[str]
    check_results: list[EvidenceRef] = Field(default_factory=list)
    recommendations: list[Recommendation]


class DesignResponse(Contract):
    report: EvidenceRef
    disposition: Literal['adopt', 'defer', 'reject']
    recommendation_id: str | None = None
    reasoning: str
    next_action: Literal['bounded_verification', 'stop']


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
