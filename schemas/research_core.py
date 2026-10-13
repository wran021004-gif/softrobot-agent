"""Native business fields for the bounded reach-and-hold research entry."""
from typing import Literal
from pydantic import Field, FiniteFloat, model_validator
from schemas.common import Contract
from schemas.platform import EvidenceRef
from schemas.casadi_feedback import Candidate as MechanicsChoice


class Parameters(Contract):
    d: FiniteFloat = Field(default=0., ge=-1, le=1)
    holding_tip_speed_weight: FiniteFloat = Field(default=.10, ge=.025, le=.10)
    terminal_tip_speed_weight: FiniteFloat = Field(default=.10, ge=.025, le=.10)


class Search(Contract):
    variables: list[Literal['d', 'holding_tip_speed_weight', 'terminal_tip_speed_weight']] = Field(min_length=1)
    bounds: dict[str, tuple[FiniteFloat, FiniteFloat]]
    fixed: Parameters = Field(default_factory=Parameters)
    max_evaluations: int = Field(default=3, ge=1, le=8, strict=True)
    step: FiniteFloat = Field(default=.25, gt=0, le=.5)
    ranking: Literal['feasible_then_max_normalized_violation_then_sum_v1'] = 'feasible_then_max_normalized_violation_then_sum_v1'
    mechanics_source: EvidenceRef | None = None

    @model_validator(mode='after')
    def domain(self):
        if len(set(self.variables)) != len(self.variables) or set(self.bounds) != set(self.variables):
            raise ValueError('SEARCH_BOUNDS_MUST_MATCH_UNIQUE_SELECTED_VARIABLES')
        for name, (a, b) in self.bounds.items():
            lo, hi = (-1., 1.) if name == 'd' else (.025, .10)
            if not lo <= a < b <= hi or not a <= getattr(self.fixed, name) <= b:
                raise ValueError('SEARCH_DOMAIN_OR_INITIAL_OUTSIDE_BOUNDS: ' + name)
        return self


class LocalDiagnostic(Contract):
    execution: EvidenceRef
    update_id: int = Field(ge=0,le=34,strict=True)
    repetitions: int = Field(default=2,ge=1,le=2,strict=True)
    mode: Literal['production', 'fixed_iteration', 'research_policy', 'research_current'] = 'production'
    iteration_cap: int = Field(default=8,ge=1,le=120,strict=True)
    reuse_solver: bool = False
    prepare_tail: bool = False


class Plan(Contract):
    action: Literal['propose', 'execute', 'search', 'mechanics', 'replay', 'diagnose', 'confirm', 'stop']
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
    selected_execution: EvidenceRef | None = None
    diagnostic: LocalDiagnostic | None = None
    mechanics: MechanicsChoice | None = None
    mechanics_source: EvidenceRef | None = None
    experience_disposition: dict[str, Literal['adopted', 'rejected', 'context_only']] = Field(default_factory=dict)

    @model_validator(mode='after')
    def required(self):
        required = {'propose': 'parameters', 'execute': 'candidate', 'search': 'search', 'confirm': 'selected_execution',
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
    actions: int = Field(ge=1,le=2048,strict=True)
    active_seconds: FiniteFloat = Field(gt=0,le=120)


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
