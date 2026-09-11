"""Resolved single-section structure shared by numerical adapters."""
import math
from typing import Literal
from pydantic import Field, model_validator
from schemas.common import Contract
from schemas.settings import PhysicsSpec


class SectionIR(Contract):
    length_m: float = Field(gt=0)
    segments: int = Field(gt=0, strict=True)
    segment_length_m: float = Field(gt=0)
    body_radius_m: float = Field(gt=0)
    # V1 has no independently modeled backbone radius or continuum material law.
    backbone_radius_m: None = None


class TendonRoute(Contract):
    index: int = Field(ge=0, strict=True)
    angle_rad: float
    offset_yz_m: tuple[float, float]


class RobotIR(Contract):
    schema_version: Literal["1"] = "1"
    robot_family: Literal["tendon_driven_continuum"]
    units: Literal["SI"] = "SI"
    coordinate_frame: Literal["world_base_x_forward_yz_cross_section"] = "world_base_x_forward_yz_cross_section"
    base_position_m: tuple[Literal[0.0], Literal[0.0], Literal[0.0]] = (0.0, 0.0, 0.0)
    section: SectionIR
    tendon_routing_radius_m: float = Field(gt=0)
    tendon_routes: tuple[TendonRoute, ...] = Field(min_length=1)
    mechanics: PhysicsSpec
    physics_contracts: tuple[str, ...]
    compiler_version: Literal["design_to_ir_v1"] = "design_to_ir_v1"

    @model_validator(mode="after")
    def structural_consistency(self):
        section = self.section
        if section.segment_length_m != section.length_m / section.segments:
            raise ValueError("IR segment discretization does not match section length")
        for i, route in enumerate(self.tendon_routes):
            angle = 2 * math.pi * i / self.tendon_count
            offsets = (self.tendon_routing_radius_m * math.cos(angle), self.tendon_routing_radius_m * math.sin(angle))
            if route.index != i or route.angle_rad != angle or route.offset_yz_m != offsets:
                raise ValueError("IR violates tendon ordering/routing contract")
        return self

    @property
    def sections(self):
        return 1

    @property
    def segments(self):
        return self.section.segments

    @property
    def total_length_m(self):
        return self.section.length_m

    @property
    def body_radius_m(self):
        return self.section.body_radius_m

    @property
    def tendon_count(self):
        return len(self.tendon_routes)
