"""Run frozen reach V1; exit 1 for a recorded scientific failure or runtime error."""
from pathlib import Path
import sys
import argparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.harness import run_reach


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-package", type=Path, default=PROJECT_ROOT / "tasks/reach_free")
    args = parser.parse_args()
    print("Running deterministic MATLAB M0/M1 -> MuJoCo reach harness...", flush=True)
    run = run_reach(task_package=args.task_package)
    print("Run:", run.path)
    print("Final status:", run.record.final_status)
    print("Failure code:", run.record.failure_code)
    print("Evidence: model_result.json, mujoco_result.json, diagnostic_summary.json, provenance.json, trace.json, trace.jsonl, run.json (when produced)")
    return 0 if run.record.final_status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
