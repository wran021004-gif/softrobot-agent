from pydantic import BaseModel


class DesignSpec(BaseModel):
    robot_family: str
    sections: int
    segments: int
    total_length_m: float
    body_radius_m: float
    tendon_count: int
    tendon_routing_radius_m: float
