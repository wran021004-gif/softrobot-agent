"""Analytic timed/free-progress SOCP and T2 fixtures; no robot or Provider."""
from copy import deepcopy
from types import SimpleNamespace as NS
import unittest
import numpy as np
from schemas.platform_analysis import TaskAnalysisRequirement
from extensions.math_analysis.conic_capability import conic_capability,PATH_METHOD
from extensions.math_analysis.capability_sensitivity import capability_sensitivity
from extensions.math_analysis.trajectory import prepare_conic_trajectory,verify_witness

PARAMETER=dict(path='model.gain_m_per_n_s',units='m/(N*s)',source='Analytic synthetic gain fixture, not a robot design law')


def problem(gain=1.,bend=False,timed=False):
    n=2 if bend else 1
    C=[[1.,0.],[0.,1.],[0.,0.]] if bend else [[1.],[0.],[0.]]
    m=NS(A=np.zeros((n,n)).tolist(),B=(gain*np.eye(n)).tolist(),drift=[0.]*n,u0=[0.]*n,
        time_domain='continuous',binding=dict(tension_limits_n=[1.]*n,coordinate_order=['q'+str(i) for i in range(n)],
            tendon_order=['tendon'+str(i) for i in range(n)],task_identity='synthetic_tracking',source_identity='synthetic'),
        endpoint_outputs=[NS(name='tip_position',units='m',frame='world',value0=[0.,0.,0.],C=C,D=np.zeros((3,n)).tolist())],
        input_scales=[1.]*n,state_definition=[dict(name='position',units='m',dimension=n)],
        input_definition=[dict(name='tendon_tension',units='N',dimension=n)],
        operating_point=dict(actual_time_s=0.,remaining_task_s=1.,previous_applied_input_n=[0.]*n,name='synthetic_initial',phase='fixture'))
    p=NS(period_s=.25,horizon_alignment_atol_s=1e-12,endpoint_check_atol=1e-8)
    signal=dict(name='tip_position',entity='tip',dimension=3,units='m',frame='world',phase='post_step')
    c=dict(constraint_id='tracking',signal=signal,indices=[0,1,2,3,4],radius=.1,provenance=['synthetic'])
    if timed:c.update(kind='norm_bound',reference=[[x,0.,0.] for x in (0.,.7,.8,.9,1.)])
    else:c.update(kind='path_bound',reference=[],path_vertices_m=[[0.,0.,0.],[.5,0.,0.],[.5,.5,0.]] if bend else [[0.,0.,0.],[1.,0.,0.]])
    r=TaskAnalysisRequirement(binding=dict(task_identity='synthetic_tracking',task_family='task.tracking'),
        duration_s=1.,sample_period_s=.25,time_grid_s=[0.,.25,.5,.75,1.],constraints=[c],
        physical_inputs=dict(lower=[0.]*n,upper=[1.]*n,tendon_order=m.binding['tendon_order']))
    return m,r,p


def stencil(bend=False,origin=.5,timed=False):
    points=[]
    for d in (origin,origin-.02,origin+.02,origin-.01,origin+.01):
        m,r,p=problem(d,bend,timed)
        points.append(dict(value=d,parameters=dict(model=dict(gain_m_per_n_s=d)),model=m,requirements=r,
            initial_delta=None,source_reference=dict(fixture=True,value=d),
            context=dict(source_identity='synthetic',topology_identity='fixed',fixed_configuration_identity='fixed',construction_rule='analytic gain fixture')))
    return points,p


