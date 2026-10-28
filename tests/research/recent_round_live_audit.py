"""Read-only live-wire export plus verified SDK restore; HTTP is forbidden."""
import asyncio
import json
import os
from unittest.mock import patch
import httpx
from tools.platform_host import Host
from tools.research import agent, reporter
from tools.research.config import ROOT
from tools.research.research_context import research_action_trace, trace_entry
from tools.research.session_handoff import pending_feedback_delivery
from tools.research.state import state
from tests.research.main_off_live_probe import safe_guard
from tests.research.recent_round_wire_audit import measure

PROBE='main-off-recent-trace-v6-20261028'
DEST=ROOT/'evidence/recent_round_trace/live_validation.json'


def main():
    h=Host(ROOT/'runs/research'/PROBE,PROBE,actor='probe-live-audit')
    before=h.store.remaining();events=h.store.events(PROBE);requests=[];feedback=[];choices=[]
    receptions={}
    for e in events:
        if e['kind']=='r3_response':receptions[e['request_id']]=h.store.artifact(e['outputs'][0])
    for e in events:
        if e['kind']=='r3_request':
            meta=h.store.artifact(e['outputs'][0]);wire=h.store.artifact(meta['request']);response=receptions[e['request_id']]
            body=json.loads(h.store.artifact(response['body'],raw=True))
            item=dict(request_id=e['request_id'],timestamp=e['timestamp'],request=meta['request'],response=response['body'],
                **measure(httpx.Request('POST','https://offline.invalid',json=wire).content),
                provider_usage=response['usage'],finish_reasons=response['finish_reasons'],elapsed_s=response['elapsed_s'])
            assert item['bytes']==meta['input_bytes']
            requests.append(item)
            choices.append(dict(request_id=e['request_id'],message=body['choices'][0]['message']))
        elif e['kind']=='model_original_tool_feedback':
            value=h.store.artifact(e['outputs'][0]);use=value['tool_use']
            parsed=json.loads(''.join(b.get('text','') for b in value['result']['content']))
            feedback.append(dict(reference=e['outputs'][0],tool_use=use,status=value['result']['status'],
                feedback={k:parsed[k] for k in ('status','error_code','field','expected','execution_feedback','tool','action','scientific_execution_started') if k in parsed}))
    def forbidden(request):raise AssertionError('Audit/restore must never send HTTP')
    with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline-restore-only'}),\
            patch('tools.research.core.guard',safe_guard),patch('tools.research.agent.guard',safe_guard),\
            patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(forbidden)):
        asyncio.run(agent.converse(h,restore_only=True))
    assert h.store.remaining()==before
    events=h.store.events(PROBE);restore=h.store.artifact(events[-1]['outputs'][0]);assert not restore['next_request_sent']
    assert not state(h)['pilot'].get('unconsumed_response') and not state(h).get('pending')
    assert before['used']['backend_solves']==before['used']['worker_calls']==0
    totals={k:sum((v['provider_usage'] or {}).get(k,0) for v in requests) for k in
        ('prompt_tokens','completion_tokens','total_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens')}
    cache_price=totals['prompt_cache_hit_tokens']*.003+totals['prompt_cache_miss_tokens']*.15+totals['completion_tokens']*.60
    result=dict(version='recent_round_live_validation_v1',probe_id=PROBE,
        tested_repository_commit='2189a5ce31da2abdd784f463a732da542a79c50d',
        frozen_source_implementation=state(h)['freeze'],
        model=state(h)['pilot']['provider']['model'],thinking=state(h)['pilot']['provider']['thinking'],
        request_limit=8,actual_main_requests=len(requests),actual_reporter_requests=reporter.provider_usage(h).get('reporter',{}).get('requests',0),
        scientific_workers=0,physical_launches=0,automatic_retries=0,requests=requests,provider_totals=totals,
        provider_elapsed_sum_s=sum(v['elapsed_s'] for v in requests),actual_reported_currency_cost=None,
        estimated_currency_usd_at_reported_cache_counts=dict(off_peak=cache_price/1e6,peak=cache_price*2/1e6),
        ledger=before,lifecycle=state(h)['probe_lifecycle'],
        probe_end=[h.store.artifact(e['outputs'][0]) for e in events if e['kind']=='probe_incomplete'],
        handoffs=sum(e['kind']=='session_handoff' and e['status']=='committed' for e in events),
        restore=restore,pending_feedback=pending_feedback_delivery(h),
        trace=[trace_entry(r) for r in research_action_trace(h,limit=None)['recent']],feedback=feedback,
        original_main_choices=choices,
        scope='Actual Provider wires and usage; audit/restore sends zero requests. No mathematical analysis, scientific result, SELECT or formal STOP was accepted. Request 8 was rejected by the harness feedback reserve before ledger/send; this is probe_inconclusive, not an API transport failure or scientific STOP.')
    assert len(requests)==7
    assert requests[0]['tool_names']==['research_route']
    assert all(len(set(r['tool_names'])-{'research_route'})<=1 for r in requests)
    DEST.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(dict(requests=len(requests),totals=totals,handoffs=result['handoffs'],restored=True,lifecycle=result['lifecycle'])))


if __name__=='__main__':main()
