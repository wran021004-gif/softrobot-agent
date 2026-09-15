from typing import Literal
from pydantic import Field
from schemas.common import Contract
from schemas.platform import EvidenceRef, Signal, Payload, EvaluationResult, BackendResult, WorkerOutput, MemoryEntry, WorkOrder
from schemas.design_spec import DesignSpec
from schemas.robot_ir import RobotIR
from schemas.exploration import ExplorationControl


class Empty(Contract):
    pass


class ReachGoal(Contract):
    target_m: tuple[float, float, float]


class ReachEvaluation(Contract):
    tolerance_m: float = Field(gt=0)


class HoldGoal(Contract):
    length_m: float = Field(gt=0)


class HoldEvaluation(Contract):
    max_deviation_m: float = Field(gt=0)


class ReferenceEnvironment(Contract):
    environment_id: str
    gravity_m_s2: tuple[Literal[0.0], Literal[0.0], Literal[0.0]]
    objects: list[str] = Field(max_length=0)
    source: str


class ReferenceRobot(Contract):
    length_m: float = Field(gt=0)
    response_fraction: float = Field(gt=0, le=1)
    model_identity: Literal['discrete_length_response_fixture']


class InitialParameters(Contract):
    length_m: float = Field(gt=0)
    jitter_m: float = Field(default=0, ge=0)


class InitialState(Contract):
    length_m: float = Field(gt=0)
    velocity_m_s: Literal[0.0] = 0.0
    seed: int


class LegacyInitial(Contract):
    mode: Literal['compiled_default_qpos_zero_qvel'] = 'compiled_default_qpos_zero_qvel'
    seed: int


class ReferenceData(Contract):
    steps: int
    kind: Literal['synthetic_reference'] = 'synthetic_reference'
    controller_state: Payload


class LegacyData(Contract):
    backend: str
    original: dict
    exported_files: list[str]
    kind: Literal['real_backend'] = 'real_backend'


class LengthControl(Contract):
    command_m: float = Field(gt=0)


class ControlState(Contract):
    steps: int = Field(ge=0)
    lifecycle: Literal['created', 'running', 'finished', 'aborted']


class ControlOutput(Contract):
    channel: Literal['tendon_target_lengths_m']
    values_m: list[float]


class ScalarSearch(Contract):
    parameter: Literal['controller.command_m'] = 'controller.command_m'
    candidates: list[float] = Field(min_length=1)


class SearchState(Contract):
    index: int = Field(ge=0)
    scores: list[float | None]
    rng_state: list[int] | None = None


class Simulate(Contract):
    candidate_id: str = 'baseline'
    changes: dict[str, float] = Field(default_factory=dict)


class Evaluate(Contract):
    result: EvidenceRef


class ReadEvidence(Contract):
    reference: EvidenceRef
    pointer: str = ''
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class EvidencePage(Contract):
    source: EvidenceRef
    pointer: str
    content: object
    next_offset: int | None


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


class WorkerParameters(Contract):
    signal: str
    delay_s: float = Field(default=0.1, ge=0, le=5)
    inject: Literal['none', 'failure', 'conflict'] = 'none'


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


class MathNorm(Contract):
    values_m: list[float] = Field(min_length=1)
    frame: Literal['world'] = 'world'
    model_id: Literal['euclidean_vector'] = 'euclidean_vector'


class MathNormResult(Contract):
    norm_m: float
    units: Literal['m'] = 'm'
    frame: Literal['world'] = 'world'
    scope: Literal['mathematical_vector_only'] = 'mathematical_vector_only'
