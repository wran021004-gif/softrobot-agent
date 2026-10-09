"""Focused live-boundary checks with controlled transport, never paid probes."""
import asyncio
from copy import deepcopy
import json
import unittest
from uuid import uuid4

import httpx

from tools.strands_pilot import ROOT, initialize, completion, fixture_decision, TARGET, InvestigationDispatcher
from tools.strands_pilot_r3 import (LiveBoundary, build_live, pilot, pending, received, reopen_live,
    live_scope, CALLER)
from tools.platform_store import zero


class LiveBoundaryTests(unittest.TestCase):
    def host(self):
        suffix=uuid4().hex[:12]
        return initialize(ROOT/'runs'/('strands-pilot-r3-test-'+suffix),'strands-pilot-r3-test-'+suffix,
            authorization='OFFLINE R3 transport substitute; no provider access')

    def wire(self,summary=False):
        return dict(model='deepseek-flash',thinking={'type':'enabled'},reasoning_effort='high',
            max_tokens=32768,stream=False,messages=[{'role':'user','content':'Summarize evidence' if summary else 'Inspect evidence'}],
            tools=[] if summary else [{'type':'function','function':{'name':'read_original'}}])

    def send(self,boundary,wire):
        return asyncio.run(boundary.handle_async_request(httpx.Request('POST','https://api.deepseek.com/chat/completions',json=wire)))

    def test_success_summary_common_budget_and_saved_replay(self):
        host=self.host();sends=[]
        def provider(request):
            sends.append(request)
            return httpx.Response(200,json=completion(text='Exact saved evidence summary'),request=request)
        boundary=LiveBoundary(host,httpx.MockTransport(provider))
        first=self.send(boundary,self.wire())
        self.assertEqual(host.store.remaining()['used']['model_calls'],1)
        # Conversion/report failure: exact request reuses received bytes and charge.
        reopened=reopen_live(host.store.root.parent,host.run_id)
        recovered=LiveBoundary(reopened,httpx.MockTransport(provider))
        replay=self.send(recovered,self.wire())
        self.assertEqual(first.content,replay.content);self.assertEqual(len(sends),1)
        with self.assertRaisesRegex(ValueError,'SAVED_RESPONSE_MUST_BE_PROCESSED_FIRST'):
            self.send(recovered,self.wire(True))
        recovered.consumed();self.send(recovered,self.wire(True));recovered.consumed()
        self.assertEqual(host.store.remaining()['used']['model_calls'],2)
        events=host.store.events(host.run_id)
        purposes=[host.store.artifact(e['outputs'][0])['purpose'] for e in events if e['kind']=='r3_request']
        self.assertEqual(purposes,['conversation','summarization'])
        for event in [e for e in events if e['kind']=='r3_response' and e['status']=='metadata_saved']:
            response=host.store.artifact(event['outputs'][0])
            self.assertEqual(json.loads(host.store.artifact(response['body'],raw=True))['usage'],response['usage'])
            self.assertIsNone(response['reasoning_tokens']);self.assertIsNone(response['money'])
        # Controlled capacity reservation, not simulated provider usage: both
        # main and auxiliary dispatch must obey the existing common ceiling.
        host.store.reserve(host.run_id,'offline-capacity-reservation','capacity','offline-test',
            {**zero(),'model_calls':38},kind='offline_capacity_fixture')
        for summary in (False,True):
            with self.assertRaisesRegex(ValueError,'BUDGET_EXHAUSTED'):
                self.send(recovered,self.wire(summary))
        self.assertEqual(len(sends),2)

    def test_confirmed_error_has_raw_response_and_single_charge(self):
        host=self.host();body=b'{"error":{"message":"Controlled confirmed rejection"}}'
        boundary=LiveBoundary(host,httpx.MockTransport(lambda r:httpx.Response(400,content=body,request=r)))
        response=self.send(boundary,self.wire())
        row=host.store.lookup(host.run_id,boundary.last_request)
        self.assertEqual(response.status_code,400);self.assertEqual(row['status'],'failed')
        saved=received(host,row['request_id'])
        self.assertEqual(host.store.artifact(saved['body'],raw=True),body)
        self.assertEqual(host.store.remaining()['used']['model_calls'],1);self.assertFalse(pending(host))

    def test_unknown_retains_reservation_across_restart_and_blocks_summary(self):
        host=self.host();sends=[]
        def timeout(request):
            sends.append(request);raise httpx.ReadTimeout('Controlled ambiguity',request=request)
        boundary=LiveBoundary(host,httpx.MockTransport(timeout));deadline=pilot(host)['deadline_unix']
        with self.assertRaises(httpx.ReadTimeout):self.send(boundary,self.wire())
        host=reopen_live(host.store.root.parent,host.run_id)
        self.assertEqual(pending(host)[0]['status'],'unknown')
        self.assertEqual(host.store.remaining()['used']['model_calls'],1)
        self.assertEqual(host.store.remaining()['occupied'],{'provider_request':1})
        for summary in (False,True):
            with self.assertRaisesRegex(ValueError,'UNCONFIRMED_ATTEMPT_BLOCKS_SEND'):
                self.send(LiveBoundary(host,httpx.MockTransport(timeout)),self.wire(summary))
        self.assertEqual(len(sends),1);self.assertEqual(pilot(host)['deadline_unix'],deadline)

    def test_assembled_harness_preserves_history_and_native_submission(self):
        host=self.host();p=pilot(host);responses=[
            completion('read_original',dict(reference=p['sources'][0],pointer='/metrics/0'),call_id='live-metric'),
            completion('read_original',dict(reference=p['sources'][0],pointer='/source_execution_id',limit=64),call_id='live-scope'),
            completion('submit_result',dict(decision=fixture_decision(host),revision=1),call_id='live-submit'),
            completion('get_receipt',dict(investigation_id=TARGET,revision=1),call_id='live-receipt'),
            completion(text='Native fixture submission complete.')]
        queue=iter(responses);wires=[]
        def provider(request):
            wires.append(json.loads(request.content));return httpx.Response(200,json=next(queue),request=request)
        with live_scope() as counts:
            agent=build_live(host,httpx.MockTransport(provider),key='offline-no-secret')
            agent('Controlled native tool protocol fixture.')
        self.assertTrue(all(v==0 for v in counts.values()))
        receipt=InvestigationDispatcher(host).disposition_receipt(TARGET,1)
        self.assertEqual(receipt['execution_status'],'completed')
        self.assertEqual(host.store.remaining()['used']['model_calls'],5)
        self.assertEqual(host.store.remaining()['used']['tool_calls'],4)
        assistant=next(m for m in wires[-1]['messages'] if m.get('tool_calls',[{}])[0].get('id')=='live-metric')
        self.assertIn('reasoning_content',assistant)
        self.assertTrue(any(m.get('tool_call_id')=='live-metric' for m in wires[-1]['messages']))
        self.assertIsNone(pilot(host).get('unconsumed_response'))
        self.assertEqual(len([e for e in host.store.events(host.run_id) if e['kind']=='principal_disposition']),1)
        schema=next(t for t in wires[0]['tools'] if t['function']['name']=='submit_result')['function']['parameters']
        encoded=json.dumps(schema)
        self.assertIn('supporting_facts',encoded);self.assertIn('scope',encoded);self.assertIn('maxItems',encoded)

    def test_framework_summary_uses_live_boundary_and_saved_configuration(self):
        host=self.host()
        # Unique actual saved source text, no synthetic context-filling copies.
        original=json.dumps(host.store.artifact(pilot(host)['sources'][2]),indent=2)
        queue=iter([completion(text=original),completion(text='Continue'),completion(text='Source-bound summary fixture'),completion(text='Continue after summary')])
        wires=[]
        def provider(request):
            wires.append(json.loads(request.content));return httpx.Response(200,json=next(queue),request=request)
        with live_scope():
            agent=build_live(host,httpx.MockTransport(provider),key='offline-no-secret')
            agent('Inspect the saved joint record.')
            agent('Continue after the saved joint review.')
            agent('Prepare to persist and restart.')
        self.assertEqual(len(wires),4)
        self.assertFalse(wires[2].get('tools'));self.assertIn('[Summarized:',str(agent.messages))
        self.assertEqual(host.store.remaining()['used']['model_calls'],4)
        self.assertEqual(wires[2]['thinking'],{'type':'enabled'})
        self.assertEqual(wires[2]['model'],'deepseek-flash')

    def test_sdk_confirmed_error_does_not_retry(self):
        host=self.host();sends=[]
        def provider(request):
            sends.append(request);return httpx.Response(400,json={'error':{'message':'Controlled error'}},request=request)
        with live_scope():
            agent=build_live(host,httpx.MockTransport(provider),key='offline-no-secret')
            with self.assertRaises(Exception):agent('Inspect evidence.')
        self.assertEqual(len(sends),1);self.assertEqual(host.store.remaining()['used']['model_calls'],1)

    def test_batched_native_reads_serialize_existing_host_lock(self):
        host=self.host();p=pilot(host)
        first=completion('read_original',dict(reference=p['sources'][0],pointer='/metrics/0'),call_id='batch-eval')
        second=completion('read_original',dict(reference=p['sources'][1],pointer='/detail/sampled_settling'),call_id='batch-hold')
        first['choices'][0]['message']['tool_calls']+=second['choices'][0]['message']['tool_calls']
        queue=iter([first,completion(text='Both original pages inspected.')])
        with live_scope():
            agent=build_live(host,httpx.MockTransport(lambda r:httpx.Response(200,json=next(queue),request=r)),key='offline-no-secret')
            agent('Inspect these two original sources.')
        results=[host.store.artifact(e['outputs'][0])['result'] for e in host.store.events(host.run_id) if e['kind']=='r3_tool_result']
        self.assertEqual(len(results),2);self.assertTrue(all(r['status']=='success' for r in results))
        self.assertEqual(host.store.remaining()['used']['tool_calls'],2)


if __name__=='__main__':unittest.main()
