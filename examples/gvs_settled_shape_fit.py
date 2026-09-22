"""Focused fit of a saved GVS operating point to its MuJoCo settled centerline."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mujoco
import numpy as np
from scipy.optimize import least_squares

from extensions.tendon_family.geometry import geometry
from extensions.tendon_family.gvs import (
    constitutive_forces, gravity_force, tendon_kinematics,
)
from extensions.tendon_family.gvs_projection import _segments, discretization_jacobian
from extensions.tendon_family.contracts import GVSModelParameters
from extensions.tendon_family.pcc import quaternion_wxyz_to_rotation
from tools.state_io import atomic_json, read


def centerline(physics, q, mount):
    bodies = geometry(physics, q, mount)['bodies']
    return {
        name: np.asarray([bodies[index]['p'] for index in physics['entity_map'][name]['bodies']]
            + [bodies[physics['entity_map'][name]['bodies'][-1]]['p']
               + bodies[physics['entity_map'][name]['bodies'][-1]]['R']
               @ [physics['parts'][physics['entity_map'][name]['bodies'][-1]]['length_m'], 0., 0.]])
        for name in ('near', 'far')
    }


def continuous_centerline(design, q, mount, counts):
    # The physical sections use different cell counts. Request their exact stations.
    from extensions.tendon_family.gvs import _Kinematics, _topology
    state = _Kinematics(_topology(design), q, 48)
    rotation = quaternion_wxyz_to_rotation(mount['quaternion_wxyz'])
    translation = np.asarray(mount['position_m'])
    points = {name: np.asarray([rotation @ state.point_pose(name, i / counts[name])[:3, 3]
                                + translation for i in range(counts[name] + 1)])
              for name in counts}
    return points, rotation @ state.attachment_pose(state.design.tip)[:3, 3] + translation


def metrics(predicted, target, tip, target_tip):
    diffs = {name: np.linalg.norm(predicted[name] - target[name], axis=1)
             for name in target}
    all_errors = np.concatenate(list(diffs.values()))
    return dict(centerline_rms_m=float(np.sqrt(np.mean(all_errors ** 2))),
                centerline_max_m=float(np.max(all_errors)),
                tip_error_m=float(np.linalg.norm(tip - target_tip)),
                section_rms_m={name: float(np.sqrt(np.mean(error ** 2)))
                               for name, error in diffs.items()},
                worst_station={name: int(np.argmax(error)) for name, error in diffs.items()})


def strain_metrics(physics, design, q_cell, target_q):
    section_errors = {}
    for name, samples, _ in _segments(physics, design):
        errors = np.asarray([sample['principal_to_segment']
             @ (q_cell[sample['dofs']] - target_q[sample['dofs']])
             / sample['cell_length_m'] for sample in samples])
        section_errors[name] = dict(rms_rad_m=float(np.sqrt(np.mean(errors ** 2))),
                                    max_rad_m=float(np.max(np.abs(errors))),
                                    worst_cell=int(np.argmax(np.linalg.norm(errors, axis=1))))
    return section_errors


def report(root, destination):
    root = Path(root)
    inp = read(root / 'input.json')
    point = read(root / 'equilibrium.json')
    physics = read(root / 'backend' / 'resolved_physics.json')
    design = inp['robot']['structure']['data']
    mount = inp['task']['environment']['data']['mount']
    counts = {name: len(physics['entity_map'][name]['bodies']) for name in ('near', 'far')}
    q0 = np.asarray(point['q0'])
    u0 = np.asarray(point['u0'])
    model = mujoco.MjModel.from_xml_path(str(root / 'backend' / 'robot.xml'))
    data = mujoco.MjData(model)
    joints = [model.joint(name).id for name in physics['dofs']]
    qi = model.jnt_qposadr[joints]
    vi = model.jnt_dofadr[joints]
    aids = [model.actuator(name + '_direct_tension').id for name in point['tendon_order']]
    data.qpos[qi] = point['backend_qpos_rad']
    data.ctrl[aids] = u0
    hold = 0
    required = max(1, round(.1 / model.opt.timestep))
    for step in range(round(2. / model.opt.timestep)):
        mujoco.mj_step(model, data)
        hold = hold + 1 if np.max(np.abs(data.qvel[vi])) < .001 else 0
        if hold >= required:
            break
    if hold < required:
        raise RuntimeError('MUJOCO_DID_NOT_SETTLE_WITHIN_TWO_SECONDS')
    mujoco.mj_forward(model, data)
    target_q = data.qpos[qi].copy()
    settled_velocity_norm = float(np.linalg.norm(data.qvel[vi]))
    settled_max_joint_rate = float(np.max(np.abs(data.qvel[vi])))
    target = centerline(physics, target_q, mount)
    target_tip = data.site_xpos[model.site('tip_site').id].copy()
    serial = geometry(physics, target_q, mount)
    body_ids = [model.body(part['entity']).id for part in physics['parts']]
    if (np.max(np.abs(data.xpos[body_ids] - np.asarray([body['p'] for body in serial['bodies']]))) > 1e-9
            or np.linalg.norm(serial['tip'] - target_tip) > 1e-9):
        raise RuntimeError('SETTLED_CENTERLINE_FRAME_OR_GEOMETRY_MISMATCH')
    names = ('near', 'far')
    def flatten(points):
        return np.concatenate([points[name].ravel() for name in names])
    def residual(q):
        points, _ = continuous_centerline(design, q, mount, counts)
        return flatten(points) - flatten(target)
    fitted = least_squares(residual, q0, max_nfev=100, xtol=1e-10, ftol=1e-10, gtol=1e-10)
    q_fit = fitted.x
    original_shape, original_tip = continuous_centerline(design, q0, mount, counts)
    fitted_shape, fitted_tip = continuous_centerline(design, q_fit, mount, counts)

    # A single extra guide-aligned hinge/kink mode in each segment and bend axis.
    # The 8D baseline is fitted in the same discrete geometry for a fair comparison.
    mapping = discretization_jacobian(physics, design)
    extras = np.zeros((len(physics['dofs']), 4))
    for section, (_, samples, _) in enumerate(_segments(physics, design)):
        for sample in samples:
            x = 2 * sample['normalized_center'] - 1
            for axis in range(2):
                vector = np.zeros(2)
                vector[axis] = sample['cell_length_m'] * max(0., x)
                extras[sample['dofs'], 2 * section + axis] = sample['principal_to_segment'].T @ vector
    def discrete_shape(coefficients, matrix):
        q_cell = matrix @ coefficients
        shape = centerline(physics, q_cell, mount)
        tip = geometry(physics, q_cell, mount)['tip']
        return shape, tip
    def fit_discrete(matrix, seed):
        return least_squares(lambda values: flatten(discrete_shape(values, matrix)[0])
                             - flatten(target), seed, max_nfev=100,
                             xtol=1e-10, ftol=1e-10, gtol=1e-10).x
    q_discrete = fit_discrete(mapping, q_fit)
    richer_map = np.column_stack((mapping, extras))
    q_richer = fit_discrete(richer_map, np.r_[q_discrete, np.zeros(4)])
    discrete_8, discrete_tip_8 = discrete_shape(q_discrete, mapping)
    discrete_12, discrete_tip_12 = discrete_shape(q_richer, richer_map)

    def backend_forces(coefficients, matrix):
        data.qpos[qi] = matrix @ coefficients
        data.qvel[vi] = 0.
        mujoco.mj_forward(model, data)
        tendon = matrix.T @ data.qfrc_actuator[vi]
        gravity = -matrix.T @ data.qfrc_bias[vi]
        elastic = -matrix.T @ data.qfrc_passive[vi]
        net = tendon + gravity - elastic
        return dict(tendon=tendon, gravity=gravity, elastic=elastic, net=net)
    backend_8 = backend_forces(q_fit, mapping)
    backend_12 = backend_forces(q_richer, richer_map)
    equilibrium_12 = least_squares(lambda values: backend_forces(values, richer_map)['net'],
                                   q_richer, max_nfev=100, xtol=1e-11,
                                   ftol=1e-11, gtol=1e-11)
    equilibrium_12_shape, equilibrium_12_tip = discrete_shape(equilibrium_12.x, richer_map)
    equilibrium_12_net = backend_forces(equilibrium_12.x, richer_map)['net']

    parameters = GVSModelParameters()
    assembly = inp['task']['environment']['data']
    gravity_world = np.asarray(assembly['environment']['gravity_m_s2'])
    rotation = quaternion_wxyz_to_rotation(mount['quaternion_wxyz'])
    def forces(q):
        elastic, _ = constitutive_forces(design, q, np.zeros(8),
                                         parameters.quadrature_points_per_segment)
        gravity = gravity_force(design, q, rotation.T @ gravity_world, parameters)
        _, _, jac = tendon_kinematics(design, q, parameters)
        tendon = -jac.T @ u0
        net = tendon + gravity - elastic
        return dict(elastic=elastic.tolist(), gravity=gravity.tolist(), tendon=tendon.tolist(),
                    elastic_norm=float(np.linalg.norm(elastic)),
                    gravity_norm=float(np.linalg.norm(gravity)),
                    tendon_norm=float(np.linalg.norm(tendon)),
                    net_norm=float(np.linalg.norm(net)), net=net.tolist())
    # Restore the settled pose before measuring its full-space residual.
    data.qpos[qi] = target_q
    mujoco.mj_forward(model, data)
    full_net = data.qfrc_actuator[vi] + data.qfrc_passive[vi] - data.qfrc_bias[vi]
    gvs_fit_forces = forces(q_fit)
    result = dict(source=str(root.resolve()), settled_time_s=float(data.time),
        settled_tip_world_m=target_tip.tolist(), settled_qpos_rad=target_q.tolist(),
        settled_joint_velocity_l2_rad_s=settled_velocity_norm,
        settled_max_joint_rate_rad_s=settled_max_joint_rate,
        settled_full_force_residual_nm=float(np.linalg.norm(full_net)),
        q0=q0.tolist(), q_fit=q_fit.tolist(), q_fit_minus_q0=(q_fit-q0).tolist(),
        current_8d_original=metrics(original_shape, target, original_tip, target_tip),
        current_8d_best=metrics(fitted_shape, target, fitted_tip, target_tip),
        current_8d_fit_success=bool(fitted.success),
        current_8d_gvs_forces_at_fit=gvs_fit_forces,
        current_8d_backend_forces_at_fit={key: values.tolist() for key, values in backend_8.items()},
        current_8d_backend_net_norm_at_fit=float(np.linalg.norm(backend_8['net'])),
        current_8d_backend_minus_gvs_net_norm_at_fit=float(np.linalg.norm(
            backend_8['net'] - np.asarray(gvs_fit_forces['net']))),
        current_8d_backend_minus_gvs_component_norms_at_fit={key: float(np.linalg.norm(
            backend_8[key] - np.asarray(gvs_fit_forces[key])))
            for key in ('tendon', 'gravity', 'elastic')},
        current_8d_discrete_best=metrics(discrete_8, target, discrete_tip_8, target_tip),
        current_8d_strain_fit=strain_metrics(physics, design, mapping @ q_discrete, target_q),
        guide_kink_12d_best=metrics(discrete_12, target, discrete_tip_12, target_tip),
        guide_kink_12d_strain_fit=strain_metrics(physics, design, richer_map @ q_richer, target_q),
        guide_kink_12d_coefficients=q_richer.tolist(),
        guide_kink_12d_backend_net_norm_at_fit=float(np.linalg.norm(backend_12['net'])),
        guide_kink_12d_constrained_equilibrium_success=bool(equilibrium_12.success),
        guide_kink_12d_constrained_equilibrium_net_norm=float(np.linalg.norm(equilibrium_12_net)),
        guide_kink_12d_constrained_equilibrium_shape=metrics(
            equilibrium_12_shape, target, equilibrium_12_tip, target_tip),
        guide_kink_12d_constrained_equilibrium_tip_world_m=equilibrium_12_tip.tolist(),
        guide_kink_12d_constrained_equilibrium_strain=strain_metrics(
            physics, design, richer_map @ equilibrium_12.x, target_q),
        guide_kink_12d_constrained_equilibrium_coefficients=equilibrium_12.x.tolist(),
        guide_kink_12d_description='one max(0,2s/L-1) curvature mode per segment and bending axis; cell-midpoint integration',
        target_centerline_world_m={name: target[name].tolist() for name in names})
    atomic_json(destination, result)
    print('8D original', result['current_8d_original'])
    print('8D best', result['current_8d_best'])
    print('12D kink', result['guide_kink_12d_best'])
    print('GVS force at fitted shape', result['current_8d_gvs_forces_at_fit']['net_norm'])
    return result


if __name__ == '__main__':
    report('runs/gvs_static_consistency_f2_20260922',
           'runs/gvs_settled_shape_fit_20260922.json')
