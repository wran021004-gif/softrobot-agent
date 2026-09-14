"""Deterministic entity/time evidence, shared by LLM and HTML; never simulates."""
import gzip
import json
from pathlib import Path
import numpy as np
from tools.state_io import read, atomic_json

RULES=dict(version='reach_events_v2',near_force_fraction=.99,zero_force_n=.001,min_duration_s=.05,
           tracking_error_m=.001,small_length_range_m=.001,small_joint_motion_rad=.005,
           slow_velocity_rad_s=.05,large_penetration_m=.002)


def load_rows(path):
    with gzip.open(path,'rt',encoding='utf8') as f: return json.load(f)


def intervals(mask,times):
    ids=np.flatnonzero(mask)
    if not len(ids): return []
    groups=np.split(ids,np.where(np.diff(ids)>1)[0]+1)
    return [g for g in groups if times[g[-1]]-times[g[0]]>=RULES['min_duration_s']-1e-10]


def diagnose(path,metadata,entity='all',t_start_s=None,t_end_s=None,fields=None):
    rows=load_rows(path)
    if not rows: return dict(status='NOT_RECORDED',events=[],queries=[])
    state_t=np.array([r['time_s'] for r in rows]); force_t=np.array([r['solver_time_s'] for r in rows])
    if t_start_s is None: t_start_s=float(min(state_t[0],force_t[0]))
    if t_end_s is None: t_end_s=float(max(state_t[-1],force_t[-1]))
    fields=fields or []; events=[]; queries=[]; p=metadata
    def record(name,idx,t,ids,kind,values,units,rule,interpretation,observed):
        return dict(run_id=p['run_id'],candidate_id=p['candidate_id'],backend=p['backend'],model_id=p['model_id'],
          entity_name=name,entity_index=idx,t_start_s=float(t[ids[0]]),t_end_s=float(t[ids[-1]]),
          sample_indices=[int(ids[0]),int(ids[-1])],observed_fields=observed,values=values,units=units,
          event_type=kind,detection_rule=rule,evidence_ref=str(path),interpretation=interpretation,
          confidence_or_status='OBSERVED_SAMPLED',diagnostic_version=RULES['version'],
          time_phase='solver' if t is force_t else 'post_step_state')
    lengths=np.array([r['solver_tendon_length_m'] for r in rows]); forces=-np.array([r['solver_actuator_force_n'] for r in rows]);
    commands=np.array([r['command_m'] for r in rows]); limit=p['force_limit_n']; kp=p['kp']
    fm=(force_t>=t_start_s-1e-10)&(force_t<=t_end_s+1e-10)
    sm=(state_t>=t_start_s-1e-10)&(state_t<=t_end_s+1e-10)
    for j in range(forces.shape[1]):
      name=f'tendon_{j}'
      if entity not in ('all',name): continue
      ids=np.flatnonzero(fm)
      if not len(ids): continue
      demand=kp*(lengths[:,j]-commands[:,j]); err=lengths[:,j]-commands[:,j]
      values=dict(raw_force_min_n=float(-forces[ids,j].max()),tension_min_n=float(forces[ids,j].min()),
          tension_max_n=float(forces[ids,j].max()),force_limit_n=limit,command_start_m=float(commands[ids[0],j]),
          command_end_m=float(commands[ids[-1],j]),path_min_m=float(lengths[ids,j].min()),path_max_m=float(lengths[ids,j].max()),
          reference_length_m=p['reference_length_m'],unclipped_demand_min_n=float(demand[ids].min()),unclipped_demand_max_n=float(demand[ids].max()),
          max_abs_tracking_error_m=float(abs(err[ids]).max()),positive_tension_sign='-raw_actuator_force',
          initial_route_offset_yz_m=p['offsets'][j],length_rate_sampled_max_abs_m_s=float(np.max(np.abs(np.gradient(lengths[:,j],force_t))[ids])) if len(rows)>1 else None)
      queries.append(record(name,j,force_t,ids,'WINDOW_SUMMARY',values,{'length':'m','force':'N','time':'s'},'inclusive saved solver-time interval',
          'Length servo demand and output share solver phase. Zero force is the no-push end; slack is not independently measured.',
          ['solver_tendon_length_m','command_m','solver_actuator_force_n']))
      for mask,kind,rule,interpretation in [
        (forces[:,j]>=.99*limit,'MAX_PULL',f'T >= {0.99*limit} N for >= .05 s','Sustained near maximum pull.'),
        (forces[:,j]<=RULES['zero_force_n'],'NO_PUSH_END','T <= .001 N for >= .05 s','No positive pull; not maximum-pull saturation.'),
        (abs(err)>.001,'TRACKING_ERROR','abs(path-command) > .001 m for >= .05 s','Tracking difference alone does not establish a mechanical block.')]:
        for g in intervals(mask&fm,force_t):
          events.append(record(name,j,force_t,g,kind,dict(tension_min_n=float(forces[g,j].min()),tension_max_n=float(forces[g,j].max()),
            tracking_error_min_m=float(err[g].min()),tracking_error_max_m=float(err[g].max())),{'tension':'N','tracking_error':'m'},rule,interpretation,
            ['solver_tendon_length_m','command_m','solver_actuator_force_n']))
      for g in intervals((commands[:,j]>p['reference_length_m']+.001)&(forces[:,j]<=.001)&fm,force_t):
        span=float(np.ptp(lengths[g,j]))
        if span<=.001:
          events.append(record(name,j,force_t,g,'RELEASE_WITH_SMALL_PATH_CHANGE',dict(path_range_m=span,command_min_m=float(commands[g,j].min()),
            tension_max_n=float(forces[g,j].max())),{'length':'m','force':'N'},'command > L_ref+.001m; T<=.001N; path range<=.001m; duration>=.05s',
            'Release command supplies no pushing force. Absence of an extending external force is a hypothesis; mechanical lock is not established.',
            ['command_m','solver_tendon_length_m','solver_actuator_force_n']))
    q=np.array([r['qpos_rad'] for r in rows]); v=np.array([r['qvel_rad_s'] for r in rows]); ids=np.flatnonzero(sm)
    for j in range(q.shape[1]):
      name=p['joint_names'][j]
      if entity not in ('all',name) or not len(ids): continue
      vals=dict(angle_min_rad=float(q[ids,j].min()),angle_max_rad=float(q[ids,j].max()),angle_final_rad=float(q[ids[-1],j]),
        velocity_max_abs_rad_s=float(abs(v[ids,j]).max()),velocity_final_rad_s=float(v[ids[-1],j]),natural_angle_rad=p['natural'][j],
        stiffness_nm_rad=p['stiffness'][j],damping_nm_s_rad=p['damping'][j],joint_limit='NOT_CONFIGURED')
      queries.append(record(name,j,state_t,ids,'WINDOW_SUMMARY',vals,{'angle':'rad','velocity':'rad/s','stiffness':'N m/rad','damping':'N m s/rad'},
          'inclusive post-step state-time interval','State phase is separate from solver force phase. No joint limit is configured.', ['qpos_rad','qvel_rad_s']))
      if np.ptp(q[ids,j])<.005:
        events.append(record(name,j,state_t,ids,'SMALL_MOTION',vals,{'angle':'rad'},'angle range < .005 rad', 'Small sampled joint motion; no causal attribution.', ['qpos_rad']))
      if abs(v[ids[-1],j])>.05:
        events.append(record(name,j,state_t,ids,'RESIDUAL_MOTION',vals,{'velocity':'rad/s'},'abs(final velocity) > .05 rad/s', 'Motion remains at window end.', ['qvel_rad_s']))
      curvature_share=abs(q[:,j])/np.maximum(np.sum(abs(q),axis=1),1e-12)
      for g in intervals((curvature_share>.5)&(abs(q[:,j])>.1)&sm,state_t):
        events.append(record(name,j,state_t,g,'LOCAL_BENDING_CONCENTRATION',dict(max_angle_share=float(curvature_share[g].max()),
          angle_min_rad=float(q[g,j].min()),angle_max_rad=float(q[g,j].max())),{'angle':'rad','share':'1'},
          'abs(q_j)/sum(abs(q)) > .5 and abs(q_j)>.1 rad for >=.05s','More than half of sampled absolute joint bending is concentrated here.', ['qpos_rad']))
    contact_counts=[r['solver_contact_count'] for r in rows]
    if entity in ('all','contact'):
      for g in intervals((np.array(contact_counts)>0)&fm,force_t):
        events.append(record('contact',0,force_t,g,'CONTACT',dict(max_contact_count=int(max(np.array(contact_counts)[g])),
            contact_force_status='RECORDED' if 'contacts' in rows[0] else 'APPROXIMATE_NORMAL_ONLY' if 'normal_contact_approx_n' in rows[0] else 'NOT_RECORDED'),
            {'count':'1'},'contact_count>0 for >=.05s','Consult contact pairs at solver time; historical count alone contains no force.', ['solver_contact_count']))
    selected=np.flatnonzero(sm | fm)
    raw={}
    for f in fields:
        raw[f]=[dict(sample_index=int(i),time_s=rows[i]['time_s'],solver_time_s=rows[i]['solver_time_s'],value=rows[i].get(f,'NOT_RECORDED')) for i in selected]
    return dict(status='completed' if queries or events else 'NO_EVENT' if entity=='contact' and fm.any() else 'NOT_RECORDED',events=events,queries=queries,raw_fields=raw,
        ground_nearest_initial_tendon=f"tendon_{int(np.argmin(np.array(p['offsets'])[:,1]))}",
        ground_mapping_rule='minimum actual initial route z; initial qpos=0; fixed base offsets and segment routes coincide in z',
        numerical=dict(last_valid_time_s=float(state_t[-1]),remaining_duration_s=max(0,p['duration_s']-float(state_t[-1])) if p.get('duration_s') is not None else None,
            duration_status='DECLARED' if p.get('duration_s') is not None else 'NOT_RECORDED',
            finite=bool(np.isfinite(q).all() and np.isfinite(v).all())),rules=RULES,
        limitations=['sampled extrema are not continuous-time bounds','old unrecorded fields remain NOT_RECORDED','no causal attribution from counts alone'])


