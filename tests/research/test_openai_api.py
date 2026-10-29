"""Official API profile and real SDK with synthetic HTTP; no network or science."""
import asyncio
from copy import deepcopy
import json
import os
import unittest
from unittest.mock import patch
from openai import BadRequestError
import httpx
from tools.platform_tasks import compile_input
from tools.platform_registry import registry
from tools.research.config import ROOT, resolve
from tools.research.provider import credential, request_settings, discover_models, LiveBoundary, record
from tools.research.state import state, update
from tests.research.test_harness_v2 import v2_host


def runtime():
    return json.loads((ROOT/'configs/research/runtime_openai_api.json').read_text(encoding='utf8'))


class OpenAIAPITests(unittest.TestCase):
    def test_explicit_proxy_and_mock_catalog_stay_on_the_selected_transport(self):
        h=v2_host();s=state(h);p=runtime()['provider'];update(h,pilot={**s['pilot'],'provider':p})
        with patch('httpx.AsyncHTTPTransport') as transport:
            LiveBoundary(h)
            transport.assert_called_once_with(retries=0,proxy='http://127.0.0.1:7890')
        seen=[]
        def catalog(request):
            seen.append(str(request.url));return httpx.Response(200,json=dict(data=[dict(id=p['model'])]))
        result=asyncio.run(discover_models(p,'official-key-fixture',transport=httpx.MockTransport(catalog)))
        self.assertEqual(seen,['https://api.openai.com/v1/models'])
        self.assertEqual(result['models'],[dict(id=p['model'])])

    def test_explicit_profile_compiles_and_maps_official_parameters(self):
        p=runtime()['provider'];settings=request_settings({**p,'max_tokens':128})
        self.assertEqual(settings,dict(model='gpt-5.4-mini',stream=False,store=False,
            reasoning_effort='none',max_completion_tokens=128))
        spec=resolve(ROOT/'configs/research/study_harness_v2.json')
        cfg=deepcopy(spec['configuration']);cfg['policy']['model']=p
        self.assertIn('openai_api@8.0.0',list(compile_input(cfg,registry())['dependencies']))

    def test_credential_is_separate_and_empty_template_fails_before_network(self):
        h=v2_host();path=h.store.root/'official-key-fixture.json';p=runtime()['provider']
        path.write_text(json.dumps(dict(base_url=p['base_url'],api_key='')),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'OPENAI_API_KEY_MISSING'):credential(p,path)
        path.write_text(json.dumps(dict(base_url=p['base_url'],api_key='official-key-fixture')),encoding='utf8')
        with patch.dict(os.environ,{'DEEPSEEK_API_KEY':'different-provider-fixture','OPENAI_API_KEY':'different-environment-fixture'}):
            self.assertEqual(credential(p,path),'official-key-fixture')
        with self.assertRaisesRegex(ValueError,'OPENAI_API_CREDENTIAL_ENDPOINT_MISMATCH'):
            credential({**p,'base_url':'http://127.0.0.1:8787/v1'},path)

    def test_sdk_tool_loop_uses_only_selected_official_endpoint_and_shared_ledger(self):
        from tools.research.agent import converse
        h=v2_host();s=state(h);spec=deepcopy(s['spec']);r=runtime();p=r['provider']
        path=h.store.root/'official-key-fixture.json'
        path.write_text(json.dumps(dict(base_url=p['base_url'],api_key='official-key-fixture')),encoding='utf8')
        r['credentials_reference']=str(path);spec['runtime']=r
        spec['research_decisions']['role_policy']=dict(version='research_roles_v3',main=dict(reasoning='none'),reporter=dict(reasoning='none'))
        spec['research_decisions']['tool_schema_policy']=dict(version='on_demand_tools_v3')
        update(h,spec=spec,pilot={**s['pilot'],'provider':p})
        sends=[]
        def reply(request):
            wire=json.loads(request.content);sends.append(wire)
            self.assertEqual(str(request.url),'https://api.openai.com/v1/chat/completions')
            self.assertEqual(request.headers['authorization'],'Bearer official-key-fixture')
            self.assertEqual(wire['store'],False);self.assertEqual(wire['reasoning_effort'],'none')
            self.assertNotIn('thinking',wire);self.assertNotIn('api_key',wire)
            if len(sends)==1:
                return httpx.Response(400,json=dict(error=dict(code='invalid_function_parameters',
                    type='invalid_request_error',message='Synthetic rejected initial Schema.')))
            message=dict(role='assistant',content='Synthetic fixture feedback consumed.')
            if len(sends)==2:
                message.update(content=None,tool_calls=[dict(id='official-call-fixture',type='function',
                    function=dict(name='research_route',arguments='{"tool":"evidence_read"}'))])
            else:
                self.assertEqual(len(sends),3)
                self.assertTrue(any(m.get('tool_call_id')=='official-call-fixture' for m in wire['messages']))
                self.assertFalse(any('provider_output' in m for m in wire['messages']))
            return httpx.Response(200,json=dict(model=p['model'],choices=[dict(index=0,
                finish_reason='tool_calls' if len(sends)==2 else 'stop',message=message)]))
        with patch('tools.research.core.guard'),patch('tools.research.agent.guard'), \
                patch.dict(os.environ,r['threads']),patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(reply)):
            with self.assertRaises(BadRequestError):
                asyncio.run(converse(h,session_handoff=False,max_new_provider_requests=2))
            self.assertEqual(len(sends),1)
            with self.assertRaisesRegex(ValueError,'NO_TRUSTED_STORE_ANCHOR'):
                asyncio.run(converse(h,session_handoff=False,restore_only=True))
            record(h,'implementation_binding',dict(scope='Explicit offline Schema repair fixture.'),status='committed')
            asyncio.run(converse(h,session_handoff=False,max_new_provider_requests=2,pause_after_completed_invocations=1))
        self.assertEqual(len(sends),3)
        self.assertEqual(h.store.remaining()['used']['model_calls'],3)
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)


if __name__=='__main__':unittest.main()
