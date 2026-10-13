"""SB3 PPO training, conservative accounting and atomic checkpoint generations."""
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import time
import uuid

import torch
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.logger import configure

from tools.rl.env import TensionEnv
from tools.rl.run import read_json, write_json


class ControlledStop(RuntimeError):
    pass


def digest(value):
    """Stable digest of parameters/Adam state, including tensor values and counters."""
    result = hashlib.sha256()
    def add(item):
        if isinstance(item, torch.Tensor):
            tensor = item.detach().cpu().contiguous()
            result.update(str((str(tensor.dtype), tuple(tensor.shape))).encode())
            result.update(tensor.numpy().tobytes())
        elif isinstance(item, dict):
            for key in sorted(item, key=str):
                add(key)
                add(item[key])
        elif isinstance(item, (list, tuple)):
            for child in item:
                add(child)
        else:
            result.update(repr(item).encode())
        result.update(b"\0")
    add(value)
    return result.hexdigest()


def config_digest(config):
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


def optimizer_steps(model):
    return max((int(s["step"].item()) for s in model.policy.optimizer.state.values() if "step" in s), default=0)


def snapshot(model):
    progress = model._current_progress_remaining
    return dict(policy_sha256=digest(model.policy.state_dict()), optimizer_sha256=digest(model.policy.optimizer.state_dict()),
                num_timesteps=model.num_timesteps, optimization_epochs=model._n_updates,
                rollout_optimizations=getattr(model, "runtime_rollouts", 0), optimizer_steps=optimizer_steps(model),
                schedule=dict(total_timesteps=model._total_timesteps, progress_remaining=progress,
                              learning_rate=float(model.lr_schedule(progress)), clip_range=float(model.clip_range(progress)),
                              clip_range_vf=None if model.clip_range_vf is None else float(model.clip_range_vf(progress))))


def schedule_setting(value):
    if not isinstance(value, dict):
        return value
    if value.get("kind") != "linear" or set(value) != {"kind", "initial", "final"}:
        raise ValueError("Schedules support only {kind: linear, initial, final}")
    initial, final = value["initial"], value["final"]
    if not all(math.isfinite(v) and v >= 0 for v in (initial, final)):
        raise ValueError("Schedule endpoints must be nonnegative and finite")
    return lambda progress: final + (initial - final) * progress


def valid_checkpoint(directory, config):
    pointer = read_json(directory / "checkpoint.json") if (directory / "checkpoint.json").exists() else {}
    errors = []
    for generation in (pointer.get("current"), pointer.get("previous")):
        if not generation:
            continue
        try:
            path = directory / "checkpoints" / generation
            metadata = read_json(path / "metadata.json")
            if metadata["config_sha256"] != config_digest(config):
                raise ValueError("immutable configuration mismatch")
            if metadata["policy_file_sha256"] != hashlib.sha256((path / "policy.zip").read_bytes()).hexdigest():
                raise ValueError("policy file digest mismatch")
            inherited = metadata["inherited"]
            schedule = inherited["schedule"]
            horizon = config["budget"]["actions"]
            if (schedule["total_timesteps"] != horizon or inherited["num_timesteps"] > horizon
                    or not math.isclose(schedule["progress_remaining"], 1 - inherited["num_timesteps"] / horizon, abs_tol=1e-12)):
                raise ValueError("original schedule horizon/progress mismatch")
            return path, metadata
        except (OSError, KeyError, ValueError) as error:
            errors.append(f"{generation}: {error}")
    raise RuntimeError("No complete valid checkpoint generation; " + "; ".join(errors))


def publish_checkpoint(directory, model, config, consumed, inherited=None):
    """The pointer is the only publication point; failed writes leave it unchanged."""
    generation = f"step-{model.num_timesteps:08d}-{uuid.uuid4().hex[:8]}"
    destination = directory / "checkpoints" / generation
    destination.mkdir(parents=True)
    model.runtime_config_sha256 = config_digest(config)
    model.save(destination / "policy.zip")
    metadata = dict(config_sha256=config_digest(config), inherited=inherited or snapshot(model), consumed=consumed.copy(),
                    policy_file_sha256=hashlib.sha256((destination / "policy.zip").read_bytes()).hexdigest())
    write_json(destination / "metadata.json", metadata)
    previous = valid_checkpoint(directory, config)[0].name if (directory / "checkpoint.json").exists() else None
    write_json(directory / "checkpoint.json", dict(current=generation, previous=previous))
    return generation


