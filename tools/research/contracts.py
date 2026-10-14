"""Native business fields for the bounded reach-and-hold research entry."""
from typing import Literal
from pydantic import Field, FiniteFloat, model_validator
from schemas.common import Contract
from schemas.platform import EvidenceRef
from schemas.platform_analysis import TaskAnalysisProtocol


class SegmentParameters(Contract):
    length_m: FiniteFloat = Field(gt=0)
    young_pa: FiniteFloat | None = Field(default=None,gt=0)
    material_scenario: Literal['baseline','compliant','stiff'] | None = None
    sections: dict[str,dict[str,FiniteFloat]]

    @model_validator(mode='after')
    def physical_authority(self):
        if (self.young_pa is None)==(self.material_scenario is None):
            raise ValueError('EXACTLY_ONE_CONTINUOUS_MODULUS_OR_NAMED_SCENARIO_REQUIRED')
        if any(v<=0 for station in self.sections.values() for v in station.values()):
            raise ValueError('POSITIVE_SECTION_DIMENSIONS_REQUIRED')
        return self


class Parameters(Contract):
    segments: dict[str,SegmentParameters]
    holding_tip_speed_weight: FiniteFloat = Field(ge=0)
    terminal_tip_speed_weight: FiniteFloat = Field(ge=0)


class Search(Contract):
    variables: list[str] = Field(min_length=1)
    bounds: dict[str,tuple[FiniteFloat,FiniteFloat]]
    fixed: Parameters
    method: Literal['hierarchical_coordinate_v1_1'] = 'hierarchical_coordinate_v1_1'
    evaluation_mode: Literal['mathematical_proxy','backend_task'] = 'mathematical_proxy'
    objective: Literal['held_position_min_eigenvalue','target_equilibrium_residual','joint_reach_hold']
    operating_point: Literal['standardized_initial_pretension','controller_start_input','target_equilibrium','halfway_waypoint']
    scoring_window_s: FiniteFloat = Field(gt=0)
    protocol: TaskAnalysisProtocol
    max_evaluations: int = Field(ge=1,le=12,strict=True)
    step: FiniteFloat = Field(default=.25,gt=0,le=.5)
    minimum_step: FiniteFloat = Field(default=.03125,gt=0,le=.5)

    @model_validator(mode='after')
    def domain(self):
        if len(set(self.variables))!=len(self.variables) or set(self.variables)!=set(self.bounds):
            raise ValueError('BOUNDS_MUST_MATCH_SELECTED_VARIABLES')
        from tools.research.design import parameter_value
        for key,(lo,hi) in self.bounds.items():
            if not lo<hi or not lo<=parameter_value(self.fixed.model_dump(),key)<=hi:
                raise ValueError('INITIAL_VALUE_OR_BOUNDS_INVALID: '+key)
        if (self.evaluation_mode=='backend_task')!=(self.objective=='joint_reach_hold'):
            raise ValueError('OBJECTIVE_EVALUATOR_MISMATCH')
        if self.evaluation_mode=='mathematical_proxy' and any('speed_weight' in k for k in self.variables):
            raise ValueError('CONTROL_VARIABLES_REQUIRE_BACKEND_TASK_EVALUATOR')
        if self.scoring_window_s not in self.protocol.windows_s:raise ValueError('EXPLICIT_DECLARED_SCORE_WINDOW_REQUIRED')
        return self


