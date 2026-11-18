"""Merge supplied historical evidence indices without rewriting task outputs.

No optimizer, model loader, integration, or hashing is invoked. SQLite is read-only.
Missing ownership is unavailable, never inferred from another Study's success.
"""
import csv
import json
import ntpath
import re
import sqlite3
from pathlib import Path

ROOT = Path(r"D:\softrobot-agent")
OUT = ROOT / "runs/multitask-paper-data-20261118"
PHS = ROOT / "runs/phs2d-paper-data-20261112"
UNKNOWN = "unavailable"
_SESSION_CACHE = {}
_ARTIFACT_CACHE = {}


def jread(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def rows(path):
    path = Path(path)
    return list(csv.DictReader(path.open(encoding="utf-8-sig", newline=""))) if path.exists() else []


def dump(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def maybejson(value):
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return value


def present(*values):
    return next((v for v in values if v not in (None, "", UNKNOWN, "null", "None")), UNKNOWN)


def first(row, *keys):
    return present(*(row.get(k) for k in keys))


def refid(value):
    value = maybejson(value)
    if isinstance(value, dict):
        return value.get("artifact_id", dump(value))
    text = str(value)
    if "#artifacts/" in text:
        return text.split("#artifacts/", 1)[1].split("/")[0]
    return value if isinstance(value, str) else dump(value)


def source_base(value):
    value = str(value).split("#", 1)[0]
    value = re.sub(r"\.jsonl:\d+$", ".jsonl", value)
    # Existing state indices sometimes append a JSON pointer without '#'.
    value = re.sub(r"(?i)(\.(?:jsonl|json(?:\.gz)?|csv|xml))[/\\].*$", r"\1", value)
    return ntpath.normpath(value)


def store_path(value):
    if value in (None, "", UNKNOWN):
        return None
    val = Path(source_base(value))
    if val.is_dir() and (val / "platform.sqlite").is_file():
        val = val / "platform.sqlite"
    return val if val.is_file() and val.name.endswith(".sqlite") else None


def sessions(value):
    p = store_path(value)
    if p is None:
        return []
    key = str(p)
    if key not in _SESSION_CACHE:
        try:
            with sqlite3.connect("file:" + key + "?mode=ro", uri=True) as db:
                _SESSION_CACHE[key] = db.execute("SELECT run_id,state FROM sessions").fetchall()
        except sqlite3.Error:
            _SESSION_CACHE[key] = []
    return _SESSION_CACHE[key]


def read_original_artifact(row, original_source, original_ref):
    raw_store = first(row, "store", "source_store")
    p = store_path(raw_store if raw_store != UNKNOWN else original_source)
    rid = str(refid(original_ref))
    if p is None or not re.fullmatch(r"[a-f0-9]{64}", rid):
        return {}
    key = (str(p), rid)
    if key not in _ARTIFACT_CACHE:
        try:
            with sqlite3.connect("file:"+str(p)+"?mode=ro", uri=True) as db:
                val = db.execute("SELECT body FROM artifacts WHERE id=?", (rid,)).fetchone()
            _ARTIFACT_CACHE[key] = json.loads(val[0]) if val else {}
        except (sqlite3.Error, ValueError):
            _ARTIFACT_CACHE[key] = {}
    return _ARTIFACT_CACHE[key]


def infer_run(row, original_source, original_ref):
    stated = first(row, "run_id", "study_id")
    if stated != UNKNOWN:
        return stated, "original_row"
    original = read_original_artifact(row, original_source, original_ref)
    direct = present(original.get("study_id"), original.get("owning_study"), original.get("source_owner"))
    if direct != UNKNOWN:
        return direct, "original_Store_artifact_study_id_or_owning_study_or_source_owner"
    raw_store = first(row, "store", "source_store")
    s = sessions(raw_store if raw_store != UNKNOWN else original_source)
    rid = str(refid(original_ref))
    matches = [run for run, state in s if rid != UNKNOWN and rid in state]
    if len(matches) == 1:
        return matches[0], "original_read_only_Store.sessions.state_contains_exact_candidate_artifact"
    if len(s) == 1:
        return s[0][0], "only_original_Store_session"
    return UNKNOWN, "unresolved_without_cross_Study_assumption"


def make_record(task, kind, row, index, row_number, actor_by_run):
    if kind == "candidate":
        original_ref = first(row, "candidate_artifact_id", "candidate_ref", "candidate_id", "candidate_reference")
        original_source = first(row, "candidate_reference", "source_ref", "candidate_source", "source", "original_source")
        if original_source == UNKNOWN:
            original_source = first(row, "store", "source_store", "source_json")
    else:
        original_ref = first(row, "decision_artifact_id", "decision_id", "event_id", "node_id")
        original_source = first(row, "source_ref", "original_source", "source", "original_request", "trace_source")
    run, run_basis = infer_run(row, original_source, original_ref)
    actor = first(row, "actor", "actor_original")
    actor_basis = "original_row"
    original_artifact = read_original_artifact(row, original_source, original_ref)
    original_actor = present(original_artifact.get("actor"), original_artifact.get("receipt", {}).get("caller"))
    if actor == UNKNOWN and original_actor != UNKNOWN:
        actor, actor_basis = original_actor, "original_Store_artifact_actor_or_receipt_caller"
    if actor == UNKNOWN:
        values = actor_by_run.get(run, set())
        actor = next(iter(values)) if len(values) == 1 else UNKNOWN
        actor_basis = "same_run_original_decision_actor_context" if actor != UNKNOWN else UNKNOWN
    subtype = "original_candidate_artifact" if kind == "candidate" else "recorded_public_decision"
    if kind == "candidate" and "accounting_scope" in original_artifact and "receipt" in original_artifact:
        subtype = "execution_accounting_receipt_not_structural_candidate"
    elif kind == "candidate" and "resolved_parameters" not in original_artifact:
        subtype = "selected_timeline_or_source_link; inspect_original_row_scope"
    return dict(task_id=task, run_id=run, actor=actor, actor_basis=actor_basis,
                run_id_basis=run_basis, record_kind=kind,
                record_subtype=subtype,
                record_id=first(row, "node_id", "event_id", "candidate_id", "decision_id"),
                original_ref=original_ref, artifact_or_event_id=refid(original_ref),
                original_source=original_source, normalized_source=ntpath.normpath(str(original_source)),
                source_index_file=str(index), source_row_number=row_number,
                original_row_json=dump(row), alternate_original_rows_json="[]",
                coverage_scope="supplied_complete_task_index; inspect_record_subtype_before_counting_candidates" if "complete_" in Path(index).name else "selected_timeline_fallback_not_exhaustive_Store_inventory")


def dedup(records):
    kept = []
    seen = {}
    for r in records:
        # Study remains part of the key even if artifact/source happen to agree.
        key = (r["task_id"], r["run_id"], r["normalized_source"], str(r["artifact_or_event_id"]))
        if r["artifact_or_event_id"] == UNKNOWN or r["original_source"] == UNKNOWN:
            key += (r["source_index_file"], str(r["source_row_number"]))
        if key in seen:
            previous = kept[seen[key]]
            duplicate = json.loads(previous["alternate_original_rows_json"])
            duplicate.append({k: r[k] for k in ["original_source", "source_index_file", "source_row_number", "original_row_json"]})
            previous["alternate_original_rows_json"] = dump(duplicate)
        else:
            seen[key] = len(kept)
            kept.append(r)
    return kept


def write_csv(path, records):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for r in records for k in r))
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fields)
        w.writeheader()
        w.writerows(records)


