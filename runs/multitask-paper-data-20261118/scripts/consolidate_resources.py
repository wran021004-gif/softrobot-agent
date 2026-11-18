"""Per-Study resource extraction and plotting, with no new scientific execution."""
import csv
import json
import math
import ntpath
import sqlite3
from pathlib import Path

ROOT = Path(r"D:\softrobot-agent")
OUT = ROOT / "runs/multitask-paper-data-20261118"
PHS = ROOT / "runs/phs2d-paper-data-20261112"
U = "unavailable"


def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def csvread(p):
    return list(csv.DictReader(Path(p).open(encoding="utf-8-sig")))


def serial(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def writecsv(p, rows):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with Path(p).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: serial(v) if isinstance(v, (dict, list)) else v for k, v in r.items()})


def num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def nsum(values):
    vals = [v for v in values if num(v)]
    return sum(vals) if vals else U


def gather_sources():
    paths = {}
    for i in range(1, 11):
        t = f"T{i:02d}"
        b = read(OUT / t / "evidence_bundle.json")
        for p in b.get("separate_cost_sources", []):
            paths[(t, ntpath.normpath(p))] = {"discovered_from": str(OUT / t / "evidence_bundle.json")}
    for t, file in [("T07", "resource_usage.json"), ("T10", "resources_per_run.json")]:
        for r in read(OUT / t / file):
            paths[(t, ntpath.normpath(r["source"]))] = {"discovered_from": str(OUT / t / file)}
    return paths


def expand_reports(paths):
    records = []
    seen_paths = set()

    def visit(task, path):
        path = Path(path)
        key = (task, ntpath.normpath(str(path)))
        if key in seen_paths or not path.is_file():
            return
        seen_paths.add(key)
        report = read(path)
        if "studies" in report:
            # Never use cumulative totals, even when present beside the studies list.
            for i, s in enumerate(report["studies"]):
                if "cost_report" in s:
                    visit(task, s["cost_report"])
                else:
                    records.append((task, s["study_id"], str(path), f"/studies/{i}", s, report))
        elif report.get("study_id"):
            records.append((task, report["study_id"], str(path), "/", report, report))

    for task, path in paths:
        visit(task, path)
    grouped = {}
    for rec in records:
        grouped.setdefault(rec[:2], []).append(rec)
    return grouped


def store_for(run, raw, source, storemap):
    value = raw.get("store") or storemap.get(run)
    if value:
        p = Path(value)
        if p.is_dir():
            p = p / "platform.sqlite"
        if p.is_file():
            return p
    for folder in [Path(source).parent, Path(source).parent.parent]:
        for suffix in ["STORE_RESEARCH/platform.sqlite", "STORE_CORRECTED_PROTOCOL/platform.sqlite", "STORE/platform.sqlite"]:
            p = folder / suffix
            if p.is_file():
                try:
                    with sqlite3.connect("file:"+str(p)+"?mode=ro", uri=True) as db:
                        if db.execute("SELECT 1 FROM sessions WHERE run_id=?", (run,)).fetchone():
                            return p
                except sqlite3.Error:
                    pass
    return None


