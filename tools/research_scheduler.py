"""Evidence-dependent choices over the shared planner and receipt executor."""
from tools.platform_store import plain
from tools.state_io import digest
from tools.batch_budget import budget_capacity, downstream_available, PREPARATION_RESERVE_S

ACTIONS=('control_search','structure_search','diagnosis','stop')


def resolved_pool(effective):
    """The effective builder/catalog is the single action and validation pool."""
    from tools.parameter_impacts import parameter_impacts
    rows=parameter_impacts(effective)['mapped']
    return {r['parameter']:r for r in rows
        if r['authorized_parameter'] and r['implementation_supported']}


def verified_observations(state, decision):
    """Check explicit values/arithmetic; hypotheses remain model judgments."""
    from tools.diagnostic_revision import resolve_aliases
    checked=[]
    for i,o in enumerate(decision.observations):
        refs=[o.evidence]+([o.comparison_evidence] if o.comparison_evidence else [])
        selectors=resolve_aliases(state,{'observation':refs})['observation']
        a=selectors[0]['value'];expected=a
        if o.operation!='recorded':
            if len(selectors)!=2:raise ValueError(f'OBSERVATION_{i}_COMPARISON_EVIDENCE_REQUIRED')
            b=selectors[1]['value']
            if o.operation!='equal' and any(isinstance(v,bool) or not isinstance(v,(int,float)) for v in (a,b)):
                raise ValueError(f'OBSERVATION_{i}_NUMERIC_VALUES_REQUIRED')
            expected={'difference':lambda:a-b,'less_than':lambda:a<b,'greater_than':lambda:a>b,'equal':lambda:a==b}[o.operation]()
        elif len(selectors)!=1:raise ValueError(f'OBSERVATION_{i}_RECORDED_USES_ONE_REFERENCE')
        v=o.value
        numeric=all(not isinstance(x,bool) and isinstance(x,(int,float)) for x in (expected,v))
        match=abs(v-expected)<=1e-12*max(1.,abs(expected)) if numeric else type(v)==type(expected) and v==expected
        if not match:raise ValueError(f'OBSERVATION_{i}_VALUE_MISMATCH: expected {expected!r} from {refs}; operation={o.operation}')
        checked.append(dict(operation=o.operation,value=expected,evidence_selectors=selectors))
    return checked


def capabilities(store, run_id, records,*,as_of_unix=None):
    from tools.platform_registry import registry
    import time
    as_of_unix=time.time() if as_of_unix is None else as_of_unix
    remaining=downstream_available(store,run_id,as_of_unix=as_of_unix)
    capacity=budget_capacity(1,remaining,preparation_reserve_s=PREPARATION_RESERVE_S)
    inp=store.session(run_id)['snapshot']['input']; controller=inp['policy']['controller']
    proposal_only=store.session(run_id)['state'].get('role_context',{}).get('decision_only',False)
    if proposal_only:remaining=store.spendable(run_id)['remaining']
    from tools.research_tasks import task_adapter
    compatibility=task_adapter(inp).check_compatibility()['technical_compatibility']
    stable=compatibility['status']=='supported'
    pool=resolved_pool(inp)
    role=store.session(run_id)['state'].get('role_context',{})
    if inp['policy']['candidate_builder'].get('version')=='2.0.0':
        from tools.candidate_parameters import planning_configuration
        for record in records:
            pool.update(resolved_pool(planning_configuration(store,record['facts']['candidate'],inp['policy'])))
    legal={}; gaps={}; reg=registry()
    methods=[m+'@1.0.0' for m in ('search.family_coordinate','search.family_explicit')
        if reg.inspect(reg.get(m,'1.0.0','search'),{m:'1.0.0'})['executable']]
    for action,paths in [('control_search',[p for p in pool if p.startswith('control/')]),
                         ('structure_search',list(pool))]:
        reason=None
        if not stable:reason='Selected task/controller pairing incompatible: '+compatibility['reason']
        elif role.get('development_backend_remaining')==0:reason='Bounded development execution allocation exhausted'
        elif role.get('mathematical_operations_remaining')==0:reason='Bounded public mathematical operation allocation exhausted'
        elif not proposal_only and not capacity['sufficient']:reason='Complete execution and delivery reservation unavailable: '+str(capacity['shortfalls'])
        elif not paths or (action=='structure_search' and not any(not p.startswith('control/') for p in paths)):
            reason='Authorized builder paths unavailable'
        elif not methods:reason='No compatible installed batch method'
        elif not all(reg.inspect(reg.get(t,'1.0.0','tool'),{t:'1.0.0'})['executable'] for t in
                     ('simulation.run','evaluation.run','control.profile_report')):reason='Backend/evaluation/profile implementation unavailable'
        if reason:gaps[action]=reason
        else:legal[action]=dict(paths=list(paths),minimum_batch=capacity['requirement'],methods=methods,
            domains={p:pool[p]['granted_range'] for p in paths},
            methods_by_path={p:(['search.family_explicit@1.0.0'] if pool[p]['builder_spec']['type']=='choice' else methods) for p in paths},
            mixed_semantics='structure_search permits joint structural/control subsets; each point constructs all selected values followed by one execution with the selected versioned controller. Online solving is separately accounted.',
            method_semantics={'search.family_coordinate@1.0.0':'Numerically generated continuous coordinate proposals; categorical paths unavailable.',
                'search.family_explicit@1.0.0':'Evaluate a model-authored finite sequence; categorical values enumerated, never interpolated.'})
    role=store.session(run_id)['state'].get('role_context',{})
    if role.get('frozen_cases'):
        for value in legal.values():
            value.update(frozen_cases=[c['case_id'] for c in role['frozen_cases']],seeds=[17,18],
                execution_authorized=True,proposal_only=False)
    if role.get('diagnosis_remaining',1)<=0:
        gaps['diagnosis']='Frozen retained-query decision ceiling reached'
    elif not records or (not proposal_only and (remaining['wall_s']<780 or remaining['tool_calls']<6 or remaining['model_calls']<4)):
        gaps['diagnosis']='Verified saved evidence or 180-second query plus protected delivery capacity unavailable'
    else:legal['diagnosis']=dict(operations=['retained prediction/plans/motion query'],max_wall_s=180,
        numerical_gap='Local controller comparisons require separately bound adoption and saved-horizon prerequisites; no such grant installed in this scheduling context.')
    legal['stop']=dict(reason='Voluntary delivery is always legal')
    if proposal_only:
        for value in legal.values():value.update(proposal_only=True,execution_authorized=False)
    # Archived role menus and elapsed deadlines cannot reopen a stopped session.
    session=store.session(run_id)
    stop=role.get('context_authority',{}).get('stop') or {}
    stopped=stop.get('sealed_cases') or str(stop.get('status','')).lower() in ('stopped','model_stopped','sealed','closed','finished')
    if session['status']!='running' or stopped:
        for action in list(legal):
            if action!='stop':gaps[action]='Session is '+session['status'];legal.pop(action)
    from tools.batch_budget import operational_view
    operational=operational_view(store,run_id,requirement=capacity['requirement'],as_of_unix=as_of_unix)
    return dict(legal=legal,unavailable=gaps,remaining=remaining,operational_facts=operational)


