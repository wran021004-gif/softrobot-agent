"""Exact transport addenda and SDK continuity; synthetic HTTP, no science."""
import asyncio
from copy import deepcopy
import json
import os
import unittest
from unittest.mock import patch
import httpx
from tools.research.config import ROOT
from tools.research.state import state, update, save, guard
from tools.research.provider import transition_transport,LiveBoundary,IncompleteModelOutput,received
from tools.research.core import bind
from tools.research.agent import converse
from tools.platform_store import zero
from tools.state_io import digest
from tests.research.test_phs2d_knowledge_start import fixture as phs_fixture


class ProviderTransportTests(unittest.TestCase):
    def fixture(self):
        manager=phs_fixture();h=manager.__enter__();self.addCleanup(manager.__exit__,None,None,None)
        s=state(h);spec=deepcopy(s['spec'])
        p=deepcopy(spec['runtime']['provider']);path=h.store.root/'gateway-key-fixture.json'
        path.write_text(json.dumps(dict(base_url=p['base_url'],api_key='gateway-fixture')))
        spec['runtime'].update(provider=p,credentials_reference=str(path))
        spec['configuration']['policy']['model']={**deepcopy(p),'thinking':None}
        spec['research_decisions']['role_policy']=dict(version='research_roles_v3',main=dict(reasoning='medium'),reporter=dict(reasoning='none'))
        spec['research_decisions']['tool_schema_policy']=dict(version='on_demand_tools_v3')
        update(h,spec=spec,pilot={**s['pilot'],'provider':{**deepcopy(p),'thinking':None}})
        target={**deepcopy(p),'adapter':'openai_api','base_url':'https://api.openai.com/v1','proxy_url':'http://127.0.0.1:7890'}
        path=h.store.root/'official-key-fixture.json'
        path.write_text(json.dumps(dict(base_url=target['base_url'],api_key='official-fixture')))
        return h,self.approval(h,target,str(path))

    def approval(self,h,p,path):
        spec=state(h)['spec']
        scope=dict(study_id=h.run_id,resolved_identity=spec['resolved_identity'],
            previous_provider_identity=digest(spec['runtime']['provider']),provider=p,credentials_reference=path)
        return dict(version='provider_transport_approval_v1',approved=True,source='Explicit offline fixture; not live authorization',scope=scope,scope_identity=digest(scope))

    def authorize(self,h):
        scope=dict(study_id=h.run_id,resolved_identity=state(h)['spec']['resolved_identity'],execution_scopes=['registered mathematics'])
        save(h,dict(user_approval='Offline fixture approval only',scope=scope,scope_identity=digest(scope)),'formal_study_authorization')

    def test_addendum_round_trip_preserves_history_costs_profile_and_limits(self):
        h,a=self.fixture();old=deepcopy(state(h));ledger=h.store.remaining()
        result=transition_transport(h,a)
        self.assertEqual(result['provider_requests_sent'],0)
        self.assertEqual(h.store.remaining(),ledger)
        self.assertTrue(transition_transport(h,a)['already_applied'])
        self.authorize(h)
        with self.assertRaisesRegex(ValueError,'AUTHORIZED_EXTENSION_REQUIRES_COMMITTED'):guard(h)
        s=state(h)
        for key in old:
            if key not in ('spec','pilot','validation_extension_pending_binding','provider_transport_transitions'):
                self.assertEqual(s[key],old[key],key)
        for key in old['pilot']:
            if key!='provider':self.assertEqual(s['pilot'][key],old['pilot'][key])
        back=self.approval(h,old['pilot']['provider'],old['spec']['runtime']['credentials_reference'])
        transition_transport(h,back)
        self.assertEqual(state(h)['spec']['runtime']['provider'],old['pilot']['provider'])
        for key in old['spec']['runtime']:
            if key!='provider':self.assertEqual(state(h)['spec']['runtime'][key],old['spec']['runtime'][key])
        self.assertEqual(state(h)['spec']['budgets'],old['spec']['budgets'])
        self.assertEqual(h.store.remaining(),ledger)
        self.assertEqual(len(state(h)['provider_transport_transitions']),2)

    def test_wrong_scope_model_science_settings_and_unsettled_responses_fail_atomically(self):
        h,a=self.fixture();old=deepcopy(state(h));ledger=h.store.remaining()
        for change in (dict(model='different-model'),dict(reasoning='none'),dict(max_turns=999)):
            bad=deepcopy(a);bad['scope']['provider'].update(change);bad['scope_identity']=digest(bad['scope'])
            with self.assertRaisesRegex(ValueError,'TRANSPORT_ONLY'):transition_transport(h,bad)
        bad=deepcopy(a);bad['scope']['resolved_identity']='0'*64;bad['scope_identity']=digest(bad['scope'])
        with self.assertRaisesRegex(ValueError,'EXACT_USER_APPROVED'):transition_transport(h,bad)
        self.assertEqual(state(h),old);self.assertEqual(h.store.remaining(),ledger)
        update(h,pilot={**old['pilot'],'unconsumed_response':'offline-response'})
        with self.assertRaisesRegex(ValueError,'SETTLED_PROVIDER'):transition_transport(h,a)
        update(h,pilot=old['pilot'])
        h.store.reserve(h.run_id,'offline-unsettled','f'*64,h.actor,zero())
        with self.assertRaisesRegex(ValueError,'SETTLED_PROVIDER'):transition_transport(h,a)
        self.assertNotIn('provider_transport_transitions',state(h))

    def test_real_sdk_restore_across_transport_retains_original_tool_feedback(self):
        h,a=self.fixture();bind(h,'Offline initial transport fixture');self.authorize(h)
        seen=[]
        def reply(request):
            wire=json.loads(request.content);seen.append((str(request.url),wire))
            self.assertEqual(wire['model'],'gpt-5.6-sol')
            if len(seen)==1:
                self.assertEqual(wire['reasoning_effort'],'medium')
                message=dict(role='assistant',content=None,tool_calls=[dict(id='transport-route',type='function',function=dict(name='research_route',arguments='{"tool":"evidence_read"}'))])
                reason='tool_calls'
            else:
                self.assertEqual(str(request.url),'https://api.openai.com/v1/responses')
                self.assertEqual(request.headers['authorization'],'Bearer official-fixture')
                self.assertEqual(wire['reasoning'],dict(effort='medium'))
                self.assertFalse(any('provider_output' in m for m in wire['input']))
                self.assertTrue(any(m.get('type')=='function_call_output' and m.get('call_id')=='transport-route' for m in wire['input']))
                self.assertFalse(wire['store'])
                self.assertTrue(all(t['strict'] is False for t in wire['tools']))
                if len(seen)==2:
                    output=[dict(type='reasoning',id='rs_fixture',summary=[],encrypted_content='opaque-fixture'),
                        dict(type='function_call',id='fc_fixture',call_id='official-route',name='research_route',arguments='{"tool":"evidence_read"}')]
                else:
                    self.assertIn(dict(type='reasoning',id='rs_fixture',summary=[],encrypted_content='opaque-fixture'),wire['input'])
                    self.assertTrue(any(m.get('type')=='function_call_output' and m.get('call_id')=='official-route' for m in wire['input']))
                    output=[dict(type='message',role='assistant',content=[dict(type='output_text',text='Synthetic feedback consumed.')])]
                return httpx.Response(200,json=dict(id='resp-fixture-'+str(len(seen)),model=wire['model'],status='completed',output=output,
                    usage=dict(input_tokens=10,output_tokens=4,total_tokens=14,output_tokens_details=dict(reasoning_tokens=2))))
            return httpx.Response(200,json=dict(id='fixture-'+str(len(seen)),object='chat.completion',created=1,model=wire['model'],
                usage=dict(prompt_tokens=10,completion_tokens=4,total_tokens=14),choices=[dict(index=0,finish_reason=reason,message=message)]))
        with patch.dict(os.environ,state(h)['spec']['runtime']['threads']),patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(reply)):
            asyncio.run(converse(h,session_handoff=False,max_new_provider_requests=1))
            session=state(h)['pilot']['framework_session_id'];ledger=h.store.remaining()
            transition_transport(h,a);self.authorize(h);bind(h,'Offline explicitly approved transport switch')
            asyncio.run(converse(h,session_handoff=False,restore_only=True))
            self.assertEqual(h.store.remaining()['used'],ledger['used'])
            self.assertEqual(state(h)['pilot']['framework_session_id'],session)
            asyncio.run(converse(h,session_handoff=False,max_new_provider_requests=2,pause_after_completed_invocations=1))
        self.assertEqual(len(seen),3)
        self.assertEqual(h.store.remaining()['used']['model_calls'],3)
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)
        receptions=[h.store.artifact(e['outputs'][0]) for e in h.store.events(h.run_id) if e['kind']=='r3_response' and e['status']=='metadata_saved']
        self.assertEqual(receptions[-1]['usage']['total_tokens'],14)
        self.assertEqual(receptions[-1]['reasoning_tokens'],2)
        self.assertTrue(receptions[-1]['body_is_derived_chat_view'])
        upstream=json.loads(h.store.artifact(receptions[-1]['upstream_body'],raw=True))
        self.assertEqual(upstream['status'],'completed')

    def test_incomplete_responses_replay_has_one_charge_and_no_tool_admission(self):
        h,a=self.fixture();transition_transport(h,a);sent=[]
        def reply(request):
            sent.append(json.loads(request.content))
            return httpx.Response(200,json=dict(id='resp_incomplete',model='gpt-5.6-sol',status='incomplete',
                incomplete_details=dict(reason='max_output_tokens'),output=[dict(type='function_call',call_id='partial',name='research_plan',arguments='{')]))
        boundary=LiveBoundary(h,httpx.MockTransport(reply))
        request=httpx.Request('POST','https://api.openai.com/v1/chat/completions',json=dict(
            model='gpt-5.6-sol',stream=False,store=False,reasoning_effort='medium',messages=[dict(role='user',content='Offline fixture')],
            tools=[dict(type='function',function=dict(name='research_plan',parameters=dict(type='object',properties={})))]))
        before=h.store.remaining()
        for _ in range(2):
            with self.assertRaises(IncompleteModelOutput):asyncio.run(boundary.handle_async_request(request))
        self.assertEqual(len(sent),1)
        self.assertEqual(h.store.remaining()['used']['model_calls'],before['used']['model_calls']+1)
        self.assertFalse(state(h)['plans']);self.assertFalse(state(h)['candidates'])
        reception=received(h,boundary.last_request)
        self.assertIsNone(reception['usage'])
        self.assertEqual(json.loads(h.store.artifact(reception['upstream_body'],raw=True))['status'],'incomplete')
        self.assertEqual(reception['finish_reasons'],['length'])


if __name__=='__main__':unittest.main()