class RuntimePPO(PPO):
    """A post-optimization hook; SB3 still owns all sampling and optimization."""
    def train(self):
        self.runtime_before_optimization()
        super().train()
        self.runtime_rollouts = getattr(self, "runtime_rollouts", 0) + 1
        self.runtime_boundary()

    def _excluded_save_params(self):
        return super()._excluded_save_params() + ["runtime_boundary", "runtime_before_optimization"]


class AccountingCallback(BaseCallback):
    def __init__(self, context):
        super().__init__()
        self.context = context

    def _on_training_start(self):
        context = self.context
        actual = snapshot(self.model)
        if actual["schedule"]["total_timesteps"] != context.config["budget"]["actions"]:
            raise RuntimeError("SB3 learn changed the original schedule horizon")
        if context.restored is not None:
            # This happens after SB3's _setup_learn, before any new sampling.
            passed = actual == context.restored
            write_json(context.directory / f"restore-{context.token}.json", dict(passed=passed, expected=context.restored, loaded=actual,
                       fresh_episode=bool(self.model._last_episode_starts.all())))
            if not passed:
                raise RuntimeError("Policy, optimizer, counters or schedule changed during restore/setup")
        context.flush()

    def _on_rollout_start(self):
        self.context.reserve()

    def _on_step(self):
        # Never discard an aligned final batch here. The pre-action guard handles
        # hard limits; the post-optimization hook handles boundary stops.
        return True


class WorkerContext:
    def __init__(self, directory, token, started):
        self.directory, self.token, self.started = directory, token, started
        self.config = read_json(directory / "config.json")
        self.state = read_json(directory / "state.json")
        if self.state["worker_token"] != token:
            raise RuntimeError("Worker token does not match this run")
        self.base = self.state["consumed"].copy()
        self.env = self.model = None
        self.restored = None
        self.reserved_actions = 0
        self.before = None

    def consumed(self):
        result = self.base.copy()
        if self.env is not None:
            for key, amount in self.env.counts.items():
                result[key] += amount
        result["active_seconds"] += time.perf_counter() - self.started
        return result

    def flush(self):
        consumed = self.consumed()
        self.state["consumed"] = consumed
        pending = max(0, self.reserved_actions - (self.env.counts["attempted_actions"] if self.env else 0))
        self.state["reservation"] = dict(attempted_actions=pending, attempted_physics_steps=pending * 20,
                active_seconds=max(0, self.config["budget"]["active_seconds"] - consumed["active_seconds"]))
        write_json(self.directory / "state.json", self.state)

    def stop_requested(self):
        path = self.directory / "stop.json"
        return path.exists() and read_json(path)["token"] == self.token

    def guard(self):
        cost = self.consumed()
        if cost["attempted_actions"] >= self.config["budget"]["actions"]:
            raise ControlledStop("action_budget; partial rollout was not optimized")
        if cost["active_seconds"] >= self.config["budget"]["active_seconds"]:
            raise ControlledStop("active_time_budget")
        if self.stop_requested():
            raise ControlledStop("user_stop; partial rollout was not optimized")

    def reserve(self):
        self.guard()
        remaining = self.config["budget"]["actions"] - self.consumed()["attempted_actions"]
        self.reserved_actions = self.env.counts["attempted_actions"] + min(self.model.n_steps, remaining)
        self.flush()  # durable reservation precedes the first attempted action

    def boundary(self):
        # Do not publish partial optimizer state after an exception in SB3.train.
        self.flush()
        generation = publish_checkpoint(self.directory, self.model, self.config, self.state["consumed"])
        self.state["checkpoints"] = read_json(self.directory / "checkpoint.json")
        self.state["inherited"] = snapshot(self.model)
        self.state["latest_checkpoint"] = str(self.directory / "checkpoints" / generation)
        self.flush()  # checkpoint write time counts toward shared active time
        cost = self.consumed()
        if cost["attempted_actions"] >= self.config["budget"]["actions"]:
            raise ControlledStop("action_budget")
        if cost["active_seconds"] >= self.config["budget"]["active_seconds"]:
            raise ControlledStop("active_time_budget")
        if self.stop_requested():
            raise ControlledStop("user_stop")
        boundary = self.config.get("stop_at_boundary")
        if boundary is not None and self.model.num_timesteps == boundary and self.restored is None:
            self.state["awaiting_stop_at_boundary"] = boundary
            self.flush()
            # Public stop writes the real request. This wait is active worker time.
            while not self.stop_requested():
                self.guard()
                time.sleep(0.02)
            raise ControlledStop("user_stop")


    def before_optimization(self):
        if self.consumed()["active_seconds"] >= self.config["budget"]["active_seconds"]:
            raise ControlledStop("active_time_budget; full rollout was not optimized")


