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


def _generate(space,design,*,serial=False):
    mesh=plain(Discretization.model_validate(space.source_mesh))
    parts={p['id']:p for p in design['components'] if p['kind']=='flexible_segment'}
    if (not serial and len(parts)!=2) or set(parts)!=set(space.segments):
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
    family_space=(builder.version,builder.parameters.contract) in (
        ('5.0.0','family.serial_space_build'),('6.0.0','family.serial_space_build_v2'),('7.0.0','family.serial_space_build_v3'))
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


def checked_control(inp, *, execution=True):
    from .gvs_profile import ReachControl
    inp=SessionInput.model_validate(inp)
    if inp.policy.controller.extension_id == 'controller.sorosim_matlab_nmpc':
        from .sorosim_control import SorosimReachControl
        ReachControl = SorosimReachControl
    authorize(inp,inp.policy.candidate_builder.parameters.data,{})
    control=ReachControl.model_validate(inp.policy.controller.parameters.data)
    if control.numerical_source!='initial_state_pretension' or not control.recipe.regenerate_warm_states:
        raise ValueError('CANDIDATE_PRETENSION_AND_CURRENT_STATE_REGENERATION_REQUIRED')
    Initial.model_validate(inp.task.initializer.parameters.data);validate_initializer(inp,inp)
    from tools.research_tasks import task_adapter
    reference = task_adapter(plain(inp)).control_reference()
    if getattr(control.recipe, 'reference_mode', 'constant') != reference['kind']:
        raise ValueError('CONTROL_REFERENCE_MODE_MUST_MATCH_TASK')
    tracking = inp.task.family == 'task.tracking'
    if tracking:
        if (inp.policy.controller.extension_id, inp.policy.controller.version) != ('controller.gvs_nmpc', '12.0.0'):
            raise ValueError('TRACKING_CONTROLLER_UNSUPPORTED')
        if execution and inp.task.status != 'development_valid':
            raise ValueError('TRACKING_REQUIRES_REVIEWED_DEVELOPMENT_TASK')
        if control.settling is not None or any((control.recipe.holding_tip_speed_weight,
                control.recipe.terminal_tip_speed_weight, control.recipe.velocity_weight,
                control.recipe.terminal_velocity_weight)):
            raise ValueError('TRACKING_HAS_NO_REACH_HOLDING_OR_ABSOLUTE_SPEED_COST')
    elif inp.task.family in ('task.position_tool_axis','task.oriented_tracking'):
        if (inp.policy.backend.version!=('1.4.0' if inp.task.family=='task.oriented_tracking' else '1.3.0') or inp.policy.controller.version!='12.0.0' or control.settling is not None):
            raise ValueError('TOOL_AXIS_REQUIRES_NATIVE_SEQUENCE_BACKEND_WITHOUT_REACH_SETTLING')
    elif control.settling is None:
        raise ValueError('REACH_SETTLING_REQUIRED')
    timing=inp.task.timing
    if inp.policy.controller.extension_id=='controller.gvs_nmpc':
        control.recipe.replan_steps(timing.control_period_s)
    grid = [timing.duration_s/timing.control_period_s,timing.control_period_s/timing.timestep_s]
    if control.settling is not None:
        grid.append(control.settling.window_s/timing.sample_period_s)
    if timing.sample_period_s!=timing.control_period_s or (control.settling is not None and control.settling.window_s>timing.duration_s) or any(
        abs(v-round(v))>1e-8 for v in grid):
        raise ValueError('REACH_TIMING_GRID')
    return control


# Historical public entry point used by retained Reach routes.
checked_reach = checked_control


def declarations():
    return dict(scope='two flexible segments, six independent tensions',parameters=['segment lengths','section station dimensions','continuous Young modulus'],
        future=['variable tendon count and explicit routes','variable segment count and conditional optimization'])


