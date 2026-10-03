"""Versioned model-facing input; materializes existing diagnostic contracts."""
from typing import Literal
from pydantic import Field, create_model
from schemas.common import Contract
from schemas.platform_handoff import InventoryDiagnosisSubmission, WorkflowDesignResponse, Recommendation, InventoryGap
from schemas.platform_diagnostics import DiagnosticReport, DiagnosticFact
from schemas.platform import EvidenceRef


class RevisionFact(Contract):
    fact_id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    references: list[str] = Field(min_length=1)


class AssessmentChange(Contract):
    kind: Literal['hypothesis', 'recommendation']
    identifier: str
    disposition: Literal['retained', 'weakened', 'rejected', 'unresolved']
    supporting_fact_ids: list[str] = Field(min_length=1, description='Report fact_id values (inherited or declared in new_facts), not F evidence aliases.')
    reason: str = Field(min_length=1)


class CompactRevision(Contract):
    changes: list[AssessmentChange] = Field(min_length=1)
    new_facts: list[RevisionFact] = Field(min_length=1, max_length=6)
    new_limitations: list[str] = Field(default_factory=list)
    recommendation: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class CheckedRevision(CompactRevision):
    """Host binds result IDs/coverage; author interprets the declared distinction."""
    result_interpretation: str = Field(min_length=1)
    expected_observations_interpretation: str = Field(min_length=1)
    remaining_uncertainty: list[str] = Field(min_length=1)
    resolving_evidence: list[str] = Field(min_length=1)


class FieldCorrection(Contract):
    operation: Literal['replace', 'remove'] = 'replace'
    path: str = Field(description='Exact existing-field JSON pointer relative to draft.arguments, e.g. /new_facts/0/references. The explicit draft-root spelling /arguments/new_facts/0/references is also supported. No guessed paths.')
    value: object = None


class Corrections(Contract):
    corrections: list[FieldCorrection] = Field(min_length=1, max_length=20)


class FinalDesignResponse(WorkflowDesignResponse):
    candidate_disposition: Literal['adopt_candidate', 'retain_baseline', 'defer_selection', 'reject_all']
    selected_candidate: dict | None
    feedback: EvidenceRef


class WireFinalDecision(Contract):
    disposition: Literal['adopt', 'defer', 'reject']
    recommendation_id: str | None = None
    reasoning: str = Field(min_length=1)
    next_action: Literal['finish']
    candidate_disposition: Literal['adopt_candidate', 'retain_baseline', 'defer_selection', 'reject_all']
    selected_candidate: Literal['baseline', 'candidate', 'none']


def without(schema, fields, **replacements):
    return create_model('Wire'+schema.__name__, __base__=Contract, **{
        **{k:(f.annotation, f) for k,f in schema.model_fields.items() if k not in fields}, **replacements})


WireFact=without(DiagnosticFact, {'evidence','observed'})
WireReport=without(DiagnosticReport, {'source','gates','facts'}, facts=(list[WireFact], Field(default_factory=list)))
WireRecommendation=without(Recommendation, {'configuration_scope'})
WireSubmission=without(InventoryDiagnosisSubmission, {'previous_report','request','check_results','report','fact_selectors','recommendations'},
    report=(WireReport,...), fact_handles=(dict[str,list[str]],...), recommendations=(list[WireRecommendation],...))
