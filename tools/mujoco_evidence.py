"""Read-only streaming observations; does not step, forward, or modify MuJoCo."""
import math
import mujoco


class ExecutionEvidence:
    def __init__(self, model, data, steps, initial_tip, controller):
        self.steps_requested = steps
        self.dt = float(model.opt.timestep)
        self.steps = 0
        self.initial_tip = initial_tip
        self.qpos_finite = True
        self.qvel_finite = True
        self.force_finite = True
        self.length_finite = True
        self.max_qpos = 0.0
        self.max_qvel = 0.0
        self.time_anomaly = False
        self.last_time = float(data.time)
        spec = getattr(controller, 'spec', None)
        self.command_source = spec.command_source if spec else None
        self.compiled = compiled_parameter_evidence(model)
        self.rows = []
        for i in range(model.nu):
            self.rows.append({
                'index': i, 'name': model.actuator(i).name,
                'tendon_index': int(model.actuator_trnid[i, 0]),
                'force_limited': bool(model.actuator_forcelimited[i]),
                'force_range_n': model.actuator_forcerange[i].tolist(),
                'active_samples': 0, 'lower_limit_samples': 0, 'upper_limit_samples': 0,
                'peak_abs_force_n': None, 'min_force_n': None, 'max_force_n': None,
                'command_min_m': None, 'command_max_m': None,
                'peak_abs_tracking_error_m': None,
            })

    def observe_step(self, model, data, commands):
        self.steps += 1
        pos = [float(v) for v in data.qpos]
        vel = [float(v) for v in data.qvel]
        self.qpos_finite &= all(math.isfinite(v) for v in pos)
        self.qvel_finite &= all(math.isfinite(v) for v in vel)
        self.max_qpos = max([self.max_qpos] + [abs(v) for v in pos if math.isfinite(v)])
        self.max_qvel = max([self.max_qvel] + [abs(v) for v in vel if math.isfinite(v)])
        now = float(data.time)
        self.time_anomaly |= not math.isclose(now - self.last_time, self.dt, rel_tol=1e-9, abs_tol=1e-12)
        self.last_time = now
        self.force_finite &= all(math.isfinite(float(v)) for v in data.actuator_force)
        self.length_finite &= all(math.isfinite(float(v)) for v in data.ten_length)
        if commands is None:
            return
        for row, command, force, length in zip(self.rows, commands, data.actuator_force, data.ten_length):
            row['active_samples'] += 1
            for key, value, fn in (('command_min_m', command, min), ('command_max_m', command, max),
                                   ('min_force_n', float(force), min), ('max_force_n', float(force), max),
                                   ('peak_abs_force_n', abs(float(force)), max),
                                   ('peak_abs_tracking_error_m', abs(float(length) - command), max)):
                if math.isfinite(value):
                    row[key] = value if row[key] is None else fn(row[key], value)
            lo, hi = row['force_range_n']
            if row['force_limited'] and math.isfinite(force):
                row['lower_limit_samples'] += int(force <= lo)
                row['upper_limit_samples'] += int(force >= hi)

    def summary(self, model, data):
        return {
            'evidence_version': '1', 'steps_requested': self.steps_requested,
            'steps_completed': self.steps, 'timestep_s': self.dt,
            'requested_duration_s': self.steps_requested * self.dt,
            'observed_time_s': float(data.time) if math.isfinite(data.time) else None,
            'tip_initial_position_m': self.initial_tip,
            'command_source': self.command_source,
            'compiled_parameter_evidence': self.compiled,
            'sampling': 'One observation per mj_step. Force/tendon length are solver-stage values; qpos/qvel are post-integration. Final lengths use final mj_forward.',
            'force_limit_comparison': 'Exact bound comparisons; upper zero is the no-push bound. A bound hit alone does not establish active clipping or cable slack.',
            'actuators': self.rows,
            'numerics': {
                'qpos_all_finite': self.qpos_finite, 'qvel_all_finite': self.qvel_finite,
                'actuator_force_all_finite': self.force_finite, 'tendon_length_all_finite': self.length_finite,
                'max_abs_qpos_rad': self.max_qpos, 'max_abs_qvel_rad_s': self.max_qvel,
                'time_advance_anomaly': self.time_anomaly,
                'warnings': {mujoco.mjtWarning(i).name: int(w.number) for i, w in enumerate(data.warning)},
                'qvel_anomaly_threshold': None,
                'stability_validated': False,
            },
        }


def compiled_parameter_evidence(model):
    """Expose resolved engine values/defaults without defining a new source of truth."""
    rows = {}
    def add(name, value, unit, category, source, status):
        rows[name] = dict(value=value.tolist() if hasattr(value, 'tolist') else value, unit=unit,
                          category=category, source=source, scientific_status=status)
    engine = f'loaded robot.xml + MuJoCo {mujoco.__version__} defaults'
    for name, unit in (('integrator', 'enum'), ('solver', 'enum'), ('iterations', '1'), ('tolerance', '1'),
                       ('ls_iterations', '1'), ('ls_tolerance', '1'), ('cone', 'enum'), ('jacobian', 'enum'),
                       ('impratio', '1'), ('noslip_iterations', '1'), ('noslip_tolerance', '1')):
        add('option.' + name, getattr(model.opt, name), unit, 'SIMULATOR_NUMERICAL', engine, 'engine numerical choice')
    for name, unit, category in (
        ('body_mass', 'kg', 'PHYSICS_MODEL'), ('body_inertia', 'kg m^2', 'PHYSICS_MODEL'),
        ('dof_armature', 'kg m^2', 'PHYSICS_MODEL'), ('dof_frictionloss', 'N m', 'PHYSICS_MODEL'),
        ('geom_friction', 'sliding 1; torsional m; rolling m', 'PHYSICS_MODEL'),
        ('geom_solref', 'engine contact solver parameter units', 'SIMULATOR_NUMERICAL'),
        ('geom_solimp', 'engine contact solver parameter units', 'SIMULATOR_NUMERICAL'),
        ('geom_condim', '1', 'PHYSICS_MODEL'), ('geom_contype', 'bitmask', 'PHYSICS_MODEL'),
        ('geom_conaffinity', 'bitmask', 'PHYSICS_MODEL'), ('geom_margin', 'm', 'PHYSICS_MODEL'),
        ('geom_gap', 'm', 'PHYSICS_MODEL'), ('jnt_axis', 'unit vector', 'ROBOT_DESIGN'),
        ('qpos_spring', 'rad', 'PHYSICS_MODEL'), ('tendon_stiffness', 'N/m', 'PHYSICS_MODEL'),
        ('tendon_damping', 'N s/m', 'PHYSICS_MODEL'), ('tendon_frictionloss', 'N', 'PHYSICS_MODEL'),
        ('actuator_gear', '1', 'ACTUATOR_MODEL'), ('actuator_dynprm', 'engine-defined', 'ACTUATOR_MODEL'),
        ('actuator_dyntype', 'enum', 'ACTUATOR_MODEL'),
    ):
        status = ('engine-derived capsule mass/inertia from surrogate density; not experimentally validated'
                  if name in ('body_mass', 'body_inertia') else 'legacy V1 representation or engine default; not physically validated')
        add(name, getattr(model, name), unit, category, engine, status)
    return rows
