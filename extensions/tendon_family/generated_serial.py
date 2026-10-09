"""Rule-generated serial family v1. Stored templates remain historical fixtures."""
from copy import deepcopy
from typing import Literal
import math
import numpy as np
from pydantic import Field, FiniteFloat, model_validator
from schemas.common import Contract
from schemas.platform import SessionInput
from tools.platform_store import plain
from tools.state_io import digest
from .finite_templates import catalog
from .contracts import Design, Discretization

GENERATOR = 'serial_two_group_v1'
CONTROLLER_VERSION = '11.0.0'
BUILDER_VERSION = '3.0.0'


class Recipe(Contract):
    family: Literal['serial_two_group_v1'] = GENERATOR
    segment_count: int = Field(default=2, ge=2, le=4, strict=True)
    proximal_tendons: int = Field(default=3, ge=3, le=4, strict=True)
    distal_tendons: int = Field(default=3, ge=3, le=4, strict=True)
    lengths_m: list[FiniteFloat] = Field(default_factory=lambda: [.16, .11])
    section_scale: FiniteFloat = Field(default=1., ge=.95, le=1.05)
    routing_scale: FiniteFloat = Field(default=1., ge=.98, le=1.02)
    material: Literal['baseline', 'compliant', 'stiff'] = 'baseline'
    pretension_n: FiniteFloat = Field(default=.2, ge=0., le=8.)

    @model_validator(mode='after')
    def lengths(self):
        if len(self.lengths_m) != self.segment_count or any(l <= 0 for l in self.lengths_m):
            raise ValueError('ACTIVE_POSITIVE_LENGTH_VECTOR_REQUIRED')
        return self


class GeneratorSpace(Contract):
    recipe: Recipe
    # Public optimization owns free/fixed domains. This builder materializes an
    # already decoded recipe and accepts no undeclared per-execution edits.
    parameters: dict = Field(default_factory=dict)
    control_parameters: dict = Field(default_factory=dict)
    model_parameters: dict = Field(default_factory=dict)
    discretization_parameters: dict = Field(default_factory=dict)


def default_lengths(count, total=.27):
    if type(count) is not int or not 2 <= count <= 4:
        raise ValueError('SEGMENT_COUNT_INTEGER_2_TO_4_REQUIRED')
    if total <= .16:
        raise ValueError('DEFAULT_BASELINE_REQUIRES_TOTAL_GREATER_THAN_PROXIMAL_LENGTH')
    return [.16] + [(total-.16)/(count-1)]*(count-1)


def attachment(part, s=0., position=None):
    return dict(part=part, s=s, position_m=position or [0., 0., 0.], quaternion_wxyz=[1., 0., 0., 0.])


