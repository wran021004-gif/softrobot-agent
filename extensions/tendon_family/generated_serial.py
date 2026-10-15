"""Source-based physical candidates; the retired template generator lives in Git history."""
from copy import deepcopy
from typing import Literal
import numpy as np
from pydantic import Field, FiniteFloat, model_validator
from schemas.common import Contract
from schemas.platform import SessionInput
from tools.platform_store import plain
from .contracts import Design,Discretization,Initial,Tendon,Actuator,Name
from schemas.environment_spec import Vec3

MATERIAL_MULTIPLIERS=dict(baseline=1.,compliant=.9,stiff=1.1)


class GeneratorSpace(Contract):
    source_design: dict
    source_mesh: dict
    segments: dict


class TopologyPatch(Contract):
    version: Literal['tendon_topology_patch_v1'] = 'tendon_topology_patch_v1'
    remove_tendons: list[Name] = Field(default_factory=list)
    upsert_tendons: list[Tendon] = Field(default_factory=list)
    guide_holes: dict[Name,dict[str,Vec3]] = Field(default_factory=dict)

    @model_validator(mode='after')
    def unique_edits(self):
        ids=[t.id for t in self.upsert_tendons]
        if len(set(ids))!=len(ids) or len(set(self.remove_tendons))!=len(self.remove_tendons) or set(ids)&set(self.remove_tendons):
            raise ValueError('UNIQUE_DISJOINT_TOPOLOGY_EDITS_REQUIRED')
        return self


class TopologyAuthorization(Contract):
    version: Literal['tendon_topology_grant_v1']
    tendon_count_bounds: tuple[int,int]
    tendon_bounds: dict[str,tuple[FiniteFloat,FiniteFloat]]
    attachment_bounds_m: dict[Name,tuple[Vec3,Vec3]]
    editable_guides: list[Name]
    actuator_rule: Literal['copy_source_independent_displacement_v1']

    @model_validator(mode='after')
    def bounds(self):
        lo,hi=self.tendon_count_bounds
        if not 1<=lo<=hi or set(self.tendon_bounds)!={'diameter_m','force_limit_n','pretension_n','length_servo_gain_n_m'}:
            raise ValueError('EXPLICIT_TOPOLOGY_BOUNDS_REQUIRED')
        if any(a>b or a<0 for a,b in self.tendon_bounds.values()) or any(
                any(a>b for a,b in zip(lower,upper)) for lower,upper in self.attachment_bounds_m.values()):
            raise ValueError('INVALID_TOPOLOGY_BOUNDS')
        return self


class TopologyGeneratorSpace(GeneratorSpace):
    authorization: TopologyAuthorization
    topology: TopologyPatch = Field(default_factory=TopologyPatch)


