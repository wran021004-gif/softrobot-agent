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


class Plan(Contract):
    action: Literal['batch','diagnostic_replay','stop']
    hypothesis: str = Field(min_length=1)
    supporting_evidence: list[EvidenceRef] = Field(min_length=1)
    weakening_observation: str = Field(min_length=1)
    fixed_conditions: str = Field(min_length=1, description='Acknowledge frozen target, limits, topology, material, zero initial state, duration and 35 input switches')
    candidates: list[Candidate] = Field(default_factory=list,max_length=2)
    diagnostic_candidate: EvidenceRef | None = None
    requested_nlp_solves: int = Field(default=0,ge=0,le=2)
    requested_replays: int = Field(default=0,ge=0,le=2)
    revision_or_stop_rule: str = Field(min_length=1)
    disposition: str = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)

    @model_validator(mode='after')
    def operations_match(self):
        if self.action=='batch':
            if not self.candidates or self.requested_nlp_solves!=len(self.candidates) or self.requested_replays!=len(self.candidates) or self.diagnostic_candidate is not None:
                raise ValueError('BATCH_REQUIRES_ONE_OR_TWO_SOLVES_WITH_REPLAYS')
        elif self.action=='diagnostic_replay':
            if self.candidates or self.requested_nlp_solves or self.requested_replays!=1 or self.diagnostic_candidate is None:
                raise ValueError('DIAGNOSIS_REQUIRES_ONE_REFERENCED_REPLAY')
        elif self.candidates or self.requested_nlp_solves or self.requested_replays or self.diagnostic_candidate is not None:
            raise ValueError('STOP_REQUESTS_NO_EXPERIMENTS')
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


class ActivityPlan(Plan):
    """This grant permits exactly one choice in either batch."""
    candidates: list[Candidate] = Field(default_factory=list,max_length=1)
    requested_nlp_solves: int = Field(default=0,ge=0,le=1)
    requested_replays: int = Field(default=0,ge=0,le=1)
