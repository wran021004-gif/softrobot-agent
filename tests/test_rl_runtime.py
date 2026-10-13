"""Focused lifecycle checks. No training campaigns or physical rollouts."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch
from stable_baselines3.common.base_class import BaseAlgorithm
from stable_baselines3.common.on_policy_algorithm import OnPolicyAlgorithm

from tools.rl import checks, run, train
from tools.rl.env import TensionEnv


def config():
    return run.read_json(Path(run.__file__).with_name("config.json"))


class FakeModel:
    def __init__(self, steps=1024):
        self.policy = torch.nn.Linear(1, 1)
        self.policy.optimizer = torch.optim.Adam(self.policy.parameters(), lr=0.0003)
        self.num_timesteps, self._n_updates, self.runtime_rollouts = steps, 40, 4
        self._total_timesteps, self._current_progress_remaining = 2048, 1 - steps / 2048
        self.lr_schedule = train.schedule_setting(dict(kind="linear", initial=0.0003, final=0.0001))
        self.clip_range = train.schedule_setting(dict(kind="linear", initial=0.2, final=0.1))
        self.clip_range_vf = train.schedule_setting(dict(kind="linear", initial=0.3, final=0.1))

    def save(self, path):
        path.write_bytes(b"complete stand-in policy")


class FakeEnv:
    def __init__(self, fail=False, surrogate=False):
        self.counts = dict(attempted_actions=0, completed_actions=0, attempted_physics_steps=0, complete_episodes=0, failed_episodes=0)
        self.k, self.fail, self.surrogate, self.failure = 0, fail, surrogate, None

    def row(self):
        return dict(control_step=self.k, time_s=self.k * 0.01, engine_time_s=self.k * 0.01,
                    position_error_m=0.001, speed_m_s=0.002, tip_m=np.zeros(3), tip_velocity_m_s=np.zeros(3),
                    applied_tension_n=np.zeros(6), commanded_tension_n=np.zeros(6), clipped=np.zeros(6), saturated=np.zeros(6))

    def reset(self, seed=None):
        return np.zeros(109), self.row()

    def step(self, action):
        self.counts["attempted_actions"] += 1
        if self.fail:
            self.counts["attempted_physics_steps"] += 1
            raise checks.NumericalFailure("captured synthetic failure")
        if self.surrogate:
            return np.zeros(109), -10000, True, False, dict(self.row(), valid_physical_transition=False)
        self.k += 1
        self.counts["completed_actions"] += 1
        self.counts["attempted_physics_steps"] += 20
        return np.zeros(109), -1, self.k == 35, False, dict(self.row(), valid_physical_transition=True)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.config = config()

    def state(self):
        value = dict(status="running", worker_token="dead", consumed=dict(attempted_actions=1024, active_seconds=10.0,
                     attempted_physics_steps=20480, completed_actions=1024, complete_episodes=0, failed_episodes=0),
                     reservation={}, consumption_uncertain=False, checkpoints={})
        run.write_json(self.directory / "config.json", self.config)
        run.write_json(self.directory / "state.json", value)
        return value

    def test_checkpoint_publication_failure_keeps_previous_generation(self):
        model = FakeModel()
        first = train.publish_checkpoint(self.directory, model, self.config, {})
        original = run.read_json(self.directory / "checkpoint.json")
        real_write = train.write_json
        def fail_metadata(path, value):
            if path.name == "metadata.json":
                raise OSError("injected metadata write failure")
            real_write(path, value)
        with patch.object(train, "write_json", side_effect=fail_metadata):
            with self.assertRaises(OSError):
                train.publish_checkpoint(self.directory, model, self.config, {})
        self.assertEqual(run.read_json(self.directory / "checkpoint.json"), original)
        self.assertEqual(train.valid_checkpoint(self.directory, self.config)[0].name, first)

    def test_fallback_keeps_previous_valid_generation(self):
        model = FakeModel()
        first = train.publish_checkpoint(self.directory, model, self.config, {})
        second = train.publish_checkpoint(self.directory, model, self.config, {})
        (self.directory / "checkpoints" / second / "policy.zip").write_bytes(b"corrupt")
        self.assertEqual(train.valid_checkpoint(self.directory, self.config)[0].name, first)
        train.publish_checkpoint(self.directory, model, self.config, {})
        self.assertEqual(run.read_json(self.directory / "checkpoint.json")["previous"], first)

    def test_schedule_mismatch_rejects_restore(self):
        generation = train.publish_checkpoint(self.directory, FakeModel(), self.config, {})
        path = self.directory / "checkpoints" / generation / "metadata.json"
        for key, value in (("total_timesteps", 3072), ("progress_remaining", 1.0)):
            metadata = run.read_json(path)
            metadata["inherited"]["schedule"][key] = value
            run.write_json(path, metadata)
            with self.assertRaisesRegex(RuntimeError, "horizon/progress"):
                train.valid_checkpoint(self.directory, self.config)

    def test_actual_installed_sb3_setup_preserves_original_horizon(self):
        model = FakeModel()
        model.ep_info_buffer = model.ep_success_buffer = []
        model.action_noise = None
        model._last_obs = np.zeros((1, 109))
        model._custom_logger = True
        model._init_callback = lambda callback, progress: callback
        original = train.snapshot(model)
        total, _ = BaseAlgorithm._setup_learn(model, 2048 - model.num_timesteps, reset_num_timesteps=False)
        self.assertEqual(total, 2048)
        self.assertEqual(train.snapshot(model), original)
        self.assertEqual(original["schedule"]["progress_remaining"], 0.5)
        self.assertAlmostEqual(original["schedule"]["learning_rate"], 0.0002)
        self.assertAlmostEqual(original["schedule"]["clip_range"], 0.15)
        self.assertAlmostEqual(original["schedule"]["clip_range_vf"], 0.2)

    def test_restore_callback_checks_schedule_values_before_sampling(self):
        model = FakeModel()
        model._last_episode_starts = np.array([True])
        context = SimpleNamespace(config=self.config, restored=train.snapshot(model), directory=self.directory, token="test", flush=lambda: None)
        callback = train.AccountingCallback(context)
        callback.model = model
        callback._on_training_start()
        self.assertTrue(run.read_json(self.directory / "restore-test.json")["passed"])
        model.clip_range = lambda progress: 0.7
        with self.assertRaisesRegex(RuntimeError, "schedule"):
            callback._on_training_start()

    def test_duplicate_worker_rejected(self):
        self.state()
        with patch.object(run, "run_path", return_value=self.directory), patch.object(run, "worker_alive", return_value=True):
            with self.assertRaisesRegex(RuntimeError, "Duplicate"):
                run.resume("same")

    def test_duplicate_start_rejected_without_launch(self):
        (self.directory / "same").mkdir()
        with patch.object(run, "RUNS", self.directory), patch.object(run, "launch") as launch:
            with self.assertRaises(FileExistsError):
                run.start(self.config, "same")
            launch.assert_not_called()

    def test_exhausted_actions_and_time_reject_without_launch(self):
        for key, amount in (("attempted_actions", 2048), ("active_seconds", 120.0)):
            state = self.state()
            state["status"] = "stopped"
            state["consumed"][key] = amount
            run.write_json(self.directory / "state.json", state)
            with patch.object(run, "run_path", return_value=self.directory), patch.object(run, "launch") as launch:
                with self.assertRaisesRegex(RuntimeError, "exhausted"):
                    run.resume("same")
                launch.assert_not_called()

    def test_interruption_charges_outstanding_reservation_once(self):
        state = self.state()
        state["reservation"] = dict(attempted_actions=256, attempted_physics_steps=5120, active_seconds=110.0)
        run.write_json(self.directory / "state.json", state)
        charged = run.reconcile(self.directory)
        self.assertEqual(charged["consumed"]["attempted_actions"], 1280)
        self.assertEqual(charged["consumed"]["active_seconds"], 120.0)
        self.assertTrue(charged["consumption_uncertain"])
        self.assertEqual(run.reconcile(self.directory), charged)
        with patch.object(run, "run_path", return_value=self.directory):
            with self.assertRaisesRegex(RuntimeError, "uncertain"):
                run.resume("same")

    def test_launch_identity_failure_retains_cost_and_reaps_exact_process(self):
        state = self.state()
        process = SimpleNamespace(pid=123, terminate=unittest.mock.Mock(), wait=unittest.mock.Mock())
        real_write = run.write_json
        def fail_identity(path, value):
            if path.name == "launch.json":
                raise OSError("injected identity publication failure")
            real_write(path, value)
        with patch.object(run.subprocess, "Popen", return_value=process) as spawn, patch.object(run, "process_birth", return_value=9), patch.object(run, "write_json", side_effect=fail_identity):
            with self.assertRaises(OSError):
                run.launch(self.directory, state, run.PYTHON)
        process.terminate.assert_called_once()
        process.wait.assert_called_once()
        charged = run.read_json(self.directory / "state.json")
        self.assertEqual(charged["consumed"]["active_seconds"], 120.0)
        self.assertTrue(charged["consumption_uncertain"])
        self.assertEqual(charged["status"], "interrupted")
        self.assertEqual(spawn.call_args.kwargs["env"]["OMP_NUM_THREADS"], "1")
        self.assertTrue(set(spawn.call_args.kwargs["env"]) <= {"SystemRoot", "WINDIR", "PATH", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "COMSPEC", "PATHEXT", "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"})

    def test_direct_does_not_load_reference(self):
        with patch("tools.rl.env.np.load", side_effect=AssertionError("reference must not be read")):
            env = TensionEnv(self.config)
        self.assertIsNone(env.reference)
        env.close()

    def test_residual_requires_reference(self):
        self.config["mode"] = "residual"
        with self.assertRaisesRegex(ValueError, "reference"):
            run.resolve_config(self.config)

    def test_reward_cannot_change_acceptance(self):
        model = SimpleNamespace(predict=lambda observation, deterministic: (np.zeros(6), None))
        task = copy.deepcopy(self.config["task"])
        _, original = checks.run_episode(model, FakeEnv(), 17, task)
        self.config["reward"]["position"] = 1e9
        _, changed = checks.run_episode(model, FakeEnv(), 17, task)
        self.assertEqual(original, changed)
        self.assertTrue(changed["passed"])

    def test_failed_evaluation_keeps_only_valid_prefix(self):
        model = SimpleNamespace(predict=lambda observation, deterministic: (np.zeros(6), None))
        for env in (FakeEnv(fail=True), FakeEnv(surrogate=True)):
            samples, metrics = checks.run_episode(model, env, 17, self.config["task"])
            self.assertFalse(metrics["complete"])
            self.assertFalse(metrics["passed"])
            self.assertIsNone(metrics["terminal_position_error_m"])
            checks.write_trajectory(self.directory / "trajectory.csv", samples, self.config["task"]["tendon_order"])
            self.assertEqual(len((self.directory / "trajectory.csv").read_text().splitlines()), 2)

    def test_partial_budget_pre_action_guard_never_grants_extra(self):
        self.state()
        context = train.WorkerContext(self.directory, "dead", train.time.perf_counter())
        context.env = FakeEnv()
        context.env.counts["attempted_actions"] = 1024
        with self.assertRaisesRegex(train.ControlledStop, "action_budget"):
            context.guard()

    def test_sb3_learn_optimizes_final_batch_and_preserves_resume_horizon(self):
        model = FakeModel(0)
        model._n_updates = model.runtime_rollouts = 0
        self.simulated_learn_setup(model)
        spent = [0]
        stop_at = [1024]
        def collect(env, callback, buffer, n_rollout_steps):
            for _ in range(n_rollout_steps):
                if spent[0] >= 2048:
                    raise train.ControlledStop("shared action budget")
                spent[0] += 1
                model.num_timesteps += 1
            return True
        def optimize():
            model.runtime_rollouts += 1
            model._n_updates += 10
            if model.num_timesteps == stop_at[0]:
                raise train.ControlledStop("user stop at completed boundary")
        model.collect_rollouts, model.train = collect, optimize
        with self.assertRaisesRegex(train.ControlledStop, "user stop"):
            OnPolicyAlgorithm.learn(model, 2048, reset_num_timesteps=False, log_interval=None)
        self.assertEqual((model.num_timesteps, model.runtime_rollouts, model._n_updates), (1024, 4, 40))
        self.assertEqual(model._current_progress_remaining, 0.5)
        stop_at[0] = None
        OnPolicyAlgorithm.learn(model, 2048 - model.num_timesteps, reset_num_timesteps=False, log_interval=None)
        self.assertEqual((spent[0], model.num_timesteps, model.runtime_rollouts, model._n_updates), (2048, 2048, 8, 80))
        self.assertEqual((model._total_timesteps, model._current_progress_remaining), (2048, 0.0))

    @staticmethod
    def simulated_learn_setup(model):
        model.ep_info_buffer = model.ep_success_buffer = []
        model.action_noise = None
        model._last_obs = np.zeros((1, 109))
        model._custom_logger = True
        callback = SimpleNamespace(on_training_start=lambda *args: None, on_training_end=lambda: None)
        model._init_callback = lambda *args: callback
        model._setup_learn = lambda *args: BaseAlgorithm._setup_learn(model, *args)
        model._update_current_progress_remaining = lambda *args: BaseAlgorithm._update_current_progress_remaining(model, *args)
        model.env, model.rollout_buffer, model.n_steps = object(), object(), 256

    def test_spent_work_ahead_of_checkpoint_limits_inherited_learning(self):
        model = FakeModel(768)
        self.simulated_learn_setup(model)
        spent = [1024]
        def collect(env, callback, buffer, n_rollout_steps):
            for _ in range(n_rollout_steps):
                if spent[0] >= 2048:
                    raise train.ControlledStop("shared action budget")
                spent[0] += 1
                model.num_timesteps += 1
            return True
        model.collect_rollouts = collect
        model.train = lambda: None
        with self.assertRaisesRegex(train.ControlledStop, "shared action budget"):
            OnPolicyAlgorithm.learn(model, 2048 - model.num_timesteps, reset_num_timesteps=False, log_interval=None)
        self.assertEqual(spent[0], 2048)
        self.assertEqual(model.num_timesteps, 1792)
        self.assertEqual((model._total_timesteps, model._current_progress_remaining), (2048, 0.125))

    def test_time_cap_prevents_optimization_even_if_expected_counts_are_short(self):
        self.state()
        context = train.WorkerContext(self.directory, "dead", train.time.perf_counter() - 120)
        with self.assertRaisesRegex(train.ControlledStop, "active_time_budget"):
            context.before_optimization()

    def test_diagnose_default_does_not_create_environment(self):
        path = self.directory / "capture.npz"
        np.savez(path, pre_step_state=np.zeros(2))
        with patch.object(checks, "TensionEnv", side_effect=AssertionError("no replay requested")):
            result = checks.diagnose(path)
        self.assertFalse(result["replay_requested"])

    def test_replay_uses_own_recorded_run_numerical_configuration(self):
        directory = self.directory / "runs/rl/case"
        directory.mkdir(parents=True)
        self.config["physics"] = dict(integrator="implicit", timestep_s=0.00025)
        run.write_json(directory / "config.json", self.config)
        with patch.object(checks, "__file__", str(self.directory / "tools/rl/checks.py")):
            selected = checks.replay_config(directory / "failures/worker/failure.npz")
        self.assertEqual(selected["physics"], self.config["physics"])

    def test_replay_without_recorded_numerical_configuration_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "numerical settings are unknown"):
            checks.replay_config(self.directory / "unknown.npz")

    def test_archived_failure_configuration_matches_the_recorded_replay(self):
        root = Path(run.__file__).resolve().parents[2]
        selected = checks.replay_config(root / "evidence/rl_pilot_20261013/direct_capture.npz")
        self.assertEqual(selected["physics"], dict(integrator="implicitfast", timestep_s=0.0005))


if __name__ == "__main__":
    unittest.main()
