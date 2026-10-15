"""Offline M2 fixtures; fabricated systems are not robot scientific evidence."""
from copy import deepcopy
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import numpy as np
from schemas.platform_analysis import TaskAnalysisRequirement
from extensions.math_analysis.trajectory import trajectory_feasibility, sampled_maps, verify_witness


def fixture(nu=1, nominal=.4, start=0., duration=3., sample=1., feedthrough=0.):
    output = NS(name='test_output', units='m', frame='world', value0=[0.], C=[[1.]], D=[[feedthrough]*nu])
    model = NS(A=[[0.]], B=[[1.]*nu], drift=[0.], u0=[nominal]*nu, time_domain='continuous',
        binding=dict(tension_limits_n=[1.]*nu), endpoint_outputs=[output], input_scales=[1.]*nu,
        operating_point=dict(actual_time_s=start, remaining_task_s=duration-start, previous_applied_input_n=[nominal]*nu))
    p = NS(period_s=1., horizon_alignment_atol_s=1e-12, endpoint_check_atol=1e-8, endpoint_max_iterations=100)
    times = [i*sample for i in range(round(duration/sample)+1)]
    req = TaskAnalysisRequirement(binding=dict(fixture=True),duration_s=duration,sample_period_s=sample,time_grid_s=times,
        physical_inputs=dict(lower=[0.]*nu,upper=[1.]*nu),constraints=[dict(constraint_id='moving',
            signal=dict(name='test_output',entity='fixture',dimension=1,units='m',frame='world',phase='post_step'),
            indices=list(range(len(times))),kind='norm_bound',radius=.02,
            reference=[[.2*t] for t in times],provenance=['/synthetic_fixture'])])
    return model,req,p