def topology_declarations():
    return dict(scope='two source-relative flexible segments; explicitly granted independent tendon topology',
        parameters=['segment lengths','section station dimensions','continuous Young modulus','versioned explicit tendon/guide-hole patch'],
        ordering='source survivors in order; replacements keep index; additions in patch order; corresponding independent actuators',
        assumptions='one tendon per named guide hole; fixed explicit offsets; straight frictionless spans; ideal tension',
        future=['nonlinear closed-loop comparisons','variable segment count'])


class GeometryFailure(ValueError):
    """Facts captured by the authoritative construction check, not a re-check."""
    def __init__(self, reason, diagnostic):
        super().__init__(reason)
        self.diagnostic=diagnostic


def v3_default_routes(space, request):
    """A symmetric base-to-distal proposal; never a task-success assumption."""
    bounds=space.routing_domains
    return [dict(anchor_segment=request.segment_count-1,anchor_s=bounds['anchor_s'].default,
        segments=[dict(radius_m=bounds['radius_m'].default,angle_rad=2*np.pi*j/request.tendon_count,
            guide_s=bounds['guide_s'].default) for _ in range(request.segment_count)])
        for j in range(request.tendon_count)]


def v3_clearance(segments, paths, diameter):
    """Conservative straight-chord clearance, including between sampled stations."""
    from .sections import properties
    def closest(a,b):
        delta=b-a;den=float(delta@delta)
        t=0. if den==0 else min(1.,max(0.,-float(a@delta)/den))
        return float(np.linalg.norm(a+t*delta))
    def at(path,s):
        for (a,x),(b,y) in zip(path,path[1:]):
            if s<=b+1e-12:return x+(y-x)*(s-a)/(b-a)
        return path[-1][1]
    for i,segment in enumerate(segments):
        envelope=max(np.linalg.norm(properties(st['section'])['outer_yz_m'],axis=1).max() for st in segment['sections'])
        active=[p[i] for p in paths if i in p]
        for path in active:
            if any(closest(a[1],b[1]) < envelope+diameter/2-1e-12 for a,b in zip(path,path[1:])):
                raise ValueError('V3_SECTION_ROUTE_CLEARANCE')
        for n,a in enumerate(active):
            for b in active[n+1:]:
                end=min(a[-1][0],b[-1][0]);knots=sorted({0.,end,*[s for s,_ in a if s<end],*[s for s,_ in b if s<end]})
                if any(closest(at(a,x)-at(b,x),at(a,y)-at(b,y)) < diameter-1e-12 for x,y in zip(knots,knots[1:])):
                    raise ValueError('V3_TENDON_PATH_CLEARANCE')


