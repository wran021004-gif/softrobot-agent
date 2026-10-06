"""Offline saved-corpus observation. No grants, provider calls or numerical work."""
from copy import deepcopy
from pathlib import Path
import sys
import hashlib
import json
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.state_io import read, atomic_json
from tools.platform_store import Store
from tools.context_assembly import EvidenceArchive, assemble_request, research_authority, measure_input
from tools.study_history import study_history, execution_chronology

DEST=ROOT/'evidence/context_assembly_20261006'
M4ROOT=ROOT/'runs/milestone4_autonomous_20261006'


def saved_research_fixture():
    """Refresh only source-derived identity fields missing in the old projection."""
    store=Store(M4ROOT);state=read(M4ROOT/'scheduler_state.json')
    saved=read(M4ROOT/'round2_request.json');packet=deepcopy(saved['packet'])
    packet['history']=study_history(store,state['records'],retained_baseline=state['baseline']['candidate'],
        selected_source=state['batch_source'],latest_tested=state['latest'],selection=state['selected'])
    packet['chronology']=execution_chronology(store,state['records'])
    packet['acceptance']=read(M4ROOT/'freeze.json')['common_scientific_input']['acceptance']
    ids=[];pairs=[]
    for row in state['rounds']:
        if row.get('kind')!='search' or not row.get('complete'):continue
        for c in store.artifact(row['result'])['candidates']:
            if c['reused'] or not c.get('execution_id'):continue
            ids.append(c['execution_id'])
            if c.get('replication_of'):pairs.append((c['replication_of']['execution_id'],c['execution_id']))
    authority=research_authority(packet,replication_pairs=pairs,new_execution_ids=ids)
    original=deepcopy(saved['payload'])
    context=json.loads(original['messages'][1]['content'])
    context['role_context']['research_packet']=packet
    original['messages'][1]['content']=json.dumps(context,ensure_ascii=False)
    return store,state,packet,authority,original


def actual_research_builder(directory):
    """Run the actual native adapter/payload path against read-only saved state.

    Mock only the current role packet in memory to supply the improved identities
    and this offline archive directory. No old session is written or resumed.
    """
    from tools.platform_host import Host
    from tools.platform_models import payload_for
    from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
    store,state,packet,authority,_=saved_research_fixture()
    run_id=read(M4ROOT/'freeze.json')['research_host'];original_session=Store.session
    real_archive=EvidenceArchive
    def session(s, rid, db=None):
        result=original_session(s,rid,db)
        if s.root==store.root and rid==run_id:
            result=deepcopy(result)
            result['state']['role_context'].update(research_packet=packet,context_authority=authority)
        return result
    def archive(_directory,**kwargs):return real_archive(directory,**kwargs)
    adapter=EvidenceDrivenAdapter()
    with patch.object(Store,'session',session),patch('tools.context_assembly.EvidenceArchive',archive):
        payload=payload_for(Host(M4ROOT,run_id),adapter)
    return payload,adapter.context_assembly_audit


def observe():
    from tools.runtime_identity import require_softagent_runtime
    require_softagent_runtime()
    from examples.milestone_bound_successor import build_reporting_request4, M4, M5
    from examples.milestone5_control_reporting import packet as packet5, build_interpretation_request
    from tools.bound_reporting import render, render_text
    from tools.context_assembly import request_facts
    # Scientific archives and ledgers are checked before/after; no old exports rerun.
    protected=[p for d in ('evidence/milestone4_bound_20261006','evidence/milestone5_control_20261006')
        for p in (ROOT/d).rglob('*') if p.is_file()]
    protected += [ROOT/'runs'/d/'platform.sqlite' for d in
        ('milestone4_autonomous_20261006','milestone4_bound_20261006','milestone5_control_20261006')]
    before={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    config=read(M4ROOT/'freeze.json')['provider_configuration']
    payload,audit=actual_research_builder(DEST/'research')
    observations={'research_decision':dict(before=audit['before_measurement'],after=audit['measurement'],
        source_manifest=audit['source_manifest'],selected_fact_count=len(audit['selected_fact_ids']))}
    atomic_json(DEST/'research_payload.json',payload);atomic_json(DEST/'research_audit.json',audit)
    old4=read(M4/'interpretation2_request.json');old5=read(M5/'interpretation0_request.json')
    archive4=EvidenceArchive(DEST/'final_report',scope={'role':'M4 final reporting','scientific_execution':False},
        stores=(Store(M4ROOT),Store(M4)))
    payload4,audit4=build_reporting_request4(config,read(M4/'ledger.json'),old4['payload']['messages'][0]['content'],archive=archive4)
    archive5=EvidenceArchive(DEST/'interpretation',scope={'role':'M5 research interpretation','prospective_case_access':False},
        stores=(Store(M5),Store(M4ROOT)))
    payload5,audit5=build_interpretation_request(config,packet5(),old5['payload']['messages'][0]['content'],archive=archive5)
    for name,p,a,old in [('M4_final_report',payload4,audit4,old4),('M5_research_interpretation',payload5,audit5,old5)]:
        atomic_json(DEST/(name+'_request.json'),dict(payload=p,context_assembly_audit=a))
        observations[name]=dict(before_same_enriched_corpus=a['before_measurement'],after=a['measurement'],
            previously_sent=measure_input(old['payload'],config,a['purpose']),
            source_manifest=a['source_manifest'],selected_fact_count=len(a['selected_fact_ids']))
        assert {k:v for k,v in p.items() if k not in ('messages','tools')}=={k:v for k,v in old['payload'].items() if k not in ('messages','tools')}
    assert render(read(M4/'interpretation2.json')['interpretation'],read(M4/'ledger.json'))==read(M4/'rendering2.json')
    rendered5=render_text(read(M5/'interpretation0.json')['interpretation'],request_facts(dict(payload=payload5,context_assembly_audit=audit5)))
    atomic_json(DEST/'saved_response_offline_render.json',rendered5)
    assert {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}==before
    atomic_json(DEST/'protected_hash_verification.json',dict(passed=True,hashes=before))
    # Archived old provider usage is observation of OLD paths only.
    old_usage={name:read(path).get('usage') for name,path in
        [('M4',M4/'interpretation2_raw.json'),('M5',M5/'interpretation0_raw.json')]}
    result=dict(version='evidence_context_assembly@1.0.0',sizes=observations,prior_actual_usage=old_usage,
        method='Complete serialized UTF-8 wire bytes plus configured framing; conservative token estimates, no tokenizer installed.',
        retained_information=['All supplied execution metrics and ownership','Different structures despite equal weights',
            'Explicit source/new matching repeat and aggregate differences','Counterexamples and failed reviews',
            'Event-bound roles and chronology','Acceptance, legal actions, sealed stop and remaining budget'],
        live_verification=dict(performed=False,reason='M4 reviewed report succeeded and provider ceiling exhausted; M5 successful interpretation and negative development sealed. No planned unexecuted eligible call remains.',
            attribution_recurrence=None,replication_recurrence=None,new_actual_input_tokens=None,new_provider_cost=None),
        charges=dict(model_calls=0,workflow_operations=0,backend_solves=0,forecasts=0,controller_solves=0,workers=0),
        accounting='Existing offline engineering convention; no grant created/reset, paid summarization or scientific operation.',
        scope_seals_preserved=True)
    atomic_json(DEST/'observation.json',result)
    print(json.dumps({k:{'before':v.get('before',v.get('before_same_enriched_corpus'))['utf8_bytes'],
        'after':v['after']['utf8_bytes']} for k,v in observations.items()}))


if __name__=='__main__':observe()
