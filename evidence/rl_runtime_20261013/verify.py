"""One fixed campaign, one frozen-policy episode, one captured physical step."""
import json
from pathlib import Path
import sys
import time

from tools.rl import run

ROOT = Path(run.__file__).resolve().parents[2]
EVIDENCE = ROOT / "evidence/rl_runtime_20261013"
RUN_ID = "migration-20261013"


def wait_for(predicate, timeout=125):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = run.status(RUN_ID)
        if predicate(state):
            return state
        if state["status"] in ("failed", "interrupted"):
            raise RuntimeError(json.dumps(state))
        time.sleep(0.03)
    raise RuntimeError("Verification wait expired; no new campaign is authorized")


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    manifest = EVIDENCE / "campaign.json"
    if manifest.exists():
        raise RuntimeError("Campaign already allocated. Repair/resume only its existing run; never rerun this allocator")
    config = run.read_json(Path(run.__file__).with_name("config.json"))
    config["stop_at_boundary"] = 1024
    run.write_json(manifest, dict(run_id=RUN_ID, budget=config["budget"], seed=17,
                                 worker_limit=2, external_model_requests=0, status="allocated"))
    evidence = dict(run_id=RUN_ID, campaign_budget=config["budget"], verification_complete=False)
    try:
        evidence["start"] = run.start(config, RUN_ID)
        active = wait_for(lambda state: state.get("awaiting_stop_at_boundary") == 1024)
        evidence["active_status"] = active
        evidence["stop_request"] = run.stop(RUN_ID)
        first = wait_for(lambda state: state["status"] == "stopped" and not state["worker_alive"])
        evidence["first_worker"] = first
        run.write_json(EVIDENCE / "verification.json", evidence)
        assert first["stop_reason"] == "user_stop"
        assert first["consumed"]["attempted_actions"] == 1024
        assert first["inherited"]["rollout_optimizations"] == 4
        assert first["inherited"]["optimization_epochs"] == 40
        assert first["inherited"]["schedule"]["total_timesteps"] == 2048
        assert first["inherited"]["schedule"]["progress_remaining"] == 0.5
        assert first["workers"][0]["parameter_change_l2"] > 0
        evidence["resume"] = run.resume(RUN_ID)
        final = wait_for(lambda state: state["status"] in ("completed", "stopped") and not state["worker_alive"])
        evidence["final_worker"] = final
        directory = Path(final["artifacts"])
        restore = run.read_json(directory / f'restore-{final["worker_token"]}.json')
        evidence["restore"] = restore
        assert restore["passed"] and restore["fresh_episode"]
        assert restore["expected"] == first["inherited"]
        assert final["consumed"]["attempted_actions"] == 2048
        assert final["consumed"]["active_seconds"] > first["consumed"]["active_seconds"]
        assert final["consumed"]["active_seconds"] <= 120
        assert final["inherited"]["num_timesteps"] == 2048
        assert final["inherited"]["rollout_optimizations"] == 8
        assert final["inherited"]["optimization_epochs"] == 80
        assert final["inherited"]["schedule"]["total_timesteps"] == 2048
        assert final["inherited"]["schedule"]["progress_remaining"] == 0.0
        assert len(final["workers"]) == 2
        assert final["workers"][1]["parameter_change_l2"] > 0
        before = final["consumed"].copy()
        try:
            run.resume(RUN_ID)
        except RuntimeError as error:
            evidence["exhausted_resume_rejected"] = str(error)
        else:
            raise AssertionError("Exhausted campaign resumed")
        assert run.status(RUN_ID)["consumed"] == before
        evidence["training_verification_complete"] = True
    except Exception as error:
        evidence["incomplete_reason"] = f"{type(error).__name__}: {error}"
        run.write_json(EVIDENCE / "verification.json", evidence)
        raise
    # These are each allocated once. Training is finished before either check.
    evaluation = run.evaluate(ROOT / "evidence/rl_pilot_20261013/round2_direct/policy.zip", EVIDENCE / "existing-policy")
    evidence["existing_policy_evaluation"] = evaluation
    metrics = evaluation["episodes"][0]
    assert metrics["passed"] and metrics["trajectory_rows"] == 36
    assert metrics["counts"]["attempted_actions"] == 35
    assert metrics["counts"]["attempted_physics_steps"] == 700
    assert metrics["holding_sample_steps"] == list(range(30, 36))
    source = "evidence/rl_pilot_20261013/round2_direct/evaluation/result.json"
    historical = run.read_json(ROOT / source)["episodes"][0]
    evidence["historical_comparison"] = dict(source=source, absolute_tolerance=1e-10,
        justification="same saved policy, initializer, physics and installed versions; roundoff allowance only",
        deltas={key: metrics[key] - historical[key] for key in
                ("terminal_position_error_m", "holding_max_position_error_m", "holding_max_speed_m_s")})
    assert all(abs(delta) <= 1e-10 for delta in evidence["historical_comparison"]["deltas"].values())
    evidence["existing_failure_replay"] = run.diagnose(ROOT / "evidence/rl_pilot_20261013/direct_capture.npz",
                                                        EVIDENCE / "existing-failure", replay=True)
    assert evidence["existing_failure_replay"]["replay"]["reproduced"]
    evidence["verification_complete"] = True
    run.write_json(EVIDENCE / "verification.json", evidence)
    print(json.dumps(dict(verification_complete=True, actions=final["consumed"]["attempted_actions"],
                         active_seconds=final["consumed"]["active_seconds"], optimizations=8, epochs=80,
                         existing_policy_passed=evaluation["passed"], failure_reproduced=True)))


if __name__ == "__main__":
    main()
