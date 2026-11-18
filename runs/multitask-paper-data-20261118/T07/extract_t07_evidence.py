"""Read archived T07 records; never constructs dynamics or integrates a model."""
import csv
import json
import math
import sqlite3
from pathlib import Path

ROOT = Path(r"D:\softrobot-agent")
OUT = ROOT / "runs/multitask-paper-data-20261118/T07"
BASE = ROOT / "paper_experiments/five_task_completion_20261113/T07_C1_four_tendon"
PRIOR = ROOT / "paper_experiments/ten_task_codex_solve_20261112/T07_C1_four_tendon"
RUN = "codex-expert-T07-20261113"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "EXTRACTED_STATES").mkdir(exist_ok=True)
(OUT / "EXTRACTED_CANDIDATES").mkdir(exist_ok=True)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def csvsave(name, rows):
    if not rows:
        return
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                        for k, v in row.items()})


def store(base):
    suffix = "STORE_RESEARCH/platform.sqlite" if base == BASE else "STORE/platform.sqlite"
    return sqlite3.connect("file:" + str(base / suffix) + "?mode=ro", uri=True)


DB = store(BASE)
PDB = store(PRIOR)


def artifact(ref, base=BASE):
    rid = ref["artifact_id"] if isinstance(ref, dict) else ref
    db = DB if base == BASE else PDB
    val = db.execute("SELECT body FROM artifacts WHERE id=?", (rid,)).fetchone()
    if val is None:
        return None
    return json.loads(val[0])


def source(ref, base=BASE):
    suffix = "STORE_RESEARCH/platform.sqlite" if base == BASE else "STORE/platform.sqlite"
    rid = ref["artifact_id"] if isinstance(ref, dict) else ref
    return str(base / suffix) + "#artifacts/" + rid


def structure(resolved):
    return {
        "segment_count": len(resolved["segments"]),
        "tendon_count": len(resolved["tendons"]),
        "actuator_count": len(resolved["actuators"]),
        "segment_lengths_m": [s["length_m"] for s in resolved["segments"]],
        "young_pa": [s["physics"]["young_pa"] for s in resolved["segments"]],
        "segment_sections": [s["sections"] for s in resolved["segments"]],
        "routing_radii_m": [math.hypot(t["points"][0]["attachment"]["position_m"][1],
                                      t["points"][0]["attachment"]["position_m"][2])
                            for t in resolved["tendons"]],
        "tendon_route_points": [t["points"] for t in resolved["tendons"]],
        "actuators": resolved["actuators"],
        "discretization": resolved["discretization"],
        "dimensions": resolved["dimensions"],
    }


struct_defs = [
    ("S0", "INITIAL_CANDIDATE.json", "Initial", "ellipse root; routing radius 18 mm"),
    ("S1", "SMALL_RADIUS_CANDIDATE.json", "Diagnosis", "same sections and lengths; routing radius 18 -> 14.1 mm"),
    ("S2", "ISOTROPIC_ROOT_CANDIDATE.json", "Refinement", "ellipse root -> circular root of radius 8 mm; root density and modulus retained"),
    ("S3", "ROOT_LENGTH_CANDIDATE.json", "Rejected", "circular root length 158.5 -> 159.5 mm"),
    ("S4", "DISTRIBUTED_REACH_CANDIDATE.json", "Rejected", "root/tail lengths 162.5/112.5 mm"),
    ("S5", "MINIMUM_RADIUS_ROOT_CANDIDATE.json", "Final", "restore lengths 158.5/109 mm; circular root; routing radius 14.1 -> 14 mm"),
]
structures = {}
for node, file, stage, change in struct_defs:
    gen = read(BASE / file)
    cand = artifact(gen["candidate"])
    extracted = OUT / "EXTRACTED_CANDIDATES" / (node + "_candidate.json")
    save(extracted, cand)
    structures[node] = dict(node_id=node, candidate_id=gen["candidate"]["artifact_id"],
                           stage=stage, structural_change=change,
                           candidate_json=str(BASE / file), candidate_store_source=source(gen["candidate"]),
                           extracted_candidate=str(extracted), parameters=structure(gen["resolved"]),
                           original_xml="unavailable")

