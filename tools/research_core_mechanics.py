"""Small mechanics adapter using the current core's evidence and shared budget."""
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import subprocess
import time
from tools.state_io import atomic_json, read, digest
from tools.platform_store import plain, zero


def source(host, reference):
    from tools.research_core import state
    if plain(reference) not in state(host).get('mechanics_results', []):
        raise ValueError('OWNED_CURRENT_STUDY_MECHANICS_RESULT_REQUIRED')
    value = host.store.artifact(reference)
    if value['operation'] != 'solve' or not value.get('candidate'):
        raise ValueError('MECHANICS_SOLVE_WITH_RETURNED_SCHEDULE_REQUIRED')
    return value


def handoff(host, reference, parameters=None, provenance=None):
    from tools.research_core import construct, state, update, save
    v = source(host, reference); c = v['candidate']; d = c['d']
    if not math.isfinite(d) or not -1.-1e-8 <= d <= 1.+1e-8:
        raise ValueError('RETURNED_STRUCTURE_OUTSIDE_AUTHORIZED_DOMAIN')
    d = min(1., max(-1., d))
    p = dict(parameters or state(host)['spec']['reference_parameters'])
    if parameters is not None and abs(p['d']-d) > 1e-10:
        raise ValueError('HANDOFF_STRUCTURE_MUST_MATCH_MECHANICS_SOURCE')
    p['d'] = d
    candidate = construct(host, p, dict(origin='mechanics_handoff', mechanics_attempt=plain(reference)))
    relation = dict(candidate=candidate, mechanics_attempt=plain(reference),
        offline_trajectory=v['trajectory_reference'], structure=dict(d=d,lengths_m=[.16+.0055*d,.11-.0055*d]),
        original_task_feasible=v.get('original_task_feasible',False), relaxed_nlp_feasible=v.get('relaxed_nlp_feasible',False),
        evaluation_mode='goal_based_NMPC; offline trajectory retained as evidence',
        exploratory=not v.get('original_task_feasible',False), provenance=provenance)
    ref = save(host,relation,'mechanics_candidate_handoff')
    update(host,handoffs=[*state(host).get('handoffs',[]),ref])
    return dict(reference=ref,**relation)


def dispatch(host, operation, arguments, key):
    from tools import research_core as core
    core.guard(host,True); s = core.state(host); b = s['spec']['budgets']
    reserve = s['spec']['mechanics_allowances'][operation+'_s']; counter = 'offline_nlp' if operation=='solve' else 'bdf_replays'
    if s.get(counter,0) >= b[counter]: raise ValueError('MECHANICS_RESOURCE_CEILING: '+counter)
    available = min(b['numerical_s']-s['numerical_s']-s['numerical_reserved_s'],s['cutoff_unix']-time.time(),host.store.remaining()['remaining']['wall_s'])
    if available < reserve+2*core.allowance(s): raise ValueError('MECHANICS_AND_TWO_CONFIRMATIONS_CANNOT_FIT')
    cfg,_ = core.configuration_for(host,s['spec']['reference_parameters'],host.run_id)
    request = dict(study_id=host.run_id,store_root=str(host.store.root),request_id=key+'-mechanics',
        operation=operation,configuration=cfg,implementation=s['freeze'],science_hashes=s['profile']['science_hashes'])
    if operation=='solve':
        request['arguments']=plain(arguments)
        if request['arguments'].get('source_candidate'):
            request['saved_tensions']=source(host,request['arguments']['source_candidate'])['candidate']['tensions_n']
    else:
        v=source(host,arguments); c=deepcopy(v['candidate'])
        import numpy as np
        u=np.asarray(c['tensions_n']); clipped=np.clip(u,0.,8.)
        if u.shape!=(35,6) or not np.isfinite(u).all() or np.max(abs(u-clipped))>1e-5:
            raise ValueError('FINITE_BOUNDED_RETURNED_SCHEDULE_REQUIRED')
        c.update(tensions_n=clipped.tolist(),replay_input_clip_max_n=float(np.max(abs(u-clipped))))
        request.update(candidate=c,source_mechanics=plain(arguments))
    def charge(db):
        current=host.store.session(host.run_id,db)['state']
        current[counter]=current.get(counter,0)+1; current['numerical_reserved_s']+=reserve
        host.store.update_state(db,host.run_id,current)
    row,_=host.store.reserve(host.run_id,request['request_id'],digest(request),host.actor,
        {**zero(),'wall_s':reserve},kind='mechanics',guard=charge)
    folder=host.store.root/'mechanics'/row['execution_id']; folder.mkdir(parents=True,exist_ok=True)
    inp,out,progress=folder/'input.json',folder/'output.json',folder/'progress.json'
    request['progress']=str(progress); atomic_json(inp,request)
    pending=dict(kind='mechanics',worker_request_id=request['request_id'],operation_key=key,operation=operation,
        original_request=request,
        input=str(inp),output=str(out),progress=str(progress),reserved_s=reserve,started_unix=time.time())
    core.update(host,pending=pending)
    return run_and_settle(host,row,request,pending)


