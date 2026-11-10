"""Synthetic archived HTTP fixtures; no provider or scientific execution."""
import json
from types import SimpleNamespace
import unittest
from tools.research.openai_responses import chat_view
from tools.research.session_handoff import verified_request_transport
from tools.research.provider import transport_endpoint

class ResponsesHandoffTransport(unittest.TestCase):
    def setUp(self):
        self.provider=dict(adapter='openai_api',base_url='https://api.openai.com/v1',model='fixture-model',reasoning='medium')
        self.meta=dict(protocol='openai_responses_v1',endpoint='https://api.openai.com/v1/responses',
            sdk_endpoint='https://api.openai.com/v1/chat/completions',upstream_request='request')
        self.reception=dict(protocol='openai_responses_v1',body_is_derived_chat_view=True,upstream_body='raw',body='chat')
        raw=json.dumps(dict(id='fixture',model='fixture-model',status='completed',output=[
            dict(type='function_call',call_id='fixture-call',name='evidence_read',arguments='{}')])).encode()
        self.artifacts=dict(request=dict(model='fixture-model',reasoning=dict(effort='medium')),raw=raw,chat=chat_view(raw))
        self.host=SimpleNamespace(store=SimpleNamespace(artifact=lambda ref,**kwargs:self.artifacts[ref]))

    def test_archived_responses_and_legacy_chat_transport_are_supported(self):
        self.assertTrue(verified_request_transport(self.host,self.provider,self.meta,self.reception))
        self.assertTrue(verified_request_transport(self.host,self.provider,
            dict(endpoint='https://api.openai.com/v1/chat/completions'),None))

    def test_wrong_endpoint_model_reasoning_and_derived_view_are_rejected(self):
        for field,value in [('endpoint','https://elsewhere/responses'),('sdk_endpoint','https://elsewhere/chat/completions')]:
            with self.subTest(field=field):
                self.assertFalse(verified_request_transport(self.host,self.provider,{**self.meta,field:value},self.reception))
        for changed in [dict(model='other',reasoning=dict(effort='medium')),dict(model='fixture-model',reasoning=dict(effort='none'))]:
            self.artifacts['request']=changed
            self.assertFalse(verified_request_transport(self.host,self.provider,self.meta,self.reception))
        self.setUp();self.artifacts['chat']=b'{"choices":[]}'
        self.assertFalse(verified_request_transport(self.host,self.provider,self.meta,self.reception))
        self.assertFalse(verified_request_transport(self.host,self.provider,self.meta,{**self.reception,'body_is_derived_chat_view':False}))

    def test_explicit_loopback_gateway_instances_share_only_protocol_evidence(self):
        provider={**self.provider,'adapter':'chatgpt_gateway','base_url':'http://127.0.0.1:8789/v1'}
        for port in (8787,8788,8789):
            base='http://127.0.0.1:'+str(port)+'/v1'
            self.assertTrue(transport_endpoint('chatgpt_gateway',base))
            self.assertTrue(verified_request_transport(self.host,provider,dict(endpoint=base+'/chat/completions'),None))
        for base in ('http://example.com:8789/v1','http://127.0.0.1:8789/wrong',
                'http://user@127.0.0.1:8789/v1','http://127.0.0.1:8789/v1?x=1',
                'http://127.0.0.1:8789/v1#x','http://127.0.0.1:99999/v1'):
            self.assertFalse(transport_endpoint('chatgpt_gateway',base))
            self.assertFalse(verified_request_transport(self.host,provider,dict(endpoint=base+'/chat/completions'),None))
        self.assertTrue(transport_endpoint('openai_api','https://api.openai.com/v1'))
        self.assertFalse(transport_endpoint('openai_api','https://elsewhere/v1'))

if __name__=='__main__':unittest.main()
