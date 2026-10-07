"""Independent grants for the explicitly authorized reporting/control successor."""
from pathlib import Path
import sys, os, time, json, shutil, hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.state_io import read,atomic_json,digest
from tools.platform_store import Store,zero,encode
from tools.platform_host import Host
from examples.milestone5_future_validation import SimpleContext

M4=ROOT/'runs/milestone4_bound_20261006'; M5=ROOT/'runs/milestone5_control_20261006'
LIMIT4=dict(model_calls=3,tool_calls=12,backend_solves=0,worker_calls=0,wall_s=1200.)
LIMIT5=dict(model_calls=12,tool_calls=100,backend_solves=6,worker_calls=0,wall_s=24000.)
AUTH='Direct successor authorization in attachment a5df5b7f-886e-41fd-9067-265fe0f56959/pasted-text-1.txt; separate grants, no workers, no historical reset; normal scoped publication authorized.'

def host(root):
    limit=LIMIT4 if root==M4 else LIMIT5;store=Store(root)
    if not store.db.exists():
        store.create(dict(project_id=root.name,grant_id=root.name,budget=limit,authorization_source=AUTH))
        if root==M5:
            with store.transaction() as db:db.execute("INSERT INTO meta VALUES ('diagnostic_work',?)",(encode(dict(
                limits=dict(local_solves=240,preview_attempts=6,component_evaluations=24,prediction_evaluations=24),
                used=dict(local_solves=0,preview_attempts=0,component_evaluations=0,prediction_evaluations=0))),))
    h=Host(root,root.name+'-successor')
    with store.connect(True) as db:exists=db.execute('SELECT 1 FROM sessions WHERE run_id=?',(h.run_id,)).fetchone()
    if not exists:
        from copy import deepcopy
        cfg=deepcopy(read(ROOT/'evidence/milestone5_matched_20261006/protocol.json')['candidates'][0]['configuration'])
        cfg['run_id']=h.run_id;cfg['policy'].update(budget=limit,route=None,allowed_tools=[])
        h.create(cfg)
    return h

def operation(root,name,fn,reserve=120.,provider=False):
    if (root/'checkpoint_seal.json').exists():raise ValueError('SUCCESSOR_SEALED')
    if root==M5 and (root/'scientific_stop.json').exists() and name.startswith(('local_','measure8_','forecast_','backend_')):
        raise ValueError('SCIENTIFIC_DEVELOPMENT_STOPPED_NO_NEW_NUMERICS')
    h=host(root)
    if h.store.lookup(h.run_id,name):raise ValueError('NO_REPLAY')
    if h.store.remaining()['remaining']['wall_s']<reserve+60.:raise ValueError('DELIVERY_RESERVE')
    row,_=h.store.reserve(h.run_id,name,digest(dict(operation=name)),h.actor,
        {**zero(),('model_calls' if provider else 'tool_calls'):1,'wall_s':reserve})
    start=time.monotonic();error=None
    try:result=fn(SimpleContext(h,row));status='completed'
    except Exception as exc:
        error=dict(type=type(exc).__name__,message=str(exc));status='failed'
        result=dict(error=error,provider_response=getattr(exc,'provider_response',None))
    elapsed=time.monotonic()-start
    atomic_json(root/(name+'_pending.json'),dict(result=result,status=status,elapsed_s=elapsed))
    receipt=h.store.complete(row,dict(request_id=name,execution_id=row['execution_id'],caller=h.actor,
        tool_id='model.deepseek' if provider else 'analysis.bound_successor',tool_version='1.0.0',
        execution_status=status,charged=zero(),error=json.dumps(error) if error else None),result,elapsed)
    atomic_json(root/(name+'.json'),result);atomic_json(root/(name+'_receipt.json'),receipt)
    print(json.dumps(dict(operation=name,status=status,charged=receipt['charged'])),flush=True)
    if error:raise RuntimeError(error)
    return result

