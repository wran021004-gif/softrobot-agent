"""Offline final accounting and citation checks; never launches experimental work."""
import json
import hashlib
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.platform_store import Store
from tools.platform_handoff import validate_selector
from schemas.platform_handoff import EvidenceSelector
from tools.state_io import read,atomic_json


def export_closure(directory, destination, source_directories):
    """Read-only recovery of portable closure across explicitly named source stores."""
    stores=[Store(directory),*[Store(p) for p in source_directories]]
    primary=stores[0];artifacts={};unresolved={}
    with primary.connect(True) as db:run_ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
    events=[e for run in run_ids for e in primary.events(run)]
    def collect(ref):
        key=ref['artifact_id']
        if key in artifacts or key in unresolved:return
        for store in stores:
            with store.connect(True) as db:
                exists=db.execute('SELECT 1 FROM artifacts WHERE id=?',(key,)).fetchone()
            if exists:
                # Existing but corrupt/mismatched content must fail, never fall through.
                body=store.artifact(ref,raw=True)
                artifacts[key]=(ref,body,str(store.root))
                if ref['media_type']=='application/json':walk(json.loads(body))
                return
        unresolved[key]=ref
    def walk(value):
        if isinstance(value,dict):
            if set(value)=={'artifact_id','media_type'} and all(isinstance(x,str) for x in value.values()):collect(value)
            else:
                for child in value.values():walk(child)
        elif isinstance(value,list):
            for child in value:walk(child)
    for event in events:
        for ref in event['inputs']+event['outputs']:collect(ref)
    outcome=read(directory/'outcome.json');walk(outcome)
    folder=destination/'artifacts';folder.mkdir(parents=True,exist_ok=True)
    for key,(ref,body,owner) in artifacts.items():
        (folder/(key+('.json' if ref['media_type']=='application/json' else '.blob'))).write_bytes(body)
    atomic_json(destination/'events.json',events)
    for path in directory.glob('*.json'):atomic_json(destination/path.name,read(path))
    atomic_json(destination/'portable_closure.json',dict(method='Offline read-only cross-store resolution; original live stores, accepted products and request identities unchanged.',
        primary_store=str(directory),source_stores=[str(p) for p in source_directories],
        references=[dict(reference=ref,owner=owner) for ref,body,owner in artifacts.values()],unresolved=list(unresolved.values())))
    if unresolved:raise ValueError('UNRESOLVED_PORTABLE_REFERENCES: '+str(list(unresolved)))
    atomic_json(destination/'sha256_manifest.json',{p.relative_to(destination).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(destination.rglob('*')) if p.is_file() and p.name!='sha256_manifest.json'})


