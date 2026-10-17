from tools.research.design import verify_candidate
"""Owned candidate preparation and dispatch to the existing bounded RL runtime."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import time

from tools.research.contracts import RLRequest
from schemas.platform import SessionInput
from tools.platform_store import plain, zero
from tools.state_io import digest
from tools.rl import run


def prepare_input(host, request):
    from tools.research import state as state_api
    from extensions.tendon_family.backends import physics_for
    from extensions.tendon_family.scene import assemble
    from extensions.tendon_family.mjcf import compile_xml
    c=verify_candidate(host,request.candidate)
    inp=SessionInput.model_validate(c['configuration'])
    p=physics_for(inp)
    scene=assemble(inp,p)
    if scene['control']['tension_execution_mode']!='ideal_tension':
        raise ValueError('Candidate uses length-servo; establish ideal_tension before construction')
    if scene['forces']:
        raise ValueError('RL external-force task semantics are unsupported')
    if inp.task.family!='task.reach':
        raise ValueError('Only reach-and-hold supported')
    folder=host.store.root/'rl_inputs'/c['identity']
    folder.mkdir(parents=True,exist_ok=True)
    xml=compile_xml(p,scene,host.reg.parse(inp.policy.backend.parameters),folder/'candidate.xml').read_text(encoding='utf8')
    # Current generator emits inline meshes and no external assets.
    import xml.etree.ElementTree as ET
    if any(e.get('file') for e in ET.fromstring(xml).iter()):
        raise ValueError('External XML assets require explicit snapshot support')
    cfg=run.merge_overrides(request.training_overrides.model_dump(exclude_unset=True),request.reward_overrides.model_dump(exclude_unset=True),defaults=state_api.state(host)['spec']['control']['rl_defaults'])
    cfg.update(mode=request.mode or cfg['mode'],reference=plain(request.reference),
        budget=plain(request.allocation) if request.allocation else deepcopy(cfg['budget']),seed=inp.seed)
    if 'initial_tension_n' in request.model_fields_set:
        cfg['initial_tension_n']=request.initial_tension_n
    initial=cfg.get('initial_tension_n')
    if initial is not None and (cfg['mode']!='direct' or any(initial>t['force_limit_n'] for t in c['configuration']['robot']['structure']['data']['tendons'])):
        raise ValueError('INITIAL_POLICY_TENSION_REQUIRES_DIRECT_MODE_AND_ACTUAL_CHANNEL_BOUNDS')
    cfg['candidate']=dict(xml=xml,sha256=__import__('hashlib').sha256(xml.encode()).hexdigest(),assets={},
        identity=c['identity'],reference=plain(request.candidate),task_identity=scene['task_identity'],provenance=c['provenance'])
    cfg['control_object']=dict(joint_names=list(p['dofs']),tendon_names=[t['entity'] for t in p['tendons']],
        actuator_names=[t['entity']+'_direct_tension' for t in p['tendons']],tip_site='tip_site',semantics='ideal_tension')
    task=deepcopy(c['configuration']['task'])
    period=scene['control_period_s']
    acceptance=task['evaluator']['parameters']['data']
    settling=c['configuration']['policy']['controller']['parameters']['data']['settling']
    cfg['task']=dict(family=inp.task.family,target_m=scene['target_world_m'],initializer=scene['initial'],
        duration_s=scene['duration_s'],control_period_s=period,command_intervals=round(scene['duration_s']/period),
        tendon_order=cfg['control_object']['tendon_names'],original=task,
        acceptance=dict(position_limit_m=settling['position_limit_m'],terminal_position_limit_m=acceptance['tolerance_m'],
            holding_speed_limit_m_s=settling['speed_limit_m_s'],
            holding_steps=[k for k in range(round(scene['duration_s']/period)+1)
                if k*period>=scene['duration_s']-settling['window_s']-1e-12]))
    task_ref=state_api.state(host)['rl_task']
    if request.task is not None and plain(request.task)!=task_ref:
        raise ValueError('Owned frozen study task required')
    compared_task=deepcopy(task)
    if state_api.state(host)['spec'].get('start_mode')=='family_space':
        compared_task['initializer']['parameters']['data']=dict(
            rule=state_api.state(host)['spec']['candidate_initialization'])
    if compared_task!=host.store.artifact(task_ref):
        raise ValueError('Candidate changed frozen study task')
    cfg['requested_allocation']=plain(request.allocation)
    cfg['budget']['actions']=align_steps(cfg['budget']['actions'],cfg['ppo']['n_steps'])
    if cfg['budget']['actions']<2*cfg['ppo']['n_steps']:
        raise ValueError('Allocation must align with rollouts and permit at least two complete optimizations')
    return run.resolve_config(cfg),task_ref


def invoke(host,operation, run_id, *arguments, timeout_s=None,interpreter=None):
    from tools.research.state import ROOT,state
    interpreter=state(host)['spec']['runtime']['rl_python']
    import os
    env={k:os.environ[k] for k in ('SystemRoot','WINDIR','PATH','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','COMSPEC','PATHEXT') if k in os.environ}
    env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',SOFTROBOT_RL_RUNS=str(run.RUNS))
    result=subprocess.run([str(interpreter or run.PYTHON),'-m','tools.rl.run',operation,'--run-id',run_id,*map(str,arguments)],
        cwd=ROOT,env=env,capture_output=True,text=True,timeout=timeout_s,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:])
    return json.loads(result.stdout)


def reconcile(host, run_id, lightweight=False):
    """Replace cumulative facts by identity; querying never sums them again."""
    from tools.research import state as state_api
    run.RUNS=host.store.root/'rl'
    s=state_api.state(host)
    entry=s['rl_runs'].get(run_id) or s.get('rl_parent_sources',{})[run_id]
    if entry.get('source_directory'):
        if run.worker_alive(Path(entry['source_directory'])):
            raise ValueError('SEALED_CONTINUATION_PARENT_WORKER_ALIVE')
        return entry['status']
    if not run.run_path(run_id).exists() and entry.get('launch_failure'):
        summary=dict(run_id=run_id,status='failed',stop_reason='launch_failed_before_owned_run_creation',
            recorded_failure_stage='launcher validation/boot',checkpoint=None,consumed=dict(attempted_actions=0,active_seconds=0.),
            error=entry['launch_failure']['error'],scope='Engineering launch failure; policy performance unmeasured')
        value=dict(worker_alive=False,status='failed',run_id=run_id,consumed=summary['consumed'],
            training_summary=summary,remaining=entry['allocation'],consumption_uncertain=False,reservation={})
        runs=state_api.state(host)['rl_runs']
        runs[run_id].update(status=value,active_reservation=None)
        state_api.update(host,rl_runs=runs)
        return value
    if entry.get('source_study'):
        if run.worker_alive(run.run_path(run_id)):
            raise ValueError('Sealed source worker unexpectedly alive')
        return entry['status']
    if lightweight:
        directory=run.run_path(run_id)
        with run.locked(directory):
            value=dict(run.reconcile(directory))
        value.update(worker_alive=run.worker_alive(directory),run_id=run_id,remaining=dict(actions=max(0,entry['allocation']['actions']-value['consumed']['attempted_actions']),active_seconds=None))
    else:
        value=run.status(run_id)
    with host.store.transaction() as db:
        s=host.store.session(host.run_id,db)['state']
        entry=s['rl_runs'][run_id]
        previous=entry.get('status',{}).get('consumed',{})
        if any(value['consumed'].get(k,0)<v for k,v in previous.items()):
            raise ValueError('RL consumption cannot decrease')
        s['numerical_s']=s.get('numerical_s',0.)+max(0.,value['consumed'].get('active_seconds',0)-previous.get('active_seconds',0))
        entry['status']=value
        entry['active_reservation']=value.get('reservation',{}) if value['worker_alive'] else dict(actions=value['remaining']['actions'],uncertain=True) if value.get('consumption_uncertain') else None
        host.store.update_state(db,host.run_id,s)
    return value


def align_steps(requested, rollout):
    """Resolve upward alignment explicitly before admission, never during learn."""
    if type(requested) is not int or requested <= 0:
        raise ValueError('POSITIVE_FINITE_STAGE_STEPS_REQUIRED')
    effective = ((requested + rollout - 1)//rollout)*rollout
    if effective < 2*rollout:
        raise ValueError('STAGE_REQUIRES_AT_LEAST_TWO_COMPLETE_PPO_UPDATES')
    return effective


def prepare_continuation(host, request):
    from tools.research.state import state
    from tools.research.config import rl_configuration
    from tools.rl.continuation import config_digest, published_checkpoint, validate_compatibility
    s=state(host)
    entry=s['rl_runs'].get(request.run_id) or s.get('rl_parent_sources',{})[request.run_id]
    directory=Path(entry.get('source_directory') or run.run_path(request.run_id))
    status=reconcile(host,request.run_id)
    if status['worker_alive'] or status.get('consumption_uncertain'):
        raise ValueError('CONTINUE_REQUIRES_EXITED_PARENT_AND_RECONCILED_CONSUMPTION')
    source=run.read_json(directory/'config.json')
    if source!=host.store.artifact(entry['configuration']):
        raise ValueError('FROZEN_PARENT_CONFIGURATION_CHANGED')
    path,metadata=published_checkpoint(directory,source,request.checkpoint)
    training=request.training_overrides.model_dump(exclude_unset=True)
    reward=request.reward_overrides.model_dump(exclude_unset=True)
    allowed=state(host)['spec']['control']['continuation']
    if set(training)-set(allowed['ppo']) or set(reward)-set(allowed['reward']):
        raise ValueError('UNSUPPORTED_CONTINUATION_CHANGE; INITIALIZATION_ONLY_FIELDS_REQUIRE_START')
    config=rl_configuration(source,training,reward)
    config['budget']=plain(request.allocation)
    if config['budget']['active_seconds'] is not None:
        raise ValueError('SCIENTIFIC_TIMING_DISABLED')
    config['requested_allocation']=plain(request.allocation)
    config['budget']['actions']=align_steps(request.allocation.actions,config['ppo']['n_steps'])
    config['stop_at_boundary']=None
    config['lineage']=dict(parent_run_id=request.run_id,directory=str(directory.resolve()),
        checkpoint=request.checkpoint,configuration=entry['configuration'],config_sha256=config_digest(source),
        policy_sha256=metadata['policy_file_sha256'],source_lifetime_timesteps=metadata['inherited'].get('lifetime_timesteps',metadata['inherited']['num_timesteps']),
        optimizer='preserve',stage_schedule='new declared schedule from stage-local progress 1',
        history=[*source.get('lineage',{}).get('history',[]),dict(run_id=request.run_id,checkpoint=request.checkpoint)])
    validate_compatibility(source,config)
    return run.resolve_config(config),entry['task']


def import_continuation_source(host, parent, run_id):
    """Link a sealed parent without copying weights, old actions or old grants."""
    from tools.research.state import state,save,update
    from tools.rl.continuation import published_checkpoint
    s=state(parent);entry=s['rl_runs'][run_id]
    directory=parent.store.root/'rl'/run_id
    if s['research_status']!='stopped' or run.worker_alive(directory):
        raise ValueError('SEALED_EXITED_CONTINUATION_SOURCE_REQUIRED')
    config=parent.store.artifact(entry['configuration'])
    if config!=run.read_json(directory/'config.json'):
        raise ValueError('SEALED_PARENT_CONFIGURATION_CHANGED')
    generation=run.read_json(directory/'checkpoint.json')['current']
    published_checkpoint(directory,config,generation)
    current=state(host);candidate=parent.store.artifact(entry['candidate'])
    if candidate['effective_task_identity']!=digest(candidate['configuration']['task']):
        raise ValueError('PARENT_TASK_BINDING_CHANGED')
    compared=deepcopy(candidate['configuration']['task'])
    compared['initializer']['parameters']['data']=dict(rule=current['spec']['candidate_initialization'])
    if compared!=host.store.artifact(current['rl_task']):
        raise ValueError('PARENT_CONTINUATION_TASK_MISMATCH')
    for ref in (entry['configuration'],entry['candidate'],entry['task']):
        save(host,parent.store.artifact(ref),'sealed_continuation_source')
    sources=current.get('rl_parent_sources',{})
    sources[run_id]=dict(entry,source_directory=str(directory.resolve()),source_study=parent.run_id,
        status=dict(entry['status'],worker_alive=False),active_reservation=None)
    candidates=current['candidates'];candidates[candidate['identity']]=entry['candidate']
    update(host,rl_parent_sources=sources,candidates=candidates,rl_source_candidate=entry['candidate'])
    return dict(run_id=run_id,checkpoint=generation,source_study=parent.run_id,
        historical_actions=config['budget']['actions'],new_actions=0,
        accounting='parent is outside new rl_runs and consumes no new stage allocation')


def evaluation_capacity(host, requested=1, confirmation=False):
    from tools.research.state import state
    s=state(host)
    used=sum(e['evaluations'] for e in s.get('rl_runs',{}).values())
    left=s['spec']['rl_limits']['evaluation_episodes']-used
    fit=max(0,min(requested,left,host.store.remaining()['remaining']['backend_solves']))
    return dict(admitted=fit,remaining_episodes=left,confirmation_reserve=0,per_episode_s=None)


def training_capacity(host, work):
    from tools.research.state import state
    from tools.research.budget import protected
    s=state(host)
    remaining=host.store.remaining()['remaining']
    engineering=s['spec'].get('mode')=='engineering_numerical'
    stages=s.get('admitted_training_stages',len(s.get('rl_runs',{})))
    if stages>=s['spec']['rl_limits']['training_stages']:
        raise ValueError('TRAINING_STAGE_LIMIT_EXHAUSTED')
    caps=s['spec']['rl_limits']
    allocated=sum(entry['allocation']['actions'] for entry in s.get('rl_runs',{}).values())
    if ((caps['actions_per_trial'] is not None and work['actions']>caps['actions_per_trial']) or
            (caps['training_actions'] is not None and allocated+work['actions']>caps['training_actions'])):
        raise ValueError('RL_ACTION_COUNT_GRANT_EXHAUSTED')
    if (protected(host) or remaining['tool_calls']<6+s['spec']['budgets']['protected_public_operations']
        or (not engineering and remaining['model_calls']<4+s['spec']['budgets']['protected_provider_requests'])
        or remaining['backend_solves']<2 or evaluation_capacity(host)['admitted']<1):
        raise ValueError('TRAINING_AND_COMPLETE_CLOSEOUT_COUNTS_CANNOT_FIT')


def confirm(host, selected, request_id):
    from tools.research import state as state_api
    r=host.store.artifact(selected)
    return dispatch(host,dict(operation='evaluate',run_id=r['run_id'],checkpoint=r['checkpoint'],rationale='Frozen selected solution; fresh confirmation; no training'),request_id,selected=selected)


def dispatch(host, value, request_id, selected=None):
    from tools.research import state as state_api
    q=RLRequest.model_validate(value)
    s=state_api.state(host)
    key=digest(plain(q))
    if not state_api.enabled(s['spec'],'rl'):
        raise ValueError('RL capability required')
    if s['spec'].get('allowed_rl_operations') is not None and q.operation not in s['spec']['allowed_rl_operations']:
        raise ValueError('RL operation outside declared follow-up scope')
    run.RUNS=host.store.root/'rl'
    source=s['spec'].get('rl_evaluation_source')
    if source and (q.run_id!=source['run_id'] or q.operation not in ('status','evaluate')
            or (q.operation=='evaluate' and q.checkpoint!=source['checkpoint'])):
        raise ValueError('Only status and evaluation of the explicitly pinned source are authorized')
    old=host.store.lookup(host.run_id,request_id)
    if old:
        if old['request_hash']!=key:
            raise ValueError('RL_OPERATION_ID_COLLISION')
        if old['receipt']:
            return host.store.artifact(json.loads(old['receipt'])['output'])
        raise ValueError('Unsealed RL operation: inspect recorded run/output, never repeat side effect')
    state_api.admit_closeout(host,'research_rl',plain(q))
    state_api.guard(host,q.operation in ('start','continue','resume') or q.replay)
    if q.operation=='start':
        if q.reference and not any(r.get('available') and r['candidate']==plain(q.candidate) and r['reference']==plain(q.reference) for r in compatible_references(host,publish=False)):
            raise ValueError('Owned compatible advertised reference required')
        config,task_ref=prepare_input(host,q)
        matching=next((r for r,e in s.get('rl_runs',{}).items() if e['request_identity']==key),None)
        if matching:
            return dict(run_id=matching,duplicate_start=True,status=reconcile(host,matching))
    else:
        if q.run_id not in s.get('rl_runs',{}) and not (q.operation=='continue' and q.run_id in s.get('rl_parent_sources',{})):
            raise ValueError('Owned RL run required')
        if q.operation=='continue':
            config,task_ref=prepare_continuation(host,q)
    if q.operation in ('start','continue'):
        if config['budget']['active_seconds'] is not None:
            raise ValueError('SCIENTIFIC_TIMING_DISABLED')
        training_capacity(host,config['budget'])
    elif q.operation=='resume':
        # Recovery retains the original admitted stage, without testing a new-stage slot.
        previous=reconcile(host,q.run_id)
        if previous['worker_alive'] or not previous['remaining']['actions']:
            raise ValueError('RESUME_REQUIRES_EXITED_WORKER_AND_ORIGINAL_REMAINING_STEPS')
    from tools.research.feedback import confirmation_progress
    progress=confirmation_progress(host)
    frozen=bool(s.get('selected') and not (progress['failures'] or progress['invalid_executions']))
    if q.operation=='evaluate' and selected is not None:
        from tools.research.feedback import eligibility
        choice=eligibility(host,selected)
        if not choice['eligible']:
            raise ValueError('; '.join(choice['reasons']))
    if q.operation=='evaluate' and selected is None and (frozen or s['spec'].get('ordinary_evaluation_limit')==0 or evaluation_capacity(host,1)['admitted']<1):
        raise ValueError('Development evaluation rejected; confirmation uses '+json.dumps(confirmation_progress(host)))
    if q.operation=='evaluate' and evaluation_capacity(host,1,confirmation=selected is not None)['admitted']<1:
        raise ValueError('RL evaluation and route confirmation reserve cannot fit')
    scientific_preflight=None
    if q.operation=='evaluate':
        from tools.rl.continuation import published_checkpoint
        from tools.research.feedback import experiment_preflight
        entry=s['rl_runs'][q.run_id]
        directory=run.run_path(q.run_id)
        config=host.store.artifact(entry['configuration'])
        generation=q.checkpoint or run.read_json(directory/'checkpoint.json')['current']
        _,metadata=published_checkpoint(directory,config,generation)
        scientific_preflight=experiment_preflight(host,entry['candidate'],'rl',
            rl_configuration=config,policy_sha=metadata['policy_file_sha256'],
            repeat=selected is not None)
        if not scientific_preflight['admitted']:
            raise ValueError('EQUIVALENT_SCIENTIFIC_EXPERIMENT_REQUIRES_EXPLICIT_REPLICATION_GRANT: '
                +json.dumps(scientific_preflight,sort_keys=True))
    stage_id=None
    stage_entry=None
    if q.operation in ('start','continue'):
        from uuid import uuid4
        stage_id=host.run_id+'-'+uuid4().hex[:8]
        config['stage_identity']=dict(run_id=stage_id,study=host.run_id,implementation=s['freeze'],
            candidate=plain(q.candidate) if q.operation=='start' else (s['rl_runs'].get(q.run_id) or s['rl_parent_sources'][q.run_id])['candidate'],
            task=task_ref,rationale=q.rationale,requested_changes=plain(q))
        stage_entry=dict(candidate=config['stage_identity']['candidate'],task=task_ref,
            configuration=state_api.save(host,config,'rl_frozen_stage_input'),
            allocation=config['budget'],request_identity=key,requested_allocation=config['requested_allocation'],
            active_reservation=config['budget'],evaluations=0,replays=0,
            parent=config.get('lineage'),implementation=s['freeze'])
    cost={**zero(),'tool_calls':1,'backend_solves':int(q.operation in ('start','continue','resume','evaluate') or q.replay)}
    def charge(db):
        current=host.store.session(host.run_id,db)['state']
        if q.operation in ('start','continue'):
            from tools.research.budget import admit_stage
            admit_stage(current)
            current.setdefault('rl_runs',{})[stage_id]=stage_entry
        if q.operation in ('start','continue','resume','evaluate') or q.replay:
            state_api.charge_start(current)
        host.store.update_state(db,host.run_id,current)
    row,_=host.store.reserve(host.run_id,request_id,key,host.actor,cost,kind='rl_operation',guard=charge)
    dispatch_started=time.perf_counter()
    evaluation_dispatched=False
    operation_started=None
    try:
        if q.operation in ('start','continue'):
            run_id=stage_id
            entry=stage_entry
            path=host.store.root/'rl_inputs'/('config-'+row['execution_id']+'.json')
            path.parent.mkdir(parents=True,exist_ok=True)
            run.write_json(path,config)
            result=invoke(host,q.operation,run_id,'--config',path)
            result.update(effective_configuration=entry['configuration'],requested_overrides=config['requested_overrides'],
                requested_allocation=config['requested_allocation'],effective_allocation=config['budget'])
        elif q.operation in ('status','stop','resume'):
            if q.operation=='status':
                result=dict(reconcile(host,q.run_id))
                entry=state_api.state(host)['rl_runs'][q.run_id]
                summary=result.get('training_summary') or run.training_summary(run.run_path(q.run_id))
                summary=dict(summary, source_study=entry.get('source_study',host.run_id),newly_incurred=not bool(entry.get('source_study')))
                previous=entry.get('training_summary')
                if previous and {k:v for k,v in host.store.artifact(previous).items() if k!='observed_at_unix'}=={k:v for k,v in summary.items() if k!='observed_at_unix'}:
                    reference=previous
                else:
                    reference=state_api.save(host,summary,'rl_training_summary')
                runs=state_api.state(host)['rl_runs']
                runs[q.run_id]['training_summary']=reference
                refs=state_api.state(host).get('rl_training_summaries',[])
                state_api.update(host,rl_runs=runs,rl_training_summaries=refs if reference in refs else [*refs,reference])
                result.update(training_summary=host.store.artifact(reference),training_summary_reference=reference,
                    task_performance='unmeasured',next_operations=['evaluate'] if summary.get('checkpoint') and summary['checkpoint'].get('policy_present') else ['choose another authorized action','stop'])
            else:
                result=invoke(host,q.operation,q.run_id,*(['--force'] if q.force else []))
        elif q.operation=='diagnose' and not q.failure:
            directory=run.run_path(q.run_id)
            result=dict(run_id=q.run_id,replay_requested=q.replay,replay_executed=False,
                scope='Owned run evidence inspection only; no capture selected, zero physical steps',
                status=reconcile(host,q.run_id),available_captures=[str(p.relative_to(directory)) for p in (directory/'failures').glob('**/*.npz')],
                root_cause='unresolved',attempted_physics_steps=0)
        else:
            run_id=q.run_id
            directory=run.run_path(run_id)
            entry=state_api.state(host)['rl_runs'][run_id]
            config=run.read_json(directory/'config.json')
            if config!=host.store.artifact(entry['configuration']):
                raise ValueError('Frozen RL input changed')
            if q.operation=='evaluate':
                status=reconcile(host,run_id)
                if status['worker_alive']:
                    raise ValueError('Wait for worker to exit before independent evaluation')
                current=run.read_json(directory/'checkpoint.json')['current']
                generation=q.checkpoint or current
                if not generation or Path(generation).name!=generation or not (directory/'checkpoints'/generation/'metadata.json').is_file():
                    raise ValueError('Explicit published checkpoint required')
                counter='evaluations'
                limit=s['spec']['rl_limits']['evaluation_episodes']
                from tools.rl.continuation import published_checkpoint
                checkpoint_path,checkpoint_metadata=published_checkpoint(directory,config,generation)
                policy=checkpoint_path/'policy.zip'
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
                counter='replays'
                limit=s['spec']['rl_limits']['diagnostic_replays']
                arguments=['--capture',capture]
                if q.replay:
                    arguments.append('--replay')
            physical=q.operation=='evaluate' or q.replay
            output=(host.store.root/'rl_outputs' if source else directory)/(q.operation+'-'+row['execution_id'])
            experiment=state_api.save(host,dict(effective_configuration=config,source_configuration=entry['configuration'],
                requested_changes=plain(q),rationale=q.rationale,candidate=entry['candidate'],task=entry['task'],
                implementation=s['freeze'],science_hashes=s['profile']['science_hashes'],
                checkpoint=generation if q.operation=='evaluate' else None), 'rl_frozen_evaluation_input')
            if physical:
                with host.store.transaction() as db:
                    st=host.store.session(host.run_id,db)['state']
                    runs=st['rl_runs']
                    if sum(e[counter] for e in runs.values())>=limit:
                        raise ValueError('Cumulative '+counter+' ceiling exhausted')
                    runs[run_id][counter]+=1
                    host.store.update_state(db,host.run_id,st)
            evaluation_dispatched=q.operation=='evaluate'
            operation_started=time.perf_counter()
            result=invoke(host,q.operation,run_id,*arguments,'--output',output,timeout_s=None,interpreter=s['spec']['runtime']['rl_python'])
            if scientific_preflight is not None:
                result['scientific_preflight']=scientific_preflight
            if source:
                result.update(source_study=source['study_id'],evaluation_owner=host.run_id)
            result.update(study=host.run_id,candidate=entry['candidate'],task=entry['task'],run_id=run_id,
                configuration=entry['configuration'],experiment_configuration=experiment,implementation=s['freeze'],
                independent_evaluation_executed=q.operation=='evaluate')
            if q.operation=='evaluate':
                result.update(execution_id=row['execution_id'],operation_key=request_id,checkpoint=generation,checkpoint_training_step=run.read_json(policy.with_name('metadata.json')).get('inherited',{}).get('num_timesteps'),policy_sha256=policy_sha,role='confirmation' if selected is not None else 'development',selected_execution=plain(selected))
            reference=state_api.save(host,result,'rl_'+q.operation+'_evidence')
            if q.operation=='evaluate':
                state_api.update(host,rl_evaluations=[*state_api.state(host).get('rl_evaluations',[]),reference])
                from tools.research.budget import observe_pass
                observe_pass(host,reference)
            result=dict(reference=reference,**result)
        host.store.complete(row,dict(request_id=request_id,execution_id=row['execution_id'],caller=host.actor,
            tool_id='research.core_rl',tool_version='1.0.0',execution_status='completed',charged=zero()),result,elapsed=time.perf_counter()-dispatch_started)
        return result
    except Exception as exc:
        if stage_id:
            runs=state_api.state(host)['rl_runs']
            runs[stage_id].update(launch_failure=dict(error=str(exc),engineering_failure=True))
            state_api.update(host,rl_runs=runs)
        failure=dict(error=str(exc))
        if q.operation=='evaluate':
            failure=unavailable_evaluation(host,q.run_id,request_id,str(exc),uncertain=evaluation_dispatched,selected=selected)
        host.store.complete(row,dict(request_id=request_id,execution_id=row['execution_id'],caller=host.actor,
            tool_id='research.core_rl',tool_version='1.0.0',execution_status='failed',charged=zero(),error=str(exc)),failure,elapsed=time.perf_counter()-dispatch_started)
        raise
    finally:
        if operation_started is not None:
            state_api.update(host,numerical_s=state_api.state(host)['numerical_s']+time.perf_counter()-operation_started)


def compatible_references(host, *, publish=True):
    """Complete exact-candidate schedules remain usable even when task scores fail."""
    from tools.research.state import state,update
    if not publish:
        return state(host).get('compatible_residual_references',[])
    import numpy as np,hashlib
    from extensions.tendon_family.backends import physics_for
    from extensions.tendon_family.scene import assemble
    from tools.research.design import full_science
    sources=[]
    rows=[]
    for relation in state(host).get('imported_mathematical_references',[]):
        ref=relation['source'];candidate_ref=relation['candidate']
        value=host.store.artifact(ref)
        candidate=verify_candidate(host,candidate_ref)
        from tools.research.physical_replay import binding
        binding(candidate['configuration'],value['trajectory'])
        sources.append((ref,candidate_ref,value['trajectory'],candidate['configuration'],'mathematics'))
    for ref in state(host).get('mechanics_results',[]):
        value=host.store.artifact(ref)
        if value.get('operation')=='solve' and value.get('trajectory'):
            sources.append((ref,value['design_candidate'],value['trajectory'],host.store.artifact(value['original_request'])['configuration'],'mathematics'))
    for ref in state(host).get('results',[]):
        value=host.store.artifact(ref)
        if value.get('status')!='evaluated' or not value.get('execution',{}).get('receipts',{}).get('simulation'):
            continue
        candidate_ref=value['candidate']
        try:
            from extensions.tendon_family.control_evidence import ControlEvidence
            reader=ControlEvidence(host.store)
            source=reader.resolve(value['execution_id'])
            if host.store.artifact({'artifact_id':source['metadata']['artifact_id']})['solver_status']!='completed':
                raise ValueError('Complete backend execution required')
            observations=reader.read_file(source,'controller_observations.json',[])
            cfg=verify_candidate(host,candidate_ref)['configuration']
            if full_science(source['configuration'])!=full_science(cfg):
                raise ValueError('Exact reference scientific configuration required')
            trajectory=dict(tendon_order=[t['id'] for t in cfg['robot']['structure']['data']['tendons']],
                tensions_n=[o['actual_tension_n'] for o in observations],
                times_s=[o['time_s'] for o in observations]+[cfg['task']['timing']['duration_s']])
            sources.append((ref,candidate_ref,trajectory,cfg,'nmpc'))
        except (ValueError,KeyError) as exc:
            rows.append(dict(candidate=candidate_ref,source=ref,source_kind='nmpc',available=False,reason=str(exc)))
    for ref,candidate_ref,trajectory,source_cfg,kind in sources:
        try:
            candidate=verify_candidate(host,candidate_ref)
            cfg=candidate['configuration']
            inp=SessionInput.model_validate(cfg)
            physics=physics_for(inp)
            scene=assemble(inp,physics)
            order=[t['entity'] for t in physics['tendons']]
            limits=np.asarray([t['force_limit_n'] for t in cfg['robot']['structure']['data']['tendons']])
            period=cfg['task']['timing']['control_period_s']
            duration=cfg['task']['timing']['duration_s']
            steps=round(duration/period)
            u=np.asarray(trajectory['tensions_n'])
            times=np.asarray(trajectory['times_s'])
            if (source_cfg!=cfg or trajectory['tendon_order']!=order or u.shape!=(steps,len(order))
                or not np.isfinite(u).all() or np.any(u<0) or np.any(u>limits)
                or abs(times[0])>1e-12 or abs(times[-1]-duration)>1e-12
                or any(not np.any(np.abs(times-k*period)<1e-12) for k in range(steps+1))):
                raise ValueError('Exact candidate/task/order/grid/bounds required; no mapping, resampling or clipping')
            folder=host.store.root/'rl_inputs'
            folder.mkdir(exist_ok=True)
            path=folder/(ref['artifact_id']+'.npz')
            if not path.exists():
                np.savez(path,saved_tensions_n=u)
            with np.load(path,allow_pickle=False) as saved:
                if not np.array_equal(saved['saved_tensions_n'],u):
                    raise ValueError('Saved reference changed')
            rows.append(dict(candidate=candidate_ref,source=ref,source_kind=kind,available=True,
                reference=dict(path=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),candidate_identity=candidate['identity'],task_identity=scene['task_identity'],tendon_order=order,control_period_s=period),
                convention='Exact candidate/task/channel SI interval tensions; reference completeness does not imply task acceptance'))
        except (ValueError,KeyError,IndexError) as exc:
            rows.append(dict(candidate=candidate_ref,source=ref,source_kind=kind,available=False,reason=str(exc)))
    update(host,compatible_residual_references=rows)
    return rows


def import_mathematical_reference(host, candidate_ref, source_ref):
    """Admit a sealed, exact-candidate complete mathematical SI command grid."""
    from tools.research.state import state,update
    from tools.research.physical_replay import binding
    candidate_ref=plain(candidate_ref);source_ref=plain(source_ref)
    candidate=verify_candidate(host,candidate_ref)
    source=host.store.artifact(source_ref)
    if (source.get('source_kind')!='verified_mathematical_trajectory' or
            not source.get('posthoc_verification',{}).get('checks',{}).get('repaired_verification_passed')):
        raise ValueError('VERIFIED_MATHEMATICAL_TRAJECTORY_REQUIRED')
    binding(candidate['configuration'],source['trajectory'])
    relation=dict(candidate=candidate_ref,source=source_ref,
        mathematical_model_identity=source['trajectory']['model_identity'],
        task_identity=source['trajectory']['task_identity'],
        scope='Complete compatible tension reference; physical acceptance is separate')
    existing=state(host).get('imported_mathematical_references',[])
    if relation not in existing:
        update(host,imported_mathematical_references=[*existing,relation])
    return relation


def allocation_feedback(host):
    from tools.research.state import state
    from tools.research.budget import stage_usage
    s=state(host)
    usage=stage_usage(s)
    cap=s['spec']['rl_limits']['training_actions']
    allocated=sum(entry['allocation']['actions'] for entry in s.get('rl_runs',{}).values())
    return dict(authorized_limits=s['spec']['rl_limits'],stages=usage,
        remaining_stages=max(0,usage['limit']-usage['admitted']) if usage['limit'] is not None else None,
        aggregate_action_limit=cap,remaining_allocatable_actions=None if cap is None else max(0,cap-allocated),
        aggregate_training_time_limit=None,
        historical_requested_allocations='Frozen admitted allocations count against the engineering action cap; actual attempted actions are reported separately',
        evaluation_capacity=evaluation_capacity(host))


def packet(host):
    from tools.research import state as state_api
    s=state_api.state(host)
    failure_categories={run_id:run.failure_diagnosis(host.store.root/'rl'/run_id)
        for run_id in s.get('rl_runs',{}) if (host.store.root/'rl'/run_id).exists()}
    return dict(allocation_feedback=allocation_feedback(host),frozen_task=s['rl_task'],
        numerical_failure_categories=failure_categories,
        capabilities=dict(task='reach-and-hold',control='ideal_tension',
        modes=['direct','residual'],compatible_references=compatible_references(host,publish=False),
        structural_domain=s['spec']['allowed_parameters'],
        defaults=(s['spec'].get('control') or {'rl_defaults':s['spec']['runtime'].get('rl_defaults')})['rl_defaults']),
        training_summaries=[dict(run_id=r,reference=e['training_summary'],evaluations=[v for v in s.get('rl_evaluations',[]) if host.store.artifact(v).get('run_id')==r]) for r,e in s.get('rl_runs',{}).items() if e.get('training_summary')],
        runs=s.get('rl_runs',{}),source_summary=s.get('rl_source_summary'),evaluations=[dict(reference=r,**host.store.artifact(r)) for r in s.get('rl_evaluations',[])],
        costs='RL active time/evaluation costs separate from provider wall time; elapsed study time uses one wall clock',
        live_elapsed_s=max(0,s.get('closed_unix',time.time())-s['started_unix']))


def unavailable_evaluation(host, run_id, operation_key, reason, uncertain=False, selected=None):
    """Seal actual failed evaluation-attempt evidence without inventing an episode."""
    from tools.research import state as state_api
    s=state_api.state(host)
    entry=s['rl_runs'][run_id]
    previous=next((r for r in s.get('rl_evaluations',[]) if host.store.artifact(r).get('operation_key')==operation_key),None)
    if previous:
        return dict(reference=previous,**host.store.artifact(previous))
    value=dict(study=host.run_id,candidate=entry['candidate'],task=entry['task'],run_id=run_id,
        configuration=entry['configuration'],operation_key=operation_key,role='confirmation' if selected is not None else 'development',selected_execution=plain(selected),failure_stage='independent evaluation',independent_evaluation_executed=False,
        passed=False,task_performance='unmeasured',failure_reason=reason,episodes=[],evaluation_elapsed_s=0,
        counts=dict(attempted_actions=0,completed_actions=0,attempted_physics_steps=0),
        scope='Failed public evaluation request; no saved policy loaded, no fresh simulation episode or trajectory fabricated',
        run_status=entry.get('status'))
    if uncertain:
        value.update(independent_evaluation_executed=None,consumption_uncertain=True,evaluation_elapsed_s=None,
            counts=None,scope='Evaluation subprocess dispatched then failed; its episode allocation remains charged; physical consumption unknown, no zero-cost claim')
    ref=state_api.save(host,value,'rl_evaluation_unavailable')
    state_api.update(host,rl_evaluations=[*s.get('rl_evaluations',[]),ref])
    return dict(reference=ref,**value)
