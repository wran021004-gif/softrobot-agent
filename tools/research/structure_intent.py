"""Scientific structure choices -> the original mixed-search Plan; no execution."""
from copy import deepcopy
from tools.platform_store import plain
from tools.research.contracts import ScientificStructureSearch, FamilyMixedSearch, Plan
from tools.research.state import state, save

INTERFACE='scientific_structure_search_v1'


def enabled(spec):
    return spec.get('research_decisions',{}).get('structure_search_interface')==INTERFACE


class StructureChoiceError(ValueError):
    def __init__(self, issues):
        self.issues=issues
        super().__init__('; '.join(i['field']+': '+i['reason'] for i in issues))


def compile_generation(host, value):
    """Explicit physical changes -> the existing exact family generation request."""
    from tools.research.contracts import ScientificGeneration
    from tools.research.design import verify_candidate,set_parameter
    from tools.research.optimal_capability import family_analysis_parameters
    from extensions.tendon_family.family_space import resolved_request,parse_build
    s=state(host)
    if s['spec']['research_decisions']['analysis_interface']!='scientific_question_v4':
        raise ValueError('SCIENTIFIC_GENERATION_REQUIRES_V4')
    parent=(value.get('decision') or {}).get('selected_candidate')
    if not parent:raise ValueError('PHYSICAL_CHANGES_REQUIRE_SELECTED_PARENT')
    try:candidate=verify_candidate(host,parent)
    except ValueError as exc:
        if str(exc)!='OLD_EVALUATION_PROFILE_CANDIDATE_REQUIRES_NEW_CONSTRUCTION':raise
        # verify_candidate already checked ownership and the exact saved
        # configuration. This parent is read-only lineage, never an executable
        # candidate or transferable result. The original constructor owns the new profile.
        candidate=host.store.artifact(parent)
    space=s['spec']['family_space']
    q=ScientificGeneration.model_validate(value['generation'])
    rows={r['parameter_id']:r for r in family_analysis_parameters(s['spec'],candidate)}
    params=resolved_request(space,candidate['parameters']) if q.changes else deepcopy(candidate['parameters'])
    for path,new in q.changes.items():
        row=rows.get(path)
        if not row or '*' in path or row['category'] in ('controller','discretization') or not row['effective_in_current_execution'] or not row['continuous_perturbation']:
            raise ValueError('SELECT_REGISTERED_EFFECTIVE_CONTINUOUS_PHYSICAL_PARAMETER: '+path)
        if not row['minimum']<=new<=row['maximum']:raise ValueError('PHYSICAL_CHANGE_OUTSIDE_FROZEN_DOMAIN: '+path)
        set_parameter(params,path,new)
    # The family validator, construction admission and frozen topology remain
    # authoritative. No candidate, control or T1 is created by this compiler.
    parse_build(dict(space=space,request=params))
    return {**deepcopy(value),'generation':params}


