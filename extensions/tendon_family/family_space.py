"""Frozen SI serial-family domains and compact requests, independent of source tendons."""
from typing import Literal
from pydantic import Field, FiniteFloat, model_validator
from schemas.common import Contract
from .contracts import Discretization, RoutePoint, Section, Segment, Rigid, Attachment


class Domain(Contract):
    minimum: FiniteFloat
    maximum: FiniteFloat
    default: FiniteFloat

    @model_validator(mode='after')
    def ordered(self):
        if not self.minimum <= self.default <= self.maximum:
            raise ValueError('ORDERED_DOMAIN_AND_DEFAULT_REQUIRED')
        return self

    def check(self, value, name):
        if not self.minimum <= value <= self.maximum:
            raise ValueError('OUTSIDE_FAMILY_DOMAIN: '+name)
        return value


class SegmentDomain(Contract):
    length_m: Domain
    young_pa: Domain
    section_dimensions_m: dict[str, dict[str, Domain]]


class Assembly(Contract):
    """Physical prototypes only; no tendon/actuator objects or scientific candidate."""
    components: list[Segment | Rigid]
    tip: Attachment
    mesh: Discretization
    provenance: dict


class ActuationDefaults(Contract):
    rule: Literal['independent_displacement_ideal_tension_v1']
    limits_m: tuple[FiniteFloat, FiniteFloat]
    velocity_limit_m_s: FiniteFloat = Field(gt=0)

    @model_validator(mode='after')
    def limits(self):
        if not self.limits_m[0] <= 0 <= self.limits_m[1] or self.limits_m[0] >= self.limits_m[1]:
            raise ValueError('ACTUATOR_LIMITS_MUST_CONTAIN_ZERO')
        return self


class FamilySpace(Contract):
    version: Literal['serial_family_space_v1'] = 'serial_family_space_v1'
    family_id: str
    assumptions: list[str]
    segment_count_bounds: tuple[int, int]
    tendon_count_bounds: tuple[int, int]
    executable_segment_counts: list[int]
    executable_tendon_count_bounds: tuple[int, int]
    segment_domain: SegmentDomain
    segment_domains: dict[int, SegmentDomain] = Field(default_factory=dict)
    tendon_domains: dict[str, Domain]
    routing_domains: dict[str, Domain]
    control_domains: dict[str, Domain]
    assembly: Assembly
    actuator_defaults: ActuationDefaults
    conditional_rules: Literal['selected_segments_and_consecutive_spans_v1'] = 'selected_segments_and_consecutive_spans_v1'
    unsupported: list[str]

    @model_validator(mode='after')
    def domains(self):
        for bounds in (self.segment_count_bounds, self.tendon_count_bounds, self.executable_tendon_count_bounds):
            if not 1 <= bounds[0] <= bounds[1]:
                raise ValueError('POSITIVE_ORDERED_TOPOLOGY_BOUNDS_REQUIRED')
        if self.version == 'serial_family_space_v1' and self.executable_segment_counts != [2]:
            raise ValueError('C1_EXECUTES_ONLY_TWO_SEGMENTS')
        if (self.version=='serial_family_space_v1' and not self.segment_count_bounds[0] <= 2 <= self.segment_count_bounds[1]) or not (
                self.tendon_count_bounds[0] <= self.executable_tendon_count_bounds[0] <=
                self.executable_tendon_count_bounds[1] <= self.tendon_count_bounds[1]):
            raise ValueError('EXECUTABLE_DOMAIN_MUST_BE_DECLARED')
        if set(self.tendon_domains) != {'diameter_m','force_limit_n','pretension_n','length_servo_gain_n_m'} or set(self.routing_domains) != {
                'radius_m','guide_s','anchor_s','phase_rad','angular_offset_rad'} or set(self.control_domains) != {
                'holding_tip_speed_weight','terminal_tip_speed_weight'}:
            raise ValueError('EXPLICIT_PHYSICAL_AND_CONTROL_DOMAINS_REQUIRED')
        for domain in [self.segment_domain, *self.segment_domains.values()]:
            if min(domain.length_m.minimum, domain.young_pa.minimum) <= 0:
                raise ValueError('POSITIVE_LENGTH_AND_MODULUS_REQUIRED')
            if any(v.minimum <= 0 for dims in domain.section_dimensions_m.values() for v in dims.values()):
                raise ValueError('POSITIVE_SECTION_DIMENSIONS_REQUIRED')
        if any(not 0 <= i < self.segment_count_bounds[1] for i in self.segment_domains):
            raise ValueError('SEGMENT_DOMAIN_INDEX_OUTSIDE_TOPOLOGY')
        if any(d.minimum < 0 for d in [*self.tendon_domains.values(), *self.control_domains.values()]):
            raise ValueError('NONNEGATIVE_PHYSICAL_DOMAINS_REQUIRED')
        if min(self.tendon_domains[k].minimum for k in ('diameter_m','force_limit_n','length_servo_gain_n_m')) <= 0:
            raise ValueError('POSITIVE_TENDON_DOMAINS_REQUIRED')
        if not (0 < self.routing_domains['radius_m'].minimum and
                0 < self.routing_domains['guide_s'].minimum <= self.routing_domains['guide_s'].maximum < 1 and
                0 < self.routing_domains['anchor_s'].minimum <= self.routing_domains['anchor_s'].maximum <= 1):
            raise ValueError('PHYSICAL_ROUTING_DOMAIN_REQUIRED')
        return self


