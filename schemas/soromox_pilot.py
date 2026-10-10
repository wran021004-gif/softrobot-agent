"""Bounded admission pilot, distinct from closed-loop design acceptance."""
from typing import Literal
from pydantic import Field
from schemas.common import Contract
from schemas.platform import EvidenceRef


class Operation(Contract):
    case: Literal['A', 'B'] = 'A'


class Solve(Operation):
    initialization: Literal['pretension_0_2', 'ramp_0_2_to_0_4'] = 'pretension_0_2'


class Replay(Operation):
    candidate: EvidenceRef


class WorkerInput(Contract):
    configuration: dict
    dimensions: dict
    implementation: str


class WorkerOutput(Contract):
    gate: Literal['model_incompatible', 'check_failed']
    reasons: list[str] = Field(min_length=1)
    checks: dict
    costs_s: dict[str, float]
    versions: dict[str, str]
    sources: dict


class Feedback(Contract):
    problem_identity: str
    model_identity: str
    implementation_identity: str
    candidate_identity: str | None = None
    evidence_identity: str
    operation: Literal['describe', 'solve', 'replay']
    case: Literal['A', 'B']
    status: Literal['model_incompatible', 'check_failed', 'entry_gate_rejected', 'candidate_rejected']
    termination_reason: str
    iterations: int = 0
    objective_components: dict = Field(default_factory=dict)
    normalized_constraint_violations: dict = Field(default_factory=dict)
    largest_residuals: list[dict] = Field(default_factory=list)
    design_values: dict
    active_bounds: list[str] = Field(default_factory=list)
    derivative_check: dict
    replay: dict
    model_feasibility: Literal['not_established'] = 'not_established'
    physical_validation: Literal['not_run'] = 'not_run'
    consumption: dict
    remaining_budget: dict
    full_artifacts: list[EvidenceRef]
