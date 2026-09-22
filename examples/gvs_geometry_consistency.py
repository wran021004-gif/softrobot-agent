"""Focused F0/F1 comparison of the baseline GVS and serial-cell geometry."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import casadi as ca
import numpy as np

from extensions.tendon_family.compiler import resolve, rx
from extensions.tendon_family.geometry import geometry
from extensions.tendon_family.gvs import _topology, forward_kinematics
from extensions.tendon_family.gvs_casadi import _SymbolicKinematics
from extensions.tendon_family.gvs_projection import discretization_jacobian, project
from extensions.tendon_family.pcc import quaternion_wxyz_to_rotation
from tools.state_io import atomic_json, read


def rotation_error(a, b):
    return float(np.arccos(np.clip((np.trace(a.T @ b) - 1) / 2, -1, 1)))


def gvs_tendon_function(design):
    topology = _topology(design)
    q = ca.MX.sym('q', 4 * len(topology[3]))
    state = _SymbolicKinematics(topology, q, 24)
    lengths = []
    for tendon in topology[0].tendons:
        positions = []
        for route_point in tendon.points:
            attachment = route_point.attachment
            override = None
            if route_point.hole:
                override = topology[1][attachment.part].guide_holes[route_point.hole]
            positions.append(state.attachment_pose(attachment, override)[:3, 3])
        lengths.append(sum((ca.norm_2(b - a) for a, b in zip(positions, positions[1:])), ca.MX(0)))
    vector = ca.vertcat(*lengths)
    return ca.Function('gvs_tendon_geometry', [q], [vector, ca.jacobian(vector, q)])


def study(source, output):
    value = read(source)
    design = value['robot']['structure']['data']
    mount = value['task']['environment']['data']['mount']
    mount_rotation = quaternion_wxyz_to_rotation(mount['quaternion_wxyz'])
    mount_position = np.asarray(mount['position_m'])
    q_high = np.asarray(read('runs/gvs_static_consistency_20260921/equilibrium.json')['q0'])
    cases = {'zero': np.zeros_like(q_high),
             'moderate': np.array([2., -1., 1., .5, -4., 2., -2., 1.]),
             'high_curvature_q0': q_high}
    reference = {name: forward_kinematics(design, q, samples_per_segment=2) for name, q in cases.items()}
    levels = [(3, 2), (6, 4), (12, 8), (24, 16)]
    results = []
    selected = {}
    for near, far in levels:
        physics = resolve(design, {'cells': {'near': near, 'far': far}})
        mapping = discretization_jacobian(physics, design)
        for name, q in cases.items():
            qpos = mapping @ q
            discrete = geometry(physics, qpos, mount)
            gvs = reference[name]
            tip_gvs = mount_rotation @ gvs['tip_position_m'] + mount_position
            segment_errors = {}
            for segment in ('near', 'far'):
                part_index = physics['entity_map'][segment]['bodies'][-1]
                body = discrete['bodies'][part_index]
                ds = physics['parts'][part_index]['length_m']
                endpoint = body['p'] + body['R'] @ [ds, 0., 0.]
                target = gvs['segment_transforms'][segment]['tip']
                segment_rotation = body['R'] @ rx(-physics['parts'][part_index]['section_axis_rad'])
                segment_errors[segment] = dict(position_m=float(np.linalg.norm(endpoint - (mount_rotation @ target[:3, 3] + mount_position))),
                    orientation_rad=rotation_error(segment_rotation, mount_rotation @ target[:3, :3]))
            projection = project(physics, design, qpos, np.zeros_like(qpos))
            results.append(dict(case=name, cells={'near': near, 'far': far},
                tip_error_m=float(np.linalg.norm(discrete['tip'] - tip_gvs)),
                segment_end_errors=segment_errors,
                projection_error_max=float(np.max(np.abs(np.asarray(projection['q_gvs']) - q))),
                gvs_tip_world_m=tip_gvs.tolist(), backend_tip_world_m=discrete['tip'].tolist()))
        selected[(near, far)] = physics
    # A useful static comparison needs a geometry gap below the 0.01 m reach tolerance.
    practical = next(((near, far) for near, far in levels
        if max(row['tip_error_m'] for row in results if row['cells'] == {'near': near, 'far': far}) < .006), None)
    report = dict(f0=results, practical_cells=dict(zip(('near', 'far'), practical)) if practical else None)
    if practical:
        physics = selected[practical]
        mapping = discretization_jacobian(physics, design)
        tendon_function = gvs_tendon_function(design)
        tendon_rows = []
        for name, q in cases.items():
            ref_lengths, ref_jacobian = (np.asarray(item, dtype=float) for item in tendon_function(q))
            ref_lengths = ref_lengths.ravel()
            discrete = geometry(physics, mapping @ q, mount)
            backend_jacobian = discrete['Jlength'] @ mapping
            difference = discrete['lengths'] - ref_lengths
            jacobian_difference = backend_jacobian - ref_jacobian
            tendon_rows.append(dict(case=name, gvs_lengths_m=ref_lengths.tolist(), backend_lengths_m=discrete['lengths'].tolist(),
                signed_length_difference_m=difference.tolist(), max_absolute_length_difference_m=float(np.max(np.abs(difference))),
                max_relative_length_difference=float(np.max(np.abs(difference) / np.maximum(ref_lengths, 1e-12))),
                max_absolute_jacobian_difference=float(np.max(np.abs(jacobian_difference))),
                relative_jacobian_difference=float(np.linalg.norm(jacobian_difference) / np.linalg.norm(ref_jacobian)),
                largest_jacobian_index=[int(i) for i in np.unravel_index(np.argmax(np.abs(jacobian_difference)), jacobian_difference.shape)]))
        report['f1'] = tendon_rows
        report['tendon_order'] = [t['id'] for t in design['tendons']]
        import mujoco
        from extensions.tendon_family.mjcf import compile_xml
        from extensions.tendon_family.backends import MujocoBackend
        from schemas.platform import SessionInput
        from tools.platform_registry import registry

        model_input = read(source)
        model_input['policy']['discretization']['data']['cells'] = dict(zip(('near', 'far'), practical))
        backend = MujocoBackend()
        backend.compile(SessionInput.model_validate(model_input), registry())
        xml_path = Path(output).parent / 'robot.xml'
        xml_path.parent.mkdir(parents=True, exist_ok=True)
        compile_xml(backend.physics, backend.scene, backend.config, xml_path)
        model = mujoco.MjModel.from_xml_path(str(xml_path))
        data = mujoco.MjData(model)
        joint_ids = [model.joint(name).id for name in physics['dofs']]
        qpos_indices = model.jnt_qposadr[joint_ids]
        qvel_indices = model.jnt_dofadr[joint_ids]
        tendon_ids = [model.tendon(t['entity']).id for t in physics['tendons']]
        engine_rows = []
        for name, q in cases.items():
            data.qpos[qpos_indices] = mapping @ q
            mujoco.mj_forward(model, data)
            reference_geometry = geometry(physics, mapping @ q, mount)
            dense_jacobian = np.zeros((model.ntendon, model.nv))
            if data.ten_J.size == model.ntendon * model.nv:
                dense_jacobian[:] = data.ten_J.reshape(model.ntendon, model.nv)
            else:
                for tendon_index in range(model.ntendon):
                    adr = model.ten_J_rowadr[tendon_index]
                    count = model.ten_J_rownnz[tendon_index]
                    dense_jacobian[tendon_index, model.ten_J_colind[adr:adr + count]] = data.ten_J[adr:adr + count]
            engine_rows.append(dict(case=name,
                tip_difference_from_serial_geometry_m=float(np.linalg.norm(data.site_xpos[model.site('tip_site').id] - reference_geometry['tip'])),
                length_difference_from_serial_geometry_m=float(np.max(np.abs(data.ten_length[tendon_ids] - reference_geometry['lengths']))),
                jacobian_difference_from_serial_geometry=float(np.max(np.abs(dense_jacobian[tendon_ids][:, qvel_indices] @ mapping - reference_geometry['Jlength'] @ mapping))),
                gvs_jacobian_difference=float(np.max(np.abs(dense_jacobian[tendon_ids][:, qvel_indices] @ mapping - np.asarray(tendon_function(q)[1]))))))
        report['mujoco_validation'] = engine_rows
    atomic_json(output, report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='runs/gvs_static_consistency_20260921/input.json')
    parser.add_argument('--output', default='runs/gvs_geometry_consistency_20260922/report.json')
    args = parser.parse_args()
    study(args.source, args.output)
