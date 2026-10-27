from typing import Literal
from pydantic import Field, FiniteFloat, model_validator
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


class ToolAxisGoal(Contract):
    target_m: tuple[FiniteFloat, FiniteFloat, FiniteFloat]
    axis_local: tuple[FiniteFloat, FiniteFloat, FiniteFloat]
    target_axis_world: tuple[FiniteFloat, FiniteFloat, FiniteFloat]
    frame: Literal['world'] = 'world'
    axis_frame: Literal['tip_site_local'] = 'tip_site_local'

    @model_validator(mode='after')
    def unit_axes(self):
        import math
        if any(abs(math.hypot(*a)-1)>1e-10 for a in (self.axis_local,self.target_axis_world)):
            raise ValueError('EXPLICIT_UNIT_LOCAL_AND_WORLD_TOOL_AXES_REQUIRED')
        return self


class ToolAxisEvaluation(Contract):
    position_tolerance_m: FiniteFloat = Field(gt=0)
    angle_tolerance_rad: FiniteFloat = Field(gt=0,lt=3.141592653589793)


class TrackingGoal(Contract):
    vertices_m: list[tuple[float, float, float]] = Field(min_length=2, max_length=3)
    units: Literal['m'] = 'm'
    frame: Literal['world'] = 'world'
    interpolation: Literal['linear'] = 'linear'
    progression: Literal['ordered_start_to_end'] = 'ordered_start_to_end'
    time_requirement: Literal['none','timed']
    times_s: list[float] | None = None

    @model_validator(mode='after')
    def nodes(self):
        import math
        if self.time_requirement=='timed':
            if (self.times_s is None or len(self.times_s)!=len(self.vertices_m) or self.times_s[0]!=0
                    or any(b<=a for a,b in zip(self.times_s,self.times_s[1:]))):
                raise ValueError('TIMED_TRACKING_REQUIRES_ORDERED_NODE_TIMES_FROM_ZERO')
            return self
        elif self.times_s is not None:raise ValueError('GEOMETRIC_TRACKING_CANNOT_IMPLY_NODE_TIMES')
        legs=[tuple(y-x for x,y in zip(a,b)) for a,b in zip(self.vertices_m,self.vertices_m[1:])]
        if any(math.hypot(*v)==0 for v in legs):raise ValueError('NONZERO_PATH_SEGMENTS_REQUIRED')
        if len(legs)==2:
            a,b=legs;cross=(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
            if sum(x*y for x,y in zip(a,b))<0 and math.hypot(*cross)<=1e-12*math.hypot(*a)*math.hypot(*b):
                raise ValueError('OVERLAPPING_RETURN_PATH_UNSUPPORTED')
        return self

    def at_time(self,time_s):
        from bisect import bisect_right
        if self.time_requirement!='timed':raise ValueError('GEOMETRIC_TRACKING_HAS_NO_TIME_REFERENCE')
        if not 0<=time_s<=self.times_s[-1]:raise ValueError('REFERENCE_TIME_OUTSIDE_HORIZON')
        i=min(bisect_right(self.times_s,time_s)-1,len(self.times_s)-2)
        alpha=(time_s-self.times_s[i])/(self.times_s[i+1]-self.times_s[i])
        a,b=self.vertices_m[i:i+2]
        return ([x+alpha*(y-x) for x,y in zip(a,b)],[(y-x)/(self.times_s[i+1]-self.times_s[i]) for x,y in zip(a,b)])


class TrackingEvaluation(Contract):
    max_error_m: float = Field(gt=0)
    geometry_step_m: float = Field(gt=0)


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
