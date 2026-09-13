from pydantic import Field, model_serializer
from schemas.common import Contract
from schemas.exploration import ExplorationPhysics


class DesignSpec(Contract):
    robot_family: str
    sections: int = Field(gt=0, strict=True)
    segments: int = Field(gt=0, strict=True)
    total_length_m: float = Field(gt=0)
    body_radius_m: float = Field(gt=0)
    tendon_count: int = Field(gt=0, strict=True)
    tendon_routing_radius_m: float = Field(gt=0)
    exploration_physics: ExplorationPhysics | None = None

    @model_serializer(mode='wrap')
    def legacy_bytes(self,handler):
        data=handler(self)
        if self.exploration_physics is None:data.pop('exploration_physics',None)
        return data
