"""Portable deterministic facts and evidence-based attribution, across domains."""
from typing import Literal
from pydantic import Field, model_validator
from schemas.common import Contract
from schemas.evidence import Identifier
from schemas.platform import EvidenceRef, Metric, Payload


class GateResult(Contract):
    """Failed means observed failure; ungradable means insufficient usable evidence.

    Missing/nonfinite measurements are never fabricated as numeric zero. A
    registered observation payload can describe nonfiniteness without JSON NaN.
    """
    gate_id: Identifier
    status: Literal['passed', 'failed', 'ungradable']
    evidence: list[EvidenceRef] = Field(default_factory=list)
    observed: Metric | Payload | EvidenceRef | None = None
    expected: Metric | Payload | EvidenceRef | None = None
    reason: str | None = None


class DiagnosticFact(Contract):
    """Produced by deterministic tools; statements report observations, not causes."""
    fact_id: Identifier
    statement: str = Field(min_length=1)
    evidence: list[EvidenceRef] = Field(min_length=1)
    observed: Metric | Payload | EvidenceRef | None = None


class DiagnosticAttribution(Contract):
    """Reasoning over facts; ruled_out is explicit, not a missing hypothesis."""
    cause: Identifier
    status: Literal['supported', 'possible', 'insufficient_evidence', 'ruled_out']
    fact_ids: list[Identifier] = Field(default_factory=list)
    reason: str = Field(min_length=1)


class DiagnosticReport(Contract):
    """Persistable handoff; facts remain distinct from LLM/human attribution.

    subject is an extensible category, source identifies the diagnosed artifact.
    Recommendations are advisory text, never executable actions or authorization.
    """
    subject: Identifier
    source: EvidenceRef
    facts: list[DiagnosticFact] = Field(default_factory=list)
    attribution: list[DiagnosticAttribution] = Field(default_factory=list)
    gates: list[GateResult | EvidenceRef] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def fact_references(self):
        ids = {fact.fact_id for fact in self.facts}
        if len(ids) != len(self.facts):
            raise ValueError('DUPLICATE_DIAGNOSTIC_FACT')
        for attribution in self.attribution:
            if set(attribution.fact_ids) - ids:
                raise ValueError('DIAGNOSTIC_FACT_NOT_DECLARED')
        return self
