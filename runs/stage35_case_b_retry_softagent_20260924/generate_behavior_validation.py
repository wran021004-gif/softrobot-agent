"""Generate the retry-only Stage 3.5 Case B behavior audit from sealed evidence."""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from extensions.tendon_family.route import view  # noqa: E402
from tools.platform_host import Host  # noqa: E402
from tools.state_io import atomic_json, digest, read  # noqa: E402


RUN_DIR = Path(__file__).resolve().parent
RUN_ID = "stage35-case-b-retry-softagent"
ORIGINAL_DIR = ROOT / "runs" / "stage35_case_b_live_20260923"
ORIGINAL_ROUTE_HASH = "d3f1e5c363fdc88585e8a3d27030a0c7a2fce70314543509479b1180085d6b5f"


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT)).replace("\\", "/")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


host = Host(RUN_DIR, RUN_ID)
session = host.store.session(RUN_ID)
route_view = view(host)
assert session["status"] == "stopped"
assert route_view["route"]["final"]["delivery_status"] == "evaluated"

with host.store.connect(True) as db:
    events = [json.loads(row[0]) for row in db.execute("SELECT body FROM events ORDER BY seq")]


def first_event(kind: str, request_id: str | None = None):
    return next(
        (
            event
            for event in events
            if event["kind"] == kind
            and (request_id is None or event.get("request_id") == request_id)
        ),
        None,
    )


initial_request = first_event("model_request", "model-0")
initial_payload = host.store.artifact(initial_request["inputs"][0])
initial_context = json.loads(initial_payload["messages"][1]["content"])
model_options = initial_context["route"]["model_options"]

decisions = []
for index in range(route_view["usage"]["used"]["model_calls"]):
    request_id = f"model-{index}"
    call = host.store.lookup(RUN_ID, request_id)
    receipt = json.loads(call["receipt"])
    request_event = first_event("model_request", request_id)
    raw_event = first_event("model_raw_response", request_id)
    raw_wrapper = host.store.artifact(raw_event["outputs"][0]) if raw_event else {}
    raw = raw_wrapper.get("raw", raw_wrapper)
    message = raw.get("choices", [{}])[0].get("message", {})
    row = {
        "model_request": request_id,
        "status": receipt["execution_status"],
        "error": receipt.get("error"),
        "request_artifact": request_event["inputs"][0]["artifact_id"],
        "raw_response_artifact": raw_event["outputs"][0]["artifact_id"] if raw_event else None,
        "decision_artifact": (receipt.get("output") or {}).get("artifact_id"),
        "provider_model": raw.get("model"),
        "provider_response_id": raw.get("id"),
        "finish_reason": raw.get("choices", [{}])[0].get("finish_reason"),
        "provider_usage": raw.get("usage"),
        "assistant_content": message.get("content"),
    }
    if receipt["execution_status"] == "completed":
        decision = host.store.artifact(receipt["output"])
        tool_call = host.store.lookup(RUN_ID, decision["request_id"])
        tool_receipt = json.loads(tool_call["receipt"]) if tool_call and tool_call["receipt"] else None
        if tool_receipt is None:
            tool_event = next(
                event
                for event in events
                if event["kind"] == "tool"
                and event.get("request_id") == decision["request_id"]
                and event["status"] == "rejected"
            )
            tool_receipt = host.store.artifact(tool_event["outputs"][0])
        row.update(
            {
                "tool_request": decision["request_id"],
                "tool": decision["tool_id"],
                "tool_version": decision["tool_version"],
                "arguments": decision["arguments"],
                "reason": decision["reason"],
                "evidence": decision.get("evidence", []),
                "tool_status": tool_receipt["execution_status"],
                "tool_error": tool_receipt.get("error"),
                "tool_result_artifact": (tool_receipt.get("output") or {}).get("artifact_id"),
                "charged": tool_receipt.get("charged"),
            }
        )
    decisions.append(row)

