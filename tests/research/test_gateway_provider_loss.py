"""One Mock Gateway response-loss case; no live request or scientific execution."""
import asyncio
from copy import deepcopy
import json
import os
import shutil
import unittest
from unittest.mock import patch
import httpx
from tools.research.provider import LiveBoundary, model_messages, request_settings, record, pending, received
from tools.research.object_choices import main_projection
from tools.research.state import state, update, core_hashes
from tools.research.contracts import REGISTERED_MATHEMATICS_SCOPE
from tools.state_io import atomic_json, digest, io_path
from tests.research.test_research_authorization_preflight import fixture, approve
from tests.research.f3_provider_recovery import inspect, apply, loss_disposition

class GatewayProviderLossTests(unittest.TestCase):
    def test_projected_gateway_long_path_loss_preserves_original_sdk_and_charge(self):
        with fixture() as h:
            approve(h,[REGISTERED_MATHEMATICS_SCOPE])
            s=state(h);pilot=deepcopy(s['pilot']);pilot['framework_session_id']='gateway-loss-'+('x'*97)
            update(h,pilot=pilot,core_hashes=core_hashes())
            ref=s['public_prior_manifest']
            use=dict(toolUseId='gateway-fixture-read',name='evidence_read',input=dict(reference=ref,view='summary'))
            result=dict(toolUseId=use['toolUseId'],status='success',content=[dict(text='Offline prior read')])
            messages=[dict(role='user',content=[dict(text='Offline Gateway fixture')]),dict(role='assistant',content=[dict(toolUse=use)]),dict(role='user',content=[dict(toolResult=result)])]
            record(h,'model_original_tool_request',dict(tool_use=use))
            record(h,'model_original_tool_feedback',dict(tool_use=use,result=result))
            path=h.store.root/'framework_sessions/session'/pilot['framework_session_id']/'scopes/agent/default/snapshots/snapshot_latest.json'
            if os.name=='nt':self.assertGreater(len(str(path)),260)
            try:
                atomic_json(path,dict(data=dict(messages=messages)))
                formatted=model_messages(h,messages,'Offline stable rules');projected=main_projection(h,formatted)
                self.assertNotEqual(formatted,projected)
                wire=dict(**request_settings(pilot['provider']),messages=projected+[dict(role='user',content='CURRENT_RESEARCH_PACKET\n{}')],tools=[dict(type='function',function=dict(name='evidence_read',parameters=dict(type='object',properties={})))],tool_choice='auto')
                sent=[]
                def fail(request):sent.append(request);raise httpx.ReadError('Mock Gateway delivery loss')
                boundary=LiveBoundary(h,httpx.MockTransport(fail))
                async def send():
                    with self.assertRaises(httpx.ReadError):await boundary.handle_async_request(httpx.Request('POST',pilot['provider']['base_url']+'/chat/completions',json=wire))
                asyncio.run(send());key=boundary.last_request
                before=deepcopy(state(h));ledger=h.store.remaining()
                with patch('tests.research.f3_provider_recovery.process_birth',return_value=None):
                    scope=inspect(h,key)
                    approval=dict(version='provider_response_loss_authorization_v1',user_approval=True,scope=scope,scope_identity=digest(scope),source='Explicit offline fixture only')
                    settled=apply(h,approval)
                    self.assertTrue(apply(h,approval)['already_applied'])
                self.assertEqual(settled['receipt']['tool_id'],'model.chatgpt_gateway')
                self.assertEqual(h.store.remaining()['used'],ledger['used'])
                self.assertEqual(state(h),before)
                self.assertEqual(len(sent),1);self.assertEqual(pending(h),[]);self.assertIsNone(received(h,key))
                self.assertEqual(loss_disposition(h,h.store.lookup(h.run_id,key))['remote_outcome'],'unknown')
            finally:
                target=h.store.root/'framework_sessions/session'/pilot['framework_session_id']
                assert target.resolve().is_relative_to(h.store.root.resolve())
                if io_path(target).exists():shutil.rmtree(io_path(target))
