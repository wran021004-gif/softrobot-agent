from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    status: str
    tool: str
    failure_code: str | None = None
    metrics: dict = Field(default_factory=dict)
    artifacts: dict = Field(default_factory=dict)
    message: str | None = None
