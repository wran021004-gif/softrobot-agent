"""Immutable source-relative candidates and the existing bounded design search."""
from copy import deepcopy
import time
from schemas.platform import SessionInput
from schemas.research_core import Parameters, Search
from schemas.design_optimization import DesignOptimizationProblem
from tools.platform_store import plain
from tools.state_io import read, digest
from extensions.tendon_family import generated_serial as family


def state(host):
    return host.store.session(host.run_id)['state']


def update(host, **values):
    with host.store.transaction() as db:
        current=host.store.session(host.run_id,db)['state'];current.update(values)
        host.store.update_state(db,host.run_id,current)


def save(host,value,kind):
    with host.store.transaction() as db:
        ref=host.store.put(db,value);host.store.event(db,host.run_id,kind,'saved',outputs=[ref])
        return plain(ref)


def full_science(cfg):
    return dict(robot=deepcopy(cfg['robot']),task=deepcopy(cfg['task']),seed=cfg['seed'],
        policy={k:deepcopy(cfg['policy'][k]) for k in ('controller','backend','dynamics_model','discretization','candidate_builder')})


def source_lengths(cfg):
    segments=[p for p in cfg['robot']['structure']['data']['components'] if p['kind']=='flexible_segment']
    if [p['id'] for p in segments]!=['near','distal1'] or len(cfg['robot']['structure']['data']['tendons'])!=6:
        raise ValueError('EXPLICIT_NEAR_DISTAL1_TWO_SEGMENT_SIX_TENDON_SOURCE_REQUIRED')
    return {p['id']:p['length_m'] for p in segments}


def configuration_for(host,parameters,owner):
    started=time.perf_counter()
    s=state(host)
    if not s['spec'].get('nominal_source'):
        # Explicitly historical study adapter, never used by the new native tools.
        from tools.research.mechanics import legacy_configuration_for
        return legacy_configuration_for(host,parameters,owner)
    p=plain(Parameters.model_validate(parameters));source=s['nominal_configuration'];base=s['base_configuration']
    domains=family.parameter_domains(source_lengths(source))
    for key,domain in domains.items():
        grant=s['spec']['allowed_parameters'][key];value=p[key]
        if 'bounds' in domain:
            if not domain['bounds'][0]<=value<=domain['bounds'][1] or not grant[0]<=value<=grant[1]:
                raise ValueError('CANDIDATE_OUTSIDE_SOURCE_DOMAIN_OR_STUDY_GRANT: '+key)
        elif value not in grant:raise ValueError('CANDIDATE_MATERIAL_OUTSIDE_STUDY_GRANT: '+key)
    constraint=s['spec'].get('length_constraint',{})
    lengths=[p[name+'_length_m'] for name in ('near','distal1')]
    if constraint.get('fixed_total_m') is not None and abs(sum(lengths)-constraint['fixed_total_m'])>1e-12:
        raise ValueError('CANDIDATE_FIXED_TOTAL_LENGTH')
    if constraint.get('aggregate_bounds_m') and not constraint['aggregate_bounds_m'][0]<=sum(lengths)<=constraint['aggregate_bounds_m'][1]:
        raise ValueError('CANDIDATE_AGGREGATE_LENGTH_CONSTRAINT')
    cfg=resolved_configuration(source,base,p,owner)
    elapsed=time.perf_counter()-started;current=state(host)
    update(host,numerical_s=current['numerical_s']+elapsed,
        construction_numerical_s=current.get('construction_numerical_s',0.)+elapsed)
    return cfg,p


def resolved_configuration(source,base,p,owner):
    lengths=[p[name+'_length_m'] for name in ('near','distal1')]
    robot=source['robot']['structure']['data']
    r=family.Recipe(lengths_m=lengths,source_design=robot,source_mesh=source['policy']['discretization']['data'],
        pretension_n=robot['tendons'][0]['pretension_n'],
        segment_section_scales={name:p[name+'_section_scale'] for name in ('near','distal1')},
        segment_routing_scales={name:p[name+'_routing_scale'] for name in ('near','distal1')},
        segment_materials={name:p[name+'_material'] for name in ('near','distal1')})
    design,mesh,physics=family.generate(r)
    cfg=deepcopy(base);cfg['run_id']=owner;cfg['robot']['structure']['data']=design
    cfg['policy']['discretization']['data']=mesh
    cfg['policy']['candidate_builder']=dict(extension_id='candidate.family',version=family.BUILDER_VERSION,
        parameters=dict(contract='family.generator_space',version='1.0.0',data=plain(family.GeneratorSpace(recipe=r))))
    for key in ('holding_tip_speed_weight','terminal_tip_speed_weight'):
        cfg['policy']['controller']['parameters']['data']['recipe'][key]=p[key]
    expected={field:{j:0. for j in physics['dofs']} for field in ('qpos_rad','qvel_rad_s')};expected['unspecified']='zero'
    if cfg['task']['initializer']['parameters']['data']!=expected:raise ValueError('SOURCE_NAMED_ZERO_INITIALIZER_MISMATCH')
    inp=SessionInput.model_validate(cfg);family.checked_reach(inp)
    return plain(inp)


