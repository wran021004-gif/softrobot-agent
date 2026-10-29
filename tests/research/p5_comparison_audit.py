"""Read-only receipt audit; raw Provider material remains in ignored Stores."""
import hashlib
import json
from tools.platform_host import Host
from tools.research.config import ROOT
from tools.research.provider import pending, received
from tools.research.state import state
from tools.state_io import atomic_json, digest


def decoded_feedback(host, saved):
    blocks=saved['result'].get('content',[])
    text=next((b['text'] for b in blocks if 'text' in b),'')
    try:value=json.loads(text)
    except ValueError:return dict(status=saved['result']['status'],message=text)
    if value.get('wrapper_reference'):
        wrapper=value['wrapper_reference'];value=host.store.artifact(wrapper)
        result=value.get('result',{})
        return dict(status=saved['result']['status'],wrapper=wrapper,
            result={k:result[k] for k in ('status','reason','candidate','source','task_acceptance',
                'scientific_acceptance','task_success','accepted_stop') if k in result},
            full_result_query=dict(reference=wrapper,view='full',pointer='/result'))
    return dict(status=saved['result']['status'],
        result={k:value[k] for k in ('status','error_code','reason','field','expected','scientific_execution_started',
            'tool','action','scope') if k in value})


def audit(arm):
    run=f'p5-m5-{arm}-none-20261029-a01'
    host=Host(ROOT/'runs/research'/run,run)
    before=hashlib.sha256(host.store.db.read_bytes()).hexdigest()
    events=host.store.events(run);s=state(host)
    sends=[e for e in events if e['kind']=='r3_request'];rows=[]
    for n,event in enumerate(sends,1):
        meta=host.store.artifact(event['outputs'][0]);wire=host.store.artifact(meta['request'])
        reception=received(host,event['request_id'])
        row=dict(number=n,request_id=event['request_id'],purpose=meta['purpose'],phase=meta.get('request_phase'),
            model=wire['model'],reasoning_effort=wire.get('reasoning_effort'),thinking=wire.get('thinking'),
            input_bytes=meta['input_bytes'],request_reference=meta['request'],
            schemas=[dict(name=t['function']['name'],identity=digest(t['function']['parameters']),
                actions=t['function']['parameters'].get('properties',{}).get('action',{}).get('enum')) for t in wire.get('tools',[])])
        row['returned_tool_ids']=[m['tool_call_id'] for m in wire['messages'] if m['role']=='tool']
        originals=[m for m in wire['messages'] if m.get('provider_output') is not None]
        row['native_function_arguments_exact']=all(
            [(c['id'],c['function']['name'],c['function']['arguments']) for c in m.get('tool_calls',[])]==
            [(i['call_id'],i['name'],i['arguments']) for i in m['provider_output'] if i['type']=='function_call'] for m in originals)
        receipt=json.loads(host.store.lookup(run,event['request_id'])['receipt'])
        row['charged_provider_requests']=receipt['charged']['model_calls']
        assert digest(wire)==host.store.lookup(run,event['request_id'])['request_hash']
        if reception:
            raw=host.store.artifact(reception['body'],raw=True);body=json.loads(raw)
            assert hashlib.sha256(raw).hexdigest()==reception['body']['artifact_id']
            message=body.get('choices',[{}])[0].get('message',{})
            row.update(http_status=reception['http_status'],response_reference=reception['body'],
                usage=reception.get('usage'),money=reception.get('money'),error=body.get('error'),
                assistant_text=message.get('content'),
                tool_calls=[dict(id=c['id'],name=c['function']['name'],arguments=json.loads(c['function']['arguments']))
                    for c in message.get('tool_calls',[])],
                native_output_item_types=[i['type'] for i in message.get('provider_output',[])],
                recovery_verified=dict(request_semantics=True,exact_gateway_response_bytes=True,settled_receipt=True))
        end=sends[n]['sequence'] if n<len(sends) else float('inf')
        row['feedback']=[]
        for feedback in events:
            if not (event['sequence']<feedback['sequence']<end and feedback['kind']=='model_original_tool_feedback'):continue
            value=host.store.artifact(feedback['outputs'][0])
            row['feedback'].append(dict(tool=value['tool_use']['name'],tool_id=value['tool_use']['toolUseId'],
                reference=feedback['outputs'][0],**decoded_feedback(host,value)))
        rows.append(row)
    usage_complete=all(r.get('usage') is not None for r in rows)
    known={k:sum((r.get('usage') or {}).get(k,0) for r in rows) for k in ('prompt_tokens','completion_tokens','total_tokens')}
    result=dict(arm=arm,study_id=run,execution_commit=s['freeze'],source_authority=s['spec']['authorization'],rows=rows,
        requests=len(rows),ledger=host.store.remaining(),usage_complete=usage_complete,known_usage_subtotal=known,
        total_usage=known if usage_complete else None,money=None,money_status='unknown',
        reporter_requests=sum(r['purpose']=='reporter' for r in rows),
        candidates=list(s['candidates'].values()),control_initializations=s.get('control_initializations',[]),
        mathematical_evaluations=s['mathematical_evaluations'],physical_results=len(s['physical_replays']),
        pending_provider_requests=len(pending(host)),pending_science=s['pending'],
        unconsumed_response=s['pilot'].get('unconsumed_response'),research_status=s['research_status'],
        final_disposition=s.get('final_disposition'),
        final_disposition_content=host.store.artifact(s['final_disposition']) if s.get('final_disposition') else None,
        source_store_unchanged=before==hashlib.sha256(host.store.db.read_bytes()).hexdigest(),
        limitations=['Usage missing on any attempt remains unknown; known_usage_subtotal is not an exact whole-arm total.',
            'Canonical request semantics and exact Gateway/Provider HTTP response bodies are retained locally; upstream SSE is not separately archived.',
            'Gateway HTTP 200 implies its response.completed-only path returned; local HTTP 400 is not a second upstream inference.',
            'No opaque reasoning, credentials, full request, or full response is exported by this audit.'])
    assert result['source_store_unchanged']
    return result


def main():
    arms=[audit(arm) for arm in ('deepseek','luna')]
    atomic_json(ROOT/'docs/research/p5_comparison_results.json',dict(arms=arms,
        actual_provider_attempts=sum(a['requests'] for a in arms),retry_policy='No automatic retry or fallback.',
        source='Existing production Harness, native tools, Store ledger and immutable receipts.'))
    print(json.dumps([dict(arm=a['arm'],requests=a['requests'],usage=a['known_usage_subtotal'],
        candidates=len(a['candidates']),control_initializations=len(a['control_initializations']),status=a['research_status']) for a in arms]))


if __name__=='__main__':main()
