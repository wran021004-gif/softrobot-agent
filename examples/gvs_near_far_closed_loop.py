"""Small saved-q0 MuJoCo comparison of feedforward, GVS LQR and tip feedback."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mujoco
import numpy as np

from extensions.tendon_family.contracts import GVSModelParameters, LQRParameters
from extensions.tendon_family.gvs import GVSModel, forward_kinematics
from extensions.tendon_family.gvs_casadi import CasadiLinearizer, ContinuousLQRController
from extensions.tendon_family.gvs_lqr import GVSLQRController
from extensions.tendon_family.gvs_projection import discretization_jacobian, project
from extensions.tendon_family.pcc import quaternion_wxyz_to_rotation
from schemas.platform import SessionInput
from schemas.platform_math import SystemContext
from tools.state_io import atomic_json, read


def save_paired_summary(output, report):
    baselines={row['mode']:row for row in report['cases'] if row['case']=='none'}
    cases=[]
    for row in report['cases']:
        if row['case']=='none': continue
        baseline=baselines[row['mode']]
        changes=[np.asarray(sample['lqr_contribution_n'])-np.asarray(reference['lqr_contribution_n'])
            for sample,reference in zip(row['history'],baseline['history'])]
        feedback=[np.asarray(sample['residual_contribution_n'])-np.asarray(reference['residual_contribution_n'])
            for sample,reference in zip(row['history'],baseline['history'])]
        reduced=[np.asarray(sample['projected_gvs_q'])-np.asarray(reference['projected_gvs_q'])
            for sample,reference in zip(row['history'],baseline['history'])]
        peak=row['disturbance_tip_delta_peak_norm_m']
        cases.append(dict(tendon=row['case'],controller=row['mode'],
            baseline_final_absolute_tip_error_m=baseline['final_tip_error_m'],
            incremental_peak_tip_displacement_m=peak,
            incremental_peak_direction_world=(np.asarray(row['disturbance_tip_delta_at_peak_m'])/peak).tolist(),
            incremental_final_tip_displacement_m=row['disturbance_tip_delta_final_norm_m'],
            incremental_peak_reduced_q_l2_rad_m=float(max(map(np.linalg.norm,reduced))),
            incremental_settling_time_s_at_10pct_peak=row['incremental_settling_time_s_at_10pct_peak'],
            maximum_incremental_lqr_tension_norm_n=float(max(map(np.linalg.norm,changes))),
            maximum_incremental_task_feedback_tension_norm_n=float(max(map(np.linalg.norm,feedback))),
            saturated_control_samples=row['saturated_control_samples']))
    summary=dict(source='closed_loop_comparison.json',definition=report['definition'],
        equilibrium_drift_inf=report['equilibrium_drift_inf'],pbh_min_rank=report['pbh_min_rank'],
        closed_loop_eigenvalue_real_max=report['closed_loop_eigenvalue_real_max'],cases=cases)
    atomic_json(Path(output)/'paired_summary.json',summary)
    return summary


def run(root, output, gain=1., horizon=1., disturbance_duration=.5):
    root=Path(root);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    saved=read(root/'input.json');inp=SessionInput.model_validate(saved)
    point=read(root/'equilibrium.json');physics=read(root/'backend'/'resolved_physics.json')
    design=saved['robot']['structure']['data'];q0=np.asarray(point['q0']);u0=np.asarray(point['u0'])
    params=GVSModelParameters()
    system=GVSModel(params).build_system(inp.robot,params,None,SystemContext(
        x0=np.r_[q0,np.zeros_like(q0)].tolist(),u0=u0.tolist(),scene=inp.task.environment))
    linear=CasadiLinearizer().linearize(system);A=np.asarray(linear.A);B=np.asarray(linear.B)
    limits=np.asarray([t['force_limit_n'] for t in design['tendons']]);qweights=[1.]*8+[.1]*8
    controller=ContinuousLQRController(LQRParameters(Q=np.diag(qweights).tolist(),R=(100*np.eye(6)).tolist(),
        tendon_order=point['tendon_order'],force_limits_n=limits.tolist()))
    K=controller.configure_model(linear)
    from scipy.linalg import eigvals
    # Normalize each block before rank calculation; raw A^k B spans many scales.
    blocks=[np.linalg.matrix_power(A,i)@B for i in range(len(A))]
    controllability=np.column_stack([block/max(np.linalg.norm(block),1e-30) for block in blocks])
    mapping=discretization_jacobian(physics,design)
    mount=inp.task.environment.data['mount'];rotation=quaternion_wxyz_to_rotation(mount['quaternion_wxyz'])
    def tip(q):
        return rotation@np.asarray(forward_kinematics(design,q.tolist(),samples_per_segment=2)['tip_position_m'])+np.asarray(mount['position_m'])
    J=np.column_stack([(tip(q0+np.eye(8)[i]*1e-5)-tip(q0-np.eye(8)[i]*1e-5))/(2e-5) for i in range(8)])
    model=mujoco.MjModel.from_xml_path(str(root/'backend'/'robot.xml'))
    ji=[model.joint(name).id for name in physics['dofs']]
    qi=model.jnt_qposadr[ji];vi=model.jnt_dofadr[ji]
    aids=[model.actuator(t['id']+'_direct_tension').id for t in design['tendons']]
    tids=[model.tendon(t['id']).id for t in design['tendons']]
    tipid=model.site('tip_site').id
    period=.01;steps=int(round(period/model.opt.timestep))
    if abs(steps*model.opt.timestep-period)>1e-10: raise ValueError('CONTROL_PERIOD_NOT_ON_MUJOCO_GRID')
    plan=dict(algorithm=dict(K=K.tolist(),x0=np.r_[q0,np.zeros_like(q0)].tolist(),u0=u0.tolist(),
        projector=dict(coordinate_order=point['coordinate_order'])),
        reference=dict(equilibrium_q=q0.tolist()),tension_execution_mode='ideal_tension',
        task_feedback=dict(gain=gain,max_tension_n=.5,desired_tip_world_m=tip(q0).tolist(),
            gvs_tip_jacobian_world_m_per_curvature=J.tolist()))
    rows=[]
    for tendon in ('none','near_t1','far_t1'):
        for mode in ('feedforward','lqr','lqr_task'):
            data=mujoco.MjData(model);data.qpos[qi]=mapping@q0;data.qvel[vi]=0.;mujoco.mj_forward(model,data)
            reference=data.site_xpos[tipid].copy()
            policy=GVSLQRController(dict(task_feedback_gain=gain if mode=='lqr_task' else 0.),period)
            policy.configure(physics,{**plan,'task_feedback':{**plan['task_feedback'],
                'gain':gain if mode=='lqr_task' else 0.}})
            history=[]
            for index in range(round(horizon/period)):
                t=index*period;mujoco.mj_forward(model,data)
                geometry=dict(tip=data.site_xpos[tipid].copy(),lengths=data.ten_length[tids].copy())
                projection=project(physics,design,data.qpos[qi],data.qvel[vi])
                if mode=='feedforward':
                    command=u0.copy();lqr=np.zeros(6);residual=np.zeros(6)
                else:
                    geometry['gvs_projection']=projection
                    command=policy.command(t,geometry,np.asarray(projection['q_gvs']),np.asarray(projection['qdot_gvs']))
                    lqr=np.asarray(policy.last['lqr_tension_contribution_n'])
                    residual=np.asarray(policy.last['task_residual_tension_contribution_n'])
                disturbance=.1 if tendon!='none' and t<disturbance_duration else 0.
                applied=command.copy()
                if tendon!='none': applied[point['tendon_order'].index(tendon)]+=disturbance
                data.ctrl[aids]=np.clip(applied,0.,limits)
                for _ in range(steps): mujoco.mj_step(model,data)
                mujoco.mj_forward(model,data)
                actual=data.site_xpos[tipid].copy();error=tip(q0)-actual
                observed_projection=project(physics,design,data.qpos[qi],data.qvel[vi])
                history.append(dict(time_s=(index+1)*period,tip_error_m=error.tolist(),tip_error_norm_m=float(np.linalg.norm(error)),
                    tip_world_m=actual.tolist(),projected_gvs_q=observed_projection['q_gvs'],
                    tip_displacement_from_initial_m=(actual-reference).tolist(),command_tension_n=command.tolist(),
                    applied_tension_n=data.ctrl[aids].tolist(),lqr_contribution_n=lqr.tolist(),residual_contribution_n=residual.tolist()))
                if not np.isfinite(data.qpos).all(): raise ValueError('NONFINITE_MUJOCO_STATE')
            norms=np.asarray([h['tip_error_norm_m'] for h in history])
            rows.append(dict(case=tendon,mode=mode,final_tip_error_m=float(norms[-1]),peak_tip_error_m=float(norms.max()),
                settled_within_5mm=bool(np.all(norms[-10:]<.005)),history=history))
    baseline={row['mode']:row for row in rows if row['case']=='none'}
    for row in rows:
        if row['case']=='none': continue
        deltas=np.asarray([np.asarray(sample['tip_world_m'])-
            np.asarray(reference['tip_world_m']) for sample,reference in
            zip(row['history'],baseline[row['mode']]['history'])])
        magnitudes=np.linalg.norm(deltas,axis=1)
        peak_index=int(np.argmax(magnitudes))
        # Settling is measured on the paired increment after the pulse ends.
        # None means it did not enter and remain inside 10% of its own peak.
        settling=next((float(row['history'][i]['time_s']) for i in range(len(magnitudes))
            if row['history'][i]['time_s']>=disturbance_duration and
            np.all(magnitudes[i:]<=.1*magnitudes[peak_index])),None)
        reduced=np.asarray([np.asarray(sample['projected_gvs_q'])-
            np.asarray(reference['projected_gvs_q']) for sample,reference in
            zip(row['history'],baseline[row['mode']]['history'])])
        represented=(J@reduced.T).T
        linearized_residual=deltas-represented
        commands=np.asarray([sample['applied_tension_n'] for sample in row['history']])
        saturation=np.any((commands<=1e-9)|(commands>=limits-1e-9),axis=1)
        row['disturbance_tip_delta_history_m']=deltas.tolist()
        row['disturbance_tip_delta_final_m']=deltas[-1].tolist()
        row['disturbance_tip_delta_final_norm_m']=float(magnitudes[-1])
        row['disturbance_tip_delta_peak_norm_m']=float(magnitudes[peak_index])
        row['disturbance_tip_delta_at_peak_m']=deltas[peak_index].tolist()
        row['disturbance_tip_peak_time_s']=float(row['history'][peak_index]['time_s'])
        row['incremental_settling_time_s_at_10pct_peak']=settling
        row['q0_jacobian_tip_delta_at_peak_m']=represented[peak_index].tolist()
        row['q0_jacobian_residual_at_peak_m']=linearized_residual[peak_index].tolist()
        row['q0_jacobian_residual_peak_norm_m']=float(np.max(np.linalg.norm(linearized_residual,axis=1)))
        row['saturated_control_samples']=int(np.count_nonzero(saturation))
    report=dict(source=str(root),definition=(f'Saved q0, u0; +0.1 N tendon step for {disturbance_duration} s; '
        f'zero initial velocity; direct tension; {horizon} s horizon'),
        state_order=[s.name for s in linear.state_definition],input_order=point['tendon_order'],
        x0=np.r_[q0,np.zeros_like(q0)].tolist(),u0=u0.tolist(),force_limits_n=limits.tolist(),
        equilibrium_drift_inf=float(np.linalg.norm(np.asarray(linear.drift),ord=np.inf)),
        A=A.tolist(),B=B.tolist(),A_shape=list(A.shape),B_shape=list(B.shape),
        controllability_rank_at_1e_9=int(np.linalg.matrix_rank(controllability,tol=1e-9)),
        controllability_normalized_singular_values=np.linalg.svd(controllability,compute_uv=False).tolist(),
        pbh_min_rank=min(int(np.linalg.matrix_rank(np.c_[value*np.eye(len(A))-A,B],tol=1e-7))
            for value in np.linalg.eigvals(A)),
        closed_loop_eigenvalue_real_max=float(np.max(np.real(eigvals(A-B@K)))),Q_diagonal=qweights,R_diagonal=[100.]*6,
        gain=K.tolist(),feedback_gain=gain,feedback_limit_n=.5,
        linearized_tip_decomposition_note='J evaluated at q0 is a local diagnostic only; later baseline drift makes its residual unsuitable as a full-order mode attribution.',
        cases=rows)
    atomic_json(output/'closed_loop_comparison.json',report)
    save_paired_summary(output,report)
    for row in rows: print(row['case'],row['mode'],'final',row['final_tip_error_m'],'peak',row['peak_tip_error_m'])
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',nargs='?',default='runs/gvs_static_consistency_f2_20260922')
    parser.add_argument('--output',default='runs/gvs_near_far_closed_loop_20260922')
    parser.add_argument('--gain',type=float,default=1.)
    parser.add_argument('--horizon',type=float,default=1.)
    parser.add_argument('--disturbance-duration',type=float,default=.5)
    args=parser.parse_args();run(args.root,args.output,args.gain,args.horizon,args.disturbance_duration)
