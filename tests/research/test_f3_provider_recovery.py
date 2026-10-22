"""Offline local loss fixtures: real Store, mock HTTP, no science or live send."""
import asyncio
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
import httpx
from tools.research.agent import LiveBoundary, DeepSeekModel, pending, received, record, provider_outcome
from tools.research.state import state, update, core_hashes
from tools.research.session_handoff import unmatched
from tools.platform_store import zero
from tools.state_io import atomic_json, digest, read
from tests.research.test_s125_contract import cold_host
from tests.research.f3_provider_recovery import inspect, apply, loss_disposition, ERROR


class ProviderLossRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.h=cold_host();s=state(self.h);update(self.h,freeze='offline-loss-fixture',core_hashes=core_hashes())
        use=dict(toolUseId='fixture-read',name='evidence_read',input={})
        feedback=dict(toolUseId='fixture-read',status='success',content=[dict(text='Explicit synthetic fixture feedback')])
        self.messages=[dict(role='user',content=[dict(text='Offline recovery fixture')]),
            dict(role='assistant',content=[dict(toolUse=use)]),dict(role='user',content=[dict(toolResult=feedback)])]
        record(self.h,'model_original_tool_request',dict(tool_use=use))
        record(self.h,'model_original_tool_feedback',dict(tool_use=use,result=feedback))
        self.path=self.h.store.root/'framework_sessions/session'/s['pilot']['framework_session_id']/'snapshot_latest.json'
        atomic_json(self.path,dict(data=dict(messages=self.messages,system_prompt=[dict(text='Offline stable rules')])) )
        self.wire=dict(model=s['pilot']['provider']['model'],thinking=dict(type=s['pilot']['provider']['thinking']),
            reasoning_effort=s['pilot']['provider']['reasoning_effort'],max_tokens=s['pilot']['provider']['max_tokens'],
            stream=False,messages=DeepSeekModel.format_request_messages(self.messages,'Offline stable rules')+
                [dict(role='user',content='CURRENT_RESEARCH_PACKET synthetic fixture')],
            tools=[dict(type='function',function=dict(name='evidence_read',parameters=dict(type='object',properties={})) )])
        self.sent=[]
        def fail(request):self.sent.append(request);raise httpx.ReadError('Explicit synthetic unknown send')
        self.boundary=LiveBoundary(self.h,httpx.MockTransport(fail))
        async def exercise():
            with self.assertRaises(httpx.ReadError):
                await self.boundary.handle_async_request(httpx.Request('POST',s['pilot']['provider']['base_url']+'/chat/completions',json=self.wire))
        asyncio.run(exercise());self.request_id=self.boundary.last_request
        self.dead=patch('tests.research.f3_provider_recovery.process_birth',return_value=None);self.dead.start();self.addCleanup(self.dead.stop)

    def approval(self):
        scope=inspect(self.h,self.request_id)
        return dict(version='provider_response_loss_authorization_v1',user_approval=True,
            source='Explicit offline fixture, no live authorization',scope=scope,scope_identity=digest(scope))

    def test_loss_keeps_costs_state_history_and_unknown_remote_outcome(self):
        approval=self.approval();before=deepcopy(state(self.h));ledger=self.h.store.remaining()
        events=self.h.store.events(self.h.run_id);snapshot=self.path.read_bytes()
        result=apply(self.h,approval)
        self.assertFalse(result['already_applied']);self.assertEqual(result['receipt']['execution_status'],'failed')
        self.assertEqual(result['receipt']['error'],ERROR)
        self.assertEqual(state(self.h),before);self.assertEqual(self.path.read_bytes(),snapshot)
        self.assertEqual(self.h.store.remaining()['used'],ledger['used'])
        self.assertEqual(self.h.store.remaining()['remaining'],ledger['remaining'])
        self.assertEqual(self.h.store.remaining()['occupied'],{})
        self.assertEqual(pending(self.h),[]);self.assertIsNone(received(self.h,self.request_id))
        self.assertTrue(provider_outcome(self.h,self.request_id)['outcome_unknown'])
        self.assertEqual(self.h.store.events(self.h.run_id)[:len(events)],events)
        self.assertEqual(len(self.sent),1);self.assertFalse(unmatched(self.messages))
        value=loss_disposition(self.h,self.h.store.lookup(self.h.run_id,self.request_id))
        self.assertEqual(value['remote_outcome'],'unknown')
        count=len(self.h.store.events(self.h.run_id));repeated=apply(self.h,approval)
        self.assertTrue(repeated['already_applied']);self.assertEqual(len(self.h.store.events(self.h.run_id)),count)

    def test_next_send_is_new_and_charged_in_original_total(self):
        apply(self.h,self.approval())
        def complete(request):
            self.sent.append(request)
            return httpx.Response(200,json=dict(id='offline-new-completion',choices=[dict(index=0,
                finish_reason='stop',message=dict(role='assistant',content='Offline new decision'))],usage={}))
        b=LiveBoundary(self.h,httpx.MockTransport(complete))
        async def exercise():
            await b.handle_async_request(httpx.Request('POST',state(self.h)['pilot']['provider']['base_url']+'/chat/completions',json=self.wire))
            self.assertNotEqual(b.last_request,self.request_id)
            self.assertEqual(self.h.store.remaining()['used']['model_calls'],2)
            self.assertEqual(self.h.store.remaining()['used']['backend_solves'],0)
            b.consumed();await b.aclose()
        asyncio.run(exercise());self.assertEqual(len(self.sent),2)

    def test_approval_or_scope_change_is_rejected_without_settlement(self):
        approval=self.approval();before=self.h.store.remaining()
        for mutate in (lambda a:a.update(user_approval=False),lambda a:a.update(scope_identity='wrong'),
                lambda a:a['scope'].update(request_hash='wrong'),lambda a:a['scope'].update(study_id='other')):
            bad=deepcopy(approval);mutate(bad)
            if bad.get('scope_identity')!='wrong':bad['scope_identity']=digest(bad['scope'])
            with self.assertRaises(ValueError):apply(self.h,bad)
            self.assertEqual(self.h.store.remaining(),before)
            self.assertIsNone(self.h.store.lookup(self.h.run_id,self.request_id)['receipt'])

    def test_live_owner_and_changed_sdk_history_block_disposition(self):
        with patch('tests.research.f3_provider_recovery.process_birth',return_value=123):
            with self.assertRaisesRegex(ValueError,'EXITED_MAIN'):inspect(self.h,self.request_id)
        data=read(self.path);data['data']['messages'][0]['content'][0]['text']='Tampered offline fixture'
        atomic_json(self.path,data)
        with self.assertRaisesRegex(ValueError,'WIRE_HISTORY_MISMATCH'):inspect(self.h,self.request_id)

    def test_active_worker_and_saved_response_require_their_original_recovery(self):
        update(self.h,pending=dict(kind='fixture-worker'))
        with self.assertRaisesRegex(ValueError,'SETTLED_ACTIVE'):inspect(self.h,self.request_id)
        update(self.h,pending=None)
        record(self.h,'r3_response',dict(http_status=200))
        with patch('tests.research.f3_provider_recovery.received',return_value=dict(http_status=200)):
            with self.assertRaisesRegex(ValueError,'SAVED_RESPONSE'):inspect(self.h,self.request_id)

    def test_settlement_exception_rolls_back_receipt_authorization_and_costs(self):
        approval=self.approval();before=self.h.store.remaining();events=self.h.store.events(self.h.run_id)
        original=self.h.store.complete
        def interrupted(*args,**kwargs):
            original(*args,**kwargs)
            raise RuntimeError('Explicit offline transaction interruption')
        with patch.object(self.h.store,'complete',side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError,'transaction interruption'):apply(self.h,approval)
        self.assertIsNone(self.h.store.lookup(self.h.run_id,self.request_id)['receipt'])
        self.assertEqual(self.h.store.events(self.h.run_id),events)
        self.assertEqual(self.h.store.remaining(),before)


if __name__=='__main__':unittest.main()
