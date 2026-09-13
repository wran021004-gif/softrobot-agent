"""Round 9 equivalent, uncalibrated physical design; SI throughout."""
import math
from typing import Literal
from pydantic import Field, model_validator
from schemas.common import Contract


class ExplorationPhysics(Contract):
    profile: Literal['equivalent_rod_v2'] = 'equivalent_rod_v2'
    validated: Literal[False] = False
    mass_mode: Literal['uniform_equivalent_cylinder'] = 'uniform_equivalent_cylinder'
    line_density_kg_m: float = Field(default=1.2566370614359172, ge=.02, le=3)
    root_ei_nm2: float = Field(default=.00375, ge=1e-4, le=1)
    tip_ei_ratio: float = Field(default=1, ge=.1, le=3)
    bending_viscosity_nm2_s: float = Field(default=.00375, ge=1e-6, le=.05)
    natural_total_angle_rad: float = Field(default=0, ge=-math.pi, le=math.pi)
    tendon_servo_kp_n_per_m: float = Field(default=1000, ge=100, le=20000)
    tendon_force_limit_n: float = Field(default=20, ge=5, le=80)


class ExplorationControl(Contract):
    version: Literal['length_control_v2'] = 'length_control_v2'
    mode: Literal['C1', 'C2'] = 'C1'
    bend_y_rad: float = Field(default=0, ge=-math.pi, le=math.pi)
    bend_z_rad: float = Field(default=1.073643020187874, ge=-math.pi, le=math.pi)
    bias_fraction: float = Field(default=0, ge=-.02, le=.05)
    gain_rad2_per_m2: float = Field(default=5, ge=0, le=100)
    update_every_steps: int = Field(default=10, ge=1, le=100, strict=True)
    max_bend_update_rad: float = Field(default=.05, gt=0, le=.2)
    rate_limit_ref_per_s: float = Field(default=.5, gt=0, le=2)

    @model_validator(mode='after')
    def norm(self):
        if math.hypot(self.bend_y_rad, self.bend_z_rad) > math.pi:
            raise ValueError('PCC feedback internal bend vector norm must be <= pi')
        if self.mode=='C2' and self.gain_rad2_per_m2<=0:
            raise ValueError('C2 feedback requires a positive gain; use C1 for fixed commands')
        return self


class ResolvedRod(Contract):
    mass_kg: tuple[float, ...]
    inertia_diagonal_kg_m2: tuple[tuple[float, float, float], ...]
    stiffness_nm_rad: tuple[float, ...]
    damping_nm_s_rad: tuple[float, ...]
    natural_y_rad: tuple[float, ...]
    derivation: Literal['k=EI/ds; c=viscosity/ds; natural_y=-total/n; m=lambda*ds; cylinder_inertia'] = 'k=EI/ds; c=viscosity/ds; natural_y=-total/n; m=lambda*ds; cylinder_inertia'
