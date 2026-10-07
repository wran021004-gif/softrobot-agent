"""Actual successor request/dispatch checks; no paid or physical operations."""
from copy import deepcopy
import json
from unittest import TestCase
from unittest.mock import patch
from examples import research_campaign_v3 as campaign
from examples import research_model_v1 as pilot
from tests.test_research_model_v1 import NativePilotTests
from tools.platform_models import payload_for
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter


class NativeSuccessorTests(NativePilotTests):
    @classmethod
    def setUpClass(cls):
        from uuid import uuid4
        cls.root=campaign.ROOT/'runs'/('successor-test-'+uuid4().hex)
        cls.w=campaign.prepare(cls.root,offline_fixture=True)

    def test_current_snapshot_agrees_with_visible_menu_and_dispatch(self):
        args=dict(action='stop',stop_reason='Engineering fixture completed',reasoning='Engineering fixture only.',evidence=[self.alias],
            observations=[dict(evidence=self.alias,value=self.packet['current_feedback']['aliases'][self.alias]['value'])],
            interpretations=[],unresolved_uncertainties=['No scientific inference'])
        result,payload=self.invoke_native(args)
        packet=json.loads(payload['messages'][1]['content'])['role_context']['research_packet']
        stamp=packet['capabilities']['authority_snapshot']
        self.assertEqual(stamp['session_id'],self.w.host.run_id)
        self.assertEqual(result['authority_check']['request'],stamp)
        self.assertTrue(result['authority_check']['revalidated_before_dispatch'])
        self.assertIn('control_search',packet['capabilities']['legal'])
        self.assertEqual(self.w.store.remaining()['used']['backend_solves'],0)

    def test_zero_search_capacity_has_stop_and_reachable_no_candidate_gate(self):
        empty=dict(backend_solves=0,model_calls=10,tool_calls=20,wall_s=0.,worker_calls=0)
        with patch('tools.research_scheduler.downstream_available',return_value=empty):
            pilot.configure(self.w);adapter=EvidenceDrivenAdapter();payload=payload_for(self.w.host,adapter)
        packet=json.loads(payload['messages'][1]['content'])['role_context']['research_packet']
        self.assertEqual(set(packet['capabilities']['legal']),{'stop'})
        remaining=dict(backend_solves=20,model_calls=4,tool_calls=80,wall_s=24000.,worker_calls=0)
        self.w.freeze['live_clock']=dict(origin_unix=100.,deadline_unix=36100.)
        with patch.object(self.w.store,'remaining',return_value={'remaining':remaining}),patch('time.time',return_value=101.):
            gate=campaign.verification_gate(self.w)
        self.assertEqual(gate['branch'],'incumbent_only_characterization')
        self.assertTrue(gate['authorized'])
        self.assertEqual(gate['attempts'],10)
        with patch.object(self.w.store,'remaining',return_value={'remaining':dict(remaining,wall_s=1000.)}),patch('time.time',return_value=101.):
            self.assertFalse(campaign.verification_gate(self.w)['authorized'])

    def test_archive_scope_does_not_replace_current_authority(self):
        from examples import research_campaign_v2
        for p in self.patches:p.stop()
        old=self.w.host.run_id
        revised=research_campaign_v2.refresh_prelaunch(self.root)
        restored=pilot.restore(self.root)
        adapter=EvidenceDrivenAdapter();payload=payload_for(restored.host,adapter)
        packet=json.loads(payload['messages'][1]['content'])['role_context']['research_packet']
        self.assertEqual(set(packet['capabilities']['legal']),{'stop'})
        self.assertEqual(packet['capabilities']['authority_snapshot']['session_id'],restored.host.run_id)
        self.assertEqual(adapter.role['archive_context_id'],old)
        self.assertEqual(adapter.context_id,revised.host.run_id)

    def test_restore_keeps_completed_outcomes_and_consumed_workflow_cost(self):
        packet=pilot.configure(self.w)
        before=self.w.store.remaining()['used']['tool_calls']
        args=dict(action='stop',stop_reason='Engineering fixture completed',reasoning='Fixture delivery.',evidence=[self.alias],
            observations=[dict(evidence=self.alias,value=packet['current_feedback']['aliases'][self.alias]['value'])],
            interpretations=[],unresolved_uncertainties=[])
        result,_=self.invoke_native(args)
        pilot.adopt_current_working(self.w)
        pilot.persist(self.w);restored=pilot.restore(self.root)
        self.assertEqual(restored.store.remaining()['used']['tool_calls'],before+1)
        self.assertEqual(len(restored.records),10)
        self.assertEqual(restored.working['experiments'],self.w.working['experiments'])
        self.assertEqual(restored.store.session(restored.host.run_id)['state']['handoffs']['research_decision'],result and self.w.store.session(self.w.host.run_id)['state']['handoffs']['research_decision'])

    def test_authority_changed_during_reasoning_is_not_a_formatting_error(self):
        from tools.research_scheduler import validate_decision
        from tools.working_state import project_working_state
        from schemas.platform_handoff import ResearchDecision
        payload_for(self.w.host,EvidenceDrivenAdapter())
        empty=dict(backend_solves=0,model_calls=10,tool_calls=20,wall_s=0.,worker_calls=0)
        with patch('tools.research_scheduler.downstream_available',return_value=empty):
            with self.assertRaisesRegex(ValueError,'CURRENT_AUTHORITY_CHANGED'):
                validate_decision(self.w.store,project_working_state(self.w.store,self.w.host.run_id),ResearchDecision.model_validate(self.search()))
            payload=payload_for(self.w.host,EvidenceDrivenAdapter())
        packet=json.loads(payload['messages'][1]['content'])['role_context']['research_packet']
        self.assertEqual(set(packet['capabilities']['legal']),{'stop'})

    def test_clock_persists_once_and_restore_cannot_reset_it(self):
        for p in self.patches:p.stop()
        self.w.working=None
        campaign.start_clock(self.w)
        clock=deepcopy(self.w.freeze['live_clock'])
        restored=pilot.restore(self.root)
        self.assertEqual(restored.freeze['live_clock'],clock)
        self.assertEqual(clock['deadline_unix']-clock['origin_unix'],36000.)
        with self.assertRaisesRegex(ValueError,'LIVE_CLOCK_ALREADY_STARTED'):
            campaign.start_clock(restored)
        self.assertEqual(restored.store.remaining()['used']['model_calls'],0)
        self.assertEqual(restored.store.remaining()['used']['backend_solves'],0)


class ConditionalBudgetTests(TestCase):
    def test_conditional_reserve_keeps_search_time_and_backend_count_boundary(self):
        from tools.batch_budget import downstream_available
        class FakeStore:
            def remaining(self,run_id=None,db=None):
                return {'remaining':dict(backend_solves=26 if run_id is None else 8,model_calls=24,tool_calls=180,wall_s=34000.,worker_calls=0)}
            def spendable(self,run_id,db=None):
                return {'remaining':dict(backend_solves=8,model_calls=22,tool_calls=170,wall_s=32800.,worker_calls=0)}
            def session(self,run_id,db=None):
                return {'state':{'role_context':{'campaign_permissions':{'phase_budget_policy':'conditional_verification@3.0.0'}}}}
        actual=downstream_available(FakeStore(),'current')
        self.assertEqual(actual['backend_solves'],6)
        self.assertEqual(actual['wall_s'],32800.)
        self.assertEqual(actual['tool_calls'],170)
        self.assertEqual(actual['model_calls'],22)
