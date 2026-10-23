from tools.research.state import state,update,save
"""Immutable source-relative candidates and the existing bounded design search."""
from copy import deepcopy
import time
from schemas.platform import SessionInput
from tools.research.contracts import Parameters,TopologyParameters
from tools.platform_store import plain
from tools.state_io import read, digest
from extensions.tendon_family import generated_serial as family


def full_science(cfg):
    return dict(robot=deepcopy(cfg['robot']),task=deepcopy(cfg['task']),seed=cfg['seed'],
        policy={k:deepcopy(cfg['policy'][k]) for k in ('controller','backend','dynamics_model','discretization','candidate_builder')})


def source_lengths(cfg):
    return {p['id']:p['length_m'] for p in cfg['robot']['structure']['data']['components'] if p['kind']=='flexible_segment'}


def parameter_value(parameters,path):
    value=parameters
    for key in path.split('.'):
        value=value[key]
    return value


def set_parameter(parameters,path,value):
    parts=path.split('.')
    parent=parameters
    for key in parts[:-1]:
        parent=parent[key]
    parent[parts[-1]]=value


def configuration_for(host,parameters,owner):
    started=time.perf_counter()
    s=state(host)
    if s['spec'].get('start_mode')=='family_space':
        raise ValueError('FAMILY_SPACE_REQUIRES_GENERATE_ACTION')
    raw=plain(parameters)
    kind=TopologyParameters if raw.get('version')=='research_topology_parameters_v1' else Parameters
    p=plain(kind.model_validate(raw))
    grant=s['spec'].get('topology_authorization')
    if 'topology' in p and not grant:
        raise ValueError('TOPOLOGY_REQUIRES_EXPLICIT_FROZEN_STUDY_GRANT')
    source=s['nominal_configuration']
    if set(p['segments'])!=set(source_lengths(source)):
        raise ValueError('DECLARED_SEGMENT_IDENTITIES_REQUIRED')
    for key,(lo,hi) in s['spec']['allowed_parameters'].items():
        value=parameter_value(p,key)
        if value is None:
            segment=key.split('.')[1]
            scenario=p['segments'][segment]['material_scenario']
            part=next(c for c in source['robot']['structure']['data']['components'] if c['id']==segment)
            value=part['physics']['young_pa']*family.MATERIAL_MULTIPLIERS[scenario]
            p['segments'][segment].update(young_pa=value,material_scenario=None)
        if not lo<=value<=hi:
            raise ValueError('CANDIDATE_OUTSIDE_STUDY_GRANT: '+key)
    total=sum(v['length_m'] for v in p['segments'].values())
    constraint=s['spec'].get('length_constraint',{})
    if constraint.get('fixed_total_m') is not None and abs(total-constraint['fixed_total_m'])>1e-12:
        raise ValueError('CANDIDATE_FIXED_TOTAL_LENGTH')
    if constraint.get('aggregate_bounds_m') and not constraint['aggregate_bounds_m'][0]<=total<=constraint['aggregate_bounds_m'][1]:
        raise ValueError('CANDIDATE_AGGREGATE_LENGTH_CONSTRAINT')
    cfg=resolved_configuration(source,s['base_configuration'],p,owner,topology_grant=grant)
    elapsed=time.perf_counter()-started
    current=state(host)
    update(host,numerical_s=current['numerical_s']+elapsed,construction_numerical_s=current.get('construction_numerical_s',0.)+elapsed)
    return cfg,p


def resolved_configuration(source,base,p,owner,*,topology_grant=None):
    values=dict(source_design=source['robot']['structure']['data'],source_mesh=source['policy']['discretization']['data'],segments=p['segments'])
    if topology_grant:
        space=family.TopologyGeneratorSpace(**values,authorization=topology_grant,topology=p.get('topology',{}))
        robot,mesh,physics=family.generate_topology(space)
    else:
        if 'topology' in p:raise ValueError('TOPOLOGY_REQUIRES_EXPLICIT_FROZEN_STUDY_GRANT')
        space=family.GeneratorSpace(**values)
        robot,mesh,physics=family.generate(space)
    cfg=deepcopy(base)
    cfg['run_id']=owner
    cfg['robot']['structure']['data']=robot
    cfg['policy']['discretization']['data']=mesh
    cfg['policy']['candidate_builder']=dict(extension_id='candidate.family',version='4.0.0' if topology_grant else '3.0.0',
        parameters=dict(contract='family.topology_space' if topology_grant else 'family.generator_space',version='1.0.0',data=plain(space)))
    for key in ('holding_tip_speed_weight','terminal_tip_speed_weight'):
        cfg['policy']['controller']['parameters']['data']['recipe'][key]=p[key]
    expected={field:{j:0. for j in physics['dofs']} for field in ('qpos_rad','qvel_rad_s')}
    expected['unspecified']='zero'
    if cfg['task']['initializer']['parameters']['data']!=expected:
        raise ValueError('SOURCE_NAMED_ZERO_INITIALIZER_MISMATCH')
    inp=SessionInput.model_validate(cfg)
    family.checked_reach(inp,execution=False)
    return plain(inp)


