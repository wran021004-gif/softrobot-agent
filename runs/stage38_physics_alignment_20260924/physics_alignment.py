"""Isolate physical force terms at the frozen Stage 3.7 GVS operating point."""
import json
from pathlib import Path
import sys

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from extensions.tendon_family.compiler import rx  # noqa: E402
from extensions.tendon_family.contracts import GVSModelParameters, ResolvedGVSBasis  # noqa: E402
from extensions.tendon_family.geometry import geometry  # noqa: E402
from extensions.tendon_family.gvs import _mass_descriptors, _topology, constitutive_forces, forward_kinematics  # noqa: E402
from extensions.tendon_family.gvs_projection import discretization_jacobian, project  # noqa: E402
from tools.state_io import atomic_json, digest  # noqa: E402

HERE = Path(__file__).resolve().parent
STAGE37 = ROOT / 'runs/stage37_gvs_backend_consistency_20260924/gvs_backend_consistency.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def array(value):
    return np.asarray(value, dtype=float)


def norm(value):
    return float(np.linalg.norm(value))


def rotation_error(a, b):
    return float(np.arccos(np.clip((np.trace(a.T @ b) - 1) / 2, -1, 1)))


def dense_tendon_jacobian(model, data):
    result = np.zeros((model.ntendon, model.nv))
    if data.ten_J.size == model.ntendon * model.nv:
        result[:] = data.ten_J.reshape(model.ntendon, model.nv)
    else:
        for k in range(model.ntendon):
            adr, count = model.ten_J_rowadr[k], model.ten_J_rownnz[k]
            result[k, model.ten_J_colind[adr:adr + count]] = data.ten_J[adr:adr + count]
    return result


def comparison(gvs, backend):
    difference = backend - gvs
    return dict(gvs=gvs.tolist(), backend=backend.tolist(), difference=difference.tolist(),
                gvs_norm=norm(gvs), backend_norm=norm(backend), difference_norm=norm(difference),
                relative_difference=None if norm(gvs) < 1e-12 else norm(difference) / norm(gvs))


