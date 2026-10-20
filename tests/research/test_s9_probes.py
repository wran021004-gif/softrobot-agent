"""Effective physical inputs and response/cost diagnostics; synthetic test fixtures."""
import unittest
import numpy as np
from tests.research import test_local_control_search as fixtures
start=fixtures.start
from tools.research.local_control_search import search


SETTINGS=dict(version='local_control_search_v2',active_coefficients=[11],method='response',
    iterations=3,evaluation_requests=8,initial_radius_n=.02,difference_step_n=.01)


class ProbeTests(unittest.TestCase):
    def test_no_input_room_never_calls_zero_change_probes(self):
        s=start()
        # Last knot is at the right endpoint, after the last applied interval start.
        f=fixtures.LocalSearchTests();r=search([s],f.evaluator(),dict(SETTINGS,
            knots_s=[.34,.35],correction_window_s=[.34,.35],active_coefficients=[7]))
        self.assertEqual(len(f.calls),1)
        self.assertEqual(r['stop_reason'],'degenerate_local_response')
        self.assertGreater(r['cost_feedback']['ineffective_probe_attempts'],0)
        self.assertEqual(r['cost_feedback']['unique_response_probes'],0)
        self.assertEqual(r['local_responses'][0]['input_direction_rank'],0)

    def test_opposite_direction_at_force_limit_is_effective(self):
        s=start()
        for row in s['schedule']['trajectory']['tensions_n']:row[3]=8
        f=fixtures.LocalSearchTests();r=search([s],f.evaluator(),dict(SETTINGS,iterations=1))
        probe=next(row for row in r['candidates'] if row['label']=='finite_difference')
        self.assertLess(probe['coefficients_n'][11],0)
        self.assertGreater(probe['effective_input_change_inf_n'],0)
        self.assertFalse(probe['projected_response'])
        self.assertGreater(r['cost_feedback']['ineffective_probe_attempts'],0)

    def test_projected_shape_and_zero_observed_response_are_reported(self):
        s=start()
        for i,row in enumerate(s['schedule']['trajectory']['tensions_n']):row[3]=8 if i>30 else 0
        f=fixtures.LocalSearchTests();r=search([s],f.evaluator(),SETTINGS)
        probe=next(row for row in r['candidates'] if row['label']=='finite_difference')
        self.assertTrue(probe['projected_response'])
        self.assertEqual(r['local_responses'][0]['response_rank'],0)
        self.assertEqual(r['stop_reason'],'degenerate_local_response')
        self.assertEqual(len(f.calls),2)

    def test_cached_valid_response_is_information_without_new_charge(self):
        f=fixtures.LocalSearchTests();base=f.evaluator()
        def cached(*args):return dict(base(*args),cache_hit=True,cost_s=0.)
        r=search([start(),start('b')],cached,dict(SETTINGS,iterations=1))
        cost=r['cost_feedback']
        self.assertEqual(cost['new_physical_evaluations'],0)
        self.assertEqual(cost['cache_reuses'],len(f.calls))
        self.assertGreater(cost['unique_response_probes'],0)
        self.assertGreater(cost['duplicate_applied_sequences'],0)
        self.assertEqual(cost['charged_numerical_s'],0)
        self.assertEqual(len(r['start_feedback']),2)
        for row in r['candidates']:
            self.assertTrue(all(c==0 for c in row['coefficients_n'][:11]))


if __name__=='__main__':unittest.main()