def construct(host,parameters,provenance):
    s=state(host)
    cfg,values=configuration_for(host,parameters,host.run_id)
    scientific=full_science(cfg)
    identity=digest(dict(parameters=values,configuration=scientific,evaluation_profile=s['profile']))
    if identity in s['candidates']:
        ref=s['candidates'][identity]
        save(host,dict(candidate=ref,provenance=provenance,additional_scientific_executions=0),'candidate_reused')
        return ref
    p=values
    candidate=dict(candidate_id='core-'+identity,identity=identity,parameters=p,resolved_parameters=values,
        configuration_reference=save(host,cfg,'resolved_candidate_configuration'),
        configuration=cfg,scientific_configuration=scientific,task_identity=digest(cfg['task']),
        source_identity=digest(s.get('nominal_configuration',s['base_configuration'])),
        profile_identity=s['profile']['identity'],evaluation_version=s['profile']['version'],
        provenance=provenance,offline_trajectory=None)
    ref=save(host,candidate,'candidate_constructed')
    candidates=state(host)['candidates']
    candidates[identity]=ref
    update(host,candidates=candidates)
    return ref


def verify_candidate(host,reference):
    s=state(host)
    c=host.store.artifact(reference)
    if s['candidates'].get(c.get('identity'))!=plain(reference):
        raise ValueError('OWNED_RESOLVED_CANDIDATE_REQUIRED')
    if c['scientific_configuration']!=full_science(c['configuration']):
        raise ValueError('IMPORTED_CONFIGURATION_IDENTITY_MISMATCH')
    if plain(reference)==s.get('rl_source_candidate'):
        return c
    if plain(reference) in s.get('imported_candidates',[]):
        if c['profile_identity']!=s['imported_candidate_profile']['identity']:
            raise ValueError('HISTORICAL_PROFILE_MISMATCH')
        return c
    if c['profile_identity']!=s['profile']['identity']:
        raise ValueError('OLD_EVALUATION_PROFILE_CANDIDATE_REQUIRES_NEW_CONSTRUCTION')
    if c.get('generation_version') in ('serial_family_generation_v1','serial_family_generation_v2'):
        if (host.store.artifact(c['configuration_reference'])!=c['configuration'] or
                c['family_space_identity']!=s['spec']['family_space_identity'] or
                c['task_identity']!=s['spec']['canonical_task_identity'] or
                c['effective_task_identity']!=digest(c['configuration']['task']) or
                c['identity']!=family_candidate_identity(c['configuration'],s)):
            raise ValueError('FAMILY_CANDIDATE_IDENTITY_MISMATCH')
        if s['spec'].get('fidelity_policy') and any(c.get(k)!=v for k,v in numerical_binding(c['configuration'],s['spec']).items()):
            raise ValueError('CANDIDATE_FIDELITY_BINDING_MISMATCH')
        return c
    if s['spec'].get('nominal_source'):
        if host.store.artifact(c['configuration_reference'])!=c['configuration'] or c['source_identity']!=digest(s['nominal_configuration']):
            raise ValueError('SAVED_CANONICAL_CONFIGURATION_OR_SOURCE_MISMATCH')
        if c['parameters']!=c['resolved_parameters'] or c['task_identity']!=digest(c['configuration']['task']):
            raise ValueError('SAVED_PARAMETER_TASK_IDENTITY_MISMATCH')
        expected=digest(dict(parameters=c['resolved_parameters'],configuration=c['scientific_configuration'],evaluation_profile=s['profile']))
        if expected!=c['identity']:
            raise ValueError('CANDIDATE_IDENTITY_MISMATCH')
        # Artifact reads and verification do not regenerate physics or incur a new calculation.
        return c
    cfg,values=configuration_for(host,c['parameters'],host.run_id)
    if values!=c['resolved_parameters'] or full_science(cfg)!=c['scientific_configuration']:
        raise ValueError('FULL_FIXED_AND_SEARCH_PARAMETER_IDENTITY_MISMATCH')
    if digest(dict(parameters=values,configuration=full_science(cfg),evaluation_profile=s['profile']))!=c['identity']:
        raise ValueError('CANDIDATE_IDENTITY_MISMATCH')
    return c


