"""Synthetic evidence and interface regressions; no Provider or physics workers."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.platform_store import plain
from tools.research.contracts import NativeStateSelection, LocalControlSearchSettings, ScientificControlEffort
from tools.research.local_control_search import search
from tools.research.numerics import native_point
from tools.research.evidence_views import bottleneck_diagnosis
from tools.research.scientific_intent import control_settings
from tools.state_io import digest
from tests.research import test_local_control_search as search_fixtures
start=search_fixtures.start
from tests.research.test_research_reporting import offline_host


def ref(letter):return dict(artifact_id=letter*64,media_type='application/json')


def evidence():
    candidate,result,source=ref('a'),ref('b'),ref('c')
    cfg=dict(task={'fixture':True},robot={},policy={})
    tr=dict(times_s=[0,.02,.04],tendon_order=['a','b'],tensions_n=[[.2,.2],[.2,.2]],
        task_identity='task',model_identity='model',design_identity='design')
    settings=plain(LocalControlSearchSettings(version='local_control_search_v2',correction_window_s=[0,.04],
        knots_s=[0,.04],evaluation_requests=2,iterations=1,method='pattern'))
    measure=dict(signed_maximum_excess=2.,sum_normalized_excess=3.,normalized_gap=2.,
        terminal_position_error_m=.03,holding_max_position_error_m=.03,holding_max_speed_m_s=.12,
        worst_constraint=dict(kind='holding_speed',time_s=.02,normalized_signed_excess=2.))
    row=dict(reference='native-rollout-0',start='native',measure=measure,coefficients_n=[0]*4,
        sequence_hash=digest(tr['tensions_n']),label='baseline',outputs=dict(times_s=tr['times_s'],
        tip_positions_m=[[0,0,0]]*3,tip_velocities_m_s=[[0,0,0],[.4,0,0],[.2,0,0]]))
    point=dict(candidate=candidate,configuration_identity=digest(cfg),physics_identity='physics',
        dof_order=['q'],tendon_order=['a','b'],actual_time_s=0.,integration_state=[0.],state_spec=1)
    raw=dict(status='computed',operation='mujoco_direct_control_v1',candidate=candidate,protocol=dict(horizon_alignment_atol_s=1e-10),
        binding=dict(candidate=candidate,effective_configuration_identity=digest(cfg),task_identity='task',tension_bounds_n=[[0,8],[0,8]]),
        requested_operation=dict(control_optimization=dict(source=source,settings=settings)),
        native_dynamics=dict(initial_state=point,original_schedule=dict(trajectory=tr),
            optimized_schedule=dict(trajectory=tr),optimization=dict(best=row,candidates=[row],algorithm='pattern',
                stop_reason='evaluation_request_budget',start_count=1,trust_radii_n={'native':.1},
                cost_feedback=dict(evaluation_callbacks=1,request_budget=2),iterations_started=1),cost={}))
    host,_=offline_host({candidate['artifact_id']:dict(configuration=cfg,condition_id='fixture'),result['artifact_id']:raw},analysis_results=[result])
    lookup=host.store.artifact.side_effect
    host.store.artifact.side_effect=lambda r,**kwargs:lookup(r)
    return host,candidate,result,cfg,raw


class JointControlTests(unittest.TestCase):
    def test_duplicate_start_reuses_callback_and_retains_per_start_feedback(self):
        f=search_fixtures.LocalSearchTests();callback=f.evaluator()
        result=search([start(),start('same-input')],callback,
            dict(method='pattern',evaluation_requests=2),reuse_sequences=True)
        self.assertEqual(len(f.calls),1)
        self.assertEqual(result['start_count'],2)
        self.assertEqual(result['cost_feedback']['cache_reuses'],1)
        self.assertEqual(len(result['start_feedback']),2)
        self.assertEqual(result['cost_feedback']['charged_numerical_s'],1.)

    def test_scientific_knots_scales_and_active_indices_reach_real_settings(self):
        spec=dict(analysis_protocol=dict(duration_s=.6))
        effort=dict(method='pattern',knot_count=4,iterations=2,evaluation_requests=8,
            coefficient_limit_n=5.,initial_radius_n=.8,difference_step_n=.04,minimum_radius_n=.002,active_coefficients=[2,3])
        coarse=control_settings(spec,effort,channels=2)
        fine=control_settings(spec,dict(effort,knot_count=8),channels=2)
        self.assertEqual(len(coarse.knots_s),4);self.assertEqual(len(fine.knots_s),8)
        self.assertEqual((coarse.initial_radius_n,coarse.difference_step_n),(.8,.04))
        self.assertEqual(coarse.active_coefficients,[2,3])
        with self.assertRaisesRegex(ValueError,'INTERIOR_KNOTS'):
            control_settings(spec,dict(effort,active_coefficients=[0]),channels=2,window=[.1,.4])
        with self.assertRaisesRegex(ValueError,'BOUND_DIMENSIONS'):
            control_settings(spec,dict(effort,active_coefficients=[99]),channels=2)

    def test_best_point_selects_time_without_fabricating_integration_state(self):
        h,c,r,cfg,raw=evidence()
        q=SimpleNamespace(candidate=c,saved_state=r,native_state_selection=NativeStateSelection(kind='best_peak_speed'))
        with patch('tools.research.physical_replay.binding'),patch('tools.research_tasks.task_adapter') as adapter:
            adapter.return_value.control_search_options.return_value=dict(holding_start=.02)
            p=native_point(h,q,cfg)
            self.assertEqual(p['actual_time_s'],.02)
            self.assertNotIn('integration_state',p)
            self.assertEqual(p['native_replay']['sample_index'],1)
            self.assertEqual(p['native_replay']['control_schedule']['trajectory']['tensions_n'],[[.2,.2]]*2)
            q.native_state_selection=NativeStateSelection(kind='best_sample',time_s=.03)
            with self.assertRaisesRegex(ValueError,'GRID_SAMPLE_REQUIRED'):native_point(h,q,cfg)
            q.native_state_selection=NativeStateSelection(kind='best_sample',time_s=.04)
            p=native_point(h,q,cfg);self.assertEqual(p['remaining_task_s'],0.)
            q.candidate=ref('d')
            with self.assertRaisesRegex(ValueError,'OWNED_COMPLETE'):native_point(h,q,cfg)

    def test_missing_best_mechanism_never_creates_structural_judgment(self):
        h,c,r,cfg,raw=evidence();view=bottleneck_diagnosis(h,r,detailed=True)
        statuses=[x['status'] for x in view['explanations']]
        self.assertIn('control_search_evidence_insufficient',statuses)
        self.assertIn('unresolved',statuses);self.assertNotIn('structural_drive_concern',statuses)
        self.assertTrue(view['missing_evidence']);self.assertEqual(view['control_search']['best_metrics']['holding_max_speed_m_s'],.12)
        h.store.reserve.assert_not_called();h.store.transaction.assert_not_called()

    def test_missing_state_selector_time_and_source_are_rejected(self):
        for payload in (dict(kind='best_sample'),dict(kind='best_peak_speed',time_s=.1)):
            with self.assertRaises(ValueError):NativeStateSelection.model_validate(payload)

    def test_failed_prefix_verification_preserves_attempted_physics_cost(self):
        from extensions.tendon_family.mujoco_analysis import NativeModel
        from unittest.mock import Mock
        native=object.__new__(NativeModel)
        native.cost=dict(physics_steps=20,physics_step_attempts=20,rollouts=1,model_builds=1)
        native._reconstruct=Mock(side_effect=ValueError('SAVED_OUTPUT_MISMATCH'))
        with self.assertRaises(ValueError) as raised:native.reconstruct({'fixture':True})
        self.assertEqual(raised.exception.native_diagnostic['cost']['physics_steps'],20)
        self.assertEqual(raised.exception.native_diagnostic['task_acceptance'],'unmeasured')

    def test_search_and_structural_concerns_can_coexist(self):
        from tools.research.state import state
        h,c,r,cfg,raw=evidence();mr=ref('d')
        mechanism=dict(status='computed',operation='mechanism_structure_v1',candidate=c,
            operating_point=dict(actual_time_s=.02,source=dict(analysis=r,sequence_hash=raw['native_dynamics']['optimization']['best']['sequence_hash'],remaining_task_s=.02)),
            structure_research=dict(target=dict(quantity='instantaneous_braking',reduction='minimum'),
                records=[dict(observation=dict(status='computed',value=1.,unit='m/s^2'),
                    mechanics=dict(function_metrics=dict(instantaneous_speed_derivative_range_m_s2=[1.,5.])))]))
        state(h)['analysis_results'].append(mr)
        lookup=h.store.artifact.side_effect
        h.store.artifact.side_effect=lambda rr,**kw:mechanism if rr==mr else lookup(rr,**kw)
        statuses=[x['status'] for x in bottleneck_diagnosis(h,r)['explanations']]
        self.assertIn('control_search_evidence_insufficient',statuses)
        self.assertIn('structural_drive_concern',statuses)
        self.assertIn('unresolved',statuses)

    def test_rl_applied_trace_prepares_unmeasured_replay_without_policy_credit(self):
        import hashlib
        from tools.research.rl import measured_rl_trajectory
        c,r,config_ref,trace_ref=map(ref,('a','b','c','d'))
        task=dict(timing=dict(duration_s=.04,control_period_s=.02))
        cfg=dict(task=task)
        text='control_step,time_s,engine_time_s,a_applied_n,b_applied_n,a_commanded_n,b_commanded_n\n0,0,0,0,0,99,99\n1,.02,.02,.3,.4,99,99\n2,.04,.04,.5,.6,99,99\n'
        trace=dict(configuration=config_ref,candidate=c,task_identity=digest(task),csv_text=text,
            sha256=hashlib.sha256(text.encode()).hexdigest())
        result=dict(candidate=c,configuration=config_ref,measured_control_trace=trace_ref,operation_key='fixture-eval',execution_id='fixture-exec',
            independent_evaluation_executed=True,episodes=[dict(complete=True,numerical_failure=None)],
            checkpoint='fixture',policy_sha256='fixture-policy')
        frozen=dict(candidate=dict(reference=c),task=dict(original=task),control_object=dict(tendon_names=['a','b']))
        h,_=offline_host({r['artifact_id']:result,config_ref['artifact_id']:frozen,trace_ref['artifact_id']:trace},rl_evaluations=[r])
        import json
        h.store.lookup.return_value=dict(receipt=json.dumps(dict(execution_status='completed',output=r,tool_id='research.core_rl',execution_id='fixture-exec')))
        physics=dict(tendons=[dict(entity='a'),dict(entity='b')]);model=dict(identity='model',design_identity='design')
        with patch('tools.research.rl.verify_candidate',return_value=dict(configuration=cfg)),patch('tools.research.physical_replay.model_context',return_value=(None,physics,None,model)),patch('tools.research.physical_replay.binding'):
            trajectory,provenance=measured_rl_trajectory(h,r)
            self.assertEqual(trajectory['tensions_n'],[[.3,.4],[.5,.6]])
            self.assertFalse(provenance['inherited_acceptance'])
            result['episodes'][0]['complete']=False
            with self.assertRaisesRegex(ValueError,'COMPLETE_MEASURED'):measured_rl_trajectory(h,r)
            result['episodes'][0]['complete']=True
            trace['csv_text']=text.replace('.02,.02','nan,.02');trace['sha256']=hashlib.sha256(trace['csv_text'].encode()).hexdigest()
            with self.assertRaisesRegex(ValueError,'ALIGNED_RL'):measured_rl_trajectory(h,r)
        h.store.reserve.assert_not_called()


if __name__=='__main__':unittest.main()
