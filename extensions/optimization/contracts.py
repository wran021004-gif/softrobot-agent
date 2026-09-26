"""Typed contracts for the generic CasADi/IPOPT optimization path."""
from typing import Literal

from pydantic import Field, FiniteFloat

from schemas.common import Contract
from schemas.platform import Binding, EvidenceRef
from schemas.platform_math import OptimizationSpecification, SystemContext


class CasadiNLPExpression(Contract):
    """Trusted serialized CasADi function with scalar objective and vector constraints."""

    expression_id: Literal['casadi_nlp_function_v1'] = 'casadi_nlp_function_v1'
    symbolic_type: Literal['MX'] = 'MX'
    variable_order: list[str] = Field(min_length=1)
    constraint_order: list[str] = Field(default_factory=list)
    serialized_function: str = Field(min_length=1)
    expression_digest: str = Field(pattern=r'^[0-9a-f]{64}$')


class CasadiNLPSelector(Contract):
    """Scalar constraint selection from the bundle carried by objective_function."""

    expression_id: Literal['casadi_nlp_selector_v1'] = 'casadi_nlp_selector_v1'
    expression_digest: str = Field(pattern=r'^[0-9a-f]{64}$')
    constraint_name: str = Field(min_length=1)
    constraint_index: int = Field(ge=0)


class IpoptParameters(Contract):
    retain_feasible_iterate: bool = False
    max_cpu_s: FiniteFloat | None = Field(default=None, gt=0)
    max_iterations: int = Field(default=300, ge=1, le=10000)
    tolerance: FiniteFloat = Field(default=1e-8, gt=0)
    acceptable_tolerance: FiniteFloat = Field(default=1e-6, gt=0)
    print_level: int = Field(default=0, ge=0, le=12)
    hessian_approximation: Literal['limited-memory', 'exact'] = 'limited-memory'


class OptimizationDescribeRequest(Contract):
    pass


class OptimizationTemplateDescription(Contract):
    template_id: str
    assembler_id: str
    objective_templates: list[str]
    constraint_templates: list[str]
    variables: str
    target_source: str
    assembler_parameters: str


class OptimizationDescription(Contract):
    solver_id: Literal['solver.ipopt'] = 'solver.ipopt'
    pipeline: Literal[
        'Task + authorized variables -> trusted assembler -> OptimizationProblem EvidenceRef -> IPOPT'
    ] = 'Task + authorized variables -> trusted assembler -> OptimizationProblem EvidenceRef -> IPOPT'
    templates: list[OptimizationTemplateDescription]
    expression_details_public: Literal[False] = False
    backend_solves: Literal[0] = 0


class OptimizationAssembleRequest(Contract):
    assembler: Binding
    specification: OptimizationSpecification
    context: SystemContext | EvidenceRef | None = Field(default=None, description=(
        'Explicit assembly initial conditions, inline or by saved SystemContext reference. '
        'Required for GVS trajectories: x0=[q,qdot] in resolved basis order '
        '(rad/m, rad/(m*s)); u0 is the previously applied tension in frozen tendon order (N). '
        'These are not nominal equilibrium metadata or a warm start. '
        'Scene may be omitted; if supplied it must match the frozen task environment. '
        'Static assemblers may omit context.'
    ))


class OptimizationAssemblyResult(Contract):
    problem: EvidenceRef
    assembler_id: str
    objective_metric: str
    variables: list[str]
    constraint_count: int = Field(ge=0)
    target_source: str


class OptimizationSolveRequest(Contract):
    problem: EvidenceRef
    solver: Literal['solver.ipopt'] = 'solver.ipopt'
    options: IpoptParameters = Field(default_factory=IpoptParameters)
