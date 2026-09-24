"""Trace one RobotIR design into the saved GVS and serial MuJoCo physics at q0."""
import json
from pathlib import Path
import sys

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from extensions.tendon_family.compiler import quat, rx  # noqa: E402
from extensions.tendon_family.contracts import GVSModelParameters, ResolvedGVSBasis  # noqa: E402
from extensions.tendon_family.gvs import _mass_descriptors, _observe_mass, _topology  # noqa: E402
from extensions.tendon_family.gvs_projection import discretization_jacobian, project  # noqa: E402
from extensions.tendon_family.sections import at, properties  # noqa: E402
from tools.state_io import atomic_json, digest  # noqa: E402

HERE = Path(__file__).resolve().parent
STAGE37 = ROOT / 'runs/stage37_gvs_backend_consistency_20260924/gvs_backend_consistency.json'
STAGE38 = ROOT / 'runs/stage38_physics_alignment_20260924/physics_alignment.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def a(value):
    return np.asarray(value, dtype=float)


def norm(value):
    return float(np.linalg.norm(value))


def grouped_mass(entries):
    """Mass, COM, and inertia about the combined COM in world axes."""
    mass = sum(row['mass_kg'] for row in entries)
    com = sum((row['mass_kg'] * row['com_world_m'] for row in entries), np.zeros(3)) / mass
    inertia = np.zeros((3, 3))
    for row in entries:
        offset = row['com_world_m'] - com
        inertia += row['inertia_world_kg_m2'] + row['mass_kg'] * (
            np.dot(offset, offset) * np.eye(3) - np.outer(offset, offset))
    return dict(mass_kg=float(mass), com_world_m=com.tolist(), inertia_com_world_kg_m2=inertia.tolist())


