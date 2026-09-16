from typing import Literal
from pydantic import Field
from schemas.common import Contract


class PeakInput(Contract):
    values_n: list[float] = Field(min_length=1)


class PeakOutput(Contract):
    validity: Literal["valid"] = "valid"
    peak_n: float
