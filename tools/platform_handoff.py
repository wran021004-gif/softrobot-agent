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
    if plain(args.request)!=role['request']: raise ValueError('REPORT_REQUEST_LINK_MISMATCH')
    request=ctx.artifact(args.request)
    if role.get('previous_report') != plain(args.previous_report):raise ValueError('REPORT_REVISION_LINK_MISMATCH')
    expected=role.get('check_feedback',[])
    if expected and [plain(r) for r in args.check_results] != [f['reference'] for f in expected]:raise ValueError('REPORT_CHECK_FEEDBACK_REQUIRED')
    if plain(args.report.source)!=request['binding']: raise ValueError('REPORT_SUBJECT_BINDING_MISMATCH')
    if set(args.fact_selectors)!={f.fact_id for f in args.report.facts}: raise ValueError('EVERY_FACT_REQUIRES_SELECTORS')
    for fact in args.report.facts:
        selectors=args.fact_selectors[fact.fact_id]
        if not selectors: raise ValueError('EMPTY_FACT_SELECTORS')
        for selector in selectors:
            if plain(selector.reference) not in [plain(r) for r in fact.evidence]: raise ValueError('FACT_EVIDENCE_LINK_MISMATCH')
            validate_selector(ctx.store,selector)
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
        raise ValueError('UNKNOWN_RECOMMENDATION')
    if args.next_action=='bounded_verification' and (args.disposition!='adopt' or args.recommendation_id is None):
        raise ValueError('VERIFICATION_REQUIRES_EXPLICIT_ADOPTION')
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


def preflight(inp,args,reg):
    return dict(cost=dict(wall_s=5.))