# Every recorded independent replay remains separate from mathematical diagnostics.
physical_defs = [
    ("S1", "M1_B", "HARD_CASE_PHYSICAL_REPLAY.json", BASE),
    ("S5", "M1_A", "MINIMUM_RADIUS_ROOT_A_REPLAY.json", BASE),
    ("S5", "M1_B", "MINIMUM_RADIUS_ROOT_M1_B_REPLAY.json", BASE),
    ("S5", "M1_C", "MINIMUM_RADIUS_ROOT_M1_C_REPLAY.json", BASE),
    ("S5", "M5", "MINIMUM_RADIUS_ROOT_M5_REPLAY.json", BASE),
    ("P0", "M1_A", "PHYSICAL_M1_A.json", PRIOR),
    ("P0", "M1_B", "PHYSICAL_M1_B.json", PRIOR),
    ("P0", "M1_C", "PHYSICAL_M1_C.json", PRIOR),
    ("P0", "M5", "PHYSICAL_M5.json", PRIOR),
    ("P1", "M1_B", "COMPARISON_PHYSICAL_M1_B.json", PRIOR),
]
physical = []
metrics = []
for node, condition, file, base in physical_defs:
    result = read(base / file)
    raw = artifact(result["raw_reference"], base)
    xml = base / ("STORE_RESEARCH" if base == BASE else "STORE") / "physical_replay" / result["execution_id"] / "robot.xml"
    extracted_state = OUT / "EXTRACTED_STATES" / f"{node}_{condition}_physical_samples.json"
    save(extracted_state, {"task_id": "T07", "node_id": node, "condition": condition,
                          "run_id": result.get("owning_study", RUN if base == BASE else "codex-surrogate-T07-20261112"),
                          "candidate_id": result["candidate"]["artifact_id"],
                          "raw_source": source(result["raw_reference"], base),
                          "original_xml": str(xml), "samples": raw["samples"]})
    p = dict(node_id=node, condition=condition, candidate_id=result["candidate"]["artifact_id"],
             run_id=RUN if base == BASE else "codex-surrogate-T07-20261112",
             original_result_json=str(base / file), result_source=source(result["reference"], base),
             result_reference=result["reference"], raw_reference=result["raw_reference"],
             raw_source=source(result["raw_reference"], base), original_xml=str(xml),
             xml_exists=xml.is_file(), extracted_states=str(extracted_state),
             state_pointer="/samples/*/qpos_rad", sample_count=len(raw["samples"]),
             state_dimension=len(raw["samples"][0]["qpos_rad"]),
             times_s=[x["time_s"] for x in raw["samples"]],
             accepted=result["acceptance"]["accepted"],
             metrics=result["acceptance"]["metrics"],
             constraints=result["acceptance"]["constraint_margins"],
             physics_steps=raw.get("physics_steps"),
             physics_timestep_s=raw.get("physics_timestep_s"),
             task_evidence=raw.get("task_evidence"))
    physical.append(p)
    if node in structures:
        structures[node]["original_xml"] = str(xml)
    for name, cm in p["constraints"].items():
        metrics.append(dict(task_id="T07", run_id=p["run_id"], node_id=node,
                            candidate_id=p["candidate_id"], condition=condition,
                            evaluation_scope="independent_frozen_task_physical_replay",
                            metric=name, value=cm["observed"], limit=cm["limit"],
                            unit=cm["units"], constraint_direction=cm["direction"],
                            margin=cm["margin"], acceptance=p["accepted"],
                            source=p["result_source"], source_pointer=f"/acceptance/constraint_margins/{name}",
                            comparability_group=p["run_id"] + ":" + condition + ":physical"))

