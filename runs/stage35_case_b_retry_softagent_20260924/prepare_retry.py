from __future__ import annotations

import hashlib
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.state_io import atomic_json, digest, read


SOURCE_ROOT = ROOT / "runs" / "stage35_case_b_live_20260923"
RETRY_ROOT = Path(__file__).resolve().parent
SOURCE_ROUTE = SOURCE_ROOT / "inputs" / "route.json"
SOURCE_PROJECT = SOURCE_ROOT / "inputs" / "project.json"
SOURCE_ROUTE_SHA256 = "d3f1e5c363fdc88585e8a3d27030a0c7a2fce70314543509479b1180085d6b5f"
RETRY_RUN_ID = "stage35-case-b-retry-softagent"
RETRY_GRANT_ID = "stage35-case-b-retry-softagent-20260924"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def changed_paths(before: object, after: object, prefix: str = "") -> list[str]:
    if type(before) is not type(after):
        return [prefix or "/"]
    if isinstance(before, dict):
        paths: list[str] = []
        for key in sorted(set(before) | set(after)):
            path = f"{prefix}/{key}"
            if key not in before or key not in after:
                paths.append(path)
            else:
                paths.extend(changed_paths(before[key], after[key], path))
        return paths
    if isinstance(before, list):
        if len(before) != len(after):
            return [prefix or "/"]
        paths: list[str] = []
        for index, (left, right) in enumerate(zip(before, after)):
            paths.extend(changed_paths(left, right, f"{prefix}/{index}"))
        return paths
    return [] if before == after else [prefix or "/"]


def main() -> None:
    source_hash_before = file_sha256(SOURCE_ROUTE)
    if source_hash_before != SOURCE_ROUTE_SHA256:
        raise RuntimeError(f"sealed source hash mismatch: {source_hash_before}")

    source_route = read(SOURCE_ROUTE)
    source_project = read(SOURCE_PROJECT)
    retry_route = deepcopy(source_route)
    retry_project = deepcopy(source_project)
    retry_route["run_id"] = RETRY_RUN_ID
    retry_project["grant_id"] = RETRY_GRANT_ID

    route_diff = changed_paths(source_route, retry_route)
    project_diff = changed_paths(source_project, retry_project)
    if route_diff != ["/run_id"]:
        raise RuntimeError(f"unexpected route differences: {route_diff}")
    if project_diff != ["/grant_id"]:
        raise RuntimeError(f"unexpected project differences: {project_diff}")

    inputs = RETRY_ROOT / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    atomic_json(inputs / "route.json", retry_route)
    atomic_json(inputs / "project.json", retry_project)

    written_route = read(inputs / "route.json")
    written_project = read(inputs / "project.json")
    if changed_paths(source_route, written_route) != ["/run_id"]:
        raise RuntimeError("written retry route differs beyond /run_id")
    if changed_paths(source_project, written_project) != ["/grant_id"]:
        raise RuntimeError("written retry project differs beyond /grant_id")
    source_hash_after = file_sha256(SOURCE_ROUTE)
    if source_hash_after != source_hash_before:
        raise RuntimeError("sealed source route changed during retry preparation")

    protected_digests = {
        key: digest(source_route[key]) for key in ("seed", "task", "robot", "policy")
    }
    retry_protected_digests = {
        key: digest(written_route[key]) for key in ("seed", "task", "robot", "policy")
    }
    if retry_protected_digests != protected_digests:
        raise RuntimeError("a protected Case B setting changed")

    provenance = {
        "kind": "stage35_case_b_environment_retry",
        "source_run_root": str(SOURCE_ROOT),
        "source_run_id": source_route["run_id"],
        "source_route": str(SOURCE_ROUTE),
        "source_route_sha256_before": source_hash_before,
        "source_route_sha256_after": source_hash_after,
        "source_environment_failure_preserved": True,
        "retry_run_root": str(RETRY_ROOT),
        "retry_run_id": RETRY_RUN_ID,
        "retry_route_sha256": file_sha256(inputs / "route.json"),
        "route_differences": route_diff,
        "project_differences": project_diff,
        "protected_digests": protected_digests,
        "retry_protected_digests": retry_protected_digests,
        "explicit_python": r"C:\Users\gugugaga\miniconda3\envs\softagent\python.exe",
        "environment_smoke": str(
            ROOT
            / "runs"
            / "stage35_case_b_softagent_smoke_20260924"
            / "environment_smoke.json"
        ),
        "scientific_settings_identical": True,
        "deepseek_configuration_identical": True,
        "tool_surface_identical": True,
        "budget_policy_identical": True,
    }
    atomic_json(RETRY_ROOT / "retry_provenance.json", provenance)
    print(
        {
            "retry_root": str(RETRY_ROOT),
            "run_id": RETRY_RUN_ID,
            "route_differences": route_diff,
            "project_differences": project_diff,
            "sealed_source_sha256": source_hash_after,
            "protected_digests_match": True,
        }
    )


if __name__ == "__main__":
    main()
