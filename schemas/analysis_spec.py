"""Scoped SI inputs for independent reduced mechanics, never a main PhysicsSpec."""
from typing import Literal
from pydantic import Field,model_validator
from schemas.common import Contract


class AnalysisSpec(Contract):
    operation: Literal['static','dynamic','fit']
    n: int = Field(ge=4,le=24)
    length_m: float = Field(gt=0,le=.8)
    offset_yz_m: list[tuple[float,float]]
    mass_kg: list[float]
    inertia_y_kg_m2: list[float]
    stiffness_nm_rad: list[float]
    damping_nm_s_rad: list[float]
    gravity_m_s2: tuple[float,float,float]
    tension_n: list[float]
    tip_force_n: tuple[float,float,float]
    stiffness_scale: float = Field(ge=.5,le=2)
    damping_scale: float = Field(ge=.5,le=2)
    source: dict
    duration_s: float = Field(default=2,gt=0,le=4)
    sample_dt_s: float = Field(default=.01,ge=.001,le=.1)
    initial_q_rad: float = Field(default=0,ge=-2.8,le=2.8)
    initial_velocity_rad_s: float = Field(default=0,ge=-10,le=10)
    pulse_start_s: float | None = None
    pulse_end_s: float | None = None
    pulse_force_n: tuple[float,float,float] | None = None
    pulse_tension_n: list[float] | None = None
    input_time_s: list[float] | None = None
    input_tension_n: list[list[float]] | None = None
    train_q_rad: list[float] | None = None
    train_force_n: list[float] | None = None
    validation_q_rad: list[float] | None = None
    validation_force_n: list[float] | None = None

    @model_validator(mode='after')
    def physical_inputs(self):
        import math
        for values in (self.mass_kg,self.inertia_y_kg_m2,self.stiffness_nm_rad,self.damping_nm_s_rad):
            if len(values)!=self.n or any(not math.isfinite(x) or x<=0 for x in values):
                raise ValueError('Positive finite compiled parameters required')
        if self.tip_force_n[1]!=0 or self.gravity_m_s2[1]!=0:
            raise ValueError('Only planar xz loads are supported')
        if not 3<=len(self.tension_n)<=8 or len(self.offset_yz_m)!=len(self.tension_n):
            raise ValueError('Tendon shape mismatch')
        if any(not math.isfinite(x) or not 0<=x<=20 for x in self.tension_n):
            raise ValueError('Nonnegative bounded tension required')
        if self.pulse_start_s is not None:
            if not (self.pulse_end_s is not None and 0<=self.pulse_start_s<self.pulse_end_s<=self.duration_s
                and self.pulse_force_n is not None and self.pulse_force_n[1]==0
                and self.pulse_tension_n is not None and len(self.pulse_tension_n)==len(self.tension_n)):
                raise ValueError('Invalid pulse')
        if self.input_time_s is not None:
            if self.input_tension_n is None or len(self.input_tension_n)!=len(self.input_time_s) or any(b<=a for a,b in zip(self.input_time_s,self.input_time_s[1:])):
                raise ValueError('Invalid force replay time series')
            if any(len(row)!=len(self.tension_n) or any(not 0<=v<=20 for v in row) for row in self.input_tension_n):
                raise ValueError('Invalid force replay tensions')
        return self
