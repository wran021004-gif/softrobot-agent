"""Read sealed physical trajectories; no dynamics, provider or task re-evaluation."""
import csv
import gzip
import io
import json
import numpy as np
from tools.research.numerics import archived, execution_source, ROOT
from tools.state_io import read, digest


def diagnose(rows, target):
    """Preserve all saved samples; extrema always carry their simultaneous state."""
    times=np.array([r['time_s'] for r in rows])
    if np.any(np.diff(times)<=0):raise ValueError('STRICT_SAVED_TIME_ORDER_REQUIRED')
    for row in rows:
        tension=np.asarray(row['actual_tension_n'])
        if tension.shape!=(4,) or not np.isfinite(tension).all() or np.any(tension<0) or np.any(tension>8):
            raise ValueError('HISTORICAL_LEGAL_TENSIONS_REQUIRED')
        row['lower_bound_channels']=(tension<=1e-10).tolist()
        row['upper_bound_channels']=(tension>=8-1e-10).tolist()
        row['position_error_m']=float(np.linalg.norm(np.array(row['position_m'])-target))
        row['speed_m_s']=float(np.linalg.norm(row['velocity_m_s']))
    late=[r for r in rows if .25-1e-12<=r['time_s']<=.35+1e-12]
    hold=[r for r in late if r['time_s']>=.30-1e-12]
    v=np.array([r['velocity_m_s'] for r in late]);p=np.array([r['position_m'] for r in late])
    reversal=[late[i]['time_s'] for i in range(1,len(late)) if v[i]@v[i-1]<0]
    path=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum())
    displacement=p[-1]-p[0]
    peak=max(hold,key=lambda r:r['speed_m_s'])
    return dict(saved_samples=len(rows),time_range_s=[float(times[0]),float(times[-1])],
        saved_sample_period_s=float(np.median(np.diff(times))),full_physics_step_coverage=False,
        scope='All archived samples retained; intersample extrema and internal mode identification unknown. Historical only; no new evaluation.',
        holding_peak=peak,late_vector_reversal_times_s=reversal,
        late_displacement_m=displacement.tolist(),late_sampled_path_length_m=path,
        late_net_distance_m=float(np.linalg.norm(displacement)),
        late_endpoint_velocity_change_m_s=(v[-1]-v[0]).tolist(),
        observations=dict(drift_support='Signed net displacement and endpoint velocity change are reported.',
            drift_weakening='Vector reversals oppose a single persistent drift direction.' if reversal else 'No vector reversal at saved samples; intersample reversals unknown.',
            transient_support='Peak and both adjacent samples are preserved in the full timeline.',
            internal_motion='Joint rates/projection residuals, where saved, permit inspection but do not identify a causal internal mode.',
            unknown=['No physics-substep velocity history','No modal identification or causal controller/structure attribution','No frequency inferred from unrelated extrema']),
        timeline=rows)


def nmpc(folder, reference):
    source=execution_source(dict(reference=reference),folder);r=source['result'];files=source['files']
    candidate=archived(folder,r['candidate']);cfg=candidate['configuration']
    motion=archived(folder,r['profile']['motion'])
    trajectory=json.loads(gzip.decompress(archived(folder,files['trajectory.json.gz'],raw=True)))
    obs=archived(folder,files['controller_observations.json']);rows=[]
    if not len(motion)==len(trajectory)==len(obs):
        raise ValueError('HISTORICAL_RECORD_LENGTH_MISMATCH')
    for i,(m,t,o) in enumerate(zip(motion,trajectory,obs)):
        if abs(m['time_s']-t['time_s'])>1e-12 or abs(m['time_s']-o['time_s']-.01)>1e-12:
            raise ValueError('HISTORICAL_TIME_ALIGNMENT_MISMATCH')
        if m['tip_position_m']!=t['tip_m'] or o['actual_tension_n']!=t['tension_n']:
            raise ValueError('HISTORICAL_STATE_OR_ACTION_MISMATCH')
        pred=o.get('one_step_prediction')
        aligned=bool(pred and o['plan_accepted'] and not o['failure_response_used']
            and pred['frame']=='world' and pred['prediction_source']=='accepted_plan'
            and abs(pred['time_s']-m['time_s'])<1e-12)
        facts=o.get('mathematical_facts') or {}
        from extensions.tendon_family.gvs_reporting import vector3
        plan=np.asarray(facts.get('tensions',[]))
        predicted_input=plan[0] if plan.ndim==2 else plan if facts.get('horizon')==1 and plan.shape==np.asarray(t['tension_n']).shape else None
        vectors_valid=bool(pred and vector3(pred.get('tip_position_m')) and vector3(pred.get('tip_velocity_m_s')))
        same_input=bool(aligned and vectors_valid and predicted_input is not None and np.allclose(predicted_input,t['tension_n'],rtol=0,atol=1e-12))
        rows.append(dict(time_s=m['time_s'],position_m=m['tip_position_m'],velocity_m_s=m['tip_velocity_m_s'],
            actual_tension_n=t['tension_n'],control_update_index=i,control_start_s=o['time_s'],
            valid_plan=o['plan_accepted'],fallback=o['failure_response_used'],plan_source=o['plan_source'],
            saturated=t['force_limit_saturated'],qpos_rad=t['qpos_rad'],qvel_rad_s=t['qvel_rad_s'],
            projection_rate_residual=m.get('rate_projection_residual_rad_m_s'),
            aligned_accepted_prediction=pred if aligned else None,prediction_uses_actual_tension=bool(same_input),
            prediction_diagnostic_available=bool(same_input),
            prediction_diagnostic_missing_reason=None if same_input else 'Invalid vector dimensions or selected-plan input does not match the actually applied input',
            signed_prediction_velocity_error_m_s=(np.array(pred['tip_velocity_m_s'])-m['tip_velocity_m_s']).tolist() if same_input else None))
    result=diagnose(rows,cfg['task']['goal']['data']['target_m'])
    result.update(route='nmpc',source_folder=folder,source_result=reference,candidate=r['candidate'],
        source_files=files,motion_reference=r['profile']['motion'],task_identity=digest(cfg['task']),
        sampling_phase='post_control_interval',tendon_order=archived(folder,files['control_spec.json'])['specification']['tendon_order'],
        model_identity=archived(folder,files['control_spec.json'])['specification']['identity'],
        robot_identity=digest(cfg['robot']),frame='world',historical_acceptance=r['acceptance'])
    return result


