"""Cross-backend comparison interpolates physical time, never frame indices."""
import math
import numpy as np
from tools.trajectory_diagnosis import load_rows
from tools.state_io import read

def compare_backends(root,c):
    a=c['results'].get('matlab',{});b=c['results'].get('mujoco',{})
    if not (a.get('complete') and b.get('complete')):return dict(status='NOT_COMPARABLE',reason='Both completed backend trajectories required')
    fa=(root/a['result_ref']).parent;fb=(root/b['result_ref']).parent
    pa=read(fa/'shared_input.json');pb=read(fb/'shared_input.json')
    same=all(pa[k]==pb[k] for k in ('ir_hash','control_hash','task_hash','environment_hash','mass','inertia_y','stiffness','damping','natural','kp','fmax','duration','dt'))
    if not same:return dict(status='INPUT_MISMATCH',reason='Do not compare differing resolved candidate inputs as a backend discrepancy')
    ra=load_rows(fa/'trajectory.json.gz');rb=load_rows(fb/'trajectory.json.gz')
    ta=np.array([r['time_s'] for r in ra]);tb=np.array([r['time_s'] for r in rb])
    qa=np.array([r['qpos_rad'] for r in ra]);qb=np.array([r['qpos_rad'] for r in rb])
    mask=(tb>=ta[0])&(tb<=ta[-1]+1e-9);t=tb[mask]
    ia=np.column_stack([np.interp(t,ta,qa[:,j]) for j in range(qa.shape[1])]);ib=qb[mask,::2]
    tipsa=np.array([r['tip_m'] for r in ra]);tipsb=np.array([r['tip_m'] for r in rb])[mask]
    tipinterp=np.column_stack([np.interp(t,ta,tipsa[:,j]) for j in range(3)])
    sta=np.array([r['solver_time_s'] for r in ra]);stb=np.array([r['solver_time_s'] for r in rb])
    forcea=-np.array([r['solver_actuator_force_n'] for r in ra]);forceb=-np.array([r['solver_actuator_force_n'] for r in rb])
    mf=(stb>=sta[0])&(stb<=sta[-1]+1e-9);tf=stb[mf]
    fi=np.column_stack([np.interp(tf,sta,forcea[:,j]) for j in range(forcea.shape[1])])
    return dict(status='COMPARABLE_WITH_PLANAR_APPROXIMATIONS',candidate_id=c['candidate_id'],
        matlab_error_m=a['position_error_m'],mujoco_error_m=b['position_error_m'],final_tip_difference_m=math.dist(a['tip_m'],b['tip_m']),
        sampled_tip_rmse_m=float(np.sqrt(np.mean(np.sum((tipinterp-tipsb)**2,axis=1)))),
        y_joint_rmse_rad=float(np.sqrt(np.mean((ia-ib)**2))),out_of_plane_joint_max_abs_rad=float(abs(qb[:,1::2]).max()),
        per_tendon_force_rmse_n=np.sqrt(np.mean((fi-forceb[mf])**2,axis=0)).tolist(),
        matlab_wall_s=a['elapsed_s'],mujoco_wall_s=b['elapsed_s'],matlab_is_faster=a['elapsed_s']<b['elapsed_s'],
        interpolation='linear query interpolation on saved samples; state and solver-force time axes processed separately',
        state_comparison_interval_s=[float(t[0]),float(t[-1])],force_comparison_interval_s=[float(tf[0]),float(tf[-1])],
        omissions=a.get('omissions'),matlab_applicability=a.get('applicability'),
        evidence=[a['result_ref'],b['result_ref'],str(fa/'trajectory.json.gz'),str(fb/'trajectory.json.gz')],
        attribution='Backend differences include omitted plane DOFs, contact law and time integration; no fitted parameters or causal guarantee')
