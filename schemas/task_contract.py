"""Reference-only Human-owned task index; no design or scientific value payload."""
from typing import Literal
from pydantic import Field
from schemas.common import Contract


class TaskContract(Contract):
    schema_version: Literal["1"] = "1"
    contract_id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    task_type: str
    status: Literal["FROZEN", "PROPOSED_NOT_APPROVED", "DEVELOPMENT_ONLY"]
    task_source: str
    environment_source: str
    environment_representation_source: str | None = None
    design_grammar_source: str
    evaluator: str
    initial_condition_source: str
    acceptance_source: str | None = None
    run_settings_source: str
    simulator_settings_source: str
    evaluation_protocol_source: str
    gate_policy_source: str
    gate_mapping_source: str
    physics_contract_sources: tuple[str, ...]
    benchmark_id: str | None = None
    benchmark_source: str | None = None
    notes: str | None = Field(default=None, max_length=1000)
