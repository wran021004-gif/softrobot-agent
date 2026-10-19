"""Fabricated fixtures for control bounds and task/error inequalities; no science."""
import unittest
from copy import deepcopy
import numpy as np
from unittest.mock import patch
from tools.research.control_correction import (corrected_tensions,task_measure,
    fitting_residual,output_error_budget,improvement_test)
from tools.research.physical_replay import explicit_control_source,numerically_verified_source


class ControlCorrectionTests(unittest.TestCase):
    def setUp(self):
        self.outputs=dict(times_s=[0.,.3,.35],tip_positions_m=[[0.,0.,0.]]*3,
            tip_velocities_m_s=[[0.,0.,0.]]*3)

    def test_controls_preserve_zero_and_clip_physical_bounds(self):
        base=np.array([[0.,8.],[2.,3.],[7.,1.]])
        np.testing.assert_array_equal(corrected_tensions(base,[0,.2,.3],[0,.3],np.zeros(4),[8,8]),base)
        q=corrected_tensions(base,[0,.2,.3],[0,.3],[-3,3,3,-3],[8,8])
        self.assertTrue(np.all((q>=0)&(q<=8)))
        self.assertEqual(q[0].tolist(),[0,8]);self.assertEqual(q[-1].tolist(),[8,0])

    def test_knots_interpolate_channels_in_declared_order(self):
        q=corrected_tensions([[3,3]]*3,[0,.15,.3],[0,.3],[0,1,2,3],[8,8])
        np.testing.assert_allclose(q,[[3,4],[4,5],[5,6]])

    def test_nonfinite_and_unordered_controls_rejected(self):
        for knots,x in [([.3,0],[0]*4),([0,.3],[0,0,0,float('nan')])]:
            with self.assertRaises(ValueError):corrected_tensions([[1,1]],[.1],knots,x,[8,8])

    def test_hold_includes_both_boundaries_and_terminal(self):
        out=deepcopy(self.outputs);out['tip_velocities_m_s'][1]=[.04,0,0]
        out['tip_positions_m'][-1]=[.015,0,0]
        q=task_measure(out,[0,0,0],.3,.01,.02)
        self.assertAlmostEqual(q['normalized_gap'],1.)
        self.assertAlmostEqual(q['sum_normalized_excess'],2.)

    def test_pre_hold_speed_does_not_change_task_gap(self):
        out=deepcopy(self.outputs);out['tip_velocities_m_s'][0]=[99,0,0]
        self.assertEqual(task_measure(out,[0,0,0],.3,.01,.02)['normalized_gap'],0.)
        self.assertEqual(len(fitting_residual(out,[0,0,0],.3,.01,.02)),12)

    def test_sample_error_inequality_randomized_vectors(self):
        rng=np.random.default_rng(19)
        for _ in range(100):
            a=deepcopy(self.outputs);b=deepcopy(self.outputs)
            for out in (a,b):
                out['tip_positions_m']=rng.normal(0,.02,(3,3)).tolist()
                out['tip_velocities_m_s']=rng.normal(0,.04,(3,3)).tolist()
            qa=task_measure(a,[0,0,0],.3,.01,.02);qb=task_measure(b,[0,0,0],.3,.01,.02)
            bound=output_error_budget(a,b,.3,.01,.02)
            self.assertLessEqual(abs(qa['normalized_gap']-qb['normalized_gap']),bound['epsilon']+1e-12)
            self.assertFalse(bound['prospective_certified'])

    def test_error_bound_grid_mismatch_rejected(self):
        b=deepcopy(self.outputs);b['times_s'][-1]=.34
        with self.assertRaises(ValueError):output_error_budget(self.outputs,b,.3,.01,.02)

    def test_two_endpoint_sufficient_condition(self):
        q=improvement_test({'normalized_gap':3},{'normalized_gap':1},
            {'normalized_gap':3.2},{'normalized_gap':1.1},{'epsilon':.3},{'epsilon':.2})
        self.assertAlmostEqual(q['sufficient_improvement_lower_bound'],1.5)
        self.assertTrue(q['sufficient_condition_met']);self.assertTrue(q['direction_agrees'])
        self.assertFalse(q['prospective_guarantee'])

    def test_explicit_controls_never_masquerade_as_verified(self):
        value=dict(source_kind='explicit_control_schedule_v1',task_acceptance='unmeasured',provenance={'source':'fixture'})
        self.assertTrue(explicit_control_source(value));self.assertFalse(numerically_verified_source(value))
        value['task_acceptance']='passed';self.assertFalse(explicit_control_source(value))

    def test_gap_interval_encloses_returned_value(self):
        out=deepcopy(self.outputs);out['tip_velocities_m_s'][1]=[.02,.003,.004]
        q=task_measure(out,[0,0,0],.3,.01,.02)
        lo,hi=q['returned_array_gap_interval']
        self.assertLessEqual(lo,q['normalized_gap']);self.assertGreaterEqual(hi,q['normalized_gap'])

    def test_correction_configuration_has_finite_scope(self):
        from tools.research.config import resolve
        spec=resolve('configs/research/study_sorosim_s510_correction.json')
        self.assertEqual(spec['budgets']['physical_launches'],192)
        self.assertEqual(spec['budgets']['provider_requests'],0)
        self.assertEqual(spec['correction_search']['knots_s'],[0.,.18,.3])


class LedgerReportingTests(unittest.TestCase):
    def test_plan_response_does_not_rebuild_full_history(self):
        from tests.research.test_agent_feedback import AgentFeedbackTests
        from tools.research import core
        fixture=AgentFeedbackTests('runTest')
        fixture.setUp()
        try:
            with patch.object(core,'packet',side_effect=AssertionError('full history must not be rebuilt')):
                fixture.generate()
                use=core.resource_use(fixture.host)
                self.assertEqual(use['shared_ledger'],fixture.host.store.remaining())
                self.assertIn('numerical_reserved_s',use)
        finally:fixture.doCleanups()


if __name__=='__main__':unittest.main()
