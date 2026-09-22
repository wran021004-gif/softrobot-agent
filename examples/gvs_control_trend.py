"""Compare local tendon-to-tip acceleration directions without time integration."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import casadi as ca
import mujoco
import numpy as np

from extensions.tendon_family.contracts import GVSModelParameters
from extensions.tendon_family.gvs import _topology, mass_matrix
from extensions.tendon_family.gvs_casadi import _SymbolicKinematics
from extensions.tendon_family.gvs_projection import discretization_jacobian, project
from extensions.tendon_family.pcc import quaternion_wxyz_to_rotation
from examples.gvs_geometry_consistency import gvs_tendon_function
from tools.state_io import atomic_json, read


DELTA_TENSION_N = .1


def direction_comparison(first, second, minimum_norm=0.):
    first = np.asarray(first, dtype=float)
    second = np.asarray(second, dtype=float)
    first_norm = float(np.linalg.norm(first))
    second_norm = float(np.linalg.norm(second))
    if min(first_norm, second_norm) < minimum_norm:
        return dict(cosine=None, angle_deg=None,
            gvs_unit=(first / first_norm).tolist() if first_norm >= minimum_norm else None,
            mujoco_unit=(second / second_norm).tolist() if second_norm >= minimum_norm else None,
            gvs_norm=first_norm, mujoco_norm=second_norm, direction_defined=False)
    cosine = float(np.dot(first, second) / (first_norm * second_norm))
    cosine = float(np.clip(cosine, -1, 1))
    return dict(cosine=cosine, angle_deg=float(np.degrees(np.arccos(cosine))),
        gvs_unit=(first / first_norm).tolist(), mujoco_unit=(second / second_norm).tolist(),
        gvs_norm=first_norm, mujoco_norm=second_norm, direction_defined=True)


def main(root):
    root = Path(root)
    saved = read(root / 'input.json')
    point = read(root / 'equilibrium.json')
    physics = read(root / 'backend' / 'resolved_physics.json')
    design = saved['robot']['structure']['data']
    topology = _topology(design)
    mount = saved['task']['environment']['data']['mount']
    rotation = quaternion_wxyz_to_rotation(mount['quaternion_wxyz'])
    mapping = discretization_jacobian(physics, design)
    params = GVSModelParameters()
    tendon_function = gvs_tendon_function(design)
    q_symbol = ca.MX.sym('q', len(point['q0']))
    symbolic_kinematics = _SymbolicKinematics(topology, q_symbol, params.integration_steps_per_segment)
    tip_local = symbolic_kinematics.attachment_pose(topology[0].tip)[:3, 3]
    tip_jacobian_function = ca.Function('gvs_tip_jacobian', [q_symbol], [ca.jacobian(tip_local, q_symbol)])

    model = mujoco.MjModel.from_xml_path(str(root / 'backend' / 'robot.xml'))
    data = mujoco.MjData(model)
    joint_ids = [model.joint(name).id for name in physics['dofs']]
    qpos_indices = model.jnt_qposadr[joint_ids]
    qvel_indices = model.jnt_dofadr[joint_ids]
    actuator_ids = [model.actuator(t['id'] + '_direct_tension').id for t in design['tendons']]
    tip_site_id = model.site('tip_site').id

    q0 = np.asarray(point['q0'])
    pretension = np.asarray([t['pretension_n'] for t in design['tendons']])
    cases = dict(straight=dict(q=np.zeros_like(q0), baseline=pretension),
        moderate=dict(q=np.array([2., -1., 1., .5, -4., 2., -2., 1.]), baseline=pretension),
        high_curvature_q0=dict(q=q0, baseline=np.asarray(point['u0'])))
    results = []
    for case, state in cases.items():
        q = state['q']
        baseline = state['baseline']
        data.qpos[qpos_indices] = mapping @ q
        data.qvel[qvel_indices] = 0
        data.ctrl[actuator_ids] = baseline
        mujoco.mj_forward(model, data)
        baseline_acceleration = data.qacc[qvel_indices].copy()
        tip_jacobian_mujoco = np.zeros((3, model.nv))
        mujoco.mj_jacSite(model, data, tip_jacobian_mujoco, np.zeros_like(tip_jacobian_mujoco), tip_site_id)
        tip_jacobian_mujoco = tip_jacobian_mujoco[:, qvel_indices]
        gvs_mass = mass_matrix(design, q, params)
        gvs_tendon_jacobian = np.asarray(tendon_function(q)[1])
        tip_jacobian_gvs = rotation @ np.asarray(tip_jacobian_function(q))
        for tendon_index, tendon in enumerate(design['tendons']):
            data.ctrl[actuator_ids] = baseline
            data.ctrl[actuator_ids[tendon_index]] += DELTA_TENSION_N
            mujoco.mj_forward(model, data)
            acceleration_mujoco = data.qacc[qvel_indices] - baseline_acceleration
            force_gvs = -gvs_tendon_jacobian[tendon_index] * DELTA_TENSION_N
            acceleration_gvs = np.linalg.solve(gvs_mass, force_gvs)
            tip_gvs = tip_jacobian_gvs @ acceleration_gvs
            tip_mujoco = tip_jacobian_mujoco @ acceleration_mujoco
            projected = np.asarray(project(physics, design, mapping @ q, acceleration_mujoco)['qdot_gvs'])
            results.append(dict(case=case, tendon=tendon['id'], baseline_tension_n=baseline.tolist(),
                delta_tension_n=DELTA_TENSION_N,
                tip=direction_comparison(tip_gvs, tip_mujoco, minimum_norm=1e-8),
                reduced_state=direction_comparison(acceleration_gvs, projected),
                gvs_tip_incremental_acceleration_m_s2=tip_gvs.tolist(),
                mujoco_tip_incremental_acceleration_m_s2=tip_mujoco.tolist(),
                gvs_q_incremental_acceleration=acceleration_gvs.tolist(),
                mujoco_projected_q_incremental_acceleration=projected.tolist(),
                mujoco_full_acceleration_l2=float(np.linalg.norm(acceleration_mujoco)),
                mujoco_acceleration_outside_gvs_fraction=float(np.linalg.norm(acceleration_mujoco - mapping @ projected)
                    / np.linalg.norm(acceleration_mujoco))))
    tip_cosines = np.asarray([row['tip']['cosine'] for row in results if row['tip']['direction_defined']])
    state_cosines = np.asarray([row['reduced_state']['cosine'] for row in results])
    report = dict(discretization=physics['discretization']['cells'], delta_tension_n=DELTA_TENSION_N,
        response_metric='incremental initial acceleration at fixed q and zero velocity; baseline subtracted',
        coordinate_order=point['coordinate_order'], tendon_order=point['tendon_order'], cases=results,
        negligible_tip_response_count=sum(not row['tip']['direction_defined'] for row in results),
        tip_cosine_min=float(tip_cosines.min()), tip_cosine_median=float(np.median(tip_cosines)),
        reduced_state_cosine_min=float(state_cosines.min()),
        reduced_state_cosine_median=float(np.median(state_cosines)))
    atomic_json(root / 'control_trend_report.json', report)
    for row in results:
        print(row['case'], row['tendon'], 'tip',
            round(row['tip']['cosine'], 4) if row['tip']['direction_defined'] else 'undefined',
            'state', round(row['reduced_state']['cosine'], 4))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', default='runs/gvs_static_consistency_f2_20260922')
    main(parser.parse_args().root)
