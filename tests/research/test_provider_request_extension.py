"""Real Store addendum transactions; no Provider transport or science execution."""
from copy import deepcopy
import unittest
from tools.research.state import state,update
from tools.research.budget import extend_provider_requests
from tools.state_io import digest
from tools.platform_store import zero
from tests.research.test_passive_program_v2 import prepared_host_v2

class ProviderExtensionTests(unittest.TestCase):
    def fixture(self):
        h,_=prepared_host_v2();spec=deepcopy(state(h)['spec'])
        spec['provider_request_extension_policy']=dict(version='finite_provider_request_extension_v1',maximum_additional_requests=3)
        update(h,spec=spec)
        scope=dict(study_id=h.run_id,resolved_identity=spec['resolved_identity'],previous_request_limit=spec['budgets']['provider_requests'],additional_requests=2)
        approval=dict(version='provider_request_extension_approval_v1',approved=True,scope=scope,scope_identity=digest(scope),source='Explicit offline unit-test approval; no actual user/provider authorization')
        return h,approval

    def test_exact_finite_addendum_is_idempotent_and_preserves_costs(self):
        h,a=self.fixture();before=h.store.remaining();old=deepcopy(state(h));result=extend_provider_requests(h,a)
        self.assertEqual(result['provider_requests_sent'],0)
        self.assertEqual(h.store.remaining()['used'],before['used'])
        self.assertEqual(h.store.remaining()['limit']['model_calls'],before['limit']['model_calls']+2)
        self.assertEqual(state(h)['spec']['budgets']['physical_launches'],old['spec']['budgets']['physical_launches'])
        self.assertEqual(state(h)['spec']['budgets']['protected_provider_requests'],old['spec']['budgets']['protected_provider_requests'])
        self.assertTrue(state(h)['validation_extension_pending_binding'])
        self.assertTrue(extend_provider_requests(h,a)['already_applied'])
        self.assertEqual(len(state(h)['provider_request_extensions']),1)
        b=deepcopy(a);b['scope'].update(resolved_identity=state(h)['spec']['resolved_identity'],previous_request_limit=state(h)['spec']['budgets']['provider_requests']);b['scope_identity']=digest(b['scope'])
        with self.assertRaisesRegex(ValueError,'CAP_EXCEEDED'):extend_provider_requests(h,b)

    def test_wrong_scope_and_unsettled_worker_fail_without_mutation(self):
        h,a=self.fixture();before=h.store.remaining();bad=deepcopy(a);bad['scope']['study_id']='wrong-study';bad['scope_identity']=digest(bad['scope'])
        with self.assertRaisesRegex(ValueError,'EXACT_USER_APPROVED'):extend_provider_requests(h,bad)
        self.assertEqual(h.store.remaining(),before)
        h.store.reserve(h.run_id,'offline-unsettled-fixture','f'*64,h.actor,zero())
        with self.assertRaisesRegex(ValueError,'SETTLED_NONSUCCESS'):extend_provider_requests(h,a)
        self.assertNotIn('provider_request_extensions',state(h))

    def test_batch_cap_multiple_addenda_stale_identity_and_cumulative_cap(self):
        h,a=self.fixture();spec=deepcopy(state(h)['spec'])
        spec['provider_request_extension_policy'].update(maximum_additional_requests=16,maximum_requests_per_extension=8)
        update(h,spec=spec)
        before=h.store.remaining();old=deepcopy(state(h))
        def approval(extra):
            current=state(h)['spec'];value=deepcopy(a)
            value['scope'].update(resolved_identity=current['resolved_identity'],
                previous_request_limit=current['budgets']['provider_requests'],additional_requests=extra)
            value['scope_identity']=digest(value['scope'])
            return value
        with self.assertRaisesRegex(ValueError,'BATCH_CAP_EXCEEDED'):extend_provider_requests(h,approval(9))
        self.assertEqual(h.store.remaining(),before)
        first=approval(8);extend_provider_requests(h,first)
        stale=deepcopy(first);stale['source']='Different fixture approval with stale identity'
        with self.assertRaisesRegex(ValueError,'EXACT_USER_APPROVED'):extend_provider_requests(h,stale)
        extend_provider_requests(h,approval(8))
        with self.assertRaisesRegex(ValueError,'CAP_EXCEEDED'):extend_provider_requests(h,approval(1))
        self.assertEqual(h.store.remaining()['used'],before['used'])
        self.assertEqual(h.store.remaining()['limit']['model_calls'],before['limit']['model_calls']+16)
        for name in ('physical_launches','mathematical_evaluations','protected_provider_requests'):
            self.assertEqual(state(h)['spec']['budgets'][name],old['spec']['budgets'][name])
        self.assertEqual(len(state(h)['provider_request_extensions']),2)

if __name__=='__main__':unittest.main()
