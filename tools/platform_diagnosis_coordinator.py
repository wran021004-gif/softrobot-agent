"""Sequential role transitions using the unchanged provider/recovery loop."""
from tools.platform_store import plain


def bind_diagnostic_grant(host,request_reference):
    """A request may narrow a frozen grant; it cannot expand it."""
    from schemas.platform_handoff import DiagnosisRequest
    request=DiagnosisRequest.model_validate(host.store.artifact(request_reference))
    with host.store.transaction() as db:
        session=host.store.session(host.run_id,db)
        if any(host.store.remaining(host.run_id,db)['used'].values()):raise ValueError('DIAGNOSTIC_GRANT_MUST_PRECEDE_WORK')
        policy=session['snapshot']['input']['policy'];budget=plain(request.budget)
        if any(value>policy['budget'][key] for key,value in budget.items()):raise ValueError('ROLE_BUDGET_EXCEEDS_FROZEN_GRANT')
        if not set(request.permitted_tools)<=policy['tool_bindings'].keys():raise ValueError('ROLE_TOOLS_EXCEED_FROZEN_GRANT')
        state=session['state'];state['role_grant']=dict(budget=budget,permitted_tools=request.permitted_tools,request=plain(request_reference))
        host.store.update_state(db,host.run_id,state)
        host.store.event(db,host.run_id,'diagnostic_grant','restricted',inputs=[request_reference],outputs=[host.store.put(db,state['role_grant'])])


def configure_role(host,role,instructions,**context):
    with host.store.transaction() as db:
        state=host.store.session(host.run_id,db)['state']
        state['role_context']=dict(role=role,instructions=instructions,**context)
        host.store.update_state(db,host.run_id,state)
        host.store.event(db,host.run_id,'role_context','configured',outputs=[host.store.put(db,state['role_context'])])


def transfer_recovery(source,destination):
    """One phase-wide correction allowance; transitions never reset counters."""
    previous=source.store.session(source.run_id)['state']
    with destination.store.transaction() as db:
        state=destination.store.session(destination.run_id,db)['state']
        for key in ('protocol_corrections_used','protocol_corrections_consecutive','length_retries_used','argument_limit_correction_used'):
            if key in previous:state[key]=previous[key]
        destination.store.update_state(db,destination.run_id,state)


def run_until_handoff(host,kind):
    from tools.platform_models import run_loop
    run_loop(host)
    session=host.store.session(host.run_id)
    ref=session['state'].get('handoffs',{}).get(kind)
    if ref is None:raise RuntimeError('EXPECTED_HANDOFF_MISSING: '+kind+' '+session['status']+' '+str(session['state'].get('stop_reason')))
    return ref