def source_record(task, run, actor, kind, source, ref, index, number, original_row):
    base = source_base(source)
    return dict(task_id=task, run_id=run, actor=actor, source_kind=kind,
                original_source=str(source), normalized_source=ntpath.normpath(str(source)),
                original_ref=ref, artifact_or_event_id=refid(ref),
                source_base_exists=Path(base).exists() if base != UNKNOWN else False,
                existence_scope="filesystem base only; artifact/state semantics retained from original indices; no SHA audit",
                source_index_file=str(index), source_row_number=number,
                original_row_json=dump(original_row), alternate_original_rows_json="[]")


def extension(task, label, run, status, sources, interpretation, excerpt=None, node=UNKNOWN):
    return dict(task_id=task, extension_id=label, run_id=run,
                actor="codex_surrogate_main" if task != "PHS-2D" else UNKNOWN,
                node_id=node, original_status=status,
                scientific_value=interpretation, original_sources_json=dump([str(s) for s in sources]),
                original_source_exists_json=dump({str(s): Path(source_base(s)).exists() for s in sources}),
                original_excerpt_json=dump(excerpt or {}),
                coverage_scope="selected_read_predecessors_and_branches_only_not_a_comprehensive_extension_inventory",
                cross_study_rule="Preserve original run/role; no acceptance or resource transfer between studies.")