# Diagnostic sweeps are finite native model calculations, not independent acceptance.
math_defs = [
    ("S0", "M1_B", "HARD_CASE_NATIVE_RESULT.json"),
    ("S0", "M1_B", "HARD_CASE_NATIVE_REFINED.json"),
    ("S0", "M1_B", "HARD_CASE_NATIVE_FINE.json"),
    ("S1", "M1_B", "SMALL_RADIUS_NATIVE_RESULT.json"),
    ("S1", "M1_A", "M1_A_SHARED_NATIVE.json"),
    ("S1", "M1_A", "M1_A_SHARED_NATIVE_REFINED.json"),
    ("S1", "M1_C", "M1_C_SHARED_NATIVE.json"),
    ("S2", "M1_A", "ISOTROPIC_ROOT_A_NATIVE.json"),
    ("S3", "M1_A", "ROOT_LENGTH_A_NATIVE.json"),
    ("S3", "M1_A", "ROOT_FULL_GRID_A_NATIVE.json"),
    ("S4", "M1_A", "DISTRIBUTED_REACH_A_NATIVE.json"),
    ("S5", "M1_A", "MINIMUM_RADIUS_ROOT_A_NATIVE.json"),
    ("S5", "M1_B", "MINIMUM_RADIUS_ROOT_M1_B_NATIVE.json"),
    ("S5", "M1_C", "MINIMUM_RADIUS_ROOT_M1_C_NATIVE.json"),
    ("S5", "M5", "MINIMUM_RADIUS_ROOT_M5_NATIVE.json"),
    ("S5", "M1_C", "CURRENT_C_FROM_A_NATIVE.json"),
]
diagnostics = []
for i, (node, condition, file) in enumerate(math_defs):
    diag = read(BASE / file)
    stored = artifact(diag["reference"])
    state_path = OUT / "EXTRACTED_STATES" / (Path(file).stem + "_diagnostic_states.json")
    save(state_path, {"task_id": "T07", "run_id": RUN, "node_id": node,
                      "condition": condition, "source": source(diag["reference"]),
                      "evaluation_scope": "finite_native_diagnostic_NOT_independent_acceptance",
                      "state_pointer": "/native_dynamics/best_control_states",
                      "states": stored.get("native_dynamics", {}).get("best_control_states", {})})
    d = dict(node_id=node, condition=condition, candidate_id=diag["candidate"]["artifact_id"],
             original_json=str(BASE / file), store_source=source(diag["reference"]),
             analysis_reference=diag["reference"], extracted_states=str(state_path),
             model_xml="unavailable" if node not in ("S1", "S5") else structures[node]["original_xml"],
             quantities=diag["native_analysis"]["quantities"],
             solver=diag["native_analysis"]["solver"],
             task_acceptance=diag["task_acceptance"],
             schedule_reference=diag["native_analysis"].get("control_schedule_reference"),
             diagnostic_measure=stored.get("native_dynamics", {}).get("optimization", {}).get("best", {}).get("measure", {}))
    if d["schedule_reference"]:
        d["control_schedule_settings"] = artifact(d["schedule_reference"]).get("provenance", {}).get("settings", {})
    diagnostics.append(d)
    for q in d["quantities"]:
        metrics.append(dict(task_id="T07", run_id=RUN, node_id=node,
                            candidate_id=d["candidate_id"], condition=condition,
                            evaluation_scope="finite_native_diagnostic_NOT_independent_acceptance",
                            metric=q["name"], value=q["value"], limit="unavailable", unit=q["unit"],
                            constraint_direction="unavailable", margin="unavailable", acceptance="unmeasured",
                            source=d["store_source"], source_pointer=q["source_pointer"],
                            comparability_group=RUN + ":" + condition + ":native_diagnostic",
                            diagnostic_iteration=i + 1, original_json=d["original_json"]))

