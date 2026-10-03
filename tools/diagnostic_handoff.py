"""Offline Milestone 2 consumer boundary, using existing exact selectors."""
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
    permitted=working_state.evidence['permitted_references']
    with store.connect(True) as db:
        state=store.session(working_state.run_id,db)['state']
        selectors=[row['selector'] for row in state.get('fact_catalog',{}).values()]
        for assessment in handoff.assessments:
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
    supporting=[select('/candidate/holding_max_speed_m_s'),select('/candidate/joint_reach_holding_passed')]
    contradicting=[select('/candidate/terminal_reach_passed')]
    feedback=working_state.products.feedback
    result=DiagnosticHandoff(provenance='engineering_fixture',
        working_state=dict(run_id=working_state.run_id,contract=working_state.contract,version=working_state.version),
        scope=dict(task=working_state.task,candidate=working_state.latest_tested,
            model=working_state.task['execution_model'],controller=working_state.parameter_impacts['mapped'][0]['controller'],
            context_id=working_state.evidence['context_id'],evidence_scope=working_state.evidence['scope']),
        unmet_criterion='Joint reach/holding acceptance remains false; terminal reach passed.',
        assessments=[dict(kind='observation',statement='The saved candidate failed holding speed while passing terminal reach.',supporting=supporting,contradicting=contradicting),
            dict(kind='hypothesis',statement='Holding-speed cost may affect motion, but this one-weight comparison does not identify a dominant cause.',
                supporting=supporting,contradicting=contradicting,
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