def build_extensions():
    ex = []
    experiments = ROOT / "paper_experiments"
    a = experiments / "five_task_completion_20261113/T04_figure_eight_tracking"
    init = jread(a / "INITIAL_EXECUTION.json")
    term = jread(a / "SUPERSEDED_NMPC_TERMINATION_REQUEST.json")
    ex.append(extension("T04", "retained_GVS_NMPC_incomplete", "codex-expert-T04-20261113-s1",
                        init.get("status", UNKNOWN), [a / "INITIAL_EXECUTION.json", a / "SUPERSEDED_NMPC_TERMINATION_REQUEST.json"],
                        "Unfinished/worker-exit GVS comparison superseded after native feedforward succeeded; not a completed performance failure or impossibility result.",
                        {"acceptance": init.get("acceptance"), "actual_termination": init.get("actual_termination"), "termination_request": term},
                        "T04-017-execute-full-tracking-decision"))
    b7 = jread(OUT / "T07/evidence_bundle.json")
    for node in ["P0", "P1", "S3", "S4"]:
        st = b7["structures"][node]
        diag = [d for d in b7["mathematical_diagnostics"] if d["node_id"] == node]
        phys = [d for d in b7["independent_physical"] if d["node_id"] == node]
        run = "codex-surrogate-T07-20261112" if node.startswith("P") else b7["selected_run_id"]
        ex.append(extension("T07", "shared_morphology_counterexample_"+node, run,
                            "independent_M1_B_FAIL" if node.startswith("P") else "finite_native_diagnostic_conflict_NOT_independent_acceptance",
                            [st["candidate_json"], *[d["original_result_json"] for d in phys], *[d["original_json"] for d in diag]],
                            "Historical common circles/root-softening or rejected root/distributed elongation; keep exact Study, structure and diagnostic-vs-physical scope.",
                            {"parameters": st["parameters"], "physical": [{"condition": p["condition"], "accepted": p["accepted"], "metrics": p["metrics"]} for p in phys],
                             "diagnostics": [{"condition": d["condition"], "quantities": d["quantities"]} for d in diag]}, node))
    t8 = OUT / "T08/recorded_replay_model_index.csv"
    for i, r in enumerate(rows(t8), 2):
        path = r["model_xml"]
        role = next((n for n in ["ablation", "half_timestep", "initial_perturbation", "baseline"] if n in path.lower()), "recorded_subrun")
        ex.append(extension("T08", "passive_payout_mechanism_"+r["execution_id"]+"_"+role,
                            "codex-surrogate-T08-20261112", "archived_role_"+role,
                            [r["original_request"], r["model_xml"]],
                            "1.5->1.8 mm fixed payout refinement; baseline, no-limiter ablation and numerical confirmation retain separate original roles. Same geometry is not a new morphology per subdirectory.",
                            r, r["execution_id"]+":"+role))
    a = experiments / "five_task_completion_20261113/T09_spring_button"
    repair = a / "T09_RUN_02/REPAIR_VARIANT_PROVENANCE.json"
    init = jread(a / "INITIAL_EXECUTION.json")
    ex.append(extension("T09", "source_hardware_interface_blocked_precursor", "codex-surrogate-T09-20261112", "BLOCKED_CORE_before_scientific_computation",
                        [experiments / "ten_task_codex_solve_20261112/T09_spring_button/STUDY_TRACE.jsonl"],
                        "Original v1.2 required 20 physical eye/spoke guide assemblies; interface could not express them. No reduced-hardware physical success is claimed.",
                        next(r for r in rows(OUT / "T09/agent_decision_timeline.csv") if r["stage"] == "Blocked precursor")))
    ex.append(extension("T09", "complete_hardware_collision_semantics_repair", "codex-expert-T09-20261113-core027", "source_no_contact_semantics_restored_then_fresh_validation",
                        [a / "INITIAL_EXECUTION.json", repair, a / "T09_RUN_02/CORE_REPAIR_REPORT.md"],
                        "First complete-hardware replay exposed assembly re-enabling forbidden guide collisions. Repair restored source semantics while retaining guide mass, COM, inertia; not aesthetic deletion of a real collision.",
                        {"initial_status": init.get("status"), "initial_acceptance": init.get("acceptance"), "repair": jread(repair)}))
    a = experiments / "five_task_completion_20261113/T10_M7_impact_recovery"
    nmpc = a / "T10_RUN_02/NO_IMPULSE_FEEDBACK_EXECUTION.json"
    init = jread(nmpc)
    ex.append(extension("T10", "GVS_NMPC_incomplete_profile_diagnostic", init.get("owning_study", UNKNOWN), init.get("status", UNKNOWN), [nmpc],
                        "Physical evaluator ran and reported violations, but missing controller_observations export made profile delivery incomplete; no completed formal acceptance or general NMPC impossibility claim.",
                        {"status": init.get("status"), "actual_termination": init.get("actual_termination"), "acceptance": init.get("acceptance"), "failure": init.get("failure")}, "T10_N03"))
    repair = a / "T10_RUN_05/REPAIR_VARIANT_PROVENANCE.json"
    r = jread(repair)
    ex.append(extension("T10", "rejected_noncommon_controller_group", r["previous_study"], "strict_joint_common_controller_check_rejected_old_group", [repair],
                        "Individual passes used differing actual first-condition controller weights. Legal bootstrap defaults were aligned; previous passes cannot be spliced into the later verified-common Study.",
                        r, "T10_N05"))
    ex.append(extension("T10", "common_controller_prephysics_check", "codex-expert-T10-20261113-verified-common", "fresh_required_and_frozen_control_replays_under_verified_common_recipe",
                        [a / "T10_RUN_06/COMMON_CONTROLLER_PREPHYSICS_CHECK.json", a / "T10_RUN_06/JOINT_SELECTION.json"],
                        "Three required passes and two original frozen-control failures keep their protocol roles; all recipes checked before physics.",
                        jread(a / "T10_RUN_06/COMMON_CONTROLLER_PREPHYSICS_CHECK.json"), "T10_N06-N10"))
    phs_exec = jread(PHS / "SOURCE_EXTRACTS/EXECUTION_MANIFEST.json")
    half = phs_exec["codex_halfstep"]
    accept = jread(PHS / "SOURCE_EXTRACTS/codex_halfstep_ACCEPTANCE.json")
    ex.append(extension("PHS-2D", "F8_existing_half_timestep_confirmation", half["run_id"], "original_halfstep_accepted",
                        [half["result"], PHS / "SOURCE_EXTRACTS/codex_halfstep_ACCEPTANCE.json", PHS / "SOURCE_EXTRACTS/EXECUTION_MANIFEST.json"],
                        "Original Codex F8 half-timestep ten-condition confirmation; distinct from Main nominal reproduction, which has no halfstep confirmation.",
                        {"execution_manifest": half, "accepted": accept["accepted"], "metrics": accept.get("metrics"), "timing": accept.get("timing")}, "F8"))
    return ex