# Exact recorded public rationale is preserved independently of editorial interpretation.
decision_specs = [
    ("010", "S0", "History-informed starting geometry; no acceptance transfer", "Initial four-channel shape was regenerated in the new Study."),
    ("017", "S0", "Control-resolution test before changing hardware", "Increased startup and hold knot resolution; residual conflict remained."),
    ("020", "S1", "Routing-radius hypothesis", "Reduced radius 18 -> 14.1 mm, same sections, lengths, topology."),
    ("024", "S1", "Independent B replay", "B passed on ellipse-root hardware; A/C/M5 remained unaccepted on this hardware."),
    ("35", "S1", "Shared-morphology bottleneck", "A retained 0.105688 signed excess after refinement; B alone was insufficient."),
    ("060", "S2", "Root-section mechanism trial", "Circular root reduced A excess to 0.008747859; this does not isolate mass from stiffness."),
    ("063", "S3", "One-millimetre reach margin trial", "Longer root and subsequent full-grid control still failed diagnostic proxy."),
    ("070", "S4", "Distributed reach-margin trial", "Both lengths increased; A signed excess worsened to 0.043968354."),
    ("074", "S5", "Reject longer geometry; exploit legal radius boundary", "Restored 158.5/109 mm, reduced radius 14.1 -> 14 mm."),
    ("078", "S5", "Carry exact shared hardware into other conditions", "A passed independently; B, C and M5 required fresh controls and replay."),
    ("104", "S5", "Control-initialization route change", "A/B/M5 passed; historical C seed retained 0.041124620 excess."),
    ("105", "S5", "Use A schedule as unmeasured C initialization", "Transferred inputs only; then reoptimized original C constraints."),
    ("114", "S5", "Select identical shared structure", "Four original independent replay results selected; prior ellipse-root B result excluded."),
]
trace = [json.loads(s) for s in (BASE / "STUDY_TRACE.jsonl").read_text().splitlines()]
decisions = []
for prefix, node, label, analysis in decision_specs:
    matches = sorted((BASE / "REQUESTS").glob(prefix + "-*.json"))
    reqpath = matches[0]
    req = read(reqpath)
    rid = req["request"]["request_id"]
    ev = next((e for e in trace if e.get("event_id") == rid + "-decision"), {})
    arguments = req["request"].get("arguments", {})
    decisions.append(dict(task_id="T07", run_id=RUN, actor=ev.get("actor", "codex_surrogate_main"),
                          node_id=node, decision_id=rid, timestamp=ev.get("timestamp", "unavailable"),
                          observation=req["intent"]["decision_summary"].split(". ")[0],
                          hypothesis=arguments.get("hypothesis", "unavailable as separate original field"),
                          investigation=req["request"]["tool_id"] + ":" + arguments.get("action", "read"),
                          evidence=req["request"].get("evidence", []),
                          decision=req["intent"]["decision_summary"],
                          action=label, outcome=analysis,
                          recorded_rationale_quote=req["intent"]["decision_summary"],
                          analysis_only_summary=analysis,
                          attribution_note="Recorded Codex expert/surrogate public decision; not a Main SDK/Provider execution.",
                          original_request=str(reqpath), trace_path=str(BASE / "STUDY_TRACE.jsonl")))

candidate_rows = []
for node, file, stage, change in struct_defs:
    st = structures[node]
    ds = [x for x in diagnostics if x["node_id"] == node]
    ps = [x for x in physical if x["node_id"] == node]
    candidate_rows.append(dict(task_id="T07", run_id=RUN, candidate_id=st["candidate_id"],
                               node_id=node, iteration=node[1:], stage=stage,
                               candidate_status="selected_shared_structure" if node == "S5" else "not_selected",
                               model_xml=st["original_xml"],
                               state_source=[p["extracted_states"] for p in ps] + [d["extracted_states"] for d in ds],
                               physical_hypothesis="See exact public quotes in agent_decision_timeline.csv; no inferred internal hypothesis",
                               observed_problem=[d["quantities"] for d in ds],
                               structural_change=change,
                               controller_change="Condition-specific native sequence reoptimization; saved schedules referenced by diagnostics",
                               mathematical_evidence=[d["store_source"] for d in ds],
                               physical_evidence=[p["result_source"] for p in ps],
                               decision_summary=[d["analysis_only_summary"] for d in decisions if d["node_id"] == node],
                               evaluation_status="four_required_conditions_independent_PASS" if node == "S5" else
                               "only_M1_B_independent_PASS; A/C diagnostic conflicts" if node == "S1" else "diagnostic_only_unaccepted",
                               resulting_metrics=[dict(condition=p["condition"], metrics=p["metrics"], accepted=p["accepted"]) for p in ps],
                               candidate_source=st["candidate_store_source"], source_json=st["candidate_json"],
                               structural_parameters=st["parameters"],
                               actor="codex_surrogate_main (expert run; no Main SDK/Provider)"))

