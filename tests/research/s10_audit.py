"""Read-only S10 decision/provenance supplement; S8/S9 audits own numerics/costs."""
import hashlib,json,os,subprocess,tarfile
from pathlib import Path
from tools.platform_host import Host
from tools.research.config import ROOT
from tools.research.state import state,science_hashes,core_hashes
from tools.research.agent import load_credential
from tools.research.feedback import task_gap
from tools.state_io import atomic_json,read,digest


def decision_chain(h,out):
    events=h.store.events(h.run_id);feedback={};packets=[];reads=[];rows=[]
    for e in events:
        if e['kind']=='model_original_tool_feedback':
            v=h.store.artifact(e['outputs'][0]);feedback[v['tool_use']['toolUseId']]=(e,v)
        if e['kind']=='model_decision_packet':packets.append(e)
        if e['kind']=='model_original_tool_request':
            v=h.store.artifact(e['outputs'][0]);q=v['tool_use']['input']
            if v['tool_use']['name']=='evidence_read':reads.append(dict(sequence=e['sequence'],request=e['outputs'][0],query=q))
    for e in events:
        if e['kind']!='model_original_tool_request':continue
        tool=h.store.artifact(e['outputs'][0])['tool_use'];q=tool['input']
        if tool['name'] not in ('research_plan','research_analysis','research_rl'):continue
        fe,fv=feedback.get(tool['toolUseId'],(None,{}));result=fv.get('result',{})
        raw=''.join(b.get('text','') for b in result.get('content',[]))
        try:response=json.loads(raw)
        except ValueError:response=dict(text=raw)
        packet=next((p for p in reversed(packets) if p['sequence']<e['sequence']),None);decision=q.get('decision',{})
        row=dict(decision_index=len(rows)+1,sequence=e['sequence'],tool=tool['name'],action=q.get('action',q.get('operation')),
            evidence_before=dict(packet_reference=packet['outputs'][0] if packet else None,supporting_evidence=q.get('supporting_evidence',[])),
            hypothesis=q.get('hypothesis'),hypothesis_id=decision.get('hypothesis_id'),selected_method=decision.get('selected_method',q.get('operation')),
            selected_variables=decision.get('selected_variables'),requested_budget=decision.get('requested_budget'),
            expected_observation=q.get('expected_observation'),weakening_observation=q.get('weakening_observation'),interpretation=q.get('interpretation'),
            hypothesis_status='Interpret original expected/observed facts; no mathematical proof inferred',tool_status=result.get('status'),
            source_references=dict(request=e['outputs'][0],feedback=fe['outputs'][0] if fe else None),original_request=q,observed_feedback=response)
        if result.get('status')=='success' and response.get('reference'):
            value=h.store.artifact(response['reference']);row['complete_output_reference']=response['reference'];row['observed_result']=value.get('result',value)
        rows.append(row)
    for a,b in zip(rows,rows[1:]):a['next_decision']=dict(index=b['decision_index'],action=b['action'],request=b['source_references']['request'])
    if rows:rows[-1]['next_decision']=None
    calculations=[r for r in rows if r['action'] in ('physical_replay','control_search','execute','mechanics','replay','refine','equilibrium','input_sensitivity','linearization','controllability','start','evaluate') and r['tool_status']=='success']
    atomic_json(out/'feedback_decision_chain.json',dict(study_id=h.run_id,decisions=rows,evidence_read_requests=reads,
        successful_calculation_decisions=len(calculations),closeout_decisions=[r['decision_index'] for r in rows if r['action'] in ('select','stop')],
        limitation='One optimizer batch is one Agent decision regardless of probes. Rejected requests and STOP are separate. Explain revisions using original requests, feedback and intervening reads, not signatures alone. Missing analysis-contract hypothesis fields remain null.'))


