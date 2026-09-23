"""One-off, read-only extraction of the sealed Case A Route evidence."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.platform_host import Host  # noqa: E402
from tools.state_io import atomic_json  # noqa: E402
from extensions.tendon_family.route import view  # noqa: E402


run_dir = Path(__file__).resolve().parent
run_id = "stage35-case-a-live"
host = Host(run_dir, run_id)
session = host.store.session(run_id)
route_view = view(host)
assert session["status"] == "stopped"
assert route_view["route"]["final"]["explicit_delivery"] is True

with host.store.connect(True) as db:
    events = [json.loads(row[0]) for row in db.execute("SELECT body FROM events ORDER BY seq")]

def first_event(kind, request_id=None):
    return next((event for event in events if event["kind"] == kind
                 and (request_id is None or event.get("request_id") == request_id)), None)

initial_request = first_event("model_request", "model-0")
initial_payload = host.store.artifact(initial_request["inputs"][0])
initial_context = json.loads(initial_payload["messages"][1]["content"])
options = initial_context["route"]["model_options"]["options"]
model_options = {
    name: ({strategy: {
        "uses": item["uses"], "representation": item["representation"],
        "basis_argument": item.get("basis_argument"), "backend_solves": item["backend_solves"],
        "tools": item["tools"]}
        for strategy, item in option["representations"].items()}
        if name == "gvs" else {
            "uses": option["uses"], "representation": option["representation"],
            "backend_solves": option["backend_solves"], "tools": option["tools"]})
    for name, option in options.items()
}

decisions = []
for index in range(route_view["usage"]["used"]["model_calls"]):
    request_id = f"model-{index}"
    call = host.store.lookup(run_id, request_id)
    receipt = json.loads(call["receipt"])
    request_event = first_event("model_request", request_id)
    raw_event = first_event("model_raw_response", request_id)
    row = {
        "model_request": request_id,
        "status": receipt["execution_status"],
        "error": receipt.get("error"),
        "request_artifact": request_event["inputs"][0]["artifact_id"],
        "raw_response_artifact": raw_event["outputs"][0]["artifact_id"] if raw_event else None,
        "decision_artifact": receipt.get("output", {}).get("artifact_id") if receipt["execution_status"] == "completed" else None,
    }
    if receipt["execution_status"] == "completed":
        decision = host.store.artifact(receipt["output"])
        tool_call = host.store.lookup(run_id, decision["request_id"])
        tool_receipt = json.loads(tool_call["receipt"]) if tool_call and tool_call["receipt"] else None
        if tool_receipt is None:
            tool_event = next(event for event in events if event["kind"] == "tool"
                              and event.get("request_id") == decision["request_id"]
                              and event["status"] == "rejected")
            tool_receipt = host.store.artifact(tool_event["outputs"][0])
        row.update({
            "tool_request": decision["request_id"],
            "tool": decision["tool_id"],
            "tool_version": decision["tool_version"],
            "arguments": decision["arguments"],
            "reason": decision["reason"],
            "evidence": decision.get("evidence", []),
            "tool_status": tool_receipt["execution_status"],
            "tool_error": tool_receipt.get("error"),
            "tool_result_artifact": (tool_receipt.get("output") or {}).get("artifact_id"),
        })
    decisions.append(row)

tool_calls = []
for event in events:
    if event["kind"] != "tool" or event["status"] not in ("completed", "failed", "rejected"):
        continue
    call = host.store.lookup(event["run_id"], event["request_id"])
    receipt = json.loads(call["receipt"]) if call and call["receipt"] else host.store.artifact(event["outputs"][0])
    tool_calls.append({
        "event_sequence": event["sequence"], "event_id": event["event_id"],
        "run_id": event["run_id"], "request_id": event["request_id"],
        "tool": receipt["tool_id"], "version": receipt["tool_version"],
        "status": receipt["execution_status"], "error": receipt.get("error"),
        "charged": receipt["charged"],
        "result_artifact": (receipt.get("output") or {}).get("artifact_id"),
    })

nodes = route_view["route"]["nodes"]
node_by_child = {node["summary"]["run_id"]: node for node in nodes
                 if node["action"] == "run" and node["summary"].get("run_id")}
backend_solves = []
for tool in tool_calls:
    if tool["tool"] != "simulation.run" or not tool["charged"]["backend_solves"]:
        continue
    node = node_by_child[tool["run_id"]]
    backend_solves.append({
        "event_sequence": tool["event_sequence"], "request_id": tool["request_id"],
        "run_id": tool["run_id"], "route_node": node["node_id"],
        "candidate_id": node["summary"]["candidate_id"],
        "preceding_model_decision": node["request_id"].removesuffix("-tool"),
        "result_artifact": tool["result_artifact"],
        "evaluation_artifact": node["summary"]["evaluation_ref"]["artifact_id"],
        "position_error_m": node["summary"]["evaluation"]["metrics"][0]["value"],
        "task_success": node["summary"]["task_success"],
    })

classifications = {
    "model_applicability_use": {
        "rating": "GOOD",
        "evidence": ["model-0 raw response explicitly cites model_options and PCC reachability ALLOW", "model-4 raw response treats PCC shape_prediction WARN as coarse", "model-5 reasons that GVS equilibrium does not directly answer the actuator-command validation question"],
    },
    "model_hierarchy_understanding": {
        "rating": "GOOD",
        "evidence": ["model-0-tool chooses zero-backend PCC description", "model-5-tool identifies MuJoCo serial-bending execution as validation", "No GVS equilibrium, DynamicSystem, linearization or LQR call occurs"],
    },
    "pcc_use": {
        "rating": "QUESTIONABLE",
        "evidence": ["model-0-tool describes PCC but no pcc_forward call follows", "model-7-tool repeats the same cached description", "model-4-tool declares baseline unreachable from flexible lengths 0.16+0.12 m while the saved design also has rigid connector and tip offsets; the stated bound is incomplete"],
    },
    "gvs_use": {"rating": "GOOD", "evidence": ["No GVS tool called; no static-equilibrium or control-design question required it"]},
    "gvs_basis_consistency": {"rating": "NOT_OBSERVED", "evidence": ["No basis-aware GVS tool called"]},
    "backend_solve_timing": {
        "rating": "QUESTIONABLE",
        "evidence": ["First solve is run-1 at event 58 after model-5-tool, based on a zero-solve build and geometric argument", "model-4-tool uses an incomplete length bound and never tests geometry with pcc_forward", "Second solve is run-2 at event 157 after model-15-tool changes feedback gain to 8.0 without establishing the direction or cause of run-1 error"],
    },
    "budget_discipline": {
        "rating": "QUESTIONABLE",
        "evidence": ["model-7-tool repeats pcc_describe", "model-9-tool and model-12-tool reread the same evaluation", "All 18 model requests and both backend solves are consumed; model-14 is a length-truncated response recovered by the platform"],
    },
    "evidence_use": {
        "rating": "QUESTIONABLE",
        "evidence": ["run-1, build-2, run-2 and finish cite saved node/evaluation artifacts", "model-3-tool and model-10-tool are rejected for extra nested reason fields", "model-6-tool fails on pointer '/' with error ''", "model-9-tool and model-12-tool reread the same metric-only evaluation; model-15-tool chooses gain 8.0 without observed error direction"],
    },
    "stopping_behavior": {
        "rating": "GOOD",
        "evidence": ["model-17-tool explicitly delivers the valid session incumbent and reports task_success false", "No further scientific tools called after finish-1"],
    },
}

final = route_view["route"]["final"]
report = {
    "experiment": "Stage 3.5 Case A: simple reach_free, no obstacle/contact/control-design requirement",
    "run_id": run_id,
    "run_directory": str(run_dir.relative_to(ROOT)).replace("\\", "/"),
    "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
    "commit": session["snapshot"]["project_commit"],
    "worktree_dirty_at_start": session["snapshot"]["worktree_dirty"],
    "task": {"task_id": initial_context["task"]["task_id"],
             "environment_id": initial_context["task"]["environment"]["data"]["environment"]["environment_id"],
             "target_m": initial_context["task"]["goal"]["data"]["target_m"],
             "tolerance_m": initial_context["task"]["evaluator"]["parameters"]["data"]["tolerance_m"]},
    "model_options_source": initial_context["route"]["model_options"]["source"],
    "available_model_options": model_options,
    "route_visible_tool_versions": {name: version for name, version in
        initial_context["policy"]["tool_bindings"].items()
        if name.startswith(("kinematics.pcc", "dynamics.gvs", "statics.gvs", "linearization.", "control.lqr"))},
    "available_execution_combinations": initial_context["route"]["combinations"],
    "budget": route_view["usage"],
    "model_requests": len(decisions), "tool_requests": len(tool_calls),
    "charged_tool_calls": route_view["usage"]["used"]["tool_calls"],
    "ordered_llm_decisions": decisions, "ordered_tool_calls": tool_calls,
    "backend_solves": backend_solves,
    "route_nodes": [{"node_id": n["node_id"], "action": n["action"], "status": n["status"],
                     "decision": n["request_id"], "result_artifact": n["result"]["artifact_id"],
                     "reason": n["selection"]["reason"], "next_step": n["selection"]["next_step"],
                     "evidence": n["selection"]["evidence"]} for n in nodes],
    "classifications": classifications,
    "final_task_result": {"candidate_id": final["candidate_id"], "evaluation": final["evaluation"],
                          "delivery_status": final["delivery_status"],
                          "explicit_delivery": final["explicit_delivery"],
                          "evaluation_artifact": final["evaluation_ref"]["artifact_id"]},
    "model_selection_observations": [
        "DeepSeek visibly used model_options and chose PCC description first; it did not execute PCC forward analysis.",
        "It distinguished zero-backend scientific models from charged serial-bending MuJoCo validation and skipped GVS/LQR as irrelevant.",
        "It never treated ALLOW or WARN as physical validation, and did not use any REJECT model as authority.",
        "The baseline-unreachable claim omitted rigid connector and tip offsets; the second gain change lacked observed error direction.",
        "The final delivery is valid but misses task tolerance; numerical score is secondary to orchestration behavior."],
    "environment_blockers": [{"run_directory": "runs/stage35_case_a_20260922", "error": "DEEPSEEK_NETWORK_ERROR",
                              "model_requests": 1, "tool_calls": 0, "backend_solves": 0,
                              "resolution": "Fresh session executed with authorized network access; no backend failure in live run"}],
    "architecture_issues_discovered": ["evidence.read on pointer '/' returned an empty KeyError string; this is weak error feedback but did not block completion"],
    "deferred_capability": "CANDIDATE_SPECIFIC_REASSESSMENT_NOT_AVAILABLE: model_options assess the frozen 0.16 m near segment, while build-1/build-2 use 0.20 m; no reassessment was attempted",
    "recommendation": "2. Behavior issue only: inspect prompt/model reasoning before changing architecture; do not start Case B yet",
    "code_changes": 0,
}

assert len(decisions) == 18 and len(tool_calls) == 21 and len(backend_solves) == 2
assert report["charged_tool_calls"] == 19
assert not any(d.get("tool", "").startswith(("dynamics.gvs", "statics.gvs", "linearization.", "control.lqr")) for d in decisions)
atomic_json(run_dir / "behavior_validation.json", report)

markdown = f"""# Stage 3.5 Case A — DeepSeek behavior validation

