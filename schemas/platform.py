"""Versioned platform envelopes. Payloads MUST be validated by Registry.parse.

Identifiers and policy are host-owned; extension payloads carry no import paths.
"""
from typing import Literal
from pydantic import Field, model_validator
from schemas.common import Contract
from schemas.evidence import Identifier

VERSION = '1.0.0'


class Payload(Contract):
    contract: Identifier
    version: str = VERSION
    data: dict


class EvidenceRef(Contract):
    artifact_id: str = Field(pattern=r'^[a-f0-9]{64}$')
    media_type: str = 'application/json'


class ExportedFile(Contract):
    filename: str
    reference: EvidenceRef


class ExportBundle(Contract):
    result: EvidenceRef
    files: list[ExportedFile]
    source: str


class Binding(Contract):
    extension_id: Identifier
    version: str = VERSION
    parameters: Payload


class SignalSpec(Contract):
    """Backend-neutral quantity and entity; dimension is each flattened sample.

    Names are extensible (e.g. contact_force). units/frame/phase are semantic,
    not backend identifiers; absence denotes unsupported, never invented zero.
    """
    name: Identifier
    entity: Identifier
    dimension: int = Field(gt=0)
    units: str = Field(min_length=1)
    frame: str = Field(min_length=1)
    phase: str = Field(min_length=1)
    missing: Literal['unsupported'] = 'unsupported'


class Signal(Contract):
    """Actual sample timestamps in seconds; spacing may be nonuniform or sparse."""
    spec: SignalSpec
    times_s: list[float]
    values: list[list[float]]

    @model_validator(mode='after')
    def shape(self):
        if len(self.values) != len(self.times_s) or any(len(v) != self.spec.dimension for v in self.values):
            raise ValueError('SIGNAL_DIMENSION_MISMATCH')
        if any(b <= a for a, b in zip(self.times_s, self.times_s[1:])):
            raise ValueError('SIGNAL_TIME_NOT_INCREASING')
        return self


class Timing(Contract):
    timestep_s: float = Field(gt=0, description='Physical integration timestep, s')
    control_period_s: float = Field(gt=0, description='Control period, s')
    sample_period_s: float = Field(gt=0, description='Output sampling period, s')
    duration_s: float = Field(gt=0, description='Physical duration, s')
    termination: list[Literal['duration', 'numerical_failure', 'cancelled']] = Field(min_length=1)

    @model_validator(mode='after')
    def grid(self):
        for value in (self.control_period_s, self.sample_period_s, self.duration_s):
            if abs(value / self.timestep_s - round(value / self.timestep_s)) > 1e-8:
                raise ValueError('TIME_MUST_BE_INTEGER_MULTIPLE_OF_TIMESTEP_S')
        if 'duration' not in self.termination:
            raise ValueError('FINITE_DURATION_TERMINATION_REQUIRED')
        return self


class Objective(Contract):
    metric: Identifier
    direction: Literal['minimize', 'maximize']
    units: str = Field(min_length=1)
    weight: float = Field(default=1, gt=0)


class Sampling(Contract):
    split: Literal['development', 'evaluation']
    seeds: list[int] = Field(min_length=1)
    aggregation: Literal['per_instance'] = 'per_instance'
    window_s: tuple[float, float]

    @model_validator(mode='after')
    def partitions(self):
        lo, hi = (0, 999) if self.split == 'development' else (10000, 10999)
        if len(set(self.seeds)) != len(self.seeds) or any(not lo <= n <= hi for n in self.seeds):
            raise ValueError('DISJOINT_SEED_PARTITIONS: development 0..999, evaluation 10000..10999')
        if not 0 <= self.window_s[0] < self.window_s[1]:
            raise ValueError('INVALID_EVALUATION_WINDOW_S')
        return self


class TaskDefinition(Contract):
    contract_version: Literal['1.0.0'] = VERSION
    task_id: Identifier
    task_version: str = Field(min_length=1)
    name: str = Field(min_length=1)
    status: Literal['draft', 'development_valid', 'formally_approved']
    source: str = Field(min_length=1)
    family: Identifier
    goal: Payload
    environment: Payload
    robot_families: list[Identifier] = Field(min_length=1)
    actuator_channels: list[Identifier] = Field(min_length=1)
    initializer: Binding
    timing: Timing
    evaluator: Binding
    objectives: list[Objective] = Field(min_length=1)
    failure_policy: Literal['retain_invalid_and_constraint_failures']
    observations: list[SignalSpec] = Field(min_length=1)
    sampling: Sampling

    @model_validator(mode='after')
    def window(self):
        if self.sampling.window_s[1] > self.timing.duration_s:
            raise ValueError('EVALUATION_WINDOW_EXCEEDS_DURATION_S')
        return self


