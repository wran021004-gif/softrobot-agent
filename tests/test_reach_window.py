"""Focused geometry, collision evidence and real constrained-route validation."""
import json
import os
from pathlib import Path
import tempfile
import unittest

import mujoco
from controllers.open_loop_length import OpenLoopLength
from metrics.reach import evaluate_reach
from schemas.environment_spec import EnvironmentSpec
from schemas.tool_result import ToolResult
from tests.test_architecture import design, BASELINE
from tools.artifact_tools import file_hash
from tools.design_compiler import build_robot_ir
from tools.diagnostic_tools import check_collision
from tools.finding_tools import extract_diagnostic_finding
from tools.harness import run_reach
from tools.mujoco_tools import compile_mujoco, run_task
from tools.spec_tools import ROOT, load_task_package, environment_xml, validate_frozen_environment
from tools.trace_tools import read_trace, validate_trace
from tools.window_evidence import WindowEvidence
from tools.window_geometry import constrained_window, aperture_crossing, window_boxes

FIXTURE = ROOT / 'tests/fixtures/reach_window_dev'
ENABLED = os.environ.get('SOFTROBOT_TEST_MATLAB') == '1'


def window_variant(environment, **updates):
    value = environment.model_dump(mode='json')
    for obj in value['objects']:
        if obj['kind'] == 'window':
            obj.update(updates)
    return EnvironmentSpec.model_validate(value)


class WindowGeometryTests(unittest.TestCase):
    def test_shared_geometry_and_whole_shape_crossing(self):
        task, env = load_task_package(FIXTURE)
        window = constrained_window(env, task)
        self.assertEqual(env.truth_status, 'NON_CANONICAL_DEVELOPMENT_ONLY')
        validate_frozen_environment(env, FIXTURE / 'mujoco.xml')
        bars = environment_xml(env).find('worldbody').findall("geom[@type='box']")
        for bar, (name, centre, size) in zip(bars, window_boxes(window)):
            self.assertEqual(bar.get('name'), name)
            self.assertEqual(list(map(float, bar.get('pos').split())), centre)
            self.assertEqual(list(map(float, bar.get('size').split())), size)
        self.assertTrue(aperture_crossing([[0, 0, 0], [.4, 0, 0]], .02, window)['aperture_constraint_satisfied'])
        # Endpoint behind the target plane cannot certify a path around the frame.
        around = [[0, 0, 0], [.18, .4, .06], [.4, 0, 0]]
        self.assertFalse(aperture_crossing(around, .02, window)['aperture_constraint_satisfied'])

    def test_actual_capsule_gap_contact_and_constraint_gate(self):
        task, env = load_task_package(FIXTURE)
        ir = build_robot_ir(design())
        with tempfile.TemporaryDirectory(dir=ROOT / 'runs') as tmp:
            for width, expected_contact in ((.12, False), (.03, True)):
                variant = window_variant(env, width_m=width)
                xml = Path(tmp) / 'model.xml'
                self.assertEqual(compile_mujoco(ir, task, xml, variant).status, 'pass')
                model = mujoco.MjModel.from_xml_path(str(xml))
                data = mujoco.MjData(model)
                mujoco.mj_forward(model, data)
                evidence = WindowEvidence(model, constrained_window(variant, task))
                evidence.observe(model, data, 0.)
                result = evidence.summary()
                self.assertEqual(result['obstacle_contact_occurred'], expected_contact)
                self.assertAlmostEqual(result['minimum_observed_robot_obstacle_clearance_m'], -.005 if expected_contact else .01, places=10)
                self.assertEqual(bool(result['contact_pairs']), expected_contact)
                metric = evaluate_reach(task.target_m, task, result)
                self.assertTrue(metric['target_reached'])
                self.assertEqual(metric['task_success'], not expected_contact)

    def test_collision_diagnostics_keep_evidence_distinct_from_cause(self):
        context = {'run_id': 'focused_fixture'}
        prediction = ToolResult(tool='analyze_clearance', status='pass', metrics={
            'comparison_context': context, 'predicted_clearance_violation': False,
            'predicted_intersection': False, 'predicted_minimum_clearance_m': .01,
            'aperture_constraint_satisfied': True})
        execution = ToolResult(tool='run_task', status='fail', failure_code='TASK_FAILED', metrics={
            'comparison_context': context, 'task_success': False, 'target_reached': False,
            'window_evidence': {'obstacle_contact_occurred': True, 'contact_count': 1,
                                'minimum_observed_robot_obstacle_clearance_m': -.001,
                                'contact_pairs': [], 'aperture_constraint_satisfied': False}})
        result = check_collision(prediction, execution)
        self.assertTrue(result.metrics['model_simulation_disagreement_observed'])
        self.assertEqual(result.metrics['failure_attribution'], 'UNKNOWN')
        failed = execution.model_copy(update={'metrics': {}, 'failure_code': 'NONFINITE_STATE'})
        self.assertEqual(check_collision(prediction, failed).metrics['evidence_status'], 'unavailable')


