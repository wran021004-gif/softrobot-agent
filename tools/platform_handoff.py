"""Fixed handoff executor. Separate contexts, common ledger, no worker framework."""
from tools.platform_store import plain
from schemas.platform_handoff import HandoffResult


def pointer(value, path):
    if not path: return value
    if not path.startswith('/'): raise ValueError('JSON_POINTER_REQUIRED')
    for part in path[1:].split('/'):
        key=part.replace('~1','/').replace('~0','~')
        value=value[int(key)] if isinstance(value,list) else value[key]
    return value


def validate_selector(store, selector):
    actual=pointer(store.artifact(selector.reference),selector.pointer)
    if actual!=selector.value: raise ValueError('FACT_SELECTOR_VALUE_MISMATCH')
    return actual


def transition(ctx, kind, value):
    ref=ctx.save_artifact(value,kind)
    with ctx.store.transaction() as db:
        state=ctx.store.session(ctx.run_id,db)['state']
        state.setdefault('handoffs',{})[kind]=plain(ref)
        state.setdefault('handoff_history',[]).append(dict(kind=kind,reference=plain(ref)))
        ctx.store.update_state(db,ctx.run_id,state,'paused')
        ctx.store.event(db,ctx.run_id,'role_transition',kind,outputs=[ref],caller=ctx.host.actor)
    return HandoffResult(reference=ref,status=kind)


def require_role(ctx, role):
    if ctx.store.session(ctx.run_id)['state'].get('role_context',{}).get('role')!=role:
        raise ValueError('HANDOFF_ROLE_NOT_AUTHORIZED')


def request(ctx,args):
    require_role(ctx,'design')
    b=ctx.artifact(args.binding)
    for name in ('candidate_id','execution_id','task_identity','controller_identity','evidence_manifest'):
        if plain(getattr(args,name))!=b[name]: raise ValueError('DIAGNOSIS_SOURCE_IDENTITY_MISMATCH: '+name)
    role=ctx.store.session(ctx.run_id)['state']['role_context']
    if role.get('protocol',{}).get('saved_state_check') is not None:
        from tools.platform_diagnosis_coordinator import validate_request_scope
        validate_request_scope(args,role['protocol'])
    if not set(args.permitted_tools)<=set(role['diagnostic_tools']): raise ValueError('DIAGNOSTIC_TOOL_SCOPE_EXCEEDED')
    if any(v>ctx.store.config()['budget'][k] for k,v in plain(args.budget).items()):
        raise ValueError('DIAGNOSTIC_BUDGET_EXCEEDS_PROJECT')
    allocation=role.get('diagnostic_allocation')
    if allocation:
        budget=plain(args.budget)
        if any(v>allocation['maximum'][k] for k,v in budget.items()):raise ValueError('DIAGNOSTIC_BUDGET_EXCEEDS_PREAUTHORIZED_ALLOCATION')
        if any(budget[k]<v for k,v in allocation['minimum'].items()):raise ValueError('DIAGNOSTIC_GRANT_CANNOT_ACCOMMODATE_DECLARED_WORKFLOW')
        remaining=ctx.store.remaining()['remaining']
        if any(budget[k]+allocation.get('reserved_for_design',{}).get(k,0)>remaining[k] for k in budget):raise ValueError('DIAGNOSTIC_GRANT_LEAVES_NO_DESIGN_REVIEW_CAPACITY')
    return transition(ctx,'diagnosis_request',args)


def check(ctx,args):
    require_role(ctx,'diagnostic')
    role=ctx.store.session(ctx.run_id)['state']['role_context']
    if plain(args.diagnosis_request)!=role['request']: raise ValueError('CHECK_REQUEST_LINK_MISMATCH')
    validate_selector(ctx.store,args.initial_state);validate_selector(ctx.store,args.input)
    if role.get('check_execution_enabled'):
        from tools.platform_diagnosis_coordinator import validate_check
        validate_check(ctx.store, role, args)
        return transition(ctx,'diagnostic_check',args)
    ref=ctx.save_artifact(args,'diagnostic_check_request')
    return HandoffResult(reference=ref,status='advisory_check_requested_no_execution')


