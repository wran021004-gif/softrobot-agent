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


class WorkerParameters(Contract):
    signal: str
    delay_s: float = Field(default=0.1, ge=0, le=5)
    inject: Literal['none', 'failure', 'conflict'] = 'none'


class MathNorm(Contract):
    values_m: list[float] = Field(min_length=1)
    frame: Literal['world'] = 'world'
    model_id: Literal['euclidean_vector'] = 'euclidean_vector'


class MathNormResult(Contract):
    norm_m: float
    units: Literal['m'] = 'm'
    frame: Literal['world'] = 'world'
    scope: Literal['mathematical_vector_only'] = 'mathematical_vector_only'

from schemas.platform_operations import *