class NumericalTests(unittest.TestCase):
    def test_known_shared_witness_moving_reference_and_total_bounds(self):
        model,req,p = fixture()
        out = trajectory_feasibility(model,req,p)
        self.assertEqual(out['status'],'feasible_witness')
        self.assertTrue(out['full_requested_coverage'])
        self.assertLess(out['replay']['max_prediction_replay_error'],1e-12)
        self.assertEqual(len(out['replay']['records']),4)
        self.assertTrue(np.all(np.array(out['applied_input_n']) >= 0))
        self.assertTrue(np.all(np.array(out['applied_input_n']) <= 1))
        np.testing.assert_allclose(np.array(out['applied_input_n'])-out['delta_input_n'],.4)
        self.assertGreaterEqual(out['replay']['minimum_tension_margin_n'],-p.endpoint_check_atol)

    def test_matrix_predictions_equal_recurrence_with_drift_initial_and_feedthrough(self):
        model,req,p = fixture(nu=5, feedthrough=.3)
        model.A=[[-.2]]; model.drift=[.07]
        dynamics,maps = sampled_maps(model,3,1.,initial_delta=[.12])
        from extensions.math_analysis.trajectory import _output_map
        z=np.arange(15).reshape(3,5)/100
        rows=[]
        c=req.constraints[0]; output=model.endpoint_outputs[0]
        for k in range(4):
            base,matrix=_output_map(output,maps[k],k,3,np.array(model.u0),np.array(model.u0))
            rows.append((c,k,k,np.array(c.reference[k]),output,base,matrix))
        from extensions.math_analysis.trajectory import time_scope
        replay=verify_witness(model,dynamics,[.12],z,rows,time_scope(req,p,0.),1e-8)
        self.assertLess(replay['max_prediction_replay_error'],1e-12)
        self.assertFalse(verify_witness(model,dynamics,[.12],z[:,:4],rows,time_scope(req,p,0.),1e-8)['passed'])
        z[0,0]=np.nan
        self.assertFalse(verify_witness(model,dynamics,[.12],z,rows,time_scope(req,p,0.),1e-8)['passed'])

    def test_norm_exclusion_rechecked_with_positive_margin(self):
        model,req,p=fixture(nominal=0.)
        c=req.constraints[0].model_copy(update=dict(indices=[1],reference=[[2.]]))
        req=req.model_copy(update=dict(constraints=[c]))
        out=trajectory_feasibility(model,req,p)
        self.assertEqual(out['status'],'model_infeasibility_certificate')
        cert=out['certificate']; v=np.array(cert['direction']); H=np.array(cert['matrix'])
        coeff=H.T@v
        bound=float(v@(np.array(cert['base'])-cert['reference'])+sum(np.minimum(coeff*cert['delta_lower'],coeff*cert['delta_upper'])))
        self.assertAlmostEqual(bound,cert['lower_bound']); self.assertGreater(cert['margin'],.9)
        self.assertEqual((cert['constraint_id'],cert['sample_index']),('moving',1))

    def test_joint_conflict_without_individual_certificate_is_inconclusive(self):
        model,req,p=fixture(nominal=0.)
        c=req.constraints[0].model_copy(update=dict(indices=[1],reference=[[.2]],radius=.01))
        d=c.model_copy(update=dict(constraint_id='conflict',reference=[[.8]]))
        req=req.model_copy(update=dict(constraints=[c,d]))
        out=trajectory_feasibility(model,req,p)
        self.assertEqual(out['status'],'inconclusive'); self.assertIsNone(out['certificate'])
        self.assertIsNotNone(out['replay']['worst_violation'])
        with patch('extensions.math_analysis.trajectory.minimize',return_value=NS(x=np.zeros(3),success=False,status=9,message='fixture stop',nit=1)):
            out=trajectory_feasibility(model,req.model_copy(update=dict(constraints=[c])),p)
        self.assertEqual(out['status'],'inconclusive')

    def test_component_intervals_and_box_exclusion(self):
        model,req,p=fixture(nominal=0.)
        c=req.constraints[0].model_copy(update=dict(kind='component_interval',radius=None,lower=[-.02],upper=[.02]))
        req=req.model_copy(update=dict(constraints=[c]))
        self.assertEqual(trajectory_feasibility(model,req,p)['status'],'feasible_witness')
        c=c.model_copy(update=dict(indices=[1],reference=[[3.]]))
        out=trajectory_feasibility(model,req.model_copy(update=dict(constraints=[c])),p)
        self.assertEqual(out['certificate']['kind'],'component_box_range')
        self.assertGreater(out['certificate']['margin'],1.9)

    def test_remaining_time_zero_horizon_aligned_different_grid_and_partial(self):
        model,req,p=fixture(start=2.)
        out=trajectory_feasibility(model,req,p)
        self.assertEqual(out['horizon']['step_count'],1)
        self.assertEqual(out['coverage'][0]['analyzed_indices'],[2,3])
        self.assertEqual(out['coverage'][0]['unchecked_indices'],[0,1])
        self.assertFalse(out['full_requested_coverage'])
        model.operating_point['actual_time_s']=3.
        out=trajectory_feasibility(model,req,p)
        self.assertEqual(out['horizon']['step_count'],0)
        self.assertEqual(out['status'],'model_infeasibility_certificate')
        model,req,p=fixture(duration=4.,sample=2.)
        self.assertEqual(trajectory_feasibility(model,req,p)['status'],'feasible_witness')
        p.period_s=.7
        self.assertEqual(trajectory_feasibility(model,req,p)['status'],'not_applicable')

    def test_feedthrough_previous_input_and_preceding_hold(self):
        model,req,p=fixture(nominal=.4,feedthrough=2.)
        model.operating_point['previous_applied_input_n']=[.7]
        req=req.model_copy(update=dict(constraints=[req.constraints[0].model_copy(update=dict(indices=[0],reference=[[.6]]))]))
        out=trajectory_feasibility(model,req,p)
        self.assertEqual(out['status'],'feasible_witness')
        self.assertAlmostEqual(out['replay']['records'][0]['output'][0],.6)
        del model.operating_point['previous_applied_input_n']
        self.assertEqual(trajectory_feasibility(model,req,p)['status'],'not_applicable')

    def test_variable_dimensions_and_unsupported_nonfinite(self):
        for nu in (1,5,7):
            model,req,p=fixture(nu=nu)
            self.assertEqual(trajectory_feasibility(model,req,p)['status'],'feasible_witness')
        model,req,p=fixture()
        model.u0=[float('nan')]
        self.assertEqual(trajectory_feasibility(model,req,p)['status'],'not_applicable')
        model,req,p=fixture()
        req=req.model_copy(update=dict(constraints=[req.constraints[0].model_copy(update=dict(signal=req.constraints[0].signal.model_copy(update=dict(frame='robot_base'))))]))
        self.assertEqual(trajectory_feasibility(model,req,p)['status'],'not_applicable')


if __name__ == '__main__': unittest.main()
