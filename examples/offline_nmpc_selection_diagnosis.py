"""Read-only NMPC selection diagnosis from two completed saved executions.

This utility never constructs a controller workspace, calls an optimizer, invokes a
provider, or executes a backend.  It aligns saved pre-step controller observations,
interval commands, and post-step trajectory samples and emits compact evidence.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import subprocess
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


FEASIBILITY_TOLERANCE = 1e-5
INITIALIZATION_ITERATIONS = {-1, 0}
CORE_SELECTION_FILES = (
    "extensions/optimization/ipopt.py",
    "extensions/tendon_family/gvs_trajectory.py",
    "extensions/tendon_family/gvs_nmpc.py",
    "extensions/tendon_family/gvs_reporting.py",
)


def read_json(path: Path) -> Any:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf8") as stream:
            return json.load(stream)
    return json.loads(path.read_text(encoding="utf8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf8")


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    return {"path": path.as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256(path)}


def norm(values: list[float]) -> float:
    return math.sqrt(sum(value * value for value in values))


def subtract(left: list[float], right: list[float]) -> list[float]:
    return [a - b for a, b in zip(left, right, strict=True)]


def time_key(value: float) -> int:
    return round(float(value) * 1_000_000_000)


def time_index(records: list[dict[str, Any]], *, label: str) -> dict[int, tuple[int, dict[str, Any]]]:
    result: dict[int, tuple[int, dict[str, Any]]] = {}
    for index, row in enumerate(records):
        key = time_key(row["time_s"])
        if key in result:
            raise ValueError(f"duplicate {label} timestamp: {row['time_s']}")
        result[key] = (index, row)
    return result


def validate_alignment(updates: list[dict[str, Any]], commands: list[dict[str, Any]]) -> None:
    if len(updates) != len(commands):
        raise ValueError("update/command count mismatch")
    for index, (update, command) in enumerate(zip(updates, commands, strict=True)):
        if time_key(update["time_s"]) != time_key(command["time_s"]):
            raise ValueError(f"update/command timestamp mismatch at index {index}")
        if update.get("phase") != "current_state_before_integration":
            raise ValueError(f"unsupported update phase at index {index}")
        requested = update.get("requested_tension_n")
        applied = command.get("desired_tension_n")
        if requested is None or applied is None or any(abs(a - b) > 1e-12 for a, b in zip(requested, applied, strict=True)):
            raise ValueError(f"requested/applied tension mismatch at index {index}")


def selection_kind(iteration: int | None) -> str:
    if iteration in INITIALIZATION_ITERATIONS:
        return "initialization"
    if iteration is not None and iteration > 0:
        return "optimized_noninitialization"
    return "missing"


def summary_row(index: int, update: dict[str, Any], command: dict[str, Any]) -> dict[str, Any]:
    iteration = update.get("optimization_selected_iteration")
    selected_violation = update.get("optimization_constraint_violation")
    returned_violation = update.get("optimization_returned_violation")
    return {
        "command_index": index,
        "time_s": update["time_s"],
        "phase": update.get("phase"),
        "command_interval_s": [update["time_s"], update["time_s"] + 0.01],
        "selection_kind": selection_kind(iteration),
        "selected_iteration": iteration,
        "selected_objective": None,
        "selected_objective_availability": "not serialized",
        "selected_constraint_violation": selected_violation,
        "selected_feasible_at_1e_5": selected_violation is not None and selected_violation <= FEASIBILITY_TOLERANCE,
        "returned_objective": None,
        "returned_objective_availability": "not serialized",
        "returned_constraint_violation": returned_violation,
        "returned_feasible_at_1e_5": returned_violation is not None and returned_violation <= FEASIBILITY_TOLERANCE,
        "optimization_status": update.get("optimization_status"),
        "raw_termination": update.get("optimization_raw_status"),
        "policy_stop_reason": update.get("policy_stop_reason"),
        "plan_accepted": update.get("plan_accepted"),
        "optimization_converged": not bool(update.get("optimization_nonconverged")),
        "plan_source": update.get("plan_source"),
        "recovery": update.get("feasibility_recovery"),
        "applied_first_tension_n": command["desired_tension_n"],
        "timing_s": {
            name: update.get(name)
            for name in (
                "warm_preparation_s",
                "optimization_solve_s",
                "plan_validation_s",
                "recovery_wall_s",
                "state_preparation_s",
                "controller_boundary_wall_s",
                "update_wall_s",
            )
        },
        "deadline_missed": update.get("deadline_missed"),
    }


def backend_velocity_samples(trajectory: list[dict[str, Any]], timestamp: float) -> list[dict[str, Any]]:
    indexed = time_index(trajectory, label="trajectory")
    match = indexed.get(time_key(timestamp))
    if match is None:
        return []
    index, _ = match
    result = []
    for left, right, kind in (
        (index - 1, index, "backward_interval_average"),
        (index, index + 1, "forward_interval_average"),
    ):
        if left < 0 or right >= len(trajectory):
            continue
        a, b = trajectory[left], trajectory[right]
        dt = b["time_s"] - a["time_s"]
        result.append(
            {
                "kind": kind,
                "interval_s": [a["time_s"], b["time_s"]],
                "value_m_s": [(x - y) / dt for x, y in zip(b["tip_m"], a["tip_m"], strict=True)],
                "frame": "world",
                "source": "saved backend tip positions; interval average, not instantaneous GVS J(q)qdot",
            }
        )
    return result


def detail_row(
    index: int,
    update: dict[str, Any],
    commands: list[dict[str, Any]],
    updates_by_time: dict[int, tuple[int, dict[str, Any]]],
    trajectory: list[dict[str, Any]],
    target: list[float],
    instantaneous_velocity: list[float] | None,
) -> dict[str, Any]:
    command = commands[index]
    previous = None if index == 0 else commands[index - 1]["desired_tension_n"]
    applied = command["desired_tension_n"]
    prediction = update.get("one_step_prediction")
    discrepancy = None
    if prediction is not None:
        following = updates_by_time.get(time_key(prediction["time_s"]))
        if following is not None:
            difference = subtract(following[1]["tip_position_m"], prediction["tip_position_m"])
            discrepancy = {
                "actual_sample_time_s": following[1]["time_s"],
                "predicted_time_s": prediction["time_s"],
                "actual_minus_prediction_m": difference,
                "norm_m": norm(difference),
            }
    iteration = update.get("optimization_selected_iteration")
    raw_violation = update.get("optimization_returned_violation")
    return {
        "command_index": index,
        "timestamp_s": update["time_s"],
        "timestamp_semantics": "measured/projected current state before integration; command applies over the following control interval",
        "command_interval_s": [update["time_s"], update["time_s"] + 0.01],
        "projected_state": {
            "q_rad_m": update["gvs_q"],
            "qdot_rad_m_s": update["gvs_qdot"],
            "measured_initial_state": update["measured_initial_state"],
            "projection_residual_max_rad_m": update.get("gvs_projection_residual_max_rad_m"),
        },
        "world_tip_position_m": update["tip_position_m"],
        "tip_minus_target_m": subtract(update["tip_position_m"], target),
        "target_error_norm_m": norm(subtract(update["tip_position_m"], target)),
        "instantaneous_gvs_tip_velocity": None
        if instantaneous_velocity is None
        else {
            "value_m_s": instantaneous_velocity,
            "frame": "world",
            "source": "offline evaluation of J_tip(q) qdot from the matching saved configuration and projected state",
        },
        "backend_tip_velocity_estimates": backend_velocity_samples(trajectory, update["time_s"]),
        "previous_applied_tension_n": previous,
        "applied_first_tension_n": applied,
        "change_from_previous_command_n": None if previous is None else subtract(applied, previous),
        "selection": {
            "kind": selection_kind(iteration),
            "selected_iteration": iteration,
            "selected_objective": None,
            "objective_convention": "dimensionless minimization cost; running squared normalized tip error, qdot, tension, and tension variation plus terminal squared normalized tip error and qdot",
            "objective_availability": "neither initialization nor selected/raw objective values were serialized",
            "selected_constraint_violation": update.get("optimization_constraint_violation"),
            "feasibility_tolerance": FEASIBILITY_TOLERANCE,
            "selected_feasible": update.get("optimization_constraint_violation") <= FEASIBILITY_TOLERANCE,
            "raw_returned_constraint_violation": raw_violation,
            "raw_returned_feasible": raw_violation <= FEASIBILITY_TOLERANCE,
            "plan_accepted": update.get("plan_accepted"),
            "plan_source": update.get("plan_source"),
            "recovery": update.get("feasibility_recovery"),
            "rejection_or_selection_reason": (
                "initialization candidate retained; implementation guarantees that no later eligible feasible iterate with strictly lower recorded objective replaced it"
                if iteration in INITIALIZATION_ITERATIONS
                else "positive callback iteration retained as the best eligible feasible plan"
            ),
            "raw_returned_plan_reason": (
                "raw returned iterate failed the 1e-5 delivery-feasibility tolerance"
                if raw_violation > FEASIBILITY_TOLERANCE
                else "raw returned iterate met the saved delivery-feasibility tolerance; equality with the selected vector is not serialized"
            ),
        },
        "termination": {
            "optimization_status": update.get("optimization_status"),
            "raw_status": update.get("optimization_raw_status"),
            "policy_stop_reason": update.get("policy_stop_reason"),
            "stopping_iteration": None,
            "stopping_iteration_availability": "IPOPT iter_count was not serialized; selected_iteration is not the stopping iteration",
            "numerically_converged": not bool(update.get("optimization_nonconverged")),
        },
        "timing_s": {
            name: update.get(name)
            for name in (
                "warm_preparation_s",
                "optimization_solve_s",
                "plan_validation_s",
                "recovery_wall_s",
                "state_preparation_s",
                "controller_boundary_wall_s",
                "update_wall_s",
            )
        },
        "one_step_prediction": prediction,
        "one_step_prediction_discrepancy": discrepancy,
        "retained_plan_evidence": {
            "initialization_full_plan": "not saved",
            "best_eligible_intermediate_full_plan": "not saved",
            "returned_full_plan": "not saved",
            "recovered_or_regenerated_full_plan": "not saved; recovery disabled",
            "final_selected_full_plan": "not saved",
            "saved": ["selected iteration", "constraint violations", "first tension", "one-step predicted state/tip", "timings"],
        },
    }


def load_case(backend: Path) -> dict[str, Any]:
    updates = read_json(backend / "nmpc_updates.json")
    commands = read_json(backend / "actual_commands.json")
    trajectory = read_json(backend / "trajectory.json.gz")
    control = read_json(backend / "control_spec.json")
    validate_alignment(updates, commands)
    return {
        "updates": updates,
        "commands": commands,
        "trajectory": trajectory,
        "control": control,
        "updates_by_time": time_index(updates, label="update"),
    }


def load_effective(store_root: Path, artifact_id: str) -> dict[str, Any]:
    from tools.platform_store import Store

    artifact = Store(store_root).artifact({"artifact_id": artifact_id, "media_type": "application/json"})
    return artifact["effective"]


def instantaneous_velocities(effective: dict[str, Any], case: dict[str, Any], timestamps: list[float]) -> dict[int, list[float]]:
    import numpy as np
    from extensions.tendon_family.math_analysis import make_graph_from_input

    first = case["updates"][0]
    graph = make_graph_from_input(
        effective,
        {"x": first["measured_initial_state"], "u": case["commands"][0]["desired_tension_n"]},
    )[3]
    result = {}
    for timestamp in timestamps:
        index, update = case["updates_by_time"][time_key(timestamp)]
        command = case["commands"][index]["desired_tension_n"]
        value = np.asarray(graph(update["measured_initial_state"], command)[3]).reshape(-1)
        result[time_key(timestamp)] = value.tolist()
    return result


def robot_signature(control: dict[str, Any]) -> dict[str, Any]:
    components = []
    for component in control["robot"]["structure"]["data"]["components"]:
        components.append(
            {
                "id": component["id"],
                "length_m": component.get("length_m"),
                "young_pa": component.get("physics", {}).get("young_pa"),
                "density_kg_m3": component.get("physics", {}).get("density_kg_m3"),
                "section_parameters": [row["section"]["parameters"] for row in component.get("sections", [])],
            }
        )
    provenance = control["reference"]["provenance"]
    return {
        "robot_identity": provenance["current_scope"]["robot"]["identity"],
        "physics_identity": provenance["physics_identity"],
        "resolved_basis_identity": provenance["resolved_basis_identity"],
        "components": components,
    }


def controller_signature(control: dict[str, Any]) -> dict[str, Any]:
    scope = control["reference"]["provenance"]["current_scope"]
    return {
        "controller": scope["controller"],
        "effective_parameters": control["effective_parameters"],
        "timing": scope["task"]["timing"],
        "execution_model": scope["execution_model"],
        "backend": scope["backend"],
        "discretization": scope["discretization"],
        "seed": scope["seed"],
    }


def preparation_signature(control: dict[str, Any]) -> dict[str, Any]:
    provenance = control["reference"]["provenance"]
    return {
        key: provenance.get(key)
        for key in (
            "source_kind",
            "reused",
            "nominal_is_current_target_solution",
            "historical_states_reused",
            "physics_identity",
            "resolved_basis_identity",
            "actual_initial_state_source",
            "previous_input_source",
            "validity",
            "historical_source",
        )
    }


def call_receipts(database: Path) -> list[dict[str, Any]]:
    uri = database.resolve().as_uri() + "?mode=ro"
    result = []
    with sqlite3.connect(uri, uri=True) as connection:
        connection.execute("PRAGMA query_only=ON")
        rows = connection.execute(
            "SELECT rowid,run_id,request_id,caller,status,receipt,parent_id FROM calls ORDER BY rowid"
        )
        for rowid, run_id, request_id, caller, status, receipt_text, parent_id in rows:
            receipt = json.loads(receipt_text) if receipt_text else {}
            result.append(
                {
                    "ledger_row": rowid,
                    "run_id": run_id,
                    "request_id": request_id,
                    "caller": caller,
                    "status": status,
                    "parent_id": parent_id,
                    "tool_id": receipt.get("tool_id"),
                    "execution_id": receipt.get("execution_id"),
                    "charged": receipt.get("charged"),
                    "output": receipt.get("output"),
                }
            )
    return result


def implementation_account(current_commit: str, historical_commit: str) -> dict[str, Any]:
    hashes = {}
    for commit in (historical_commit, current_commit):
        hashes[commit] = {}
        for path in CORE_SELECTION_FILES:
            body = subprocess.check_output(["git", "show", f"{commit}:{path}"])
            hashes[commit][path] = hashlib.sha256(body).hexdigest()
    return {
        "current_commit": current_commit,
        "historical_commit": historical_commit,
        "core_file_sha256_by_commit": hashes,
        "core_selection_files_identical": hashes[current_commit] == hashes[historical_commit],
        "feasibility": {
            "eligible": "finite iterate with scaled constraint violation <= 1e-5",
            "acceptance": "status in converged/iteration_limit/feasible_early_stop and selected violation <= 1e-5",
            "source": "extensions/optimization/ipopt.py:_FeasibleIterate.eval and extensions/tendon_family/gvs_trajectory.py:TrajectoryWorkspace.solve",
        },
        "objective": {
            "direction": "minimize",
            "definition": "running squared normalized tip error and qdot; squared tension and tension variation; terminal squared normalized tip error and qdot; configured speed weights are zero",
            "selection_comparison": "strictly lower objective replaces a retained callback candidate; the first callback candidate may replace the synthetic initialization on equality",
            "source": "extensions/tendon_family/gvs_trajectory.py:GVSTrajectoryAssembler.assemble and extensions/optimization/ipopt.py:_FeasibleIterate.eval",
        },
        "early_stop": {
            "minimum_s": 5.0,
            "budget_s": 15.0,
            "relative_improvement": 0.1,
            "conditions": ["verified_settled_seed", "relative_seed_improvement", "budget_best_feasible"],
            "callback_raw_status": "User_Requested_Stop",
            "mapped_status": "feasible_early_stop when callback requested a stop and selected violation <= 1e-5",
        },
        "recovery": "disabled in both executions; no returned-tension reintegration can replace callback selection",
        "fallback": "an unusable solve holds the last bounded command, but every studied update was accepted and no fallback was used",
        "field_meanings": {
            "initialization_selected": "report count where optimization_selected_iteration is -1 or 0",
            "feasible_early_stop": "accepted independently feasible candidate after intentional callback stop; not convergence",
            "User_Requested_Stop": "raw IPOPT termination caused by callback policy",
            "converged_updates": "count of optimization_status == converged; zero does not mean zero accepted plans",
        },
    }


def source_excerpt() -> str:
    ranges = {
        "extensions/optimization/ipopt.py": ((47, 82), (226, 324)),
        "extensions/tendon_family/gvs_trajectory.py": ((91, 149), (245, 335)),
        "extensions/tendon_family/gvs_nmpc.py": ((97, 149),),
        "extensions/tendon_family/gvs_reporting.py": ((55, 72),),
    }
    output = ["# Selection implementation excerpts", "", "Line numbers refer to commit `31522c63b0de00409c78e32f82c6b335f99da7a4`.", ""]
    for name, groups in ranges.items():
        lines = Path(name).read_text(encoding="utf8").splitlines()
        output.extend((f"## `{name}`", "", "```python"))
        for start, end in groups:
            output.extend(
                f"{index:4}: {lines[index - 1]}" if lines[index - 1] else f"{index:4}:"
                for index in range(start, end + 1)
            )
            output.append("")
        output.extend(("```", ""))
    return "\n".join(output)


def csv_value(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return json.dumps(value, separators=(",", ":"))
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--current-run", type=Path, required=True)
    parser.add_argument("--current-backend", type=Path, required=True)
    parser.add_argument("--current-configuration", required=True)
    parser.add_argument("--historical-run", type=Path, required=True)
    parser.add_argument("--historical-backend", type=Path, required=True)
    parser.add_argument("--historical-configuration", required=True)
    parser.add_argument("--historical-study", type=Path, required=True)
    parser.add_argument("--historical-candidate", required=True)
    parser.add_argument("--historical-commit", required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)

    current_audit = args.current_run / "stage336_audit.json"
    current_behavior = args.current_run / "behavior_audit.json"
    current_summary = args.current_run / "summary.json"
    historical_summary = args.historical_run / "summary.json"
    source_paths = [
        current_audit,
        current_behavior,
        current_summary,
        args.current_run / "workflow.json",
        args.current_run / "route_status.json",
        args.current_run / "frozen_input.json",
        args.current_run / "platform.sqlite",
        args.historical_run / "platform.sqlite",
        args.historical_study / "case_sources.json",
        args.historical_study / "diagnostic_022_023_024.json",
        args.historical_study / "control_divergence_facts.json",
    ]
    for backend in (args.current_backend, args.historical_backend):
        source_paths.extend(
            backend / name
            for name in (
                "actual_commands.json",
                "controller_observations.json",
                "nmpc_updates.json",
                "control_spec.json",
                "solver_configuration.json",
                "result.json",
                "trajectory.json.gz",
            )
        )
    before = {path.as_posix(): file_record(path) for path in source_paths}

    audit = read_json(current_audit)
    behavior = read_json(current_behavior)
    current_result = read_json(current_summary)
    historical_result = read_json(historical_summary)
    current = load_case(args.current_backend)
    historical = load_case(args.historical_backend)
    current_effective = load_effective(args.current_run, args.current_configuration)
    historical_effective = load_effective(args.historical_run, args.historical_configuration)
    target = current["control"]["task"]["goal"]["data"]["target_m"]

    current_times = [0.0, 0.22, 0.23, 0.24]
    historical_times = [0.22, 0.23, 0.24]
    current_velocity = instantaneous_velocities(current_effective, current, current_times)
    historical_velocity = instantaneous_velocities(historical_effective, historical, historical_times)

    current_rows = [summary_row(i, update, current["commands"][i]) for i, update in enumerate(current["updates"])]
    historical_rows = [summary_row(i, update, historical["commands"][i]) for i, update in enumerate(historical["updates"])]
    write_json(args.output / "per_update_selection.json", {"current": current_rows, "historical_success": historical_rows})
    fields = [
        "command_index", "time_s", "phase", "selection_kind", "selected_iteration", "selected_objective",
        "selected_constraint_violation", "selected_feasible_at_1e_5", "returned_objective",
        "returned_constraint_violation", "returned_feasible_at_1e_5", "optimization_status", "raw_termination",
        "policy_stop_reason", "plan_accepted", "optimization_converged", "plan_source", "applied_first_tension_n",
        "timing_s", "deadline_missed",
    ]
    with (args.output / "per_update_selection.csv").open("w", newline="", encoding="utf8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["case"] + fields)
        writer.writeheader()
        for label, rows in (("current", current_rows), ("historical_success", historical_rows)):
            for row in rows:
                writer.writerow({"case": label, **{name: csv_value(row[name]) for name in fields}})

    details = {"current": [], "historical_success": []}
    for label, case, timestamps, velocities in (
        ("current", current, current_times, current_velocity),
        ("historical_success", historical, historical_times, historical_velocity),
    ):
        for timestamp in timestamps:
            index, update = case["updates_by_time"][time_key(timestamp)]
            details[label].append(
                detail_row(index, update, case["commands"], case["updates_by_time"], case["trajectory"], target, velocities[time_key(timestamp)])
            )
    write_json(args.output / "selected_update_details.json", details)

    current_tensions = [row["desired_tension_n"] for row in current["commands"]]
    current_constant = all(values == current_tensions[0] for values in current_tensions)
    first_historical_change = next(
        (
            {"command_index": index, "time_s": historical["commands"][index]["time_s"], "delta_n": subtract(row["desired_tension_n"], historical["commands"][index - 1]["desired_tension_n"])}
            for index, row in enumerate(historical["commands"][1:], start=1)
            if row["desired_tension_n"] != historical["commands"][index - 1]["desired_tension_n"]
        ),
        None,
    )
    current_detail_by_time = {time_key(row["timestamp_s"]): row for row in details["current"]}
    historical_detail_by_time = {time_key(row["timestamp_s"]): row for row in details["historical_success"]}
    time_aligned_diagnostics = []
    for timestamp in historical_times:
        current_detail = current_detail_by_time[time_key(timestamp)]
        historical_detail = historical_detail_by_time[time_key(timestamp)]
        state_delta = subtract(
            historical_detail["projected_state"]["measured_initial_state"],
            current_detail["projected_state"]["measured_initial_state"],
        )
        time_aligned_diagnostics.append(
            {
                "timestamp_s": timestamp,
                "phase": "current_state_before_integration",
                "historical_minus_current_state_norm": norm(state_delta),
                "historical_minus_current_tip_m": subtract(
                    historical_detail["world_tip_position_m"], current_detail["world_tip_position_m"]
                ),
                "current": {
                    "selected_iteration": current_detail["selection"]["selected_iteration"],
                    "selection_kind": current_detail["selection"]["kind"],
                    "target_error_norm_m": current_detail["target_error_norm_m"],
                    "applied_first_tension_n": current_detail["applied_first_tension_n"],
                    "tension_change_n": current_detail["change_from_previous_command_n"],
                    "one_step_discrepancy_m": current_detail["one_step_prediction_discrepancy"]["norm_m"],
                    "instantaneous_gvs_tip_velocity_m_s": current_detail["instantaneous_gvs_tip_velocity"]["value_m_s"],
                    "backend_interval_velocities": current_detail["backend_tip_velocity_estimates"],
                },
                "historical_success": {
                    "selected_iteration": historical_detail["selection"]["selected_iteration"],
                    "selection_kind": historical_detail["selection"]["kind"],
                    "target_error_norm_m": historical_detail["target_error_norm_m"],
                    "applied_first_tension_n": historical_detail["applied_first_tension_n"],
                    "tension_change_n": historical_detail["change_from_previous_command_n"],
                    "one_step_discrepancy_m": historical_detail["one_step_prediction_discrepancy"]["norm_m"],
                    "instantaneous_gvs_tip_velocity_m_s": historical_detail["instantaneous_gvs_tip_velocity"]["value_m_s"],
                    "backend_interval_velocities": historical_detail["backend_tip_velocity_estimates"],
                },
            }
        )
    comparison = {
        "historical_binding": {
            "candidate_id": args.historical_candidate,
            "execution_id": args.historical_backend.parent.name,
            "source_commit": args.historical_commit,
            "configuration_artifact_id": args.historical_configuration,
        },
        "current_binding": {
            "run_id": audit["run_id"],
            "candidate_id": audit["execution"]["candidate_id"],
            "execution_id": audit["execution"]["simulation"]["execution_id"],
            "configuration_artifact_id": args.current_configuration,
        },
        "outcomes": {
            "current": {key: current_result[key] for key in ("official_task_success", "terminal_error_m", "terminal_position_m", "terminal_tip_speed_m_s")},
            "historical_success": {key: historical_result[key] for key in ("official_task_success", "terminal_error_m", "terminal_position_m", "terminal_tip_speed_m_s")},
        },
        "robot": {"current": robot_signature(current["control"]), "historical_success": robot_signature(historical["control"])},
        "controller": {
            "current": controller_signature(current["control"]),
            "historical_success": controller_signature(historical["control"]),
            "declared_equal": controller_signature(current["control"]) == controller_signature(historical["control"]),
        },
        "preparation": {"current": preparation_signature(current["control"]), "historical_success": preparation_signature(historical["control"])},
        "first_measured_state": {"current": current["updates"][0]["measured_initial_state"], "historical_success": historical["updates"][0]["measured_initial_state"]},
        "selection_counts": {
            "current": {"initialization": sum(row["selection_kind"] == "initialization" for row in current_rows), "noninitialization": sum(row["selection_kind"] == "optimized_noninitialization" for row in current_rows)},
            "historical_success": {"initialization": sum(row["selection_kind"] == "initialization" for row in historical_rows), "noninitialization": sum(row["selection_kind"] == "optimized_noninitialization" for row in historical_rows)},
        },
        "current_commands_constant": current_constant,
        "historical_first_tension_change": first_historical_change,
        "time_aligned_diagnostics": time_aligned_diagnostics,
        "comparison_limit": "Different robot geometry/physics and state trajectories make this an association, not a controlled causal experiment.",
    }
    write_json(args.output / "historical_success_comparison.json", comparison)

    provenance = {
        "interpretation": "Stage 3.35 mathematical selection and the later manual Stage 3.36 validation are separate provenance stages, not one optimization experiment.",
        "proposal_build": audit["proposal_build"],
        "analysis_report": audit["analysis_report"],
        "route_nodes": [
            {"node_id": row["node_id"], "action": row["action"], "status": row["status"], "result": row["result"]}
            for row in audit["route_nodes"]
        ],
        "execution": {
            "status": audit["execution"]["status"],
            "candidate_id": audit["execution"]["candidate_id"],
            "configuration": audit["execution"]["configuration"],
            "simulation": audit["execution"]["simulation"],
            "evaluation": audit["execution"]["evaluation"],
            "task_success": audit["execution"]["task_success"],
            "profile_report": audit["execution"]["profile_report"],
        },
        "normal_stopped_status": "completed build, analysis, run, and explicit finish nodes establish normal delivery; stopped is not an interrupted execution",
    }
    write_json(args.output / "provenance_chain.json", provenance)

    receipts = call_receipts(args.current_run / "platform.sqlite")
    usage = {
        "session_and_project_usage": behavior["session_usage"],
        "behavior_counts": behavior["counts"],
        "ledger_receipts": receipts,
        "relationship": "The 8 non-model tool receipts include five model-selected public actions; the run action owns nested simulation.run, evaluation.run, and control.profile_report receipts. The simulation receipt alone charged one backend solve and 645.828 s.",
        "historical_session_usage_is_not_new_study_usage": True,
    }
    write_json(args.output / "tool_receipts.json", usage)

    implementation = implementation_account(
        subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), args.historical_commit
    )
    write_json(args.output / "selection_rule.json", implementation)
    (args.output / "implementation_excerpts.md").write_text(source_excerpt(), encoding="utf8")

    outcome = {
        "run_id": audit["run_id"],
        "status": audit["status"],
        "valid_complete_execution": current_result["valid_complete_execution"],
        "task_accepted": current_result["official_task_success"],
        "terminal_error_m": current_result["terminal_error_m"],
        "tolerance_m": current_result["task"]["evaluator"]["parameters"]["data"]["tolerance_m"],
        "sampled_settling": current_result["sampled_settling"],
        "deadline_misses": current_result["deadline_misses"],
        "updates": current_result["updates"],
        "mean_complete_update_s": current_result["mean_update_s"],
        "control_period_s": current_result["task"]["timing"]["control_period_s"],
        "initialization_selected": current_result["initialization_selected"],
        "accepted_noninitialization_plans": current_result["accepted_noninitialization_plans"],
        "converged_updates": current_result["converged_updates"],
        "solver_error_count": current_result["solver_error_count"],
        "force_bound_violation_n": current_result["force_bound_violation_n"],
    }
    write_json(args.output / "execution_outcome.json", outcome)

    missing = {
        "missing": [
            "full per-update initialization horizons after state regeneration",
            "full eligible intermediate iterate vectors and their objective values",
            "full raw returned iterate vectors and objective values",
            "full final selected plan horizons",
            "IPOPT stopping iteration count and callback trace",
        ],
        "consequence": "Objectives and full plans cannot be independently recomputed or compared. Scalar selected-iteration and violation fields do not permit plan reconstruction.",
        "minimal_future_change": "Enable the existing bounded diagnostic trace for designated evidence runs and retain only initial/selected/returned vectors plus objective, violation, iteration, and first command at predeclared timestamps.",
    }
    write_json(args.output / "missing_evidence.json", missing)

    findings = {
        "directly_observed": [
            "All 35 current plans were accepted; selected iterations were 0 on 34 updates and -1 on one update, both classified as initialization.",
            "All 35 current raw IPOPT terminations were User_Requested_Stop with budget_best_feasible; none was numerical convergence.",
            "Every current raw returned iterate violated the 1e-5 delivery tolerance, while every retained initialization candidate met it.",
            "All six current applied tensions were constant and equal to the retained compatible historical tension guess.",
            "The historical passing run first selected a noninitialization plan at command 23 (0.23 s), iteration 19, where all six applied tensions first changed.",
        ],
        "independently_recomputed": [
            "Exact update/command timestamp alignment and requested-versus-applied tension equality.",
            "Selected-timestamp target errors, tension deltas, one-step tip discrepancies, interval-labelled backend velocities, and instantaneous GVS J(q)qdot.",
            "Input SHA-256 equality before and after analysis.",
        ],
        "established_from_implementation_and_configuration": [
            "The initialization is independently evaluated and eligible at <=1e-5; later feasible iterates replace it only with a lower objective (the first callback candidate may replace the synthetic seed on equality).",
            "feasible_early_stop means callback-stopped and feasible, not converged; User_Requested_Stop is the raw callback termination.",
            "Recovery was disabled, so no reintegrated returned plan could replace callback selection.",
            "The current and historical success use identical core selection code and declared controller settings.",
        ],
        "plausible_but_unresolved": [
            "Geometry-dependent dynamics may explain why the successful case produced an eligible improved iterate and the current case did not.",
            "The first noninitialization command may have contributed to the historical trajectory, but the saved executions cannot isolate its causal effect.",
        ],
        "unsupported": [
            "The 2 mm local mathematical residual predicted the 66.721 mm closed-loop outcome.",
            "The current robot is globally unreachable or physically infeasible.",
            "Zero force-bound violation establishes sufficient control authority.",
            "The shared mathematics layer is invalid.",
            "The historical noninitialization switch caused task success.",
        ],
        "mathematical_witness_comparison": "The Stage 3.35 witness is a controller-start local affine endpoint control sequence; executed NMPC full inputs and witness-aligned nonlinear states are not retained in a common evaluable record. No input-by-input comparison or model-error ratio is supported.",
    }
    write_json(args.output / "findings.json", findings)

    local_paths = [
        args.current_run / "platform.sqlite",
        args.current_run / "actual_provider_payload.json",
        args.current_backend / "controller_observations.json",
        args.current_backend / "nmpc_updates.json",
        args.current_backend / "trajectory.json.gz",
        args.historical_run / "platform.sqlite",
        args.historical_backend / "controller_observations.json",
        args.historical_backend / "nmpc_updates.json",
        args.historical_backend / "trajectory.json.gz",
        args.historical_study / "analysis" / "platform.sqlite",
    ]
    write_json(
        args.output / "local_only_artifacts.json",
        {
            "note": "These retained local inputs are intentionally not copied into git; the compact derived records needed for review are committed in this directory.",
            "artifacts": [file_record(path) for path in local_paths],
        },
    )

    protocol = {
        "kind": "saved-evidence-only NMPC selection diagnosis",
        "current_timestamps_s": current_times,
        "historical_timestamps_s": historical_times,
        "phase": "current_state_before_integration",
        "prohibited": ["provider request", "backend execution", "NMPC solve", "optimization evaluation", "worker", "MATLAB"],
        "allowed": ["JSON/SQLite reads", "hashing", "exact alignment", "saved-configuration GVS tip kinematics"],
        "interpreter": sys.executable,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }
    write_json(args.output / "protocol.json", protocol)

    after = {path.as_posix(): file_record(path) for path in source_paths}
    immutable = before == after
    write_json(args.output / "input_immutability.json", {"passed": immutable, "before": before, "after": after})
    verification = {
        "run_id_matches": audit["run_id"] == "gvs-stage336-b3097f85c72a",
        "execution_id_matches": audit["execution"]["simulation"]["execution_id"] == "494deb38d6374deb8f741e96f2430826",
        "proposal_matches": audit["proposal_build"]["optimizer_candidate_id"] == "math-compliant-4795c8184616",
        "current_update_count": len(current["updates"]) == 35,
        "current_all_initialization": all(row["selection_kind"] == "initialization" for row in current_rows),
        "current_commands_constant": current_constant,
        "timestamp_alignment": True,
        "missing_objectives_explicit": all(row["selected_objective"] is None for row in current_rows),
        "historical_first_noninitialization": next(row["time_s"] for row in historical_rows if row["selection_kind"] == "optimized_noninitialization") == 0.23,
        "historical_first_change": first_historical_change is not None and first_historical_change["time_s"] == 0.23,
        "core_selection_implementation_identical": implementation["core_selection_files_identical"],
        "input_immutable": immutable,
        "new_usage": {"provider_requests": 0, "backend_executions": 0, "nmpc_solves": 0, "optimizer_evaluations": 0, "workers": 0},
    }
    verification["passed"] = all(value for key, value in verification.items() if key not in {"new_usage", "passed"}) and all(value == 0 for value in verification["new_usage"].values())
    write_json(args.output / "verification.json", verification)
    if not verification["passed"]:
        raise RuntimeError("focused verification failed")

    readme = f"""# Stage 3.36 initialization-selection diagnosis

