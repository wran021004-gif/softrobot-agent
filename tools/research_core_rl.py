"""Owned candidate preparation and dispatch to the existing bounded RL runtime."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import time

from schemas.research_core import RLRequest
from schemas.platform import SessionInput
from tools.platform_store import plain, zero
from tools.state_io import digest
from tools.rl import run


def prepare_input(host, request):
    from tools import research_core as core
    from extensions.tendon_family.backends import physics_for
    from extensions.tendon_family.scene import assemble
    from extensions.tendon_family.mjcf import compile_xml
    c=core.verify_candidate(host,request.candidate)
    inp=SessionInput.model_validate(c['configuration'])
    p=physics_for(inp); scene=assemble(inp,p)
    if scene['control']['tension_execution_mode']!='ideal_tension':
        raise ValueError('Candidate uses length-servo; establish ideal_tension before construction')
    if scene['forces']: raise ValueError('RL external-force task semantics are unsupported')
    if inp.task.family!='task.reach': raise ValueError('Only reach-and-hold supported')
    folder=host.store.root/'rl_inputs'/c['identity']; folder.mkdir(parents=True,exist_ok=True)
    xml=compile_xml(p,scene,host.reg.parse(inp.policy.backend.parameters),folder/'candidate.xml').read_text(encoding='utf8')
    # Current generator emits inline meshes and no external assets.
    import xml.etree.ElementTree as ET
    if any(e.get('file') for e in ET.fromstring(xml).iter()):
        raise ValueError('External XML assets require explicit snapshot support')
    cfg=run.merge_overrides(request.training_overrides.model_dump(exclude_unset=True),request.reward_overrides.model_dump(exclude_unset=True))
    cfg.update(mode=request.mode,reference=plain(request.reference),budget=plain(request.allocation))
    cfg['candidate']=dict(xml=xml,sha256=__import__('hashlib').sha256(xml.encode()).hexdigest(),assets={},
        identity=c['identity'],reference=plain(request.candidate),task_identity=scene['task_identity'],provenance=c['provenance'])
    cfg['control_object']=dict(joint_names=list(p['dofs']),tendon_names=[t['entity'] for t in p['tendons']],
        actuator_names=[t['entity']+'_direct_tension' for t in p['tendons']],tip_site='tip_site',semantics='ideal_tension')
    task=deepcopy(c['configuration']['task']); period=scene['control_period_s']
    acceptance=task['evaluator']['parameters']['data']; settling=c['configuration']['policy']['controller']['parameters']['data']['settling']
    cfg['task']=dict(family=inp.task.family,target_m=scene['target_world_m'],initializer=scene['initial'],
        duration_s=scene['duration_s'],control_period_s=period,command_intervals=round(scene['duration_s']/period),
        tendon_order=cfg['control_object']['tendon_names'],original=task,
        acceptance=dict(position_limit_m=settling['position_limit_m'],terminal_position_limit_m=acceptance['tolerance_m'],
            holding_speed_limit_m_s=settling['speed_limit_m_s'],
            holding_steps=[k for k in range(round(scene['duration_s']/period)+1)
                if k*period>=scene['duration_s']-settling['window_s']-1e-12]))
    task_ref=core.state(host)['rl_task']
    if request.task is not None and plain(request.task)!=task_ref: raise ValueError('Owned frozen study task required')
    if task!=host.store.artifact(task_ref): raise ValueError('Candidate changed frozen study task')
    if cfg['budget']['actions']%cfg['ppo']['n_steps'] or cfg['budget']['actions']<2*cfg['ppo']['n_steps']:
        raise ValueError('Allocation must align with rollouts and permit at least two complete optimizations')
    return run.resolve_config(cfg),task_ref


def invoke(operation, run_id, *arguments, deadline=float("inf")):
    from tools.research_core import ROOT
    import os
    env={k:os.environ[k] for k in ('SystemRoot','WINDIR','PATH','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','COMSPEC','PATHEXT') if k in os.environ}
    env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    result=subprocess.run([str(run.PYTHON),'-m','tools.rl.run',operation,'--run-id',run_id,*map(str,arguments)],
        cwd=ROOT,env=env,capture_output=True,text=True,timeout=min(150,max(.001,deadline-time.time())),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode: raise RuntimeError(result.stderr[-3000:])
    return json.loads(result.stdout)


def reconcile(host, run_id):
    """Replace cumulative facts by identity; querying never sums them again."""
    from tools import research_core as core
    value=run.status(run_id)
    with host.store.transaction() as db:
        s=host.store.session(host.run_id,db)['state']; entry=s['rl_runs'][run_id]
        previous=entry.get('status',{}).get('consumed',{})
        if any(value['consumed'].get(k,0)<v for k,v in previous.items()): raise ValueError('RL consumption cannot decrease')
        entry['status']=value
        entry['active_reservation']=entry['allocation'] if value['worker_alive'] else None
        host.store.update_state(db,host.run_id,s)
    return value


def dispatch(host, value, request_id):
    from tools import research_core as core
    q=RLRequest.model_validate(value); s=core.state(host); key=digest(plain(q))
    if s['spec'].get('mode')!='rl_interface': raise ValueError('RL operation requires scoped RL study')
    old=host.store.lookup(host.run_id,request_id)
    if old:
        if old['request_hash']!=key: raise ValueError('RL_OPERATION_ID_COLLISION')
        if old['receipt']: return host.store.artifact(json.loads(old['receipt'])['output'])
        raise ValueError('Unsealed RL operation: inspect recorded run/output, never repeat side effect')
    core.guard(host,q.operation not in ('status','diagnose'))
    if host.store.remaining()['remaining']['model_calls']<=s['spec']['budgets']['protected_provider_requests'] and q.operation!='status':
        raise ValueError('Protected closeout allows RL status only')
    if q.operation=='start':
        config,task_ref=prepare_input(host,q)
        matching=next((r for r,e in s.get('rl_runs',{}).items() if e['request_identity']==key),None)
        if matching:
            return dict(run_id=matching,duplicate_start=True,status=reconcile(host,matching))
        caps=s['spec']['rl_limits']; entries=list(s.get('rl_runs',{}).values())
        if (len(entries)>=caps['training_runs'] or sum(e['allocation']['actions'] for e in entries)+q.allocation.actions>caps['training_actions']
                or sum(e['allocation']['active_seconds'] for e in entries)+q.allocation.active_seconds>caps['training_active_seconds']):
            raise ValueError('Cumulative RL training ceiling exhausted')
    else:
        if q.run_id not in s.get('rl_runs',{}): raise ValueError('Owned RL run required')
    cost={**zero(),'tool_calls':1,'backend_solves':int(q.operation=='start')}
    row,_=host.store.reserve(host.run_id,request_id,key,host.actor,cost,kind='rl_operation')
    evaluation_dispatched=False
    try:
        if q.operation=='start':
            run_id=host.run_id+'-'+row['execution_id'][:8]
            entry=dict(candidate=plain(q.candidate),task=task_ref,configuration=core.save(host,config,'rl_frozen_input'),
                allocation=plain(q.allocation),request_identity=key,active_reservation=plain(q.allocation),evaluations=0,replays=0)
            runs=core.state(host).get('rl_runs',{}); runs[run_id]=entry; core.update(host,rl_runs=runs)
            path=host.store.root/'rl_inputs'/('config-'+row['execution_id']+'.json');run.write_json(path,config)
            result=invoke('start',run_id,'--config',path,deadline=s['cutoff_unix'])
            result.update(effective_configuration=entry['configuration'],requested_overrides=config['requested_overrides'])
        elif q.operation in ('status','stop','resume'):
            if q.operation=='status': result=reconcile(host,q.run_id)
            else: result=invoke(q.operation,q.run_id,deadline=s['cutoff_unix'])
        elif q.operation=='diagnose' and not q.failure:
            directory=run.run_path(q.run_id)
            result=dict(run_id=q.run_id,replay_requested=q.replay,replay_executed=False,
                scope='Owned run evidence inspection only; no capture selected, zero physical steps',
                status=reconcile(host,q.run_id),available_captures=[str(p.relative_to(directory)) for p in (directory/'failures').glob('**/*.npz')],
                root_cause='unresolved',attempted_physics_steps=0)
        else:
            run_id=q.run_id; directory=run.run_path(run_id); entry=core.state(host)['rl_runs'][run_id]
            config=run.read_json(directory/'config.json')
            if config!=host.store.artifact(entry['configuration']): raise ValueError('Frozen RL input changed')
            if q.operation=='evaluate':
                status=reconcile(host,run_id)
                if status['worker_alive']: raise ValueError('Wait for worker to exit before independent evaluation')
                current=run.read_json(directory/'checkpoint.json')['current']
                generation=q.checkpoint or current
                if not generation or Path(generation).name!=generation or generation not in (current,run.read_json(directory/'checkpoint.json').get('previous')):
                    raise ValueError('Explicit published checkpoint required')
                counter='evaluations';limit=s['spec']['rl_limits']['evaluation_episodes']
                policy=directory/'checkpoints'/generation/'policy.zip'
                arguments=['--policy',policy]
            else:
                capture=directory/q.failure if q.failure else None
                if not capture or not capture.resolve().is_relative_to((directory/'failures').resolve()) or not capture.exists():
                    raise ValueError('Owned pre-failure capture required; no compatible capture means inspection only')
                counter='replays';limit=s['spec']['rl_limits']['diagnostic_replays']
                arguments=['--capture',capture]
                if q.replay: arguments.append('--replay')
            physical=q.operation=='evaluate' or q.replay
            output=directory/(q.operation+'-'+row['execution_id'])
            if physical:
                with host.store.transaction() as db:
                    st=host.store.session(host.run_id,db)['state']; runs=st['rl_runs']
                    if sum(e[counter] for e in runs.values())>=limit: raise ValueError('Cumulative '+counter+' ceiling exhausted')
                    runs[run_id][counter]+=1;host.store.update_state(db,host.run_id,st)
            evaluation_dispatched=q.operation=='evaluate'
            result=invoke(q.operation,run_id,*arguments,'--output',output,deadline=s['cutoff_unix'])
            result.update(study=host.run_id,candidate=entry['candidate'],task=entry['task'],run_id=run_id,configuration=entry['configuration'],independent_evaluation_executed=q.operation=='evaluate')
            reference=core.save(host,result,'rl_'+q.operation+'_evidence')
            if q.operation=='evaluate': core.update(host,rl_evaluations=[*core.state(host).get('rl_evaluations',[]),reference])
            result=dict(reference=reference,**result)
        host.store.complete(row,dict(request_id=request_id,execution_id=row['execution_id'],caller=host.actor,
            tool_id='research.core_rl',tool_version='1.0.0',execution_status='completed',charged=zero()),result)
        return result
    except Exception as exc:
        failure=dict(error=str(exc))
        if q.operation=='evaluate':
            failure=unavailable_evaluation(host,q.run_id,request_id,str(exc),uncertain=evaluation_dispatched)
        host.store.complete(row,dict(request_id=request_id,execution_id=row['execution_id'],caller=host.actor,
            tool_id='research.core_rl',tool_version='1.0.0',execution_status='failed',charged=zero(),error=str(exc)),failure)
        raise


def packet(host):
    from tools import research_core as core
    s=core.state(host)
    return dict(frozen_task=s['rl_task'],capabilities=dict(task='reach-and-hold',control='ideal_tension',
        modes=['direct','residual'],compatible_reference=None,reference_status='No compatible residual reference exists',
        structural_coordinate='d in [-1,1]: lengths [.16+.0055*d,.11-.0055*d] m',
        defaults=run.read_json(Path(run.__file__).with_name('config.json'))),
        runs=s.get('rl_runs',{}),evaluations=[dict(reference=r,**host.store.artifact(r)) for r in s.get('rl_evaluations',[])],
        costs='RL active time/evaluation costs separate from provider wall time; elapsed study time uses one wall clock',
        live_elapsed_s=max(0,time.time()-s['started_unix']))



def unavailable_evaluation(host, run_id, operation_key, reason, uncertain=False):
    """Seal actual failed evaluation-attempt evidence without inventing an episode."""
    from tools import research_core as core
    s=core.state(host);entry=s['rl_runs'][run_id]
    previous=next((r for r in s.get('rl_evaluations',[]) if host.store.artifact(r).get('operation_key')==operation_key),None)
    if previous:return dict(reference=previous,**host.store.artifact(previous))
    value=dict(study=host.run_id,candidate=entry['candidate'],task=entry['task'],run_id=run_id,
        configuration=entry['configuration'],operation_key=operation_key,independent_evaluation_executed=False,
        passed=False,task_performance='unmeasured',failure_reason=reason,episodes=[],evaluation_elapsed_s=0,
        counts=dict(attempted_actions=0,completed_actions=0,attempted_physics_steps=0),
        scope='Failed public evaluation request; no saved policy loaded, no fresh simulation episode or trajectory fabricated',
        run_status=entry.get('status'))
    if uncertain:
        value.update(independent_evaluation_executed=None,consumption_uncertain=True,evaluation_elapsed_s=None,
            counts=None,scope='Evaluation subprocess dispatched then failed; its episode allocation remains charged; physical consumption unknown, no zero-cost claim')
    ref=core.save(host,value,'rl_evaluation_unavailable')
    core.update(host,rl_evaluations=[*s.get('rl_evaluations',[]),ref])
    return dict(reference=ref,**value)