def compile_search(host, value, request_id):
    """Bind frozen implementation fields, then use original contract/admission."""
    from extensions.tendon_family.family_space import span_strategies
    from tools.research.scientific_intent import control_settings
    s=state(host);spec=s['spec']
    if not enabled(spec):raise ValueError('VERSIONED_STRUCTURE_SEARCH_INTERFACE_REQUIRED')
    q=ScientificStructureSearch.model_validate(value['search'])
    grant=spec['family_search'];space=spec['family_space'];issues=[]
    def issue(field,reason,**extra):issues.append(dict(field='search.'+field,reason=reason,**extra))
    groups=q.design_variable_groups
    if q.span_strategies and not set(q.span_strategies)<=set(span_strategies(space)):
        issue('span_strategies','Outside the frozen FamilySpace rule',choices=span_strategies(space))
    if len(groups)!=len(set(groups)) or not set(groups)<=set(grant['variable_groups'])-{'control'}:
        issue('design_variable_groups','Choose unique authorized structural groups',choices=[g for g in grant['variable_groups'] if g!='control'])
    topology={}
    for field,group in (('segment_counts','segment_count'),('tendon_counts','tendon_count')):
        choices=getattr(q,field)
        if choices is None:
            if len(grant[field])==1 or group in groups:choices=grant[field]
            else:issue(field,'Explicit fixed topology choice required',choices=grant[field])
        elif not choices or not set(choices)<=set(grant[field]):
            issue(field,'Outside frozen topology; no automatic replacement',choices=grant[field])
        topology[field]=choices
    native=q.evaluation_model=='native_mujoco'
    passive=q.evaluation_model.startswith('passive_')
    if passive and (q.research_goal!='passive_structure_research' or q.control_treatment!='no_active_control'
            or q.control_search_effort is not None or q.initial_tension_n is not None
            or q.proxy_objective not in ('task_violation','equilibrium_qualification')):
        issue('evaluation_model','Passive research requires no_active_control and an explicit passive objective; no control search.')
    starts={}
    prior_ref=(value.get('decision') or {}).get('selected_candidate')
    prior=host.store.artifact(prior_ref)['parameters'] if prior_ref else {}
    for name,choices,previous in (('initial_segment_count',topology['segment_counts'],prior.get('segment_count')),
            ('initial_tendon_count',topology['tendon_counts'],prior.get('tendon_count')),
            ('initial_span_strategy',q.span_strategies or (span_strategies(space) if 'spans' in groups else ['whole_chain']),None)):
        selected=getattr(q,name)
        if selected is None and previous in (choices or []):selected=previous
        if selected is None and choices and len(choices)==1:selected=choices[0]
        if selected is None and grant.get('require_explicit_start'):
            issue(name,'Main must choose an initial point; list order is not a scientific preference',choices=choices)
        elif selected is not None:
            if selected not in (choices or []):issue(name,'Initial point outside selected range',choices=choices)
            else:starts[name]=selected
    if native and (q.research_goal!='structure_control_codesign' or q.control_treatment!='reoptimized' or q.proxy_objective is not None):
        issue('control_treatment','Native task codesign requires reoptimized control and no proxy objective')
    proxy_treatment='proxy_optimized' if q.proxy_objective=='task_violation' else 'not_optimized'
    if not (native or passive) and (q.control_treatment!=proxy_treatment or q.research_goal!='structural_capability_screening' or q.proxy_objective is None
            or q.control_search_effort is not None or q.initial_tension_n is not None):
        issue('evaluation_model','Mathematical proxy requires explicit proxy_objective and structural_capability_screening; task_violation uses proxy_optimized, static/held-input proxies use not_optimized; no Native control effort')
    if native and q.control_search_effort is None:issue('control_search_effort','Choose temporal resolution, exploration scale and a shared finite callback cap')
    tension=q.initial_tension_n
    if native and tension is None:
        tension=space.get('tendon_domains',{}).get('pretension_n',{}).get('default')
        if tension is None:issue('initial_tension_n','No unique frozen common pretension; choose a legal initial tension')
    if issues:raise StructureChoiceError(issues)
    fidelities=spec['fidelity_policy']['screening']
    # Exact final discretization when available; otherwise require an explicit
    # scientific choice rather than silently changing the numerical model.
    exact=[k for k,v in fidelities.items() if v==spec['fidelity_policy']['final_evaluation']]
    if len(exact)!=1:raise StructureChoiceError([dict(field='search.evaluation_model',reason='Unique frozen final screening fidelity required',choices=list(fidelities))])
    query=dict(version='family_mixed_search_v1',family_space_identity=spec['family_space_identity'],
        variable_groups=groups,**topology,
        span_strategies=q.span_strategies or (span_strategies(space) if 'spans' in groups else ['whole_chain']),
        section_types=q.section_types,screening_fidelity=exact[0],
        bounds=q.bounds,
        objective='task_violation' if native else q.proxy_objective,
        operating_point='standardized_initial_pretension' if native or q.proxy_objective!='target_equilibrium_residual' else 'target_equilibrium',
        **plain(q.structure_search_effort),evaluation_mode=q.evaluation_model if passive else 'mujoco_control' if native else 'mathematical_proxy',
        **starts,
        evidence_used=value.get('supporting_evidence',[]))
    if q.diagnostic_load_conditions:query['diagnostic_load_conditions']=q.diagnostic_load_conditions
    decision=deepcopy(value.get('decision') or {})
    if decision.get('selected_candidate'):query['previous_candidate_ref']=decision['selected_candidate']
    if native:
        query.update(control_settings=plain(control_settings(spec,q.control_search_effort)),initial_tension_n=tension)
    compiled={**deepcopy(value),'search':plain(FamilyMixedSearch.model_validate(query)),
        'decision':{**decision,'research_intent':'MATHEMATICAL_ANALYSIS',
            'selected_method':'bounded_mixed_coordinate_v1',
            'requested_budget':q.structure_search_effort.max_evaluations}}
    compiled=plain(Plan.model_validate(compiled))
    from tools.research.search import search_problem
    from tools.research.analysis import admission
    try:problem=search_problem(host,compiled['search'],admission(host,q.structure_search_effort.max_evaluations)['admitted'])
    except ValueError as exc:
        if not str(exc).startswith('SEARCH_SEED_NOT_REPRESENTABLE_USE_GENERATE'):raise
        raise StructureChoiceError([dict(field='decision.selected_candidate',reason=str(exc),
            preparation=dict(tool='research_plan',action='generate',parent=prior_ref,
                parameters_query=dict(reference=prior_ref,view='full',pointer='/parameters'),
                instruction='Copy the complete original generation parameters and change only the explicitly chosen coordinates. Preserve section rotations and all other fixed parameters. This search cannot seed that structure without loss.'))]) from exc
    save(host,dict(version=INTERFACE,request_id=request_id,original_plan=value,compiled_plan=compiled,
        original_admission=problem,decision_owner='Main scientific choices; program binds frozen implementation fields',
        initial_tension_source=('Main' if q.initial_tension_n is not None else 'frozen tendon_domains.pretension_n.default') if native else 'not_applicable_proxy',
        initialization_scope='Main-selected start. A representable previous candidate seeds structure coordinates; unsupported routes require generate. Every condition receives fresh controls; no inherited acceptance.'),
        'structure_search_intent_binding')
    return compiled