def audit_run(directory):
    outcome=read(directory/'outcome.json');store=Store(directory)
    with store.connect(True) as db:
        run_ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
        pending=[dict(r) for r in db.execute('SELECT run_id,request_id,status FROM calls WHERE receipt IS NULL')]
        receipts=[json.loads(r[0]) for r in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL')]
    phases={};tokens=[];requests=[];model_failures=[]
    for run_id in run_ids:
        for event in store.events(run_id):
            if event['kind']=='model_request':
                payload=store.artifact(event['inputs'][0]);context=json.loads(payload['messages'][1]['content'])
                phase=context['role_context']['phase'];phases[phase]=phases.get(phase,0)+1;requests.append(event['event_id'])
            elif event['kind']=='model_raw_response':
                response=store.artifact(event['outputs'][0]);value=response.get('raw',{}).get('usage')
                if value:tokens.append(value)
            elif event['kind']=='model' and event['status']!='completed':model_failures.append(event)
    reports=[]
    for key in ('initial_report','revised_report'):
        ref=outcome.get('chain',{}).get(key)
        if not ref:continue
        report=store.artifact(ref);count=0
        for selectors in report['fact_selectors'].values():
            for selector in selectors:
                validate_selector(store,EvidenceSelector.model_validate(selector));count+=1
        reports.append(dict(key=key,reference=ref,facts=len(report['fact_selectors']),exact_selectors=count,exact_mismatches=0,
            coverage='Accepted by existing live inventory/read-ledger validator; prose is reviewed separately.'))
    charged=store.remaining()['used']
    assert charged==outcome['usage']['used']
    assert not pending, pending
    assert len(requests)==charged['model_calls'], (len(requests),charged)
    result=dict(label=directory.name,status=outcome['status'],reason=outcome.get('stop_reason',outcome.get('gate_reason')),
        used=charged,limits=store.remaining()['limit'],pending=pending,attempts_by_phase=phases,
        token_usage_records=len(tokens),tokens={k:sum(t.get(k,0) for t in tokens) for k in ('prompt_tokens','completion_tokens','total_tokens')},
        monetary_cost=None,token_qualification='Reported usage only; a failed transport may return no usage.',
        accepted_reports=reports,failed_receipts=[r for r in receipts if r['execution_status']!='completed'],model_failures=model_failures)
    if 'physical_improvement' in outcome and isinstance(outcome['physical_improvement'],dict):
        physical=outcome['physical_improvement'];execution=physical.get('complete_execution')
        result.update(decision=store.artifact(outcome['chain']['improvement_decision']) if outcome.get('chain',{}).get('improvement_decision') else None,
            workflow_feedback_complete=outcome['feedback_complete'],candidate_executed=physical['candidate_executed'],
            validation_gap=physical['validation_gap'],execution=execution,improvement_measured=False)
        if execution and execution.get('factual_result'):
            current=execution['factual_result'];baseline=physical['baseline_facts']
            result['improvement_measured']=True
            result['comparison']=dict(definition='candidate minus replayed baseline; offline arithmetic from sealed factual results, not a model claim',
                baseline_execution=baseline['execution_id'],candidate_execution=current['execution_id'],
                terminal_error_delta_m=current['terminal_error_m']-baseline['terminal_error_m'],
                holding_max_error_delta_m=current['sampled_settling']['max_error_m']-baseline['sampled_settling']['max_error_m'],
                holding_max_speed_delta_m_s=current['sampled_settling']['max_speed_m_s']-baseline['sampled_settling']['max_speed_m_s'],
                mean_complete_update_delta_s=current['mean_complete_update_s']-baseline['mean_complete_update_s'],
                reach_plus_holding_passed=current['task_accepted'] and current['sampled_settling']['passed'])
    if directory.name=='baseline':result.update(gate_passed=outcome['gate_passed'],execution=outcome['result'])
    return result


def main():
    config=read(ROOT/'examples/stage350_experiment.json')
    physical_root=ROOT/'runs/stage350_physical_pilot_20261003'
    export_root=ROOT/'evidence/stage350_physical_pilot_20261003'
    for mode in ('single_context','dual_context'):
        if (physical_root/mode/'outcome.json').exists():
            export_closure(physical_root/mode,export_root/mode,[physical_root/'baseline',Path(config['source_store'])])
    diagnostic=[audit_run(path.parent) for path in sorted(Path(config['run_directory']).glob('*/outcome.json'))]
    physical=[audit_run(path.parent) for path in sorted((ROOT/'runs/stage350_physical_pilot_20261003').glob('*/outcome.json'))]
    rows=diagnostic+physical;used={k:sum(r['used'][k] for r in rows) for k in config['overall_stage_limits']}
    assert all(used[k]<=cap for k,cap in config['overall_stage_limits'].items())
    result=dict(diagnostic=diagnostic,physical=physical,used=used,limits=config['overall_stage_limits'],
        remaining={k:cap-used[k] for k,cap in config['overall_stage_limits'].items()},
        tokens={k:sum(r['tokens'][k] for r in rows) for k in ('prompt_tokens','completion_tokens','total_tokens')},monetary_cost=None,
        scope='Every original Stage 3.50 run exactly once. Mocked integration fixtures excluded from live campaign usage. No historical-stage costs included. Failed requests retained; provider-reported tokens may be incomplete.',
        diagnostic_freeze=read(Path(config['evidence_directory'])/'paired_freeze.json')['implementation'],
        physical_freeze=read(ROOT/'evidence/stage350_physical_pilot_20261003/campaign_freeze.json')['implementation'])
    atomic_json(ROOT/'evidence/stage350_physical_pilot_20261003/final_audit.json',result)
    print(json.dumps(dict(runs=len(rows),used=used,tokens=result['tokens'])))


if __name__=='__main__':main()