def rl(folder, reference, raw_folder, raw_index):
    result=archived(folder,reference);cfg=archived(folder,result['experiment_configuration'])['effective_configuration']
    order=cfg['task']['tendon_order'];items=archived(raw_folder,raw_index)
    suffix=result['trajectory'].replace('\\','/').split('/')[-2]+'/trajectory.csv'
    item=next(r for r in items if r['path'].replace('\\','/').endswith(suffix))
    records=list(csv.DictReader(io.StringIO(archived(raw_folder,item['reference'],raw=True).decode('utf8'))))
    rows=[dict(time_s=float(r['time_s']),engine_time_s=float(r['engine_time_s']),position_m=[float(r[f'tip_{a}_m']) for a in 'xyz'],
        velocity_m_s=[float(r[f'velocity_{a}_m_s']) for a in 'xyz'],
        actual_tension_n=[float(r[f'{t}_applied_n']) for t in order],
        commanded_tension_n=[float(r[f'{t}_commanded_n']) for t in order],
        control_update_index=int(r['control_step'])-1,
        saturated=[bool(int(r[f'{t}_saturated'])) for t in order],
        validity='completed archived episode; per-physics-step validity unavailable') for r in records]
    value=diagnose(rows,cfg['task']['target_m'])
    value.update(route='rl',source_folder=folder,source_result=reference,candidate=result['candidate'],
        frame='world',raw_trajectory_reference=item['reference'],raw_folder=raw_folder,
        sampling_phase='post_control_interval',tendon_order=order,effective_configuration=cfg,
        historical_acceptance=result['acceptance'],policy_sha256=result['policy_sha256'])
    return value


def applied_schedule(rows, *, phase, period, timestep, intervals, order, expected_order, limits):
    """Recover held actions, never planned inputs or averages of substep forces.

    Post-interval rows are the held ideal command just executed. A dense source
    must explicitly declare post-physics-step phase, cover every step and show
    constant applied inputs within each control interval.
    """
    if order!=expected_order or phase not in ('post_control_interval','post_physics_step'):
        raise ValueError('CONTROL_ORDER_OR_PHASE_MISMATCH')
    if not np.isfinite([period,timestep,*limits]).all() or min(period,timestep,*limits)<=0:
        raise ValueError('FINITE_POSITIVE_GRID_AND_LIMITS_REQUIRED')
    stride=round(period/timestep) if phase=='post_physics_step' else 1
    if stride<1 or (phase=='post_physics_step' and abs(stride*timestep-period)>1e-12):
        raise ValueError('CONTROL_PHYSICS_GRID_MISMATCH')
    rows=list(rows)
    if rows and rows[0]['time_s']==0 and rows[0]['control_update_index']==-1:rows=rows[1:]
    if len(rows)!=intervals*stride:raise ValueError('INCOMPLETE_APPLIED_CONTROL_COVERAGE')
    commands=[]
    for k in range(intervals):
        block=rows[k*stride:(k+1)*stride]
        u=np.asarray([r['actual_tension_n'] for r in block],dtype=float)
        if u.shape!=(stride,len(order)) or not np.isfinite(u).all() or np.any(u<0) or np.any(u>limits):
            raise ValueError('ILLEGAL_ACTUAL_TENSION')
        for j,r in enumerate(block):
            if (not np.isfinite([r['time_s'],r.get('control_start_s',k*period),r.get('engine_time_s',r['time_s'])]).all()
                    or abs(r.get('engine_time_s',r['time_s'])-r['time_s'])>1e-10
                    or abs(r['time_s']-(k+(j+1)/stride)*period)>1e-12 or r['control_update_index']!=k
                    or ('control_start_s' in r and abs(r['control_start_s']-k*period)>1e-12)):
                raise ValueError('APPLIED_CONTROL_TIME_OR_INDEX_MISMATCH')
            command=r.get('commanded_tension_n')
            if command is not None and not np.array_equal(command,u[j]):
                raise ValueError('IDEAL_COMMAND_APPLIED_MISMATCH')
        if not np.all(u==u[0]):raise ValueError('NONCONSTANT_INTERVAL_CANNOT_RECONSTRUCT_HELD_COMMAND')
        commands.append(u[0].tolist())
    return commands