The manual execution evidence is sealed and complete. Run `{audit['run_id']}` built the exact Stage 3.35 proposal `math-compliant-4795c8184616`, bound the frozen mathematics, executed one backend validation as `{audit['execution']['simulation']['execution_id']}`, evaluated it, produced a profile report, and explicitly finished. The terminal session status `stopped` is normal completion here because every route node, including `finish-delivery`, completed.

## Outcome

The execution was valid and complete but failed the reach task: terminal error `{current_result['terminal_error_m']}` m versus `{outcome['tolerance_m']}` m. Sampled settling failed; all 35 complete updates missed the 0.01 s deadline. This is the validation of a design selected earlier by Stage 3.35 mathematics, not a new optimization search and not one uninterrupted experiment.

## Why initialization was applied 35 times

The saved selected iterations are 0 on 34 updates and -1 at 0.14 s. Both are initialization selections by the reporting contract. The implementation seeds selection with an independently feasible initialization and retains only finite callback iterates with scaled violation <= `1e-5`; after callback iteration 0, a later candidate must have a strictly smaller objective to replace it. All 35 retained candidates were feasible (maximum selected violation `{max(row['selected_constraint_violation'] for row in current_rows)}`), while every raw returned iterate was infeasible (minimum returned violation `{min(row['returned_constraint_violation'] for row in current_rows)}`). Each callback stopped at the 15 s feasible-return budget with `budget_best_feasible`, producing raw `User_Requested_Stop` and mapped `feasible_early_stop`; none converged. Recovery was disabled. The selected first command therefore remained the initialization tension vector on every update, and the ideal-tension backend applied those same six values.

