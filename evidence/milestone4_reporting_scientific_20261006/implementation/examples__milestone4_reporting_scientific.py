"""Independent, reporting-only successor; never resumes scientific execution.

prepare is offline engineering. Each later provider/analysis operation has its own
Store reservation/receipt. A failed or pending request is never replayed.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import os
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.state_io import read,atomic_json,digest
from tools.platform_store import Store,zero
from tools.platform_host import Host
from tools.study_history import study_history,reporting_summary,reporting_scientific_scope
from examples.milestone45_checkpoint import reporting_payload

RUN=ROOT/'runs/milestone4_reporting_scientific_20261006'
EVIDENCE=ROOT/'evidence/milestone4_reporting_scientific_20261006'
OLD=ROOT/'evidence/milestone4_autonomous_20261006'
PRIOR=ROOT/'evidence/milestone4_reporting_20261006'
LIMIT=dict(model_calls=2,tool_calls=12,backend_solves=0,worker_calls=0,wall_s=1200.)
AUTH='Direct chat authorization: independent M4 reporting remediation, 2 provider attempts, 12 workflow calls, 1200 charged seconds; zero backend/controller/numerical/worker work; scoped normal publication authorized.'
INSTRUCTIONS='''Author a standalone evidence-grounded corrected interpretation of the stopped M4 autonomous supplement. The source-bound factual packet is authoritative; previous reports and reviews are fallible historical text. Check the claims they actually made and correct contradictions without treating all failures as model failures. Keep different structures separate even when weights match. Bind cited outcomes to execution IDs and their structure/scientific configuration identities using the packet. Distinguish frozen pre-experiment background from updated campaign observations. Interpret explicit replication and its measured differences within the comparison scope; evaluate trade-offs, selection versus chronology, budget/STOP facts and observations versus hypotheses. Do not infer causality, general variability, continuous-time or realtime performance from unsupported evidence. This is post-run reporting only: the original audits, selected incumbent and scientific STOP stay sealed. You author the interpretation and recommendation freely from evidence; no scientific execution is available. Submit one report_interpretation tool call with a concise report, recommendation and unresolved limitations.'''


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_paths():
    paths=[p for folder in (OLD,PRIOR) for p in folder.rglob('*') if p.is_file()]
    paths.extend(ROOT/'runs/milestone5_matched_20261006'/n for n in
        ('protocol.json','accounting.json','checkpoint_seal.json','platform.sqlite'))
    return paths


def protected_hashes():return {p.relative_to(ROOT).as_posix():sha(p) for p in protected_paths()}


def build_packet():
    state=read(OLD/'scheduler_state.json');audit=read(OLD/'acceptance_audit.json')
    source=Store(ROOT/'runs/milestone4_autonomous_20261006')
    history=study_history(source,state['records'])
    ids=[];pairs=[];batches=[]
    for row in state['rounds']:
        if row.get('kind')!='search' or not row.get('complete'):continue
        batch=source.artifact(row['result']);batches.append(dict(round_index=row['index'],reference=row['result']))
        for result in batch['candidates']:
            if result['reused'] or not result.get('execution_id'):continue
            ids.append(result['execution_id'])
            if result.get('replication_of'):pairs.append((result['replication_of']['execution_id'],result['execution_id']))
    summary=reporting_summary(history,new_execution_ids=ids,replication_pairs=pairs,
        selected=state['selected'],latest=state['latest'],usage=audit['usage'],
        stop=dict(status=state['status'],reason=state['stop_reason'],sealed=True))
    summary.update(batch_count=len(batches),batch_references=batches,
        chronological_authority='Selected/latest are saved scheduler bindings, not list order.')
    # Archive the exact configuration objects separately. Compact input contains
    # scientific digest + scope reference; no scientific setting is masked away.
    bindings=[]
    for record in state['records']:
        candidate=record['facts']['candidate'];cfg=source.artifact(candidate['configuration'])
        effective=cfg['effective'];scope=reporting_scientific_scope(effective)
        bindings.append(dict(candidate=candidate,configuration=cfg,scientific_scope=scope,
            scientific_configuration_identity=digest(scope),facts=record['facts']))
    old_request=read(PRIOR/'correction2_request.json')
    return dict(version='m4_source_bound_reporting@2.0.0',summary=summary,
        frozen_background_reference=(OLD/'freeze.json').relative_to(ROOT).as_posix(),
        source_audit=(OLD/'acceptance_audit.json').relative_to(ROOT).as_posix(),
        source_state=(OLD/'scheduler_state.json').relative_to(ROOT).as_posix(),
        scientific_identity_definition='digest(scientific_fixed_scope(effective, variables=())); unmasked physical/task/initial/controller/model/backend/discretization/seed settings; run labels and grants excluded. Original configuration hash retained.',
        prior_original_review=audit['interpretation_review'],
        prior_failed_report=read(PRIOR/'correction2.json')['interpretation'],
        prior_reporting_failure=dict(transport0=read(PRIOR/'correction0.json'),client1=read(PRIOR/'correction1.json'),
            factual_review=read(PRIOR/'final_factual_review.json'),
            sent_summary_omitted_structure=all('structure_identity' not in r for r in json.loads(old_request['payload']['messages'][1]['content'])['summary']['results'])),
        protected_hashes=protected_hashes()),bindings,history


def prepare():
    if (RUN/'checkpoint_seal.json').exists():raise ValueError('SEALED')
    packet,bindings,history=build_packet()
    config=read(OLD/'freeze.json')['provider_configuration']
    payload=reporting_payload(config,packet,INSTRUCTIONS)
    reference=read(PRIOR/'correction2_request.json')
    parameters={k:v for k,v in payload.items() if k not in ('messages','tools')}
    expected={k:v for k,v in reference['payload'].items() if k not in ('messages','tools')}
    assert config==reference['provider_configuration'] and parameters==expected
    assert 'tool_choice' not in payload and payload['thinking']=={'type':'enabled'}
    assert read(ROOT/'runs/milestone5_matched_20261006/checkpoint_seal.json')['status'].startswith('stopped')
    atomic_json(RUN/'prepared_packet.json',packet)
    atomic_json(RUN/'source_bindings.json',bindings)
    atomic_json(RUN/'prepared_history.json',history)
    atomic_json(RUN/'client_check.json',dict(passed=True,already_working_request=(PRIOR/'correction2_request.json').relative_to(ROOT).as_posix(),
        parameters=parameters,configuration=config,transport_source_sha=sha(ROOT/'tools/model_transports/deepseek.py'),
        tls='Existing urllib default verified HTTPS; no TLS override or redirect enabled.',
        source_packet_bytes=len(json.dumps(packet,ensure_ascii=False).encode('utf-8'))))
    print(json.dumps(dict(prepared=True,results=len(packet['summary']['results']),
        new_executions=packet['summary']['new_execution_count'],novel=packet['summary']['novel_configuration_count'])))


def host():
    store=Store(RUN)
    if not store.db.exists():
        assert read(RUN/'offline_checks.json')['passed']
        store.create(dict(project_id=RUN.name,grant_id=RUN.name,budget=LIMIT,authorization_source=AUTH))
    h=Host(RUN,RUN.name+'-report')
    with store.connect(True) as db:exists=db.execute('SELECT 1 FROM sessions WHERE run_id=?',(h.run_id,)).fetchone()
    if not exists:
        packet=read(RUN/'prepared_packet.json');selected=packet['summary']['selected']
        cfg=next(b['configuration']['effective'] for b in read(RUN/'source_bindings.json') if b['candidate']==selected)
        cfg=deepcopy(cfg);cfg['run_id']=h.run_id
        cfg['policy'].update(budget=LIMIT,route=None,allowed_tools=[])
        h.create(cfg)
    return h


def operation(name,fn,reserve=30.,provider=False):
    if (RUN/'checkpoint_seal.json').exists():raise ValueError('REPORTING_SCOPE_SEALED')
    h=host();existing=h.store.lookup(h.run_id,name)
    if existing:raise ValueError('ATTEMPT_ALREADY_RECORDED_NO_REPLAY')
    if provider and h.store.remaining()['remaining']['wall_s']<reserve+30.:raise ValueError('FINAL_REVIEW_CAPACITY_REQUIRED')
    row,_=h.store.reserve(h.run_id,name,digest(dict(operation=name)),h.actor,
        {**zero(),('model_calls' if provider else 'tool_calls'):1,'wall_s':reserve})
    started=time.monotonic();error=None
    try:result=fn();status='completed'
    except Exception as exc:
        error=dict(type=type(exc).__name__,message=str(exc));status='failed'
        result=dict(error=error,provider_response=getattr(exc,'provider_response',None))
    receipt=h.store.complete(row,dict(request_id=name,execution_id=row['execution_id'],caller=h.actor,
        tool_id='model.deepseek' if provider else 'analysis.m4_reporting',tool_version='2.0.0',
        execution_status=status,charged=zero(),error=json.dumps(error) if error else None),result,time.monotonic()-started)
    atomic_json(RUN/(name+'.json'),result);atomic_json(RUN/(name+'_receipt.json'),receipt)
    print(json.dumps(dict(operation=name,status=status,charged=receipt['charged'])),flush=True)
    if error:raise RuntimeError(error)
    return result


def packet_operation():
    def make():
        packet,_,_=build_packet()
        assert packet==read(RUN/'prepared_packet.json'),'IMMUTABLE_SOURCE_CHANGED'
        assert protected_hashes()==packet['protected_hashes']
        return packet
    return operation('factual_packet',make)


def provider_attempt(index):
    config=read(OLD/'freeze.json')['provider_configuration'];packet=read(RUN/'factual_packet.json')
    instructions=INSTRUCTIONS
    if index:
        prior=read(RUN/'review0.json')
        assert not prior['passed'] and prior.get('specific_contradictions')
        packet=deepcopy(packet);packet['specific_correction']=dict(previous=read(RUN/'interpretation0.json'),review=prior)
        instructions+=' Correct the specific evidence-grounded contradictions in specific_correction. Do not change the sealed scientific outcome.'
    payload=reporting_payload(config,packet,instructions)
    atomic_json(RUN/f'interpretation{index}_request.json',dict(provider_configuration=config,payload=payload))
    def call():
        from examples.gvs_nmpc_route_experiment import load_credential
        from tools.model_transports.deepseek import request_completion
        load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
        raw=request_completion(config,payload,os.environ['DEEPSEEK_API_KEY'])
        atomic_json(RUN/f'interpretation{index}_raw.json',raw)
        choice=raw['choices'][0];calls=choice['message'].get('tool_calls',[])
        if choice.get('finish_reason')=='length':raise ValueError('TRUNCATED_RESPONSE')
        if len(calls)!=1 or calls[0]['function']['name']!='report_interpretation':raise ValueError('ONE_REPORT_REQUIRED')
        report=json.loads(calls[0]['function']['arguments'])
        if set(report)!={'report','recommendation','unresolved'}:raise ValueError('REPORT_FIELDS')
        return dict(model_authored=True,interpretation=report,request_identity=digest(payload),raw_identity=digest(raw))
    return operation(f'interpretation{index}',call,config['timeout_s'],provider=True)


def record_review(index):
    def check():
        review=read(RUN/f'review{index}.json')
        report=read(RUN/f'interpretation{index}.json')
        assert review['model_report_identity']==digest(report['interpretation'])
        assert review['claim_checks'] and all('actual_claim' in c and 'source' in c for c in review['claim_checks'])
        assert review['passed']==all(c['passed'] for c in review['claim_checks'])
        assert protected_hashes()==read(RUN/'prepared_packet.json')['protected_hashes']
        return review
    return operation(f'review{index}_bound',check)


def seal(index):
    def check():
        review=read(RUN/f'review{index}_bound.json');h=host()
        assert protected_hashes()==read(RUN/'prepared_packet.json')['protected_hashes']
        with h.store.transaction() as db:
            session=h.store.session(h.run_id,db);session['state']['status']='stopped'
            h.store.update_state(db,h.run_id,session['state'],status='stopped')
        return dict(status='closed_after_recorded_post_run_remediation' if review['passed'] else 'open_factual_contradiction',
            supplement_closed=review['passed'],qualification='Multibatch behavior passed originally; factual reporting passed after recorded post-run remediation.' if review['passed'] else 'Multibatch behavior passed originally; reporting remains open.',
            original_scientific_stop_preserved=True,selected_incumbent_preserved=True,
            original_audits_and_exhausted_reporting_grant_unchanged=True,
            new_scientific_work=zero(),workers=0,review_reference=f'review{index}_bound.json')
    result=operation('linked_superseding_report',check)
    atomic_json(RUN/'checkpoint_seal.json',result)
    export()


def export():
    import shutil
    store=Store(RUN)
    with store.connect(True) as db:calls=[dict(r) for r in db.execute('SELECT * FROM calls')]
    receipts=[json.loads(r['receipt']) for r in calls if r['receipt']]
    assert len(receipts)==len(calls),'UNRESOLVED_RESERVATION'
    total={k:sum(r['charged'][k] for r in receipts) for k in zero()}
    predecessor=read(ROOT/'evidence/milestone5_matched_20261006/accounting.json')
    base=predecessor['lifetime_with_new_scopes']
    atomic_json(RUN/'accounting.json',dict(limit=LIMIT,actual=total,remaining=store.remaining()['remaining'],receipts=receipts,
        lifetime_base=base,lifetime_base_reference='evidence/milestone5_matched_20261006/accounting.json',
        linked_lifetime={k:base[k]+total[k] for k in zero()},
        exhausted_previous_reporting_grant=read(PRIOR/'receipt_accounting.json')['actual'],
        prior_grant_is_already_in_lifetime_base=True,no_m5_budget_transfer=True,
        convention='Existing offline inspection/edit/test/export engineering convention; actual reporting operations charged by Store receipts once.'))
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    for p in RUN.glob('*.json'):shutil.copyfile(p,EVIDENCE/p.name)
    (EVIDENCE/'.gitattributes').write_bytes(b'* -text\n')
    implementation=EVIDENCE/'implementation';implementation.mkdir(exist_ok=True)
    for name in ('tools/study_history.py','examples/milestone4_autonomous.py',
                 'examples/milestone45_checkpoint.py','examples/milestone4_reporting_scientific.py',
                 'tests/test_milestone4_reporting_scientific.py'):
        shutil.copyfile(ROOT/name,implementation/name.replace('/','__'))
    atomic_json(EVIDENCE/'sha256_manifest.json',{p.relative_to(EVIDENCE).as_posix():sha(p)
        for p in EVIDENCE.rglob('*') if p.is_file() and p.name!='sha256_manifest.json'})
    print(json.dumps(dict(exported=True,actual=total)))


if __name__=='__main__':
    action=sys.argv[1];index=int(sys.argv[2]) if len(sys.argv)>2 else 0
    if action=='prepare':prepare()
    elif action=='packet':packet_operation()
    elif action=='provider':provider_attempt(index)
    elif action=='review':record_review(index)
    elif action=='seal':seal(index)
    elif action=='export':export()
    else:raise ValueError('UNKNOWN_REPORTING_ACTION')
