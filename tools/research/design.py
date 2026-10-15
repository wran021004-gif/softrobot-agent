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
    family.checked_reach(inp)
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


