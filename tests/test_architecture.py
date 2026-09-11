import copy
import importlib
import json
import math
from pathlib import Path
import tempfile
import unittest
import warnings
import xml.etree.ElementTree as ET
import yaml
from pydantic import ValidationError
from agents.contracts.permissions import can_write, require_write_permission, HUMAN_OWNED
from agents.contracts.outputs import DiagnosisOutput
from capabilities.registry import get_robot_family_grammar, get_tool_manifest, list_tool_bundles
from controllers.open_loop_length import OpenLoopLength, plan_open_loop
from metrics.reach import evaluate_reach
from schemas.control_spec import ControlCommand, ControlSpec
from schemas.failure_taxonomy import failure_category
from schemas.robot_ir import RobotIR
from schemas.task_spec import TaskSpec
from tools.artifact_tools import create_run, save_tool_result, finalize_run, file_hash
from tools.capability_resolver import resolve_capability
from tools.design_compiler import build_robot_ir, ensure_robot_ir
from tools.harness import run_reach
from tools.mujoco_tools import compile_mujoco, run_task, validate_task
from tools.spec_tools import (ROOT, load_yaml, load_task, load_task_package, load_environment, validate_environment,
                              validate_design, environment_xml, validate_frozen_environment, load_simulator)
from schemas.tool_result import ToolResult

BASELINE = json.loads((ROOT / "tests/fixtures/legacy_v1.json").read_text())


def design(**updates):
    return validate_design({**load_yaml(ROOT / "configs/design_tendon_arm.yaml"), **updates})


class SpecTests(unittest.TestCase):
    def test_task_loading(self):
        task, env = load_task_package()
        self.assertEqual(task.target_m, [0.25, 0, 0.15])
        self.assertEqual(task.position_error_max_m, 0.01)
        self.assertEqual(task.environment_id, env.environment_id)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            self.assertEqual(load_task(ROOT / "configs/task_reach.yaml"), task)
            self.assertTrue(any(issubclass(w.category, DeprecationWarning) for w in caught))

    def test_environment_validation(self):
        value = load_environment().model_dump(mode="json")
        for update in ({"units": "mm"}, {"gravity_m_s2": [0, 0, float("nan")]}, {"timestep_s": 0.1},
                       {"coordinate_frame": "unknown"}, {"objects": [value["objects"][0]] * 2}):
            with self.subTest(update=update), self.assertRaises(ValidationError):
                validate_environment({**value, **update})

    def test_reserved_environment_is_not_executable(self):
        value = load_environment().model_dump(mode="json")
        value["objects"].append({"kind": "ball", "name": "ball", "position_m": [0, 0, 1]})
        with self.assertRaisesRegex(ValueError, "IMPLEMENTATION_REQUIRED"):
            environment_xml(validate_environment(value))

    def test_frozen_environment_consistency(self):
        env = load_environment()
        validate_frozen_environment(env, ROOT / "tasks/reach_free/mujoco.xml")
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as tmp:
            path = Path(tmp) / "mujoco.xml"
            text = (ROOT / "tasks/reach_free/mujoco.xml").read_text().replace("-0.02", "-0.03")
            path.write_text(text)
            before = file_hash(path)
            with self.assertRaisesRegex(ValueError, "differs"):
                validate_frozen_environment(env, path)
            self.assertEqual(file_hash(path), before)

    def test_legacy_environment_matches(self):
        legacy = ET.parse(ROOT / "mujoco/environments/reach_free.xml").getroot()
        timestep = float(legacy.find("option").attrib.pop("timestep"))
        self.assertEqual(timestep, load_simulator().timestep_s)
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as tmp:
            path = Path(tmp) / "environment.xml"
            ET.ElementTree(legacy).write(path)
            validate_frozen_environment(load_environment(), path)

    def test_invalid_design_and_task_inputs(self):
        for update in ({"segments": 0}, {"tendon_count": True}, {"sections": 1.5}, {"total_length_m": float("inf")}, {"unknown_physics": 1}):
            with self.subTest(update=update), self.assertRaises(ValidationError):
                design(**update)
        for update in ({"target_m": [float("nan"), 0, 0]}, {"position_error_max_m": -1}, {"environment_id": "../../escape"}):
            with self.subTest(update=update), self.assertRaises(ValidationError):
                TaskSpec.model_validate({**load_task().model_dump(), **update})


