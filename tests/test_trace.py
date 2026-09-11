import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from schemas.trace import TraceEvent, DecisionRecord
from schemas.tool_result import ToolResult
from tools.artifact_tools import create_run, finalize_run, file_hash
from tools.trace_tools import read_trace, validate_trace
from tools.harness import run_reach
from tools.spec_tools import ROOT
from tests.test_architecture import BASELINE


class FixtureMatlab:
    """Explicit M0/M1 test double; real MATLAB is tested separately."""
    def version(self):
        return "TEST_FIXTURE"

    def analyze_workspace(self, *args):
        return ToolResult(tool="analyze_workspace", status="pass", metrics={"target_reachable": True})

    def plan_pcc_reach(self, ir, task, environment):
        return ToolResult(tool="plan_pcc_reach", status="pass", metrics={
            "predicted_tip_m": [0.4 * math.sin(BASELINE["theta_rad"]) / BASELINE["theta_rad"],
                                0.4 * (1 - math.cos(BASELINE["theta_rad"])) / BASELINE["theta_rad"] * math.cos(BASELINE["phi_rad"]),
                                0.4 * (1 - math.cos(BASELINE["theta_rad"])) / BASELINE["theta_rad"] * math.sin(BASELINE["phi_rad"])],
            "target_position_m": list(task.target_m),
            "predicted_position_error_m": BASELINE["predicted_position_error_m"],
            "model_task_success": False, "tendon_target_lengths_m": BASELINE["tendon_target_lengths_m"]})

    def close(self):
        pass


def assert_canonical_trace(test, run):
    events = read_trace(run.path / "trace.jsonl")
    test.assertEqual(events[0].event_type, "RUN_STARTED")
    test.assertEqual(events[-1].event_type, "RUN_FINISHED")
    test.assertTrue(all(e.actor in ("tool", "harness", "gate") for e in events))
    test.assertFalse(any(e.event_type in ("SKILL_PROPOSED", "SKILL_RETRIEVED", "REPAIR_APPLIED", "DECISION_RECORDED") for e in events))
    operations = {e.operation for e in events}
    test.assertTrue({"task_loaded", "environment_validated", "design_loaded", "robot_ir_built",
                     "resolve_capability", "open_loop_length"}.issubset(operations))
    starts = {e.event_id: e for e in events if e.event_type in ("STAGE_STARTED", "TOOL_STARTED", "DIAGNOSTIC_STARTED")}
    for name, stage in (("analyze_workspace", "model"), ("plan_pcc_reach", "model"),
                        ("compile_mujoco", "mujoco"), ("run_task", "mujoco"),
                        ("compare_model_sim", "diagnostics"), ("check_actuator_limits", "diagnostics"),
                        ("check_tendon_tracking", "diagnostics"), ("inspect_numerics", "diagnostics")):
        started = next(e for e in starts.values() if e.operation == name)
        test.assertEqual(starts[started.parent_event_id].operation, stage)
        finished = next(e for e in events if e.parent_event_id == started.event_id and e.event_type in
                        ("TOOL_FINISHED", "TOOL_FAILED", "DIAGNOSTIC_FINISHED"))
        test.assertTrue(started.inputs["artifacts"])
        test.assertTrue(finished.outputs["result"])
        test.assertTrue(finished.evidence_refs)
    gate = next(e for e in events if e.operation == "task_metric_gate" and e.gate)
    test.assertEqual(gate.gate.decision, "FAIL")
    test.assertEqual(gate.gate.threshold, 0.01)
    test.assertAlmostEqual(gate.gate.value, BASELINE["position_error_m"], places=12)
    test.assertIn("frozen TaskSpec", gate.gate.authority)
    test.assertEqual(file_hash(run.path / "trace.jsonl"), run.record.artifact_hashes["trace.jsonl"])
    test.assertLess(len(events), 150)
    return events


class TraceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / "runs")
        self.addCleanup(self.tmp.cleanup)
        self.run = create_run(self.tmp.name)

    def completed(self):
        with self.run.events.span("model"):
            self.run.invoke_tool("example", "result.json", lambda: ToolResult(tool="example", status="pass"))
        finalize_run(self.run, "PASS")
        return [e.model_dump(mode="json") for e in read_trace(self.run.path / "trace.jsonl")]

    def test_jsonl_roundtrip_unique_order_hash_and_seal(self):
        rows = self.completed()
        self.assertEqual(len({r["event_id"] for r in rows}), len(rows))
        self.assertEqual([r["sequence"] for r in rows], list(range(len(rows))))
        self.assertEqual(rows, [json.loads(line) for line in (self.run.path / "trace.jsonl").read_text().splitlines()])
        for name, expected in self.run.record.artifact_hashes.items():
            self.assertEqual(file_hash(self.run.path / name), expected)
        with self.assertRaises(ValueError):
            self.run.events.emit("RUN_STARTED", "run")
        with self.assertRaises(ValueError):
            self.run.save("new.json", {})

    def test_invalid_graphs_and_pairings(self):
        rows = self.completed()
        stage = next(i for i, r in enumerate(rows) if r["event_type"] == "STAGE_STARTED")
        finish = next(i for i, r in enumerate(rows) if r["event_type"] == "TOOL_FINISHED")
        for index, update in ((stage, {"event_id": rows[0]["event_id"]}), (stage, {"sequence": 999}),
                              (stage, {"parent_event_id": "missing"}), (stage, {"parent_event_id": rows[stage]["event_id"]}),
                              (stage, {"run_id": "other"}), (finish, {"operation": "different"}),
                              (finish, {"parent_event_id": rows[0]["event_id"]}), (finish, {"duration_s": None}),
                              (finish, {"timestamp": "2000-01-01T00:00:00Z"})):
            broken = copy.deepcopy(rows)
            broken[index].update(update)
            with self.subTest(update=update), self.assertRaises(ValueError):
                validate_trace(broken)
        with self.assertRaises(ValueError):
            validate_trace(rows[:-1])

    def test_invalid_schema_and_large_payload_rejected(self):
        row = self.run.events.events[0].model_dump(mode="json")
        for update in ({"event_type": "arbitrary"}, {"actor": "fake"}, {"status": "invented"},
                       {"private_chain_of_thought": "hidden"}, {"timestamp": "2026-01-01"},
                       {"summary": {"qpos": list(range(1000))}}, {"summary": {"xml": "x" * 2000}},
                       {"summary": {"x": float("nan")}}, {"duration_s": -1}, {"sequence": True},
                       {"event_type": "GATE_EVALUATED"}, {"event_type": "DECISION_RECORDED"},
                       {"summary": {"a": {"b": {"c": {"d": {"e": {"f": {"g": 1}}}}}}}}):
            with self.subTest(keys=list(update)), self.assertRaises(ValueError):
                TraceEvent.model_validate({**row, **update})

    def test_artifact_references_must_resolve(self):
        rows = self.completed()
        ref_row = next(row for row in rows if row["evidence_refs"])
        for path in ("missing.json", "../run.json", "C:/outside.json", "bad\\path", "aux.json"):
            bad = copy.deepcopy(rows)
            bad[ref_row["sequence"]]["evidence_refs"][0]["path"] = path
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_trace(bad, self.run.path)

    def test_artifact_pointer_and_hash_verified(self):
        rows = self.completed()
        i = next(i for i, row in enumerate(rows) if row["evidence_refs"])
        for update in ({"sha256": "0" * 64}, {"pointer": "/nonexistent"}, {"run_id": "different"}):
            bad = copy.deepcopy(rows)
            bad[i]["evidence_refs"][0].update(update)
            with self.subTest(update=update), self.assertRaises(ValueError):
                validate_trace(bad, self.run.path)

    def test_tool_exception_closes_spans_without_fake_result(self):
        with self.assertRaises(RuntimeError):
            with self.run.events.span("model"):
                self.run.invoke_tool("explode", "absent.json", lambda: (_ for _ in ()).throw(RuntimeError("test")))
        finalize_run(self.run, "ERROR", "UNKNOWN")
        events = read_trace(self.run.path / "trace.jsonl")
        self.assertTrue(any(e.event_type == "TOOL_FAILED" for e in events))
        self.assertFalse((self.run.path / "absent.json").exists())

    def test_decision_placeholder_is_bounded_and_not_generated(self):
        record = DecisionRecord(actor="diagnosis_agent", decision="request_diagnostics", rationale="Evidence is incomplete",
                                requested_tools=("inspect_numerics",), next_action="request_tool")
        self.assertEqual(DecisionRecord.model_validate_json(record.model_dump_json()), record)
        with self.assertRaises(ValueError):
            DecisionRecord.model_validate({**record.model_dump(), "reasoning_tokens": [1]})
        self.assertFalse(any(e.actor == "diagnosis_agent" for e in self.run.events.events))

    def test_rerun_requires_existing_finalized_run(self):
        finalize_run(self.run, "PASS")
        rerun = create_run(self.tmp.name, previous_run_id=self.run.record.run_id, relationship="rerun")
        finalize_run(rerun, "PASS")
        self.assertEqual(read_trace(rerun.path / "trace.jsonl")[0].metadata["previous_run_id"], self.run.record.run_id)
        with self.assertRaises(ValueError):
            create_run(self.tmp.name, previous_run_id="missing", relationship="repair")

    def test_pipeline_trace_completeness_and_numerics(self):
        run = run_reach(run_root=self.tmp.name, matlab_factory=FixtureMatlab)
        self.assertEqual(run.record.final_status, "TASK_FAILED")
        assert_canonical_trace(self, run)

    def test_pipeline_runtime_failure_and_unavailable_diagnostics(self):
        run = run_reach(run_root=self.tmp.name, matlab_factory=lambda: (_ for _ in ()).throw(RuntimeError("test startup")))
        self.assertEqual(run.record.final_status, "ERROR")
        events = read_trace(run.path / "trace.jsonl")
        self.assertTrue(any(e.operation == "matlab_session" and e.event_type == "TOOL_FAILED" for e in events))
        self.assertFalse((run.path / "model_result.json").exists())
        with patch("tools.diagnostic_tools.inspect_numerics", side_effect=RuntimeError("test diagnostic")) as diagnostic:
            diagnostic.__name__ = "inspect_numerics"
            run = run_reach(run_root=self.tmp.name, matlab_factory=FixtureMatlab)
        self.assertEqual(run.record.final_status, "TASK_FAILED")
        events = read_trace(run.path / "trace.jsonl")
        self.assertTrue(any(e.operation == "diagnostics" and e.status == "fail" for e in events))
