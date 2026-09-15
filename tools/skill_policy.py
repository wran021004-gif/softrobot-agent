"""Deterministic admission, checked against capabilities and hashed run evidence.

This validates structured contracts, not arbitrary natural-language scientific truth.
Human review and executor permission checks remain mandatory boundaries.
"""
import hashlib
import json
import re
from capabilities.registry import get_tool_manifest, list_tool_bundles, list_robot_families
from schemas.skill import Skill, SkillValidationEvidence
from schemas.finding import CandidateFinding
from tools.evidence import EvidenceStore
from tools.finding_tools import validate_finding

REQUIRED_CONSTRAINTS = {
    "do_not_modify_task_tolerance", "do_not_override_task_gate",
    "do_not_assume_model_mismatch_from_task_failure", "do_not_retune_surrogate_without_provenance",
    "do_not_bypass_agent_permissions",
}


def skill_content_hash(skill):
    data = Skill.model_validate(skill).model_dump(mode="json", exclude={"status", "human_approval", "deprecated_by"})
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def strategy_hash(skill):
    """Bind an experiment to the proposed strategy/scope, independent of later evidence."""
    fields = {"skill_id", "version", "trigger_signature", "when_to_apply", "when_not_to_apply", "applicability",
              "required_tools", "strategy", "negative_constraints", "requires_new_physics", "causal_claim", "authority"}
    data = Skill.model_validate(skill).model_dump(mode="json", include=fields)
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def validate_skill(skill, run_root, *, evidence_store=None, tool_manifests=None, robot_families=None):
    # Revalidate even model_copy/model_construct objects, which bypass Pydantic checks.
    skill = Skill.model_validate(skill.model_dump(mode="json") if isinstance(skill, Skill) else skill)
    if skill.requires_new_physics:
        raise ValueError("PHYSICS_ASSUMPTION_REQUIRED: proposal requires Human scientific review")
    if not REQUIRED_CONSTRAINTS.issubset(skill.negative_constraints):
        raise ValueError("Missing mandatory negative constraints")
    if set(skill.applicability.robot_families) - set(robot_families if robot_families is not None else list_robot_families()):
        raise ValueError("Unknown robot family")
    manifests = {}
    for bundle in list_tool_bundles():
        manifests.update(get_tool_manifest(bundle)["tools"])
    if tool_manifests is not None:
        manifests.update(tool_manifests)
    used_tools = set(skill.required_tools) | {s.tool for s in skill.strategy if s.tool} | {m.tool for m in skill.trigger_signature.metrics}
    if used_tools - set(skill.required_tools):
        raise ValueError("Strategy/trigger tools must be declared in required_tools")
    for name in used_tools:
        tool = manifests.get(name)
        if tool is None:
            raise ValueError(f"Unknown tool: {name}")
        if tool.get("implementation_status") != "IMPLEMENTED" or not tool.get("implementation"):
            raise ValueError(f"PLANNED or unavailable tool: {name}")
        if set(skill.applicability.robot_families) - set(tool.get("supported_robot_families", ())):
            raise ValueError(f"Tool {name} does not support applicability family")
    # Reject explicit mutation/override instructions in prose as well as forbidden
    # structured fields (extra=forbid). This is not a general language classifier.
    for step in skill.strategy:
        text = step.instruction.casefold().replace("\\", "/")
        if (re.search(r"\b(modify|write|edit|overwrite|delete|set|change)\b.{0,80}\b(tasks/|benchmarks/|physics_contracts/|schemas/|metrics/|capabilities/|configs/|agents/contracts/)", text)
                or re.search(r"\b(override|bypass|ignore|relax|increase|change|modify|set)\b.{0,40}\b(task gate|task_gate|task_success|task tolerance|task_tolerance|position_error_max_m)\b", text)):
            raise ValueError("Human-owned mutation or task gate override is forbidden")
    store = evidence_store or EvidenceStore(run_root)
    sources = set(skill.provenance.source_runs)
    for run_id in sources:
        store.run(run_id)
    refs = (*skill.evidence, *skill.provenance.supporting_evidence,
            *(r for s in skill.strategy for r in s.evidence_refs),
            *(m.evidence for m in skill.trigger_signature.metrics), *skill.provenance.source_findings)
    if sources - {r.run_id for r in refs}:
        raise ValueError("Every source run requires evidence")
    for ref in refs:
        if ref.run_id not in sources:
            raise ValueError("Evidence run absent from provenance")
        store.resolve(ref)
    for ref in skill.provenance.source_findings:
        if ref.pointer is not None:
            raise ValueError("Source finding must reference the full CandidateFinding artifact")
        finding = CandidateFinding.model_validate_json(store.resolve(ref))
        validate_finding(finding, run_root)
        if set(finding.source_runs) - sources:
            raise ValueError("Finding sources absent from skill provenance")
    for metric in skill.trigger_signature.metrics:
        if metric.evidence.pointer != "/metrics/" + metric.metric:
            raise ValueError("Metric must reference its exact ToolResult metrics field")
        raw_ref = metric.evidence.model_copy(update={"pointer": None})
        result = json.loads(store.resolve(raw_ref))
        if result.get("tool") != metric.tool:
            raise ValueError("Metric belongs to another tool")
        value = store.resolve(metric.evidence)
        if type(value) not in (bool, int, float):
            raise ValueError("Trigger metric must be scalar")
        if (type(value) is bool) != (type(metric.value) is bool):
            raise ValueError("Trigger metric type mismatch")
        if type(value) is bool and metric.operator != "eq":
            raise ValueError("Boolean trigger supports eq only")
    ids = set()
    previous_time = skill.provenance.created_at
    for validation in skill.validation:
        if validation.skill_ref != skill.reference or validation.strategy_sha256 != strategy_hash(skill):
            raise ValueError("Validation belongs to another skill version or strategy")
        if validation.validation_id in ids or validation.validated_at < previous_time:
            raise ValueError("Duplicate validation ID or unordered validation timestamps")
        ids.add(validation.validation_id)
        previous_time = validation.validated_at
        runs = set(validation.validated_runs) | set(validation.failed_validation_runs)
        if runs != {r.run_id for r in validation.evidence_refs}:
            raise ValueError("Every validation run, including failures, requires evidence")
        for ref in validation.evidence_refs:
            raw = store.resolve(ref)
            evidence = (SkillValidationEvidence.model_validate(raw) if ref.pointer else
                        SkillValidationEvidence.model_validate_json(raw))
            if (evidence.run_id != ref.run_id or evidence.skill_ref != skill.reference
                    or evidence.strategy_sha256 != validation.strategy_sha256
                    or evidence.worked != (ref.run_id in validation.validated_runs)):
                raise ValueError("Validation outcome contradicts experiment evidence")
        # Coverage must come from the actual run snapshots, not a claimed count.
        tasks, families, seeds = set(), set(), set()
        for run_id in runs:
            tasks.add(store.resolve(store.reference(run_id, "task.yaml", "/task_type")))
            families.add(store.resolve(store.reference(run_id, "design_input.yaml", "/robot_family")))
            seed = store.run(run_id).random_seed
            if seed is not None:
                seeds.add(seed)
        if (set(validation.task_coverage) != tasks or set(validation.robot_coverage) != families
                or set(validation.seed_coverage) != seeds):
            raise ValueError("Validation coverage contradicts run provenance")
    if skill.validation:
        if skill.provenance.last_validated_at != skill.validation[-1].validated_at:
            raise ValueError("last_validated_at must match the most recent validation")
    elif skill.provenance.last_validated_at is not None:
        raise ValueError("Validation timestamp without validation")
    if skill.status in ("validated", "approved"):
        if not skill.validation or skill.validation[-1].outcome != "passed":
            raise ValueError("Validated/approved skill requires a latest passed validation record")
    if skill.status == "approved" and skill.human_approval is None:
        raise ValueError("Human approval is required")
    if skill.human_approval:
        if not skill.validation or skill.human_approval.approved_at < skill.validation[-1].validated_at:
            raise ValueError("Approval must follow validation")
        if skill.human_approval.content_sha256 != skill_content_hash(skill):
            raise ValueError("Human approval does not match skill content")
    return skill
