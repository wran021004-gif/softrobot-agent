"""Synthetic lost Main response at a committed handoff; no network or science."""
import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import httpx
from tools.research import provider
from tools.research.state import state, update, save
from tools.research.session_handoff import INVOCATION_PROMPT, session_storage_path, trusted_history, snapshot_files
from tests.research.test_p63g3_action_handoff import g3_host


class UnknownMainDispositionTests(unittest.TestCase):
    def setUp(self):
        self.h=g3_host();s=state(self.h);self.session=s['pilot']['framework_session_id']
        self.initial=[dict(role='user',content=[dict(text='Synthetic committed context; not scientific evidence.')])]
        self.messages=self.initial+[dict(role='user',content=[dict(text=INVOCATION_PROMPT)])]
        self.directory=self.h.store.root/'framework_sessions'
        self.snapshot=Path(session_storage_path(self.directory))/'session'/self.session/'scopes/agent/default/snapshots/snapshot_latest.json'
        self.snapshot.parent.mkdir(parents=True,exist_ok=True)
        self.snapshot.write_text(json.dumps(dict(data=dict(messages=self.messages))),encoding='utf-8')
        self.prep=save(self.h,dict(next_session=self.session,initial_messages=self.initial),'synthetic_preparation')
        verification=save(self.h,dict(preparation=self.prep,independently_restored=True,snapshot_files={}),
                          'synthetic_verification')
        s=state(self.h);s['pilot'].update(handoff=self.prep,handoff_verification=verification);update(self.h,pilot=s['pilot'])
        with self.h.store.transaction() as db:
            self.h.store.event(db,self.h.run_id,'session_handoff','committed',outputs=[self.prep,verification])
        packet=dict(synthetic=True)
        provider.record(self.h,'model_decision_packet',packet)
        wire=dict(provider.request_settings(s['pilot']['provider']),messages=provider.model_messages(self.h,self.messages,'Synthetic system')+
                  [dict(role='user',content='CURRENT_RESEARCH_PACKET\n'+json.dumps(packet))],stream=False)
        def disconnected(request):raise httpx.RemoteProtocolError('Synthetic lost response',request=request)
        async def send():
            class Boundary(provider.LiveBoundary):purpose='conversation'
            boundary=Boundary(self.h,httpx.MockTransport(disconnected))
            try:
                with self.assertRaises(httpx.RemoteProtocolError):
                    await boundary.handle_async_request(httpx.Request('POST',s['pilot']['provider']['base_url'].rstrip('/')+'/chat/completions',json=wire))
                self.key=boundary.last_request
            finally:await boundary.aclose()
        asyncio.run(send())
        self.auth=dict(approved=True,scope='abandon_unrecoverable_main_attempt_v1',study_id=self.h.run_id,
                       request_id=self.key,expected_provider_requests=1,source_sha256='synthetic-explicit-user',
                       reason='Synthetic approval to retain unknown outcome and continue from original committed context')

    def abandon(self,**changes):
        with patch('tools.service_execution.process_exit_observation',return_value=dict(exited=True,pid=123)):
            return provider.abandon_unrecoverable_main_attempt(self.h,self.key,authorization={**self.auth,**changes})

    def test_preserves_unknown_cost_state_snapshot_and_trusted_handoff(self):
        before=state(self.h);ledger=self.h.store.remaining();snapshot=self.snapshot.read_bytes()
        result=self.abandon()
        self.assertEqual(state(self.h),before);self.assertEqual(self.snapshot.read_bytes(),snapshot)
        self.assertEqual(self.h.store.remaining()['used'],ledger['used']);self.assertEqual(provider.pending(self.h),[])
        self.assertEqual(result['provider_outcome'],'unknown');self.assertFalse(result['upstream_cancelled'])
        self.assertFalse(result['new_send']);self.assertFalse(result['response_saved'])
        outcome=provider.provider_outcome(self.h,self.key)
        self.assertTrue(outcome['outcome_unknown']);self.assertTrue(outcome['provider_charged'])
        self.assertEqual(outcome['charged_model_requests'],1);self.assertIsNone(outcome['money'])
        agent=SimpleNamespace(messages=self.messages,_session_manager=SimpleNamespace(session_id=self.session))
        self.assertEqual(trusted_history(self.h,agent,initial_messages=self.initial,
                         files=snapshot_files(self.directory,self.session),preparation=self.prep),'initial_unsent_invocation')
        events=self.h.store.events(self.h.run_id);self.assertEqual(self.abandon(),result)
        self.assertEqual(self.h.store.events(self.h.run_id),events)

    def test_explicit_exact_authorization_and_original_charge_required(self):
        for changes in (dict(approved=False),dict(study_id='wrong'),dict(expected_provider_requests=2)):
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.abandon(**changes)
        self.assertEqual(len(provider.pending(self.h)),1)

    def test_saved_response_cannot_be_abandoned(self):
        with self.h.store.transaction() as db:
            self.h.store.event(db,self.h.run_id,'r3_response','received',request=self.key,
                              outputs=[self.h.store.put(db,dict(http_status=200))])
        with self.assertRaisesRegex(ValueError,'SAVED_RESPONSE'):self.abandon()

    def test_changed_snapshot_or_post_send_tool_blocks_disposition(self):
        self.snapshot.write_text(json.dumps(dict(data=dict(messages=self.messages[:-1]))),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'SDK'):self.abandon()
        self.snapshot.write_text(json.dumps(dict(data=dict(messages=self.messages))),encoding='utf-8')
        provider.record(self.h,'model_original_tool_request',dict(synthetic=True))
        with self.assertRaisesRegex(ValueError,'POST_SEND'):self.abandon()

    def test_live_sender_or_pending_science_blocks_disposition(self):
        with patch('tools.service_execution.process_exit_observation',side_effect=ValueError('PROCESS_STILL_PRESENT')):
            with self.assertRaisesRegex(ValueError,'PROCESS_STILL_PRESENT'):
                provider.abandon_unrecoverable_main_attempt(self.h,self.key,authorization=self.auth)
        update(self.h,pending=dict(kind='synthetic_pending'))
        with self.assertRaisesRegex(ValueError,'QUIESCENT'):self.abandon()