def observed_store_counts(run, path):
    result = {"source_store": str(path) if path else U,
              "candidate_artifacts_from_session": U, "unique_recorded_physical_designs": U,
              "physical_design_count_basis": "Exact canonical robot.structure.data equality excluding only top-level id and metadata; includes material, payout, real mass/inertia and actuator hardware; no hashing. Not count of optimizer calls.",
              "physics_steps_from_recorded_executions": U, "recorded_execution_count_with_steps": 0,
              "physical_request_groups_from_session": U,
              "active_raw_episodes_completed": U,
              "recorded_execution_sources": [], "elapsed_closed_minus_started_s": U}
    if path is None:
        return result
    with sqlite3.connect("file:"+str(path)+"?mode=ro", uri=True) as db:
        row = db.execute("SELECT state FROM sessions WHERE run_id=?", (run,)).fetchone()
        if not row:
            return result
        state = json.loads(row[0])

        def art(ref):
            if not isinstance(ref, dict) or "artifact_id" not in ref:
                return {}
            val = db.execute("SELECT body FROM artifacts WHERE id=?", (ref["artifact_id"],)).fetchone()
            return json.loads(val[0]) if val else {}

        refs = list({r["artifact_id"]: r for r in state.get("candidates", {}).values() if isinstance(r, dict) and "artifact_id" in r}.values())
        designs = set()
        for ref in refs:
            a = art(ref)
            design = a.get("scientific_configuration", {}).get("robot", {}).get("structure", {}).get("data")
            if design:
                design = {k: v for k, v in design.items() if k not in ["id", "metadata"]}
                designs.add(serial(design))
        result["candidate_artifacts_from_session"] = len(refs)
        result["unique_recorded_physical_designs"] = len(designs) if refs else 0
        if num(state.get("closed_unix")) and num(state.get("started_unix")):
            result["elapsed_closed_minus_started_s"] = state["closed_unix"] - state["started_unix"]
        execution_steps = {}
        completed_flags = {}
        refs = [*state.get("physical_replays", []), *state.get("results", [])]
        result["physical_request_groups_from_session"] = len({r["artifact_id"] for r in refs if isinstance(r, dict) and "artifact_id" in r})
        for ref in refs:
            a = art(ref)
            raw_ref = a.get("raw_reference")
            if not raw_ref:
                raw_ref = a.get("execution", {}).get("completion_stages", {}).get("simulation", {}).get("receipt", {}).get("output")
            if not raw_ref:
                continue
            raw = art(raw_ref)
            steps = raw.get("physics_steps", raw.get("cost", {}).get("physics_steps"))
            if steps is None:
                steps = raw.get("data", {}).get("data", {}).get("numerical_steps")
            if num(steps):
                exid = a.get("execution_id") or raw_ref["artifact_id"]
                execution_steps[exid] = steps
                raw_status = raw.get("solver_status", raw.get("status"))
                known_complete = a.get("acceptance", {}) or {}
                known_complete = known_complete.get("components", {}).get("execution_complete", {}).get("value")
                if isinstance(known_complete, bool):
                    completed_flags[exid] = known_complete
                elif raw_status in ["completed", "success", "ok"]:
                    completed_flags[exid] = True
                else:
                    fact = a.get("execution", {}).get("factual_result", {}).get("complete")
                    if isinstance(fact, bool):
                        completed_flags[exid] = fact
                result["recorded_execution_sources"].append(str(path)+"#artifacts/"+raw_ref["artifact_id"])
        result["recorded_execution_count_with_steps"] = len(execution_steps)
        result["physics_steps_from_recorded_executions"] = sum(execution_steps.values()) if execution_steps else U
        if execution_steps and len(completed_flags) == len(execution_steps):
            result["active_raw_episodes_completed"] = sum(completed_flags.values())
    return result