def metadata_from_shared(shared,cid,backend,run_id):
    p=shared;n=len(p['mass']); planar=backend=='matlab'
    return dict(candidate_id=cid,backend=backend,run_id=run_id,duration_s=p.get('duration'),model_id=p['model_id'] if planar else 'mujoco_segmented',
        force_limit_n=p['fmax'],kp=p['kp'],reference_length_m=p['length'],offsets=p['offsets'],
        joint_names=[f'joint_{i}_{a}' for i in range(n) for a in (['y'] if planar else ['y','z'])],
        natural=p['natural'] if planar else [v for a in p['natural'] for v in (a,0)],
        stiffness=p['stiffness'] if planar else [v for a in p['stiffness'] for v in (a,a)],
        damping=p['damping'] if planar else [v for a in p['damping'] for v in (a,a)])


def historical_audit(source,output):
    source=Path(source); state=read(source/'state.json'); reports=[]
    import yaml
    for c in state['candidates']:
        ev=read(source/c['evaluate_candidate_ref'])['data']; folder=source/ev['run']; ir=yaml.safe_load((folder/'robot_ir.yaml').read_text())
        p=ir['mechanics'];n=ir['section']['segments']
        meta=dict(run_id=source.name,candidate_id=c['candidate_id'],backend='mujoco',model_id='mujoco_legacy_v1',force_limit_n=p['tendon_force_limit_n'],
          kp=p['tendon_servo_kp_n_per_m'],reference_length_m=ir['section']['length_m'],offsets=[r['offset_yz_m'] for r in ir['tendon_routes']],
          joint_names=[f'joint_{i}_{a}' for i in range(n) for a in ['y','z']],natural=[0]*(2*n),stiffness=[p['joint_stiffness_nm_per_rad']]*(2*n),damping=[p['joint_damping_nm_s_per_rad']]*(2*n))
        report=diagnose(folder/'trajectory.json.gz',meta); path=output/f"{c['candidate_id']}_diagnosis.json";atomic_json(path,report)
        reports.append(dict(candidate_id=c['candidate_id'],design_hash=c['design_hash'],position_error_m=ev['position_error_m'],
            actual_tip_m=ev['actual_tip_m'],model_tip_m=ev['model_tip_m'],diagnostic_ref=str(path),source_run=str(folder)))
    audit=dict(source=str(source),source_state_sha256=__import__('hashlib').sha256((source/'state.json').read_bytes()).hexdigest(),
        status=state['status'],model_calls_total=len(state['model_calls']),round_budget=state['request'].get('round_budget'),candidates=reports,
        interpretation='PCC misses gravity, independent bending and contact. Historical task failure does not establish geometric impossibility or insufficient actuator capacity.')
    atomic_json(output/'audit.json',audit);return audit
