from pydantic import Field
from schemas.common import Contract


class TaskSpec(Contract):
    task_id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    task_type: str
    environment_id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    target_m: list[float] = Field(min_length=3, max_length=3)
    position_error_max_m: float = Field(ge=0)
