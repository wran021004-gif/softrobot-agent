"""Portable integrity, physics binding and saved-state checks; zero mj_step calls."""
import argparse
import json
from pathlib import Path

import mujoco
import numpy as np
from package_io import read,write,sha,digest,csv_read,joint_map,restore,compare_timestep,observation


def require(condition, message):
    if not condition:raise ValueError(message)


def physical_fingerprint(model):
    """Exclude optional task_target site; retain every dynamic and routing field."""
    fields=('body_parentid','body_pos','body_quat','body_mass','body_ipos','body_inertia','body_iquat',
        'jnt_type','jnt_bodyid','jnt_pos','jnt_axis','jnt_stiffness','dof_damping',
        'geom_type','geom_bodyid','geom_pos','geom_quat','geom_size','geom_contype','geom_conaffinity',
        'geom_friction','geom_solref','geom_solimp','mesh_vert','mesh_face',
        'actuator_trnid','actuator_gainprm','actuator_gear','actuator_ctrlrange','actuator_forcerange')
    value={k:getattr(model,k).tolist() for k in fields}
    value['options']=dict(timestep=float(model.opt.timestep),gravity=model.opt.gravity.tolist(),
        integrator=int(model.opt.integrator),solver=int(model.opt.solver),iterations=int(model.opt.iterations))
    value['routing']=[dict(name=model.tendon(i).name,sites=[dict(name=model.site(int(model.wrap_objid[j])).name,
        body=model.body(int(model.site_bodyid[int(model.wrap_objid[j])])).name,
        position=model.site_pos[int(model.wrap_objid[j])].tolist()) for j in
        range(model.tendon_adr[i],model.tendon_adr[i]+model.tendon_num[i])]) for i in range(model.ntendon)]
    return digest(value)


