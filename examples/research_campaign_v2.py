"""One cumulative case-aware native development campaign; no sealed-run reset."""
from copy import deepcopy
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from examples import research_model_v1 as pilot
from tools.state_io import atomic_json,read,digest
from tools.platform_store import plain,zero
from tools.research_spec import load_spec
from tools.fixed_research import evaluate_candidate,schedule,select_candidate,can_reserve
from tools.research_tasks import aggregate_acceptance,compare_acceptance
from tools.candidate_parameters import parameter_value

CONFIG_PATH=ROOT/'configs/research/native_campaign_v2.json'
FILES=(*pilot.FILES,'examples/research_campaign_v2.py','configs/research/native_campaign_v2.json',
       'schemas/platform_handoff.py','tools/batch_budget.py','tools/research_spec.py','tools/study_history.py',
       'tools/candidate_parameters.py','tools/research_tasks.py','tools/fixed_research.py')


def seal():
    return dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                files={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FILES},
                stable_controller=pilot.revision()['stable_controller'])


def prepare(directory=None,offline_fixture=False):
    config=read(CONFIG_PATH)
    directory=Path(directory or ROOT/'runs'/config['campaign_id'])
    w=pilot.prepare(directory,offline_fixture=offline_fixture,campaign_config=config)
    w.freeze['implementation']=seal()
    w.freeze['assignment_start_unix']=config['assignment_start_unix']
    w.freeze['selection_rule']=config['selection_rule']
    # Preserve and expose the original recovery and its independent corrections.
    w.freeze['known_review_issues']=read(ROOT/'evidence/research_decision_recovery_20261007/independent_factual_review.json')['issues']
    for eid in ('68ec1d6cc55c4b9baefe6eb58b73540b','af79836372454e4184e61dee1030ec39'):
        w.records.append(pilot.historical(w,'runs/research_native_v1_20261006',eid,'original_pilot_matching_failure'))
    event=w.freeze['subsequent_event'];event['case_id']='near_z_plus';w.records.append(event)
    w.freeze['history_coverage']['selected_execution_ids']=[r['execution_id'] for r in w.records]
    w.freeze['history_coverage']['additional_sources']=['Both original pilot executions','Completed changed-section near_z_plus event']
    old=read(ROOT/'evidence/research_decision_recovery_20261007/live_request_0.json')
    w.freeze['recovery_request_review']=dict(source='evidence/research_decision_recovery_20261007/live_request_0.json',
        identity=digest(old),limitation='Historical zero-experiment recovery; its answer and independent review are preserved, not present execution authorization.')
    pilot.configure(w);pilot.persist(w)
    from tools.platform_models import payload_for
    from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
    adapter=EvidenceDrivenAdapter();payload=payload_for(w.host,adapter)
    atomic_json(directory/'prepared_request.json',dict(payload=payload,audit=adapter.context_assembly_audit))
    atomic_json(directory/'freeze_seal.json',dict(identity=digest(w.freeze),before_paid_activity=True))
    return w


def append_results(w,row):
    if not row.get('result'):return
    for c in w.store.artifact(row['result'])['candidates']:
        if not c.get('execution'):continue
        r=next(r for r in w.records if r['execution_id']==c['execution_id'])
        r.update(acceptance=c['execution']['acceptance'],implementation=w.freeze['implementation'],
                 case_id=row['decision']['decision']['plan']['case_id'],seed=row['decision']['decision']['plan']['seed'])
    pilot.configure(w);pilot.persist(w)


