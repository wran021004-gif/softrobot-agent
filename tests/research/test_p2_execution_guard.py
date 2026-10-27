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

    def test_optional_v3_conic_does_not_block_agent_but_legacy_remains_strict(self):
        from tools.research.tool_readiness import execution_environment
        from tools.research.optimal_capability import CONIC
        import sys
        spec=resolve(ROOT/'configs/research/study_p2_v3_agent_positive_high.json')
        spec['runtime']['research_python']=sys.executable
        spec['numerical_environment']={}
        with patch('tools.research.optimal_capability.dependencies',return_value={'available':False,'reason':'fixture'}):
            result=execution_environment(spec)
            self.assertEqual(result['status'],'ready')
            self.assertFalse(result['conic_required_before_agent'])
            self.assertFalse(result['conic']['available'])
            spec.pop('mathematical_method_scope')
            self.assertEqual(execution_environment(spec)['status'],'not_ready')
            self.assertIn(CONIC,spec['mathematical_methods'])

    def test_windows_session_storage_handles_long_snapshot_path(self):
        import asyncio,shutil,uuid
        from tools.research.agent import session_storage,session_storage_path
        folder=ROOT/'runs'/('p2-path-fixture-'+uuid.uuid4().hex[:8])
        try:
            folder.mkdir(parents=True)
            root=folder/('a'*70)/'framework_sessions'
            key='session/p2-v3-positive-high-agent-remaining-20261028/scopes/agent/default/snapshots/p2-check-'+uuid.uuid4().hex+'.json'
            storage=session_storage(root)
            asyncio.run(storage.write(key,b'verified'))
            self.assertEqual(asyncio.run(storage.read(key)),b'verified')
            scoped=storage.namespace('context')
            asyncio.run(scoped.write(key,b'context'))
            self.assertEqual(asyncio.run(scoped.read(key)),b'context')
        finally:
            if folder.resolve().parent!=(ROOT/'runs').resolve():raise ValueError('WORKSPACE_FIXTURE_REQUIRED')
            shutil.rmtree(session_storage_path(folder))