class SegmentChoice(Contract):
    length_m: FiniteFloat | None = None
    young_pa: FiniteFloat | None = None
    sections: list[Section] | None = None


class Span(Contract):
    first_segment: int = Field(default=0, ge=0, strict=True)
    last_segment: int = Field(ge=0, strict=True)
    count: int = Field(ge=1, strict=True)
    phase_rad: FiniteFloat = 0.
    angular_offsets_rad: list[FiniteFloat] = Field(default_factory=list)
    radius_m: FiniteFloat | None = None
    guide_s: list[FiniteFloat] | None = None
    anchor_s: FiniteFloat | None = None
    guide_angle_offset_rad: FiniteFloat = 0.
    anchor_angle_offset_rad: FiniteFloat = 0.


class GenerationRequest(Contract):
    version: Literal['serial_family_generation_v1'] = 'serial_family_generation_v1'
    family_space_identity: str = Field(min_length=1)
    segment_count: int = Field(default=2, ge=1, strict=True)
    tendon_count: int = Field(ge=1, strict=True)
    strategy: Literal['polar_consecutive_spans_v1'] = 'polar_consecutive_spans_v1'
    spans: list[Span] = Field(default_factory=list)
    segments: dict[int, SegmentChoice] = Field(default_factory=dict)
    tendon_parameters: dict[str, FiniteFloat] = Field(default_factory=dict)
    control_weights: dict[str, FiniteFloat] = Field(default_factory=dict)
    route_overrides: dict[int, list[RoutePoint]] = Field(default_factory=dict)

    @model_validator(mode='after')
    def conditional(self):
        if any(not 0 <= i < self.segment_count for i in self.segments) or any(
                not 0 <= i < self.tendon_count for i in self.route_overrides):
            raise ValueError('PARAMETER_DOES_NOT_EXIST_IN_SELECTED_TOPOLOGY')
        if self.spans and sum(s.count for s in self.spans) != self.tendon_count:
            raise ValueError('SPAN_COUNTS_MUST_SUM_TO_TENDON_COUNT')
        for span in self.spans:
            if not 0 <= span.first_segment <= span.last_segment < self.segment_count:
                raise ValueError('CONSECUTIVE_SPAN_OUTSIDE_SELECTED_TOPOLOGY')
            if span.angular_offsets_rad and len(span.angular_offsets_rad) != span.count:
                raise ValueError('ONE_ANGULAR_OFFSET_PER_SELECTED_TENDON')
        return self


class FamilyBuild(Contract):
    space: FamilySpace
    request: GenerationRequest


class SerialAssemblyRule(Contract):
    version: Literal['repeat_serial_prototypes_v1'] = 'repeat_serial_prototypes_v1'
    root_segment: str
    repeated_segment: str
    guide: str
    connector: str
    payload: str
    cell_count_bounds: tuple[int,int]
    default_cells: int

    @model_validator(mode='after')
    def cells(self):
        if not 1 <= self.cell_count_bounds[0] <= self.default_cells <= self.cell_count_bounds[1]:
            raise ValueError('POSITIVE_ORDERED_CELL_DOMAIN_REQUIRED')
        return self


