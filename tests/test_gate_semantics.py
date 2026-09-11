"""Five focused scientific-contract tests; no new hardening matrix."""
import json
import math
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import mujoco
from pydantic import ValidationError
import yaml
from metrics.reach import evaluate_reach
from schemas.environment_spec import EnvironmentSpec
from schemas.gate import gate_action
from schemas.task_spec import TaskSpec, WindowAcceptance
from schemas.tool_result import ToolResult
from tests.test_architecture import design
from tests.test_trace import FixtureMatlab
from tools.design_compiler import build_robot_ir
from tools.harness import run_reach
from tools.mujoco_tools import compile_mujoco
from tools.spec_tools import ROOT, load_task_package, load_yaml
from tools.trace_tools import read_trace
from tools.window_evidence import WindowEvidence
from tools.window_geometry import constrained_window


class ExactTargetOutsideMatlab(FixtureMatlab):
    """Test double reproducing M0 exact-point failure, not a MATLAB result."""
    def analyze_workspace(self, ir, task, environment):
        return ToolResult(tool='analyze_workspace', status='fail', failure_code='DESIGN_INFEASIBLE',
                          metrics={'target_reachable': False})

    def plan_pcc_reach(self, ir, task, environment):
        tip = [ir.total_length_m, 0., 0.]
        error = math.dist(tip, task.target_m)
        return ToolResult(tool='plan_pcc_reach', status='pass', metrics={
            'predicted_tip_m': tip, 'target_position_m': list(task.target_m),
            'predicted_position_error_m': error, 'model_task_success': error <= task.position_error_max_m,
            'tendon_target_lengths_m': [ir.total_length_m] * ir.tendon_count})


class NegativeClearanceMatlab(FixtureMatlab):
    """Deliberate negative screening evidence to test routing, not scientific data."""
    def analyze_clearance(self, ir, task, environment, plan):
        return ToolResult(tool='analyze_clearance', status='pass', metrics={
            'comparison_context': plan.metrics['comparison_context'],
            'predicted_minimum_clearance_m': -.005, 'predicted_clearance_violation': True,
            'predicted_intersection': True, 'aperture_constraint_satisfied': False})


class GateSemanticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / 'runs')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def summary(self, run):
        return json.loads((run.path / 'gate_summary.json').read_text())

    def test_hard_necessary_bound_stops_but_respects_task_tolerance(self):
        package = self.root / 'task_package'
        shutil.copytree(ROOT / 'tasks/reach_free', package)
        # This modified local test is deliberately not the registered frozen task.
        (package / 'contract.yaml').unlink()
        original = load_yaml(package / 'task.yaml')
        for target_x, should_stop in ((.42, True), (.405, False)):
            (package / 'task.yaml').write_text(yaml.safe_dump({**original, 'target_m': [target_x, 0., 0.]}))
            with patch('tools.mujoco_tools.compile_mujoco', wraps=compile_mujoco) as compiler:
                run = run_reach(task_package=package, run_root=self.root, matlab_factory=ExactTargetOutsideMatlab)
            summary = self.summary(run)
            gate = next(g for g in summary['gates'] if g['operation'] == 'workspace_gate')
            self.assertEqual(gate['gate_type'], 'HARD')
            self.assertAlmostEqual(gate['threshold'], .41)
            self.assertEqual(compiler.called, not should_stop)
            if should_stop:
                self.assertEqual(summary['termination'], 'HARD_FAIL')
                self.assertEqual(summary['canonical_result'], 'NOT_RUN')
                self.assertEqual(run.record.final_status, 'DESIGN_INFEASIBLE')
            else:
                self.assertEqual(gate['decision'], 'PASS')
                self.assertTrue((run.path / 'mujoco_result.json').exists())

    def test_screening_failures_continue_and_canonical_failure_is_final(self):
        run = run_reach(task_package=ROOT / 'tests/fixtures/reach_window_dev', run_root=self.root,
                        matlab_factory=NegativeClearanceMatlab)
        summary = self.summary(run)
        self.assertEqual(run.record.final_status, 'TASK_FAILED')
        self.assertEqual(summary['canonical_result'], 'FAIL')
        self.assertEqual(set(summary['screening_failures']), {'model_prediction_gate', 'model_clearance_gate'})
        self.assertFalse(summary['stopped_by'])
        self.assertEqual(gate_action('SCREENING', 'FAIL'), 'CONTINUE')
        self.assertEqual(gate_action('CANONICAL', 'FAIL'), 'TASK_FAILED')
        events = read_trace(run.path / 'trace.jsonl')
        gates = [e for e in events if e.gate is not None]
        self.assertTrue(all(e.gate.gate_type is not None for e in gates))
        self.assertEqual({e.gate.gate_type.value for e in gates}, {'HARD', 'SCREENING', 'CANONICAL'})
        screening_end = max(e.sequence for e in gates if e.gate.gate_type == 'SCREENING')
        self.assertTrue(any(e.sequence > screening_end and e.operation == 'run_task' and
                            e.event_type == 'TOOL_STARTED' for e in events))
        self.assertEqual(summary['gates'][-1]['action'], 'TASK_FAILED')

    def test_proposal_cannot_be_loaded_as_frozen_task(self):
        proposal = ROOT / 'proposals/benchmark/reach_window_v1'
        for name in ('candidate_task.yaml', 'candidate_environment.yaml', 'candidate_acceptance.yaml'):
            self.assertEqual(load_yaml(proposal / name)['truth_status'], 'PROPOSED_NOT_APPROVED')
        with self.assertRaises(ValidationError):
            TaskSpec.model_validate(load_yaml(proposal / 'candidate_task.yaml'))
        with self.assertRaises(ValidationError):
            EnvironmentSpec.model_validate(load_yaml(proposal / 'candidate_environment.yaml'))
        registry = load_yaml(ROOT / 'benchmarks/tendon_v1.yaml')
        self.assertEqual([t['package'] for t in registry['tasks']], ['tasks/reach_free'])
        self.assertEqual(registry['tasks'][0]['truth_status'], 'FROZEN')
        _, env = load_task_package(ROOT / 'tests/fixtures/reach_window_dev')
        self.assertEqual(env.truth_status, 'NON_CANONICAL_DEVELOPMENT_ONLY')

    def test_initial_whole_body_region_and_acceptance(self):
        task, env = load_task_package(ROOT / 'tests/fixtures/reach_window_dev')
        ir = build_robot_ir(design())
        compiled = compile_mujoco(ir, task, self.root / 'robot.xml', env)
        model = mujoco.MjModel.from_xml_path(compiled.artifacts['mjcf_path'])
        data = mujoco.MjData(model)
        mujoco.mj_forward(model, data)
        evidence = WindowEvidence(model, constrained_window(env, task))
        evidence.observe(model, data, 0.)
        observed = evidence.summary()
        self.assertEqual(observed['initial_side_of_wall'], 'straddles_window')
        self.assertTrue(observed['initial_aperture_state']['aperture_constraint_satisfied'])
        before_task = task.model_copy(update={'acceptance': WindowAcceptance(initial_robot_region='before_window')})
        # Exact target isolates the initial-side criterion from endpoint error.
        self.assertTrue(evaluate_reach(task.target_m, task, observed)['task_success'])
        checked = evaluate_reach(task.target_m, before_task, observed)
        self.assertFalse(checked['initial_required_side_satisfied'])
        self.assertFalse(checked['task_success'])
        # Isolated geometry sample of a backwards-folded arm; not a new initializer.
        data.qpos[0] = math.pi
        mujoco.mj_forward(model, data)
        before = WindowEvidence(model, constrained_window(env, task))
        before.observe(model, data, 0.)
        self.assertEqual(before.summary()['initial_side_of_wall'], 'before_window')
        self.assertEqual(before.summary()['final_side_of_wall'], 'before_window')

    def test_tool_execution_failure_is_hard_not_negative_prediction(self):
        class FailedPlanner(FixtureMatlab):
            def plan_pcc_reach(self, *args):
                return ToolResult(tool='plan_pcc_reach', status='fail', failure_code='PCC_INVALID_COMMAND')
        with patch('tools.mujoco_tools.compile_mujoco') as compiler:
            run = run_reach(run_root=self.root, matlab_factory=FailedPlanner)
        compiler.assert_not_called()
        summary = self.summary(run)
        self.assertIn('model_execution_gate', summary['stopped_by'])
        self.assertEqual(summary['screening_failures'], [])
        self.assertEqual(summary['canonical_result'], 'NOT_RUN')
