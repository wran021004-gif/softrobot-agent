"""Versioned output-aware local analysis; old LinearizedModel is unchanged."""
from typing import Literal
from pydantic import Field, PositiveFloat, StrictInt, model_validator
from schemas.common import Contract
from schemas.platform import EvidenceRef, SignalSpec
from schemas.platform_math import LinearizedModel
from schemas.platform_diagnostics import DiagnosticFact


class AnalysisProtocol(Contract):
    protocol_id: Literal['reach-local-v1'] = 'reach-local-v1'
    baseline_lengths_m: dict[str, PositiveFloat]
    duration_s: PositiveFloat = .35
    period_s: PositiveFloat = .01
    input_scale_n: PositiveFloat = 8.
    output_scale_m: PositiveFloat = .01
    windows_s: list[PositiveFloat] = [.05, .10, .35]
    samples_s: list[float] = [0., .10, .20, .30, .34]
    frequency_rad_s: list[PositiveFloat]
    rank_atol: PositiveFloat = 1e-12
    rank_rtol: PositiveFloat = 1e-9
    comparison_atol: PositiveFloat = 1e-8
    comparison_rtol: PositiveFloat = 2e-6
    derivative_atol: PositiveFloat = 2e-5
    derivative_rtol: PositiveFloat = 2e-4
    derivative_step: PositiveFloat = 1e-5
    equilibrium_normalized_residual: PositiveFloat = 1e-5
    static_force_tolerance: PositiveFloat = 1e-10
    static_max_iterations: int = Field(default=20, ge=1, le=20)
    pole_margin_s_inv: PositiveFloat = 1e-7
    authority_threshold: PositiveFloat | None = None
    authority_reason: str = 'No independently justified task-required MIMO gain threshold; usable bandwidth undefined.'
    authority_rule: str = 'Smallest singular value >= threshold, connected grid band starting at lowest frequency; no extrapolation.'

    @model_validator(mode='after')
    def ordered_frequency_grid(self):
        if any(b <= a for a, b in zip(self.frequency_rad_s, self.frequency_rad_s[1:])):
            raise ValueError('FREQUENCY_GRID_MUST_BE_STRICTLY_INCREASING')
        return self


class TaskAnalysisProtocol(AnalysisProtocol):
    """Frozen task-time and candidate-construction additions to the v1 baseline."""
    protocol_id: Literal['task-local-v2'] = 'task-local-v2'
    candidate_rule: Literal['initial_target_equilibrium_halfway'] = 'initial_target_equilibrium_halfway'
    endpoint_max_iterations: int = Field(default=100, ge=1, le=100)
    construction_max_iterations: int = Field(default=20, ge=1, le=20)
    horizon_alignment_atol_s: PositiveFloat = 1e-12
    endpoint_check_atol: PositiveFloat = 1e-8


class OutputLinearizedModel(LinearizedModel):
    analysis_version: Literal['1.0.0'] = '1.0.0'
    y0: list[float]
    C: list[list[float]]
    D: list[list[float]]
    drift: list[float]
    binding: dict
    operating_point: dict
    state_scales: list[PositiveFloat]
    input_scales: list[PositiveFloat]
    output_scales: list[PositiveFloat]
    normalization_derivation: str
    protocol_identity: str
    evidence: list[EvidenceRef]

    @model_validator(mode='after')
    def output_dimensions(self):
        nx, nu, ny = len(self.x0), len(self.u0), len(self.y0)
        if (ny != sum(s.dimension for s in self.output_definition) or len(self.C) != ny
                or any(len(r) != nx for r in self.C) or len(self.D) != ny
                or any(len(r) != nu for r in self.D)
                or tuple(map(len, (self.state_scales,self.input_scales,self.output_scales))) != (nx,nu,ny)):
            raise ValueError('OUTPUT_ANALYSIS_DIMENSION_MISMATCH')
        return self


