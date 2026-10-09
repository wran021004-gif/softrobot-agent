"""Finite V2 serial layouts, public grants, and named initialization.

The four committed designs are complete templates, not a topology optimizer.
Continuous changes are relative to the selected template, whose T0 already
contains the executed 1.01/0.99 routing changes.
"""
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
from schemas.platform import SessionInput
from tools.platform_store import plain
from tools.state_io import digest
from .contracts import Space, Design, Discretization

ASSET = 'extensions/tendon_family/profiles/finite_templates_v2.json'
BUILDER_VERSION = '2.0.0'
CONTROLLER_VERSION = '10.0.0'


def catalog():
    return json.loads((Path(__file__).resolve().parents[2]/ASSET).read_text(encoding='utf8'))


def template_id(design):
    key = design.get('metadata', {}).get('finite_template', 'T0')
    if key not in catalog()['templates']:raise ValueError('FINITE_TEMPLATE_UNKNOWN')
    return key


def specifications(key):
    design=catalog()['templates'][key]['design']
    specs={}
    for component in design['components']:
        if component['kind']!='flexible_segment':continue
        name=component['id'];length=component['length_m']
        specs[f'components/{name}/length_m']=dict(type='number',bounds=[.95*length,1.05*length],unit='m')
        specs[f'design/{name}_section_scale']=dict(type='number',bounds=[.95,1.05],unit='1')
        specs[f'design/{name}_material_scenario']=dict(type='choice',options=['baseline','compliant','stiff'],unit='1')
        specs[f'design/{name}_routing_radius_scale']=dict(type='number',bounds=[.98,1.02],unit='1')
    for name in ('holding_tip_speed_weight','terminal_tip_speed_weight'):
        specs['control/recipe/'+name]=dict(type='number',bounds=[.025,.1],unit='1')
    return specs


def declarations():
    from .parameter_capabilities import routing_declarations
    value=routing_declarations()
    value['version']='2.0.0'
    rows=[]
    existing={r['id']:r for r in value['parameters']}
    for path in dict.fromkeys(p for key in catalog()['templates'] for p in specifications(key)):
        prototype=existing.get(path) or existing.get(path.replace('middle','far'))
        row=deepcopy(prototype)
        row['id']=path
        if 'middle' in path:
            row['components']=['middle']
            row['meaning']=row['meaning'].replace('far','middle')
            row['effective_locations']=[p.replace('far','middle') for p in row['effective_locations']]
        row.update(task_families=['task.reach'],controller_versions=[CONTROLLER_VERSION],
            per_template_domains={k:specifications(k)[path] for k in catalog()['templates'] if path in specifications(k)},
            applicable_templates=[k for k in catalog()['templates'] if path in specifications(k)])
        if row['operation'] in ('section_scale','material_scenario','routing_radius_scale'):
            row['meaning'] += '; V2 source is the selected executed-radius template, and 1/baseline preserves it.'
        rows.append(row)
    rows.insert(0,dict(id='template',kind='physical_design',type='choice',unit='1',
        operation='complete_template',components=['selected complete serial design'],
        meaning='Named complete finite design and template-owned mesh; categorical explicit enumeration only.',
        schema='family.space:templates',legal_domain=dict(options=list(catalog()['templates'])),
        task_families=['task.reach'],controller_versions=[CONTROLLER_VERSION],
        effective_locations=['robot/structure/data','policy/discretization'],
        coupled_constraints=['Independent one-to-one actuator/tendon mapping; ideal tension only.',
            'T2/T3 split distal region into explicitly initialized middle/far components.',
            'Template-specific lengths and continuous parameter ownership apply.'],
        derived_quantities=['all physical/reduced/backend/input dimensions and orderings']))
    value['parameters']=rows
    value['integration_backlog']=[r for r in value['integration_backlog'] if r['id'] not in
        ('segment_count','tendon_count','tendon_layout','discretization/cells')]
    value['integration_backlog'].extend([
        dict(id='arbitrary_topology',reason='Only T0-T3 complete templates and their owned meshes supported.'),
        dict(id='coupled_actuation',reason='Independent tension input bypasses motor execution; coupled drives are unsupported.')])
    value['templates']={k:{f:v for f,v in t.items() if f!='design'} for k,t in catalog()['templates'].items()}
    return value


