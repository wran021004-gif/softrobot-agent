"""Linked decision-only successor. Same original project ledger, no experiments."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import argparse
import hashlib
import json
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from examples import research_model_v1 as pilot
from tools.platform_store import Store,plain,zero
from tools.platform_host import Host
from tools.state_io import read,atomic_json,digest
from tools.study_history import scientific_match,reporting_scientific_scope
from tools.platform_models import payload_for,run_loop
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter

ORIGINAL=pilot.DEFAULT
DIRECTORY=ROOT/'runs/research_decision_recovery_20261007'
EXPORT=ROOT/'evidence/research_decision_recovery_20261007'
VERSION='research.decision_recovery@1.1.0'
POLICY=dict(max_provider_attempts=3,max_protocol_corrections=1,max_transport_retries=1,
    backend_solves=0,numerical_operations=0,worker_calls=0,
    transport_retry='Only a sealed transport failure with no complete response, accepted decision, pending action or dispatched scientific action; ambiguous outcomes stop.',
    length_retry=False,provider_settings_unchanged=True,review_reserve=dict(tool_calls=1,wall_s=60.))
FILES=tuple(sorted(set(pilot.FILES+('examples/research_decision_recovery.py','tools/study_history.py',
    'tools/platform_models.py','tools/platform_host.py','tests/test_research_decision_recovery.py'))))
INSTRUCTIONS=pilot.reusable.SUCCESSOR_INSTRUCTIONS+'''
This is a linked decision-only recovery, not a new experiment campaign. You are the SAME research decision role. The original campaign is sealed failed: its feedback request produced no complete response or validated decision. This NEW request adds previously omitted history; it is not a successful replay. Read decision_recovery and history_coverage, scientific_overlap and exact bound evidence. The original two simulations remain charged fresh executions but both scientific parameter points were previously evaluated. Original replication_reason was null: do not invent deliberate repetition intent. Verify each metric independently. Matching science is separate from strict result reuse and implementation boundaries.
Reassess the ORIGINAL hypothesis and first decision using both pilot outcomes, directly matching historical failures, incumbent and counterexamples. Explain support, contradictions, uncertainty and applicable mathematical support or its absence. Choose stop, recommend diagnosis, propose another search, or propose an explicitly justified repetition yourself. No predetermined conclusion, route or parameter values. One research.decide call supplies your own decision AND interpretation. All diagnosis/search decisions are PROPOSALS ONLY: no candidate, backend, numerical operation, diagnostic query or worker will run here. Future execution needs separate authorization. For search, planned_budget describes hypothetical future complete execution requirements and is not funded by current zero-experiment recovery budget. Use frozen eight-variable catalog, <=2 hypothetical backend attempts per batch, current feedback F aliases, explicit source_candidate and predecessor_decision. Known scientific points that cannot be reused require replication_reason. Preserve exact task/case/initial conditions; near_z_plus is a distinct subsequent event. Do not mark proposals completed. Host closure after recording is an engineering boundary, not your scientific STOP. Original autonomy, mathematical selection and multi-round execution remain unproven. Keep exact observations bound to current aliases; concise conditional interpretations.
'''


def file_seal(directory):
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in Path(directory).rglob('*') if p.is_file()}


def failed_session_seal(store,run_id):
    with store.connect(True) as db:
        calls=[dict(r) for r in db.execute('SELECT * FROM calls WHERE run_id=? ORDER BY request_id',(run_id,))]
    return dict(session_identity=digest(store.session(run_id)),calls_identity=digest(calls))


def overlap_report(w):
    pairs=[('e3876a1d289f41f08d46c96202f1da0c','68ec1d6cc55c4b9baefe6eb58b73540b'),
        ('110dc2c9c1d642dcb018664a65c62c30','af79836372454e4184e61dee1030ec39')]
    by_id={r['execution_id']:r for r in w.records};rows=[]
    from tools.settling_campaign import campaign_metrics
    def differences(a,b,path=''):
        if type(a)!=type(b):return [path]
        if isinstance(a,dict):return [p for k in sorted(set(a)|set(b)) for p in
            ([path+'/'+k] if k not in a or k not in b else differences(a[k],b[k],path+'/'+k))]
        if isinstance(a,list):return [path] if len(a)!=len(b) else [p for i,(x,y) in enumerate(zip(a,b)) for p in differences(x,y,path+'/'+str(i))]
        return [] if a==b else [path]
    for old,new in pairs:
        a,b=by_id[old],by_id[new]
        ca=w.store.artifact(a['facts']['configuration'])['effective'];cb=w.store.artifact(b['facts']['configuration'])['effective']
        comparison=scientific_match(cb,ca,implementation=b['implementation'],historical_implementation=a['implementation'])
        ma,mb=campaign_metrics(a['facts']),campaign_metrics(b['facts'])
        rows.append(dict(historical=a['facts']['candidate'],pilot=b['facts']['candidate'],comparison=comparison,
            scientific_scope=reporting_scientific_scope(ca),scientific_differences=differences(reporting_scientific_scope(ca),reporting_scientific_scope(cb)),
            raw_robot_differences=differences(ca['robot'],cb['robot']),
            builder_bindings=dict(historical=ca['policy']['candidate_builder'],pilot=cb['policy']['candidate_builder']),
            implementations=dict(historical=a['implementation'],pilot=b['implementation']),
            metrics={k:dict(historical=ma[k],pilot=mb[k],equal=ma[k]==mb[k],pilot_minus_historical=mb[k]-ma[k])
                for k in ('terminal_error_m','holding_max_error_m','holding_max_speed_m_s')},
            original_replication_reason=None,fresh_charged_execution=True,novel_parameter_point=False,
            deliberately_planned_repetition=False,result_reused=False))
    if any(not r['comparison']['scientific_match'] for r in rows):raise ValueError('EXPECTED_OVERLAP_NOT_VERIFIED')
    return dict(version=VERSION,pairs=rows,scope='Exact saved configurations and three aggregate metrics; no full trajectory/timing equality or causal inference.',
        correction='Two fresh simulations at previously evaluated scientific points. Zero recorded deliberate repetitions; original null purpose unchanged.')


def prepare(directory=DIRECTORY,source_directory=ORIGINAL):
    directory=Path(directory);original=pilot.restore(source_directory)
    if directory.exists():raise ValueError('EXISTING_RECOVERY_NO_ALLOWANCE_RESET')
    if original.status!='failed' or original.store.session(original.host.run_id)['status']!='failed':raise ValueError('SEALED_FAILED_SOURCE_REQUIRED')
    cumulative=original.store.remaining();remaining=cumulative['remaining']
    cap={k:min(remaining[k],v) for k,v in dict(model_calls=3,tool_calls=12,wall_s=1800.,backend_solves=0,worker_calls=0).items()}
    if cap['model_calls']<1 or cap['tool_calls']<3 or cap['wall_s']<720:raise ValueError('INSUFFICIENT_RECOVERY_AND_REVIEW_ALLOWANCE')
    directory.mkdir(parents=True)
    old_seal=failed_session_seal(original.store,original.host.run_id)
    publication_seal=file_seal(ROOT/'evidence/research_native_v1_live_20261006')
    runtime_seal={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(source_directory).glob('*.json')}
    inp=deepcopy(original.store.session(original.host.run_id)['snapshot']['input']);inp['run_id']='research-native-v1-decision-recovery-20261007'
    inp['policy'].update(budget=cap,tool_bindings={'research.decide':'1.0.0'},allowed_tools=[])
    inp['policy'].setdefault('operation_allowances',{})['research.decide']=dict(timeout_s=30.,reserve_s=30.)
    # Keep the exact model configuration, including original naming policy. Only
    # the granted business tool is exposed; protocol recovery is locally narrower.
    host=Host(original.store.root,inp['run_id']);host.create(inp,parent_run_id=original.host.run_id)
    reservation,_=original.store.reserve(host.run_id,'recovery-preparation',digest(dict(version=VERSION,parent=original.host.run_id)),
        'engineering',{**zero(),'tool_calls':1,'wall_s':120.})
    started=time.monotonic()
    w=SimpleNamespace(directory=directory,store=original.store,host=host,working=None,
        rounds=deepcopy(original.rounds),repairs=0,status='prepared',stop_reason=None,batch_source=original.batch_source,
        current_case='nominal',sealed_cases=deepcopy(original.sealed_cases),baseline=original.baseline,selected=original.selected,
        latest=original.latest,previous_decision=original.previous_decision)
    w.records,coverage=pilot.relevant_history(w)
    new_ids=[r['execution_id'] for r in original.records if r['source_store']==str(original.directory)]
    for eid in new_ids:
        w.records.append(pilot.historical(w,str(original.directory),eid,'original_pilot_observation'))
    overlap=overlap_report(w);overlap_ref=pilot.save(w.store,overlap)
    failure=read(Path(source_directory)/'failure.json')
    first=original.rounds[0]['decision']
    boundary=dict(version=VERSION,original_directory=str(source_directory),original_host=original.host.run_id,
        original_status='failed',original_failure=failure,original_usage=cumulative,
        recovery_limits=cap,cumulative_grant_id=w.store.config()['grant_id'],new_project_grant=False,
        original_hypothesis=first['model_interpretations'],first_decision=original.previous_decision,
        original_action=first['decision'],feedback_bridge_boundary=original.freeze.get('repair_boundary'),
        old_implementation=original.freeze['implementation'],overlap_correction=overlap_ref,
        interpretation_status='No validated successor from failed model-1; this request adds evidence.',
        alias_scope='Aliases inside original_action/hypothesis belong to the sealed original context; do not reuse them as current F aliases. Exact original decision and selectors remain archived.',
        policy=POLICY,original_unknown_usage='Failed original provider request has unknown token usage; known subtotal excludes it.',
        original_session_seal=old_seal,original_publication_seal=publication_seal,original_runtime_seal=runtime_seal)
    w.freeze=deepcopy(original.freeze)
    w.freeze.update(version=VERSION,research_host=host.run_id,limits=cap,decision_only=True,ledger_root=str(w.store.root),
        recovery_boundary=boundary,recovery_policy=POLICY,recovery_instructions=INSTRUCTIONS,history_coverage=coverage,
        original_pilot_execution_ids=new_ids,implementation=pilot.revision(),
        recovery_files={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FILES},
        experiment=dict(evidence_directory=str(EXPORT)))
    with w.store.transaction() as db:
        state=w.store.session(host.run_id,db)['state'];state['fact_scope']=dict(project=w.freeze['project_id'],binding=w.freeze['binding'])
        w.store.update_state(db,host.run_id,state)
    previous_feedback=w.store.artifact(original.feedback)['result']
    content=deepcopy(w.store.artifact(previous_feedback))
    content.update(history_evidence=[dict(candidate=r['facts']['candidate'],metrics=r['acceptance']['metrics'],
        accepted=r['acceptance']['accepted'],status=r['acceptance']['status'],role=r['role'],
        profile=r['facts']['report']) for r in w.records],
        scientific_overlap_correction=dict(reference=overlap_ref,summary=overlap['correction']),
        status='recovery_decision_only',original_feedback_reference=previous_feedback)
    pilot.reusable.feedback(w,content,'corrected_history_recovery_feedback')
    w.store.complete(reservation,dict(request_id='recovery-preparation',execution_id=reservation['execution_id'],caller='engineering',
        tool_id='engineering.recovery_preparation',tool_version='1.0.0',execution_status='completed',charged=zero()),
        dict(boundary=pilot.save(w.store,boundary),overlap=overlap_ref),time.monotonic()-started)
    pilot.configure(w);pilot.persist(w)
    atomic_json(directory/'overlap_review.json',overlap)
    atomic_json(directory/'freeze_seal.json',dict(identity=digest(w.freeze),before_first_live_request=True))
    outgoing(w,'prepared_request.json');verify_seals(w)
    return w


def restore(directory=DIRECTORY):
    directory=Path(directory);freeze=read(directory/'freeze.json');store=Store(freeze['ledger_root'])
    w=SimpleNamespace(directory=directory,store=store,host=Host(store.root,freeze['research_host']),freeze=freeze)
    for k,v in read(directory/'scheduler_state.json').items():setattr(w,k,v)
    from tools.context_assembly import restore_working_state
    w.working,w.context_archive=restore_working_state(read(directory/'working_state.json')['reference'],
        store=Store(directory/'working_archive'),scope=dict(context_id=w.host.run_id,role='design',binding=w.freeze['binding']),stores=(store,))
    return w


def outgoing(w,name):
    adapter=EvidenceDrivenAdapter();payload=payload_for(w.host,adapter)
    if list(adapter.advertised.values())!=['research.decide']:raise ValueError('RECOVERY_TOOLS_CHANGED')
    atomic_json(w.directory/name,dict(payload=payload,context_assembly_audit=adapter.context_assembly_audit))
    return adapter


def verify_seals(w):
    boundary=w.freeze['recovery_boundary']
    if failed_session_seal(w.store,boundary['original_host'])!=boundary['original_session_seal']:raise ValueError('ORIGINAL_FAILED_SESSION_CHANGED')
    if file_seal(ROOT/'evidence/research_native_v1_live_20261006')!=boundary['original_publication_seal']:raise ValueError('ORIGINAL_PUBLICATION_CHANGED')
    original=Path(boundary['original_directory'])
    if {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in original.glob('*.json')}!=boundary['original_runtime_seal']:
        raise ValueError('ORIGINAL_RUNTIME_FILES_CHANGED')
    if w.store.session(w.host.run_id)['snapshot']['input']['policy']['model']!=w.freeze['provider_configuration']:
        raise ValueError('PROVIDER_SETTINGS_CHANGED')


def reconciled_transport_retry(w):
    """Read durable request/response/action records; an ambiguous result stops."""
    state=w.store.session(w.host.run_id)['state']
    with w.store.connect(True) as db:
        calls=[dict(r) for r in db.execute('SELECT * FROM calls WHERE run_id=? ORDER BY rowid',(w.host.run_id,))]
        events=[json.loads(r[0]) for r in db.execute('SELECT body FROM events WHERE run_id=?',(w.host.run_id,))]
    model=[r for r in calls if json.loads(r['charged'])['model_calls']]
    if not model:return False
    last=model[-1];receipt=json.loads(last['receipt']) if last['receipt'] else {}
    failure=w.store.artifact(receipt['output']) if receipt.get('output') else {}
    eligible=(last['status']=='failed' and receipt.get('execution_status')=='failed' and
        not state.get('handoffs',{}).get('research_decision') and not state.get('pending') and
        not any(e['kind']=='model_raw_response' and e['status']=='completed' for e in events) and
        not any(json.loads(r['receipt']).get('tool_id')=='research.decide' for r in calls if r['receipt']) and
        any(s in str(failure) for s in ('IncompleteRead','URLError','ConnectionResetError','RemoteDisconnected')))
    atomic_json(w.directory/'transport_reconciliation.json',dict(eligible=eligible,request=last['request_id'],
        receipt=receipt,failure=failure,no_accepted_decision=not state.get('handoffs',{}).get('research_decision'),
        no_pending_action=not state.get('pending'),provider_usage='unknown if not supplied; never zero-filled'))
    return eligible


def live(directory=DIRECTORY):
    from examples.gvs_nmpc_route_experiment import load_credential
    w=restore(directory)
    if w.status!='prepared':raise ValueError('RECOVERY_ALREADY_ATTEMPTED_NO_RESET')
    if any(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=v for p,v in w.freeze['recovery_files'].items()):
        raise ValueError('FROZEN_RECOVERY_IMPLEMENTATION_CHANGED')
    verify_seals(w);load_credential(Path.home()/'.codex/.env')
    w.status='running';pilot.persist(w)
    try:
        adapter=outgoing(w,'live_request_0.json');run_loop(w.host,adapter)
        state=w.store.session(w.host.run_id)['state']
        if not state.get('handoffs',{}).get('research_decision') and reconciled_transport_retry(w):
            remaining=w.store.spendable(w.host.run_id)['remaining'];timeout=w.freeze['provider_configuration']['timeout_s']
            if remaining['model_calls']>=1 and remaining['tool_calls']>=1 and remaining['wall_s']>=timeout:
                with w.store.transaction() as db:
                    state=w.store.session(w.host.run_id,db)['state'];state['transport_retries_used']=1;state['turn']+=1
                    state['transport_reconciliation']='No complete response, accepted decision or dispatched action; prior failed charge retained.'
                    w.store.update_state(db,w.host.run_id,state)
                    w.store.event(db,w.host.run_id,'transport_retry','reconciled_no_action')
                w.host.resume();adapter=outgoing(w,'live_transport_retry_request.json');run_loop(w.host,adapter)
        state=w.store.session(w.host.run_id)['state'];ref=state.get('handoffs',{}).get('research_decision')
        if ref:
            result=w.store.artifact(ref);w.previous_decision=ref
            w.rounds.append(dict(index=len(w.rounds),kind=result['decision']['action'],accepted_decision=ref,
                decision=result,proposal_only=True,execution_dispatched=False))
            w.status='decision_recorded';w.stop_reason='Engineering recovery closed after one accepted proposal/interpretation; no experiment authorized.'
        else:w.status='incomplete';w.stop_reason=state.get('stop_reason') or 'No validated successor decision'
    except Exception as exc:
        w.status='incomplete';w.stop_reason=str(exc)
        atomic_json(w.directory/'recovery_failure.json',dict(type=type(exc).__name__,message=str(exc)))
    finish(w)
    print(w.status,w.stop_reason,flush=True)


def finish(w):
    state=w.store.session(w.host.run_id)['state']
    # Release the protected engineering review only after the native phase ends.
    with w.store.transaction() as db:
        state['role_context'].pop('phase_budget',None);w.store.update_state(db,w.host.run_id,state)
    row,_=w.store.reserve(w.host.run_id,'final-factual-review',digest(dict(version=VERSION,decision=w.previous_decision)),
        'engineering',{**zero(),'tool_calls':1,'wall_s':60.});started=time.monotonic()
    verify_seals(w)
    combined=w.store.remaining();used=w.store.remaining(w.host.run_id)['used']
    if used['backend_solves'] or used['worker_calls']:raise ValueError('RECOVERY_EXPERIMENT_WAS_DISPATCHED')
    ref=state.get('handoffs',{}).get('research_decision')
    result=w.store.artifact(ref) if ref else None
    review=dict(version=VERSION,status=w.status,original_campaign_sealed=True,recovered_history_available=True,
        scientific_overlap_distinct_from_reuse=True,valid_successor_decision=bool(ref),decision=ref,
        verified_observations=result['verified_observations'] if result else [],
        interpretation_bindings=result['interpretation_bindings'] if result else [],
        model_interpretations=result['model_interpretations'] if result else [],
        proposed_action=result['decision']['action'] if result else None,executed_action=None,
        semantic_review_status='Native observation arithmetic and citation resolution checked; model prose requires separate factual scope review.',
        original_pilot_fresh_simulations=2,original_pilot_new_parameter_points=0,original_deliberate_repetitions=0,
        new_backend_simulations=0,new_numerical_experiments=0,new_workers=0,
        limitations=['Original autonomous historical coverage was incomplete.','No retrospective mathematical support for original points.',
            'No second executed batch or verified multi-round experiment cycle.','No physical improvement, causal proof or formal comparison.'])
    w.store.complete(row,dict(request_id='final-factual-review',execution_id=row['execution_id'],caller='engineering',
        tool_id='engineering.factual_review',tool_version='1.0.0',execution_status='completed',charged=zero()),review,time.monotonic()-started)
    review.update(recovery_usage=w.store.remaining(w.host.run_id),combined_usage=w.store.remaining(),
        original_usage=w.freeze['recovery_boundary']['original_usage'])
    atomic_json(w.directory/'factual_review.json',review)
    pilot.persist(w)
    # Close host without implying a model scientific STOP or completed experiment.
    with w.store.transaction() as db:
        state=w.store.session(w.host.run_id,db)['state'];state['engineering_boundary_closed']=True
        w.store.update_state(db,w.host.run_id,state,'stopped')
    export(w)


def export(w):
    from tools.improvement_workflow import archive_store
    out=Path(w.freeze['experiment']['evidence_directory']);out.mkdir(parents=True,exist_ok=True)
    for p in w.directory.glob('*.json'):(out/p.name).write_bytes(p.read_bytes())
    shutil.copytree(w.directory/'context_assembly',out/'context_assembly',dirs_exist_ok=True)
    archive_store(w.store,out/'store')
    atomic_json(out/'delivery.json',dict(version=VERSION,status=w.status,stop_reason=w.stop_reason,
        successor=w.rounds[-1] if w.status=='decision_recorded' else None,
        original_campaign_status='failed',proposal_only=True,execution_dispatched=False,
        recovery_usage=w.store.remaining(w.host.run_id),combined_usage=w.store.remaining()))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','live','export']);args=p.parse_args()
    if args.action=='prepare':prepare()
    elif args.action=='live':live()
    else:export(restore())
