from typing import Annotated, Literal
from pydantic import Field
from schemas.common import Contract


class ControlSpec(Contract):
    controller: str
    level: Literal["C0", "C1", "C2", "C3"]
    command_source: str


class ControlCommand(Contract):
    tendon_target_lengths_m: tuple[Annotated[float, Field(gt=0)], ...] = Field(min_length=1)


class ControllerResult(Contract):
    status: Literal["pass", "fail"]
    spec: ControlSpec
    command: ControlCommand | None = None
    failure_code: str | None = None
