"""Offline Milestone 2 consumer boundary, using existing exact selectors."""
from contextlib import closing
from schemas.working_state import DiagnosticHandoff
from tools.platform_store import plain
from tools.platform_handoff import pointer


def consume_handoff(store, working_state, submission):
    handoff=DiagnosticHandoff.model_validate(submission)
    if handoff.working_state!={'run_id':working_state.run_id,'contract':working_state.contract,'version':working_state.version}:
        raise ValueError('DIAGNOSTIC_WORKING_STATE_MISMATCH')
    if (handoff.scope['evidence_scope']!=working_state.evidence['scope'] or
            handoff.scope['context_id']!=working_state.evidence['context_id']):
        raise ValueError('DIAGNOSTIC_EVIDENCE_SCOPE_MISMATCH')
    if handoff.scope['candidate']!=working_state.latest_tested:
        raise ValueError('DIAGNOSTIC_CANDIDATE_MISMATCH')
    expected=dict(task=working_state.task,model=working_state.task['execution_model'],
        controller=working_state.parameter_impacts['mapped'][0]['controller'])
    if any(handoff.scope.get(k)!=v for k,v in expected.items()):
        raise ValueError('DIAGNOSTIC_TASK_MODEL_SCOPE_MISMATCH')
    if handoff.provenance=='accepted_diagnostic_product':
        from tools.diagnostic_handoff import accepted_product
        for name in ('source_report','previous_assessment'):
            accepted_product(store,handoff.scope.get(name),'diagnosis_report')
        from tools.diagnostic_handoff import validate_lineage
        validate_lineage(store,working_state,handoff.scope)
    permitted=working_state.evidence['permitted_references']
    with closing(store.connect(True)) as db:
        state=store.session(working_state.run_id,db)['state']
        selectors=[row['selector'] for row in state.get('fact_catalog',{}).values()]
        for assessment in handoff.assessments:
            if (len(assessment.supporting)!=len(assessment.supporting_relevance) or
                    len(assessment.contradicting)!=len(assessment.contradicting_relevance) or
                    any(not r.strip() for r in assessment.supporting_relevance+assessment.contradicting_relevance)):
                raise ValueError('DIAGNOSTIC_RELATIONSHIP_RELEVANCE_REQUIRED')
            for selector in assessment.supporting+assessment.contradicting:
                value=plain(selector)
                if value['reference'] not in permitted or value not in selectors:
                    raise ValueError('DIAGNOSTIC_SELECTOR_OUTSIDE_CURRENT_SCOPE')
                if pointer(store.artifact(selector.reference,db=db),selector.pointer)!=selector.value:
                    raise ValueError('DIAGNOSTIC_SELECTOR_VALUE_MISMATCH')
    # Validation proves scope and exact citation agreement only.
    return handoff


def engineering_fixture(store, working_state):
    state=store.session(working_state.run_id)['state']
    rows=list(state.get('fact_catalog',{}).values())
    def select(suffix):
        matches=[r['selector'] for r in rows if r['selector']['pointer'].endswith(suffix)]
        if not matches:raise ValueError('FIXTURE_REQUIRES_SAVED_COMPARISON: '+suffix)
        return matches[-1]
    supporting=[select('/candidate/holding_max_speed_m_s'),select('/candidate/joint_reach_holding_passed'),select('/candidate/terminal_reach_passed')]
    relevance=['Measured holding speed exceeds the saved speed limit.',
        'Joint acceptance is false, consistent with the failed holding criterion.',
        'Terminal reach passes independently; it is compatible with holding-speed failure.']
    feedback=working_state.products.feedback
    result=DiagnosticHandoff(provenance='engineering_fixture',
        working_state=dict(run_id=working_state.run_id,contract=working_state.contract,version=working_state.version),
        scope=dict(task=working_state.task,candidate=working_state.latest_tested,
            model=working_state.task['execution_model'],controller=working_state.parameter_impacts['mapped'][0]['controller'],
            context_id=working_state.evidence['context_id'],evidence_scope=working_state.evidence['scope']),
        unmet_criterion='Joint reach/holding acceptance remains false; terminal reach passed.',
        assessments=[dict(kind='observation',statement='The saved candidate failed holding speed while passing terminal reach.',supporting=supporting,supporting_relevance=relevance),
            dict(kind='hypothesis',statement='Holding-speed cost may affect motion, but this one-weight comparison does not identify a dominant cause.',
                supporting=supporting,supporting_relevance=['The unmet speed criterion motivates testing a speed cost; it does not prove its cause.',
                    'Joint failure supplies the performance problem, not causal attribution.',
                    'Reach success bounds the problem to holding in this case; it does not refute a holding hypothesis.'],
                previous_assessment=working_state.products.initial_report,changed_by=[feedback] if feedback else []),
            dict(kind='unresolved_question',statement='Would a separately authorized bounded comparison preserve reach while reducing holding speed sufficiently?')],
        check=dict(proposal='Future bounded one-weight experiment with fixed task, robot and evaluation; this fixture executes nothing.',
            expected_observations=['Holding speed decreases and joint acceptance is gained without terminal reach failure.'],
            weakening_observations=['Speed remains outside its limit or terminal reach worsens beyond tolerance.'],
            capability='simulation.run + evaluation.run + control.profile_report',
            authorization='Unavailable in this offline stage; requires a new explicit search-batch grant and phase bindings.',
            budget=dict(required_reservations_s=dict(simulation=900,evaluation=30,profile=60),
                current_spendable=working_state.budgets['spendable'],backend_solves_required=1),
            proceed_if='New sealed joint acceptance and comparison support the hypothesis under the approved batch plan.',
            revise_if='Directional changes occur but acceptance remains unmet or contradicting evidence grows.',
            stop_if='Grant/budget absent, unresolved operation, or approved batch stopping condition is met.'))
    return consume_handoff(store,working_state,result)


