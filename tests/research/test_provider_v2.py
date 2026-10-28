"""Provider roles and real SDK with synthetic HTTP; no account/network checks."""
import asyncio
from copy import deepcopy
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import httpx
from tools.research import agent
from tools.research.provider import (credential, request_settings, validate_provider,
    discover_models, model_messages, LiveBoundary, pending, IncompleteModelOutput)
from tools.research.config import role_provider
from tools.research.provider_context import capacity_estimate,handoff_input_estimate
from tools.research.state import state,update
from tests.research.test_harness_v2 import v2_host


def gateway(h):
    provider=deepcopy(state(h)['pilot']['provider'])
    provider.update(adapter='chatgpt_gateway',base_url='http://127.0.0.1:8787/v1',model='synthetic-account-model',
        max_tokens=None,reasoning='none',model_capabilities=dict(model='synthetic-account-model',tools=True,
            reasoning=['none','medium'],verification='offline_contract',catalog_source='synthetic model directory',max_request_bytes=1048576))
    return provider


class ProviderV2Tests(unittest.TestCase):
    def test_empty_sdk_history_distinguishes_shared_non_sdk_accounting(self):
        from tools.research.session_handoff import trusted_history
        from tools.research.provider import record
        h=v2_host();sdk=SimpleNamespace(messages=[],
            _session_manager=SimpleNamespace(session_id=state(h)['pilot']['framework_session_id']))
        before=h.store.remaining()
        for purpose in ('provider_validation','reporter'):
            record(h,'r3_request',dict(purpose=purpose))
            self.assertEqual(trusted_history(h,sdk),'empty')
        self.assertEqual(h.store.remaining(),before)
        for purpose in ('conversation','summarization','unknown'):
            ref=record(h,'p4_synthetic_metadata',dict(purpose=purpose))
            with patch.object(h.store,'events',return_value=[dict(kind='r3_request',outputs=[ref])]):
                with self.assertRaisesRegex(ValueError,'NO_TRUSTED_STORE_ANCHOR'):
                    trusted_history(h,sdk)
        sdk.messages=[dict(role='user',content=[dict(text='Untrusted suffix')])]
        with self.assertRaisesRegex(ValueError,'NO_TRUSTED_STORE_ANCHOR'):trusted_history(h,sdk)

    def test_gateway_completed_reasoning_reuses_original_receipt(self):
        h=v2_host();p=deepcopy(state(h)['pilot']);p['provider']=gateway(h);update(h,pilot=p)
        calls=[dict(id='opaque-call',type='function',function=dict(name='evidence_read',arguments='{}'))]
        output=[dict(type='reasoning',summary=[],encrypted_content='opaque-fixture'),
            dict(type='function_call',namespace='research',name='evidence_read',arguments='{}',call_id='opaque-call',status='completed')]
        with h.store.transaction() as db:
            body=h.store.put(db,json.dumps(dict(choices=[dict(message=dict(role='assistant',tool_calls=calls,provider_output=output))])).encode(),media='application/octet-stream')
            meta=h.store.put(db,dict(http_status=200,body=body.model_dump(mode='json')))
            h.store.event(db,h.run_id,'r3_response','metadata_saved',outputs=[meta])
        messages=[dict(role='assistant',content=[dict(toolUse=dict(toolUseId='opaque-call',name='evidence_read',input={}))])]
        before=h.store.remaining();wire=model_messages(h,messages)
        self.assertEqual(wire[0]['provider_output'],output)
        self.assertNotIn('reasoning_content',wire[0]);self.assertEqual(h.store.remaining(),before)
    def test_reporter_uses_independent_gateway_model_and_english_sources(self):
        from tests.research.test_s129_agent_reporting import AgentReportingTests,reporter_response
        from tools.research import reporter
        AgentReportingTests.setUpClass();case=AgentReportingTests();case.setUp()
        self.addCleanup(case.doCleanups)
        h=case.h;g=gateway(h);s=state(h);spec=deepcopy(s['spec']);p=deepcopy(s['pilot'])
        path=h.store.root/'reporter-credential-fixture.json'
        path.write_text(json.dumps(dict(base_url='http://127.0.0.1:8787',api_key='synthetic-key',model=None)))
        spec['runtime']['credentials_reference']=str(path)
        spec['research_decisions']=dict(architecture='english_decision_v2',
            language_policy=dict(version='english_sources_v1',authored_language='en'),
            role_policy=dict(version='research_roles_v3',main=dict(reasoning='none'),
                reporter=dict(model='synthetic-reporter-model',reasoning='medium',
                    model_capabilities={**g['model_capabilities'],'model':'synthetic-reporter-model'})))
        p['provider']=g;update(h,spec=spec,pilot=p)
        ref=case.physical();reporter.investigate(h,dict(question='Explain this saved fixture with uncertainty.',references=[ref]))
        original=h.store.artifact(ref);wires=[]
        def reply(request):
            wires.append(json.loads(request.content));return reporter_response(request)
        asyncio.run(reporter.complete_reports(h,httpx.MockTransport(reply)))
        self.assertEqual(wires[0]['model'],'synthetic-reporter-model')
        self.assertEqual(wires[0]['reasoning_effort'],'medium');self.assertNotIn('thinking',wires[0])
        self.assertIn('Write directly in English',wires[0]['messages'][0]['content'])
        self.assertEqual(reporter.entries(h)[-1][1]['interpretation_status'],'available')
        self.assertEqual(h.store.artifact(ref),original)
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)

    def test_gateway_unknown_send_blocks_retry_and_truncation_executes_nothing(self):
        for failure in ('unknown','truncated'):
            h=v2_host();p=deepcopy(state(h)['pilot']);p['provider']=gateway(h);update(h,pilot=p)
            sends=[]
            def reply(request):
                sends.append(request)
                if failure=='unknown':raise httpx.ReadTimeout('Synthetic uncertain transport.')
                return httpx.Response(200,json=dict(choices=[dict(finish_reason='length',message=dict(role='assistant',content='partial'))]))
            boundary=LiveBoundary(h,httpx.MockTransport(reply))
            wire=dict(**request_settings(p['provider']),messages=[dict(role='user',content='Synthetic input.')])
            async def run():
                request=httpx.Request('POST',p['provider']['base_url']+'/chat/completions',json=wire)
                with self.assertRaises(httpx.ReadTimeout if failure=='unknown' else IncompleteModelOutput):
                    await boundary.handle_async_request(request)
                if failure=='unknown':
                    self.assertEqual(len(pending(h)),1)
                    with self.assertRaisesRegex(ValueError,'UNCONFIRMED_ATTEMPT'):
                        await boundary.handle_async_request(request)
                await boundary.aclose()
            asyncio.run(run())
            self.assertEqual(len(sends),1);self.assertEqual(h.store.remaining()['used']['model_calls'],1)
            self.assertEqual(h.store.remaining()['used']['backend_solves'],0)

    def test_roles_construct_provider_specific_parameters(self):
        h=v2_host();base=state(h)['pilot']['provider']
        policy=dict(research_decisions=dict(role_policy=dict(version='research_roles_v3',
            main=dict(reasoning='none'),reporter=dict(reasoning='medium'))))
        main=request_settings(role_provider(policy,base,'conversation'))
        reporter=request_settings(role_provider(policy,base,'reporter'))
        self.assertEqual(main['thinking'],dict(type='disabled'))
        self.assertEqual(reporter['reasoning_effort'],'high')
        g=gateway(h);validate_provider(g)
        self.assertNotIn('thinking',request_settings(g))
        self.assertEqual(request_settings({**g,'reasoning':'medium'})['reasoning_effort'],'medium')
        with self.assertRaisesRegex(ValueError,'NOT_VERIFIED'):
            validate_provider({**g,'reasoning':'medium','model_capabilities':{**g['model_capabilities'],'reasoning':['none']}})
        with self.assertRaisesRegex(ValueError,'ACCOUNT_MODEL'):
            validate_provider({**g,'model':'different-model'})

    def test_gateway_credentials_capacity_and_discovery_are_explicit(self):
        h=v2_host();g=gateway(h);path=h.store.root/'credential-fixture.json'
        path.write_text(json.dumps(dict(base_url='http://127.0.0.1:8787',api_key='synthetic-key',model=None)))
        self.assertEqual(credential(g,path),'synthetic-key')
        with self.assertRaisesRegex(ValueError,'ENDPOINT_MISMATCH'):
            credential({**g,'base_url':'http://example.invalid/v1'},path)
        self.assertEqual(handoff_input_estimate(b'English',g)['method'],'serialized_utf8_byte_upper_estimate')
        with self.assertRaisesRegex(ValueError,'BODY_TOO_LARGE'):capacity_estimate(b'x'*1048577,g)
        sent=[]
        def catalog(request):
            sent.append(request);return httpx.Response(200,json=dict(data=[dict(id='synthetic-account-model')]))
        result=asyncio.run(discover_models(g,'synthetic-key',transport=httpx.MockTransport(catalog)))
        self.assertEqual(len(sent),1);self.assertEqual(result['pricing'],'unknown')
        self.assertIn('separate_verification',result['tool_support'])

    def test_gateway_tool_feedback_and_handoff_have_no_deepseek_fields(self):
        h=v2_host();g=gateway(h);s=state(h);spec=deepcopy(s['spec']);pilot=deepcopy(s['pilot'])
        path=h.store.root/'gateway-fixture.json';path.write_text(json.dumps(dict(base_url='http://127.0.0.1:8787',api_key='synthetic-key',model=None)))
        spec['runtime']['credentials_reference']=str(path)
        spec['research_decisions']['role_policy']=dict(version='research_roles_v3',main=dict(reasoning='none'),reporter=dict(reasoning='medium'))
        spec['research_decisions']['language_policy']=dict(version='english_sources_v1',authored_language='en')
        pilot['provider']=g;update(h,spec=spec,pilot=pilot);wires=[]
        def reply(request):
            w=json.loads(request.content);wires.append(w)
            m=dict(role='assistant',content='Synthetic completed decision.')
            if len(wires)==1:
                m.update(content=None,tool_calls=[dict(id='gateway-read',type='function',function=dict(name='research_plan',arguments=json.dumps(dict(action='stop'))))])
            return httpx.Response(200,json=dict(id='synthetic',object='chat.completion',created=1,model=w['model'],
                choices=[dict(index=0,finish_reason='tool_calls' if len(wires)==1 else 'stop',message=m)]))
        with patch('tools.research.core.guard'),patch('tools.research.agent.guard'),\
                patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(reply)):
            asyncio.run(agent.converse(h,pause_after_completed_invocations=1))
            before=h.store.remaining()['used']
            asyncio.run(agent.converse(h,restore_only=True))
        self.assertEqual(len(wires),2);self.assertEqual(before,h.store.remaining()['used'])
        self.assertNotIn('synthetic-key',(h.store.root/'framework_configuration.json').read_text(encoding='utf8'))
        self.assertTrue(all('thinking' not in w and 'max_tokens' not in w for w in wires))
        self.assertTrue(all(w['reasoning_effort']=='none' for w in wires))
        self.assertTrue(all('reasoning_content' not in m for w in wires for m in w['messages']))
        feedback=json.loads(wires[1]['messages'][-1]['content'].split('\n',1)[1])['research']['research_state']['pending_feedback']
        self.assertEqual(feedback['items'][0]['tool_id'],'gateway-read')
        self.assertEqual(feedback['items'][0]['status'],'error')
        receptions=[h.store.artifact(e['outputs'][0]) for e in h.store.events(h.run_id) if e['kind']=='r3_response' and e['status']=='metadata_saved']
        self.assertTrue(all(r['usage'] is None and r['money'] is None for r in receptions))
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)



if __name__=='__main__':unittest.main()
