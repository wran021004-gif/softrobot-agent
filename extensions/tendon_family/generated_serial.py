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
    design,mesh,_=(generate_topology if topology else generate)(space)
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