def construct(host,parameters,provenance):
    s=state(host);cfg,values=configuration_for(host,parameters,host.run_id)
    scientific=full_science(cfg)
    identity=digest(dict(parameters=values,configuration=scientific,evaluation_profile=s['profile']))
    if identity in s['candidates']:
        ref=s['candidates'][identity]
        save(host,dict(candidate=ref,provenance=provenance,additional_scientific_executions=0),'candidate_reused')
        return ref
    p=plain(Parameters.model_validate(parameters)) if s['spec'].get('nominal_source') else dict(parameters)
    candidate=dict(candidate_id='core-'+identity,identity=identity,parameters=p,resolved_parameters=values,
        configuration_reference=save(host,cfg,'resolved_candidate_configuration'),
        configuration=cfg,scientific_configuration=scientific,task_identity=digest(cfg['task']),
        source_identity=digest(s.get('nominal_configuration',s['base_configuration'])),
        profile_identity=s['profile']['identity'],evaluation_version=s['profile']['version'],
        provenance=provenance,offline_trajectory=None)
    ref=save(host,candidate,'candidate_constructed');candidates=state(host)['candidates'];candidates[identity]=ref
    update(host,candidates=candidates)
    return ref


def verify_candidate(host,reference):
    s=state(host);c=host.store.artifact(reference)
    if s['candidates'].get(c.get('identity'))!=plain(reference):raise ValueError('OWNED_RESOLVED_CANDIDATE_REQUIRED')
    if c['scientific_configuration']!=full_science(c['configuration']):raise ValueError('IMPORTED_CONFIGURATION_IDENTITY_MISMATCH')
    if plain(reference)==s.get('rl_source_candidate'):return c
    if plain(reference) in s.get('imported_candidates',[]):
        if c['profile_identity']!=s['imported_candidate_profile']['identity']:raise ValueError('HISTORICAL_PROFILE_MISMATCH')
        return c
    if c['profile_identity']!=s['profile']['identity']:raise ValueError('OLD_EVALUATION_PROFILE_CANDIDATE_REQUIRES_NEW_CONSTRUCTION')
    if s['spec'].get('nominal_source'):
        if host.store.artifact(c['configuration_reference'])!=c['configuration'] or c['source_identity']!=digest(s['nominal_configuration']):
            raise ValueError('SAVED_CANONICAL_CONFIGURATION_OR_SOURCE_MISMATCH')
        if c['parameters']!=c['resolved_parameters'] or c['task_identity']!=digest(c['configuration']['task']):
            raise ValueError('SAVED_PARAMETER_TASK_IDENTITY_MISMATCH')
        expected=digest(dict(parameters=c['resolved_parameters'],configuration=c['scientific_configuration'],evaluation_profile=s['profile']))
        if expected!=c['identity']:raise ValueError('CANDIDATE_IDENTITY_MISMATCH')
        # Artifact reads and verification do not regenerate physics or incur a new calculation.
        return c
    cfg,values=configuration_for(host,c['parameters'],host.run_id)
    if values!=c['resolved_parameters'] or full_science(cfg)!=c['scientific_configuration']:
        raise ValueError('FULL_FIXED_AND_SEARCH_PARAMETER_IDENTITY_MISMATCH')
    if digest(dict(parameters=values,configuration=full_science(cfg),evaluation_profile=s['profile']))!=c['identity']:
        raise ValueError('CANDIDATE_IDENTITY_MISMATCH')
    return c


def search_problem(host,query,count):
    q=Search.model_validate(query);s=state(host);p=plain(q.fixed)
    domains=family.parameter_domains(source_lengths(s['nominal_configuration']))
    variables={k:dict(kind='fixed',value=v) for k,v in p.items() if 'length_m' not in k}
    for key in q.variables:
        grant=s['spec']['allowed_parameters'][key]
        if key in q.options:
            if set(q.options[key])-set(grant):raise ValueError('SEARCH_OPTIONS_OUTSIDE_STUDY_GRANT')
            variables[key]=dict(kind='categorical',choices=q.options[key])
        else:
            a,b=q.bounds[key];lo,hi=domains[key]['bounds']
            if not lo<=a<b<=hi or not grant[0]<=a<b<=grant[1]:raise ValueError('SEARCH_BOUNDS_OUTSIDE_SOURCE_OR_GRANT')
            if 'length_m' not in key:variables[key]=dict(kind='continuous',bounds=[a,b],initial=p[key])
    variables.update({k:dict(kind='fixed',value=v) for k,v in dict(segment_count=2,proximal_tendons=3,distal_tendons=3,material='baseline',section_scale=1.,routing_scale=1.,pretension_n=.2).items()})
    names=['near_length_m','distal1_length_m'];lengths=[p[k] for k in names]
    bounds=[list(q.bounds[k]) if k in q.bounds else [p[k],p[k]] for k in names]
    return DesignOptimizationProblem.model_validate(dict(study_id=host.run_id,task=s['base_configuration']['task'],
        source_configuration=s['nominal_configuration'],evaluation_mode=q.evaluation_mode,
        execution=dict(recipe=s['profile']['recipe'],settling=s['base_configuration']['policy']['controller']['parameters']['data']['settling']),
        variables=variables,lengths=dict(mode=q.length_mode,free=any(k in q.variables for k in names),
            total_flexible_length_m=q.total_length_m or sum(lengths),baseline_by_count={'2':lengths},bounds_by_count={'2':bounds},
            aggregate_bounds_m=q.aggregate_length_bounds_m),fixed_tendon_count=6,fixed_actuator_count=6,
        objective=dict(proxy=q.objective if q.evaluation_mode=='mathematical_proxy' else None,
            operating_point=q.operating_point,protocol=plain(q.protocol or s['spec']['analysis_protocol']),accepted_resource_preference='none'),
        method=dict(step=q.step,stop_on_acceptance=False),budget=dict(max_evaluations=count,wall_s=s['spec']['analysis_cap_s']*count)))


