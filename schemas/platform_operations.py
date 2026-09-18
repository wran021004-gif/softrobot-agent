"""Common registered operation contracts; versioned independently of examples."""
from typing import Literal
from pydantic import Field
from schemas.common import Contract
from schemas.platform import EvidenceRef, MemoryEntry, WorkOrder

class Simulate(Contract):
    candidate_id: str = Field(default='baseline', description='Candidate label bound to the frozen effective configuration and execution receipt.')
    changes: dict[str, object] = Field(default_factory=dict, description='Authorized edits to this session baseline; empty preserves its configuration. One charged backend attempt; does not evaluate.')


class Evaluate(Contract):
    result: EvidenceRef = Field(description='Existing saved simulation result reference from this session; no new solve.')
    execution_id: str | None = Field(default=None, description='Simulation execution identity; required when the saved artifact has multiple executions.')


class ReadEvidence(Contract):
    reference: EvidenceRef = Field(description='Existing immutable evidence reference, not a node_id. A build has no evaluation or trajectory to read.')
    pointer: str = Field(default='', description='JSON Pointer into original evidence, e.g. /detail or /signals/0/values. Empty reads the root. Oversized nested content returns a labeled overview with valid child pointers; follow those pointers using the same source reference.')
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)
    byte_limit: int = Field(default=4096, ge=128, le=8192, description='Requested content byte cap; response and observation envelopes also count toward the inline limit. Pages may be smaller. Follow next_offset at the same pointer.')


class EvidencePage(Contract):
    source: EvidenceRef
    pointer: str
    content: object
    next_offset: int | None
    kind: Literal['content','overview'] = 'content'
    offset: int = 0
    total_items: int = 0
    returned_items: int = 0
    presentation: Literal['original','english_projection'] = 'original'


class DiagnosticQuery(Contract):
    result: EvidenceRef
    signal: str
    threshold: float
    units: str


class DiagnosticResult(Contract):
    status: Literal['events_found', 'no_event', 'missing_data', 'not_applicable', 'execution_failed']
    source: EvidenceRef
    signal: str
    sample_indices: list[int]
    observed: list[list[float]]
    rule: Literal['sample_exceeds@1.0.0'] = 'sample_exceeds@1.0.0'
    causal_hypothesis: None = None
    rescoring: Literal[False] = False


class MemoryQuery(Contract):
    task_family: str | None = None
    task_version: str | None = None
    backend: str | None = None
    model_id: str | None = None
    failure_category: str | None = None
    tags: list[str] = Field(default_factory=list)


class MemoryResults(Contract):
    entries: list[MemoryEntry]


class MemorySave(Contract):
    entry: MemoryEntry


class SavedMemory(Contract):
    entry: MemoryEntry


class Stop(Contract):
    status: Literal['stopped', 'paused', 'needs_input', 'capability_missing', 'failed']
    reason: str = Field(min_length=1)


class Stopped(Contract):
    status: str
    reason: str



class SubmitWork(Contract):
    order: WorkOrder


class WorkQuery(Contract):
    work_id: str


class WorkStatus(Contract):
    work_id: str
    status: str
    result: EvidenceRef | None = None
    reason: str | None = None


class SkillQuery(Contract):
    reference: str | None = None


class SkillRecords(Contract):
    skills: list[dict]
    classification: Literal['guidance_strategy'] = 'guidance_strategy'


from schemas.skill import Skill, SkillValidationRecord


class SkillProposal(Contract):
    skill: Skill


class SkillValidation(Contract):
    reference: str
    record: SkillValidationRecord


class ServiceData(Contract):
    """Legacy services retain their own registered output validator when present."""
    detail: dict


