"""Optional observability. No debug value is returned to a ToolResult or gate."""
import json
import math
import time
from pathlib import Path

LABEL = "DEBUG_ONLY / NON_CANONICAL"


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _model_values(obj):
    """Snapshot exposed model buffers and option structs that a GUI may edit."""
    import numpy as np
    result = []
    for name in dir(obj):
        if name.startswith('_'):
            continue
        value = getattr(obj, name)
        if isinstance(value, np.ndarray):
            result.append((obj, name, value.copy()))
        elif isinstance(value, (int, float)):
            result.append((obj, name, value))
        elif type(value).__name__.startswith(('MjOption', 'MjVisual', 'MjStatistic')):
            result.extend(_model_values(value))
    return result


class PassiveObserver:
    """Same executed objects at launch; discard GUI writes at each sync boundary.

    MuJoCo sync is bidirectional even with state_only=True. Preserve full MjData
    (including warm starts/work arrays) and model buffers/options around launch,
    sync and close. No mj_forward or mj_step is called on the executed data here.
    Passive viewer threads do not access the supplied structs outside sync.
    """
    def __init__(self, model, data, launcher=None):
        import mujoco
        self.model, self.data = model, data
        self.backup = mujoco.MjData(model)
        self.handle = None
        if launcher is None:
            from mujoco.viewer import launch_passive
            launcher = launch_passive
        self.guarded(lambda: setattr(self, 'handle', launcher(model, data,
            show_left_ui=False, show_right_ui=False)))

    def guarded(self, action):
        import mujoco
        import numpy as np
        snapshot = _model_values(self.model)
        mujoco.mj_copyData(self.backup, self.model, self.data)
        try:
            return action()
        finally:
            for obj, name, value in snapshot:
                current = getattr(obj, name)
                if isinstance(value, np.ndarray):
                    if not np.array_equal(current, value, equal_nan=True):
                        current[...] = value
                elif current != value:
                    setattr(obj, name, value)
            mujoco.mj_copyData(self.data, self.model, self.backup)

    def sync(self):
        if self.handle.is_running():
            self.guarded(lambda: self.handle.sync(state_only=True))

    def close(self):
        if self.handle is not None:
            self.guarded(self.handle.close)


class DebugObservability:
    def __init__(self, folder, *, debug=False, visualize=False, viewer_launcher=None):
        self.folder = Path(folder)
        self.debug, self.visualize = debug, visualize
        self.viewer_launcher = viewer_launcher
        self.viewer = None
        self.samples, self.errors = [], []
        self.dimensions = None

    def attempt(self, name, action):
        try:
            return action()
        except Exception as exc:
            self.errors.append({"operation": name, "exception": type(exc).__name__, "message": str(exc)})
            return None

    def start(self, model, data, task):
        import mujoco
        self.task = task
        self.dimensions = {key: int(getattr(model, key)) for key in ('nq', 'nv', 'ntendon', 'nu')}
        self.kinematics = mujoco.MjData(model) if self.debug else None
        if self.visualize:
            self.viewer = self.attempt('viewer_launch', lambda: PassiveObserver(model, data, self.viewer_launcher))
        self.wall_start, self.sim_start = time.monotonic(), float(data.time)
        self.next_sync = self.sim_start

    def observe(self, model, data, commands):
        if self.debug:
            self.attempt('trajectory_sample', lambda: self._sample(model, data, commands))
        if self.viewer is not None and data.time >= self.next_sync:
            self.attempt('viewer_sync', self.viewer.sync)
            self.next_sync = float(data.time) + 1 / 30
            # Only wall-clock pacing. Step count, timestep and simulation time stay fixed.
            delay = float(data.time) - self.sim_start - (time.monotonic() - self.wall_start)
            if delay > 0:
                time.sleep(min(delay, 1 / 30))

    def _sample(self, model, data, commands):
        import mujoco
        self.kinematics.qpos[:] = data.qpos
        mujoco.mj_kinematics(model, self.kinematics)
        tip = self.kinematics.site_xpos[model.site('tip_site').id].tolist()
        self.samples.append(dict(time_s=float(data.time), tip_position_m=tip,
            position_error_m=math.dist(tip, self.task.target_m),
            tendon_target_lengths_m=list(commands) if commands is not None else None,
            tendon_actual_lengths_m=data.ten_length.tolist(), actuator_force_n=data.actuator_force.tolist(),
            qpos=data.qpos.tolist(), qvel=data.qvel.tolist()))

    def plot_matlab(self, matlab, run_path, *, visible=False):
        self.attempt('matlab_plot', lambda: matlab.plot_saved_results(run_path, self.folder, visible=visible))

    def finish(self):
        if self.viewer is not None:
            self.attempt('viewer_close', self.viewer.close)
        if self.debug and self.dimensions is not None:
            self.attempt('trajectory_save', self._save_trajectory)
            if self.samples:
                self.attempt('trajectory_plots', self._plots)
        self.attempt('debug_status', lambda: _write(self.folder / 'status.json', {
            'labels': ['DEBUG_ONLY', 'NON_CANONICAL'], 'debug': self.debug, 'visualize': self.visualize,
            'sample_count': len(self.samples), 'errors': self.errors,
            'prohibited_uses': ['canonical_gate', 'optimizer_ranking', 'skill_admission', 'causal_attribution']}))

    def _save_trajectory(self):
        from schemas.debug_artifact import DebugTrajectory
        value = DebugTrajectory(**self.dimensions, samples=self.samples)
        _write(self.folder / 'trajectory.json', value.model_dump(mode='json'))

    def _plots(self):
        # Agg Figure API: no desktop, pyplot state, or MATLAB numerical dependency.
        import numpy as np
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        t = [s['time_s'] for s in self.samples]
        groups = [('tip_error.png', [('position_error_m', 'error (m)')]),
                  ('tip_xyz.png', [('tip_position_m', 'XYZ (m)')]),
                  ('tendon_tracking.png', [('tendon_actual_lengths_m', 'actual (m)'), ('tendon_target_lengths_m', 'target (m)')]),
                  ('actuator_force.png', [('actuator_force_n', 'force (N)')]),
                  ('qpos_qvel.png', [('qpos', 'qpos (rad)'), ('qvel', 'qvel (rad/s)')])]
        for filename, fields in groups:
            figure = Figure(figsize=(10, 6), layout='constrained')
            FigureCanvasAgg(figure)
            figure.suptitle(LABEL + '\n' + filename[:-4])
            axes = figure.subplots(len(fields), 1, squeeze=False)[:, 0]
            for axis, (key, label) in zip(axes, fields):
                values = [s[key] for s in self.samples]
                if all(v is not None for v in values):
                    matrix = np.asarray(values)
                    lines = axis.plot(t, matrix)
                    for i, line in enumerate(lines):
                        line.set_label(('XYZ'[i] if key == 'tip_position_m' else str(i)))
                    axis.legend(ncol=min(len(lines), 8), fontsize=7)
                axis.set(xlabel='time (s)', ylabel=label)
                axis.grid(alpha=.3)
            figure.savefig(self.folder / filename, metadata={'Description': LABEL})
