from pydantic import Field
from schemas.common import Contract


class DesignSpec(Contract):
    robot_family: str
    sections: int = Field(gt=0, strict=True)
    segments: int = Field(gt=0, strict=True)
    total_length_m: float = Field(gt=0)
    body_radius_m: float = Field(gt=0)
    tendon_count: int = Field(gt=0, strict=True)
    tendon_routing_radius_m: float = Field(gt=0)
