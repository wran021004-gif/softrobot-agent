"""Public bounded design problem/result v1; counts never coerce floats."""
import math
from typing import Literal, Annotated
from pydantic import Field, FiniteFloat, model_validator
from schemas.common import Contract
from schemas.platform import TaskDefinition, EvidenceRef
from extensions.tendon_family.contracts import GVSTrajectoryParameters
from extensions.tendon_family.gvs_profile import SampledSettling


class Fixed(Contract):
    kind: Literal['fixed'] = 'fixed'
    value: int | float | str


class Integer(Contract):
    kind: Literal['integer'] = 'integer'
    bounds: tuple[Annotated[int,Field(strict=True)],Annotated[int,Field(strict=True)]]


class Categorical(Contract):
    kind: Literal['categorical'] = 'categorical'
    choices: list[str] = Field(min_length=1)


class Continuous(Contract):
    kind: Literal['continuous'] = 'continuous'
    bounds: tuple[FiniteFloat,FiniteFloat]
    initial: FiniteFloat


Variable = Annotated[Fixed | Integer | Categorical | Continuous,Field(discriminator='kind')]


class LengthAllocation(Contract):
    free: bool = True
    total_flexible_length_m: FiniteFloat = Field(default=.27,gt=0)
    relative_range: FiniteFloat = Field(default=.05,ge=0,le=.05)
    # Overrides are explicit topology-local physical length vectors, not latent
    # optimizer coordinates. A caller may provide different positive baselines.
    baseline_by_count: dict[str,list[FiniteFloat]] = Field(default_factory=dict)
    bounds_by_count: dict[str,list[tuple[FiniteFloat,FiniteFloat]]] = Field(default_factory=dict)
    fixed_by_count: dict[str,dict[str,FiniteFloat]] = Field(default_factory=dict)
    constraint_tolerance_m: Literal[1e-12] = 1e-12


class SearchBudget(Contract):
    max_evaluations: int = Field(default=4,ge=1,le=8,strict=True)
    wall_s: FiniteFloat = Field(default=7200.,gt=0,le=54000.)


class Structure(Contract):
    segment_count: int = Field(ge=2,le=4,strict=True)
    proximal_tendons: int = Field(ge=3,le=4,strict=True)
    distal_tendons: int = Field(ge=3,le=4,strict=True)
    material: Literal['baseline','compliant','stiff'] = 'baseline'


class Method(Contract):
    name: Literal['hierarchical_coordinate_v1'] = 'hierarchical_coordinate_v1'
    initial_structures: list[Structure] = Field(default_factory=list,max_length=3)
    step: FiniteFloat = Field(default=.25,gt=0,le=.5)
    minimum_step: FiniteFloat = Field(default=.03125,gt=0,le=.5)
    stop_on_acceptance: bool = False


class Objective(Contract):
    feasibility: Literal['joint_reach_hold_v1'] = 'joint_reach_hold_v1'
    ranking: Literal['feasible_then_max_normalized_violation_then_sum_v1'] = 'feasible_then_max_normalized_violation_then_sum_v1'
    accepted_resource_preference: Literal['fewer_actuators','none'] = 'fewer_actuators'


class FrozenExecution(Contract):
    seed: Literal[17] = 17
    controller: Literal['controller.gvs_nmpc@11.0.0'] = 'controller.gvs_nmpc@11.0.0'
    numerical_source: Literal['initial_state_pretension'] = 'initial_state_pretension'
    physical_initial_state: Literal['named_zero_positions_and_velocities'] = 'named_zero_positions_and_velocities'
    mesh: Literal['24_cells_12_proximal_equal_distal'] = '24_cells_12_proximal_equal_distal'
    force_limit_n: Literal[8.0] = 8.
    recipe: GVSTrajectoryParameters
    settling: SampledSettling


