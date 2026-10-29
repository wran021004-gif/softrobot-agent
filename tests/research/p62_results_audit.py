"""Read-only P6.2 receipt, provenance and actual-wire continuity export."""
import argparse
from copy import deepcopy
import hashlib
import json
from tests.research.p62_live_audit import host, source_data
from tests.research.p5_comparison_audit import decoded_feedback
from tools.research import reporter
from tools.research.provider import pending, received
from tools.research.session_handoff import packet_feedback, unmatched
from tools.research.state import state
from tools.state_io import atomic_json, digest
from tools.research.config import ROOT


def audit(arm):
    h=host(arm);before=hashlib.sha256(h.store.db.read_bytes()).hexdigest()
    s=state(h);events=h.store.events(h.run_id);rows=[];wires={}
    for e in events:
        if e['kind']!='r3_request':continue
        meta=h.store.artifact(e['outputs'][0]);wire=h.store.artifact(meta['request'])
        response=received(h,e['request_id']);wires[e['sequence']]=wire
        body=json.loads(h.store.artifact(response['body'],raw=True)) if response else {}
        msg=body.get('choices',[{}])[0].get('message',{})
        receipt=json.loads(h.store.lookup(h.run_id,e['request_id'])['receipt'])
        assert receipt['charged']['model_calls']==1
        assert digest(wire)==h.store.lookup(h.run_id,e['request_id'])['request_hash']
        row=dict(sequence=e['sequence'],request_id=e['request_id'],purpose=meta['purpose'],
            model=wire['model'],reasoning=wire.get('reasoning_effort'),input_bytes=meta['input_bytes'],
            request_reference=meta['request'],response_reference=response.get('body') if response else None,
            http_status=response.get('http_status') if response else None,usage=body.get('usage'),
            error=body.get('error'),text=msg.get('content'),
            tool_calls=[dict(id=t['id'],name=t['function']['name'],arguments=json.loads(t['function']['arguments'])) for t in msg.get('tool_calls',[])],
            schema_names=[t['function']['name'] for t in wire.get('tools',[])],
            delivered_tool_ids=[m['tool_call_id'] for m in wire['messages'] if m['role']=='tool'])
        rows.append(row)
    for i,row in enumerate(rows):
        end=rows[i+1]['sequence'] if i+1<len(rows) else float('inf')
        row['feedback']=[dict(tool=h.store.artifact(e['outputs'][0])['tool_use']['name'],
            tool_id=h.store.artifact(e['outputs'][0])['tool_use']['toolUseId'],reference=e['outputs'][0],
            **decoded_feedback(h,h.store.artifact(e['outputs'][0]))) for e in events
            if row['sequence']<e['sequence']<end and e['kind']=='model_original_tool_feedback']
    reports=[]
    for ref,saved in reporter.current_reports(h):
        report=saved['report']
        payloads=[json.loads(w['messages'][-1]['content']) for seq,w in wires.items()
            if next(r for r in rows if r['sequence']==seq)['purpose']=='reporter']
        payload=next((p for p in payloads if p['report']['question']==report['question']),{})
        for loc in payload.get('source_catalog',{}).values():
            value=h.store.artifact(loc['reference'])
            for token in loc['pointer'].strip('/').split('/') if loc['pointer'] else []:
                token=token.replace('~1','/').replace('~0','~')
                value=value[int(token)] if isinstance(value,list) else value[token]
        reports.append(dict(reference=ref,question=report['question'],status=saved['interpretation_status'],error=saved['error'],
            interpretations=report['interpretations'],source_catalog_count=len(payload.get('source_catalog',{})),
            all_catalog_sources_recoverable=True if payload else None,selected_reads=[dict(query=r['query'],status=r.get('status','available'),reason=r.get('reason'))
                for r in saved.get('request',{}).get('selected_reads',[])],
            findings=[dict(identity=c['identity'],metrics=c['metrics'],critical_observations=c['critical_observations'],
                violations=c['main_violations'],comparisons=c['deterministic_summary'].get('comparisons')) for c in report['results']]))
    handoffs=[]
    for event in events:
        if event['kind']!='session_handoff' or event['status']!='committed':continue
        prep=h.store.artifact(event['outputs'][0]);verification=h.store.artifact(event['outputs'][1])
        boundary=h.store.artifact(prep.get('boundary',prep.get('completed_boundary')))
        assert not unmatched(boundary['messages'])
        prior=next((h.store.artifact(e['outputs'][0])['research'] for e in reversed(events)
            if e['kind']=='model_decision_packet' and e['sequence']<event['sequence']),None)
        next_seq=next((seq for seq,w in wires.items() if seq>event['sequence'] and w.get('tools')),None)
        after=json.loads(wires[next_seq]['messages'][-1]['content'].split('\n',1)[1])['research'] if next_seq else None
        fields=('study_goal','research_focus','verified_facts','research_trace','knowledge','reporter_findings','budget','evidence_access','tool_continuation')
        equal={k:prior.get(k)==after.get(k) for k in fields} if after and prior else {}
        expected=prep.get('pending_feedback_delivery')
        delivered=packet_feedback(after) if after else None
        continuation_equal=(
            {k:v for k,v in prior['tool_continuation'].items() if k not in ('recent','pending_feedback')}==
            {k:v for k,v in after['tool_continuation'].items() if k not in ('recent','pending_feedback')}
            if prior and after else None)
        handoffs.append(dict(sequence=event['sequence'],reference=event['outputs'][0],
            boundary=prep.get('boundary_kind','completed_invocation'),old_session=prep['previous_session'],new_session=prep['next_session'],
            source_state_identity=prep['source_state_identity'],scientific_results=prep['scientific_results'],
            budget=prep['budget'],independently_restored=verification['independently_restored'],
            original_tool_pairs_complete=True,next_request_sequence=next_seq,actual_wire_field_equality=equal,
            selected_and_loaded_tools_preserved=continuation_equal,
            feedback_representation='Settled native feedback is projected into pending_feedback in the fresh SDK session; recent is consumed, not lost.',
            precise_feedback_preserved=(expected==delivered) if expected else None,
            pending_feedback_expected=expected,actual_feedback=delivered,
            old_history_absent=not any(m.get('tool_calls') or m['role']=='tool' for m in wires[next_seq]['messages']) if next_seq else None))
    usage={}
    for role in ('reporter','main'):
        group=[r for r in rows if (r['purpose']=='reporter')==(role=='reporter')]
        def total(field):
            values=[(r.get('usage') or {}).get(field) for r in group]
            return sum(values) if all(v is not None for v in values) else None
        cached=[(r.get('usage') or {}).get('prompt_tokens_details',{}).get('cached_tokens') for r in group]
        usage[role]=dict(requests=len(group),prompt_tokens=total('prompt_tokens'),completion_tokens=total('completion_tokens'),
            total_tokens=total('total_tokens'),cached_tokens=sum(cached) if all(v is not None for v in cached) else None,
            usage_missing=sum(r.get('usage') is None for r in group))
    source,_,refs=source_data();manifest=json.loads((h.store.root/'source_manifest.json').read_text())
    source_unchanged=hashlib.sha256(source.db.read_bytes()).hexdigest()==manifest['source_store_sha256']
    assert source_unchanged and len(rows)<=10 and usage['main']['requests']<=7 and usage['reporter']['requests']<=3
    ledger=h.store.remaining();assert ledger['used']['model_calls']==len(rows)
    assert ledger['used']['backend_solves']==ledger['used']['worker_calls']==s['mathematical_evaluations']==0
    result=dict(arm=arm,study=h.run_id,execution_commit=s['freeze'],source_manifest=manifest,
        rows=rows,reports=reports,handoffs=handoffs,usage=usage,ledger=ledger,
        provider_pending=len(pending(h)),unconsumed_response=s['pilot'].get('unconsumed_response'),
        scientific_pending=s['pending'],new_science=dict(mathematics=0,physics=0,rl=0),
        source_unchanged=source_unchanged,read_coverage=s['reads'],
        final_status=s['research_status'],final_disposition=s.get('final_disposition'),
        limitations=['Single trajectory per model; no causal model ranking or efficiency-improvement claim.',
            'Historical S142 observations are background evidence and do not earn current-study acceptance.',
            'Raw Provider requests/responses and SDK snapshots remain in the local ignored Store; opaque reasoning and credentials are not exported.',
            'Null usage fields are unreported, never imputed as zero.'])
    assert hashlib.sha256(h.store.db.read_bytes()).hexdigest()==before
    atomic_json(ROOT/'docs/research'/('p62_'+arm+'_results.json'),result)
    print(json.dumps(dict(arm=arm,usage=usage,handoffs=[{k:v for k,v in row.items() if k not in ('pending_feedback_expected','actual_feedback')} for row in handoffs],source_unchanged=source_unchanged)))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--arm',choices=['luna','mini'],required=True)
    audit(p.parse_args().arm)
