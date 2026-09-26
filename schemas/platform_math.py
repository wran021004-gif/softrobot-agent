"""Serializable mathematical contracts, independent of algorithms and engines.

Functions use existing typed Payloads or immutable EvidenceRefs. A payload's
registered contract defines its expression format; adapters interpret it, never
eval configuration text or persist Python/CasADi/MATLAB objects.
"""
from typing import Literal
from pydantic import Field, model_validator
from schemas.common import Contract
from schemas.evidence import Identifier
from schemas.platform import Binding, EvidenceRef, Objective, Payload, SignalSpec


ModelCapability = Literal['kinematics', 'statics', 'dynamics', 'linearization', 'gradients']
ModelRepresentation = Literal['dynamic_system', 'linearized_model']
ModelUse = Literal['reachability', 'shape_prediction', 'static_equilibrium',
    'reduced_dynamics', 'control_trend', 'linearization', 'local_model_control',
    'contact_prediction', 'high_fidelity_validation']
ModelUseStatus = Literal['ALLOW', 'WARN', 'REJECT']
MathematicalExpression = Payload | EvidenceRef
# Same path -> specification format as Space: type, bounds/options, optional when.
# Vector/trajectory variables use indexed paths; no second variable namespace.
ParameterDefinitions = dict[str, dict]


class ModelCapabilities(Contract):
    kinematics: bool = False
    statics: bool = False
    dynamics: bool = False
    linearization: bool = False
    gradients: bool = False

    def supports(self, required: list[ModelCapability]) -> bool:
        declared = self.model_dump()
        return all(declared[name] for name in required)


class ModelVariable(Contract):
    """Declaration template; symbolic dimensions are resolved when exporting IR."""
    name: Identifier
    dimension: int | str
    units: str
    frame: str


class MathematicalModel(Contract):
    """What a model describes/provides, separate from its parameters and backend.

    Capabilities describe implemented mathematics. Representations separately
    declare available public exports; dynamics alone does not promise an IR.
    """
    state_definition: list[ModelVariable]
    input_definition: list[ModelVariable]
    output_definition: list[ModelVariable]
    required_robot_data: list[str]
    discretization_contract: str | None = None
    capabilities: ModelCapabilities
    representations: list[ModelRepresentation] = Field(default_factory=list)
    intended_uses: list[ModelUse] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    unsupported_physics: list[str] = Field(default_factory=list)


class ModelUseVerdict(Contract):
    status: ModelUseStatus
    reasons: list[str] = Field(min_length=1)
    validation: Literal['unavailable', 'measured_local'] = 'unavailable'
    evidence: list[EvidenceRef] = Field(default_factory=list)


class AgreementMetric(Contract):
    absolute_error: float = Field(ge=0)
    relative_error: float | None = Field(default=None, ge=0)
    units: str
    norm: str


class ModelAgreementEvidence(Contract):
    """Scoped measurements, without a composite score or implied acceptance."""
    design_identity: str
    model_bindings: list[Binding]
    representation_ids: dict[str, str]
    numerical_settings: dict
    mapping_convention: str
    reference_state_input: dict
    environment: dict
    measured_uses: list[ModelUse]
    metrics: dict[str, AgreementMetric]
    sources: list[EvidenceRef]
    source_locations: list[str]
    limitations: list[str]
    costs: dict = Field(default_factory=dict)


class ModelUseAssessment(Contract):
    """Deterministic, per-use physical applicability; not backend compilability."""
    model_id: str
    model_version: str
    design_id: str
    design_identity: str
    representation_id: str | None = None
    representation_kind: str | None = None
    representation_strategy: str | None = None
    generalized_coordinate_dimension: int | None = Field(default=None, ge=0)
    state_dimension: int | None = Field(default=None, ge=0)
    uses: dict[ModelUse, ModelUseVerdict] = Field(min_length=1)
    relevant_assumptions: list[str]
    unsupported_requested_physics: list[str]


class ModelRequirement(Contract):
    """Controller metadata; omitted metadata means no public model dependency."""
    input: Literal['none', 'mathematical_model', 'dynamic_system', 'linearized_model'] = 'none'
    capabilities: list[ModelCapability] = Field(default_factory=list)

    @model_validator(mode='after')
    def dependency(self):
        if self.input == 'none' and self.capabilities:
            raise ValueError('MODEL_CAPABILITIES_REQUIRE_MODEL_INPUT')
        return self

    def accepts(self, model: MathematicalModel | None) -> bool:
        if self.input == 'none':
            return True
        if model is None:
            return False
        required = list(self.capabilities)
        if self.input in ('dynamic_system', 'linearized_model'):
            required.append('dynamics' if self.input == 'dynamic_system' else 'linearization')
            if self.input not in model.representations:
                return False
        return model.capabilities.supports(required)


