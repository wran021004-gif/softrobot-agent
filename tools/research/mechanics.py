"""Native candidate-bound full-horizon solve/replay; separate from backend acceptance."""
from pathlib import Path
import json,subprocess,time
from tools.research.state import state,update,save,guard
from tools.research.design import verify_candidate
from tools.platform_store import plain,zero
from tools.state_io import atomic_json,read,digest

def source(host,reference):
    if plain(reference) not in state(host).get('mechanics_results',[]):
        raise ValueError('OWNED_MATHEMATICAL_RESULT_REQUIRED')
    value=host.store.artifact(reference)
    if value['operation']!='solve' or not value.get('trajectory'):
        raise ValueError('COMPLETED_SOLVE_TRAJECTORY_REQUIRED')
    return value

def handoff(host,reference,parameters=None,provenance=None):
    value=source(host,reference)
    candidate=verify_candidate(host,value['design_candidate'])
    if parameters is not None and plain(parameters)!=candidate['parameters']:
        raise ValueError('HANDOFF_REQUIRES_EXACT_SOLVED_CANDIDATE')
    return dict(candidate=value['design_candidate'],reference=plain(reference),trajectory=value['trajectory'],interpretation='Mathematical trajectory is not backend acceptance')

def dispatch(host,operation,arguments,key):
    guard(host,True)
    s=state(host)
    counter='offline_nlp' if operation=='solve' else 'bdf_replays'
    if s.get(counter,0)>=s['spec']['budgets'][counter]:
        raise ValueError('CAPABILITY_NOT_ALLOCATED_IN_THIS_STUDY: '+operation)
    grant=0.
    if operation=='solve':
        candidate=plain(arguments.candidate)
        cfg=verify_candidate(host,candidate)['configuration']
        trajectory=None
    else:
        old=source(host,arguments)
        candidate=old['design_candidate']
        cfg=verify_candidate(host,candidate)['configuration']
        trajectory=old['trajectory']
    request=dict(implementation=s['freeze'],operation=operation,configuration=cfg,design_candidate=candidate,arguments=plain(arguments) if operation=='solve' else None,trajectory=trajectory,study_id=host.run_id,store_root=str(host.store.root),request_id=key+'-mechanics')
    worker_key=key+'-mechanics'
    old=host.store.lookup(host.run_id,worker_key)
    if old:
        if old['request_hash']!=digest(request):
            raise ValueError('MATHEMATICAL_OPERATION_COLLISION')
        if not old['receipt']:
            raise ValueError('RECOVER_MATHEMATICAL_WORK_NO_REPEAT')
        return dict(reference=json.loads(old['receipt'])['output'],additional_numerical_s=0)
    def charge(db):
        current=host.store.session(host.run_id,db)['state']
        current[counter]=current.get(counter,0)+1
        current['numerical_reserved_s']+=grant
        host.store.update_state(db,host.run_id,current)
    row,_=host.store.reserve(host.run_id,worker_key,digest(request),host.actor,{**zero(),'wall_s':grant},guard=charge)
    folder=host.store.root/'mechanics'/row['execution_id']
    folder.mkdir(parents=True,exist_ok=True)
    atomic_json(folder/'request.json',request)
    update(host,pending=dict(kind='mechanics',worker_request_id=worker_key,folder=str(folder),reserved_s=grant,implementation=s['freeze']))
    from tools.service_execution import _run_contained
    started=time.perf_counter()
    try:
        with (folder/'worker.log').open('w',encoding='utf8') as log:
            done=_run_contained([s['spec']['runtime']['research_python'],'-m','tools.research.mechanics_worker',str(folder/'request.json')],log,None)
        boundary=dict(termination_confirmed=True,returncode=done.returncode)
    except subprocess.TimeoutExpired as exc:
        boundary=dict(termination_confirmed=getattr(exc,'termination_confirmed',False),timed_out=True)
    boundary['elapsed_s']=time.perf_counter()-started
    atomic_json(folder/'boundary.json',boundary)
    return recover(host)

def recover(host):
    s=state(host)
    p=s['pending']
    folder=Path(p['folder'])
    boundary=read(folder/'boundary.json')
    if not boundary['termination_confirmed']:
        raise ValueError('UNKNOWN_MATHEMATICAL_OUTCOME_RETAINS_RESERVATION')
    value=read(folder/'result.json') if (folder/'result.json').exists() else dict(status='incomplete')
    request=read(folder/'request.json')
    value.update(operation=request['operation'],design_candidate=request['design_candidate'],
        original_request=save(host,request,'mathematical_request'),charged_numerical_s=boundary['elapsed_s'],implementation=p['implementation'],
        boundary=boundary,task_acceptance='unmeasured',log_reference=save(host,dict(text=(folder/'worker.log').read_text(encoding='utf8')),'mathematical_log'))
    ref=save(host,value,'mathematical_result')
    row=host.store.lookup(host.run_id,p['worker_request_id'])
    with host.store.transaction() as db:
        current=host.store.session(host.run_id,db)['state']
        if current.get('pending')!=p:
            raise ValueError('ALREADY_SETTLED_MATHEMATICS')
        current['numerical_s']+=boundary['elapsed_s']
        current['numerical_reserved_s']-=p['reserved_s']
        current['pending']=None
        current.setdefault('mechanics_results',[]).append(ref)
        host.store.update_state(db,host.run_id,current)
        host.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=host.actor,tool_id='research.mechanics',tool_version='1.0.0',execution_status='completed',charged=zero()),value,elapsed=boundary['elapsed_s'],db=db)
    from tools.research.rl import compatible_references
    compatible_references(host)
    return dict(reference=ref,**value)