def worker(directory, token, started):
    context = WorkerContext(directory, token, started)
    reason, outcome = "worker_failed", "failed"
    try:
        torch.set_num_threads(1)
        context.guard()
        context.state["status"] = "running"
        context.env = TensionEnv(context.config, trace_dir=directory / "failures" / token,
                                 failure_mode="terminal", guard=context.guard)
        if (directory / "checkpoint.json").exists():
            path, metadata = valid_checkpoint(directory, context.config)
            context.model = RuntimePPO.load(path / "policy.zip", env=context.env, device="cpu", force_reset=True)
            context.restored = metadata["inherited"]
            if context.model.runtime_config_sha256 != config_digest(context.config) or snapshot(context.model) != context.restored:
                raise RuntimeError("Checkpoint policy/optimizer/counters/schedules differ from generation metadata")
            context.state["inherited"] = context.restored
            context.state["latest_checkpoint"] = str(path)
            context.state["recovered_from_generation"] = path.name
        else:
            settings = context.config["ppo"].copy()
            for key in ("learning_rate", "clip_range", "clip_range_vf"):
                settings[key] = schedule_setting(settings[key])
            context.model = RuntimePPO("MlpPolicy", context.env, seed=context.config["seed"], **settings)
            context.model._total_timesteps = context.config["budget"]["actions"]
        model = context.model
        context.before = snapshot(model)
        context.initial_parameters = torch.nn.utils.parameters_to_vector(model.policy.parameters()).detach().clone()
        model.runtime_boundary = context.boundary
        model.runtime_before_optimization = context.before_optimization
        model.set_logger(configure(str(directory / token), ["csv"]))
        context.flush()
        context.guard()
        # SB3 2.9 adds the loaded num_timesteps when reset_num_timesteps=False.
        # Preserve the original schedule denominator even when spent work is
        # ahead of checkpoint-inherited learning; the independent guard enforces
        # the smaller remaining campaign allowance before every action.
        horizon = context.config["budget"]["actions"]
        model.learn(total_timesteps=horizon - model.num_timesteps,
                    reset_num_timesteps=False, callback=AccountingCallback(context))
        reason, outcome = "action_budget", "completed"
    except ControlledStop as error:
        reason = str(error)
        outcome = "completed" if reason == "action_budget" else "stopped"
    except Exception as error:
        reason = f"{type(error).__name__}: {error}"
        context.state["error"] = reason
    finally:
        if context.model is not None:
            after = snapshot(context.model)
            record = dict(token=token, before=context.before, after=after,
                          attempted_actions=context.env.counts["attempted_actions"],
                          active_seconds=time.perf_counter() - started,
                          parameter_change_l2=float(torch.linalg.vector_norm(
                              torch.nn.utils.parameters_to_vector(context.model.policy.parameters()).detach() - context.initial_parameters))
                          if hasattr(context, "initial_parameters") else None,
                          unoptimized_actions=after["num_timesteps"] - context.state.get("inherited", {}).get("num_timesteps", 0))
            context.state["workers"].append(record)
            context.model.logger.close() if hasattr(context.model, "_logger") else None
        if context.env:
            context.env.close()
        context.state.update(status=outcome, stop_reason=reason, reservation={})
        context.state.pop("awaiting_stop_at_boundary", None)
        context.state["consumed"] = context.consumed()
        context.state["active_time_overrun_s"] = max(0, context.state["consumed"]["active_seconds"] - context.config["budget"]["active_seconds"])
        write_json(directory / "state.json", context.state)
        print(json.dumps(dict(status=outcome, stop_reason=reason, consumed=context.state["consumed"])))
