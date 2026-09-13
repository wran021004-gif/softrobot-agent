"""JSON boundary shared by deterministic policies and future model adapters."""
from typing import Literal
from pydantic import Field, model_validator
from schemas.common import Contract


class Decision(Contract):
    action: Literal['continue', 'stop', 'capability_missing']
    tool: str | None = None
    arguments: dict = Field(default_factory=dict)
    evidence: list[str] = Field(min_length=1)
    reason: str = Field(min_length=1, max_length=4000)

    @model_validator(mode='after')
    def consistent(self):
        if (self.action == 'continue') != (self.tool is not None):
            raise ValueError('Only continue selects a tool')
        if self.action != 'continue' and self.arguments:
            raise ValueError('Terminal decisions cannot carry arguments')
        return self


class NoArguments(Contract):
    pass


class EvaluationArguments(Contract):
    controller: Literal['C1'] = 'C1'


class EvidenceArguments(Contract):
    evidence_id: str = Field(min_length=1)


class WorkbenchResult(Contract):
    status: Literal['completed', 'failed', 'capability_missing', 'rejected', 'interrupted']
    tool: str
    failure_code: str | None = None
    message: str = ''
    data: dict = Field(default_factory=dict)
    artifacts: list[str] = Field(default_factory=list)
