"""Bounded execution audit contracts. Rationale means a short public explanation."""
import json
from enum import Enum
from typing import Literal
from pydantic import AwareDatetime, Field, JsonValue, model_validator
from schemas.common import Contract
from schemas.evidence import ArtifactReference, Identifier
from schemas.gate import GateType


class Actor(str, Enum):
    HUMAN = "human"
    HARNESS = "harness"
    TOOL = "tool"
    GATE = "gate"
    ENGINEER = "engineer_agent"
    CODING = "coding_agent"
    DIAGNOSIS = "diagnosis_agent"
    SKILL = "skill_system"


class EventType(str, Enum):
    RUN_STARTED = "RUN_STARTED"
    RUN_FINISHED = "RUN_FINISHED"
    STAGE_STARTED = "STAGE_STARTED"
    STAGE_FINISHED = "STAGE_FINISHED"
    SPEC_VALIDATED = "SPEC_VALIDATED"
    CAPABILITY_RESOLVED = "CAPABILITY_RESOLVED"
    TOOL_STARTED = "TOOL_STARTED"
    TOOL_FINISHED = "TOOL_FINISHED"
    TOOL_FAILED = "TOOL_FAILED"
    GATE_EVALUATED = "GATE_EVALUATED"
    CONTROL_SELECTED = "CONTROL_SELECTED"
    CONTROL_APPLIED = "CONTROL_APPLIED"
    DIAGNOSTIC_STARTED = "DIAGNOSTIC_STARTED"
    DIAGNOSTIC_FINISHED = "DIAGNOSTIC_FINISHED"
    DECISION_RECORDED = "DECISION_RECORDED"
    REPAIR_PROPOSED = "REPAIR_PROPOSED"
    REPAIR_APPLIED = "REPAIR_APPLIED"
    ARTIFACT_CREATED = "ARTIFACT_CREATED"
    SKILL_RETRIEVED = "SKILL_RETRIEVED"
    SKILL_PROPOSED = "SKILL_PROPOSED"


class DecisionRecord(Contract):
    actor: Actor
    decision: str = Field(min_length=1, max_length=256)
    rationale: str = Field(min_length=1, max_length=1000, description="Public rationale, never private chain-of-thought")
    requested_tools: tuple[Identifier, ...] = ()
    evidence_refs: tuple[ArtifactReference, ...] = ()
    selected_skill_refs: tuple[str, ...] = ()
    next_action: str = Field(min_length=1, max_length=256)


class GateEvidence(Contract):
    gate: Identifier
    gate_type: GateType | None = Field(default=None, description="None only for historical untyped traces; never infer scientific authority")
    input_metric: str = Field(min_length=1, max_length=128)
    value: float | bool | None
    threshold: float | bool | None
    comparison: Literal["<=", "==", "available"]
    decision: Literal["PASS", "FAIL", "NOT_RUN"]
    authority: str = Field(min_length=1, max_length=256)


def bounded_payload(value, depth=0):
    if depth > 6:
        raise ValueError("Trace payload nesting limit exceeded")
    if isinstance(value, (list, tuple, dict)):
        if isinstance(value, dict) and {str(k).casefold() for k in value} & {
                "chain_of_thought", "private_chain_of_thought", "reasoning_tokens", "internal_reasoning"}:
            raise ValueError("Private reasoning is not trace evidence")
        if len(value) > 32:
            raise ValueError("Trace payload collection limit exceeded; use artifacts")
        for item in (value.values() if isinstance(value, dict) else value):
            bounded_payload(item, depth + 1)
    elif isinstance(value, str) and len(value) > 1024:
        raise ValueError("Trace text limit exceeded; use artifacts")


class TraceEvent(Contract):
    event_id: Identifier
    run_id: Identifier
    parent_event_id: Identifier | None = None
    sequence: int = Field(ge=0, strict=True)
    timestamp: AwareDatetime
    actor: Actor
    event_type: EventType
    operation: Identifier
    status: Literal["started", "pass", "fail", "not_run", "recorded"]
    inputs: dict[str, JsonValue] = Field(default_factory=dict)
    outputs: dict[str, JsonValue] = Field(default_factory=dict)
    summary: dict[str, JsonValue] = Field(default_factory=dict)
    failure_code: str | None = Field(default=None, max_length=128)
    evidence_refs: tuple[ArtifactReference, ...] = Field(default=(), max_length=32)
    duration_s: float | None = Field(default=None, ge=0)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    gate: GateEvidence | None = None
    decision: DecisionRecord | None = None

    @model_validator(mode="after")
    def bounded_and_typed(self):
        for value in (self.inputs, self.outputs, self.summary, self.metadata):
            bounded_payload(value)
        if len(json.dumps(self.model_dump(mode="json"), allow_nan=False).encode("utf-8")) > 16384:
            raise ValueError("Trace event exceeds 16 KiB; reference artifacts")
        if (self.event_type == EventType.GATE_EVALUATED) != (self.gate is not None):
            raise ValueError("GATE_EVALUATED requires structured gate evidence exclusively")
        if (self.event_type == EventType.DECISION_RECORDED) != (self.decision is not None):
            raise ValueError("DECISION_RECORDED requires DecisionRecord exclusively")
        if self.decision and self.decision.actor != self.actor:
            raise ValueError("Decision actor mismatch")
        if self.gate and (self.actor != Actor.GATE or self.status != {
                "PASS": "pass", "FAIL": "fail", "NOT_RUN": "not_run"}[self.gate.decision]):
            raise ValueError("Gate actor/status mismatch")
        return self
