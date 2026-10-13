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

from experiments.rl_pilot.env import DEFAULT_SOURCE_ROOT, ROOT, PHYSICS_DT, TensionEnv, NumericalFailure

PPO_SETTINGS = dict(
    learning_rate=3e-4, n_steps=256, batch_size=64, n_epochs=10,
    gamma=0.99, gae_lambda=0.95, clip_range=0.2, clip_range_vf=None,
    normalize_advantage=True, ent_coef=0.0, vf_coef=0.5, max_grad_norm=0.5,
    use_sde=False, sde_sample_freq=-1, target_kl=None,
    policy_kwargs=dict(net_arch=dict(pi=[64, 64], vf=[64, 64]), log_std_init=-3.0),
    device="cpu", verbose=0)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def versions():
    return {name: version(name) for name in ("numpy", "mujoco", "gymnasium", "stable-baselines3", "torch")}


class BudgetCallback(BaseCallback):
    def __init__(self, steps, max_seconds, started, writer, start_steps=0, checkpoint=None):
        super().__init__()
        self.steps, self.max_seconds = steps, max_seconds
        self.started, self.writer = started, writer
        self.start_steps = start_steps
        self.checkpoint = checkpoint
        self.stop_reason = "step_budget"
        self.sampling_batches = 0
        self.sampling_batches_started = 0

    def _on_rollout_start(self):
        if self.sampling_batches and self.sampling_batches % 25 == 0 and self.checkpoint:
            self.checkpoint(self, "recovery_checkpoint")
        self.sampling_batches_started += 1

    def _on_rollout_end(self):
        self.sampling_batches += 1

    def _on_step(self):
        elapsed = time.perf_counter() - self.started
        info = self.locals["infos"][0]
        self.writer.writerow([self.num_timesteps-self.start_steps, self.num_timesteps, elapsed, float(self.locals["rewards"][0]),
                              bool(self.locals["dones"][0]), json.dumps(info, default=lambda x: x.tolist())])
        if self.num_timesteps-self.start_steps >= self.steps:
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
    parser.add_argument("--physics-dt", type=float, default=PHYSICS_DT)
    parser.add_argument("--integrator", choices=["implicitfast", "implicit"], default="implicitfast")
    parser.add_argument("--resume", type=Path, help="compatible policy.zip; preserves cumulative cost")
    parser.add_argument("--learning-rate", type=float, default=PPO_SETTINGS["learning_rate"])
    parser.add_argument("--additional-cost", type=Path, help="interruption JSON: cost of lost work, added to resumed lineage")
    args = parser.parse_args()
    if args.steps <= 0 or not 0 < args.max_seconds < float("inf") or not 0 <= args.seed < 2**32:
        parser.error("steps/time must be positive and finite; seed must be in [0, 2**32)")
    if not 0 < args.learning_rate < float("inf"):
        parser.error("learning-rate must be finite and positive")
    output = (args.output or ROOT / "runs/rl_pilot" / args.mode).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    torch.set_num_threads(1)
    env = TensionEnv(args.mode, args.source_root, physics_dt=args.physics_dt, trace_dir=output, integrator=args.integrator, failure_mode="terminal")
    ppo_settings = dict(PPO_SETTINGS, learning_rate=args.learning_rate)
    prior = {}
    if args.resume:
        previous = json.loads(args.resume.with_name("settings.json").read_text(encoding="utf-8"))
        if previous["environment"] != env.settings() or previous["seed"] != args.seed:
            raise ValueError("Resume requires identical environment/action/observation/seed settings")
        expected_ppo = dict(policy="MlpPolicy", seed=args.seed, **ppo_settings)
        if any(previous["ppo"].get(key) != value for key, value in expected_ppo.items()
               if key != "learning_rate"):
            raise ValueError("Resume permits only a learning-rate change to PPO settings")
        model = PPO.load(args.resume, env=env, device="cpu", learning_rate=args.learning_rate)
        if model.pilot_environment != previous["environment"]:
            raise ValueError("Resume checkpoint/settings mismatch")
        prior = previous.get("cumulative_training", previous["training"])
    else:
        model = PPO("MlpPolicy", env, seed=args.seed, **ppo_settings)
    additional = json.loads(args.additional_cost.read_text()) if args.additional_cost else None
    if additional:
        prior = {key: prior.get(key, 0) + value for key, value in additional["cost"].items()}
    start_steps, start_epochs = model.num_timesteps, model._n_updates
    initial_parameters = torch.nn.utils.parameters_to_vector(model.policy.parameters()).detach().clone()
    model.pilot_environment = env.settings()  # pair checkpoint with its JSON conventions
    model.set_logger(configure(str(output), ["csv"]))
    settings = dict(
        mode=args.mode, seed=args.seed, environment=env.settings(),
        ppo=dict(policy="MlpPolicy", seed=args.seed, **ppo_settings),
        resume_from=str(args.resume.resolve()) if args.resume else None,
        prior_training=prior, additional_cost=additional,
        policy_defaults="SB3 Tanh activation, orthogonal init, Adam; see recorded SB3 version",
        torch_threads=1, environments=1, versions=versions(),
        requested=dict(control_steps=args.steps, max_seconds=args.max_seconds))
    write_json(output / "settings.json", settings)
    def save_snapshot(callback, reason, destination):
        elapsed = time.perf_counter() - started
        destination.mkdir(exist_ok=True)
        model.save(destination / "policy_pending.zip")
        (destination / "policy_pending.zip").replace(destination / "policy.zip")
        settings["training"] = dict(
            actual_control_steps=model.num_timesteps-start_steps,
            actual_physics_steps=env.counts["attempted_physics_steps"],
            **env.counts, sampling_batches=callback.sampling_batches,
            sampling_batches_started=callback.sampling_batches_started,
            policy_parameter_change_l2=float(torch.linalg.vector_norm(
                torch.nn.utils.parameters_to_vector(model.policy.parameters()).detach()-initial_parameters)),
            optimization_updates=(model._n_updates-start_epochs) // PPO_SETTINGS["n_epochs"],
            time_overrun_s=max(0.0, elapsed-args.max_seconds),
            elapsed_s=elapsed, stop_reason=reason,
            optimization_epochs_completed=model._n_updates-start_epochs,
            time_scope="environment/PPO setup and learning including optimization; excludes export/import")
        cost_keys = ("actual_control_steps", "actual_physics_steps", "completed_actions",
                     "attempted_actions", "complete_episodes", "failed_episodes",
                     "sampling_batches", "optimization_updates", "optimization_epochs_completed", "elapsed_s")
        settings["cumulative_training"] = {
            key: settings["training"][key] + prior.get(key, 0) for key in cost_keys}
        write_json(destination / "settings.json", settings)

    with (output / "training.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["control_steps", "cumulative_control_steps", "elapsed_s", "reward", "episode_end", "info_json"])
        def checkpoint(callback, reason):
            stream.flush()
            save_snapshot(callback, reason, output / "recovery")

        callback = BudgetCallback(args.steps, args.max_seconds, started, writer, start_steps, checkpoint)
        try:
            if time.perf_counter() - started >= args.max_seconds:
                callback.stop_reason = "time_limit_before_learning"
            else:
                model.learn(total_timesteps=args.steps, callback=callback, reset_num_timesteps=not bool(args.resume))
        except NumericalFailure as error:
            callback.stop_reason = "numerical_failure"
            settings["failure"] = env.failure
            print(str(error))
        except BaseException:
            callback.stop_reason = "interrupted_or_error"
            raise
        finally:
            save_snapshot(callback, callback.stop_reason, output)
            model.logger.close()
            env.close()
    print(json.dumps(settings["training"]))


if __name__ == "__main__":
    main()