def family_candidate_identity(cfg,s):
    science=full_science(cfg)
    science['policy'].pop('candidate_builder')  # Request spelling is provenance, not physical identity.
    return digest(dict(configuration=science,family_space_identity=s['spec']['family_space_identity'],
        canonical_task_identity=s['spec']['canonical_task_identity'],evaluation_profile=s['profile']))


def numerical_binding(cfg, spec):
    physical=digest(cfg['robot']['structure']['data'])
    model=digest(dict(physical_design_identity=physical,policy={k:cfg['policy'][k] for k in
        ('discretization','dynamics_model','backend')},basis=cfg['policy']['controller']['parameters']['data']['recipe']['basis']))
    return dict(physical_design_identity=physical,numerical_model_identity=model,
        effective_discretization=cfg['policy']['discretization'],
        fidelity_policy_identity=digest(spec['fidelity_policy']) if spec.get('fidelity_policy') else None,
        final_evaluation_identity=spec.get('final_evaluation_identity'))


def final_fidelity_matches(spec, candidate):
    """Legacy studies retain their original frozen execution semantics."""
    policy=spec.get('fidelity_policy')
    if not policy:
        return True
    cfg=candidate['configuration'];final=policy['final_evaluation']
    return (candidate.get('fidelity_policy_identity')==digest(policy) and
        candidate.get('final_evaluation_identity')==spec['final_evaluation_identity'] and
        cfg['policy']['backend']==spec['configuration']['policy']['backend'] and
        set(cfg['policy']['discretization']['data']['cells'].values())=={final['cells_per_segment']} and
        candidate['task_identity']==spec['canonical_task_identity'])


def final_generation_request(spec, candidate):
    """Copy exact physical choices to the frozen final mesh; never dispatch work."""
    if not spec.get('fidelity_policy') or candidate.get('generation_version')!='serial_family_generation_v2':
        return None
    request=deepcopy(candidate['parameters'])
    cells=spec['fidelity_policy']['final_evaluation']['cells_per_segment']
    for i in range(request['segment_count']):
        request.setdefault('segments',{}).setdefault(str(i),{})['cells']=cells
    return request


