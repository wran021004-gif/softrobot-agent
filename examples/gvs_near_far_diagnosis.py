"""Two fixed tendon perturbations at the saved high-curvature operating point."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mujoco
import numpy as np

from extensions.tendon_family.contracts import GVSModelParameters
from extensions.tendon_family.gvs import mass_matrix
from extensions.tendon_family.gvs_projection import discretization_jacobian
from examples.gvs_control_trend import direction_comparison
from examples.gvs_geometry_consistency import gvs_tendon_function
from tools.state_io import atomic_json, read


def analyze(root):
    root = Path(root)
    saved = read(root / 'input.json')
    point = read(root / 'equilibrium.json')
    physics = read(root / 'backend' / 'resolved_physics.json')
    design = saved['robot']['structure']['data']
    q0 = np.asarray(point['q0'])
    u0 = np.asarray(point['u0'])
    mapping = discretization_jacobian(physics, design)
    model = mujoco.MjModel.from_xml_path(str(root / 'backend' / 'robot.xml'))
    data = mujoco.MjData(model)
    jids = [model.joint(name).id for name in physics['dofs']]
    qi = model.jnt_qposadr[jids]
    vi = model.jnt_dofadr[jids]
    aids = [model.actuator(t['id'] + '_direct_tension').id for t in design['tendons']]
    data.qpos[qi] = mapping @ q0
    data.qvel[vi] = 0.
    data.ctrl[aids] = u0
    mujoco.mj_forward(model, data)
    baseline_acceleration = data.qacc[vi].copy()
    baseline_force = data.qfrc_actuator[vi].copy()
    full_mass = np.zeros((model.nv, model.nv))
    mujoco.mj_fullM(model, data, full_mass)
    mass = full_mass[np.ix_(vi, vi)]
    reduced_mass = mapping.T @ mass @ mapping
    reduced_mass_gvs = mass_matrix(design, q0, GVSModelParameters())
    Jtip = np.zeros((3, model.nv))
    mujoco.mj_jacSite(model, data, Jtip, np.zeros_like(Jtip), model.site('tip_site').id)
    Jtip = Jtip[:, vi]
    tendon_jacobian = np.asarray(gvs_tendon_function(design)(q0)[1])
    rows = []
    for name in ('near_t1', 'far_t1'):
        index = point['tendon_order'].index(name)
        data.ctrl[aids] = u0
        data.ctrl[aids[index]] += .1
        mujoco.mj_forward(model, data)
        force = data.qfrc_actuator[vi] - baseline_force
        acceleration = data.qacc[vi] - baseline_acceleration
        reduced_force = mapping.T @ force
        # M-orthogonal projection: J qdd minimizes ||a-J qdd||_M.
        reduced_acceleration = np.linalg.solve(reduced_mass, mapping.T @ mass @ acceleration)
        representable = mapping @ reduced_acceleration
        residual = acceleration - representable
        tip_representable = Jtip @ representable
        tip_residual = Jtip @ residual
        tip_total = Jtip @ acceleration
        gvs_force = -.1 * tendon_jacobian[index]
        gvs_acceleration = np.linalg.solve(reduced_mass_gvs, gvs_force)
        # Existing report holds the GVS tip response for the same q0.
        previous = read(root / 'control_trend_report.json')
        gvs_tip = np.asarray(next(row['gvs_tip_incremental_acceleration_m_s2'] for row in previous['cases']
            if row['case'] == 'high_curvature_q0' and row['tendon'] == name))
        rows.append(dict(case=name, delta_tension_n=.1,
            delta_generalized_force_nm=force.tolist(), delta_reduced_generalized_force_nm=reduced_force.tolist(),
            gvs_delta_generalized_force_nm=gvs_force.tolist(),
            delta_generalized_acceleration_rad_s2=acceleration.tolist(),
            reduced_acceleration= reduced_acceleration.tolist(),
            representable_acceleration_rad_s2=representable.tolist(),
            residual_acceleration_rad_s2=residual.tolist(),
            acceleration_mass_norm=float(np.sqrt(acceleration @ mass @ acceleration)),
            representable_mass_norm=float(np.sqrt(representable @ mass @ representable)),
            residual_mass_norm=float(np.sqrt(residual @ mass @ residual)),
            residual_mass_fraction=float(np.sqrt(residual @ mass @ residual / (acceleration @ mass @ acceleration))),
            gvs_reduced_acceleration=gvs_acceleration.tolist(),
            backend_reduced_mass_acceleration=np.linalg.solve(reduced_mass, reduced_force).tolist(),
            tip_acceleration_gvs_m_s2=gvs_tip.tolist(),tip_acceleration_representable_m_s2=tip_representable.tolist(),
            tip_acceleration_residual_m_s2=tip_residual.tolist(),tip_acceleration_total_m_s2=tip_total.tolist(),
            tip_representable_norm_m_s2=float(np.linalg.norm(tip_representable)),
            tip_residual_norm_m_s2=float(np.linalg.norm(tip_residual)),
            tip_angle_gvs_to_total_deg=direction_comparison(gvs_tip, tip_total)['angle_deg'],
            tip_angle_gvs_to_representable_deg=direction_comparison(gvs_tip, tip_representable)['angle_deg'],
            tip_angle_representable_to_total_deg=direction_comparison(tip_representable, tip_total)['angle_deg'],
            tip_residual_over_total_norm=float(np.linalg.norm(tip_residual) / np.linalg.norm(tip_total))))
    report = dict(operating_point=str(root / 'equilibrium.json'), projection=(
        'Mass-orthogonal acceleration projection onto the existing 8-column cell-angle discretization J: '
        'a_rep=J (J.T M J)^-1 J.T M a; a_res=a-a_rep. Tip components use the same MuJoCo tip Jacobian.'),
        generalized_force_mapping='J.T times MuJoCo incremental actuator generalized force',
        reduced_mass_gvs=reduced_mass_gvs.tolist(),reduced_mass_mujoco=reduced_mass.tolist(),
        reduced_mass_relative_frobenius=float(np.linalg.norm(reduced_mass-reduced_mass_gvs)/np.linalg.norm(reduced_mass_gvs)),
        cases=rows,conclusion=('PARTIAL: the near_t1 representable tip direction follows GVS, while its '
            'mass-orthogonal local component rotates the total response by about 80 degrees. Far_t1 has '
            'a large local component too, but it reinforces rather than reverses the tip direction. '
            'Reduced mass and force differences are small; local response is supported as the main near_t1 cause, '
            'while the precise local mass coupling mechanism is not identified.'))
    atomic_json(root / 'near_far_dynamics_diagnosis.json',report)
    for row in rows:
        print(row['case'], 'tip angle',row['tip_angle_gvs_to_total_deg'], 'residual tip / total',
            row['tip_residual_over_total_norm'],'mass residual fraction',row['residual_mass_fraction'])
    return report


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',nargs='?',default='runs/gvs_static_consistency_f2_20260922')
    analyze(parser.parse_args().root)
