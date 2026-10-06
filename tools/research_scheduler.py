"""Evidence-dependent choices over the shared planner and receipt executor."""
from tools.platform_store import plain
from tools.state_io import digest
from tools.batch_budget import budget_capacity, downstream_available, PREPARATION_RESERVE_S
from tools.candidate_parameters import STRUCTURAL_PATHS
from extensions.tendon_family.candidate import REACH_WEIGHT_PATHS

ACTIONS=('control_search','structure_search','diagnosis','stop')


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


def capabilities(store, run_id, records):
    from tools.platform_registry import registry
    remaining=downstream_available(store,run_id)
    capacity=budget_capacity(1,remaining,preparation_reserve_s=PREPARATION_RESERVE_S)
    inp=store.session(run_id)['snapshot']['input']; controller=inp['policy']['controller']
    stable=(controller['extension_id'],controller['version'])==('controller.gvs_nmpc','7.0.0')
    space=inp['policy']['candidate_builder']['parameters']['data']
    legal={}; gaps={}; reg=registry()
    for action,paths in [('control_search',REACH_WEIGHT_PATHS),('structure_search',STRUCTURAL_PATHS)]:
        builder=space.get('control_parameters',{}) if action=='control_search' else space['parameters']
        reason=None
        if not stable:reason='Stable controller.gvs_nmpc@7.0.0 prerequisite absent'
        elif not capacity['sufficient']:reason='Complete execution and delivery reservation unavailable: '+str(capacity['shortfalls'])
        elif not all(p in builder for p in paths):reason='Authorized builder paths unavailable'
        elif not all(reg.inspect(reg.get(t,'1.0.0','tool'),{t:'1.0.0'})['executable'] for t in
                     ('simulation.run','evaluation.run','control.profile_report')):reason='Backend/evaluation/profile implementation unavailable'
        if reason:gaps[action]=reason
        else:legal[action]=dict(paths=list(paths),minimum_batch=capacity['requirement'])
    if not records or remaining['wall_s']<780 or remaining['tool_calls']<6 or remaining['model_calls']<4:
        gaps['diagnosis']='Verified saved evidence or 180-second query plus protected delivery capacity unavailable'
    else:legal['diagnosis']=dict(operations=['retained prediction/plans/motion query'],max_wall_s=180,
        numerical_gap='Local controller comparisons require separately bound adoption and saved-horizon prerequisites; no such grant installed in this scheduling context.')
    legal['stop']=dict(reason='Voluntary delivery is always legal')
    return dict(legal=legal,unavailable=gaps,remaining=remaining)


def validate_decision(store, view, decision):
    from schemas.platform_handoff import ResearchDecision
    from tools.diagnostic_revision import resolve_aliases
    from tools.study_history import select_source
    from tools.platform_search import validate_batch_plan
    d=ResearchDecision.model_validate(decision);state=store.session(view.run_id)['state'];role=state['role_context']
    if not role.get('autonomous_scheduling'):raise ValueError('AUTONOMOUS_RESEARCH_GRANT_REQUIRED')
    cap=capabilities(store,view.run_id,role['research_records'])
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
        verified_observations=observations,model_interpretations=[plain(i) for i in d.interpretations],
        interpretation_bindings=interpretation_bindings,unresolved_uncertainties=d.unresolved_uncertainties,
        scientific_reasoning_status='Model-authored; valid references do not establish causal truth')
    if d.plan:
        if (d.plan.max_backend_attempts or d.plan.max_candidates)>role['max_batch_backends']:
            raise ValueError('BATCH_ALLOCATION_EXCEEDED: '+str(role['max_batch_backends']))
        paths=set(d.plan.variables);allowed=set(REACH_WEIGHT_PATHS if d.action=='control_search' else STRUCTURAL_PATHS)
        if not paths or paths-allowed:raise ValueError('ACTION_VARIABLE_SCOPE: '+str(sorted(allowed)))
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
