"""Small research choices; physical truth remains in the frozen pilot spec."""
from typing import Literal
from pydantic import Field, model_validator
from schemas.common import Contract
from schemas.platform import EvidenceRef


class Candidate(Contract):
    design_bounds: tuple[float, float] = (-1., 1.)
    design_initial: float = 0.
    objective_mode: Literal['task_gap', 'task_gap_with_effort'] = 'task_gap'
    position_weight: float = Field(default=1., ge=.25, le=4.)
    speed_weight: float = Field(default=1., ge=.25, le=4.)
    secondary_coefficient: float = Field(default=0., ge=0., le=.001)
    initialization: Literal['pretension_0_2','ramp_0_2_to_0_4','saved_schedule'] = 'pretension_0_2'
    source_candidate: EvidenceRef | None = None
    substeps: Literal[1,2] = 1

    @model_validator(mode='after')
    def legal_choices(self):
        lo,hi=self.design_bounds
        if not -1.<=lo<=self.design_initial<=hi<=1.:raise ValueError('DESIGN_DOMAIN_OUTSIDE_AUTHORIZATION')
        if self.objective_mode=='task_gap' and self.secondary_coefficient!=0.:raise ValueError('TASK_GAP_HAS_NO_SECONDARY_TRADEOFF')
        if (self.initialization=='saved_schedule') != (self.source_candidate is not None):raise ValueError('SAVED_INITIALIZATION_REQUIRES_EXACT_REFERENCE')
        return self


class Solve(Candidate):
    batch: Literal['initial','revision']
    plan_reference: EvidenceRef
    candidate_index: int = Field(ge=0,le=1)


class Empty(Contract):
    pass


class Replay(Contract):
    candidate: EvidenceRef


class ControlChoice(Contract):
    candidate: EvidenceRef
    holding_tip_speed_weight: float = Field(default=.05, ge=.025, le=.10)
    terminal_tip_speed_weight: float = Field(default=.10, ge=.025, le=.10)
    preceding_execution: EvidenceRef | None = None
    feasible_return_budget_s: float = Field(default=15.,ge=15.,le=30.)
    substeps: Literal[1,2] = 1
    record_update_ids: list[int] = Field(default_factory=list,max_length=2)
    recover_returned_tensions: bool = False


class SavedPlanChoice(Contract):
    source_problem: EvidenceRef = Field(description='Immutable paired snapshot reference, including exact source problem and plan vectors')
    plan_label: Literal['returned','checkpoint_1','checkpoint_2'] = 'returned'
    regenerated_reference: EvidenceRef | None = None
    max_wall_s: float = Field(default=180.,gt=0,le=300.)


class LocalComparison(Contract):
    update_id: int = Field(ge=1,le=34,description='Saved update; zero is excluded to avoid undefined preceding input.')
    changed_parameter: Literal['feasible_return.budget_s','terminal_tip_speed_weight','holding_tip_speed_weight','substeps']
    changed_value: float = Field(gt=0,le=30.)
    max_wall_s: float = Field(default=300.,gt=0,le=300.)


class Plan(Contract):
    action: Literal['solve','diagnose','diagnostic_replay','closed_loop','control_revision','saved_state_comparison','inspect_residuals','reintegrate_saved_tensions','warm_start_comparison','stop']
    hypothesis: str = Field(min_length=1)
    supporting_evidence: list[EvidenceRef] = Field(min_length=1)
    weakening_observation: str = Field(min_length=1)
    expected_observation: str = Field(min_length=1)
    fixed_conditions: str = Field(min_length=1, description='Acknowledge frozen target, limits, topology, material, zero initial state, duration and 35 input switches')
    candidates: list[Candidate] = Field(default_factory=list,max_length=1)
    control: ControlChoice | None = None
    diagnostic_candidate: EvidenceRef | None = None
    comparison: LocalComparison | None = None
    saved_plan: SavedPlanChoice | None = None
    requested_nlp_solves: int = Field(default=0,ge=0,le=2)
    requested_replays: int = Field(default=0,ge=0,le=2)
    revision_or_stop_rule: str = Field(min_length=1)
    disposition: str = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)

    @model_validator(mode='after')
    def operations_match(self):
        if self.action=='solve':
            if not self.candidates or self.requested_nlp_solves!=len(self.candidates) or self.requested_replays!=len(self.candidates) or self.diagnostic_candidate is not None:
                raise ValueError('SOLVE_REQUIRES_ONE_CANDIDATE_AND_REPLAY')
        elif self.action=='diagnostic_replay':
            if self.candidates or self.requested_nlp_solves or self.requested_replays!=1 or self.diagnostic_candidate is None:
                raise ValueError('DIAGNOSIS_REQUIRES_ONE_REFERENCED_REPLAY')
        elif self.candidates or self.requested_nlp_solves or self.requested_replays or self.diagnostic_candidate is not None:
            raise ValueError('STOP_REQUESTS_NO_EXPERIMENTS')
        if (self.action in ('closed_loop','control_revision')) != (self.control is not None):
            raise ValueError('CONTROL_ACTION_REQUIRES_EXACT_CANDIDATE_AND_WEIGHTS')
        if self.action=='control_revision' and self.control.preceding_execution is None:
            raise ValueError('CONTROL_REVISION_REQUIRES_PRECEDING_EXECUTION')
        if (self.action=='saved_state_comparison') != (self.comparison is not None):
            raise ValueError('PAIRED_COMPARISON_REQUIRES_ONE_DECLARED_FACTOR')
        if (self.action in ('inspect_residuals','reintegrate_saved_tensions','warm_start_comparison')) != (self.saved_plan is not None):
            raise ValueError('SAVED_PLAN_ACTION_REQUIRES_EXACT_REFERENCE')
        return self


class Result(Contract):
    detail: dict


class CloseoutPlan(Plan):
    """The final four sends can consume outstanding results and close only."""
    action: Literal['stop']
    candidates: list[Candidate] = Field(default_factory=list,max_length=0)
    requested_nlp_solves: Literal[0] = 0
    requested_replays: Literal[0] = 0
    diagnostic_candidate: None = None
    control: None = None
    comparison: None = None
    saved_plan: None = None


class FeasibilityPlan(Plan):
    action: Literal['diagnose','inspect_residuals','reintegrate_saved_tensions','warm_start_comparison','control_revision','stop']
    candidates: list[Candidate] = Field(default_factory=list,max_length=0)
    requested_nlp_solves: Literal[0] = 0
    requested_replays: Literal[0] = 0
    comparison: None = None
    diagnostic_candidate: None = None


class FeasibilityCheck(Contract):
    operation: Literal['inspect_residuals','reintegrate_saved_tensions','warm_start_comparison']
    choice: SavedPlanChoice
    plan_reference: EvidenceRef


class InitializationPlan(Plan):
    """Fresh diagnosis grant excludes full-horizon solves and BDF campaigns."""
    action: Literal['diagnose','saved_state_comparison','control_revision','stop']
    candidates: list[Candidate] = Field(default_factory=list,max_length=0)
    requested_nlp_solves: Literal[0] = 0
    requested_replays: Literal[0] = 0
    diagnostic_candidate: None = None


class ActivityPlan(Plan):
    """One expensive experiment per decision; evidence diagnosis is solve-free."""
    candidates: list[Candidate] = Field(default_factory=list,max_length=1)
    requested_nlp_solves: int = Field(default=0,ge=0,le=1)
    requested_replays: int = Field(default=0,ge=0,le=1)
