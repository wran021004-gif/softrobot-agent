from typing import Literal
from pydantic import Field
from schemas.common import Contract


class RunRecord(Contract):
    run_id: str
    timestamp: str
    git_commit: str | None
    git_dirty: bool | None
    python_version: str
    matlab_version: str | None = None
    mujoco_version: str | None = None
    task_hash: str | None = None
    environment_hash: str | None = None
    design_hash: str | None = None
    robot_ir_hash: str | None = None
    capability_version: str = "harness_v1"
    tool_version: str = "harness_v1"
    model_level: str = "M1"
    control_level: str = "C1"
    random_seed: int | None = None
    final_status: str = "RUNNING"
    failure_code: str | None = None
    failure_category: str | None = None
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    source_hashes: dict[str, str] = Field(default_factory=dict)
    hash_algorithm: Literal["sha256_file_bytes"] = "sha256_file_bytes"
