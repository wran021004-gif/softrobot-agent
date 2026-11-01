"""A resumed V4 Study starts with tool discovery, not its historical STOP selector."""
import asyncio
from copy import deepcopy
import unittest
from unittest.mock import patch
import httpx
from tools.research import agent,core
from tools.research.state import state,update,save
from tools.research.contracts import REGISTERED_MATHEMATICS_SCOPE
from tests.research.test_research_authorization_preflight import fixture,approve
from tests.research.test_recent_round_tools import run_fixture
from tests.research.test_cross_task_integration import plan

class ContinuedRouteTests(unittest.TestCase):
    def test_v4_nonpass_resume_clears_historical_stop_route_before_new_send(self):
        with fixture() as h:
            approve(h,[REGISTERED_MATHEMATICS_SCOPE])
            spec=state(h)['spec']
            with patch('tools.research.core.guard'),patch('tools.research.state.guard'):
                core.dispatch(h,plan('generate',generation=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],segment_count=1,tendon_count=3)),'offline-generate')
            with patch('tools.research.agent.credential',return_value='offline-fixture'):
                run_fixture(h,[('research_route',dict(tool='research_plan',action='stop'))],limit=1)
                run_fixture(h,[None],limit=1,id_offset=1)
            stop=save(h,dict(fixture='Synthetic nonpass STOP; no scientific result'),'offline_stop')
            update(h,research_status='stopped',final_disposition=stop)
            old=state(h)
            self.assertEqual(old['research_status'],'stopped')
            self.assertEqual(h.store.artifact(old['pilot']['tool_route'])['action'],'stop')
            previous=save(h,old,'offline_sealed_stop_state')
            approval=save(h,dict(user_approval=True,previous_state=previous,previous_final_disposition=old['final_disposition']),'offline_nonpass_continuation')
            update(h,research_status='ready',count_closeout=False,final_disposition=None,research_continuations=[approval],pending_authorized_continuation=approval)
            before=h.store.remaining()
            def forbidden(request):raise AssertionError('Restore must not send')
            with patch('tools.research.agent.credential',return_value='offline-fixture'),patch('tools.research.tool_readiness.execution_environment',return_value=dict(status='ready')),patch('tools.research.core.guard'),patch('tools.research.agent.guard'),patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(forbidden)):
                asyncio.run(agent.converse(h,session_handoff=False,restore_only=True))
            self.assertEqual(h.store.remaining(),before)
            self.assertIsNone(state(h)['pilot'].get('tool_route'))
            self.assertIsNone(state(h)['pending_authorized_continuation'])
            with patch('tools.research.agent.credential',return_value='offline-fixture'):
                fresh=run_fixture(h,[None],limit=1)
            functions={t['function']['name'] for t in fresh[0]['tools']}
            self.assertIn('research_route',functions)
            schema=next(t['function']['parameters'] for t in fresh[0]['tools'] if t['function']['name']=='research_plan')
            self.assertNotEqual(schema['properties']['action']['enum'],['stop'])
            self.assertEqual(h.store.artifact(previous)['final_disposition'],old['final_disposition'])
