"""Fabricated sparse response/multistart outcomes; no provider or physical worker."""
from copy import deepcopy
import unittest
import numpy as np
from tests.research import test_local_control_search as fixtures
start=fixtures.start
from tools.research.local_control_search import search
from tools.research.contracts import LocalControlSearchSettings, ControlSearchRequest


class SparseSearchTests(unittest.TestCase):
    def test_sparse_probes_and_inactive_coefficients(self):
        fixture=fixtures.LocalSearchTests();evaluate=fixture.evaluator()
        r=search([start()],evaluate,dict(version='local_control_search_v2',active_coefficients=[11],
            method='response',evaluation_requests=3,iterations=1,initial_radius_n=.02))
        self.assertEqual(r['finite_difference_evaluations'],1)
        self.assertEqual(r['search_dimension'],1)
        self.assertEqual([x['label'] for x in r['candidates']],['baseline','finite_difference','local_response_proposal'])
        for row in r['candidates']:
            np.testing.assert_array_equal(row['coefficients_n'][:11],np.zeros(11))
        for u in fixture.calls:np.testing.assert_array_equal(u[:,:3],np.full((35,3),4.))

    def test_all_start_validation_precedes_any_evaluation(self):
        fixture=fixtures.LocalSearchTests();evaluate=fixture.evaluator();b=start('b')
        b['schedule']['trajectory']['tendon_order'][0]='different'
        with self.assertRaisesRegex(ValueError,'COMPATIBLE'):search([start(),b],evaluate,{'version':'local_control_search_v2'})
        self.assertEqual(fixture.calls,[])
        with self.assertRaisesRegex(ValueError,'OUTSIDE'):search([start()],evaluate,{'version':'local_control_search_v2','active_coefficients':[12]})
        self.assertEqual(fixture.calls,[])

    def test_sparse_multiple_starts_share_cap_and_stop_first_pass(self):
        fixture=fixtures.LocalSearchTests()
        r=search([start(),start('b')],fixture.evaluator(passes=True),dict(version='local_control_search_v2',active_coefficients=[11],evaluation_requests=4))
        self.assertEqual(len(fixture.calls),1);self.assertEqual(r['stop_reason'],'first_original_task_pass')

    def test_duplicate_and_coerced_indices_rejected(self):
        for values in ([1,1],[-1],[True],[1.5]):
            with self.assertRaises(ValueError):LocalControlSearchSettings(version='local_control_search_v2',active_coefficients=values)

    def test_public_multistart_contract_is_same_source_protocol(self):
        ref={'artifact_id':'a'*64,'media_type':'application/json'}
        q=ControlSearchRequest(candidate=ref,source=ref,settings={'version':'local_control_search_v2'},additional_starts=[dict(candidate=ref,source=ref)])
        self.assertEqual(q.additional_starts[0].source,q.source)
        self.assertNotIn('active_coefficients',LocalControlSearchSettings().model_dump())


if __name__=='__main__':unittest.main()