## Execution

- Branch/commit: `{report['branch']}` / `{report['commit']}`; run ID `{run_id}`.
- Task: frozen `{report['task']['environment_id']}` reach, target `{report['task']['target_m']}` m, tolerance `{report['task']['tolerance_m']}` m. The environment has no active obstacle/contact requirement.
- Available choices: PCC, GVS `first_order` (8 q) and `structural_linear` (12 q), serial bending (10 q), and one executable `family_mujoco` combination. The bound GVS tools are `dynamics.gvs_describe@2.0.0`, `dynamics.gvs_evaluate@3.0.0`, `dynamics.gvs_build_system@3.0.0`, and `statics.gvs_equilibrium@2.0.0`. Initial verdicts, representation identities and all route-visible versions are in `behavior_validation.json`.
- Budget used: **18/18 model requests, 19/40 charged tool calls, 2/2 backend solves**. There were 21 tool requests including two rejected requests, and one length-truncated model response recovered on the next request.
- Final: explicit `finish-1` delivery of `build-2`, valid evaluation, position error **{final['evaluation']['metrics'][0]['value']:.6f} m**, task success **false**. `run-1` measured {backend_solves[0]['position_error_m']:.6f} m; `run-2` measured {backend_solves[1]['position_error_m']:.6f} m.
- The source tree was clean at start and remains unchanged. Saved model requests, raw responses, decisions, receipts and route nodes are referenced by artifact ID in the JSON report.

