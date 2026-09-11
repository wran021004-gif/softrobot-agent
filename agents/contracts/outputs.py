from typing import Literal
from pydantic import Field, model_validator
from schemas.common import Contract
from schemas.design_spec import DesignSpec
from schemas.failure_taxonomy import FailureCategory


class EngineerOutput(Contract):
    design_hypothesis: DesignSpec | None = None
    rationale: str
    requested_model_level: Literal["M0", "M1", "M2", "M3"]
    requested_control_level: Literal["C0", "C1", "C2", "C3"]
    requested_tools: tuple[str, ...] = ()
    optimization_variables: tuple[str, ...] = ()
    decision: Literal["execute", "stop", "escalate"]

    @model_validator(mode="after")
    def authorized_variables(self):
        if self.optimization_variables:
            from agents.contracts.optimization import validate_optimization_variables
            if self.design_hypothesis is None:
                raise ValueError("Optimization selection requires a design hypothesis")
            validate_optimization_variables(self.design_hypothesis.robot_family, self.optimization_variables)
        return self


class CodingOutput(Contract):
    approved_contracts: tuple[str, ...]
    changed_files: tuple[str, ...]
    tests_run: tuple[str, ...]
    proposal_paths: tuple[str, ...] = ()
    implementation_status: Literal["ready_for_review", "blocked"]


class FailureHypothesis(Contract):
    hypothesis: str
    evidence_paths: tuple[str, ...] = Field(min_length=1)


class DiagnosisOutput(Contract):
    failure_hypotheses: tuple[FailureHypothesis, ...]
    diagnostic_tests: tuple[str, ...]
    failure_attribution: FailureCategory
    recommended_repair_target: str
    # No task_success field: diagnosis cannot set or override the task gate.