def contract_issues(payload, errors):
    """Select versioned union branch; expose a few actionable G1 field issues."""
    search=payload.get('search') or {};version=search.get('version') or (INTERFACE if 'research_goal' in search else None)
    contract={'family_mixed_search_v1':'FamilyMixedSearch',INTERFACE:'ScientificStructureSearch'}.get(version)
    chosen=[e for e in errors if any(contract in str(p) for p in e['loc'])] if contract else []
    errors=chosen or errors
    issues=[dict(field='.'.join(str(p) for p in e['loc'] if not str(p).startswith('function-after[')),
        error_type=e['type'],reason=e['msg']) for e in errors[:4]]
    if version==INTERFACE:
        for i in issues:
            if not i['field'].startswith('search'):i['field']='search.'+i['field']
    if version=='family_mixed_search_v1' and search.get('evaluation_mode')=='mujoco_control':
        fixes=[]
        if search.get('operating_point')!='standardized_initial_pretension':
            fixes.append(dict(field='search.operating_point',error_type='native_initialization',reason='Native search starts from frozen initial state',expected='standardized_initial_pretension'))
        if 'control' in search.get('variable_groups',[]):
            fixes.append(dict(field='search.variable_groups',error_type='structural_groups',reason='control_is_not_structural_variable',expected='Remove control; reoptimization belongs in control_settings'))
        issues=fixes+issues
    return contract,issues[:4]
