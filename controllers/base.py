from typing import Protocol
from schemas.control_spec import ControlCommand, ControlSpec


class Controller(Protocol):
    spec: ControlSpec

    def command(self, time_s: float, observation: dict) -> ControlCommand | None:
        """None explicitly disables actuation for this step (C0)."""
        ...
