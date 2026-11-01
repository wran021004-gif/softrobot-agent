"""Last of the existing six engineering requests: actual STOP submission context."""
import asyncio,json,hashlib
from pathlib import Path
from types import SimpleNamespace
from copy import deepcopy
import httpx
from jsonschema import Draft202012Validator
from tools.platform_store import Store,zero
from tools.research.provider import LiveBoundary,credential,record
from tools.research.state import state
from tools.research.research_context import research_opportunity_review
from tools.research.object_choices import main_projection
from tools.research.agent import plan_schema
from tools.state_io import read,atomic_json,digest
from tests.research.m1_stop_review import historical_decision


async def run(out):
    data=read(out/'results-private.json');h,wire,source=historical_decision(73)
    engine=SimpleNamespace(store=Store(out/'provider'),run_id='m1-stop-real-decision-contrast-20261102')
    if engine.store.remaining()['used']['model_calls']!=5:raise ValueError('EXACT_FIVE_PRIOR_ENGINEERING_REQUESTS_REQUIRED')
    before=deepcopy(wire);packet=json.loads(wire['messages'][-1]['content'].split('\n',1)[1])
    facts=research_opportunity_review(h)
    packet['research']['evidence_access']['opportunity_review']=main_projection(h,dict(
        query=dict(reference=state(h)['family_space_reference'],view='working_set',pointer='/research_opportunities'),facts=facts,
        purpose='Explain considered alternatives in Plan interpretation; no direction is prescribed.'))
    wire['messages'][-1]['content']='CURRENT_RESEARCH_PACKET\n'+json.dumps(packet,separators=(',',':'))
    for t in wire['tools']:
        if t['function']['name']=='research_plan':t['function']['parameters']['properties']['interpretation']['description']=plan_schema(['stop'],study=state(h)['spec'])['properties']['interpretation']['description']
    assert wire['messages'][:-1]==before['messages'][:-1]
    record(engine,'engineering_stop_trigger_case',dict(source=source,original_wire=digest(before),new_wire=digest(wire),
        changed_fields=['last current packet: opportunity facts/query','STOP interpretation description'],
        source_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),new_scientific_data=False))
    atomic_json(out/'trigger-request.json',wire)
    provider=state(h)['pilot']['provider'];key=credential(provider,state(h)['spec']['runtime']['credentials_reference'])
    boundary=LiveBoundary(engine,max_model_calls=6)
    try:
        response=await boundary.handle_async_request(httpx.Request('POST',provider['base_url'].rstrip('/')+'/chat/completions',json=wire,
            headers={'Authorization':'Bearer '+key},extensions={'timeout':dict(connect=30,read=provider['timeout_s'],write=30,pool=30)}))
        response.raise_for_status();body=response.json();atomic_json(out/'trigger-response.json',body);boundary.consumed()
        row=dict(arm='stop_trigger_new',turn=1,request_id=boundary.last_request,usage=body.get('usage'),decisions=[],scientific_dispatch=False,source=source)
        for c in body['choices'][0]['message'].get('tool_calls',[]):
            name=c['function']['name'];payload=json.loads(c['function']['arguments']);schema=next(t['function']['parameters'] for t in wire['tools'] if t['function']['name']==name)
            try:Draft202012Validator(schema).validate(payload);feedback=dict(status='provider_schema_valid',scientific_execution=False)
            except Exception as exc:feedback=dict(status='rejected',reason=str(exc)[:1000],scientific_execution=False)
            row['decisions'].append(dict(tool=name,input=payload,feedback=feedback))
        data['results'].append(row)
        # Account the read-only followup feedback in this same engineering ledger.
        # Initial turn-1 feedback was already settled by the initial harness.
        for r in data['results']:
            if r['turn']==1 and r['arm'] in ('old','new'):continue
            for i,d in enumerate(r['decisions']):
                key='engineering-feedback-'+r['request_id']+'-'+str(i)
                reservation,reused=engine.store.reserve(engine.run_id,key,digest(d['input']),'engineering-read',{**zero(),'tool_calls':1},kind='engineering_decision_feedback')
                if not reused:engine.store.complete(reservation,dict(request_id=key,execution_id=reservation['execution_id'],caller='engineering-read',tool_id='engineering.decision_feedback',tool_version='1',execution_status='completed',charged={**zero(),'tool_calls':1}),d['feedback'])
        data['ledger']=engine.store.remaining();atomic_json(out/'results-private.json',data);atomic_json(out/'opportunity-example.json',facts)
        print(json.dumps(dict(used=data['ledger']['used'],decision=[dict(tool=d['tool'],action=d['input'].get('action'),status=d['feedback']['status']) for d in row['decisions']])))
    finally:await boundary.aclose()


if __name__=='__main__':
    import sys
    asyncio.run(run(Path(sys.argv[1])))
