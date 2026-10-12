"""Bounded repair milestone on the existing host, ledger and archive lifecycle."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import time
import numpy as np
from tools import research_core as core
from tools import research_core_numerics as numerics
from tools.platform_host import Host
from tools.state_io import digest, atomic_json

SPEC=core.ROOT/'examples/numerical_repair/specification.json'
DIAG='evidence/numerical_diagnosis_20261011'


def reference(value):
    if len(value)==64 and all(c in '0123456789abcdef' for c in value):return dict(artifact_id=value,media_type='application/json')
    return json.loads(value)


def history_inputs(host, *, folder=None, execution_id=None, offline_execution_id=None, updates=(29,19)):
    if folder is not None:
        if core.state(host).get('repair_history'):return core.state(host)['repair_history']
        summary=core.read(core.ROOT/folder/'scientific_summary.json')
        row=next(r for r in summary['physical'] if r['execution_id']==execution_id)
        source=numerics.execution_source(row,folder)
        candidate=numerics.archived(folder,source['result']['candidate'])
        observations=numerics.archived(folder,source['files']['controller_observations.json'])
        records={}
        for index in updates:
            record=deepcopy(observations[index]['complete_update_record'])
            definition=record['resolved_problem_reference'];ref=source['files'][definition['filename']]
            if ref['artifact_id']!=definition['sha256']:raise ValueError('SAVED_PROBLEM_IDENTITY_MISMATCH')
            record['resolved_problem_archive']=dict(folder=folder,reference=ref)
            records[str(index)]=numerics.imported_record(host,candidate['configuration'],record,
                dict(study_id=summary['study_id'],folder=folder,execution_id=execution_id,update_id=index))
        offline=next(r for r in summary['mechanics'] if r['execution_id']==offline_execution_id)
        value=numerics.archived(folder,offline['reference'])
        value.update(imported_historical_evidence=True,source_reference=offline['reference'],source_archive=folder,
            additional_numerical_s=0.,confirmation_eligible=False)
        ref=core.save(host,value,'imported_archived_mechanics')
        info=dict(records=records,mechanics=ref,source_execution=execution_id,source_archive=folder,
            resolved_profile=source['files']['resolved_control.json'] if 'resolved_control.json' in source['files'] else None)
        core.update(host,repair_history=info,imported_mechanics_sources=[*core.state(host).get('imported_mechanics_sources',[]),ref])
        return info
    info=numerics.import_history(host)
    summary=core.read(core.ROOT/numerics.HISTORY/'scientific_summary.json')
    row=next(r for r in summary['closed_loop'] if r['execution_id']=='d42321543b9a45bb97b3ff28aca097ae')
    source=numerics.execution_source(row)
    observations=numerics.archived(numerics.HISTORY,source['files']['controller_observations.json'])
    samples=json.loads(gzip.decompress(numerics.archived(numerics.HISTORY,source['files']['trajectory.json.gz'],raw=True)))
    candidate=numerics.archived(numerics.HISTORY,source['result']['candidate'])
    records={}
    for index in (10,30,34):
        record=deepcopy(observations[index]['complete_update_record'])
        definition=record['resolved_problem_reference'];ref=source['files'][definition['filename']]
        record['resolved_problem_archive']=dict(folder=numerics.HISTORY,reference=ref)
        records[str(index)]=numerics.imported_record(host,candidate['configuration'],record,
            dict(study_id=summary['study_id'],folder=numerics.HISTORY,execution_id=row['execution_id'],update_id=index))
    diagnosis=core.read(core.ROOT/DIAG/'scientific_summary.json')
    divergent=diagnosis['physical_validation'][0];div_source=numerics.execution_source(divergent,DIAG)
    div_observations=numerics.archived(DIAG,div_source['files']['controller_observations.json'])
    div_record=deepcopy(div_observations[10]['complete_update_record'])
    definition=div_record['resolved_problem_reference']
    div_record['resolved_problem_archive']=dict(folder=DIAG,reference=div_source['files'][definition['filename']])
    div_candidate=numerics.archived(DIAG,div_source['result']['candidate'])
    records['primary-10']=records['10']
    records['10']=numerics.imported_record(host,div_candidate['configuration'],div_record,
        dict(study_id=diagnosis['study_id'],folder=DIAG,execution_id=divergent['execution_id'],update_id=10,
             reason='Saved first-divergence input: timed iteration 5 versus 4'))
    ref=core.save(host,dict(configuration=candidate['configuration'],observations=observations,samples=samples,
        files=source['files'],source_archive=numerics.HISTORY,source_execution=row['execution_id']), 'repair_source_states')
    core.update(host,repair_history=dict(**info,records=records,states=ref))
    return core.state(host)['repair_history']


def length_admission(host):
    s=core.state(host);offline=[];passing=[]
    fixed=s['spec']['reference_parameters']['d']
    for ref in s.get('mechanics_results',[]):
        value=host.store.artifact(ref)
        if value.get('operation')=='integrate' and value.get('replay',{}).get('gates_passed'):
            parent=host.store.artifact(value['source_mechanics'])
            if (not parent.get('imported_historical_evidence') and parent.get('original_task_feasible')
                and parent.get('hard_max_normalized_violation',float('inf'))<=1e-5
                and abs(parent['candidate']['d']-fixed)<1e-10):offline.append(ref)
    for ref in s['results']:
        row=host.store.artifact(ref)
        if (row.get('fresh_execution') and (row.get('acceptance') or {}).get('accepted')
            and row['profile_identity']==s['profile']['identity']
            and abs(host.store.artifact(row['candidate'])['parameters']['d']-fixed)<1e-10):passing.append((ref,row))
    pair=next(([a[0],b[0]] for i,a in enumerate(passing) for b in passing[i+1:]
        if a[1]['candidate']==b[1]['candidate'] and a[1]['execution_id']!=b[1]['execution_id']
        and a[1]['role']=='fixed_validation' and b[1]['role']=='engineering_repetition'
        and b[1]['selected_execution']==a[0]),[])
    return dict(passed=bool(offline and pair),new_fixed_offline_validations=offline,matching_passing_executions=pair,
        diagnostic_execution_alone_is_insufficient=True)


def select_recipe(host,changes,reason):
    s=core.state(host)
    if s['pending']:raise ValueError('PENDING_RECIPE_CHANGE_FORBIDDEN')
    base=deepcopy(s['base_configuration']);base['policy']['controller']['parameters']['data']['recipe'].update(changes)
    profile=deepcopy(s['profile']);profile.pop('identity');profile['version']+=1
    profile.update(configuration=core.full_science(base),recipe=deepcopy(base['policy']['controller']['parameters']['data']['recipe']))
    profile['identity']=digest(profile)
    evidence=core.save(host,dict(changes=changes,reason=reason,previous_profile=s['profile']['identity'],profile=profile),'controller_recipe_selection')
    core.update(host,base_configuration=base,profile=profile,profile_history=[*s['profile_history'],profile],selected=None)
    ref=core.construct(host,s['spec']['reference_parameters'],dict(origin='engineering_recipe_selection',evidence=evidence))
    core.update(host,reference_candidate=ref)
    return ref


def projection_continuation(request):
    """One counted continuation; restore available q/v honestly, never claim full snapshot."""
    import mujoco
    from extensions.tendon_family.gvs_projection import project,discretize,discretization_jacobian
    from extensions.tendon_family.gvs_codesign import Workspace
    p=request['diagnostic_parameters'];source=p['saved_source'];index=p['update_id']
    archive=source['source_archive'];files=source['files']
    physics=numerics.archived(archive,files['resolved_physics.json'])
    obs=source['observations'][index];record=obs['complete_update_record']
    # Samples are post-step: update k begins at sample k-1.
    saved=next(r for r in source['samples'] if abs(r['time_s']-index*.01)<1e-9)
    next_saved=next(r for r in source['samples'] if abs(r['time_s']-(index+1)*.01)<1e-9)
    q=np.asarray(saved['qpos_rad']);v=np.asarray(saved['qvel_rad_s'])
    basis=source['configuration']['policy']['controller']['parameters']['data']['recipe']['basis']
    projected=project(physics,source['configuration']['robot']['structure']['data'],q,v,basis)
    if p['state_kind']=='representable':q,v=discretize(physics,source['configuration']['robot']['structure']['data'],projected['q_gvs'],projected['qdot_gvs'],basis)
    if True:
        # Archived meshes are inline. Avoid Windows temporary-directory ACLs.
        model=mujoco.MjModel.from_xml_string(numerics.archived(archive,files['robot.xml'],raw=True).decode('utf8'));data=mujoco.MjData(model)
        joints=[model.joint(name).id for name in physics['dofs']]
        qi=model.jnt_qposadr[joints];vi=model.jnt_dofadr[joints]
        aids=[model.actuator(t['entity']+'_direct_tension').id for t in physics['tendons']]
        data.qpos[qi]=q;data.qvel[vi]=v;data.time=index*.01;data.ctrl[aids]=obs['actual_tension_n']
        mapping=discretization_jacobian(physics,source['configuration']['robot']['structure']['data'],basis)
        rows=[]
        for k in range(21):
            mujoco.mj_forward(model,data)
            jac=np.zeros((3,model.nv));rot=np.zeros_like(jac)
            mujoco.mj_jacSite(model,data,jac,rot,model.site('tip_site').id)
            rows.append(dict(time_s=float(data.time),tip_m=data.site_xpos[model.site('tip_site').id].tolist(),
                tip_velocity_m_s=(jac@data.qvel).tolist(),qacc=data.qacc[vi].tolist(),
                projected_qacc=np.linalg.lstsq(mapping,data.qacc[vi],rcond=None)[0].tolist(),
                generalized_terms={name:(mapping.T@getattr(data,name)[vi]).tolist()
                    for name in ('qfrc_actuator','qfrc_passive','qfrc_bias')}))
            if k<20:mujoco.mj_step(model,data)
    w=Workspace(source['configuration']);x=np.r_[projected['q_gvs'],projected['qdot_gvs']];d=request['candidate']['d']
    terms=w.functions.evaluate(x,obs['actual_tension_n'],d)
    position=np.asarray(w.tip(x[:w.n],d)).ravel();velocity=np.asarray(w.velocity(x[:w.n],x[w.n:],d)).ravel()
    actual_initial=np.asarray(obs['tip_position_m']);actual_final=np.asarray(next_saved['tip_m'])
    return dict(status='completed',state_kind=p['state_kind'],update_id=index,forward_integration_jobs=1,rows=rows,
        original_state_restore='Available named joint qpos/qvel, time and constant command restored; activation/warmstart/solver history not archived. Baseline reconciled before interpretation.',
        initial_tip_vs_archived_m=float(np.linalg.norm(np.asarray(rows[0]['tip_m'])-actual_initial)),
        final_tip_vs_archived_m=float(np.linalg.norm(np.asarray(rows[-1]['tip_m'])-actual_final)),
        initial_reduced_world_tip_m=position.tolist(),initial_reduced_world_velocity_m_s=velocity.tolist(),
        initial_position_model_difference_m=float(np.linalg.norm(position-rows[0]['tip_m'])),
        initial_velocity_model_difference_m_s=float(np.linalg.norm(velocity-rows[0]['tip_velocity_m_s'])),
        reduced_terms={key:value.tolist() for key,value in terms.items() if key not in ('mass_matrix','tendon_length_jacobian')},
        projection=projected,recorded_reduced_state_max_difference=float(abs(x-record['measured_state']).max()))


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','import','midpoint','continuation','policy','solve','verify','execute','repeat','gate'])
    parser.add_argument('--substeps',type=int,default=4);parser.add_argument('--update',type=int,default=34)
    parser.add_argument('--kind',default='original');parser.add_argument('--iterations',type=int,default=12)
    parser.add_argument('--source');parser.add_argument('--key',default='');parser.add_argument('--current',action='store_true')
    parser.add_argument('--repetitions',type=int,default=2);args=parser.parse_args()
    host=core.prepare(SPEC) if args.command=='prepare' else Host(core.ROOT/'runs/nr1012','nr1012',actor='unified-research')
    s=core.state(host);history=s.get('repair_history',{})
    if args.command=='prepare':value=dict(prepared=host.run_id)
    elif args.command=='import':value=history_inputs(host)
    elif args.command=='gate':value=length_admission(host)
    elif args.command=='policy':value=core.local_diagnostic(host,dict(execution=history['records'][str(args.update)],update_id=args.update,
        mode='research_current' if args.current else 'research_policy',iteration_cap=args.iterations,repetitions=args.repetitions,prepare_tail=True),args.key or f'policy-{args.update}-{args.iterations}')
    elif args.command=='execute':value=core.execute(host,s['reference_candidate'],args.key,role='fixed_validation')
    elif args.command=='repeat':
        selected=reference(args.source);row=host.store.artifact(selected)
        value=core.execute(host,row['candidate'],args.key,role='engineering_repetition' if (row.get('acceptance') or {}).get('accepted') else 'diagnostic_repetition',selected=selected)
    else:
        source=reference(args.source) if args.source else history['mechanics']
        if args.command=='solve':
            from schemas.casadi_feedback import Candidate
            d=s['spec']['reference_parameters']['d'];recipe=s['profile']['recipe']
            payload=Candidate(design_bounds=(d,d),design_initial=d,initialization='saved_schedule',source_candidate=source,
                substeps=recipe['substeps'],integration_method=recipe['integration_method']).model_dump(mode='json')
            value=numerics.experiment(host,'solve',payload,args.key,'Can corrected fixed-structure optimization satisfy the original task?',
                'Numerical transcription; fixed d and original physical task','Frozen zero state, six bounded .01s commands and original task limits',
                'Retained feasibility, sampled original task, independent BDF task and node agreement are separate gates')
        else:
            payload=dict(source=source)
            if args.command=='midpoint':payload.update(integration_method='implicit_midpoint',substeps=args.substeps)
            elif args.command=='verify':payload.update(method='BDF')
            else:payload.update(investigation='projection_continuation',saved_source=host.store.artifact(history['states']),update_id=args.update,state_kind=args.kind)
            value=numerics.experiment(host,'integrate',payload,args.key or f'{args.command}-{args.update}-{args.kind}-{args.substeps}',
                'Resolve one repair-relevant numerical discrepancy','Only declared integration or representable state',
                'Identical structure, input and interval','Compare initial world motion before subsequent velocity and force terms')
    # Persist the full result; console output stays small, including local complete plans.
    atomic_json(host.store.root/'last_operation.json',value)
    if args.command=='policy':value=dict(reference=value['reference'],difference=value['maximum_first_input_difference_n'],
        rows=[dict(iterations=r.get('diagnostics',{}).get('iterations'),delivered=r.get('delivered_tension_n'),
            feasible=r.get('verification',{}).get('feasible'),cost=r.get('charged_numerical_s')) for r in value['rows']])
    print(json.dumps(value,ensure_ascii=True))


if __name__=='__main__':main()