class DynamicSystem(Contract):
    """Ordered flattened x/u/y coordinates with concrete SignalSpec dimensions.

    Continuous: dynamics is xdot=f(x,u); discrete: x_next=f(x,u).
    Output, when present, is y=h(x,u); no output map is inferred from names.
    times/phase in coordinate specs describe the model's sampling convention.
    """
    state_definition: list[SignalSpec]
    input_definition: list[SignalSpec]
    output_definition: list[SignalSpec]
    dynamics: MathematicalExpression
    output: MathematicalExpression | None = None
    x0: list[float]
    u0: list[float]
    time_domain: Literal['continuous', 'discrete']
    timestep: float | None = Field(default=None, gt=0, description='Seconds; required for discrete time')

    @model_validator(mode='after')
    def coordinates(self):
        if self.time_domain == 'discrete' and self.timestep is None:
            raise ValueError('DISCRETE_SYSTEM_REQUIRES_TIMESTEP')
        if len(self.x0) != sum(s.dimension for s in self.state_definition) or len(self.u0) != sum(s.dimension for s in self.input_definition):
            raise ValueError('MODEL_OPERATING_POINT_DIMENSION_MISMATCH')
        return self


class SystemContext(Contract):
    """Explicit x0/u0 in the provider's declared coordinate order; no zero defaults.

    The caller resolves existing Initial/control data into these vectors. Scene
    may carry an existing Scene/Assembly payload or its saved evidence reference;
    this contract does not define another environment or initialization model.
    """
    x0: list[float]
    u0: list[float]
    scene: Payload | EvidenceRef | None = None


class LinearizedModel(Contract):
    """First-order perturbation model about x0/u0, in declared coordinate order.

    A/B are continuous derivatives or discrete transition Jacobians according
    to time_domain. drift is f(x0,u0) (continuous) or f(x0,u0)-x0 (discrete).
    Omitted drift asserts an equilibrium; linearization never implies it.
    """
    state_definition: list[SignalSpec]
    input_definition: list[SignalSpec]
    output_definition: list[SignalSpec]
    x0: list[float]
    u0: list[float]
    A: list[list[float]]
    B: list[list[float]]
    time_domain: Literal['continuous', 'discrete']
    timestep: float | None = Field(default=None, gt=0, description='Seconds; required for discrete time')
    drift: list[float] | None = None

    @model_validator(mode='after')
    def coordinates(self):
        nx = sum(s.dimension for s in self.state_definition)
        nu = sum(s.dimension for s in self.input_definition)
        if self.time_domain == 'discrete' and self.timestep is None:
            raise ValueError('DISCRETE_SYSTEM_REQUIRES_TIMESTEP')
        if len(self.x0) != nx or len(self.u0) != nu:
            raise ValueError('MODEL_OPERATING_POINT_DIMENSION_MISMATCH')
        if len(self.A) != nx or any(len(row) != nx for row in self.A) or len(self.B) != nx or any(len(row) != nu for row in self.B):
            raise ValueError('LINEARIZED_MATRIX_DIMENSION_MISMATCH')
        if self.drift is not None and len(self.drift) != nx:
            raise ValueError('LINEARIZED_DRIFT_DIMENSION_MISMATCH')
        return self


class ObjectiveSelection(Contract):
    """A declared semantic template and its public numeric weight, never code."""
    template_id: Identifier
    weight: float = Field(default=1., ge=0)


class ConstraintSelection(Contract):
    template_id: Identifier


class OptimizationSpecification(Contract):
    """Agent choices only; paths refer to the existing authorized Space.

    Template IDs must be declared by the selected assembler. No expression,
    generic configuration dictionary or executable string slot is accepted.
    Task remains the authority for physical targets and limits.
    """
    variables: list[str]
    objectives: list[ObjectiveSelection]
    constraints: list[ConstraintSelection] = Field(default_factory=list)
    horizon: int | None = Field(default=None, gt=0)
    initial_guess: dict[str, float] = Field(default_factory=dict)


class OptimizationConstraint(Contract):
    """Scalar lower <= expression(variables) <= upper; equal bounds mean equality."""
    name: Identifier
    expression: MathematicalExpression
    units: str
    lower: float | None = None
    upper: float | None = None

    @model_validator(mode='after')
    def bounds(self):
        if self.lower is None and self.upper is None:
            raise ValueError('OPTIMIZATION_CONSTRAINT_BOUND_REQUIRED')
        if self.lower is not None and self.upper is not None and self.lower > self.upper:
            raise ValueError('OPTIMIZATION_CONSTRAINT_BOUNDS_REVERSED')
        return self


class OptimizationProblem(Contract):
    """One explicit mathematical problem derived from a task, with no solver choice.

    objective_function returns the raw scalar metric; Objective retains the task's
    direction, weight and units. Constraints are mathematical expressions, not
    observed ConstraintResults. Adapters validate expression payloads via Registry.
    """
    variables: ParameterDefinitions
    objective: Objective
    objective_function: MathematicalExpression
    constraints: list[OptimizationConstraint] = Field(default_factory=list)
    model_reference: Binding | EvidenceRef | None = None
    horizon: int | None = Field(default=None, gt=0, description='Number of stages, when applicable')
    initial_guess: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode='after')
    def declared_initial_guess(self):
        if self.initial_guess.keys() - self.variables.keys():
            raise ValueError('INITIAL_GUESS_VARIABLE_NOT_DECLARED')
        return self


class OptimizationResult(Contract):
    status: Literal['converged', 'infeasible', 'unbounded', 'iteration_limit', 'failed', 'cancelled', 'unknown']
    optimum: dict[str, float] | None = None
    objective_value: float | None = None
    constraint_violation: float | None = Field(default=None, ge=0)
    iterations: int | None = Field(default=None, ge=0)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    problem_reference: EvidenceRef | None = None
    solver_evidence: EvidenceRef | None = None
