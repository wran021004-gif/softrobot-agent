"""Framework-neutral learning interfaces; no algorithms, environments or runtime.

    Nested Payloads are interpreted only by trusted adapters after Registry.parse.
    Reward guides training; only the existing Evaluator establishes task success.
"""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from schemas.common import Contract
from schemas.evidence import Identifier
from schemas.platform import Binding, EvidenceRef, Payload, SignalSpec
from schemas.platform_diagnostics import GateResult


class RewardDefinition(Contract):
    """Stable term names; composition and implementation use a trusted contract.

    No reward DSL, executable string or automatically generated reward is defined.
    """
    terms: list[Identifier] = Field(min_length=1)
    implementation: Payload | EvidenceRef


class RLProblem(Contract):
    """Learning interface referencing authoritative TaskDefinition and SessionInput.

    experiment identifies a frozen SessionInput (robot, backend, environment and
    policy); task references its TaskDefinition. Adapters check their consistency.
    Ordered SignalSpecs define flattened observation/action semantics. Reset and
    termination adapt existing initial/episode definitions without changing the
    task's formal success criterion. Reward is not an Evaluator.
    """
    task: EvidenceRef
    experiment: EvidenceRef
    observations: list[SignalSpec] = Field(min_length=1)
    actions: list[SignalSpec] = Field(min_length=1)
    reward: RewardDefinition
    termination: Payload | EvidenceRef
    reset: Binding | EvidenceRef


class TrainingBudget(Contract):
    """Total environment transitions across all selected seeds and environments.

    This is a training stop limit, not a new Host resource grant or ledger.
    """
    environment_steps: int = Field(gt=0)
    wall_s: float | None = Field(default=None, gt=0)


class RLTrainingSpecification(Contract):
    """Agent-owned choices; trainer metadata declares supported algorithm IDs.

    parameters is a registered algorithm configuration, not an arbitrary dict.
    Adapters validate it and enforce the existing Host authorization/budget.
    No task, evaluator, environment, robot or design-space override is accepted.
    """
    algorithm_id: Identifier
    parameters: Payload
    budget: TrainingBudget
    seeds: list[Annotated[int, Field(ge=0)]] = Field(min_length=1)


TrainingStatus = Literal['queued', 'running', 'completed', 'failed', 'cancelled', 'unknown']


class TrainingJob(Contract):
    """Durable identity/status snapshot, never a Python process handle.

    Rebind trainer and query job_id after restoring this artifact. handle may
    reference existing Worker identity or an adapter's typed external job handle.
    problem/specification reference frozen inputs; status is an observation, not
    proof of policy quality. No process exit code implies training success.
    """
    job_id: Identifier
    trainer: Binding
    problem: EvidenceRef
    specification: EvidenceRef
    status: TrainingStatus
    handle: Payload | EvidenceRef | None = None
    reason: str | None = None


# Hierarchical metric names extend Identifier with slash-separated segments;
# other platform identifiers and their historical serialization stay unchanged.
TrainingMetricName = Annotated[str, Field(max_length=160,
    pattern=r'^[A-Za-z0-9][A-Za-z0-9_.-]*(/[A-Za-z0-9][A-Za-z0-9_.-]*)*$')]


class TrainingMetric(Contract):
    """Adapter-normalized sample; step counts environment transitions.

    Names include train/return, eval/success_rate, train/loss/policy,
    train/loss/value, train/entropy, train/approx_kl, train/clip_fraction,
    train/actor_loss, train/critic_loss, train/q_value and
    reward/<term>/episodic_return. No algorithm must emit every metric.
    eval/* describes training monitoring, not a formal EvaluationResult.
    """
    name: TrainingMetricName
    step: int = Field(ge=0)
    value: float
    units: str | None = None
    seed: int | None = Field(default=None, ge=0, description='None for an explicitly aggregated sample')


class PolicyArtifact(Contract):
    """Loadable policy plus its inference semantics, not just network weights.

    preprocessing is required, including an explicit identity declaration when
    unused. It holds/references normalization and other input/output transforms.
    Concrete weight formats/loaders belong to trusted adapters. source_job points
    to a saved TrainingJob; training_configuration points to the exact saved spec.
    """
    checkpoint: EvidenceRef
    algorithm_id: Identifier
    observations: list[SignalSpec] = Field(min_length=1)
    actions: list[SignalSpec] = Field(min_length=1)
    preprocessing: Payload | EvidenceRef
    training_configuration: EvidenceRef
    source_job: EvidenceRef


class TrainingResult(Contract):
    """Training outcome, separate from formal task evaluation.

    Policy references resolve to PolicyArtifact, and best may differ from final.
    completed requires a policy artifact; its suitability still depends on gates
    and evaluation, never on a high return or process exit code. Failed/cancelled
    runs may retain useful checkpoints. Large metrics/logs stay in evidence.
    """
    job: EvidenceRef
    status: Literal['completed', 'failed', 'cancelled', 'unknown']
    best_policy: EvidenceRef | None = None
    final_policy: EvidenceRef | None = None
    metrics: list[TrainingMetric] = Field(default_factory=list)
    metrics_evidence: list[EvidenceRef] = Field(default_factory=list)
    logs: list[EvidenceRef] = Field(default_factory=list)
    gates: list[GateResult | EvidenceRef] = Field(default_factory=list)
    reason: str | None = None
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def completed_policy(self):
        if self.status == 'completed' and self.best_policy is None and self.final_policy is None:
            raise ValueError('COMPLETED_TRAINING_REQUIRES_POLICY_ARTIFACT')
        return self
