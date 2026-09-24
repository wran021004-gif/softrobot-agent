"""Measure the saved Stage 3.6 GVS equilibrium in the unchanged MuJoCo model."""
import json
from pathlib import Path
import sys

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from extensions.tendon_family.contracts import GVSModelParameters, ResolvedGVSBasis  # noqa: E402
from extensions.tendon_family.geometry import geometry  # noqa: E402
from extensions.tendon_family.gvs import GVSModel, forward_kinematics  # noqa: E402
from extensions.tendon_family.gvs_casadi import CasadiLinearizer, expression_from_system, functions_for  # noqa: E402
from extensions.tendon_family.gvs_projection import discretization_jacobian, project  # noqa: E402
from schemas.platform import Payload, RobotDescription  # noqa: E402
from schemas.platform_math import SystemContext  # noqa: E402
from tools.state_io import atomic_json, digest  # noqa: E402

HERE = Path(__file__).resolve().parent
STAGE36 = ROOT / 'runs/stage36_controller_attribution_20260924'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def vec(value):
    return np.asarray(value, dtype=float).reshape(-1)


def norm(value):
    return float(np.linalg.norm(value))


def dense_tendon_jacobian(model, data):
    result = np.zeros((model.ntendon, model.nv))
    if data.ten_J.size == model.ntendon * model.nv:
        result[:] = data.ten_J.reshape(model.ntendon, model.nv)
    else:
        for k in range(model.ntendon):
            address, count = model.ten_J_rowadr[k], model.ten_J_rownnz[k]
            result[k, model.ten_J_colind[address:address + count]] = data.ten_J[address:address + count]
    return result


