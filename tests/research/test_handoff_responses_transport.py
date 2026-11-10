"""Synthetic archived HTTP fixtures; no provider or scientific execution."""
import json
from types import SimpleNamespace
import unittest
from tools.research.openai_responses import chat_view
from tools.research.session_handoff import verified_request_transport

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

if __name__=='__main__':unittest.main()
