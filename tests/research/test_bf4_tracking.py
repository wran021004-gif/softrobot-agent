"""BF4 contract/search fixtures only: no integration, providers or scientific search."""
from copy import deepcopy
import unittest
from unittest.mock import patch

import numpy as np

from schemas.platform import SessionInput
from tools.platform_store import plain
from tools.platform_tasks import compile_input
from tools.research.config import ROOT, resolve
from tools.research.contracts import AnalysisRequest
from tools.research.control_correction import constraint_vectors, task_measure
from tools.research.feedback import task_gap
from tools.research.local_control_search import search
from tools.research.native_analysis import assessment, applicability
from tools.research.physical_replay import evaluate_playback
from tools.research_tasks import task_adapter, assemble_acceptance, _outcome_issue, _source_issue
from tools.state_io import digest, read


RAW = dict(artifact_id='a'*64, media_type='application/json')
EVALUATION = dict(artifact_id='b'*64, media_type='application/json')
PROFILE = dict(artifact_id='c'*64, media_type='application/json')


class BF4TrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = resolve(ROOT/'configs/research/study_bf4_tracking_preparation.json')
        cls.freeze = read(ROOT/'configs/research/bf4_tracking_freeze_v1.json')

    def setUp(self):
        self.cfg = deepcopy(self.spec['configuration'])
        self.adapter = task_adapter(self.cfg)
        self.times = np.arange(31)*.02
        self.reference = self.adapter.reference_at(self.times)[0]
        self.options = self.adapter.control_search_options()

    def raw(self, positions=None):
        positions = self.reference if positions is None else positions
        return dict(status='completed', physics_steps=600, tendon_order=[
            t['id'] for t in self.cfg['robot']['structure']['data']['tendons']],
            fixture='Fabricated contract record; no physical execution',
            samples=[dict(time_s=float(t), tip_m=list(p), speed_m_s=0., actual_tension_n=[.2]*6)
                for t,p in zip(self.times,positions)])

    def accept(self, raw):
        ev,profile = evaluate_playback(self.cfg, raw, RAW, 'bf4-synthetic')
        profile.update(execution_id='synthetic-execution', evaluation=EVALUATION, simulation=RAW)
        result = assemble_acceptance(self.cfg, ev, profile,
            evaluation_reference=EVALUATION, profile_reference=PROFILE, motion=raw['samples'])
        return ev, profile, result

    def test_compile_freeze_grid_and_nonconstant_requirement(self):
        self.assertTrue(compile_input(self.cfg)['approval']['capabilities_ready'])
        self.assertFalse(compile_input(self.cfg)['approval']['formally_approved'])
        self.assertEqual(self.freeze['canonical_task_identity'],self.spec['canonical_task_identity'])
        self.assertEqual(self.freeze['family_space_identity'],self.spec['family_space_identity'])
        self.assertEqual(self.freeze['task_file_identity'],digest(read(ROOT/self.freeze['task_file'])))
        self.assertEqual(self.spec['budgets']['physical_launches'],0)
        self.assertEqual(self.spec['budgets']['mathematical_evaluations'],0)
        req = self.adapter.analysis_requirements({})
        self.assertEqual(req.constraints[0].indices,list(range(1,31)))
        np.testing.assert_allclose(req.constraints[0].reference,self.reference[1:])
        self.assertEqual(self.adapter.execution_requirements()['protocol_id'],'offline_timed_tracking_v1')
        # Two scored references farther than twice the tolerance exclude all constants.
        self.assertGreater(np.linalg.norm(self.reference[15]-self.reference[-1]),2*.012)
        self.assertFalse(self.accept(self.raw(np.tile(self.reference[-1],(31,1))))[0].task_success)

    def test_all_prespecified_requests_are_legal_equal_channel_designs(self):
        from extensions.tendon_family.family_space import parse_build
        from extensions.tendon_family.generated_serial import generate_family
        for request in self.freeze['candidate_requests'].values():
            design,mesh,physics = generate_family(parse_build(dict(space=self.spec['family_space'],request=request)))
            self.assertEqual(len(design['tendons']),6)
            self.assertEqual(len(physics['dofs']),48)
            self.assertEqual(len(design['actuators']),6)
            self.assertEqual(request['control_weights'],dict(holding_tip_speed_weight=0.,terminal_tip_speed_weight=0.))

    def test_measure_matches_original_evaluator_and_rejects_time_shift(self):
        positions=self.reference.copy();positions[15]+=[0.,.015,0.]
        outputs=dict(times_s=self.times.tolist(),tip_positions_m=positions.tolist())
        measure=task_measure(outputs,**self.options)
        ev,_,accepted=self.accept(self.raw(positions))
        self.assertFalse(accepted['accepted'])
        self.assertAlmostEqual(measure['max_position_error_m'],next(m.value for m in ev.metrics if m.name=='max_position_error'))
        self.assertAlmostEqual(measure['normalized_gap'],.25)
        self.assertAlmostEqual(measure['worst_constraint']['time_s'],.3)
        self.assertEqual(constraint_vectors(outputs,**self.options).shape,(30,3))
        self.assertNotIn('holding_max_speed_m_s',measure)
        outputs['times_s'][15]+=.001
        with self.assertRaisesRegex(ValueError,'ALL_SCORED_TRACKING_SAMPLES_REQUIRED'):
            task_measure(outputs,**self.options)
        self.assertEqual(self.accept(self.raw())[2]['status'],'accepted')
        # The scored window is authoritative, and need not include the endpoint.
        changed=deepcopy(self.cfg);changed['task']['sampling']['window_s']=[.10,.30]
        narrow=task_adapter(changed).control_search_options()
        outputs=dict(times_s=self.times.tolist(),tip_positions_m=self.reference.tolist())
        outputs['tip_positions_m'][-1]=[99.,99.,99.]
        self.assertEqual(task_measure(outputs,**narrow)['normalized_gap'],0.)

    def test_complete_acceptance_sources_force_bounds_and_missing_conditions(self):
        ev,profile,result=self.accept(self.raw())
        self.assertIsNone(_outcome_issue(result));self.assertIsNone(_source_issue(result))
        self.assertEqual(set(result['components']),{
            'evaluation_validity','execution_complete','task_evaluator','solver_errors','force_bounds',
            'tracking_sampling','evaluator:tracking_max_error'})
        missing=ev.model_copy(update=dict(constraints=[]))
        self.assertEqual(assemble_acceptance(self.cfg,missing,profile)['status'],'missing_evidence')
        broken=deepcopy(result);broken['evidence_binding']['profile_binding']['execution_id']='other'
        self.assertIsNotNone(_source_issue(broken))
        over=self.raw();over['samples'][-1]['actual_tension_n'][0]=9.
        self.assertFalse(self.accept(over)[2]['components']['force_bounds']['passed'])
        shifted=self.raw();shifted['samples'][15]['time_s']+=.001
        self.assertEqual(self.accept(shifted)[2]['status'],'invalid')
        incomplete=self.raw();incomplete['samples'].pop()
        self.assertEqual(self.accept(incomplete)[2]['status'],'incomplete')
        gap=task_gap(dict(status='evaluated',acceptance=result))
        self.assertEqual(gap['normalized_gap'],0.);self.assertTrue(gap['valid_complete'])

    def test_existing_response_search_improves_timed_vectors_and_stops_at_pass(self):
        order=[t['id'] for t in self.cfg['robot']['structure']['data']['tendons']]
        start=dict(id='synthetic',limits=[8.]*6,task_options=self.options,
            schedule=dict(source_kind='explicit_control_schedule_v1',task_acceptance='unmeasured',provenance=dict(fixture=True),
                trajectory=dict(times_s=self.times.tolist(),tensions_n=[[.2]*6 for _ in range(30)],
                    tendon_order=order,task_identity='synthetic-task',model_identity='synthetic-model',design_identity='synthetic-design')))
        def evaluate(start,source,meta):
            u=np.asarray(source['trajectory']['tensions_n'])
            positions=self.reference.copy();positions[1:,1]+=(u[:,0]-.7)*.03
            _,_,acceptance=self.accept(self.raw(positions))
            return dict(reference='fixture-'+str(meta['label'])+str(meta['coefficients_n']),
                task_gap=task_gap(dict(status='evaluated',acceptance=acceptance)),cost_s=0.,
                outputs=dict(times_s=self.times.tolist(),tip_positions_m=positions.tolist()),cache_hit=False)
        settings=deepcopy(self.freeze['search_settings'])
        settings.update(evaluation_requests=6,iterations=1,active_coefficients=[0,6,12,18])
        result=search([start],evaluate,settings)
        self.assertEqual(result['stop_reason'],'first_original_task_pass')
        self.assertTrue(result['best']['task_gap']['accepted'])
        self.assertEqual(result['finite_difference_evaluations'],4)
        self.assertEqual(len(result['candidates']),6)
        self.assertEqual(result['candidates'][0]['task_gap']['components'].keys(),{'evaluator:tracking_max_error'})

    def test_native_coverage_is_timed_and_t1_remains_not_applicable(self):
        req=self.adapter.analysis_requirements({})
        query=AnalysisRequest(candidate=RAW,operation='mujoco_direct_control_v1',model_source='mujoco',
            operating_point='standardized_initial_pretension',protocol=self.spec['analysis_protocol'],
            control_optimization=dict(source=RAW,settings=self.freeze['search_settings']))
        inp=SessionInput.model_validate(self.cfg);assessed=assessment(inp,req)
        fit=applicability(req,query,assessed,dict(actual_time_s=0.))
        self.assertEqual(fit['status'],'applicable')
        self.assertEqual(fit['constraint_coverage'][0]['analyzed_indices'],list(range(1,31)))
        self.assertFalse(fit['full_task_supported'])
        t1=query.model_copy(update=dict(operation='mujoco_nonlinear_task_capability_v1'))
        from tools.research.analysis import calculate
        with patch('extensions.tendon_family.mujoco_analysis.NativeModel',side_effect=AssertionError('NO_BUILD')):
            result=calculate(self.cfg,{},t1,dict(actual_time_s=0.))
        self.assertEqual(result['status'],'not_applicable')
        self.assertEqual(result['task_acceptance'],'unmeasured')
        late=query.model_copy(update=dict(control_optimization=query.control_optimization.model_copy(update=dict(
            settings=query.control_optimization.settings.model_copy(update=dict(correction_window_s=(.2,.6)))))))
        self.assertTrue(any('All task' in reason for reason in applicability(req,late,assessed,dict(actual_time_s=.2))['reasons']))
        geometric=deepcopy(self.cfg);geometric['task']=read(ROOT/'tasks/tracking_linear_development.json')['task']
        with self.assertRaisesRegex(ValueError,'UNTIMED_CONTROL_SEARCH_UNSUPPORTED'):
            task_adapter(geometric).control_search_options()


if __name__=='__main__':
    unittest.main()
