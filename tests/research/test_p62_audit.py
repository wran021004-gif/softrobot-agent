"""Audit grant ceilings; no credentials, Provider traffic, or scientific work."""
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import httpx
from tests.research import p62_live_audit as audit
from tools.research.config import resolve, ROOT


class P62AuditTests(unittest.IsolatedAsyncioTestCase):
    async def test_role_caps_reject_before_reservation_or_send(self):
        for role,counts in [('reporter',{'reporter':{'requests':3}}),
                ('conversation',{'conversation':{'requests':6},'summarization':{'requests':1}})]:
            with self.subTest(role=role),patch.object(audit.reporter,'provider_usage',return_value=counts),\
                    patch.object(audit,'ORIGINAL_SEND',new_callable=AsyncMock) as send:
                with self.assertRaisesRegex(ValueError,'P62_ROLE_REQUEST_CEILING'):
                    await audit.limited_send(SimpleNamespace(host=object(),purpose=role),
                        httpx.Request('POST','http://offline.invalid',json={'tools':[]}))
                send.assert_not_awaited()

    async def test_last_allowed_request_uses_original_accounted_boundary(self):
        with patch.object(audit.reporter,'provider_usage',return_value={'reporter':{'requests':2}}),\
                patch.object(audit,'ORIGINAL_SEND',new_callable=AsyncMock,return_value='original') as send:
            boundary=SimpleNamespace(host=object(),purpose='reporter')
            request=httpx.Request('POST','http://offline.invalid',json={})
            self.assertEqual(await audit.limited_send(boundary,request),'original')
            send.assert_awaited_once_with(boundary,request)

    def test_frozen_arms_share_conditions_and_forbid_science(self):
        a,b=[resolve(ROOT/'configs/research'/('study_p62_'+arm+'.json')) for arm in ('luna','mini')]
        for k in ('research_decisions','budgets','execution_instructions','capabilities','allowed_plan_actions'):
            self.assertEqual(a[k],b[k],k)
        self.assertEqual(a['configuration']['task'],b['configuration']['task'])
        for s in (a,b):
            self.assertEqual(s['mode'],'engineering_investigation')
            self.assertEqual(s['budgets']['provider_requests'],10)
            for k in ('mathematical_evaluations','physical_launches','offline_nlp','bdf_replays'):
                self.assertEqual(s['budgets'][k],0)
            self.assertEqual(s['nmpc_limits']['executions'],0)
            self.assertEqual(s['rl_limits']['training_stages'],0)
        self.assertEqual(a['runtime']['provider']['model'],'gpt-5.6-luna')
        self.assertEqual(b['runtime']['provider']['model'],'gpt-5.4-mini')


class OfficialHandoffTests(unittest.TestCase):
    def test_real_sdk_official_api_rotates_at_settled_feedback(self):
        from tests.research.test_information_flow import flow_host, packet
        from tests.research.test_recent_round_tools import run_fixture
        from tools.research.state import state, update
        h=flow_host();s=state(h);spec=deepcopy(s['spec'])
        runtime=resolve(ROOT/'configs/research/study_p62_mini.json')['runtime']
        spec['runtime']=runtime
        spec['research_decisions']['role_policy']=dict(version='research_roles_v3',
            main=dict(reasoning='none'),reporter=dict(reasoning='none'))
        spec['research_decisions']['handoff_policy']=dict(version='token_handoff_v1',input_tokens=38000)
        update(h,spec=spec,pilot={**s['pilot'],'provider':runtime['provider']})
        original=state(h)['pilot']['framework_session_id']
        with patch('tools.research.provider.credential',return_value='offline'),\
                patch('tools.research.agent.credential',return_value='offline'):
            wires=run_fixture(h,[('evidence_read',dict(reference=s['family_space_reference'],view='full')),None])
        self.assertEqual(len(wires),2)
        self.assertNotEqual(original,state(h)['pilot']['framework_session_id'])
        self.assertTrue(packet(wires[1])['tool_continuation']['pending_feedback'])
        self.assertFalse(any(m.get('tool_calls') or m['role']=='tool' for m in wires[1]['messages']))
        self.assertEqual(h.store.remaining()['used']['model_calls'],2)
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)


if __name__=='__main__':unittest.main()
