"""Offline protocol fixtures: real Store/SDK, mocked HTTP, no scientific workers."""
import asyncio
from copy import deepcopy
import json
import os
import unittest
from unittest.mock import patch
from unittest.mock import AsyncMock
from types import SimpleNamespace
import httpx
from schemas.platform import ProjectConfig
from tools.platform_store import plain, zero
from tools.research import reporter
from tools.research.agent import LiveBoundary, converse, record
from tools.research.core import read_evidence
from tools.research.evidence_policy import registered_references
from tools.research.research_context import research_intent
from tools.research.session_handoff import handoff, reconcile, recover_feedback, unmatched
from tools.research.state import state, update, save
from tools.state_io import digest, atomic_json
from tests.research import test_research_reporting as f0
from tests.research import test_mainline as mainline
from tests.research.test_s126_checkpoint import cold_host
from tests.research.test_s127_session_recovery import factory, complete, response


def byte_size(value):
    return len(json.dumps(plain(value),ensure_ascii=False,separators=(',',':')).encode())


def reporter_response(request, *, malicious=False, finish='stop'):
    wire=json.loads(request.content);payload=json.loads(wire['messages'][-1]['content'])
    content=dict(interpretations=[dict(kind='unresolved_question',
        text='Fixture: multiple conditions changed; evidence does not isolate a cause.',
        sources=[payload['report']['results'][0]['identity']['result']])])
    if malicious:content['results']=[{'metrics':'replace authoritative values'}]
    return httpx.Response(200,json=dict(id='offline-reporter',object='chat.completion',created=1,
        model=wire['model'],choices=[dict(index=0,finish_reason=finish,message=dict(role='assistant',
            content=json.dumps(content)))],usage=dict(prompt_tokens=17,completion_tokens=3,total_tokens=20)))


class AgentReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):f0.ReportingTests.setUpClass()

    def setUp(self):
        self.case=mainline.MainlineTests()
        with patch.object(mainline,'ProjectConfig',side_effect=lambda **kw:ProjectConfig(
                **kw,exclusive_resources={'provider_request':1})):
            self.case.setUp()
        self.addCleanup(self.case.tearDown)
        self.h=self.case.host;self.f=f0.ReportingTests();self.f.setUp()
        # F0's in-memory fixture uses a synthetic all-a reference. Persist a real
        # content-addressed candidate before exercising the actual Store boundary.
        candidate=self.f.values.pop(self.f.candidate['artifact_id'])
        self.f.candidate=self.f.put(candidate)
        self.f.fixture.ref=self.f.candidate
        spec=deepcopy(state(self.h)['spec']);spec['mode']='engineering_numerical'
        update(self.h,spec=spec,results=[],pilot=dict(provider=self.case.cfg['policy']['model'],
            live_model_requests=0,framework_session_id='offline-main'),freeze='offline-fixture')

    def put(self, value):
        ref=self.f.put(value)
        for v in self.f.values.values():save(self.h,v,'synthetic_fixture')
        return ref

    def physical(self):
        ref=self.put(self.f.physical_result());update(self.h,physical_replays=[ref]);return ref

    def test_automatic_physics_math_search_and_rl_reports_preserve_f0_facts(self):
        before=state(self.h);reference=self.physical()
        auto=reporter.scientific_feedback(self.h,dict(result=dict(reference=reference)),before)
        self.assertEqual(auto['report']['mode'],'result_summary')
        speed=next(m for m in auto['report']['results'][0]['metrics'] if m['name']=='holding_speed')
        self.assertEqual((speed['value'],speed['threshold'],speed['unit'],speed['passed']),(.04,.02,'m/s',False))
        baseline=self.h.store.artifact(reference);variant=deepcopy(baseline)
        variant['acceptance']['components']['holding_speed']['value']=.05
        other=self.put(variant);update(self.h,physical_replays=[reference,other])
        compared=reporter.assemble(self.h,[other]);self.assertTrue(compared.relations[0].comparable)
        self.assertIsNone(compared.relations[0].single_factor_attribution)
        changes=compared.results[0].deterministic_summary['comparisons'][0]['metrics']
        self.assertAlmostEqual(next(m for m in changes if m['metric']=='holding_speed')['delta'],.01)
        math=self.put(self.f.math_result());update(self.h,analysis_results=[math])
        self.assertIsNotNone(reporter.assemble(self.h,[math]).results[0].mathematics)
        legacy=self.put(dict(operation='solve',status='computed',design_candidate=self.f.candidate,
            mathematical_facts=dict(status='inconclusive',objective=115.64175490824711,iterations=78),
            verified_conclusions=['Fixture: local numerical result only']))
        legacy_card=reporter.assemble(self.h,[legacy]).results[0]
        self.assertIsNone(legacy_card.mathematics)
        self.assertEqual(legacy_card.deterministic_summary['recorded_mathematics']['status'],'inconclusive')
        self.assertEqual(next(m.value for m in legacy_card.metrics if m.name=='iterations'),78)
        row=dict(label='baseline',reference=reference,candidate=self.f.candidate,
            source=baseline['source_reference'],task_gap=dict(normalized_gap=1.,accepted=False),
            original_acceptance=baseline['acceptance'])
        search=self.put(dict(candidates=[row],best=row,starts=[],start_feedback=[],
            stop_reason='iteration_limit',cost_feedback=dict(new_physical_evaluations=1)))
        self.assertEqual(reporter.assemble(self.h,[search]).results[0].control_search.stop_reason.value,'iteration_limit')
        rl=self.put(dict(independent_evaluation_executed=True,candidate=self.f.candidate,
            acceptance=dict(terminal_position_limit_m=.01,position_limit_m=.01,holding_speed_limit_m_s=.02),
            episodes=[dict(complete=True,holding_coverage_complete=True,terminal_position_error_m=.03,
                holding_max_position_error_m=.04,holding_max_speed_m_s=.05)],passed=False))
        card=reporter.assemble(self.h,[rl]).results[0]
        self.assertEqual(len(card.metrics),3)
        for metric in card.metrics:
            self.assertEqual(read_evidence(self.h,plain(metric.source),record_read=False),metric.value)
        self.assertEqual(state(self.h).get('evaluation_reads',[]),[])

    def test_investigation_uses_exact_reads_and_never_registers_or_credits_reports(self):
        reference=self.physical();known=registered_references(self.h);before=state(self.h)
        request=dict(question='Can the speed difference be attributed to the controller?',references=[reference],
            focus=['holding_speed'],constraints=['Only existing saved evidence'],
            reads=[dict(reference=reference,view='fields',pointer='/acceptance/components/holding_speed',
                fields=['value','limit','passed'])])
        result=reporter.investigate(self.h,request)
        self.assertEqual(result['report']['question'],request['question'])
        self.assertEqual(result['report']['mode'],'investigation')
        self.assertEqual(registered_references(self.h),known)
        self.assertEqual(state(self.h),before)
        self.assertNotIn(result['report_reference'],known)
        with self.assertRaises(ValueError):reporter.InvestigationRequest.model_validate({**request,'execute':True})

    def test_reporter_is_independent_accounted_and_cannot_overwrite_facts(self):
        reference=self.physical();initial=reporter.investigate(self.h,dict(question='Explain limits',references=[reference]))
        before=self.h.store.artifact(reference);sent=[]
        def respond(request):sent.append(json.loads(request.content));return reporter_response(request)
        asyncio.run(reporter.complete_reports(self.h,httpx.MockTransport(respond)))
        final=reporter.entries(self.h)[-1][1]
        self.assertEqual(final['interpretation_status'],'available')
        self.assertEqual(final['report']['results'],initial['report']['results'])
        self.assertEqual(self.h.store.artifact(reference),before)
        self.assertEqual(self.h.store.remaining()['used']['model_calls'],1)
        self.assertEqual(len(sent[0]['messages']),2);self.assertNotIn('tools',sent[0])
        reception=next(self.h.store.artifact(e['outputs'][0]) for e in reversed(self.h.store.events(self.h.run_id)) if e['kind']=='r3_response')
        self.assertEqual(reception['purpose'],'reporter');self.assertEqual(reception['usage']['total_tokens'],20)
        self.assertNotIn('unconsumed_response',state(self.h)['pilot'])
        self.assertEqual(state(self.h).get('evaluation_reads',[]),[])
        self.assertNotIn(final['report'],[self.h.store.artifact(r) for r in registered_references(self.h)])

    def test_invalid_or_truncated_interpretation_falls_back_without_scientific_reexecution(self):
        reference=self.physical();before=self.h.store.artifact(reference)
        for malicious,finish in ((True,'stop'),(False,'length')):
            initial=reporter.investigate(self.h,dict(question='Fixture '+finish,references=[reference]))
            with patch('tools.research.core.dispatch',side_effect=AssertionError('No science')):
                asyncio.run(reporter.complete_reports(self.h,httpx.MockTransport(
                    lambda request:reporter_response(request,malicious=malicious,finish=finish))))
            final=reporter.entries(self.h)[-1][1]
            self.assertEqual(final['interpretation_status'],'unavailable')
            self.assertEqual(final['report'],initial['report'])
            self.assertNotIn('unconsumed_response',state(self.h)['pilot'])
        self.assertEqual(self.h.store.artifact(reference),before)
        self.assertEqual(self.h.store.remaining()['used']['model_calls'],2)

    def test_main_unconsumed_response_and_unknown_reporter_send_block_nested_requests(self):
        reference=self.physical();reporter.investigate(self.h,dict(question='Fixture',references=[reference]))
        p=deepcopy(state(self.h)['pilot']);p['unconsumed_response']='main-fixture';update(self.h,pilot=p)
        forbidden=httpx.MockTransport(lambda r:(_ for _ in ()).throw(AssertionError('No send')))
        asyncio.run(reporter.complete_reports(self.h,forbidden))
        self.assertEqual(self.h.store.remaining()['used']['model_calls'],0)
        p.pop('unconsumed_response');update(self.h,pilot=p)
        def unknown(request):raise httpx.ReadError('Unknown offline send')
        with self.assertRaises(httpx.ReadError):asyncio.run(reporter.complete_reports(self.h,httpx.MockTransport(unknown)))
        with self.assertRaisesRegex(ValueError,'SETTLED'):asyncio.run(reporter.complete_reports(self.h,forbidden))
        self.assertEqual(self.h.store.remaining()['used']['model_calls'],1)

    def test_saved_reporter_response_recovers_without_resend_or_new_charge(self):
        from tools.research.agent import received
        reference=self.physical();reporter.investigate(self.h,dict(question='Recover fixture',references=[reference]))
        ref,saved=reporter.entries(self.h)[0];wire=reporter._wire(self.h,ref,saved)
        boundary=LiveBoundary(self.h,httpx.MockTransport(reporter_response));boundary.purpose='reporter'
        provider=state(self.h)['pilot']['provider']
        async def exercise():
            await boundary.handle_async_request(httpx.Request('POST',provider['base_url']+'/chat/completions',json=wire))
            self.assertEqual(received(self.h,boundary.last_request)['purpose'],'reporter')
            before=self.h.store.remaining()
            await reporter.complete_reports(self.h,httpx.MockTransport(lambda r:(_ for _ in ()).throw(AssertionError('No send'))),recover_only=True)
            self.assertEqual(self.h.store.remaining(),before)
        asyncio.run(exercise())
        self.assertEqual(reporter.entries(self.h)[-1][1]['interpretation_status'],'available')
        self.assertNotIn('unconsumed_response',state(self.h)['pilot'])

    def test_budget_preserves_closeout_capacity(self):
        reference=self.physical();reporter.investigate(self.h,dict(question='Budget fixture',references=[reference]))
        spec=deepcopy(state(self.h)['spec'])
        spec['budgets']['protected_provider_requests']=self.h.store.remaining()['remaining']['model_calls']-1
        update(self.h,spec=spec)
        asyncio.run(reporter.complete_reports(self.h,httpx.MockTransport(lambda r:(_ for _ in ()).throw(AssertionError('No send')))))
        self.assertEqual(self.h.store.remaining()['used']['model_calls'],0)
        self.assertIn('PRESERVE_CLOSEOUT',reporter.entries(self.h)[-1][1]['error'])
        events=self.h.store.events(self.h.run_id)
        asyncio.run(reporter.complete_reports(self.h,httpx.MockTransport(lambda r:(_ for _ in ()).throw(AssertionError('No send')))))
        self.assertEqual(self.h.store.events(self.h.run_id),events)

    def test_intent_is_rebuilt_from_original_plan_receipt_and_observation(self):
        reference=self.physical();plan=dict(action='physical_replay',hypothesis='Damping may reduce speed',
            decision=dict(hypothesis_id='H-fixture',research_intent='PHYSICAL_VALIDATION',selected_method='fixed input'),
            expected_observation='Lower speed',weakening_observation='Speed rises',fixed_conditions='Task and time grid',
            interpretation='Unconfirmed hypothesis',stopping_condition='Original thresholds')
        key='native-fixture';row,_=self.h.store.reserve(self.h.run_id,key,digest(plan),self.h.actor,zero())
        ref=save(self.h,dict(request_id=key,original_plan=plan),'original_research_plan')
        self.h.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller=self.h.actor,
            tool_id='research.core_plan',tool_version='1.0.0',execution_status='completed',charged=zero()),dict(result=dict(reference=reference)))
        update(self.h,plans=[ref]);intent=research_intent(self.h)['last_research']
        self.assertEqual(intent['agent_hypothesis']['decision']['hypothesis_id'],'H-fixture')
        self.assertEqual(intent['actual_result'],reference)
        report=reporter.assemble(self.h,[reference])
        self.assertTrue(any(f.name=='agent_intent/weakening_observation' for f in report.results[0].recorded_context))

    def test_investigation_receipt_recovers_original_id_without_rerunning_reporter(self):
        reference=self.physical();query=dict(question='Recover saved investigation',references=[reference])
        value=reporter.investigate(self.h,query);key='native-original-investigation-id'
        use=dict(name='research_investigate',toolUseId='original-investigation-id',input=query)
        row,_=self.h.store.reserve(self.h.run_id,key,digest(query),self.h.actor,zero())
        self.h.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller=self.h.actor,
            tool_id='research.core_investigate',tool_version='1.0.0',execution_status='completed',charged=zero()),value)
        record(self.h,'model_original_tool_request',dict(tool_use=use))
        agent=SimpleNamespace(messages=[dict(role='assistant',content=[dict(toolUse=use)])],
            _session_manager=SimpleNamespace(session_id='offline-main',save_snapshot=AsyncMock()))
        before=self.h.store.remaining()
        with patch.object(reporter,'investigate',side_effect=AssertionError('No reexecution')):
            self.assertEqual(asyncio.run(recover_feedback(self.h,agent)),1)
        result=agent.messages[-1]['content'][0]['toolResult']
        self.assertEqual(result['toolUseId'],use['toolUseId'])
        self.assertEqual(json.loads(result['content'][0]['text']),value)
        self.assertEqual(self.h.store.remaining(),before)


