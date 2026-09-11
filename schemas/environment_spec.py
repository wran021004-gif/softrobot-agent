from typing import Annotated, Literal
from pydantic import Field, model_validator
from schemas.common import Contract

Vec3 = tuple[float, float, float]


class Plane(Contract):
    kind: Literal["plane"] = "plane"
    name: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    position_m: Vec3
    half_size_m: tuple[Annotated[float, Field(gt=0)], Annotated[float, Field(gt=0)], Annotated[float, Field(gt=0)]]
    contype: int = Field(ge=0)
    conaffinity: int = Field(ge=0)


class Window(Contract):
    """Finite rectangular frame; aperture in the world y-z plane, normal +x."""
    kind: Literal["window"] = "window"
    name: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    position_m: Vec3
    plane: Literal["yz_normal_positive_x"]
    width_m: float = Field(gt=0)
    height_m: float = Field(gt=0)
    thickness_m: float = Field(gt=0)
    frame_width_m: float = Field(gt=0)
    contype: Literal[0] = 0
    conaffinity: Literal[1] = 1


class ReservedComponent(Contract):
    """Serializable extension proposals; no execution support in V1."""
    kind: Literal["ball", "ramp", "platform_disturbance"]
    name: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    position_m: Vec3
    status: Literal["PLANNED"] = "PLANNED"


class Light(Contract):
    position_m: Vec3
    direction: Vec3


class EnvironmentSpec(Contract):
    schema_version: Literal["1"] = "1"
    environment_id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    units: Literal["SI"] = "SI"
    coordinate_frame: Literal["world_base_x_forward_yz_cross_section"]
    gravity_m_s2: Vec3
    gravity_source: str = Field(min_length=1)
    truth_status: Literal["HUMAN_OWNED", "HUMAN_APPROVED", "NON_CANONICAL_DEVELOPMENT_ONLY"] = "HUMAN_OWNED"
    objects: tuple[Annotated[Plane | Window | ReservedComponent, Field(discriminator="kind")], ...]
    lights: tuple[Light, ...] = ()

    @model_validator(mode="after")
    def unique_names(self):
        names = [obj.name for obj in self.objects]
        if len(names) != len(set(names)):
            raise ValueError("Environment object names must be unique")
        return self
