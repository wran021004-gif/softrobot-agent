"""Sequential role transitions using the unchanged provider/recovery loop."""
from tools.platform_store import plain


def validate_request_scope(request, protocol):
    """The new request must itself carry the frozen numerical authorization."""
    from schemas.platform_handoff import SavedStateScope
    scope=request.saved_state_check
    if scope is None:
        raise ValueError('SAVED_STATE_SCOPE_REQUIRED: separate retained-evidence reading from one saved-state numerical check in saved_state_check and scope; production changes and backend execution remain excluded.')
    frozen=SavedStateScope.model_validate(protocol['saved_state_check'])
    for name in ('model','horizon_s','integration','integration_step_s','configuration_scope','max_checks'):
        if getattr(scope,name)!=getattr(frozen,name):raise ValueError('REQUEST_CHECK_SCOPE_MISMATCH: '+name)
    if not set(scope.operations)<=set(frozen.operations):raise ValueError('REQUEST_CHECK_OPERATION_OUTSIDE_FROZEN_SCOPE')
    if scope.max_wall_s>frozen.max_wall_s:raise ValueError('REQUEST_CHECK_TIME_EXCEEDS_FROZEN_SCOPE')
    if set(scope.numerical_limits)!=set(frozen.numerical_limits) or any(
            v<0 or v>frozen.numerical_limits[k] for k,v in scope.numerical_limits.items()):
        raise ValueError('REQUEST_NUMERICAL_LIMITS_OUTSIDE_FROZEN_SCOPE')
    for operation in scope.operations:
        units='local_solves' if operation=='local_comparison' else 'prediction_evaluations'
        if scope.numerical_limits[units]<2:raise ValueError('REQUEST_NUMERICAL_LIMIT_INSUFFICIENT_FOR_PAIR')
    required={'diagnosis.inspect_evidence','diagnosis.check_request','diagnosis.submit','evidence.read'}
    if not required<=set(request.permitted_tools):raise ValueError('REQUEST_TOOLS_CANNOT_COMPLETE_SAVED_STATE_WORKFLOW')
    if request.budget.backend_solves or request.budget.worker_calls:raise ValueError('REQUEST_BACKENDS_AND_WORKERS_EXCLUDED')


def adopted_check_parameter(store, report_reference, response_reference):
    """Disposition never gates independent checking; only matched local pairs need adoption."""
    response=store.artifact(response_reference)
    if response['report']!=plain(report_reference):raise ValueError('DESIGN_REPORT_LINK_MISMATCH')
    if response['disposition']!='adopt' or response['next_action']!='bounded_verification':return None
    recommendation=next(r for r in store.artifact(report_reference)['recommendations']
        if r['recommendation_id']==response['recommendation_id'])
    if recommendation['action']!='control_parameter':return None
    return dict(parameter=recommendation['parameter'],value=recommendation['value'])


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
        if context.get('phase_budget') is not None:
            context['phase_budget']={**context['phase_budget'], 'started_usage':host.store.remaining(host.run_id,db)['used']}
            context['successful_read_turns']=0
            context['phase_started_turn']=state.get('turn',0)
        if role=='design':
            delivery='design.review_verification' if context.get('verification') else ('design.respond_diagnosis' if context.get('report') else 'diagnosis.request')
            context['phase_tools']=['evidence.read',delivery]
            context['phase_started_turn']=state.get('turn',0)
        state['role_context']=dict(role=role,instructions=instructions,**context)
        host.store.update_state(db,host.run_id,state)
        host.store.event(db,host.run_id,'role_context','configured',outputs=[host.store.put(db,state['role_context'])])


def transfer_recovery(source,destination):
    """One phase-wide correction allowance; transitions never reset counters."""
    previous=source.store.session(source.run_id)['state']
    with destination.store.transaction() as db:
        state=destination.store.session(destination.run_id,db)['state']
        for key in ('protocol_corrections_used','protocol_corrections_consecutive','length_retries_used','argument_limit_correction_used','repairs','business_failures_total','business_feedback'):
            if key in previous:state[key]=previous[key]
            else:state.pop(key,None)
        destination.store.update_state(db,destination.run_id,state)


def recovery_status(state, config):
    limits=config.get('protocol_recovery') or dict(max_total=1,max_consecutive=1)
    total=state.get('protocol_corrections_used',0);consecutive=state.get('protocol_corrections_consecutive',0)
    repairs=state.get('repairs',0)
    return dict(version='2.0.0',scope='workflow shared across phases and contexts',
        protocol=dict(category='native_schema_or_envelope',limits=limits,total_used=total,
            consecutive_used=consecutive,total_remaining=max(0,limits['max_total']-total),
            consecutive_remaining=max(0,limits['max_consecutive']-consecutive),
            reset='Completed business call resets consecutive only; decoding alone does not.'),
        business=dict(category='accepted_call_execution_rejected_or_failed',limit=config['max_repairs'],
            consecutive_failures=repairs,total_failures=state.get('business_failures_total',0),
            remaining_repairs=max(0,config['max_repairs']-repairs),
            stop_when='consecutive_failures > limit; two repair opportunities after first failure',
            reset='Completed business call resets consecutive; phase/context switch does not.',
            feedback=state.get('business_feedback')),
        transport=dict(category='provider_transport_failure',automatic_retry=False),
        length=dict(category='truncated_without_usable_action',limit=1,used=state.get('length_retries_used',0),
            configuration=config.get('length_recovery')),stop_reason=state.get('stop_reason'))


