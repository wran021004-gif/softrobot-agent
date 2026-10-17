"""Native candidate-bound full-horizon solve/replay; separate from backend acceptance."""
from pathlib import Path
import base64,hashlib,json,subprocess,time
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
    counter=('mathematical_evaluations' if arguments.check_only else 'offline_nlp') if operation=='solve' else 'bdf_replays'
    if s.get(counter,0)>=s['spec']['budgets'][counter]:
        raise ValueError('CAPABILITY_NOT_ALLOCATED_IN_THIS_STUDY: '+operation)
    grant=0.
    if operation=='solve':
        candidate=plain(arguments.candidate)
        cfg=verify_candidate(host,candidate)['configuration']
        trajectory=None
        warm_trajectory=None
        if arguments.warm_source:
            if plain(arguments.warm_source) in s.get('mechanics_results',[]):
                warm=source(host,arguments.warm_source)
            else:
                warm=host.store.artifact(arguments.warm_source)
                verified=(warm.get('source_kind')=='verified_mathematical_trajectory' and
                    warm.get('posthoc_verification',{}).get('checks',{}).get('repaired_verification_passed'))
                historical=(warm.get('source_kind')=='historical_mathematical_trajectory' and
                    (arguments.initialization=='saved_candidate_controls' or arguments.objective_mode!='task_capability'))
                if not (verified or historical):
                    raise ValueError('VERIFIED_MATHEMATICAL_WARM_SOURCE_REQUIRED')
            warm_trajectory=warm['trajectory']
    elif operation=='refine':
        candidate=plain(arguments.candidate)
        cfg=verify_candidate(host,candidate)['configuration']
        source_row=host.store.artifact(arguments.source)
        owned_solve=(plain(arguments.source) in s.get('mechanics_results',[]) and
            source_row.get('operation')=='solve' and source_row.get('trajectory') and
            source_row['design_candidate']==candidate)
        if not owned_solve and (source_row.get('source_kind')!='verified_mathematical_trajectory' or
                not source_row['posthoc_verification']['checks']['repaired_verification_passed']):
            raise ValueError('REFINEMENT_REQUIRES_VERIFIED_FROZEN_MATHEMATICAL_SOURCE')
        trajectory=source_row['trajectory']
        warm_trajectory=None
        if any((row:=host.store.artifact(ref)).get('operation')=='refine'
                and row.get('source_reference')==plain(arguments.source)
                and row.get('design_candidate')==candidate
                and row.get('substeps')==arguments.substeps
                for ref in s.get('mechanics_results',[])):
            raise ValueError('EQUIVALENT_REFINEMENT_ALREADY_EXECUTED')
        prior=[host.store.artifact(ref) for ref in s.get('mechanics_results',[])
            if host.store.artifact(ref).get('operation')=='refine'
            and host.store.artifact(ref).get('source_reference')==plain(arguments.source)]
        if prior and arguments.substeps<=max(row['substeps'] for row in prior):
            raise ValueError('REFINEMENT_REQUIRES_INCREASING_RESOLUTION')
        if arguments.substeps==64:
            from extensions.tendon_family.sorosim_codesign import compare_refinements
            grids={row['substeps']:row for row in prior}
            if not all(grids.get(k,{}).get('complete') for k in (16,32)):
                raise ValueError('OPTIONAL_64_REQUIRES_COMPLETE_16_AND_32')
            gap=compare_refinements(grids[16]['raw'],grids[32]['raw'])
            if gap['maximum_position_m']<=.01 and gap['maximum_velocity_m_s']<=.02:
                raise ValueError('OPTIONAL_64_NOT_JUSTIFIED_BY_MATERIAL_DISCREPANCY')
    elif operation=='cross_replay':
        candidate=plain(arguments.candidate)
        cfg=verify_candidate(host,candidate)['configuration']
        source_row=host.store.artifact(arguments.source)
        if source_row.get('source_kind')!='historical_mathematical_trajectory':
            raise ValueError('IMMUTABLE_HISTORICAL_TRAJECTORY_SOURCE_REQUIRED')
        trajectory=source_row['trajectory']
        warm_trajectory=None
    else:
        old=source(host,arguments)
        candidate=old['design_candidate']
        cfg=verify_candidate(host,candidate)['configuration']
        trajectory=old['trajectory']
        warm_trajectory=None
    request=dict(implementation=s['freeze'],operation=operation,configuration=cfg,design_candidate=candidate,
        arguments=plain(arguments) if operation in ('solve','refine') else None,trajectory=trajectory,
        warm_trajectory=warm_trajectory,source_reference=plain(arguments.source) if operation in ('cross_replay','refine') else None,
        study_id=host.run_id,store_root=str(host.store.root),request_id=key+'-mechanics')
    if operation=='solve' and arguments.check_only:request['check_only']=True
    if operation=='solve' and arguments.diagnostic_source:
        point=host.store.artifact(arguments.diagnostic_source)
        if point.get('source_kind')!='raw_nlp_point':
            raise ValueError('EXACT_RAW_NLP_CHECKPOINT_REQUIRED')
        request['diagnostic_point']=point
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
    checkpoints={name:read(folder/(name+'.json')) for name in ('environment','optimizer_iterate','matlab_result')
        if (folder/(name+'.json')).exists()}
    if checkpoints:value['checkpoint_reference']=save(host,checkpoints,'mathematical_checkpoints')
    log_bytes=(folder/'worker.log').read_bytes()
    log=dict(text=log_bytes.decode('utf8',errors='replace'),
        raw_base64=base64.b64encode(log_bytes).decode('ascii'),raw_sha256=hashlib.sha256(log_bytes).hexdigest())
    value.update(operation=request['operation'],design_candidate=request['design_candidate'],
        source_reference=request.get('source_reference'),
        original_request=save(host,request,'mathematical_request'),charged_numerical_s=boundary['elapsed_s'],implementation=p['implementation'],
        boundary=boundary,task_acceptance='unmeasured',log_reference=save(host,log,'mathematical_log'))
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