def generate_family(value):
    """Expand polar spans; v1 preserves its assembly, v2 expands named prototypes."""
    from .family_space import parse_build, Span, validate_request, FamilyBuildV2, FamilyBuildV3, UnsupportedGeneration
    from .sections import properties
    build=parse_build(value);space=build.space;r=build.request
    validate_request(space,r)
    serial=isinstance(build,FamilyBuildV2);v3=isinstance(build,FamilyBuildV3)
    if serial:
        components,mesh,tip=serial_components(space,r)
    else:
        components=plain(space.assembly)['components']
        mesh=plain(space.assembly.mesh);tip=plain(space.assembly.tip)
    segments=[c for c in components if c['kind']=='flexible_segment']
    if not serial and [c['id'] for c in segments]!=['segment_0','segment_1']:
        raise ValueError('INDEXED_TWO_SEGMENT_ASSEMBLY_REQUIRED')
    guides=[c for c in components if c['kind']=='guide']
    if not serial and (len(guides)!=1 or guides[0]['connection']['part']!='segment_0'):
        raise ValueError('C1_REQUIRES_ONE_INTERSEGMENT_GUIDE')
    guides_by_segment={i:guides[i-1] for i in range(1,len(segments))}
    guides_by_id={g['id']:g for g in guides}
    for guide in guides:guide['guide_holes']={}
    for i,part in enumerate(segments):
        domain=space.segment_domains.get(i,space.segment_domain);choice=r.segments.get(i)
        edits=getattr(choice,'physical_parameters',{}) if choice else {}
        for key,v in edits.items():
            if key not in domain.physical_domains:raise ValueError('UNDECLARED_SEGMENT_PHYSICS: '+key)
            domain.physical_domains[key].check(v,key)
            if key=='density_kg_m3':part['physics'][key]=v
            elif key.startswith('viscosity_') or key.startswith('curvature_'):
                field='bending_viscosity_nm2_s' if key.startswith('viscosity_') else 'natural_curvature_rad_m'
                target=part['physics'] if key.startswith('viscosity_') else part
                values=list(target[field]);values[0 if '_y_' in key else 1]=v;target[field]=values
        for key in ('length_m','young_pa'):
            d=getattr(domain,key);v=getattr(choice,key) if choice else None
            v=d.check(d.default if v is None else v,key)
            (part['physics'] if key=='young_pa' else part)[key]=v
        if choice and choice.sections is not None:
            if len(choice.sections)!=len(part['sections']):raise ValueError('EXACT_SECTION_STATIONS_REQUIRED')
            for station,section in zip(part['sections'],choice.sections):station['section']=plain(section)
        for station in part['sections']:
            if 'section_angle_rad' in edits:station['section']['angle_rad']=edits['section_angle_rad']
            section=station['section'];dims=domain.section_dimensions_m.get(section['kind'])
            if 'section_angle_rad' in domain.physical_domains:
                domain.physical_domains['section_angle_rad'].check(section['angle_rad'],'section_angle_rad')
            if dims is None or set(dims)!=set(section['parameters']):raise ValueError('SECTION_OUTSIDE_FAMILY_DOMAIN')
            for key,v in section['parameters'].items():dims[key].check(v,key)
            properties(section)
    tendon_values={k:r.tendon_parameters.get(k,d.default) for k,d in space.tendon_domains.items()}
    if tendon_values['pretension_n']>tendon_values['force_limit_n']:raise ValueError('PRETENSION_EXCEEDS_PHYSICAL_FORCE_LIMIT')
    tendons=[];actuators=[];attachments={}
    def point(part,s,position,role,hole=None):
        return dict(attachment=dict(part=part,s=s,position_m=position),role=role,hole=hole)
    def yz(radius,angle):return [0.,radius*float(np.cos(angle)),radius*float(np.sin(angle))]
    routes_v3=[plain(v) for v in r.routes] if v3 and r.routes else v3_default_routes(space,r) if v3 else []
    if v3:
        # The compact clearance model below assumes coaxial, unrotated serial
        # interfaces. Other mount geometry needs a different physical analysis.
        for part in components:
            if part['id']=='payload':continue
            c=part['connection']
            if c['quaternion_wxyz']!=[1.,0.,0.,0.] or any(abs(x)>1e-12 for x in c['position_m'][1:]):
                raise UnsupportedGeneration('V3_REQUIRES_COAXIAL_UNROTATED_SERIAL_INTERFACES')
        if any(g['hole_radius_m'] < tendon_values['diameter_m']/2 for g in guides):
            raise ValueError('V3_GUIDE_HOLE_TOO_SMALL')
    v3_paths=[]
    spans=([Span(last_segment=x['anchor_segment'],count=1,phase_rad=x['segments'][0]['angle_rad'],
        radius_m=x['segments'][0]['radius_m'],guide_s=[x['segments'][0]['guide_s']],anchor_s=x['anchor_s']) for x in routes_v3]
        if v3 else r.spans or [Span(last_segment=len(segments)-1,count=r.tendon_count)])
    for span_index,span in enumerate(spans):
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
            selected=routes_v3[index] if v3 else None
            if v3:
                for seg in selected['segments']:
                    bounds['radius_m'].check(seg['radius_m'],'route_radius_m')
                    bounds['phase_rad'].check(seg['angle_rad'],'route_angle_rad')
                    bounds['guide_s'].check(seg['guide_s'],'guide_s')
                bounds['anchor_s'].check(selected['anchor_s'],'anchor_s')
            if span.first_segment==0:route.append(point('fixed_base',0.,yz(radius,angle),'start'))
            for i in range(span.first_segment,span.last_segment+1):
                seg=selected['segments'][i] if v3 else None
                seg_radius=seg['radius_m'] if v3 else radius
                seg_angle=seg['angle_rad'] if v3 else angle+span.guide_angle_offset_rad
                seg_stations=[seg['guide_s']] if v3 else stations
                if i>0:
                    guide=guides_by_segment[i]
                    hole=name+'_hole';guide['guide_holes'][hole]=yz(seg_radius,seg_angle)
                    route.append(point(guide['id'],0.,[0.,0.,0.],'start' if span.first_segment==i else 'guide',hole))
                for s in seg_stations:route.append(point(segments[i]['id'],s,yz(seg_radius,seg_angle),'guide'))
            last=selected['segments'][-1] if v3 else None
            route.append(point(segments[span.last_segment]['id'],anchor,yz(last['radius_m'],last['angle_rad']) if v3 else yz(radius,angle+span.anchor_angle_offset_rad),'anchor'))
            if v3:
                paths={}
                for i,seg in enumerate(selected['segments']):
                    v=np.asarray(yz(seg['radius_m'],seg['angle_rad'])[1:])
                    end=(np.asarray(yz(selected['segments'][i+1]['radius_m'],selected['segments'][i+1]['angle_rad'])[1:]) if i<span.last_segment else v)
                    paths[i]=[(0.,v),(seg['guide_s'],v),(1. if i<span.last_segment else anchor,end)]
                v3_paths.append(paths)
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
                elif part in guides_by_id:
                    i=next(k for k,g in guides_by_segment.items() if g['id']==part)
                    if not max(1,span.first_segment)<=i<=span.last_segment:
                        raise ValueError('GUIDE_OUTSIDE_SELECTED_SPAN')
                    if p.get('hole')!=name+'_hole' or p['role'] not in ('start','guide'):
                        raise ValueError('NAMED_OWNED_GUIDE_HOLE_REQUIRED')
                    order.append(float(i))
                elif part=='fixed_base' and span.first_segment==0 and p['role']=='start':
                    if a['s'] or a['position_m'][0]!=0:raise ValueError('BASE_SECTION_PLANE_REQUIRED')
                    bounds['radius_m'].check(np.linalg.norm(a['position_m'][1:]),'base_radius_m');order.append(0.)
                else:raise ValueError('ROUTE_ATTACHMENT_OUTSIDE_FAMILY')
            if order!=sorted(set(order)) or route[0]['attachment']['part']!=('fixed_base' if span.first_segment==0 else guides_by_segment[span.first_segment]['id']) or route[-1]['attachment']['part']!=segments[span.last_segment]['id']:
                raise ValueError('ORDERED_SELECTED_SPAN_REQUIRED')
            for point_index,p in enumerate(route):
                a=p['attachment']
                position=guides_by_id[a['part']]['guide_holes'][p['hole']] if p.get('hole') else a['position_m']
                station=(a['part'],a['s']);previous=attachments.setdefault(station,[])
                paths=([f'/route_overrides/{index}/{point_index}'] if index in r.route_overrides else
                    [f'/spans/{span_index}'] if r.spans else ['/tendon_count','/spans'])
                facts=dict(tendon=name,position_m=position,request_paths=paths,
                    polar_angle_rad=None if index in r.route_overrides else angle,
                    point_index=point_index)
                for old in previous:
                    distance=float(np.linalg.norm(np.asarray(position)-old['position_m']))
                    if distance<tendon_values['diameter_m']:
                        raise GeometryFailure('TENDON_ATTACHMENT_CLEARANCE',dict(
                            status='available',constraint='tendon_attachment_clearance',
                            station=dict(part=a['part'],s=a['s']),local_frame='attachment part YZ plane',
                            attachments=[old,facts],actual_distance_m=distance,
                            required_distance_m=tendon_values['diameter_m']))
                previous.append(facts)
            tendons.append(dict(id=name,points=route,**tendon_values))
            actuators.append(dict(id='actuator_'+str(index),command_type='displacement',units='m',
                limits=space.actuator_defaults.limits_m,velocity_limit=space.actuator_defaults.velocity_limit_m_s,
                transmission=[dict(tendon=name,ratio=1.)]))
    if v3:v3_clearance(segments,v3_paths,tendon_values['diameter_m'])
    used={p['hole'] for t in tendons for p in t['points'] if p.get('hole')}
    for guide in guides:guide['guide_holes']={k:v for k,v in guide['guide_holes'].items() if k in used}
    design=dict(id='serial_family_candidate',components=components,tendons=tendons,actuators=actuators,tip=tip)
    values={c['id']:dict(length_m=c['length_m'],young_pa=c['physics']['young_pa'],
        sections={str(i):st['section']['parameters'] for i,st in enumerate(c['sections'])}) for c in segments}
    result=_generate(GeneratorSpace(source_design=design,source_mesh=mesh,segments=values),design,serial=serial)
    from .geometry import geometry
    geometry(result[2],[0.]*len(result[2]['dofs']))  # Reject zero-length resolved spans.
    return result


