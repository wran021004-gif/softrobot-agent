"""Independent frozen-policy acceptance and one selected failure replay."""
import copy
import csv
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch
from stable_baselines3 import PPO

from tools.rl.env import NumericalFailure, TensionEnv
from tools.rl.run import read_json, write_json


def run_episode(model, env, seed, task):
    """Only valid physical transitions can enter the exported trajectory."""
    before = env.counts.copy()
    observation, initial = env.reset(seed=seed)
    samples, reward_sum, failure = [initial], 0.0, None
    terminated = truncated = False
    for _ in range(task["command_intervals"]):
        try:
            action, _ = model.predict(observation, deterministic=True)
            observation, reward, terminated, truncated, info = env.step(action)
        except (NumericalFailure, ValueError, FloatingPointError) as error:
            failure = env.failure or dict(type=type(error).__name__, message=str(error))
            break
        if not info.get("valid_physical_transition", False):
            failure = info.get("failure") or {"message": "Surrogate terminal excluded from physical evaluation"}
            break
        samples.append(info)
        reward_sum += reward
        if terminated or truncated:
            break
    acceptance = task["acceptance"]
    indices = [row["control_step"] for row in samples]
    hold = [row for row in samples if row["control_step"] in acceptance["holding_steps"]]
    coverage = [row["control_step"] for row in hold] == acceptance["holding_steps"]
    complete = (failure is None and indices == list(range(task["command_intervals"] + 1)) and terminated and not truncated
                and all(abs(row["engine_time_s"] - row["control_step"] * task["control_period_s"]) < 1e-10 for row in samples))
    terminal = samples[-1]["position_error_m"] if complete else None
    hold_error = max((row["position_error_m"] for row in hold), default=None)
    hold_speed = max((row["speed_m_s"] for row in hold), default=None)
    passed = (complete and coverage and terminal <= acceptance.get('terminal_position_limit_m',acceptance['position_limit_m'])
              and hold_error <= acceptance["position_limit_m"] and hold_speed <= acceptance["holding_speed_limit_m_s"])
    return samples, dict(complete=bool(complete), passed=bool(passed), holding_coverage_complete=coverage,
                         terminal_position_error_m=terminal, holding_max_position_error_m=hold_error,
                         holding_max_speed_m_s=hold_speed, holding_sample_steps=[r["control_step"] for r in hold],
                         trajectory_rows=len(samples), numerical_failure=failure, episode_reward=reward_sum,
                         counts={key: value - before[key] for key, value in env.counts.items()})


def write_trajectory(path, samples, tendons):
    header = ["control_step", "time_s", "engine_time_s"]
    header += [f"tip_{axis}_m" for axis in "xyz"] + [f"velocity_{axis}_m_s" for axis in "xyz"]
    for field in ("applied_n", "commanded_n", "clipped", "saturated"):
        header += [f"{tendon}_{field}" for tendon in tendons]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        for row in samples:
            writer.writerow([row["control_step"], row["time_s"], row["engine_time_s"],
                             *row["tip_m"], *row["tip_velocity_m_s"], *row["applied_tension_n"],
                             *row["commanded_tension_n"], *map(int, row["clipped"]), *map(int, row["saturated"])])


def legacy_config(settings, source_root=None):
    """Translate the historical policy's conventions once, without rewriting it."""
    config = read_json(Path(__file__).resolve().parents[2] / "evidence/rl_runtime_20261013/historical_config.json")
    saved = settings["environment"]
    config["mode"], config["seed"] = saved["mode"], settings["seed"]
    config["source_root"] = str(source_root or saved["source_root"])
    config["physics"] = dict(timestep_s=saved["physics_dt_s"], integrator=saved.get("integrator", "implicitfast"))
    config["action"]["residual_scale_n"] = saved["residual_scale_n"]
    config["reward"].update(saved["reward"], failure_penalty=saved["failure_penalty"])
    for key in ("position_scale_m", "speed_scale_m_s"):
        config["observation"][key] = saved[key]
    if saved["mode"] == "residual":
        path = Path(__file__).resolve().parents[2] / "evidence/fc1012_open_loop_20261013/references.npz"
        config["reference"] = dict(path=str(path), tendon_order=saved["tendon_order"], control_period_s=saved["control_dt_s"],
                                   source_physical_execution=config["task"]["source_physical_execution"],
                                   sha256=hashlib.sha256(path.read_bytes()).hexdigest(), validation="failed MuJoCo task acceptance")
    config=historical_input(config)
    if config.get('reference'):
        config['reference'].update(candidate_identity=config['candidate']['identity'],task_identity=config['candidate']['task_identity'])
    return config


