"""Lossless semantic projection of fields already recorded by the two executors."""
from schemas.platform import Signal, SignalSpec, BackendResult
from .contracts import SelectedSignal, EntityDiagnosticResult


def declarations(backend):
    state = 'sampled_state' if backend == 'matlab' else 'post_step'
    solver = 'sampled_state' if backend == 'matlab' else 'pre_step_solver'
    # Entity groups expand from the actual IR. These are templates, not fixed counts.
    items = [
        ('tip_m', 'tip_position', 'tip', 3, 'm', 'world', state, 'time_s'),
        ('qpos_rad', 'joint_position', 'joint', 1, 'rad', 'joint_local', state, 'time_s'),
        ('qvel_rad_s', 'joint_velocity', 'joint', 1, 'rad/s', 'joint_local', state, 'time_s'),
        ('command_m', 'tendon_command', 'tendon', 1, 'm', 'actuator', solver, 'solver_time_s'),
        ('solver_tendon_length_m', 'tendon_length', 'tendon', 1, 'm', 'actuator', solver, 'solver_time_s'),
        ('solver_actuator_force_n', 'actuator_force', 'tendon', 1, 'N', 'actuator', solver, 'solver_time_s'),
        ('solver_contact_count', 'contact_count', 'contact', 1, 'count', 'world', solver, 'solver_time_s'),
    ]
    if backend == 'matlab':
        items += [
            ('tendon_demand_n', 'tendon_demand', 'tendon', 1, 'N', 'actuator', solver, 'solver_time_s'),
            ('tendon_velocity_m_s', 'tendon_velocity', 'tendon', 1, 'm/s', 'actuator', solver, 'solver_time_s'),
            ('floor_gap_m', 'floor_gap', 'segment', 1, 'm', 'world', solver, 'solver_time_s'),
            ('normal_contact_approx_n', 'contact_normal_approx', 'segment', 1, 'N', 'world_z', solver, 'solver_time_s'),
        ]
        torques = [('qfrc_actuator', 'actuator_torque'), ('qfrc_spring', 'spring_torque'),
                   ('qfrc_damper', 'damping_torque'), ('qfrc_contact_approx', 'contact_torque_approx')]
    else:
        torques = [('solver_qfrc_actuator_nm', 'actuator_torque'), ('solver_qfrc_passive_nm', 'passive_torque'),
                   ('solver_qfrc_constraint_nm', 'constraint_torque')]
    items += [(field, name, 'joint', 1, 'N.m', 'joint_local', solver, 'solver_time_s') for field, name in torques]
    return [dict(field=f, name=n, entity_group=e, dimension=d, units=u, frame=fr, phase=p, time_field=t)
            for f, n, e, d, u, fr, p, t in items]


def entity_groups(backend, ir):
    return dict(joint=[f'joint_{i}_{a}' for i in range(ir.segments) for a in (('y',) if backend == 'matlab' else ('y', 'z'))],
                    tendon=[f'tendon_{r.index}' for r in ir.tendon_routes], segment=[f'segment_{i}' for i in range(ir.segments)])


def signal_spec(item, entity):
    return SignalSpec(name=item['name'], entity=entity, dimension=item['dimension'],
        units=item['units'], frame=item['frame'], phase=item['phase'])


def observation_specs(inp, reg):
    """Expand stable observations from the same definitions/IR as saved signals."""
    from tools.design_compiler import ensure_robot_ir
    ir = ensure_robot_ir(reg.parse(inp.robot.structure))
    backend = inp.policy.backend.extension_id.split('.')[-1]
    entities = entity_groups(backend, ir)
    specs = []
    for item in declarations(backend):
        for entity in entities.get(item['entity_group'], [item['entity_group']]):
            spec = signal_spec(item, entity)
            specs.append(spec)
            if spec.name == 'actuator_force':
                specs.append(spec.model_copy(update={'name': 'tendon_tension'}))
    # Sparse contact occurrences have no pre-execution stable entity identity.
    return specs


def from_rows(rows, backend, ir):
    entities = entity_groups(backend, ir)
    signals = []
    for item in declarations(backend):
        field, clock, group = item['field'], item['time_field'], item['entity_group']
        if not rows or not all(field in r and clock in r for r in rows):
            continue  # Missing is absent, never a manufactured zero.
        names = entities.get(group, [group])
        for i, entity in enumerate(names):
            if group in entities:
                if any(len(r[field]) != len(names) for r in rows):
                    raise ValueError('SAVED_SIGNAL_ENTITY_DIMENSION_MISMATCH: ' + field)
                values = [[r[field][i]] for r in rows]
            else:
                values = [r[field] if item['dimension'] > 1 else [r[field]] for r in rows]
            spec = signal_spec(item, entity)
            signals.append(Signal(spec=spec, times_s=[r[clock] for r in rows], values=values))
            if item['name'] == 'actuator_force':
                signals.append(Signal(spec=spec.model_copy(update={'name': 'tendon_tension'}),
                    times_s=[r[clock] for r in rows], values=[[-v[0]] for v in values]))
    # Contact points do not have stable identities across samples. Retain each
    # recorded occurrence independently; absence of a point is not zero force.
    if backend == 'mujoco':
        for i, row in enumerate(rows):
            for j, contact in enumerate(row.get('contacts', [])):
                entity = f'contact_sample_{i}_point_{j}'
                for field, name, dimension, units, frame in (
                    ('normal_force_n', 'contact_normal_force', 1, 'N', 'contact_local'),
                    ('tangent_force_n', 'contact_tangent_force', 2, 'N', 'contact_local'),
                    ('position_m', 'contact_position', 3, 'm', 'world'),
                    ('gap_m', 'contact_gap', 1, 'm', 'world')):
                    if field in contact:
                        value = contact[field] if dimension > 1 else [contact[field]]
                        signals.append(Signal(spec=SignalSpec(name=name, entity=entity, dimension=dimension,
                            units=units, frame=frame, phase='pre_step_solver'), times_s=[contact['time_s']], values=[value]))
    return signals


def select(signals, name, entity=None, phase=None):
    matches = [s for s in signals if s.spec.name == name and (entity is None or s.spec.entity == entity)
               and (phase is None or s.spec.phase == phase)]
    if len(matches) > 1:
        raise ValueError('SIGNAL_SELECTION_REQUIRED: specify entity and phase')
    return matches[0] if matches else None


def read_signal(ctx, args):
    result = BackendResult.model_validate(ctx.artifact(args.result))
    signal = select(result.signals, args.name, args.entity, args.phase)
    return SelectedSignal(source=args.result, status='available' if signal else 'missing_data', signal=signal)


def sample_exceeds(ctx, args):
    result = BackendResult.model_validate(ctx.artifact(args.result))
    signal = select(result.signals, args.signal, args.entity, args.phase)
    indices = []
    if signal is None or not signal.values:
        status = 'missing_data'
    elif signal.spec.units != args.units or signal.spec.dimension != 1:
        status = 'not_applicable'
    else:
        indices = [i for i, row in enumerate(signal.values) if row[0] > args.threshold]
        status = 'events_found' if indices else 'no_event'
    output = EntityDiagnosticResult(status=status, source=args.result, signal=args.signal,
        entity=signal.spec.entity if signal else args.entity, phase=signal.spec.phase if signal else args.phase,
        units=args.units, threshold=args.threshold, sample_indices=indices,
        observed=[signal.values[i] for i in indices] if signal else [])
    ctx.record('diagnosis', status, inputs=[args.result])
    return output
