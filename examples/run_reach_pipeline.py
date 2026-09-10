"""Run the minimal deterministic harness from the project root."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import yaml

from schemas.design_spec import DesignSpec
from schemas.task_spec import TaskSpec
from tools.matlab_tools import MatlabTools
from tools.mujoco_tools import compile_mujoco, validate_task


def main() -> int:
    print("[1] Loading task...", flush=True)
    with (PROJECT_ROOT / "configs/task_reach.yaml").open(encoding="utf-8") as stream:
        task = TaskSpec(**yaml.safe_load(stream))
    print("PASS")

    print("[2] Loading design...", flush=True)
    with (PROJECT_ROOT / "configs/design_tendon_arm.yaml").open(encoding="utf-8") as stream:
        design = DesignSpec(**yaml.safe_load(stream))
    print("PASS")

    print("[3] Starting MATLAB...", flush=True)
    matlab_tools = MatlabTools()
    try:
        print("PASS")
        print("[4] MATLAB workspace analysis...", flush=True)
        workspace = matlab_tools.analyze_workspace(design, task)
        print("Target reachable:", workspace.metrics["target_reachable"])
        print("Target distance:", workspace.metrics["target_distance_m"])
        print("Max reach:", workspace.metrics["max_reach_m"])
        print("Reach margin:", workspace.metrics["reach_margin_m"])
        if workspace.status != "pass":
            print("FAIL:", workspace.failure_code)
            return 1

        print("[5] Compiling MuJoCo model...", flush=True)
        compiled = compile_mujoco(
            design, task, PROJECT_ROOT / "mujoco/generated" / f"{task.task_id}.xml",
        )
        if compiled.status != "pass":
            print("FAIL:", compiled.failure_code, compiled.message)
            return 1
        print("Generated:", compiled.artifacts["mjcf_path"])

        print("[6] Running MuJoCo task validation...", flush=True)
        validation = validate_task(compiled.artifacts["mjcf_path"], task)
        if "task_success" in validation.metrics:
            print("Steps:", validation.metrics["steps"])
            print("Tip position:", validation.metrics["tip_position_m"])
            print("Target position:", validation.metrics["target_position_m"])
            print("Position error:", validation.metrics["position_error_m"], "m")
            print("Allowed error:", validation.metrics["position_error_max_m"], "m")
            print("Task success:", validation.metrics["task_success"])
        if validation.status != "pass":
            print("FAIL:", validation.failure_code)
            if validation.message:
                print(validation.message)
            return 1
        print("PASS")
    finally:
        matlab_tools.close()

    print("Pipeline completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