def normalize(task, run, alternatives, storemap, final_runs):
    # Prefer a per-run report over the enclosing cumulative report. Duplicate reports are not added.
    alternatives.sort(key=lambda r: ("cumulative" in r[5].get("version", ""), -len(Path(r[2]).parts)))
    _, _, source, pointer, s, enclosing = alternatives[0]
    expert = "budget" in s
    ledger = s.get("budget", s.get("ledger", {})).get("used", {})
    counter = s.get("store_counters", {})
    replay = s.get("physical_replay_launches", counter.get("physical_replay_launches", U))
    controller = s.get("legacy_controller_launch_counter", counter.get("nmpc_launches", U))
    additional = s.get("additional_independent_launches_from_reporting", 0)
    registered = s.get("registered_controller_executions", [])
    # Replay and controller counters refer to separate pipelines, not duplicate report snapshots.
    if expert:
        launches = nsum([replay, controller, additional])
        launch_basis = "physical_replay_launches + legacy_controller_launch_counter + explicit additional reporting launches within this Study"
    else:
        launches = nsum([replay, controller])
        launch_basis = "original Store physical_replay_launches plus nmpc_launches; unavailable counters remain separately recorded"
    internal = [c for a in s.get("native_analysis_cost_records", []) for c in a.get("internal_calculations", [])]
    inner = s.get("native_analysis_actual_resource_totals", {})
    if internal:
        inner = {k: nsum(c.get(k) for c in internal) for k in ["physics_steps", "rollouts", "forward_evaluations", "optimization_evaluations"]}
    episodes = s.get("physical_episodes", {})
    raw = s.get("physical_actual_resource_totals", {})
    observed = observed_store_counts(run, store_for(run, s, source, storemap), )
    physics = raw.get("physics_steps", observed["physics_steps_from_recorded_executions"])
    token = s.get("codex_usage", {})
    native_preps = [e.get("native_preparation_cost", {}) for e in registered]
    row = dict(task_id=task, run_id=run, actor="codex_surrogate_main", selected_final_run=run in final_runs.get(task, set()),
               mathematical_evaluations=s.get("charged_mathematical_evaluations", counter.get("mathematical_evaluations", U)),
               math_count_scope="charged original mathematical evaluations; not inner optimizer evaluations or controller preparation arithmetic",
               physical_launches=launches, physical_launch_count_basis=launch_basis,
               physical_replay_launches=replay, controller_launches=controller,
               additional_independent_launches=additional,
               physical_episodes_started=episodes.get("recorded_started", U), physical_episodes_completed=episodes.get("recorded_completed", U),
               physical_integration_steps=physics,
               physical_step_scope="recorded within-run physical execution steps; independent of native math internal integration steps",
               physical_step_coverage="original_COST_REPORT_totals" if "physics_steps" in raw else "stored result/raw artifacts; recorded execution count retained",
               native_math_integration_steps=inner.get("physics_steps", U),
               native_math_inner_rollouts=inner.get("rollouts", U),
               native_math_optimization_evaluations=inner.get("optimization_evaluations", U),
               controller_preparation_forward_evaluations=nsum(p.get("forward_evaluations") for p in native_preps),
               controller_preparation_physics_steps=nsum(p.get("physics_steps") for p in native_preps),
               morphology_or_physical_design_count_reported=s.get("structural_candidates", U),
               candidate_artifact_count_reported=s.get("candidate_artifacts", U),
               tools=ledger.get("tool_calls", s.get("top_level_public_operations", U)),
               provider_calls=s.get("provider_requests", ledger.get("model_calls", U)),
               codex_orchestration_tokens=U, token_availability="unavailable",
               token_reason=s.get("codex_usage_reason", enclosing.get("codex_token_status", "No authoritative per-task Codex host Token usage exposed; zero Provider calls is not zero orchestration tokens.")),
               raw_token_fields=token,
               budget_wall_s=ledger.get("wall_s", U),
               recorded_numerical_wall_s=s.get("recorded_numerical_wall_s", counter.get("numerical_s", U)),
               original_study_elapsed_s=s.get("study_elapsed_s", U),
               original_public_call_wall_s=s.get("public_call_wall_s", U),
               elapsed_wall_scope="different wall scopes remain separate; none are added",
               source=source, source_pointer=pointer,
               duplicate_report_sources=[{"path": a[2], "pointer": a[3]} for a in alternatives[1:]],
               duplicate_report_rule="One task/run row; cumulative totals excluded; repeated per-Study snapshots are alternate sources, never summed.",
               report_version=enclosing.get("version", U), original_record=s,
               **observed)
    if expert and episodes.get("recorded_started") is None and num(launches) and observed["recorded_execution_count_with_steps"] == launches:
        # All active expert tasks have one continuous trajectory per replay; passive reports retain their own episode totals.
        row["physical_episodes_started"] = launches
        row["physical_episodes_completed"] = observed["active_raw_episodes_completed"]
        row["physical_episode_basis"] = "one recorded active-task raw trajectory per original execution; each source is listed"
    return row