class ReportingSessionTests(unittest.TestCase):
    def test_three_real_sdk_sessions_keep_tools_budget_and_bounded_input(self):
        h=cold_host();p=deepcopy(state(h)['pilot']);p['session_handoff_live_admitted']=True;update(h,pilot=p)
        observation=save(h,dict(status='computed',solver_status='fixture_only'),'synthetic_fixture')
        plan=dict(action='mechanics',hypothesis='Fixture H: damping explains speed',
            decision=dict(hypothesis_id='H-fixture',research_intent='MATHEMATICAL_ANALYSIS',selected_method='fixture'),
            expected_observation='Lower speed',weakening_observation='Higher speed',fixed_conditions='Frozen task',
            interpretation='Unconfirmed explanation',stopping_condition='Original acceptance')
        row,_=h.store.reserve(h.run_id,'native-intent-fixture',digest(plan),h.actor,zero())
        plan_ref=save(h,dict(request_id=row['request_id'],original_plan=plan),'original_research_plan')
        h.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=h.actor,
            tool_id='research.core_plan',tool_version='1.0.0',execution_status='completed',charged=zero()),dict(result=dict(reference=observation)))
        update(h,plans=[plan_ref])
        boundary=LiveBoundary(h,httpx.MockTransport(response));build=factory(h,boundary);sessions=[];sizes=[];old_sizes=[]
        async def exercise():
            agent=build()
            for i in range(3):
                sessions.append(agent._session_manager.session_id)
                await complete(h,agent,'Offline complete round '+str(i)+' historical payload '*3000)
                self.assertFalse(unmatched(agent.messages))
                if i==2:break
                ledger=h.store.remaining();old_messages=deepcopy(agent.messages)
                _,agent=await handoff(h,agent,build,h.store.root/'sdk')
                sizes.append(byte_size(agent.messages))
                old_sizes.append(byte_size(old_messages))
                self.assertLess(byte_size(agent.messages),byte_size(old_messages))
                self.assertNotIn('historical payload',json.dumps(agent.messages))
                packet=json.loads(agent.messages[0]['content'][0]['text'].split('\n',1)[1])
                intent=packet['research']['research_intent']['last_research']
                self.assertEqual(intent['agent_hypothesis']['decision']['hypothesis_id'],'H-fixture')
                self.assertEqual(intent['agent_hypothesis']['weakening_observation'],'Higher speed')
                self.assertEqual(intent['actual_result'],observation)
                self.assertEqual(h.store.remaining(),ledger)
                self.assertEqual((await reconcile(h,build,h.store.root/'sdk')).messages,agent.messages)
            self.assertEqual(len(set(sessions)),3)
            self.assertLess(abs(sizes[1]-sizes[0]),500)
            self.assertEqual(h.store.remaining()['used']['model_calls'],3)
            self.assertEqual(h.store.remaining()['used']['backend_solves'],0)
            baseline=cold_host();control=LiveBoundary(baseline,httpx.MockTransport(response));continuous=factory(baseline,control)()
            for i in range(3):await complete(baseline,continuous,'Offline complete round '+str(i)+' historical payload '*3000)
            atomic_json(h.store.root/'reporting_measurements.json',dict(session_ids=sessions,
                initial_context_bytes=sizes,completed_context_bytes=old_sizes,
                rotated_usage=reporter.provider_usage(h),continuous_usage=reporter.provider_usage(baseline),
                mocked_prompt_tokens=30,mocked_completion_tokens=6))
            await control.aclose()
            await boundary.aclose()
        asyncio.run(exercise())

    def test_native_investigation_round_delivers_report_next_session_and_separate_usage(self):
        h=cold_host();p=deepcopy(state(h)['pilot']);p['session_handoff_live_admitted']=True;update(h,pilot=p)
        reference=save(h,dict(status='computed',operation='offline_fixture',solver_status='iteration_limit'),'synthetic_fixture')
        sent=[];main=[]
        def respond(request):
            wire=json.loads(request.content);sent.append(wire)
            if not wire.get('tools'):return reporter_response(request)
            main.append(wire)
            if len(main)==1:
                return httpx.Response(200,json=dict(id='native-fixture',object='chat.completion',created=1,
                    model=wire['model'],usage=dict(prompt_tokens=10,completion_tokens=2,total_tokens=12),
                    choices=[dict(index=0,finish_reason='tool_calls',message=dict(role='assistant',content=None,
                        tool_calls=[dict(id='original-investigation-id',type='function',function=dict(
                            name='research_investigate',arguments=json.dumps(dict(question='Does saved solver status establish success?',
                                references=[reference],focus=['solver status'],constraints=['Saved evidence only']))))]))]))
            if len(main)==3:
                self.assertIn('latest_reports',wire['messages'][0]['content'])
                self.assertIn('available',wire['messages'][0]['content'])
                update(h,research_status='stopped')
            return response(request)
        with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                patch('tools.research.core.guard'),patch('tools.research.agent.guard'),\
                patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(respond)):
            asyncio.run(converse(h,session_handoff=True))
        self.assertEqual(len(sent),4);self.assertEqual(len(main),3)
        feedback=[h.store.artifact(e['outputs'][0]) for e in h.store.events(h.run_id) if e['kind']=='model_original_tool_feedback']
        self.assertEqual(feedback[0]['result']['toolUseId'],'original-investigation-id')
        self.assertEqual(feedback[0]['result']['status'],'success')
        self.assertIsNotNone(h.store.lookup(h.run_id,'native-original-investigation-id')['receipt'])
        usage=reporter.provider_usage(h)
        self.assertEqual((usage['conversation']['prompt_tokens'],usage['reporter']['prompt_tokens']),(30,17))
        self.assertEqual(h.store.remaining()['used']['model_calls'],4)
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)
        self.assertEqual(state(h).get('evaluation_reads',[]),[])
        atomic_json(h.store.root/'reporting_measurements.json',dict(usage=usage,report=reporter.entries(h)[-1][1]))

    def test_original_tool_feedback_recovery_survives_two_handoffs(self):
        from strands.tools.executors import SequentialToolExecutor
        from strands.tools.tools import PythonAgentTool
        from tools.research.agent import build_harness, live_model_class
        h=cold_host();calls=[];http_calls=[]
        def respond(request):
            http_calls.append(request)
            if len(http_calls)==1:
                body=response(request).json();body['choices'][0].update(finish_reason='tool_calls',message=dict(
                    role='assistant',content=None,tool_calls=[dict(id='original-fixture-id',type='function',
                        function=dict(name='fixture',arguments='{}'))]))
                return httpx.Response(200,json=body)
            return response(request)
        def execute(use,**kwargs):
            calls.append(use['toolUseId']);record(h,'model_original_tool_request',dict(tool_use=use))
            result=dict(toolUseId=use['toolUseId'],status='success',content=[dict(text='Saved fixture outcome')])
            record(h,'model_original_tool_feedback',dict(tool_use=use,result=result));return result
        boundary=LiveBoundary(h,httpx.MockTransport(respond))
        tool=PythonAgentTool('fixture',dict(name='fixture',description='Offline fixture',
            inputSchema={'json':dict(type='object',properties={})}),execute)
        def build(session_id=None):
            return build_harness(h,transport=boundary,api_key='offline',instructions='Fixture',
                model_class=live_model_class(boundary),tool_executor=SequentialToolExecutor(),research_tools=[tool],
                configuration_path=h.store.root/'framework.json',session_directory=h.store.root/'sdk',session_id=session_id)
        async def exercise():
            agent=build();await complete(h,agent,'Native offline fixture')
            original=deepcopy(agent.messages);agent.messages=original[:2]
            await agent._session_manager.save_snapshot(agent,is_latest=True)
            ledger=h.store.remaining()
            self.assertEqual(await recover_feedback(h,agent),1)
            self.assertEqual(agent.messages[-1]['content'],original[2]['content']);self.assertFalse(unmatched(agent.messages))
            self.assertEqual(await recover_feedback(h,agent),0)
            with self.assertRaisesRegex(ValueError,'CONSUMED'):await handoff(h,agent,build,h.store.root/'sdk')
            agent.messages=original
            await agent._session_manager.save_snapshot(agent,is_latest=True)
            for i in range(2):
                _,agent=await handoff(h,agent,build,h.store.root/'sdk')
                await complete(h,agent,'Consume next fixture '+str(i))
            self.assertEqual(calls,['original-fixture-id'])
            self.assertEqual(h.store.remaining()['used']['model_calls'],ledger['used']['model_calls']+2)
            self.assertEqual((await reconcile(h,build,h.store.root/'sdk')).messages,agent.messages)
            await boundary.aclose()
        asyncio.run(exercise())

    def test_production_loop_rotates_twice_and_advertises_native_investigation(self):
        h=cold_host();p=deepcopy(state(h)['pilot']);p['session_handoff_live_admitted']=True;update(h,pilot=p)
        sent=[]
        def respond(request):
            wire=json.loads(request.content);sent.append(wire)
            self.assertIn('research_investigate',[t['function']['name'] for t in wire['tools']])
            if len(sent)==3:update(h,research_status='stopped')
            return response(request)
        with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                patch('tools.research.core.guard'),patch('tools.research.agent.guard'),\
                patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(respond)):
            asyncio.run(converse(h,session_handoff=True))
        commits=[e for e in h.store.events(h.run_id) if e['kind']=='session_handoff' and e['status']=='committed']
        self.assertEqual(len(commits),2);self.assertEqual(len(sent),3)
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)
        self.assertNotIn('unconsumed_response',state(h)['pilot'])


if __name__=='__main__':unittest.main()