def verify(h,out):
    s=state(h);frozen=read(out/'frozen_protocol.json');events=h.store.events(h.run_id)
    assert s['spec']['resolved_identity']==frozen['configuration_identity']
    assert science_hashes()==frozen['science_hashes'] and core_hashes()==frozen['core_hashes']
    assert s['freeze']=='7bac54ad311fab798d806ccd29504740a5cf07c4'
    unchanged=['tools','extensions','matlab','schemas','tasks','evidence/s7_mirror','evidence/s8_mirror','evidence/s9_variant','configs/research/family_space_s7.json']
    assert not subprocess.check_output(['git','diff','e7750c95','--',*unchanged],text=True)
    assert s['research_status']=='stopped' and not s['pending'] and not s['pilot'].get('unconsumed_response')
    assert not s.get('success_gate') and not s['selected']
    disposition=h.store.artifact(s['final_disposition']);assert disposition['origin']=='model' and disposition['original_plan']['action']=='stop'
    fresh=[r for k in ('results','mechanics_results','physical_replays','matched_state_results','rl_evaluations','analysis_results') for r in s.get(k,[])]
    assert {r['artifact_id'] for r in disposition['original_plan']['supporting_evidence']}=={r['artifact_id'] for r in fresh}
    assert all(task_gap(h.store.artifact(r))['valid_complete'] and not task_gap(h.store.artifact(r))['accepted'] for r in s['physical_replays'])
    assert all(h.store.artifact(r)['owning_study']==h.run_id for r in [*s['physical_replays'],*s['analysis_results']])
    with h.store.connect(True) as db:assert db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]==0
    requests=[e for e in events if e['kind']=='r3_request'];paired=0;responses={}
    for e in requests:
        wire=h.store.artifact(h.store.artifact(e['outputs'][0])['request']);assert digest(wire)==h.store.lookup(h.run_id,e['request_id'])['request_hash']
        ids={t['id'] for m in wire['messages'] if m['role']=='assistant' for t in m.get('tool_calls',[])}
        assert all(m.get('tool_call_id') in ids for m in wire['messages'] if m['role']=='tool')
    for e in events:
        if e['kind']=='r3_response':
            v=h.store.artifact(e['outputs'][0]);body=h.store.artifact(v['body'],raw=True)
            assert hashlib.sha256(body).hexdigest()==v['body']['artifact_id'];responses[e['request_id']]=v
        if e['kind']=='model_original_tool_request':
            t=h.store.artifact(e['outputs'][0])['tool_use'];matches=[f for f in events if f['kind']=='model_original_tool_feedback' and h.store.artifact(f['outputs'][0])['tool_use']['toolUseId']==t['toolUseId']]
            assert len(matches)==1 and h.store.artifact(matches[0]['outputs'][0])['tool_use']==t;paired+=1
    assert len(responses)==len(requests)
    load_credential(Path(s['spec']['runtime']['credentials_reference']).expanduser());secret=os.environ['DEEPSEEK_API_KEY'].encode()
    manifest=read(out/'study/archive_manifest.json');archive=out/'study/immutable_artifacts.tar.gz'
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['archive_sha256']
    with tarfile.open(archive) as tar:
        for m in manifest['members']:
            body=tar.extractfile(m['name']).read();assert hashlib.sha256(body).hexdigest()==m['sha256'] and secret not in body
    files=[p for d in (out,ROOT/'evidence/s10_readiness') for p in d.rglob('*') if p.is_file()]+[ROOT/p for p in ('docs/research/s10_delivery.md','configs/research/study_s10_mirror.json','configs/research/study_s10_readiness.json','configs/research/study_s10_admission.json','tests/research/s10_audit.py','tests/research/test_s10_configuration.py')]
    assert all(secret not in p.read_bytes() for p in files)
    atomic_json(out/'final_artifact_checks.json',dict(archive_members_verified=len(manifest['members']),configured_key_matches=0,files_scanned=len(files),
        science_core_task_and_sealed_history_unchanged=True,provider_requests=len(requests),model_tool_pairs=paired,
        request_tool_pairs_and_original_response_hashes_verified=True,all_receipts_settled=True,complete_stop_citations=len(fresh),
        fresh_physical_results=len(s['physical_replays']),fresh_mathematics=len(s['analysis_results']),native_model_stop=True,accepted=False,
        pending=None,unconsumed_response=None,ledger=h.store.remaining(),new_scientific_executions_in_audit=0))


if __name__=='__main__':
    host=Host(ROOT/'runs/research/s10-mirror-live-20261020','s10-mirror-live-20261020',actor='unified-research')
    destination=ROOT/'evidence/s10_mirror';decision_chain(host,destination);verify(host,destination)
    print(json.dumps(read(destination/'final_artifact_checks.json')))