def accepted_product(store, reference, kind):
    """Acceptance comes from host events, never a submitted provenance label."""
    import json
    if not reference:raise ValueError('ACCEPTED_PRODUCT_REQUIRED: '+kind)
    with closing(store.connect(True)) as db:
        for row in db.execute('SELECT body FROM events ORDER BY seq'):
            event=json.loads(row[0])
            if event['kind']=='role_transition' and event['status']==kind and reference in event['outputs']:
                return store.artifact(reference,db=db)
            if event['kind']=='accepted_saved_report_handoff' and event['status']=='verified':
                record=store.artifact(event['outputs'][0],db=db)
                if kind=='diagnosis_report' and reference==record.get('source_report'):
                    return store.artifact(reference,db=db)
    raise ValueError('PRODUCT_NOT_HOST_ACCEPTED: '+kind)


def source_record(store, reference):
    import json
    with closing(store.connect(True)) as db:
        for row in db.execute("SELECT body FROM events ORDER BY seq"):
            e=json.loads(row[0])
            if e['kind']=='accepted_saved_report_handoff' and e['status']=='verified' and reference in e['outputs']:
                return store.artifact(reference,db=db)
    raise ValueError('VERIFIED_SOURCE_RECORD_REQUIRED')


def validate_lineage(store, view, scope):
    from extensions.tendon_family.diagnostic_evidence import BoundReader
    record=source_record(store,scope.get('source_record'))
    if record['source_report']!=scope.get('source_report'):raise ValueError('SOURCE_REPORT_LINEAGE_MISMATCH')
    reader=BoundReader(store,scope['binding']);source=reader.resolve(reader.binding['execution_id'])
    candidate=dict(candidate_id=source['metadata']['candidate'],execution_id=source['execution_id'],
        configuration=source['metadata']['candidate_input'],owner_run_id=source['owner'])
    if candidate!=view.latest_tested or record['subject']!=candidate or record['baseline']!=view.baseline or scope.get('baseline')!=view.baseline:
        raise ValueError('HANDOFF_EXECUTION_BASELINE_MISMATCH')
    report=accepted_product(store,scope['previous_assessment'],'diagnosis_report')
    if report['report']['source']!=scope['binding']:raise ValueError('ASSESSMENT_BINDING_MISMATCH')
    snapshot=accepted_product(store,scope.get('working_state_snapshot'),'diagnostic_working_state')
    if (snapshot['run_id']!=view.run_id or scope.get('budget')!=snapshot['budgets'] or
            scope.get('budget',{}).get('project',{}).get('limit')!=view.budgets['project']['limit'] or
            scope.get('acceptance')!=view.acceptance or scope.get('grant')!=view.budgets['role_grant'] or
            scope.get('feedback')!=record['feedback']):
        raise ValueError('HANDOFF_ACCEPTANCE_GRANT_FEEDBACK_MISMATCH')
    if report.get('previous_report'):
        accepted_product(store,report['previous_report'],'diagnosis_report')
        if scope.get('check_result') not in report.get('check_results',[]):raise ValueError('REVISION_RESULT_LINEAGE_MISMATCH')
        result=store.artifact(scope['check_result'])
        proposal=accepted_product(store,result['proposal'],'diagnostic_check')
        if result.get('execution_id')!=source['execution_id'] or result.get('binding')!=scope['binding'] or proposal['binding']!=scope['binding']:
            raise ValueError('CHECK_RESULT_EXECUTION_BINDING_MISMATCH')
        if result['previous_assessment']!=report['previous_report'] or proposal['previous_assessment']!=report['previous_report']:
            raise ValueError('CHECK_PREVIOUS_ASSESSMENT_MISMATCH')
        with closing(store.connect(True)) as db:
            import json
            receipts=[json.loads(r[0]) for r in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL')]
        if result['receipt'] not in receipts:raise ValueError('CHECK_RECEIPT_NOT_SEALED')
        if result['result']!=result['receipt']['output']:raise ValueError('CHECK_RESULT_RECEIPT_MISMATCH')


def numerical_eligibility(store,binding,horizon_s=.01):
    """Read saved metadata; never shorten a horizon or run a solver."""
    from extensions.tendon_family.diagnostic_evidence import BoundReader
    reader=BoundReader(store,binding);source=reader.resolve(reader.binding['execution_id'])
    updates=reader.read_file(source,'controller_observations.json');cfg=source['configuration']
    period=cfg['task']['timing']['control_period_s'];configured=cfg['policy']['controller']['parameters']['data']['recipe']['horizon']
    eligible=[i for i,u in enumerate(updates) if i>=1 and u.get('measured_initial_state') is not None
        and u.get('actual_tension_n') is not None]
    local=[i for i in eligible if abs(updates[i].get('effective_horizon',configured)*period-horizon_s)<1e-9]
    return dict(horizon_s=horizon_s,control_period_s=period,model='model.gvs@1.0.0',
        prediction_braking=eligible,local_comparison=local,
        local_requirement='Exact design adoption of the changed parameter/value is additionally required.',
        limitation='Local projected-model calculation, separate from recorded serial-backend motion; no new backend execution.')


def bind_handoff(store,view,role,assessments,check,*,check_result=None):
    with store.transaction() as db:
        snapshot=plain(store.put(db,view))
        store.event(db,view.run_id,'role_transition','diagnostic_working_state',outputs=[snapshot])
    scope=dict(task=view.task,candidate=view.latest_tested,baseline=view.baseline,
        model=view.task['execution_model'],controller=view.parameter_impacts['mapped'][0]['controller'],
        context_id=view.evidence['context_id'],evidence_scope=view.evidence['scope'],binding=role['binding'],
        source_report=role['source_report'],source_record=role['source_record'],previous_assessment=role['previous_report'],
        feedback=role['historical_feedback'],acceptance=view.acceptance,grant=view.budgets['role_grant'],budget=view.budgets,
        check_result=check_result,working_state_snapshot=snapshot)
    value=DiagnosticHandoff(provenance='accepted_diagnostic_product',working_state=dict(
        run_id=view.run_id,contract=view.contract,version=view.version),scope=scope,
        unmet_criterion='Historical joint reach/holding acceptance is false; exact criteria are host-bound.',
        assessments=assessments,check=check)
    return consume_handoff(store,view,value)


def propose_check(ctx,args):
    from tools.platform_handoff import require_role,transition
    from tools.working_state import project_working_state
    from tools.diagnostic_revision import resolve_aliases
    from tools.platform_diagnosis_coordinator import validate_check
    from schemas.platform_handoff import ScopedDiagnosticCheckRequest
    require_role(ctx,'diagnostic');state=ctx.store.session(ctx.run_id)['state'];role=state['role_context']
    report=accepted_product(ctx.store,role['previous_report'],'diagnosis_report')
    hypotheses={r['cause']:r for r in report['report']['attribution']}
    if len(set(args.assessment_ids))!=len(args.assessment_ids) or set(args.assessment_ids)-hypotheses.keys():
        raise ValueError('CHECK_ASSESSMENT_NOT_IN_ACCEPTED_REPORT')
    if {r.assessment_id for r in args.expected}!=set(args.assessment_ids):raise ValueError('EXPECTED_OUTCOMES_MUST_COVER_CHECKED_ASSESSMENTS')
    if set(r.assessment_id for r in args.relationships)-set(args.assessment_ids):raise ValueError('RELATIONSHIP_ASSESSMENT_MISMATCH')
    if not 0<args.work_limits.get('wall_s',0)<=180:raise ValueError('CHECK_WALL_LIMIT: (0,180] seconds')
    binding=ctx.store.artifact(role['binding']);reader_eligibility=numerical_eligibility(ctx.store,role['binding'])
    valid_ids=reader_eligibility['prediction_braking']+[0]
    if len(set(args.update_ids))!=len(args.update_ids) or set(args.update_ids)-set(valid_ids):raise ValueError('CHECK_UPDATE_OUTSIDE_SAVED_COVERAGE')
    numerical=None
    if args.operation=='evidence_query':
        if args.view is None or (args.view!='motion' and not args.update_ids):raise ValueError('QUERY_VIEW_AND_COVERAGE_REQUIRED')
        if args.view=='motion' and args.update_ids:raise ValueError('MOTION_QUERY_COVERS_FINAL_WINDOW: update_ids must be empty')
        allowed_units={'m','m/s','s','N','rad/m','rad/(m*s)','control intervals','iteration index','status string'}
        if set(args.units)-allowed_units:raise ValueError('QUERY_UNITS_UNSUPPORTED: use SI units and retained metadata units')
        if args.changed_parameter is not None or args.changed_value is not None:raise ValueError('EVIDENCE_QUERY_CHANGES_NO_PARAMETER')
        if args.work_limits.get('tool_calls')!=1:raise ValueError('QUERY_LIMIT_REQUIRES_ONE_TOOL_CALL')
    else:
        if args.view is not None or len(args.update_ids)!=1:raise ValueError('NUMERICAL_CHECK_REQUIRES_ONE_UPDATE_AND_NO_QUERY_VIEW')
        index=args.update_ids[0]
        if index not in reader_eligibility[args.operation]:raise ValueError('NUMERICAL_UPDATE_INELIGIBLE_FOR_REQUEST_HORIZON')
        if not set(args.units)<={'m','m/s','s','N','rad/m','rad/(m*s)'}:raise ValueError('NUMERICAL_UNITS_UNSUPPORTED')
        from extensions.tendon_family.diagnostic_evidence import BoundReader
        reader=BoundReader(ctx.store,role['binding']);source=reader.resolve(binding['execution_id'])
        ref=source['files']['controller_observations.json'];updates=ctx.store.artifact(ref)
        input_index=index-1 if args.operation=='local_comparison' else index
        numerical=validate_check(ctx.store,role,ScopedDiagnosticCheckRequest(
            check_id='milestone2-check',operation=args.operation,update_id=index,diagnosis_request=role['request'],
            hypotheses=[hypotheses[k]['reason'] for k in args.assessment_ids]+['Other explanations may remain unresolved.'],
            initial_state=dict(reference=ref,pointer=f'/{index}/measured_initial_state',value=updates[index]['measured_initial_state']),
            input=dict(reference=ref,pointer=f'/{input_index}/actual_tension_n',value=updates[input_index]['actual_tension_n']),
            fixed_conditions=['Saved candidate state, input and task'],changed_parameter=args.changed_parameter,changed_value=args.changed_value,
            model='model.gvs@1.0.0',horizon_s=.01,integration='implicit_euler',integration_step_s=.002,
            metrics=args.units,work_limits=args.work_limits,acceptance_criteria=args.stopping_conditions,
            local_question=args.question,discriminating_observations=[r.observation for r in args.expected],unresolved=args.limitations))
    assessments=[]
    for key in args.assessment_ids:
        supporting=[];contradicting=[];sr=[];cr=[]
        for r in args.relationships:
            if r.assessment_id!=key:continue
            selectors=resolve_aliases(state,{'relationship':r.references})['relationship']
            (supporting if r.relationship=='supporting' else contradicting).extend(selectors)
            (sr if r.relationship=='supporting' else cr).extend([r.relevance]*len(selectors))
        assessments.append(dict(kind='hypothesis',statement=key+': '+hypotheses[key]['reason'],supporting=supporting,
            contradicting=contradicting,supporting_relevance=sr,contradicting_relevance=cr,previous_assessment=role['previous_report']))
    check=dict(proposal=args.question,expected_observations=[r.observation for r in args.expected],
        weakening_observations=[r.observation for r in args.expected if r.effect in ('weaken','reject')] or ['Result leaves the distinction unresolved.'],
        capability='diagnosis.inspect_evidence@1.0.0' if args.operation=='evidence_query' else 'diagnosis.saved_state_check@1.0.0',
        authorization='Current frozen diagnosis request; no production change or backend execution.',budget=args.work_limits,
        proceed_if=args.distinguishes,revise_if='Interpret the received result against the declared outcomes.',stop_if='; '.join(args.stopping_conditions))
    view=project_working_state(ctx.store,ctx.run_id);handoff=bind_handoff(ctx.store,view,role,assessments,check)
    return transition(ctx,'diagnostic_check',dict(proposal=plain(args),handoff=plain(handoff),previous_assessment=role['previous_report'],
        binding=role['binding'],numerical=plain(numerical) if numerical else None,
        before_facts=[dict(field=r['field'],value=r['value']) for r in state['fact_catalog'].values()]))


def revise_assessment(ctx,args):
    """Reuse compact report expansion and its existing acceptance validator."""
    from tools.platform_handoff import require_role,submit
    from tools.diagnostic_revision import materialize,resolve_aliases
    from schemas.platform_handoff import InventoryDiagnosisSubmission
    require_role(ctx,'diagnostic');state=ctx.store.session(ctx.run_id)['state'];role=state['role_context']
    proposal=accepted_product(ctx.store,role['proposal'],'diagnostic_check');result=ctx.store.artifact(role['result_feedback'])
    if result['proposal']!=role['proposal'] or result['previous_assessment']!=role['previous_report']:raise ValueError('REVISION_CHECK_LINK_MISMATCH')
    if result['receipt']['execution_status']!='completed':raise ValueError('MILESTONE2_REQUIRES_COMPLETED_CHECK')
    relevant={c.identifier for c in args.changes if c.kind=='hypothesis'}
    if not set(proposal['proposal']['assessment_ids'])<=relevant:raise ValueError('REVISION_MUST_ADDRESS_CHECKED_ASSESSMENTS')
    selectors=resolve_aliases(state,{f.fact_id:f.references for f in args.new_facts})
    new_ids={f.fact_id for f in args.new_facts}
    if not any(set(c.supporting_fact_ids)&new_ids for c in args.changes):raise ValueError('REVISION_MUST_LINK_NEW_FACT_TO_ASSESSMENT')
    novel=[]
    for rows in selectors.values():
        for s in rows:
            if s['reference']!=result['result']:continue
            p=s['pointer']
            if result['kind']=='newly_read_historical_evidence' and not p.startswith(('/detail/evidence/','/detail/selected_prediction_summary/','/detail/late_motion/')):continue
            row=next(r for r in state['fact_catalog'].values() if r['selector']==s)
            if dict(field=row['field'],value=row['value']) not in proposal['before_facts'] and isinstance(s['value'],(int,float)) and not isinstance(s['value'],bool):novel.append(s)
    if not novel:raise ValueError('REVISION_REQUIRES_ADDITIONAL_RESULT_DETAIL: cite newly inspected detail beyond the initial supplied summary')
    initial=accepted_product(ctx.store,role['previous_report'],'diagnosis_report')
    compact={k:v for k,v in plain(args).items() if k in ('changes','new_facts','new_limitations','recommendation','rationale')}
    expanded=materialize(initial,compact,state)
    expanded.update(previous_report=role['previous_report'],request=role['request'],check_results=[role['result_feedback']])
    accepted=submit(ctx,InventoryDiagnosisSubmission.model_validate(expanded))
    # Immutable companion retains interpretation and exact proposal/result coverage.
    with ctx.store.transaction() as db:
        ref=ctx.store.put(db,dict(revision=plain(args),accepted_report=plain(accepted.reference),proposal=role['proposal'],
            feedback=role['result_feedback'],coverage=result['coverage'],new_information=novel,
            semantic_status='Model-authored interpretation; deterministic lineage/citation checks do not certify causality.'))
        ctx.store.event(db,ctx.run_id,'assessment_revision','interpreted',inputs=[accepted.reference],outputs=[ref])
    return accepted


def final_decision(ctx,args):
    from tools.platform_handoff import respond_workflow
    role=ctx.store.session(ctx.run_id)['state']['role_context']
    plan=accepted_product(ctx.store,role['experiment_plan'],'search_batch_plan')
    if not plan['structurally_operationally_valid'] or plan['execution_authorized']:raise ValueError('FINAL_REQUIRES_VALID_UNEXECUTED_PLAN')
    if plan['bindings']['revised_assessment']!=plain(args.report):raise ValueError('FINAL_PLAN_REVISION_MISMATCH')
    if plan['bindings']['check_feedback']!=role['result_feedback']:raise ValueError('FINAL_PLAN_CHECK_MISMATCH')
    return respond_workflow(ctx,args)
