"""Focused A4 contracts. Fabricated arrays here are test fixtures, not evidence."""
from types import SimpleNamespace
import unittest
import numpy as np
from copy import deepcopy
from tools.research.nonlinear_capability import task_sensitivities,compare_scales,validate_prediction,control_prediction_validation
from tools.research.contracts import NonlinearResponseDirection
from tools.platform_store import plain

from extensions.tendon_family.mujoco_analysis import NativeModel


class NativeTaskSensitivityTests(unittest.TestCase):
    def response_fixture(self,h=1.):
        def sample(x):
            return [dict(constraint_id='speed',sample_index=2,time_s=.2,units='m/s',limit=.02,
                value=.02*(2+3*x+.1*x*x),normalized_signed_excess=1+3*x+.1*x*x)]
        def row(x):
            return dict(value=x,reference=dict(artifact_id=str(x),media_type='application/json'),
                parameter_values={'modulus':5.},task_samples={k:sample(x) for k in ('fixed_control','reoptimized_control')})
        return dict(rows=[row(0),row(-h),row(h)],validation_rows=[row(.75)],parameter=dict(units='Pa'),
            parameters=dict(modulus=dict(minimum=0.,maximum=10.)),coefficients=dict(modulus=1.))

    def test_held_out_quadratic_prediction_units_and_optimization_scope(self):
        result=task_sensitivities(self.response_fixture())
        fixed=result['fixed_control'];check=fixed['validation'][0]
        self.assertAlmostEqual(fixed['finite_difference_per_unit'][0],3.)
        self.assertAlmostEqual(fixed['dimensionless_sensitivity'][0],30.)
        self.assertAlmostEqual(check['maximum_error_over_threshold'],.05625)
        self.assertAlmostEqual(check['samples'][0]['error'],-.001125)
        self.assertEqual(result['reoptimized_control']['status'],'unresolved')
        directions=[]
        for h in (1.,.5):
            directions.append(dict(direction_id=str(h),coefficients=dict(modulus=1.),step=h,
                task_sensitivity=task_sensitivities(self.response_fixture(h))))
        compare_scales(directions)
        self.assertEqual(directions[0]['task_sensitivity']['fixed_control']['status'],'validated_local_prediction')
        self.assertAlmostEqual(directions[0]['task_sensitivity']['fixed_control']['scale_comparisons'][0]['relative_difference'],0.)

    def test_active_switch_and_error_as_large_as_benefit_stay_unresolved(self):
        context=self.response_fixture()
        for row in context['rows']:
            for samples in row['task_samples'].values():
                samples.append(dict(samples[0],sample_index=3,normalized_signed_excess=1-3*row['value']))
        result=task_sensitivities(context)['fixed_control']
        self.assertEqual(result['status'],'unresolved')
        self.assertIn('signed_J',result['active_switches'])
        base=self.response_fixture()['rows'][0]['task_samples']['fixed_control']
        actual=[dict(base[0],normalized_signed_excess=1.01)]
        self.assertEqual(validate_prediction(base,[1.],.5,actual)['status'],'unresolved')

    def test_validation_requires_distinct_results_and_preserves_old_v2_request(self):
        refs=[dict(artifact_id=c*64,media_type='application/json') for c in 'abcd']
        value=dict(direction_id='E',variables={'E':1.},coordinates=[0.,-1.,1.],coordinate_unit='Pa',t1_results=refs[:3])
        self.assertNotIn('validation_coordinates',plain(NonlinearResponseDirection(**value)))
        for coordinate,reference in [(1.,refs[3]),(.75,refs[0])]:
            with self.assertRaises(ValueError):
                NonlinearResponseDirection(**value,validation_coordinates=[coordinate],validation_t1_results=[reference])

    def test_control_holdout_is_independent_and_clipped_probe_is_unresolved(self):
        samples=self.response_fixture()['rows'][0]['task_samples']['fixed_control']
        def row(h):
            return dict(reference=dict(artifact_id=str(h)),control_response=dict(responses=[dict(
                coefficient_index=0,delta_n=h,samples=samples,finite_difference_per_n=[3+.1*h],
                projected=False,active_baseline={'worst':['speed',2]},active_probe={'worst':['speed',2]})]))
        rows=[row(.01),row(.005),row(.0075)]
        result=control_prediction_validation(rows)
        self.assertEqual(result['status'],'validated_local_prediction')
        self.assertAlmostEqual(result['validation']['maximum_error_over_threshold'],.000001875)
        rows[-1]['control_response']['responses'][0]['projected']=True
        self.assertEqual(control_prediction_validation(rows)['status'],'unresolved')
        rows[-1]=row(.005)
        self.assertEqual(control_prediction_validation(rows)['status'],'unresolved')

    def test_contact_failure_retains_geometry_time_and_actual_cost(self):
        native=object.__new__(NativeModel)
        native.cost=dict(model_builds=1,physics_steps=17)
        native.model=SimpleNamespace(geom=lambda i:SimpleNamespace(name=['arm','guide'][i]))
        data=SimpleNamespace(ncon=1,nefc=4,time=.0085,warning=[],qacc=np.array([0.]),
            contact=[SimpleNamespace(geom1=0,geom2=1,dist=-.001)])
        with self.assertRaisesRegex(ValueError,'CONTACT_FREE') as caught:
            native.check_supported(data,.008)
        diagnostic=caught.exception.native_diagnostic
        self.assertEqual(diagnostic['cost']['physics_steps'],17)
        self.assertEqual(diagnostic['evaluation_interval_s'],[.008,.0085])
        self.assertEqual(diagnostic['contacts'][0]['geom2'],'guide')


if __name__=='__main__':unittest.main()
