"""Export the completed P4 transcript read-only; never sends or resumes a Study."""
import json
import hashlib
from tools.platform_host import Host
from tools.research.config import ROOT
from tools.research.provider import pending
from tools.research.provider_context import official_tokenizer
from tools.research.state import state
from tools.state_io import atomic_json, digest


def audit():
    study='p4-m5-none-20261029-a01';h=Host(ROOT/'runs/research'/study,study)
    events=h.store.events(study);s=state(h)
    folder=ROOT/'evidence/p4_provider_acceptance';folder.mkdir(parents=True,exist_ok=True)
    sends=[e for e in events if e['kind']=='r3_request'];rows=[]
    for i,event in enumerate(sends):
        meta=h.store.artifact(event['outputs'][0]);wire=h.store.artifact(meta['request'])
        reception=next(h.store.artifact(e['outputs'][0]) for e in reversed(events)
            if e['kind']=='r3_response' and e['request_id']==event['request_id'])
        body=h.store.artifact(reception['body'],raw=True);response=json.loads(body)
        # Store canonical request bytes preserve semantics; response bytes are
        # original HTTP body bytes saved before decoding. No auth header exists.
        (folder/f'request_{i+1:02}.json').write_bytes(h.store.artifact(meta['request'],raw=True))
        (folder/f'response_{i+1:02}.json').write_bytes(body)
        receipt=json.loads(h.store.lookup(study,event['request_id'])['receipt'])
        assert digest(json.loads((folder/f'request_{i+1:02}.json').read_bytes()))==h.store.lookup(study,event['request_id'])['request_hash']
        assert hashlib.sha256((folder/f'response_{i+1:02}.json').read_bytes()).hexdigest()==reception['body']['artifact_id']
        assert receipt['execution_status']=='completed' and receipt['charged']['model_calls']==1
        end=sends[i+1]['sequence'] if i+1<len(sends) else float('inf')
        feedback=[dict(reference=e['outputs'][0],**h.store.artifact(e['outputs'][0])) for e in events
            if event['sequence']<e['sequence']<end and e['kind']=='model_original_tool_feedback']
        atomic_json(folder/f'feedback_{i+1:02}.json',feedback)
        definitions=[dict(name=t['function']['name'],
            actions=t['function']['parameters'].get('properties',{}).get('action',{}).get('enum')) for t in wire.get('tools',[])]
        message=response['choices'][0]['message']
        rows.append(dict(number=i+1,request_id=event['request_id'],purpose=meta['purpose'],
            request=meta['request'],response=reception['body'],http_status=reception['http_status'],
            recovery_verified=dict(request_semantics=True,response_bytes=True,settled_receipt=True),
            actual_request_bytes=meta['input_bytes'],offline_serialized_token_estimate=len(official_tokenizer().encode(
                h.store.artifact(meta['request'],raw=True).decode(),add_special_tokens=False).ids),
            model=wire['model'],thinking=wire.get('thinking'),reasoning_effort=wire.get('reasoning_effort'),
            schemas=definitions,tool_calls=message.get('tool_calls',[]),text=message.get('content'),
            feedback=[dict(tool=f['tool_use']['name'],input=f['tool_use']['input'],status=f['result']['status'],
                reference=f['reference']) for f in feedback],usage=reception['usage'],money=reception['money'],
            finish_reasons=reception['finish_reasons']))
    totals={k:sum((r['usage'] or {}).get(k,0) for r in rows) for k in ('prompt_tokens','completion_tokens','total_tokens')}
    result=dict(study_id=study,execution_commit=s['freeze'],rows=rows,usage=totals,
        usage_complete=all(r['usage'] is not None for r in rows),money=None,money_status='unknown',
        ledger=h.store.remaining(),pending_provider_requests=len(pending(h)),unconsumed_response=s['pilot'].get('unconsumed_response'),
        candidates=len(s['candidates']),plans=len(s['plans']),mathematical_evaluations=s['mathematical_evaluations'],
        independent_physical_results=len(s['physical_replays']),reporter_requests=sum(r['purpose']=='reporter' for r in rows),
        research_status=s['research_status'],final_disposition=h.store.artifact(s['final_disposition']),
        levels=dict(L1=False,L2=False,L3=False,L4=False),
        scope='Real Provider protocol passed, no scientific Plan or new task-performance evidence. Engineering closure is not model STOP. No scientific Worker or retry.',
        request_export='Canonical original Store JSON, not byte-for-byte HTTP formatting; actual serialized length is recorded separately. Response files preserve exact original HTTP bodies.')
    atomic_json(folder/'manifest.json',result)
    print(json.dumps(dict(requests=len(rows),usage=totals,ledger=result['ledger'],levels=result['levels'],
        summaries=[dict(number=r['number'],schemas=r['schemas'],tools=[t['function']['name'] for t in r['tool_calls']],
            feedback=[f['status'] for f in r['feedback']],bytes=r['actual_request_bytes']) for r in rows])))
    return result


if __name__=='__main__':audit()