def submit(ctx,args):
    require_role(ctx,'diagnostic')
    role=ctx.store.session(ctx.run_id)['state']['role_context']
    from schemas.platform_handoff import InventoryDiagnosisSubmission
    if isinstance(args,InventoryDiagnosisSubmission):
        from tools.diagnostic_inventory import validate_gaps
        state=ctx.store.session(ctx.run_id)['state']
        gaps=args.missing_evidence
        if state.get('reference_interface') and role.get('previous_report'):
            # These declarations retain the accepted report's historical reading
            # scope. Only newly authored declarations claim current availability.
            inherited=ctx.artifact(role['previous_report']).get('missing_evidence',[])
            gaps=[g for g in gaps if plain(g) not in inherited]
        if state.get('fact_scope'):
            from tools.diagnostic_facts import context_view
            view=context_view(state)
            validate_gaps(gaps,role['inventory'],view['read_ledger'],[f['handle'] for f in view['fact_catalog']])
        else:validate_gaps(gaps,role['inventory'])
    if plain(args.request)!=role['request']: raise ValueError('REPORT_REQUEST_LINK_MISMATCH')
    request=ctx.artifact(args.request)
    if role.get('require_initial_views'):
        views={v['view'] for v in role.get('evidence_views',[])}
        if 'prediction' not in views or not views.intersection({'motion','plans'}):
            raise ValueError('INITIAL_REPORT_REQUIRES_PREDICTION_AND_MOTION_OR_PLAN_VIEW')
    if role.get('previous_report') != plain(args.previous_report):raise ValueError('REPORT_REVISION_LINK_MISMATCH')
    expected=role.get('check_feedback',[])
    if expected and [plain(r) for r in args.check_results] != [f['reference'] for f in expected]:
        raise ValueError('REPORT_CHECK_FEEDBACK_REQUIRED: check_results must contain only the feedback artifact IDs '+
            ', '.join(f['reference']['artifact_id'] for f in expected)+'; numerical result references belong in fact_selectors, not check_results.')
    if plain(args.report.source)!=request['binding']: raise ValueError('REPORT_SUBJECT_BINDING_MISMATCH')
    if set(args.fact_selectors)!={f.fact_id for f in args.report.facts}: raise ValueError('EVERY_FACT_REQUIRES_SELECTORS')
    for fact in args.report.facts:
        selectors=args.fact_selectors[fact.fact_id]
        if not selectors: raise ValueError('EMPTY_FACT_SELECTORS')
        for selector in selectors:
            if plain(selector.reference) not in [plain(r) for r in fact.evidence]: raise ValueError('FACT_EVIDENCE_LINK_MISMATCH')
            validate_selector(ctx.store,selector)
    for feedback in expected:
        if feedback['receipt']['execution_status']=='completed' and feedback.get('result'):
            if not any(plain(s.reference)==feedback['result'] and isinstance(s.value,(float,int)) and not isinstance(s.value,bool)
                    and s.pointer.rsplit('/',1)[-1] not in ('update_id','time_s','horizon_s','integration_step_s','complete_cost_s','computation_s','new_local_solves')
                    for selectors in args.fact_selectors.values() for s in selectors):
                raise ValueError('REVISED_REPORT_REQUIRES_NUMERICAL_RESULT_SELECTOR: cite at least one relevant numeric value from the executed result artifact, with its exact JSON pointer, and explain model/horizon limits.')
    binding=ctx.artifact(request['binding'])
    for r in args.recommendations:
        if plain(r.configuration_scope)!=binding['configuration']: raise ValueError('RECOMMENDATION_CONFIGURATION_MISMATCH')
    return transition(ctx,'diagnosis_report',args)


def respond(ctx,args):
    require_role(ctx,'design')
    role=ctx.store.session(ctx.run_id)['state']['role_context']
    if plain(args.report)!=role.get('report'): raise ValueError('DESIGN_REPORT_LINK_MISMATCH')
    report=ctx.artifact(args.report)
    if args.recommendation_id is not None and args.recommendation_id not in [r['recommendation_id'] for r in report['recommendations']]:
        raise ValueError('UNKNOWN_RECOMMENDATION: arguments.recommendation_id must name an ID in this report; defer/reject may omit it with next_action=stop.')
    if args.next_action=='bounded_verification' and (args.disposition!='adopt' or args.recommendation_id is None):
        raise ValueError('VERIFICATION_REQUIRES_EXPLICIT_ADOPTION: incompatible arguments.disposition='+args.disposition+
            ' and arguments.next_action=bounded_verification. Keep defer/reject and use next_action=stop, or explicitly adopt a valid named recommendation if justified. '
            'stop does not terminate the independently authorized diagnostic check phase. Resubmit the complete provider envelope with all domain fields inside arguments.')
    if args.disposition=='adopt' and args.recommendation_id is None:
        raise ValueError('ADOPTION_REQUIRES_NAMED_RECOMMENDATION: supply arguments.recommendation_id from this report, or defer/reject with next_action=stop. Resubmit the complete envelope.')
    return transition(ctx,'design_response',args)


