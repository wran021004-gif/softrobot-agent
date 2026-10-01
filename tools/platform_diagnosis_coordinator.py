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
        if role=='design':
            delivery='design.review_verification' if context.get('verification') else ('design.respond_diagnosis' if context.get('report') else 'diagnosis.request')
            context['phase_tools']=['evidence.read',delivery]
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


def validate_check(store,role,args):
    """Bind executable enums to exactly the selected saved state and input."""
    from extensions.tendon_family.diagnostic_evidence import BoundReader
    from extensions.tendon_family.diagnostic_math import SavedStateCheck
    from tools.platform_handoff import validate_selector
    if not args.check_id or args.operation is None or args.update_id is None:raise ValueError('TYPED_CHECK_ID_OPERATION_UPDATE_REQUIRED')
    reader=BoundReader(store,role['binding']);source=reader.resolve(reader.binding['execution_id'])
    reference=source['files']['controller_observations.json']
    expected_input=args.update_id-1 if args.operation=='local_comparison' else args.update_id
    if plain(args.initial_state.reference)!=reference or args.initial_state.pointer!=f'/{args.update_id}/measured_initial_state':raise ValueError('CHECK_STATE_BINDING_MISMATCH')
    if plain(args.input.reference)!=reference or args.input.pointer!=f'/{expected_input}/actual_tension_n':raise ValueError('CHECK_CURRENT_VERSUS_PREVIOUS_INPUT_MISMATCH')
    validate_selector(store,args.initial_state);validate_selector(store,args.input)
    feedback=role.get('check_feedback',[])
    if len(feedback)>=2:raise ValueError('AT_MOST_TWO_DIAGNOSTIC_CHECKS')
    if feedback and (plain(args.prior_result)!=feedback[-1]['reference'] or not args.additional_need):raise ValueError('ADDITIONAL_CHECK_REQUIRES_RESULT_AND_SPECIFIC_NEED')
    if args.model!='model.gvs@1.0.0' or args.integration!='implicit_euler':raise ValueError('CHECK_NUMERICAL_PROTOCOL_UNSUPPORTED')
    units='local_solves' if args.operation=='local_comparison' else 'prediction_evaluations'
    if units in args.work_limits and args.work_limits[units]<2:raise ValueError('CHECK_WORK_LIMIT_INSUFFICIENT_FOR_PAIR')
    if args.operation=='local_comparison':
        adopted=role.get('adopted_parameter')
        if adopted!={'parameter':args.changed_parameter,'value':args.changed_value}:
            raise ValueError('LOCAL_PAIR_REQUIRES_MATCHED_DESIGN_ADOPTION_FIRST')
    return SavedStateCheck(binding=role['binding'],update_id=args.update_id,operation=args.operation,
        horizon_s=args.horizon_s,integration_step_s=args.integration_step_s,
        max_wall_s=args.work_limits.get('wall_s',180.),changed_parameter=args.changed_parameter,changed_value=args.changed_value)


def execute_check_feedback(diagnostic,executor,reference):
    """Execute one model-selected check and resume the same diagnostic grant."""
    from schemas.platform_handoff import DiagnosticCheckRequest
    role=diagnostic.store.session(diagnostic.run_id)['state']['role_context']
    args=DiagnosticCheckRequest.model_validate(diagnostic.store.artifact(reference))
    numerical=validate_check(diagnostic.store,role,args)
    executor.resume()
    receipt=executor.invoke(dict(request_id='check-'+args.check_id,tool_id='diagnosis.saved_state_check',tool_version='1.0.0',
        arguments=plain(numerical),reason='Execute the diagnostic model-selected typed check under the frozen project grant.',evidence=[reference],cache='new'))
    with diagnostic.store.transaction() as db:
        feedback=dict(check_request=plain(reference),diagnosis_request=plain(args.diagnosis_request),check_id=args.check_id,
            hypotheses=args.hypotheses,protocol=plain(numerical),receipt=receipt,result=receipt.get('output'))
        ref=plain(diagnostic.store.put(db,feedback))
        state=diagnostic.store.session(diagnostic.run_id,db)['state']
        result=diagnostic.store.artifact(receipt['output']) if receipt.get('output') else None
        state['role_context'].setdefault('check_feedback',[]).append(dict(reference=ref,**feedback,result_content=result))
        state['role_context']['instructions'] += ' Consume check_feedback now, update competing hypotheses, and submit a revised report citing every feedback reference in check_results. A second check needs the prior result and a specific unresolved need; otherwise submit.'
        diagnostic.store.update_state(db,diagnostic.run_id,state,'paused')
        diagnostic.store.event(db,diagnostic.run_id,'check_feedback','available',inputs=[reference],outputs=[ref])
    return ref