def _patched_topology(space):
    """Only explicit routes/holes change; survivor order precedes new patch order."""
    design=deepcopy(space.source_design);patch=space.topology;grant=space.authorization
    source=Design.model_validate(design)
    if len(source.tendons)!=6 or len(source.actuators)!=6:
        raise ValueError('SIX_TENDON_FROZEN_SOURCE_REQUIRED')
    tendons={t.id:plain(t) for t in source.tendons}
    actuators={}
    for a in source.actuators:
        if a.command_type!='displacement' or len(a.transmission)!=1 or a.transmission[0].ratio!=1:
            raise ValueError('SOURCE_INDEPENDENT_DISPLACEMENT_REQUIRED')
        key=a.transmission[0].tendon
        if key not in tendons or key in actuators:raise ValueError('SOURCE_ONE_TO_ONE_ACTUATORS_REQUIRED')
        actuators[key]=plain(a)
    for name in patch.remove_tendons:
        if name not in tendons:raise ValueError('UNKNOWN_REMOVED_TENDON: '+name)
        del tendons[name];del actuators[name]
    for tendon in patch.upsert_tendons:
        tendons[tendon.id]=plain(tendon)
        if tendon.id not in actuators:
            a=plain(source.actuators[0]);a['id']=tendon.id+'_motor'
            a['transmission']=[dict(tendon=tendon.id,ratio=1.)]
            actuators[tendon.id]=plain(Actuator.model_validate(a))
    components={c['id']:c for c in design['components']}
    for name,holes in patch.guide_holes.items():
        if name not in grant.editable_guides or name not in components or components[name]['kind']!='guide':
            raise ValueError('GUIDE_EDIT_OUTSIDE_TOPOLOGY_GRANT')
        components[name]['guide_holes'].update({key:list(pos) for key,pos in holes.items()})
    lo,hi=grant.tendon_count_bounds
    if not lo<=len(tendons)<=hi:raise ValueError('TENDON_COUNT_OUTSIDE_TOPOLOGY_GRANT')
    used_holes=set()
    for t in tendons.values():
        for key,(lo,hi) in grant.tendon_bounds.items():
            if not lo<=t[key]<=hi:raise ValueError('TENDON_PARAMETER_OUTSIDE_TOPOLOGY_GRANT: '+key)
        for p in t['points']:
            a=p['attachment'];bounds=grant.attachment_bounds_m.get(a['part'])
            if bounds is None or any(not lo<=v<=hi for v,lo,hi in zip(a['position_m'],*bounds)):
                raise ValueError('ATTACHMENT_OUTSIDE_TOPOLOGY_GRANT')
            if components.get(a['part'],{}).get('kind')=='guide' and not p['hole']:
                raise ValueError('M3_GUIDE_REQUIRES_NAMED_HOLE')
            if p['hole']:
                hole=(a['part'],p['hole'])
                if hole in used_holes:raise ValueError('M3_SINGLE_TENDON_PER_GUIDE_HOLE')
                used_holes.add(hole)
    design['tendons']=list(tendons.values())
    design['actuators']=[actuators[t] for t in tendons]
    return design


def generate_topology(value):
    space=TopologyGeneratorSpace.model_validate(value)
    return _generate(space,_patched_topology(space))


def generate(value):
    space=GeneratorSpace.model_validate(value)
    if len(space.source_design['tendons'])!=6 or len(space.source_design['actuators'])!=6:
        raise ValueError('TWO_SEGMENT_SIX_INDEPENDENT_TENSION_SCOPE')
    return _generate(space,deepcopy(space.source_design))


def _generate(space,design):
    mesh=plain(Discretization.model_validate(space.source_mesh))
    parts={p['id']:p for p in design['components'] if p['kind']=='flexible_segment'}
    if len(parts)!=2 or set(parts)!=set(space.segments):
        raise ValueError('TWO_DECLARED_FLEXIBLE_SEGMENTS_REQUIRED')
    for name,values in space.segments.items():
        part=parts[name];part['length_m']=values['length_m']
        if part['physics']['mode']!='material':raise ValueError('CONTINUOUS_MODULUS_REQUIRES_MATERIAL_AUTHORITY')
        young=values['young_pa']
        if young is None:young=part['physics']['young_pa']*MATERIAL_MULTIPLIERS[values['material_scenario']]
        part['physics']['young_pa']=young
        if set(values['sections'])!={str(i) for i in range(len(part['sections']))}:raise ValueError('EXACT_STATION_IDS_REQUIRED')
        for i,station in enumerate(part['sections']):
            dimensions=values['sections'][str(i)]
            if set(dimensions)!=set(station['section']['parameters']):raise ValueError('EXACT_SECTION_DIMENSIONS_REQUIRED')
            station['section']['parameters']=dict(dimensions)
    design=plain(Design.model_validate(design))
    # Preserve guide ownership, pairwise clearance and fixed routing coordinates.
    for part in design['components']:
        if part['kind']!='guide':continue
        holes=list(part['guide_holes'].values());radius=part['hole_radius_m']
        if any(np.linalg.norm(np.array(a)-b)<2*radius for i,a in enumerate(holes) for b in holes[i+1:]):
            raise ValueError('GUIDE_HOLE_CLEARANCE')
        if any(abs(p[j])+radius>part['envelope_halfsize_m'][j]+1e-12 for p in holes for j in (1,2)):
            raise ValueError('GUIDE_ENVELOPE')
    from .compiler import resolve
    physics=resolve(design,mesh)
    if not np.allclose(physics['transmission'],np.eye(len(design['tendons']))):raise ValueError('ONE_TO_ONE_TRANSMISSION_REQUIRED')
    return design,mesh,physics