def evaluate(policy, output, source_root=None):
    started = time.perf_counter()
    torch.set_num_threads(1)
    metadata_path = policy.with_name("metadata.json")
    if metadata_path.exists():
        from tools.rl.train import config_digest, snapshot
        metadata = read_json(metadata_path)
        config = read_json(policy.parents[2] / "config.json")
        if (config_digest(config) != metadata["config_sha256"]
                or hashlib.sha256(policy.read_bytes()).hexdigest() != metadata["policy_file_sha256"]):
            raise ValueError("Incomplete or mismatched checkpoint generation")
        config = copy.deepcopy(config)
        if not config.get('candidate'): config=historical_input(config)
        if source_root:
            raise ValueError('Frozen candidate evaluation cannot change source_root')
        settings = None
    else:
        settings = read_json(policy.with_name("settings.json"))
        config = legacy_config(settings, source_root)
    output.mkdir(parents=True, exist_ok=False)
    env = TensionEnv(config, trace_dir=output, failure_mode="raise")
    try:
        if settings is not None:
            saved = settings["environment"]
            if (env.mode!=saved['mode'] or env.horizon!=saved['horizon']
                    or env.control_dt!=saved['control_dt_s'] or float(env.model.opt.timestep)!=saved['physics_dt_s']
                    or env.tendons!=saved['tendon_order']):
                raise ValueError("Historical policy conventions differ from this runtime")
        model = PPO.load(policy, env=env, device="cpu")
        if settings is not None and model.pilot_environment != settings["environment"]:
            raise ValueError("Historical policy/settings mismatch")
        if settings is None and snapshot(model) != metadata["inherited"]:
            raise ValueError("Policy/optimizer/counters/schedule metadata mismatch")
        task = copy.deepcopy(config["task"])
        samples, metrics = run_episode(model, env, config["seed"], task)
        write_trajectory(output / "trajectory.csv", samples, task["tendon_order"])
        result = dict(policy=str(policy.resolve()), mode=config["mode"], seed=config["seed"], acceptance=task["acceptance"],
                      episodes=[metrics], passed=metrics["passed"], evaluation_elapsed_s=time.perf_counter() - started,
                      candidate_identity=config['candidate']['identity'],task_identity=config['candidate']['task_identity'],
                      run_id=policy.parents[2].name if settings is None else 'historical',
                      checkpoint=policy.parent.name,config_sha256=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest(),
                      failure_reason=('numerical_failure' if metrics['numerical_failure'] else
                          None if metrics['passed'] else 'incomplete_trajectory' if not metrics['complete'] else 'task_thresholds_not_met'),
                      policy_sha256=hashlib.sha256(policy.read_bytes()).hexdigest(),
                      failure_stage='physics sampling' if metrics['numerical_failure'] else 'task criteria unmet' if metrics['complete'] and not metrics['passed'] else None,
                      last_valid_position_error_m=samples[-1]['position_error_m'],last_valid_speed_m_s=samples[-1]['speed_m_s'],
                      trajectory=str(output / "trajectory.csv"), scope="one deterministic fixed-initial-state episode; no robustness claim")
        write_json(output / "result.json", result)
        return result
    finally:
        env.close()