class RobotDescription(Contract):
    family: Identifier
    structure: Payload
    channels: list[Identifier] = Field(min_length=1)
    units: Literal['SI'] = 'SI'
    frame: str
    assumptions: list[str] = Field(min_length=1)
    sources: list[str] = Field(min_length=1)
    unsupported: list[str]


class Budget(Contract):
    tool_calls: int = Field(ge=0)
    model_calls: int = Field(ge=0)
    backend_solves: int = Field(ge=0)
    worker_calls: int = Field(ge=0)
    wall_s: float = Field(ge=0)


class ModelConfig(Contract):
    adapter: Identifier = 'offline'
    adapter_version: str = '1.0.0'
    parameters: dict = Field(default_factory=dict)
    strategy: Identifier = 'strategy.tool'
    strategy_version: str = '1.0.0'
    model: str = 'offline-contract-fixture'
    base_url: str = 'https://api.deepseek.com'
    thinking: Literal['enabled','disabled'] | None = None
    max_tokens: int = Field(default=2000,ge=1)
    supports_tools: Literal[True] = True
    supports_text: Literal[True] = True
    supports_images: bool = False
    timeout_s: float = Field(default=30, gt=0)
    max_turns: int = Field(default=12, ge=1, le=1000)
    max_repairs: int = Field(default=2, ge=0, le=10)
    max_no_progress: int = Field(default=3, ge=1, le=20)
    context_bytes: int = Field(default=64000, ge=4000)


class ExperimentPolicy(Contract):
    policy_id: Identifier
    editable: dict[str, tuple[float, float]] = Field(default_factory=dict)
    backend: Binding
    controller: Binding
    # Robot dynamics are distinct from ModelConfig, which configures the LLM.
    # Optional for old snapshots whose backend binding carried this selection.
    dynamics_model: Binding | None = None
    # Model/discretization belongs to the run plan, not the physical robot.
    # It is optional so existing non-discretized extensions remain unchanged.
    discretization: Payload | None = None
    candidate_builder: Binding | None = None
    search: Binding | None = None
    route: Payload | None = None
    model: ModelConfig = Field(default_factory=ModelConfig)
    allowed_tools: list[Identifier] = Field(default_factory=list)
    tool_bindings: dict[Identifier, str] = Field(default_factory=dict)
    budget: Budget
    timeout_s: float = Field(gt=0)
    allow_development_skills: bool = False
    recovery: Literal['sealed_or_unknown_no_replay'] = 'sealed_or_unknown_no_replay'


class ProjectConfig(Contract):
    contract_version: Literal['1.0.0'] = VERSION
    project_id: Identifier
    grant_id: Identifier
    purpose: Literal['development'] = 'development'
    authorization_source: str = Field(min_length=1)
    budget: Budget
    exclusive_resources: dict[str, int] = Field(default_factory=dict)


class SessionInput(Contract):
    contract_version: Literal['1.0.0'] = VERSION
    run_id: Identifier
    task: TaskDefinition
    robot: RobotDescription
    policy: ExperimentPolicy
    seed: int


class ToolRequest(Contract):
    contract_version: Literal['1.0.0'] = VERSION
    request_id: Identifier
    tool_id: Identifier
    tool_version: str = VERSION
    arguments: dict
    reason: str = Field(min_length=1, max_length=2000)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    cache: Literal['reuse', 'new'] = 'reuse'


class Metric(Contract):
    name: Identifier
    value: float
    units: str


class ConstraintResult(Contract):
    name: Identifier
    satisfied: bool
    observed: float
    limit: float
    units: str


class EvaluationResult(Contract):
    contract_version: Literal['1.0.0', '1.1.0', '1.2.0'] = '1.2.0'
    validity: Literal['valid', 'invalid', 'incomplete', 'unsupported']
    task_success: bool | None
    metrics: list[Metric]
    constraints: list[ConstraintResult]
    source: EvidenceRef
    evaluator: str
    evaluator_version: str = VERSION
    source_execution_id: str | None = None
    original_execution_id: str | None = None
    candidate_id: str | None = None
    comparison_identity: str
    reason: str | None = None

    @model_validator(mode='after')
    def valid_success(self):
        if self.validity != 'valid' and (self.task_success is not None or self.metrics):
            raise ValueError('INVALID_EVALUATION_CANNOT_HAVE_SCORE_OR_TASK_SUCCESS')
        if self.validity == 'valid' and (self.task_success is None or not self.metrics):
            raise ValueError('VALID_EVALUATION_REQUIRES_METRICS_AND_TASK_RESULT')
        if len({m.name for m in self.metrics}) != len(self.metrics):
            raise ValueError('DUPLICATE_METRIC')
        return self


