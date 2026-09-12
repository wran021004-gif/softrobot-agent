"""Model evidence never fills a canonical result slot."""
from typing import Literal
from pydantic import Field, JsonValue, model_validator
from schemas.common import Contract
from schemas.experiment_policy import Fidelity


class CandidateEvaluation(Contract):
    candidate_id: str
    parent_experiment_id: str
    policy_id: str
    policy_hash: str
    task_contract_id: str
    scope: Literal["HUMAN_APPROVED", "TEST_ONLY"]
    fidelity: Fidelity
    controller_level: Literal["C1", "C2"]
    design_hash: str
    run_id: str | None = None
    run_manifest_hash: str | None = None
    robot_ir_hash: str | None = None
    status: str
    model_metrics: dict[str, JsonValue] = Field(default_factory=dict)
    canonical_metrics: dict[str, JsonValue] = Field(default_factory=dict)
    canonical_task_status: Literal["PASS", "TASK_FAILED", "NOT_RUN"] = "NOT_RUN"
    failure_message: str | None = None

    @model_validator(mode="after")
    def authority(self):
        if self.fidelity != "MUJOCO" and (self.canonical_metrics or self.canonical_task_status != "NOT_RUN"):
            raise ValueError("Model evidence is not canonical")
        if self.canonical_task_status != "NOT_RUN":
            if self.canonical_metrics.get("task_success") is not (self.canonical_task_status == "PASS"):
                raise ValueError("Canonical status requires actual task_success evidence")
            if not self.run_id or not self.run_manifest_hash or not self.robot_ir_hash:
                raise ValueError("Canonical result requires executed run provenance")
        return self