def run_search(host,query,key,*,guard,execute,capacity):
    from tools.design_optimization import solve
    from tools.research.analysis import dispatch as analyze, admission
    guard(host,True);q=Search.model_validate(query);s=state(host)
    if q.mechanics_source:raise ValueError('SEARCH_REFERENCES_DO_NOT_CHANGE_CANONICAL_CONSTRUCTION')
    fit=admission(host,q.max_evaluations) if q.evaluation_mode=='mathematical_proxy' else capacity(host,q.max_evaluations)
    if not fit['admitted']:return dict(status='budget_limited',admission=fit,evaluated=[])
    problem=search_problem(host,q,fit['admitted'])
    saved=s['searches'].get(key)
    if saved and plain(problem)!=saved['problem']:raise ValueError('SEARCH_RECOVERY_OBJECTIVE_PROTOCOL_OR_DOMAIN_CHANGED')
    def evaluator(problem,values,proposal_id):
        params={k:values[k] for k in Parameters.model_fields if k in values}
        params.update(near_length_m=values['lengths_m'][0],distal1_length_m=values['lengths_m'][1])
        ref=construct(host,params,dict(origin='model_design_search',plan_key=key,proposal_id=proposal_id))
        c=verify_candidate(host,ref)
        if q.evaluation_mode=='backend_task':
            old=next((host.store.artifact(r) for r in state(host)['results'] if host.store.artifact(r)['operation_key']==key+':'+proposal_id),None)
            if old is None:
                feedback=execute(host,ref,key+':'+proposal_id,role='search')
                if feedback['status']!='evaluated':return feedback
                old=host.store.artifact(feedback['reference'])
            return dict(kind='backend_task',status=old['status'],acceptance=old['acceptance'],evidence=dict(result=old),candidate_id=c['candidate_id'],scientific_identity=c['identity'])
        operation='equilibrium' if q.objective=='target_equilibrium_residual' else 'controllability'
        output=analyze(host,dict(candidate=ref,operation=operation,operating_point=q.operating_point,
            protocol=plain(q.protocol or s['spec']['analysis_protocol'])),key+':'+proposal_id,guard=guard,origin='model_search')
        result=host.store.artifact(output['reference'])
        score=result.get('proxy_values',{}).get(q.objective)
        return dict(kind='mathematical_proxy',status='evaluated',computation_status=result['status'],
            proxy_values=result.get('proxy_values',{}),local_model_constraints=result.get('local_model_constraints'),
            task_acceptance='unmeasured',objective_identity=digest(plain(problem.objective)),
            candidate_id=c['candidate_id'],scientific_identity=c['identity'],
            evidence=dict(candidate=ref,analysis=output['reference'],model=result.get('model'),limitations=result.get('limitations'),operating_point=result.get('operating_point')))
    def checkpoint(value):
        searches=state(host)['searches'];searches[key]=deepcopy(value);update(host,searches=searches)
        return save(host,value,'search_checkpoint')
    result=plain(solve(problem,evaluator=evaluator,state=saved,save_state=checkpoint,evaluation_profile=s['profile']))
    changed=[r for r in result['evaluated'] if host.store.artifact(r['evidence']['candidate'])['configuration']['robot']!=s['nominal_configuration']['robot']] if q.evaluation_mode=='mathematical_proxy' else []
    ref=save(host,dict(result=result,structurally_changed_evaluations=len(changed),admission=fit),'design_search_result')
    update(host,search_results=[*state(host).get('search_results',[]),ref])
    return dict(reference=ref,result=result,structurally_changed_evaluations=len(changed),
        selection_rule='Incumbent may remain best; never select a worse robot merely to call it new.',admission=fit)