## Actual decision sequence

| Decision | Question, choice and reason | Backend cost |
| --- | --- | ---: |
| `model-0-tool` | Starts with `kinematics.pcc_describe` to learn two segment curvature coordinates. The saved `model-0` reasoning explicitly cites `model_options`: PCC reachability **ALLOW**. | 0 |
| `model-1-tool` to `model-3-tool` | Reads optimizer templates and frozen design space. `model-3-tool` is rejected because it adds a forbidden nested `reason` to `evidence.read`. | 0 |
| `model-4-tool` (`build-1`) | Raises near length to 0.20 m, claiming 0.28 m of baseline flexible length cannot reach the target. Build constructs without evaluation. This bound omits rigid connector/tip offsets; no `pcc_forward` was called. | 0 |
| `model-5-tool` (`run-1`) | Uses serial-bending MuJoCo to measure task error after the saved build. It says execution is validation authority and plans to inspect the result. First charged solve: global tool event **58**. | 1 |
| `model-6-tool` to `model-13-tool` | Tries to inspect run-1 configuration, evaluation and simulation. `model-6-tool` fails on pointer `/`; `model-10-tool` is rejected for the extra nested `reason`; `model-7-tool` repeats cached PCC description; `model-9-tool` and `model-12-tool` reread the same scalar evaluation. | 0 |
| `model-14` | DeepSeek response truncates; the platform's existing length recovery requests one complete call, with no tool executed from the truncated response. | 0 |
| `model-15-tool` (`build-2`) | Rebuilds with near length 0.20 m and feedback gain 8.0 after run-1 error 0.078380 m. It cites saved result/evaluation refs but has not established the error direction or that gain is the cause. | 0 |
| `model-16-tool` (`run-2`) | Runs and evaluates build-2 on MuJoCo. Second charged solve: global tool event **157**. | 1 |
| `model-17-tool` (`finish-1`) | Stops and explicitly delivers the valid session incumbent, reporting the unmet 0.01 m tolerance. | 0 |