def study_input(effective, grants=None):
    """Add finite capability without mutating the exact T0 robot/task/recipe."""
    result=deepcopy(plain(effective));value=catalog()
    if result['robot']!=value['scientific_source']['robot']:
        raise ValueError('V2_ENTRY_REQUIRES_EXACT_EXECUTED_T0_ROBOT')
    space=dict(parameters={'template':dict(type='choice',options=list(value['templates']))},
        control_parameters={},model_parameters={},discretization_parameters={},semantic_decisions={},
        semantic_source=value['templates']['T0']['design'],
        templates={k:t['design'] for k,t in value['templates'].items()},
        template_discretizations={k:t['discretization'] for k,t in value['templates'].items()})
    for key in value['templates']:
        for path,spec in specifications(key).items():
            group='control_parameters' if path.startswith('control/') else 'parameters'
            if path not in space[group]:space[group][path]=deepcopy(spec)
            elif spec['type']=='number':
                bounds=space[group][path]['bounds']
                bounds[:]=[min(bounds[0],spec['bounds'][0]),max(bounds[1],spec['bounds'][1])]
    if grants is not None:
        for group in ('parameters','control_parameters'):
            space[group]={p:{**s,**deepcopy(grants[p])} for p,s in space[group].items() if p in grants}
        options=space['parameters'].get('template',{}).get('options',[])
        if not options or set(options)-set(value['templates']):raise ValueError('FINITE_TEMPLATE_GRANT_REQUIRED')
        space['templates']={k:t for k,t in space['templates'].items() if k in options}
        space['template_discretizations']={k:t for k,t in space['template_discretizations'].items() if k in options}
    result['policy']['candidate_builder']=dict(extension_id='candidate.family',version=BUILDER_VERSION,
        parameters=dict(contract='family.space',version='1.0.0',data=space))
    result['policy']['controller']['version']=CONTROLLER_VERSION
    result['policy']['editable']={p:s['bounds'] for group in ('parameters','control_parameters')
        for p,s in space[group].items() if s['type']=='number'}
    return SessionInput.model_validate(result).model_dump(mode='json')


def selected_space(inp,space,changes):
    """Intersect the session grant with the selected template's physical domain."""
    from .candidate import check_value
    space=Space.model_validate(space)
    key=changes.get('template',template_id(inp.robot.structure.data))
    value=catalog()
    if key not in space.templates:raise ValueError('TEMPLATE_NOT_AUTHORIZED')
    if (plain(space.templates[key])!=value['templates'][key]['design'] or
            plain(space.template_discretizations.get(key))!=value['templates'][key]['discretization']):
        raise ValueError('FINITE_TEMPLATE_DEFINITION_CHANGED')
    legal=specifications(key);parameters={};control={};decisions={}
    for path,grant in {**space.parameters,**space.control_parameters}.items():
        if path=='template':continue
        if path not in legal:
            if path in changes:raise ValueError('PARAMETER_INACTIVE_FOR_TEMPLATE: '+path)
            continue
        spec=deepcopy(legal[path])
        if spec['type']=='number':
            spec['bounds']=[max(spec['bounds'][0],grant['bounds'][0]),min(spec['bounds'][1],grant['bounds'][1])]
            if spec['bounds'][0]>spec['bounds'][1]:continue
        else:spec['options']=[v for v in spec['options'] if v in grant['options']]
        if path in changes:check_value(path,changes[path],spec,{})
        (control if path.startswith('control/') else parameters)[path]=spec
        if path.startswith('design/'):
            name=path[7:].split('_',1)[0];operation=path.split('_',1)[1]
            decisions[path]=dict(operation=operation,components=[name],
                baseline_value='baseline' if operation=='material_scenario' else 1.)
    # Templates select the physical source; absolute scaling never compounds.
    return key,Space.model_validate(dict(parameters=parameters,control_parameters=control,
        semantic_decisions=decisions,semantic_source=value['templates'][key]['design'],
        templates=plain(space.templates),template_discretizations=plain(space.template_discretizations)))


def authorize(inp,space,changes):
    from .candidate import authorize as standard
    declared={r['id'] for r in declarations()['parameters']}
    if set(changes)-declared:raise ValueError('RESEARCH_PARAMETER_CAPABILITY_UNAVAILABLE')
    if inp.task.family!='task.reach' or inp.policy.controller.version!=CONTROLLER_VERSION:
        raise ValueError('FINITE_TEMPLATES_REQUIRE_REACH_V10')
    standard(inp,space,changes)
    selected_space(inp,space,changes)


def semantic_expand(data,space,changes):
    from .routing_radius import expand_routing
    # An untouched complete template retains its exact bytes, including T0 metadata.
    if not any(p.startswith('design/') for p in changes):return
    metadata=data.setdefault('metadata',{})
    metadata['design_decisions']=dict(selections=deepcopy(metadata.get('v2_selections',{})))
    expand_routing(data,space,changes)
    metadata['v2_selections']=deepcopy(metadata['design_decisions']['selections'])


