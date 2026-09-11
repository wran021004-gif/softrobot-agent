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
        print("[4] M0 geometric workspace analysis...", flush=True)
        workspace = matlab_tools.analyze_workspace(design, task)
        if workspace.metrics:
            print("Target reachable:", workspace.metrics["target_reachable"])
            print("Target distance:", workspace.metrics["target_distance_m"])
            print("Max reach:", workspace.metrics["max_reach_m"])
            print("Reach margin:", workspace.metrics["reach_margin_m"])
        if workspace.status != "pass":
            print("FAIL:", workspace.failure_code)
            return 1

        print("[5] M1 PCC reach planning...", flush=True)
        plan = matlab_tools.plan_pcc_reach(design, task)
        if plan.status != "pass":
            print("FAIL:", plan.failure_code, plan.message)
            return 1
        print("Theta:", plan.metrics["theta_rad"], "rad")
        print("Phi:", plan.metrics["phi_rad"], "rad")
        print("PCC predicted tip:", plan.metrics["predicted_tip_m"])
        print("PCC predicted error:", plan.metrics["predicted_position_error_m"], "m")
        print("PCC model task success:", plan.metrics["model_task_success"])
        print("Tendon target lengths:", plan.metrics["tendon_target_lengths_m"])

        print("[6] Compiling tendon-driven MuJoCo model...", flush=True)
        compiled = compile_mujoco(
            design, task, PROJECT_ROOT / "mujoco/generated" / f"{task.task_id}.xml",
        )
        if compiled.status != "pass":
            print("FAIL:", compiled.failure_code, compiled.message)
            return 1
        print("Generated:", compiled.artifacts["mjcf_path"])

        print("[7] Running MuJoCo tendon task validation...", flush=True)
        validation = validate_task(
            compiled.artifacts["mjcf_path"], task,
            tendon_target_lengths_m=plan.metrics["tendon_target_lengths_m"],
        )
        if "task_success" in validation.metrics:
            print("Steps:", validation.metrics["steps"])
            print("Tip position:", validation.metrics["tip_position_m"])
            print("Target position:", validation.metrics["target_position_m"])
            print("Position error:", validation.metrics["position_error_m"], "m")
            print("Allowed error:", validation.metrics["position_error_max_m"], "m")
            print("Task success:", validation.metrics["task_success"])
            print("Final tendon lengths:", validation.metrics["final_tendon_lengths_m"])
            print("Actuator controls:", validation.metrics["actuator_controls"])
            print("Actuator force:", validation.metrics["actuator_force"])
        print("Failure code:", validation.failure_code)
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