DeepSeek's saved `model-5` reasoning considers GVS equilibrium and rejects it as unnecessary for this actuator-command validation question. It calls **no** GVS equilibrium, DynamicSystem export, linearization or LQR tool. GVS basis consistency therefore has no executed call to inspect. The initial GVS `reachability` verdict is ALLOW for both bases; its static equilibrium verdicts are WARN and contact/high-fidelity validation verdicts are REJECT. No rejected use becomes an authority in the decision sequence.

## Behavior classifications

| Category | Rating | Saved evidence |
| --- | --- | --- |
| Model applicability use | **GOOD** | `model-0` raw response names `model_options` and PCC `reachability: ALLOW`; `model-4` reasoning treats PCC shape prediction WARN as coarse. |
| Model hierarchy understanding | **GOOD** | `model-0-tool` chooses cheap PCC description; `model-5-tool` reserves MuJoCo for validation; GVS/LQR is skipped. |
| PCC use | **QUESTIONABLE** | `model-0-tool` and cached repeat `model-7-tool` describe PCC, but no `pcc_forward`; `model-4-tool` uses an incomplete flexible-length bound. |
| GVS use | **GOOD** | No GVS call was needed for simple reach; `model-5` explains why equilibrium would not directly validate commanded actuation. |
| GVS basis consistency | **NOT_OBSERVED** | No basis-aware GVS call. |
| Backend solve timing | **QUESTIONABLE** | First solve after a zero-solve build (`model-5-tool`), but the build premise is incomplete; second solve follows a gain choice unsupported by directional error evidence (`model-15-tool`). |
| Budget discipline | **QUESTIONABLE** | Repeated PCC description (`model-7-tool`), duplicate evaluation reads (`model-9-tool`, `model-12-tool`), all 18 model requests consumed. |
| Evidence use | **QUESTIONABLE** | Route transitions cite refs, but `model-3-tool`/`model-10-tool` reject on schema, `model-6-tool` fails on `/`, and the gain decision lacks causal evidence. |
| Stopping behavior | **GOOD** | `model-17-tool` explicitly delivers the valid failed-tolerance result; no further tools follow. |