def semantic_initialization(design,mesh,basis_specification,*,bends=None,rates=None):
    """Named region integrated curvature/rate -> candidate basis -> backend joints.

    Axes are segment local y/z. Distal split halves share constant curvature;
    each receives its length fraction of the named distal region's integrated bend.
    """
    from .compiler import resolve
    from .gvs_basis import resolve_basis
    from .gvs_projection import discretize,project
    from .geometry import geometry
    key=template_id(design);regions=catalog()['templates'][key]['initialization']['regions']
    bends=bends or {name:[0.,0.] for name in regions}
    rates=rates or {name:[0.,0.] for name in regions}
    if set(bends)!=set(regions) or set(rates)!=set(regions):raise ValueError('NAMED_INITIAL_REGIONS_REQUIRED')
    physics=resolve(design,mesh);basis=resolve_basis(design,basis_specification)
    q=np.zeros(basis.dimension);v=np.zeros_like(q);integrated={}
    for region,names in regions.items():
        total=sum(s.length_m for s in basis.segments if s.segment in names)
        for local in basis.segments:
            if local.segment not in names:continue
            b=np.asarray(bends[region],dtype=float);r=np.asarray(rates[region],dtype=float)
            if b.shape!=(2,) or r.shape!=(2,) or not np.isfinite(np.r_[b,r]).all():raise ValueError('FINITE_BEND_RATE_REQUIRED')
            count=len(local.knots)
            for axis in range(2):
                q[local.start+axis*count:local.start+(axis+1)*count]=b[axis]/total
                v[local.start+axis*count:local.start+(axis+1)*count]=r[axis]/total
            integrated[local.segment]=dict(bend_rad=(b*local.length_m/total).tolist(),rate_rad_s=(r*local.length_m/total).tolist())
    position,velocity=discretize(physics,basis,q,v)
    projection=project(physics,basis,position,velocity)
    return dict(initial=dict(qpos_rad=dict(zip(physics['dofs'],position.tolist())),
        qvel_rad_s=dict(zip(physics['dofs'],velocity.tolist())),unspecified='zero'),
        region_bends_rad=bends,region_rates_rad_s=rates,segment_integrals=integrated,
        axes='physical segment local y/z; positive right-hand curvature; integrated curvature in rad',
        initial_tip_pose=geometry(physics,position)['tip'].tolist(),projection=projection)


def apply(inp,space,changes):
    from .candidate import apply as standard
    authorize(inp,space,changes)
    key,selected=selected_space(inp,space,changes)
    original_editable=deepcopy(inp.policy.editable)
    active={**selected.parameters,**selected.control_parameters}
    inp=inp.model_copy(update={'policy':inp.policy.model_copy(update={
        'editable':{p:tuple(s['bounds']) for p,s in active.items() if s['type']=='number'}})})
    result=standard(inp,selected,changes,semantic_expander=semantic_expand)
    initialization=semantic_initialization(result.robot.structure.data,result.policy.discretization.data,
        result.policy.controller.parameters.data['recipe']['basis'])
    if key!='T0':
        result.task.initializer.parameters.data.clear()
        result.task.initializer.parameters.data.update(initialization['initial'])
    return result.model_copy(update={'policy':result.policy.model_copy(update={'editable':original_editable})})


def validate_initializer(before,after):
    """Only semantic zero bends/rates are authorized in this frozen template entry."""
    initial=before.task.initializer.parameters.data
    if any(v!=0 for field in ('qpos_rad','qvel_rad_s') for v in initial.get(field,{}).values()):
        raise ValueError('FINITE_TEMPLATE_ENTRY_REQUIRES_ARCHIVED_ZERO_INITIALIZATION')
    expected=semantic_initialization(after.robot.structure.data,after.policy.discretization.data,
        after.policy.controller.parameters.data['recipe']['basis'])['initial']
    if after.task.initializer.parameters.data!=expected:raise ValueError('FINITE_NAMED_INITIALIZER_MISMATCH')


