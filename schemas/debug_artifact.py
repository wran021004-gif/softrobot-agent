"""Observational debug format; never an input to scientific decisions."""
from typing import Literal
from pydantic import Field, model_validator
from schemas.common import Contract


class DebugSample(Contract):
    time_s: float
    tip_position_m: tuple[float, float, float]
    position_error_m: float
    tendon_target_lengths_m: tuple[float, ...] | None
    tendon_actual_lengths_m: tuple[float, ...]
    actuator_force_n: tuple[float, ...]
    qpos: tuple[float, ...]
    qvel: tuple[float, ...]


class DebugTrajectory(Contract):
    schema_version: Literal["1"] = "1"
    labels: tuple[Literal["DEBUG_ONLY"], Literal["NON_CANONICAL"]] = ("DEBUG_ONLY", "NON_CANONICAL")
    prohibited_uses: tuple[str, ...] = ("canonical_gate", "optimizer_ranking", "skill_admission", "causal_attribution")
    sampling: str = ("After each existing mj_step: time/qpos/qvel and independently computed current tip; "
        "tendon lengths and actuator forces are untouched mj_step work arrays from the last dynamics evaluation, "
        "not recomputed at post-integration qpos. Commands are those used for that step.")
    nq: int = Field(ge=0)
    nv: int = Field(ge=0)
    ntendon: int = Field(ge=0)
    nu: int = Field(ge=0)
    samples: tuple[DebugSample, ...]

    @model_validator(mode="after")
    def dimensions(self):
        previous = -1.
        for sample in self.samples:
            if sample.time_s <= previous:
                raise ValueError("Debug time must increase")
            previous = sample.time_s
            for key, size in (("qpos", self.nq), ("qvel", self.nv),
                              ("tendon_actual_lengths_m", self.ntendon), ("actuator_force_n", self.nu)):
                if len(getattr(sample, key)) != size:
                    raise ValueError("Debug dimension mismatch: " + key)
            if sample.tendon_target_lengths_m is not None and len(sample.tendon_target_lengths_m) != self.nu:
                raise ValueError("Debug command dimension mismatch")
        return self
