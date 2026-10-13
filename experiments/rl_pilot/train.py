"""Train one CPU PPO policy; importing this module never starts training."""
import argparse
import csv
from importlib.metadata import version
import json
from pathlib import Path
import time

import torch
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.logger import configure

from experiments.rl_pilot.env import DEFAULT_SOURCE_ROOT, ROOT, SUBSTEPS, TensionEnv

PPO_SETTINGS = dict(
    learning_rate=3e-4, n_steps=256, batch_size=64, n_epochs=10,
    gamma=0.99, gae_lambda=0.95, clip_range=0.2, clip_range_vf=None,
    normalize_advantage=True, ent_coef=0.0, vf_coef=0.5, max_grad_norm=0.5,
    use_sde=False, sde_sample_freq=-1, target_kl=None,
    policy_kwargs=dict(net_arch=dict(pi=[64, 64], vf=[64, 64])),
    device="cpu", verbose=0)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def versions():
    return {name: version(name) for name in ("numpy", "mujoco", "gymnasium", "stable-baselines3", "torch")}


class BudgetCallback(BaseCallback):
    def __init__(self, steps, max_seconds, started, writer):
        super().__init__()
        self.steps, self.max_seconds = steps, max_seconds
        self.started, self.writer = started, writer
        self.stop_reason = "step_budget"

    def _on_step(self):
        elapsed = time.perf_counter() - self.started
        self.writer.writerow([self.num_timesteps, self.num_timesteps * SUBSTEPS,
                              elapsed, float(self.locals["rewards"][0]),
                              bool(self.locals["dones"][0])])
        if self.num_timesteps >= self.steps:
            self.stop_reason = "step_budget"
            return False
        if elapsed >= self.max_seconds:
            self.stop_reason = "time_limit"
            return False
        return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["residual", "direct"], required=True)
    parser.add_argument("--steps", type=int, default=200_000)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--max-seconds", type=float, default=1800)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.steps <= 0 or not 0 < args.max_seconds < float("inf") or not 0 <= args.seed < 2**32:
        parser.error("steps/time must be positive and finite; seed must be in [0, 2**32)")
    output = (args.output or ROOT / "runs/rl_pilot" / args.mode).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    torch.set_num_threads(1)
    env = TensionEnv(args.mode, args.source_root)
    model = PPO("MlpPolicy", env, seed=args.seed, **PPO_SETTINGS)
    model.pilot_environment = env.settings()  # pair checkpoint with its JSON conventions
    model.set_logger(configure(str(output), ["csv"]))
    settings = dict(
        mode=args.mode, seed=args.seed, environment=env.settings(),
        ppo=dict(policy="MlpPolicy", seed=args.seed, **PPO_SETTINGS),
        policy_defaults="SB3 Tanh activation, orthogonal init, Adam; see recorded SB3 version",
        torch_threads=1, environments=1, versions=versions(),
        requested=dict(control_steps=args.steps, max_seconds=args.max_seconds))
    write_json(output / "settings.json", settings)
    with (output / "training.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["control_steps", "physics_steps", "elapsed_s", "reward", "episode_end"])
        callback = BudgetCallback(args.steps, args.max_seconds, started, writer)
        try:
            if time.perf_counter() - started >= args.max_seconds:
                callback.stop_reason = "time_limit_before_learning"
            else:
                model.learn(total_timesteps=args.steps, callback=callback)
        except BaseException:
            callback.stop_reason = "interrupted_or_error"
            raise
        finally:
            elapsed = time.perf_counter() - started
            model.save(output / "policy.zip")
            settings["training"] = dict(
                actual_control_steps=model.num_timesteps,
                actual_physics_steps=model.num_timesteps * SUBSTEPS,
                elapsed_s=elapsed, stop_reason=callback.stop_reason,
                optimization_epochs_completed=model._n_updates,
                time_scope="environment/PPO setup and learning including optimization; excludes export/import")
            write_json(output / "settings.json", settings)
            model.logger.close()
            env.close()
    print(json.dumps(settings["training"]))


if __name__ == "__main__":
    main()
