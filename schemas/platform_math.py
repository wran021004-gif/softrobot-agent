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


class OptimizationConstraint(Contract):
    """Scalar lower <= expression(variables) <= upper; equal bounds mean equality."""
    name: Identifier
    expression: MathematicalExpression
    units: str
    lower: float | None = None
    upper: float | None = None


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


class OptimizationResult(Contract):
    status: Literal['converged', 'infeasible', 'unbounded', 'iteration_limit', 'failed', 'cancelled', 'unknown']
    optimum: dict[str, float] | None = None
    objective_value: float | None = None
    constraint_violation: float | None = Field(default=None, ge=0)
    iterations: int | None = Field(default=None, ge=0)
    evidence: list[EvidenceRef] = Field(default_factory=list)
