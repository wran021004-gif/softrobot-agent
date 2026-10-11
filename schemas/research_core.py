"""Native business fields for the bounded reach-and-hold research entry."""
from typing import Literal
from pydantic import Field, FiniteFloat, model_validator
from schemas.common import Contract
from schemas.platform import EvidenceRef


class Parameters(Contract):
    d: FiniteFloat = Field(default=0., ge=-1, le=1)
    holding_tip_speed_weight: FiniteFloat = Field(default=.10, ge=.025, le=.10)
    terminal_tip_speed_weight: FiniteFloat = Field(default=.10, ge=.025, le=.10)


class Search(Contract):
    variables: list[Literal['d', 'holding_tip_speed_weight', 'terminal_tip_speed_weight']] = Field(min_length=1)
    bounds: dict[str, tuple[FiniteFloat, FiniteFloat]]
    fixed: Parameters = Field(default_factory=Parameters)
    max_evaluations: int = Field(default=3, ge=1, le=8, strict=True)
    step: FiniteFloat = Field(default=.25, gt=0, le=.5)
    ranking: Literal['feasible_then_max_normalized_violation_then_sum_v1'] = 'feasible_then_max_normalized_violation_then_sum_v1'

    @model_validator(mode='after')
    def domain(self):
        if len(set(self.variables)) != len(self.variables) or set(self.bounds) != set(self.variables):
            raise ValueError('SEARCH_BOUNDS_MUST_MATCH_UNIQUE_SELECTED_VARIABLES')
        for name, (a, b) in self.bounds.items():
            lo, hi = (-1., 1.) if name == 'd' else (.025, .10)
            if not lo <= a < b <= hi or not a <= getattr(self.fixed, name) <= b:
                raise ValueError('SEARCH_DOMAIN_OR_INITIAL_OUTSIDE_BOUNDS: ' + name)
        return self


class LocalDiagnostic(Contract):
    execution: EvidenceRef
    update_id: int = Field(ge=0,le=34,strict=True)
    repetitions: int = Field(default=2,ge=1,le=2,strict=True)
    mode: Literal['production', 'fixed_iteration'] = 'production'
    iteration_cap: int = Field(default=8,ge=1,le=120,strict=True)


class Plan(Contract):
    action: Literal['propose', 'execute', 'search', 'diagnose', 'confirm', 'stop']
    hypothesis: str = Field(min_length=1)
    supporting_evidence: list[EvidenceRef] = Field(default_factory=list)
    expected_observation: str = Field(min_length=1)
    weakening_observation: str = Field(min_length=1)
    fixed_conditions: str = Field(min_length=1)
    stopping_condition: str = Field(min_length=1)
    interpretation: str = Field(min_length=1)
    parameters: Parameters | None = None
    search: Search | None = None
    candidate: EvidenceRef | None = None
    selected_execution: EvidenceRef | None = None
    diagnostic: LocalDiagnostic | None = None
    experience_disposition: dict[str, Literal['adopted', 'rejected', 'context_only']] = Field(default_factory=dict)

    @model_validator(mode='after')
    def required(self):
        required = {'propose': 'parameters', 'execute': 'candidate', 'search': 'search', 'confirm': 'selected_execution'}
        active = required.get(self.action)
        for field in ('parameters', 'search', 'candidate', 'selected_execution'):
            if (getattr(self, field) is not None) != (field == active):
                raise ValueError('ACTION_REQUIRES_ONLY_' + str(active))
        if self.diagnostic is not None and self.action!='diagnose':
            raise ValueError('LOCAL_DIAGNOSTIC_REQUIRES_DIAGNOSE_ACTION')
        return self


class ExperienceQuery(Contract):
    operation: Literal['search', 'read'] = 'search'
    key: Literal['case', 'procedure'] | None = None
    task: str | None = None
    structure: str | None = None
    failure_type: str | None = None
    version: str | None = None


class EvidenceQuery(Contract):
    reference: EvidenceRef
    pointer: str = ''