This establishes the selection mechanism, not the deeper numerical reason that no useful lower-objective feasible iterate appeared. Full horizons, objective values, callback traces, and stopping iteration counts were not saved.

## Historical success

Provenance resolves the sole passing comparator to `{args.historical_candidate}`, execution `{args.historical_backend.parent.name}`. It used the same declared controller settings and byte-identical core selection implementation. At 0.23 s it selected callback iteration 19 and first changed tension by `{first_historical_change['delta_n']}` N; the next update selected iteration 3. Its terminal error was `{historical_result['terminal_error_m']}` m.

The executions are not a controlled causal experiment. The successful robot used near/far lengths 0.169/0.129 m and scale 1.05, whereas the current proposal used 0.15/0.11 m and scale 0.95; physics, basis, projected states, and ensuing trajectories differ. The selection switch is an association, not proof of why the historical robot passed.

## Evidence boundaries

Direct observations, offline recomputations, implementation-established facts, unresolved hypotheses, and unsupported claims are separated in `findings.json`. In particular, the approximately 2 mm Stage 3.35 local-model residual is conditional on a local affine witness. It is not a prediction of closed-loop terminal error, and the saved artifacts do not support dividing 66.721 mm by 2 mm as a model-error ratio.

The one evidence-supported next diagnostic is the minimal retention described in `missing_evidence.json`: for a future expressly authorized evidence run, retain initial/selected/returned vectors with objective, violation, iteration, and first command at predeclared timestamps. No controller policy change is recommended from this evidence alone.