def serial_components(space,request):
    """One chain from explicit frozen prototype roles; IDs belong to the candidate."""
    rule=space.serial_assembly
    prototypes={c['id']:c for c in plain(space.assembly)['components']}
    components=[];cells={}
    for i in range(request.segment_count):
        part=deepcopy(prototypes[rule.root_segment if i==0 else rule.repeated_segment])
        part['id']='segment_'+str(i)
        if i:
            guide=deepcopy(prototypes[rule.guide]);guide['id']='guide_'+str(i)
            guide['connection']['part']='segment_'+str(i-1)
            connector=deepcopy(prototypes[rule.connector]);connector['id']='connector_'+str(i)
            connector['connection']['part']=guide['id']
            part['connection']['part']=connector['id']
            components.extend([guide,connector])
        choice=request.segments.get(i)
        count=choice.cells if choice and choice.cells is not None else rule.default_cells
        if not rule.cell_count_bounds[0]<=count<=rule.cell_count_bounds[1]:
            raise ValueError('CELLS_OUTSIDE_FAMILY_DOMAIN')
        cells[part['id']]=count
        components.append(part)
    payload=deepcopy(prototypes[rule.payload])
    payload['connection']['part']='segment_'+str(request.segment_count-1)
    components.append(payload)
    mesh=plain(space.assembly.mesh);mesh['cells']=cells
    return components,mesh,plain(space.assembly.tip)


def family_declarations():
    return dict(contract='serial_family_space_v1',execution='two segments; bounded independent tendon counts',
        routing='polar consecutive spans with explicit local stations and optional typed route overrides',
        future=['variable segment construction and numerical compatibility (M3-C2)'])


def serial_declarations():
    return dict(contract='serial_family_space_v2',execution='declared serial segment and tendon domains subject to physical checks',
        routing='consecutive spans; independent angular offsets and typed route overrides',
        numerical='candidate-specific compatibility; no task-feasibility claim')


def serial_v3_declarations():
    return dict(contract='serial_family_space_v3',execution='base-anchored piecewise paths subject to conservative physical clearance checks',
        routing='one fixed-base start, explicit per-segment polar path and one flexible-segment anchor',
        numerical='coaxial unrotated serial interfaces; ideal frictionless model; no task-feasibility claim')