class FamilySpaceV2(FamilySpace):
    version: Literal['serial_family_space_v2'] = 'serial_family_space_v2'
    serial_assembly: SerialAssemblyRule

    @model_validator(mode='after')
    def serial(self):
        if not self.executable_segment_counts or self.executable_segment_counts != sorted(set(self.executable_segment_counts)) or any(
                not self.segment_count_bounds[0] <= i <= self.segment_count_bounds[1] for i in self.executable_segment_counts):
            raise ValueError('EXECUTABLE_SEGMENT_COUNTS_MUST_BE_DECLARED')
        parts={c.id:c for c in self.assembly.components}
        rule=self.serial_assembly
        for name,kind in ((rule.root_segment,'flexible_segment'),(rule.repeated_segment,'flexible_segment'),
                          (rule.guide,'guide'),(rule.connector,'rigid_connector'),(rule.payload,'payload')):
            if name not in parts or parts[name].kind!=kind:
                raise ValueError('NAMED_SERIAL_PROTOTYPE_REQUIRED: '+name)
        if parts[rule.root_segment].connection.part!='fixed_base' or self.assembly.tip.part!=rule.payload:
            raise ValueError('SERIAL_ROOT_AND_PAYLOAD_TIP_REQUIRED')
        if (parts[rule.guide].connection.s!=1 or parts[rule.connector].connection.s!=0 or
                parts[rule.repeated_segment].connection.s!=0 or parts[rule.payload].connection.s!=1):
            raise ValueError('SERIAL_BOUNDARY_CONNECTION_STATIONS_REQUIRED')
        return self


class SegmentChoiceV2(SegmentChoice):
    cells: int | None = Field(default=None,ge=1,strict=True)


class GenerationRequestV2(GenerationRequest):
    version: Literal['serial_family_generation_v2'] = 'serial_family_generation_v2'
    segments: dict[int,SegmentChoiceV2] = Field(default_factory=dict)


class FamilyBuildV2(Contract):
    space: FamilySpaceV2
    request: GenerationRequestV2


def parse_space(value):
    return (FamilySpaceV2 if value.get('version')=='serial_family_space_v2' else FamilySpace).model_validate(value)


def parse_build(value):
    from tools.platform_store import plain
    value=plain(value)
    return (FamilyBuildV2 if value['space'].get('version')=='serial_family_space_v2' else FamilyBuild).model_validate(value)


class UnsupportedGeneration(ValueError):
    """Declared domain whose physical implementation belongs to a later milestone."""


def validate_request(space, request):
    from tools.state_io import digest
    from tools.platform_store import plain
    if request.family_space_identity != digest(plain(space)):
        raise ValueError('FROZEN_FAMILY_SPACE_IDENTITY_MISMATCH')
    for value, bounds, name in ((request.segment_count, space.segment_count_bounds, 'segment_count'),
                                (request.tendon_count, space.tendon_count_bounds, 'tendon_count')):
        if not bounds[0] <= value <= bounds[1]:
            raise ValueError('OUTSIDE_FAMILY_DOMAIN: '+name)
    if request.segment_count not in space.executable_segment_counts:
        raise UnsupportedGeneration('segment_count='+str(request.segment_count)+'; C1 materializes only two segments')
    if not space.executable_tendon_count_bounds[0] <= request.tendon_count <= space.executable_tendon_count_bounds[1]:
        raise UnsupportedGeneration('tendon_count='+str(request.tendon_count)+'; outside current executable envelope')
    for values, domains in ((request.tendon_parameters, space.tendon_domains), (request.control_weights, space.control_domains)):
        for key, value in values.items():
            if key not in domains:
                raise ValueError('UNDECLARED_FAMILY_PARAMETER: '+key)
            domains[key].check(value, key)