# Predecessor models are retained but explicitly do not contribute to current acceptance.
for node, genfile, change in [("P0", "GENERATION_RESULT.json", "cold two-circle baseline"),
                              ("P1", "COMPARISON_GENERATION.json", "root-softening comparison")]:
    gen = read(PRIOR / genfile)
    cand = artifact(gen["candidate"], PRIOR)
    extracted = OUT / "EXTRACTED_CANDIDATES" / (node + "_candidate.json")
    save(extracted, cand)
    ps = [x for x in physical if x["node_id"] == node]
    st = structure(gen["resolved"])
    structures[node] = dict(node_id=node, candidate_id=gen["candidate"]["artifact_id"], stage="HistoricalRejected",
                           candidate_json=str(PRIOR / genfile), candidate_store_source=source(gen["candidate"], PRIOR),
                           extracted_candidate=str(extracted), parameters=st, original_xml=ps[0]["original_xml"])
    candidate_rows.append(dict(task_id="T07", run_id="codex-surrogate-T07-20261112", candidate_id=gen["candidate"]["artifact_id"],
                               node_id=node, iteration="historical", stage="HistoricalRejected", candidate_status="predecessor_failed_group",
                               model_xml=ps[0]["original_xml"], state_source=[p["extracted_states"] for p in ps],
                               physical_hypothesis="unavailable as separate original field", observed_problem="M1_B independent physical failure",
                               structural_change=change, controller_change="archived native sequence optimization",
                               mathematical_evidence="see predecessor archive; not used as present-run acceptance",
                               physical_evidence=[p["result_source"] for p in ps],
                               decision_summary="Historical context only; no acceptance transfer between studies",
                               evaluation_status="M1_B failed; group unsolved", resulting_metrics=[dict(condition=p["condition"], metrics=p["metrics"]) for p in ps],
                               candidate_source=source(gen["candidate"], PRIOR), source_json=str(PRIOR / genfile), structural_parameters=st,
                               actor="Codex surrogate; not Main SDK/Provider"))

csvsave("candidate_timeline.csv", candidate_rows)
csvsave("agent_decision_timeline.csv", decisions)
csvsave("metric_history.csv", metrics)
csvsave("final_condition_results.csv", [{"task_id": "T07", "run_id": RUN, "condition": p["condition"],
                                        "candidate_id": p["candidate_id"], "accepted": p["accepted"],
                                        **p["metrics"], "constraints": p["constraints"],
                                        "source": p["result_source"]} for p in physical if p["node_id"] == "S5"])

bundle = dict(task_id="T07", task_name="Shared-Morphology Multi-Task Design", selected_run_id=RUN,
              actor="codex_surrogate_main", actual_executor_note="Codex expert archived full tool execution; no official Main/Provider execution",
              origin="historical_FULL method C", required_conditions=["M1_A", "M1_B", "M1_C", "M5"],
              source_base=str(BASE), prior_source_base=str(PRIOR), structures=structures,
              independent_physical=physical, mathematical_diagnostics=diagnostics,
              selected_render_nodes=[dict(node_id="S1", condition="M1_B", reason="independent physical saved model of ellipse-root intermediate; compare with final on same B task"),
                                     *[dict(node_id="S5", condition=c, reason="same shared morphology; independent condition-specific controls and frozen task PASS")
                                       for c in ["M1_A", "M1_B", "M1_C", "M5"]]],
              optional_predecessor_render_nodes=["P0:M1_B", "P1:M1_B"],
              render_constraints=["Do not render nonexistent original XML for S0/S2/S3/S4 as an original physical replay.",
                                  "S1 M1_B pass does not establish any S5 condition acceptance.",
                                  "qpos samples come from archived raw artifacts, never from new integration.",
                                  "No new solver, optimizer, model integration or core edits were performed by extraction."],
              missing_data=["Original XML files for S0, S2, S3, S4 are not present; complete candidate parameters and saved diagnostic states are retained.",
                            "No official Main SDK/Provider autonomous run in this FULL archive.",
                            "No physical independent acceptance of S0/S2/S3/S4, nor of S1 A/C/M5."])
