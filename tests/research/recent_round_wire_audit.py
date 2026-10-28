"""Offline SDK wire audit of saved v5 evidence. All HTTP uses MockTransport.

The paired workflow replays v5 replies 1, 2, 6, 7, 8; routing replies are
explicit scripted fixtures. No model choices, new scientific results or API
charges can be inferred. Historical Stores are opened read-only.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
import sqlite3
from unittest.mock import patch
from uuid import uuid4
import httpx
from tools.research.config import ROOT
from tools.research.provider_context import official_tokenizer, TOKENIZER_SHA256
from tools.research.research_context import research_action_trace, trace_entry, research_recall, read_coverage
from tools.research.state import state
from tests.research import main_off_live_probe as probe

SOURCE=ROOT/'runs/research/main-off-saved-c3-v5-20261028/platform.sqlite'
DEST=ROOT/'evidence/recent_round_trace/offline_wire_audit.json'


def spans(text):
    """Exact JSON character spans, including each selected value's encoding."""
    decoder=json.JSONDecoder();found={}
    def walk(i,path):
        while text[i].isspace():i+=1
        start=i;value,end=decoder.raw_decode(text,i);found[path]=(start,end)
        if isinstance(value,dict):
            i+=1
            for _ in value:
                while text[i].isspace() or text[i]==',':i+=1
                key,i=decoder.raw_decode(text,i)
                while text[i].isspace() or text[i]==':':i+=1
                i=walk(i,(*path,key))
        elif isinstance(value,list):
            i+=1
            for n in range(len(value)):
                while text[i].isspace() or text[i]==',':i+=1
                i=walk(i,(*path,n))
        return end
    walk(0,());return found


def measure(content):
    """Mutually exclusive encoded byte partitions, plus whole-request tokens."""
    text=content.decode();wire=json.loads(text);nodes=spans(text);ranges=[]
    def add(path,group):
        if path in nodes:ranges.append((*nodes[path],group))
    add(('tools',),'tool_schema')
    messages=wire['messages'];last_tools=[]
    for i,m in enumerate(messages):
        if m.get('tool_calls'):last_tools=[]
        if m['role']=='tool':last_tools.append(i)
    for i,m in enumerate(messages):
        path=('messages',i)
        if m['role']=='system':add(path,'system');continue
        value=m.get('content')
        if m['role']=='user' and isinstance(value,str) and value.startswith('CURRENT_RESEARCH_PACKET\n'):
            start,end=nodes[path];cstart,_=nodes[(*path,'content')];subranges=[]
            prefix,packet=value.split('\n',1);parts=spans(packet)
            for key,group in (('history_trace','trace'),('recent_round','recent_feedback'),('tool_directory','tool_directory')):
                pointer=('research',key)
                if pointer in parts:
                    a,b=parts[pointer];a+=len(prefix)+1;b+=len(prefix)+1
                    raw=lambda pos:len(json.dumps(value[:pos],ensure_ascii=False)[1:-1])
                    subranges.append((cstart+1+raw(a),cstart+1+raw(b),group))
            pointer=('research','research_state','pending_feedback')
            if pointer in parts:
                a,b=parts[pointer];a+=len(prefix)+1;b+=len(prefix)+1
                subranges.append((cstart+1+len(json.dumps(value[:a],ensure_ascii=False)[1:-1]),
                    cstart+1+len(json.dumps(value[:b],ensure_ascii=False)[1:-1]),'recent_feedback'))
            cursor=start
            for a,b,group in sorted(subranges):
                if a>cursor:ranges.append((cursor,a,'l0_current_state'))
                ranges.append((a,b,group));cursor=b
            if cursor<end:ranges.append((cursor,end,'l0_current_state'))
        else:add(path,'recent_feedback' if i in last_tools else 'sdk_history')
    groups={};cursor=0;tokenizer=official_tokenizer()
    for a,b,group in sorted(ranges):
        if a<cursor:raise AssertionError('Overlapping request partitions')
        if a>cursor:groups.setdefault('framing_and_other',[]).append(text[cursor:a])
        groups.setdefault(group,[]).append(text[a:b]);cursor=b
    groups.setdefault('framing_and_other',[]).append(text[cursor:])
    stats={k:dict(bytes=sum(len(x.encode()) for x in values),
        fragment_token_estimate=sum(len(tokenizer.encode(x,add_special_tokens=False).ids) for x in values))
        for k,values in groups.items()}
    assert sum(x['bytes'] for x in stats.values())==len(content)
    return dict(bytes=len(content),local_input_estimate=len(tokenizer.encode(text,add_special_tokens=False).ids),
        tool_names=[t['function']['name'] for t in wire.get('tools',[])],parts=stats)


