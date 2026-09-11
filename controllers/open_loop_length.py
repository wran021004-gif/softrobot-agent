import math
from schemas.control_spec import ControlSpec, ControlCommand, ControllerResult


class OpenLoopLength:
    def __init__(self, lengths, source="PCC plan_pcc_reach"):
        self.spec = ControlSpec(controller="open_loop_length", level="C1", command_source=source)
        self.target = ControlCommand(tendon_target_lengths_m=tuple(lengths))
        if not all(math.isfinite(v) and v > 0 for v in self.target.tendon_target_lengths_m):
            raise ValueError("INVALID_TENDON_COMMAND: positive finite lengths required")

    def command(self, time_s, observation):
        return self.target

    def result(self):
        return ControllerResult(status="pass", spec=self.spec, command=self.target)


def plan_open_loop(lengths) -> ControllerResult:
    return OpenLoopLength(lengths).result()