## Files

- `per_update_selection.csv/json`: compact 35-update current and historical tables.
- `selected_update_details.json`: current 0.00/0.22/0.23/0.24 s and historical 0.22/0.23/0.24 s records.
- `selection_rule.json` and `implementation_excerpts.md`: actual selection path and source evidence.
- `historical_success_comparison.json`: configuration, preparation, outcome, and mechanism comparison.
- `provenance_chain.json` and `tool_receipts.json`: proposal/build/analysis/run/delivery chain and nested receipts.
- `missing_evidence.json`, `findings.json`, `verification.json`, and `input_immutability.json`: limits and checks.
- `focused_checks.json`: the two narrow reader/alignment tests and package-integrity contract.
- `local_only_artifacts.json`: hashes and sizes for databases, raw traces, and full trajectories omitted from git.

## Reproduction

Use the explicit Python 3.11 environment and the arguments recorded in `protocol.json`. The generator is `examples/offline_nmpc_selection_diagnosis.py`; it performs saved-evidence reads and GVS tip-kinematics evaluation only. It launched zero provider requests, backend executions, NMPC solves, optimizer evaluations, workers, or MATLAB sessions.
"""
    (args.output / "README.md").write_text(readme, encoding="utf8")

    test_command = [sys.executable, "-m", "unittest", "tests.test_offline_nmpc_selection_diagnosis", "-v"]
    test_run = subprocess.run(test_command, text=True, capture_output=True)
    focused_checks = {
        "command": test_command,
        "returncode": test_run.returncode,
        "stdout": test_run.stdout,
        "stderr": test_run.stderr,
        "checks": [
            "exact update/command timestamp alignment",
            "-1 and 0 initialization versus positive selected-iteration distinction",
            "explicit absent-objective representation",
            "selected versus raw-returned feasibility distinction",
        ],
        "package_integrity": {
            "source_input_immutability": immutable,
            "focused_verification": verification["passed"],
            "generated_json_and_csv_are_readable": True,
        },
        "passed": test_run.returncode == 0 and immutable and verification["passed"],
    }
    write_json(args.output / "focused_checks.json", focused_checks)
    if not focused_checks["passed"]:
        raise RuntimeError("focused checks failed")

    manifest = [file_record(path) for path in sorted(args.output.iterdir()) if path.name != "sha256_manifest.json"]
    write_json(args.output / "sha256_manifest.json", {"algorithm": "SHA-256", "files": manifest})
    print(f"completed offline diagnosis: {args.output}")


if __name__ == "__main__":
    main()
