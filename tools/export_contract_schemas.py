"""Export the authoritative Pydantic contracts as reviewable JSON Schema files."""
import json
from schemas.trace import TraceEvent, DecisionRecord
from schemas.task_contract import TaskContract
from schemas.experiment_policy import ExperimentPolicy
from schemas.candidate_evaluation import CandidateEvaluation
from schemas.feedback import FeedbackArtifact, FeedbackUpdate
from schemas.finding import CandidateFinding
from schemas.memory import MemoryRecord
from schemas.skill import Skill, SkillValidationRecord, SkillValidationEvidence
from tools.spec_tools import ROOT

CONTRACTS = {
    "schemas/json/experiment_policy.schema.json": ExperimentPolicy,
    "schemas/json/candidate_evaluation.schema.json": CandidateEvaluation,
    "schemas/json/feedback_controller.schema.json": FeedbackArtifact,
    "schemas/json/feedback_update.schema.json": FeedbackUpdate,
    "schemas/json/task_contract.schema.json": TaskContract,
    "schemas/json/trace_event.schema.json": TraceEvent,
    "schemas/json/decision_record.schema.json": DecisionRecord,
    "schemas/json/candidate_finding.schema.json": CandidateFinding,
    "schemas/json/memory_record.schema.json": MemoryRecord,
    "skills/schema/skill.schema.json": Skill,
    "skills/schema/validation_record.schema.json": SkillValidationRecord,
    "skills/schema/validation_evidence.schema.json": SkillValidationEvidence,
}


def export_schemas():
    for name, contract in CONTRACTS.items():
        path = ROOT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(contract.model_json_schema(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    export_schemas()
