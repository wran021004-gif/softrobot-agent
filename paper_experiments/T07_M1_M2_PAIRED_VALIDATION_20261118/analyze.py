"""Reconstruct the four-condition table from archived certificates and new raw runs."""

import argparse
import csv
import gzip
import hashlib
import json
import math
import sqlite3
from pathlib import Path

from run_missing import BASE, REPLAY, WORKERS, HERE, load, save

CELLS = ("m1_d0", "m1_d1", "m2_d0", "m2_d1")
OLD = Path("paper_experiments/ten_task_codex_solve_20261112/T07_C1_four_tendon")
MASTER = Path("paper_experiments/paper_results_master_20261113")
SHOWCASE = Path(".worktrees/showcase-ten-task-reference-20261112/C1_four_tendons")


def file_sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def table(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_optimizer(path):
    compressed = path.with_suffix(".json.gz")
    return json.loads(gzip.decompress(compressed.read_bytes())) if compressed.exists() else load(path)


def constraint_rows(qualification, condition, cell):
    margins = qualification["constraint_margins"]
    components = qualification["components"]
    assert qualification["status"] in ("valid_failure", "accepted", "valid_pass", "passed"), qualification["status"]
    scaled = {}
    values = []
    for name, row in sorted(margins.items()):
        bound, observed, direction = row["limit"], row["observed"], row["direction"]
        assert direction in ("maximum", "minimum")
        assert all(isinstance(value, (int, float)) and math.isfinite(value) for value in (bound, observed))
        passed = components["evaluator:" + name]["passed"]
        excess = (-row["margin"] / abs(bound)) if bound else None
        if excess is not None:
            scaled[name] = excess
        else:
            assert passed is True, "Unscaled hard gate failed: gmax cannot be reported"
        values.append(dict(condition=condition, cell=cell, constraint=name, value=observed, unit=row["units"],
                           bound=bound, direction=direction, signed_normalized_excess=excess, passed=passed))
    for key in ("evaluation_validity", "execution_complete", "protocol_sampling"):
        assert components[key]["passed"] is True
    assert qualification["accepted"] == all(row["passed"] for row in values)
    worst = max(scaled, key=scaled.get)
    return dict(gmax=scaled[worst], gap=max(0.0, scaled[worst]), worst_constraint=worst,
                acceptance="PASS" if qualification["accepted"] else "FAIL"), values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--runs", type=Path, default=HERE / "runs")
    parser.add_argument("--output", type=Path, default=HERE)
    args = parser.parse_args()
    root, runs, output = (path.resolve() for path in (args.archive, args.runs, args.output))
    output.mkdir(parents=True, exist_ok=True)
    src = root / BASE
    store_path = src / "STORE_RESEARCH/platform.sqlite"
    sources, constraints, cells, paired = [], [], [], []
    native_costs = {}
    seen = set()

    def index(path, role, basis="archive"):
        relative = path.relative_to(root if basis == "archive" else runs).as_posix()
        if (basis, relative) not in seen:
            sources.append(dict(basis=basis, path=relative, role=role, sha256=file_sha(path) if path.is_file() else "",
                                availability="present" if path.is_file() else "missing"))
            seen.add((basis, relative))
        return relative

    def read(path, role):
        index(path, role)
        return load(path)

    protocol = read(src / "TASK_PROTOCOL.json", "original four required cases")
    cases = [row["condition_id"] for row in protocol["cases"] if row["role"] == "required"]
    assert cases == list(WORKERS)
    final = read(src / "FINAL_RESULT.json", "independent final evaluation and common root")
    baseline = read(src / "INITIAL_CANDIDATE.json", "d0 generated baseline")
    modified = read(src / "MINIMUM_RADIUS_ROOT_CANDIDATE.json", "d1 final modified structure")
    assert final["root_candidate"] == modified["candidate"]
    for key in ("actuator_order", "actuators", "tendon_order", "force_limits_n", "discretization"):
        assert baseline["resolved"][key] == modified["resolved"][key]
    assert len(baseline["resolved"]["tendon_order"]) == 4
    index(store_path, "source of individual T07 Store artifacts")
    for path, role in [(src / "STUDY_TRACE.jsonl", "primary external-Codex Study trace"),
                       (src / "HARD_CASE_SEED.json", "candidate-bound d0/M1_B U0"),
                       (src / "HARD_CASE_ALIAS.json", "d0 original M1_B task binding"),
                       (src / "REQUESTS/014-seed-historical-hard-case-tensions.json", "d0 seed input"),
                       (src / "COST_REPORT.json", "historical budget debit"),
                       (root / OLD / "STORE/platform.sqlite", "earlier T07 Store; different design and evaluation version"),
                       (root / OLD / "STUDY_TRACE.jsonl", "earlier T07 Trace"),
                       (root / MASTER / "RAW_RESULT_INDEX.csv", "publication evidence index only"),
                       (root / BASE.parent / "ENVIRONMENT_LOCK.json", "frozen runtime versions")]:
        index(path, role)
    for path in sorted((src / "HISTORICAL_SOURCES").glob("*.json")):
        index(path, "historical showcase source")
    for case in cases:
        for path in [root / SHOWCASE / case / "schedule.json", root / OLD / f"PHYSICAL_{case}.json",
                     root / OLD / f"NATIVE_{case}.json", root / MASTER / "SOURCE_DATA" / f"T07_{case}_RESULT.json",
                     root / MASTER / "SOURCE_DATA/TASK_TIME_SERIES" / f"T07_{case}_FULL_ARRAYS.json"]:
            index(path, "historical cross-check (not an exact new paired cell)")
    for variant in ("A", "B"):
        path = root / EXP_VARIANTS / variant
        for name in ("TRACE.jsonl", "SUMMARY.json"):
            index(path / name, "T07 A/B ablation, not matched")
    artifact_rows = []
    matched_raw = {}
    with sqlite3.connect(store_path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        def store(ref, role):
            identifier = ref["artifact_id"]
            media, body = db.execute("SELECT media,body FROM artifacts WHERE id=?", (identifier,)).fetchone()
            artifact_rows.append(dict(artifact_id=identifier, media_type=media,
                sha256=hashlib.sha256(body).hexdigest(), role=role, store=store_path.relative_to(root).as_posix()))
            return json.loads(body)

        source = load(src / "HARD_CASE_SEED.json")
        fixed = store(source["source"], "d0 M1_B candidate-bound original seed")["trajectory"]
        for case in cases:
            hist_path = src / REPLAY[case]
            hist = read(hist_path, "archived d1 independent evaluation")
            final_case = next(row for row in final["cases"] if row["condition_id"] == (case if case != "M1_A" else "default"))
            assert hist["reference"] == final_case["reference"]
            assert hist["acceptance"] == final_case["acceptance"]
            worker = src / "STORE_RESEARCH/analyses" / WORKERS[case]
            query = read(worker / "request.json", "archived d1 M2 optimizer request")
            native = read(worker / "result.json", "archived d1 M2 optimizer result")
            old_trajectory = store(hist["source_reference"], f"{case} d1 historical applied optimized schedule")["trajectory"]
            raw = store(hist["raw_reference"], f"{case} d1 historical raw MuJoCo replay")
            store(hist["evaluation_reference"], f"{case} d1 evaluator result")
            assert raw["source_reference"] == hist["source_reference"] and raw["status"] == "completed"
            assert raw["tendon_order"] == old_trajectory["tendon_order"]
            for key in ("times_s", "tensions_n", "tendon_order"):
                assert native["native_dynamics"]["optimized_schedule"]["trajectory"][key] == old_trajectory[key]
            replay_folder = src / "STORE_RESEARCH/physical_replay" / hist["execution_id"]
            for name in ("request.json", "result.json", "samples.json", "robot.xml"):
                index(replay_folder / name, "archived d1 native replay file")
            new_opt_file = runs / f"{case}_reoptimized/optimizer_result.json"
            new_opt = read_optimizer(new_opt_file)
            native_costs[case] = new_opt["native_dynamics"]["cost"]
            new_opt_in = new_opt_file.with_name("optimizer_input.json")
            new_input = load(new_opt_in)
            assert new_input["query"]["control_optimization"]["settings"] == query["query"]["control_optimization"]["settings"]
            for key in ("protocol", "operation", "model_source", "operating_point", "scoring_window_s"):
                assert new_input["query"][key] == query["query"][key]
            for key in ("times_s", "tensions_n", "tendon_order"):
                assert (new_input["design_context"]["schedule"]["trajectory"][key] ==
                        query["design_context"]["schedule"]["trajectory"][key])
            prior_opt = native["native_dynamics"]["optimization"]
            trial = new_opt.get("native_dynamics", {}).get("optimization", {})
            values = {}
            for cell in CELLS:
                mode, arm = cell.split("_")
                item = dict(condition=case, cell=cell, data_status="", reuse="", gmax=None, gap=None,
                            acceptance="", worst_constraint="", optimizer_stop="", optimizer_native_gmax=None,
                            source="", evaluation_id="")
                relevant_opt = prior_opt if arm == "d1" else trial
                if mode == "m2":
                    item.update(optimizer_stop=relevant_opt.get("stop_reason") or new_opt.get("status"),
                        optimizer_native_gmax=(relevant_opt.get("best") or {}).get("measure", {}).get("signed_maximum_excess"))
                acceptance = None
                if mode == "m1" and case != "M1_B":
                    item.update(data_status="missing_d0_bound_U0")
                elif cell == "m2_d1":
                    item.update(data_status="observed", reuse="historical", evaluation_id=hist["evaluation_reference"]["artifact_id"],
                        source=hist_path.relative_to(root).as_posix())
                    acceptance = hist["acceptance"]
                else:
                    folder = runs / ("M1_B_fixed" if mode == "m1" else f"{case}_reoptimized") / arm
                    f = folder / "evaluation.json"
                    if f.is_file():
                        observed = load(f)
                        raw_new = load(folder / "raw.json")
                        assert raw_new["status"] == "completed"
                        request = load(folder / "input.json")
                        if mode == "m1":
                            for key in ("times_s", "tensions_n", "tendon_order"):
                                assert request["trajectory"][key] == fixed[key]
                            for key in ("requested_tension_n", "actual_tension_n"):
                                assert [sample[key] for sample in raw_new["samples"][1:]] == fixed["tensions_n"]
                            assert file_sha(folder / "robot.xml") == raw_new["xml_sha256"]
                            matched_raw[arm] = raw_new
                        else:
                            assert relevant_opt["stop_reason"] == "local_target_reached"
                        item.update(data_status="observed", reuse="new", source=f.relative_to(runs).as_posix(),
                                    evaluation_id=observed["evaluation_reference"]["artifact_id"])
                        acceptance = observed["acceptance"]
                    else:
                        assert mode == "m2" and relevant_opt.get("stop_reason") != "local_target_reached"
                        item.update(data_status="optimizer_not_reliably_converged", source=new_opt_in.relative_to(runs).parent.as_posix())
                if acceptance:
                    stats, metrics = constraint_rows(acceptance, case, cell)
                    item.update(stats)
                    constraints.extend(metrics)
                values[cell] = item
                cells.append(item)
            delta = lambda right, left: (values[right]["gmax"] - values[left]["gmax"]
                if values[right]["gmax"] is not None and values[left]["gmax"] is not None else None)
            paired.append(dict(condition=case, role="required",
                **{f"{cell}_{field}": values[cell][field] for cell in CELLS
                   for field in ("gmax", "gap", "acceptance", "data_status", "optimizer_stop")},
                delta_m1=delta("m1_d1", "m1_d0"), delta_m2=delta("m2_d1", "m2_d0"),
                delta_d1_reoptimization=delta("m2_d1", "m1_d1")))
    left, right = matched_raw["d0"], matched_raw["d1"]
    for key in ("physics_timestep_s", "physics_steps", "integrator", "physical_backend",
                "tension_execution_mode", "external_force_execution"):
        assert left[key] == right[key], key
    assert left["task_evidence"]["task_identity"] == right["task_evidence"]["task_identity"]
    for key in ("qpos_rad", "qvel_rad_s", "time_s"):
        assert left["samples"][0][key] == right["samples"][0][key], key
    assert left["xml_sha256"] != right["xml_sha256"]
    for path in sorted(runs.rglob("*")):
        if path.is_file():
            index(path, "new run input, raw output, or registered evaluator output", basis="runs")
    table(output / "paired_results.csv", paired)
    table(output / "cell_results.csv", cells)
    table(output / "raw_constraint_metrics.csv", constraints)
    table(output / "source_sha256.csv", sources)
    table(output / "store_artifact_sha256.csv", artifact_rows)
    summary = dict(task="T07", shared_roots={"d0": baseline["candidate"], "d1": modified["candidate"]},
        new_optimizer_runs=len(cases), new_independent_replays=sum(row["reuse"] == "new" for row in cells),
        historical_reused_optimizers=len(cases), historical_reused_independent_replays=len(cases),
        historical_reused_fixed_control_sequences=1, full_studies_rerun=0,
        new_optimizer_internal_rollouts=sum(cost["rollouts"] for cost in native_costs.values()),
        new_optimizer_internal_physics_steps=sum(cost["physics_steps"] for cost in native_costs.values()),
        baseline_optimizer_cost_by_condition=native_costs,
        full_m1_pairs=sum(row["delta_m1"] is not None for row in paired),
        full_m2_pairs=sum(row["delta_m2"] is not None for row in paired), paired=paired)
    save(output / "summary.json", summary)
    print(json.dumps({key: value for key, value in summary.items()
        if key not in ("shared_roots", "paired", "baseline_optimizer_cost_by_condition")}))


EXP_VARIANTS = Path("paper_experiments/ab_batch1_20261114/T07")


if __name__ == "__main__":
    main()
