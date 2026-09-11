"""Evidence-level observations, never automatic causal rules or reusable skills."""
from typing import Literal
from pydantic import Field, JsonValue
from schemas.common import Contract
from schemas.evidence import ArtifactReference, Identifier
from schemas.trace import Actor


class Observation(Contract):
    evidence: ArtifactReference
    value: JsonValue
    description: str = Field(min_length=1, max_length=512)


class CandidateFinding(Contract):
    finding_id: Identifier
    title: str = Field(min_length=1, max_length=256)
    category: Literal["MODEL_SIM_COMPARISON", "ACTUATION", "NUMERICS", "SOFTWARE", "TASK_OUTCOME"]
    observation: tuple[Observation, ...] = Field(min_length=1, max_length=32)
    conditions: dict[str, str]
    evidence_refs: tuple[ArtifactReference, ...] = Field(min_length=1)
    source_runs: tuple[Identifier, ...] = Field(min_length=1)
    ruled_out: tuple[Observation, ...] = ()
    unresolved: tuple[str, ...] = Field(min_length=1)
    causal_attribution: Literal["UNKNOWN"] = "UNKNOWN"
    status: Literal["observed", "under_review", "rejected"] = "observed"
    confidence: Literal["observation_only"] = "observation_only"
    created_by: Actor