def export(root):
    store=Store(root)
    with store.connect(True) as db:rows=[dict(r) for r in db.execute('SELECT * FROM calls')]
    assert all(r['receipt'] for r in rows),'PENDING_OPERATION'
    receipts=[json.loads(r['receipt']) for r in rows]
    total={k:sum(r['charged'][k] for r in receipts) for k in zero()}
    base=read(ROOT/'evidence/milestone4_reporting_scientific_20261006/accounting.json')['linked_lifetime']
    other=read(M4/'accounting.json')['actual'] if root==M5 and (M4/'accounting.json').exists() else zero()
    with store.connect(True) as db:work=db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone() if root==M5 else None
    atomic_json(root/'accounting.json',dict(limit=LIMIT4 if root==M4 else LIMIT5,actual=total,
        remaining=store.remaining()['remaining'],receipts=receipts,
        numerical_work=json.loads(work[0]) if work else None,
        linked_predecessor='evidence/milestone4_reporting_scientific_20261006/accounting.json',
        linked_m4_successor=other,linked_lifetime={k:base[k]+other[k]+total[k] for k in zero()},
        historical_reporting_failures=dict(connection_refusal='evidence/milestone4_reporting_20261006/correction0.json',
            client_parameter_rejection='evidence/milestone4_reporting_20261006/correction1.json',
            geometry_misattribution='evidence/milestone4_reporting_20261006/correction2.json',
            numerical_cross_execution_misattribution='evidence/milestone4_reporting_scientific_20261006/interpretation1.json'),
        platform_denial='M4 first provider command rejected before process launch; zero actual provider charge. Explicit chat authorization pending.' if not (M4/'interpretation0_raw.json').exists() else 'Preserved prelaunch rejection; subsequent authorized attempts have own receipts.',
        historical_scopes_unchanged=True,protected_pairs_used=0,protected_backend_slots_preserved=6,
        workers=0,subagents=0,embedded_backend_updates=0,
        convention='Actual outer runtime charged once; inspection/edit/offline tests/export retain existing engineering convention; embedded updates not standalone.'))
    dest=ROOT/'evidence'/root.name;dest.mkdir(parents=True,exist_ok=True)
    for p in root.glob('*.json'):shutil.copyfile(p,dest/p.name)
    for p in root.glob('*.md'):shutil.copyfile(p,dest/p.name)
    implementation=dest/'implementation';implementation.mkdir(exist_ok=True)
    files=('tools/bound_reporting.py','examples/milestone_bound_successor.py','tests/test_bound_reporting.py') if root==M4 else (
        'examples/milestone5_control_successor.py','examples/milestone5_control_reporting.py','extensions/optimization/ipopt.py','extensions/tendon_family/gvs_bounded_nmpc.py',
        'extensions/tendon_family/gvs_nmpc.py','extensions/tendon_family/gvs_profile.py','extensions/tendon_family/milestone5_feedback_runtime.py',
        'extensions/tendon_family/manifest.py','tests/test_milestone5_control_successor.py')
    for n in files:shutil.copyfile(ROOT/n,implementation/n.replace('/','__'))
    (dest/'.gitattributes').write_bytes(b'* -text\n')
    atomic_json(dest/'sha256_manifest.json',{p.relative_to(dest).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file() and p.name!='sha256_manifest.json'})
    print(json.dumps(dict(exported=str(dest),actual=total)))

def prepare4():
    from examples.milestone4_reporting_scientific import build_packet,protected_hashes
    from tools.bound_reporting import ledger
    packet,bindings,history=build_packet();compact=ledger(packet['summary'])
    for binding in bindings:
        robot=binding['configuration']['effective']['robot'];identity=digest(robot)
        definition=dict(components=[{k:c[k] for k in ('id','length_m','sections','physics')}
            for c in robot['structure']['data']['components'] if c['kind']=='flexible_segment'],
            source_configuration=binding['candidate']['configuration'],
            group_name_scope='Original/shortened are inherited group labels; physical dimensions and identity are authoritative, not a claim of length order between groups.')
        if identity in compact['structure_definitions']:compact['structure_definitions'][identity]=definition
    compact['failures']=dict(connection='Prior connection refusal',client='Incompatible required tool choice with thinking',
        geometry='Original geometry pass attributed to shortened geometry',numerical='Terminal metric attributed across execution IDs; correct source retained in ledger')
    atomic_json(M4/'ledger.json',compact);atomic_json(M4/'source_archive.json',dict(packet=packet,bindings=bindings,history=history))
    # Also protect the most recent failed reporting campaign.
    paths=list((ROOT/'evidence/milestone4_reporting_scientific_20261006').rglob('*'))
    atomic_json(M4/'protected_hashes.json',protected_hashes() | {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()})