def authorize(inp,space,changes):
    if changes:raise ValueError('SOURCE_CANDIDATE_ALREADY_RESOLVED')
    builder=inp.policy.candidate_builder
    topology=(builder.version,builder.parameters.contract,builder.parameters.version)==('4.0.0','family.topology_space','1.0.0')
    family_space=builder.version=='5.0.0' and builder.parameters.contract=='family.serial_space_build'
    design,mesh,_=(generate_family if family_space else generate_topology if topology else generate)(space)
    if design!=inp.robot.structure.data or mesh!=inp.policy.discretization.data:raise ValueError('SOURCE_CANDIDATE_BINDING_MISMATCH')


def apply(inp,space,changes):
    authorize(inp,space,changes);checked_reach(inp)
    return inp.model_copy(deep=True)


def validate_initializer(before,after):
    from .backends import physics_for
    p=physics_for(after)
    expected={f:{j:0. for j in p['dofs']} for f in ('qpos_rad','qvel_rad_s')};expected['unspecified']='zero'
    if after.task.initializer.parameters.data!=expected:raise ValueError('NAMED_ZERO_STATE_REQUIRED')


def checked_reach(inp):
    from .gvs_profile import ReachControl
    inp=SessionInput.model_validate(inp)
    authorize(inp,inp.policy.candidate_builder.parameters.data,{})
    control=ReachControl.model_validate(inp.policy.controller.parameters.data)
    if control.numerical_source!='initial_state_pretension' or not control.recipe.regenerate_warm_states:
        raise ValueError('CANDIDATE_PRETENSION_AND_CURRENT_STATE_REGENERATION_REQUIRED')
    Initial.model_validate(inp.task.initializer.parameters.data);validate_initializer(inp,inp)
    timing=inp.task.timing
    if timing.sample_period_s!=timing.control_period_s or control.settling.window_s>timing.duration_s or any(
        abs(v-round(v))>1e-8 for v in (timing.duration_s/timing.control_period_s,timing.control_period_s/timing.timestep_s,control.settling.window_s/timing.sample_period_s)):
        raise ValueError('REACH_TIMING_GRID')
    return control


def declarations():
    return dict(scope='two flexible segments, six independent tensions',parameters=['segment lengths','section station dimensions','continuous Young modulus'],
        future=['variable tendon count and explicit routes','variable segment count and conditional optimization'])


def topology_declarations():
    return dict(scope='two source-relative flexible segments; explicitly granted independent tendon topology',
        parameters=['segment lengths','section station dimensions','continuous Young modulus','versioned explicit tendon/guide-hole patch'],
        ordering='source survivors in order; replacements keep index; additions in patch order; corresponding independent actuators',
        assumptions='one tendon per named guide hole; fixed explicit offsets; straight frictionless spans; ideal tension',
        future=['nonlinear closed-loop comparisons','variable segment count'])


