"""Independent, nonphysical development extension payloads."""
from typing import Literal
from pydantic import Field
from schemas.common import Contract


class Empty(Contract):
    pass


class AdapterParameters(Contract):
    values_m: list[float] = Field(default_factory=lambda: [3., 4.], min_length=1)


class TerminalGoal(Contract):
    target_m: float


class TerminalEvaluation(Contract):
    tolerance_m: float = Field(gt=0)


class WorkerParameters(Contract):
    delay_s: float = Field(default=0.5, ge=0, le=5)
    fail: bool = False


class MathReport(Contract):
    norm_m: float
    units: Literal['m'] = 'm'


class DiagnosticReport(Contract):
    signal_count: int = Field(ge=0)
    interpretation: Literal['saved_signal_inventory'] = 'saved_signal_inventory'


class StatefulParameters(Contract):
    candidates: list[float] = Field(min_length=1)


class StatefulState(Contract):
    proposed: int = Field(ge=0)
    feedback: list[float | None]
    rng_state: list[int]


class Value(Contract):
    value: float