def generate_candidate(host,request,provenance,*,screening_fidelity=None):
    """Materialize a frozen family request and persist through the existing Store."""
    from extensions.tendon_family.family_space import parse_build, UnsupportedGeneration
    from extensions.tendon_family.gvs_profile import mathematical_numerical
    from tools.platform_tasks import compile_input
    s=state(host);spec=s['spec']
    if spec.get('start_mode')!='family_space':raise ValueError('FROZEN_FAMILY_SPACE_REQUIRED')
    started=time.perf_counter()
    try:
        request=deepcopy(plain(request))
        if screening_fidelity is not None:
            level=spec.get('fidelity_policy',{}).get('screening',{}).get(screening_fidelity)
            if level is None:
                raise ValueError('UNAUTHORIZED_SCREENING_FIDELITY')
            for i in range(request['segment_count']):
                segment=request.setdefault('segments',{}).setdefault(str(i),{})
                if segment.get('cells',level['cells_per_segment'])!=level['cells_per_segment']:
                    raise ValueError('SCREENING_MESH_CONFLICT')
                segment['cells']=level['cells_per_segment']
        build=parse_build(dict(space=spec['family_space'],request=plain(request)))
        robot,mesh,physics=family.generate_family(build)
        cfg=deepcopy(s['base_configuration']);cfg['run_id']=host.run_id
        cfg['robot'].update(sources=['frozen family-space assembly prototypes'])
        cfg['robot']['structure']['data']=robot
        cfg['policy']['discretization']['data']=mesh
        serial=build.request.version=='serial_family_generation_v2'
        cfg['policy']['candidate_builder']=dict(extension_id='candidate.family',version='6.0.0' if serial else '5.0.0',
            parameters=dict(contract='family.serial_space_build_v2' if serial else 'family.serial_space_build',version='1.0.0',data=plain(build)))
        for key,d in build.space.control_domains.items():
            cfg['policy']['controller']['parameters']['data']['recipe'][key]=build.request.control_weights.get(key,d.default)
        if serial:
            from tools.research.config import patch
            control=cfg['policy']['controller']['parameters']['data']
            for field,edits in (('recipe',build.request.controller_recipe),('solver',build.request.controller_solver)):
                if field=='recipe' and cfg['policy']['controller']['extension_id']=='controller.gvs_nmpc':
                    from extensions.tendon_family.contracts import GVSTrajectoryParameters
                    for key in edits:
                        if key not in control[field] and key in GVSTrajectoryParameters.model_fields:
                            control[field][key]=GVSTrajectoryParameters.model_fields[key].default
                if edits:control[field]=patch(control[field],edits)
        initial={f:{j:0. for j in physics['dofs']} for f in ('qpos_rad','qvel_rad_s')};initial['unspecified']='zero'
        cfg['task']['initializer']['parameters']['data']=initial
        cfg=plain(SessionInput.model_validate(cfg))
        compile_input(cfg,host.reg)
        numerical=mathematical_numerical(SessionInput.model_validate(cfg))
        identity=family_candidate_identity(cfg,s)
        dimensions=dict(physical_dofs=len(physics['dofs']),gvs_coordinates=len(numerical['coordinate_order']),
            state=len(numerical['measured_initial_state']),inputs=len(numerical['tendon_order']))
        resolved=dict(segments=[c for c in robot['components'] if c['kind']=='flexible_segment'],
            tendons=robot['tendons'],actuators=robot['actuators'],discretization=mesh,
            tendon_order=numerical['tendon_order'],actuator_order=[a['id'] for a in robot['actuators']],
            force_limits_n=numerical['force_limits_n'],dimensions=dimensions,
            controller_preparation=dict(status='candidate_initial_projection_and_pretension_ready',
                coordinate_order=numerical['coordinate_order'],warm_input_shape=[len(numerical['warm_guess']['tensions']),dimensions['inputs']],
                model_constructed=False,rollout_executed=False))
        resolved['capabilities']=dict(declarative=True,materialized=True,physically_compiled=True,
            gvs_basis_resolved=True,gvs_model_built=False,gvs_dynamics_evaluated=False,
            controller_update_tested=False,complete_task_evaluated=False)
        if identity in s['candidates']:
            ref=s['candidates'][identity]
            save(host,dict(candidate=ref,request=plain(request),provenance=provenance),'candidate_reused')
        else:
            candidate=dict(candidate_id='core-'+identity,identity=identity,parameters=plain(request),resolved_parameters=resolved,
                configuration_reference=save(host,cfg,'resolved_candidate_configuration'),configuration=cfg,
                scientific_configuration=full_science(cfg),task_identity=spec['canonical_task_identity'],
                effective_task_identity=digest(cfg['task']),initialization_provenance=dict(
                    rule=spec['candidate_initialization'],effective=initial,canonical_task_identity=spec['canonical_task_identity']),
                family_space_identity=spec['family_space_identity'],generation_version=build.request.version,
                source_identity=spec['family_space_identity'],source_provenance=plain(build.space.assembly)['provenance'],
                profile_identity=s['profile']['identity'],evaluation_version=s['profile']['version'],
                physical_validation='compiled',unchecked=['controllability','task feasibility',*build.space.unsupported],
                provenance=provenance,offline_trajectory=None)
            if spec.get('fidelity_policy'):
                candidate.update(numerical_binding(cfg,spec),screening_fidelity=screening_fidelity)
            ref=save(host,candidate,'candidate_constructed')
            update(host,candidates={**state(host)['candidates'],identity:ref})
        return dict(status='generated',candidate=ref,resolved=resolved,task_success=None)
    except UnsupportedGeneration as exc:
        return dict(status='not_yet_supported',unsupported_capability=str(exc),candidate=None,task_success=None)
    except ValueError as exc:
        diagnostic=deepcopy(getattr(exc,'diagnostic',dict(status='unavailable',reason='No structured facts captured by this check')))
        reference=save(host,dict(request=request,reason=str(exc),diagnostic=diagnostic,
            scientific_acceptance='unmeasured'),'generation_failure')
        return dict(status='invalid',reason=str(exc),candidate=None,task_success=None,
            diagnostic={**diagnostic,'raw_reference':reference,'read_pointer':'/diagnostic'},
            scientific_acceptance='unmeasured')
    finally:
        elapsed=time.perf_counter()-started;current=state(host)
        update(host,numerical_s=current['numerical_s']+elapsed,
            construction_numerical_s=current.get('construction_numerical_s',0.)+elapsed)


