"""Transport-neutral public contracts. Caller identity belongs to the host."""
import math
from typing import Literal
from pydantic import Field, model_validator
from schemas.common import Contract


class ToolCall(Contract):
    contract_version: Literal['1.0'] = '1.0'
    tool_id: str = Field(min_length=1)
    tool_version: Literal['1.0.0','1.1.0'] = '1.1.0'
    arguments: dict = Field(default_factory=dict)
    reason: str = Field(min_length=1, max_length=4000)
    evidence: list[str] = Field(default_factory=list)


class Caller(Contract):
    actor_id: str = Field(min_length=1, max_length=200)
    origin: Literal['human_cli', 'agent', 'development', 'legacy_unknown']
    transport: str = 'python'
    model_request_index: int | None = None


class PCCJacobian(Contract):
    length_m: float = Field(gt=0, description='Positive arc length in meters; geometry only, no design authorization.')
    bend_rad: tuple[float, float] = Field(description='[theta*cos(phi), theta*sin(phi)] in radians; norm <= pi.')
    frame: Literal['base_origin_x_forward_yz_bending'] = 'base_origin_x_forward_yz_bending'

    @model_validator(mode='after')
    def branch(self):
        if math.hypot(*self.bend_rad) > math.pi:
            raise ValueError('PCC branch requires norm(bend_rad) <= pi')
        return self


class EvidenceRef(Contract):
    ref: str
    sha256: str | None = None
    role: Literal['input', 'output', 'detail'] = 'output'


class ToolError(Contract):
    category: Literal['input', 'permission', 'budget', 'evidence', 'dependency', 'timeout', 'interrupted', 'execution']
    code: str
    message: str
    retryable: bool = False
    recovery_condition: str
    next_actions: list[str]


class PublicResult(Contract):
    contract_version: Literal['1.0'] = '1.0'
    tool_id: str
    tool_version: Literal['1.0.0','1.1.0'] = '1.1.0'
    call_id: str
    caller: Caller
    execution_status: Literal['completed', 'failed', 'rejected', 'interrupted', 'capability_missing']
    solver_status: Literal['NOT_APPLICABLE','NOT_RUN','COMPLETED','INCOMPLETE','FAILED','UNKNOWN'] = 'NOT_APPLICABLE'
    analysis_status: str = 'NOT_ASSESSED'
    task_status: str = 'NOT_ASSESSED'
    summary: str
    error: ToolError | None = None
    evidence: list[EvidenceRef] = Field(default_factory=list)
    cost: dict = Field(default_factory=dict)
    provenance: dict = Field(default_factory=dict)
    epistemics: dict = Field(default_factory=dict)
    details_ref: str | None = None


class ServiceConfig(Contract):
    """Independent offline profile; cannot grant dynamics, scoring or model calls."""
    profile_id: str = Field(min_length=1)
    permissions: list[Literal['analysis', 'read_evidence', 'derived_artifacts']]
    tool_calls: int = Field(ge=0)


class SavedDiagnosis(Contract):
    result_ref: str
    backend: Literal['matlab','mujoco']
    entity: str = 'all'
    t_start_s: float | None = Field(default=None,ge=0)
    t_end_s: float | None = Field(default=None,ge=0)
    fields: list[str] = Field(default_factory=list,max_length=8)

    @model_validator(mode='after')
    def interval(self):
        if self.t_start_s is not None and self.t_end_s is not None and self.t_end_s < self.t_start_s:
            raise ValueError('REVERSED_TIME_INTERVAL')
        return self
