"""Small regression checks; synthetic fixtures are not scientific evidence."""
from pathlib import Path
from types import SimpleNamespace
import unittest

import numpy as np

from tests.research.s141_model_validity import geometry_errors, legal_point, read, returned_geometry_point

EVIDENCE = Path(__file__).resolve().parents[2]/'evidence/s141_model_validity'


class ModelValidityTests(unittest.TestCase):
    def test_absolute_state_and_input_offsets(self):
        # Synthetic scalar-state quadratic: exact Taylor remainder is dx**2.
        model = SimpleNamespace(x0=[2.], u0=[3.], y0=[4., 7., 1.],
            C=[[4.], [2.], [0.]], D=[[0.], [1.], [0.]])
        def h(x, u):
            return (np.array([x[0]**2, 2*x[0]+u[0], 1.]),)
        result = geometry_errors(h, model, np.array([[2.1], [1.8]]), np.array([[4.], [2.]]))
        np.testing.assert_allclose(result['error_m'], [.01, .04], atol=1e-14)

    def test_failed_constructor_is_not_promoted_to_equilibrium(self):
        # Synthetic failed IK return can independently describe a geometric state.
        saved = dict(points=[dict(name='halfway_waypoint', available=False,
            construction=dict(requested_world_point_m=[1., 0., 0.], success=False, status=0))],
            optimizer_returns=[dict(kind='least_squares_attempts', x=[.5])])
        inp = SimpleNamespace(robot=SimpleNamespace(structure=SimpleNamespace(
            data=dict(tendons=[dict(pretension_n=.2)]))))
        graph = (inp, None, None, lambda x,u: (np.array([1., 0., 0.]),))
        point = returned_geometry_point(saved, graph, 1e-8)
        self.assertTrue(legal_point(point, [8.]))
        self.assertFalse(point['construction']['static_equilibrium'])
        self.assertFalse(point['construction']['optimizer_success'])
        self.assertFalse(saved['points'][0]['available'])
        self.assertFalse(legal_point(dict(point, available=False), [8.]))
        self.assertFalse(legal_point(dict(point, u=[-1.]), [8.]))

    def test_saved_full_task_uses_original_initializer_and_legal_control(self):
        frozen = read(EVIDENCE/'input.json')
        construction = read(EVIDENCE/'construction.json')
        for label, case in frozen['cases'].items():
            for point in construction['cases'][label]['points']:
                if point['name'] != 'controller_start_input':
                    self.assertFalse(point['available'])
                    self.assertFalse(point['construction']['success'])
            raw = read(EVIDENCE/f'{label}-bent-conic.json')
            model, trajectory = raw['model'], raw['trajectory']
            np.testing.assert_allclose(np.array(model['x0'])+trajectory['replay']['states'][0],
                case['saved_model']['x0'], atol=1e-14)
            controls = np.array(trajectory['applied_input_n'])
            self.assertEqual(controls.shape, (35, 6))
            self.assertTrue(np.all(controls >= 0) and np.all(controls <= 8))
            self.assertTrue(trajectory['all_requested_checked'])
            self.assertEqual(trajectory['optimality_status'], 'numerically_checked')
            self.assertFalse(model['operating_point']['construction']['static_equilibrium'])
            self.assertGreater(np.linalg.norm(model['drift']), 1.)


if __name__ == '__main__':
    unittest.main()
