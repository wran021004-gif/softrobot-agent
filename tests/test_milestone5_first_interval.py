"""Focused saved-state identity, vector resolution, accounting and native receipt checks."""
from copy import deepcopy
import unittest
from unittest.mock import patch
import numpy as np
from examples import milestone5_first_interval as stage
from examples import milestone5_preparation as preparation
from extensions.tendon_family.milestone5_first_interval import stable,output_accounting


class FirstIntervalTests(unittest.TestCase):
    def test_shared_original_state_input_and_time(self):
        spec=stage.read(stage.RUN/'specification.json')
        self.assertEqual(len({c['shared_identity'] for c in spec['cases']}),1)
        self.assertEqual([c['holding_weight'] for c in spec['cases']],[.075,.15])
        self.assertEqual(spec['state'],[0.]*24);self.assertEqual(spec['interval_s'],[0.,.01]);self.assertEqual(spec['time_origin_s'],0.)
        for binding,case in zip(stage.read(stage.RUN/'freeze.json')['bindings'],spec['cases']):
            reader=stage.BoundReader(stage.Store(stage.RUN),binding);source=reader.resolve(case['execution_id'])
            o=reader.read_file(source,'controller_observations.json')[0];end=reader.read_file(source,'trajectory.json.gz')[0]
            self.assertEqual(o['measured_initial_state'],spec['state']);self.assertEqual(o['actual_tension_n'],spec['input_n'])
            self.assertEqual(end['tension_n'],spec['input_n']);self.assertEqual(o['time_s'],0.);self.assertAlmostEqual(end['time_s'],.01)
            self.assertEqual(end['tip_m'],spec['observed']['position_m'])
        self.assertLess(max(abs(x) for x in spec['full_initial_backend_state']['qvel']),1e-12)

    def test_vector_resolution_and_accounting(self):
        # Equal speed norms with rotating vectors must not certify stability.
        fake=[dict(step_s=h,position_m=[0.,0.,0.],velocity_m_s=v,speed_m_s=1.) for h,v in zip((.0005,.00025,.000125),([1.,0.,0.],[0.,1.,0.],[-1.,0.,0.]))]
        self.assertFalse(stable(fake))
        report=stage.read(stage.RUN/'calculation.json');spec=stage.read(stage.RUN/'specification.json')
        self.assertEqual(report['numerical_stability_supported'],stable(report['results']))
        self.assertLess(report['coarse_reproduction']['state_max'],1e-7)
        for result,saved in zip(report['results'],report['endpoint_accounting']):
            self.assertLessEqual(result['step_count'],320);self.assertLessEqual(result['max_scaled_residual'],1e-5)
            expected=output_accounting(result,report['observed_projected_output'],spec['observed']);self.assertEqual(expected,saved['accounting'])
            for term in expected.values():self.assertLess(term['identity_residual'],1e-12)
        a,b=report['results'][0],report['results'][-1]
        self.assertAlmostEqual(report['vector_error_change']['absolute_reduction_m_s'],a['velocity_error_norm_m_s']-b['velocity_error_norm_m_s'])

    def test_receipt_reuse_and_accepted_research_binding(self):
        store=stage.Store(stage.RUN);before=store.remaining()
        with patch.object(stage.Host,'invoke',side_effect=AssertionError('No repeated integration permitted')):result=stage.calculate()
        self.assertEqual(before,store.remaining());self.assertTrue(result['shared_with'])
        refs=store.session(stage.host('research').run_id)['state']['handoffs'];selection=stage.read(stage.RUN/'selection_response.json')
        p=preparation.protocol(stage.read(preparation.RUN/'registration.json'),selection,stage.read(preparation.RUN/'reference.json'),research_store=store,
            decision_refs={phase:refs['m5_'+phase] for phase in ('selection','interpretation')})
        self.assertTrue(p['research_pair_selected']);self.assertTrue(p['research_interpretation_complete']);self.assertFalse(p['ready_for_bounded_prospective_experiment'])
        stage.check_previous()


if __name__=='__main__':unittest.main()
