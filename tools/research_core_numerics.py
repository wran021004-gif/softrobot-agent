"""Engineering diagnostics on the existing research host, ledger and workers."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tarfile
import time
import numpy as np
from tools import research_core as core


def archived(folder, reference, raw=False):
    folder=core.ROOT/folder
    manifest=core.read(folder/'archive_manifest.json')
    path=folder/'immutable_artifacts.tar.gz'
    # Cache verified archive identity, retaining per-member verification.
    identity=(str(path),path.stat().st_mtime_ns,path.stat().st_size)
    if identity not in _verified:
        with path.open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest()!=manifest['archive_sha256']:
                raise ValueError('HISTORICAL_ARCHIVE_HASH_MISMATCH')
        _verified.add(identity)
    member=next(m for m in manifest['members'] if m['sha256']==reference['artifact_id'])
    with tarfile.open(path) as archive:body=archive.extractfile(member['name']).read()
    if hashlib.sha256(body).hexdigest()!=reference['artifact_id']:raise ValueError('HISTORICAL_MEMBER_HASH_MISMATCH')
    return body if raw else json.loads(body)


_verified=set()
HISTORY='evidence/mechanics_control_20261011'


def execution_source(row, folder=HISTORY):
    result=archived(folder,row['reference'])
    target=result['execution']['receipts']['simulation']['output']
    key=(folder,target['artifact_id'])
    if key not in _manifests:
        with tarfile.open(core.ROOT/folder/'immutable_artifacts.tar.gz') as archive:
            for member in archive:
                if member.name.endswith('.json') and member.size<200000:
                    body=archive.extractfile(member).read();value=json.loads(body)
                    if isinstance(value,dict) and 'files' in value and isinstance(value.get('result'),dict):
                        if hashlib.sha256(body).hexdigest()!=Path(member.name).stem:raise ValueError('MANIFEST_HASH_MISMATCH')
                        _manifests[(folder,value['result']['artifact_id'])]=value
    manifest=_manifests[key]
    files={r['filename']:r['reference'] for r in manifest['files']}
    return dict(result=result,files=files,folder=folder)


_manifests={}


def imported_record(host, configuration, record, provenance):
    value=dict(configuration=configuration,record=record,provenance=provenance,
        original_study=provenance['study_id'],imported_historical_evidence=True,
        additional_numerical_s=0.,confirmation_eligible=False,
        complete_original_problem_available=bool(record.get('resolved_problem_archive') or record.get('resolved_problem')))
    ref=core.save(host,value,'imported_historical_diagnostic_input')
    core.update(host,historical_diagnostic_sources=[*core.state(host).get('historical_diagnostic_sources',[]),ref])
    return ref


def import_history(host):
    core.guard(host)
    if core.state(host).get('numerical_history'):return core.state(host)['numerical_history']
    summary=core.read(core.ROOT/HISTORY/'scientific_summary.json')
    solved=summary['mechanics'][0]; original=archived(HISTORY,solved['reference'])
    checkpoint=archived(HISTORY,solved['checkpoint_reference'])
    trajectory=archived(HISTORY,solved['trajectory_reference'])
    if trajectory!=original['candidate']:raise ValueError('ARCHIVED_TRAJECTORY_IDENTITY_MISMATCH')
    # References retain original ownership. Large graphs/checkpoints stay in source archive.
    value={k:deepcopy(original.get(k)) for k in ('operation','candidate','owning_study','execution_id','trajectory_reference',
        'checkpoint_reference','original_task_feasible','relaxed_nlp_feasible','original_task_gaps','trajectory_metrics','implementation')}
    value.update(imported_historical_evidence=True,source_reference=solved['reference'],source_archive=HISTORY,
        additional_numerical_s=0.,original_resolved_problem_available=False,
        reconstruction='Exact saved trajectory and solver checkpoint; original offline serialized NLP was not archived.')
    ref=core.save(host,value,'imported_archived_mechanics')
    core.update(host,imported_mechanics_sources=[ref])
    old_folder='evidence/research_core_20261011'
    old_summary=core.read(core.ROOT/old_folder/'scientific_summary.json')
    old=old_summary['local_solve_outcomes'][0]
    old_input=archived(old_folder,old['original_worker_input'])
    historical=imported_record(host,old_input['configuration'],old_input['record'],
        dict(study_id=old_summary['study_id'],folder=old_folder,reference=old['original_worker_input'],update_id=1))
    primary=next(r for r in summary['closed_loop'] if r['execution_id']=='d42321543b9a45bb97b3ff28aca097ae')
    source=execution_source(primary)
    observations=json.loads(archived(HISTORY,source['files']['controller_observations.json'],raw=True))
    record=deepcopy(observations[1]['complete_update_record'])
    definition=record['resolved_problem_reference'];problem_ref=source['files'][definition['filename']]
    problem=archived(HISTORY,problem_ref)
    if problem_ref['artifact_id']!=definition['sha256'] or core.digest(problem['objective_function'])!=record['model_identity']:
        raise ValueError('ARCHIVED_RESOLVED_PROBLEM_IDENTITY_MISMATCH')
    record['resolved_problem_archive']=dict(folder=HISTORY,reference=problem_ref)
    current=imported_record(host,checkpoint['configuration'],record,
        dict(study_id=summary['study_id'],folder=HISTORY,execution_id=primary['execution_id'],
            reference=primary['reference'],update_id=1,problem_reference=problem_ref))
    # Replace offline configuration with the exact closed-loop candidate configuration.
    candidate=archived(HISTORY,source['result']['candidate'])
    current_value=host.store.artifact(current);current_value['configuration']=candidate['configuration']
    current=core.save(host,current_value,'imported_current_complete_update')
    refs=core.state(host)['historical_diagnostic_sources'];refs[-1]=current;core.update(host,historical_diagnostic_sources=refs)
    info=dict(mechanics=ref,historical_update=historical,current_update=current,
        saved_checkpoint_archive=dict(folder=HISTORY,reference=solved['checkpoint_reference']),
        saved_bdf_archive=dict(folder=HISTORY,reference=summary['mechanics'][1]['reference']),
        original_study_sealed=True,imported_scientific_executions=0,configuration_source=source['result']['candidate'])
    core.update(host,numerical_history=info)
    return info


def trajectory_outputs(w,candidate):
    states=np.asarray(candidate['states']);d=candidate['d']
    return dict(times_s=candidate['times_s'],states=candidate['states'],
        tip_positions_m=[np.asarray(w.tip(x[:w.n],d)).ravel().tolist() for x in states],
        tip_velocities_m_s=[np.asarray(w.velocity(x[:w.n],x[w.n:],d)).ravel().tolist() for x in states])


def offline_diagnostic(request):
    from extensions.tendon_family.gvs_codesign import Workspace,integrate
    started=time.perf_counter();p=request['diagnostic_parameters'];saved=request['candidate']
    if p.get('investigation')=='projection_continuation':
        from tools.numerical_repair import projection_continuation
        return projection_continuation(request)
    if p.get('investigation')=='current_control_plans':return current_control_plans(request)
    if p.get('investigation')=='closed_loop':return closed_loop_analysis(request)
    w=Workspace(request['configuration'],p.get('substeps',saved.get('substeps',1)),integration_method=p.get('integration_method',saved.get('integration_method','implicit_euler')))
    if p.get('fixed_interval'):return fixed_input_comparison(w,p['fixed_interval'])
    if request['operation']=='inspect':
        residuals=np.array([np.asarray(w.step(a,b,u,saved['d'])).ravel()
            for a,b,u in zip(saved['states'][:-1],saved['states'][1:],saved['tensions_n'])])
        return dict(status='completed',saved_trajectory=trajectory_outputs(w,saved),metrics=w.metrics(saved),
            residuals=residuals.tolist(),maximum_normalized_residual=float(abs(residuals).max()),
            maximum_kinematic_residual_rad_m=float(abs(residuals[:,:w.n]).max()*10.),
            maximum_force_balance_residual_N_m2_rad=float(abs(residuals[:,w.n:]).max()*.001),
            initial_state_max_abs=float(abs(np.asarray(saved['states'][0])).max()),
            state_order=dict(coordinates=w.expression.coordinate_order,tendons=w.expression.tendon_order,
                scales=w.scales.tolist(),order_equal=saved['coordinate_order']==w.expression.coordinate_order and saved['tendon_order']==w.expression.tendon_order),
            physical_context=request['configuration']['task']['environment'],
            switching='U[k] held on [k*.01,(k+1)*.01); state continuous at switches',
            numerical_s=time.perf_counter()-started,forward_integration_jobs=0)
    if p.get('method','implicit')=='implicit':
        rollout=w.rollout(saved['tensions_n'],saved['d'])
        candidate=dict(saved,states=rollout['states'],times_s=rollout['times_s'],substeps=w.substeps)
        return dict(status=rollout['status'],method=w.integration_method,substeps=w.substeps,
            trajectory=trajectory_outputs(w,candidate),rollout=rollout,
            metrics=w.metrics(candidate) if not rollout['failure'] else None,forward_integration_jobs=1)
    result,trajectory=integrate(w.functions,w.tip,w.velocity,saved,
        request['configuration']['task']['goal']['data']['target_m'],**p.get('tolerances',{}))
    return dict(status=result['status'],method='BDF',replay=result,trajectory=trajectory,forward_integration_jobs=1)


def current_control_plans(request):
    """One charged read-only assessment of the current complete accepted plans."""
    from tools.platform_store import Store
    from extensions.tendon_family.control_evidence import ControlEvidence
    from extensions.tendon_family.gvs_codesign import Workspace
    store=Store(request['store_root']);result=store.artifact(request['diagnostic_parameters']['current_result'])
    reader=ControlEvidence(store);source=reader.resolve(result['execution_id'])
    obs=reader.read_file(source,'controller_observations.json',[])
    motion=store.artifact(result['profile']['motion']);w=Workspace(request['configuration'])
    target=np.asarray(request['configuration']['task']['goal']['data']['target_m']);rows=[]
    for observation in obs:
        record=observation['complete_update_record'];plan=record['delivered_plan'];scales=np.asarray(record['state_scales'])
        times=np.r_[record['time_s'],record['prediction_timing']['node_times_s']]
        states=np.array([[plan[f'x/{k}/{j}']*scales[j] for j in range(2*w.n)] for k in range(len(times))])
        velocities=np.array([np.asarray(w.velocity(x[:w.n],x[w.n:],request['candidate']['d'])).ravel() for x in states])
        hold=(times>=.30-1e-9)&(times<=.35+1e-9)
        current=next((m for m in motion if abs(m['time_s']-record['time_s'])<1e-9),None)
        rows.append(dict(update_id=record['update_id'],time_s=record['time_s'],accepted=observation['plan_accepted'],
            predicted_holding_max_speed_m_s=float(np.linalg.norm(velocities[hold],axis=1).max()) if any(hold) else None,
            predicted_terminal_speed_m_s=float(np.linalg.norm(velocities[-1])),
            measured_current_speed_m_s=None if current is None else current['tip_speed_m_s'],
            delivered_tension_n=observation['actual_tension_n'],solver_iterations=record['diagnostics']['iterations'],
            prediction_timing=record['prediction_timing']))
    return dict(status='completed',investigation='current_control_plans',source_result=request['diagnostic_parameters']['current_result'],
        rows=rows,holding_predictions_exceed_limit_at_updates=[r['update_id'] for r in rows if r['predicted_holding_max_speed_m_s'] is not None and r['predicted_holding_max_speed_m_s']>.02],
        forward_integration_jobs=0,qualification='Accepted goal-based plans evaluated from their actual delivered states; original physical holding acceptance remains separate.')


def fixed_input_comparison(w,interval):
    """One independent continuous integration, matched to an archived NMPC interval."""
    import casadi as ca
    from scipy.integrate import solve_ivp
    state=np.asarray(interval['measured_state']);u=np.asarray(interval['applied_tension_n']);d=interval['d']
    x,tension,rhs=w.functions._linearization_symbols;design=w.functions.design_input
    rhs_fn=ca.Function('matched_rhs',[x,tension,design],[rhs],{'cse':True})
    jac_fn=ca.Function('matched_jac',[x,tension,design],[ca.jacobian(rhs,x)],{'ad_weight':1.,'cse':True})
    t0=interval['time_s'];times=t0+np.arange(21)*.0005
    solution=solve_ivp(lambda t,y:np.asarray(rhs_fn(y,u,d)).ravel(),(t0,t0+.01),state,
        method='BDF',jac=lambda t,y:np.asarray(jac_fn(y,u,d)),rtol=1e-10,
        atol=np.r_[np.full(w.n,1e-11),np.full(w.n,1e-9)],dense_output=True)
    if not solution.success:return dict(status='failed',message=solution.message,forward_integration_jobs=1)
    states=solution.sol(times).T
    trajectory=trajectory_outputs(w,dict(states=states.tolist(),times_s=times.tolist(),d=d))
    reference=interval['alignment'];prediction=interval['implicit_predicted_state']
    residual=np.asarray(w.step(state,prediction,u,d)).ravel()
    actual_v=np.asarray(reference['measured_tip_velocity_m_s']);implicit_v=np.asarray(reference['predicted_tip_velocity_m_s'])
    continuous_v=np.asarray(trajectory['tip_velocities_m_s'][-1]);actual_p=np.asarray(reference['measured_tip_m'])
    return dict(status='completed',method='BDF matched NMPC interval',trajectory=trajectory,
        source_interval=interval,forward_integration_jobs=1,
        implicit_prediction_same_equations_max_normalized_residual=float(abs(residual).max()),
        initial_projected_velocity_difference_m_s=float(np.linalg.norm(np.asarray(trajectory['tip_velocities_m_s'][0])-interval['initial_physical_velocity_m_s'])),
        final_implicit_physical_velocity_difference_m_s=float(np.linalg.norm(implicit_v-actual_v)),
        final_continuous_physical_velocity_difference_m_s=float(np.linalg.norm(continuous_v-actual_v)),
        final_implicit_continuous_velocity_difference_m_s=float(np.linalg.norm(implicit_v-continuous_v)),
        final_continuous_physical_position_difference_m=float(np.linalg.norm(np.asarray(trajectory['tip_positions_m'][-1])-actual_p)),
        final_implicit_speed_m_s=float(np.linalg.norm(implicit_v)),final_continuous_speed_m_s=float(np.linalg.norm(continuous_v)),
        final_physical_speed_m_s=float(np.linalg.norm(actual_v)),
        qualification='Continuous integration starts from the exact recorded projected state; physical realization uses its full MuJoCo state. Remaining error can include projection and model differences.')


def compact_numerics(value):
    result={k:value.get(k) for k in ('method','substeps','metrics','forward_integration_jobs','maximum_normalized_residual',
        'initial_state_max_abs','implicit_prediction_same_equations_max_normalized_residual',
        'final_implicit_physical_velocity_difference_m_s','final_continuous_physical_velocity_difference_m_s',
        'final_implicit_continuous_velocity_difference_m_s','final_physical_speed_m_s') if k in value}
    if value.get('investigation')=='closed_loop':
        result['aligned_closed_loop']=[dict(execution_id=r['execution_id'],peak_interval_s=[r['peak_velocity_disagreement']['start_s'],r['peak_velocity_disagreement']['end_s']],
            peak_velocity_difference_m_s=r['peak_velocity_disagreement']['velocity_difference_m_s'],
            holding_velocity_difference_m_s=r['holding_velocity_disagreement']['velocity_difference_m_s'],
            initialization_selected=r['initialization_selected'],noninitialization_accepted=r['noninitialization_accepted'],unusable=r['unusable']) for r in value['runs']]
    return result


def experiment(host,operation,arguments,key,question,changed,fixed,discriminator):
    from tools.research_core_mechanics import dispatch
    core.guard(host,True)
    core.save(host,dict(operation=operation,operation_key=key,question=question,changed_factor=changed,
        fixed_conditions=fixed,expected_discriminating_observation=discriminator,
        maximum_cost_s=core.state(host)['spec']['mechanics_allowances'][operation+'_s'],
        integration_count=int(operation in ('integrate','replay')),recorded_unix=time.time()),'numerical_experiment_protocol')
    return dispatch(host,operation,arguments,key)


def recover_local(host):
    s=core.state(host);p=s['pending'];out=Path(p['output'])
    if not out.exists():raise ValueError('UNKNOWN_LOCAL_SOLVE_RETAINS_RESERVATION_NO_REPEAT')
    value=core.read(out);row=host.store.lookup(host.run_id,p['worker_request_id']);charged=p['reserved_s']
    value.update(execution_id=row['execution_id'],charged_numerical_s=charged,
        source_execution=p['source_execution'],source_update_id=p['source_update_id'],owning_study=host.run_id,
        origin=p['origin'],historical_input=p['historical_input'],recovered_output_without_solve=True)
    with host.store.transaction() as db:
        current=host.store.session(host.run_id,db)['state'];current.update(pending=None,
            numerical_s=current['numerical_s']+charged,local_solve_s=current['local_solve_s']+charged,
            numerical_reserved_s=current['numerical_reserved_s']-charged)
        host.store.update_state(db,host.run_id,current)
        host.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=host.actor,
            tool_id='research.core_local_solve',tool_version='1.0.0',execution_status='completed',charged=core.zero()),value,elapsed=charged,db=db)
    return value


def closed_loop_analysis(request):
    """Align archived measured world velocity and accepted plans at their timestamps."""
    import gzip
    from extensions.tendon_family.gvs_codesign import Workspace
    from extensions.tendon_family.control_evidence import aligned_interval_predictions
    summary=core.read(core.ROOT/HISTORY/'scientific_summary.json')
    w=Workspace(request['configuration']);target=np.asarray(request['configuration']['task']['goal']['data']['target_m'])
    results=[]
    for row in summary['closed_loop']:
        if row['status']!='evaluated':continue
        source=execution_source(row);r=source['result'];d=row['parameters']['d']
        obs=archived(HISTORY,source['files']['controller_observations.json'])
        samples=json.loads(gzip.decompress(archived(HISTORY,source['files']['trajectory.json.gz'],raw=True)))
        commands=archived(HISTORY,source['files']['actual_commands.json'])
        motion=archived(HISTORY,r['profile']['motion'])
        from extensions.tendon_family.gvs_reporting import aligned_predictions
        aligned,missing=aligned_predictions(samples,obs,motion)
        points=[]
        for observation in obs:
            record=observation['complete_update_record'];time_s=record['time_s'];scales=np.asarray(record['state_scales'])
            plan=record['delivered_plan'];steps=record['effective_horizon']
            states=np.array([[plan[f'x/{k}/{j}']*scales[j] for j in range(2*w.n)] for k in range(steps+1)])
            times=np.r_[time_s,record['prediction_timing']['node_times_s']]
            positions=np.array([np.asarray(w.tip(x[:w.n],d)).ravel() for x in states])
            velocities=np.array([np.asarray(w.velocity(x[:w.n],x[w.n:],d)).ravel() for x in states])
            holding=times>=.30-1e-12
            match=next((m for m in aligned if abs(m['start_s']-time_s)<1e-8),None)
            measured=next((m for m in motion if abs(m['time_s']-time_s)<1e-8),None)
            q=np.asarray(record['measured_state']); projected_p=np.asarray(w.tip(q[:w.n],d)).ravel();projected_v=np.asarray(w.velocity(q[:w.n],q[w.n:],d)).ravel()
            path={name:[record[key]['u/0/'+t] for t in record['tendon_order']] for name,key in
                [('raw','raw_returned_plan'),('retained','selected_feasible_plan'),('delivered','delivered_plan')]}
            if record.get('recovery_candidate'):path['recovered']=[record['recovery_candidate']['u/0/'+t] for t in record['tendon_order']]
            points.append(dict(update_id=record['update_id'],time_s=time_s,alignment=match,
                measured_current=measured,projected_world_position_m=projected_p.tolist(),projected_world_velocity_m_s=projected_v.tolist(),
                projected_position_difference_m=float(np.linalg.norm(projected_p-observation['tip_position_m'])),
                measured_state=record['measured_state'],applied_tension_n=observation['actual_tension_n'],
                projection_residual_rad_m=observation['gvs_projection_residual_max_rad_m'],
                horizon=record['effective_horizon'],absolute_times_s=times.tolist(),prediction_timing=record['prediction_timing'],
                predicted_position_error_m=np.linalg.norm(positions-target,axis=1).tolist(),
                predicted_speed_m_s=np.linalg.norm(velocities,axis=1).tolist(),
                predicted_holding_max_speed_m_s=float(np.linalg.norm(velocities[holding],axis=1).max()) if any(holding) else None,
                predicted_terminal_speed_m_s=float(np.linalg.norm(velocities[-1])),action_path=path,
                requested_applied_difference_n=float(max(abs(np.asarray(observation['requested_tension_n'])-observation['actual_tension_n']))),
                raw_retained_difference_n=float(max(abs(np.asarray(path['raw'])-path['retained']))),
                retained_delivered_difference_n=float(max(abs(np.asarray(path['retained'])-path['delivered']))),
                accepted=observation['plan_accepted'],selected_iteration=observation['optimization_selected_iteration'],
                diagnostics={k:record['diagnostics'].get(k) for k in ('iterations','policy_stop_reason','returned_iterate_constraint_violation','selected_feasible_iteration','initial_scaled_violation')},
                recovery={k:record['recovery'].get(k) for k in ('attempted','selected','scaled_violation','objective','error')},
                input_min_n=float(np.min(observation['actual_tension_n'])),input_max_n=float(np.max(observation['actual_tension_n']))))
        peak=max(aligned,key=lambda p:p.get('velocity_difference_m_s') or 0.)
        holding=[a for a in aligned if a['end_s']>=.30-1e-12]
        results.append(dict(execution_id=row['execution_id'],reference=row['reference'],parameters=row['parameters'],
            acceptance=r['acceptance'],aligned=aligned,alignment_missing=missing,points=points,motion=motion,
            peak_velocity_disagreement=peak,holding_velocity_disagreement=max(holding,key=lambda p:p.get('velocity_difference_m_s') or 0.),
            initialization_selected=sum(p['selected_iteration'] in (-1,0) for p in points),
            noninitialization_accepted=sum(p['accepted'] and p['selected_iteration'] not in (-1,0) for p in points),
            unusable=sum(not p['accepted'] for p in points)))
    return dict(status='completed',investigation='closed_loop',runs=results,forward_integration_jobs=0,
        source_archive=HISTORY,qualification='Recorded sampled physical motion; accepted plan predictions are model estimates. Projection residual and input proximity alone do not identify control authority.')


def main():
    import argparse
    from tools.platform_host import Host
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['import','inspect','closed-loop','integrate'])
    parser.add_argument('--spec',type=Path,default=core.ROOT/'examples/numerical_diagnosis/specification.json')
    parser.add_argument('--substeps',type=int,choices=[1,2,4],default=1);parser.add_argument('--method',choices=['implicit','BDF'],default='implicit')
    args=parser.parse_args();spec=core.read(args.spec);host=Host(core.ROOT/'runs'/spec['study_id'],spec['study_id'],actor='engineering')
    history=import_history(host)
    if args.command=='import':print(json.dumps(history));return
    p=dict(source=history['mechanics'],substeps=args.substeps,method=args.method)
    if args.command=='closed-loop':p['investigation']='closed_loop'
    operation='integrate' if args.command=='integrate' else 'inspect'
    key='engineering-'+args.command+'-'+args.method+'-'+str(args.substeps)
    value=experiment(host,operation,p,key,
        question='Distinguish saved discrete feasibility, integration accuracy and aligned closed-loop prediction/settling behavior.',
        changed=f'{args.command}: {args.method}, substeps={args.substeps}',fixed='Saved structure, all 35 commands, zero initial state, original .35s task; closed-loop uses exact sealed inputs.',
        discriminator='Residuals and aligned state/position/velocity differences identify earliest divergence; holding outcomes remain separately sampled.')
    print(json.dumps(value))


if __name__=='__main__':main()
