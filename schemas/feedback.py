from typing import Literal
from pydantic import Field
from schemas.common import Contract
from schemas.experiment_policy import FeedbackParameters
from schemas.control_spec import ControlCommand


class FeedbackArtifact(Contract):
    controller: Literal["pcc_tip_feedback"] = "pcc_tip_feedback"
    level: Literal["C2"] = "C2"
    policy_id: str
    policy_hash: str
    parameter_source: str
    parameters: FeedbackParameters
    initial_command: ControlCommand
    mapping_source: Literal["tools/pcc_math.py; approved PCC and tendon mapping derivatives"] = "tools/pcc_math.py; approved PCC and tendon mapping derivatives"


class FeedbackUpdate(Contract):
    step: int = Field(ge=0, strict=True)
    time_s: float = Field(ge=0)
    observed_tip_m: tuple[float, float, float]
    error_m: tuple[float, float, float]
    bend_rad: tuple[float, float]
    command: ControlCommand
    max_command_delta_m: float = Field(ge=0)
    command_clipped: bool
