"""Human-owned gate meaning; no caller-selectable route policy or Agent override.

HARD certifies input/execution legality or a necessary condition under the stated
contract, never unconditional physical impossibility. SCREENING is a prediction.
CANONICAL applies the selected task evaluator; benchmark approval is separate.
"""
from enum import Enum


class GateType(str, Enum):
    HARD = "HARD"
    SCREENING = "SCREENING"
    CANONICAL = "CANONICAL"


def gate_action(gate_type, decision):
    """Fixed deterministic default; historical untyped evidence has no authority."""
    if gate_type is None:
        return "LEGACY_UNTYPED"
    if decision == "NOT_RUN":
        return "NOT_RUN"
    if decision == "PASS":
        return "CONTINUE" if gate_type != GateType.CANONICAL else "ACCEPT_METRIC"
    return {GateType.HARD: "STOP", GateType.SCREENING: "CONTINUE",
            GateType.CANONICAL: "TASK_FAILED"}[GateType(gate_type)]
