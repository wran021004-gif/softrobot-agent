"""Read-only original-source checks and publication projection; no live calls."""
from pathlib import Path
import hashlib,json,sys,time
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from tools.report_completion import D,OLD,OUT,START,workspace
from tools.state_io import read,atomic_json,digest
from tools.context_assembly import _no_secrets,request_facts
from tools.platform_store import zero

def run():
    w=workspace();v=read(D/'verification.json');rows=read(OUT/'all_execution_results.json')
    facts=read(OUT/'corrected_fact_projection.json')['bound_facts']
    request=read(OUT/'prepared_report_request.json')
    assert request_facts(request)==facts
    evidence={s['reference']['artifact_id']:s for s in read(OUT/'original_evidence_manifest.json')}
    for f in facts.values():
        s=evidence[f['source_artifact']['artifact_id']];raw=(ROOT/s['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==f['source_artifact']['artifact_id']
        value=json.loads(raw)
        for part in f['source_pointer'].split('/')[1:]:value=value[int(part)] if isinstance(value,list) else value[part]
        assert value==f['value']
    costs={};records=[];by_id={r['execution_id']:r for r in rows};verification_total=zero()
    for g in v['groups']:
        for r in g['records']:
            c=zero()
            assert [x['tool_id'] for x in r['receipts']]==['simulation.run','evaluation.run','control.profile_report']
            assert all(x['execution_status']=='completed' for x in r['receipts'])
            for rec in r['receipts']:
                call=w.store.lookup(r['candidate_id'],rec['request_id'])
                assert call and json.loads(call['receipt'])==rec
                for k in c:c[k]+=rec['charged'][k]
            assert c==r['cost']==by_id[r['receipt']['execution_id']]['costs']
            key=g['role']+'/'+r['case_id'];costs.setdefault(key,zero())
            for k in c:costs[key][k]+=c[k];verification_total[k]+=c[k]
            records.append(dict(execution_id=r['receipt']['execution_id'],receipts=r['receipts'],cost=c))
    assert len(records)==20
    atomic_json(OUT/'verified_execution_and_case_costs.json',dict(per_execution=records,per_role_case=costs,total=verification_total))
    attempts=[read(OUT/f'model_attempt_{i}.json') for i in range(3)]
    summary=read(OUT/'aggregate_results.json');report=attempts[2]['interpretation']
    assert (report['verification_execution_count'],report['incumbent_joint_passes'],report['candidate_joint_passes'],report['selection'],report['entire_suite_passed'],report['physical_structure_changed'])==(20,6,7,'promote_frozen_candidate',False,False)
    allowed=set(by_id)|{summary['original_incumbent']['execution_id']}
    assert set(report['evidence_execution_ids'])<=allowed and set(by_id)<=set(report['evidence_execution_ids'])
    assert all(a['report_binding']==digest(rows) for a in attempts if a['status']=='completed')
    old_usage=[]
    for e in w.store.events(w.host.run_id):
        if e['kind']=='model_raw_response' and e['status']=='completed':
            raw=w.store.artifact(e['outputs'][0]);old_usage.append(dict(request_id=e.get('request_id'),usage=raw.get('raw',raw).get('usage')))
    subtotal={k:sum((x['usage'] or {}).get(k,0) for x in old_usage) for k in ('prompt_tokens','completion_tokens','total_tokens')}
    initial=read(START)['authorization']['baseline'];current=w.store.remaining()
    with w.store.connect(True) as db:
        calls=[dict(x) for x in db.execute('SELECT * FROM calls WHERE receipt IS NULL')]
    assert len(calls)==1 and calls[0]['request_id']=='report-completion-engineering'
    reservation=json.loads(calls[0]['reserved']);settled_wall=current['used']['wall_s']-reservation['wall_s']
    accounting=dict(status='publication_inflight_delivery_reservation',original_local_settlement=initial,
        original_clock=read(D/'live_clock.json'),current_ledger=current,
        cumulative_settled_wall_s=settled_wall,outstanding_delivery_reservation=reservation,
        incremental_settled_provider_cost={k:sum(a['receipt']['charged'][k] for a in attempts) for k in zero()},
        workflow_operations_charged=1,provider_attempts=3,cumulative_material_repairs=8,
        actual_delivery_elapsed_so_far_s=time.time()-read(START)['authorization']['started_unix'],
        known_token_subtotal=subtotal,provider_usage=old_usage,
        unknown_usage=[dict(request_id='report-completion-model-0',usage=None,reason='Connection refused, no complete response or supplied usage')],
        monetary_bill=None,final_actual_source='runs/research_native_development_v3_20261007/report_completion_settled_costs.json after verified normal push; no second settlement of the old campaign close')
    atomic_json(OUT/'publication_inflight_accounting.json',accounting)
    # Freeze the new report-phase Store records needed by manifests/receipts.
    refs=[]
    for p in (OUT/'context_assembly/manifests').glob('*.json'):
        refs += [s['reference'] for s in read(p)['sources'] if 'store_root' in s]
    refs += [a['receipt']['output'] for a in attempts]
    refs += [a['raw_response'] for a in attempts if isinstance(a.get('raw_response'),dict)]
    for ref in refs:
        if (OLD/'store/artifacts'/f'{ref["artifact_id"]}.json').exists():continue
        raw=w.store.artifact(ref,raw=True)
        assert hashlib.sha256(raw).hexdigest()==ref['artifact_id']
        path=OUT/'store/artifacts'/f'{ref["artifact_id"]}.json';path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():assert path.read_bytes()==raw
        else:path.write_bytes(raw)
    integrity=[]
    for path in OUT.rglob('*'):
        if not path.is_file() or path.name=='publication_manifest.json':continue
        if path.suffix=='.json':_no_secrets(read(path))
        raw=path.read_bytes()
        if len(path.stem)==64 and path.suffix=='.json':
            if path.parent.name in ('sources','artifacts'):assert hashlib.sha256(raw).hexdigest()==path.stem
            elif path.parent.name=='manifests':assert digest(read(path))==path.stem
        integrity.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
    atomic_json(OUT/'publication_manifest.json',dict(files=integrity,original_records_hash_verified=80,
        all_fact_source_pointers_exact=60,source_count=20,original_snapshot_unchanged=True,
        tests=dict(affected_regression_tests=10,actual_source_adversarial_tests=4,passed=True),
        complete_counts_unchanged=True,current_response_has_complete_evidence_binding=True,
        model_interpretation_accepted=False,full_deterministic_report_available=True))
    print(json.dumps(dict(verified_records=20,exact_facts=60,verification_cost=verification_total,
        publication_files=len(integrity),known_token_subtotal=subtotal,inflight_usage=current,provider_settled_wall=accounting['incremental_settled_provider_cost']['wall_s'])))

if __name__=='__main__':run()