class EndpointOutputLinearization(Contract):
    name: Literal['tip_position', 'tip_velocity']
    dimension: Literal[3] = 3
    units: Literal['m', 'm/s']
    frame: Literal['world'] = 'world'
    phase: Literal['instantaneous'] = 'instantaneous'
    value0: list[float] = Field(min_length=3, max_length=3)
    C: list[list[float]]
    D: list[list[float]]
    scales: list[PositiveFloat] = Field(min_length=3, max_length=3)

    @model_validator(mode='after')
    def dimensions(self):
        nx = len(self.C[0]) if self.C else 0
        nu = len(self.D[0]) if self.D else 0
        if (len(self.C) != 3 or any(len(row) != nx for row in self.C)
                or len(self.D) != 3 or any(len(row) != nu for row in self.D)):
            raise ValueError('ENDPOINT_OUTPUT_DIMENSION_MISMATCH')
        return self


class EndpointLinearizedModel(OutputLinearizedModel):
    analysis_version: Literal['2.0.0'] = '2.0.0'
    endpoint_outputs: list[EndpointOutputLinearization] = Field(min_length=2, max_length=2)

    @model_validator(mode='after')
    def endpoint_dimensions(self):
        outputs = {row.name: row for row in self.endpoint_outputs}
        if set(outputs) != {'tip_position', 'tip_velocity'}:
            raise ValueError('POSITION_AND_VELOCITY_ENDPOINT_OUTPUTS_REQUIRED')
        nx, nu = len(self.x0), len(self.u0)
        if any(len(row.C[0]) != nx or len(row.D[0]) != nu for row in outputs.values()):
            raise ValueError('ENDPOINT_MODEL_DIMENSION_MISMATCH')
        position = outputs['tip_position']
        if (position.value0 != self.y0 or position.C != self.C or position.D != self.D
                or position.scales != self.output_scales):
            raise ValueError('POSITION_OUTPUT_MUST_MATCH_FREQUENCY_OUTPUT')
        return self


class EndpointTarget(Contract):
    position_m: tuple[float, float, float]
    position_tolerance_m: PositiveFloat
    position_scale_m: PositiveFloat
    tip_velocity_m_s: tuple[float, float, float] = (0., 0., 0.)
    tip_speed_limit_m_s: PositiveFloat = .02
    tip_velocity_scale_m_s: PositiveFloat = .02


class MetricsRequest(Contract):
    models: list[EvidenceRef] = Field(min_length=1, description='Bare linear-model references or candidate-linearization result envelopes containing model references.')
    protocol: EvidenceRef
    implementation: Literal['scipy','matlab'] = 'scipy'


class LinearizeRequest(Contract):
    case: EvidenceRef
    protocol: EvidenceRef


class SavedLinearizeRequestV2(LinearizeRequest):
    include_static_equilibrium: bool = False


class SavedCaseRequest(LinearizeRequest):
    pass


class CandidateLinearizeRequest(Contract):
    source_node: str
    protocol: EvidenceRef


class BoundedEndpointRequest(Contract):
    models: list[EvidenceRef] = Field(min_length=1, description='Bare endpoint-model references or candidate-linearization result envelopes containing model references.')
    protocol: EvidenceRef
    target: EvidenceRef


class DesignScreenRequest(Contract):
    source_node: str
    protocol: EvidenceRef
    linearization: EvidenceRef
    metrics: EvidenceRef
    endpoint: EvidenceRef


class CandidateAnalysisRequest(Contract):
    source_node: str = Field(description='Owned completed Route build. The frozen Route protocol and endpoint target are resolved by the Host.')


class CandidateAnalysisComponent(Contract):
    tool_id: str
    tool_version: str
    status: Literal['computed','reused','failed','not_performed']
    reference: EvidenceRef | None = None
    failure: EvidenceRef | None = None
    detail: str | None = None


class CandidateAnalysisBundle(Contract):
    kind: Literal['candidate_analysis_bundle'] = 'candidate_analysis_bundle'
    source_node: str
    build_candidate_id: str
    build_result: EvidenceRef
    configuration: EvidenceRef
    scientific_configuration_identity: str
    analysis_scope_identity: str
    protocol: EvidenceRef
    target: EvidenceRef
    binding: dict
    model: dict
    dependency_identities: dict[str, dict | str | None]
    components: dict[Literal['linearization','metrics','endpoint','screen'], CandidateAnalysisComponent]
    evidence: list[EvidenceRef]
    advisory_findings: dict
    limitations: list[str]
    proposal_provenance: dict | None = None
    complete: bool


