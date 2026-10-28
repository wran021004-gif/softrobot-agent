"""Focused offline binding/SDK regressions. Mock replies are not scientific evidence."""
import asyncio
from copy import deepcopy
import json
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx
from jsonschema import Draft202012Validator
from pydantic import ValidationError
from tools.research import agent, core
from tools.research.config import ROOT, resolve
from tools.research.contracts import AnalysisRequest
from tools.research.state import state, update
from tools.research.task_constraints import analysis_operating_points
from tests.research import main_off_live_probe as probe


class BoundAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.run_id='bound-analysis-offline-'+uuid4().hex[:10]
        cls.host=probe.prepare(ROOT/'runs/research'/cls.run_id,cls.run_id)

    def setUp(self):
        self.h=self.host
        self.auth=patch('tools.research.research_context.mathematics_authorization',
            return_value={'registered_study_scope_authorized':True,'methods':[]})
        self.auth.start();self.addCleanup(self.auth.stop)

    def select(self, method='native_dynamics_v1'):
        candidate=list(state(self.h)['candidates'].values())[-1]
        value=dict(action='diagnose',hypothesis='Offline fixture: inspect a local mechanism.',
            expected_observation='A local model diagnostic.',weakening_observation='Contrary local evidence.',
            fixed_conditions='Frozen candidate and task.',stopping_condition='No scientific execution.',
            interpretation='Fixture only; no computed conclusion.',
            decision=dict(hypothesis_id='offline-fixture',research_intent='DIAGNOSE',
                selected_candidate=candidate,selected_method=method))
        with patch('tools.research.core.guard',probe.safe_guard):
            core.dispatch(self.h,value,'offline-diagnose-'+uuid4().hex)
        selected=agent.selected_analysis(self.h,None)
        self.assertIsNotNone(selected)
        return selected

    def test_binding_schema_contract_and_provenance(self):
        method,detail=self.select()
        old=agent.selected_analysis_schema(method,detail)
        new=agent.selected_analysis_schema(method,detail,bound=True)
        for key in ('candidate','protocol','operation','model_source'):
            self.assertNotIn(key,new['properties']);self.assertIn(key,old['properties'])
        self.assertEqual(new['properties']['operating_point']['enum'],['standardized_initial_pretension','saved_state'])
        raw={'operating_point':'standardized_initial_pretension'}
        full=agent.bind_selected_analysis_request(self.h,raw,tool_use_id='offline-bound')
        self.assertEqual(raw,{'operating_point':'standardized_initial_pretension'})
        self.assertEqual(full['candidate'],detail['candidate'])
        self.assertEqual(full['protocol'],state(self.h)['spec']['analysis_protocol'])
        self.assertEqual(full['model_source'],'mujoco')
        Draft202012Validator(AnalysisRequest.model_json_schema()).validate(full)
        self.assertEqual(AnalysisRequest.model_validate(full).operation,method)
        event=next(e for e in reversed(self.h.store.events(self.h.run_id)) if e['kind']=='analysis_request_binding')
        audit=self.h.store.artifact(event['outputs'][0])
        self.assertEqual(set(audit['field_sources']),set(full))
        self.assertEqual(audit['raw_main_input'],raw)
        self.assertIn('does not diagnose the observed terminal state',new['description'])
        self.assertEqual(set(new['$defs']['NativeAnalysisOptions']['properties']),{'tensions_n'})
        sizes={name:len(json.dumps(schema,separators=(',',':')).encode()) for name,schema in [('legacy',old),('bound',new)]}
        agent.record(self.h,'offline_schema_measurement',dict(method=method,bytes=sizes,scope='Schema bytes only; no live cost comparison.'))

    def test_invalid_science_frozen_overrides_and_no_candidate_guess(self):
        self.select()
        for payload,code in [({'operating_point':'fixed_input_equilibrium'},'NATIVE_ANALYSIS_REQUIRES_EXACT_STATE'),
                ({'operating_point':'saved_state'},'SAVED_POINT_REQUIRES_UNAMBIGUOUS_STATE_SOURCE'),
                ({'operating_point':'standardized_initial_pretension','candidate':{}},'unsupported or frozen'),
                ({'operating_point':'standardized_initial_pretension','control_optimization':{}},'unsupported or frozen')]:
            with self.subTest(payload=payload),self.assertRaisesRegex((ValueError,ValidationError),code):
                agent.bind_selected_analysis_request(self.h,payload,tool_use_id='offline-invalid')
        original=deepcopy(state(self.h));update(self.h,plans=[])
        try:
            with self.assertRaisesRegex(ValueError,'SELECTED_AUTHORIZED_ANALYSIS_METHOD_REQUIRED'):
                agent.bind_selected_analysis_request(self.h,{'operating_point':'standardized_initial_pretension'},tool_use_id='no-decision')
        finally:update(self.h,plans=original['plans'])
        owned=deepcopy(original['candidates']);update(self.h,candidates={})
        try:self.assertIsNone(agent.selected_analysis(self.h,None))
        finally:update(self.h,candidates=owned)

    def test_method_specific_points_and_reduced_model_choice(self):
        method,detail=self.select('braking')
        schema=agent.selected_analysis_schema(method,detail,bound=True)
        self.assertNotIn('native',schema['properties'])
        self.assertEqual(schema['properties']['model_source']['enum'],['controller','gvs','sorosim'])
        self.assertIn('model_source',schema['required'])
        full=agent.bind_selected_analysis_request(self.h,dict(operating_point='controller_start_input',model_source='gvs'),tool_use_id='reduced')
        self.assertEqual(full['model_source'],'gvs')
        self.assertEqual(analysis_operating_points('input_sensitivity','input_sensitivity'),['fixed_input_equilibrium'])
        self.assertEqual(analysis_operating_points('instantaneous_braking_v1','instantaneous_braking_v1'),['saved_state'])
        self.assertEqual(analysis_operating_points('mujoco-nonlinear-task-capability-v1','mujoco_nonlinear_task_capability_v1'),['standardized_initial_pretension'])

    def test_mock_http_invalid_then_corrected_feedback_without_worker(self):
        self.select();sent=[]
        def respond(request):
            wire=json.loads(request.content);sent.append(wire)
            message=dict(role='assistant',content='Offline fixture: probe did not execute mathematics; no result or acceptance exists.')
            if len(sent)<3:
                message=dict(role='assistant',content=None,tool_calls=[dict(id='offline-analysis-'+str(len(sent)),type='function',
                    function=dict(name='research_analysis',arguments=json.dumps(dict(operating_point=
                        'fixed_input_equilibrium' if len(sent)==1 else 'standardized_initial_pretension'))))])
            return httpx.Response(200,json=dict(id='offline-response',object='chat.completion',created=1,model=wire['model'],
                usage=dict(prompt_tokens=10,completion_tokens=5,total_tokens=15),
                choices=[dict(index=0,finish_reason='tool_calls' if len(sent)<3 else 'stop',message=message)]))
        with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                patch('subprocess.Popen',side_effect=AssertionError('WORKER_MUST_NOT_START')):
            asyncio.run(probe.run(self.h,httpx.MockTransport(respond),max_requests=3))
        self.assertEqual(len(sent),3)
        schema=next(t['function']['parameters'] for t in sent[0]['tools'] if t['function']['name']=='research_analysis')
        self.assertNotIn('candidate',schema['properties']);self.assertNotIn('protocol',schema['properties'])
        self.assertIn('NATIVE_ANALYSIS_REQUIRES_EXACT_STATE_OR_FROZEN_INITIALIZATION',json.dumps(sent[1]['messages']))
        self.assertIn('probe_only_not_executed',json.dumps(sent[2]['messages']))
        events=self.h.store.events(self.h.run_id)
        outcome=self.h.store.artifact(next(e for e in reversed(events) if e['kind']=='probe_analysis_intercept')['outputs'][0])['outcome']
        self.assertTrue(outcome['typed_request_valid']);self.assertTrue(outcome['schema_valid'])
        self.assertEqual(outcome['deterministic_applicability']['status'],'applicable')
        self.assertIn('DEPENDENCIES_CHANGED',outcome['original_guard'])
        self.assertFalse(outcome['execution_feedback']['worker_started'])
        self.assertEqual(self.h.store.remaining()['used']['worker_calls'],0)
        self.assertEqual(self.h.store.remaining()['used']['backend_solves'],0)
        with patch('tools.research.core.guard',probe.safe_guard),patch('tools.research.agent.guard',probe.safe_guard),patch('tools.research.agent.load_credential'),\
                patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(respond)):
            asyncio.run(agent.converse(self.h,restore_only=True))
        self.assertEqual(len(sent),3)

    def test_budget_preserves_feedback_and_rejects_reporter(self):
        from unittest.mock import MagicMock
        fake=MagicMock();fake.run_id='offline-cap';fake.store.events.return_value=[]
        sends=[]
        transport=probe.CappedTransport(httpx.MockTransport(lambda r:sends.append(r) or httpx.Response(200,json={})),
            {'conversation':7,'reporter':0},host=fake)
        request=httpx.Request('POST','https://offline.invalid',json={'tools':[{}]})
        with self.assertRaisesRegex(ValueError,'FEEDBACK_TURN_RESERVED'):
            asyncio.run(transport.handle_async_request(request))
        self.assertEqual(sends,[])
        fake.store.events.return_value=[dict(kind='model_original_tool_feedback',outputs=[{}])]
        fake.store.artifact.return_value={'tool_use':{'name':'research_analysis'}}
        asyncio.run(transport.handle_async_request(request));self.assertEqual(len(sends),1)
        with self.assertRaisesRegex(ValueError,'ROLE_CAP'):
            asyncio.run(transport.handle_async_request(request))
        with self.assertRaisesRegex(ValueError,'ROLE_CAP'):
            asyncio.run(transport.handle_async_request(httpx.Request('POST','https://offline.invalid',json={})))
        before=self.h.store.remaining()
        async def boundary_attempt(host,**kwargs):
            boundary=agent.LiveBoundary(host,httpx.MockTransport(lambda r:self.fail('NO_NETWORK_SEND')))
            await boundary.handle_async_request(request)
        with patch.object(probe.reporter,'provider_usage',return_value={'conversation':{'requests':7}}),\
                patch.object(agent,'converse',side_effect=boundary_attempt),\
                self.assertRaisesRegex(ValueError,'FEEDBACK_TURN_RESERVED'):
            asyncio.run(probe.run(self.h,httpx.MockTransport(lambda r:self.fail('NO_NETWORK_SEND'))))
        self.assertEqual(self.h.store.remaining(),before)

    def test_opt_in_config_is_frozen_and_legacy_default_unchanged(self):
        old=resolve(ROOT/'configs/research/study_fresh_english_shared_reach_v1_pending.json')
        self.assertNotIn('analysis_interface',old['research_decisions'])
        self.assertFalse(agent.bound_analysis_enabled(old))
        path=ROOT/'configs/research'/('._bound_fixture_'+uuid4().hex+'.json')
        value=json.loads((ROOT/'configs/research/study_fresh_english_shared_reach_v1_pending.json').read_text())
        value['research_decisions']['analysis_interface']='bound_scientific_variables_v1'
        try:
            path.write_text(json.dumps(value),encoding='utf8');self.assertTrue(agent.bound_analysis_enabled(resolve(path)))
            value['research_decisions']['analysis_interface']='unversioned'
            path.write_text(json.dumps(value),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'VERSIONED_ENGLISH_ANALYSIS_INTERFACE_REQUIRED'):resolve(path)
        finally:path.unlink()


if __name__=='__main__':unittest.main()
