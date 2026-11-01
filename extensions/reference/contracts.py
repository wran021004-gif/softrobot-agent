from typing import Literal
from pydantic import Field, FiniteFloat, model_validator
from schemas.common import Contract
from schemas.platform import EvidenceRef, Signal, Payload, EvaluationResult, BackendResult, WorkerOutput, MemoryEntry, WorkOrder
from schemas.design_spec import DesignSpec
from schemas.robot_ir import RobotIR
from schemas.exploration import ExplorationControl


class Empty(Contract):
    pass


class PassiveResponseGoal(Contract):
    """One reset per load; the unloaded prefix is part of every episode."""
    version: Literal['passive_response_v1'] = 'passive_response_v1'
    load_conditions: list[str] = Field(min_length=1)
    unloaded_until_s: FiniteFloat = Field(gt=0)
    ramp_until_s: FiniteFloat = Field(gt=0)
    hold_window_s: tuple[FiniteFloat, FiniteFloat]
    reset: Literal['frozen_named_state_each_episode'] = 'frozen_named_state_each_episode'
    force_interpolation: Literal['linear_ramp_then_hold'] = 'linear_ramp_then_hold'
    displacement_reference: Literal['last_unloaded_sample_same_episode'] = 'last_unloaded_sample_same_episode'

    @model_validator(mode='after')
    def protocol(self):
        if (len(set(self.load_conditions)) != len(self.load_conditions) or
                not self.unloaded_until_s < self.ramp_until_s <= self.hold_window_s[0] < self.hold_window_s[1]):
            raise ValueError('ORDERED_PASSIVE_PROTOCOL_REQUIRED')
        return self


from extensions.tendon_family.contracts import ConstrainedObservation


class PassiveResponseBound(ConstrainedObservation):
    """Spatial reductions reuse static observation semantics; time is explicit."""
    quantity: Literal['material_displacement','tip_displacement','displacement_ratio','displacement_difference',
        'maximum_tension','maximum_length_excess','material_speed','tip_speed','unloaded_tip_drift',
        'maximum_joint_position','maximum_joint_speed']
    window: Literal['unloaded','hold','full'] = 'hold'
    unit: Literal['m','N','1','m/s','rad','rad/s'] | None = None

    @property
    def physical_unit(self):
        return {'maximum_tension':'N','displacement_ratio':'1','material_speed':'m/s',
            'tip_speed':'m/s','maximum_joint_position':'rad','maximum_joint_speed':'rad/s'}.get(self.quantity,'m')

    @model_validator(mode='after')
    def hard_bound(self):
        if self.minimum is None and self.maximum is None:
            raise ValueError('DYNAMIC_HARD_BOUND_REQUIRED')
        if self.reference_load is not None:
            raise ValueError('DYNAMIC_REFERENCE_IS_THE_SAME_EPISODE_UNLOADED_PREFIX')
        return self


class PassiveResponseEvaluation(Contract):
    bounds: list[PassiveResponseBound] = Field(min_length=1)
    prohibit_contact: bool = True

    @model_validator(mode='after')
    def names(self):
        if len({b.name for b in self.bounds}) != len(self.bounds):
            raise ValueError('UNIQUE_PASSIVE_BOUND_NAMES_REQUIRED')
        return self


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


class RigidToolLoad(Contract):
    body: str
    mass_kg: FiniteFloat = Field(gt=0)
    com_local_m: tuple[FiniteFloat,FiniteFloat,FiniteFloat]
    inertia_com_local_kg_m2: tuple[tuple[FiniteFloat,FiniteFloat,FiniteFloat],tuple[FiniteFloat,FiniteFloat,FiniteFloat],tuple[FiniteFloat,FiniteFloat,FiniteFloat]]
    tip_position_local_m: tuple[FiniteFloat,FiniteFloat,FiniteFloat]


class OrientedTrackingGoal(TrackingGoal):
    axis_local: tuple[FiniteFloat,FiniteFloat,FiniteFloat]
    axis_vertices_world: list[tuple[FiniteFloat,FiniteFloat,FiniteFloat]] = Field(min_length=2,max_length=3)
    axis_interpolation: Literal['normalized_linear'] = 'normalized_linear'
    axis_frame: Literal['tip_site_local'] = 'tip_site_local'
    rigid_tool: RigidToolLoad

    @model_validator(mode='after')
    def directed_timed_axes(self):
        import math
        if (self.time_requirement!='timed' or len(self.axis_vertices_world)!=len(self.vertices_m)
                or any(abs(math.hypot(*v)-1)>1e-10 for v in [self.axis_local,*self.axis_vertices_world])
                or any(sum(x*y for x,y in zip(a,b))<=-1+1e-10 for a,b in zip(self.axis_vertices_world,self.axis_vertices_world[1:]))):
            raise ValueError('TIMED_UNIT_AXES_WITH_NONANTIPODAL_NODES_REQUIRED')
        return self

    def position_goal(self):
        return TrackingGoal(**{k:getattr(self,k) for k in TrackingGoal.model_fields})

    def axis_at_time(self,time_s):
        from bisect import bisect_right
        import math
        if not 0<=time_s<=self.times_s[-1]:raise ValueError('AXIS_REFERENCE_TIME_OUTSIDE_HORIZON')
        i=min(bisect_right(self.times_s,time_s)-1,len(self.times_s)-2)
        alpha=(time_s-self.times_s[i])/(self.times_s[i+1]-self.times_s[i])
        a,b=self.axis_vertices_world[i:i+2];v=[(1-alpha)*x+alpha*y for x,y in zip(a,b)];n=math.hypot(*v)
        return [x/n for x in v]


class OrientedTrackingEvaluation(TrackingEvaluation):
    angle_tolerance_rad: FiniteFloat = Field(gt=0,lt=3.141592653589793)


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
