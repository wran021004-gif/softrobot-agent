"""One baseline GVS/MuJoCo static-equilibrium test, then conditional force attribution."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import numpy as np

from tools.state_io import atomic_json, read


def source_input(path):
    value=deepcopy(read(path))
    assert value['task']['goal']['data']['target_m']==[.25,0.,.15]
    assert value['task']['evaluator']['parameters']['data']['tolerance_m']==.01
    assert value['robot']['structure']['data']['id']=='two_segment_development'
    value['task']['environment']['data']['external_forces']=[]
    value['run_id']='gvs-static-e1'
    value['policy']['route']=None
    return value


def static_experiment(root,source):
    from extensions.tendon_family.backends import MujocoBackend, physics_for
    from extensions.tendon_family.contracts import Control
    from extensions.tendon_family.control import Controller
    from extensions.tendon_family.gvs import forward_kinematics
    from extensions.tendon_family.gvs_lqr import _candidate_operating_point
    from extensions.tendon_family.gvs_projection import discretize, project
    from extensions.tendon_family.pcc import quaternion_wxyz_to_rotation
    from schemas.platform import SessionInput
    from tools.platform_registry import registry
    from tools.platform_tasks import compile_input

    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=False)
    value=source_input(source)
    preliminary=SessionInput.model_validate(value)
    point=_candidate_operating_point(preliminary)
    q0=np.asarray(point['q0']);u0=np.asarray(point['u0'])
    physics=physics_for(preliminary)
    qpos,qvel=discretize(physics,preliminary.robot.structure.data,q0,np.zeros_like(q0))
    roundtrip=project(physics,preliminary.robot.structure.data,qpos,qvel)
    value['task']['initializer']['parameters']['data']=dict(qpos_rad=dict(zip(physics['dofs'],qpos.tolist())),
        qvel_rad_s=dict(zip(physics['dofs'],qvel.tolist())))
    value['policy']['controller']=dict(extension_id='controller.family',version='1.0.0',parameters=dict(
        contract='family.control',version='1.0.0',data=dict(mode='tension_reference',
        tension_execution_mode='ideal_tension',desired_tendon_tensions_n=u0.tolist())))
    inp=SessionInput.model_validate(compile_input(value)['input'])
    design=inp.robot.structure.data;assembly=inp.task.environment.data
    local_tip=forward_kinematics(design,q0,samples_per_segment=2)['tip_position_m']
    rotation=quaternion_wxyz_to_rotation(assembly['mount']['quaternion_wxyz'])
    predicted_tip=(rotation@local_tip+np.asarray(assembly['mount']['position_m'])).tolist()
    equilibrium=dict(q0=q0.tolist(),u0=u0.tolist(),coordinate_order=point['coordinate_order'],
        tendon_order=point['tendon_order'],gvs_static_residual_norm=point['refined_equilibrium_residual_norm'],
        gvs_predicted_tip_world_m=predicted_tip,backend_qpos_rad=qpos.tolist(),backend_qvel_rad_s=qvel.tolist(),
        roundtrip_q_error_max_rad_m=float(np.max(np.abs(np.asarray(roundtrip['q_gvs'])-q0))),
        roundtrip_qdot_error_max_rad_m_s=float(np.max(np.abs(roundtrip['qdot_gvs']))),
        roundtrip_projection_residual_max_rad_m=roundtrip['projection_residual_max_rad_m'],
        source=str(Path(source).resolve()))
    atomic_json(root/'input.json',value);atomic_json(root/'equilibrium.json',equilibrium)

    backend=MujocoBackend();backend.compile(inp,registry())
    controller=Controller(Control.model_validate(inp.policy.controller.parameters.data),inp.task.timing.control_period_s)
    backend.initialize(inp.task.initializer.parameters,controller)
    result=backend.run(root/'backend',inp.policy.timeout_s)
    observations=read(root/'backend'/'controller_observations.json')
    from gzip import open as gzip_open
    import json
    with gzip_open(root/'backend'/'trajectory.json.gz','rt',encoding='utf8') as stream: rows=json.load(stream)
    tip0=np.asarray(observations[0]['tip_position_m']);tip=np.asarray([row['tip_m'] for row in rows])
    backend_q=np.asarray([row['qpos_rad'] for row in rows]);initial_q=qpos
    projected=[project(physics,design,row['qpos_rad'],row['qvel_rad_s']) for row in rows]
    q_projected=np.asarray([row['q_gvs'] for row in projected])
    tolerance=float(inp.task.evaluator.parameters.data['tolerance_m'])
    arm_length=sum(component['length_m'] for component in design['components'] if component['kind']=='flexible_segment')
    tip_drift=np.linalg.norm(tip-tip0,axis=1)
    max_q_drift=float(np.max(np.linalg.norm(backend_q-initial_q,axis=1)))
    geometry_gap=float(np.linalg.norm(tip0-np.asarray(predicted_tip)))
    finite=bool(np.isfinite(tip).all() and np.isfinite(backend_q).all() and
        all(np.isfinite(row['qvel_rad_s']).all() for row in rows))
    # One target-tolerance budget for geometry and static drift; the state bound
    # is the angle whose single full-arm lever would move the tip by that budget.
    passed=(result.solver_status=='completed' and finite and geometry_gap<=tolerance and
        float(tip_drift.max())<=tolerance and max_q_drift<=tolerance/arm_length)
    report=dict(classification='PASS' if passed else 'FAIL',criterion=dict(
        maximum_initial_gvs_backend_tip_gap_m=tolerance,maximum_tip_drift_m=tolerance,
        maximum_backend_joint_l2_drift_rad=tolerance/arm_length,
        basis='Frozen 0.01 m reach tolerance; joint angle converted using total flexible-arm length.'),
        solver_status=result.solver_status,initial_tip_world_m=tip0.tolist(),final_tip_world_m=tip[-1].tolist(),
        final_tip_drift_m=float(tip_drift[-1]),maximum_tip_drift_m=float(tip_drift.max()),
        initial_gvs_backend_tip_gap_m=geometry_gap,
        initial_backend_qpos_rad=initial_q.tolist(),final_backend_qpos_rad=backend_q[-1].tolist(),
        maximum_backend_joint_l2_drift_rad=max_q_drift,
        initial_projected_gvs_q=roundtrip['q_gvs'],final_projected_gvs_q=q_projected[-1].tolist(),
        final_projected_gvs_q_drift_l2_rad_m=float(np.linalg.norm(q_projected[-1]-q0)),
        maximum_projected_gvs_q_drift_l2_rad_m=float(np.max(np.linalg.norm(q_projected-q0,axis=1))),
        maximum_projection_residual_rad_m=max(row['projection_residual_max_rad_m'] for row in projected),
        desired_tension_initial_n=rows[0]['desired_tension_n'],desired_tension_final_n=rows[-1]['desired_tension_n'],
        actual_tension_initial_n=rows[0]['tension_n'],actual_tension_final_n=rows[-1]['tension_n'],
        initial_tendon_lengths_m=observations[0]['tendon_length_m'],final_tendon_lengths_m=rows[-1]['tendon_length_m'],
        final_tendon_length_change_m=rows[-1]['tendon_length_change_m'],
        nonfinite_states=not finite,backend_solves=1,mujoco_launches=1,matlab_launches=0,model_calls=0)
    atomic_json(root/'e1_report.json',report)
    return report


def force_attribution(root):
    import mujoco
    from extensions.tendon_family.contracts import GVSModelParameters
    from extensions.tendon_family.gvs import constitutive_forces, gravity_force, tendon_kinematics
    from extensions.tendon_family.gvs_projection import discretization_jacobian
    from extensions.tendon_family.pcc import quaternion_wxyz_to_rotation

    root=Path(root).resolve();e1=read(root/'e1_report.json')
    if e1['classification']!='FAIL': raise ValueError('E2_REQUIRES_FAILED_E1')
    inp=read(root/'input.json');point=read(root/'equilibrium.json')
    physics=read(root/'backend'/'resolved_physics.json');compiled=read(root/'backend'/'compiled_physics.json')
    design=inp['robot']['structure']['data'];q=np.asarray(point['q0']);u=np.asarray(point['u0'])
    params=GVSModelParameters();zeros=np.zeros_like(q)
    elastic,_=constitutive_forces(design,q,zeros,params.quadrature_points_per_segment)
    assembly=inp['task']['environment']['data'];rotation=quaternion_wxyz_to_rotation(assembly['mount']['quaternion_wxyz'])
    gravity=gravity_force(design,q,rotation.T@np.asarray(assembly['environment']['gravity_m_s2']),params)
    tendon_order,_,tendon_jac=tendon_kinematics(design,q,params)
    if tendon_order!=point['tendon_order']: raise ValueError('TENDON_ORDER_CHANGED')
    tendon=-tendon_jac.T@u
    mapping=discretization_jacobian(physics,design)
    model=mujoco.MjModel.from_xml_path(str(root/'backend'/'robot.xml'));data=mujoco.MjData(model)
    qi=np.asarray(compiled['qpos_indices']);vi=np.asarray(compiled['qvel_indices'])
    aids=np.asarray(compiled['direct_tension_ids'])
    data.qpos[qi]=point['backend_qpos_rad'];data.qvel[vi]=0.;data.ctrl[aids]=u
    mujoco.mj_forward(model,data)
    backend=dict(elastic=-mapping.T@data.qfrc_passive[vi],gravity=-mapping.T@data.qfrc_bias[vi],
        tendon=mapping.T@data.qfrc_actuator[vi])
    backend['net']=backend['tendon']+backend['gravity']-backend['elastic']
    gvs=dict(elastic=elastic,gravity=gravity,tendon=tendon,net=tendon+gravity-elastic)
    differences={term:backend[term]-gvs[term] for term in ('elastic','gravity','tendon','net')}
    norms={term:float(np.linalg.norm(differences[term])) for term in ('elastic','gravity','tendon')}
    ranked=sorted(norms,key=norms.get,reverse=True)
    dominant=ranked[0] if norms[ranked[0]]>1.5*norms[ranked[1]] else 'multiple_comparable_terms'
    report=dict(mapping='delta_q_backend = J_map delta_q_gvs; tau_gvs = J_map.T tau_backend',
        coordinate_order=point['coordinate_order'],backend_dof_order=physics['dofs'],mapping_matrix=mapping.tolist(),
        sign_convention='GVS net = tendon + gravity - elastic; MuJoCo elastic = -qfrc_passive, gravity = -qfrc_bias at qvel=0, tendon = qfrc_actuator',
        gvs={k:v.tolist() for k,v in gvs.items()},mujoco_projected={k:v.tolist() for k,v in backend.items()},
        difference_mujoco_minus_gvs={k:v.tolist() for k,v in differences.items()},difference_l2_norms=norms,
        dominant_mismatch=dominant,mujoco_contacts=int(data.ncon),
        projected_constraint_force=(mapping.T@data.qfrc_constraint[vi]).tolist(),
        raw_backend_forces=dict(passive=data.qfrc_passive[vi].tolist(),bias=data.qfrc_bias[vi].tolist(),
            actuator=data.qfrc_actuator[vi].tolist(),constraint=data.qfrc_constraint[vi].tolist()),
        backend_solves=0,mujoco_integrations=0)
    atomic_json(root/'e2_force_report.json',report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['e1','e2']);parser.add_argument('root')
    parser.add_argument('--source',default='runs/reach_free_gvs_candidate_rebuild_retry_20260921/inputs/route.json')
    args=parser.parse_args()
    import json
    report=static_experiment(args.root,args.source) if args.action=='e1' else force_attribution(args.root)
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
