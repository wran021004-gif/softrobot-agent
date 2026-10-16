"""One candidate-bound fixed-tension MuJoCo rollout and existing task settlement."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import time

import numpy as np

from schemas.platform import BackendResult, Payload, Signal, SessionInput
from tools.platform_store import plain, zero, Store
from tools.state_io import atomic_json, digest, read
from tools.research.state import state, update, save, guard
from tools.research.design import verify_candidate


def binding(configuration, trajectory):
    from extensions.tendon_family.sorosim_control import checked_control
    from extensions.tendon_family.sorosim_spec import SorosimModel
    from extensions.tendon_family.backends import physics_for
    from extensions.tendon_family.scene import assemble

    inp=SessionInput.model_validate(configuration)
    control=checked_control(inp)
    spec=SorosimModel(dict(basis=control.recipe.basis,
        gauss_per_interval=control.solver.gauss_per_interval)).convert(
        inp.robot.structure.data,inp.policy.discretization.data,inp.task.environment.data,solver=control.solver)
    physics=physics_for(inp);scene=assemble(inp,physics)
    timing=inp.task.timing;count=round(timing.duration_s/timing.control_period_s)
    order=[t['entity'] for t in physics['tendons']]
    u=np.asarray(trajectory['tensions_n'],dtype=float)
    configured_limits={t['id']:t['force_limit_n'] for t in configuration['robot']['structure']['data']['tendons']}
    limits=np.asarray([configured_limits[name] for name in order])
    if (trajectory['model_identity']!=spec['identity'] or trajectory['design_identity']!=spec['design_identity']
            or trajectory['task_identity']!=digest(plain(inp.task)) or trajectory['tendon_order']!=order
            or u.shape!=(count,len(order)) or not np.isfinite(u).all() or np.any(u<0) or np.any(u>limits)
            or len(trajectory['times_s'])!=count+1 or
            any(abs(t-k*timing.control_period_s)>1e-12 for k,t in enumerate(trajectory['times_s']))
            or scene['control']['tension_execution_mode']!='ideal_tension'):
        raise ValueError('PHYSICAL_REPLAY_CANDIDATE_TASK_MODEL_OR_SEQUENCE_MISMATCH')
    return inp,physics,scene


def calculate(request,folder):
    from extensions.tendon_family.backends import playback_tensions
    store=Store(request['store_root'])
    current=store.session(request['study_id'])['state']
    pending=current.get('pending') or {}
    row=store.lookup(request['study_id'],request['request_id'])
    if (not row or row['receipt'] or row['request_hash']!=digest(request)
            or pending.get('kind')!='physical_replay' or pending.get('worker_request_id')!=request['request_id']
            or Path(pending['folder']).resolve()!=Path(folder).resolve()):
        raise ValueError('OWNED_ACTIVE_PHYSICAL_REPLAY_RESERVATION_REQUIRED')
    inp,physics,scene=binding(request['configuration'],request['trajectory'])
    result=playback_tensions(inp,physics,scene,request['trajectory']['tensions_n'],folder)
    result.update(candidate=request['candidate'],source_reference=request['source_reference'],
        task_identity=digest(plain(inp.task)),mathematical_model_identity=request['trajectory']['model_identity'])
    return result


def dispatch(host,arguments,key):
    guard(host,True)
    s=state(host)
    if s.get('physical_replay_launches',0)>=s['spec']['budgets']['physical_launches']:
        raise ValueError('PHYSICAL_REPLAY_LAUNCH_BUDGET_EXHAUSTED')
    candidate=plain(arguments.candidate)
    cfg=verify_candidate(host,candidate)['configuration']
    source_ref=plain(arguments.source)
    source=host.store.artifact(source_ref)
    if (source.get('source_kind')!='verified_mathematical_trajectory' or
            not source['posthoc_verification']['checks']['repaired_verification_passed']):
        raise ValueError('VERIFIED_OR_EXPLICIT_DIAGNOSTIC_MATHEMATICAL_SOURCE_REQUIRED')
    binding(cfg,source['trajectory'])
    outputs=source['mathematical_outputs']
    if (outputs['model_identity']!=source['trajectory']['model_identity'] or
            outputs['times_s']!=source['trajectory']['times_s'] or outputs['samples']!=36):
        raise ValueError('MATHEMATICAL_OUTPUT_BINDING_MISMATCH')
    request=dict(kind='physical_replay',implementation=s['freeze'],study_id=host.run_id,
        store_root=str(host.store.root),request_id=key+'-physical',candidate=candidate,
        source_reference=source_ref,configuration=cfg,trajectory=source['trajectory'])
    worker_key=request['request_id']
    old=host.store.lookup(host.run_id,worker_key)
    if old:
        if old['request_hash']!=digest(request):raise ValueError('PHYSICAL_REPLAY_OPERATION_COLLISION')
        if not old['receipt']:raise ValueError('RECOVER_PHYSICAL_REPLAY_NO_RELAUNCH')
        return dict(reference=json.loads(old['receipt'])['output'],additional_physical_launches=0)
    def charge(db):
        current=host.store.session(host.run_id,db)['state']
        current['physical_replay_launches']=current.get('physical_replay_launches',0)+1
        host.store.update_state(db,host.run_id,current)
    row,_=host.store.reserve(host.run_id,worker_key,digest(request),host.actor,
        {**zero(),'backend_solves':1},resources=('backend.family_mujoco',),guard=charge)
    folder=host.store.root/'physical_replay'/row['execution_id']
    folder.mkdir(parents=True,exist_ok=True)
    atomic_json(folder/'request.json',request)
    update(host,pending=dict(kind='physical_replay',worker_request_id=worker_key,folder=str(folder),
        implementation=s['freeze'],candidate=candidate,source_reference=source_ref))
    from tools.service_execution import _run_contained
    started=time.perf_counter()
    try:
        with (folder/'worker.log').open('w',encoding='utf8') as log:
            done=_run_contained([s['spec']['runtime']['research_python'],'-m','tools.research.execution_worker',
                str(folder/'request.json')],log,None)
        boundary=dict(termination_confirmed=True,returncode=done.returncode)
    except subprocess.TimeoutExpired as exc:
        boundary=dict(termination_confirmed=getattr(exc,'termination_confirmed',False),timed_out=True)
    boundary['elapsed_s']=time.perf_counter()-started
    atomic_json(folder/'boundary.json',boundary)
    return recover(host)


def recover(host):
    from tools.platform_registry import registry
    from tools.research_tasks import assemble_acceptance, task_adapter
    from extensions.reference.implementation import evaluate_reach

    p=state(host)['pending'];folder=Path(p['folder'])
    boundary=read(folder/'boundary.json')
    if not boundary['termination_confirmed']:
        raise ValueError('UNKNOWN_PHYSICAL_REPLAY_OUTCOME_RETAINS_RESERVATION')
    raw=read(folder/'result.json') if (folder/'result.json').exists() else dict(status='incomplete',reason='worker_result_missing')
    if raw.get('status')!='completed' and (folder/'samples.json').exists():
        raw['samples']=read(folder/'samples.json')
    raw.update(boundary=boundary,implementation=p['implementation'])
    raw_ref=save(host,raw,'physical_playback_raw')
    source=host.store.artifact(p['source_reference'])
    cfg=verify_candidate(host,p['candidate'])['configuration']
    inp=SessionInput.model_validate(cfg)
    samples=raw.get('samples',[])
    signal=next(v for v in inp.task.observations if v.name=='tip_position' and v.phase=='post_step')
    result=BackendResult(solver_status='completed' if raw.get('status')=='completed' else 'failed',
        backend_id='backend.family_mujoco',model_id='mujoco_serial_bending_v1',
        signals=[Signal(spec=signal,times_s=[v['time_s'] for v in samples[1:]],
            values=[v['tip_m'] for v in samples[1:]])],
        data=Payload(contract='family.backend_data',data=dict(physical_replay=True)),
        limitations=['Ideal direct tendon tension; no hardware or robustness claim'],
        initial_state=inp.task.initializer.parameters,seed=inp.seed)
    evaluation=evaluate_reach(inp.task,result,raw_ref,registry(),digest(dict(candidate=p['candidate'],source=p['source_reference'])))
    evaluation_ref=save(host,plain(evaluation),'physical_playback_endpoint_evaluation')
    adapter=task_adapter(cfg);limits=adapter.ranking_limits()
    hold=[v for v in samples if v['time_s']>=adapter.holding_start_s()-1e-12]
    timing=inp.task.timing;intervals=round(timing.duration_s/timing.control_period_s)
    substeps=round(timing.control_period_s/timing.timestep_s)
    expected_hold=round(inp.policy.controller.parameters.data['settling']['window_s']/timing.sample_period_s)+1
    complete=raw.get('status')=='completed' and len(samples)==intervals+1 and raw.get('physics_steps')==intervals*substeps
    covered=complete and len(hold)==expected_hold
    max_error=max((v['position_error_m'] for v in hold),default=None)
    max_speed=max((v['speed_m_s'] for v in hold),default=None)
    configured_limits={t['id']:t['force_limit_n'] for t in cfg['robot']['structure']['data']['tendons']}
    tendon_limits=[configured_limits[name] for name in raw.get('tendon_order',source['trajectory']['tendon_order'])]
    force_violation=max((max(0.,-v,v-hi) for row in samples[1:]
        for v,hi in zip(row['actual_tension_n'],tendon_limits)),default=0.)
    profile=dict(complete=complete,execution_id=folder.name,simulation=raw_ref,evaluation=evaluation_ref,
        task=plain(inp.task),official_task_success=evaluation.task_success,
        solver_error_count=0 if complete else 1,force_bound_violation_n=force_violation,
        sampled_settling=dict(window_s=inp.policy.controller.parameters.data['settling']['window_s'],
            position_limit_m=limits['holding_max_error_m'],speed_limit_m_s=limits['holding_max_speed_m_s'],
            available=covered,max_error_m=max_error,max_speed_m_s=max_speed,
            passed=bool(covered and max_error<=limits['holding_max_error_m'] and max_speed<=limits['holding_max_speed_m_s'])))
    acceptance=assemble_acceptance(cfg,evaluation,profile,evaluation_reference=evaluation_ref,
        profile_reference=None,motion=[dict(time_s=v['time_s']) for v in samples])
    predicted=source['mathematical_outputs']
    aligned=all(abs(v['time_s']-t)<1e-12 for v,t in zip(samples,predicted['times_s']))
    differences=[dict(time_s=v['time_s'],position_m=(np.asarray(v['tip_m'])-predicted['tip_positions_m'][i]).tolist(),
        position_norm_m=float(np.linalg.norm(np.asarray(v['tip_m'])-predicted['tip_positions_m'][i])),
        velocity_m_s=(np.asarray(v['tip_velocity_m_s'])-predicted['tip_velocities_m_s'][i]).tolist(),
        velocity_norm_m_s=float(np.linalg.norm(np.asarray(v['tip_velocity_m_s'])-predicted['tip_velocities_m_s'][i])))
        for i,v in enumerate(samples)] if aligned else []
    comparison=dict(aligned=aligned and complete,available_samples=len(differences),
        initial_position_offset_m=differences[0]['position_norm_m'] if differences else None,
        max_position_difference_m=max((v['position_norm_m'] for v in differences),default=None),
        max_velocity_difference_m_s=max((v['velocity_norm_m_s'] for v in differences),default=None),
        samples=differences)
    log_bytes=(folder/'worker.log').read_bytes()
    log_ref=save(host,dict(raw_base64=base64.b64encode(log_bytes).decode('ascii'),
        raw_sha256=hashlib.sha256(log_bytes).hexdigest(),text=log_bytes.decode('utf8',errors='replace')),
        'physical_playback_log')
    final=dict(status='evaluated' if complete else 'execution_incomplete',candidate=p['candidate'],
        source_reference=p['source_reference'],raw_reference=raw_ref,evaluation_reference=evaluation_ref,
        acceptance=acceptance,comparison=comparison,profile=profile,boundary=boundary,
        charged_numerical_s=boundary['elapsed_s'],implementation=p['implementation'],log_reference=log_ref,
        physical_launches=1,mathematical_reintegrations=0,rl_actions=0,nmpc_updates=0)
    ref=save(host,final,'physical_playback_result')
    row=host.store.lookup(host.run_id,p['worker_request_id'])
    with host.store.transaction() as db:
        current=host.store.session(host.run_id,db)['state']
        if current.get('pending')!=p:raise ValueError('ALREADY_SETTLED_PHYSICAL_REPLAY')
        current['numerical_s']+=boundary['elapsed_s']
        current['pending']=None
        current.setdefault('physical_replays',[]).append(ref)
        host.store.update_state(db,host.run_id,current)
        host.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],
            caller=host.actor,tool_id='research.physical_replay',tool_version='1.0.0',
            execution_status='completed',charged=zero()),final,elapsed=boundary['elapsed_s'],db=db)
    return dict(reference=ref,**final)
