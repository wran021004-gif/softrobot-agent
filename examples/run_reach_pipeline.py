"""Run frozen reach V1; exit 1 for a recorded scientific failure or runtime error."""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.harness import run_reach


def main() -> int:
    print("Running deterministic MATLAB M0/M1 -> MuJoCo reach harness...", flush=True)
    run = run_reach()
    print("Run:", run.path)
    print("Final status:", run.record.final_status)
    print("Failure code:", run.record.failure_code)
    print("Evidence: model_result.json, mujoco_result.json, diagnostic_summary.json, provenance.json, trace.json, run.json (when produced)")
    return 0 if run.record.final_status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
