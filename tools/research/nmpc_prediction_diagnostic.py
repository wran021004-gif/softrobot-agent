"""Archive-only physical case admission and signed one-interval output diagnosis."""
import gzip
import json

import numpy as np

from tools.platform_store import plain
from tools.state_io import digest
from tools.research.design import full_science
from tools.research.matched_state import _vectors
from tools.research.numerics import archived, execution_source
from tools.research.state import save, state, update


def archive_index(folder, reference, indices=(0, 19, 29)):
    """Recover exact indexed measurements; never load or step a physical backend."""
    source=execution_source(dict(reference=plain(reference)),folder)
    result=source['result'];files=source['files']
    candidate=archived(folder,result['candidate']);cfg=candidate['configuration']
    control=archived(folder,files['control_spec.json'])
    physics=archived(folder,files['resolved_physics.json'])
    scene=archived(folder,files['experiment_scene.json'])
    observations=archived(folder,files['controller_observations.json'])
    commands=archived(folder,files['actual_commands.json'])
    motion=archived(folder,result['profile']['motion'])
    trajectory=json.loads(gzip.decompress(archived(folder,files['trajectory.json.gz'],raw=True)))
    spec=control['specification'];order=spec['coordinate_order'];dt=cfg['task']['timing']['control_period_s']
    if (candidate['scientific_configuration']!=full_science(cfg) or control['task']!=cfg['task']
            or control['robot']!=cfg['robot'] or scene['physics_identity']!=physics['identity']
            or spec['tendon_order']!=[t['entity'] for t in physics['tendons']]
            or control['projector']['coordinate_order']!=order or len(order)!=12 or dt!=.01
            or len(observations)!=35 or len(trajectory)!=35 or len(motion)!=35 or len(commands)!=35):
        raise ValueError('ARCHIVED_PREDICTION_IDENTITY_OR_COVERAGE_MISMATCH')
    cases=[]
    for k in indices:
        o=observations[k];after=motion[k];raw=trajectory[k];command=commands[k]
        before=motion[k-1] if k else dict(time_s=0.,tip_position_m=o['tip_position_m'],tip_velocity_m_s=[0.]*3)
        # Initial velocity is exactly zero from the archived physical joint state.
        if not k and any(scene['qvel_rad_s']):raise ValueError('INITIAL_PHYSICAL_VELOCITY_UNAVAILABLE')
        if (o['phase']!='current_state_before_integration'
                or any(abs(row['time_s']-t)>1e-12 for row,t in
                    ((o,k*dt),(command,k*dt),(before,k*dt),(after,(k+1)*dt),(raw,(k+1)*dt)))
                or o['tip_position_m']!=before['tip_position_m'] or raw['tip_m']!=after['tip_position_m']
                or o['actual_tension_n']!=raw['tension_n'] or command['desired_tension_n']!=raw['desired_tension_n']
                or o['measured_initial_state']!=o['gvs_q']+o['gvs_qdot'] or len(o['measured_initial_state'])!=24):
            raise ValueError('ARCHIVED_PREDICTION_TIME_STATE_OR_ACTION_MISMATCH')
        tension=np.asarray(raw['tension_n'])
        if (tension.shape!=(4,) or not np.isfinite(tension).all() or np.any(tension<0) or np.any(tension>8)):
            raise ValueError('ARCHIVED_APPLIED_TENSION_INVALID')
        facts=o.get('mathematical_facts');prediction=o.get('one_step_prediction') if o['plan_accepted'] and not o['failure_response_used'] else None
        from extensions.tendon_family.gvs_projection import project
        q,v=(scene['qpos_rad'],scene['qvel_rad_s']) if k==0 else (trajectory[k-1]['qpos_rad'],trajectory[k-1]['qvel_rad_s'])
        projection=project(physics,cfg['robot']['structure']['data'],q,v,
            basis=control['projector']['resolved_basis']['specification'],convention=control['projector']['id'])
        if not np.allclose(projection['q_gvs']+projection['qdot_gvs'],o['measured_initial_state'],rtol=0,atol=1e-10):
            raise ValueError('ARCHIVED_PROJECTION_RECONSTRUCTION_MISMATCH')
        if facts and (facts['model_identity']!=spec['identity'] or facts['initial_state']!=o['measured_initial_state']):
            raise ValueError('ARCHIVED_PLAN_MODEL_OR_INITIAL_STATE_MISMATCH')
        if prediction and (prediction['frame']!='world' or prediction['prediction_source']!='accepted_plan'
                or abs(prediction['time_s']-(k+1)*dt)>1e-12 or prediction['integration']!='implicit_euler'
                or prediction['state']!=facts['states'][prediction['substeps']]
                or prediction['tip_position_m']!=facts['tip_positions'][prediction['substeps']-1]
                or prediction['tip_velocity_m_s']!=facts['tip_velocities'][prediction['substeps']-1]):
            raise ValueError('ARCHIVED_ACCEPTED_PREDICTION_SEMANTICS_MISMATCH')
        cases.append(dict(update_index=k,time_s=k*dt,end_time_s=(k+1)*dt,initial_state=o['measured_initial_state'],
            before=before,after=after,applied_tension_n=raw['tension_n'],requested_tension_n=o['requested_tension_n'],
            selected_tension_n=facts['tensions'][0] if prediction else None,accepted_prediction=prediction,
            accepted_action_equals_applied=bool(prediction and np.allclose(facts['tensions'][0],tension,rtol=0,atol=1e-12)),
            plan_source=o['plan_source'],fallback=o['failure_response_used'],
            projection_residual_max_rad_m=o['gvs_projection_residual_max_rad_m'],
            projection_reconstruction=projection,
            rate_projection_residual_rad_m_s=before.get('rate_projection_residual_rad_m_s',0. if k==0 else None),
            initial_velocity_source='archived zero joint velocity' if k==0 else 'archived post-step motion at index k-1',
            physical_state_before=scene['initial'] if k==0 else {key:trajectory[k-1][key] for key in ('qpos_rad','qvel_rad_s')},
            observation_pointer='/'+str(k),physical_target_pointer='/'+str(k),prediction_missing=prediction is None))
    return dict(source_kind='archived_nmpc_prediction_cases_v1',source_folder=folder,source_execution=plain(reference),
        source_study=result['owning_study'],execution_id=result['execution_id'],candidate=result['candidate'],
        scientific_configuration=candidate['scientific_configuration'],model_identity=spec['identity'],
        task_identity=digest(cfg['task']),physics_identity=physics['identity'],specification=spec,
        projector=control['projector'],tendon_order=spec['tendon_order'],coordinate_order=order,
        period_s=dt,cases=cases,source_files=files,motion_reference=result['profile']['motion'],
        historical_acceptance=result['acceptance'],new_physical_steps=0)


