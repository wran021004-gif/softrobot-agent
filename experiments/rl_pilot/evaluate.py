"""Deterministic complete-episode evaluation using a checkpoint's saved settings."""
import argparse
import csv
import json
from pathlib import Path
import time

import torch
from stable_baselines3 import PPO

from experiments.rl_pilot.env import (
    CONTROL_DT, HOLD_STEPS, HORIZON, POSITION_SCALE, SPEED_SCALE, TENDONS, TensionEnv)
from experiments.rl_pilot.train import write_json


def run_episode(model, env, seed):
    observation, initial = env.reset(seed=seed)
    samples = [initial]
    total_reward = 0.0
    for _ in range(HORIZON):
        action, _ = model.predict(observation, deterministic=True)
        observation, reward, terminated, truncated, info = env.step(action)
        samples.append(info)
        total_reward += reward
        if terminated or truncated:
            break
    # Use the raw Gymnasium env: the final sample is never lost to vector auto-reset.
    indices = [row["control_step"] for row in samples]
    hold = [row for row in samples if row["control_step"] in HOLD_STEPS]
    coverage = [row["control_step"] for row in hold] == HOLD_STEPS
    complete = (indices == list(range(HORIZON + 1)) and terminated and not truncated
                and all(abs(row["engine_time_s"] - row["control_step"] * CONTROL_DT) < 1e-10
                        for row in samples))
    terminal_error = samples[-1]["position_error_m"]
    hold_error = max((row["position_error_m"] for row in hold), default=None)
    hold_speed = max((row["speed_m_s"] for row in hold), default=None)
    passed = (complete and coverage and terminal_error <= POSITION_SCALE
              and hold_error <= POSITION_SCALE and hold_speed <= SPEED_SCALE)
    metrics = dict(
        terminal_position_error_m=terminal_error, holding_max_position_error_m=hold_error,
        holding_max_speed_m_s=hold_speed, holding_sample_steps=[row["control_step"] for row in hold],
        holding_sample_times_s=[row["time_s"] for row in hold],
        complete=bool(complete), holding_coverage_complete=coverage, passed=bool(passed),
        episode_reward=total_reward)
    return samples, metrics


def write_trajectory(path, samples):
    header = ["control_step", "time_s", "engine_time_s"]
    header += [f"tip_{axis}_m" for axis in "xyz"] + [f"velocity_{axis}_m_s" for axis in "xyz"]
    for field in ("applied_n", "commanded_n", "clipped", "saturated"):
        header += [f"{tendon}_{field}" for tendon in TENDONS]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        for row in samples:
            writer.writerow([
                row["control_step"], row["time_s"], row["engine_time_s"],
                *row["tip_m"], *row["tip_velocity_m_s"], *row["applied_tension_n"],
                *row["commanded_tension_n"], *row["clipped"].astype(int),
                *row["saturated"].astype(int)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True, help="policy.zip beside settings.json")
    parser.add_argument("--source-root", type=Path, help="optional relocated XML source")
    parser.add_argument("--output", type=Path, help="new evaluation directory")
    parser.add_argument("--episodes", type=int, choices=[1, 2], default=1)
    args = parser.parse_args()
    started = time.perf_counter()
    settings = json.loads(args.policy.with_name("settings.json").read_text(encoding="utf-8"))
    saved = settings["environment"]
    torch.set_num_threads(settings["torch_threads"])
    env = TensionEnv(saved["mode"], args.source_root or saved["source_root"], saved["residual_scale_n"])
    current = env.settings()
    paths = {"source_root", "xml_source", "execution_json", "reference_npz"}
    if any(current[key] != value for key, value in saved.items() if key not in paths):
        raise ValueError("Saved environment conventions differ from this implementation")
    model = PPO.load(args.policy, env=env, device="cpu")
    if model.pilot_environment != saved:
        raise ValueError("policy.zip and settings.json do not belong together")
    output = (args.output or args.policy.parent / "evaluation").resolve()
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for episode in range(1, args.episodes + 1):
        samples, metrics = run_episode(model, env, settings["seed"])
        write_trajectory(output / f"trajectory_{episode}.csv", samples)
        results.append(metrics)
    env.close()
    result = dict(
        mode=saved["mode"], policy=str(args.policy.resolve()), seed=settings["seed"],
        training_cost=settings["training"], evaluation_elapsed_s=time.perf_counter() - started,
        input_source=current, episodes=results, passed=all(item["passed"] for item in results),
        acceptance=dict(position_limit_m=POSITION_SCALE, holding_speed_limit_m_s=SPEED_SCALE,
                        holding_steps=HOLD_STEPS),
        tension_timing="row k>0: tension on interval [(k-1)*0.01,k*0.01]; row 0: zero, no action",
        repetition_scope="identical initial states; nominal confirmation only")
    write_json(output / "result.json", result)
    print(json.dumps({key: result[key] for key in ("mode", "passed", "episodes", "evaluation_elapsed_s")}))


if __name__ == "__main__":
    main()