def phs_rows():
    source = PHS / "RESOURCE_USAGE.json"
    old = read(source)
    result = []
    for s in old["stores"]:
        run = s["run_id"]
        r = dict(task_id="PHS-2D", run_id=run, actor="Main SDK" if run == old["main"]["run_id"] else "Codex host; exact actor unavailable",
                 selected_final_run=run == "psd2d-core-fresh-20261112", source=str(source), source_pointer="/stores/"+str(old["stores"].index(s)),
                 source_store=s["store"], original_scope=s["scope"],
                 mathematical_evaluations=old["codex"]["math_evaluations_by_run"].get(run, U),
                 physical_launches=U, physical_episodes_started=U, physical_episodes_completed=U,
                 physical_integration_steps=U, morphology_or_physical_design_count_reported=U,
                 candidate_artifact_count_reported=U, tools=s["receipt_totals"]["tool_calls"],
                 provider_calls=s["receipt_totals"]["model_calls"], codex_orchestration_tokens=U,
                 token_availability="unavailable", budget_wall_s=s["receipt_totals"]["wall_s"],
                 recorded_numerical_wall_s=U, original_study_elapsed_s=U,
                 ledger_backend_solves=s["receipt_totals"]["backend_solves"],
                 accounting_note="Existing audited PHS paper package retained as a source reference; nominal, halfstep and Main costs stay separate. Backend-solves are not relabeled as replay launches.", original_record=s)
        if run == "psd2d-core-fresh-20261112":
            r.update(candidate_artifact_count_reported=old["codex"]["fresh_candidate_count"],
                     physics_steps_named_scopes={"fresh_search_as_originally_reported": old["codex"]["fresh_search_physics_steps"], "nominal": old["codex"]["nominal_physics_steps"]},
                     wall_named_scopes=old["codex"]["wall_time"])
        elif run == "psd2d-core-halfstep-20261112":
            r.update(candidate_artifact_count_reported=old["codex"]["halfstep_candidate_count"], physical_integration_steps=old["codex"]["halfstep_physics_steps"])
        elif run == old["main"]["run_id"]:
            m = old["main"]
            r.update(mathematical_evaluations=m["math_evaluations"], physical_episodes_started=m["physical_load_episodes"],
                     physical_episodes_completed=m["physical_load_episodes"], physical_integration_steps=m["physics_steps"],
                     candidate_artifact_count_reported=m["generated_candidates"],
                     provider_total_tokens=m["tokens"]["total_tokens"], provider_token_fields=m["tokens"],
                     token_availability="measured_Main_Provider_tokens; Codex_host_not_applicable",
                     wall_named_scopes=m.get("raw_time_derivation"), original_main_record=m)
        result.append(r)
    return result