@unittest.skipUnless(ENABLED, 'Set SOFTROBOT_TEST_MATLAB=1 for real clearance analysis')
class MatlabClearanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tools.matlab_tools import MatlabTools
        cls.matlab = MatlabTools()
        cls.task, cls.env = load_task_package(FIXTURE)
        cls.ir = build_robot_ir(design())

    @classmethod
    def tearDownClass(cls):
        cls.matlab.close()

    def test_nominal_straight_clearance_bound(self):
        plan = ToolResult(tool='plan_pcc_reach', status='pass', metrics={'theta_rad': 0., 'phi_rad': 0.})
        result = self.matlab.analyze_clearance(self.ir, self.task, self.env, plan)
        self.assertAlmostEqual(result.metrics['sampled_minimum_clearance_m'], .01, places=12)
        self.assertAlmostEqual(result.metrics['predicted_minimum_clearance_m'], .0095, places=12)
        self.assertTrue(result.metrics['aperture_constraint_satisfied'])
        self.assertEqual(result.artifacts['predicted_centerline_m'][-1], [.4, 0., 0.])

    def test_narrow_aperture_detects_body_intersection_away_from_tip(self):
        env = window_variant(self.env, width_m=.03)
        plan = ToolResult(tool='plan_pcc_reach', status='pass', metrics={'theta_rad': 0., 'phi_rad': 0., 'comparison_context': {'run_id': 'narrow'}})
        result = self.matlab.analyze_clearance(self.ir, self.task, env, plan)
        self.assertTrue(result.metrics['predicted_intersection'])
        self.assertFalse(result.metrics['aperture_constraint_satisfied'])
        self.assertLess(result.metrics['closest_location_m'][0], .21)
        self.assertGreater(result.artifacts['predicted_centerline_m'][-1][0], .3)
        sim = ToolResult(tool='run_task', status='fail', metrics={'comparison_context': {'run_id': 'narrow'},
            'task_success': False, 'target_reached': False, 'window_evidence': {
                'obstacle_contact_occurred': True, 'contact_count': 1, 'contact_pairs': [],
                'minimum_observed_robot_obstacle_clearance_m': -.005, 'aperture_constraint_satisfied': False}})
        self.assertEqual(check_collision(result, sim).metrics['observation'], 'predicted_geometric_intersection')

    def test_real_clear_prediction_with_initial_collision_disagreement(self):
        # Deliberately overlapping initial arm, explicitly distinguished from insertion.
        env = window_variant(self.env, position_m=[.18, 0., .08], height_m=.12)
        plan = self.matlab.plan_pcc_reach(self.ir, self.task, env)
        context = {'run_id': 'initial_collision_development_case'}
        plan = plan.model_copy(update={'metrics': {**plan.metrics, 'comparison_context': context}})
        prediction = self.matlab.analyze_clearance(self.ir, self.task, env, plan)
        self.assertFalse(prediction.metrics['predicted_clearance_violation'])
        with tempfile.TemporaryDirectory(dir=ROOT / 'runs') as tmp:
            compiled = compile_mujoco(self.ir, self.task, Path(tmp) / 'robot.xml', env)
            result = run_task(compiled.artifacts['mjcf_path'], self.task,
                              OpenLoopLength(plan.metrics['tendon_target_lengths_m']), environment=env)
        self.assertIn('task_success', result.metrics, result)
        result = result.model_copy(update={'metrics': {**result.metrics, 'comparison_context': context}})
        self.assertTrue(result.metrics['window_evidence']['initial_configuration']['obstacle_contact_occurred'])
        diagnostic = check_collision(prediction, result)
        self.assertTrue(diagnostic.metrics['model_simulation_disagreement_observed'], diagnostic)
        self.assertEqual(diagnostic.metrics['failure_attribution'], 'UNKNOWN')


@unittest.skipUnless(ENABLED, 'Set SOFTROBOT_TEST_MATLAB=1 for real constrained Harness')
class WindowPipelineTests(unittest.TestCase):
    def test_real_development_route_artifacts_and_finding(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'runs') as tmp:
            run = run_reach(task_package=FIXTURE, run_root=tmp)
            self.assertEqual(run.record.final_status, 'TASK_FAILED', (run.path / 'trace.json').read_text())
            load = lambda name: json.loads((run.path / name).read_text())
            self.assertAlmostEqual(load('model_result.json')['metrics']['predicted_position_error_m'], BASELINE['predicted_position_error_m'], places=12)
            result = load('mujoco_result.json')['metrics']
            self.assertFalse(result['target_reached'])
            self.assertTrue(result['aperture_constraint_satisfied'])
            self.assertFalse(result['obstacle_contact_occurred'])
            self.assertEqual(load('check_collision.json')['metrics']['observation'], 'no_window_contact_observed')
            self.assertEqual(load('provenance.json')['parameters']['target_m']['scientific_status'], 'NON_CANONICAL_DEVELOPMENT_ONLY')
            events = read_trace(run.path / 'trace.jsonl')
            validate_trace(events)
            operations = {e.operation for e in events}
            self.assertTrue({'analyze_clearance', 'check_collision', 'model_clearance_gate', 'aperture_constraint_satisfied_gate', 'task_success_gate'} <= operations)
            self.assertLess(len(events), 170)
            for name, expected in run.record.artifact_hashes.items():
                self.assertEqual(file_hash(run.path / name), expected)
            finding = extract_diagnostic_finding(run.record.run_id, tmp)
            self.assertIsNotNone(finding)
            self.assertTrue(any(o.evidence.path == 'check_collision.json' for o in finding.observation))
            self.assertEqual(finding.causal_attribution, 'UNKNOWN')
