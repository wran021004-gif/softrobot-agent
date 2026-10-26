"""Three offline checks. Mock Provider decisions/usage are fixtures, not evidence."""
import asyncio
import gc
import json
import os
import shutil
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx
from tests.research import agent_math_decision_probe as probe
from tools.state_io import read


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.out = probe.ROOT / 'runs' / ('probe-fixture-' + uuid4().hex)
        self.summary = self.out.parent / (self.out.name + '-summary.json')
        self.summary_patch = patch.object(probe, 'SUMMARY', self.summary)
        self.summary_patch.start()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.summary_patch.stop()
        gc.collect()
        assert self.out.resolve().parent == (probe.ROOT / 'runs').resolve()
        if self.out.exists():
            shutil.rmtree(self.out)
        self.summary.unlink(missing_ok=True)

    def test_pairs_have_only_evidence_difference_and_no_future_or_rubric(self):
        frozen = probe.freeze(self.out)
        schema = probe.decision_schema()
        self.assertNotIn('revise_selection', schema['properties'])
        self.assertNotIn('revise_selection', schema['$defs']['ResearchDecision']['properties'])
        self.assertFalse(schema['additionalProperties'])
        data = frozen['cases']
        for case in data['cases']:
            for turn in (1, 2):
                b = probe.wire(frozen['provider'], data, case, 'baseline', turn)
                e = probe.wire(frozen['provider'], data, case, 'evidence', turn)
                bp = json.loads(b['messages'][-1]['content'])
                ep = json.loads(e['messages'][-1]['content'])
                self.assertEqual(ep.pop('diagnostic_evidence'), data['cases'][case]['evidence'])
                self.assertEqual(bp.pop('diagnostic_evidence'), [])
                self.assertEqual(bp, ep)
                b['messages'][-1] = e['messages'][-1] = {'content': 'compared above'}
                self.assertEqual(b, e)
                text = json.dumps(probe.wire(frozen['provider'], data, case, 'evidence', turn))
                self.assertNotIn('rubric_offline_only', text)
                self.assertNotIn('sources_offline_only', text)
                self.assertNotIn('.md', text)
                if turn == 1:
                    self.assertNotIn('new_observations', bp)
                    for future in data['cases'][case]['round2']:
                        self.assertNotIn('"' + future['id'] + '"', text)
                    self.assertNotIn('-0.050734', text)
                    self.assertNotIn('0.022752409', text)
        actual = read(probe.ROOT / 'evidence/mujoco_reoptimized_structure/summary.json')['results']
        rows = list(actual.values())
        st = data['cases']['structure']
        self.assertEqual(st['common'][0]['values']['J'], [r['fixed']['signed_maximum_excess'] for r in rows])
        self.assertEqual(st['round2'][0]['raw_values']['J'], [r['warm']['best']['signed_maximum_excess'] for r in rows])

    def test_c3_template_reuses_packet_and_cannot_inherit_prior_approval(self):
        template=probe.ROOT/'tests/research/fixtures/c3_math_decision_template.json'
        frozen=probe.freeze(self.out,cases_path=template)
        self.assertEqual(frozen['request_ceiling'],4)
        self.assertTrue(frozen['authorization'].startswith('PENDING_EXPLICIT_APPROVAL'))
        a=probe.packet(frozen['cases'],'c3_next_decision','baseline',1)
        b=probe.packet(frozen['cases'],'c3_next_decision','evidence',1)
        a.pop('diagnostic_evidence');b.pop('diagnostic_evidence');self.assertEqual(a,b)
        with self.assertRaisesRegex(ValueError,'EXPLICIT_PROBE_APPROVAL'):
            asyncio.run(probe.live(self.out,test_transport=httpx.MockTransport(lambda r:(_ for _ in ()).throw(AssertionError('NO_SEND')))))
        self.assertFalse((self.out/'provider').exists())

    def test_c32_saved_boundary_excludes_future_and_has_no_inherited_live_grant(self):
        from tests.research.c3_readiness_audit import FrozenDecisionBoundary,c3_frozen_audit
        from tools.state_io import atomic_json
        protocol=read(probe.ROOT/'tests/research/fixtures/c32_scientific_decision_protocol.json')
        definition=protocol['cases']['M']
        with patch('tools.research.analysis.dispatch',side_effect=AssertionError('NO_SCIENCE')) as worker, \
                patch('httpx.AsyncHTTPTransport.handle_async_request',side_effect=AssertionError('NO_PROVIDER')) as provider:
            b=FrozenDecisionBoundary(probe.ROOT,'M',source=(definition['folder'],definition['sequence']))
            try:
                self.assertEqual(b.preparation['source_state']['artifact_id'],definition['source_state'])
                self.assertEqual(len(b.saved_state['analysis_results']),6)
                self.assertEqual(b.saved_state.get('physical_replays',[]),[])
                future=b.snapshot['session']['state']['physical_replays'][0]
                with self.assertRaisesRegex(ValueError,'C3_FUTURE_OR_UNPUBLISHED_REFERENCE'):
                    b.host.store.artifact(future)
                packet,tools=b.projection()
                self.assertNotIn('rubric_offline_only',json.dumps(packet))
                self.assertNotIn(future['artifact_id'],json.dumps(packet))
                b.host.store.transaction.assert_not_called();b.host.store.reserve.assert_not_called()
                self.out.mkdir(parents=True)
                original=b.artifact(b.saved_state['analysis_results'][0])['requested_operation']
                calls=self.out/'calls.json';feedback=self.out/'feedback.json'
                atomic_json(calls,[dict(id='recorded-analysis',function=dict(name='research_analysis',arguments=json.dumps(original)))])
                c3_frozen_audit(probe.ROOT,'M',feedback,calls,source=(definition['folder'],definition['sequence']))
                result=read(feedback)[0]
                self.assertEqual(result['status'],'success')
                self.assertEqual(result['result']['new_scientific_computations'],0)
                self.assertIsNone(result['result']['expected_computation_cost']['native_physics_steps'])
                self.assertTrue(result['result']['unchecked_execution_preconditions'])
            finally:b.archive.close()
            atomic_json(self.out/'frozen.json',dict(offline_passed=True,scope=probe.C3_SCOPE.replace('C3 is','C3.2 is'),
                authorization='PENDING_EXPLICIT_C32_APPROVAL'))
            with self.assertRaisesRegex(ValueError,'C3_OFFLINE_GATE_REQUIRED'):
                asyncio.run(probe.c3_live(self.out))
            self.assertFalse((self.out/'provider').exists())
            worker.assert_not_called();provider.assert_not_called()

    def c32_fixture(self):
        """Copies of the real freeze; explicit mock approval never authorizes real egress."""
        from tools.state_io import atomic_json
        inputs=self.out.parent/(self.out.name+'-inputs');approval=self.out.parent/(self.out.name+'-approval.json')
        shutil.copytree(probe.C32_INPUTS,inputs)
        def cleanup():
            assert inputs.resolve().parent==(probe.ROOT/'runs').resolve()
            shutil.rmtree(inputs);approval.unlink(missing_ok=True)
        self.addCleanup(cleanup)
        f=read(inputs/'frozen.json')
        value=dict(experiment='C3.2',approved=True,user_approval='EXPLICIT MOCK TRANSPORT FIXTURE ONLY; no real egress',
            endpoint='https://api.deepseek.com/chat/completions',model='deepseek-flash',max_requests=12,
            commits=f['commits'],frozen_inputs=str(inputs.resolve()),data_scope='six_frozen_inputs_and_read_only_followup',
            scientific_execution=False,no_retries=True)
        atomic_json(approval,value)
        return inputs,approval,value

    def test_c32_live_reuses_six_inputs_two_rounds_and_read_only_proposals(self):
        from tests.research.c3_readiness_audit import FrozenDecisionBoundary
        from tools.state_io import atomic_json
        inputs,approval,_=self.c32_fixture();f=read(inputs/'frozen.json');sends=[]
        originals={p.name:p.read_bytes() for p in probe.C32_INPUTS.iterdir()}
        a=FrozenDecisionBoundary(probe.ROOT,'M',source=('c3_math_search_ab_100ms_20261025',184))
        try:analysis=a.artifact(a.saved_state['analysis_results'][0])['requested_operation']
        finally:a.archive.close()
        def respond(request):
            wire=json.loads(request.content);index=len(sends);sends.append(wire)
            case,arm=(f['order'] if index<6 else list(reversed(f['order'])))[index%6]
            label=f'{case}-{arm}'
            message=dict(role='assistant',content='Mock judgment only; not scientific evidence',reasoning_content='mock-'+label)
            if index<6:
                base=read(inputs/f'{case}-{arm}.json');facts=base['source_facts']
                name='evidence_read';args=dict(reference=facts['physical_results'][0]['reference'],view='fields',fields=['acceptance']) if case!='M' else None
                if label=='N-treatment':args=dict(reference=dict(artifact_id='f'*64,media_type='application/json'),view='full')
                elif label=='K-control':args['fields']=[]
                elif label=='K-treatment':
                    name='research_plan';args=dict(action='diagnose',hypothesis='Mock competing explanations A and B',
                        expected_observation='Mock conditional observation',weakening_observation='Mock falsifier',
                        fixed_conditions='Frozen task',stopping_condition='No scientific execution',interpretation='Mock branches only',
                        decision=dict(hypothesis_id='fixture',research_intent='DIAGNOSE',selected_method='native_dynamics_v1',
                            selected_candidate=facts['candidates'][0],requested_budget=1))
                elif label=='M-control':name='research_analysis';args=analysis
                elif label=='M-treatment':name='research_plan'
                message['tool_calls']=[dict(id=label,type='function',function=dict(name=name,
                    arguments='{invalid mock JSON' if label=='M-treatment' else json.dumps(args)))]
            return httpx.Response(200,json=dict(choices=[dict(finish_reason='tool_calls' if index<6 else 'stop',message=message)],
                usage=dict(prompt_tokens=10,completion_tokens=5,total_tokens=15)))
        project_config=probe.ProjectConfig;original_boundary=probe.c3_boundary
        def isolated_grant(**values):return project_config(**{**values,'grant_id':'mock-c32-'+self.out.name})
        def feedback(case,arm,output,tool_input,**kw):
            if read(tool_input):return original_boundary(case,arm,output,tool_input,**kw)
            atomic_json(output,[])
        with patch.dict(os.environ,DEEPSEEK_API_KEY='offline-fixture'),\
                patch('httpx.AsyncHTTPTransport',side_effect=AssertionError('NO_REAL_PROVIDER')),\
                patch.object(probe,'ProjectConfig',side_effect=isolated_grant),\
                patch.object(probe,'c3_boundary',side_effect=feedback),\
                patch.object(probe,'c32_freeze',side_effect=AssertionError('NO_REFREEZE')),\
                patch('tools.research.core.dispatch',side_effect=AssertionError('NO_SCIENCE')) as worker:
            transport=httpx.MockTransport(respond)
            first=asyncio.run(probe.c32_live(self.out,inputs,approval,test_transport=transport))
            self.assertEqual(first['status'],'first_six_complete');self.assertEqual(len(sends),6)
            review=probe.c32_review(self.out,inputs)
            self.assertTrue(review['first_batch_validity']['passed'])
            self.assertEqual((review['public_tool_calls'],review['evidence_reads'],review['error_queries']),(6,3,1))
            self.assertEqual((review['invalid_tool_json'],review['empty_object_reads'],review['schema_legal_proposals']),(1,1,2))
            proposals=[v['result'] for r in first['results'] for v in r['feedback'] if v['result'].get('status')=='proposal_recorded']
            self.assertEqual([v['method_authorization']['catalog']['formal_execution_authorized'] for v in proposals],[True,False])
            self.assertTrue(all(v['observation'] is None and v['new_scientific_computations']==0 for v in proposals))
            feedback_path=self.out/'K-treatment-1-feedback.json';original_feedback=feedback_path.read_bytes()
            changed=read(feedback_path);changed[0]['result']['observation']='Fabricated mock observation must be rejected'
            atomic_json(feedback_path,changed)
            with self.assertRaisesRegex(ValueError,'FIRST_BATCH_VALIDITY'):
                asyncio.run(probe.c32_live(self.out,inputs,approval,True,test_transport=transport))
            self.assertEqual(len(sends),6);feedback_path.write_bytes(original_feedback)
            response_path=self.out/'N-control-1-response.json';original_response=response_path.read_bytes()
            changed=read(response_path);changed['choices'][0]['message']['content']='Changed mock response'
            atomic_json(response_path,changed)
            self.assertFalse(probe.c32_review(self.out,inputs)['first_batch_validity']['passed'])
            response_path.write_bytes(original_response)
            second=asyncio.run(probe.c32_live(self.out,inputs,approval,True,test_transport=transport))
            self.assertEqual((second['actual_requests'],second['usage']['total_tokens']),(12,180))
            self.assertEqual(second['provider_ledger']['remaining']['model_calls'],0)
            with self.assertRaisesRegex(ValueError,'NO_AUTOMATIC_RESEND'):
                asyncio.run(probe.c32_live(self.out,inputs,approval,test_transport=transport))
            with self.assertRaisesRegex(ValueError,'FOLLOWUP_REQUIRES'):
                asyncio.run(probe.c32_live(self.out,inputs,approval,True,test_transport=transport))
            self.assertEqual(len(sends),12);worker.assert_not_called()
        for index,(case,arm) in enumerate(f['order']):
            self.assertEqual(sends[index],read(inputs/f'{case}-{arm}-1-request.json'))
            follow=sends[11-index]
            self.assertEqual({k:v for k,v in follow.items() if k!='messages'},{k:v for k,v in sends[index].items() if k!='messages'})
            self.assertEqual(follow['messages'][:len(sends[index]['messages'])],sends[index]['messages'])
            self.assertEqual(follow['messages'][-3]['reasoning_content'],'mock-'+case+'-'+arm)
        final=probe.c32_review(self.out,inputs)
        self.assertEqual(final['scientific_verdict'],'insufficient_evidence')
        self.assertTrue(all(v is None for c in final['worksheets'].values() for a in c.values() for v in a['ratings'].values()))
        self.assertEqual(originals,{p.name:p.read_bytes() for p in probe.C32_INPUTS.iterdir()})

    def test_c32_requires_bound_approval_and_unchanged_inputs_before_any_send(self):
        from tools.state_io import atomic_json
        inputs,approval,valid=self.c32_fixture()
        transport=httpx.MockTransport(lambda r:(_ for _ in ()).throw(AssertionError('NO_SEND')))
        with patch.object(probe,'load_credential',side_effect=AssertionError('NO_CREDENTIAL_READ')):
            with self.assertRaisesRegex(ValueError,'EXPLICIT_EGRESS_APPROVAL'):
                asyncio.run(probe.c32_live(self.out,inputs,test_transport=transport))
            for changed in (dict(approved=False),dict(experiment='C3'),dict(max_requests=13),dict(endpoint='https://other.invalid'),dict(commits={})):
                atomic_json(approval,{**valid,**changed})
                with self.assertRaisesRegex(ValueError,'EXPLICIT_EGRESS_APPROVAL'):
                    asyncio.run(probe.c32_live(self.out,inputs,approval,test_transport=transport))
            atomic_json(approval,valid)
            frozen_path=inputs/'frozen.json';original=frozen_path.read_bytes()
            for key in ('protocol','commits'):
                frozen=read(frozen_path)
                if key=='protocol':frozen['protocol']['rubric_offline_only']['axes']['cost']+=' changed'
                else:frozen['commits']['treatment']='0'*40
                atomic_json(frozen_path,frozen)
                with self.assertRaisesRegex(ValueError,'FROZEN_PROTOCOL_OR_BASELINE_CHANGED'):
                    asyncio.run(probe.c32_live(self.out,inputs,approval,test_transport=transport))
                frozen_path.write_bytes(original)
            request=inputs/'N-control-1-request.json';value=read(request);value['messages'][0]['content']+=' changed'
            atomic_json(request,value)
            with self.assertRaisesRegex(ValueError,'FROZEN_REQUEST_CHANGED'):
                asyncio.run(probe.c32_live(self.out,inputs,approval,test_transport=transport))
        self.assertFalse((self.out/'provider').exists())

    def test_c32_unknown_send_stops_and_cannot_enter_second_round(self):
        inputs,approval,_=self.c32_fixture();sends=[];project_config=probe.ProjectConfig
        def isolated_grant(**values):return project_config(**{**values,'grant_id':'mock-c32-'+self.out.name})
        def fail(request):sends.append(request);raise httpx.ReadError('Mock unknown outcome')
        transport=httpx.MockTransport(fail)
        with patch.dict(os.environ,DEEPSEEK_API_KEY='offline-fixture'),patch.object(probe,'ProjectConfig',side_effect=isolated_grant):
            with self.assertRaises(httpx.ReadError):asyncio.run(probe.c32_live(self.out,inputs,approval,test_transport=transport))
            with self.assertRaisesRegex(ValueError,'NO_AUTOMATIC_RESEND'):
                asyncio.run(probe.c32_live(self.out,inputs,approval,test_transport=transport))
            with self.assertRaisesRegex(ValueError,'FIRST_BATCH_VALIDITY'):
                asyncio.run(probe.c32_live(self.out,inputs,approval,True,test_transport=transport))
        result=probe.c32_review(self.out,inputs)
        self.assertEqual((len(sends),result['actual_requests'],result['confirmed_responses']),(1,1,0))
        self.assertIsNone(result['usage']['total_tokens']);self.assertFalse(result['first_batch_validity']['passed'])

    def test_eight_single_decisions_exact_usage_and_isolated_history_no_dispatch(self):
        probe.freeze(self.out)
        requests = []

        def respond(request):
            requests.append(json.loads(request.content))
            plan = dict(action='diagnose', hypothesis='Fixture competing mechanisms A and B',
                expected_observation='Fixture metric', weakening_observation='Fixture falsifier',
                fixed_conditions='Fixture fixed inputs', stopping_condition='Fixture budget',
                interpretation='Fixture conditional decision', decision=dict(hypothesis_id=f'fixture-{len(requests)}',
                    research_intent='DIAGNOSE', selected_method='native_dynamics_v1', requested_budget=1))
            return httpx.Response(200, json=dict(choices=[dict(finish_reason='tool_calls', message=dict(
                role='assistant', content=None, tool_calls=[dict(id=f'call-{len(requests)}', type='function',
                function=dict(name='research_plan', arguments=json.dumps(plan)))]))],
                usage=dict(prompt_tokens=10, completion_tokens=5, total_tokens=15,
                           prompt_cache_hit_tokens=2, prompt_cache_miss_tokens=8,
                           completion_tokens_details=dict(reasoning_tokens=3))))

        with patch.dict(os.environ, DEEPSEEK_API_KEY='offline-fixture'), \
             patch('tools.research.core.dispatch', side_effect=AssertionError('NO_SCIENCE')) as dispatch:
            result = asyncio.run(probe.live(self.out, test_transport=httpx.MockTransport(respond)))
        self.assertEqual(len(requests), 8)
        self.assertEqual(result['usage']['total_tokens'], 120)
        self.assertEqual(result['usage']['reasoning_tokens'], 24)
        self.assertEqual(result['provider_ledger']['used']['model_calls'], 8)
        self.assertEqual(result['provider_ledger']['used']['backend_solves'], 0)
        self.assertEqual(result['provider_ledger']['used']['worker_calls'], 0)
        self.assertTrue(all(r['schema_check'] == 'passed' for r in result['results']))
        dispatch.assert_not_called()
        for second, own_first, other_first in ((2, 1, 2), (3, 2, 1), (6, 5, 6), (7, 6, 5)):
            messages = json.dumps(requests[second]['messages'])
            self.assertIn(f'fixture-{own_first}', messages)
            self.assertNotIn(f'fixture-{other_first}', messages)
        with self.assertRaises(ValueError):
            probe.parse(dict(content='unstructured fixture without a tool call'))
        self.assertIsNone(result['money'])

    def test_unknown_outcome_stops_and_existing_attempt_cannot_resend(self):
        probe.freeze(self.out)
        attempts = []

        def fail(request):
            attempts.append(request)
            raise httpx.ReadError('offline fixture unknown outcome')

        with patch.dict(os.environ, DEEPSEEK_API_KEY='offline-fixture'):
            with self.assertRaises(httpx.ReadError):
                asyncio.run(probe.live(self.out, test_transport=httpx.MockTransport(fail)))
            with self.assertRaisesRegex(ValueError, 'NO_AUTOMATIC_RESEND'):
                asyncio.run(probe.live(self.out, test_transport=httpx.MockTransport(fail)))
        result = read(self.summary)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(result['actual_requests'], 1)
        self.assertEqual(result['confirmed_responses'], 0)
        self.assertEqual(result['provider_ledger']['occupied']['provider_request'], 1)
        self.assertIsNone(result['usage']['total_tokens'])

    def test_c3_rounds_share_twelve_request_cap_and_never_dispatch(self):
        from types import SimpleNamespace
        from tools.platform_store import Store
        from tools.state_io import atomic_json
        provider=read(probe.ROOT/'configs/research/runtime_c3_ab.json')['provider']
        self.out.mkdir(parents=True)
        order=[(c,a) for c in ('A','B','C') for a in probe.C3_ARMS]
        atomic_json(self.out/'frozen.json',dict(offline_passed=True,scope=probe.C3_SCOPE,
            authorization='EXPLICIT OFFLINE MOCK ONLY',provider=provider,order=order))
        for case,arm in order:
            atomic_json(self.out/f'{case}-{arm}.json',dict(handoff_wire=dict(model=provider['model'],
                tools=[],messages=[dict(role='system',content='Explicit mock fixture'),dict(role='user',content='No scientific facts')])) )
        sends=[]
        def respond(request):
            sends.append(request)
            return httpx.Response(200,json=dict(choices=[dict(finish_reason='stop',message=dict(
                role='assistant',content='Mock decision only'))],usage=dict(prompt_tokens=1,completion_tokens=1,total_tokens=2)))
        def feedback(case,arm,output,tool_input):atomic_json(output,[])
        project_config=probe.ProjectConfig
        def isolated_grant(**values):
            return project_config(**{**values,'grant_id':'explicit-mock-c3-'+self.out.name})
        transport=httpx.MockTransport(respond)
        with patch.dict(os.environ,DEEPSEEK_API_KEY='offline-fixture'),\
                patch('httpx.AsyncHTTPTransport',return_value=transport),\
                patch.object(probe,'ProjectConfig',side_effect=isolated_grant),\
                patch.object(probe,'c3_boundary',side_effect=feedback),\
                patch('tools.research.core.dispatch',side_effect=AssertionError('NO_SCIENCE')) as dispatch:
            first=asyncio.run(probe.c3_live(self.out));self.assertEqual(first['actual_requests'],6)
            second=asyncio.run(probe.c3_live(self.out,True));self.assertEqual(second['actual_requests'],12)
            with self.assertRaisesRegex(ValueError,'NO_AUTOMATIC_RESEND'):asyncio.run(probe.c3_live(self.out))
            with self.assertRaisesRegex(ValueError,'FOLLOWUP_REQUIRES'):asyncio.run(probe.c3_live(self.out,True))
            host=SimpleNamespace(store=Store(self.out/'provider'),run_id='c3-agent-decision-efficiency')
            boundary=probe.LiveBoundary(host,transport)
            wire=json.loads(sends[-1].content)
            with self.assertRaisesRegex(ValueError,'PROVIDER_COUNT_EXHAUSTED'):
                asyncio.run(boundary.handle_async_request(httpx.Request('POST',provider['base_url']+'/chat/completions',json=wire)))
            self.assertEqual(len(sends),12);dispatch.assert_not_called()
        self.assertEqual(second['provider_ledger']['remaining']['model_calls'],0)
        self.assertEqual(second['provider_ledger']['used']['worker_calls'],0)


if __name__ == '__main__':
    unittest.main()
