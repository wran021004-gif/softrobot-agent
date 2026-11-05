from typing import Literal
from pydantic import Field, FiniteFloat, model_validator, model_serializer
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


class PassiveStageV2(Contract):
    name: str = Field(min_length=1,max_length=80)
    start_s: FiniteFloat = Field(ge=0)
    end_s: FiniteFloat = Field(gt=0)
    force_start_world_n: tuple[FiniteFloat,FiniteFloat,FiniteFloat]
    force_end_world_n: tuple[FiniteFloat,FiniteFloat,FiniteFloat]
    interpolation: Literal['hold','linear','smoothstep']
    ramp_until_s: FiniteFloat
    observation_window_s: tuple[FiniteFloat,FiniteFloat]
    scoring_window_s: tuple[FiniteFloat,FiniteFloat]

    @model_validator(mode='after')
    def intervals(self):
        if not self.start_s<self.end_s or not self.start_s<=self.ramp_until_s<=self.end_s:
            raise ValueError('ORDERED_PASSIVE_STAGE_REQUIRED')
        for window in (self.observation_window_s,self.scoring_window_s):
            if not self.start_s<=window[0]<window[1]<=self.end_s:raise ValueError('WINDOW_INSIDE_PASSIVE_STAGE_REQUIRED')
        if self.interpolation=='hold':
            if self.force_start_world_n!=self.force_end_world_n:raise ValueError('HOLD_REQUIRES_CONSTANT_FORCE')
        elif self.ramp_until_s<=self.start_s:raise ValueError('POSITIVE_PASSIVE_RAMP_REQUIRED')
        return self


class PassiveQualificationV2(Contract):
    stage: str
    window_s: tuple[FiniteFloat,FiniteFloat]
    tip_speed_max_m_s: FiniteFloat = Field(ge=0)
    monitor_speed_max_m_s: FiniteFloat = Field(ge=0)
    qvel_max_rad_s: FiniteFloat = Field(ge=0)
    tail_drift_max_m: FiniteFloat = Field(ge=0)
    static_balance_max_nm: FiniteFloat = Field(ge=0)
    length_excess_max_m: FiniteFloat = Field(ge=0)
    initial_lateral_max_m: FiniteFloat | None = Field(default=None,ge=0)
    sampling: Literal['score_grid','every_physics_step']


class PassiveResponseGoalV2(Contract):
    """Finite frozen programs; the Agent chooses owned objects, never engine state."""
    version: Literal['passive_response_v2'] = 'passive_response_v2'
    execution_protocol: Literal['continuous_v1','phs2d_original_v1'] = 'continuous_v1'
    unloaded_static_solver: dict[str, FiniteFloat] = Field(default_factory=dict)
    unloaded_multistart: bool = False
    load_conditions: list[str] = Field(min_length=1,max_length=32)
    programs: dict[str,list[PassiveStageV2]]
    protocol_source: EvidenceRef
    force_unit: Literal['N'] = 'N'
    time_unit: Literal['s'] = 's'
    frame: Literal['world'] = 'world'
    force_sampling: Literal['interval_start','interval_end']
    static_balance_reference: Literal['cold_zero_velocity','copied_integration_zero_velocity']
    reset: Literal['same_complete_initial_state_each_episode','qpos_only_shared_unloaded'] = 'same_complete_initial_state_each_episode'
    initial_source: Literal['frozen_named_state','qualified_unloaded','fresh_unloaded_hard_equilibrium']
    allow_saved_state: bool = False
    unloaded_stage: str
    qualifications: list[PassiveQualificationV2] = Field(min_length=1,max_length=32)
    solreflimit: tuple[FiniteFloat,FiniteFloat]
    solimplimit: tuple[FiniteFloat,FiniteFloat,FiniteFloat,FiniteFloat,FiniteFloat]
    length_tolerance_m: FiniteFloat = Field(gt=0)
    tension_tolerance_n: FiniteFloat = Field(ge=0)
    multiplier_sign_tolerance_n: FiniteFloat = Field(ge=0)
    constraint_direction_tolerance: FiniteFloat = Field(ge=0)
    force_map_tolerance_nm: FiniteFloat = Field(ge=0)
    allowed_ablation: Literal['none','disable_selected_passive_limits'] = 'none'
    recording: Literal['score_and_qualification','full_physics_csv'] = 'score_and_qualification'
    route_check: Literal['not_required','score_grid','every_physics_step'] = 'not_required'

    @model_serializer(mode='wrap')
    def historical_serialization(self,handler):
        value=handler(self)
        if self.execution_protocol=='continuous_v1':value.pop('execution_protocol',None)
        if not self.unloaded_static_solver:value.pop('unloaded_static_solver',None)
        if not self.unloaded_multistart:value.pop('unloaded_multistart',None)
        return value

    @model_validator(mode='after')
    def programs_match(self):
        if self.execution_protocol=='phs2d_original_v1':
            if (self.initial_source!='fresh_unloaded_hard_equilibrium' or self.reset!='qpos_only_shared_unloaded' or self.allow_saved_state or
                    self.force_sampling!='interval_start' or self.static_balance_reference!='copied_integration_zero_velocity' or
                    self.allowed_ablation!='none' or not self.unloaded_static_solver):
                raise ValueError('EXPLICIT_ORIGINAL_PHS_INITIALIZATION_AND_PHASE_REQUIRED')
            keys={'max_iterations','ftol','length_tolerance_m','stationarity_tolerance_nm',
                'complementarity_tolerance_nm','active_tolerance_m','rank_relative_tolerance',
                'hessian_step_rad','minimum_reduced_eigenvalue'}
            if (set(self.unloaded_static_solver)!=keys or
                    any(v<=0 for v in self.unloaded_static_solver.values()) or
                    self.unloaded_static_solver.get('max_iterations',0)!=int(self.unloaded_static_solver.get('max_iterations',0))):
                raise ValueError('VALID_FROZEN_UNLOADED_STATIC_SOLVER_REQUIRED')
        elif self.initial_source=='fresh_unloaded_hard_equilibrium' or self.unloaded_static_solver or self.unloaded_multistart or self.reset!='same_complete_initial_state_each_episode':
            raise ValueError('VERSIONED_HARD_EQUILIBRIUM_PROTOCOL_REQUIRED')
        if len(set(self.load_conditions))!=len(self.load_conditions) or set(self.programs)!=set(self.load_conditions):
            raise ValueError('EXACT_ORDERED_EPISODE_PROGRAMS_REQUIRED')
        for stages in self.programs.values():
            if not stages or len(stages)>32 or len({s.name for s in stages})!=len(stages):raise ValueError('BOUNDED_UNIQUE_PASSIVE_STAGES_REQUIRED')
            if stages[0].start_s!=0 or stages[0].name!=self.unloaded_stage:
                raise ValueError('EXPLICIT_INITIAL_UNLOADED_STAGE_REQUIRED')
            if any(stages[0].force_start_world_n) or any(stages[0].force_end_world_n):raise ValueError('INITIAL_STAGE_MUST_BE_UNLOADED')
            for left,right in zip(stages,stages[1:]):
                if left.end_s!=right.start_s or left.force_end_world_n!=right.force_start_world_n:
                    raise ValueError('CONTINUOUS_PASSIVE_TIME_AND_FORCE_REQUIRED')
        if len({q.stage for q in self.qualifications})!=len(self.qualifications) or not any(q.stage==self.unloaded_stage for q in self.qualifications):
            raise ValueError('UNIQUE_UNLOADED_DYNAMIC_QUALIFICATION_REQUIRED')
        if self.solreflimit[0]<=0 or self.solreflimit[1]<=0 or self.solimplimit[2]<=0:
            raise ValueError('EXPLICIT_VALID_PASSIVE_LIMIT_SOLVER_REQUIRED')
        return self


