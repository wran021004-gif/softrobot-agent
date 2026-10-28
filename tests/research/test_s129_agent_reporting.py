"""Offline protocol fixtures: real Store/SDK, mocked HTTP, no scientific workers."""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
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
        **(dict(source_ids=[next(iter(payload['source_catalog']))]) if 'source_catalog' in payload
            else dict(sources=[payload['report']['results'][0]['identity']['result']])))])
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
                **{**kw,'exclusive_resources':{**kw.get('exclusive_resources',{}),'provider_request':1}})):
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

    def test_v2_uncapped_roles_wire_and_context_reserve(self):
        from tools.research.config import role_provider,validate_role_policy
        from tools.research.provider_context import capacity_estimate
        from tests.research.test_s127_provider_output import reply
        policy=dict(version='research_roles_v2',main=dict(thinking='disabled',reasoning_effort='none'),
            reporter=dict(thinking='enabled',reasoning_effort='low',max_tokens=None))
        validate_role_policy(policy)
        spec=deepcopy(state(self.h)['spec']);spec['research_decisions']={'role_policy':policy}
        pilot=deepcopy(state(self.h)['pilot']);pilot['provider'].update(policy['main']);pilot['provider']['max_tokens']=None
        pilot['provider']['output_context_reserve_tokens']=32768;update(self.h,spec=spec,pilot=pilot)
        ref=self.physical();delivery=reporter.scientific_feedback(self.h,dict(reference=ref))
        wire=reporter._wire(self.h,delivery['report_reference'],self.h.store.artifact(delivery['report_reference']))
        self.assertNotIn('max_tokens',wire);self.assertEqual(wire['reasoning_effort'],'low')
        self.assertEqual(capacity_estimate(b'{}',role_provider(spec,pilot['provider'],'reporter'))['reserved_output_tokens'],32768)
        main=dict(model=pilot['provider']['model'],thinking={'type':'disabled'},reasoning_effort='none',stream=False,
            messages=[dict(role='user',content='fixture')],tools=[])
        boundary=LiveBoundary(self.h,httpx.MockTransport(lambda r:httpx.Response(200,json=reply('stop'))))
        async def run():
            await boundary.handle_async_request(httpx.Request('POST',pilot['provider']['base_url']+'/chat/completions',json=main))
            boundary.consumed();await boundary.aclose()
        asyncio.run(run())
        self.assertNotIn('max_tokens',main)
        with self.assertRaisesRegex(ValueError,'INVALID_RESEARCH_ROLE_PROFILE'):
            validate_role_policy({**policy,'main':{**policy['main'],'max_tokens':4096}})

    def test_v2_bounded_evidence_preserves_precise_and_formal_reads(self):
        from tools.research.agent import read_tool_evidence
        policy=dict(version='research_roles_v2',main=dict(thinking='disabled',reasoning_effort='none'),
            reporter=dict(thinking='enabled',reasoning_effort='low'))
        spec=deepcopy(state(self.h)['spec']);spec['research_decisions']={'architecture':'english_decision_v1','role_policy':policy}
        reference=save(self.h,dict(metric={'speed_m_s':0.043009681835387996,'unit':'m/s'},trajectory=list(range(10000))),'v2_test')
        update(self.h,spec=spec,physical_replays=[reference],evaluation_reads=[])
        summary=read_tool_evidence(self.h,dict(reference=reference,view='fields',fields=['trajectory']))
        self.assertEqual(summary['policy'],'main_evidence_navigation_v1');self.assertLessEqual(byte_size(summary),6144)
        self.assertEqual(read_tool_evidence(self.h,dict(reference=reference,view='full',pointer='/metric/speed_m_s')),0.043009681835387996)
        self.assertNotIn(reference,state(self.h)['evaluation_reads'])
        from tools.research.core import read_evidence
        read_evidence(self.h,dict(reference=reference,view='full'),record_read=False)
        self.assertNotIn(reference,state(self.h)['evaluation_reads'])
        self.assertEqual(read_tool_evidence(self.h,dict(reference=reference,view='full')),self.h.store.artifact(reference))
        self.assertIn(reference,state(self.h)['evaluation_reads'])

    def test_role_policy_freezes_new_study_without_reinterpreting_old_study(self):
        from tools.research.config import resolve, ROOT
        from tempfile import NamedTemporaryFile
        path=ROOT/'configs/research/study_p3a_v3_pending.json'
        old=resolve(path)
        source=json.loads(path.read_text(encoding='utf-8'))
        source['study_id']='offline-role-policy-fixture'
        source['research_decisions']['role_policy']=dict(version='research_roles_v1',
            main=dict(thinking='disabled',reasoning_effort='none',max_tokens=4096),
            reporter=dict(thinking='enabled',reasoning_effort='low',max_tokens=2048))
        with NamedTemporaryFile(mode='w',encoding='utf-8',suffix='.json',dir=path.parent,delete=False) as f:
            json.dump(source,f);fixture=Path(f.name)
        try: new=resolve(fixture)
        finally: fixture.unlink()
        self.assertEqual(old['configuration']['policy']['model']['thinking'],'enabled')
        self.assertEqual(old['configuration']['policy']['model']['reasoning_effort'],'high')
        self.assertEqual(new['configuration']['policy']['model']['thinking'],'disabled')
        self.assertEqual(new['configuration']['policy']['model']['reasoning_effort'],'none')
        self.assertEqual(new['research_decisions']['role_policy']['reporter']['reasoning_effort'],'low')

    def test_versioned_roles_share_ledger_and_reject_wrong_wire(self):
        from tools.research.config import role_provider, validate_role_policy
        from tools.research.agent import pending
        from tests.research.test_s127_provider_output import reply
        policy=dict(version='research_roles_v1',
            main=dict(thinking='disabled',reasoning_effort='none',max_tokens=4096),
            reporter=dict(thinking='enabled',reasoning_effort='low',max_tokens=2048))
        validate_role_policy(policy)
        with self.assertRaisesRegex(ValueError,'INVALID_RESEARCH_ROLE_PROFILE'):
            validate_role_policy({**policy,'reporter':{**policy['reporter'],'reasoning_effort':'high'}})
        s=state(self.h);spec=deepcopy(s['spec']);spec['research_decisions']={'role_policy':policy}
        pilot=deepcopy(s['pilot']);pilot['provider'].update(policy['main']);update(self.h,spec=spec,pilot=pilot)
        provider=pilot['provider'];self.assertEqual(role_provider({},provider,'reporter'),provider)
        self.assertEqual(role_provider(spec,provider,'reporter')['reasoning_effort'],'low')
        ref=self.physical();delivery=reporter.scientific_feedback(self.h,dict(reference=ref))
        saved=self.h.store.artifact(delivery['report_reference'])
        generated=reporter._wire(self.h,delivery['report_reference'],saved)
        self.assertEqual((generated['thinking'],generated['reasoning_effort'],generated['max_tokens']),
            ({'type':'enabled'},'low',2048))
        def response(request):return httpx.Response(200,json=reply('stop'))
        main=LiveBoundary(self.h,httpx.MockTransport(response))
        aux=LiveBoundary(self.h,httpx.MockTransport(response));aux.purpose='reporter'
        main_wire=dict(model=provider['model'],thinking={'type':'disabled'},reasoning_effort='none',
            max_tokens=4096,stream=False,messages=[{'role':'user','content':'Fixture'}],tools=[])
        reporter_wire={**main_wire,'thinking':{'type':'enabled'},'reasoning_effort':'low','max_tokens':2048}
        url=provider['base_url'].rstrip('/')+'/chat/completions'
        async def run():
            with self.assertRaisesRegex(ValueError,'PROVIDER_CONFIGURATION_MISMATCH'):
                await aux.handle_async_request(httpx.Request('POST',url,json=main_wire))
            await main.handle_async_request(httpx.Request('POST',url,json=main_wire));main.consumed()
            await aux.handle_async_request(httpx.Request('POST',url,json=reporter_wire));aux.consumed()
            await main.aclose();await aux.aclose()
        before=self.h.store.remaining()['used']['model_calls'];asyncio.run(run())
        self.assertEqual(self.h.store.remaining()['used']['model_calls']-before,2)
        self.assertFalse(pending(self.h))

    def test_new_architecture_freezes_roles_and_token_threshold(self):
        from tempfile import NamedTemporaryFile
        from tools.research.config import resolve, ROOT
        path=ROOT/'configs/research/study_p3a_v3_pending.json'
        source=json.loads(path.read_text(encoding='utf-8'))
        source['study_id']='offline-english-architecture-fixture'
        source['research_decisions'].update(architecture='english_decision_v1',background=[],
            role_policy=dict(version='research_roles_v1',main=dict(thinking='disabled',reasoning_effort='none',max_tokens=4096),
                reporter=dict(thinking='enabled',reasoning_effort='low',max_tokens=2048)))
        with NamedTemporaryFile(mode='w',encoding='utf-8',suffix='.json',dir=path.parent,delete=False) as f:
            json.dump(source,f);fixture=Path(f.name)
        try:spec=resolve(fixture)
        finally:fixture.unlink()
        self.assertEqual(spec['research_decisions']['handoff_policy'],dict(version='token_handoff_v1',input_tokens=38000))
        self.assertEqual(spec['configuration']['policy']['model']['thinking'],'disabled')
        self.assertEqual(spec['research_decisions']['role_policy']['reporter']['reasoning_effort'],'low')
        self.assertTrue(spec['authorization'].startswith('PENDING_EXPLICIT_APPROVAL:'))

    def test_legacy_text_read_preserves_original_and_formal_read_rules(self):
        ref=self.physical();raw=self.h.store.artifact(ref);raw['legacy_note']='历史记录'
        legacy=save(self.h,raw,'legacy_fixture');spec=deepcopy(state(self.h)['spec'])
        spec['research_decisions']={'architecture':'english_decision_v1'}
        update(self.h,spec=spec,physical_replays=[legacy],evaluation_reads=[])
        original=deepcopy(self.h.store.artifact(legacy))
        self.assertEqual(read_evidence(self.h,dict(reference=legacy,view='fields',fields=['legacy_note'])),{'legacy_note':'历史记录'})
        self.assertEqual(state(self.h)['evaluation_reads'],[])
        self.assertEqual(read_evidence(self.h,dict(reference=legacy,view='full')),original)
        self.assertIn(legacy,state(self.h)['evaluation_reads'])
        self.assertEqual(self.h.store.artifact(legacy),original)

    def test_english_selection_requires_full_read_not_summary(self):
        reference=self.physical();spec=deepcopy(state(self.h)['spec'])
        spec['research_decisions']={'architecture':'english_decision_v1'}
        update(self.h,spec=spec,evaluation_reads=[])
        read_evidence(self.h,dict(reference=reference,view='summary'))
        self.assertNotIn(reference,state(self.h)['evaluation_reads'])
        read_evidence(self.h,dict(reference=reference,view='full'))
        self.assertIn(reference,state(self.h)['evaluation_reads'])

    def test_non_english_main_response_is_preserved_and_consumed(self):
        spec=deepcopy(state(self.h)['spec']);spec['research_decisions']={'architecture':'english_decision_v1'}
        update(self.h,spec=spec);provider=state(self.h)['pilot']['provider']
        wire=dict(model=provider['model'],thinking={'type':provider['thinking']},
            reasoning_effort=provider['reasoning_effort'],max_tokens=provider['max_tokens'],stream=False,
            messages=[dict(role='user',content='Fixture')],tools=[])
        body=dict(id='fixture',object='chat.completion',created=1,model=provider['model'],
            choices=[dict(index=0,finish_reason='stop',message=dict(role='assistant',content='非英文'))])
        boundary=LiveBoundary(self.h,httpx.MockTransport(lambda r:httpx.Response(200,json=body)))
        async def run():
            response=await boundary.handle_async_request(httpx.Request('POST',provider['base_url']+'/chat/completions',json=wire))
            self.assertEqual(response.json(),body)
            boundary.consumed()
            self.assertFalse(state(self.h)['pilot'].get('unconsumed_response'))
            await boundary.aclose()
        asyncio.run(run())

    def test_new_reporter_incomplete_novelty_and_unicode_acceptance(self):
        reference=self.physical();report=plain(reporter.assemble(self.h,[reference]))
        card=report['results'][0];card['deterministic_summary']['task_gap']['valid_complete']=False
        self.assertEqual(reporter.interpretation_priority(report,[],decision_v3=True),'new_incomplete_task_result')
        self.assertEqual(reporter.interpretation_priority(report,[deepcopy(report)],decision_v3=True),'routine_or_repeated_result')
        conflict=deepcopy(report);summary=conflict['results'][0]['deterministic_summary']
        summary.pop('task_gap',None);summary['task_capability']={'physical_failure_relation':{'status':'constraint_mismatch'}}
        self.assertEqual(reporter.interpretation_priority(conflict,[],decision_v3=True),'model_physical_constraint_mismatch')
        spec=deepcopy(state(self.h)['spec']);spec['research_decisions']={'architecture':'english_decision_v1'}
        update(self.h,spec=spec)
        delivery=reporter.scientific_feedback(self.h,dict(reference=reference));base=delivery['report_reference']
        wire=reporter._wire(self.h,base,self.h.store.artifact(base))
        request=httpx.Request('POST','https://offline.invalid',json=wire)
        response=reporter_response(request);body=response.json()
        output=json.loads(body['choices'][0]['message']['content']);output['interpretations'][0]['text']='中文报告'
        body['choices'][0]['message']['content']=json.dumps(output)
        saved=reporter._finish(self.h,SimpleNamespace(last_request='offline-non-english'),wire,httpx.Response(200,json=body))
        result=self.h.store.artifact(saved)
        self.assertEqual(result['interpretation_status'],'available')
        self.assertEqual(result['report']['interpretations'][0]['text'],'中文报告')

    def test_unchanged_scientific_feedback_does_not_repeat_reporter_call(self):
        ref=self.physical();first=reporter.scientific_feedback(self.h,dict(reference=ref),{})
        other=deepcopy(self.h.store.artifact(ref));other['fixture_repetition']='second'
        second=save(self.h,other,'synthetic_fixture');update(self.h,physical_replays=[ref,second])
        duplicate=reporter.scientific_feedback(self.h,dict(reference=second),{})
        spec=deepcopy(state(self.h)['spec']);spec['research_decisions']={'architecture':'english_decision_v1'}
        update(self.h,spec=spec);calls=[]
        def respond(request):calls.append(request);return reporter_response(request)
        asyncio.run(reporter.complete_reports(self.h,httpx.MockTransport(respond)))
        self.assertEqual(len(calls),1)
        revision=next(v for _,v in reporter.entries(self.h) if v['interpretation_for']==duplicate['report_reference'])
        self.assertEqual(revision['interpretation_status'],'skipped')

    def test_selected_method_requires_settled_diagnosis_and_matching_candidate(self):
        from tools.research.agent import selected_analysis,selected_analysis_schema
        candidate=self.f.candidate;method='mujoco-nonlinear-task-capability-v1'
        plan=dict(action='diagnose',decision=dict(selected_method=method,selected_candidate=candidate))
        row,_=self.h.store.reserve(self.h.run_id,'native-selected-fixture',digest(plan),self.h.actor,zero())
        ref=save(self.h,dict(request_id=row['request_id'],original_plan=plan),'original_research_plan')
        detail=dict(operation='mujoco_nonlinear_task_capability_v1',formal_execution_authorized=True,
            planning_status='ready',request_template=dict(candidate=candidate,model_source='mujoco',protocol={'version':'fixture'}),required_parameters=[])
        update(self.h,plans=[ref])
        with patch('tools.research.task_constraints.mathematical_method_view',return_value={'methods':{method:detail}}):
            self.assertIsNone(selected_analysis(self.h,{}))
            self.h.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=self.h.actor,
                tool_id='research.core_plan',tool_version='1.0.0',execution_status='completed',charged=zero()),dict(result={}))
            selection=selected_analysis(self.h,{})
        self.assertEqual(selection,(method,detail))
        schema=selected_analysis_schema(*selection)
        self.assertEqual(schema['properties']['candidate']['const'],candidate)
        self.assertEqual(schema['properties']['protocol']['const'],{'version':'fixture'})
        self.assertNotIn('nonlinear_response',schema['properties'])

    def test_automatic_physics_math_search_and_rl_reports_preserve_f0_facts(self):
        before=state(self.h);reference=self.physical()
        auto=reporter.scientific_feedback(self.h,dict(result=dict(reference=reference)),before)
        self.assertNotIn('report',auto)
        self.assertEqual(auto['scientific_result_reference'],reference)
        self.assertTrue(auto['independent_physical_evaluation'])
        self.assertEqual(auto['task_acceptance'],'measured_failure')
        self.assertEqual(self.h.store.artifact(auto['report_reference'])['report']['mode'],'result_summary')
        speed=next(m for m in self.h.store.artifact(auto['report_reference'])['report']['results'][0]['metrics'] if m['name']=='holding_speed')
        self.assertEqual((speed['value'],speed['threshold'],speed['unit'],speed['passed']),(.04,.02,'m/s',False))
        baseline=self.h.store.artifact(reference);variant=deepcopy(baseline)
        variant['acceptance']['components']['holding_speed']['value']=.05
        other=self.put(variant);update(self.h,physical_replays=[reference,other])
        compared=reporter.assemble(self.h,[other]);self.assertTrue(compared.relations[0].comparable)
        self.assertIsNone(compared.relations[0].single_factor_attribution)
        changes=compared.results[0].deterministic_summary['comparisons'][0]['metrics']
        self.assertAlmostEqual(next(m for m in changes if m['metric']=='holding_speed')['delta'],.01)
        math=self.put(self.f.math_result());update(self.h,analysis_results=[math])
        math_feedback=reporter.scientific_feedback(self.h,dict(reference=math))
        self.assertFalse(math_feedback['independent_physical_evaluation'])
        self.assertEqual(math_feedback['task_acceptance'],'unmeasured')
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
        self.assertNotIn('report',result)
        self.assertEqual(result['result_count'],1)
        self.assertEqual(self.h.store.artifact(result['report_reference'])['report']['question'],request['question'])
        self.assertEqual(self.h.store.artifact(result['report_reference'])['report']['mode'],'investigation')
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
        self.assertEqual(final['report']['results'],self.h.store.artifact(initial['report_reference'])['report']['results'])
        self.assertEqual(self.h.store.artifact(reference),before)
        self.assertEqual(self.h.store.remaining()['used']['model_calls'],1)
        self.assertEqual(len(sent[0]['messages']),2);self.assertNotIn('tools',sent[0])
        reception=next(self.h.store.artifact(e['outputs'][0]) for e in reversed(self.h.store.events(self.h.run_id)) if e['kind']=='r3_response')
        self.assertEqual(reception['purpose'],'reporter');self.assertEqual(reception['usage']['total_tokens'],20)
        self.assertNotIn('unconsumed_response',state(self.h)['pilot'])
        self.assertEqual(state(self.h).get('evaluation_reads',[]),[])
        self.assertNotIn(final['report'],[self.h.store.artifact(r) for r in registered_references(self.h)])

    def test_reporter_projected_reads_keep_views_and_raw_citations(self):
        reference=self.physical()
        queries=[dict(reference=reference,view='working_set',pointer='/control_result_links'),
            dict(reference=self.f.candidate,view='mathematical_capabilities',pointer='/methods')]
        from tools.research.contracts import EvidenceQuery
        queries=[plain(EvidenceQuery.model_validate(q)) for q in queries]
        original=reporter.read_evidence
        def read(host,query,**kwargs):
            if query in queries:return {'fixture_projected_value':query['view']}
            return original(host,query,**kwargs)
        with patch.object(reporter,'read_evidence',side_effect=read):
            initial=reporter.investigate(self.h,dict(question='Projected evidence fixture',
                references=[reference],reads=queries))
            wire=reporter._wire(self.h,initial['report_reference'],self.h.store.artifact(initial['report_reference']))
            payload=json.loads(wire['messages'][-1]['content'])
            delivered=[r['query'] for r in payload['selected_reads']]
            self.assertEqual(delivered[:len(queries)],queries)
            self.assertEqual(delivered[-1]['pointer'],'/diagnostic_relations')
            self.assertEqual(delivered[-1]['reference'],reference)
            for query in queries:
                self.assertIn(dict(reference=query['reference'],pointer=''),payload['source_catalog'].values())
                self.assertNotIn(dict(reference=query['reference'],pointer=query['pointer']),payload['source_catalog'].values())
            asyncio.run(reporter.complete_reports(self.h,httpx.MockTransport(reporter_response)))
        self.assertEqual(reporter.entries(self.h)[-1][1]['interpretation_status'],'available')
        self.assertEqual(self.h.store.remaining()['used']['model_calls'],1)
        self.assertEqual(state(self.h).get('evaluation_reads',[]),[])

    def test_reporter_preparation_failure_keeps_deterministic_report_without_send(self):
        reference=self.physical()
        initial=reporter.investigate(self.h,dict(question='Preparation failure fixture',references=[reference]))
        with patch.object(reporter,'_wire',side_effect=KeyError('fixture_invalid_pointer')):
            asyncio.run(reporter.complete_reports(self.h,httpx.MockTransport(
                lambda request:(_ for _ in ()).throw(AssertionError('No send')))))
        final=reporter.entries(self.h)[-1][1]
        self.assertEqual(final['interpretation_status'],'unavailable')
        self.assertEqual(final['report'],self.h.store.artifact(initial['report_reference'])['report'])
        self.assertIn('fixture_invalid_pointer',final['error'])
        self.assertEqual(self.h.store.remaining()['used']['model_calls'],0)

    def test_handoff_large_method_read_preserves_bounded_execution_fields(self):
        from tools.research.session_handoff import feedback_delivery
        template=dict(candidate=self.physical(),operation='mujoco_direct_control_v1',protocol={'fixture':True})
        fields=dict(request_template=template,execution_limits=dict(evaluation_requests=24,iterations=3,knots_s=4),
            required_parameters=['fixture source/settings'],measured_control_initialization={'fixture':True})
        original={'fixture_large_detail':'x'*8000,**fields}
        use=dict(toolUseId='fixture-large-method',name='evidence_read',input=dict(view='mathematical_capabilities'))
        record(self.h,'model_original_tool_feedback',dict(tool_use=use,
            result=dict(status='success',content=[dict(text=json.dumps(original))])))
        row=feedback_delivery(self.h,[use['toolUseId']])['items'][0]
        self.assertEqual(row['delivery'],'summary_only')
        for key,value in fields.items():self.assertEqual(row['facts'][key],value)
        self.assertLessEqual(len(json.dumps(row['facts']).encode()),3000)
        self.assertEqual(read_evidence(self.h,row['original_result_query'],record_read=False)['content'][0]['text'],json.dumps(original))

    def test_invalid_or_truncated_interpretation_falls_back_without_scientific_reexecution(self):
        reference=self.physical();before=self.h.store.artifact(reference)
        for malicious,finish in ((True,'stop'),(False,'length')):
            initial=reporter.investigate(self.h,dict(question='Fixture '+finish,references=[reference]))
            with patch('tools.research.core.dispatch',side_effect=AssertionError('No science')):
                asyncio.run(reporter.complete_reports(self.h,httpx.MockTransport(
                    lambda request:reporter_response(request,malicious=malicious,finish=finish))))
            final=reporter.entries(self.h)[-1][1]
            self.assertEqual(final['interpretation_status'],'unavailable')
            self.assertEqual(final['report'],self.h.store.artifact(initial['report_reference'])['report'])
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

    def test_legacy_saved_reporter_response_recovers_without_resend_or_new_charge(self):
        from tools.research.agent import received
        reference=self.physical();reporter.investigate(self.h,dict(question='Recover fixture',references=[reference]))
        ref,saved=reporter.entries(self.h)[0];wire=reporter._wire(self.h,ref,saved)
        payload=json.loads(wire['messages'][-1]['content'])
        payload.pop('source_catalog');payload.pop('score_comparisons')
        wire['messages'][-1]['content']=json.dumps(payload)
        wire['messages'][0]['content']='Legacy Reporter contract: '+json.dumps(reporter.InterpretationResponse.model_json_schema())
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

    def test_source_ids_reject_unknown_malformed_and_raw_locations_preserving_l2(self):
        reference=self.physical()
        result=reporter.investigate(self.h,dict(question='ID boundary fixture',references=[reference],
            reads=[dict(reference=reference,pointer='/acceptance',view='fields',fields=['components'])]))
        base=result['report_reference'];saved=self.h.store.artifact(base)
        wire=reporter._wire(self.h,base,saved);payload=json.loads(wire['messages'][-1]['content'])
        self.assertIn(dict(reference=reference,pointer='/acceptance'),payload['source_catalog'].values())
        for invalid in (dict(source_ids=['S999999']),dict(source_ids=['/trajectory/score_semantics']),
                dict(source_ids=[]),dict(source_ids=[1]),dict(sources=[dict(reference=reference,pointer='')])):
            with self.subTest(invalid=invalid):
                response=httpx.Response(200,json=dict(choices=[dict(finish_reason='stop',message=dict(
                    content=json.dumps(dict(interpretations=[dict(kind='new_information',text='Fixture',**invalid)]))))]))
                ref=reporter._finish(self.h,SimpleNamespace(last_request='offline-fixture'),wire,response)
                final=self.h.store.artifact(ref)
                self.assertEqual(final['interpretation_status'],'unavailable')
                self.assertEqual(final['report'],saved['report'])
        self.assertEqual(self.h.store.remaining()['used']['model_calls'],0)

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
        from tools.research.research_context import research_action_trace
        trace=research_action_trace(self.h)
        self.assertEqual(trace['total'],1)
        entry=trace['recent'][0]
        self.assertEqual(read_evidence(self.h,entry['source'],record_read=False),plan)
        self.assertEqual(entry['agent_hypothesis']['hypothesis'],'Damping may reduce speed')
        self.assertEqual(entry['result_references'],[reference])
        self.assertEqual(entry['receipt_output'],json.loads(self.h.store.lookup(self.h.run_id,key)['receipt'])['output'])
        # Rejected research is retained; ordinary reads are not new research actions.
        for name in ('evidence_read','research_analysis'):
            record(self.h,'tool_request_error',dict(tool_use=dict(name=name,toolUseId=name,input={'operation':'fixture'}),error='fixture'))
        trace=research_action_trace(self.h)
        self.assertEqual((trace['total'],trace['failed_or_rejected']),(2,1))
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
                self.assertIn('CURRENT_RESEARCH_PACKET',agent.messages[0]['content'][0]['text'])
                self.assertNotIn('latest_reports',agent.messages[0]['content'][0]['text'])
                from tools.research.agent import decision_packet
                packet=decision_packet(h)
                intent=packet['research']['research_intent']['last_research']
                if intent.get('same_as')=='research_intent.latest_decision':intent=packet['research']['research_intent']['latest_decision']
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

    def test_native_investigation_delivers_l1_before_next_model_in_same_invocation(self):
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
            if len(main)==2:
                self.assertEqual(len(sent),3)  # main -> Reporter -> main, same invocation
                self.assertIn('latest_reports',wire['messages'][-1]['content'])
                self.assertIn('available',wire['messages'][-1]['content'])
                update(h,research_status='stopped')
            return response(request)
        with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                patch('tools.research.core.guard'),patch('tools.research.agent.guard'),\
                patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(respond)):
            asyncio.run(converse(h,session_handoff=True))
        self.assertEqual(len(sent),3);self.assertEqual(len(main),2)
        feedback=[h.store.artifact(e['outputs'][0]) for e in h.store.events(h.run_id) if e['kind']=='model_original_tool_feedback']
        self.assertEqual(feedback[0]['result']['toolUseId'],'original-investigation-id')
        self.assertEqual(feedback[0]['result']['status'],'success')
        self.assertIsNotNone(h.store.lookup(h.run_id,'native-original-investigation-id')['receipt'])
        usage=reporter.provider_usage(h)
        self.assertEqual((usage['conversation']['prompt_tokens'],usage['reporter']['prompt_tokens']),(20,17))
        self.assertEqual(h.store.remaining()['used']['model_calls'],3)
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)
        self.assertEqual(state(h).get('evaluation_reads',[]),[])
        events=h.store.events(h.run_id)
        sequence=[e['kind'] for e in events if e['kind'] in ('r3_request','r3_response_processing',
            'research_report','model_original_tool_feedback','science_delivery_boundary','reporter_completed','model_decision_packet')]
        self.assertLess(sequence.index('model_original_tool_feedback'),sequence.index('science_delivery_boundary'))
        self.assertLess(sequence.index('science_delivery_boundary'),sequence.index('reporter_completed'))
        self.assertLess(sequence.index('reporter_completed'),len(sequence)-1-sequence[::-1].index('model_decision_packet'))
        self.assertEqual(main[0]['messages'][0],main[1]['messages'][0])
        self.assertTrue(main[1]['messages'][-1]['content'].startswith('CURRENT_RESEARCH_PACKET\n'))
        self.assertEqual(sum(isinstance(m.get('content'),str) and m['content'].startswith('CURRENT_RESEARCH_PACKET\n') for m in main[1]['messages']),1)
        self.assertNotIn('report',json.loads(feedback[0]['result']['content'][0]['text']))
        atomic_json(h.store.root/'reporting_measurements.json',dict(usage=usage,report=reporter.entries(h)[-1][1]))

    def test_native_science_tool_reporter_boundary_and_unknown_send(self):
        """Saved B fixture behind a mocked executor; actual SDK and HTTP boundary."""
        from tests.research.s129_provider_check import prepare
        from tools.research.analysis import compact_result
        from tools.research.agent import build_harness, live_model_class, pending
        from tools.research.research_context import research_action_trace
        from strands.tools.executors import SequentialToolExecutor
        from strands.types.exceptions import EventLoopException
        for outcome in ('available','invalid_pointer','unknown','interrupted'):
            with self.subTest(outcome=outcome):
                h,refs=prepare(False);raw=deepcopy(h.store.artifact(refs[1]))
                raw['fixture']='offline native delivery '+outcome
                query=raw['requested_operation'];sent=[];executions=[];snapshots=[]
                def execute(host,request,key,**kwargs):
                    executions.append(key)
                    row,_=host.store.reserve(host.run_id,key+'-analysis',digest(query),host.actor,zero())
                    receipt=host.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],
                        caller=host.actor,tool_id='research.candidate_analysis',tool_version='1.0.0',
                        execution_status='completed',charged=zero()),raw)
                    ref=save(host,raw,'saved_B_delivery_fixture')
                    update(host,analysis_results=[*state(host)['analysis_results'],ref])
                    return compact_result(raw,ref)
                def respond(request):
                    wire=json.loads(request.content);role='main' if wire.get('tools') else 'reporter';sent.append(role)
                    if role=='reporter':
                        self.assertFalse(state(h)['pilot'].get('unconsumed_response'))
                        self.assertEqual(len(pending(h)),1)  # current Reporter reservation only
                        # Independently reopen SDK at the saved intra-invocation boundary.
                        boundary=LiveBoundary(h,httpx.MockTransport(lambda r: self.fail('No replay send')))
                        reopened=build_harness(h,transport=boundary,api_key='offline',instructions='fixture',
                            model_class=live_model_class(boundary),research_tools=[],tool_executor=SequentialToolExecutor(),
                            configuration_path=h.store.root/'reopen.json',session_directory=h.store.root/'framework_sessions')
                        self.assertFalse(unmatched(reopened.messages));snapshots.append(reopened.messages)
                        if outcome=='unknown':raise httpx.ReadError('Offline unknown Reporter outcome')
                        result=reporter_response(request)
                        if outcome=='invalid_pointer':
                            body=result.json();items=json.loads(body['choices'][0]['message']['content'])
                            items['interpretations'][0]['source_ids']=['/trajectory/score_semantics']
                            body['choices'][0]['message']['content']=json.dumps(items)
                            result=httpx.Response(200,json=body)
                        return result
                    if sent==['main']:
                        body=response(request).json();body['choices'][0].update(finish_reason='tool_calls',message=dict(
                            role='assistant',content=None,tool_calls=[dict(id='native-detail',type='function',function=dict(
                                name='evidence_read',arguments=json.dumps(dict(reference=refs[1],view='full')))),
                                dict(id='native-science',type='function',function=dict(
                                name='research_analysis',arguments=json.dumps(query)))]))
                        return httpx.Response(200,json=body)
                    packet=json.loads(wire['messages'][-1]['content'].split('CURRENT_RESEARCH_PACKET\n')[1])
                    latest=packet['research']['latest_reports'][-1]
                    self.assertEqual(latest['reporter_status'],'unavailable' if outcome=='invalid_pointer' else 'available')
                    self.assertEqual(latest['delivery_mode'],'deterministic_only' if outcome=='invalid_pointer' else 'reporter_interpreted')
                    self.assertEqual(latest['findings'][0]['mathematics']['capability']['score_comparisons']['comparisons'][0]['computed_score_direction'],'worse')
                    update(h,research_status='stopped');return response(request)
                original=[digest(h.store.artifact(r)) for r in refs]
                with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                        patch('tools.research.core.guard'),patch('tools.research.agent.guard'),\
                        patch('tools.research.analysis.dispatch',side_effect=execute),\
                        patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(respond)):
                    if outcome=='unknown':
                        with self.assertRaisesRegex(EventLoopException,'Offline unknown Reporter outcome'):asyncio.run(converse(h))
                        self.assertTrue(pending(h))
                        with self.assertRaisesRegex(ValueError,'UNKNOWN_PROVIDER'):asyncio.run(converse(h))
                    elif outcome=='interrupted':
                        with patch.object(reporter,'_finish',side_effect=RuntimeError('fixture before Reporter archive')):
                            with self.assertRaisesRegex(EventLoopException,'fixture before Reporter archive'):asyncio.run(converse(h))
                        self.assertTrue(state(h)['pilot'].get('unconsumed_response'))
                        before=h.store.remaining()['used']['model_calls']
                        latest=next((h.store.root/'framework_sessions'/'session'/state(h)['pilot']['framework_session_id']).rglob('snapshot_latest.json'))
                        original_snapshot=latest.read_bytes();tampered=json.loads(original_snapshot)
                        tampered['data']['messages'][0]['content'][0]['text']+=' tampered fixture'
                        atomic_json(latest,tampered)
                        with self.assertRaisesRegex(ValueError,'HISTORY'):asyncio.run(converse(h))
                        latest.write_bytes(original_snapshot)
                        asyncio.run(converse(h))
                        self.assertEqual(h.store.remaining()['used']['model_calls'],before+1)  # only next main
                    else:asyncio.run(converse(h))
                self.assertEqual(sent,['main','reporter'] if outcome=='unknown' else ['main','reporter','main'])
                self.assertEqual(executions,['native-native-science']);self.assertEqual(len(snapshots),1)
                self.assertEqual([digest(h.store.artifact(r)) for r in refs],original)
                self.assertEqual(h.store.remaining()['used']['backend_solves'],0)
                trace=research_action_trace(h)['recent'][-1]
                self.assertEqual(trace['action'],'research_analysis')
                self.assertEqual(trace['result_references'],[save(h,raw)])
                if outcome=='available':
                    audit=[]
                    for event in h.store.events(h.run_id):
                        if event['kind'] in ('r3_request','r3_response_processing','research_report',
                                'model_original_tool_feedback','science_delivery_boundary','reporter_completed','model_decision_packet'):
                            audit.append(dict(kind=event['kind'],status=event['status']))
                    atomic_json(Path('runs/f21_sdk_audit.json'),dict(study_id=h.run_id,event_order=audit,
                        provider_roles=sent,action_trace_example=trace,original_B_hashes_unchanged=True,
                        sdk_snapshot_independently_reopened=True,ledger=h.store.remaining(),
                        fixture='Mock HTTP and saved B results behind a mocked executor; no new scientific computation'))

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