class MathOptimizeRequest(Contract):
    source_node: str = Field(description='Owned completed Route build supplying the explicit starting configuration.')
    protocol: EvidenceRef
    target: EvidenceRef
    variables: dict[str, tuple[float, float]]
    material_scenarios: list[Literal['compliant','stiff']] = Field(min_length=2,max_length=2)
    objective: Literal['controller_start_local_endpoint_lexicographic_v1'] = 'controller_start_local_endpoint_lexicographic_v1'
    max_evaluations: int = Field(default=12,ge=2,le=24, description='Maximum new mathematical evaluations requested by this call. All calls share the Route cumulative allowance; cache hits are free and failures count once work begins.')

    @model_validator(mode='after')
    def frozen_space(self):
        required={'components/near/length_m','components/far/length_m','design/section_scale'}
        if set(self.variables)!=required:
            raise ValueError('MATH_OPTIMIZER_REQUIRES_NEAR_FAR_AND_SECTION_SCALE')
        if set(self.material_scenarios)!={'compliant','stiff'}:
            raise ValueError('MATH_OPTIMIZER_REQUIRES_STIFF_AND_COMPLIANT_SCENARIOS')
        return self


class MathOptimizationResult(Contract):
    kind: Literal['mathematical_design_optimization'] = 'mathematical_design_optimization'
    starting_binding: dict
    protocol: EvidenceRef
    target: EvidenceRef
    objective: dict
    bounds: dict[str, tuple[float, float]]
    material_scenarios: list[str]
    evaluations: list[dict]
    proposals: list[dict]
    provenance: dict
    evidence: list[EvidenceRef]
    limitations: list[str]


class HistoricalMathBindingRequest(Contract):
    source_node: str = Field(description='Proposal-bound build node in the current Route session.')
    import_manifest: EvidenceRef = Field(description='Frozen historical-mathematics import manifest authorized by this Route session.')


class HistoricalMathBindingResult(Contract):
    kind: Literal['historical_math_binding'] = 'historical_math_binding'
    build_candidate_id: str
    optimizer_candidate_id: str
    source_build_node: str
    optimizer_result: EvidenceRef
    proposal_configuration: EvidenceRef
    scientific_configuration_identity: str
    references: dict[str, dict]
    lineage: dict
    usage: dict


class AnalysisResult(Contract):
    analysis_version: Literal['1.0.0'] = '1.0.0'
    kind: str
    protocol: EvidenceRef
    bindings: list[dict]
    records: list[dict]
    evidence: list[EvidenceRef]
    limitations: list[str]
    facts: list[DiagnosticFact] = Field(default_factory=list)


class CompareRequest(Contract):
    results: list[EvidenceRef] = Field(min_length=1)
    protocol: EvidenceRef


class TaskAnalysisConstraint(Contract):
    """Sampled convex descriptions; unsupported requirements retain their payload."""
    constraint_id: str
    signal: SignalSpec
    indices: list[StrictInt] = Field(min_length=1)
    kind: Literal['norm_bound', 'component_interval', 'unsupported']
    reference: list[list[float]]
    radius: float | None = Field(default=None, ge=0)
    lower: list[float] | None = None
    upper: list[float] | None = None
    provenance: list[str] = Field(min_length=1)
    unsupported_requirement: dict | None = None

    @model_validator(mode='after')
    def sampled_values(self):
        if any(i < 0 for i in self.indices) or self.indices != sorted(set(self.indices)):
            raise ValueError('ORDERED_UNIQUE_NONNEGATIVE_SAMPLE_INDICES_REQUIRED')
        if self.kind!='path_bound' and (len(self.reference) != len(self.indices) or any(len(v) != self.signal.dimension for v in self.reference)):
            raise ValueError('ONE_REFERENCE_VECTOR_PER_SAMPLE_REQUIRED')
        if self.kind == 'norm_bound' and (self.radius is None or self.lower is not None or self.upper is not None):
            raise ValueError('NORM_BOUND_REQUIRES_ONLY_RADIUS')
        if self.kind == 'component_interval':
            if (self.radius is not None or self.lower is None or self.upper is None
                    or len(self.lower) != self.signal.dimension or len(self.upper) != self.signal.dimension
                    or any(lo > hi for lo, hi in zip(self.lower, self.upper))):
                raise ValueError('ORDERED_COMPONENT_BOUNDS_REQUIRED')
        if (self.kind == 'unsupported') != (self.unsupported_requirement is not None):
            raise ValueError('UNSUPPORTED_REQUIREMENT_PAYLOAD_REQUIRED')
        return self