## Direct answers

1. **Used `model_options`?** Yes. `model-0` raw reasoning explicitly cites PCC reachability ALLOW; later reasoning cites WARN and avoids treating it as validation.
2. **Recognized PCC for initial reasoning?** Yes in choice and explanation, but only called `pcc_describe`, never `pcc_forward`; its geometric reach claim was incomplete.
3. **Invoked GVS?** No. No GVS use, verdict or basis was executed; the saved reasoning judged it unnecessary for this task.
4. **Unnecessary equilibrium/DynamicSystem/linearization/LQR?** None.
5. **First backend solve?** `run-1`, global event 58 after `model-5-tool`, with PCC description, space/template reads and `build-1` as prior evidence. It sought the first actual tip-error measurement, although its reachability premise was incomplete.
6. **Applicability confused with physical validation?** No visible confusion: DeepSeek says simulation provides validation and treats PCC WARN as a coarse prediction.
7. **REJECT respected?** No relevant REJECT use was attempted. Contact and control-design questions were absent, so strict REJECT handling remains untested in this case.
8. **Stopped appropriately?** Yes after two valid evaluations and exhausted solve budget, with explicit honest delivery. Earlier repeat reads show room to stop or decide sooner.
9. **Cause of weaknesses?** The flexible-length claim, gain inference and repeated reads are LLM reasoning issues; nested `reason` rejections are tool-schema misuse; pointer `/` gives weak interface feedback; the first sealed launch failed from sandbox network access. MuJoCo worked in the live run.

## Problems and next step

- **LLM behavior:** Incomplete geometric bound, no PCC forward test, repeated evidence reads, and a gain trial without established error direction.
- **Interface / Stage 3:** `evidence.read` pointer `/` failed with an empty error string. This did not block the completed run; no planner, guidance, assessment or tool description was changed.
- **Environment:** A separate sealed first launch in `runs/stage35_case_a_20260922` stopped at `DEEPSEEK_NETWORK_ERROR` before a decision. Network-enabled execution completed; MuJoCo had no environment blocker.
- **Deferred capability:** `CANDIDATE_SPECIFIC_REASSESSMENT_NOT_AVAILABLE`. `model_options` assesses the frozen near length 0.16 m; both candidates changed it to 0.20 m.

**Conclusion:** DeepSeek behaved as a model-aware planner, not as an undifferentiated tool caller, but its concrete PCC and evidence use was inefficient and partly unsound. **Recommendation 2:** inspect prompt/model reasoning before changing architecture. Do not start Case B yet.
"""
(run_dir / "behavior_validation.md").write_text(markdown, encoding="utf-8")
print("wrote behavior_validation.json and behavior_validation.md")