def validate_decision(store, view, decision):
    from schemas.platform_handoff import ResearchDecision
    from tools.diagnostic_revision import resolve_aliases
    from tools.study_history import select_source
    from tools.platform_search import validate_batch_plan
    d=ResearchDecision.model_validate(decision);state=store.session(view.run_id)['state'];role=state['role_context']
    if not role.get('autonomous_scheduling'):raise ValueError('AUTONOMOUS_RESEARCH_GRANT_REQUIRED')
    cap=capabilities(store,view.run_id,role['research_records'])
    if role.get('research_final_reporting'):
        cap['legal']={'stop':dict(reason='Final interpretation only',execution_authorized=False)}
        cap['unavailable'].update({a:'Research trajectory closed' for a in ACTIONS if a!='stop'})
    from tools.current_research_authority import dispatch_snapshot
    authority_check=dispatch_snapshot(store,view.run_id,role,cap,d.action)
    if d.action not in cap['legal']:raise ValueError('CAPABILITY_GAP: '+cap['unavailable'][d.action])
    selectors=resolve_aliases(state,{'evidence':d.evidence})['evidence']
    latest=role['result_feedback']; feedback=store.artifact(latest)['result']
    if not any(s['reference']==feedback for s in selectors):raise ValueError('DECISION_REQUIRES_CURRENT_FEEDBACK_REFERENCE')
    if d.selected_candidate is not None:select_source(role['research_records'],d.selected_candidate)
    if role.get('fact_separation') and not d.observations:
        raise ValueError('OBSERVATIONS_REQUIRED: bind at least one recorded fact; interpretations and voluntary stop remain free')
    observations=verified_observations(state,d)
    interpretation_bindings=[resolve_aliases(state,{k:v for k,v in dict(support=i.supporting_evidence,contradiction=i.contradicting_evidence).items() if v})
        for i in d.interpretations]
    result=dict(decision=plain(d),evidence_selectors=selectors,capabilities=cap,feedback=latest,
        authority_check=authority_check,
        verified_observations=observations,model_interpretations=[plain(i) for i in d.interpretations],
        interpretation_bindings=interpretation_bindings,unresolved_uncertainties=d.unresolved_uncertainties,
        scientific_reasoning_status='Model-authored; valid references do not establish causal truth')
    if d.action=='stop':
        from tools.research_tasks import stop_interpretation
        result['stop_interpretation']=stop_interpretation(
            role.get('acceptance_result') or {},'voluntary_stop',operational=cap['operational_facts'])
    if d.plan:
        if (d.plan.max_backend_attempts or d.plan.max_candidates)>role['max_batch_backends']:
            raise ValueError('BATCH_ALLOCATION_EXCEEDED: '+str(role['max_batch_backends']))
        paths=set(d.plan.variables);allowed=set(cap['legal'][d.action]['paths'])
        if not paths or paths-allowed:raise ValueError('ACTION_VARIABLE_SCOPE: '+str(sorted(allowed)))
        if d.action=='structure_search' and not any(not p.startswith('control/') for p in paths):
            raise ValueError('STRUCTURE_SEARCH_REQUIRES_STRUCTURAL_VARIABLE')
        if plain(d.plan.predecessor_decision)!=role['predecessor_decision']:raise ValueError('PLAN_PREDECESSOR_DECISION_MISMATCH')
        result['batch_plan']=validate_batch_plan(store,view,d.plan)
    if d.diagnosis:
        request=plain(d.diagnosis); select_source(role['research_records'],request['source_candidate'])
        resolve_aliases(state,{'diagnosis':request['evidence']})
        key=digest({k:request[k] for k in ('source_candidate','view','update_ids')})
        previous=state.get('research_diagnostics',{}).get(key)
        result.update(diagnostic_key=key,prior_diagnostic=previous,
            duplicate_without_replication=bool(previous and not request['replication_reason']))
    return result


def decide(ctx,args):
    from tools.platform_handoff import require_role,transition
    from tools.working_state import project_working_state
    require_role(ctx,'design')
    result=validate_decision(ctx.store,project_working_state(ctx.store,ctx.run_id),args)
    if result.get('batch_plan'):
        result['search_plan']=plain(transition(ctx,'search_batch_plan',result['batch_plan']).reference)
    return transition(ctx,'research_decision',result)
