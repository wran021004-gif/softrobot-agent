"""Derived provenance view of existing authoritative inputs; never supplies values."""


def parameter_provenance(design, ir, task, environment, simulator, settings, command=None):
    rows = {}
    def add(name, value, unit, category, source, status):
        rows[name] = dict(value=value, unit=unit, category=category, source=source, scientific_status=status)
    for name, unit in (
        ('joint_stiffness_nm_per_rad', 'N m/rad'), ('joint_damping_nm_s_per_rad', 'N m s/rad'),
        ('body_density_kg_m3', 'kg/m^3'), ('tendon_servo_kp_n_per_m', 'N/m'), ('tendon_force_limit_n', 'N'),
    ):
        add(name, getattr(ir.mechanics, name), unit,
            'ACTUATOR_MODEL' if name.startswith('tendon_') else 'PHYSICS_MODEL',
            'physics.yaml <- RobotIR.mechanics <- physics_contracts/legacy_v1_surrogate.yaml; ' + ir.mechanics.provenance,
            'legacy_v1_surrogate; not validated')
    for name, value in design.model_dump(mode='json').items():
        add('design.' + name, value, 'm' if name.endswith('_m') else '1', 'ROBOT_DESIGN',
            'design_input.yaml (DesignSpec)', 'design input; not validated operating range')
    add('segment_length_m', ir.section.segment_length_m, 'm', 'ROBOT_DESIGN',
        'RobotIR-derived: length / segments; segmented_mujoco_mapping_v1.md', 'approved geometric mapping')
    add('base_position_m', list(ir.base_position_m), 'm', 'ROBOT_DESIGN',
        'robot_ir.yaml; coordinate_frames.md', 'approved frame convention')
    add('tendon_routes', [r.model_dump(mode='json') for r in ir.tendon_routes], 'angle rad; offset m',
        'ROBOT_DESIGN', 'RobotIR-derived from DesignSpec; tendon_length_mapping_v1.md', 'approved geometric mapping')
    add('gravity_m_s2', list(environment.gravity_m_s2), 'm/s^2', 'ENVIRONMENT',
        'environment.yaml; ' + environment.gravity_source, 'frozen benchmark fact')
    add('environment_objects', [o.model_dump(mode='json') for o in environment.objects], 'SI; masks dimensionless',
        'ENVIRONMENT', 'environment.yaml (frozen package)', 'frozen benchmark fact')
    add('target_m', task.target_m, 'm', 'TASK', 'task.yaml', 'frozen benchmark fact')
    add('position_error_max_m', task.position_error_max_m, 'm', 'TASK', 'task.yaml; metrics/reach.py', 'frozen canonical threshold')
    add('timestep_s', simulator.timestep_s, 's', 'SIMULATOR_NUMERICAL',
        'simulator.yaml; ' + simulator.provenance, 'simulator numerical choice')
    add('steps', settings.steps, '1', 'RUN_SETTING', 'run_settings.yaml; ' + settings.provenance, 'legacy run choice')
    add('duration_s', settings.steps * simulator.timestep_s, 's', 'RUN_SETTING',
        'run_settings.yaml steps * simulator.yaml timestep_s', 'derived run duration; not settling-time validation')
    add('random_seed', settings.random_seed, '1', 'RUN_SETTING', 'run_settings.yaml', 'recorded; no random sampling')
    add('tendon_target_lengths_m', list(command.tendon_target_lengths_m) if command else None, 'm', 'CONTROLLER',
        'tendon_command.json <- model_result.json; ordered tendon_length_mapping_v1.md',
        'M1 kinematic command; open-loop hold' if command else 'unavailable: model command not yet produced')
    if environment.truth_status == 'NON_CANONICAL_DEVELOPMENT_ONLY':
        for key in ('gravity_m_s2', 'environment_objects', 'target_m', 'position_error_max_m'):
            rows[key]['scientific_status'] = environment.truth_status
            rows[key]['source'] = 'environment.yaml' if rows[key]['category'] == 'ENVIRONMENT' else 'task.yaml'
    return rows
