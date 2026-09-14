"""Additive domain contracts, independent of frozen campaign wire schemas."""
from typing import Literal
from pydantic import Field
from schemas.common import Contract
from schemas.public_tools import PCCJacobian


class PCCCondition(PCCJacobian):
    relative_rank_tolerance: float = Field(default=1e-10,gt=0,lt=1)


class RuleQuery(Contract):
    result_ref: str
    backend: Literal['matlab','mujoco']
    rule_id: str = 'contact_presence'
    rule_version: str = '1.0.0'
    entity: str = 'contact'
    t_start_s: float | None = Field(default=None,ge=0)
    t_end_s: float | None = Field(default=None,ge=0)


class QuantityRequest(Contract):
    quantity: str
    frame: Literal['base_origin_x_forward_yz_bending'] = 'base_origin_x_forward_yz_bending'
    units: str


class Evaluation(Contract):
    status: Literal['VALID','INCOMPLETE','INVALID','REJECTED']
    score: float | None = None
    task_success: bool | None = None
    evidence_ref: str | None = None
    actual_evaluations: int = Field(default=0,ge=0)
    reason: str | None = None


class PCCConditionResult(Contract):
    singular_values_m_per_rad: list[float] = Field(min_length=2,max_length=2)
    rank: int = Field(ge=0,le=2)
    condition_number: float | None
    condition_status: Literal['FINITE','RANK_DEFICIENT']
    relative_rank_tolerance: float
    model: dict
    input: dict
    analysis_status: Literal['LOCAL_GEOMETRY_ONLY']
    backend_solves: Literal[0]
    limitations: list[str]


class SignalRuleResult(Contract):
    rule_id: str
    rule_version: str
    rule_sha256: str
    status: Literal['EVENTS_FOUND','NO_EVENT','MISSING_DATA','NOT_APPLICABLE','EXECUTION_FAILED']
    events: list[dict]
    backend_solves: Literal[0]
    rescoring: Literal[False]
    semantics: str
    reason: str | None = None
    query: dict | None = None
    source_hashes: dict[str,str] = Field(default_factory=dict)
    model: dict | None = None
