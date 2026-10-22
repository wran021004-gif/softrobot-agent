"""Synthetic parametric analytic fixtures; not GVS scientific design evidence."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
import numpy as np

from tests.research.test_conic_capability import terminal
from extensions.math_analysis.capability_sensitivity import capability_sensitivity
from extensions.math_analysis.conic_capability import conic_capability


PARAMETER = dict(path='segments.test.length_m', units='m', source='synthetic test fixture')


def point(d, mode='smooth'):
    m, r, p = terminal(target=2., radius=1.)
    m.binding.update(coordinate_order=['test.q'], tendon_order=['test.tendon'])
    m.state_definition=[dict(name='q', units='m')]; m.input_definition=[dict(name='tension', units='N')]
    m.operating_point.update(name='synthetic_initial', phase='post_step')
    initial = None
    if mode == 'smooth': m.endpoint_outputs[0].value0=[-d]
    elif mode == 'curved': m.endpoint_outputs[0].value0=[-d**3]
    elif mode == 'nominal':
        m.u0=[.2+d]; m.endpoint_outputs[0].value0=[.2+d]
    elif mode == 'initial':
        m.u0=[.2+d]; m.endpoint_outputs[0].value0=[.2+d]; initial=[d]
    elif mode == 'box':
        m.binding['tension_limits_n']=[1+d]
        r=r.model_copy(update=dict(physical_inputs=dict(lower=[0.], upper=[1+d])))
    elif mode in ('tradeoff', 'switch'):
        second=deepcopy(m.endpoint_outputs[0]); second.name='second'; m.endpoint_outputs.append(second)
        c=r.constraints[0].model_copy(update=dict(reference=[[0.]], radius=1.))
        other=c.model_copy(update=dict(constraint_id='second', signal=c.signal.model_copy(update=dict(name='second')),
                                       reference=[[1.]], radius=2.))
        if mode=='tradeoff': second.value0=[-d]
        else:
            m.B=[[0.]]; m.endpoint_outputs[0].value0=[2+d]; second.value0=[2-d]
            other=other.model_copy(update=dict(reference=[[0.]], radius=1.))
        r=r.model_copy(update=dict(constraints=[c, other]))
    elif mode == 'interval':
        m.endpoint_outputs[0].value0=[-d]
        c=r.constraints[0].model_copy(update=dict(kind='component_interval', radius=None, lower=[-.5], upper=[.5]))
        r=r.model_copy(update=dict(constraints=[c]))
    elif mode == 'duplicate':
        m.endpoint_outputs[0].value0=[-d]
        r=r.model_copy(update=dict(constraints=r.constraints+[r.constraints[0].model_copy(update=dict(constraint_id='duplicate'))]))
    return dict(value=d, parameters=dict(segments=dict(test=dict(length_m=d, young_pa=1.))),
        model=m, requirements=r, initial_delta=initial,
        source_reference=dict(fixture=True, value=d, mode=mode),
        context=dict(source_identity='synthetic-v1', topology_identity='one-state-one-tendon',
                     fixed_configuration_identity=mode, construction_rule='synthetic analytic model')), p


def group(mode='smooth', origin=.2, steps=(.02,.01)):
    data=[point(d,mode) for d in (origin, *[origin+s*h for h in steps for s in (-1,1)])]
    return [d[0] for d in data], data[0][1]


class SensitivityTests(unittest.TestCase):
    def analyze(self, mode='smooth', parameter=None, **kw):
        points, protocol=group(mode)
        out=capability_sensitivity(points, parameter or PARAMETER, protocol, **kw)
        self.assertEqual(out['status'], 'computed_diagnostic', out)
        json.dumps(out, allow_nan=False)
        return out

    def test_analytic_smooth_value_and_envelope(self):
        out=self.analyze()
        self.assertEqual(out['direction_status'], 'numerically_stable_local_direction', out)
        self.assertEqual(out['preferred_parameter_direction'], 'decrease')
        self.assertFalse(out['regularity']['differentiability_proven'])
        for row in out['reoptimized_finite_difference']:
            self.assertAlmostEqual(row['reoptimized'], 1., places=6)
            self.assertAlmostEqual(row['envelope'], 1., places=6)
            self.assertLess(row['dual_face']['range'][1]-row['dual_face']['range'][0], .001)

    def test_fixed_control_and_reoptimized_are_different(self):
        out=self.analyze('tradeoff')
        for row in out['reoptimized_finite_difference']:
            self.assertAlmostEqual(row['reoptimized'], 1/3, places=6)
            self.assertAlmostEqual(row['envelope'], 1/3, places=6)
            self.assertAlmostEqual(row['fixed_control'], .25, places=5)
            self.assertAlmostEqual(row['left_fixed_control'], 0., places=5)
            self.assertAlmostEqual(row['right_fixed_control'], .5, places=5)

    def test_nominal_changes_preserve_absolute_input(self):
        out=self.analyze('nominal')
        for row in out['reoptimized_finite_difference']:
            self.assertAlmostEqual(row['fixed_control'], 0., places=7)
            self.assertAlmostEqual(row['envelope'], 0., places=7)
            self.assertAlmostEqual(row['reoptimized'], 0., places=7)
        self.assertEqual(out['direction_status'], 'numerically_flat_at_resolution')

    def test_initial_projection_dependence_is_included(self):
        out=self.analyze('initial')
        for row in out['reoptimized_finite_difference']:
            self.assertAlmostEqual(row['envelope'], -1., places=6)
            self.assertAlmostEqual(row['reoptimized'], -1., places=6)

    def test_moving_box_has_full_lagrangian_term(self):
        parameter=dict(PARAMETER, input_bounds_treatment='parameter_dependent', input_bounds_source='synthetic upper=1+d')
        out=self.analyze('box', parameter)
        for row in out['reoptimized_finite_difference']:
            self.assertAlmostEqual(row['envelope'], -1., places=6)
            self.assertAlmostEqual(row['box_contribution'], -1., places=6)
            self.assertAlmostEqual(row['reoptimized'], -1., places=6)
            self.assertFalse(row['fixed_control_legal'])

    def test_duplicate_nonunique_multipliers_same_aggregate(self):
        out=self.analyze('duplicate')
        self.assertEqual(out['regularity']['duplicate_groups_across_stencil'], [[0,1]])
        for row in out['reoptimized_finite_difference']:
            group=row['duplicate_aggregates'][0]
            a,b=group['alternative_allocations']
            self.assertNotEqual(a['receiver_atom'], b['receiver_atom'])
            self.assertAlmostEqual(a['contribution'], b['contribution'], places=9)
            self.assertLess(a['stationarity_change_inf'], 1e-10)
            self.assertLess(a['cone_violation'], 1e-8)
            self.assertAlmostEqual(group['contribution'], 1., places=6)
        self.assertEqual(out['direction_status'], 'numerically_stable_local_direction')

    def test_switch_is_not_a_zero_gradient(self):
        points,p=group('switch', origin=0.)
        out=capability_sensitivity(points, PARAMETER, p)
        self.assertEqual(out['direction_status'], 'directional_comparisons_only')
        self.assertTrue(out['regularity']['active_set_changed'])
        for row in out['reoptimized_finite_difference']:
            self.assertAlmostEqual(row['left_reoptimized'], -1., places=6)
            self.assertAlmostEqual(row['right_reoptimized'], 1., places=6)
            self.assertLess(row['dual_face']['range'][0], -.99)
            self.assertGreater(row['dual_face']['range'][1], .99)

    def test_component_intervals_and_moving_reference(self):
        points,p=group('interval')
        for q in points:
            c=q['requirements'].constraints[0]
            q['requirements']=q['requirements'].model_copy(update=dict(constraints=[c.model_copy(update=dict(
                indices=[0,1], reference=[[0.], [2.]]))]))
        out=capability_sensitivity(points, PARAMETER, p)
        for row in out['reoptimized_finite_difference']:
            self.assertAlmostEqual(row['envelope'], 2., places=5)
            self.assertAlmostEqual(row['reoptimized'], 2., places=5)

    def test_bad_comparisons_are_rejected_before_solving(self):
        for mode in ('parameters','task','topology','channels','coverage','bound','source','rule'):
            points,p=group()
            q=points[-1]
            if mode=='parameters': q['parameters']['segments']['test']['young_pa']=2.
            elif mode=='task':
                c=q['requirements'].constraints[0].model_copy(update=dict(radius=2.))
                q['requirements']=q['requirements'].model_copy(update=dict(constraints=[c]))
            elif mode=='topology': q['context']['topology_identity']='different'
            elif mode=='channels': q['model'].binding['tendon_order']=['different']
            elif mode=='coverage': q['model'].endpoint_outputs[0].units='mm'
            elif mode=='bound': q['model'].binding['tension_limits_n']=[2.]
            elif mode=='source': q['source_reference']=None
            else: q['context']['construction_rule']='different'
            with patch('extensions.math_analysis.capability_sensitivity.conic_capability') as solve:
                out=capability_sensitivity(points, PARAMETER, p)
                self.assertEqual(out['status'],'not_applicable', (mode,out)); solve.assert_not_called()

    def test_gap_or_convergence_unknown_withholds_sensitivity(self):
        points,p=group()
        def unknown(*a,**kw):
            result=conic_capability(*a,**kw); result['optimality_status']='unknown'; return result
        with patch('extensions.math_analysis.capability_sensitivity.conic_capability', side_effect=unknown):
            out=capability_sensitivity(points, PARAMETER, p)
        self.assertEqual(out['reason'], 'NUMERICAL_OPTIMALITY_INSUFFICIENT')
        self.assertNotIn('envelope_sensitivity',out)

    def test_gap_resolution_and_steps_can_prevent_direction(self):
        out=self.analyze(slope_atol=1e-13, slope_rtol=1e-12)
        self.assertEqual(out['direction_status'],'directional_comparisons_only')
        points,p=group()
        out=capability_sensitivity(points[:2],PARAMETER,p)
        self.assertEqual(out['direction_status'],'directional_comparisons_only')
        self.assertEqual(out['reoptimized_finite_difference'][0]['kind'],'one_sided_secant')

    def test_finite_steps_with_curvature_do_not_establish_local_gradient(self):
        points,p=group('curved',steps=(.1,.05))
        out=capability_sensitivity(points,PARAMETER,p)
        self.assertEqual(out['direction_status'],'directional_comparisons_only')
        self.assertAlmostEqual(out['reoptimized_finite_difference'][0]['reoptimized'],.13,places=6)
        self.assertAlmostEqual(out['reoptimized_finite_difference'][1]['reoptimized'],.1225,places=6)

    def test_dual_face_failure_retains_only_supported_fd_direction(self):
        points,p=group()
        with patch('extensions.math_analysis.capability_sensitivity._dual_face', return_value=dict(
                status='unresolved',range=None,extrema=[],solve_count=2,wall_s=0.)):
            out=capability_sensitivity(points,PARAMETER,p)
        self.assertEqual(out['direction_status'],'stable_reoptimized_direction_envelope_unresolved')
        self.assertEqual(out['preferred_parameter_direction'],'decrease')
        self.assertEqual(out['envelope_sensitivity']['multiplier_robustness'],'unresolved')
        self.assertFalse(out['regularity']['step_and_envelope_checks_passed'])

    def test_inverted_float_bound_estimates_do_not_pass_resolution_gate(self):
        points,p=group()
        def inverted(*a,**kw):
            result=conic_capability(*a,**kw)
            result['dual_checks']['support_lower_estimate']=result['replayed_violation']+1e-8
            return result
        with patch('extensions.math_analysis.capability_sensitivity.conic_capability',side_effect=inverted):
            out=capability_sensitivity(points,PARAMETER,p)
        self.assertFalse(out['regularity']['finite_difference_checks_passed'])
        self.assertEqual(out['direction_status'],'directional_comparisons_only')

    def test_authoritative_normalization_and_one_sided(self):
        points,p=group()
        points=[q for q in points if q['value'] >= .2]
        parameter=dict(PARAMETER,bounds=[.2,.4],bounds_source='synthetic declared range')
        out=capability_sensitivity(points,parameter,p)
        self.assertEqual(out['direction_status'],'one_sided_numerical_direction')
        self.assertAlmostEqual(out['reoptimized_finite_difference'][0]['normalized_envelope'],.2,places=6)
        parameter.pop('bounds_source')
        self.assertEqual(capability_sensitivity(points,parameter,p)['status'],'not_applicable')


if __name__ == '__main__':
    unittest.main()
