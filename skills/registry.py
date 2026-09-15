"""File-backed immutable revisions; metadata retrieval only, never tool execution."""
from pathlib import Path
import yaml
from agents.contracts.permissions import require_write_permission
from schemas.common import Contract
from schemas.skill import Skill, SkillStatus, SkillCategory, HumanApproval, SkillValidationRecord
from tools.skill_policy import validate_skill
from tools.spec_tools import ROOT

DIRECTORY = {"candidate": "candidates", "validated": "candidates", "approved": "approved",
             "deprecated": "deprecated", "rejected": "candidates"}
TRANSITIONS = {"candidate": {"candidate", "validated", "rejected"},
               "validated": {"validated", "approved", "candidate", "rejected"},
               "approved": {"deprecated"}, "deprecated": set(), "rejected": set()}


class Revision(Contract):
    revision: int
    skill: Skill


def _strategy_identity(skill):
    return skill.model_dump(mode="json", exclude={"status", "validation", "human_approval", "deprecated_by", "provenance"}) | {
        "provenance": skill.provenance.model_dump(mode="json", exclude={"last_validated_at"})}


def _check_transition(previous, current):
    if current.status not in TRANSITIONS[previous.status]:
        raise ValueError("Illegal skill status transition")
    if _strategy_identity(previous) != _strategy_identity(current):
        raise ValueError("Strategy/applicability/evidence changes require a new version")
    if current.validation[:len(previous.validation)] != previous.validation:
        raise ValueError("Validation history, including failures, is append-only")
    if previous.status == "approved" and (current.validation != previous.validation or current.human_approval != previous.human_approval):
        raise ValueError("Deprecation preserves validation and Human approval")


class SkillRegistry:
    def __init__(self, root=ROOT / "skills", run_root=ROOT / "runs", *, validator=None):
        self.root, self.run_root = Path(root).resolve(), Path(run_root).resolve()
        self.validator = validator or validate_skill

    def history(self):
        groups = {}
        for directory in sorted(set(DIRECTORY.values())):
            for path in sorted((self.root / directory).glob("*.yaml")):
                if not path.resolve().is_relative_to(self.root):
                    raise ValueError("Registry path escapes root")
                revision = Revision.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
                skill = self.validator(revision.skill, self.run_root)
                if directory != DIRECTORY[skill.status] or path.name != f"{skill.reference}.r{revision.revision}.yaml":
                    raise ValueError("Registry path/status/version mismatch")
                groups.setdefault(skill.reference, []).append(revision)
        for rows in groups.values():
            rows.sort(key=lambda row: row.revision)
            for i, row in enumerate(rows, 1):
                if row.revision != i:
                    raise ValueError("Duplicate or missing skill revision")
                if i == 1 and row.skill.status != "candidate":
                    raise ValueError("Skill lifecycle must begin with a candidate")
                if i > 1:
                    _check_transition(rows[i - 2].skill, row.skill)
        return groups

    def current(self):
        return [rows[-1].skill for _, rows in sorted(self.history().items())]

    def get(self, reference):
        return self.history()[reference][-1].skill

    def _append(self, skill):
        skill = self.validator(skill, self.run_root)
        history = self.history()
        rows = history.get(skill.reference, [])
        if rows:
            _check_transition(rows[-1].skill, skill)
        elif skill.status != "candidate":
            raise ValueError("New versions must start as candidates")
        if not rows:
            versions = [rs[-1].skill.version for rs in history.values() if rs[-1].skill.skill_id == skill.skill_id]
            if versions and skill.version <= max(versions):
                raise ValueError("Version must increase")
            if versions and skill.supersedes != f"{skill.skill_id}@{max(versions)}":
                raise ValueError("New version must link superseded version")
            if skill.supersedes and skill.supersedes not in history:
                raise ValueError("Superseded skill does not exist")
        if skill.deprecated_by and skill.deprecated_by not in history:
            raise ValueError("Replacement skill does not exist")
        revision = Revision(revision=len(rows) + 1, skill=skill)
        folder = self.root / DIRECTORY[skill.status]
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{skill.reference}.r{revision.revision}.yaml"
        if not path.resolve().is_relative_to(self.root):
            raise ValueError("Registry write escapes root")
        # Exclusive creation prevents silently replacing a previously reviewed revision.
        with path.open("x", encoding="utf-8") as stream:
            yaml.safe_dump(revision.model_dump(mode="json"), stream, sort_keys=False)
        return skill

    def propose(self, skill):
        skill = Skill.model_validate(skill)
        if skill.status != "candidate" or skill.human_approval is not None:
            raise ValueError("Proposal must be an unapproved candidate")
        return self._append(skill)

    def record_validation(self, reference, record):
        skill = self.get(reference)
        record = SkillValidationRecord.model_validate(record)
        provenance = skill.provenance.model_copy(update={"last_validated_at": record.validated_at})
        return self._append(skill.model_copy(update={"validation": (*skill.validation, record),
            "provenance": provenance, "status": SkillStatus.VALIDATED if record.outcome == "passed" else SkillStatus.CANDIDATE}))

    def approve(self, reference, approval, *, actor):
        """Trusted Human entry point. Actor identity must be supplied by a future authenticated caller."""
        if actor != "human":
            raise PermissionError("Only Human may approve a skill")
        require_write_permission(actor, self.root / "approved")
        skill = self.get(reference)
        if skill.status != "validated":
            raise ValueError("Human approval requires validated status")
        approval = HumanApproval.model_validate(approval)
        return self._append(skill.model_copy(update={"status": SkillStatus.APPROVED, "human_approval": approval}))

    def retire(self, reference, *, actor, replacement=None):
        if actor != "human":
            raise PermissionError("Only Human may deprecate or reject a skill")
        skill = self.get(reference)
        status = SkillStatus.DEPRECATED if skill.status == "approved" else SkillStatus.REJECTED
        return self._append(skill.model_copy(update={"status": status, "deprecated_by": replacement}))

    def retrieve_skills(self, *, robot_family=None, task_type=None, failure_category=None, model_level=None,
                        control_level=None, required_tools=(), skill_category=None, status=None, include_candidates=False):
        if status is not None:
            status = SkillStatus(status)
        if skill_category is not None:
            skill_category = SkillCategory(skill_category)
        results = []
        for skill in self.current():
            if skill.status != "approved" and not (include_candidates and skill.status in ("candidate", "validated")):
                continue
            if status is not None and skill.status != status:
                continue
            applicability = skill.applicability
            if any(value is not None and value not in choices for value, choices in (
                    (robot_family, applicability.robot_families), (task_type, applicability.task_types),
                    (failure_category, skill.trigger_signature.failure_categories),
                    (model_level, applicability.model_levels), (control_level, applicability.control_levels))):
                continue
            if skill_category is not None and skill.category != skill_category:
                continue
            if set(required_tools) - set(skill.required_tools):
                continue
            results.append(skill)
        def rank(skill):
            coverage = len({run for v in skill.validation for run in v.validated_runs})
            return ({"approved": 0, "validated": 1, "candidate": 2}[skill.status], -coverage,
                    -skill.version, skill.skill_id)
        return sorted(results, key=rank)


def retrieve_skills(**filters):
    return SkillRegistry().retrieve_skills(**filters)
