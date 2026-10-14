"""Source-based physical candidates; the retired template generator lives in Git history."""
from copy import deepcopy
import numpy as np
from pydantic import Field
from schemas.common import Contract
from schemas.platform import SessionInput
from tools.platform_store import plain
from .contracts import Design,Discretization,Initial

MATERIAL_MULTIPLIERS=dict(baseline=1.,compliant=.9,stiff=1.1)


class GeneratorSpace(Contract):
    source_design: dict
    source_mesh: dict
    segments: dict


def generate(value):
    space=GeneratorSpace.model_validate(value)
    design=deepcopy(space.source_design);mesh=plain(Discretization.model_validate(space.source_mesh))
    parts={p['id']:p for p in design['components'] if p['kind']=='flexible_segment'}
    if len(parts)!=2 or len(design['tendons'])!=6 or len(design['actuators'])!=6 or set(parts)!=set(space.segments):
        raise ValueError('TWO_SEGMENT_SIX_INDEPENDENT_TENSION_SCOPE')
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
    design,mesh,_=generate(space)
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
