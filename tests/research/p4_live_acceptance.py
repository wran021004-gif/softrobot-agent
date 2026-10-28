"""Explicit P4 operator commands over the existing Provider, Harness and Store.

No command retries. Validation is read-only, consumes the same eight-call ledger
as Main/Reporter, and must complete before the autonomous scientific invocation.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import httpx
from jsonschema import validate
from tools.platform_host import Host
from tools.research.config import ROOT
from tools.research.state import state, guard, update
from tools.research.provider import LiveBoundary, credential, request_settings, record
from tools.state_io import atomic_json

STUDY='p4-m5-none-20261029-a01'
TOKEN='p4-live-readonly-20261029'
TOOL=dict(type='function',function=dict(name='p4_echo',
    description='Return the supplied token exactly. This is a read-only engineering protocol probe, not scientific evidence.',
    parameters=dict(type='object',properties=dict(token=dict(type='string')),required=['token'],additionalProperties=False)))


async def validation(host, step):
    guard(host)
    events=host.store.events(host.run_id)
    if any(e['kind']=='p4_validation_attempt' and host.store.artifact(e['outputs'][0])['step']==step for e in events):
        raise ValueError('P4_VALIDATION_ALREADY_ATTEMPTED_NO_RETRY')
    record(host,'p4_validation_attempt',dict(step=step,real_inference=True))
    messages=[dict(role='system',content='Verify the local function protocol. Use the offered function when requested. Never claim scientific evidence.'),
        dict(role='user',content='Call p4_echo with token '+TOKEN+'. Do not simulate the tool result.')]
    if step==2:
        prior=next(host.store.artifact(e['outputs'][0]) for e in events if e['kind']=='p4_validation_result'
            and host.store.artifact(e['outputs'][0])['step']==1)
        if not prior['passed']:raise ValueError('P4_TOOL_CALL_NOT_OBSERVED_STOP')
        messages.extend([prior['message'],dict(role='tool',tool_call_id=prior['call_id'],content=json.dumps(prior['tool_result'])),
            dict(role='user',content='State the exact returned token and whether the function succeeded. Produce a concise text answer; no further tool call is needed.')])
    p=state(host)['pilot']['provider'];boundary=LiveBoundary(host,max_model_calls=8)
    boundary.purpose='provider_validation'
    wire=dict(**request_settings(p),messages=messages,**(dict(tools=[TOOL],tool_choice='auto') if step==1 else {}))
    async with httpx.AsyncClient(transport=boundary,timeout=p['timeout_s'],follow_redirects=False) as client:
        response=await client.post(p['base_url'].rstrip('/')+'/chat/completions',json=wire,
            headers={'Authorization':'Bearer '+credential(p,state(host)['spec']['runtime']['credentials_reference'])})
        response.raise_for_status();raw=response.json();message=raw['choices'][0]['message']
        if step==1:
            calls=message.get('tool_calls',[]);passed=len(calls)==1 and calls[0]['function']['name']=='p4_echo'
            result=dict(step=step,passed=passed,message=message,usage=raw.get('usage'),scientific_evidence=False)
            if passed:
                args=json.loads(calls[0]['function']['arguments']);validate(args,TOOL['function']['parameters'])
                result.update(passed=args['token']==TOKEN,call_id=calls[0]['id'],arguments=args,
                    tool_result=dict(token=args['token'],status='success',scientific_evidence=False))
        else:
            result=dict(step=step,passed=TOKEN in (message.get('content') or '') and not message.get('tool_calls'),
                message=message,usage=raw.get('usage'),scientific_evidence=False,
                returned_call_id=prior['call_id'],returned_result=prior['tool_result'])
        record(host,'p4_validation_result',result);boundary.consumed()
        if step==2 and result['passed']:
            pilot={**state(host)['pilot'],'session_handoff_live_admitted':True,
                'session_handoff_boundary':'request_feedback'}
            update(host,pilot=pilot)
        print(json.dumps(result))
        if not result['passed']:raise ValueError('P4_PROTOCOL_VALIDATION_NOT_PASSED_STOP')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['validate1','validate2','research','inspect'])
    parser.add_argument('--requests',type=int,default=2);args=parser.parse_args()
    host=Host(ROOT/'runs/research'/STUDY,STUDY,actor='unified-research')
    for key,value in state(host)['spec']['runtime']['threads'].items():os.environ[key]=value
    if args.command.startswith('validate'):
        asyncio.run(validation(host,int(args.command[-1])))
    elif args.command=='research':
        results=[host.store.artifact(e['outputs'][0]) for e in host.store.events(STUDY) if e['kind']=='p4_validation_result']
        if {r['step'] for r in results if r['passed']}!={1,2}:raise ValueError('REAL_PROVIDER_TOOL_LOOP_REQUIRED')
        from tools.research.agent import converse
        asyncio.run(converse(host,max_new_provider_requests=args.requests,pause_after_completed_invocations=1))
    s=state(host)
    summary=dict(study_id=STUDY,research_status=s['research_status'],ledger=host.store.remaining(),
        candidates=list(s['candidates'].values()),plans=s['plans'],analysis=s.get('analysis_results',[]),
        physical=s.get('physical_replays',[]),final_disposition=s.get('final_disposition'))
    atomic_json(host.store.root/'p4_progress.json',summary);print(json.dumps(summary))


if __name__=='__main__':main()