def generate(value):
    r=Recipe.model_validate(value)
    source=catalog()['templates']['T0']['design']
    parts={c['id']:deepcopy(c) for c in source['components']}
    near=parts['near'];far=parts['far'];mid=parts['mid_guide']
    # Three-tendon angles and anisotropic proximal guides are archived, not
    # replaced with a symmetric assumption. Four uses the declared T1 layout.
    layouts={3:source, 4:catalog()['templates']['T1']['design']}
    groups={}
    for group,count in [('near',r.proximal_tendons),('far',r.distal_tendons)]:
        groups[group]=[deepcopy(t) for t in layouts[count]['tendons'] if t['id'].startswith(group+'_')]
    mid['guide_holes']={}
    for group,tendons in groups.items():
        layout_mid=next(c for c in layouts[len(tendons)]['components'] if c['id']=='mid_guide')
        for i in range(len(tendons)):
            mid['guide_holes'][f'{group}_h{i}']=[v*r.routing_scale for v in layout_mid['guide_holes'][f'{group}_h{i}']]
    names=['near']+[f'distal{i+1}' for i in range(r.segment_count-1)]
    near['length_m']=r.lengths_m[0]
    components=[near,mid,parts['connector']]
    distal_total=sum(r.lengths_m[1:]);boundaries=np.r_[0.,np.cumsum(r.lengths_m[1:])/distal_total]
    def section_at(s):
        a,b=far['sections'][0]['section'],far['sections'][-1]['section']
        result=deepcopy(a)
        result['angle_rad']=a['angle_rad']+(b['angle_rad']-a['angle_rad'])*s
        result['parameters']={k:v+(b['parameters'][k]-v)*s for k,v in a['parameters'].items()}
        return result
    def route_at(t,s):
        # Distal taper is the piecewise-linear archived physical-position profile:
        # entrance hole at 0, old flexible guide at 0.5, terminal anchor at 1.
        points=[mid['guide_holes'][t['points'][2]['hole']],
                [v*r.routing_scale for v in t['points'][3]['attachment']['position_m']],
                [v*r.routing_scale for v in t['points'][4]['attachment']['position_m']]]
        return [float(np.interp(s,[0.,.5,1.],[p[j] for p in points])) for j in range(3)]
    for i,name in enumerate(names[1:]):
        part=deepcopy(far);part['id']=name;part['length_m']=r.lengths_m[i+1]
        part['connection']=deepcopy(far['connection']) if i==0 else attachment(f'boundary{i}')
        part['sections']=[dict(s=0.,section=section_at(boundaries[i])),dict(s=1.,section=section_at(boundaries[i+1]))]
        components.append(part)
        if i < len(names)-2:
            guide=deepcopy(mid);guide['id']=f'boundary{i+1}';guide['connection']=attachment(name,1.)
            guide['guide_holes']={f'far_h{j}':route_at(t,boundaries[i+1]) for j,t in enumerate(groups['far'])}
            components.append(guide)
    payload=parts['payload'];payload['connection']['part']=names[-1];components.append(payload)
    for c in components:
        if c['kind']=='flexible_segment':
            for station in c['sections']:
                station['section']['parameters']={k:v*r.section_scale for k,v in station['section']['parameters'].items()}
            c['physics']['young_pa']*=dict(baseline=1.,compliant=.9,stiff=1.1)[r.material]
    tendons=[];actuators=[]
    for group in ('near','far'):
        for j,t in enumerate(groups[group]):
            for point in t['points'][:2]:
                point['attachment']['position_m']=[v*r.routing_scale for v in point['attachment']['position_m']]
            if group=='far':
                points=deepcopy(t['points'][:3])
                for i,name in enumerate(names[1:]):
                    points.append(dict(role='guide',hole=None,attachment=attachment(name,.5,route_at(t,(boundaries[i]+boundaries[i+1])/2))))
                    if i<len(names)-2:
                        points.append(dict(role='guide',hole=f'far_h{j}',attachment=attachment(f'boundary{i+1}')))
                points.append(dict(role='anchor',hole=None,attachment=attachment(names[-1],1.,route_at(t,1.))))
                t['points']=points
            t['pretension_n']=r.pretension_n;t['force_limit_n']=8.
            tendons.append(t)
            actuator=deepcopy(source['actuators'][0]);actuator['id']=f'{group}_motor{j}'
            actuator['transmission']=[dict(tendon=t['id'],ratio=1.)];actuators.append(actuator)
    tip=deepcopy(source['tip'])
    design=dict(version='tendon_family_v1',id='generated_'+digest(plain(r))[:16],components=components,
        tendons=tendons,actuators=actuators,tip=tip,metadata=dict(generator=GENERATOR,recipe=plain(r),
            source_recipe='Archived executed-radius T0 profiles; T1 four-group layouts; physical distal positions',
            numerical_initialization=dict(source='initial_state_pretension',per_tendon_n=r.pretension_n,
                construction='Ordered candidate tendon pretensions, bounded by 0..8 N; projected zero state; all warm states regenerated'),
            physical_initialization='Every generated backend joint position and velocity is zero'))
    mesh=plain(Discretization(cells={names[0]:12,**{name:12//(r.segment_count-1) for name in names[1:]}}))
    design=plain(Design.model_validate(design))
    # Check pairwise guide clearance independently of compiler route ownership.
    for c in design['components']:
        if c['kind']!='guide':continue
        holes=list(c['guide_holes'].values());radius=c['hole_radius_m']
        if any(np.linalg.norm(np.array(a)-b)<2*radius for i,a in enumerate(holes) for b in holes[i+1:]):
            raise ValueError('GENERATED_GUIDE_HOLE_CLEARANCE')
        if any(abs(p[j])+radius>c['envelope_halfsize_m'][j]+1e-12 for p in holes for j in (1,2)):
            raise ValueError('GENERATED_GUIDE_ENVELOPE')
    from .compiler import resolve
    physics=resolve(design,mesh)
    if not np.allclose(physics['transmission'],np.eye(len(tendons))):
        raise ValueError('GENERATED_ONE_TO_ONE_TRANSMISSION')
    return design,mesh,physics


def check_robot(design,mesh):
    metadata=design.get('metadata',{})
    if metadata.get('generator')!=GENERATOR:raise ValueError('GENERATED_RECIPE_REQUIRED')
    expected,expected_mesh,physics=generate(metadata['recipe'])
    if design!=expected or plain(mesh)!=expected_mesh:raise ValueError('GENERATED_PHYSICAL_RECIPE_MISMATCH')
    return physics


def authorize(inp,space,changes):
    if changes:raise ValueError('GENERATED_RECIPE_ALREADY_RESOLVED_USE_DESIGN_OPTIMIZATION')
    space=GeneratorSpace.model_validate(space)
    expected,mesh,_=generate(space.recipe)
    if expected!=inp.robot.structure.data or mesh!=inp.policy.discretization.data:
        raise ValueError('GENERATED_BUILDER_RECIPE_MISMATCH')


def apply(inp,space,changes):
    authorize(inp,space,changes)
    checked_reach(inp)
    return inp.model_copy(deep=True)


def validate_initializer(before,after):
    from .backends import physics_for
    physics=physics_for(after)
    expected={field:{j:0. for j in physics['dofs']} for field in ('qpos_rad','qvel_rad_s')}
    expected['unspecified']='zero'
    if after.task.initializer.parameters.data!=expected:raise ValueError('GENERATED_PHYSICAL_ZERO_STATE_REQUIRED')


def checked_reach(inp):
    from .gvs_profile import ReachControl
    from .contracts import Initial
    inp=SessionInput.model_validate(inp);source=catalog()['scientific_source']
    physics=check_robot(inp.robot.structure.data,inp.policy.discretization.data)
    task=plain(inp.task);original=deepcopy(source['task'])
    for t in (task,original):
        for field in ('goal','initializer','timing'):t.pop(field)
    if task!=original or any(plain(getattr(inp.policy,k))!=source['policy'][k] for k in ('backend','dynamics_model')):
        raise ValueError('GENERATED_REACH_PHYSICAL_TASK_DOMAIN')
    control=ReachControl.model_validate(inp.policy.controller.parameters.data)
    if control.numerical_source!='initial_state_pretension':raise ValueError('GENERATED_EXPLICIT_PRETENSION_INITIALIZATION_REQUIRED')
    if plain(control.recipe.basis)!=source['policy']['controller']['parameters']['data']['recipe']['basis'] or not control.recipe.regenerate_warm_states:
        raise ValueError('GENERATED_STRUCTURAL_BASIS_AND_WARM_REGENERATION_REQUIRED')
    Initial.model_validate(inp.task.initializer.parameters.data);validate_initializer(inp,inp)
    t=inp.task.timing
    if t.sample_period_s!=t.control_period_s or control.settling.window_s>t.duration_s or any(
        abs(v-round(v))>1e-8 for v in (t.duration_s/t.control_period_s,t.control_period_s/t.timestep_s,control.settling.window_s/t.sample_period_s)):
        raise ValueError('GENERATED_REACH_TIMING_GRID')
    return control


def dimensions(inp):
    from .gvs_basis import resolve_basis
    from .gvs_profile import candidate_numerical,load_profile
    control=checked_reach(inp);physics=check_robot(inp.robot.structure.data,inp.policy.discretization.data)
    basis=resolve_basis(inp.robot.structure.data,control.recipe.basis)
    numerical=candidate_numerical(inp,control,load_profile())
    return dict(generator=GENERATOR,coordinate_order=list(basis.coordinate_order),backend_position_order=physics['dofs'],
        tendon_input_order=[t['entity'] for t in physics['tendons']],actuator_command_order=[a['id'] for a in physics['actuators']],
        dimensions=dict(reduced_coordinate=basis.dimension,reduced_state=2*basis.dimension,backend_position=len(physics['dofs']),
            backend_velocity=len(physics['dofs']),tendon_input=len(physics['tendons']),actuator_command=len(physics['actuators'])),
        transmission=physics['transmission'],force_limits_n=numerical['force_limits_n'],
        numerical_initialization=numerical,physical_initialization=inp.task.initializer.parameters.data)


def declarations():
    return dict(version='3.0.0',family=GENERATOR,segment_counts=[2,3,4],group_counts=[3,4],
        parameters=[],search='search.design_mixed@1.0.0',derived=['tendon_count','actuator_count','active_length_vector'],
        excluded=['coupled_actuation','arbitrary_graphs','mesh_optimization','motor_mass'])
