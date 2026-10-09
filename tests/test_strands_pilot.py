"""Focused A-G acceptance checks; native tools and real pure business services."""
from copy import deepcopy
from contextlib import ExitStack
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

from tools.strands_pilot import (ROOT,SAVED,TARGET,SOURCE_IDS,initialize,reopen,build_harness,
    normal_responses,fixture_decision,completion,offline_scope,InvestigationDispatcher)
from tools.state_io import atomic_json,read
from tools.platform_store import encode

RESULTS={}
RUN_ROOT=None


def requests(host):
    return [host.store.artifact(e['outputs'][0]) for e in host.store.events(host.run_id) if e['kind']=='fixture_request']


def tool_results(wire):
    return [m for m in wire['messages'] if m['role']=='tool']


class StrandsPilotTests(unittest.TestCase):
    def setUp(self):
        self.scope=ExitStack();self.addCleanup(self.scope.close)
        self.counters=self.scope.enter_context(offline_scope())
        root=RUN_ROOT or ROOT/'runs'/('strands-pilot-tests-'+uuid4().hex[:8])
        self.directory=root/self._testMethodName
        self.activity='strands-pilot-'+uuid4().hex[:12]

    def host(self,ceiling=32):return initialize(self.directory,self.activity,ceiling)

    def capture(self,name,host,**details):
        state=host.store.session(host.run_id)['state'];pilot=state['pilot']
        RESULTS[name]=dict(passed=True,activity_id=host.run_id,
            receipt=InvestigationDispatcher(host).disposition_receipt(TARGET,1),
            accounting=host.store.remaining(),fixture_requests=pilot['fixture_requests'],
            fixture_tokens=pilot['fixture_tokens'],real_provider_tokens=None,real_cost=None,
            deadline_unix=pilot['deadline_unix'],scope_invocations=deepcopy(self.counters),**details)

    def child(self,action,fault=None):
        command=[sys.executable,'-m','tools.strands_pilot',action,'--directory',str(self.directory),'--activity',self.activity]
        if fault:command+=['--fault',fault]
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=45)
        return result

    def test_A_normal(self):
        host=self.host();validated=[]
        original=InvestigationDispatcher._validate_fact
        def validate(service,fact,label):
            validated.append(label);return original(service,fact,label)
        with patch.object(InvestigationDispatcher,'_validate_fact',new=validate):
            agent=build_harness(host,normal_responses(host));agent('Review the saved case and submit the formal decision.')
        receipt=InvestigationDispatcher(host).disposition_receipt(TARGET,1)
        self.assertEqual(receipt['execution_status'],'completed');self.assertGreaterEqual(len(validated),2)
        record=host.store.artifact(receipt['output'])
        self.assertTrue(record['independently_inspected']);self.assertEqual(record['decision'],
            __import__('tools.research_investigations',fromlist=['PrincipalDisposition']).PrincipalDisposition.model_validate(fixture_decision(host)).model_dump(mode='json'))
        joint=host.store.artifact(dict(artifact_id=SOURCE_IDS[2],media_type='application/json'))['detail']
        components=joint['components']
        self.assertAlmostEqual(components['evaluator:task_bound']['value'],0.00313144378856093,places=16)
        self.assertAlmostEqual(components['holding_position']['value'],0.0033622899352609,places=16)
        self.assertAlmostEqual(components['holding_speed']['value'],0.0268176708469683,places=16)
        self.assertEqual([components[k]['passed'] for k in ('evaluator:task_bound','holding_position','holding_speed')],[True,True,False])
        self.assertEqual([components[k]['unit'] for k in ('evaluator:task_bound','holding_position','holding_speed')],['m','m','m/s'])
        self.assertEqual(joint['status'],'valid_failure');self.assertFalse(joint['accepted'])
        self.assertEqual(joint['evidence_binding']['evaluation']['artifact_id'],SOURCE_IDS[0])
        self.assertEqual(joint['evidence_binding']['profile']['artifact_id'],SOURCE_IDS[1])
        outgoing=requests(host);last=outgoing[-1]
        self.assertEqual(len(outgoing),9);self.assertEqual(last['model'],'deepseek-flash')
        self.assertEqual(last['thinking'],dict(type='enabled'));self.assertEqual(last['reasoning_effort'],'high')
        self.assertEqual(last['max_tokens'],32768);self.assertNotIn('temperature',last)
        assistant=next(m for m in last['messages'] if m.get('tool_calls',[{}])[0].get('id')=='discover-1')
        self.assertEqual(assistant['content'][0]['text'],'Inspect source discovery')
        self.assertEqual(assistant['reasoning_content'],'Controlled reasoning preserved across native tool turns.')
        self.assertTrue(any(m.get('tool_call_id')=='discover-1' for m in last['messages']))
        config=read(self.directory/'configuration.json')
        self.assertEqual(config['registered_tools'],['discover_evidence','get_receipt','read_original','retrieve_context','submit_result'])
        self.capture('A',host,validator_invocations=len(validated),frozen_components=components,
            provider=last | {'messages':None,'tools':None},registered_tools=config['registered_tools'],
            protocol_sample=assistant,pagination=next(json.loads(m['content'])['page'] for m in tool_results(last) if m['tool_call_id']=='discover-1'))

    def test_B_correction(self):
        host=self.host();build_harness(host,normal_responses(host,correction=True))('Submit a source-bound principal decision.')
        wire=requests(host)[-1];feedback=next(m['content'] for m in tool_results(wire) if m['tool_call_id']=='invalid-submit')
        self.assertIn('SOURCE_VALUE',feedback)
        receipt=InvestigationDispatcher(host).disposition_receipt(TARGET,1);self.assertIsNotNone(receipt)
        self.assertEqual(host.store.remaining()['used']['model_calls'],10)
        decisions=[e for e in host.store.events(host.run_id) if e['kind']=='principal_disposition']
        self.assertEqual(len(decisions),1)
        self.capture('B',host,validator_feedback=json.loads(feedback),business_effects=len(decisions))

    def test_A_saved_provider_response(self):
        """Replay a real archived response through the pinned provider and Harness.

        Its historical tool name is intentionally unavailable. A tool error is
        expected; this protocol-only replay never counts as a formal submission.
        """
        bundle=read(SAVED/'coordinated_bundle.json')
        event=next(e for e in bundle['events'] if e['kind']=='investigation_provider_response')
        source=event['outputs'][0];response=deepcopy(bundle['artifacts'][source['artifact_id']])
        message=response['choices'][0]['message'];self.assertTrue(message.get('reasoning_content'))
        self.assertTrue(message.get('tool_calls'))
        host=self.host();agent=build_harness(host,[response,completion(text='Archived protocol replay complete.')])
        agent('Replay the archived transport response as a controlled protocol fixture.')
        outgoing=requests(host)[-1]
        restored=next(m for m in outgoing['messages'] if m.get('tool_calls',[{}])[0].get('id')==message['tool_calls'][0]['id'])
        self.assertEqual(restored['reasoning_content'],message['reasoning_content'])
        self.assertEqual([c['id'] for c in restored['tool_calls']],[c['id'] for c in message['tool_calls']])
        for actual,original in zip(restored['tool_calls'],message['tool_calls']):
            self.assertEqual(actual['function']['name'],original['function']['name'])
            self.assertEqual(json.loads(actual['function']['arguments']),json.loads(original['function']['arguments']))
        if message['content'] is None:self.assertIsNone(restored['content'])
        else:self.assertEqual(restored['content'][0]['text'],message['content'])
        self.assertTrue(any(m.get('tool_call_id')==message['tool_calls'][0]['id'] for m in outgoing['messages']))
        self.assertIsNone(InvestigationDispatcher(host).disposition_receipt(TARGET,1))
        self.capture('provider_saved',host,source_response=source,original_reasoning_characters=len(message['reasoning_content']),
            original_tool_ids=[c['id'] for c in message['tool_calls']],formal_submission=False,
            meaning='Historical usage replay is simulated usage here; no live provider request.')

    def test_C_process_read(self):
        stopped=self.child('start','read');self.assertEqual(stopped.returncode,73,stopped.stderr)
        host=reopen(self.directory,self.activity);before=host.store.session(host.run_id)['state']['pilot']
        self.assertEqual(before['fixture_requests'],6)
        session_files=list((self.directory/'sessions').rglob('*latest*'));self.assertTrue(session_files)
        resumed=self.child('resume');self.assertEqual(resumed.returncode,0,resumed.stderr)
        host=reopen(self.directory,self.activity);self.assertIsNotNone(InvestigationDispatcher(host).disposition_receipt(TARGET,1))
        self.assertEqual(host.store.remaining()['used']['model_calls'],9)
        self.assertEqual(host.store.session(host.run_id)['state']['pilot']['deadline_unix'],before['deadline_unix'])
        wire=requests(host)[6]
        self.assertTrue(any(m.get('tool_call_id')=='metric-read' for m in wire['messages']))
        self.assertTrue(any(m.get('reasoning_content') for m in wire['messages']))
        self.capture('C',host,termination_code=stopped.returncode,new_process=True,requests_before_restart=6,
            restored_tool_ids=[m['tool_call_id'] for m in tool_results(wire)])

    def test_D_process_submit(self):
        stopped=self.child('start','submit');self.assertEqual(stopped.returncode,74,stopped.stderr)
        host=reopen(self.directory,self.activity);dispatcher=InvestigationDispatcher(host)
        receipt=dispatcher.disposition_receipt(TARGET,1);self.assertIsNotNone(receipt)
        before=host.store.remaining();resumed=self.child('resume');self.assertEqual(resumed.returncode,0,resumed.stderr)
        host=reopen(self.directory,self.activity);dispatcher=InvestigationDispatcher(host)
        self.assertEqual(dispatcher.disposition_receipt(TARGET,1),receipt)
        decision=fixture_decision(host)
        self.assertEqual(dispatcher.submit_disposition(decision,1),receipt)
        different=deepcopy(decision);different['reason']='Different delivered judgment'
        with self.assertRaisesRegex(ValueError,'REVISION_CONFLICT'):dispatcher.submit_disposition(different,1)
        self.assertEqual(len([e for e in host.store.events(host.run_id) if e['kind']=='principal_disposition']),1)
        record=host.store.artifact(receipt['output'])
        self.assertEqual(host.store.session(host.run_id)['state']['historical_investigations'][TARGET]['disposition_record'],receipt['output'])
        # Explicit next revision follows the existing disposition_versions list.
        revised=dispatcher.submit_disposition(different,2)
        node=host.store.session(host.run_id)['state']['historical_investigations'][TARGET]
        self.assertEqual(node['disposition_versions'],[receipt['output']]);self.assertNotEqual(revised['output'],receipt['output'])
        # A failure at sealing must roll back the decision too, retaining escrow.
        from tools.platform_store import Store
        revision_3=deepcopy(different);revision_3['reason']='Explicit third revision'
        with patch.object(Store,'complete',side_effect=RuntimeError('Controlled failure before receipt sealing')):
            with self.assertRaisesRegex(RuntimeError,'before receipt sealing'):dispatcher.submit_disposition(revision_3,3)
        self.assertIsNone(dispatcher.disposition_receipt(TARGET,3))
        self.assertEqual(host.store.session(host.run_id)['state']['historical_investigations'][TARGET]['disposition_record'],revised['output'])
        restored_3=dispatcher.submit_disposition(revision_3,3)
        self.assertEqual(restored_3['execution_status'],'completed')
        self.capture('D',host,termination_code=stopped.returncode,new_process=True,original_receipt=receipt,
            changed_payload_rejected=True,budget_before_restart=before,revision_2_receipt=revised,
            original_record=record,atomic_rollback_verified=True,revision_3_receipt=restored_3)

    def test_E_context(self):
        host=self.host();pilot=host.store.session(host.run_id)['state']['pilot']
        responses=[completion('read_original',dict(reference=pilot['long_material'],limit=16,byte_limit=4096),call_id='long-original'),
            completion(text='Long source page read; original values remain retrievable.'),
            completion(text='Fixture summary retaining the saved source identity, exact values and units.'),
            completion(text='Continue after framework summarization.')]
        agent=build_harness(host,responses,context_test=True)
        agent('Review controlled long evidence. '+'Old context material. '*500)
        agent('Continue the review after the long source reading.')
        wires=requests(host)
        self.assertTrue(any(not wire['tools'] for wire in wires),'Built-in summarizer did not issue a request')
        self.assertTrue(any('[Summarized:' in str(m) for m in agent.messages),'No actual framework summary')
        self.assertTrue(any('[ref:' in str(m) for m in agent.messages),'No actual tool offload')
        stash_files=list((self.directory/'sessions'/'context').rglob('*long-original_0*'))
        self.assertTrue(stash_files,'Original not durably stashed')
        # New interpreter, same activity/session; native framework retrieval.
        command=[sys.executable,'-c',
            "from tools.strands_pilot import *\nwith offline_scope():\n"+
            " h=reopen("+repr(str(self.directory))+","+repr(self.activity)+")\n"+
            " a=build_harness(h,[completion('retrieve_context',dict(reference='long-original_0'),call_id='durable-retrieval'),completion(text='Retrieved original')],context_test=True)\n"+
            " a('Retrieve the offloaded original source page.')\n"]
        recovered=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=45)
        self.assertEqual(recovered.returncode,0,recovered.stderr)
        host=reopen(self.directory,self.activity);last=requests(host)[-1]
        result=next(m for m in tool_results(last) if m['tool_call_id']=='durable-retrieval')
        retrieved=json.loads(json.loads(result['content'])['text'])
        original=retrieved['page']
        self.assertEqual(original,host.store.artifact(retrieved['receipt']['output']))
        self.assertEqual(original['source'],pilot['long_material'])
        for item in original['content']:
            self.assertEqual(item['identity'],'controlled-long-original')
            self.assertEqual(item['value'],0.0268176708469683);self.assertEqual(item['units'],'m/s')
        # Reasoning and paired IDs survive offloading of the tool result.
        assistant=next(m for m in last['messages'] if m.get('tool_calls',[{}])[0].get('id')=='long-original')
        self.assertIn('reasoning_content',assistant)
        self.capture('E',host,new_process=True,retrieved_original=original,
            context_markers=[str(m)[:500] for m in agent.messages if '[Summarized:' in str(m) or '[ref:' in str(m)],
            summarization_requests=sum(not w['tools'] for w in requests(host)))

    def test_F_unknown_exhaustion(self):
        stopped=self.child('start','unresolved');self.assertEqual(stopped.returncode,75,stopped.stderr)
        host=reopen(self.directory,self.activity);pilot=host.store.session(host.run_id)['state']['pilot']
        with host.store.connect(True) as db:rows=[dict(r) for r in db.execute("SELECT * FROM calls WHERE caller='fixture-provider'")]
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['status'],'unknown');self.assertIsNone(rows[0]['receipt'])
        self.assertEqual(host.store.remaining()['remaining']['model_calls'],0)
        agent=build_harness(host,[completion(text='Must not dispatch')],context_test=True)
        with self.assertRaises(Exception):agent('Continue without minting another allowance.')
        host=reopen(self.directory,self.activity)
        rejected=[host.store.artifact(e['outputs'][0]) for e in host.store.events(host.run_id) if e['kind']=='fixture_budget']
        self.assertTrue(any(r['purpose']=='summarization' for r in rejected),rejected)
        self.assertTrue(any(r['purpose']=='conversation' for r in rejected),rejected)
        self.assertEqual(host.store.session(host.run_id)['state']['pilot']['fixture_requests'],1)
        self.assertEqual(host.store.session(host.run_id)['state']['pilot']['deadline_unix'],pilot['deadline_unix'])
        self.assertEqual(host.store.remaining()['used']['model_calls'],1)
        self.capture('F',host,termination_code=stopped.returncode,new_process=True,unresolved_request=rows[0],
            blocked_auxiliary_and_ordinary=rejected)

    def test_G_scope_and_legacy(self):
        sealed={p.name:__import__('hashlib').sha256(p.read_bytes()).hexdigest() for p in SAVED.iterdir() if p.is_file()}
        host=self.host();build_harness(host,normal_responses(host))('Review and submit using only the permitted tools.')
        self.assertTrue(all(n==0 for n in self.counters.values()))
        self.assertEqual(host.store.remaining()['used']['backend_solves'],0)
        self.assertEqual(host.store.session(host.run_id)['state']['turn'],0)
        self.assertEqual(host.store.session(host.run_id)['state']['model_notes'],[])
        self.assertEqual(sealed,{p.name:__import__('hashlib').sha256(p.read_bytes()).hexdigest() for p in SAVED.iterdir() if p.is_file()})
        self.capture('G',host,historical_sha256=sealed,legacy_turn=0,legacy_conversation_notes=0)


def run_scenarios(directory,only=None):
    global RUN_ROOT
    directory=Path(directory).resolve()
    if directory.exists():raise ValueError('NEW_SCENARIO_DIRECTORY_REQUIRED')
    RUN_ROOT=directory;RESULTS.clear()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(StrandsPilotTests)
    if only:suite=unittest.TestSuite(t for t in suite if t._testMethodName.startswith('test_'+only+'_'))
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    output=dict(assessment='offline acceptance passed' if result.wasSuccessful() else 'partially passed',
        passed=result.wasSuccessful(),scenarios=RESULTS,tests_run=result.testsRun,
        failures=[dict(test=str(t),traceback=e) for t,e in [*result.failures,*result.errors]],
        live_model_requests=0,mathematical_solves=0,robot_backend_executions=0,
        meaning='Controlled fixtures and pure business services; no real model compatibility or scientific improvement claim.')
    atomic_json(directory/'results.json',output)
    (directory/'test-log.txt').write_text(stream.getvalue(),encoding='utf-8')
    if not result.wasSuccessful():raise AssertionError(stream.getvalue())
    return output


if __name__=='__main__':unittest.main()
