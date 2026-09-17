"""Domain payloads; existing envelopes and old path contracts remain unchanged."""
from typing import Literal
from pydantic import Field
from schemas.common import Contract
from schemas.design_spec import DesignSpec
from schemas.exploration import ExplorationPhysics
from schemas.platform import EvidenceRef, Signal
from schemas.platform_operations import DiagnosticQuery, DiagnosticResult


class RodDesign(DesignSpec):
    robot_family: Literal['tendon_driven_continuum'] = 'tendon_driven_continuum'
    sections: Literal[1] = 1
    segments: Literal[8] = 8
    tendon_count: Literal[4] = 4
    total_length_m: float = Field(default=.3, ge=.05, le=.8)
    body_radius_m: float = Field(default=.02, ge=.005, le=.05)
    tendon_routing_radius_m: float = Field(default=.018, ge=.002, le=.045)
    exploration_physics: ExplorationPhysics = Field(default_factory=ExplorationPhysics)


class Empty(Contract):
    pass


class ResultSource(Contract):
    result: EvidenceRef
    execution_id: str | None = None


class SignalQuery(Contract):
    result: EvidenceRef
    name: str
    entity: str | None = None
    phase: str | None = None


class SelectedSignal(Contract):
    source: EvidenceRef
    status: Literal['available', 'missing_data']
    signal: Signal | None = None


class EntityDiagnosticQuery(DiagnosticQuery):
    entity: str | None = None
    phase: str | None = None


class EntityDiagnosticResult(DiagnosticResult):
    entity: str | None
    phase: str | None
    units: str
    threshold: float
    rule: Literal['sample_exceeds@1.1.0'] = 'sample_exceeds@1.1.0'


class SavedDiagnosis(ResultSource):
    entity: str = 'all'
    t_start_s: float | None = Field(default=None, ge=0)
    t_end_s: float | None = Field(default=None, ge=0)
    fields: list[str] = Field(default_factory=list, max_length=8)


class SavedRule(ResultSource):
    rule_id: str = 'contact_presence'
    rule_version: str = '1.0.0'
    entity: str = 'contact'
    t_start_s: float | None = Field(default=None, ge=0)
    t_end_s: float | None = Field(default=None, ge=0)


class SavedVideo(ResultSource):
    t_start_s: float | None = Field(default=None, ge=0)
    t_end_s: float | None = Field(default=None, ge=0)
    fps: int = Field(default=25, ge=1, le=60)
    azimuth_deg: float = 135.
    elevation_deg: float = Field(default=-20.,ge=-90,le=90)


class SavedProduct(Contract):
    source: EvidenceRef
    source_execution_id: str
    original_execution_id: str
    candidate_id: str
    bundle: EvidenceRef
    report: EvidenceRef
    files: dict[str, EvidenceRef] = Field(default_factory=dict)
    backend_solves: Literal[0] = 0
    rescoring: Literal[False] = False