class PathAnalysisConstraint(TaskAnalysisConstraint):
    """Free ordered progress, distinct from a fixed reference at each sample."""
    kind: Literal['path_bound'] = 'path_bound'
    path_vertices_m: list[list[float]] = Field(min_length=2,max_length=3)
    radius: PositiveFloat

    @model_validator(mode='after')
    def path_geometry(self):
        if (self.signal.dimension!=3 or self.signal.units!='m' or self.signal.frame!='world'
                or any(len(v)!=3 for v in self.path_vertices_m) or self.reference
                or self.lower is not None or self.upper is not None or self.unsupported_requirement is not None):
            raise ValueError('WORLD_METRE_PATH_WITH_FREE_PROGRESS_REQUIRED')
        from extensions.reference.contracts import TrackingGoal
        TrackingGoal(vertices_m=self.path_vertices_m,time_requirement='none')
        return self


class TaskAnalysisRequirement(Contract):
    """Frozen context and sample grid; horizon_semantics distinguishes deadlines.

    Constraints may retain unsupported evaluator conditions alongside solvable
    proxies. Full requested mathematical coverage is not physical acceptance.
    """
    contract: Literal['task-analysis-v1'] = 'task-analysis-v1'
    binding: dict
    duration_s: PositiveFloat
    sample_period_s: PositiveFloat
    time_grid_s: list[float] = Field(min_length=2)
    constraints: list[TaskAnalysisConstraint | PathAnalysisConstraint] = Field(min_length=1)
    physical_inputs: dict
    required_physics: list[str] = Field(default_factory=list)
    horizon_semantics: Literal['absolute_task_time_inclusive_samples',
        'numerical_witness_horizon_inclusive_samples'] = 'absolute_task_time_inclusive_samples'

    @model_validator(mode='after')
    def exact_grid(self):
        if (any(abs(t-i*self.sample_period_s) > 1e-12 for i,t in enumerate(self.time_grid_s))
                or abs(self.time_grid_s[-1]-self.duration_s) > 1e-12):
            raise ValueError('INCLUSIVE_UNIFORM_TASK_GRID_REQUIRED')
        if len({c.constraint_id for c in self.constraints}) != len(self.constraints):
            raise ValueError('UNIQUE_CONSTRAINT_IDENTITIES_REQUIRED')
        if any(c.indices[-1] >= len(self.time_grid_s) for c in self.constraints):
            raise ValueError('CONSTRAINT_INDEX_OUTSIDE_TASK_HORIZON')
        return self


class ScopedMathematicalClaim(Contract):
    contract: Literal['scoped-mathematical-claim-v1'] = 'scoped-mathematical-claim-v1'
    conclusion: Literal['feasible_witness', 'model_infeasibility_certificate', 'diagnostic', 'inconclusive', 'not_applicable']
    binding: dict
    requirement_identity: str
    model_identity: str | None
    model_declaration: dict
    protocol_identity: str
    operating_point: dict
    horizon: dict
    physical_inputs: dict
    constraint_coverage: list[dict]
    numerical_result_pointer: str
    computation_status: str
    verification_status: str
    supported_interpretation: str
    unsupported_conclusions: list[str]
