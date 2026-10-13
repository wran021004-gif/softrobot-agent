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


class TensionEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, mode, source_root=DEFAULT_SOURCE_ROOT, residual_scale=RESIDUAL_SCALE):
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
            physics_dt_s=PHYSICS_DT, control_dt_s=CONTROL_DT, substeps=SUBSTEPS,
            horizon=HORIZON, holding_steps=HOLD_STEPS, max_tension_n=MAX_TENSION,
            position_scale_m=POSITION_SCALE, speed_scale_m_s=SPEED_SCALE, reward=REWARD,
            observation=["qpos_rad (XML order)", "qvel_rad_s (XML order)",
                         "(target-tip)/0.01", "world_tip_velocity/0.02",
                         "previous_applied_tension/8", "control_step/35"],
            action="direct: 4*(a+1); residual: clip(reference[k]+residual_scale_n*a,0,8)",
            termination="terminated at action 35; never truncated",
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

    def step(self, action):
        if self.k >= HORIZON:
            raise RuntimeError("Call reset before stepping a new episode")
        self.command, self.clipped = self.map_action(action)
        previous = self.previous_tension.copy()
        self.data.ctrl[self.actuators] = self.command  # positive command already pulls
        mujoco.mj_forward(self.model, self.data)
        for _ in range(SUBSTEPS):
            before = self.data.time
            mujoco.mj_step(self.model, self.data)
            if self.data.time <= before or any(
                    self.data.warning[w].number for w in (
                        mujoco.mjtWarning.mjWARN_BADQPOS, mujoco.mjtWarning.mjWARN_BADQVEL,
                        mujoco.mjtWarning.mjWARN_BADQACC)):
                raise RuntimeError("MuJoCo numerical failure")
        self.previous_tension = -self.data.actuator_force[self.actuators].copy()
        self.k += 1
        mujoco.mj_forward(self.model, self.data)
        observation, info = self._observe()
        if not np.isfinite(observation).all():
            raise RuntimeError("Nonfinite MuJoCo observation")
        reward = -REWARD["position"] * (info["position_error_m"] / POSITION_SCALE) ** 2
        if self.k in HOLD_STEPS:
            reward -= REWARD["holding_speed"] * (info["speed_m_s"] / SPEED_SCALE) ** 2
        reward -= REWARD["smoothness"] * np.mean(
            ((self.previous_tension - previous) / MAX_TENSION) ** 2)
        return observation, float(reward), self.k == HORIZON, False, info