def review(ctx,args):
    require_role(ctx,'design')
    role=ctx.store.session(ctx.run_id)['state']['role_context']
    if plain(args.response)!=role.get('response') or plain(args.verification)!=role.get('verification'):
        raise ValueError('REVIEW_LINK_MISMATCH')
    evidence=ctx.artifact(args.verification)
    if args.adopt_into_baseline and not evidence['improvement_gate_passed']:
        raise ValueError('FAILED_VARIANT_CANNOT_BE_ADOPTED')
    return transition(ctx,'final_review',args)


def respond_workflow(ctx,args):
    require_role(ctx,'design')
    role=ctx.store.session(ctx.run_id)['state']['role_context']
    if plain(args.report)!=role.get('report'):raise ValueError('DESIGN_REPORT_LINK_MISMATCH')
    recommendations=ctx.artifact(args.report)['recommendations']
    selected=next((r for r in recommendations if r['recommendation_id']==args.recommendation_id),None)
    if args.recommendation_id is not None and selected is None:raise ValueError('UNKNOWN_RECOMMENDATION')
    if args.disposition=='adopt' and selected is None:raise ValueError('ADOPTION_REQUIRES_NAMED_RECOMMENDATION')
    if args.next_action=='verify_adopted_change' and (args.disposition!='adopt' or selected['action']!='control_parameter'):
        raise ValueError('VERIFICATION_REQUIRES_ADOPTION_OF_EXACT_CONTROL_PARAMETER')
    if role.get('final_response') and args.next_action!='finish':raise ValueError('CHECK_ALLOWANCE_SPENT: choose finish')
    from schemas.diagnostic_revision import FinalDesignResponse
    if isinstance(args,FinalDesignResponse):
        if role.get('require_research_route') and args.next_research is None:raise ValueError('FINAL_RESEARCH_ROUTE_REQUIRED')
        if role.get('require_research_budget') and args.next_research and args.next_research.proposed_budget.backend_solves:
            from tools.batch_budget import budget_capacity
            capacity=budget_capacity(args.next_research.proposed_budget.backend_solves,plain(args.next_research.proposed_budget),
                preparation_reserve_s=role.get('candidate_preparation_reserve_s',0.))
            if not capacity['sufficient']:raise ValueError('NEXT_RESEARCH_BUDGET_INSUFFICIENT: '+str(capacity['requirement']))
        feedback=role['improvement_feedback_content']
        if plain(args.feedback)!=role['check_feedback'][0]['reference']:raise ValueError('FINAL_FEEDBACK_BINDING_MISMATCH')
        if args.candidate_disposition in ('defer_selection','reject_all'):
            expected=None
        else:
            if args.candidate_disposition=='adopt_candidate' and role.get('batch_result'):
                choices=[c['execution']['factual_result']['candidate'] for c in role['batch_result']['candidates']
                    if c.get('execution') and c.get('feedback') is not None]
                choices.extend(r['facts']['candidate'] for r in role.get('research_records',[]) if r['facts'].get('valid_complete_execution'))
                if args.selected_candidate not in choices:raise ValueError('FINAL_BATCH_CANDIDATE_BINDING_MISMATCH')
                expected=args.selected_candidate
                facts=None
            else:facts=feedback['baseline_facts'] if args.candidate_disposition=='retain_baseline' else feedback['execution']['factual_result']
            if facts is not None:expected=facts['candidate']
        if args.selected_candidate!=expected:raise ValueError('FINAL_CANDIDATE_BINDING_MISMATCH')
    return transition(ctx,'design_response',args)


def preflight(inp,args,reg):
    return dict(cost=dict(wall_s=5.))
