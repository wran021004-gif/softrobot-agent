"""Use the archived Core kernels without modifying its frozen Study/Store."""

import argparse
import gzip
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = Path("paper_experiments/five_task_completion_20261113/T07_C1_four_tendon")
CORE = "5a1865d1e07c1505f787fa767572ffa00bf8d19c"
WORKERS = {
    "M1_A": "227ebd73be084652bd779e133fa2bbd9",
    "M1_B": "2b4e48bcb66c4c51af34fc4fd6b9d591",
    "M1_C": "d050546432844075857ff38262acf293",
    "M5": "9529bc659c71478f953cfda5730f48c9",
}
REPLAY = {
    "M1_A": "MINIMUM_RADIUS_ROOT_A_REPLAY.json",
    **{case: f"MINIMUM_RADIUS_ROOT_{case}_REPLAY.json" for case in ("M1_B", "M1_C", "M5")},
}


def load(path):
    return json.loads(path.read_bytes())


def save(path, value):
    content = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    path.write_bytes(gzip.compress(content, mtime=0) if path.suffix == ".gz" else content)


def digest_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("core", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("cells", nargs="+", choices=["M1", *WORKERS])
    args = parser.parse_args()
    args.archive, args.core, args.output = (path.resolve() for path in (args.archive, args.core, args.output))
    assert subprocess.check_output(["git", "-C", args.core, "rev-parse", "HEAD"], text=True).strip() == CORE
    assert not subprocess.check_output(["git", "-C", args.core, "status", "--porcelain", "-uno"], text=True).strip()
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[name] = "1"
    sys.path.insert(0, str(args.core))
    from extensions.tendon_family.backends import playback_tensions
    from tools.research import analysis, physical_replay
    from tools.research_tasks import assemble_acceptance
    from tools.platform_store import plain
    from tools.state_io import digest

    archive = args.archive / BASE
    store = archive / "STORE_RESEARCH"
    cost = load(archive / "COST_REPORT.json")
    assert cost["totals"]["charged_math"] + 4 <= cost["original_ceilings"]["charged_math"]
    assert cost["totals"]["physical_launches"] + 6 <= cost["original_ceilings"]["physical_launches"]
    with sqlite3.connect((store / "platform.sqlite").as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        def artifact(ref):
            body, = db.execute("SELECT body FROM artifacts WHERE id=?", (ref["artifact_id"],)).fetchone()
            return json.loads(body)

        base_ref = load(archive / "INITIAL_CANDIDATE.json")["candidate"]
        base_candidate = artifact(base_ref)
        base_b = artifact(load(archive / "HARD_CASE_ALIAS.json")["candidate"])
        fixed = artifact(load(archive / "HARD_CASE_SEED.json")["source"])["trajectory"]
        original = load(archive / "HISTORICAL_SOURCES/C1_four_tendons__M1_B__schedule.json")["trajectory"]
        for key in ("times_s", "tensions_n", "tendon_order"):
            assert fixed[key] == original[key]
        final = load(archive / "FINAL_RESULT.json")
        for mode in dict.fromkeys(args.cells):
            case = "M1_B" if mode == "M1" else mode
            historical = load(archive / REPLAY[case])
            folder = store / "analyses" / WORKERS[case]
            template = load(folder / "request.json")
            historical_native = load(folder / "result.json")
            archived_schedule = artifact(historical["source_reference"])["trajectory"]
            assert historical_native["native_dynamics"]["optimization"]["stop_reason"] == "local_target_reached"
            assert historical["candidate"] == template["query"]["candidate"]
            assert case in ("M1_A", *(row["condition_id"] for row in final["cases"]))
            config1 = template["configuration"]
            config0 = deepcopy(config1)
            config0["robot"]["structure"] = base_candidate["configuration"]["robot"]["structure"]
            config0["policy"]["candidate_builder"] = base_candidate["configuration"]["policy"]["candidate_builder"]
            for key in ("robot", "policy", "task", "seed"):
                if case == "M1_B":
                    assert config0[key] == base_b["configuration"][key], key
            context0 = physical_replay.model_context(config0)
            context1 = physical_replay.model_context(config1)
            assert context0[3]["design_identity"] != context1[3]["design_identity"]
            for key in ("qpos_rad", "qvel_rad_s", "gravity", "mount_position", "mount_rotation",
                        "forces", "duration_s", "timestep_s", "control_period_s", "sample_period_s"):
                assert context0[2][key] == context1[2][key], key
            for key in ("tendon_order", "coordinate_order"):
                assert context0[3][key] == context1[3][key]
            out = args.output / ("M1_B_fixed" if mode == "M1" else f"{case}_reoptimized")
            out.mkdir(parents=True, exist_ok=False)

            def bind(context, trajectory):
                inp, _, _, spec = context
                return dict(trajectory, model_identity=spec["identity"], design_identity=spec["design_identity"],
                            task_identity=digest(plain(inp.task)))

            def replay(arm, config, context, trajectory):
                trajectory = bind(context, trajectory)
                inp, physics, scene = physical_replay.binding(config, trajectory)
                dest = out / arm
                dest.mkdir()
                save(dest / "input.json", dict(configuration=config, trajectory=trajectory, core=CORE))
                raw = playback_tensions(inp, physics, scene, trajectory["tensions_n"], dest)
                save(dest / "raw.json", raw)
                raw_ref = dict(artifact_id=digest(raw), media_type="application/json")
                evaluation, profile = physical_replay.evaluate_playback(config, raw, raw_ref, digest(trajectory))
                evaluation_ref = dict(artifact_id=digest(plain(evaluation)), media_type="application/json")
                profile.update(execution_id=f"{out.name}/{arm}", simulation=raw_ref, evaluation=evaluation_ref)
                acceptance = assemble_acceptance(config, evaluation, profile, evaluation_reference=evaluation_ref,
                    motion=[dict(time_s=row["time_s"]) for row in raw["samples"]])
                save(dest / "evaluation.json", dict(acceptance=acceptance, evaluation=plain(evaluation), profile=profile,
                                                    raw_reference=raw_ref, evaluation_reference=evaluation_ref))

            if mode == "M1":
                assert bind(context0, fixed) == fixed
                for arm, cfg, ctx in (("d0", config0, context0), ("d1", config1, context1)):
                    replay(arm, cfg, ctx, fixed)
                continue

            search = deepcopy(template)
            search["configuration"] = config0
            seed = search["design_context"]["schedule"]
            seed["trajectory"] = bind(context0, seed["trajectory"])
            assert len(seed["trajectory"]["tensions_n"]) == len(archived_schedule["tensions_n"])
            physical_replay.binding(config0, seed["trajectory"])
            ref = dict(artifact_id=digest(config0), media_type="application/json")
            candidate = base_b if case == "M1_B" else base_candidate
            candidate_ref = load(archive / "HARD_CASE_ALIAS.json")["candidate"] if case == "M1_B" else base_ref
            search["query"]["candidate"] = candidate_ref
            search["binding"].update(candidate=candidate_ref, candidate_id=candidate["candidate_id"],
                configuration=ref, effective_configuration_identity=ref["artifact_id"],
                physical_design_identity=context0[3]["design_identity"])
            point = search["exact_point"]
            point.update(candidate=candidate_ref, configuration_identity=ref["artifact_id"],
                physics_identity=context0[2]["physics_identity"])
            point["native_replay"]["scene"] = context0[2]
            save(out / "optimizer_input.json", search)
            result = analysis.calculate(config0, search["binding"], search["query"], point,
                                        design_context=search["design_context"])
            save(out / "optimizer_result.json.gz", result)
            native = result["native_dynamics"]
            optimization = native["optimization"]
            print(case, optimization["stop_reason"], optimization["best"]["measure"]["signed_maximum_excess"], flush=True)
            if optimization["stop_reason"] == "local_target_reached":
                trajectory = native["optimized_schedule"]["trajectory"]
                replay("d0", config0, context0, trajectory)


if __name__ == "__main__":
    main()
