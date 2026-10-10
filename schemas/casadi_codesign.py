"""Results for the executed CasADi pilot; historical admission stays unchanged."""
from typing import Literal
from pydantic import Field
from schemas.common import Contract
from schemas.platform import EvidenceRef


class Solve(Contract):
    case: Literal['A', 'B']
    initialization: Literal['pretension_0_2', 'ramp_0_2_to_0_4'] = 'pretension_0_2'
    substeps: Literal[1, 2] = 1
    category: Literal['primary', 'paired_second', 'correction'] = 'primary'
    jacobian_mode: Literal['reverse', 'automatic'] = 'reverse'


class Replay(Contract):
    candidate: EvidenceRef


class Check(Contract):
    scope: Literal['mechanics_reference', 'jacobian_execution'] = 'mechanics_reference'


class Feedback(Contract):
    operation: Literal['check', 'solve', 'replay']
    problem_identity: str
    implementation_identity: str
    candidate_identity: str | None = None
    evidence_identity: str
    case: Literal['A', 'B'] | None = None
    status: str
    termination_reason: str
    iterations: int = 0
    design_values: dict = Field(default_factory=dict)
    objective_components: dict = Field(default_factory=dict)
    largest_residuals: list[dict] = Field(default_factory=list)
    derivative_check: dict = Field(default_factory=dict)
    replay: dict = Field(default_factory=dict)
    mathematical_feasibility: str = 'not_established'
    physical_validation: str = 'not_run'
    trajectory: EvidenceRef | None = None
    full_artifacts: list[EvidenceRef]
    consumption: dict
    remaining_budget: dict