def saved_requests():
    with sqlite3.connect(SOURCE.as_uri()+'?mode=ro',uri=True) as db:
        def artifact(ref):return json.loads(db.execute('SELECT body FROM artifacts WHERE id=?',(ref['artifact_id'],)).fetchone()[0])
        events=[json.loads(r[0]) for r in db.execute('SELECT body FROM events WHERE run_id=? ORDER BY seq',('main-off-saved-c3-v5-20261028',))]
        responses={}
        for e in events:
            if e['kind']=='r3_response':responses[e['request_id']]=artifact(e['outputs'][0])
        rows=[];bodies=[]
        for e in events:
            if e['kind']!='r3_request':continue
            meta=artifact(e['outputs'][0]);wire=artifact(meta['request'])
            # Store retains the original parsed request. Re-serialize through
            # httpx, matching its production JSON encoder; key order is normalized.
            content=httpx.Request('POST','https://offline.invalid',json=wire).content
            assert len(content)==meta['input_bytes']
            response=artifact(responses[e['request_id']]['body'])
            rows.append(dict(request_id=e['request_id'],request=meta['request'],**measure(content),
                provider_usage=responses[e['request_id']]['usage']))
            bodies.append(response)
    return rows,bodies


async def workflow(bodies,mode):
    run_id='rr-offline-'+mode+'-'+uuid4().hex[:8]
    recent=mode!='original';ondemand=mode=='routed'
    h=probe.prepare(ROOT/'runs/research'/run_id,run_id,analysis_interface='bound_scientific_variables_v2',
        conversation_policy=dict(version='recent_round_trace_v1',trace_limit=8) if recent else None,
        tool_schema_policy=dict(version='on_demand_tools_v1') if ondemand else None)
    # Replay one complete read/diagnose/analysis/feedback path from the same v5
    # source state, within the unchanged eight-call isolated fixture allowance.
    script=[]
    for n in (0,1,5,6,7):
        if ondemand and n in (0,5,7):
            tool='evidence_read' if n==0 else 'research_plan'
            payload=dict(tool=tool)
            if n!=0:payload['action']='diagnose' if n==5 else 'stop'
            script.append(dict(choices=[dict(index=0,finish_reason='tool_calls',message=dict(role='assistant',content=None,
                tool_calls=[dict(id='offline-route-'+str(n),type='function',function=dict(name='research_route',arguments=json.dumps(payload)))]))]))
        script.append(deepcopy(bodies[n]))
    wires=[];route_output_estimate=0;verified_facts=None;recall_sample=None
    def response(request):
        nonlocal route_output_estimate,verified_facts,recall_sample
        index=len(wires);wire=json.loads(request.content)
        if index>=len(script):raise AssertionError('Unexpected offline request')
        body=deepcopy(script[index]);calls=body['choices'][0]['message'].get('tool_calls',[])
        stage='tool_selection' if calls and calls[0]['function']['name']=='research_route' else 'tool_execution'
        if stage=='tool_selection':
            route_output_estimate+=len(official_tokenizer().encode(json.dumps(body['choices'][0]['message']),add_special_tokens=False).ids)
        if index==0:stage='ordinary_decision'
        packet=json.loads(wire['messages'][-1]['content'].split('\n',1)[1])['research']
        if verified_facts is None:verified_facts=packet['verified_facts']
        if calls and calls[0]['function']['name']=='research_analysis':
            trace=research_action_trace(h,limit=None);before_reads=read_coverage(h)
            recall_sample=research_recall(h,dict(step=trace['recent'][-1]['step'],view='details'))
            assert before_reads==read_coverage(h)
        wires.append(dict(stage=stage,**measure(request.content)))
        body.update(id='explicit-offline-replay-'+str(index),object='chat.completion',created=1,model=wire['model'],
            usage=dict(prompt_tokens=0,completion_tokens=0,total_tokens=0))
        return httpx.Response(200,json=body)
    with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline-mock-only'}):
        counts=await probe.run(h,httpx.MockTransport(response),max_requests=len(script))
    trace=research_action_trace(h,limit=None)
    assert len(wires)==len(script)
    if ondemand:
        assert wires[0]['tool_names']==['research_route']
        assert all(len(set(w['tool_names'])-{'research_route'})<=1 for w in wires)
        assert any('research_analysis' in w['tool_names'] for w in wires)
    assert h.store.remaining()['used']['backend_solves']==h.store.remaining()['used']['worker_calls']==0
    total=sum(w['local_input_estimate'] for w in wires)
    output_scenario=sum(bodies[n]['usage']['completion_tokens'] for n in (0,1,5,6,7))+route_output_estimate
    assert recall_sample is not None
    return dict(store=str(h.store.root),requests=len(wires),wires=wires,total_local_input_estimate=total,
        verified_facts=verified_facts,recall_sample=recall_sample,
        fixed_response_output_scenario_tokens=output_scenario,scripted_route_output_estimate=route_output_estimate,
        provider_requests_sent=0,mock_requests=counts['conversation'],
        input_cost_usd_scenario=dict(all_cache_miss_off_peak=total*.15/1e6,all_cache_miss_peak=total*.30/1e6,
            all_cache_hit_off_peak=total*.003/1e6,all_cache_hit_peak=total*.006/1e6),
        combined_cost_usd_fixed_response_scenario=dict(all_cache_miss_off_peak=(total*.15+output_scenario*.60)/1e6,
            all_cache_miss_peak=(total*.30+output_scenario*1.20)/1e6),
        trace=[trace_entry(r) for r in trace['recent']],lifecycle=state(h)['probe_lifecycle'])


