"""Real SDK request-boundary rotation with explicit mock HTTP; no live science."""
import asyncio
from copy import deepcopy
import json
import os
import unittest
from unittest.mock import patch
import httpx
from tools.research.agent import converse
from tools.research.contracts import EvidenceQuery
from tools.research.session_handoff import request_feedback_boundary,handoff
from tools.research.state import state,update,save
from tests.research.test_s125_contract import cold_host


class RequestBoundaryHandoffTests(unittest.TestCase):
    def provision(self):
        h=cold_host();pilot=deepcopy(state(h)['pilot'])
        pilot.update(session_handoff_live_admitted=True,session_handoff_boundary='request_feedback')
        update(h,freeze='explicit-offline-request-boundary-fixture',pilot=pilot)
        return h

    def responder(self,h,sent):
        def respond(request):
            wire=json.loads(request.content);sent.append(wire)
            message=dict(role='assistant',content='Consumed fixture feedback',reasoning_content='Exact offline request reasoning')
            reason='stop'
            if len(sent)==1:
                message.update(content='Exact response text before tool use\nPreserve all characters.',tool_calls=[dict(id='fixture-read-priors',type='function',function=dict(
                    name='evidence_read',arguments=json.dumps(dict(reference=state(h)['public_prior_manifest'],view='summary'))))])
                reason='tool_calls'
            return httpx.Response(200,json=dict(id='explicit-offline-response',object='chat.completion',created=1,
                model=wire['model'],usage=dict(prompt_tokens=10,completion_tokens=4,total_tokens=14),
                choices=[dict(index=0,finish_reason=reason,message=message)]))
        return respond

    def test_rotation_precedes_next_send_without_fabricated_completed_invocation(self):
        h=self.provision();original=state(h)['pilot']['framework_session_id'];sent=[]
        with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                patch('tools.research.core.guard'),patch('tools.research.agent.guard'),\
                patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(self.responder(h,sent))):
            asyncio.run(converse(h,session_handoff=True,handoff_request_bytes=1,pause_after_completed_invocations=1))
        self.assertEqual(len(sent),2);self.assertNotEqual(state(h)['pilot']['framework_session_id'],original)
        events=h.store.events(h.run_id)
        committed=next(e for e in events if e['kind']=='session_handoff' and e['status']=='committed')
        preparation=h.store.artifact(committed['outputs'][0])
        self.assertEqual(preparation['version'],'research_session_handoff_v3')
        self.assertEqual(preparation['boundary_kind'],'request_feedback')
        self.assertFalse(preparation['invocation_completed'])
        self.assertNotIn('completed_boundary',preparation)
        suspended=next(e for e in events if e['kind']=='sdk_invocation_suspended_for_handoff')
        self.assertLess(suspended['sequence'],committed['sequence'])
        turns=[e for e in events if e['kind']=='model_original_turn']
        self.assertEqual(len(turns),1);self.assertGreater(turns[0]['sequence'],committed['sequence'])
        self.assertEqual(h.store.remaining()['used']['model_calls'],2)
        self.assertFalse(any(m.get('tool_calls') for m in sent[1]['messages']))
        self.assertIn('CURRENT_RESEARCH_PACKET',sent[1]['messages'][-1]['content'])
        delivery=json.loads(sent[1]['messages'][-1]['content'].split('\n',1)[1])['research']['pending_feedback_delivery']
        self.assertEqual(delivery['items'][0]['tool_id'],'fixture-read-priors')
        self.assertEqual(delivery['items'][0]['status'],'success')
        from tools.research.session_handoff import pending_feedback_delivery
        self.assertIsNone(pending_feedback_delivery(h))
        self.assertEqual(len([e for e in events if e['kind']=='model_original_tool_request']),1)
        with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                patch('tools.research.core.guard'),patch('tools.research.agent.guard'),\
                patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(self.responder(h,sent))):
            asyncio.run(converse(h,session_handoff=True,restore_only=True))
        self.assertEqual(len(sent),2)
        restored=h.store.artifact(h.store.events(h.run_id)[-1]['outputs'][0])
        self.assertFalse(restored['next_request_sent']);self.assertEqual(restored['unmatched_tool_ids'],[])

    def test_changed_original_response_blocks_rotation_and_next_send(self):
        h=self.provision();sent=[]
        async def changed(host,agent):
            last=next(m for m in reversed(agent.messages) if m['role']=='assistant')
            reasoning=next(b for b in last['content'] if 'reasoningContent' in b)
            reasoning['reasoningContent']['reasoningText']['text']='Tampered explicit offline fixture'
            return await request_feedback_boundary(host,agent)
        with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                patch('tools.research.core.guard'),patch('tools.research.agent.guard'),\
                patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(self.responder(h,sent))),\
                patch('tools.research.session_handoff.request_feedback_boundary',side_effect=changed):
            with self.assertRaisesRegex(Exception,'ORIGINAL_RESPONSE_MISMATCH'):
                asyncio.run(converse(h,session_handoff=True,handoff_before_next_request=True))
        self.assertEqual(len(sent),1)
        self.assertFalse(any(e['kind']=='session_handoff' for e in h.store.events(h.run_id)))
        self.assertFalse(any(e['kind']=='model_original_turn' for e in h.store.events(h.run_id)))

    def test_request_timing_requires_separate_live_admission(self):
        h=cold_host()
        with patch('tools.research.agent.load_credential',side_effect=AssertionError('NO_CREDENTIAL_OR_SEND')):
            with self.assertRaisesRegex(ValueError,'REQUEST_FEEDBACK_LIVE_ADMISSION_REQUIRED'):
                asyncio.run(converse(h,handoff_before_next_request=True))

    def test_unsent_initial_invocation_recovers_and_changed_text_is_rejected(self):
        h=self.provision();sent=[]
        async def pause_after_commit(*args,**kwargs):
            result=await handoff(*args,**kwargs)
            update(h,validation_extension_pending_binding=True)
            return result
        def migration_guard(host,*args,**kwargs):
            if state(host).get('validation_extension_pending_binding'):raise ValueError('fixture migration pause')
        with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                patch('tools.research.core.guard',side_effect=migration_guard),patch('tools.research.agent.guard'),\
                patch('tools.research.session_handoff.handoff',side_effect=pause_after_commit),\
                patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(self.responder(h,sent))):
            with self.assertRaisesRegex(ValueError,'fixture migration pause'):
                asyncio.run(converse(h,session_handoff=True,handoff_request_bytes=1))
        self.assertEqual(len(sent),1);ledger=h.store.remaining()
        update(h,validation_extension_pending_binding=False)
        root=h.store.root/'framework_sessions/session'/state(h)['pilot']['framework_session_id']
        path=next(root.rglob('snapshot_latest.json'));original=path.read_bytes()
        snapshot=json.loads(original);snapshot['data']['messages'][-1]['content'][0]['text']='untrusted changed prompt'
        path.write_text(json.dumps(snapshot),encoding='utf8')
        def forbidden(request):raise AssertionError('No new request')
        with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                patch('tools.research.core.guard'),patch('tools.research.agent.guard'),\
                patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(forbidden)):
            with self.assertRaisesRegex(ValueError,'SDK_INITIAL_CONTEXT_MISMATCH'):
                asyncio.run(converse(h,session_handoff=True,restore_only=True))
            path.write_bytes(original)
            asyncio.run(converse(h,session_handoff=True,restore_only=True))
        self.assertEqual(h.store.remaining(),ledger)
        events=h.store.events(h.run_id)
        self.assertTrue(any(e['kind']=='sdk_unsent_invocation_verified' for e in events))
        self.assertFalse(any(e['kind']=='model_original_turn' for e in events))

    def test_new_requests_refresh_query_schema_after_old_snapshot_verification(self):
        h=self.provision();sent=[]
        current=EvidenceQuery.model_json_schema();old=deepcopy(current)
        old['properties']['fields']['description']='Explicit synthetic older query description'
        with patch.object(EvidenceQuery,'model_json_schema',return_value=old),\
                patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                patch('tools.research.core.guard'),patch('tools.research.agent.guard'),\
                patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(self.responder(h,sent))):
            asyncio.run(converse(h,session_handoff=True,handoff_request_bytes=1,pause_after_completed_invocations=1))
        with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                patch('tools.research.core.guard'),patch('tools.research.agent.guard'),\
                patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(self.responder(h,sent))):
            asyncio.run(converse(h,session_handoff=True,pause_after_completed_invocations=1))
        first=next(t for t in sent[1]['tools'] if t['function']['name']=='evidence_read')['function']['parameters']
        last=next(t for t in sent[-1]['tools'] if t['function']['name']=='evidence_read')['function']['parameters']
        self.assertEqual(first['properties']['fields']['description'],old['properties']['fields']['description'])
        self.assertEqual(last['properties']['fields']['description'],current['properties']['fields']['description'])

    def test_explicit_nonpass_continuation_restores_tools_without_send_or_reset(self):
        h=self.provision();sent=[];update(h,count_closeout=True)
        transport=httpx.MockTransport(self.responder(h,sent))
        with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                patch('tools.research.core.guard'),patch('tools.research.agent.guard'),\
                patch('httpx.AsyncHTTPTransport',return_value=transport):
            asyncio.run(converse(h,session_handoff=True,handoff_request_bytes=1,pause_after_completed_invocations=1))
        self.assertEqual(len(sent),2)
        self.assertNotIn('research_analysis',[t['function']['name'] for t in sent[-1]['tools']])
        stop=save(h,dict(fixture='explicit synthetic nonpass STOP, no science'),'synthetic_fixture')
        update(h,research_status='stopped',final_disposition=stop)
        prior=save(h,state(h),'synthetic_sealed_state')
        approval=save(h,dict(user_approval=True,previous_state=prior,previous_final_disposition=stop),
            'synthetic_continuation_authorization')
        update(h,research_status='ready',count_closeout=False,final_disposition=None,
            research_continuations=[approval],pending_authorized_continuation=approval)
        ledger=h.store.remaining();old_session=state(h)['pilot']['framework_session_id']
        def forbidden(request):raise AssertionError('Restore must not send')
        def interrupted_update(host,**values):
            if 'pending_authorized_continuation' in values:raise RuntimeError('fixture after committed continuation handoff')
            return update(host,**values)
        with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                patch('tools.research.core.guard'),patch('tools.research.agent.guard'),\
                patch('tools.research.agent.update',side_effect=interrupted_update),\
                patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(forbidden)):
            with self.assertRaisesRegex(RuntimeError,'after committed continuation'):
                asyncio.run(converse(h,session_handoff=True,restore_only=True))
        for _ in range(2):
            with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                    patch('tools.research.core.guard'),patch('tools.research.agent.guard'),\
                    patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(forbidden)):
                asyncio.run(converse(h,session_handoff=True,restore_only=True))
        self.assertEqual(h.store.remaining(),ledger)
        self.assertNotEqual(state(h)['pilot']['framework_session_id'],old_session)
        self.assertEqual(h.store.artifact(prior)['final_disposition'],stop)
        activated=[h.store.artifact(e['outputs'][0]) for e in h.store.events(h.run_id)
            if e['kind']=='authorized_continuation_activated']
        self.assertEqual(len(activated),1)
        self.assertEqual(len([e for e in h.store.events(h.run_id) if e['kind']=='session_handoff' and e['status']=='committed']),2)
        self.assertIn('research_analysis',activated[0]['tools'])
        self.assertFalse(activated[0]['next_request_sent'])
        self.assertIsNone(state(h)['pending_authorized_continuation'])

    def test_budget_review_pauses_at_verified_feedback_before_second_send(self):
        h=self.provision();sent=[];original=state(h)['pilot']['framework_session_id']
        with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                patch('tools.research.core.guard'),patch('tools.research.agent.guard'),\
                patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(self.responder(h,sent))):
            asyncio.run(converse(h,session_handoff=True,pause_exploration_remaining=100))
        self.assertEqual(len(sent),1)
        self.assertEqual(state(h)['pilot']['framework_session_id'],original)
        events=h.store.events(h.run_id)
        self.assertTrue(any(e['kind']=='request_feedback_boundary' for e in events))
        pause=h.store.artifact(next(e['outputs'][0] for e in events if e['kind']=='supervisor_pause'))
        self.assertEqual(pause['boundary'],'request_feedback');self.assertFalse(pause['next_request_sent'])
        self.assertFalse(any(e['kind']=='model_original_turn' for e in events))
        self.assertFalse(state(h)['pending'])

    def test_failed_snapshot_verification_keeps_old_pointer_and_no_next_send(self):
        h=self.provision();original=state(h)['pilot']['framework_session_id'];sent=[]
        async def interrupted(*args,**kwargs):
            def stage(name):
                if name=='snapshot_saved':raise RuntimeError('EXPLICIT_OFFLINE_SNAPSHOT_INTERRUPTION')
            return await handoff(*args,**kwargs,stage=stage)
        with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                patch('tools.research.core.guard'),patch('tools.research.agent.guard'),\
                patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(self.responder(h,sent))),\
                patch('tools.research.session_handoff.handoff',side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError,'EXPLICIT_OFFLINE_SNAPSHOT_INTERRUPTION'):
                asyncio.run(converse(h,session_handoff=True,handoff_before_next_request=True))
        self.assertEqual(state(h)['pilot']['framework_session_id'],original)
        self.assertEqual(len(sent),1);self.assertEqual(h.store.remaining()['used']['model_calls'],1)
        self.assertFalse(any(e['kind']=='session_handoff' and e['status']=='committed' for e in h.store.events(h.run_id)))
        self.assertFalse(any(e['kind']=='model_original_turn' for e in h.store.events(h.run_id)))


if __name__=='__main__':unittest.main()