class IRTests(unittest.TestCase):
    def test_design_to_robot_ir(self):
        ir = build_robot_ir(design())
        self.assertEqual(ir, build_robot_ir(design()))
        self.assertEqual(ir.section.segment_length_m, 0.05)
        self.assertEqual(ir.section.backbone_radius_m, None)
        self.assertEqual(ir.mechanics.joint_stiffness_nm_per_rad, 0.1)
        self.assertEqual(ir.mechanics.joint_damping_nm_s_per_rad, 0.1)
        self.assertEqual(ir.mechanics.body_density_kg_m3, 1000)
        self.assertEqual(ir.mechanics.tendon_servo_kp_n_per_m, 1000)
        self.assertEqual(ir.mechanics.tendon_force_limit_n, 20)
        self.assertFalse(ir.mechanics.validated)

    def test_robot_ir_serialization(self):
        ir = build_robot_ir(design())
        restored = RobotIR.model_validate(yaml.safe_load(yaml.safe_dump(ir.model_dump(mode="json"))))
        self.assertEqual(ir, restored)
        self.assertEqual(ir, RobotIR.model_validate_json(ir.model_dump_json()))

    def test_tendon_order_contract(self):
        for count in (1, 3, 4, 6):
            ir = build_robot_ir(design(tendon_count=count))
            for i, route in enumerate(ir.tendon_routes):
                self.assertEqual(route.index, i)
                self.assertAlmostEqual(route.angle_rad, 2 * math.pi * i / count)
                self.assertAlmostEqual(math.hypot(*route.offset_yz_m), 0.015)
        ir = build_robot_ir(design()).model_dump(mode="json")
        ir["tendon_routes"].reverse()
        with self.assertRaises(ValidationError):
            RobotIR.model_validate(ir)

    def test_unapproved_ir_mechanics_rejected(self):
        value = build_robot_ir(design()).model_dump(mode="json")
        value["mechanics"]["joint_stiffness_nm_per_rad"] = 0.01
        with self.assertRaisesRegex(ValueError, "PHYSICS_ASSUMPTION_REQUIRED"):
            ensure_robot_ir(RobotIR.model_validate(value))


class CapabilityTests(unittest.TestCase):
    def test_capability_resolution(self):
        self.assertEqual(resolve_capability(design()).state, "SUPPORTED")
        self.assertEqual(resolve_capability(design(segments=6, tendon_count=3)).state, "PARAMETRICALLY_SUPPORTED")
        self.assertEqual(resolve_capability(design(robot_family="other")).state, "OUT_OF_GRAMMAR")
        self.assertEqual(resolve_capability(design(sections=2)).state, "OUT_OF_GRAMMAR")
        self.assertEqual(resolve_capability(design(), ["optimize_design"]).state, "IMPLEMENTATION_REQUIRED")
        self.assertEqual(resolve_capability(design(), ["missing_tool"]).state, "IMPLEMENTATION_REQUIRED")
        self.assertEqual(resolve_capability(design(), physics_profile="new_stiffness_law").state, "PHYSICS_ASSUMPTION_REQUIRED")
        self.assertEqual(resolve_capability(design(), model_level="M2").state, "IMPLEMENTATION_REQUIRED")
        self.assertEqual(resolve_capability(design(), control_level="C3").state, "IMPLEMENTATION_REQUIRED")
        grammar = copy.deepcopy(get_robot_family_grammar("tendon_driven_continuum"))
        grammar["design_fields"]["sections"]["allowed_values"] = [1, 2]
        self.assertEqual(resolve_capability(design(sections=2), grammar=grammar).state, "IMPLEMENTATION_REQUIRED")

    def test_manifest_contracts_and_real_entry_points(self):
        required = {"implementation_status", "inputs", "outputs", "supported_robot_families", "fidelity", "assumptions",
                    "applicable_when", "limitations", "failure_codes", "cost", "fields_consumed", "artifacts", "physics_contract_dependencies"}
        for bundle in list_tool_bundles():
            for name, entry in get_tool_manifest(bundle)["tools"].items():
                with self.subTest(bundle=bundle, tool=name):
                    self.assertFalse(required - entry.keys())
                    if entry["implementation_status"] == "PLANNED":
                        self.assertNotIn("implementation", entry)
                    else:
                        impl = entry["implementation"]
                        obj = importlib.import_module(impl["module"])
                        for part in impl["callable"].split("."):
                            obj = getattr(obj, part)
                        self.assertTrue(callable(obj))
        self.assertEqual(get_tool_manifest("matlab_analysis"), get_tool_manifest("model"))

    def test_failure_taxonomy_compatibility(self):
        self.assertEqual(failure_category("PHYSICS_ERROR"), "SIMULATION_ERROR")
        self.assertEqual(failure_category("NONFINITE_STATE"), "NUMERICAL_FAILURE")
        self.assertEqual(failure_category("TASK_FAILED"), "TASK_FAILED")
        self.assertEqual(failure_category("unexpected"), "UNKNOWN")
        self.assertIsNone(failure_category(None))


class MuJoCoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / "runs")
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "robot.xml"
        self.task, self.env = load_task_package()
        self.ir = build_robot_ir(design())
        self.assertEqual(compile_mujoco(self.ir, self.task, self.path, self.env).status, "pass")

    def test_mujoco_compile(self):
        import mujoco
        model = mujoco.MjModel.from_xml_path(str(self.path))
        self.assertEqual((model.nq, model.nv, model.nu, model.ntendon), (16, 16, 4, 4))
        self.assertEqual(model.opt.timestep, 0.002)
        self.assertEqual(model.opt.gravity.tolist(), [0, 0, -9.81])
        self.assertEqual(model.geom_pos[model.geom("floor").id].tolist(), [0, 0, -0.02])
        self.assertEqual(model.actuator_forcerange.tolist(), [[-20, 0]] * 4)
        data = mujoco.MjData(model)
        mujoco.mj_forward(model, data)
        for actual, expected in zip(data.site_xpos[model.site("tip_site").id], [0.4, 0, 0]):
            self.assertAlmostEqual(actual, expected)
        before = self.path.read_bytes()
        compile_mujoco(self.ir, self.task, self.path, self.env)
        self.assertEqual(before, self.path.read_bytes())

    def test_parametric_compile_routing(self):
        import mujoco
        for count in (1, 3, 6):
            ir = build_robot_ir(design(tendon_count=count, segments=5))
            compile_mujoco(ir, self.task, self.path, self.env)
            model = mujoco.MjModel.from_xml_path(str(self.path))
            self.assertEqual(model.nu, count)
            self.assertEqual(model.nq, 10)
            for i, route in enumerate(ir.tendon_routes):
                self.assertEqual(model.actuator_trnid[i, 0], i)
                self.assertEqual(model.site_pos[model.site(f"tendon_{i}_base").id].tolist(), [0, *route.offset_yz_m])

    def test_current_reach_pipeline_smoke(self):
        # Recorded real pre-migration MATLAB commands; real MuJoCo regression, no mock physics.
        result = validate_task(self.path, self.task, BASELINE["tendon_target_lengths_m"])
        self.assertEqual(result.failure_code, "TASK_FAILED")
        self.assertAlmostEqual(result.metrics["position_error_m"], BASELINE["position_error_m"], places=12)
        self.assertFalse(result.metrics["task_success"])
        for actual, expected in zip(result.metrics["final_tendon_lengths_m"], BASELINE["final_tendon_lengths_m"]):
            self.assertAlmostEqual(actual, expected, places=12)

    def test_controller_abstraction_and_passive_execution(self):
        class AlternatingController:
            spec = ControlSpec(controller="test_schedule", level="C1", command_source="test protocol exercise")
            calls = 0
            def command(self, time_s, observation):
                self.calls += 1
                assert len(observation["qpos"]) == 16
                return ControlCommand(tendon_target_lengths_m=(0.4,) * 4) if self.calls > 500 else None
        controller = AlternatingController()
        result = run_task(self.path, self.task, controller)
        self.assertEqual(controller.calls, 1000)
        self.assertIn("task_success", result.metrics)
        passive = validate_task(self.path, self.task)
        self.assertIn("task_success", passive.metrics)
        self.assertNotIn("tendon_target_lengths_m", passive.metrics)

    def test_invalid_commands_and_missing_model(self):
        for lengths in ([0.4], [0, 0.4, 0.4, 0.4], [float("nan")] * 4, 1.0):
            with self.subTest(lengths=lengths):
                self.assertEqual(validate_task(self.path, self.task, lengths).failure_code, "INVALID_TENDON_COMMAND")
        self.assertEqual(validate_task(self.path.with_name("missing.xml"), self.task).failure_code, "PHYSICS_ERROR")

    def test_task_gate_uses_task_not_marker(self):
        tree = ET.parse(self.path)
        tree.find(".//site[@name='target_site']").set("pos", "0.3844450937959572 0 0.04407156345517224")
        tree.write(self.path)
        result = validate_task(self.path, self.task, BASELINE["tendon_target_lengths_m"])
        self.assertEqual(result.failure_code, "TASK_FAILED")
        self.assertAlmostEqual(result.metrics["position_error_m"], BASELINE["position_error_m"], places=12)

    def test_open_loop_contract(self):
        result = plan_open_loop(BASELINE["tendon_target_lengths_m"])
        controller = OpenLoopLength(result.command.tendon_target_lengths_m)
        self.assertEqual(controller.command(0, {}), controller.command(100, {}))
        self.assertEqual(result.spec.level, "C1")

    def test_canonical_metric_boundary_and_unknown_task(self):
        # Synthetic metric unit case; official benchmark files are untouched.
        task = TaskSpec(task_id="metric_unit", task_type="reach", environment_id="reach_free",
                        target_m=[0, 0, 0], position_error_max_m=0.01)
        self.assertTrue(evaluate_reach([0.01, 0, 0], task)["task_success"])
        self.assertFalse(evaluate_reach([0.010001, 0, 0], task)["task_success"])
        unknown = TaskSpec.model_validate({**self.task.model_dump(), "task_type": "catch"})
        self.assertEqual(run_task(self.path, unknown).failure_code, "CAPABILITY_MISSING")

    def test_controller_failure_retains_execution_evidence(self):
        class BrokenController:
            def command(self, time_s, observation):
                raise RuntimeError("test controller error")
        result = run_task(self.path, self.task, BrokenController())
        self.assertEqual(result.failure_code, "CONTROL_FAILURE")
        self.assertEqual(result.metrics["steps_completed"], 0)
        self.assertNotIn("task_success", result.metrics)