def replay_config(capture, explicit=None):
    selected=copy.deepcopy(explicit) if isinstance(explicit,dict) else read_json(explicit) if explicit else None
    # Runtime captures remain bound to their own immutable run configuration.
    root = Path(__file__).resolve().parents[2]
    for ancestor in capture.resolve().parents:
        if not ancestor.is_relative_to(root / "runs/rl"):
            break
        if (ancestor / "config.json").exists():
            recorded=read_json(ancestor / 'config.json')
            if selected is not None and selected!=recorded: raise ValueError('Diagnosis config differs from capture run')
            return recorded
    archive = capture.parent / "diagnosis.json"
    if archive.exists():
        record = read_json(archive).get(capture.stem)
        if record and "environment" in record:
            saved = record["environment"]
            saved = dict(saved, integrator=saved.get("integrator", "implicitfast"), failure_penalty=saved.get("failure_penalty", -10000.0))
            return legacy_config(dict(seed=record["seed"], environment=saved))
    raise ValueError("Replay needs a recorded run configuration or explicit --config; numerical settings are unknown")


def diagnose(capture, output=None, replay=False, config=None):
    result = dict(capture=str(capture.resolve()), replay_requested=replay, root_cause="unresolved")
    with np.load(capture, allow_pickle=False) as archive:
        result["arrays"] = {key: list(archive[key].shape) for key in archive.files}
        if not replay:
            result["scope"] = "saved evidence inspection; zero physical steps"
            return result
        state = archive["pre_step_state"].copy()
    if output is None:
        raise ValueError("Explicit replay requires a new output directory")
    output.mkdir(parents=True, exist_ok=False)
    config = replay_config(capture, config)
    sidecar=capture.with_suffix('.json')
    if sidecar.exists():
        recorded=read_json(sidecar)
        expected=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
        if recorded.get('config_sha256',expected)!=expected: raise ValueError('Capture configuration digest mismatch')
    env = TensionEnv(config, failure_mode="raise")
    try:
        result["replay"] = env.replay_pre_step(state)
        result["physics"] = config["physics"]
        result["scope"] = "one recorded pre-failure integration state, one physical step; no sweep"
        write_json(output / "result.json", result)
        return result
    finally:
        env.close()


def historical_input(config):
    """Explicit archive compatibility only; never called for new candidates."""
    from tools.rl.env import ROOT
    from contextlib import closing
    import sqlite3
    import tarfile
    XML_ID = config['provenance']['xml_id']
    def load_xml(source_root):
        """Read exactly one saved artifact; never rebuild or audit the archive."""
        dbpath = source_root / "runs/fc1012/platform.sqlite"
        if dbpath.exists():
            with closing(sqlite3.connect(dbpath.as_uri() + "?mode=ro", uri=True)) as db:
                row = db.execute("SELECT body FROM artifacts WHERE id=?", (XML_ID,)).fetchone()
            if row is not None:
                return row[0].decode("utf-8"), str(dbpath) + "#" + XML_ID
        member = f"artifacts/{XML_ID}.bin"
        archives = [source_root / "runs/fc1012/delivery_archive_reassembled.tar.gz",
                    source_root / "evidence/fixed_task_20261012/immutable_artifacts.tar.gz"]
        for path in archives:
            if path.exists():
                with tarfile.open(path, "r|gz") as archive:
                    for entry in archive:
                        if entry.name == member:
                            return archive.extractfile(entry).read().decode("utf-8"), str(path) + "#" + member
        raise FileNotFoundError(
            f"Missing robot XML: {dbpath} (artifacts.id={XML_ID}); "
            + "; ".join(f"{path}::{member}" for path in archives))


    xml, _ = load_xml(Path(config['source_root']))
    import xml.etree.ElementTree as ET
    document=ET.fromstring(xml)
    if config.get('physics'):
        # Historical policies explicitly recorded edits to a loaded model copy.
        document.find('option').set('timestep',str(config['physics']['timestep_s']))
        document.find('option').set('integrator',config['physics']['integrator'])
        xml=ET.tostring(document,encoding='unicode')
    tendons=config['task']['tendon_order']
    config['candidate']=dict(xml=xml,sha256=hashlib.sha256(xml.encode()).hexdigest(),assets={},
        identity=config['provenance']['xml_id'],task_identity=config['task']['source_physical_execution'])
    config['control_object']=dict(joint_names=[j.get('name') for j in document.findall('.//worldbody//joint')],
        tendon_names=tendons,actuator_names=[t+'_direct_tension' for t in tendons],
        tip_site='tip_site',semantics='ideal_tension')
    config['task']['family']='task.reach'
    return config
