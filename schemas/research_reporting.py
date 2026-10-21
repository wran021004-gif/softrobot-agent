"""Derived research reports, not evaluator receipts or mathematical certificates.

Existing EvidenceSummary and ScopedMathematicalClaim remain the scope owners.
Construction validates shape and provenance, never the truth of free text.
"""
from typing import Literal
from pydantic import Field, FiniteFloat, JsonValue, model_validator
from schemas.common import Contract
from schemas.platform import EvidenceRef
from schemas.platform_analysis import ScopedMathematicalClaim
from tools.research.contracts import EvidenceSummary


class EvidenceLocation(Contract):
    reference: EvidenceRef
    pointer: str = Field(default='', pattern=r'^(?:/(?:[^~/]|~[01])*)*$')


class RecordedField(Contract):
    name: str
    value: JsonValue
    source: EvidenceLocation


class ResultIdentity(Contract):
    result: EvidenceLocation
    study: str | None = None
    task_identity: str | None = None
    canonical_task_identity: str | None = None
    design_identity: str | None = None
    evaluation_profile_identity: str | None = None
    candidate: EvidenceRef | None = None
    control_source: EvidenceRef | None = None
    operation: str | None = None
    model_identity: str | None = None
    evaluation_identity: str | None = None


class ReportedMetric(Contract):
    name: str
    value: FiniteFloat | list[FiniteFloat] | None
    unit: str | None = None
    threshold: FiniteFloat | list[FiniteFloat] | None = None
    threshold_source: EvidenceLocation | None = None
    passed: bool | None = None
    scope: Literal['physical_task', 'model_sample', 'solver', 'search_ranking']
    source: EvidenceLocation
    time_s: FiniteFloat | None = None
    window_s: tuple[FiniteFloat, FiniteFloat] | None = None
    conditions: list[RecordedField] = Field(default_factory=list)


class ResourceUse(Contract):
    name: str
    amount: FiniteFloat | None = Field(default=None, ge=0)
    unit: str
    time_basis: Literal['worker_wall', 'parent_action_wall', 'cpu', 'recorded_elapsed_unspecified'] | None = None
    source: EvidenceLocation | None = None

    @model_validator(mode='after')
    def known_cost_has_source(self):
        if self.amount is not None and self.source is None:
            raise ValueError('KNOWN_COST_REQUIRES_SOURCE')
        if self.unit == 's' and self.time_basis is None:
            raise ValueError('TIME_BASIS_REQUIRED')
        return self


class MathematicalQuantity(Contract):
    """B-line output slot; unavailable is not a zero or a verified bound."""
    name: str
    status: Literal['verified', 'unverified_estimate', 'unavailable'] = 'unavailable'
    value: FiniteFloat | list[FiniteFloat] | None = None
    unit: str | None = None
    source: EvidenceLocation | None = None
    structural_parameters: list[str] = Field(default_factory=list)
    control_reoptimization: Literal['required', 'fixed_control', 'not_assessed'] = 'not_assessed'
    conditions: list[RecordedField] = Field(default_factory=list)

    @model_validator(mode='after')
    def availability(self):
        if self.status == 'unavailable':
            if self.value is not None:
                raise ValueError('UNAVAILABLE_QUANTITY_HAS_NO_VALUE')
        elif self.value is None or self.source is None:
            raise ValueError('AVAILABLE_QUANTITY_REQUIRES_VALUE_AND_SOURCE')
        return self


class MathematicalEvidence(Contract):
    claim: ScopedMathematicalClaim
    claim_source: EvidenceLocation
    # Point to the existing TaskAnalysisRequirement; do not define another task.
    requirement_source: EvidenceLocation | None = None
    problem_definition: EvidenceLocation | None = None
    quantities: list[MathematicalQuantity] = Field(default_factory=list)