def native_decision(w):
    """One safe transport retry only after durable no-response/no-action review."""
    before=w.store.session(w.host.run_id)['state'].get('handoffs',{}).get('research_decision')
    try:return pilot.decision(w)
    except Exception as exc:
        state=w.store.session(w.host.run_id)['state']
        with w.store.connect(True) as db:
            calls=[dict(r) for r in db.execute('SELECT * FROM calls WHERE run_id=? ORDER BY rowid',(w.host.run_id,))]
        models=[r for r in calls if json.loads(r['charged'])['model_calls']]
        last=models[-1] if models else None
        receipt=json.loads(last['receipt']) if last and last['receipt'] else {}
        events=w.store.events(w.host.run_id)
        completed=any(e['kind']=='model_raw_response' and e['status']=='completed' and
            e.get('execution_id')==receipt.get('execution_id') for e in events)
        transport=any(s in str(exc)+' '+str(receipt) for s in ('IncompleteRead','DEEPSEEK_NETWORK_ERROR','RemoteDisconnected','ConnectionResetError'))
        eligible=bool(last and last['status']=='failed' and transport and not completed and not state.get('pending') and
            state.get('handoffs',{}).get('research_decision')==before and state.get('transport_retries_used',0)<2)
        audit=dict(error=str(exc),receipt=receipt,complete_response=completed,accepted_new_action=False,
                   eligible=eligible,request_id=last['request_id'] if last else None)
        atomic_json(w.directory/f'transport_review_{len(models)}.json',audit)
        if not eligible:raise
        with w.store.transaction() as db:
            state=w.store.session(w.host.run_id,db)['state'];state['transport_retries_used']=state.get('transport_retries_used',0)+1
            state['turn']+=1;w.store.update_state(db,w.host.run_id,state)
        return pilot.decision(w)


def search_rows(w):
    spec=load_spec();source=spec['starting_configuration']['effective']
    rows=[]
    for r in w.records:
        if r['source_store']!=str(w.directory):continue
        effective=w.store.artifact(r['facts']['configuration'])['effective']
        changes={p:parameter_value(effective,p) for p in spec['parameter_grants']
                 if parameter_value(effective,p)!=parameter_value(source,p)}
        rows.append(dict(candidate_id=r['facts']['candidate']['candidate_id'],configuration=r['facts']['configuration'],
            changes=changes,case_id=r.get('case_id','nominal'),seed=effective['seed'],
            acceptance=r['acceptance'],receipt=r['receipts']['simulation']))
    return rows


def verify(w):
    spec=load_spec();rows=search_rows(w)
    chosen=select_candidate([r for r in rows if r['case_id']=='nominal'])
    frozen={k:deepcopy(chosen[k]) for k in ('candidate_id','configuration','changes')} if chosen else None
    slots=schedule(spec)
    groups=[dict(role='unchanged_incumbent',changes={},records=[])]
    if frozen:groups.append(dict(role='selected_candidate',changes=frozen['changes'],records=[]))
    plan=dict(version='native_matched_verification@2.0.0',schedule=slots,selected_candidate=frozen,
        source_search=rows,groups=[dict(role=g['role'],changes=g['changes']) for g in groups],
        no_candidate_reason='Incumbent-only characterization resolves the unmeasured unchanged five-case performance; changed near-scale failure is not incumbent evidence.' if not frozen else None)
    path=w.directory/'matched_validation_schedule.json'
    if path.exists():raise ValueError('VERIFICATION_ALREADY_FROZEN_NO_AUTOMATIC_REPLAY')
    atomic_json(path,plan)
    for slot in slots:
        if time.time()-w.freeze['assignment_start_unix']>=36000:break
        remaining=w.store.remaining()['remaining']
        # Delivery capacity remains protected until final interpretation.
        remaining={k:max(0,v-{'model_calls':2,'tool_calls':10,'wall_s':1200}.get(k,0)) for k,v in remaining.items()}
        if not can_reserve(remaining,len(groups)):break
        for g in groups:
            candidate_id=f'v2-verify-{g["role"]}-{slot["case_id"]}-rep{slot["repetition"]}'
            print('VERIFY',candidate_id,flush=True)
            r=evaluate_candidate(w.store,spec,candidate_id=candidate_id,changes=g['changes'],purpose='native_matched_verification',**slot)
            g['records'].append(r)
            atomic_json(w.directory/'verification_progress.json',dict(plan=plan,groups=groups,usage=w.store.remaining()))
            if r['status']!='completed':
                atomic_json(w.directory/'verification_failure.json',r)
                break
        else:continue
        break
    aggregates=[dict(role=g['role'],acceptance=aggregate_acceptance(g['records'],10,schedule=slots)) for g in groups]
    complete=all(a['acceptance']['recorded']==10 and all(e['fresh_execution'] and e['acceptance_execution_matches'] and
        e['status'] in ('accepted','valid_failure') for e in a['acceptance']['entries']) for a in aggregates)
    comparison=compare_acceptance(aggregates[1]['acceptance'],aggregates[0]['acceptance']) if frozen and complete else dict(
        relation='unavailable',reason='No eligible candidate' if not frozen else 'Incomplete matched evidence')
    result=dict(plan=plan,groups=groups,aggregates=aggregates,complete=complete,comparison=comparison,
                improvement_supported=bool(frozen and complete and comparison['relation']=='improved'),usage=w.store.remaining())
    atomic_json(w.directory/'verification.json',result)
    pilot.reusable.feedback(w,dict(status='verification_delivered',verification=result), 'fresh_frozen_verification_feedback')
    return result


