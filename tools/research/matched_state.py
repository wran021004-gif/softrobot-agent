"""Three saved-state, fixed-tension SoRoSim/MuJoCo interval comparisons."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

from tools.platform_store import plain, zero, Store
from tools.state_io import atomic_json, digest, read
from tools.research.state import state, update, save, guard
from tools.research.design import verify_candidate
from tools.research.physical_replay import binding


def _vectors(math, physical):
    start=np.asarray(math['start'],dtype=float)-physical['start']
    end=np.asarray(math['end'],dtype=float)-physical['end']
    return dict(e_projection=start.tolist(),e_one_step=end.tolist(),
        e_increment=(end-start).tolist(),projection_norm=float(np.linalg.norm(start)),
        one_step_norm=float(np.linalg.norm(end)),increment_norm=float(np.linalg.norm(end-start)))


def calculate(request, folder):
    """Run one contained prefix reconstruction and three counted intervals."""
    import mujoco
    from extensions.tendon_family.backends import _mujoco_state_failed
    from extensions.tendon_family.gvs_projection import project, PROJECTOR_ID
    from extensions.tendon_family.sorosim_control import checked_control
    from extensions.tendon_family.sorosim_spec import SorosimModel
    from extensions.tendon_family.sorosim_session import SorosimSession

    store=Store(request['store_root'])
    row=store.lookup(request['study_id'],request['request_id'])
    pending=store.session(request['study_id'])['state'].get('pending') or {}
    if (not row or row['receipt'] or row['request_hash']!=digest(request) or
            pending.get('kind')!='matched_state' or pending.get('worker_request_id')!=request['request_id'] or
            Path(pending['folder']).resolve()!=Path(folder).resolve()):
        raise ValueError('OWNED_ACTIVE_MATCHED_STATE_RESERVATION_REQUIRED')
    inp,physics,scene=binding(request['configuration'],request['trajectory'])
    saved=request['physical_source'];xml=Path(saved['xml_path'])
    if (hashlib.sha256(xml.read_bytes()).hexdigest()!=saved['xml_sha256'] or
            saved['model_identity']!=physics['identity'] or saved['scene_identity']!=scene['identity'] or
            len(saved['samples'])!=36 or request['indices']!=[0,15,29] or
            request['resolutions']!=[4,8]):
        raise ValueError('MATCHED_STATE_SOURCE_OR_SCOPE_MISMATCH')
    model=mujoco.MjModel.from_xml_path(str(xml));data=mujoco.MjData(model)
    joints=[model.joint(name).id for name in physics['dofs']]
    qi=model.jnt_qposadr[joints];vi=model.jnt_dofadr[joints]
    names=[t['entity'] for t in physics['tendons']]
    aids=[model.actuator(name+'_direct_tension').id for name in names]
    tids=[model.tendon(name).id for name in names]
    if (model.actuator_trnid[aids,0].tolist()!=tids or
            not np.all(model.actuator_gainprm[aids,0]==-1) or
            not np.all(model.actuator_gear[aids,0]==1) or
            not np.all(model.actuator_dyntype[aids]==mujoco.mjtDyn.mjDYN_NONE)):
        raise ValueError('MATCHED_STATE_IDEAL_TENSION_ACTUATOR_MISMATCH')
    dt=scene['control_period_s'];substeps=round(dt/model.opt.timestep)
    if substeps!=20 or abs(substeps*model.opt.timestep-dt)>1e-12:
        raise ValueError('MATCHED_STATE_MUJOCO_CLOCK_MISMATCH')
    control=checked_control(inp)
    spec=SorosimModel(dict(basis=control.recipe.basis,
        gauss_per_interval=control.solver.gauss_per_interval)).convert(
        inp.robot.structure.data,inp.policy.discretization.data,inp.task.environment.data,
        solver=control.solver)
    if spec['identity']!=request['trajectory']['model_identity']:
        raise ValueError('MATCHED_STATE_SOROSIM_MODEL_MISMATCH')
    mujoco.mj_resetData(model,data)
    data.qpos[qi]=scene['qpos_rad'];data.qvel[vi]=scene['qvel_rad_s']
    tip=model.site('tip_site').id;jac=np.zeros((3,model.nv))
    commands=np.asarray(request['trajectory']['tensions_n'],dtype=float)

    def sample(index):
        mujoco.mj_forward(model,data)
        mujoco.mj_jacSite(model,data,jac,None,tip)
        p=data.site_xpos[tip].copy();v=jac@data.qvel
        archived=saved['samples'][index]
        errors=dict(qpos=float(np.max(np.abs(data.qpos[qi]-archived['qpos_rad']))),
            qvel=float(np.max(np.abs(data.qvel[vi]-archived['qvel_rad_s']))),
            tip=float(np.max(np.abs(p-archived['tip_m']))),
            velocity=float(np.max(np.abs(v-archived['tip_velocity_m_s']))))
        if (abs(float(data.time)-index*dt)>1e-10 or max(errors.values())>1e-9):
            raise ValueError('ARCHIVED_MUJOCO_CHECKPOINT_RECONSTRUCTION_MISMATCH: '
                +json.dumps(dict(index=index,errors=errors)))
        return dict(position=p.tolist(),velocity=v.tolist(),archive_errors=errors,
            qpos_rad=data.qpos[qi].tolist(),qvel_rad_s=data.qvel[vi].tolist(),
            qacc_warmstart=data.qacc_warmstart.tolist(),engine_time_s=float(data.time))

    before=sample(0);checkpoints=[];steps=0
    for index in range(30):
        if index in request['indices']:
            projection=project(physics,inp.robot.structure.data,before['qpos_rad'],
                before['qvel_rad_s'],basis=control.recipe.basis,convention=PROJECTOR_ID)
            checkpoints.append(dict(index=index,time_s=index*dt,before=before,
                projection=projection,following_command_index=index,
                tension_n=commands[index].tolist()))
        data.ctrl[aids]=commands[index];data.xfrc_applied[:]=0
        mujoco.mj_forward(model,data)
        actual=-data.actuator_force[aids].copy()
        if not np.allclose(actual,commands[index],rtol=0,atol=1e-9):
            raise ValueError('MATCHED_STATE_ACTUAL_TENSION_MISMATCH')
        for substep in range(substeps):
            previous=float(data.time);mujoco.mj_step(model,data);steps+=1
            if _mujoco_state_failed(data,previous):
                raise ValueError(f'MATCHED_STATE_MUJOCO_NUMERICAL_FAILURE:{index}:{substep+1}')
        after=sample(index+1)
        if index in request['indices']:
            checkpoints[-1].update(after=after,actual_tension_n=actual.tolist())
        before=after
    if len(checkpoints)!=3:
        raise ValueError('MATCHED_STATE_CHECKPOINT_COUNT_MISMATCH')

    with SorosimSession() as session:
        session.construct(spec)
        for checkpoint in checkpoints:
            p=checkpoint['projection'];x=p['q_gvs']+p['qdot_gvs']
            checkpoint['sorosim']={}
            for count in request['resolutions']:
                t=checkpoint['time_s']
                result=session.evaluate('diagnose',dict(kind='fixed_sequence',x=x,
                    u=checkpoint['tension_n'],a=[0.]*len(p['q_gvs']),
                    tensions_n=[checkpoint['tension_n']],times_s=[t,t+dt],
                    period_s=dt,substeps=count))
                row=dict(status=result['status'],complete=result['complete'],
                    roots=result['roots'],failed_root=result.get('failed_root'),
                    initial_state=result['initial_state'],states=result['states'],
                    tip_positions_m=result['tip_positions_m'],
                    tip_velocities_m_s=result['tip_velocities_m_s'],
                    maximum_force_residual_nm2=result['maximum_force_residual_nm2'],
                    residual_verified_nonpositive_exitflags=result.get('residual_verified_nonpositive_exitflags'))
                for field,outputs in [('position','tip_positions_m'),('velocity','tip_velocities_m_s')]:
                    start=np.asarray(result[outputs][0])-checkpoint['before'][field]
                    row[field]=dict(e_projection=start.tolist(),projection_norm=float(np.linalg.norm(start)),
                        e_one_step=None,e_increment=None,one_step_norm=None,increment_norm=None)
                if result['complete']:
                    for field,outputs in [('position','tip_positions_m'),('velocity','tip_velocities_m_s')]:
                        row[field]=_vectors(dict(start=result[outputs][0],end=result[outputs][1]),
                            dict(start=np.asarray(checkpoint['before'][field]),
                                 end=np.asarray(checkpoint['after'][field])))
                checkpoint['sorosim'][str(count)]=row
        environment=dict(dependency=session.dependency,environment=session.environment,timings=session.timings)
    return dict(status='completed',model_identity=spec['identity'],physics_identity=physics['identity'],
        scene_identity=scene['identity'],source_xml_sha256=saved['xml_sha256'],
        projector=PROJECTOR_ID,checkpoint_indices=request['indices'],
        mathematical_substeps=request['resolutions'],checkpoints=checkpoints,
        physical_steps=steps,physical_probe_steps=len(checkpoints)*substeps,
        checkpoint_reconstruction_steps=steps-len(checkpoints)*substeps,
        physical_probe_count=len(checkpoints),mathematical_one_interval_integrations=6,
        numerical_environment=environment,task_acceptance='unmeasured')


def dispatch(host, query, key):
    guard(host,True);s=state(host)
    candidate=plain(query.candidate);cfg=verify_candidate(host,candidate)['configuration']
    source_ref=plain(query.source);source=host.store.artifact(source_ref)
    physical_ref=plain(query.physical_source);physical=host.store.artifact(physical_ref)
    if (source.get('source_kind')!='verified_mathematical_trajectory' or
            not source['posthoc_verification']['checks']['repaired_verification_passed'] or
            physical.get('source_kind')!='historical_fixed_tension_physical_samples'):
        raise ValueError('MATCHED_STATE_VERIFIED_SOURCES_REQUIRED')
    _,physics,scene=binding(cfg,source['trajectory'])
    if physical['model_identity']!=physics['identity'] or physical['scene_identity']!=scene['identity']:
        raise ValueError('MATCHED_STATE_CANDIDATE_PHYSICAL_SOURCE_MISMATCH')
    count=len(query.indices)
    if s.get('matched_state_probes',0)+count>s['spec']['budgets']['physical_launches']:
        raise ValueError('MATCHED_STATE_PHYSICAL_PROBE_BUDGET_EXHAUSTED')
    if s.get('mathematical_evaluations',0)+count*len(query.resolutions)>s['spec']['budgets']['mathematical_evaluations']:
        raise ValueError('MATCHED_STATE_MATHEMATICAL_PROBE_BUDGET_EXHAUSTED')
    request=dict(kind='matched_state',implementation=s['freeze'],study_id=host.run_id,
        store_root=str(host.store.root),request_id=key+'-matched',candidate=candidate,
        source_reference=source_ref,physical_source_reference=physical_ref,
        configuration=cfg,trajectory=source['trajectory'],physical_source=physical,
        indices=query.indices,resolutions=query.resolutions)
    old=host.store.lookup(host.run_id,request['request_id'])
    if old:
        if old['request_hash']!=digest(request):raise ValueError('MATCHED_STATE_OPERATION_COLLISION')
        if not old['receipt']:raise ValueError('RECOVER_MATCHED_STATE_NO_REPEAT')
        return dict(reference=json.loads(old['receipt'])['output'],additional_physical_probes=0)
    def charge(db):
        current=host.store.session(host.run_id,db)['state']
        current['matched_state_probes']=current.get('matched_state_probes',0)+count
        current['mathematical_evaluations']=current.get('mathematical_evaluations',0)+count*len(query.resolutions)
        host.store.update_state(db,host.run_id,current)
    row,_=host.store.reserve(host.run_id,request['request_id'],digest(request),host.actor,
        {**zero(),'backend_solves':count},resources=('backend.family_mujoco',),guard=charge)
    folder=host.store.root/'matched_state'/row['execution_id'];folder.mkdir(parents=True,exist_ok=True)
    atomic_json(folder/'request.json',request)
    update(host,pending=dict(kind='matched_state',worker_request_id=request['request_id'],
        folder=str(folder),implementation=s['freeze'],candidate=candidate,
        source_reference=source_ref,physical_source_reference=physical_ref))
    from tools.service_execution import _run_contained
    started=time.perf_counter()
    try:
        with (folder/'worker.log').open('w',encoding='utf8') as log:
            done=_run_contained([s['spec']['runtime']['research_python'],'-m',
                'tools.research.matched_state',str(folder/'request.json')],log,None)
        boundary=dict(termination_confirmed=True,returncode=done.returncode)
    except subprocess.TimeoutExpired as exc:
        boundary=dict(termination_confirmed=getattr(exc,'termination_confirmed',False),timed_out=True)
    boundary['elapsed_s']=time.perf_counter()-started
    atomic_json(folder/'boundary.json',boundary)
    return recover(host)


def recover(host):
    p=state(host)['pending'];folder=Path(p['folder']);boundary=read(folder/'boundary.json')
    if not boundary['termination_confirmed']:
        raise ValueError('UNKNOWN_MATCHED_STATE_OUTCOME_RETAINS_RESERVATION')
    value=read(folder/'result.json') if (folder/'result.json').exists() else dict(status='incomplete')
    value.update(boundary=boundary,implementation=p['implementation'],candidate=p['candidate'],
        source_reference=p['source_reference'],physical_source_reference=p['physical_source_reference'],
        charged_numerical_s=boundary['elapsed_s'])
    ref=save(host,value,'matched_state_result')
    row=host.store.lookup(host.run_id,p['worker_request_id'])
    with host.store.transaction() as db:
        current=host.store.session(host.run_id,db)['state']
        if current.get('pending')!=p:raise ValueError('ALREADY_SETTLED_MATCHED_STATE')
        current['numerical_s']+=boundary['elapsed_s'];current['pending']=None
        current.setdefault('matched_state_results',[]).append(ref)
        host.store.update_state(db,host.run_id,current)
        host.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],
            caller=host.actor,tool_id='research.matched_state',tool_version='1.0.0',
            execution_status='completed',charged=zero()),value,elapsed=boundary['elapsed_s'],db=db)
    return dict(reference=ref,**value)


if __name__=='__main__':
    request=read(sys.argv[1]);folder=Path(sys.argv[1]).resolve().parent
    try:
        result=calculate(request,folder)
    except Exception as exc:
        import traceback
        result=dict(status='diagnostic_error',error=type(exc).__name__,message=str(exc),
            traceback=traceback.format_exc())
    atomic_json(folder/'result.json',result)