def main():
    saved = read(STAGE36 / 'controller_failure_attribution.json')
    source = ROOT / saved['source']['gvs']
    inputs = ROOT / 'runs/stage35_case_b_retry_softagent_20260924/inputs/route.json'
    control = read(source / 'control_spec.json')
    physics = read(source / 'resolved_physics.json')
    scene = read(source / 'experiment_scene.json')
    compiled = read(source / 'compiled_physics.json')
    robot = RobotDescription.model_validate(read(inputs)['robot'])
    design = robot.structure.data
    algorithm = control['algorithm']
    x0, u0 = (vec(algorithm[k]) for k in ('x0', 'u0'))
    q0 = x0[:len(x0)//2]
    assert np.array_equal(q0, vec(saved['chain']['q0']))
    assert np.array_equal(u0, vec(saved['chain']['u0']))
    basis = ResolvedGVSBasis.model_validate(algorithm['projector']['resolved_basis'])
    assert basis.model_dump(mode='json') == saved['identities']['basis']
    assert control['reference']['derivation']['coordinate_order'] == basis.coordinate_order
    assert control['reference']['tendon_order'] == saved['chain']['tendon_order']
    assert [t['entity'] for t in physics['tendons']] == saved['chain']['tendon_order']
    for design_tendon, backend_tendon in zip(design['tendons'], physics['tendons']):
        assert design_tendon['id'] == backend_tendon['entity']
        assert design_tendon['points'] == [point['physical_binding'] for point in backend_tendon['points']]
        assert design_tendon['pretension_n'] == backend_tendon['pretension_n']
        assert design_tendon['force_limit_n'] == backend_tendon['force_limit_n']
    assert compiled['physics_identity'] == physics['identity'] == scene['physics_identity']
    assert not scene['forces']

    parameters = GVSModelParameters.model_validate({'basis': basis.specification})
    system = GVSModel(parameters).build_system(
        robot, parameters, None, SystemContext(
            x0=x0.tolist(), u0=u0.tolist(),
            scene=Payload(contract='experiment.assembly', data=scene['assembly'])))
    assert digest(system.model_dump(mode='json')) == algorithm['dynamic_system_identity'] == saved['identities']['dynamic_system']
    linear = CasadiLinearizer().linearize(system)
    assert digest(linear.model_dump(mode='json')) == algorithm['linearization_identity'] == saved['identities']['linearization']
    functions = functions_for(expression_from_system(system))
    gvs = functions.evaluate(x0, u0)
    gvs_force = {k: vec(gvs[k]) for k in ('elastic_force', 'gravity_force', 'tendon_generalized_force')}
    gvs_net = gvs_force['tendon_generalized_force'] + gvs_force['gravity_force'] - gvs_force['elastic_force']
    gvs_length = vec(gvs['tendon_lengths_m'])
    gvs_jac = np.asarray(gvs['tendon_length_jacobian'])
    gvs_tip = vec(control['predicted_equilibrium_tip_world_m'])
    mapping = discretization_jacobian(physics, basis)
    q_cell = mapping @ q0
    transferred = project(physics, basis, q_cell, np.zeros_like(q_cell))
    assert np.allclose(transferred['q_gvs'], q0, atol=1e-11)

    model = mujoco.MjModel.from_xml_path(str(source / 'robot.xml'))
    data = mujoco.MjData(model)
    qi = np.asarray(compiled['qpos_indices'], dtype=int)
    vi = np.asarray(compiled['qvel_indices'], dtype=int)
    tids = np.asarray(compiled['tendon_ids'], dtype=int)
    aids = np.asarray(compiled['direct_tension_ids'], dtype=int)
    assert model.nq == len(qi) == len(q_cell) and model.nv == len(vi)
    assert [model.tendon(i).name for i in tids] == [t['entity'] for t in physics['tendons']]
    assert np.allclose(model.opt.gravity, scene['gravity'])
    data.qpos[qi] = q_cell
    data.qvel[vi] = 0
    data.ctrl[aids] = u0

    def snapshot():
        mujoco.mj_forward(model, data)
        jac = dense_tendon_jacobian(model, data)[tids][:, vi]
        forces = dict(elastic=-(mapping.T @ data.qfrc_passive[vi]),
                      gravity=-(mapping.T @ data.qfrc_bias[vi]),
                      tendon=mapping.T @ data.qfrc_actuator[vi])
        net = forces['tendon'] + forces['gravity'] - forces['elastic'] + mapping.T @ data.qfrc_constraint[vi]
        projection = project(physics, basis, data.qpos[qi], data.qvel[vi])
        return dict(qpos_rad=data.qpos[qi].tolist(), qvel_rad_s=data.qvel[vi].tolist(),
                    q_gvs=projection['q_gvs'], qdot_gvs=projection['qdot_gvs'],
                    projection_residual_max_rad_m=projection['projection_residual_max_rad_m'],
                    tip_world_m=data.site_xpos[model.site('tip_site').id].tolist(),
                    tendon_lengths_m=data.ten_length[tids].tolist(),
                    tendon_tensions_n=(-data.actuator_force[aids]).tolist(),
                    tendon_jacobian_gvs=(jac @ mapping).tolist(),
                    qacc_rad_s2=data.qacc[vi].tolist(), qacc_norm_rad_s2=norm(data.qacc[vi]),
                    forces_gvs={k: v.tolist() for k, v in forces.items()},
                    net_force_gvs=net.tolist(), net_force_norm=norm(net),
                    contacts=int(data.ncon), constraint_force_norm=norm(data.qfrc_constraint[vi]),
                    actuator_virtual_work_max_error_nm=float(np.max(np.abs(data.qfrc_actuator[vi] + jac.T @ u0))),
                    spring_force_max_error_nm=float(np.max(np.abs(data.qfrc_passive[vi] +
                        model.jnt_stiffness[[model.joint(name).id for name in physics['dofs']]] *
                        (data.qpos[qi] - model.qpos_spring[qi])))))

    initial = snapshot()
    mount = scene['assembly']['mount']
    shape_gvs = forward_kinematics(design, q0, samples_per_segment=4,
                                   basis=basis.specification)['segment_backbones_m']
    serial = geometry(physics, q_cell, mount)
    shape = {}
    for segment in basis.segments:
        parts = [physics['parts'][index] for index in physics['entity_map'][segment.segment]['bodies']]
        backend_points = []
        for part in parts:
            body = serial['bodies'][physics['parts'].index(part)]
            backend_points.append(body['p'] + body['R'] @ [part['length_m'], 0, 0])
        reference = np.asarray(shape_gvs[segment.segment])
        reference = np.asarray(scene['mount_position']) + reference @ np.asarray(scene['mount_rotation']).T
        shape[segment.segment] = dict(gvs_points_world_m=reference.tolist(),
                                      backend_cell_endpoints_world_m=np.asarray(backend_points).tolist(),
                                      endpoint_differences_m=(np.asarray(backend_points)-reference[1:]).tolist())

    # Fixed-tension forward dynamics, using the existing MuJoCo integrator only.
    timestep = float(model.opt.timestep)
    history = []
    settled = False
    for step in range(round(5.0 / timestep)):
        mujoco.mj_step(model, data)
        if (step + 1) % max(1, round(.1 / timestep)) == 0:
            mujoco.mj_forward(model, data)
            history.append(dict(time_s=float(data.time), qvel_norm_rad_s=norm(data.qvel[vi]),
                                qacc_norm_rad_s2=norm(data.qacc[vi]),
                                tip_world_m=data.site_xpos[model.site('tip_site').id].tolist()))
            if len(history) >= 5 and all(row['qvel_norm_rad_s'] < 1e-4 and row['qacc_norm_rad_s2'] < 1e-2
                                         for row in history[-5:]):
                settled = True
                break
        if not np.isfinite(data.qpos).all() or data.warning[mujoco.mjtWarning.mjWARN_BADQACC].number:
            break
    equilibrium = snapshot()
    differences = dict(tip_initial_minus_gvs_m=(vec(initial['tip_world_m'])-gvs_tip).tolist(),
                       tip_initial_norm_m=norm(vec(initial['tip_world_m'])-gvs_tip),
                       q_initial_minus_gvs=vec(initial['q_gvs'])-q0,
                       tendon_lengths_initial_minus_gvs_m=(vec(initial['tendon_lengths_m'])-gvs_length).tolist(),
                       tendon_jacobian_initial_minus_gvs=np.asarray(initial['tendon_jacobian_gvs'])-gvs_jac,
                       q_backend_eq_minus_gvs=vec(equilibrium['q_gvs'])-q0,
                       tip_backend_eq_minus_gvs_m=vec(equilibrium['tip_world_m'])-gvs_tip,
                       tendon_lengths_backend_eq_minus_gvs_m=vec(equilibrium['tendon_lengths_m'])-gvs_length)
    force_differences = {name: vec(initial['forces_gvs'][name])-gvs_force[key] for name, key in
                         [('elastic','elastic_force'), ('gravity','gravity_force'), ('tendon','tendon_generalized_force')]}
    report = dict(source=str(source.relative_to(ROOT)),
                  identities=dict(robot=digest(robot.model_dump(mode='json')), physics=physics['identity'], scene=scene['identity'],
                                  dynamic_system=algorithm['dynamic_system_identity'],
                                  linearization=algorithm['linearization_identity'], resolved_basis=basis.model_dump(mode='json')),
                  baseline=dict(coordinate_order=basis.coordinate_order,
                                tendon_order=saved['chain']['tendon_order'],
                                tendon_limits_n=saved['chain']['force_limits_n'],
                                pretension_n=[t['pretension_n'] for t in physics['tendons']],
                                tension_execution_mode=compiled['tension_execution_mode'],
                                q0=q0.tolist(), u0=u0.tolist(),
                                gvs_tip_world_m=gvs_tip.tolist(), gvs_tendon_lengths_m=gvs_length.tolist(),
                                gvs_tendon_jacobian=gvs_jac.tolist(),
                                gvs_forces={k:v.tolist() for k,v in gvs_force.items()},
                                gvs_residual=gvs_net.tolist(), gvs_residual_norm=norm(gvs_net),
                                saved_refined_residual_norm=control['reference']['derivation']['refined_equilibrium_residual_norm'],
                                q_cell_rad=q_cell.tolist(), mapped_projection=transferred,
                                shape=shape),
                  initial_backend=initial, settle=dict(duration_s=float(data.time), timestep_s=timestep,
                    settled=settled, history=history, backend_equilibrium=equilibrium),
                  differences={k:np.asarray(v).tolist() for k,v in differences.items()},
                  force_differences={k:dict(vector=v.tolist(), norm=norm(v)) for k,v in force_differences.items()},
                  backend_net_minus_gvs_norm=norm(vec(initial['net_force_gvs'])-gvs_net))
    atomic_json(HERE / 'gvs_backend_consistency.json', report)
    print(json.dumps(dict(initial_tip_gap_m=differences['tip_initial_norm_m'],
        initial_acceleration_norm=initial['qacc_norm_rad_s2'], settled=settled,
        equilibrium_q_gap=norm(differences['q_backend_eq_minus_gvs']),
        equilibrium_tip_gap_m=norm(differences['tip_backend_eq_minus_gvs_m']),
        component_difference_norms={k:v['norm'] for k,v in report['force_differences'].items()}), indent=2))


if __name__ == '__main__':
    main()