def main():
    prior = read(STAGE37)
    source = ROOT / prior['source']
    route = read(ROOT / 'runs/stage35_case_b_retry_softagent_20260924/inputs/route.json')
    design = route['robot']['structure']['data']
    physics = read(source / 'resolved_physics.json')
    scene = read(source / 'experiment_scene.json')
    compiled = read(source / 'compiled_physics.json')
    basis = prior['identities']['resolved_basis']
    resolved = ResolvedGVSBasis.model_validate(basis)
    q0, u0 = array(prior['baseline']['q0']), array(prior['baseline']['u0'])
    mapping = discretization_jacobian(physics, resolved)
    qcell = mapping @ q0
    assert digest(route['robot']) == prior['identities']['robot']
    assert physics['identity'] == prior['identities']['physics'] == compiled['physics_identity']
    assert physics['identity'] == scene['physics_identity']
    assert basis == read(source / 'control_spec.json')['algorithm']['projector']['resolved_basis']
    assert np.allclose(qcell, prior['baseline']['q_cell_rad'], atol=1e-14)
    assert np.allclose(project(physics, resolved, qcell, np.zeros_like(qcell))['q_gvs'], q0, atol=1e-12)
    assert not scene['forces']
    for tendon, compiled_tendon in zip(design['tendons'], physics['tendons']):
        assert tendon['id'] == compiled_tendon['entity']
        assert tendon['points'] == [point['physical_binding'] for point in compiled_tendon['points']]

    model = mujoco.MjModel.from_xml_path(str(source / 'robot.xml'))
    data = mujoco.MjData(model)
    qi, vi = (np.asarray(compiled[key], dtype=int) for key in ('qpos_indices', 'qvel_indices'))
    tids = np.asarray(compiled['tendon_ids'], dtype=int)
    aids = np.asarray(compiled['direct_tension_ids'], dtype=int)
    assert model.nq == model.nv == len(qcell)
    data.qpos[qi], data.qvel[vi] = qcell, 0
    original_gravity = model.opt.gravity.copy()
    assert np.allclose(original_gravity, scene['gravity'])

    def probe(gravity_on, tensions):
        model.opt.gravity[:] = original_gravity if gravity_on else 0
        data.ctrl[aids] = tensions
        mujoco.mj_forward(model, data)
        jac = dense_tendon_jacobian(model, data)[tids][:, vi]
        return dict(gravity=-(mapping.T @ data.qfrc_bias[vi]),
                    elastic=-(mapping.T @ data.qfrc_passive[vi]),
                    tendon=mapping.T @ data.qfrc_actuator[vi],
                    joint_gravity=-data.qfrc_bias[vi].copy(),
                    joint_elastic=-data.qfrc_passive[vi].copy(),
                    joint_tendon=data.qfrc_actuator[vi].copy(),
                    jacobian=jac, lengths=data.ten_length[tids].copy(),
                    tip=data.site_xpos[model.site('tip_site').id].copy(),
                    tip_rotation=data.site_xmat[model.site('tip_site').id].reshape(3, 3).copy(),
                    tension=-data.actuator_force[aids].copy(),
                    contacts=int(data.ncon), constraint=norm(data.qfrc_constraint[vi]))

    full = probe(True, u0)
    gravity_only = probe(True, np.zeros_like(u0))
    tendon_only = probe(False, u0)
    elastic_only = probe(False, np.zeros_like(u0))
    assert np.allclose(full['gravity'], gravity_only['gravity'], atol=1e-13)
    assert np.allclose(full['tendon'], tendon_only['tendon'], atol=1e-13)
    assert np.allclose(full['elastic'], elastic_only['elastic'], atol=1e-13)
    assert norm(tendon_only['gravity']) < 1e-13 and norm(elastic_only['tendon']) < 1e-13
    assert norm(gravity_only['tendon']) < 1e-13
    assert full['contacts'] == 0 and full['constraint'] == 0
    assert np.allclose(full['tension'], u0, atol=1e-12)
    assert np.allclose(full['tip'], prior['initial_backend']['tip_world_m'], atol=1e-12)
    assert np.allclose(full['lengths'], prior['initial_backend']['tendon_lengths_m'], atol=1e-12)

    gvs_forces = prior['baseline']['gvs_forces']
    terms = {name: comparison(array(gvs_forces[key]), measured[name]) for name, key, measured in (
        ('gravity', 'gravity_force', gravity_only),
        ('tendon', 'tendon_generalized_force', tendon_only),
        ('elastic', 'elastic_force', elastic_only))}
    for name in terms:
        assert np.allclose(terms[name]['backend'], prior['initial_backend']['forces_gvs'][name], atol=1e-12)
    gvs_residual = array(terms['tendon']['gvs']) + array(terms['gravity']['gvs']) - array(terms['elastic']['gvs'])
    backend_residual = array(terms['tendon']['backend']) + array(terms['gravity']['backend']) - array(terms['elastic']['backend'])
    assert norm(gvs_residual) < 1e-12
    assert np.allclose(backend_residual, prior['initial_backend']['net_force_gvs'], atol=1e-12)
    delta = {key: array(value['difference']) for key, value in terms.items()}
    residual = delta['gravity'] + delta['tendon'] - delta['elastic']
    directional = {name: float(np.dot(sign * value, residual) / norm(residual)**2) for name, value, sign in
                   [('gravity', delta['gravity'], 1), ('tendon', delta['tendon'], 1), ('elastic', delta['elastic'], -1)]}
    gvs_jac = array(prior['baseline']['gvs_tendon_jacobian'])
    backend_jac = tendon_only['jacobian'] @ mapping
    per_tendon = []
    for k, name in enumerate(prior['baseline']['tendon_order']):
        gvs_force = -u0[k] * gvs_jac[k]
        backend_force = -u0[k] * backend_jac[k]
        per_tendon.append(dict(tendon=name, tension_n=float(u0[k]),
                               gvs_length_m=float(prior['baseline']['gvs_tendon_lengths_m'][k]),
                               backend_length_m=float(full['lengths'][k]),
                               gvs_jacobian=gvs_jac[k].tolist(), backend_jacobian=backend_jac[k].tolist(),
                               generalized_force=comparison(gvs_force, backend_force)))
    assert np.allclose(sum((array(row['generalized_force']['gvs']) for row in per_tendon), np.zeros_like(q0)), terms['tendon']['gvs'])
    assert np.allclose(sum((array(row['generalized_force']['backend']) for row in per_tendon), np.zeros_like(q0)), terms['tendon']['backend'])

    segment_elastic = {}
    for segment in basis['segments']:
        name, start = segment['segment'], segment['start']
        count = 2 * len(segment['knots'])
        gvs, backend = array(terms['elastic']['gvs'])[start:start+count], array(terms['elastic']['backend'])[start:start+count]
        segment_elastic[name] = dict(**comparison(gvs, backend),
                                     direction_cosine=float(np.dot(gvs, backend) / (norm(gvs)*norm(backend))))

    parameters = GVSModelParameters.model_validate({'basis': basis['specification']})
    gvs_stiffness = np.column_stack([
        constitutive_forces(design, np.eye(len(q0))[k], np.zeros_like(q0),
                            parameters.quadrature_points_per_segment, parameters.basis)[0]
        for k in range(len(q0))])
    joint_stiffness = model.jnt_stiffness[[model.joint(name).id for name in physics['dofs']]]
    backend_stiffness = mapping.T @ np.diag(joint_stiffness) @ mapping
    assert np.allclose(gvs_stiffness @ q0, terms['elastic']['gvs'], atol=1e-12)
    assert np.allclose(backend_stiffness @ q0, terms['elastic']['backend'], atol=1e-12)
    stiffness = dict(gvs_matrix=gvs_stiffness.tolist(), backend_matrix=backend_stiffness.tolist(),
                     difference_frobenius_norm=norm(backend_stiffness-gvs_stiffness),
                     relative_difference=norm(backend_stiffness-gvs_stiffness)/norm(gvs_stiffness),
                     difference_max_abs=float(np.max(np.abs(backend_stiffness-gvs_stiffness))))
    gvs_mass = {name: 0.0 for name in physics['entity_map']}
    for descriptor in _mass_descriptors(_topology(design), parameters.quadrature_points_per_segment, parameters.basis):
        gvs_mass[descriptor['component']] += descriptor['mass']
    backend_mass = {name: sum(float(model.body_mass[model.body(physics['parts'][i]['entity']).id])
                              for i in entity['bodies']) for name, entity in physics['entity_map'].items()}
    mass = {name: dict(gvs_kg=gvs_mass[name], backend_kg=backend_mass[name],
                       difference_kg=backend_mass[name]-gvs_mass[name]) for name in gvs_mass}

    kinematics = forward_kinematics(design, q0, samples_per_segment=4, basis=basis['specification'])
    serial = geometry(physics, qcell, scene['assembly']['mount'])
    mount_p, mount_R = array(scene['mount_position']), array(scene['mount_rotation'])
    shape = {}
    for segment in basis['segments']:
        name = segment['segment']
        part_ids = physics['entity_map'][name]['bodies']
        points = []
        for part_id in part_ids:
            body, part = serial['bodies'][part_id], physics['parts'][part_id]
            points.append(body['p'] + body['R'] @ [part['length_m'], 0, 0])
        gvs_points = mount_p + array(kinematics['segment_backbones_m'][name]) @ mount_R.T
        final_part = physics['parts'][part_ids[-1]]
        backend_R = serial['bodies'][part_ids[-1]]['R'] @ rx(-final_part['section_axis_rad'])
        gvs_R = mount_R @ kinematics['segment_transforms'][name]['tip'][:3, :3]
        shape[name] = dict(gvs_backbone_points_world_m=gvs_points.tolist(),
                           backend_cell_endpoints_world_m=array(points).tolist(),
                           endpoint_position_difference_m=(array(points)-gvs_points[1:]).tolist(),
                           endpoint_position_max_norm_m=max(map(norm, array(points)-gvs_points[1:])),
                           endpoint_orientation_difference_rad=rotation_error(gvs_R, backend_R))
    gvs_tip_transform = kinematics['tip_transform']
    gvs_tip_R = mount_R @ gvs_tip_transform[:3, :3]
    geometric = dict(segments=shape,
                     tip_gvs_world_m=(mount_p + mount_R @ gvs_tip_transform[:3, 3]).tolist(),
                     tip_backend_world_m=full['tip'].tolist(),
                     tip_position_difference_m=(full['tip']-mount_p-mount_R @ gvs_tip_transform[:3, 3]).tolist(),
                     tip_orientation_difference_rad=rotation_error(gvs_tip_R, full['tip_rotation']),
                     tendon_binding_exact=True,
                     tendon_length_difference_m=(full['lengths']-array(prior['baseline']['gvs_tendon_lengths_m'])).tolist(),
                     tendon_jacobian_difference_max=float(np.max(np.abs(backend_jac-gvs_jac))),
                     backend_serial_geometry_tip_error_m=norm(serial['tip']-full['tip']),
                     backend_serial_geometry_length_max_error_m=float(np.max(np.abs(serial['lengths']-full['lengths']))))
    assert geometric['backend_serial_geometry_tip_error_m'] < 1e-12
    assert geometric['backend_serial_geometry_length_max_error_m'] < 1e-12

    components = {entry['id']: entry for entry in design['components'] if entry['id'] in ('near', 'far')}
    reference = dict(robot_identity=prior['identities']['robot'],
                     dynamic_system_identity=prior['identities']['dynamic_system'],
                     linearization_identity=prior['identities']['linearization'],
                     basis=prior['identities']['resolved_basis'], basis_identity=digest(basis),
                     backend_discretization_identity=physics['discretization_identity'],
                     backend_discretization=physics['discretization'],
                     physics_identity=physics['identity'],
                     q0=q0.tolist(), qcell_rad=qcell.tolist(), u0_n=u0.tolist(),
                     tendon_order=prior['baseline']['tendon_order'],
                     gravity_world_m_s2=scene['gravity'],
                     material={name:dict(length_m=part['length_m'], sections=part['sections'],
                        physics=part['physics'], natural_curvature_rad_m=part['natural_curvature_rad_m'])
                        for name, part in components.items()},
                     compiled_stiffness_nm_rad=compiled['stiffness_nm_rad'])
    result = dict(reference_state=reference,
                  measurement_semantics=dict(gvs='Stage 3.7 evaluated saved DynamicSystem at q0/u0; exact CasADi force outputs',
                    backend='MuJoCo mj_forward qfrc_bias, qfrc_passive, qfrc_actuator at identical qcell and zero velocity',
                    projection='M.T maps 12 joint forces into 12 GVS generalized coordinates',
                    gravity_only='ctrl=0; original gravity; Qg=-M.T qfrc_bias',
                    tendon_only='gravity=0; ctrl=u0; Qt=M.T qfrc_actuator',
                    elastic_only='gravity=0; ctrl=0; Qe=-M.T qfrc_passive',
                    unavailable='No continuum-equivalent per-body gravity decomposition or causal geometry/mass separation exposed'),
                  direct_backend_joint_forces=dict(gravity_nm=gravity_only['joint_gravity'].tolist(),
                    tendon_nm=tendon_only['joint_tendon'].tolist(),
                    elastic_nm=elastic_only['joint_elastic'].tolist()),
                  terms=terms,
                  total_residual=comparison(gvs_residual, backend_residual),
                  residual_attribution=dict(directional_fraction=directional,
                    gravity_only_mismatch_residual_norm=norm(delta['gravity']),
                    non_gravity_mismatch_residual_norm=norm(delta['tendon']-delta['elastic']),
                    observed_residual_norm=norm(residual)),
                  per_tendon=per_tendon, segment_elastic=segment_elastic,
                  stiffness_matrix=stiffness, mass_by_component=mass, geometry=geometric,
                  classifications=dict(gravity='GRAVITY_MODEL_MISMATCH', tendon='TENDON_FORCE_MISMATCH',
                    elasticity='STIFFNESS_MODEL_MISMATCH', geometry='GEOMETRIC_INTEGRATION_MISMATCH',
                    primary_cause='multiple', confidence='medium'))
    atomic_json(HERE / 'physics_alignment.json', result)
    print(json.dumps(dict(term_difference_norms={k:v['difference_norm'] for k,v in terms.items()},
                          total_residual_norm=result['total_residual']['backend_norm'],
                          non_gravity_residual_norm=result['residual_attribution']['non_gravity_mismatch_residual_norm'],
                          segment_endpoint_gaps_m={k:v['endpoint_position_max_norm_m'] for k,v in shape.items()},
                          classification=result['classifications']), indent=2))


if __name__ == '__main__':
    main()