def finish(w):
    # A STOP closes research; this predeclared reporting step cannot reopen it.
    w.freeze['final_reporting']=True
    pilot.configure(w);pilot.persist(w)
    try:
        row=pilot.decision(w)
        atomic_json(w.directory/'final_model_interpretation.json',row)
    except Exception as exc:
        atomic_json(w.directory/'final_interpretation_failure.json',dict(type=type(exc).__name__,message=str(exc)))
    pilot.configure(w);pilot.persist(w)
    pilot.export(w)
    out=Path(w.freeze['experiment']['evidence_directory'])
    summary=dict(status=w.status,stop_reason=w.stop_reason,usage=w.store.remaining(),
        search=search_rows(w),verification=read(w.directory/'verification.json') if (w.directory/'verification.json').exists() else None,
        decisions=[dict(index=r['index'],action=r['decision']['decision']['action'],decision=r['accepted_decision'],
            mathematical_support=r['decision']['decision'].get('plan'),interpretations=r['decision']['model_interpretations']) for r in w.rounds],
        standalone_numerical_operations=0,workers=0,subagents=0,implementation=w.freeze['implementation'],
        historical_answers_unchanged=True,formal_groups_not_launched=True)
    usage=[]
    for e in w.store.events(w.host.run_id):
        if e['kind']=='model_raw_response' and e['status']=='completed':
            response=w.store.artifact(e['outputs'][0]);raw=response.get('raw',response)
            usage.append(dict(request_id=e.get('request_id'),usage=raw.get('usage')))
    summary['provider_usage']=usage
    summary['known_token_subtotal']={k:sum((r['usage'] or {}).get(k,0) for r in usage) for k in ('prompt_tokens','completion_tokens','total_tokens')}
    summary['usage_limitations']=['Failed requests without supplied usage remain unknown; monetary billing unknown.',
        'Embedded controller updates are backend work; zero standalone numerical experiments does not mean zero numerical computation.']
    atomic_json(out/'campaign_delivery.json',summary)
    print(json.dumps(dict(status=w.status,usage=w.store.remaining())),flush=True)


def live(directory=None):
    from examples.gvs_nmpc_route_experiment import load_credential
    config=read(CONFIG_PATH);w=pilot.restore(directory or ROOT/'runs'/config['campaign_id'])
    if w.status!='prepared' or w.freeze.get('offline_fixture'):raise ValueError('SEALED_OR_ATTEMPTED_CAMPAIGN_NO_RESET')
    if seal()['files']!=w.freeze['implementation']['files']:raise ValueError('FROZEN_IMPLEMENTATION_CHANGED')
    load_credential(Path.home()/'.codex/.env')
    w.status='running';pilot.persist(w)
    try:
        while w.status=='running':
            if time.time()-w.freeze['assignment_start_unix']>=36000:
                w.status='host_stopped';w.stop_reason='Elapsed assignment ceiling';break
            row=native_decision(w);pilot.reusable.execute(w,row);append_results(w,row)
    except Exception as exc:
        w.status='failed';w.stop_reason=str(exc)
        atomic_json(w.directory/'failure.json',dict(type=type(exc).__name__,message=str(exc),usage=w.store.remaining()))
    pilot.persist(w)
    # A complete negative scientific STOP permits frozen incumbent characterization.
    # Ambiguous execution/transport failure does not launch further paid physics.
    if w.status in ('model_stopped','execution_stopped'):
        try:verify(w)
        except Exception as exc:atomic_json(w.directory/'verification_failure.json',dict(message=str(exc)))
    finish(w)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['prepare','live']);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    prepare(args.output) if args.mode=='prepare' else live(args.output)