def reporting_authority4(packet):
    from tools.study_history import execution_chronology
    state=read(ROOT/'runs/milestone4_autonomous_20261006/scheduler_state.json')
    freeze=read(ROOT/'evidence/milestone4_autonomous_20261006/freeze.json')
    chronology=execution_chronology(Store(ROOT/'runs/milestone4_autonomous_20261006'),state['records'])
    issues=[dict(source_path=(M4/f'review{i}.json').relative_to(ROOT).as_posix(),status='Historical rejected report; preserved',
        contradictions=read(M4/f'review{i}.json')['specific_contradictions']) for i in (0,1) if (M4/f'review{i}.json').exists()]
    return dict(question='Interpret the completed M4 batches, tradeoffs, explicit repeat and qualified reporting repair.',
        acceptance=freeze['common_scientific_input'].get('acceptance',freeze['profile']),chronology=chronology,
        roles=dict(selected_incumbent=packet['selected'],latest_attempt=chronology['latest_execution'],
            latest_completed_evaluation=chronology['latest_completed_evaluation'],source_baseline=state['baseline']['candidate']),
        stop=packet['stop'],legal_actions={'report_only':'No scientific execution or budget reopening'},
        remaining_budget=read(M4/'accounting.json')['remaining'],
        unresolved=packet['limitations'],rejected_claims=packet['failures'],known_review_issues=issues)


def build_reporting_request4(config,packet,instructions,*,archive=None):
    """Actual request builder, also inspectable offline after the scope seals."""
    from examples.milestone45_checkpoint import reporting_payload
    from tools.bound_reporting import model_packet
    from tools.context_assembly import EvidenceArchive,assemble_request
    payload=reporting_payload(config,model_packet(packet),instructions,check_context=False)
    string=dict(type='string')
    claim=dict(type='object',properties=dict(execution_id=string,metric=string,fact_ref=string,comparison_ref=string,
        relation=dict(type='string',enum=['recorded','less','greater','equal'])),required=['execution_id','metric','fact_ref','relation'],additionalProperties=False)
    group=dict(type='object',properties=dict(structure_identity=string,execution_ids=dict(type='array',items=string)),required=['structure_identity','execution_ids'],additionalProperties=False)
    rep=dict(type='object',properties=dict(source_execution_id=string,repeat_execution_id=string),required=['source_execution_id','repeat_execution_id'],additionalProperties=False)
    props=dict(interpretation=string,recommendation=string,unresolved=dict(type='array',items=string),
        selected_execution_id=string,latest_execution_id=string,claims=dict(type='array',items=claim),
        geometry_groups=dict(type='array',items=group),replications=dict(type='array',items=rep))
    payload['tools'][0]['function']['parameters']=dict(type='object',properties=props,required=list(props),additionalProperties=False)
    archive=archive or EvidenceArchive(M4/'context_assembly',scope={'role':'M4 final reporting','scientific_execution':False},
        stores=(Store(ROOT/'runs/milestone4_autonomous_20261006'),Store(M4)))
    return assemble_request(payload,config,'final_report',packet,archive=archive,authority=reporting_authority4(packet))


