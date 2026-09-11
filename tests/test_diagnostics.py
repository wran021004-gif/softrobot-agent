import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import mujoco
from controllers.open_loop_length import OpenLoopLength
from schemas.tool_result import ToolResult
from schemas.task_spec import TaskSpec
from tools.diagnostic_tools import compare_model_sim, check_actuator_limits, check_tendon_tracking, inspect_numerics
from tools.mujoco_tools import compile_mujoco, run_task
from tools.spec_tools import ROOT, load_task, load_run_settings
from tests.test_architecture import design, BASELINE


def sample():
    # Hand-checkable synthetic observations, independent of the canonical run.
    task = TaskSpec(task_id='unit', task_type='reach', environment_id='reach_free', target_m=[0, 0, 0], position_error_max_m=0.01)
    model = ToolResult(tool='plan_pcc_reach', status='pass', metrics={
        'predicted_tip_m': [0.03, 0, 0], 'target_position_m': [0, 0, 0],
        'predicted_position_error_m': 0.03, 'model_task_success': False, 'tendon_target_lengths_m': [0.4]})
    sim = ToolResult(tool='run_task', status='fail', failure_code='TASK_FAILED', metrics={
        'tip_position_m': [0, 0.04, 0], 'target_position_m': [0, 0, 0], 'position_error_m': 0.04,
        'position_error_max_m': 0.01, 'task_success': False, 'tendon_target_lengths_m': [0.4],
        'actuator_controls': [0.4], 'final_tendon_lengths_m': [0.42],
        'execution_evidence': {'steps_requested': 10, 'steps_completed': 10, 'timestep_s': 0.002,
            'actuators': [{'index': 0, 'name': 'tendon_0_actuator', 'tendon_index': 0, 'force_limited': True,
                'force_range_n': [-20, 0], 'active_samples': 10, 'lower_limit_samples': 2, 'upper_limit_samples': 3,
                'peak_abs_force_n': 20, 'min_force_n': -20, 'max_force_n': 0,
                'command_min_m': 0.4, 'command_max_m': 0.4}],
            'numerics': {'qpos_all_finite': True, 'qvel_all_finite': True, 'actuator_force_all_finite': True,
                'tendon_length_all_finite': True, 'max_abs_qpos_rad': 1, 'max_abs_qvel_rad_s': 2,
                'time_advance_anomaly': False, 'warnings': {'mjWARN_BADQVEL': 0}}}})
    context = dict(run_id='synthetic_unit', task_hash='synthetic_task', environment_hash='synthetic_environment',
                   robot_ir_hash='synthetic_ir', coordinate_frame='world_base_x_forward_yz_cross_section')
    model.metrics['comparison_context'] = context.copy()
    sim.metrics['comparison_context'] = context.copy()
    return task, model, sim


class DiagnosticTests(unittest.TestCase):
    def test_comparison_and_no_fabricated_attribution(self):
        task, model, sim = sample()
        result = compare_model_sim(model, sim, task, evidence_paths=('model.json', 'sim.json'))
        self.assertEqual(result.metrics['tip_discrepancy_m'], 0.05)
        self.assertTrue(result.metrics['model_predicts_tolerance_failure'])
        self.assertEqual(result.metrics['failure_attribution'], 'UNKNOWN')
        self.assertIsNone(result.metrics['mismatch_criterion'])
        self.assertEqual(result.artifacts['evidence_paths'], ['model.json', 'sim.json'])
        sim.metrics['target_position_m'][0] = 1
        self.assertEqual(compare_model_sim(model, sim, task).metrics['evidence_status'], 'unavailable')

    def test_inconsistent_commands_and_recorded_error_rejected(self):
        for field, value in [('tendon_target_lengths_m', [0.3]), ('position_error_m', 0.5), ('task_success', True)]:
            task, model, sim = sample()
            sim.metrics[field] = value
            self.assertEqual(compare_model_sim(model, sim, task).status, 'fail')
        task, model, sim = sample()
        sim.metrics['execution_evidence']['actuators'][0]['command_min_m'] = 0.3
        self.assertEqual(compare_model_sim(model, sim, task).status, 'fail')
        task, model, sim = sample()
        sim.metrics['comparison_context']['robot_ir_hash'] = 'different_robot'
        self.assertEqual(compare_model_sim(model, sim, task).status, 'fail')

    def test_saturation_and_no_push_bound_are_distinct(self):
        _, _, sim = sample()
        result = check_actuator_limits(sim)
        row = result.metrics['actuators'][0]
        self.assertEqual(row['max_pull_limit_fraction'], 0.2)
        self.assertEqual(row['max_pull_limit_sampled_duration_s'], 0.004)
        self.assertEqual(result.metrics['supported_evidence_category'], 'ACTUATOR_LIMIT')
        row = sim.metrics['execution_evidence']['actuators'][0]
        row.update(lower_limit_samples=0, min_force_n=-5, peak_abs_force_n=5)
        result = check_actuator_limits(sim)
        self.assertFalse(result.metrics['max_pull_limit_observed'])
        self.assertEqual(result.metrics['actuators'][0]['upper_zero_bound_fraction'], 0.3)
        self.assertEqual(result.metrics['failure_attribution'], 'UNKNOWN')

    def test_tracking_arithmetic(self):
        _, _, sim = sample()
        result = check_tendon_tracking(sim)
        row = result.metrics['tendons'][0]
        self.assertAlmostEqual(row['absolute_error_m'], 0.02)
        self.assertAlmostEqual(row['relative_error'], 0.05)
        self.assertIsNone(result.metrics['tracking_acceptance_threshold'])

    def test_numerical_anomalies_and_no_stability_claim(self):
        _, _, sim = sample()
        result = inspect_numerics(sim)
        self.assertEqual(result.metrics['anomaly_indicators'], [])
        self.assertFalse(result.metrics['stability_validated'])
        n = sim.metrics['execution_evidence']['numerics']
        n.update(qvel_all_finite=False, time_advance_anomaly=True, warnings={'mjWARN_BADQVEL': 2})
        sim.failure_code = 'NONFINITE_STATE'
        result = inspect_numerics(sim)
        self.assertIn('qvel_all_finite', result.metrics['anomaly_indicators'])
        self.assertIn('NONFINITE_STATE', result.metrics['anomaly_indicators'])
        self.assertFalse(result.metrics['stability_validated'])

    def test_missing_and_malformed_evidence(self):
        task, model, _ = sample()
        for metrics in ({}, {'execution_evidence': None}, {'tendon_target_lengths_m': [float('nan')]},
                        {'execution_evidence': {'actuators': []}}):
            sim = ToolResult(status='fail', tool='run_task', failure_code='TASK_FAILED', metrics=metrics)
            for tool in (check_actuator_limits, check_tendon_tracking, inspect_numerics):
                result = tool(sim)
                self.assertEqual(result.metrics['evidence_status'], 'unavailable')
                self.assertEqual(result.failure_code, 'UNKNOWN')
                self.assertEqual(result.metrics['failure_attribution'], 'UNKNOWN')
            self.assertEqual(compare_model_sim(model, sim, task).status, 'fail')
        _, _, sim = sample()
        sim.metrics['execution_evidence']['actuators'][0]['lower_limit_samples'] = 11
        self.assertEqual(check_actuator_limits(sim).status, 'fail')
        sim.metrics['execution_evidence']['numerics']['qvel_all_finite'] = 'true'
        self.assertEqual(inspect_numerics(sim).status, 'fail')

    def test_no_samples_or_overflow_do_not_fabricate_evidence(self):
        _, _, sim = sample()
        sim.metrics['execution_evidence']['steps_completed'] = 0
        self.assertEqual(inspect_numerics(sim).metrics['evidence_status'], 'unavailable')
        sim.metrics.update(tendon_target_lengths_m=[1e-300], actuator_controls=[1e-300], final_tendon_lengths_m=[1e300])
        result = check_tendon_tracking(sim)
        self.assertEqual(result.metrics['evidence_status'], 'unavailable')
        json.dumps(result.model_dump(), allow_nan=False)


class RunnerEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / 'runs')
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'robot.xml'
        self.task = load_task()
        compile_mujoco(design(), self.task, self.path)

    def test_baseline_observation_does_not_change_simulation(self):
        result = run_task(self.path, self.task, OpenLoopLength(BASELINE['tendon_target_lengths_m']))
        self.assertEqual(result.failure_code, 'TASK_FAILED')
        self.assertAlmostEqual(result.metrics['position_error_m'], BASELINE['position_error_m'], places=12)
        obs = result.metrics['execution_evidence']
        self.assertEqual(obs['steps_completed'], load_run_settings().steps)
        self.assertAlmostEqual(obs['tip_initial_position_m'][0], design().total_length_m)
        self.assertEqual(len(obs['actuators']), design().tendon_count)
        self.assertEqual(inspect_numerics(result).metrics['anomaly_indicators'], [])
        self.assertEqual(check_actuator_limits(result).status, 'pass')
        self.assertEqual(check_tendon_tracking(result).status, 'pass')
        json.dumps(result.model_dump(), allow_nan=False)

    def test_force_limit_observed_in_independent_synthetic_xml(self):
        # Unit case only; the frozen baseline/compiler constants remain untouched.
        tree = ET.parse(self.path)
        for node in tree.findall('./actuator/position'):
            node.set('forcerange', '-1 0')
        tree.write(self.path)
        result = run_task(self.path, self.task, OpenLoopLength([0.3] * design().tendon_count),
                          load_run_settings().model_copy(update={'steps': 5}))
        checked = check_actuator_limits(result)
        self.assertTrue(checked.metrics['max_pull_limit_observed'])
        self.assertTrue(all(r['observed_peak_abs_force_n'] == 1 for r in checked.metrics['actuators']))

    def test_passive_has_no_command_or_saturation_evidence(self):
        result = run_task(self.path, self.task)
        self.assertEqual(check_actuator_limits(result).metrics['evidence_status'], 'unavailable')
        self.assertEqual(check_tendon_tracking(result).metrics['evidence_status'], 'unavailable')
        self.assertEqual(inspect_numerics(result).status, 'pass')

    def test_nonfinite_interruption_keeps_serializable_evidence(self):
        def invalid_step(model, data):
            data.qpos[:] = float('nan')
            data.qvel[:] = float('inf')
        with patch('tools.mujoco_tools.mujoco.mj_step', side_effect=invalid_step):
            result = run_task(self.path, self.task)
        self.assertEqual(result.failure_code, 'NONFINITE_STATE')
        self.assertFalse(result.metrics['execution_evidence']['numerics']['qpos_all_finite'])
        self.assertNotIn('task_success', result.metrics)
        json.dumps(result.model_dump(), allow_nan=False)

    def test_engine_warning_survives_finite_state(self):
        real_step = mujoco.mj_step
        def warned_step(model, data):
            real_step(model, data)
            data.warning[int(mujoco.mjtWarning.mjWARN_BADQVEL)].number += 1
        with patch('tools.mujoco_tools.mujoco.mj_step', side_effect=warned_step):
            result = run_task(self.path, self.task, run_settings=load_run_settings().model_copy(update={'steps': 2}))
        checked = inspect_numerics(result)
        self.assertIn('simulator_warnings', checked.metrics['anomaly_indicators'])


if __name__ == '__main__':
    unittest.main()
