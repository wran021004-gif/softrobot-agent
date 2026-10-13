"""Fixed fc1012 task: physical observations, direct or residual tension actions."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tarfile

import gymnasium as gym
import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_ROOT = Path(r"D:\softrobot-agent\.worktrees\mechanics-control-mainline")
EVIDENCE = ROOT / "evidence/fc1012_open_loop_20261013"
XML_ID = "60c5e069f76253e05d9b0aa2cd873abda87abecb84b6d0814c30f4e0052a88de"
EXECUTION_ID = "6380ef76518b4c24a6bf459942f72545"
TENDONS = ["near_t0", "near_t1", "near_t2", "far_t0", "far_t1", "far_t2"]
TARGET = np.array([0.29, 0.035, 0.19])
LENGTHS = [0.15758113296570092, 0.11241886703429908]
PHYSICS_DT, CONTROL_DT, SUBSTEPS, HORIZON = 0.0005, 0.01, 20, 35
HOLD_STEPS = list(range(30, 36))
MAX_TENSION, RESIDUAL_SCALE = 8.0, 8.0
POSITION_SCALE, SPEED_SCALE = 0.01, 0.02
REWARD = dict(position=1.0, holding_speed=1.0, smoothness=0.001)
FAILURE_PENALTY = -10000.0


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


STATE_SPEC = mujoco.mjtState.mjSTATE_INTEGRATION
WARNINGS = (mujoco.mjtWarning.mjWARN_BADQPOS, mujoco.mjtWarning.mjWARN_BADQVEL,
            mujoco.mjtWarning.mjWARN_BADQACC)


class NumericalFailure(RuntimeError):
    """A failed physical transition; never returned as a valid PPO sample."""


class TensionEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, mode, source_root=DEFAULT_SOURCE_ROOT, residual_scale=RESIDUAL_SCALE,
                 physics_dt=PHYSICS_DT, trace_dir=None, integrator="implicitfast", failure_mode="raise"):

        if mode not in ("residual", "direct"):
            raise ValueError("mode must be residual or direct")
        if not np.isfinite(residual_scale) or residual_scale <= 0:
            raise ValueError("residual_scale must be positive and finite")
        self.mode, self.residual_scale = mode, float(residual_scale)
        self.source_root = Path(source_root).resolve()
        self.saved = json.loads((EVIDENCE / "execution.json").read_text(encoding="utf-8"))
        with np.load(EVIDENCE / "references.npz", allow_pickle=False) as refs:
            self.reference = refs["saved_tensions_n"].copy()
        if (self.reference.shape != (HORIZON, 6) or not np.isfinite(self.reference).all()
                or np.any((self.reference < 0) | (self.reference > MAX_TENSION))):
            raise ValueError(f"Invalid saved_tensions_n in {EVIDENCE / 'references.npz'}")
        expected = dict(source_physical_execution=EXECUTION_ID, lengths_m=LENGTHS,
                        target_m=TARGET.tolist(), tendon_order=TENDONS,
                        timestep_s=PHYSICS_DT, control_period_s=CONTROL_DT,
                        command_intervals=HORIZON, duration_s=0.35)
        if any(self.saved[key] != value for key, value in expected.items()):
            raise ValueError("Committed execution metadata differs from the fixed task")
        xml, self.xml_source = load_xml(self.source_root)
        self.model = m = mujoco.MjModel.from_xml_string(xml)
        self.data = mujoco.MjData(m)
        self.actuators = [m.actuator(t + "_direct_tension").id for t in TENDONS]
        tendon_ids = [m.tendon(t).id for t in TENDONS]
        a = self.actuators
        if (m.opt.timestep != PHYSICS_DT or m.nu != 6 or m.nq != 48 or m.nv != 48
                or a != self.saved["actuator_ids"]
                or not np.all(m.actuator_trntype[a] == mujoco.mjtTrn.mjTRN_TENDON)
                or m.actuator_trnid[a, 0].tolist() != tendon_ids
                or not np.all(m.actuator_gainprm[a, 0] == -1)
                or not np.all(m.actuator_ctrlrange[a] == [0, 8])
                or not np.all(m.actuator_forcerange[a] == [-8, 0])):
            raise ValueError("Saved XML actuator mapping, dimensions or timing differs")
        if not np.isfinite(physics_dt) or physics_dt <= 0:
            raise ValueError("physics_dt must be positive and finite")
        self.substeps = round(CONTROL_DT / physics_dt)
        if physics_dt <= 0 or abs(self.substeps * physics_dt - CONTROL_DT) > 1e-12:
            raise ValueError("physics_dt must divide the control period")
        m.opt.timestep = physics_dt  # loaded model copy only
        m.opt.integrator = getattr(mujoco.mjtIntegrator, "mjINT_" + integrator.upper())
        self.integrator = integrator
        if failure_mode not in ("raise", "terminal"):
            raise ValueError("failure_mode must be raise or terminal")
        self.failure_mode = failure_mode
        self.trace_dir = Path(trace_dir) if trace_dir else None
        self.counts = dict(attempted_actions=0, completed_actions=0, attempted_physics_steps=0,
                           complete_episodes=0, failed_episodes=0)
        self.episode = 0
        self.failure = None
        self.site = m.site("tip_site").id
        self.jacobian = np.zeros((3, m.nv))
        self.action_space = gym.spaces.Box(-1.0, 1.0, (6,), dtype=np.float32)
        self.observation_space = gym.spaces.Box(
            -np.inf, np.inf, (m.nq + m.nv + 13,), dtype=np.float32)
        self.k = HORIZON  # reset is required before step

    def settings(self):
        return dict(
            mode=self.mode, residual_scale_n=self.residual_scale,
            target_m=TARGET.tolist(), lengths_m=LENGTHS, tendon_order=TENDONS,
            physics_dt_s=float(self.model.opt.timestep), control_dt_s=CONTROL_DT, substeps=self.substeps,
            integrator=self.integrator, numerical_version="pilot-v2-" + self.integrator + "-dt-" + str(self.model.opt.timestep),
            horizon=HORIZON, holding_steps=HOLD_STEPS, max_tension_n=MAX_TENSION,
            position_scale_m=POSITION_SCALE, speed_scale_m_s=SPEED_SCALE, reward=REWARD,
            observation=["qpos_rad (XML order)", "qvel_rad_s (XML order)",
                         "(target-tip)/0.01", "world_tip_velocity/0.02",
                         "previous_applied_tension/8", "control_step/35"],
            action="direct: 4*(a+1); residual: clip(reference[k]+residual_scale_n*a,0,8)",
            termination="terminated at action 35; numerical failure is an explicit absorbing training failure",
            failure_penalty=FAILURE_PENALTY,
            source_root=str(self.source_root), xml_source=self.xml_source, xml_id=XML_ID,
            execution_json=str(EVIDENCE / "execution.json"),
            reference_npz=str(EVIDENCE / "references.npz"))

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model, self.data)
        for field, address, destination in (
                ("qpos_rad", self.model.jnt_qposadr, self.data.qpos),
                ("qvel_rad_s", self.model.jnt_dofadr, self.data.qvel)):
            for name, value in self.saved["initializer"][field].items():
                destination[address[self.model.joint(name).id]] = value
        self.k = 0
        self.needs_reset = False
        self.episode += 1
        self.episode_records = []
        self.failure = None
        self.previous_tension = np.zeros(6)
        self.command = np.zeros(6)
        self.clipped = np.zeros(6, dtype=bool)
        mujoco.mj_forward(self.model, self.data)
        return self._observe()

    def map_action(self, action):
        action = np.asarray(action, dtype=np.float64)
        if action.shape != (6,) or not np.isfinite(action).all() or np.any(abs(action) > 1):
            raise ValueError("Expected six finite actions in [-1, 1]")
        raw = (4 * (action + 1) if self.mode == "direct"
               else self.reference[self.k] + self.residual_scale * action)
        tension = np.clip(raw, 0, MAX_TENSION)
        return tension, raw != tension

    def _observe(self):
        # step/reset synchronize kinematics before evaluating the world Jacobian.
        mujoco.mj_jacSite(self.model, self.data, self.jacobian, None, self.site)
        position = self.data.site_xpos[self.site].copy()
        velocity = self.jacobian @ self.data.qvel
        error = TARGET - position
        observation = np.concatenate((
            self.data.qpos, self.data.qvel, error / POSITION_SCALE,
            velocity / SPEED_SCALE, self.previous_tension / MAX_TENSION,
            [self.k / HORIZON])).astype(np.float32)
        info = dict(control_step=self.k, time_s=self.k * CONTROL_DT,
                    engine_time_s=float(self.data.time), tip_m=position,
                    tip_velocity_m_s=velocity, position_error_m=float(np.linalg.norm(error)),
                    speed_m_s=float(np.linalg.norm(velocity)),
                    applied_tension_n=self.previous_tension.copy(),
                    commanded_tension_n=self.command.copy(), clipped=self.clipped.copy(),
                    saturated=(self.command == 0) | (self.command == MAX_TENSION))
        return observation, info

    def get_state(self):
        state = np.empty(mujoco.mj_stateSize(self.model, STATE_SPEC))
        mujoco.mj_getState(self.model, self.data, state, STATE_SPEC)
        return state

    def fail(self, record, start_state, pre_step_state, substep, warnings):
        self.counts["failed_episodes"] += 1
        self.failure = dict(record, failed_substep=substep, warnings=warnings,
                            pre_step_time_s=float(pre_step_state[0]),
                            returned_engine_time_s=float(self.data.time),
                            state_spec=int(STATE_SPEC), counts=self.counts.copy())
        if self.trace_dir:
            self.trace_dir.mkdir(parents=True, exist_ok=True)
            prefix = self.trace_dir / f"failure_episode_{self.episode}"
            prefix.with_suffix(".json").write_text(
                json.dumps(self.failure, indent=2, allow_nan=False), encoding="utf-8")
            np.savez_compressed(prefix.with_suffix(".npz"),
                                interval_start_state=start_state, pre_step_state=pre_step_state,
                                actions=np.array([r["action"] for r in self.episode_records]),
                                tensions=np.array([r["tension_n"] for r in self.episode_records]))
            prefix.with_suffix(".jsonl").write_text(
                "\n".join(json.dumps(r, allow_nan=False) for r in self.episode_records) + "\n",
                encoding="utf-8")
        if self.failure_mode == "raise":
            raise NumericalFailure("MuJoCo numerical failure: " + ", ".join(warnings))
        # A terminal surrogate at the last valid boundary, never the engine's reset state.
        mujoco.mj_setState(self.model, self.data, start_state, STATE_SPEC)
        self.k = record["episode_action"] - 1
        self.previous_tension = np.array(record["tension_n"]) - np.array(record["delta_tension_n"])
        mujoco.mj_forward(self.model, self.data)
        observation, info = self._observe()
        if not np.isfinite(observation).all():
            raise NumericalFailure("No valid observation for failure terminal")
        self.needs_reset = True
        info.update(record, numerical_failure=True, valid_physical_transition=False,
                    counts=self.counts.copy(), failure=self.failure,
                    reward=FAILURE_PENALTY,
                    reward_terms=dict(position=0.0, holding_speed=0.0, smoothness=0.0,
                                      numerical_failure=FAILURE_PENALTY))
        return observation, FAILURE_PENALTY, True, False, info

    def step(self, action):
        if self.k >= HORIZON or self.needs_reset:
            raise RuntimeError("Call reset before stepping a new episode")
        self.command, self.clipped = self.map_action(action)
        self.counts["attempted_actions"] += 1
        previous = self.previous_tension.copy()
        start_state = self.get_state()
        _, before_info = self._observe()
        record = dict(episode_number=self.episode, cumulative_action=self.counts["attempted_actions"],
                      episode_action=self.k + 1, action=np.asarray(action).tolist(),
                      tension_n=self.command.tolist(), delta_tension_n=(self.command-previous).tolist(),
                      clipped=self.clipped.tolist(),
                      saturated=((self.command == 0) | (self.command == MAX_TENSION)).tolist(),
                      start_error_m=before_info["position_error_m"], start_speed_m_s=before_info["speed_m_s"])
        self.episode_records.append(record)
        self.data.ctrl[self.actuators] = self.command
        mujoco.mj_forward(self.model, self.data)
        for substep in range(1, self.substeps + 1):
            pre_step = self.get_state()  # capture BEFORE an engine warning can reset data
            self.counts["attempted_physics_steps"] += 1
            mujoco.mj_step(self.model, self.data)
            warnings = [w.name for w in WARNINGS if self.data.warning[w].number]
            if self.data.time <= pre_step[0]:
                warnings.append("engine_time_reset")
            if not all(np.isfinite(x).all() for x in (self.data.qpos, self.data.qvel, self.data.qacc)):
                warnings.append("nonfinite_state")
            if warnings:
                return self.fail(record, start_state, pre_step, substep, warnings)
        self.previous_tension = -self.data.actuator_force[self.actuators].copy()
        self.k += 1
        mujoco.mj_forward(self.model, self.data)
        observation, info = self._observe()
        if not np.isfinite(observation).all():
            return self.fail(record, start_state, pre_step, self.substeps, ["nonfinite_observation"])
        terms = dict(position=-REWARD["position"] * (info["position_error_m"] / POSITION_SCALE) ** 2,
                     holding_speed=(-REWARD["holding_speed"] * (info["speed_m_s"] / SPEED_SCALE) ** 2
                                    if self.k in HOLD_STEPS else 0.0),
                     smoothness=-REWARD["smoothness"] * float(np.mean(
                         ((self.previous_tension - previous) / MAX_TENSION) ** 2)))
        reward = float(sum(terms.values()))
        record.update(end_error_m=info["position_error_m"], end_speed_m_s=info["speed_m_s"],
                      reward_terms=terms, reward=reward)
        self.counts["completed_actions"] += 1
        self.counts["complete_episodes"] += int(self.k == HORIZON)
        info.update(record, numerical_failure=False, valid_physical_transition=True, counts=self.counts.copy())
        return observation, reward, self.k == HORIZON, False, info