def import_index(host, folder, reference):
    value=archive_index(folder,reference)
    ref=save(host,value,'archived_nmpc_case_index')
    update(host,scoped_context=list({r['artifact_id']:r for r in [*state(host).get('scoped_context',[]),ref]}.values()))
    return ref


def admitted_case(host, query, cfg):
    ref=plain(query.source);index=host.store.artifact(ref)
    if ref not in state(host).get('scoped_context',[]) or index.get('source_kind')!='archived_nmpc_prediction_cases_v1':
        raise ValueError('IMPORTED_ARCHIVED_NMPC_INDEX_REQUIRED')
    # Re-admit from sealed source bytes, rather than trusting editable intermediate data.
    if index!=archive_index(index['source_folder'],index['source_execution'],tuple(c['update_index'] for c in index['cases'])):
        raise ValueError('ARCHIVED_CASE_INDEX_CHANGED')
    if full_science(cfg)!=index['scientific_configuration']:
        raise ValueError('PREDICTION_CANDIDATE_TASK_MODEL_OR_CONTROLLER_MISMATCH')
    case=next(c for c in index['cases'] if c['update_index']==query.update_index)
    return index,case


def compare_outputs(raw, case):
    result={}
    for field,key in (('position','tip_positions_m'),('velocity','tip_velocities_m_s')):
        physical='tip_position_m' if field=='position' else 'tip_velocity_m_s'
        start=np.asarray(raw[key][0])-case['before'][physical]
        row=dict(e_projection=start.tolist(),e_initial=start.tolist(),projection_norm=float(np.linalg.norm(start)))
        if raw['complete']:
            row.update(_vectors(dict(start=raw[key][0],end=raw[key][1]),
                dict(start=np.asarray(case['before'][physical]),end=np.asarray(case['after'][physical]))))
            row['decomposition_residual_inf']=float(np.max(np.abs(np.asarray(row['e_one_step'])-row['e_initial']-np.asarray(row['e_increment']))))
        result[field]=row
    prediction=case['accepted_prediction']
    if raw['complete'] and prediction:
        result['archived_prediction_difference']={key:(np.asarray(raw[out][1])-prediction[key]).tolist()
            for key,out in (('tip_position_m','tip_positions_m'),('tip_velocity_m_s','tip_velocities_m_s'),('state','states'))}
        result['same_original_experiment']=case['accepted_action_equals_applied'] and raw['substeps']==prediction['substeps']
    return result


def interval_identity(index, case):
    return digest(dict(model=index['model_identity'],task=index['task_identity'],period_s=index['period_s'],
        coordinates=index['coordinate_order'],tendons=index['tendon_order'],
        initial_state=case['initial_state'],tension_n=case['applied_tension_n']))
