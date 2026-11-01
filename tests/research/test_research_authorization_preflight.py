"""Exact existing approval gates at the actual conversation entry; Mock HTTP only."""
import asyncio
from copy import deepcopy
from contextlib import contextmanager
from uuid import uuid4
import unittest
from unittest.mock import patch
from tools.research import core, agent
from tools.research.config import ROOT, resolve
from tools.research.contracts import REGISTERED_MATHEMATICS_SCOPE
from tools.research.state import state, update, save, require_authorization, require_research_authorization
from tools.research.research_context import mathematics_authorization
from tools.state_io import digest
from tests.research.test_cross_task_integration import fixture_directory
from tests.research.test_recent_round_tools import run_fixture

@contextmanager
def fixture():
    spec=resolve(ROOT/'configs/research/study_m1_elevated_auth_checked_v2.json')
    spec=deepcopy(spec);spec['study_id']='authorization-fixture-'+uuid4().hex[:8]
    spec['configuration']['run_id']=spec['study_id']
    with fixture_directory() as folder, patch('tools.research.config.resolve',return_value=spec):
        h=core.prepare(directory=folder)
        update(h,freeze='offline-authorization-fixture',pilot={**state(h)['pilot'],
            'session_handoff_live_admitted':True,'session_handoff_boundary':'request_feedback'})
        yield h

def approve(h,scopes,**changes):
    scope=dict(study_id=h.run_id,resolved_identity=state(h)['spec']['resolved_identity'],execution_scopes=scopes)
    scope.update(changes)
    return save(h,dict(user_approval='Explicit offline fixture only; not live science',scope=scope,scope_identity=digest(scope)),'formal_study_authorization')

class ResearchAuthorizationPreflightTests(unittest.TestCase):
    def assert_no_send(self,h,reason):
        before=h.store.remaining()
        with patch('tools.research.agent.credential') as credential, patch('httpx.AsyncHTTPTransport') as transport:
            with self.assertRaisesRegex(ValueError,reason):
                asyncio.run(agent.converse(h,session_handoff=False,max_new_provider_requests=1))
        credential.assert_not_called();transport.assert_not_called()
        self.assertEqual(h.store.remaining(),before)
        self.assertFalse(any(e['kind']=='r3_request' for e in h.store.events(h.run_id)))
        self.assertIsNone(state(h)['pending'])

    def test_wrong_descriptive_scope_rejected_before_first_provider_send(self):
        with fixture() as h:
            approve(h,['registered mathematics including Native T1/T2'])
            require_authorization(h)  # The old total-Study gate alone admits it.
            self.assertFalse(mathematics_authorization(h,state(h))['registered_study_scope_authorized'])
            self.assert_no_send(h,'MATHEMATICS_APPROVAL_REQUIRED_BEFORE_PROVIDER')

    def test_missing_or_wrong_identity_total_approval_rejected_before_send(self):
        with fixture() as h:
            self.assert_no_send(h,'INDEPENDENT_FORMAL_STUDY_APPROVAL')
            approve(h,[REGISTERED_MATHEMATICS_SCOPE],resolved_identity='wrong-identity')
            self.assert_no_send(h,'INDEPENDENT_FORMAL_STUDY_APPROVAL')

    def test_exact_scope_admits_original_mock_provider_boundary(self):
        with fixture() as h:
            approve(h,[REGISTERED_MATHEMATICS_SCOPE])
            require_research_authorization(h)
            with patch('tools.research.agent.credential',return_value='offline-fixture'):
                sent=run_fixture(h,[None],limit=1)
            self.assertEqual(len(sent),1)
            self.assertEqual(h.store.remaining()['used']['model_calls'],1)
            self.assertEqual(state(h)['mathematical_evaluations'],0)
            self.assertFalse(state(h)['physical_replays'])

    def test_original_capability_grant_semantics_preserved(self):
        with fixture() as h:
            approve(h,[],capabilities=['analysis'])
            self.assertTrue(mathematics_authorization(h,state(h))['registered_study_scope_authorized'])
            require_research_authorization(h)
