"""Independent parameter standard deviations; local geometric propagation only."""
from typing import Annotated, Literal
from pydantic import Field
from schemas.common import Contract
from schemas.public_tools import PCCJacobian

Nonnegative = Annotated[float,Field(ge=0)]


class PCCTolerance(PCCJacobian):
    length_std_m: Nonnegative
    bend_std_rad: tuple[Nonnegative,Nonnegative]


class PCCToleranceResult(Contract):
    nominal_tip_m: list[float]
    tip_covariance_m2: list[list[float]]
    tip_axis_std_m: list[float]
    rms_position_deviation_m: float
    principal_variances_m2: list[float]
    principal_directions: list[list[float]]
    parameter_contributions: list[dict]
    model: dict
    input: dict
    assumptions: list[str]
    backend_solves: Literal[0]