final_candidate_records = [artifact(p["candidate_id"]) for p in physical if p["node_id"] == "S5"]
bundle["shared_morphology_check"] = {
    "method": "Direct Python equality of stored candidate.parameters and candidate.resolved_parameters; original replay design/model identities also agree.",
    "parameters_equal_all_four": all(x["parameters"] == final_candidate_records[0]["parameters"] for x in final_candidate_records),
    "resolved_parameters_equal_all_four": all(x["resolved_parameters"] == final_candidate_records[0]["resolved_parameters"] for x in final_candidate_records),
    "design_identity": "2cc088d7947ba93ee7c0b76d4d154ba23091a8298304c02ce6ad7cf9fef4529e",
    "model_identity": "1eff34702875c584c44cb607f6943d28f4c99b176ea8661cf02ec1358bd0d85f",
    "condition_specific_candidate_ids": {p["condition"]: p["candidate_id"] for p in physical if p["node_id"] == "S5"},
}
resources = []
for base in [BASE, PRIOR]:
    cost = read(base / "COST_REPORT.json")
    if "study_id" in cost and "studies" not in cost:
        resources.append({"run_id": cost["study_id"], "source": str(base / "COST_REPORT.json"),
                          "budget_used": cost.get("ledger", {}).get("used"),
                          "store_counters": cost.get("store_counters"),
                          "structural_candidates": cost.get("structural_candidates"),
                          "candidate_artifacts": cost.get("candidate_artifacts"),
                          "physical_actual_resource_totals": cost.get("physical_actual_resource_totals"),
                          "native_analysis_actual_resource_totals": cost.get("native_analysis_actual_resource_totals"),
                          "token_usage": cost.get("codex_usage"),
                          "token_usage_reason": cost.get("codex_usage_reason"),
                          "study_elapsed_s": cost.get("study_elapsed_s"),
                          "aggregation_rule": "Historical predecessor retained separately; never added to selected expert-run cost."})
    for study in cost.get("studies", []):
        rec = {"run_id": study.get("study_id"), "source": str(base / "COST_REPORT.json"),
               "budget_used": study.get("budget", {}).get("used"),
               "charged_mathematical_evaluations": study.get("charged_mathematical_evaluations"),
               "recorded_numerical_wall_s": study.get("recorded_numerical_wall_s"),
               "physical_replay_launches": study.get("physical_replay_launches"),
               "token_usage": "unavailable; no official Main/Provider run; model_calls=0 does not quantify Codex orchestration tokens",
               "aggregation_rule": "One record per original Study; never sum predecessors into selected-run cost."}
        calcs = [c for a in study.get("native_analysis_cost_records", []) for c in a.get("internal_calculations", [])]
        rec["native_math_internal_calculations_sum_within_this_run"] = {
            k: sum(c.get(k, 0) for c in calcs) for k in ["optimization_evaluations", "physics_steps", "rollouts", "model_builds"]}
        resources.append(rec)
save(OUT / "resource_usage.json", resources)
save(OUT / "evidence_bundle.json", bundle)
print(json.dumps({"structures": len(structures), "decisions": len(decisions), "metric_rows": len(metrics),
                  "physical_results": len(physical), "saved_state_files": len(list((OUT / 'EXTRACTED_STATES').glob('*.json'))),
                  "output": str(OUT)}, ensure_ascii=False))
