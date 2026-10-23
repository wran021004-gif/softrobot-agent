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


def stable_phase_diagnostics(directory):
    """Saved complete-episode states only; reconstruct kinematics without mj_step."""
    import mujoco
    from tools.rl.env import STATE_SPEC
    directory=Path(directory);env=TensionEnv(read_json(directory/'config.json'));rows=[]
    for path in (directory/'failures').rglob('stable_episode_*.npz'):
        with np.load(path,allow_pickle=False) as values:
            for action,x,u in zip(values['episode_actions'],values['states'],values['tensions_n']):
                mujoco.mj_setState(env.model,env.data,x,STATE_SPEC);mujoco.mj_forward(env.model,env.data)
                rows.append(dict(episode_action=int(action),max_abs_qpos_rad=float(max(abs(env.data.qpos))),
                    max_abs_qvel_rad_s=float(max(abs(env.data.qvel))),tension_n=u.tolist()))
    return dict(stable_direct_phase_states=rows,physical_steps=0,
        scope='observational saved-state comparison; no unique causal failure attribution')


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
    indices = [row["control_step"] for row in samples]
    complete = (failure is None and indices == list(range(task["command_intervals"] + 1)) and terminated and not truncated
                and all(abs(row["engine_time_s"] - row["control_step"] * task["control_period_s"]) < 1e-10 for row in samples))
    if task['family']=='task.tracking':
        from schemas.platform import BackendResult,TaskDefinition
        from tools.platform_registry import registry
        from tools.state_io import digest
        original=TaskDefinition.model_validate(task['original'])
        raw=BackendResult(solver_status='completed' if complete else 'failed',backend_id='backend.family_mujoco',
            model_id='mujoco_serial_bending_v1',signals=[dict(spec=original.observations[0],
                times_s=[r['time_s'] for r in samples[1:]],values=[r['tip_m'].tolist() for r in samples[1:]])],
            data=dict(contract='platform.empty',data={}),initial_state=original.initializer.parameters,
            limitations=['Independent saved trajectory evaluation; no robustness claim'],seed=seed)
        reg=registry();source=dict(artifact_id=digest(raw.model_dump(mode='json')),media_type='application/json')
        ev=reg.get('evaluate.tracking',kind='evaluator').resolve()(original,raw,source,reg,digest(task['original']))
        bounds=all(np.all(r['applied_tension_n']>=env.lower-1e-8) and
                   np.all(r['applied_tension_n']<=env.upper+1e-8) for r in samples[1:])
        return samples,dict(complete=bool(complete),passed=bool(complete and bounds and ev.task_success),
            independent_evaluation=ev.model_dump(mode='json'),evaluated_trajectory=raw.model_dump(mode='json'),
            force_bounds_passed=bool(bounds),trajectory_rows=len(samples),numerical_failure=failure,
            episode_reward=reward_sum,counts={key:value-before[key] for key,value in env.counts.items()})
    acceptance = task["acceptance"]
    hold = [row for row in samples if row["control_step"] in acceptance["holding_steps"]]
    coverage = [row["control_step"] for row in hold] == acceptance["holding_steps"]
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




def evaluate(policy, output, source_root=None):
    started = time.perf_counter()
    torch.set_num_threads(1)
    metadata_path = policy.with_name("metadata.json")
    if metadata_path.exists():
        from tools.rl.train import config_digest, snapshot
        from tools.rl.continuation import published_checkpoint
        published_checkpoint(policy.parents[2],read_json(policy.parents[2]/"config.json"),policy.parent.name)
        metadata = read_json(metadata_path)
        config = read_json(policy.parents[2] / "config.json")
        if (config_digest(config) != metadata["config_sha256"]
                or hashlib.sha256(policy.read_bytes()).hexdigest() != metadata["policy_file_sha256"]):
            raise ValueError("Incomplete or mismatched checkpoint generation")
        config = copy.deepcopy(config)
        if not config.get('candidate'):raise ValueError('EXPLICIT_CHECKPOINT_CANDIDATE_REQUIRED')
        if source_root:
            raise ValueError('Frozen candidate evaluation cannot change source_root')
    else:
        raise ValueError('EXACT_PUBLISHED_CHECKPOINT_METADATA_REQUIRED')
    output.mkdir(parents=True, exist_ok=False)
    env = TensionEnv(config, trace_dir=output, failure_mode="raise")
    try:
        model = PPO.load(policy, env=env, device="cpu")
        if snapshot(model) != metadata["inherited"]:
            raise ValueError("Policy/optimizer/counters/schedule metadata mismatch")
        task = copy.deepcopy(config["task"])
        samples, metrics = run_episode(model, env, config["seed"], task)
        write_trajectory(output / "trajectory.csv", samples, task["tendon_order"])
        result = dict(policy=str(policy.resolve()), mode=config["mode"], seed=config["seed"], acceptance=task.get('acceptance',task.get('original',{}).get('evaluator')),
                      episodes=[metrics], passed=metrics["passed"], evaluation_elapsed_s=time.perf_counter() - started,
                      candidate_identity=config['candidate']['identity'],task_identity=config['candidate']['task_identity'],
                      run_id=policy.parents[2].name,
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
        if not ancestor.is_relative_to(root / "runs"):
            break
        if (ancestor / "config.json").exists():
            recorded=read_json(ancestor / 'config.json')
            if selected is not None and selected!=recorded: raise ValueError('Diagnosis config differs from capture run')
            return recorded
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


