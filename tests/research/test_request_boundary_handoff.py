"""Real SDK request-boundary rotation with explicit mock HTTP; no live science."""
import asyncio
from copy import deepcopy
import json
import os
import unittest
from unittest.mock import patch
import httpx
from tools.research.agent import converse
from tools.research.session_handoff import request_feedback_boundary,handoff
from tools.research.state import state,update
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
            asyncio.run(converse(h,session_handoff=True,handoff_before_next_request=True,pause_after_completed_invocations=1))
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
        self.assertEqual(len([e for e in events if e['kind']=='model_original_tool_request']),1)

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