class ArtifactPermissionTests(unittest.TestCase):
    def test_run_artifact_creation(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as tmp:
            run = create_run(tmp)
            other = create_run(tmp)
            self.assertNotEqual(run.path, other.path)
            result = ToolResult(status="fail", tool="example", failure_code="TASK_FAILED", metrics={"task_success": False})
            save_tool_result(run, "result.json", result)
            record = finalize_run(run, "TASK_FAILED", result.failure_code)
            self.assertEqual(record.artifact_hashes["result.json"], file_hash(run.path / "result.json"))
            self.assertEqual(json.loads((run.path / "run.json").read_text())["final_status"], "TASK_FAILED")
            with self.assertRaises(ValueError):
                run.save("../escape.json", {})

    def test_runtime_failure_is_recorded_without_fake_model_data(self):
        def unavailable():
            raise RuntimeError("MATLAB unavailable for explicit failure-path test")
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as tmp:
            run = run_reach(run_root=tmp, matlab_factory=unavailable)
            self.assertEqual(run.record.final_status, "ERROR")
            self.assertTrue((run.path / "error.json").is_file())
            self.assertFalse((run.path / "model_result.json").exists())
            self.assertTrue((run.path / "source_snapshot.zip").is_file())
            self.assertEqual(run.record.task_hash, file_hash(run.path / "task.yaml"))

    def test_invalid_input_run_is_finalized(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as tmp:
            path = Path(tmp) / "invalid.yaml"
            path.write_text("segments: -1")
            run = run_reach(design_path=path, run_root=Path(tmp) / "runs")
            self.assertEqual(run.record.failure_code, "INVALID_SPEC")
            self.assertNotEqual(run.record.final_status, "RUNNING")
            self.assertFalse((run.path / "robot_ir.yaml").exists())

    def test_agent_permission_contracts(self):
        for role in ("engineer", "coding", "diagnosis", "unknown"):
            for folder in HUMAN_OWNED:
                self.assertFalse(can_write(role, folder + "/truth.yaml"))
            self.assertFalse(can_write(role, "runs/run/metrics.json"))
            self.assertFalse(can_write(role, "../escape.py"))
        self.assertTrue(can_write("coding", "tools/new_adapter.py"))
        self.assertTrue(can_write("engineer", "proposals/engineer/candidate.yaml"))
        self.assertFalse(can_write("coding", "tools/../tasks/reach_free/task.yaml"))
        self.assertFalse(can_write("coding", "TASKS/reach_free/task.yaml"))
        with self.assertRaises(PermissionError):
            require_write_permission("coding", "benchmarks/tendon_v1.yaml")
        with self.assertRaises(ValidationError):
            DiagnosisOutput(failure_hypotheses=(), diagnostic_tests=(), failure_attribution="UNKNOWN", recommended_repair_target="none", task_success=True)


if __name__ == "__main__":
    unittest.main()