def run_and_settle(host,row,request,pending,recovery=False):
    from tools import research_core as core
    reserve=pending['reserved_s']; started=time.perf_counter()
    env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    log=b''; out=Path(pending['output']); progress=Path(pending['progress'])
    def worker(req,seconds):
        inp=Path(pending['input']); atomic_json(inp,req)
        return subprocess.run([str(core.PYTHON),'-m','tools.research_core_mechanics_worker',str(inp),str(out)],
            cwd=core.ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=seconds)
    if recovery:
        if out.exists(): value=read(out)
        elif progress.exists() and read(progress).get('phase')=='solver_returned':
            process=worker(dict(request,operation='recover'),reserve); log=process.stdout;value=read(out)
        else: raise ValueError('UNKNOWN_MECHANICS_OUTCOME_RETAINS_RESERVATION; NO_SECOND_SOLVE')
    else:
        try:
            process=worker(request,reserve);log=process.stdout
            value=read(out) if out.exists() else dict(status='worker_no_output',returncode=process.returncode)
        except subprocess.TimeoutExpired as exc:
            log=exc.stdout or b'';value=dict(status='known_killed_waited_timeout',timeout_s=reserve)
    checkpoint=read(progress) if progress.exists() else None
    checkpoint_ref=core.save(host,checkpoint,'mechanics_checkpoint') if checkpoint else None
    if checkpoint and checkpoint.get('phase')=='solver_returned' and not value.get('candidate'):
        failure=deepcopy(value);remaining=reserve-(time.perf_counter()-started)
        if remaining>0:
            try:
                process=worker(dict(request,operation='recover'),remaining);log+=process.stdout;value=read(out)
            except subprocess.TimeoutExpired: value=dict(status='checkpoint_packaging_timeout')
        value.update(original_packaging_failure=failure,checkpoint_preserved=True)
    elapsed=time.perf_counter()-started
    # Recovery of a previously unknown outcome charges its original reservation,
    # plus measured packaging time; counters and clocks are never reset.
    charged=elapsed+(reserve if recovery else 0.)
    trajectory=core.save(host,value['candidate'],'offline_state_tension_trajectory') if value.get('candidate') else None
    value.update(operation=request['operation'],execution_id=row['execution_id'],owning_study=host.run_id,
        original_request=core.save(host,request,'mechanics_original_request'),source_mechanics=request.get('source_mechanics'),
        checkpoint_reference=checkpoint_ref,trajectory_reference=trajectory,
        log_reference=core.save(host,dict(text=log.decode('utf8',errors='replace')),'mechanics_worker_log'),
        implementation=request['implementation'],charged_numerical_s=charged,process_elapsed_s=elapsed,
        physical_validation='not_run; BDF is independent integration of the model, not physical validation',
        objective_definition=request.get('arguments'), variable_order=(checkpoint or {}).get('variable_order'))
    ref=core.save(host,value,'mechanics_'+request['operation'])
    with host.store.transaction() as db:
        current=host.store.session(host.run_id,db)['state']
        current['numerical_s']+=charged;current['numerical_reserved_s']-=reserve;current['pending']=None
        current['mechanics_results']=[*current.get('mechanics_results',[]),ref]
        host.store.update_state(db,host.run_id,current)
        host.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=host.actor,
            tool_id='research.core_mechanics',tool_version='1.0.0',execution_status='completed',charged=zero()),value,elapsed=charged,db=db)
    result=dict(reference=ref,**{k:value.get(k) for k in ('status','operation','execution_id','owning_study','termination_reason',
        'trajectory_reference','checkpoint_reference','relaxed_nlp_feasible','original_task_feasible','hard_max_normalized_violation',
        'trajectory_metrics','original_task_gaps','charged_numerical_s','costs_s','replay','physical_validation')})
    if value.get('candidate'):
        try:result['handoff']=handoff(host,ref)
        except ValueError as exc: result['handoff_failure']=str(exc)
    return result


def recover(host):
    from tools import research_core as core
    p=core.state(host)['pending'];row=host.store.lookup(host.run_id,p['worker_request_id'])
    return run_and_settle(host,row,p['original_request'],p,recovery=True)