class PassiveResponseBoundV2(PassiveResponseBound):
    window: str
    reference_window: str
    reference_reduction: Literal['last','mean'] = 'last'
    aggregation: Literal['range','mean','mean_state','last'] = 'range'
    tip_projection_world: list[tuple[FiniteFloat,FiniteFloat,FiniteFloat]] | None = Field(default=None,min_length=1,max_length=3)
    material_projection_world: list[tuple[FiniteFloat,FiniteFloat,FiniteFloat]] | None = Field(default=None,min_length=1,max_length=3)
    denominator_floor_m: FiniteFloat = Field(default=0.,ge=0)


class PassiveStiffnessV2(Contract):
    """Registered interval stiffness, not an arbitrary evaluation expression."""
    load_condition: str
    stages: tuple[str,str,str]
    reference_stage: str
    material_s: FiniteFloat = Field(ge=0,le=1)
    direction_world: tuple[FiniteFloat,FiniteFloat,FiniteFloat]
    denominator_min_m: FiniteFloat = Field(gt=0)
    denominator_uncertainty_multiplier: FiniteFloat = Field(ge=0)
    stiffness_ratio_min: FiniteFloat = Field(gt=0)
    low_tension_max_n: FiniteFloat = Field(ge=0)
    high_tension_min_n: FiniteFloat = Field(gt=0)
    low_slack_min_m: FiniteFloat = Field(gt=0)
    high_constraint_residual_max_m: FiniteFloat = Field(gt=0)

    @model_validator(mode='after')
    def direction(self):
        import math
        if abs(math.hypot(*self.direction_world)-1)>1e-10 or len(set(self.stages))!=3:raise ValueError('ORDERED_STIFFNESS_STAGES_AND_UNIT_DIRECTION_REQUIRED')
        return self


class PassiveMechanismV2(Contract):
    high_displacement_increase_min: FiniteFloat = Field(gt=0)
    late_stiffness_ratio_max: FiniteFloat = Field(gt=0)
    require_stable_comparable: Literal[True] = True


class PassiveResponseEvaluationV2(Contract):
    bounds: list[PassiveResponseBoundV2] = Field(min_length=1)
    prohibit_contact: bool = True
    progressive_stiffness: list[PassiveStiffnessV2] = Field(default_factory=list,max_length=32)
    mechanism: PassiveMechanismV2 | None = None

    @model_validator(mode='after')
    def names(self):
        if len({b.name for b in self.bounds})!=len(self.bounds):raise ValueError('UNIQUE_PASSIVE_BOUND_NAMES_REQUIRED')
        if len({s.load_condition for s in self.progressive_stiffness})!=len(self.progressive_stiffness):raise ValueError('ONE_REGISTERED_STIFFNESS_DEFINITION_PER_EPISODE_REQUIRED')
        if self.mechanism and not self.progressive_stiffness:raise ValueError('MECHANISM_REQUIRES_FROZEN_RESPONSE_COMPARISON')
        return self


class PassiveInitialExecutionV2(Contract):
    source: Literal['frozen_named_state','qualified_unloaded','saved_integration_state']
    state_identities: dict[str,str]
    source_result: EvidenceRef | None = None


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