def main():
    tasks = [f"T{i:02d}" for i in range(1, 11)]
    candidates, decisions, selected, source_rows = [], [], [], []
    actor_by_run = {}
    for task in tasks:
        index = OUT / task / "complete_decision_index.csv"
        if not index.exists():
            index = OUT / task / "agent_decision_timeline.csv"
        for r in rows(index):
            run = first(r, "run_id", "study_id")
            actor = first(r, "actor", "actor_original")
            if run != UNKNOWN and actor != UNKNOWN:
                actor_by_run.setdefault(run, set()).add(actor)
    for task in tasks:
        for kind, complete, fallback, collection in [
                ("candidate", "complete_candidate_index.csv", "candidate_timeline.csv", candidates),
                ("decision", "complete_decision_index.csv", "agent_decision_timeline.csv", decisions)]:
            index = OUT / task / complete
            if not index.exists():
                index = OUT / task / fallback
            collection.extend(make_record(task, kind, r, index, i, actor_by_run) for i, r in enumerate(rows(index), 2))
        index = OUT / task / "agent_decision_timeline.csv"
        for i, r in enumerate(rows(index), 2):
            item = make_record(task, "decision", r, index, i, actor_by_run)
            item.update({k: r.get(k, UNKNOWN) for k in ["observation", "hypothesis", "investigation", "evidence", "decision", "action", "outcome"]})
            item["interpretation_status"] = first(r, "interpretation_status", "hypothesis_provenance", "evidence_type", "attribution_note")
            item["recorded_public_rationale"] = first(r, "recorded_rationale_quote", "decision")
            item["editorial_analysis_only"] = first(r, "analysis_only_summary")
            selected.append(item)
        index = OUT / task / "source_index.csv"
        for i, r in enumerate(rows(index), 2):
            run = first(r, "run_id", "run_ids")
            runs = maybejson(run)
            for rid in runs if isinstance(runs, list) else [run]:
                values = actor_by_run.get(rid, set())
                actor = next(iter(values)) if len(values) == 1 else UNKNOWN
                source_rows.append(source_record(task, rid, actor, first(r, "kind", "source_kind"),
                                                 first(r, "path", "source"), first(r, "path", "source"), index, i, r))
    # Nine Codex candidates are source links into the existing PHS package; no study mixing.
    manifest_path = PHS / "SOURCE_EXTRACTS/CANDIDATE_MANIFEST.json"
    manifest = jread(manifest_path)
    for i, (name, r) in enumerate(manifest.items(), 1):
        original = {"candidate": name, **r}
        record = make_record("PHS-2D", "candidate", {"candidate_id": name, "candidate_ref": r["reference"]["artifact_id"],
                              "run_id": r["run_id"], "source": r["generation_source"], **r}, manifest_path, i, actor_by_run)
        record["original_row_json"] = dump(original)
        record["coverage_scope"] = "existing_PHS_package_Codex_candidate_manifest_9_source_links"
        candidates.append(record)
    keypath = PHS / "KEY_NODES.csv"
    for i, r in enumerate(rows(keypath), 2):
        run = "psd2d-core-fresh-20261112"
        record = make_record("PHS-2D", "decision", {**r, "run_id": run, "decision_id": r["node_id"],
                             "source": r["trace_source"]}, keypath, i, actor_by_run)
        record["original_row_json"] = dump(r)
        record["coverage_scope"] = "existing_PHS_package_KEY_NODES_11_source_links; original text preserved verbatim"
        decisions.append(record)
        selected.append({**record, "observation": r["observed_problem"], "hypothesis": UNKNOWN,
                         "investigation": r["decision_basis"], "evidence": r["evidence_paths"],
                         "decision": r["decision"], "action": UNKNOWN, "outcome": r["followup_result"],
                         "interpretation_status": "existing_PHS_editorial_key_nodes; not newly inferred original agent reasoning",
                         "recorded_public_rationale": UNKNOWN, "editorial_analysis_only": r["title"]})
    candidates, decisions = dedup(candidates), dedup(decisions)
    for r in [*candidates, *decisions]:
        source_rows.append(source_record(r["task_id"], r["run_id"], r["actor"], r["record_kind"]+"_reference",
                                         r["original_source"], r["original_ref"], r["source_index_file"], r["source_row_number"], json.loads(r["original_row_json"])))
    # Preserve the root's original model/state/result binding indices without modifying them.
    for name in ["source_index_initial.csv", "final_condition_index.csv", "selected_state_index.csv"]:
        index = OUT / "SUPPLEMENTARY" / name
        for i, r in enumerate(rows(index), 2):
            run = first(r, "run_id")
            actor = first(r, "actor")
            for key in ["source_store", "result_source", "candidate_source", "state_source", "model_xml", "source_xml", "original_state_source"]:
                if r.get(key):
                    source_rows.append(source_record(r["task_id"], run, actor, key, r[key],
                                                     first(r, "result_ref", "candidate_ref", "candidate_id", "condition_id"), index, i, r))
    extensions = build_extensions()
    for r in extensions:
        for path in json.loads(r["original_sources_json"]):
            source_rows.append(source_record(r["task_id"], r["run_id"], r["actor"], "selected_extension_source", path,
                                             r["extension_id"], OUT / "SUPPLEMENTARY/extension_index.csv", r["extension_id"], r))
    # dedup also works for source rows; same source + same ref + same Study only.
    source_rows = dedup([{**r, "record_kind": "source"} for r in source_rows])
    write_csv(OUT / "SUPPLEMENTARY/complete_candidate_index.csv", candidates)
    write_csv(OUT / "SUPPLEMENTARY/complete_decision_index.csv", decisions)
    write_csv(OUT / "SUPPLEMENTARY/source_index.csv", source_rows)
    write_csv(OUT / "SUPPLEMENTARY/extension_index.csv", extensions)
    write_csv(OUT / "CROSS_TASK/research_decision_summary.csv", selected)
    unresolved = [r for r in candidates if r["run_id"] == UNKNOWN]
    print(dump({"candidate_rows": len(candidates), "decision_rows": len(decisions),
                "selected_research_decisions": len(selected), "source_rows": len(source_rows),
                "selected_extension_rows": len(extensions), "candidate_run_unavailable": len(unresolved),
                "counts_by_task": {t: {"candidates": sum(r["task_id"] == t for r in candidates),
                                      "decisions": sum(r["task_id"] == t for r in decisions)} for t in [*tasks, "PHS-2D"]},
                "coverage": "Existing supplied task indices plus explicitly read branches, not an all-repository inventory."}))


if __name__ == "__main__":
    main()
