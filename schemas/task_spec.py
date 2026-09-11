from pydantic import BaseModel, Field


class TaskSpec(BaseModel):
    task_id: str
    task_type: str
    environment_id: str
    target_m: list[float] = Field(min_length=3, max_length=3)
    position_error_max_m: float