def check_robot(design,mesh):
    """Exact finite topology with the declared continuous physical changes only."""
    from .routing_radius import normalize
    from .design_decisions import normalize_supported
    key=template_id(design);template=catalog()['templates'][key]
    if plain(mesh)!=template['discretization']:raise ValueError('FINITE_TEMPLATE_MESH_MISMATCH')
    candidate=deepcopy(design);source=deepcopy(template['design'])
    normalize(candidate,source)
    normalize_supported(candidate,source)
    for d in (candidate,source):
        d.get('metadata',{}).pop('design_decisions',None)
        d.get('metadata',{}).pop('v2_selections',None)
    if candidate!=source:raise ValueError('UNSUPPORTED_FINITE_TOPOLOGY_OR_PHYSICS')
    from .compiler import resolve
    physics=resolve(design,mesh)
    matrix=np.asarray(physics['transmission'])
    if matrix.shape!=(len(design['tendons']),len(design['tendons'])) or not np.allclose(matrix,np.eye(len(matrix))):
        raise ValueError('FINITE_CONTROLLER_REQUIRES_INDEPENDENT_ONE_TO_ONE_INPUTS')
    return key


def checked_reach(inp):
    """Version 10 technical domain; recipe algorithm remains inherited V7."""
    from .gvs_profile import ReachControl
    from .backends import physics_for
    from .contracts import Initial
    inp=SessionInput.model_validate(inp);value=catalog();source=value['scientific_source']
    key=check_robot(inp.robot.structure.data,inp.policy.discretization.data)
    if inp.task.family!='task.reach':raise ValueError('FINITE_REACH_TASK_REQUIRED')
    task=plain(inp.task);original=deepcopy(source['task'])
    for x in (task,original):
        for field in ('goal','initializer','timing'):x.pop(field)
    if task!=original or any(plain(getattr(inp.policy,k))!=source['policy'][k] for k in ('backend','dynamics_model')):
        raise ValueError('FINITE_REACH_FROZEN_PHYSICAL_TASK_DOMAIN')
    if (inp.task.goal.contract!=source['task']['goal']['contract'] or
            inp.task.initializer.extension_id!=source['task']['initializer']['extension_id']):
        raise ValueError('FINITE_REACH_GOAL_OR_INITIALIZER_CONTRACT')
    control=ReachControl.model_validate(inp.policy.controller.parameters.data)
    if plain(control.recipe.basis)!=source['policy']['controller']['parameters']['data']['recipe']['basis']:
        raise ValueError('FINITE_REACH_STRUCTURAL_BASIS_REQUIRED')
    if not control.recipe.regenerate_warm_states:raise ValueError('MEASURED_WARM_REGENERATION_REQUIRED')
    initial=Initial.model_validate(inp.task.initializer.parameters.data);physics=physics_for(inp)
    for values,limit in ((initial.qpos_rad,.05),(initial.qvel_rad_s,.5)):
        if set(values)-set(physics['dofs']) or any(not np.isfinite(v) or abs(v)>limit for v in values.values()):
            raise ValueError('FINITE_REACH_SMALL_NAMED_INITIAL_STATE_REQUIRED')
    timing=inp.task.timing
    if timing.sample_period_s!=timing.control_period_s or control.settling.window_s>timing.duration_s or any(
            abs(v-round(v))>1e-8 for v in (timing.duration_s/timing.control_period_s,
                timing.control_period_s/timing.timestep_s,control.settling.window_s/timing.sample_period_s)):
        raise ValueError('FINITE_REACH_TIMING_GRID_REQUIRED')
    return control


def dimensions(inp):
    from .backends import physics_for
    from .gvs_basis import resolve_basis
    from .gvs_profile import candidate_numerical,load_profile
    control=checked_reach(inp);physics=physics_for(inp)
    basis=resolve_basis(inp.robot.structure.data,control.recipe.basis)
    numerical=candidate_numerical(inp,control,load_profile())
    return dict(template=template_id(inp.robot.structure.data),
        component_order=[c['id'] for c in inp.robot.structure.data['components']],
        coordinate_order=list(basis.coordinate_order),
        state_order=[*basis.coordinate_order,*[p+'.rate' for p in basis.coordinate_order]],
        backend_position_order=physics['dofs'],backend_velocity_order=physics['dofs'],
        tendon_input_order=[t['entity'] for t in physics['tendons']],
        actuator_command_order=[a['id'] for a in physics['actuators']],
        dimensions=dict(reduced_coordinate=basis.dimension,reduced_state=2*basis.dimension,
            backend_position=len(physics['dofs']),backend_velocity=len(physics['dofs']),
            tendon_input=len(physics['tendons']),actuator_command=len(physics['actuators'])),
        force_limits_n=numerical['force_limits_n'],numerical_initialization=numerical,
        transmission=physics['transmission'],execution_model='ideal_tension',
        enforced='0 <= tendon force <= candidate force_limit_n',
        merely_declared='actuator travel, velocity, transmission and length-servo specifications; bypassed during ideal-tension execution')
