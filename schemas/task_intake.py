"""N1 proposals and review-only drafts; no executable task or approval contract."""
from typing import Literal

from pydantic import ConfigDict, Field, JsonValue, model_validator

from schemas.common import Contract
from schemas.platform import SessionInput, TaskDefinition


class IntakeContract(Contract):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False, frozen=True)


class RequirementProposal(IntakeContract):
    id: str = Field(min_length=1)
    kind: Literal['behavior', 'constraint', 'observable', 'environment', 'acceptance']
    source: Literal['user_explicit', 'verified_configuration', 'llm_candidate', 'undefined']
    quote: str | None = None
    config_pointer: str | None = None
    question: str | None = None

    @model_validator(mode='after')
    def source_shape(self):
        expected = ('quote' if self.source == 'user_explicit' else
                    'config_pointer' if self.source == 'verified_configuration' else 'question')
        for name in ('quote', 'config_pointer', 'question'):
            value = getattr(self, name)
            if name == expected:
                if not value or not value.strip():
                    raise ValueError('SOURCE_CONTENT_REQUIRED: ' + name)
            elif value is not None:
                raise ValueError('SOURCE_CONTENT_CONFLICT: ' + name)
        return self


class TemporalRelation(IntakeContract):
    first: str
    relation: Literal['before', 'after', 'during', 'until', 'then', 'throughout']
    second: str
    quote: str = Field(min_length=1)
    source: Literal['user_explicit'] = 'user_explicit'


class IntakeProposal(IntakeContract):
    """Single model response. Configuration claims contain pointers, never values.

    Questions are suggestions to clarify, not declarations of physical facts.
    Goal/object quotes and all relation/requirement quotes are checked verbatim.
    """
    goal_quote: str = Field(min_length=1)
    object_quote: str | None
    intent: Literal['reach', 'reach_and_hold', 'tracking', 'obstacle_reach',
                    'catch_and_hold', 'disturbance_stabilization', 'other']
    requirements: list[RequirementProposal] = Field(min_length=1)
    temporal_relations: list[TemporalRelation]
    explanation: str = Field(min_length=1, description='Unverified LLM interpretation only')

    @model_validator(mode='after')
    def references(self):
        ids = [item.id for item in self.requirements]
        if len(ids) != len(set(ids)):
            raise ValueError('DUPLICATE_REQUIREMENT_ID')
        for relation in self.temporal_relations:
            if relation.first not in ids or relation.second not in ids or relation.first == relation.second:
                raise ValueError('INVALID_TEMPORAL_REFERENCE')
        return self


class AcceptanceView(IntakeContract):
    """Ephemeral projection of an explicitly supplied definition/configuration."""
    source_label: str
    source_identity: str
    task_identity: str
    family: str
    facts: dict[str, JsonValue]
    holding_interval_s: list[float] | None
    adapter_limits: dict[str, float] | None
    limitations: list[str]


class DraftRequirement(RequirementProposal):
    value: JsonValue
    source_identity: str | None
    confirmation: Literal['required'] = 'required'


class UnquotedSpan(IntakeContract):
    """Exact original text absent from requirement quotes; offsets are [start, end)."""
    start: int
    end: int
    text: str


class TaskIntakeDraft(IntakeContract):
    version: Literal['s130-n1'] = 's130-n1'
    status: Literal['needs_confirmation'] = 'needs_confirmation'
    executable: Literal[False] = False
    user_text: str
    unquoted_spans: list[UnquotedSpan] = Field(default_factory=list)
    user_goal: str
    user_goal_source: Literal['user_explicit'] = 'user_explicit'
    task_object: str | None
    task_object_source: Literal['user_explicit', 'undefined']
    intent: str
    interpretation_source: Literal['llm_candidate'] = 'llm_candidate'
    requirements: list[DraftRequirement]
    temporal_relations: list[TemporalRelation]
    missing_definitions: list[str]
    llm_explanation: str
    acceptance_context: AcceptanceView | None
    registered_task_families: list[str]
    execution_support: Literal['not_assessed'] = 'not_assessed'
    limitations: list[str]


class IntakeResult(IntakeContract):
    status: Literal['draft', 'parse_failed']
    draft: TaskIntakeDraft | None
    error: str | None
    provider_receipt: dict[str, JsonValue] | None = None

    @model_validator(mode='after')
    def closed_failure(self):
        if self.status == 'draft':
            if self.draft is None or self.error is not None:
                raise ValueError('DRAFT_RESULT_REQUIRED')
        elif self.draft is not None or not self.error:
            raise ValueError('FAILURE_MUST_NOT_CONTAIN_DRAFT')
        return self


class CompilationPreview(IntakeContract):
    """Review artifact, never an execution or task approval receipt."""
    version: Literal['s130-n2'] = 's130-n2'
    executable: Literal[False] = False
    semantic_spec: TaskIntakeDraft
    requirement_mappings: list[dict[str, JsonValue]]
    diagnostics: list[str]
    capabilities: dict[str, JsonValue]
    acceptance_spec: dict[str, JsonValue] | None = None
    candidate_task: TaskDefinition | None = None
    configuration_preview: SessionInput | None = None
    reference_identity: str | None = None