class ControlSearchStep(Contract):
    label: str
    source: EvidenceLocation
    evaluation: EvidenceRef
    candidate: EvidenceRef | None = None
    control_source: EvidenceRef | None = None
    prediction_base: EvidenceRef | None = None
    predicted_improvement: FiniteFloat | None = None
    actual_improvement: FiniteFloat | None = None
    # Exact recorded ranking, never an independent acceptance decision.
    task_gap: dict
    metrics: list[ReportedMetric] = Field(default_factory=list)


class ControlSearchEvidence(Contract):
    stop_reason: RecordedField | None = None
    baselines: list[ControlSearchStep] = Field(default_factory=list)
    proposals: list[ControlSearchStep] = Field(default_factory=list)
    best: ControlSearchStep | None = None
    all_steps: EvidenceLocation


class CriticalObservation(Contract):
    time_s: FiniteFloat
    observed: dict
    source: EvidenceLocation
    input_source: EvidenceLocation | None = None


class ResultCard(Contract):
    version: Literal['scientific_result_card_v1'] = 'scientific_result_card_v1'
    identity: ResultIdentity
    evidence_summary: EvidenceSummary
    # Configuration/purpose/deltas are recorded fields or exact detail links.
    recorded_context: list[RecordedField] = Field(default_factory=list)
    metrics: list[ReportedMetric] = Field(default_factory=list)
    main_violations: list[str] = Field(default_factory=list)
    critical_observations: list[CriticalObservation] = Field(default_factory=list)
    deterministic_summary: dict = Field(default_factory=dict)
    mathematics: MathematicalEvidence | None = None
    control_search: ControlSearchEvidence | None = None
    resources: list[ResourceUse] = Field(default_factory=list)
    detail_sources: list[EvidenceLocation] = Field(default_factory=list)
    authoritative_scientific_evidence: Literal[False] = False


class EvidenceRelation(Contract):
    """Declared comparison inputs; F0 does not compute diagnostic relations."""
    kind: Literal['same_structure_controls', 'structures', 'model_physics', 'solver_task_acceptance']
    left: ResultIdentity
    right: ResultIdentity
    comparable: bool | None = None
    reasons: list[str] = Field(default_factory=list)
    changed_factors: list[Literal['structure', 'control', 'model', 'task', 'evaluator', 'solver']] = Field(default_factory=list)
    single_factor_attribution: str | None = None
    sources: list[EvidenceLocation] = Field(min_length=1)

    @model_validator(mode='after')
    def comparison_scope(self):
        if self.comparable is not True and not self.reasons:
            raise ValueError('UNKNOWN_OR_INCOMPARABLE_RELATION_REQUIRES_REASONS')
        if self.single_factor_attribution is not None and (
                self.comparable is not True or len(set(self.changed_factors)) != 1):
            raise ValueError('SINGLE_FACTOR_ATTRIBUTION_REQUIRES_ONE_DECLARED_CHANGED_FACTOR')
        return self


class ReporterInterpretation(Contract):
    """Non-authoritative prose, never a scientific action or registration input."""
    kind: Literal['new_information', 'supported_explanation', 'weakened_explanation',
                  'unresolved_question', 'further_investigation', 'hypothesis']
    text: str
    sources: list[EvidenceLocation] = Field(default_factory=list)
    status: Literal['reporter_interpretation'] = 'reporter_interpretation'


class ScientificReport(Contract):
    version: Literal['scientific_report_v1'] = 'scientific_report_v1'
    mode: Literal['result_summary', 'investigation']
    question: str | None = None
    results: list[ResultCard] = Field(min_length=1)
    relations: list[EvidenceRelation] = Field(default_factory=list)
    interpretations: list[ReporterInterpretation] = Field(default_factory=list)
    authoritative_scientific_evidence: Literal[False] = False

    @model_validator(mode='after')
    def report_mode(self):
        if self.mode == 'investigation' and not (self.question and self.question.strip()):
            raise ValueError('INVESTIGATION_REQUIRES_QUESTION')
        if self.mode == 'result_summary' and len(self.results) != 1:
            raise ValueError('RESULT_SUMMARY_REQUIRES_ONE_RESULT')
        return self