def provider4(index,prepare_only=False):
    from tools.runtime_identity import require_softagent_runtime
    require_softagent_runtime()
    if (M4/'checkpoint_seal.json').exists():raise ValueError('SUCCESSOR_SEALED')
    if index not in (0,1,2):raise ValueError('THREE_ATTEMPT_BOUND')
    if (M4/f'interpretation{index}_request.json').exists():raise ValueError('NO_REPLAY')
    from examples.gvs_nmpc_route_experiment import load_credential
    from tools.model_transports.deepseek import request_completion
    config=read(ROOT/'evidence/milestone4_autonomous_20261006/freeze.json')['provider_configuration']
    packet=read(M4/'ledger.json')
    instructions='''Author a standalone interpretation of the stopped autonomous supplement under evidence_bound_reporting@3.0.0. Read ALL compact execution facts including original geometry counterexamples. Every quantitative assertion must be a structured claim referencing a fact_ref with its exact execution_id and metric; use comparison_ref and less/greater/equal for comparisons, recorded otherwise. Renderer prints the value you reference, never fixes wrong selections or references. Do not type ANY digit in interpretation/recommendation/unresolved prose; put execution IDs only in structured fields. Select facts worth discussing freely. Include the original geometry matching-weight pass, the distinct shortened historical passes, new passing-point tradeoffs versus retained incumbent, replication metrics, timing. Provide geometry_groups for all executions. Replications must match actual source/repeat IDs; only aggregate metric repeat, not broad variability or trajectories/timing. Retain selected versus latest. Stop was exhausted backend capacity for another complete search, not reporting cost. Distinguish four historical failure causes. Describe evidence projection defects as possible contributors, not proven internal mechanisms. Preserve all scientific STOPs and do not request scientific work. Explain that closure needs this versioned post-run repair and does not retroactively correct earlier text. Submit report_interpretation once.'''
    if index:
        prior=read(M4/f'review{index-1}.json')
        if prior['passed']:raise ValueError('NO_CORRECTION_AFTER_PASS')
        packet=dict(**packet,correction=prior,previous=read(M4/f'interpretation{index-1}.json'))
    payload,audit=build_reporting_request4(config,packet,instructions)
    atomic_json(M4/f'interpretation{index}_request.json',dict(provider_configuration=config,payload=payload,context_assembly_audit=audit))
    if prepare_only:return
    def call(ctx):
        from tools.context_assembly import check_outgoing_request
        check_outgoing_request(payload,config,'final_report')
        load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
        raw=request_completion(config,payload,os.environ['DEEPSEEK_API_KEY']);atomic_json(M4/f'interpretation{index}_raw.json',raw)
        choice=raw['choices'][0];calls=choice['message'].get('tool_calls',[])
        if choice.get('finish_reason')=='length' or len(calls)!=1 or calls[0]['function']['name']!='report_interpretation':raise ValueError('ONE_COMPLETE_BOUND_REPORT')
        return dict(model_authored=True,interpretation=json.loads(calls[0]['function']['arguments']),raw_identity=digest(raw),request_identity=digest(payload))
    operation(M4,f'interpretation{index}',call,reserve=config['timeout_s'],provider=True)

def render4(index):
    from tools.bound_reporting import render
    def run(ctx):
        raw=read(M4/f'interpretation{index}.json');result=render(raw['interpretation'],read(M4/'ledger.json'))
        atomic_json(M4/f'rendering{index}.json',result)
        (M4/f'rendered_report{index}.md').write_text(result['rendered'],encoding='utf-8')
        return result
    try:operation(M4,f'rendering{index}',run,reserve=30.)
    except RuntimeError as exc:
        atomic_json(M4/f'review{index}.json',dict(passed=False,specific_contradictions=[str(exc)],stage='binding/rendering'))
        raise

def seal4(index):
    from tools.bound_reporting import render
    def check(ctx):
        report=read(M4/f'interpretation{index}.json')['interpretation'];review=read(M4/f'review{index}.json')
        assert review['model_report_identity']==digest(report)
        assert review['passed'] and all(c['passed'] for c in review['claim_checks'])
        assert render(report,read(M4/'ledger.json'))==read(M4/f'rendering{index}.json')
        assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==v for n,v in read(M4/'protected_hashes.json').items())
        return dict(status='closed_after_versioned_post_run_reporting_repair',supplement_closed=True,
            qualification='Multibatch behavior passed in the original run; factual reporting passed after recorded post-run repair under evidence_bound_reporting@3.0.0.',
            original_free_text_failures_preserved=True,original_stop_and_incumbent_unchanged=True,
            report_reference=f'rendered_report{index}.md',review_reference=f'review{index}.json',new_numerical_work=0)
    result=operation(M4,'linked_superseding_report',check,reserve=30.)
    atomic_json(M4/'checkpoint_seal.json',result);export(M4)

if __name__=='__main__':
    action=sys.argv[1]
    if action=='prepare4':prepare4()
    elif action=='request4':provider4(int(sys.argv[2]),prepare_only=True)
    elif action=='provider4':provider4(int(sys.argv[2]))
    elif action=='render4':render4(int(sys.argv[2]))
    elif action=='seal4':seal4(int(sys.argv[2]))
    elif action=='export4':export(M4)
    elif action=='export5':export(M5)