class DesignOptimizationProblem(Contract):
    contract: Literal['research.design_optimization_problem'] = 'research.design_optimization_problem'
    version: Literal['1.0.0'] = '1.0.0'
    study_id: str = Field(min_length=1,max_length=64)
    generator: Literal['serial_two_group_v1'] = 'serial_two_group_v1'
    task: TaskDefinition
    execution: FrozenExecution
    variables: dict[str,Variable]
    lengths: LengthAllocation = Field(default_factory=LengthAllocation)
    # Counts are derived under one independent actuator per tendon. Fixed totals
    # constrain compatible group choices, not extra optimizer coordinates.
    fixed_tendon_count: int | None = Field(default=None,ge=6,le=8,strict=True)
    fixed_actuator_count: int | None = Field(default=None,ge=6,le=8,strict=True)
    objective: Objective = Field(default_factory=Objective)
    method: Method = Field(default_factory=Method)
    budget: SearchBudget = Field(default_factory=SearchBudget)

    @model_validator(mode='after')
    def domain(self):
        legal={'segment_count':(2,4),'proximal_tendons':(3,4),'distal_tendons':(3,4),
            'section_scale':(.95,1.05),'routing_scale':(.98,1.02),
            'holding_tip_speed_weight':(.025,.1),'terminal_tip_speed_weight':(.025,.1),'pretension_n':(0.,8.)}
        required=set(legal)-{'pretension_n'} | {'material'}
        if not required <= set(self.variables) or set(self.variables)-set(legal)-{'material'}:
            raise ValueError('DESIGN_VARIABLE_KEYS: required '+str(sorted(required)))
        for key,var in list(self.variables.items()):
            count=key in ('segment_count','proximal_tendons','distal_tendons')
            if key=='material':
                values=[var.value] if isinstance(var,Fixed) else var.choices if isinstance(var,Categorical) else []
                if not values or set(values)-{'baseline','compliant','stiff'}:raise ValueError('MATERIAL_CATEGORICAL_DOMAIN')
                continue
            lo,hi=legal[key]
            if isinstance(var,Fixed):
                v=var.value
                if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not lo<=v<=hi or count and type(v) is not int:
                    raise ValueError('INVALID_FIXED_VALUE: '+key)
            elif count:
                if not isinstance(var,Integer):raise ValueError('GENUINE_INTEGER_DOMAIN_REQUIRED: '+key)
            elif not isinstance(var,Continuous):raise ValueError('CONTINUOUS_DOMAIN_REQUIRED: '+key)
            if not isinstance(var,Fixed):
                a,b=var.bounds
                if not lo<=a<=b<=hi:raise ValueError('VARIABLE_OUTSIDE_SUPPORTED_DOMAIN: '+key)
                if isinstance(var,Continuous) and not a<=var.initial<=b:raise ValueError('INITIAL_OUTSIDE_BOUNDS: '+key)
                if a==b:self.variables[key]=Fixed(value=a)
        if 'pretension_n' not in self.variables:self.variables['pretension_n']=Fixed(value=.2)
        if (self.fixed_tendon_count is not None and self.fixed_actuator_count is not None and
                self.fixed_tendon_count!=self.fixed_actuator_count):raise ValueError('ONE_TO_ONE_ACTUATOR_TENDON_COUNTS_CONFLICT')
        if self.method.minimum_step>self.method.step:raise ValueError('MINIMUM_STEP_EXCEEDS_INITIAL_STEP')
        return self


class EvaluatedDesign(Contract):
    candidate_id: str
    phase: Literal['structural_initialization','feedback_coordinate','confirmation']
    scientific_identity: str
    latent_coordinates: dict[str,FiniteFloat]
    resolved: dict
    feasible: bool
    objective_values: dict
    constraint_outcomes: dict
    evidence: dict
    execution_status: str
    used_feedback: str | None = None


class DesignOptimizationResult(Contract):
    contract: Literal['research.design_optimization_result'] = 'research.design_optimization_result'
    version: Literal['1.0.0'] = '1.0.0'
    problem_identity: str
    status: Literal['best_feasible_found','bounded_search_without_feasible','pending_execution']
    best_feasible: EvaluatedDesign | None = None
    best_observed_infeasible: EvaluatedDesign | None = None
    evaluated: list[EvaluatedDesign]
    construction_rejections: list[dict] = Field(default_factory=list)
    search_updates: list[dict]
    termination_reason: str
    unsearched_scope: dict
    search_state: EvidenceRef | None = None
    resource_use: dict
