"""Versioned output-aware local analysis; old LinearizedModel is unchanged."""
from typing import Literal
from pydantic import Field, PositiveFloat, model_validator
from schemas.common import Contract
from schemas.platform import EvidenceRef
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


class MathOptimizeRequest(Contract):
    source_node: str = Field(description='Owned completed Route build supplying the explicit starting configuration.')
    protocol: EvidenceRef
    target: EvidenceRef
    variables: dict[str, tuple[float, float]]
    material_scenarios: list[Literal['compliant','stiff']] = Field(min_length=2,max_length=2)
    objective: Literal['controller_start_local_endpoint_lexicographic_v1'] = 'controller_start_local_endpoint_lexicographic_v1'
    max_evaluations: int = Field(default=12,ge=2,le=24)

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
