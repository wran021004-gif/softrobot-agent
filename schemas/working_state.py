"""Read-only observation and the next diagnostic consumer, wire version 1."""
from typing import Literal
from typing_extensions import TypedDict
from pydantic import Field
from schemas.common import Contract
from schemas.platform import EvidenceRef
from schemas.platform_handoff import EvidenceSelector


class WorkflowView(TypedDict):
    session_status: str
    role: str | None
    phase: str | None
    computation_complete: bool
    delivery_complete: bool
    execution_validity: Literal['valid', 'invalid', 'unknown'] | None
    physical_acceptance: dict[str, bool | None]


class SelectionView(TypedDict):
    recorded: bool
    selected_candidate: dict | None
    candidate_disposition: Literal['adopt_candidate', 'retain_baseline', 'defer_selection', 'reject_all'] | None
    recommendation_disposition: Literal['adopt', 'defer', 'reject'] | None


class StageView(TypedDict):
    status: Literal['completed', 'unresolved']
    operation: str
    source_execution_id: str
    configuration: dict
    output: dict | None


class OperationsView(TypedDict):
    pending: dict | None
    unresolved: list[dict]
    completed_stages: dict[str, StageView]


class ProductState(Contract):
    initial_report: EvidenceRef | None = None
    accepted_revision: EvidenceRef | None = None
    feedback: EvidenceRef | None = None
    final_decision: EvidenceRef | None = None
    unaccepted_draft: dict | None = None


class ActionState(Contract):
    tool: str
    native_function: str | None = None
    version: str | None = None
    installed: bool
    permitted: bool
    reasons: list[str]
    validation: str = 'Arguments, exact evidence bindings and preflight costs still require the existing host.'


class WorkingState(Contract):
    contract: Literal['platform.working_state'] = 'platform.working_state'
    version: Literal['1.0.0'] = '1.0.0'
    run_id: str
    task: dict
    workflow: WorkflowView
    baseline: dict | None
    proposed: dict | None
    prepared: dict | None
    latest_tested: dict | None
    selection: SelectionView
    products: ProductState
    operations: OperationsView
    evidence: dict
    budgets: dict
    recovery: dict
    actions: list[ActionState]
    acceptance: dict
    parameter_impacts: dict
    experiment_plan: dict | None
    search_batch: dict | None = None


class DiagnosticAssessment(Contract):
    kind: Literal['observation', 'hypothesis', 'unresolved_question']
    statement: str = Field(min_length=1)
    supporting: list[EvidenceSelector] = Field(default_factory=list)
    contradicting: list[EvidenceSelector] = Field(default_factory=list)
    previous_assessment: EvidenceRef | None = None
    changed_by: list[EvidenceRef] = Field(default_factory=list)
    supporting_relevance: list[str] = Field(default_factory=list)
    contradicting_relevance: list[str] = Field(default_factory=list)


class DiscriminatingCheck(Contract):
    proposal: str
    expected_observations: list[str] = Field(min_length=1)
    weakening_observations: list[str] = Field(min_length=1)
    capability: str
    authorization: str
    budget: dict
    proceed_if: str
    revise_if: str
    stop_if: str


class DiagnosticHandoff(Contract):
    contract: Literal['platform.diagnostic_handoff'] = 'platform.diagnostic_handoff'
    version: Literal['1.0.0'] = '1.0.0'
    provenance: Literal['engineering_fixture', 'accepted_diagnostic_product']
    working_state: dict
    scope: dict
    unmet_criterion: str
    assessments: list[DiagnosticAssessment] = Field(min_length=1)
    check: DiscriminatingCheck
    search_plan: EvidenceRef | None = None
    causal_status: Literal['unproven'] = 'unproven'