class UnknownMainSDKRecoveryTests(unittest.TestCase):
    def test_real_sdk_restores_and_sends_once_after_authorized_disposition(self):
        from tools.research.agent import converse
        from tests.research.test_phs2d_knowledge_start import fixture
        from tests.research.test_research_authorization_preflight import approve
        from tools.research.contracts import REGISTERED_MATHEMATICS_SCOPE
        from tests.research.test_request_boundary_handoff import RequestBoundaryHandoffTests
        context=fixture();h=context.__enter__();self.addCleanup(context.__exit__,None,None,None)
        approve(h,[REGISTERED_MATHEMATICS_SCOPE]);sent=[]
        normal=RequestBoundaryHandoffTests().responder(h,sent)
        def respond(request):
            if len(sent)==1:
                sent.append(json.loads(request.content))
                raise httpx.RemoteProtocolError('Synthetic lost Main response',request=request)
            body=normal(request).json()
            body['choices'][0]['message'].pop('reasoning_content',None)
            return httpx.Response(200,json=body)
        with patch('tools.research.agent.credential',return_value='offline'),\
                patch('tools.research.provider.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                patch('tools.research.core.guard'),patch('tools.research.agent.guard'),\
                patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(respond)):
            with self.assertRaises(Exception):
                asyncio.run(converse(h,session_handoff=True,handoff_request_bytes=1,max_new_provider_requests=2))
            self.assertEqual(len(sent),2);key=provider.pending(h)[0]['request_id']
            auth=dict(approved=True,scope='abandon_unrecoverable_main_attempt_v1',study_id=h.run_id,
                request_id=key,expected_provider_requests=2,source_sha256='synthetic-explicit-approval',
                reason='Synthetic exact local disposition, no inferred remote outcome')
            before=state(h);ledger=h.store.remaining()['used']
            with patch('tools.service_execution.process_exit_observation',return_value=dict(exited=True,pid=123)):
                provider.abandon_unrecoverable_main_attempt(h,key,authorization=auth)
            self.assertEqual(state(h),before);self.assertEqual(h.store.remaining()['used'],ledger)
            asyncio.run(converse(h,session_handoff=True,restore_only=True))
            self.assertEqual(len(sent),2)
            asyncio.run(converse(h,session_handoff=True,max_new_provider_requests=1))
        self.assertEqual(len(sent),3);self.assertEqual(provider.pending(h),[])
        self.assertEqual(h.store.remaining()['used']['model_calls'],3)
        self.assertTrue(provider.provider_outcome(h,key)['outcome_unknown'])
        self.assertEqual(len([e for e in h.store.events(h.run_id) if e['kind']=='model_original_tool_request']),1)


if __name__=='__main__':unittest.main()