def run_until_handoff(host,kind):
    from tools.platform_models import run_loop
    previous=host.store.session(host.run_id)['state'].get('handoffs',{}).get(kind)
    run_loop(host)
    session=host.store.session(host.run_id)
    ref=session['state'].get('handoffs',{}).get(kind)
    if ref is None or ref == previous:raise RuntimeError('EXPECTED_NEW_HANDOFF_MISSING: '+kind+' '+session['status']+' '+str(session['state'].get('stop_reason')))
    return ref


def validate_check(store,role,args):
    """Bind executable enums to exactly the selected saved state and input."""
    from extensions.tendon_family.diagnostic_evidence import BoundReader
    from extensions.tendon_family.diagnostic_math import SavedStateCheck
    from tools.platform_handoff import validate_selector
    from schemas.platform_handoff import DiagnosisRequest
    if plain(args.diagnosis_request)!=role['request']:raise ValueError('CHECK_REQUEST_LINK_MISMATCH')
    request=DiagnosisRequest.model_validate(store.artifact(role['request']))
    if plain(request.binding)!=role['binding']:raise ValueError('CHECK_REQUEST_BINDING_MISMATCH')
    # Historical read-only requests confer no numerical authority, even when an
    # executor has its own tool binding. Never broaden the saved request here.
    scope=request.saved_state_check
    if scope is None:raise ValueError('SAVED_STATE_SCOPE_REQUIRED: this request authorizes no numerical check')
    if role.get('protocol',{}).get('saved_state_check') is not None:
        validate_request_scope(request,role['protocol'])
    if 'diagnosis.check_request' not in request.permitted_tools:raise ValueError('CHECK_TOOL_NOT_IN_REQUEST_SCOPE')
    if args.operation not in scope.operations:raise ValueError('CHECK_OPERATION_NOT_IN_REQUEST_SCOPE')
    for name in ('model','horizon_s','integration','integration_step_s'):
        if getattr(args,name)!=getattr(scope,name):raise ValueError('CHECK_OUTSIDE_REQUEST_SCOPE: '+name)
    if set(args.work_limits)-{'wall_s','local_solves','prediction_evaluations'}:
        raise ValueError('CHECK_UNKNOWN_WORK_LIMIT: use only wall_s, local_solves and prediction_evaluations; backend/worker limits are host-bound, not work_limits fields')
    if not 0<args.work_limits.get('wall_s',0)<=scope.max_wall_s:raise ValueError('CHECK_TIME_OUTSIDE_REQUEST_SCOPE')
    units='local_solves' if args.operation=='local_comparison' else 'prediction_evaluations'
    if not 2<=args.work_limits.get(units,0)<=scope.numerical_limits[units]:
        raise ValueError('CHECK_NUMERICAL_UNITS_OUTSIDE_REQUEST_SCOPE: '+units+' must explicitly cover the pair within the request grant')
    import json
    with store.connect(True) as db:
        row=db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()
    if row is None:raise ValueError('FROZEN_DIAGNOSTIC_ALLOCATION_REQUIRED')
    work=json.loads(row[0])
    if work['used'][units]+2>work['limits'][units]:raise ValueError('DIAGNOSTIC_WORK_LIMIT_EXHAUSTED')
    if not args.check_id or args.operation is None or args.update_id is None:raise ValueError('TYPED_CHECK_ID_OPERATION_UPDATE_REQUIRED')
    reader=BoundReader(store,role['binding']);source=reader.resolve(reader.binding['execution_id'])
    reference=source['files']['controller_observations.json']
    expected_input=args.update_id-1 if args.operation=='local_comparison' else args.update_id
    if plain(args.initial_state.reference)!=reference or args.initial_state.pointer!=f'/{args.update_id}/measured_initial_state':raise ValueError('CHECK_STATE_BINDING_MISMATCH')
    if plain(args.input.reference)!=reference or args.input.pointer!=f'/{expected_input}/actual_tension_n':raise ValueError('CHECK_CURRENT_VERSUS_PREVIOUS_INPUT_MISMATCH')
    validate_selector(store,args.initial_state);validate_selector(store,args.input)
    feedback=role.get('check_feedback',[])
    if len(feedback)>=min(role.get('max_checks',2),scope.max_checks):raise ValueError('DIAGNOSTIC_CHECK_LIMIT')
    if feedback and (plain(args.prior_result)!=feedback[-1]['reference'] or not args.additional_need):raise ValueError('ADDITIONAL_CHECK_REQUIRES_RESULT_AND_SPECIFIC_NEED')
    if args.model!='model.gvs@1.0.0' or args.integration!='implicit_euler':raise ValueError('CHECK_NUMERICAL_PROTOCOL_UNSUPPORTED')
    units='local_solves' if args.operation=='local_comparison' else 'prediction_evaluations'
    if units in args.work_limits and args.work_limits[units]<2:raise ValueError('CHECK_WORK_LIMIT_INSUFFICIENT_FOR_PAIR')
    if args.operation=='local_comparison':
        adopted=role.get('adopted_parameter')
        if adopted!={'parameter':args.changed_parameter,'value':args.changed_value}:
            raise ValueError('LOCAL_PAIR_REQUIRES_MATCHED_DESIGN_ADOPTION_FIRST')
        update=store.artifact(reference)[args.update_id]
        config=source['configuration']
        horizon=update.get('effective_horizon',config['policy']['controller']['parameters']['data']['recipe']['horizon'])
        if abs(horizon*config['task']['timing']['control_period_s']-args.horizon_s)>1e-9:
            raise ValueError('LOCAL_PAIR_SAVED_PLAN_HORIZON_MISMATCH: select a saved update whose effective plan horizon matches the declared request horizon')
    elif args.changed_parameter is not None or args.changed_value is not None:
        raise ValueError('PREDICTION_CHECK_DOES_NOT_CHANGE_CONTROLLER_PARAMETERS')
    return SavedStateCheck(binding=role['binding'],update_id=args.update_id,operation=args.operation,
        horizon_s=args.horizon_s,integration_step_s=args.integration_step_s,
        max_wall_s=args.work_limits.get('wall_s',180.),changed_parameter=args.changed_parameter,changed_value=args.changed_value)


