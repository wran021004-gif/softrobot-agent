"""Future cross-run index entry. No storage, trace copy, or embedded skill."""
from pydantic import Field
from schemas.common import Contract
from schemas.evidence import ArtifactReference, Identifier


class MemoryRecord(Contract):
    run_id: Identifier
    summary: str = Field(min_length=1, max_length=1000)
    searchable_metadata: dict[str, str] = Field(max_length=16)
    evidence_refs: tuple[ArtifactReference, ...] = Field(min_length=1, max_length=32)