def plot(rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({"font.family": "Arial", "font.size": 8.5, "axes.labelsize": 8.5,
                         "axes.titlesize": 8.5, "xtick.labelsize": 8, "ytick.labelsize": 8,
                         "axes.linewidth": .6, "xtick.major.width": .5, "ytick.major.width": .5,
                         "svg.fonttype": "none", "figure.facecolor": "white", "savefig.facecolor": "white"})
    final = [r for r in rows if r.get("selected_final_run") and r["task_id"] != "PHS-2D"]
    final.sort(key=lambda r: r["task_id"])
    assets = OUT / "CROSS_TASK/figure_assets"
    data = OUT / "CROSS_TASK/FIGURE_DATA"
    assets.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)
    writecsv(data / "selected_final_run_resources_plotdata.csv", final)
    fig, axs = plt.subplots(1, 3, figsize=(7.16, 2.5))
    fig.subplots_adjust(left=.075, right=.99, top=.86, bottom=.29, wspace=.42)
    for ax, metric, title, color in zip(axs,
            ["mathematical_evaluations", "physical_episodes_started", "tools"],
            ["(a) Charged math evaluations", "(b) Physical episodes", "(c) Budget tool calls"],
            ["#527F7B", "#70849A", "#26384B"]):
        vals = [r.get(metric, U) for r in final]
        numeric = [v if num(v) else math.nan for v in vals]
        xx = np.arange(len(final))
        ax.bar(xx, numeric, color=color, width=.65, linewidth=0)
        maximum = max([v for v in vals if num(v)] or [1])
        for x, v in zip(xx, vals):
            if num(v):
                ax.text(x, v+maximum*.025, str(int(v)), ha="center", va="bottom", fontsize=7.8)
            else:
                ax.text(x, maximum*.03, "n/a", ha="center", va="bottom", fontsize=7.8, rotation=90)
        ax.set_xticks(xx, [r["task_id"] for r in final], rotation=90)
        ax.set_ylim(0, maximum*1.22)
        ax.set_title(title, pad=7)
        ax.set_ylabel("Count")
        ax.spines[["right", "top"]].set_visible(False)
        ax.tick_params(direction="out", length=3, pad=2)
    fig.savefig(assets / "selected_final_run_resources.png", dpi=600)
    fig.savefig(assets / "selected_final_run_resources.svg")
    plt.close(fig)
    caption = """# Selected-final-run resource figure

**Caption.** Resources recorded for the selected final Study of each FULL task, with predecessor and superseded Studies excluded from each bar. (a) Charged original mathematical evaluations; these are accounting units, not internal optimizer evaluations or native controller preparation. (b) Original physical episodes started. (c) Budget tool calls. These are per-Study costs, not cumulative task-development costs and not a task-difficulty ranking. For T10, the five final episodes include the three required cases and two original frozen controls; zero charged mathematical evaluations does not imply zero controller-preparation computation. T08 has three top-level replay requests containing 16 physical sub-episodes, including baseline, mechanism ablation and numerical confirmations; these 16 episodes are not relabeled as 16 distinct candidate structures or 16 top-level requests. The original physical-launch counters and request groups are retained separately in CSV. Authoritative Codex orchestration Token usage is unavailable for all ten FULL runs; zero Provider calls is not zero host Token usage. The separate historical PHS-2D Main reproduction has measured Provider Token usage and is retained in RESOURCE_USAGE.json rather than combined with these Codex runs.

**Production.** 7.16 × 2.5 inches, Arial 8–8.5 pt, 600 dpi PNG and editable-text SVG. Exact per-run source paths, original counts, pipeline definitions and alternate duplicate reports are in ../FIGURE_DATA/selected_final_run_resources_plotdata.csv. Figures involve plotting arithmetic only; no new experiment or simulation.
"""
    (assets / "selected_final_run_resources_CAPTION.md").write_text(caption, encoding="utf-8")


def main():
    finals = read(OUT / "FINAL_CASES.json")
    final_runs = {}
    storemap = {}
    for f in finals:
        final_runs.setdefault(f["task_id"], set()).add(f["run_id"])
        if f.get("source_store"):
            storemap[f["run_id"]] = f["source_store"]
    index = OUT / "SUPPLEMENTARY/complete_candidate_index.csv"
    if index.exists():
        for r in csvread(index):
            original = json.loads(r["original_row_json"])
            s = original.get("store") or original.get("source_store")
            if s and r["run_id"] != U:
                storemap.setdefault(r["run_id"], s)
    grouped = expand_reports(gather_sources())
    records = [normalize(task, run, alternatives, storemap, final_runs) for (task, run), alternatives in grouped.items()]
    records.extend(phs_rows())
    records.sort(key=lambda r: (r["task_id"], r["run_id"]))
    package = {"schema_version": "per_study_resource_evidence_v1", "aggregation": "No grand totals. Every task/run remains separate. Cumulative source reports are expanded into their original Study records; duplicate snapshots are not added.",
               "scope": "Historical recorded costs only. Material extraction, plotting and rendering costs excluded.",
               "units_notice": "Charged mathematics, inner rollouts/integration, physical launches, physical sub-episodes, and different wall-clock scopes are distinct quantities.",
               "token_notice": "Codex host orchestration Tokens unavailable. PHS Main Provider Tokens retained separately and cannot be used as Codex Tokens.",
               "per_run": records}
    (OUT / "RESOURCE_USAGE.json").write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    writecsv(OUT / "CROSS_TASK/resource_usage_per_run.csv", records)
    plot(records)
    print(serial({"per_run_records": len(records), "selected_FULL_runs": [{k: r.get(k, U) for k in ["task_id", "run_id", "mathematical_evaluations", "physical_launches", "physical_integration_steps", "unique_recorded_physical_designs", "candidate_artifacts_from_session", "tools"]} for r in records if r.get("selected_final_run") and r["task_id"] != "PHS-2D"]}))


if __name__ == "__main__":
    main()
