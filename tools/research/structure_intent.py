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
    if native and (q.research_goal!='structure_control_codesign' or q.control_treatment!='reoptimized' or q.proxy_objective is not None):
        issue('control_treatment','Native task codesign requires reoptimized control and no proxy objective')
    if not native and (q.control_treatment!='not_optimized' or q.research_goal!='structural_capability_screening' or q.proxy_objective is None
            or q.control_search_effort is not None or q.initial_tension_n is not None):
        issue('evaluation_model','Mathematical proxy requires explicit proxy_objective, structural_capability_screening and not_optimized; no Native control effort')
    if native and q.control_search_effort is None:issue('control_search_effort','Choose method, knot count and independent callback/iteration effort')
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
        objective='task_violation' if native else q.proxy_objective,
        operating_point='standardized_initial_pretension' if native or q.proxy_objective!='target_equilibrium_residual' else 'target_equilibrium',
        **plain(q.structure_search_effort),evaluation_mode='mujoco_control' if native else 'mathematical_proxy',
        evidence_used=value.get('supporting_evidence',[]))
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
    problem=search_problem(host,compiled['search'],q.structure_search_effort.max_evaluations)
    save(host,dict(version=INTERFACE,request_id=request_id,original_plan=value,compiled_plan=compiled,
        original_admission=problem,decision_owner='Main scientific choices; program binds frozen implementation fields',
        initial_tension_source=('Main' if q.initial_tension_n is not None else 'frozen tendon_domains.pretension_n.default') if native else 'not_applicable_proxy',
        initialization_scope='Original mixed_moves initialization; previous candidate seeds segment parameters only, not its full routing/control. Each proposed structure is re-evaluated; no inherited acceptance.'),
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
