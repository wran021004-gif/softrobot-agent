from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--robot-xml", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=20)
    args = parser.parse_args()

    import mujoco

    key_present = bool(os.environ.get("DEEPSEEK_API_KEY"))
    mjmodel_present = hasattr(mujoco, "MjModel")
    if not key_present:
        raise RuntimeError("DEEPSEEK_API_KEY is unavailable to the explicit interpreter")
    if not mjmodel_present:
        raise RuntimeError("mujoco.MjModel is unavailable to the explicit interpreter")

    model = mujoco.MjModel.from_xml_path(str(args.robot_xml.resolve()))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    for _ in range(args.steps):
        mujoco.mj_step(model, data)

    finite = bool(
        np.isfinite(data.time)
        and np.all(np.isfinite(data.qpos))
        and np.all(np.isfinite(data.qvel))
    )
    if not finite:
        raise RuntimeError("local MuJoCo integration produced non-finite state")

    report = {
        "smoke_kind": "environment_only_no_deepseek",
        "python_executable": sys.executable,
        "deepseek_api_key_present": key_present,
        "mujoco_module_file": getattr(mujoco, "__file__", None),
        "mujoco_mjmodel_present": mjmodel_present,
        "robot_xml": str(args.robot_xml.resolve()),
        "model_dimensions": {
            "nq": int(model.nq),
            "nv": int(model.nv),
            "nu": int(model.nu),
            "ntendon": int(model.ntendon),
        },
        "integration": {
            "steps": args.steps,
            "final_time": float(data.time),
            "finite_state": finite,
        },
        "deepseek_requests": 0,
        "passed": True,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
