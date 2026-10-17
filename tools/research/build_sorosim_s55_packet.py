"""Rebuild the compact S5.5/S5-T decision evidence from sealed records."""

import json
import hashlib
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "evidence" / "sorosim_s55"
IDS = {
    "solve_1": "32af0d4b524ff9c703e8f67e9e3c97d471d65b8651cb859ef58bcf34b789db7b",
    "solve_2": "af0f3168bc4fc94efcffcff55ce26e7b8241f99a3912a93b7d07ef56d6795bbf",
    "replay_1": "ed5177fafb89f920708f1eea018e67c75c70df313252ca75e0ca33efb0a66f63",
    "replay_2": "a9257722a8f765fbac48ef3e4a5c32024fff95d7a51f9b5a7a6bc4e4603571bb",
    "bestfeasible": "cebf11fca474d18456a03ac4d6cd2c88e4c8463ff2184521b6da5ba0920caf9d",
}


def read(name):
    return json.loads((ROOT / f"{name}.json").read_text(encoding="utf-8"))


def write(name, value):
    (ROOT / f"{name}.json").write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def build():
    manifest = read("optimality_study/archive_manifest")
    with tarfile.open(ROOT / "optimality_study" / "immutable_artifacts.tar.gz") as archive:
        artifacts = {}
        for key, artifact_id in IDS.items():
            raw = archive.extractfile(f"artifacts/{artifact_id}.json").read()
            if hashlib.sha256(raw).hexdigest() != artifact_id:
                raise ValueError(f"Archived artifact hash mismatch: {artifact_id}")
            artifacts[key] = json.loads(raw)
    preflight = read("p3_warm_derivative_preflight")
    optimality = {
        "stage": "S5-T P3/P4",
        "study": "sorosim-s5t-optimality-20261017",
        "archive_sha256": manifest["archive_sha256"],
        "raw_artifact_ids": IDS,
        "initial_preflight": {
            "variables": preflight["variables"],
            "equalities": preflight["equalities"],
            "optimized_task_inequalities": preflight["optimized_task_inequalities"],
            "original_task_predicates": preflight["original_task_predicates"],
            "warm_scaled_violation": preflight["warm_start"]["scaled_violation"],
            "objective_directional_relative_error": preflight["objective_relative_error"],
            "constraint_directional_relative_error": preflight["constraint_relative_error"],
            "charged_s": preflight["charged_numerical_s"],
        },
        "attempts": [],
        "bestfeasible_between_attempts": {
            "source_artifact_id": IDS["bestfeasible"],
            **{
                key: artifacts["bestfeasible"][key]
                for key in ("bestfeasible_report", "posthoc_verification", "diagnostic_cost_s", "qualification")
            },
        },
        "conclusion": {
            "base_kkt_verified": False,
            "full_lagrangian_design_derivative": "unavailable",
            "reoptimized_plus_minus": "not_admitted_without_valid_base_kkt",
            "delta_s": "unavailable",
            "regional_L": "unavailable",
            "strict_descent_certificate": "unavailable",
            "physical_acceptance": "unmeasured",
        },
    }
    for index in (1, 2):
        result = artifacts[f"solve_{index}"]
        facts = result["mathematical_facts"]
        kkt = facts["kkt"]
        replay = artifacts[f"replay_{index}"]
        replay_facts = replay["mathematical_facts"]
        optimality["attempts"].append({
            "number": index,
            "source_artifact_id": IDS[f"solve_{index}"],
            "checkpoint_artifact_id": result["checkpoint_reference"]["artifact_id"],
            "independent_replay_artifact_id": IDS[f"replay_{index}"],
            "initial_objective": facts["initial_objective"],
            "objective": facts["objective"],
            "solver_exitflag": facts["exitflag"],
            "iterations": facts["iterations"],
            "function_evaluations": facts["function_evaluations"],
            "raw_equals_selected": kkt["same_as_selected_trajectory"],
            "raw_scaled_primal_violation": kkt["primal_inf"],
            "raw_stationarity_inf": kkt["stationarity_inf"],
            "raw_dual_violation": kkt["dual_violation"],
            "raw_complementarity_inf": kkt["complementarity_inf"],
            "multipliers_count": {key: len(value) for key, value in kkt["multipliers"].items()},
            "active_task_constraints": kkt["active_task_constraints"],
            "original_sampled_task_satisfied": facts["task"]["original_sampled_requirements_satisfied"],
            "charged_numerical_s": result["charged_numerical_s"],
            "replay": {
                "passed": replay_facts["passed"],
                "independent_scaled_violation": replay_facts["independent_scaled_violation"],
                "reintegrated_scaled_state_error": replay_facts["reintegrated_scaled_state_error"],
                "force_residual_max_nm2": replay_facts["force_residual_max_nm2"],
                "charged_numerical_s": replay["charged_numerical_s"],
            },
        })
    write("p3_p4_optimality", optimality)

    p0, p1, p2, ppo = (read(name) for name in (
        "p0_equivalence", "p1_refinement", "p2_matched_state", "p0_ppo_diagnosis"
    ))
    requirements = artifacts["solve_1"]["task_requirements"]
    packet = {
        "schema": "sorosim_s55_s5t_feedback_v1",
        "scope": "Future Agent decision evidence; saved diagnostics, no live model pilot",
        "frozen_task": {
            "binding": requirements["binding"],
            "constraints": requirements["constraints"],
            "sample_times_s": [round(i * .01, 2) for i in range(36)],
            "world_target_m": [.29, .035, .19],
        },
        "model_and_candidate": {
            "model_identity": p1["model_identity"],
            "design_identity": requirements["binding"]["design_identity"],
            "candidate_artifact_id": requirements["binding"]["candidate"],
            "physical_scene_identity": p2["scene_identity"],
            "physical_physics_identity": p2["physics_identity"],
            "pinned_sorosim_commit": p1["pinned_upstream"]["commit"],
        },
        "evaluated_signatures": {
            key: {
                "sha256": value["proposed_identity_sha256"],
                "equivalent_historical": [
                    {"study": match["study"], "reference": match["reference"], "outcome": match["outcome"]}
                    for match in value["matches"]
                ],
                "admitted": value["admitted"],
            }
            for key, value in p0["comparisons"].items()
        },
        "controller_routes": {
            "fixed_tension": "available for bounded replays",
            "nmpc": "historical S5-B valid failure; equivalent repeat withheld",
            "ppo_direct": "available; original training numerically unstable",
            "ppo_residual": "available; zero saved training numerical failures",
        },
        "integration_refinement": {
            key: {field: value.get(field) for field in (
                "reference", "status", "complete", "original_task_satisfied", "root_count",
                "holding_max_speed_m_s", "holding_max_position_error_m", "terminal_position_error_m"
            )} for key, value in p1["results"].items()
        },
        "matched_state": [{
            "time_s": row["time_s"],
            "following_command_index": row["following_command_index"],
            "projection_curvature_residual_max_rad_m": row["projection"]["curvature_residual_max_rad_m"],
            "eight_substep": {key: row["resolutions"]["8"][key] for key in ("position", "velocity")},
            "four_to_eight": row["eight_minus_four"],
            "historical_open_loop_gap": row["historical_open_loop_endpoint_gap"],
        } for row in p2["checkpoints"]],
        "mechanisms": {
            "H1": "Strong discretization sensitivity; continuous-time convergence unresolved",
            "H2": "Reduced-state projection and cross-model initial output differences",
            "H3": "Same-state response disagreement with numerical and projection confounders",
            "H4": "Historical open-loop gap exceeds matched one-step gap; history contributes",
            "unique_cause": "unresolved",
        },
        "ppo_numerical_failure_categories": {
            "direct": {key: ppo["routes"]["direct"]["diagnosis"][key] for key in (
                "recorded_failures", "warnings", "engine_time_resets", "nonfinite_failures",
                "episode_actions", "training_action_quarters"
            )},
            "residual": {key: ppo["routes"]["residual"]["diagnosis"][key] for key in (
                "recorded_failures", "warnings", "engine_time_resets", "nonfinite_failures"
            )},
        },
        "optimality": {
            "base_kkt_verified": False,
            "attempts": [{key: row[key] for key in (
                "solver_exitflag", "raw_scaled_primal_violation", "raw_stationarity_inf",
                "raw_dual_violation", "raw_complementarity_inf", "source_artifact_id"
            )} for row in optimality["attempts"]],
            "multiplier_reliability": "Full NLP arrays saved; primal and stationarity tolerances fail",
            "structural_sensitivity": "unavailable; fixed-command A/B secant is not reoptimized sensitivity",
            "conditional_descent": "theorem under stated assumptions; no numerical certificate",
        },
        "budget": {
            "p1_refinement_study": {"new_integrations": 3, "completed": 2, "partial": 1, "remaining_public_operations": 0},
            "p2_matched_study": p2["accounting"],
            "p3_optimality_study": {
                "full_nlp": 2, "mathematical_replays": 2, "remaining_public_operations": 0,
                "remaining_full_nlp": 0, "remaining_replays": 0,
                "charged_numerical_s": read("optimality_study/disposition")["resource_use"]["numerical_s"],
            },
            "p4_perturbations_used": 0,
            "new_ppo_training_actions": 0,
            "live_provider_requests": 0,
        },
        "agent_guidance": {
            "permitted_next_decisions": [
                "improve numerical integration", "revise model fidelity", "inspect state projection",
                "diagnose controller performance", "change structural parameters", "continue NMPC research",
                "continue direct PPO", "continue residual PPO", "request discriminating experiment", "stop"
            ],
            "proposal_fields": [
                "hypothesis", "difference_from_existing_evidence", "supporting_and_weakening_observations",
                "decision_impact", "expected_scope_and_cost"
            ],
            "novelty_gate": "Harness verifies resolved scientific identity and executability; equivalent S5-Agent configurations are not unexplored physical candidates",
            "interpretation": "Agent explanation is a hypothesis, not proof; no invented probabilities or information gain",
        },
        "source_evidence": {name: f"{name}.json" for name in (
            "p0_equivalence", "p0_ppo_diagnosis", "p1_refinement", "p2_projection_audit",
            "p2_matched_state", "p3_p4_saved_audit", "p3_warm_derivative_preflight", "p3_p4_optimality"
        )},
    }
    write("agent_feedback_packet", packet)


if __name__ == "__main__":
    build()