def validate_trajectory(root,entry):
    key=entry['benchmark'];base=root/key;folder=root/entry['directory']
    model=mujoco.MjModel.from_xml_path(str(base/'robot.xml'));mapping=read(base/'joint_map.json')
    require(mapping==joint_map(model,[j['name'] for j in mapping['joints']]),'JOINT_OR_CHANNEL_MAP_CHANGED')
    require(model.ntendon==model.nu==6,'SIX_TENDONS_REQUIRED')
    require(mapping['actuator_order']==[t+'_direct_tension' for t in mapping['tendon_order']],'ACTUATOR_ORDER')
    for i in range(model.ntendon):
        adr=model.tendon_adr[i];sid=int(model.wrap_objid[adr])
        require(model.wrap_type[adr]==mujoco.mjtWrap.mjWRAP_SITE,'TENDON_START_MUST_BE_SITE')
        require(model.body(int(model.site_bodyid[sid])).name=='fixed_base','TENDON_START_NOT_FIXED_BASE')
    structure=read(base/'structure.json');task=read(folder/'task.json');definition=task['definition']
    provenance=read(folder/'provenance.json');artifacts={}
    for kind,ref in provenance['references'].items():
        artifact=root/'evidence/artifacts'/(ref['artifact_id']+'.json')
        require(sha(artifact)==ref['artifact_id'],'ORIGINAL_ARTIFACT_CONTENT_IDENTITY')
        artifacts[kind]=read(artifact)
    result=artifacts['reference'];raw=artifacts['raw'];profile=artifacts['profile'];evaluation=artifacts['evaluation']
    require(result['acceptance']==task['historical_acceptance'],'HISTORICAL_RESULT_BINDING')
    require(artifacts['candidate']['configuration']==read(folder/'configuration.json'),'CONFIGURATION_BINDING')
    require(artifacts['candidate']['configuration']['task']==definition,'FROZEN_TASK_BINDING')
    require(raw['samples']==read(folder/'original_samples.json'),'ORIGINAL_SAMPLES_BINDING')
    require(raw['xml_sha256']==provenance['original_xml_sha256'],'ORIGINAL_XML_BINDING')
    refs=provenance['references']
    require(result['candidate']==raw['candidate']==refs['candidate'] and
        result['source_reference']==raw['source_reference']==refs['source'] and
        result['raw_reference']==evaluation['source']==profile['simulation']==refs['raw'] and
        result['evaluation_reference']==profile['evaluation']==refs['evaluation'] and
        result['profile_reference']==refs['profile'],'ORIGINAL_RECEIPT_CHAIN')
    receipt=read(folder/'original_receipt.json')
    require(receipt['execution_id']==result['execution_id']==profile['execution_id'],'RECEIPT_EXECUTION')
    require(digest(structure['design'])==structure['design_identity'],'DESIGN_IDENTITY')
    require(digest(definition)==task['task_identity'],'TASK_IDENTITY')
    require(sha(base/'robot.xml')==structure['xml_sha256'],'XML_IDENTITY')
    require(physical_fingerprint(model)==entry['compiled_physical_identity'],'COMPILED_MODEL_IDENTITY')
    require(all(t['points'][0]['attachment']['part']=='fixed_base' and t['points'][0]['role']=='start'
        for t in structure['design']['tendons']),'DESIGN_BASE_RULE')
    timing=definition['timing'];dt=timing['timestep_s'];duration=timing['duration_s']
    require(dt==model.opt.timestep==entry['timestep_s'],'TIMESTEP')
    rows=csv_read(folder/'trajectory_timestep.csv');schedule=csv_read(folder/'control_schedule.csv')
    reference=csv_read(folder/'reference.csv')
    require(len(rows)==round(duration/dt)+1==entry['rows'],'ROW_COUNT')
    for name,table in [('trajectory',rows),('control',schedule),('reference',reference)]:
        require(bool(table) and all(np.isfinite(list(r.values())).all() for r in table),name+'_NONFINITE')
    times=np.array([r['time_s'] for r in rows])
    require(times[0]==0 and np.max(np.abs(times-np.arange(len(rows))*dt))<1e-11,'TIME_GRID')
    require(np.all(np.diff(times)>0) and abs(times[-1]-duration)<1e-11,'TIME_COVERAGE')
    require(len(schedule)==round(duration/timing['control_period_s']),'CONTROL_COUNT')
    require(len(reference)==len(rows),'REFERENCE_GRID')
    expected_controls=['control_interval_index','start_s','end_s',*mapping['requested_tension_columns']]
    require(list(schedule[0])==expected_controls,'CONTROL_COLUMNS')
    for k,r in enumerate(schedule):
        require(r['control_interval_index']==k and abs(r['start_s']-k*timing['control_period_s'])<1e-12
            and abs(r['end_s']-(k+1)*timing['control_period_s'])<1e-12,'CONTROL_GRID')
        command=np.array([r[c] for c in mapping['requested_tension_columns']])
        require(command.tolist()==artifacts['source']['trajectory']['tensions_n'][k],'ORIGINAL_CONTROL_BINDING')
        require(np.all(command>=model.actuator_ctrlrange[:,0]) and np.all(command<=model.actuator_ctrlrange[:,1]),'CONTROL_BOUNDS')
    data=mujoco.MjData(model);tip=model.site('tip_site').id;max_pose=0.;max_velocity=0.
    force_def=definition['environment']['data'].get('external_forces',[])
    expected=observation(model,mujoco.MjData(model),0,-1,mapping,task['tool_axis_local'],sorted({f['entity'] for f in force_def}))
    require(set(rows[0])==set(expected),'TRAJECTORY_COLUMNS')
    for index,row in enumerate(rows):
        require(row['step_index']==index,'STEP_INDEX')
        interval=-1 if index==0 else (index-1)//round(timing['control_period_s']/dt)
        require(row['control_interval_index']==interval,'CONTROL_INTERVAL_INDEX')
        for c in mapping['requested_tension_columns']:
            require(row[c]==(0 if interval<0 else schedule[interval][c]),'STEP_CONTROL')
        require(max(abs(row[a]-row[b]) for a,b in zip(mapping['actual_tension_columns'],mapping['requested_tension_columns']))<1e-9,'ACTUAL_TENSION')
        restore(model,data,row,mapping)
        position=np.array([row['tip_position_m_'+a] for a in 'xyz'])
        rotation=np.array([[row[f'tip_rotation_r{i}{j}'] for j in range(3)] for i in range(3)])
        max_pose=max(max_pose,float(np.max(np.abs(data.site_xpos[tip]-position))),
            float(np.max(np.abs(data.site_xmat[tip].reshape(3,3)-rotation))))
        jac=np.zeros((3,model.nv));mujoco.mj_jacSite(model,data,jac,None,tip)
        max_velocity=max(max_velocity,float(np.max(np.abs(jac@data.qvel-[row['tip_velocity_m_s_'+a] for a in 'xyz']))))
        require(np.max(np.abs(rotation@task['tool_axis_local']-[row['tool_axis_world_'+a] for a in 'xyz']))<1e-12,'TOOL_AXIS')
        force=np.zeros(3);by_body={f['entity']:np.zeros(3) for f in force_def}
        # Force columns describe the force held for the PRECEDING step, t=0 is the initial buffer.
        tick=max(0,index-1)
        for f in force_def:
            if round(f['start_s']/dt)<=tick<round(f['end_s']/dt):by_body[f['entity']]+=f['force_n']
        for body,value in by_body.items():
            force+=value
            require(np.max(np.abs(value-[row['external_force_n__'+body+'_'+a] for a in 'xyz']))<1e-12,'BODY_COM_FORCE')
        require(np.max(np.abs(force-[row['external_force_n_'+a] for a in 'xyz']))<1e-12,'WORLD_FORCE')
        require(row['post_state_contact_count']==data.ncon,'CONTACT_CACHE')
    require(max_pose<1e-12 and max_velocity<1e-12,'POST_STATE_KINEMATICS')
    initial=read(folder/'replay_spec.json')['scene']
    require([rows[0][j['qpos_column']] for j in mapping['joints']]==initial['qpos_rad'],'INITIAL_QPOS')
    require([rows[0][j['qvel_column']] for j in mapping['joints']]==initial['qvel_rad_s'],'INITIAL_QVEL')
    errors=compare_timestep(read(folder/'original_samples.json'),rows,mapping,timing['control_period_s'],dt)
    validation=read(folder/'validation.json')
    require(validation['historical_acceptance']['accepted'] is True,'HISTORICAL_ACCEPTANCE')
    require(errors==validation['timestep_comparison_max_abs'],'RECORDED_DIAGNOSTICS')
    if key=='M6':
        tool=definition['goal']['data']['rigid_tool'];bid=model.body(tool['body']).id
        r=np.empty(9);mujoco.mju_quat2Mat(r,model.body_iquat[bid]);r=r.reshape(3,3)
        require(abs(model.body_mass[bid]-.02)<1e-12,'TOOL_MASS')
        require(np.max(np.abs(model.body_ipos[bid]-tool['com_local_m']))<1e-12,'TOOL_COM')
        require(np.max(np.abs(r@np.diag(model.body_inertia[bid])@r.T-tool['inertia_com_local_kg_m2']))<1e-12,'TOOL_FULL_INERTIA')
        require(model.body_jntnum[bid]==0 and model.site_bodyid[tip]==bid,'TOOL_RIGID_BINDING')
        require(all(r['integration_cache_contact_count']==0 and r['post_state_contact_count']==0 for r in rows),'M6_CONTACT')
    return dict(benchmark=key,condition=entry['condition'],integrity='passed',
        reproduction='consistent' if max(errors.values())<=1e-9 else 'reproduction_unverified',
        rows=len(rows),timestep_s=dt,maximum_pose_error=max_pose,maximum_velocity_error=max_velocity,
        original_comparison=errors,physics_steps=0)