class AnalysisRequest(Contract):
    candidate: EvidenceRef
    operation: Literal['equilibrium','linearization','controllability','endpoint','braking']
    operating_point: Literal['standardized_initial_pretension','controller_start_input','target_equilibrium','halfway_waypoint','saved_state'] = 'halfway_waypoint'
    saved_state: EvidenceRef | None = None
    execution: EvidenceRef | None = None
    update_id: int | None = Field(default=None,ge=0,le=34,strict=True)
    protocol: TaskAnalysisProtocol
    scoring_window_s: FiniteFloat | None = Field(default=None,gt=0)

    @model_validator(mode='after')
    def exact_state(self):
        if self.operation in ('linearization','controllability') and self.scoring_window_s is None:
            raise ValueError('EXPLICIT_SCORE_WINDOW_REQUIRED')
        if (self.execution is None)!=(self.update_id is None):raise ValueError('EXECUTION_REQUIRES_UPDATE_ID')
        sources=int(self.saved_state is not None)+int(self.execution is not None)
        if sources>1 or (self.operating_point=='saved_state')!=(sources==1):raise ValueError('SAVED_POINT_REQUIRES_UNAMBIGUOUS_STATE_SOURCE')
        return self


class LocalDiagnostic(Contract):
    execution: EvidenceRef
    update_id: int = Field(ge=0,le=34,strict=True)
    repetitions: int = Field(default=2,ge=1,le=2,strict=True)
    mode: Literal['research_policy', 'research_current'] = 'research_policy'


class MechanicsRequest(Contract):
    candidate: EvidenceRef
    substeps: int = Field(default=1,ge=1,le=4,strict=True)
    initialization: Literal['constant_0_2','ramp_0_2_to_0_4'] = 'constant_0_2'
    objective_mode: Literal['task_gap','task_gap_with_effort'] = 'task_gap'
    position_weight: FiniteFloat = Field(default=1,gt=0)
    speed_weight: FiniteFloat = Field(default=1,gt=0)
    secondary_coefficient: FiniteFloat = Field(default=.001,ge=0)


class Plan(Contract):
    action: Literal['propose', 'execute', 'search', 'mechanics', 'replay', 'diagnose', 'confirm', 'select', 'stop']
    next_step: Literal['adjust_training','revise_design','diagnose','stop'] | None = None
    hypothesis: str = Field(min_length=1)
    supporting_evidence: list[EvidenceRef] = Field(default_factory=list)
    expected_observation: str = Field(min_length=1)
    weakening_observation: str = Field(min_length=1)
    fixed_conditions: str = Field(min_length=1)
    stopping_condition: str = Field(min_length=1)
    interpretation: str = Field(min_length=1)
    parameters: Parameters | None = None
    search: Search | None = None
    candidate: EvidenceRef | None = None
    selected_execution: EvidenceRef | None = Field(default=None, description='Exact immutable passing NMPC result or independent RL evaluation; freezes the complete solution')
    revise_selection: bool = Field(default=False, description='Explicitly replace a failed selection with a scientifically changed, freshly passing development solution; retain all confirmation records and cumulative costs')
    diagnostic: LocalDiagnostic | None = None
    mechanics: MechanicsRequest | None = None
    mechanics_source: EvidenceRef | None = None
    experience_disposition: dict[str, Literal['adopted', 'rejected', 'context_only']] = Field(default_factory=dict)

    @model_validator(mode='after')
    def required(self):
        if self.revise_selection and self.action not in ('confirm','select'):
            raise ValueError('REVISE_SELECTION_REQUIRES_CONFIRM_ACTION')
        required = {'propose': 'parameters', 'execute': 'candidate', 'search': 'search', 'confirm': 'selected_execution', 'select': 'selected_execution',
                    'mechanics': 'mechanics', 'replay': 'mechanics_source'}
        active = required.get(self.action)
        for field in ('parameters', 'search', 'candidate', 'selected_execution', 'mechanics'):
            if (getattr(self, field) is not None) != (field == active):
                raise ValueError('ACTION_REQUIRES_ONLY_' + str(active))
        if self.action=='replay' and self.mechanics_source is None:
            raise ValueError('REPLAY_REQUIRES_OWNED_MECHANICS_RESULT')
        if self.mechanics_source is not None and self.action not in ('propose','replay'):
            raise ValueError('MECHANICS_SOURCE_REQUIRES_PROPOSE_OR_REPLAY; SEARCH_HAS_ITS_OWN_SOURCE')
        if self.diagnostic is not None and self.action!='diagnose':
            raise ValueError('LOCAL_DIAGNOSTIC_REQUIRES_DIAGNOSE_ACTION')
        return self