def generate_family(value):
    """Expand independent polar routes over the two-segment assembly prototypes."""
    from .family_space import FamilyBuild, Span, validate_request
    from .sections import properties
    build=FamilyBuild.model_validate(value);space=build.space;r=build.request
    validate_request(space,r)
    components=plain(space.assembly)['components']
    segments=[c for c in components if c['kind']=='flexible_segment']
    if [c['id'] for c in segments]!=['segment_0','segment_1']:
        raise ValueError('INDEXED_TWO_SEGMENT_ASSEMBLY_REQUIRED')
    guides=[c for c in components if c['kind']=='guide']
    if len(guides)!=1 or guides[0]['connection']['part']!='segment_0':
        raise ValueError('C1_REQUIRES_ONE_INTERSEGMENT_GUIDE')
    guide=guides[0];guide['guide_holes']={}
    for i,part in enumerate(segments):
        domain=space.segment_domains.get(i,space.segment_domain);choice=r.segments.get(i)
        for key in ('length_m','young_pa'):
            d=getattr(domain,key);v=getattr(choice,key) if choice else None
            v=d.check(d.default if v is None else v,key)
            (part['physics'] if key=='young_pa' else part)[key]=v
        if choice and choice.sections is not None:
            if len(choice.sections)!=len(part['sections']):raise ValueError('EXACT_SECTION_STATIONS_REQUIRED')
            for station,section in zip(part['sections'],choice.sections):station['section']=plain(section)
        for station in part['sections']:
            section=station['section'];dims=domain.section_dimensions_m.get(section['kind'])
            if dims is None or set(dims)!=set(section['parameters']):raise ValueError('SECTION_OUTSIDE_FAMILY_DOMAIN')
            for key,v in section['parameters'].items():dims[key].check(v,key)
            properties(section)
    tendon_values={k:r.tendon_parameters.get(k,d.default) for k,d in space.tendon_domains.items()}
    if tendon_values['pretension_n']>tendon_values['force_limit_n']:raise ValueError('PRETENSION_EXCEEDS_PHYSICAL_FORCE_LIMIT')
    tendons=[];actuators=[];attachments={}
    def point(part,s,position,role,hole=None):
        return dict(attachment=dict(part=part,s=s,position_m=position),role=role,hole=hole)
    def yz(radius,angle):return [0.,radius*float(np.cos(angle)),radius*float(np.sin(angle))]
    spans=r.spans or [Span(last_segment=1,count=r.tendon_count)]
    for span in spans:
        bounds=space.routing_domains
        radius=bounds['radius_m'].check(span.radius_m if span.radius_m is not None else bounds['radius_m'].default,'radius_m')
        anchor=bounds['anchor_s'].check(span.anchor_s if span.anchor_s is not None else bounds['anchor_s'].default,'anchor_s')
        stations=span.guide_s if span.guide_s is not None else [bounds['guide_s'].default]
        if stations!=sorted(set(stations)):raise ValueError('ORDERED_UNIQUE_GUIDE_STATIONS_REQUIRED')
        for s in stations:bounds['guide_s'].check(s,'guide_s')
        if stations and max(stations)>=anchor:raise ValueError('GUIDES_MUST_PRECEDE_ANCHOR')
        bounds['phase_rad'].check(span.phase_rad,'phase_rad')
        for a in [*span.angular_offsets_rad,span.guide_angle_offset_rad,span.anchor_angle_offset_rad]:
            bounds['angular_offset_rad'].check(a,'angular_offset_rad')
        for j in range(span.count):
            index=len(tendons);name='tendon_'+str(index)
            angle=span.phase_rad+2*np.pi*j/span.count+(span.angular_offsets_rad[j] if span.angular_offsets_rad else 0.)
            route=[]
            if span.first_segment==0:route.append(point('fixed_base',0.,yz(radius,angle),'start'))
            for i in range(span.first_segment,span.last_segment+1):
                if i==1:
                    hole=name+'_hole';guide['guide_holes'][hole]=yz(radius,angle+span.guide_angle_offset_rad)
                    route.append(point(guide['id'],0.,[0.,0.,0.],'start' if span.first_segment==1 else 'guide',hole))
                for s in stations:route.append(point(segments[i]['id'],s,yz(radius,angle+span.guide_angle_offset_rad),'guide'))
            route.append(point(segments[span.last_segment]['id'],anchor,yz(radius,angle+span.anchor_angle_offset_rad),'anchor'))
            if index in r.route_overrides:route=[plain(p) for p in r.route_overrides[index]]
            # Explicit overrides retain span ownership, local radial and station bounds.
            order=[]
            for p in route:
                a=p['attachment'];part=a['part']
                if part.startswith('segment_'):
                    i=next((k for k,c in enumerate(segments) if c['id']==part),-1)
                    if not span.first_segment<=i<=span.last_segment:raise ValueError('ROUTE_OUTSIDE_SELECTED_SPAN')
                    if p.get('hole') or a['position_m'][0]!=0:raise ValueError('LOCAL_SECTION_PLANE_REQUIRED')
                    bounds['anchor_s' if p['role']=='anchor' else 'guide_s'].check(a['s'],'route_station')
                    distance=np.linalg.norm(a['position_m'][1:]);bounds['radius_m'].check(distance,'route_radius_m')
                    envelope=max(np.linalg.norm(properties(st['section'])['outer_yz_m'],axis=1).max() for st in segments[i]['sections'])
                    if distance<envelope+tendon_values['diameter_m']/2:raise ValueError('SECTION_ROUTE_CLEARANCE')
                    order.append(i+a['s'])
                elif part==guide['id']:
                    if p.get('hole')!=name+'_hole' or p['role'] not in ('start','guide'):
                        raise ValueError('NAMED_OWNED_GUIDE_HOLE_REQUIRED')
                    order.append(1.)
                elif part=='fixed_base' and span.first_segment==0 and p['role']=='start':
                    if a['s'] or a['position_m'][0]!=0:raise ValueError('BASE_SECTION_PLANE_REQUIRED')
                    bounds['radius_m'].check(np.linalg.norm(a['position_m'][1:]),'base_radius_m');order.append(0.)
                else:raise ValueError('ROUTE_ATTACHMENT_OUTSIDE_FAMILY')
            if order!=sorted(set(order)) or route[0]['attachment']['part']!=('fixed_base' if span.first_segment==0 else guide['id']) or route[-1]['attachment']['part']!=segments[span.last_segment]['id']:
                raise ValueError('ORDERED_SELECTED_SPAN_REQUIRED')
            for p in route:
                a=p['attachment']
                position=guide['guide_holes'][p['hole']] if p.get('hole') else a['position_m']
                station=(a['part'],a['s']);previous=attachments.setdefault(station,[])
                if any(np.linalg.norm(np.asarray(position)-old)<tendon_values['diameter_m'] for old in previous):
                    raise ValueError('TENDON_ATTACHMENT_CLEARANCE')
                previous.append(position)
            tendons.append(dict(id=name,points=route,**tendon_values))
            actuators.append(dict(id='actuator_'+str(index),command_type='displacement',units='m',
                limits=space.actuator_defaults.limits_m,velocity_limit=space.actuator_defaults.velocity_limit_m_s,
                transmission=[dict(tendon=name,ratio=1.)]))
    used={p['hole'] for t in tendons for p in t['points'] if p.get('hole')}
    guide['guide_holes']={k:v for k,v in guide['guide_holes'].items() if k in used}
    design=dict(id='serial_family_candidate',components=components,tendons=tendons,actuators=actuators,tip=plain(space.assembly.tip))
    values={c['id']:dict(length_m=c['length_m'],young_pa=c['physics']['young_pa'],
        sections={str(i):st['section']['parameters'] for i,st in enumerate(c['sections'])}) for c in segments}
    result=_generate(GeneratorSpace(source_design=design,source_mesh=plain(space.assembly.mesh),segments=values),design)
    from .geometry import geometry
    geometry(result[2],[0.]*len(result[2]['dofs']))  # Reject zero-length resolved spans.
    return result


def family_declarations():
    return dict(contract='serial_family_space_v1',execution='two segments; bounded independent tendon counts',
        routing='polar consecutive spans with explicit local stations and optional typed route overrides',
        future=['variable segment construction and numerical compatibility (M3-C2)'])
