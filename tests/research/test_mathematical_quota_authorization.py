"""Explicit unmetered addenda over real Store fixtures; no numerical launches."""
from copy import deepcopy
import unittest
from tools.research.budget import authorize_unmetered_mathematics,mathematical_remaining,mathematics_fits
from tools.research.state import state,update,require_research_authorization,guard,save
from tools.research.analysis import admission
from tools.state_io import digest
from tools.platform_store import zero
from tests.research.test_phs2d_knowledge_start import fixture


class MathematicalQuotaAuthorizationTests(unittest.TestCase):
    def approval(self,h):
        spec=state(h)['spec'];scope=dict(study_id=h.run_id,resolved_identity=spec['resolved_identity'],
            previous_limit=spec['budgets']['mathematical_evaluations'],new_limit=None)
        return dict(version='unmetered_mathematics_approval_v1',approved=True,source='Explicit offline authorization fixture, no live permission',scope=scope,scope_identity=digest(scope))

    def test_exact_addendum_retains_costs_and_admits_beyond_old_count_after_new_grant(self):
        with fixture() as h:
            update(h,mathematical_evaluations=20,analysis_costs=[dict(origin='synthetic_fixture',numerical_s=3.)],numerical_s=3.)
            before=deepcopy(state(h));ledger=h.store.remaining();a=self.approval(h)
            result=authorize_unmetered_mathematics(h,a);s=state(h)
            self.assertEqual(h.store.remaining(),ledger)
            self.assertEqual(s['mathematical_evaluations'],20);self.assertEqual(s['analysis_costs'],before['analysis_costs'])
            self.assertEqual(s['profile'],before['profile']);self.assertEqual(s['numerical_s'],3.)
            for k,v in before['spec']['budgets'].items():
                if k!='mathematical_evaluations':self.assertEqual(s['spec']['budgets'][k],v)
            self.assertIsNone(mathematical_remaining(s['spec'],1000000))
            self.assertTrue(mathematics_fits(s['spec'],1000000,5000))
            self.assertEqual(admission(h,5)['admitted'],5)
            self.assertTrue(authorize_unmetered_mathematics(h,a)['already_applied'])
            self.assertEqual(len(state(h)['mathematical_quota_authorizations']),1)
            with self.assertRaisesRegex(ValueError,'INDEPENDENT_FORMAL_STUDY_APPROVAL'):require_research_authorization(h)
            scope=dict(study_id=h.run_id,resolved_identity=s['spec']['resolved_identity'],execution_scopes=['registered mathematics'])
            save(h,dict(user_approval='Offline fixture only',scope=scope,scope_identity=digest(scope)),'formal_study_authorization')
            require_research_authorization(h)
            with self.assertRaisesRegex(ValueError,'AUTHORIZED_EXTENSION_REQUIRES_COMMITTED'):guard(h)
            self.assertEqual(result['provider_requests_sent'],0)

    def test_wrong_identity_non_null_target_and_pending_work_fail_atomically(self):
        with fixture() as h:
            a=self.approval(h);before=deepcopy(state(h));ledger=h.store.remaining()
            for change in (dict(new_limit=100),dict(resolved_identity='0'*64),dict(previous_limit=19)):
                bad=deepcopy(a);bad['scope'].update(change);bad['scope_identity']=digest(bad['scope'])
                with self.assertRaisesRegex(ValueError,'EXACT_EXPLICIT_UNMETERED'):authorize_unmetered_mathematics(h,bad)
            self.assertEqual(state(h),before);self.assertEqual(h.store.remaining(),ledger)
            update(h,pilot={**before['pilot'],'unconsumed_response':'offline-response'})
            with self.assertRaisesRegex(ValueError,'SETTLED_NONSUCCESS'):authorize_unmetered_mathematics(h,a)
            update(h,pilot=before['pilot'])
            h.store.reserve(h.run_id,'offline-pending','f'*64,h.actor,zero())
            with self.assertRaisesRegex(ValueError,'SETTLED_NONSUCCESS'):authorize_unmetered_mathematics(h,a)
            self.assertEqual(state(h),before)


if __name__=='__main__':unittest.main()
