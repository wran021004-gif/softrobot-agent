"""Model-specific entity expansion and clocks shared by declarations and export."""
from schemas.platform import Signal, SignalSpec
from extensions.robot_domain.signals import declarations as legacy_declarations, from_rows, signal_spec


def kind(inp):
    return 'matlab' if inp.policy.backend.extension_id == 'backend.math_planar' else 'spatial'


def declarations(model):
    items = legacy_declarations('matlab' if model == 'matlab' else 'mujoco')
    if model != 'matlab':
        items = [s for s in items if s['name'] != 'constraint_torque']
        items += [dict(field='external_torque_nm', name='external_torque', entity_group='joint', dimension=1,
                       units='N.m', frame='joint_local', phase='pre_step_solver', time_field='solver_time_s')]
        if model == 'spatial':
            items += [dict(field=f, name=n, entity_group='segment', dimension=1, units=u,
                frame='world', phase='pre_step_solver', time_field='solver_time_s') for f,n,u in
                [('floor_gap_m','floor_gap','m'), ('normal_contact_approx_n','contact_normal_approx','N')]]
    return items


def observation_specs(inp, reg):
    from tools.design_compiler import ensure_robot_ir
    from extensions.robot_domain.signals import entity_groups
    ir = ensure_robot_ir(reg.parse(inp.robot.structure))
    model = kind(inp) if inp.policy.backend.extension_id != 'backend.scene_mujoco' else 'mujoco'
    entities = entity_groups('matlab' if model == 'matlab' else 'mujoco', ir)
    result = []
    for item in declarations(model):
        for entity in entities.get(item['entity_group'], [item['entity_group']]):
            spec = signal_spec(item, entity)
            result.append(spec)
            if spec.name == 'actuator_force':
                result.append(spec.model_copy(update={'name':'tendon_tension'}))
    return result


def export(rows, model, ir):
    # Reuse existing sign conventions; spatial models expand both axes.
    result = from_rows(rows, 'matlab' if model == 'matlab' else 'mujoco', ir)
    for item in declarations(model):
        if not rows or item['field'] not in rows[0]:
            continue
        from extensions.robot_domain.signals import entity_groups
        entities = entity_groups('matlab' if model == 'matlab' else 'mujoco', ir)
        for i, entity in enumerate(entities.get(item['entity_group'], [item['entity_group']])):
            spec = signal_spec(item, entity)
            if any(s.spec == spec for s in result):
                continue
            result.append(Signal(spec=spec, times_s=[r[item['time_field']] for r in rows],
                values=[[r[item['field']][i]] for r in rows]))
    return result