def main():
    before=hashlib.sha256(SOURCE.read_bytes()).hexdigest();saved,bodies=saved_requests()
    result=dict(version='recent_round_wire_audit_v1',source_database_sha256=before,
        source='Read-only original v5 requests and replies; workflows use the same frozen pre-decision state.',
        tokenizer_sha256=TOKENIZER_SHA256,
        measurement='Exact serialized byte partitions. Whole-request pinned tokenizer estimates are local, not Provider billing. Fragment token counts have BPE boundary effects and are not additive API prompt tokens.',
        saved_v5=saved,workflows={mode:asyncio.run(workflow(bodies,mode)) for mode in ('original','recent','routed')},
        pricing=dict(source='https://api-docs.deepseek.com/quick_start/pricing/',checked='2026-10-28',
            unit='USD per million tokens',flash_input_miss_off_peak=.15,flash_input_miss_peak=.30,
            flash_input_hit_off_peak=.003,flash_input_hit_peak=.006,output_off_peak=.60,output_peak=1.20,
            interpretation='Scenario input costs only. Cache behavior, new model output and latency are unknown; mock usage is zero and not an API invoice.'))
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==before
    facts=[v['verified_facts'] for v in result['workflows'].values()]
    assert all(f==facts[0] for f in facts)
    DEST.parent.mkdir(parents=True,exist_ok=True);DEST.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:dict(requests=v['requests'],tokens=v['total_local_input_estimate']) for k,v in result['workflows'].items()}))


if __name__=='__main__':main()
