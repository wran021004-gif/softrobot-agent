"""Human-owned experimental authority, separate from task and candidate truth."""
from typing import Literal
from pydantic import Field, model_validator
from schemas.common import Contract

Fidelity = Literal["M0", "M1", "MUJOCO"]
RepairAction = Literal["next_candidate", "optimize_design", "synthesize_feedback", "run_parameter_sensitivity"]


class SearchVariable(Contract):
    name: str
    unit: str
    lower_bound: float
    upper_bound: float
    constraints: tuple[Literal["positive", "integer"], ...] = ()

    @model_validator(mode="after")
    def bounds(self):
        if self.lower_bound > self.upper_bound:
            raise ValueError("Reversed search bounds")
        if "positive" in self.constraints and self.lower_bound <= 0:
            raise ValueError("Positive bounds required")
        if "integer" in self.constraints and any(int(v) != v for v in (self.lower_bound, self.upper_bound)):
            raise ValueError("Integer bounds required")
        return self


class FeedbackParameters(Contract):
    """No numerical defaults: all experimental numbers require a policy source."""
    gain_rad2_per_m2: float = Field(gt=0)
    update_every_steps: int = Field(gt=0, strict=True)
    max_bend_update_rad: float = Field(gt=0)
    max_command_update_m: float = Field(gt=0)
    min_tendon_length_m: float = Field(gt=0)
    max_tendon_length_m: float = Field(gt=0)

    @model_validator(mode="after")
    def bounds(self):
        if self.min_tendon_length_m > self.max_tendon_length_m:
            raise ValueError("Reversed controller command bounds")
        return self


class ExperimentPolicy(Contract):
    authorization_mode: Literal['HUMAN_POLICY', 'ENVELOPE_SUBSET'] = 'HUMAN_POLICY'
    purpose: Literal['DESIGN_SEARCH', 'NUMERICAL_SENSITIVITY'] = 'DESIGN_SEARCH'
    physics_profile: Literal['legacy_v1_surrogate'] = 'legacy_v1_surrogate'
    policy_id: str = Field(min_length=1)
    task_contract_id: str
    task_contract_source: str
    baseline_design: str
    scientific_status: Literal["PROPOSED", "HUMAN_APPROVED", "TEST_ONLY"]
    approval_status: Literal["HUMAN_APPROVAL_REQUIRED", "HUMAN_APPROVED", "TEST_ONLY"]
    approval_source: str | None = None
    variables: tuple[SearchVariable, ...] = ()
    objective_metric_refs: tuple[Literal["model.predicted_position_error_m", "mujoco.position_error_m"], ...] = ()
    evaluation_budget: int | None = Field(default=None, gt=0, strict=True)
    seed: int | None = Field(default=None, ge=0, strict=True)
    allowed_model_levels: tuple[Literal["M0", "M1"], ...] = ()
    allowed_controller_levels: tuple[Literal["C1", "C2"], ...] = ()
    feedback_parameters: FeedbackParameters | None = None
    controller_parameter_bounds: tuple[SearchVariable, ...] = ()
    mujoco_validation_budget: int | None = Field(default=None, ge=0, strict=True)
    repair_iteration_budget: int | None = Field(default=None, ge=0, strict=True)
    repair_actions: tuple[RepairAction, ...] = ()
    stop_conditions: tuple[Literal["budget_exhausted", "canonical_success", "actions_exhausted"], ...] = ()

    @model_validator(mode="after")
    def consistent(self):
        expected = {"PROPOSED": "HUMAN_APPROVAL_REQUIRED", "HUMAN_APPROVED": "HUMAN_APPROVED", "TEST_ONLY": "TEST_ONLY"}
        if self.approval_status != expected[self.scientific_status]:
            raise ValueError("Scientific/approval status mismatch")
        if len({v.name for v in self.variables}) != len(self.variables):
            raise ValueError("Duplicate variables")
        if self.controller_parameter_bounds:
            raise ValueError("IMPLEMENTATION_REQUIRED: controller tuning search; Round 3 supports explicit fixed parameters only")
        if self.scientific_status != "PROPOSED":
            if any(v is None for v in (self.evaluation_budget, self.seed, self.mujoco_validation_budget, self.repair_iteration_budget)):
                raise ValueError("Explicit budgets and seed required")
            if not self.approval_source or not self.allowed_model_levels or not self.allowed_controller_levels:
                raise ValueError("Explicit authority and executable routes required")
            if self.mujoco_validation_budget > self.evaluation_budget:
                raise ValueError("MuJoCo budget exceeds total evaluation budget")
            if not {"budget_exhausted", "actions_exhausted"}.issubset(self.stop_conditions):
                raise ValueError("Explicit finite stop conditions required")
            if ("C2" in self.allowed_controller_levels) != (self.feedback_parameters is not None):
                raise ValueError("C2 requires exact sourced feedback parameters")
            if "synthesize_feedback" in self.repair_actions and "C2" not in self.allowed_controller_levels:
                raise ValueError("Feedback repair requires an authorized C2 route")
            if set(self.repair_actions) & {"next_candidate", "optimize_design", "run_parameter_sensitivity"} and not self.variables:
                raise ValueError("Design/sensitivity repair requires selected variables")
        return self
