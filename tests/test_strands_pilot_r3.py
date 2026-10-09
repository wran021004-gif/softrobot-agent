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
        queue=iter([first,completion(text='Both original pages inspected.')]);wires=[]
        def provider(request):
            wires.append(json.loads(request.content))
            return httpx.Response(200,json=next(queue),request=request)
        with live_scope():
            agent=build_live(host,httpx.MockTransport(provider),key='offline-no-secret')
            agent('Inspect these two original sources.')
        results=[host.store.artifact(e['outputs'][0])['result'] for e in host.store.events(host.run_id) if e['kind']=='r3_tool_result']
        self.assertEqual(len(results),2);self.assertTrue(all(r['status']=='success' for r in results))
        self.assertEqual(host.store.remaining()['used']['tool_calls'],2)
        events=[e['kind'] for e in host.store.events(host.run_id) if e['kind'] in ('r3_tool_dispatch','r3_tool_result')]
        self.assertEqual(events,['r3_tool_dispatch','r3_tool_result']*2)
        matched={m['tool_call_id']:json.loads(m['content']) for m in wires[1]['messages'] if m['role']=='tool'}
        for call_id,source,pointer in [('batch-eval',p['sources'][0],'/metrics/0'),('batch-hold',p['sources'][1],'/detail/sampled_settling')]:
            self.assertEqual(matched[call_id]['page']['source'],source)
            self.assertEqual(matched[call_id]['page']['pointer'],pointer)

    def test_thirteen_evidence_items_and_real_validation_errors(self):
        host=self.host();p=pilot(host);decision=fixture_decision(host)
        # Distinct original fields provide numerical, identity and structural evidence.
        fields=[]
        def leaves(value,pointer,source):
            if isinstance(value,dict):
                for k,v in value.items():leaves(v,pointer+'/'+k.replace('~','~0').replace('/','~1'),source)
            elif not isinstance(value,list):fields.append((source,pointer,value))
        leaves(host.store.artifact(p['sources'][1])['detail']['sampled_settling'],'/detail/sampled_settling',p['sources'][1])
        leaves(host.store.artifact(p['sources'][2])['detail']['components'],'/detail/components',p['sources'][2])
        selected=fields[:13]
        self.assertEqual(len(selected),13)
        decision['evidence_used']=[dict(statement='Exact original '+ptr,reference=source,pointer=ptr,value=value)
            for source,ptr,value in selected]
        responses=[completion('read_original',dict(reference=p['sources'][0],pointer='/metrics/0')),
            completion('read_original',dict(reference=p['sources'][0],pointer='/source_execution_id',limit=64))]
        responses.extend(completion('read_original',dict(reference=source,pointer=ptr,limit=100),call_id='inspect-'+str(i))
            for i,(source,ptr,_) in enumerate(selected))
        responses.extend([completion('submit_result',dict(decision=decision,revision=1)),completion(text='Done')])
        queue=iter(responses);wires=[]
        def provider(request):
            wires.append(json.loads(request.content));return httpx.Response(200,json=next(queue),request=request)
        with live_scope():build_live(host,httpx.MockTransport(provider),key='offline-no-secret')('Validate thirteen facts')
        dispatcher=InvestigationDispatcher(host);receipt=dispatcher.disposition_receipt(TARGET,1)
        self.assertIsNotNone(receipt)
        self.assertEqual(len(host.store.artifact(receipt['output'])['decision']['evidence_used']),13)
        schema=next(t for t in wires[0]['tools'] if t['function']['name']=='submit_result')['function']['parameters']
        def find_evidence(value):
            if isinstance(value,dict):
                if 'evidence_used' in value.get('properties',{}):
                    self.assertNotIn('maxItems',value['properties']['evidence_used'])
                for v in value.values():find_evidence(v)
            elif isinstance(value,list):
                for v in value:find_evidence(v)
        find_evidence(schema)
        from tools.disposition_facts import SelectedDisposition
        self.assertNotIn('maxItems',SelectedDisposition.model_json_schema()['properties']['evidence_used'])
        for kind in ('path','value','required','identity','scope'):
            bad=deepcopy(decision)
            if kind=='path':bad['evidence_used'][0]['pointer']='/nonexistent'
            if kind=='value':bad['evidence_used'][0]['value']='mismatched original'
            if kind=='required':del bad['reason']
            if kind=='identity':bad['evidence_used'][0]['source_identity']={'candidate_id':'other-candidate'}
            if kind=='scope':bad['adopted_claims'][0]['scope']=[]
            with self.subTest(kind=kind),self.assertRaises(ValueError) as error:
                dispatcher.disposition(bad,validate_only=True)
            self.assertTrue(str(error.exception))

    def test_linked_closeout_restores_without_mutating_stopped_records(self):
        from tools.strands_pilot_closeout import prepare, execute, verify_preservation, preserved_files
        import time
        old=self.host();p=pilot(old)
        queue=iter([completion('read_original',dict(reference=p['sources'][0],pointer='/metrics/0'),call_id='saved-metric'),
            completion('read_original',dict(reference=p['sources'][0],pointer='/source_execution_id',limit=64),call_id='saved-scope'),
            completion(text='Saved source-bound reasoning to continue.')])
        with live_scope():
            build_live(old,httpx.MockTransport(lambda r:httpx.Response(200,json=next(queue),request=r)),key='offline-no-secret')('Saved review')
        # Explicit offline historical-capacity fixture; these are not provider sends.
        old.store.reserve(old.run_id,'offline-historical-capacity','capacity','offline-test',
            {**zero(),'model_calls':37},kind='offline_capacity_fixture')
        with old.store.transaction() as db:
            state=old.store.session(old.run_id,db)['state'];state['pilot'].update(phase='stopped_budget',live_model_requests=40)
            old.store.update_state(db,old.run_id,state)
        before=preserved_files(old.store.root.parent)
        directory=ROOT/'runs'/('strands-pilot-closeout-test-'+uuid4().hex[:12])
        host=prepare(directory,old.store.root.parent,old.run_id,time.time())
        self.assertEqual(host.store.remaining()['limit']['model_calls'],24)
        self.assertEqual(host.store.remaining()['used']['model_calls'],0)
        self.assertEqual(pilot(host)['sources'],p['sources'])
        self.assertEqual(pilot(host)['report'],p['report'])
        queue=iter([completion('submit_result',dict(decision=fixture_decision(host),revision=1),call_id='closeout-submit'),
            completion('get_receipt',dict(investigation_id=TARGET,revision=1),call_id='closeout-receipt'),completion(text='Closed')])
        wires=[]
        def provider(request):
            wires.append(json.loads(request.content));return httpx.Response(200,json=next(queue),request=request)
        receipt=execute(host,transport=httpx.MockTransport(provider),key='offline-no-secret')
        self.assertEqual(receipt['execution_status'],'completed')
        self.assertEqual(host.store.remaining()['used']['model_calls'],3)
        self.assertEqual(pilot(host)['phase'],'submitted')
        from tools.strands_pilot_r3 import audit
        self.assertEqual(audit(host)['formal']['validation_failures'],[])
        self.assertTrue(verify_preservation(host)['original_files_unchanged'])
        self.assertEqual(before,preserved_files(old.store.root.parent))
        self.assertEqual([m['tool_call_id'] for m in wires[0]['messages'] if m['role']=='tool'],['saved-metric','saved-scope'])
        self.assertIn('no item-count cap',wires[0]['messages'][0]['content'])
        with self.assertRaisesRegex(ValueError,'CLOSEOUT_EXISTS'):
            prepare(directory,old.store.root.parent,old.run_id,time.time())

    def test_saved_failed_thirteen_item_native_arguments_keep_value_checks(self):
        from tools.research_investigations import PrincipalDisposition, SourceFact
        from pydantic import ValidationError
        saved=json.loads((ROOT/'evidence/strands_runtime_pilot_r3_20261009/raw_archive.json').read_text(encoding='utf8'))
        submissions=[saved['artifacts'][e['outputs'][0]['artifact_id']]['tool_use']['input']['decision']
            for e in saved['events'] if e['kind']=='r3_tool_result'
            and saved['artifacts'][e['outputs'][0]['artifact_id']]['tool_use']['name']=='submit_result']
        count_valid=0
        for decision in submissions:
            if len(decision['evidence_used'])!=13:continue
            try:PrincipalDisposition.model_validate(decision);count_valid+=1
            except ValidationError as exc:
                self.assertFalse(any(e['loc']==('evidence_used',) and e['type']=='too_long' for e in exc.errors()))
        self.assertGreater(count_valid,0)
        # Replay the actual partial-object defect against the unchanged fact validator.
        bad=next(f for d in submissions for f in d['evidence_used']
            if f['pointer']=='/detail/motion_summary' and 'scope' not in f['value'])
        host=self.host()
        with self.assertRaisesRegex(ValueError,'SOURCE_VALUE_MISMATCH') as error:
            InvestigationDispatcher(host)._validate_fact(SourceFact.model_validate(bad),'PRINCIPAL')
        self.assertEqual(error.exception.issue['pointer'],'/detail/motion_summary')


if __name__=='__main__':unittest.main()
