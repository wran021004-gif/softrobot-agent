"""Inspect signed GVS and MuJoCo forces at the saved F2 equilibrium, without stepping."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mujoco
import numpy as np

from extensions.tendon_family.contracts import GVSModelParameters
from extensions.tendon_family.gvs import constitutive_forces, gravity_force
from extensions.tendon_family.gvs_projection import discretization_jacobian
from extensions.tendon_family.pcc import quaternion_wxyz_to_rotation
from examples.gvs_geometry_consistency import gvs_tendon_function
from tools.state_io import atomic_json, read


def analyze(root):
    root = Path(root)
    saved = read(root / 'input.json')
    point = read(root / 'equilibrium.json')
    physics = read(root / 'backend' / 'resolved_physics.json')
    compiled = read(root / 'backend' / 'compiled_physics.json')
    design = saved['robot']['structure']['data']
    q = np.asarray(point['q0'])
    tension = np.asarray(point['u0'])
    mapping = discretization_jacobian(physics, design)
    params = GVSModelParameters()
    elastic, _ = constitutive_forces(design, q, np.zeros_like(q), params.quadrature_points_per_segment)
    assembly = saved['task']['environment']['data']
    rotation = quaternion_wxyz_to_rotation(assembly['mount']['quaternion_wxyz'])
    gravity = gravity_force(design, q, rotation.T @ assembly['environment']['gravity_m_s2'], params)
    _, tendon_jacobian = (np.asarray(item) for item in gvs_tendon_function(design)(q))
    tendon = -tendon_jacobian.T @ tension
    gvs = dict(elastic=elastic, gravity=gravity, tendon=tendon, net=tendon + gravity - elastic)

    model = mujoco.MjModel.from_xml_path(str(root / 'backend' / 'robot.xml'))
    data = mujoco.MjData(model)
    qi = np.asarray(compiled['qpos_indices'])
    vi = np.asarray(compiled['qvel_indices'])
    aids = np.asarray(compiled['direct_tension_ids'])
    tids = np.asarray(compiled['tendon_ids'])
    data.qpos[qi] = point['backend_qpos_rad']
    data.qvel[vi] = 0
    data.ctrl[aids] = tension
    mujoco.mj_forward(model, data)
    passive = data.qfrc_passive[vi].copy()
    bias = data.qfrc_bias[vi].copy()
    actuator = data.qfrc_actuator[vi].copy()
    constraints = data.qfrc_constraint[vi].copy()
    dense_jacobian = np.zeros((model.ntendon, model.nv))
    if data.ten_J.size == model.ntendon * model.nv:
        dense_jacobian[:] = data.ten_J.reshape(model.ntendon, model.nv)
    else:
        for k in range(model.ntendon):
            address = model.ten_J_rowadr[k]
            count = model.ten_J_rownnz[k]
            dense_jacobian[k, model.ten_J_colind[address:address + count]] = data.ten_J[address:address + count]
    tendon_jacobian_backend = dense_jacobian[tids][:, vi]
    tendon_per_tendon = np.array([-t * mapping.T @ j for t, j in zip(tension, tendon_jacobian_backend)])
    actuator_virtual_work_error = float(np.max(np.abs(actuator + tendon_jacobian_backend.T @ tension)))
    spring_force = -model.jnt_stiffness[[model.joint(name).id for name in physics['dofs']]] * (
        data.qpos[qi] - model.qpos_spring[qi])
    spring_error = float(np.max(np.abs(passive - spring_force)))
    contacts = int(data.ncon)

    original_gravity = model.opt.gravity.copy()
    model.opt.gravity[:] = 0
    mujoco.mj_forward(model, data)
    zero_gravity_bias = data.qfrc_bias[vi].copy()
    zero_gravity_passive = data.qfrc_passive[vi].copy()
    model.opt.gravity[:] = original_gravity
    mujoco.mj_forward(model, data)

    backend = dict(elastic=-mapping.T @ passive, gravity=-mapping.T @ bias,
        tendon=mapping.T @ actuator)
    backend['net'] = backend['tendon'] + backend['gravity'] - backend['elastic']
    full_net = passive - bias + actuator + constraints
    tangent = mapping @ np.linalg.lstsq(mapping, full_net, rcond=None)[0]
    normal = full_net - tangent
    def normal_norm(force):
        return float(np.linalg.norm(force - mapping @ np.linalg.lstsq(mapping, force, rcond=None)[0]))
    table = [dict(coordinate=name, **{term: dict(gvs=float(gvs[term][i]), mujoco=float(backend[term][i]),
        difference=float(backend[term][i] - gvs[term][i])) for term in ('elastic', 'gravity', 'tendon', 'net')})
        for i, name in enumerate(point['coordinate_order'])]
    report = dict(coordinates=table, tendon_order=point['tendon_order'],
        tendon_length_jacobian_gvs=tendon_jacobian.tolist(),
        tendon_length_jacobian_backend_gvs=(tendon_jacobian_backend @ mapping).tolist(),
        tendon_generalized_force_by_tendon_backend=tendon_per_tendon.tolist(),
        component_difference_norms={term: float(np.linalg.norm(backend[term] - gvs[term]))
            for term in ('elastic', 'gravity', 'tendon')},
        force_semantics=dict(spring_force_max_error_nm=spring_error,
            actuator_virtual_work_max_error_nm=actuator_virtual_work_error,
            zero_gravity_bias_max_nm=float(np.max(np.abs(zero_gravity_bias))),
            passive_change_without_gravity_max_nm=float(np.max(np.abs(zero_gravity_passive - passive))),
            contacts=contacts, constraint_force_l2_nm=float(np.linalg.norm(constraints))),
        full_backend_force=dict(net_l2_nm=float(np.linalg.norm(full_net)),
            tangent_l2_nm=float(np.linalg.norm(tangent)), normal_l2_nm=float(np.linalg.norm(normal)),
            projected_normal_max_nm2=float(np.max(np.abs(mapping.T @ normal))),
            normal_component_norms_nm=dict(elastic=normal_norm(-passive),
                gravity=normal_norm(-bias), tendon=normal_norm(actuator)),
            largest_cell_force=[dict(dof=physics['dofs'][i], force_nm=float(full_net[i])) for i in
                np.argsort(np.abs(full_net))[-8:][::-1]]))
    atomic_json(root / 'f3_force_report.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', default='runs/gvs_static_consistency_f2_20260922')
    analyze(parser.parse_args().root)