def historical():
    s56=read(ROOT/'evidence/sorosim_s56/physics/summary.json')
    results=[nmpc('evidence/sorosim_s56/physics/study',s56['nmpc'])]
    folder='evidence/sorosim_s56/physics/study';fixed=archived(folder,s56['open_loop'])
    raw=archived(folder,fixed['raw_reference']);candidate=archived(folder,fixed['candidate'])
    rows=[dict(time_s=r['time_s'],position_m=r['tip_m'],velocity_m_s=r['tip_velocity_m_s'],
        actual_tension_n=r['actual_tension_n'],qpos_rad=r['qpos_rad'],qvel_rad_s=r['qvel_rad_s'],
        control_update_index=r['control_step']-1,validity=raw['status']) for r in raw['samples']]
    value=diagnose(rows,candidate['configuration']['task']['goal']['data']['target_m'])
    value.update(route='fixed_tension',source_result=s56['open_loop'],raw_reference=fixed['raw_reference'],source_folder=folder)
    results.append(value)
    for r in read(ROOT/'evidence/sorosim_s56/rl/summary.json')['routes']:
        results.append(rl('evidence/sorosim_s56/rl/study',r['evaluation'],'evidence/sorosim_s56/rl/study',r['raw_files']))
    checkpoints=read(ROOT/'evidence/sorosim_s58/checkpoints/summary.json')
    for r in read(ROOT/'evidence/sorosim_s58/summary.json')['physical_results']:
        if r['route']=='nmpc':results.append(nmpc('evidence/sorosim_s58/study',r['reference']))
        else:
            original=archived('evidence/sorosim_s58/study',r['reference'])
            index=next(x['reference'] for x in checkpoints['rl_files'] if x['run_id']==original['run_id'])
            results.append(rl('evidence/sorosim_s58/study',r['reference'],'evidence/sorosim_s58/checkpoints/study',index))
    return dict(version='holding_diagnostic_v1',historical_only=True,results=results,
        new_provider_requests=0,new_backend_launches=0,new_physics_steps=0)


def snapshot_audit(source):
    """Read-only admission: qpos/qvel are insufficient for exact integration restore."""
    import hashlib
    import mujoco
    xml=archived(source['source_folder'],source['source_files']['robot.xml'],raw=True)
    model=mujoco.MjModel.from_xml_string(xml.decode('utf8'))
    dimensions={k:int(getattr(model,k)) for k in ('nq','nv','na','nu','neq','nmocap','nuserdata','npluginstate','nbody')}
    required=['qacc_warmstart','qfrc_applied','xfrc_applied']
    for dimension,fields in [('na',['act']),('nu',['ctrl']),('neq',['eq_active']),
            ('nmocap',['mocap_pos','mocap_quat']),('nuserdata',['userdata']),('npluginstate',['plugin_state'])]:
        if dimensions[dimension]:required+=fields
    sample=source['timeline'][28]
    missing=[k for k in required if k not in sample]
    return dict(status='not_restorable',selected_time_s=sample['time_s'],source_result=source['source_result'],
        model_xml_sha256=hashlib.sha256(xml).hexdigest(),model_dimensions=dimensions,
        complete_qpos_qvel_dimensions=(len(sample['qpos_rad'])==model.nq and len(sample['qvel_rad_s'])==model.nv),
        source_files=source['source_files'],present_partial_fields=['time_s','qpos_rad','qvel_rad_s','actual_tension_n'],
        missing_integration_fields=missing,empty_fields_checked_from_model=True,
        required_identity_checks=['robot.xml hash','complete model dimensions','tendon order','world coordinates','actual ideal tensions'],
        reason='No saved mjSTATE_INTEGRATION vector or equivalent complete snapshot. Named joint positions/velocities and projected GVS state do not prove complete restore. No fields defaulted to zero.',
        paired_probe_launches=0,attempted_physics_steps=0,prefix_replay_steps=0,retries=0,
        prediction_supported_by_probe=None,task_evaluations=0)