def decision_summary(value, evidence, operations):
    """Exact frozen domains without repeating component meshes and inertias."""
    from tools.platform_store import plain
    space = parse_space(value)
    frozen = plain(space)
    result = {k:frozen[k] for k in (
        'version','family_id','assumptions','segment_count_bounds','executable_segment_counts',
        'tendon_count_bounds','executable_tendon_count_bounds','segment_domain','segment_domains',
        'tendon_domains','routing_domains','control_domains','actuator_defaults','conditional_rules','unsupported')}
    result['segment_domains'] = {i:{k:v for k,v in domain.items() if v != frozen['segment_domain'][k]}
        for i,domain in frozen['segment_domains'].items()}
    def compact(value):
        if isinstance(value,dict):
            if set(value)=={'minimum','maximum','default'}:
                return [value['minimum'],value['maximum'],value['default']]
            return {k:compact(v) for k,v in value.items()}
        return value
    result = compact(result)
    result['domain_encoding'] = '[minimum, maximum, default]; indexed segment fields override generic domain'
    if isinstance(space,FamilySpaceV2):
        result['serial_assembly']=plain(space.serial_assembly)
        result['generation_version']='serial_family_generation_v2'
    else:
        result['generation_version']='serial_family_generation_v1'
    result.update(full_specification=evidence, available_operations=operations,
        routing_strategy='polar_consecutive_spans_v1',
        span_semantics='first_segment <= last_segment < selected segment_count; counts sum to tendon_count',
        conditional_parameters='Segment and route overrides must exist in selected topology; per-span offsets match count',
        attachment_constraints=dict(local_frame='segment YZ plane; normalized station s',
            order='unique increasing stations; guides precede anchor; anchor on last selected segment',
            clearance='section envelope + tendon radius; pairwise tendon diameters; one owned hole per tendon',
            guides=[dict(envelope_halfsize_m=c.envelope_halfsize_m,hole_radius_m=c.hole_radius_m)
                for c in space.assembly.components if isinstance(c,Rigid) and c.kind=='guide']),
        numerical_support='Candidate-specific validation required; physical generation does not certify dynamics, control or task success')
    return result


def search_domains(space, query, grant):
    """Authorize the small mixed-search subspace; mesh is deliberately absent."""
    from tools.state_io import digest
    if query.family_space_identity!=digest(space):
        raise ValueError('FROZEN_FAMILY_SPACE_IDENTITY_MISMATCH')
    if query.method!=grant['method'] or not set(query.variable_groups)<=set(grant['variable_groups']):
        raise ValueError('UNAUTHORIZED_FAMILY_SEARCH_METHOD_OR_GROUP')
    if (not set(query.segment_counts)<=set(grant['segment_counts']) or
            not set(query.tendon_counts)<=set(grant['tendon_counts']) or
            query.max_proposals>grant['max_proposals'] or query.max_evaluations>grant['max_evaluations']):
        raise ValueError('SEARCH_OUTSIDE_FROZEN_NUMERICAL_SCOPE_OR_COUNT_CAP')
    for group,choices in (('segment_count',query.segment_counts),('tendon_count',query.tendon_counts),('spans',query.span_strategies)):
        if len(choices)>1 and group not in query.variable_groups:
            raise ValueError('MULTIPLE_CHOICES_REQUIRE_SELECTED_GROUP: '+group)
    domains={}
    prototypes={c['id']:c for c in space['assembly']['components']}
    for i in range(max(query.segment_counts)):
        d=space['segment_domains'].get(str(i),space['segment_domain'])
        for k in ('length_m','young_pa'):
            domains.setdefault(k,[]).append(d[k])
        proto=prototypes[space['serial_assembly']['root_segment' if i==0 else 'repeated_segment']]
        kinds=query.section_types or sorted({st['section']['kind'] for st in proto['sections']})
        for kind in kinds:
            if kind not in d['section_dimensions_m']:
                raise ValueError('SECTION_TYPE_OUTSIDE_FAMILY_DOMAIN')
            for k,v in d['section_dimensions_m'][kind].items():
                domains.setdefault('section.'+kind+'.'+k,[]).append(v)
    domains.update({'routing.'+k:[v] for k,v in space['routing_domains'].items()})
    groups=dict(length_m='lengths',young_pa='materials',section='sections',routing='routing')
    for key,(lo,hi) in query.bounds.items():
        if key not in domains or groups[key.split('.')[0]] not in query.variable_groups or any(
                not d['minimum']<=lo<hi<=d['maximum'] for d in domains[key]):
            raise ValueError('SEARCH_BOUND_OUTSIDE_SELECTED_PHYSICAL_DOMAIN: '+key)
    return {k:[max(d['minimum'] for d in values),min(d['maximum'] for d in values)] for k,values in domains.items()}