class ExperienceQuery(Contract):
    operation: Literal['search', 'read'] = 'search'
    key: str | None = Field(default=None,min_length=1)
    entry_id: str | None = Field(default=None,min_length=1)
    revision: str | None = Field(default=None,min_length=1)
    task: str | None = None
    structure: str | None = None
    failure_type: str | None = None
    version: str | None = None


class EvidenceQuery(Contract):
    reference: EvidenceRef
    pointer: str = ''


class PPOOverrides(Contract):
    learning_rate: FiniteFloat | dict = Field(default=.0003)
    n_steps: int = Field(default=256,ge=2,le=1024,strict=True)
    batch_size: int = Field(default=64,ge=2,le=1024,strict=True)
    n_epochs: int = Field(default=10,ge=1,le=20,strict=True)
    gamma: FiniteFloat = Field(default=.99,ge=0,le=1)
    gae_lambda: FiniteFloat = Field(default=.95,ge=0,le=1)
    clip_range: FiniteFloat | dict = .2
    clip_range_vf: FiniteFloat | dict | None = None
    normalize_advantage: bool = True
    ent_coef: FiniteFloat = Field(default=0,ge=0)
    vf_coef: FiniteFloat = Field(default=.5,ge=0)
    max_grad_norm: FiniteFloat = Field(default=.5,gt=0)
    target_kl: FiniteFloat | None = Field(default=None,gt=0)
    policy_kwargs: dict = Field(default_factory=dict)


class RewardOverrides(Contract):
    position: FiniteFloat = Field(default=1,ge=0)
    holding_speed: FiniteFloat = Field(default=1,ge=0)
    smoothness: FiniteFloat = Field(default=.001,ge=0)
    failure_penalty: FiniteFloat = Field(default=-10000,le=0)


class RLAllocation(Contract):
    actions: int = Field(ge=1,strict=True)
    active_seconds: FiniteFloat = Field(gt=0)


class RLReference(Contract):
    path: str
    sha256: str
    candidate_identity: str
    task_identity: str
    tendon_order: list[str]
    control_period_s: FiniteFloat = Field(gt=0)


class RLRequest(Contract):
    operation: Literal['start','status','stop','resume','evaluate','diagnose']
    candidate: EvidenceRef | None = None
    task: EvidenceRef | None = None
    mode: Literal['direct','residual'] | None = None
    reference: RLReference | None = None
    training_overrides: PPOOverrides = Field(default_factory=PPOOverrides)
    reward_overrides: RewardOverrides = Field(default_factory=RewardOverrides)
    allocation: RLAllocation | None = None
    rationale: str = Field(min_length=1)
    run_id: str | None = None
    checkpoint: str | None = None
    failure: str | None = None
    replay: bool = False

    @model_validator(mode='after')
    def operation_contract(self):
        if self.operation=='start':
            if self.candidate is None or self.mode is None or self.allocation is None or self.run_id:
                raise ValueError('START_REQUIRES_CANDIDATE_MODE_ALLOCATION')
            if (self.mode=='residual')!=(self.reference is not None): raise ValueError('RESIDUAL_REQUIRES_REFERENCE_DIRECT_REQUIRES_NONE')
        else:
            if not self.run_id: raise ValueError('RECORDED_RUN_ID_REQUIRED')
            if self.candidate or self.task or self.mode or self.reference or self.allocation or self.training_overrides.model_fields_set or self.reward_overrides.model_fields_set:
                raise ValueError('SUBSEQUENT_OPERATIONS_RETAIN_FROZEN_CONFIGURATION')
        if self.checkpoint and self.operation!='evaluate': raise ValueError('CHECKPOINT_ONLY_FOR_EVALUATE')
        if (self.failure or self.replay) and self.operation!='diagnose': raise ValueError('FAILURE_REPLAY_ONLY_FOR_DIAGNOSE')
        return self