def validate(root):
    manifest=read(root/'manifest.json');failures=[];results=[]
    expected={'M1':{'central_high','positive_high','negative_low'},'M2':{'zero','positive','negative'},
        **{k:{'default'} for k in ('M3','M4','M5','M6')}}
    require(len(manifest['trajectories'])==10,'TEN_TRAJECTORIES_REQUIRED')
    require({k:{e['condition'] for e in manifest['trajectories'] if e['benchmark']==k} for k in expected}==expected,'CONDITIONS')
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and
        p.name!='manifest.json' and '__pycache__' not in p.parts and '.viewer-env' not in p.parts}
    require(actual==set(manifest['files']),'UNMANIFESTED_OR_MISSING_FILES')
    for relative,identity in manifest['files'].items():
        path=(root/relative).resolve();require(path.is_relative_to(root.resolve()),'UNSAFE_MANIFEST_PATH')
        require(sha(path)==identity,'SHA256_MISMATCH:'+relative)
    for key in ('M1','M2'):
        entries=[e for e in manifest['trajectories'] if e['benchmark']==key]
        require(len({e['compiled_physical_identity'] for e in entries})==1,'CONDITION_PHYSICAL_MODEL_MISMATCH')
    for entry in manifest['trajectories']:
        try:results.append(validate_trajectory(root,entry))
        except Exception as exc:failures.append(dict(benchmark=entry['benchmark'],condition=entry['condition'],error=str(exc)))
    return dict(status='passed' if not failures else 'failed',results=results,failures=failures,physics_steps=0,
        reproduction_status='consistent' if not failures and all(r['reproduction']=='consistent' for r in results) else 'reproduction_unverified',
        interpretation='Integrity and reproduction are independent of historical scientific acceptance.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--report',type=Path)
    args=p.parse_args()
    try:report=validate(args.package.resolve())
    except Exception as exc:report=dict(status='failed',failures=[str(exc)],physics_steps=0)
    if args.report:write(args.report,report)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if report['status']!='passed':raise SystemExit(1)


if __name__=='__main__':main()
