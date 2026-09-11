from typing import Literal
from pydantic import Field, model_validator
from schemas.common import Contract


class WindowAcceptance(Contract):
    """Minimal executable acceptance; defaults preserve Round 2 development only.

    before_window means every robot capsule, including radius, is strictly before
    the near wall face at the initial sampled pose. No initializer is implied.
    """
    initial_robot_region: Literal["before_window", "unrestricted"] = "unrestricted"
    final_aperture_required: Literal[True] = True
    window_contact_policy: Literal["forbid"] = "forbid"
    final_robot_region: Literal["unrestricted"] = "unrestricted"
    randomization: Literal["none"] = "none"


class TaskSpec(Contract):
    task_id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    task_type: str
    environment_id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    target_m: list[float] = Field(min_length=3, max_length=3)
    position_error_max_m: float = Field(ge=0)
    acceptance: WindowAcceptance | None = None

    @model_validator(mode="after")
    def acceptance_matches_task(self):
        if self.acceptance is not None and self.task_type != "reach_window":
            raise ValueError("Window acceptance is only supported for reach_window")
        return self

    def window_acceptance(self):
        return self.acceptance or WindowAcceptance()
