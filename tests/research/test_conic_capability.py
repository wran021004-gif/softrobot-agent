"""Analytic synthetic fixtures and saved models only; never start a physics worker."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import cvxpy as cp
import numpy as np

from extensions.math_analysis.conic_capability import conic_capability
from extensions.math_analysis.task_capability import task_capability
from extensions.math_analysis.trajectory import verify_witness
from tests.research.test_trajectory_feasibility import fixture


def terminal(target=.5, radius=.1, nominal=0.):
    model, req, protocol = fixture(nominal=nominal, duration=1.)
    c = req.constraints[0].model_copy(update=dict(indices=[1], reference=[[target]], radius=radius))
    return model, req.model_copy(update=dict(constraints=[c])), protocol


class ConicTests(unittest.TestCase):
    def checked(self, m, r, p, optimum, **kwargs):
        out = conic_capability(m, r, p, **kwargs)
        self.assertEqual(out['optimality_status'], 'numerically_checked', out)
        self.assertAlmostEqual(out['replayed_violation'], optimum, places=6)
        self.assertAlmostEqual(out['dual_checks']['support_lower_estimate'], optimum, places=6)
        self.assertTrue(out['replay']['numerically_valid'])
        self.assertIsNone(out['certificate'])
        json.dumps(out, allow_nan=False)
        return out

    def test_norm_analytic_negative_zero_positive_and_nonzero_nominal(self):
        for target, expected in ((.5, -1.), (1., 0.), (1.25, 1.), (-.75, 1.)):
            with self.subTest(target=target):
                # y=delta input, absolute tension in [0,1], nominal=.25.
                m, r, p = terminal(target=target, radius=.25, nominal=.25)
                out = self.checked(m, r, p, expected)
                np.testing.assert_allclose(np.array(out['applied_input_n'])-out['delta_input_n'], .25)
                self.assertGreaterEqual(out['replay']['minimum_tension_margin_n'], 0.)
                if expected > 0:
                    self.assertEqual(out['status'], 'inconclusive')

    def test_joint_conflict_and_dual_weights(self):
        for radius, expected in ((.1, 2.), (.3, 0.), (.6, -.5)):
            m, r, p = terminal(.2, radius)
            c = r.constraints[0].model_copy(update=dict(constraint_id='conflict', reference=[[.8]]))
            r = r.model_copy(update=dict(constraints=r.constraints+[c]))
            out = self.checked(m, r, p, expected)
            np.testing.assert_allclose([v['signed_multiplier'] for v in out['dual_checks']['constraint_multipliers']],
                                       [.5, .5], atol=1e-7)
            slsqp = task_capability(m, r, p)
            self.assertAlmostEqual(slsqp['best_found_violation'], out['replayed_violation'], places=6)

    def test_asymmetric_interval_lp_and_multiplier_sides(self):
        m, r, p = terminal(.2)
        c = r.constraints[0].model_copy(update=dict(kind='component_interval', radius=None, lower=[-.1], upper=[.3]))
        r = r.model_copy(update=dict(constraints=[c]))
        out = self.checked(m, r, p, -2/3)
        self.assertAlmostEqual(out['applied_input_n'][0][0], .3, places=7)
        duals = out['dual_checks']['constraint_multipliers']
        self.assertEqual([v['side'] for v in duals], ['lower', 'upper'])
        self.assertTrue(all(v['normalization_scale'] == .3 for v in duals))
        self.assertAlmostEqual(task_capability(m, r, p)['best_found_violation'], -2/3)

    def test_genuine_vector_norm_and_mixed_constraint(self):
        m, r, p = terminal()
        out = m.endpoint_outputs[0]
        out.value0=[0., .3]; out.C=[[1.], [0.]]; out.D=[[0.], [0.]]
        c = r.constraints[0].model_copy(update=dict(signal=r.constraints[0].signal.model_copy(update=dict(dimension=2)),
                                                  reference=[[.5, 0.]], radius=.2))
        d = c.model_copy(update=dict(constraint_id='interval', kind='component_interval', radius=None,
                                     lower=[-.4, -.4], upper=[.4, .4]))
        out = self.checked(m, r.model_copy(update=dict(constraints=[c, d])), p, .5)
        self.assertEqual(out['numerical_feasibility'], 'positive_optimum_numerical_evidence')
        self.assertGreater(out['dual_checks']['support_lower_estimate'], 0.)

    def test_initial_drift_reference_and_previous_hold(self):
        m, r, p = fixture(nominal=.4, feedthrough=.3)
        m.A=[[-.2]]; m.drift=[.07]
        m.operating_point['previous_applied_input_n']=[.7]
        out = conic_capability(m, r, p, initial_delta=[.12])
        self.assertEqual(out['optimality_status'], 'numerically_checked')
        self.assertAlmostEqual(out['replay']['records'][0]['output'][0], .12+.3*(.7-.4))
        self.assertLess(out['replay']['max_prediction_replay_error'], 1e-12)
        slsqp = task_capability(m, r, p, initial_delta=[.12])
        self.assertAlmostEqual(slsqp['best_found_violation'], out['replayed_violation'], places=6)

    def test_partial_sampling_and_zero_horizon_norm_and_interval(self):
        for start in (2., 3.):
            for interval in (False, True):
                m, r, p = fixture(start=start, sample=.5, feedthrough=.1)
                # A finer aligned control grid than sample grid exercises repeated holds.
                p.period_s=.5
                if interval:
                    c = r.constraints[0].model_copy(update=dict(kind='component_interval', radius=None, lower=[-.1], upper=[.3]))
                    r = r.model_copy(update=dict(constraints=[c]))
                out = conic_capability(m, r, p)
                self.assertEqual(out['optimality_status'], 'numerically_checked', out)
                self.assertFalse(out['all_requested_checked'])
                self.assertEqual(out['coverage'][0]['unchecked_indices'], list(range(int(start*2))))
                if start == 3.:
                    self.assertEqual(out['delta_input_n'], [])
                    self.assertIsNone(out['replay']['minimum_tension_margin_n'])
                json.dumps(out, allow_nan=False)

    def test_unsupported_outputs_and_initial_feedthrough_coverage(self):
        m, r, p = fixture(feedthrough=.1)
        m.operating_point.pop('previous_applied_input_n')
        out = conic_capability(m, r, p)
        self.assertEqual(out['coverage'][0]['unchecked_indices'], [0])
        self.assertFalse(out['all_requested_checked'])
        m.endpoint_outputs[0].units='mm'
        out = conic_capability(m, r, p)
        self.assertEqual(out['status'], 'not_applicable')
        self.assertEqual(out['coverage_counts']['analyzed'], 0)

    def test_invalid_normalization_and_nonfinite_inputs(self):
        m, r, p = terminal(radius=0.)
        self.assertEqual(conic_capability(m, r, p)['status'], 'not_applicable')
        for bounds in (([0.], [0.]), ([float('nan')], [.3])):
            c = r.constraints[0].model_copy(update=dict(kind='component_interval', radius=None, lower=bounds[0], upper=bounds[1]))
            out = conic_capability(m, r.model_copy(update=dict(constraints=[c])), p)
            self.assertEqual(out['status'], 'not_applicable')
            json.dumps(out, allow_nan=False)
        m, r, p = terminal()
        m.B=[[float('nan')]]
        self.assertEqual(conic_capability(m, r, p)['status'], 'not_applicable')
        m, r, p = terminal()
        c = r.constraints[0].model_copy(update=dict(reference=[[float('inf')]]))
        self.assertEqual(conic_capability(m, r.model_copy(update=dict(constraints=[c])), p)['status'], 'not_applicable')

    def test_real_iteration_limit_and_solver_exception(self):
        m, r, p = terminal(.8)
        with self.assertWarns(UserWarning):
            out = conic_capability(m, r, p, solver_options=dict(max_iter=1))
        self.assertEqual(out['optimality_status'], 'unknown')
        self.assertIsNone(out['certificate'])
        self.assertEqual(out['solver']['status'], 'user_limit')
        with patch.object(cp.Problem, 'solve', side_effect=cp.error.SolverError('fixture failure')):
            out = conic_capability(m, r, p)
        self.assertEqual(out['status'], 'inconclusive')
        self.assertEqual(out['solver']['error'], 'fixture failure')

    def test_no_primal_and_nonfinite_primal(self):
        m, r, p = terminal()
        solve = cp.Problem.solve
        for corrupt in ('missing', 'nan'):
            def fake(problem, **kw):
                solve(problem, **kw)
                for variable in problem.variables():
                    variable.save_value(None if corrupt == 'missing' else np.full(variable.shape, np.nan))
            with patch.object(cp.Problem, 'solve', fake):
                out = conic_capability(m, r, p)
            self.assertEqual(out['optimality_status'], 'unknown')
            self.assertNotIn('replayed_violation', out)
            json.dumps(out, allow_nan=False)

    def test_replay_failure_withholds_quantities(self):
        def corrupt(*args):
            out = verify_witness(*args); out['max_prediction_replay_error']=1.; return out
        with patch('extensions.math_analysis.conic_capability.verify_witness', side_effect=corrupt):
            out = conic_capability(*terminal())
        self.assertFalse(out['all_requested_checked'])
        self.assertEqual(out['quantities'], {})
        self.assertEqual(out['optimality_status'], 'unknown')

    def test_tiny_box_repair_is_explicit_and_large_excursion_rejected(self):
        solve = cp.Problem.solve
        for excursion in (5e-9, .01):
            def corrupt(problem, **kw):
                solve(problem, **kw)
                for v in problem.variables():
                    if v.name() == 'physical_delta_tensions_n':
                        v.save_value(np.array([-excursion]))
            with patch.object(cp.Problem, 'solve', corrupt):
                out = conic_capability(*terminal(0.))
            self.assertEqual(out['raw_primal']['applied_input_n'], [[-excursion]])
            if excursion < 1e-8:
                self.assertEqual(out['applied_input_n'], [[0.]])
                self.assertEqual(out['box_repair_inf_n'], excursion)
                self.assertTrue(out['replay']['numerically_valid'])
            else:
                self.assertNotIn('replayed_violation', out)
                self.assertEqual(out['optimality_status'], 'unknown')

    def test_inaccurate_status_is_not_promoted_by_good_residuals(self):
        solve = cp.Problem.solve
        def inaccurate(problem, **kw):
            solve(problem, **kw)
            problem._status = cp.OPTIMAL_INACCURATE
        with patch.object(cp.Problem, 'solve', inaccurate):
            out = conic_capability(*terminal())
        self.assertEqual(out['solver']['status'], 'optimal_inaccurate')
        self.assertEqual(out['optimality_status'], 'unknown')
        self.assertEqual(out['status'], 'feasible_witness')

    def test_corrupted_dual_cannot_create_optimality(self):
        solve = cp.Problem.solve
        def corrupt(problem, **kw):
            solve(problem, **kw)
            for c in problem.constraints:
                for dual in c.dual_variables:
                    dual.save_value(np.full(dual.shape, -10.))
        with patch.object(cp.Problem, 'solve', corrupt):
            out = conic_capability(*terminal())
        self.assertEqual(out['optimality_status'], 'unknown')
        self.assertTrue(out['replay']['numerically_valid'])
        self.assertEqual(out['dual_checks']['status'], 'unavailable')

    def test_corrupted_stationarity_support_bound_remains_conservative(self):
        solve = cp.Problem.solve
        def corrupt(problem, **kw):
            solve(problem, **kw)
            # Keep SOC feasibility but deliberately break stationarity.
            for c in problem.constraints:
                if isinstance(c, cp.constraints.second_order.SOC):
                    c.dual_variables[0].save_value(np.array([1.]))
                    c.dual_variables[1].save_value(np.array([[.5]]))
        with patch.object(cp.Problem, 'solve', corrupt):
            out = conic_capability(*terminal())
        self.assertEqual(out['optimality_status'], 'unknown')
        self.assertLessEqual(out['dual_checks']['support_lower_estimate'], -1.)
        self.assertGreater(out['dual_checks']['stationarity_inf'], 1.)

    def test_options_are_local_and_provenance_is_stable(self):
        m, r, p = terminal()
        before = deepcopy(vars(p))
        first = conic_capability(m, r, p)
        second = conic_capability(m, r, p, solver_options=dict(tol_feas=1e-10))
        self.assertEqual(vars(p), before)
        self.assertEqual(first['provenance'], second['provenance'])
        self.assertIsNone(first['solver']['reported_dual_residual'])
        for options in ({'solver':'SCS'}, {'max_iter':0}, {'tol_feas':float('nan')}, {'tol_feas':'bad'}):
            self.assertEqual(conic_capability(m, r, p, solver_options=options)['status'], 'not_applicable')

    def test_saved_b_pair_no_model_builder(self):
        from schemas.platform_analysis import EndpointLinearizedModel, TaskAnalysisProtocol, TaskAnalysisRequirement
        source = Path(__file__).resolve().parents[2]/'evidence/s129_math_capability/gvs_pair.json'
        saved = json.loads(source.read_text(encoding='utf-8'))
        for key in ('baseline', 'changed'):
            row = saved[key]
            m = EndpointLinearizedModel.model_validate(row['model'])
            r = TaskAnalysisRequirement.model_validate(row['task_analysis'])
            p = TaskAnalysisProtocol.model_validate(row['protocol'])
            out = conic_capability(m, r, p)
            self.assertEqual(out['optimality_status'], 'numerically_checked', out)
            self.assertTrue(out['all_requested_checked'])
            self.assertLessEqual(out['replayed_violation'], row['trajectory']['best_found_violation']+1e-7)
            self.assertLess(out['dual_checks']['replayed_support_gap'], 1e-6)


if __name__ == '__main__':
    unittest.main()