tool_calls = []
for event in events:
    if event["kind"] != "tool" or event["status"] not in ("completed", "failed", "rejected"):
        continue
    call = host.store.lookup(event["run_id"], event["request_id"])
    if call and call["receipt"]:
        receipt = json.loads(call["receipt"])
    else:
        receipt = host.store.artifact(event["outputs"][0])
    tool_calls.append(
        {
            "event_sequence": event.get("sequence"),
            "event_id": event["event_id"],
            "run_id": event["run_id"],
            "request_id": event["request_id"],
            "tool": receipt["tool_id"],
            "version": receipt["tool_version"],
            "status": receipt["execution_status"],
            "error": receipt.get("error"),
            "charged": receipt["charged"],
            "result_artifact": (receipt.get("output") or {}).get("artifact_id"),
            "execution_id": receipt.get("execution_id"),
            "solver_status": receipt.get("solver_status"),
            "analysis_status": receipt.get("analysis_status"),
            "task_success": receipt.get("task_success"),
        }
    )

nodes = route_view["route"]["nodes"]
node_by_id = {node["node_id"]: node for node in nodes}
target = session["snapshot"]["input"]["task"]["goal"]["data"]["target_m"]


def backend_summary(node_id: str) -> dict:
    node = node_by_id[node_id]
    execution_id = node["summary"]["simulation"]["execution_id"]
    child_run_id = node["summary"]["run_id"]
    backend = RUN_DIR / "sessions" / child_run_id / "executions" / execution_id / "backend"
    control = load_json(backend / "control_spec.json")
    result = load_json(backend / "result.json")
    observations = load_json(backend / "controller_observations.json")
    commands = load_json(backend / "actual_commands.json")
    with gzip.open(backend / "trajectory.json.gz", "rt", encoding="utf-8") as stream:
        rows = json.load(stream)
    errors = [math.dist(row["tip_m"], target) for row in rows]
    files = {
        path.name: {"path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size}
        for path in sorted(backend.iterdir())
        if path.is_file()
    }
    summary = {
        "route_node": node_id,
        "candidate_id": node["summary"]["candidate_id"],
        "child_run_id": child_run_id,
        "execution_id": execution_id,
        "controller_mode": control["mode"],
        "tension_execution_mode": control.get("tension_execution_mode"),
        "solver_status": result["solver_status"],
        "integration_started": True,
        "integration_completed": result["solver_status"] == "completed",
        "trajectory_samples": len(rows),
        "controller_observations": len(observations),
        "time_range_s": [rows[0]["time_s"], rows[-1]["time_s"]],
        "target_world_m": target,
        "initial_tip_world_m": observations[0]["tip_position_m"],
        "final_tip_world_m": rows[-1]["tip_m"],
        "initial_error_m": math.dist(observations[0]["tip_position_m"], target),
        "minimum_post_step_error_m": min(errors),
        "maximum_post_step_error_m": max(errors),
        "final_error_m": errors[-1],
        "evaluation": node["summary"]["evaluation"],
        "evaluation_ref": node["summary"]["evaluation_ref"],
        "robot_description_identity": digest(load_json(backend / "robot_description.json")),
        "files": files,
    }
    if control["mode"] == "gvs_lqr":
        saturation = [flag for row in observations for flag in row["force_limit_saturated"]]
        summary["gvs_lqr_execution"] = {
            "basis": control["effective_parameters"]["basis"]["strategy"],
            "task_feedback_gain": control["effective_parameters"]["task_feedback_gain"],
            "dynamic_system_identity": control["algorithm"]["dynamic_system_identity"],
            "linearization_identity": control["algorithm"]["linearization_identity"],
            "gain_identity": control["algorithm"]["gain_identity"],
            "gain_shape": [len(control["algorithm"]["K"]), len(control["algorithm"]["K"][0])],
            "state_dimension": len(control["algorithm"]["x0"]),
            "input_dimension": len(control["algorithm"]["u0"]),
            "operating_point_source": control["reference"]["source"],
            "operating_point_identity": control["reference"]["operating_point_identity"],
            "q0": control["reference"]["derivation"]["q0"],
            "u0": control["reference"]["derivation"]["u0"],
            "inverse_constraint_violation": control["reference"]["derivation"]["inverse_constraint_violation"],
            "equilibrium_residual_norm": control["reference"]["derivation"]["refined_equilibrium_residual_norm"],
            "predicted_equilibrium_tip_world_m": control["predicted_equilibrium_tip_world_m"],
            "predicted_equilibrium_tip_error_m": math.dist(control["predicted_equilibrium_tip_world_m"], target),
            "linearized_drift_norm_inf": control["algorithm"]["linearized_drift_norm_inf"],
            "resolved_basis": control["algorithm"]["projector"]["resolved_basis"],
            "coordinate_order": control["algorithm"]["projector"]["coordinate_order"],
            "closed_loop_stability_saved": "closed_loop_stable" in control["algorithm"],
            "closed_loop_eigenvalues_saved": "closed_loop_eigenvalues" in control["algorithm"],
            "controllability_or_stabilizability_saved": any(
                key in control["algorithm"] for key in ("controllability_rank", "stabilizability_issue")
            ),
            "force_limit_saturated_channel_samples": sum(bool(flag) for flag in saturation),
            "force_limit_channel_samples": len(saturation),
            "steps_with_any_force_limit_saturation": sum(
                any(row["force_limit_saturated"]) for row in observations
            ),
            "total_steps": len(observations),
            "first_step_saturated_channels": sum(observations[0]["force_limit_saturated"]),
            "final_step_saturated_channels": sum(observations[-1]["force_limit_saturated"]),
            "maximum_absolute_requested_tension_n": max(
                abs(value) for row in observations for value in row["requested_tension_n"]
            ),
            "maximum_projection_residual_rad_m": max(
                row["gvs_projection_residual_max_rad_m"] for row in observations
            ),
            "maximum_rate_projection_residual_rad_m_s": max(
                row["gvs_rate_projection_residual_max_rad_m_s"] for row in observations
            ),
        }
    else:
        summary["tip_feedback_execution"] = {
            "feedback_gain": control["effective_parameters"]["feedback_gain"],
            "damping": control["effective_parameters"]["damping"],
            "max_joint_update_rad": control["effective_parameters"]["max_joint_update_rad"],
            "maximum_absolute_actuator_command_m": max(
                abs(value) for row in commands for value in row.get("actuator_command", [])
            ),
        }
    return summary


gvs_backend = backend_summary("run_gvs_lqr_1")
tip_backend = backend_summary("run_tip_fb_1")
gvs_run = node_by_id["run_gvs_lqr_1"]
tip_run = node_by_id["run_tip_fb_1"]
gvs_configuration = host.store.artifact(gvs_run["summary"]["configuration"])["effective"]
tip_configuration = host.store.artifact(tip_run["summary"]["configuration"])["effective"]
frozen_robot_identity = digest(session["snapshot"]["input"]["robot"]["structure"])
gvs_robot_identity = digest(gvs_configuration["robot"]["structure"])
tip_robot_identity = digest(tip_configuration["robot"]["structure"])
gvs_representation = model_options["options"]["gvs"]["representations"]["structural_linear"]["representation"]
resolved_basis = gvs_backend["gvs_lqr_execution"]["resolved_basis"]

classifications = {
    "model_applicability_use": {
        "rating": "GOOD",
        "evidence": [
            "model-0 uses the representation-specific model_options distinctions to select structural_linear rather than treating all combinations as interchangeable",
            "model-22 preserves WARN as an uncertainty statement and does not claim validated physical truth",
        ],
    },
    "recognition_of_local_control_problem": {
        "rating": "GOOD",
        "evidence": [
            "model-0 selects controller.gvs_lqr as the first hypothesis and calls it the local-model-control option",
            "model-1 says MuJoCo execution is required to judge the local LQR feedback strategy",
        ],
    },
    "warn_interpretation": {
        "rating": "GOOD",
        "evidence": [
            "GVS local_model_control and linearization are WARN in the saved model_options, yet model-0 uses the model and model-1 requests backend validation",
            "model-22 explicitly reports unvalidated WARN limitations and false task_success",
        ],
    },
    "pcc_use": {
        "rating": "GOOD",
        "evidence": [
            "No PCC tool was used and no PCC result was treated as controller-synthesis authority",
            "The first hypothesis directly uses the GVS-LQR combination appropriate to local-model control",
        ],
    },
    "gvs_use": {
        "rating": "GOOD",
        "evidence": [
            "model-0 builds gvs_lqr_structural_linear_mujoco before spending a solve",
            "The saved backend control specification contains the GVS operating point, DynamicSystem, linearization, gain and projector identities",
        ],
    },
    "gvs_representation_choice": {
        "rating": "GOOD",
        "evidence": [
            "model-0 chooses structural_linear because first_order omits interior structural locations",
            "The reason is grounded in saved representation coverage rather than a generic more-coordinates claim",
        ],
    },
    "gvs_basis_consistency": {
        "rating": "GOOD",
        "evidence": [
            "The structural_linear model_options identity equals the resolved projector-basis identity",
            "Saved controller, equilibrium, 12-coordinate projector, 24-state linearization and 6x24 gain all use structural_linear",
        ],
    },
    "operating_point_reasoning": {
        "rating": "QUESTIONABLE",
        "evidence": [
            f"The executable build generated q0/u0 with residual {gvs_backend['gvs_lqr_execution']['equilibrium_residual_norm']:.2e} and predicted target error {gvs_backend['gvs_lqr_execution']['predicted_equilibrium_tip_error_m']:.2e} m",
            "DeepSeek did not explicitly inspect or reason from q0, u0, equilibrium residual, or the large backend departure before labeling the result a wrong or under-driven equilibrium",
        ],
    },
    "linearization_reasoning": {
        "rating": "QUESTIONABLE",
        "evidence": [
            f"The saved chain is dimensionally coherent: 24 states, 6 inputs, structural_linear basis and drift norm {gvs_backend['gvs_lqr_execution']['linearized_drift_norm_inf']:.2e}",
            "No public DynamicSystem/linearization call or inspection of state order, operating-point match, drift, or local-validity range appears in the 23 model decisions",
        ],
    },
    "lqr_reasoning": {
        "rating": "QUESTIONABLE",
        "evidence": [
            "The saved 6x24 gain is dimensionally consistent, but no closed-loop stability/eigenvalue or controllability/stabilizability fact is saved or requested",
            "MuJoCo shows force-limit saturation at every LQR control step (4/6 channels initially and 6/6 finally), yet DeepSeek never identifies saturation explicitly before switching controllers",
        ],
    },
    "backend_solve_timing": {
        "rating": "GOOD",
        "evidence": [
            "model-0 builds a specific structural_linear GVS-LQR hypothesis before model-1 spends solve 1",
            "After a zero-solve diagnosis, model-13 forms a distinct tip-feedback hypothesis before model-15 spends solve 2; no identical rerun occurs",
        ],
    },
    "model_vs_validation_distinction": {
        "rating": "GOOD",
        "evidence": [
            "DeepSeek obtains real MuJoCo evaluations for both hypotheses instead of treating the GVS-predicted target match as task success",
            "model-22 delivers task_success=false and keeps model/backend limitations explicit",
        ],
    },
    "budget_discipline": {
        "rating": "BAD",
        "evidence": [
            "The run consumes 23/24 model calls despite only five substantive route actions plus finish",
            "It repeats the same empty-space read four times, repeatedly rereads the diagnosis, makes three rejected schema/tool calls, and has one length-terminated model request",
        ],
    },
    "evidence_use": {
        "rating": "BAD",
        "evidence": [
            "model-3, model-14 and model-17 use the wrong tool/schema; model-2/model-16/model-18/model-20 reread the same empty candidate space",
            "model-13 calls the error profile almost flat although saved error rises from 0.0504 m to 0.2202 m before ending at 0.1948 m, and it does not surface the all-step force saturation",
        ],
    },
    "stopping_behavior": {
        "rating": "QUESTIONABLE",
        "evidence": [
            "model-22 stops honestly with a valid best incumbent, false task_success and one solve preserved",
            "Its rationale conflates an empty mutation space with lack of an executable third hypothesis; gvs_lqr_first_order_mujoco remained authorized and untried, and the final decision does not explain why its known representation weakness made that solve unnecessary",
        ],
    },
}

failure_modes = {
    "1_pcc_reject_used_for_local_control": {"status": "NOT_TRIGGERED", "evidence": "No PCC tool or PCC control authority appears."},
    "2_gvs_warn_causes_refusal": {"status": "NOT_TRIGGERED", "evidence": "The first executed hypothesis is structural_linear GVS-LQR."},
    "3_gvs_warn_claimed_as_physical_truth": {"status": "NOT_TRIGGERED", "evidence": "Two MuJoCo validations are run and the final failure is reported honestly."},
    "4_structural_advertised_first_order_executes": {"status": "NOT_TRIGGERED", "evidence": "The executed GVS controller/projector basis is structural_linear."},
    "5_mixed_gvs_bases": {"status": "NOT_TRIGGERED", "evidence": "Operating point, state order, gain and projector share the structural_linear resolved basis."},
    "6_bad_lqr_quality_ignored": {"status": "NOT_OBSERVED", "evidence": "No public synthesis-quality verdict was produced; backend saturation was under-analyzed, but DeepSeek did not claim LQR success."},
    "7_backend_disagreement_called_implementation_bug": {"status": "NOT_TRIGGERED", "evidence": "DeepSeek treats the poor GVS-LQR result as a control/equilibrium hypothesis failure, not an implementation defect."},
    "8_physical_robot_changed": {"status": "NOT_TRIGGERED", "evidence": "Both build changes are empty and all frozen/build robot identities match."},
    "9_repeated_backend_solves_without_hypothesis": {"status": "NOT_TRIGGERED", "evidence": "The two solves test distinct structural-linear GVS-LQR and tip-feedback hypotheses."},
}

route_nodes = [
    {
        "node_id": node["node_id"],
        "action": node["action"],
        "status": node["status"],
        "decision": node["request_id"],
        "result_artifact": (node.get("result") or {}).get("artifact_id"),
        "reason": node["selection"]["reason"],
        "next_step": node["selection"]["next_step"],
        "evidence": node["selection"]["evidence"],
        "summary": node["summary"],
    }
    for node in nodes
]

original_audit_path = ORIGINAL_DIR / "behavior_validation.json"
original_audit = read(original_audit_path)
smoke_path = ROOT / "runs" / "stage35_case_b_softagent_smoke_20260924" / "environment_smoke.json"
smoke = read(smoke_path)
provenance = read(RUN_DIR / "retry_provenance.json")
original_route = ORIGINAL_DIR / "inputs" / "route.json"
retry_route = RUN_DIR / "inputs" / "route.json"
final = route_view["route"]["final"]

behavioral_comparison = {
    "comparison_scope": "Behavioral comparison only; the original and retry ledgers, sessions, decisions and artifacts remain separate.",
    "original_audit": rel(original_audit_path),
    "original_trajectory": {
        "run_id": original_audit["run_id"],
        "classification": original_audit["launch_and_environment"]["classification"],
        "status": original_audit["final_route"]["session_status"],
        "model_calls": original_audit["model_requests"],
        "backend_solves": original_audit["backend_solve_attempts"],
        "successful_integrations": original_audit["successful_integrations"],
    },
    "retry_trajectory": {
        "run_id": RUN_ID,
        "classification": "COMPLETED_BEHAVIOR_TRAJECTORY",
        "status": session["status"],
        "model_calls": route_view["usage"]["used"]["model_calls"],
        "backend_solves": route_view["usage"]["used"]["backend_solves"],
        "successful_integrations": route_view["counts"]["successful_integrations"],
    },
    "same_behavior": [
        "Both trajectories select structural_linear GVS-LQR first for the same representation-specific coverage reason.",
        "Both preserve the frozen physical robot and structural_linear basis through the saved controller/projector chain.",
        "Both treat WARN as usable but unvalidated and avoid claiming physical/task success without backend evidence.",
    ],
    "changed_behavior_after_environment_repair": [
        "The original stops after one pre-integration ENVIRONMENT_FAILURE; the retry completes two integrations and two evaluations.",
        "The retry reacts to a poor GVS-LQR score with a diagnosis and a distinct tip-feedback validation, then delivers the better result.",
        "The retry uses substantially more model turns and exhibits repeated evidence reads, three malformed calls and one length failure.",
        "The retry leaves first_order untested and gives an incomplete stopping rationale for doing so.",
    ],
}

report = {
    "experiment": "Stage 3.5 Case B retry: explicit-softagent model-aware local-control behavior validation",
    "run_id": RUN_ID,
    "run_directory": rel(RUN_DIR),
    "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
    "commit": session["snapshot"]["project_commit"],
    "worktree_dirty_at_start": session["snapshot"]["worktree_dirty"],
    "retry_isolation": {
        "original_run_directory": rel(ORIGINAL_DIR),
        "original_route_sha256": sha256(original_route),
        "original_route_hash_matches_seal": sha256(original_route) == ORIGINAL_ROUTE_HASH,
        "retry_route": rel(retry_route),
        "retry_route_sha256": sha256(retry_route),
        "route_differences": provenance["route_differences"],
        "project_differences": provenance["project_differences"],
        "scientific_settings_identical": provenance["scientific_settings_identical"],
        "protected_digests_match": provenance["protected_digests"] == provenance["retry_protected_digests"],
        "original_session_modified": False,
        "trajectories_merged": False,
    },
    "environment_smoke": {**smoke, "report": rel(smoke_path)},
    "source_fix": original_audit["tiny_source_fix"],
    "usage": route_view["usage"],
    "route_counts": route_view["counts"],
    "model_level_tool_requests": len([decision for decision in decisions if decision.get("tool_request")]),
    "rejected_model_level_tool_requests": len([decision for decision in decisions if decision.get("tool_status") == "rejected"]),
    "failed_model_requests": len([decision for decision in decisions if decision["status"] != "completed"]),
    "model_options": model_options,
    "authorized_combinations": list(route_view["combinations"]),
    "fixed_discretization": session["snapshot"]["input"]["policy"]["discretization"],
    "physical_robot_identity": {
        "frozen": frozen_robot_identity,
        "gvs_build": gvs_robot_identity,
        "tip_feedback_build": tip_robot_identity,
        "all_match": frozen_robot_identity == gvs_robot_identity == tip_robot_identity,
        "build_changes": {
            node["node_id"]: node["selection"]["changes"]
            for node in nodes
            if node["action"] == "build"
        },
    },
    "decisions": decisions,
    "tool_calls": tool_calls,
    "route_nodes": route_nodes,
    "backend_validations": [gvs_backend, tip_backend],
    "scientific_chain": {
        "selected_gvs_basis": "structural_linear",
        "model_options_representation_identity": gvs_representation["identity"],
        "resolved_execution_basis_identity": digest(resolved_basis),
        "basis_identity_matches": digest(resolved_basis) == gvs_representation["identity"],
        "generalized_coordinate_dimension": gvs_representation["generalized_coordinate_dimension"],
        "state_dimension": gvs_representation["state_dimension"],
        **gvs_backend["gvs_lqr_execution"],
    },
    "evaluation_comparison": {
        "gvs_lqr_structural_linear": gvs_run["summary"]["evaluation"],
        "tip_feedback": tip_run["summary"]["evaluation"],
        "tip_feedback_error_ratio_vs_gvs": tip_backend["final_error_m"] / gvs_backend["final_error_m"],
        "tip_feedback_error_reduction_fraction": 1.0 - tip_backend["final_error_m"] / gvs_backend["final_error_m"],
        "delivered_candidate": final["candidate_id"],
        "delivered_task_success": final["task_success"],
    },
    "behavior_classifications": classifications,
    "failure_mode_checks": failure_modes,
    "final_route": {
        "session_status": session["status"],
        "delivery_status": final["delivery_status"],
        "explicit_delivery": final["explicit_delivery"],
        "candidate_id": final["candidate_id"],
        "evaluation": final["evaluation"],
        "task_success": final["task_success"],
        "stop_reason": final["stop_reason"],
    },
    "behavioral_comparison_with_original": behavioral_comparison,
    "main_conclusion": (
        "DeepSeek recognized the local-model-control problem, used WARN-level GVS rather than PCC, chose and preserved "
        "structural_linear coherently, and required MuJoCo validation. The repaired environment exposed an important "
        "weakness: it under-analyzed the operating point, LQR quality and pervasive force saturation, spent most model "
        "turns on repeated reads/protocol corrections, and gave an incomplete reason for leaving the third authorized "
        "combination untested. It nevertheless avoided false success and delivered the better validated baseline honestly."
    ),
    "scope_limitation": (
        "Case B is not the official stabilize_tip benchmark because that task is not yet executable. It validates "
        "model-aware local-control orchestration around the frozen reach operating point. It does not prove disturbance "
        "rejection, robust stabilization, real-robot stability, formal closed-loop robustness, or official stabilization success."
    ),
    "recommendation": "2. LLM reasoning weakness -> inspect behavior before architecture changes.",
    "case_c_started": False,
}

atomic_json(RUN_DIR / "behavior_validation.json", report)

decision_rows = [
    ("Choose the initial local-control hypothesis", "model-0", "structural_linear GVS-LQR build", "0"),
    ("Validate the GVS-LQR hypothesis", "model-1", "MuJoCo run; valid, 0.194811 m, false", "1"),
    ("Investigate poor GVS-LQR result", "model-4", "saved-trajectory diagnosis", "0"),
    ("Choose a distinct alternative", "model-13", "tip_feedback_family_mujoco build", "0"),
    ("Validate the alternative", "model-15", "MuJoCo run; valid, 0.025987 m, false", "1"),
    ("Stop or spend final allowance", "model-22", "finish with tip-feedback incumbent", "0"),
]

lines = [
    "# Stage 3.5 Case B retry - behavior validation",
    "",
    "## A. Isolated retry provenance",
    "",
    f"- Retry directory: `{rel(RUN_DIR)}`; run ID `{RUN_ID}`.",
    f"- Explicit interpreter: `{smoke['python_executable']}`.",
    f"- Environment-only smoke passed: key present `{smoke['deepseek_api_key_present']}`, `mujoco.MjModel` present `{smoke['mujoco_mjmodel_present']}`, 20 finite local steps, zero DeepSeek requests.",
    f"- Original sealed Route SHA-256 remains `{sha256(original_route)}`. The retry Route differs only at `/run_id`; the project differs only at `/grant_id`.",
    "- Frozen task, robot, policy, guidance, model options, controller combinations, tool surface and budget have identical protected digests. The original environment-failure trajectory was not resumed or modified.",
    "",
    "## B. Experiment result",
    "",
    f"- Branch `{report['branch']}`; source commit `{report['commit']}`.",
    f"- DeepSeek model requests: **{route_view['usage']['used']['model_calls']}/24**; model-level tool requests: **{report['model_level_tool_requests']}**; charged tool calls: **{route_view['usage']['used']['tool_calls']}/60**.",
    f"- Backend validations: **{route_view['usage']['used']['backend_solves']}/3**; successful integrations: **{route_view['counts']['successful_integrations']}**; evaluations: **{route_view['counts']['evaluations']}**.",
    f"- Final Route status: **`{session['status']}`**, delivery **`{final['delivery_status']}`**.",
    f"- Delivered candidate `{final['candidate_id']}`: position error **{final['evaluation']['metrics'][0]['value']:.9f} m**, tolerance **0.01 m**, task success **{str(final['task_success']).lower()}**.",
    "",
    "## C. Available choices and identity checks",
    "",
    "- PCC local-model control and linearization are `REJECT`.",
    "- GVS `first_order` is 8 q / 16 state and WARN for local control/linearization; it omits interior structural locations.",
    "- GVS `structural_linear` is 12 q / 24 state, WARN for local control/linearization, and ALLOW for reduced dynamics/shape.",
    "- Serial bending is 12 q / 24 state at the fixed 3+3-cell discretization and is the MuJoCo execution model.",
    "- Authorized combinations remained tip feedback, GVS-LQR first_order and GVS-LQR structural_linear. Physical mutation space remained empty.",
    f"- Frozen/GVS-build/tip-build physical robot identities match: **{report['physical_robot_identity']['all_match']}**.",
    f"- Structural-linear model-options and execution projector identities match: **{report['scientific_chain']['basis_identity_matches']}**.",
    "",
    "## D. Important DeepSeek decisions",
    "",
    "| Question | Model turn | Decision/evidence outcome | Backend solves |",
    "|---|---|---|---:|",
]
for question, turn, outcome, cost in decision_rows:
    lines.append(f"| {question} | `{turn}` | {outcome} | {cost} |")

lines.extend(
    [
        "",
        "DeepSeek chose `structural_linear` immediately because its saved applicability record does not omit interior structural locations. It built before running, validated the poor result, diagnosed it without another solve, then formed and validated a distinct tip-feedback hypothesis. It ultimately preserved one backend solve.",
        "",
        "The decision trace was inefficient: four duplicate reads of the empty candidate space, repeated diagnosis reads, three rejected tool/schema calls (`model-3`, `model-14`, `model-17`), and one length-terminated response (`model-21`). All request, raw-response, decision, receipt and artifact references are enumerated in `behavior_validation.json`.",
        "",
        "## E. Scientific chain and backend evidence",
        "",
        f"- GVS operating point: 12 q / 6 tendon inputs, inverse constraint violation `{report['scientific_chain']['inverse_constraint_violation']:.3e}`, refined residual `{report['scientific_chain']['equilibrium_residual_norm']:.3e}`, predicted tip error `{report['scientific_chain']['predicted_equilibrium_tip_error_m']:.3e}` m.",
        f"- DynamicSystem/linearization/gain identities are saved; state dimension 24, input dimension 6, gain 6x24, drift infinity norm `{report['scientific_chain']['linearized_drift_norm_inf']:.3e}`.",
        "- The saved control specification contains no closed-loop stability/eigenvalue or controllability/stabilizability result.",
        f"- Structural-linear GVS-LQR completed 35 samples. Error moved from `{gvs_backend['initial_error_m']:.6f}` m initially to `{gvs_backend['maximum_post_step_error_m']:.6f}` m maximum and `{gvs_backend['final_error_m']:.6f}` m final.",
        f"- Its command was force-limit saturated on **{report['scientific_chain']['steps_with_any_force_limit_saturation']}/{report['scientific_chain']['total_steps']}** controller steps: 4/6 channels initially and 6/6 finally. Maximum absolute requested tension was `{report['scientific_chain']['maximum_absolute_requested_tension_n']:.3f}` N against 8 N limits. Task-feedback gain was zero.",
        f"- Tip feedback completed 35 samples and ended at `{tip_backend['final_error_m']:.6f}` m, a `{report['evaluation_comparison']['tip_feedback_error_reduction_fraction'] * 100:.1f}%` reduction versus GVS-LQR, but still failed the 0.01 m tolerance.",
        "- Both backend solver statuses are `completed`; both evaluations are valid. The numerical reach result is secondary to the behavior audit.",
        "",
        "## F. Behavior audit",
        "",
        "| Category | Rating | Evidence |",
        "|---|---|---|",
    ]
)
for name, item in classifications.items():
    evidence = "; ".join(item["evidence"])
    lines.append(f"| {name.replace('_', ' ').title()} | **{item['rating']}** | {evidence} |")

lines.extend(["", "### Required failure-mode checks", "", "| Failure mode | Result | Evidence |", "|---|---|---|"])
for name, item in failure_modes.items():
    lines.append(f"| {name} | {item['status']} | {item['evidence']} |")

lines.extend(
    [
        "",
        "## G. Behavioral comparison with the original Case B",
        "",
        "The records remain separate. The original trajectory is still an `ENVIRONMENT_FAILURE`: it selected the same structural-linear GVS-LQR hypothesis but failed before integration and stopped without fabrication. The retry preserved that scientific setup, completed two integrations, reacted to the poor GVS result with a distinct controller hypothesis, and delivered the better valid evaluation.",
        "",
        "The retry confirms the original model-selection strengths, but it also exposes behavior the failed run could not: weak inspection of operating-point/LQR quality, pervasive saturation left unnamed, repeated evidence reads/protocol corrections, and an incomplete explanation for not testing the remaining first-order combination.",
        "",
        "## H. Main conclusion",
        "",
        report["main_conclusion"],
        "",
        "## I. Scope limitation",
        "",
        "**" + report["scope_limitation"] + "**",
        "",
        "## J. Next recommendation",
        "",
        "**" + report["recommendation"] + "**",
        "",
        "Case C was not started.",
        "",
    ]
)
(RUN_DIR / "behavior_validation.md").write_text("\n".join(lines), encoding="utf-8")

print(
    json.dumps(
        {
            "json": rel(RUN_DIR / "behavior_validation.json"),
            "markdown": rel(RUN_DIR / "behavior_validation.md"),
            "status": session["status"],
            "model_calls": route_view["usage"]["used"]["model_calls"],
            "backend_solves": route_view["usage"]["used"]["backend_solves"],
            "task_success": final["task_success"],
            "recommendation": report["recommendation"],
        },
        indent=2,
    )
)
