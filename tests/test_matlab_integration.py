import json
import math
import os
from pathlib import Path
import tempfile
import unittest
import hashlib
import zipfile
from schemas.task_spec import TaskSpec
from tools.artifact_tools import file_hash
from tools.design_compiler import build_robot_ir
from tools.harness import run_reach
from tools.spec_tools import ROOT, load_task_package
from tests.test_architecture import design, BASELINE

ENABLED = os.environ.get("SOFTROBOT_TEST_MATLAB") == "1"


@unittest.skipUnless(ENABLED, "Set SOFTROBOT_TEST_MATLAB=1 for real MATLAB Engine tests")
class MatlabCoordinateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tools.matlab_tools import MatlabTools
        cls.matlab = MatlabTools()
        cls.task, cls.environment = load_task_package()

    @classmethod
    def tearDownClass(cls):
        cls.matlab.close()

    def test_pcc_coordinate_contract(self):
        ir = build_robot_ir(design())
        straight = TaskSpec.model_validate({**self.task.model_dump(), "target_m": [0.4, 0, 0]})
        plan = self.matlab.plan_pcc_reach(ir, straight, self.environment)
        self.assertEqual(plan.metrics["theta_rad"], 0)
        self.assertEqual(plan.metrics["predicted_tip_m"], [0.4, 0, 0])
        for phi in (0, math.pi / 2, -math.pi / 2):
            target = [0.4 * math.sin(1), 0.4 * (1 - math.cos(1)) * math.cos(phi), 0.4 * (1 - math.cos(1)) * math.sin(phi)]
            task = TaskSpec.model_validate({**self.task.model_dump(), "target_m": target})
            plan = self.matlab.plan_pcc_reach(ir, task, self.environment)
            self.assertAlmostEqual(plan.metrics["phi_rad"], phi, places=12)
            self.assertLess(plan.metrics["predicted_position_error_m"], 1e-5)
            for route, length in zip(ir.tendon_routes, plan.metrics["tendon_target_lengths_m"]):
                expected = 0.4 - 0.015 * plan.metrics["theta_rad"] * math.cos(route.angle_rad - phi)
                self.assertAlmostEqual(length, expected, places=14)

    def test_real_matlab_best_effort_and_single_tendon(self):
        for count in (1, 4):
            ir = build_robot_ir(design(tendon_count=count))
            plan = self.matlab.plan_pcc_reach(ir, self.task, self.environment)
            self.assertEqual(plan.status, "pass")
            self.assertFalse(plan.metrics["model_task_success"])
            self.assertEqual(len(plan.metrics["tendon_target_lengths_m"]), count)
            self.assertAlmostEqual(plan.metrics["predicted_position_error_m"], BASELINE["predicted_position_error_m"], places=12)


@unittest.skipUnless(ENABLED, "Set SOFTROBOT_TEST_MATLAB=1 for real full pipeline")
class FullPipelineTests(unittest.TestCase):
    def test_current_reach_pipeline_smoke_and_run_artifacts(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as tmp:
            run = run_reach(run_root=tmp)
            self.assertEqual(run.record.final_status, "TASK_FAILED", (run.path / "trace.json").read_text())
            required = {"task.yaml", "environment.yaml", "design_input.yaml", "robot_ir.yaml", "design_final.yaml", "model_result.json", "tendon_command.json", "robot.xml", "controller.json", "mujoco_result.json", "metrics.json", "trace.json", "run.json", "source_snapshot.zip"}
            self.assertFalse(required - {p.name for p in run.path.iterdir()})
            model = json.loads((run.path / "model_result.json").read_text())
            simulation = json.loads((run.path / "mujoco_result.json").read_text())
            self.assertFalse(model["metrics"]["model_task_success"])
            self.assertEqual(model["status"], "pass")
            self.assertAlmostEqual(model["metrics"]["predicted_position_error_m"], BASELINE["predicted_position_error_m"], places=12)
            self.assertAlmostEqual(simulation["metrics"]["position_error_m"], BASELINE["position_error_m"], places=12)
            summary = json.loads((run.path / "diagnostic_summary.json").read_text())
            self.assertEqual(summary['task_gate'], 'FAIL')
            self.assertEqual(summary['failure_attribution'], 'UNKNOWN')
            diagnostics = summary['diagnostics']
            for result in diagnostics.values():
                self.assertEqual(result['metrics']['evidence_status'], 'available', result)
                self.assertTrue((run.path / (result['tool'] + '.json')).is_file())
                for evidence_path in result['artifacts']['evidence_paths']:
                    self.assertTrue((run.path / evidence_path).is_file())
            comparison = diagnostics['compare_model_sim']['metrics']
            self.assertAlmostEqual(comparison['tip_discrepancy_m'], math.dist(model['metrics']['predicted_tip_m'], simulation['metrics']['tip_position_m']))
            self.assertTrue(comparison['model_predicts_tolerance_failure'])
            self.assertIsNone(comparison['mismatch_criterion'])
            provenance = json.loads((run.path / 'provenance.json').read_text())
            self.assertEqual(provenance['parameters']['tendon_target_lengths_m']['value'], model['metrics']['tendon_target_lengths_m'])
            self.assertIn('body_mass', provenance['compiled_engine_parameters'])
            for name, expected in run.record.artifact_hashes.items():
                self.assertEqual(file_hash(run.path / name), expected)
            with zipfile.ZipFile(run.path / "source_snapshot.zip") as archive:
                for name, expected in run.record.source_hashes.items():
                    self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), expected)
            self.assertIsNotNone(run.record.matlab_version)
            trace = json.loads((run.path / "trace.json").read_text())
            gates = {event["gate"]: event["status"] for event in trace}
            self.assertEqual(gates["physics_sanity_gate"], "pass")
            self.assertEqual(gates["task_metric_gate"], "fail")


if __name__ == "__main__":
    unittest.main()
