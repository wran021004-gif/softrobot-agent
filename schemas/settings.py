from typing import Literal
from pydantic import Field
from schemas.common import Contract


class PhysicsSpec(Contract):
    profile: Literal["legacy_v1_surrogate"]
    provenance: str
    validated: Literal[False]
    joint_stiffness_nm_per_rad: float = Field(gt=0)
    joint_damping_nm_s_per_rad: float = Field(ge=0)
    body_density_kg_m3: float = Field(gt=0)
    tendon_servo_kp_n_per_m: float = Field(gt=0)
    tendon_force_limit_n: float = Field(gt=0)


class SimulatorSpec(Contract):
    profile: Literal["legacy_v1"] = "legacy_v1"
    timestep_s: float = Field(gt=0)
    provenance: str


class RunSettings(Contract):
    steps: int = Field(gt=0, strict=True)
    random_seed: int = Field(ge=0, strict=True)
    provenance: str
