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


class MetricsRequest(Contract):
    models: list[EvidenceRef] = Field(min_length=1)
    protocol: EvidenceRef
    implementation: Literal['scipy','matlab'] = 'scipy'


class LinearizeRequest(Contract):
    case: EvidenceRef
    protocol: EvidenceRef


class SavedCaseRequest(LinearizeRequest):
    pass


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