class TrackingMathTests(unittest.TestCase):
    def test_free_progress_and_timed_reference_are_different_problems(self):
        m,r,p=problem();free=conic_capability(m,r,p)
        timed=conic_capability(*problem(timed=True))
        self.assertEqual(free['method_version'],PATH_METHOD)
        self.assertEqual(free['optimality_status'],'numerically_checked')
        self.assertEqual(free['status'],'feasible_witness')
        self.assertAlmostEqual(free['replayed_violation'],-1.,places=6)
        self.assertGreater(timed['replayed_violation'],3.)
        self.assertEqual(np.asarray(free['applied_input_n']).shape,(4,1))
        self.assertEqual(len(free['path_progress']),5)
        self.assertTrue(np.all(np.diff(free['path_progress'])>=-1e-8))
        self.assertAlmostEqual(free['path_progress'][0],0.)
        self.assertAlmostEqual(free['path_progress'][-1],1.)
        self.assertIn('not infeasibility',free['untimed_scope'])

    def test_bend_enumerates_corner_instead_of_assigning_a_time(self):
        out=conic_capability(*problem(bend=True))
        self.assertEqual(out['status'],'feasible_witness',out)
        self.assertEqual(out['optimality_status'],'numerically_checked')
        self.assertEqual(out['path_assignment'],2)
        self.assertEqual(out['internal_conic_solves'],3)
        self.assertEqual([r['corner_sample'] for r in out['path_assignment_comparison']],[1,2,3])
        self.assertEqual(np.asarray(out['applied_input_n']).shape,(4,2))
        self.assertAlmostEqual(out['path_progress'][2],.5,places=7)

    def test_bend_is_not_weakened_to_convex_hull_or_endpoint_reach(self):
        m,r,p=problem(bend=True)
        # This model can move only on the diagonal: it reaches the endpoint but misses the bend.
        m.B=[[1.,0.],[1.,0.]]
        out=conic_capability(m,r,p)
        self.assertGreater(out['replayed_violation'],1.)
        self.assertNotEqual(out['status'],'feasible_witness')

    def test_progress_replayed_independently_and_partial_horizon_rejected(self):
        m,r,p=problem();out=conic_capability(m,r,p);info=dict(coverage=[])
        scope,dynamics,initial,rows,*_=prepare_conic_trajectory(m,r,p,info)
        bad=[0.,.8,.2,.9,1.]
        replay=verify_witness(m,dynamics,initial,np.asarray(out['delta_input_n']),rows,scope,1e-8,bad)
        self.assertFalse(replay['path_progress_valid']);self.assertFalse(replay['passed'])
        m.operating_point['actual_time_s']=.25
        m.operating_point['remaining_task_s']=.75
        rejected=conic_capability(m,r,p)
        self.assertEqual(rejected['status'],'not_applicable')
        self.assertIn('COMPLETE_DECLARED_INITIAL_HORIZON',rejected['reason'])

    def test_t2_reoptimizes_progress_and_matches_analytic_gain_slope(self):
        points,p=stencil();out=capability_sensitivity(points,PARAMETER,p)
        self.assertEqual(out['status'],'computed_diagnostic',out)
        self.assertEqual(out['method_version'],'controlled-path-progress-sensitivity-v1')
        self.assertEqual(out['computation_cost']['conic_solves'],5)
        self.assertIn(out['direction_status'],('numerically_stable_local_direction','stable_reoptimized_direction_envelope_unresolved'))
        self.assertEqual(out['preferred_parameter_direction'],'increase')
        self.assertEqual(len(out['fixed_control_sensitivity']['baseline_absolute_input_n']),4)
        self.assertEqual(len(out['fixed_control_sensitivity']['baseline_path_progress']),5)
        for row in out['reoptimized_finite_difference']:
            self.assertAlmostEqual(row['reoptimized'],-10.,places=5)
            self.assertAlmostEqual(row['envelope'],-10.,places=5)
            if row['dual_face']['status']!='numerically_checked':
                self.assertEqual(out['direction_status'],'stable_reoptimized_direction_envelope_unresolved')
        self.assertFalse(out['regularity']['differentiability_proven'])

    def test_t2_keeps_timed_reference_support(self):
        points,p=stencil(timed=True);out=capability_sensitivity(points,PARAMETER,p)
        self.assertEqual(out['status'],'computed_diagnostic',out)
        self.assertEqual(out['method_version'],'controlled-capability-sensitivity-v1')
        self.assertNotIn('baseline_path_progress',out['fixed_control_sensitivity'])
        for row in out['reoptimized_finite_difference']:self.assertAlmostEqual(row['reoptimized'],-2.5,places=5)

    def test_t2_corner_ties_withhold_single_derivative_claim(self):
        points,p=stencil(bend=True,origin=2.);out=capability_sensitivity(points,PARAMETER,p)
        self.assertEqual(out['status'],'computed_diagnostic',out)
        self.assertTrue(out['regularity']['path_assignment_ambiguous'])
        self.assertEqual(out['direction_status'],'directional_comparisons_only')
        self.assertEqual(out['preferred_parameter_direction'],'unresolved')
        self.assertEqual(out['computation_cost']['conic_solves'],15)


if __name__=='__main__':unittest.main()
