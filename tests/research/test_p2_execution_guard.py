"""Regression checks for the opt-in worker boundary, no scientific execution."""
from unittest import TestCase
from unittest.mock import patch
from tools.research.config import ROOT,resolve
from tools.research.state import bounded_worker_timeout

class P2ExecutionGuardTests(TestCase):
    def test_guard_uses_remaining_ledger_and_preserves_count_mode(self):
        s={'spec':{},'numerical_s':580.0}
        with patch('tools.research.state.state',return_value=s):
            self.assertIsNone(bounded_worker_timeout(None))
            s['spec']['numerical_execution_guard']=dict(version='bounded_worker_v1',limit_s=600,worker_timeout_s=180,margin_s=10)
            self.assertEqual(bounded_worker_timeout(None),10)
            s['numerical_s']=590
            with self.assertRaisesRegex(ValueError,'BOUNDED_NUMERICAL_ALLOWANCE_EXHAUSTED'):bounded_worker_timeout(None)
    def test_p2_guard_is_frozen_and_legacy_time_contract_unchanged(self):
        spec=resolve(ROOT/'configs/research/study_p2_v3_native_positive_high.json')
        self.assertEqual(spec['numerical_execution_guard']['worker_timeout_s'],180)
        self.assertIsNone(spec['budgets']['numerical_s'])
        self.assertLessEqual(spec['budgets']['mathematical_evaluations'],5)

    def test_pending_p3_templates_resolve_but_reject_unapproved_execution(self):
        from unittest.mock import Mock
        from tools.research.state import require_authorization
        for name in ('study_p3a_v3_pending.json','study_p3b_v3_pending.json'):
            spec=resolve(ROOT/'configs/research'/name)
            self.assertIn('PENDING_EXPLICIT_P3_APPROVAL',spec['authorization'])
            self.assertEqual(spec['budgets']['provider_requests'],0)
            self.assertEqual(spec['budgets']['mathematical_evaluations'],0)
            self.assertEqual(spec['budgets']['physical_launches'],0)
            h=Mock();h.store.events.return_value=[];h.run_id=spec['study_id']
            with patch('tools.research.state.state',return_value={'spec':spec}):
                with self.assertRaisesRegex(ValueError,'INDEPENDENT_FORMAL_STUDY_APPROVAL_REQUIRED'):
                    require_authorization(h)