def main():
    old, alignment = read(STAGE37), read(STAGE38)
    source = ROOT / old['source']
    route = read(ROOT / 'runs/stage35_case_b_retry_softagent_20260924/inputs/route.json')
    design = route['robot']['structure']['data']
    physics = read(source / 'resolved_physics.json')
    scene = read(source / 'experiment_scene.json')
    compiled = read(source / 'compiled_physics.json')
    basis = ResolvedGVSBasis.model_validate(old['identities']['resolved_basis'])
    parameters = GVSModelParameters.model_validate({'basis': basis.specification})
    q0, u0 = a(old['baseline']['q0']), a(old['baseline']['u0'])
    mapping = discretization_jacobian(physics, basis)
    qcell = mapping @ q0
    assert digest(route['robot']) == old['identities']['robot'] == alignment['reference_state']['robot_identity']
    assert physics['identity'] == old['identities']['physics'] == alignment['reference_state']['physics_identity']
    assert physics['discretization_identity'] == alignment['reference_state']['backend_discretization_identity']
    assert digest(basis.model_dump(mode='json')) == alignment['reference_state']['basis_identity']
    assert np.allclose(qcell, old['baseline']['q_cell_rad'], atol=1e-14)
    assert np.allclose(project(physics, basis, qcell, np.zeros_like(qcell))['q_gvs'], q0, atol=1e-12)

    model = mujoco.MjModel.from_xml_path(str(source / 'robot.xml'))
    data = mujoco.MjData(model)
    qi, vi = (np.asarray(compiled[key], dtype=int) for key in ('qpos_indices', 'qvel_indices'))
    aids = np.asarray(compiled['direct_tension_ids'], dtype=int)
    data.qpos[qi], data.qvel[vi], data.ctrl[aids] = qcell, 0, u0
    mujoco.mj_forward(model, data)
    mount_p, mount_R, gravity_world = (a(scene[key]) for key in ('mount_position', 'mount_rotation', 'gravity'))
    gravity_base = mount_R.T @ gravity_world

    topology = _topology(design)
    descriptors = _mass_descriptors(topology, parameters.quadrature_points_per_segment, parameters.basis)
    observations = _observe_mass(topology, q0, parameters.integration_steps_per_segment, descriptors, parameters.basis)
    gvs_rows = []
    for descriptor, (position, rotation) in zip(descriptors, observations):
        world_R = mount_R @ rotation
        gvs_rows.append(dict(component=descriptor['component'], kind=descriptor['kind'],
                             s=descriptor.get('s'), mass_kg=descriptor['mass'],
                             com_world_m=mount_p + mount_R @ position,
                             inertia_world_kg_m2=world_R @ descriptor['inertia'] @ world_R.T,
                             gravity_generalized=np.zeros(len(q0))))
    # Match the production GVS finite-difference kinematics, grouping each
    # quadrature sample before comparing with MuJoCo's body COM Jacobians.
    for coordinate in range(len(q0)):
        delta = np.zeros_like(q0)
        delta[coordinate] = parameters.finite_difference_step
        plus = _observe_mass(topology, q0 + delta, parameters.integration_steps_per_segment,
                             descriptors, parameters.basis)
        minus = _observe_mass(topology, q0 - delta, parameters.integration_steps_per_segment,
                              descriptors, parameters.basis)
        for row, descriptor, (p_plus, _), (p_minus, _) in zip(gvs_rows, descriptors, plus, minus):
            derivative = (p_plus - p_minus) / (2 * parameters.finite_difference_step)
            row['gravity_generalized'][coordinate] = descriptor['mass'] * np.dot(derivative, gravity_base)

    backend_rows = []
    xml_mass_max_error = xml_com_max_error = xml_inertia_max_error = 0.0
    for part in physics['parts']:
        body_id = model.body(part['entity']).id
        local_inertia = a(part['inertia_com_local_kg_m2'])
        inertial_R = quat(model.body_iquat[body_id])
        xml_inertia = inertial_R @ np.diag(model.body_inertia[body_id]) @ inertial_R.T
        xml_mass_max_error = max(xml_mass_max_error, abs(model.body_mass[body_id] - part['mass_kg']))
        xml_com_max_error = max(xml_com_max_error, norm(model.body_ipos[body_id] - part['com_local_m']))
        xml_inertia_max_error = max(xml_inertia_max_error, norm(xml_inertia - local_inertia))
        jac = np.zeros((3, model.nv))
        jac_r = np.zeros_like(jac)
        mujoco.mj_jacBodyCom(model, data, jac, jac_r, body_id)
        body_R = data.xmat[body_id].reshape(3, 3)
        backend_rows.append(dict(component=part['component'], entity=part['entity'],
                                 mass_kg=float(model.body_mass[body_id]),
                                 com_world_m=data.xipos[body_id].copy(),
                                 inertia_world_kg_m2=body_R @ local_inertia @ body_R.T,
                                 gravity_generalized=mapping.T @ jac[:, vi].T @
                                     (model.body_mass[body_id] * gravity_world)))
    assert xml_mass_max_error < 1e-13 and xml_com_max_error < 1e-13 and xml_inertia_max_error < 1e-12

    components = [entry['id'] for entry in design['components']]
    comparison = {}
    gvs_gravity = np.zeros(len(q0))
    backend_gravity = np.zeros(len(q0))
    for name in components:
        g_rows = [row for row in gvs_rows if row['component'] == name]
        b_rows = [row for row in backend_rows if row['component'] == name]
        g_mass, b_mass = grouped_mass(g_rows), grouped_mass(b_rows)
        g_force = sum((row['gravity_generalized'] for row in g_rows), np.zeros(len(q0)))
        b_force = sum((row['gravity_generalized'] for row in b_rows), np.zeros(len(q0)))
        gvs_gravity += g_force
        backend_gravity += b_force
        comparison[name] = dict(kind=next(entry['kind'] for entry in design['components'] if entry['id'] == name),
            gvs=g_mass, backend=b_mass,
            mass_difference_kg=b_mass['mass_kg']-g_mass['mass_kg'],
            com_difference_world_m=(a(b_mass['com_world_m'])-a(g_mass['com_world_m'])).tolist(),
            com_distance_m=norm(a(b_mass['com_world_m'])-a(g_mass['com_world_m'])),
            inertia_difference_frobenius_kg_m2=norm(a(b_mass['inertia_com_world_kg_m2'])-a(g_mass['inertia_com_world_kg_m2'])),
            inertia_relative_difference=norm(a(b_mass['inertia_com_world_kg_m2'])-a(g_mass['inertia_com_world_kg_m2'])) /
                norm(a(g_mass['inertia_com_world_kg_m2'])),
            gravity_gvs=g_force.tolist(), gravity_backend=b_force.tolist(),
            gravity_difference=(b_force-g_force).tolist(), gravity_difference_norm=norm(b_force-g_force))
    # Finite-difference GVS terms should reproduce the saved exact CasADi term;
    # the independent per-body MuJoCo Jacobian sum must reproduce qfrc_bias.
    exact_gvs = a(alignment['terms']['gravity']['gvs'])
    exact_backend = a(alignment['terms']['gravity']['backend'])
    gvs_error = norm(gvs_gravity-exact_gvs)
    backend_error = norm(backend_gravity-exact_backend)
    assert gvs_error < 2e-7 and backend_error < 1e-12
    gravity_difference = backend_gravity-gvs_gravity
    coordinate_rows = [dict(coordinate=name, segment=name.split('.')[0],
                            gvs=float(gvs_gravity[i]), backend=float(backend_gravity[i]),
                            difference=float(gravity_difference[i]))
                       for i, name in enumerate(old['baseline']['coordinate_order'])]

    # Flexible RobotIR stores material and section fields; its mass, COM and
    # inertia are derived quantities. Preserve the source stations and the
    # actual section samples used by each generator.
    flexible = {}
    for component in design['components']:
        if component['kind'] != 'flexible_segment':
            continue
        name = component['id']
        cells = physics['entity_map'][name]['bodies']
        part_rows = []
        for cell, part_id in enumerate(cells):
            part = physics['parts'][part_id]
            section = part['section_properties']
            sampled = properties(at(topology[1][name], (cell+.5)/len(cells)))
            assert np.allclose(section['area_m2'], sampled['area_m2'], atol=1e-15)
            assert np.allclose(section['bending_area_m4'], sampled['bending_area_m4'], atol=1e-15)
            ds = part['length_m']
            phi = part['section_axis_rad']
            principal = rx(phi)[1:, 1:].T @ a(section['bending_area_m4']) @ rx(phi)[1:, 1:]
            predicted = np.diag(principal) * component['physics']['young_pa'] / ds
            measured = model.jnt_stiffness[[model.joint(physics['dofs'][index]).id for index in part['dofs']]]
            assert np.allclose(predicted, part['stiffness_nm_rad'], atol=1e-12)
            assert np.allclose(measured, predicted, atol=1e-12)
            part_rows.append(dict(cell=cell, normalized_center=(cell+.5)/len(cells), length_m=ds,
                area_m2=section['area_m2'], centroid_yz_m=section['centroid_yz_m'],
                bending_area_m4=section['bending_area_m4'],
                compiler_stiffness_nm_rad=part['stiffness_nm_rad'],
                xml_stiffness_nm_rad=measured.tolist(),
                body_mass_kg=part['mass_kg'], body_com_local_m=part['com_local_m'],
                body_inertia_com_local_kg_m2=part['inertia_com_local_kg_m2']))
        flexible[name] = dict(robot_ir=dict(length_m=component['length_m'],
            sections=component['sections'], interpolation=component['interpolation'],
            section_station_properties=[properties(station['section']) for station in component['sections']],
            physics=component['physics'], natural_curvature_rad_m=component['natural_curvature_rad_m'],
            mass_com_inertia='derived from density and section; not explicit flexible-segment RobotIR fields'),
            gvs_quadrature=[dict(s=row['s'], mass_kg=row['mass_kg'])
                for row in gvs_rows if row['component'] == name],
            backend_cells=part_rows,
            gvs_integrated_mass_kg=comparison[name]['gvs']['mass_kg'],
            backend_cell_mass_kg=comparison[name]['backend']['mass_kg'])

    rigid_source = {}
    for component in design['components']:
        if component['kind'] == 'flexible_segment':
            continue
        part = physics['parts'][physics['entity_map'][component['id']]['bodies'][0]]
        assert component['mass_kg'] == part['mass_kg']
        assert np.allclose(component['com_local_m'], part['com_local_m'], atol=1e-15)
        assert np.allclose(component['inertia_com_local_kg_m2'], part['inertia_com_local_kg_m2'], atol=1e-15)
        rigid_source[component['id']] = dict(mass_kg=component['mass_kg'],
            com_local_m=component['com_local_m'],
            inertia_com_local_kg_m2=component['inertia_com_local_kg_m2'])

    route_rows = []
    for tendon, backend_tendon, measured in zip(design['tendons'], physics['tendons'], alignment['per_tendon']):
        bindings = [point['physical_binding'] for point in backend_tendon['points']]
        assert tendon['id'] == backend_tendon['entity'] == measured['tendon']
        assert tendon['points'] == bindings
        route_rows.append(dict(tendon=tendon['id'], bindings_identical=True,
            roles=[point['role'] for point in tendon['points']],
            gvs_length_m=measured['gvs_length_m'], backend_length_m=measured['backend_length_m'],
            force_difference_norm=measured['generalized_force']['difference_norm']))

    result = dict(reference_state=dict(robot_identity=old['identities']['robot'],
        gvs_dynamic_system_identity=old['identities']['dynamic_system'],
        basis_identity=alignment['reference_state']['basis_identity'],
        backend_discretization_identity=physics['discretization_identity'],
        physics_identity=physics['identity'], q0=q0.tolist(), u0_n=u0.tolist(),
        gravity_world_m_s2=gravity_world.tolist(), tendon_order=old['baseline']['tendon_order']),
        source_paths=dict(robot_ir='runs/stage35_case_b_retry_softagent_20260924/inputs/route.json:robot.structure.data',
            gvs='extensions/tendon_family/gvs.py and gvs_casadi.py',
            backend='extensions/tendon_family/compiler.py -> mjcf.py -> saved robot.xml'),
        mass_com_inertia_by_component=comparison,
        flexible_segments=flexible,
        robot_ir_rigid_components=rigid_source,
        gravity_by_coordinate=coordinate_rows,
        gravity_reconstruction=dict(gvs_numeric_minus_casadi_norm=gvs_error,
            backend_body_jacobian_minus_qfrc_norm=backend_error,
            compiler_to_xml_mass_max_error_kg=xml_mass_max_error,
            compiler_to_xml_com_max_error_m=xml_com_max_error,
            compiler_to_xml_inertia_max_error_kg_m2=xml_inertia_max_error),
        stiffness=dict(**{key:alignment['stiffness_matrix'][key] for key in
            ('difference_frobenius_norm','relative_difference','difference_max_abs')},
            gvs_elastic_force_norm=alignment['terms']['elastic']['gvs_norm'],
            backend_elastic_force_norm=alignment['terms']['elastic']['backend_norm'],
            force_difference_norm=alignment['terms']['elastic']['difference_norm']),
        tendons=dict(routes=route_rows,
            total_generalized_force_difference_norm=alignment['terms']['tendon']['difference_norm'],
            maximum_length_jacobian_entry_difference=alignment['geometry']['tendon_jacobian_difference_max']),
        geometry=alignment['geometry'],
        classifications=dict(mass='MASS_MAPPING_MISMATCH',
            gravity='GRAVITY_MODEL_MISMATCH', stiffness='STIFFNESS_MAPPING_MISMATCH',
            tendon='TENDON_MAPPING_MISMATCH', geometry='GEOMETRY_INTEGRATION_MISMATCH',
            main_suspected_cause='multiple causes', confidence='medium'))
    atomic_json(HERE / 'physics_consistency.json', result)
    print(json.dumps(dict(component_com_gap_mm={k:1000*v['com_distance_m'] for k,v in comparison.items()},
        component_gravity_gap={k:v['gravity_difference_norm'] for k,v in comparison.items()},
        gravity_reconstruction=result['gravity_reconstruction'],
        classifications=result['classifications']), indent=2))


if __name__ == '__main__':
    main()