def execute_check_feedback(diagnostic,executor,reference):
    """Execute one model-selected check and resume the same diagnostic grant."""
    from schemas.platform_handoff import DiagnosticCheckRequest,ScopedDiagnosticCheckRequest
    role=diagnostic.store.session(diagnostic.run_id)['state']['role_context']
    value=diagnostic.store.artifact(reference)
    schema=ScopedDiagnosticCheckRequest if 'local_question' in value else DiagnosticCheckRequest
    args=schema.model_validate(value)
    numerical=validate_check(diagnostic.store,role,args)
    executor.resume()
    receipt=executor.invoke(dict(request_id='check-'+args.check_id,tool_id='diagnosis.saved_state_check',tool_version='1.0.0',
        arguments=plain(numerical),reason='Execute the diagnostic model-selected typed check under the frozen project grant.',evidence=[reference],cache='new'))
    with diagnostic.store.transaction() as db:
        feedback=dict(check_request=plain(reference),diagnosis_request=plain(args.diagnosis_request),check_id=args.check_id,
            hypotheses=args.hypotheses,protocol=plain(numerical),receipt=receipt,result=receipt.get('output'))
        if isinstance(args,ScopedDiagnosticCheckRequest):
            feedback.update(local_question=args.local_question,discriminating_observations=args.discriminating_observations,unresolved=args.unresolved)
        ref=plain(diagnostic.store.put(db,feedback))
        state=diagnostic.store.session(diagnostic.run_id,db)['state']
        result=diagnostic.store.artifact(receipt['output']) if receipt.get('output') else None
        if role.get('max_checks') == 1 and result and 'detail' in result:
            # Keep exact scalar pointers while leaving full trajectories in the
            # immutable result artifact for inspection outside the inline view.
            result={**result,'detail':{**result['detail'],'rows':[
                {k:v for k,v in row.items() if k not in ('physical_motion','parameters','verification')}
                for row in result['detail'].get('rows',[])]}}
        state['role_context'].setdefault('check_feedback',[]).append(dict(reference=ref,**feedback,result_content=result))
        state['role_context']['instructions'] += ' Consume check_feedback now, update competing hypotheses, and submit a revised report citing every feedback reference in check_results. A second check needs the prior result and a specific unresolved need; otherwise submit.'
        if role.get('max_checks') == 1:
            state['role_context']['phase_tools']=['diagnosis.submit']
            if role.get('after_feedback_reservations'):
                state['role_context']['phase_budget'].update(role['after_feedback_reservations'])
            state['role_context']['instructions'] += ' The one-check allowance is spent. Only diagnosis.submit is available. Cite result selectors and state whether each checked hypothesis is supported, weakened, or unresolved; no further check is authorized.'
        diagnostic.store.update_state(db,diagnostic.run_id,state,'paused')
        diagnostic.store.event(db,diagnostic.run_id,'check_feedback','available',inputs=[reference],outputs=[ref])
    return ref
