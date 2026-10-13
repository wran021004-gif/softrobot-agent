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


def bind_source(host):
    """Bind one sealed run for evaluation; copied consumption stays historical."""
    import hashlib
    from tools import research_core as core
    from tools.platform_store import Store
    source=core.state(host)['spec']['rl_evaluation_source']
    old=Store(core.ROOT/'runs'/source['study_id']); sealed=old.session(source['study_id'])['state']
    entry=deepcopy(sealed['rl_runs'][source['run_id']]); directory=run.run_path(source['run_id'])
    config=run.read_json(directory/'config.json'); generation=source['checkpoint']
    if Path(generation).name!=generation: raise ValueError('Published checkpoint name required')
    policy=directory/'checkpoints'/generation/'policy.zip'; metadata=run.read_json(policy.with_name('metadata.json'))
    if (sealed['research_status']!='stopped' or entry['status']['worker_alive'] or run.worker_alive(directory)
            or generation not in run.read_json(directory/'checkpoint.json').values()
            or config!=old.artifact(entry['configuration']) or config['candidate']['reference']!=entry['candidate']
            or config['task']['original']!=old.artifact(entry['task'])
            or metadata['config_sha256']!=source['config_sha256']
            or metadata['policy_file_sha256']!=source['policy_sha256']
            or hashlib.sha256(policy.read_bytes()).hexdigest()!=source['policy_sha256']):
        raise ValueError('Pinned sealed evaluation source identity mismatch')
    for field in ('candidate','task','configuration',*(['training_summary'] if entry.get('training_summary') else [])):
        if core.save(host,old.artifact(entry[field]),'linked_source_'+field)!=entry[field]:
            raise ValueError('Source artifact identity changed')
    history=dict(study_id=source['study_id'],run_id=source['run_id'],checkpoint=generation,
        training_status=entry['status']['status'],consumed=entry['status']['consumed'],optimization=metadata['inherited'],
        previous_evaluations=[old.artifact(r) for r in sealed.get('rl_evaluations',[])],engineering_closeout=sealed.get('engineering_closeout'),accepted_historical_stop=not bool(sealed.get('engineering_closeout')),newly_incurred=False)
    entry.update(source_study=source['study_id'],historical_consumption=entry['status'].pop('consumed'),
        allocation=dict(actions=0,active_seconds=0),active_reservation=None,evaluations=0,replays=0)
    candidate=old.artifact(entry['candidate']); candidates=core.state(host)['candidates']
    candidates[candidate['identity']]=entry['candidate']
    core.update(host,candidates=candidates,rl_source_candidate=entry['candidate'],
        rl_runs={source['run_id']:entry},rl_task=entry['task'],rl_training_summaries=[entry['training_summary']] if entry.get('training_summary') else [],
        rl_source_summary=core.save(host,history,'linked_source_training_summary'))


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
    cfg['requested_allocation']=plain(request.allocation)
    cfg['budget']['actions']=(cfg['budget']['actions']//cfg['ppo']['n_steps'])*cfg['ppo']['n_steps']
    if cfg['budget']['actions']<2*cfg['ppo']['n_steps']:
        raise ValueError('Allocation must align with rollouts and permit at least two complete optimizations')
    return run.resolve_config(cfg),task_ref


def invoke(operation, run_id, *arguments, deadline=float("inf"), timeout_s=150.):
    from tools.research_core import ROOT
    import os
    env={k:os.environ[k] for k in ('SystemRoot','WINDIR','PATH','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','COMSPEC','PATHEXT') if k in os.environ}
    env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    result=subprocess.run([str(run.PYTHON),'-m','tools.rl.run',operation,'--run-id',run_id,*map(str,arguments)],
        cwd=ROOT,env=env,capture_output=True,text=True,timeout=min(120. if operation=='evaluate' else timeout_s,timeout_s,max(.001,deadline-time.time())),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode: raise RuntimeError(result.stderr[-3000:])
    return json.loads(result.stdout)


def reconcile(host, run_id, lightweight=False):
    """Replace cumulative facts by identity; querying never sums them again."""
    from tools import research_core as core
    entry=core.state(host)['rl_runs'][run_id]
    if entry.get('source_study'):
        if run.worker_alive(run.run_path(run_id)): raise ValueError('Sealed source worker unexpectedly alive')
        return entry['status']
    if lightweight:
        directory=run.run_path(run_id)
        with run.locked(directory): value=dict(run.reconcile(directory))
        value.update(worker_alive=run.worker_alive(directory),run_id=run_id)
    else: value=run.status(run_id)
    with host.store.transaction() as db:
        s=host.store.session(host.run_id,db)['state']; entry=s['rl_runs'][run_id]
        previous=entry.get('status',{}).get('consumed',{})
        if any(value['consumed'].get(k,0)<v for k,v in previous.items()): raise ValueError('RL consumption cannot decrease')
        s['numerical_s']=s.get('numerical_s',0.)+max(0.,value['consumed'].get('active_seconds',0)-previous.get('active_seconds',0))
        entry['status']=value
        entry['active_reservation']=entry['allocation'] if value['worker_alive'] else None
        host.store.update_state(db,host.run_id,s)
    return value


def evaluation_capacity(host, requested=1, confirmation=False):
    from tools import research_core as core
    s=core.state(host); reserve=0 if confirmation else core.confirmation_count(s)
    used=sum(e['evaluations'] for e in s.get('rl_runs',{}).values())
    seconds=s['spec'].get('rl_evaluation_allowance_s',150.)
    available=min(core.execution_deadline(host)-time.time(),host.store.remaining()['remaining']['wall_s'],s['spec']['budgets']['numerical_s']-s['numerical_s']-s['numerical_reserved_s'])
    fit=max(0,min(requested,s['spec']['rl_limits']['evaluation_episodes']-used-reserve,int(available//seconds)-reserve))
    return dict(admitted=fit,remaining_episodes=s['spec']['rl_limits']['evaluation_episodes']-used,confirmation_reserve=reserve,per_episode_s=seconds)


def training_capacity(host, work):
    from tools import research_core as core
    s=core.state(host); b=s['spec']['budgets']; remaining=host.store.remaining()['remaining']
    confirmations=core.confirmation_count(s)
    # Start/resume, terminal status+read, evaluation+read, each confirm+read, STOP.
    operations=6+3*confirmations
    requests=6+2*confirmations
    seconds=work['active_seconds']+(1+confirmations)*s['spec'].get('rl_evaluation_allowance_s',150.)
    if (b['protected_provider_requests']<requests or remaining['model_calls']<=b['protected_provider_requests']
            or remaining['tool_calls']<operations
            or evaluation_capacity(host,1)['admitted']<1
            or seconds>min(s['cutoff_unix']-time.time(),remaining['wall_s'],
                b['numerical_s']-s['numerical_s']-s['numerical_reserved_s'])):
        raise ValueError('TRAINING_AND_COMPLETE_CLOSEOUT_RESOURCES_CANNOT_FIT')


def confirm(host, selected, request_id):
    from tools import research_core as core
    r=host.store.artifact(selected)
    return dispatch(host,dict(operation='evaluate',run_id=r['run_id'],checkpoint=r['checkpoint'],rationale='Frozen selected solution; fresh confirmation; no training'),request_id,selected=selected)


def dispatch(host, value, request_id, selected=None):
    from tools import research_core as core
    q=RLRequest.model_validate(value); s=core.state(host); key=digest(plain(q))
    if not core.enabled(s['spec'],'rl'): raise ValueError('RL capability required')
    if s['spec'].get('allowed_rl_operations') is not None and q.operation not in s['spec']['allowed_rl_operations']:
        raise ValueError('RL operation outside declared follow-up scope')
    source=s['spec'].get('rl_evaluation_source')
    if source and (q.run_id!=source['run_id'] or q.operation not in ('status','evaluate')
            or (q.operation=='evaluate' and q.checkpoint!=source['checkpoint'])):
        raise ValueError('Only status and evaluation of the explicitly pinned source are authorized')
    old=host.store.lookup(host.run_id,request_id)
    if old:
        if old['request_hash']!=key: raise ValueError('RL_OPERATION_ID_COLLISION')
        if old['receipt']: return host.store.artifact(json.loads(old['receipt'])['output'])
        raise ValueError('Unsealed RL operation: inspect recorded run/output, never repeat side effect')
    core.admit_closeout(host,'research_rl',plain(q))
    core.guard(host,q.operation in ('start','resume') or q.replay)
    if q.operation=='start':
        if q.reference and not any(r.get('available') and r['candidate']==plain(q.candidate) and r['reference']==plain(q.reference) for r in compatible_references(host)):
            raise ValueError('Owned compatible advertised reference required')
        config,task_ref=prepare_input(host,q)
        matching=next((r for r,e in s.get('rl_runs',{}).items() if e['request_identity']==key),None)
        if matching:
            return dict(run_id=matching,duplicate_start=True,status=reconcile(host,matching))
        caps=s['spec']['rl_limits']; entries=list(s.get('rl_runs',{}).values())
        if (q.allocation.actions>caps.get('actions_per_trial',caps['training_actions'])
                or q.allocation.active_seconds>caps.get('seconds_per_trial',caps['training_active_seconds'])):
            raise ValueError('Declared per-trial RL ceiling exceeded')
        if (len(entries)>=caps['training_runs'] or sum(e['allocation']['actions'] for e in entries)+q.allocation.actions>caps['training_actions']
                or sum(e['allocation']['active_seconds'] for e in entries)+q.allocation.active_seconds>caps['training_active_seconds']):
            raise ValueError('Cumulative RL training ceiling exhausted')
    else:
        if q.run_id not in s.get('rl_runs',{}): raise ValueError('Owned RL run required')
    if q.operation in ('start','resume'):
        work=config['budget'] if q.operation=='start' else reconcile(host,q.run_id)['remaining']
        training_capacity(host,work)
    if q.operation=='evaluate' and evaluation_capacity(host,1,confirmation=selected is not None)['admitted']<1:
        raise ValueError('RL evaluation and route confirmation reserve cannot fit')
    cost={**zero(),'tool_calls':1,'backend_solves':int(q.operation=='start')}
    row,_=host.store.reserve(host.run_id,request_id,key,host.actor,cost,kind='rl_operation')
    evaluation_dispatched=False;operation_started=None
    try:
        if q.operation=='start':
            run_id=host.run_id+'-'+row['execution_id'][:8]
            entry=dict(candidate=plain(q.candidate),task=task_ref,configuration=core.save(host,config,'rl_frozen_input'),
                allocation=config['budget'],mathematical_handoffs=[r for r in s.get('handoffs',[]) if host.store.artifact(r)['candidate']==plain(q.candidate)],request_identity=key,requested_allocation=plain(q.allocation),active_reservation=config['budget'],evaluations=0,replays=0)
            runs=core.state(host).get('rl_runs',{}); runs[run_id]=entry; core.update(host,rl_runs=runs)
            path=host.store.root/'rl_inputs'/('config-'+row['execution_id']+'.json');run.write_json(path,config)
            result=invoke('start',run_id,'--config',path,deadline=s['cutoff_unix'])
            result.update(effective_configuration=entry['configuration'],requested_overrides=config['requested_overrides'],
                requested_allocation=plain(q.allocation),effective_allocation=config['budget'])
        elif q.operation in ('status','stop','resume'):
            if q.operation=='status':
                result=dict(reconcile(host,q.run_id))
                entry=core.state(host)['rl_runs'][q.run_id]
                summary=result.get('training_summary') or run.training_summary(run.run_path(q.run_id))
                summary=dict(summary, source_study=entry.get('source_study',host.run_id),newly_incurred=not bool(entry.get('source_study')))
                previous=entry.get('training_summary')
                if previous and {k:v for k,v in host.store.artifact(previous).items() if k!='observed_at_unix'}=={k:v for k,v in summary.items() if k!='observed_at_unix'}:
                    reference=previous
                else: reference=core.save(host,summary,'rl_training_summary')
                runs=core.state(host)['rl_runs'];runs[q.run_id]['training_summary']=reference
                refs=core.state(host).get('rl_training_summaries',[])
                core.update(host,rl_runs=runs,rl_training_summaries=refs if reference in refs else [*refs,reference])
                result.update(training_summary=host.store.artifact(reference),training_summary_reference=reference)
            else: result=invoke(q.operation,q.run_id,deadline=core.execution_deadline(host))
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
                if not generation or Path(generation).name!=generation or not (directory/'checkpoints'/generation/'metadata.json').is_file():
                    raise ValueError('Explicit published checkpoint required')
                counter='evaluations';limit=s['spec']['rl_limits']['evaluation_episodes']
                policy=directory/'checkpoints'/generation/'policy.zip'
                import hashlib
                policy_sha=hashlib.sha256(policy.read_bytes()).hexdigest()
                if source and (policy_sha!=source['policy_sha256'] or run.read_json(policy.with_name('metadata.json'))['config_sha256']!=source['config_sha256']):
                    raise ValueError('Pinned source checkpoint identity changed')
                if selected is not None and (host.store.artifact(selected)['policy_sha256']!=policy_sha or host.store.artifact(selected)['configuration']!=entry['configuration']):
                    raise ValueError('Selected checkpoint/configuration changed')
                arguments=['--policy',policy]
            else:
                capture=directory/q.failure if q.failure else None
                if not capture or not capture.resolve().is_relative_to((directory/'failures').resolve()) or not capture.exists():
                    raise ValueError('Owned pre-failure capture required; no compatible capture means inspection only')
                counter='replays';limit=s['spec']['rl_limits']['diagnostic_replays']
                arguments=['--capture',capture]
                if q.replay: arguments.append('--replay')
            physical=q.operation=='evaluate' or q.replay
            output=(host.store.root/'rl_outputs' if source else directory)/(q.operation+'-'+row['execution_id'])
            if physical:
                with host.store.transaction() as db:
                    st=host.store.session(host.run_id,db)['state']; runs=st['rl_runs']
                    if sum(e[counter] for e in runs.values())>=limit: raise ValueError('Cumulative '+counter+' ceiling exhausted')
                    runs[run_id][counter]+=1;host.store.update_state(db,host.run_id,st)
            evaluation_dispatched=q.operation=='evaluate'
            operation_started=time.perf_counter()
            result=invoke(q.operation,run_id,*arguments,'--output',output,deadline=core.execution_deadline(host),timeout_s=s['spec'].get('rl_diagnostic_allowance_s',60.) if q.operation=='diagnose' else s['spec'].get('rl_evaluation_allowance_s',150.))
            if source: result.update(source_study=source['study_id'],evaluation_owner=host.run_id)
            result.update(study=host.run_id,candidate=entry['candidate'],task=entry['task'],run_id=run_id,configuration=entry['configuration'],independent_evaluation_executed=q.operation=='evaluate')
            if q.operation=='evaluate':
                result.update(checkpoint=generation,checkpoint_training_step=run.read_json(policy.with_name('metadata.json')).get('inherited',{}).get('num_timesteps'),policy_sha256=policy_sha,role='confirmation' if selected is not None else 'development',selected_execution=plain(selected))
            reference=core.save(host,result,'rl_'+q.operation+'_evidence')
            if q.operation=='evaluate': core.update(host,rl_evaluations=[*core.state(host).get('rl_evaluations',[]),reference])
            result=dict(reference=reference,**result)
        host.store.complete(row,dict(request_id=request_id,execution_id=row['execution_id'],caller=host.actor,
            tool_id='research.core_rl',tool_version='1.0.0',execution_status='completed',charged=zero()),result)
        return result
    except Exception as exc:
        failure=dict(error=str(exc))
        if q.operation=='evaluate':
            failure=unavailable_evaluation(host,q.run_id,request_id,str(exc),uncertain=evaluation_dispatched,selected=selected)
        host.store.complete(row,dict(request_id=request_id,execution_id=row['execution_id'],caller=host.actor,
            tool_id='research.core_rl',tool_version='1.0.0',execution_status='failed',charged=zero(),error=str(exc)),failure)
        raise
    finally:
        if operation_started is not None:
            core.update(host,numerical_s=core.state(host)['numerical_s']+time.perf_counter()-operation_started)


def compatible_references(host):
    """Convert only the existing 35-interval, six-channel SI tension schedule."""
    import numpy as np
    import hashlib
    from tools import research_core as core
    from extensions.tendon_family.backends import physics_for
    from extensions.tendon_family.scene import assemble
    rows=[]
    for ref in core.state(host).get('handoffs',[]):
        relation=host.store.artifact(ref);v=host.store.artifact(relation['mechanics_attempt'])
        try:
            candidate=core.verify_candidate(host,relation['candidate']);trajectory=v['candidate']
            request=host.store.artifact(v['original_request']);scene=assemble(SessionInput.model_validate(candidate['configuration']),physics_for(SessionInput.model_validate(candidate['configuration'])))
            u=np.asarray(trajectory['tensions_n']);times=np.asarray(trajectory['times_s'])
            order=[t['entity'] for t in physics_for(SessionInput.model_validate(candidate['configuration']))['tendons']]
            if (request['configuration']['task']!=candidate['configuration']['task'] or abs(trajectory['d']-candidate['parameters']['d'])>1e-10
                    or trajectory['tendon_order']!=order
                    or order!=['near_t0','near_t1','near_t2','far_t0','far_t1','far_t2']
                    or scene['control_period_s']!=.01 or scene['duration_s']!=.35
                    or u.shape!=(35,6) or not np.isfinite(u).all() or np.any(u<0) or np.any(u>8)
                    or abs(times[0])>1e-12 or abs(times[-1]-.35)>1e-12
                    or any(not np.any(np.abs(times-k*.01)<1e-12) for k in range(36))):
                raise ValueError('Candidate/task/channel/interval/timing/bounds incompatibility; no resampling or clipping')
            folder=host.store.root/'rl_inputs';folder.mkdir(exist_ok=True)
            path=folder/(relation['offline_trajectory']['artifact_id']+'.npz')
            if not path.exists(): np.savez(path,saved_tensions_n=u)
            with np.load(path,allow_pickle=False) as saved:
                if not np.array_equal(saved['saved_tensions_n'],u): raise ValueError('Saved reference changed')
            rows.append(dict(candidate=relation['candidate'],handoff=ref,available=True,
                reference=dict(path=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),candidate_identity=candidate['identity'],task_identity=scene['task_identity'],tendon_order=order,control_period_s=.01),
                convention='35 zero-order-held interval tensions in N; .35s; mathematical source, MuJoCo acceptance unproven'))
        except (ValueError,KeyError,IndexError) as exc: rows.append(dict(candidate=relation['candidate'],handoff=ref,available=False,reason=str(exc)))
    return rows


def packet(host):
    from tools import research_core as core
    s=core.state(host)
    return dict(frozen_task=s['rl_task'],capabilities=dict(task='reach-and-hold',control='ideal_tension',
        modes=['direct','residual'],compatible_references=compatible_references(host),
        structural_coordinate='d in [-1,1]: lengths [.16+.0055*d,.11-.0055*d] m',
        defaults=run.read_json(Path(run.__file__).with_name('config.json'))),
        training_summaries=[dict(run_id=r,reference=e['training_summary'],evaluations=[v for v in s.get('rl_evaluations',[]) if host.store.artifact(v).get('run_id')==r]) for r,e in s.get('rl_runs',{}).items() if e.get('training_summary')],
        runs=s.get('rl_runs',{}),source_summary=s.get('rl_source_summary'),evaluations=[dict(reference=r,**host.store.artifact(r)) for r in s.get('rl_evaluations',[])],
        costs='RL active time/evaluation costs separate from provider wall time; elapsed study time uses one wall clock',
        live_elapsed_s=max(0,s.get('closed_unix',time.time())-s['started_unix']))



def unavailable_evaluation(host, run_id, operation_key, reason, uncertain=False, selected=None):
    """Seal actual failed evaluation-attempt evidence without inventing an episode."""
    from tools import research_core as core
    s=core.state(host);entry=s['rl_runs'][run_id]
    previous=next((r for r in s.get('rl_evaluations',[]) if host.store.artifact(r).get('operation_key')==operation_key),None)
    if previous:return dict(reference=previous,**host.store.artifact(previous))
    value=dict(study=host.run_id,candidate=entry['candidate'],task=entry['task'],run_id=run_id,
        configuration=entry['configuration'],operation_key=operation_key,role='confirmation' if selected is not None else 'development',selected_execution=plain(selected),failure_stage='independent evaluation',independent_evaluation_executed=False,
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
