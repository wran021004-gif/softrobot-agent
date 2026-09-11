import copy
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import tempfile
import unittest
import yaml
from capabilities.registry import get_skill_registry
from schemas.skill import Skill, SkillStatus, SkillValidationRecord
from schemas.finding import CandidateFinding
from schemas.memory import MemoryRecord
from skills.registry import SkillRegistry
from tools.artifact_tools import create_run, finalize_run, file_hash
from tools.evidence import EvidenceStore
from tools.finding_tools import extract_diagnostic_finding, validate_finding
from tools.harness import run_reach
from tools.skill_policy import validate_skill, skill_content_hash, strategy_hash
from tools.spec_tools import ROOT
from tests.test_trace import FixtureMatlab

NOW = datetime(2026, 9, 11, tzinfo=timezone.utc)


class SkillTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / "runs")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run_root = self.root / "evidence"
        self.runs = []
        for success in (True, False):
            run = create_run(self.run_root)
            run.save("task.yaml", {"task_type": "reach"})
            run.save("design_input.yaml", {"robot_family": "tendon_driven_continuum"})
            run.save("check_tendon_tracking.json", {"tool": "check_tendon_tracking", "status": "pass",
                "metrics": {"max_absolute_error_m": 0.006, "evidence_status": "available"}})
            run.update(random_seed=0)
            self.runs.append(run)
        from schemas.evidence import ArtifactReference
        self.ref = ArtifactReference(run_id=self.runs[0].record.run_id, path="check_tendon_tracking.json",
                                     sha256=file_hash(self.runs[0].path / "check_tendon_tracking.json"))
        self.data = yaml.safe_load((ROOT / "tests/fixtures/skill_candidate.yaml").read_text(encoding="utf-8"))
        self.data["evidence"] = [self.ref.model_dump(mode="json")]
        self.data["provenance"].update(source_runs=[self.ref.run_id], supporting_evidence=[self.ref.model_dump(mode="json")])
        self.strategy_digest = strategy_hash(self.data)
        for i, run in enumerate(self.runs):
            run.save("validation.json", {"skill_ref": "fixture_tracking_inspection@1", "strategy_sha256": self.strategy_digest,
                                         "run_id": run.record.run_id, "worked": i == 0, "summary": "Synthetic experiment fixture only"})
            finalize_run(run, "PASS" if i == 0 else "TASK_FAILED", None if i == 0 else "TASK_FAILED")
        self.registry = SkillRegistry(self.root / "library", self.run_root)

    def validation(self, passed=True, index=1):
        run = self.runs[0 if passed else 1]
        ref = EvidenceStore(self.run_root).reference(run.record.run_id, "validation.json")
        return SkillValidationRecord(validation_id=f"validation_{index}", method="deterministic",
            skill_ref="fixture_tracking_inspection@1", strategy_sha256=self.strategy_digest,
            outcome="passed" if passed else "failed", validated_runs=(run.record.run_id,) if passed else (),
            failed_validation_runs=() if passed else (run.record.run_id,), task_coverage=("reach",),
            robot_coverage=("tendon_driven_continuum",), seed_coverage=(0,), evidence_refs=(ref,),
            validated_by="harness", validated_at=NOW + timedelta(minutes=index), summary="Synthetic fixture check only")

    def approve(self, data=None):
        skill = self.registry.propose(data or self.data)
        skill = self.registry.record_validation(skill.reference, self.validation())
        return self.registry.approve(skill.reference, {"actor": "human", "approved_by": "fixture_human",
            "approved_at": NOW + timedelta(hours=1), "content_sha256": skill_content_hash(skill),
            "rationale": "Fixture lifecycle test only"}, actor="human")

    def test_valid_candidate_and_invalid_schema(self):
        skill = validate_skill(self.data, self.run_root)
        self.assertEqual(Skill.model_validate_json(skill.model_dump_json()), skill)
        for update in ({"status": "invented"}, {"category": "FREE_FORM"}, {"version": 0}, {"version": True},
                       {"evidence": []}, {"task_success": True}, {"causal_claim": "PCC is unsuitable"},
                       {"authority": "override_gate"}, {"changed_files": ["tasks/reach_free/task.yaml"]}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                validate_skill({**self.data, **update}, self.run_root)

    def test_unknown_and_planned_tools_rejected(self):
        for name in ("not_a_tool", "optimize_design"):
            data = copy.deepcopy(self.data)
            data["required_tools"] = [name]
            data["strategy"][0]["tool"] = name
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "Unknown tool|PLANNED"):
                validate_skill(data, self.run_root)

    def test_invalid_family_and_undeclared_strategy_tool(self):
        data = copy.deepcopy(self.data)
        data["applicability"]["robot_families"] = ["invented"]
        with self.assertRaisesRegex(ValueError, "robot family"):
            validate_skill(data, self.run_root)
        data = copy.deepcopy(self.data)
        data["strategy"][0]["tool"] = "inspect_numerics"
        with self.assertRaisesRegex(ValueError, "required_tools"):
            validate_skill(data, self.run_root)

    def test_nonexistent_run_missing_and_tampered_evidence(self):
        data = copy.deepcopy(self.data)
        data["provenance"]["source_runs"] = ["missing"]
        with self.assertRaisesRegex(ValueError, "Nonexistent run"):
            validate_skill(data, self.run_root)
        for update in ({"path": "missing.json"}, {"sha256": "0" * 64}, {"sha256": None},
                       {"path": "../outside.json"}, {"pointer": "/metrics/not_real"}):
            data = copy.deepcopy(self.data)
            data["evidence"][0].update(update)
            with self.subTest(update=update), self.assertRaises(ValueError):
                validate_skill(data, self.run_root)
        (self.runs[0].path / self.ref.path).write_text("{}")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_skill(self.data, self.run_root)

    def test_human_owned_mutations_gate_override_and_physics(self):
        for instruction in ("modify tasks/reach_free/task.yaml", "override task gate", "change task tolerance",
                            "write physics_contracts/new.yaml", "set task_success true"):
            data = copy.deepcopy(self.data)
            data["strategy"][0]["instruction"] = instruction
            with self.subTest(instruction=instruction), self.assertRaises(ValueError):
                validate_skill(data, self.run_root)
        with self.assertRaisesRegex(ValueError, "PHYSICS_ASSUMPTION_REQUIRED"):
            validate_skill({**self.data, "requires_new_physics": True}, self.run_root)
        data = copy.deepcopy(self.data)
        data["strategy"][0]["execution_result"] = "repair succeeded"
        with self.assertRaises(ValueError):
            validate_skill(data, self.run_root)

    def test_metric_must_exist_and_belong_to_tool(self):
        data = copy.deepcopy(self.data)
        data["trigger_signature"]["metrics"] = [{"tool": "check_tendon_tracking", "metric": "max_absolute_error_m",
            "operator": "gt", "value": 0, "evidence": {**self.ref.model_dump(), "pointer": "/metrics/max_absolute_error_m"}}]
        validate_skill(data, self.run_root)
        data["trigger_signature"]["metrics"][0]["metric"] = "fabricated"
        data["trigger_signature"]["metrics"][0]["evidence"]["pointer"] = "/metrics/fabricated"
        with self.assertRaises(ValueError):
            validate_skill(data, self.run_root)

    def test_approval_requires_validation_and_human(self):
        skill = self.registry.propose(self.data)
        with self.assertRaises(ValueError):
            validate_skill({**self.data, "status": "approved"}, self.run_root)
        with self.assertRaises(PermissionError):
            self.registry.approve(skill.reference, {}, actor="skill_system")
        with self.assertRaisesRegex(ValueError, "validated status"):
            self.registry.approve(skill.reference, {}, actor="human")
        skill = self.registry.record_validation(skill.reference, self.validation())
        with self.assertRaisesRegex(ValueError, "Human approval"):
            validate_skill(skill.model_copy(update={"status": SkillStatus.APPROVED}), self.run_root)
        with self.assertRaises(ValueError):
            self.registry.propose(skill.model_copy(update={"status": SkillStatus.APPROVED}))

    def test_negative_validation_preserved_and_coverage_verified(self):
        skill = self.registry.propose(self.data)
        negative = self.validation(False)
        skill = self.registry.record_validation(skill.reference, negative)
        self.assertEqual(skill.status, "candidate")
        skill = self.registry.record_validation(skill.reference, self.validation(True, 2))
        self.assertEqual(skill.validation[0].failed_validation_runs, (self.runs[1].record.run_id,))
        self.assertEqual(self.registry.get(skill.reference).validation, skill.validation)
        with self.assertRaisesRegex(ValueError, "append-only"):
            self.registry._append(skill.model_copy(update={"validation": skill.validation[1:]}))
        bad = self.validation(True, 3).model_copy(update={"seed_coverage": (999,)})
        with self.assertRaisesRegex(ValueError, "coverage"):
            self.registry.record_validation(skill.reference, bad)

    def test_validation_cannot_borrow_other_strategy_or_relabel_failure(self):
        skill = self.registry.propose(self.data)
        for update in ({"skill_ref": "other@1"}, {"strategy_sha256": "0" * 64}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                self.registry.record_validation(skill.reference, self.validation().model_copy(update=update))
        negative = self.validation(False)
        forged = negative.model_copy(update={"outcome": "passed", "validated_runs": negative.failed_validation_runs,
                                            "failed_validation_runs": ()})
        with self.assertRaisesRegex(ValueError, "contradicts"):
            self.registry.record_validation(skill.reference, forged)

    def test_retrieval_ranking_and_candidate_opt_in(self):
        first = self.registry.propose(self.data)
        data = copy.deepcopy(self.data)
        data.update(version=2, supersedes=first.reference)
        newer = self.registry.propose(data)
        self.assertEqual(self.registry.retrieve_skills(include_candidates=True), [newer, first])
        validated = self.registry.record_validation(first.reference, self.validation())
        self.assertEqual(self.registry.retrieve_skills(include_candidates=True), [validated, newer])
        self.assertEqual(self.registry.retrieve_skills(), [])

    def test_version_history_and_approval_content_binding(self):
        skill = self.approve()
        with self.assertRaisesRegex(ValueError, "content"):
            validate_skill(skill.model_copy(update={"description": "changed"}), self.run_root)
        data = copy.deepcopy(self.data)
        data["strategy"][0]["instruction"] = "Inspect tracking again."
        with self.assertRaises(ValueError):
            self.registry.propose(data)
        data.update(version=2, supersedes=skill.reference)
        second = self.registry.propose(data)
        self.assertEqual(second.reference, skill.skill_id + "@2")
        self.registry.retire(skill.reference, actor="human", replacement=second.reference)
        self.assertEqual(self.registry.get(skill.reference).status, "deprecated")
        self.assertEqual(self.registry.retrieve_skills(), [])
        self.assertTrue(list((self.registry.root / "approved").glob("*.yaml")))
        self.assertEqual(len(self.registry.history()[skill.reference]), 4)

    def test_retrieval_approved_only_exact_and_no_match(self):
        skill = self.registry.propose(self.data)
        self.assertEqual(self.registry.retrieve_skills(), [])
        self.assertEqual(self.registry.retrieve_skills(status="candidate"), [])
        self.assertEqual(self.registry.retrieve_skills(include_candidates=True), [skill])
        # A separate version starts as a fixture candidate; the first is admitted by an explicit Human fixture call.
        skill = self.registry.record_validation(skill.reference, self.validation())
        skill = self.registry.approve(skill.reference, {"actor": "human", "approved_by": "fixture",
            "approved_at": NOW + timedelta(hours=1), "content_sha256": skill_content_hash(skill),
            "rationale": "Test only"}, actor="human")
        exact = dict(robot_family="tendon_driven_continuum", task_type="reach", failure_category="TASK_FAILED",
                     model_level="M1", control_level="C1", required_tools=("check_tendon_tracking",), skill_category="DIAGNOSIS")
        self.assertEqual(self.registry.retrieve_skills(**exact), [skill])
        for key, value in (("robot_family", "other"), ("task_type", "other"), ("failure_category", "CONTROL_FAILURE"),
                           ("model_level", "M2"), ("control_level", "C2"), ("skill_category", "DESIGN"),
                           ("required_tools", ("inspect_numerics",))):
            with self.subTest(filter=key):
                self.assertEqual(self.registry.retrieve_skills(**{**exact, key: value}), [])

    def test_production_registry_empty_catalog_connected(self):
        self.assertEqual(get_skill_registry().root, ROOT / "skills")
        self.assertEqual(get_skill_registry().retrieve_skills(), [])
        self.assertEqual(get_skill_registry().current(), [])

    def test_wrong_directory_and_missing_revision_rejected(self):
        skill = self.registry.propose(self.data)
        file = next((self.registry.root / "candidates").glob("*.yaml"))
        file.rename(file.with_name(f"{skill.reference}.r2.yaml"))
        with self.assertRaises(ValueError):
            self.registry.retrieve_skills()

    def test_exported_schemas_match_authoritative_contracts(self):
        from tools.export_contract_schemas import CONTRACTS
        for name, contract in CONTRACTS.items():
            with self.subTest(schema=name):
                self.assertEqual(json.loads((ROOT / name).read_text(encoding="utf-8")), contract.model_json_schema())


class FindingTests(unittest.TestCase):
    def test_canonical_finding_is_observation_only(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as tmp:
            run = run_reach(run_root=tmp, matlab_factory=FixtureMatlab)
            finding = extract_diagnostic_finding(run.record.run_id, tmp)
            self.assertIsNotNone(finding)
            self.assertEqual(finding.created_by, "harness")
            self.assertEqual(finding.causal_attribution, "UNKNOWN")
            self.assertEqual(len(finding.observation), 5)
            self.assertEqual(len(finding.ruled_out), 2)
            validate_finding(finding, tmp)
            data = finding.model_dump(mode="json")
            data["observation"][0]["value"] = False
            with self.assertRaisesRegex(ValueError, "contradicts"):
                validate_finding(data, tmp)
            with self.assertRaises(ValueError):
                CandidateFinding.model_validate({**finding.model_dump(), "causal_attribution": "MODEL_MISMATCH"})
            memory = MemoryRecord(run_id=run.record.run_id, summary="Recorded TASK_FAILED", searchable_metadata={"task": "reach"},
                                  evidence_refs=finding.evidence_refs)
            self.assertEqual(MemoryRecord.model_validate_json(memory.model_dump_json()), memory)
            with self.assertRaises(ValueError):
                MemoryRecord.model_validate({**memory.model_dump(), "full_trace": []})

    def test_unavailable_finding_is_not_fabricated(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as tmp:
            run = create_run(tmp)
            finalize_run(run, "ERROR")
            self.assertIsNone(extract_diagnostic_finding(run.record.run_id, tmp))