class BackendResult(Contract):
    """Public exit for every execution backend, one-shot or stepping.

    Native traces may be retained in data/ExportBundle, but shared evaluators
    and diagnostics consume signals with their full SignalSpec semantics.
    solver_status is the historical execution status, unrelated to Solver.solve.
    """
    solver_status: Literal['completed', 'failed', 'cancelled', 'unknown']
    backend_id: Identifier
    model_id: Identifier
    backend_version: str = VERSION
    signals: list[Signal]
    data: Payload
    limitations: list[str]
    initial_state: Payload
    seed: int


class ToolReceipt(Contract):
    contract_version: Literal['1.0.0', '1.1.0', '1.2.0'] = '1.2.0'
    request_id: str
    execution_id: str
    caller: str
    tool_id: str
    tool_version: str = VERSION
    result_contract: str | None = None
    result_version: str = VERSION
    execution_status: Literal['completed', 'rejected', 'failed', 'unknown', 'cancelled']
    solver_status: str = 'not_run'
    analysis_status: str = 'not_assessed'
    task_success: bool | None = None
    output: EvidenceRef | None = None
    error: str | None = None
    cache_hit: bool = False
    original_execution_id: str | None = None
    charged: Budget


class Event(Contract):
    contract_version: Literal['1.0.0'] = VERSION
    project_id: str
    run_id: str
    sequence: int
    event_id: str
    parent_id: str | None
    candidate_id: str | None = None
    agent_id: str
    request_id: str | None
    execution_id: str | None
    timestamp: str
    kind: str
    status: str
    inputs: list[EvidenceRef] = Field(default_factory=list)
    outputs: list[EvidenceRef] = Field(default_factory=list)
    implementation_version: str
    cost: Budget


class MemoryEntry(Contract):
    memory_id: Identifier
    summary: str = Field(min_length=1, max_length=1200)
    kind: Literal['model_note', 'direct_observation', 'verified_record', 'hypothesis']
    task_family: str
    task_version: str
    backend: str
    model_id: str
    model_scope: str | None = None
    transferable_scopes: list[str] = Field(default_factory=list)
    failure_category: str | None = None
    tags: list[str] = Field(default_factory=list)
    sources: list[EvidenceRef] = Field(min_length=1)
    expires_at: str | None = None
    invalidated: bool = False


class WorkOrder(Contract):
    work_id: Identifier
    goal: str = Field(min_length=1)
    worker: Binding
    input_snapshot: EvidenceRef
    base_candidate: str
    tool_bindings: dict[Identifier, str] = Field(default_factory=dict)
    allowed_tools: list[Identifier]
    budget: Budget
    timeout_s: float = Field(gt=0, le=3600)
    dependencies: list[Identifier] = Field(default_factory=list)
    resources: list[Identifier] = Field(default_factory=list)
    output_contract: str
    write_scope: Literal['own_output_directory'] = 'own_output_directory'
    completion_check: Literal['hash_contract_source_base_candidate'] = 'hash_contract_source_base_candidate'


class LegacyWorkerOutput(Contract):
    work_id: str
    base_candidate: str
    source: EvidenceRef
    signal: str
    status: Literal['observed', 'missing_data']
    sample_indices: list[int]
    values: list[list[float]]
    claim_key: str
    conclusion: str
    started_at: float
    ended_at: float


class ToolObservation(Contract):
    contract_version: Literal['1.0.0'] = '1.0.0'
    receipt: ToolReceipt
    content: object = None
    content_bytes: int = 0
    truncated: bool = False
    retained: Literal['latest_only'] = 'latest_only'


class CandidateInput(Contract):
    contract_version: Literal['1.0.0'] = '1.0.0'
    candidate_id: str
    baseline_identity: str
    builder: str
    builder_version: str
    changes: dict[str, object]
    allowed: dict[str, tuple[float, float]]
    effective: SessionInput
    content_identity: str
    sources: dict[str, str] = Field(default_factory=dict)


class ModelContent(Contract):
    kind: Literal['text', 'image', 'video']
    text: str | None = None
    source: EvidenceRef | None = None


class ModelInput(Contract):
    contract_version: Literal['1.0.0'] = '1.0.0'
    context: dict
    tools: list[dict]
    content: list[ModelContent]


class ModelResponse(Contract):
    contract_version: Literal['1.0.0'] = '1.0.0'
    raw: object
    usage: dict[str, int] = Field(default_factory=dict)
    status: Literal['completed', 'failed', 'cancelled', 'timeout'] = 'completed'
    error: str | None = None


class WorkerOutput(Contract):
    contract_version: Literal['2.0.0'] = '2.0.0'
    work_id: str
    base_candidate: str
    source: EvidenceRef
    status: Literal['completed', 'failed', 'cancelled', 'needs_input']
    result: Payload
    evidence: list[EvidenceRef] = Field(default_factory=list)
    error: str | None = None
    usage: Budget
    claim_key: str
    conclusion: str
    started_at: float
    ended_at: float
