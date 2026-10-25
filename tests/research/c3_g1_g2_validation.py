"""User-authorized bounded G1/G2 validation through the existing research interfaces."""
import argparse
import json
from pathlib import Path

from tests.research import c3_f1_f2_validation as prior
from tools.platform_host import Host
from tools.research import core
from tools.research.agent import load_credential, record
from tools.research.state import state
from tools.state_io import atomic_json, digest, read

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'evidence/c3_g1_g2'
SOURCE = 'C:/Users/gugugaga/.codex/attachments/b47b5887-0227-426f-9031-13cbb0fdda25/已粘贴的文本.txt'
AUTH = ('2026-10-25 explicit user G1/G2 authorization: G1 continuity <=2 and paired decisions <=4 '
        'DeepSeek requests, mathematics=0; only after G1 passes G2 <=8 DeepSeek requests including '
        'Reporter and <=4 total mathematical evaluations including preparation/internal calls. '
        'All stages: independent physics=0, NMPC=0, PPO=0; no retries, budget resets, full A/B '
        'or unbounded search. Necessary frozen task/design and cited scientific excerpts only. ' + SOURCE)
CONTINUITY_ID = 'c3-g1-continuity-20261025'
DECISION_ID = 'c3-g1-decisions-20261025'
PROBE = ROOT / 'runs/c3-g1-decision-probe'
G2_ID = 'c3-g2-scientific-20261025'
G2_OUT = ROOT / 'evidence/c3_g2_scientific_decision_loop'
G2_SOURCE = 'C:/Users/gugugaga/.codex/attachments/0b9bc8a1-5d03-48e6-84fc-1edfee7abd87/已粘贴的文本.txt'
G2_AUTH = ('2026-10-25 explicit independent G2 user authorization: <=8 total DeepSeek requests including Reporter; '
    '<=4 mathematical evaluations including preparation, internal solves and failures; <=24 public operations; '
    'independent physics=0, NMPC=0, PPO=0. One primary Agent-selected mathematical experiment and its feedback decision. '
    'No old Study reset, no new A/B or retry Study; ordinary commit/push authorized. ' + G2_SOURCE)


def g2_background():
    """Original B facts only; never import them into the new result ledger."""
    from tools.research.evidence_views import diagnostic_relations
    old = prior.historical_host(); s = state(old); ref = s['results'][-1]
    p = old.store.artifact(ref); mr = s['analysis_results'][-1]; m = old.store.artifact(mr)
    d = diagnostic_relations(old, ref)
    value = dict(kind='historical_scoped_evidence', owning_study=old.run_id,
        historical_only=True, original_reference=ref, historical_candidate=p['candidate'],
        metrics=p['acceptance']['metrics'], components=p['acceptance']['components'],
        critical_discrete_observations=[{k:r[k] for k in ('time_s','observed','raw_reference','read_pointer') if k in r}
            for r in d['task_diagnosis']['critical_samples']],
        task=old.store.artifact(p['candidate'])['configuration']['task'],
        sampled_model_witness=dict(reference=mr, method=m['trajectory']['method_version'],
            score=m['trajectory']['replayed_violation'], scope='Local sampled affine model; different control from NMPC; no physical acceptance'),
        historical_diagnostics=dict(reference=dict(artifact_id=digest(d),
            media_type='application/json'), pointer=''),
        saved_state_qualification=dict(update_id=30, actual_time_s=.30, native_qpos_qvel=True,
            integration_checkpoint=False, measured_prefix_intervals=30,
            current_study_admission='unavailable: existing native_point requires OWNED_NATIVE_EXECUTION_REQUIRED; no registered cross-Study native state rebinding',
            alternatives='Native methods may use standardized_initial_pretension; reduced model methods use their catalog prerequisites. Do not invent a saved_state.'),
        scope='Historical research background only. This Study regenerates the same design; no historical acceptance or costs transfer.')
    return value, old, p, m


def prepare_g2():
    from tools.research.state import save, update, guard
    from tools.research.design import generate_candidate, verify_candidate
    from tools.state_io import digest
    from tools.research.tool_readiness import execution_environment
    background, old, p, m = g2_background()
    background_ref = dict(artifact_id=digest(background), media_type='application/json')
    instructions = ('You are the autonomous scientific research Agent seeking a robot structure/control solution to the frozen task. '
        'This independent G2 is limited to one primary mathematical experiment and the decision after its real feedback. '
        'Do not generate/search designs, run independent physics, NMPC or PPO. A current candidate with the historical B design is already legally generated. '
        'Read the historical background ONCE per entire Study, not once per SDK Session: evidence_read(reference='+json.dumps(background_ref)+', view=full). '
        'Check read_state/pending_feedback_delivery; completed delivered reads satisfy that obligation. Purposeful rechecks remain legal. '
        'Read candidate view=mathematical_capabilities at /scientific_interpretation and /methods/<chosen method> for method meaning, prerequisites, costs and template (L1); other methods remain available on demand. '
        'Choose the research question and method yourself; no preferred method is prescribed. '
        'First submit a NEW research_plan action=diagnose (without diagnostic payload), recording the selected method, hypothesis, reason, expected observation, weakening observation, frozen conditions and total requested budget. '
        'Then invoke research_analysis with your own legal request. If admission rejects it, use its actual reason to correct it within remaining counts; do not fabricate a state or silently change the hypothesis. '
        'After one primary experiment returns computed/unknown/inconclusive, do not run another experiment. Consume the actual saved result and L1 feedback. '
        'Then submit a NEW research_plan action=stop: explain what remains supported, what changes, unresolved mechanisms, how this helps find a feasible solution, '
        'and the most valuable future design/control/verification action with its conditions and complete cost justification; proposing future physics is allowed but executing it is not. '
        'Use the exact stop_result_index and publicly read the new result before STOP; cite every new result. Reports do not grant formal read credit. '
        'Every Plan needs decision={hypothesis_id,research_intent:DIAGNOSE for diagnose or STOP for stop,selected_method,selected_candidate,requested_budget,claimed_inference:empirical_search}; '
        'also hypothesis,supporting_evidence,expected_observation,weakening_observation,fixed_conditions,stopping_condition,interpretation. '
        'Keep reasoning concise in Chinese. Uncertainty and results that weaken your hypothesis are valid outcomes. '
        'Budget is <=8 Provider including Reporter, <=4 total math evaluations including preparation/internal failures, <=24 public operations, independent physics/NMPC/PPO=0. Stop after G2.')
    h = host(G2_ID) if (ROOT / 'runs/research' / G2_ID / 'platform.sqlite').exists() else prior.provision('continuity', study_id=G2_ID, instructions=instructions,
        overrides=dict(base_commit='576a18a0be6e77da6840d09ab1a2f4360d499f30', mode='formal_research',
            capabilities=['analysis'], allowed_plan_actions=['diagnose','stop'],
            evidence_destination=str(G2_OUT.relative_to(ROOT))),
        budget_overrides=dict(provider_requests=8, mathematical_evaluations=4, public_operations=24,
            protected_provider_requests=1, protected_public_operations=2), source=G2_SOURCE, authorization=G2_AUTH)
    spec = state(h)['spec']; guard(h)
    original = old.store.artifact(p['candidate'])
    if m['candidate']!=p['candidate']: raise ValueError('HISTORICAL_MATHEMATICS_CANDIDATE_MISMATCH')
    request = original['parameters']
    existing = next((r for r in state(h)['candidates'].values() if h.store.artifact(r)['parameters']==request), None)
    generated = dict(status='generated', candidate=existing) if existing else generate_candidate(h, request,
        dict(origin='user_authorized_same_historical_design', historical_study=old.run_id,
             historical_candidate=p['candidate'], historical_result=background['original_reference']))
    if generated['status']!='generated': raise ValueError(generated)
    candidate = generated['candidate']; current = verify_candidate(h, candidate)
    for key in ('robot','task'):
        if current['configuration'][key]!=original['configuration'][key]: raise ValueError('HISTORICAL_DESIGN_OR_TASK_MISMATCH: '+key)
    for key in ('backend','discretization','dynamics_model','controller'):
        if current['configuration']['policy'][key]!=original['configuration']['policy'][key]: raise ValueError('HISTORICAL_MODEL_MISMATCH: '+key)
    # Preserve exact original artifacts as historical raw sources, never current results/candidates.
    for ref in (background['original_reference'], p['candidate'], original['configuration_reference'],
                p['profile']['motion'], background['sampled_model_witness']['reference']):
        if save(h, old.store.artifact(ref), 'imported_historical_raw_source')!=ref: raise ValueError('HISTORICAL_SOURCE_IDENTITY_MISMATCH')
    from tools.research.evidence_views import diagnostic_relations
    if save(h, diagnostic_relations(old, background['original_reference']), 'historical_l1_diagnostics')!=background['historical_diagnostics']['reference']:
        raise ValueError('HISTORICAL_DIAGNOSTIC_IDENTITY_MISMATCH')
    if save(h, background, 'authorized_historical_background')!=background_ref: raise ValueError('BACKGROUND_IDENTITY_MISMATCH')
    update(h, scoped_context=[background_ref])
    qualification = dict(candidate=candidate, historical_candidate=p['candidate'], parameters=current['parameters'],
        same_robot_task_model=True, current_candidate_owned=True, historical_results_not_registered_as_new=True,
        environment=execution_environment(spec), native_history=background['saved_state_qualification'])
    record(h, 'g2_candidate_qualification', qualification)
    atomic_json(G2_OUT / 'protocol.json', dict(study_id=G2_ID, authorization=G2_AUTH, background=background_ref,
        candidate=candidate, qualification=qualification, evaluation_focus=['research_effectiveness','action_relevance',
        'task_focus','feedback_use','resource_efficiency','evidence_scope'],
        outcome_rule='Real admission and costs are strict; scientific prose mistakes are review findings, not a block on the second decision.'))
    core.export(h)
    return dict(study_id=G2_ID, candidate=candidate, background=background_ref, environment=qualification['environment']['status'])


def live_g2(restore=False):
    import asyncio
    from tools.research.agent import converse
    h = host(G2_ID)
    try:
        asyncio.run(converse(h, session_handoff=False, restore_only=restore, pause_after_completed_invocations=1))
    finally:
        core.export(h)
    return dict(study_id=G2_ID, status=state(h)['research_status'], ledger=h.store.remaining())


def host(study_id):
    return Host(ROOT / 'runs/research' / study_id, study_id, actor='unified-research')


def prepare_g1():
    h = prior.provision('continuity', study_id=DECISION_ID,
        instructions='Read-only paired evaluation turns; new Plan required every turn; no scientific dispatch.',
        overrides=dict(base_commit='5e5f6532406eb7616f8da2d8984d74ba3f63f9af',
            evidence_destination='evidence/c3_g1_g2/decisions'),
        budget_overrides=dict(provider_requests=4, mathematical_evaluations=0),
        source=SOURCE, authorization=AUTH)
    result = prior.decision_probe(out=PROBE, destination=OUT, authorization=AUTH,
                                 version='c3-g1-paired-decisions-v1')
    core.export(h)
    return result


def audit_continuity():
    """Check settled original wire, exact feedback and a separate-process restore."""
    from tests.research.agent_math_decision_probe import provider_usage
    from tools.research.agent import pending
    from tools.research.research_context import read_coverage
    h = host(CONTINUITY_ID)
    events = h.store.events(h.run_id)
    requests = []
    for event in events:
        if event['kind'] == 'r3_request':
            meta = h.store.artifact(event['outputs'][0])
            wire = h.store.artifact(meta['request'])
            packet = next(json.loads(message['content'].split('CURRENT_RESEARCH_PACKET\n', 1)[1])
                for message in wire['messages'] if isinstance(message.get('content'), str)
                and message['content'].startswith('CURRENT_RESEARCH_PACKET\n'))
            requests.append(dict(request_id=event['request_id'], reference=meta['request'],
                bytes=meta['input_bytes'], messages=len(wire['messages']), research=packet['research'],
                evidence_schema=next(t['function']['parameters'] for t in wire['tools']
                                     if t['function']['name'] == 'evidence_read')))
    assert len(requests) == 2
    delivery = requests[1]['research']['pending_feedback_delivery']['items']
    assert len(delivery) == 1
    item = delivery[0]
    assert item['result'] == h.store.artifact(item['feedback_reference'])['result']
    uses = [h.store.artifact(e['outputs'][0])['tool_use'] for e in events
            if e['kind'] == 'model_original_tool_request']
    assert len(uses) == 1 and uses[0]['name'] == 'evidence_read'
    assert uses[0]['toolUseId'] == item['tool_id']
    coverage = read_coverage(h)
    assert len(coverage) == 1 and coverage[0]['successfully_provided'] and coverage[0]['complete_data']
    restores = [h.store.artifact(e['outputs'][0]) for e in events if e['kind'] == 'sdk_restore_verified']
    assert restores and not pending(h) and not state(h)['pilot'].get('unconsumed_response')
    assert any(e['kind'] == 'session_handoff' and e['status'] == 'committed' for e in events)
    from tools.research.session_handoff import pending_feedback_delivery
    assert pending_feedback_delivery(h) is None
    old = read(ROOT / 'evidence/c3_f1_f2/continuity_summary.json')
    assert uses[0]['input'] == old['tool_queries'][0]['input']
    permitted = requests[1]['evidence_schema']['$defs']['EvidenceRef']['properties']['artifact_id'].get('enum')
    source_permitted = permitted is None or uses[0]['input']['reference']['artifact_id'] in permitted
    result = dict(status='passed' if source_permitted else 'feedback_passed_startup_scope_confounded',
        original_query_permitted_after_handoff=source_permitted,
        post_handoff_allowed_evidence_ids=permitted, usage=provider_usage(h),
        requests=[{k:r[k] for k in ('request_id', 'reference', 'bytes', 'messages')} for r in requests],
        handoff_feedback=dict(tool_id=item['tool_id'], feedback_reference=item['feedback_reference'],
                              query=item['query'], exact_original_feedback=True),
        post_handoff_read_state=requests[1]['research']['evidence_working_set']['read_state'],
        final_read_coverage=coverage, restore_only=restores,
        prior_f1_query_identical=True, further_pending_delivery=False,
        post_handoff_action_trace=requests[1]['research']['action_trace'],
        trace_scope='No Plan precedes this continuity read; archived A/B regression checks existing decision traces.')
    atomic_json(OUT / 'continuity_review.json', result)
    return result


def finalize_g1():
    """Audit original decisions and seal the failed scientific gate without new sends."""
    from tests.research import agent_math_decision_probe as probe
    from tools.research.agent import pending, received, record
    from tools.research.budget import engineering_closeout
    continuity = audit_continuity()
    frozen = read(PROBE / 'frozen.json')
    summary = read(OUT / 'decision_summary.json')
    h = host(DECISION_ID)
    originals = {event['request_id']: h.store.artifact(h.store.artifact(event['outputs'][0])['request'])
                 for event in h.store.events(h.run_id) if event['kind'] == 'r3_request'}
    assert len(originals) == 4 and all(row['schema_check'] == 'passed' for row in summary['results'])
    calls = []
    for row in summary['results']:
        wire = originals[row['request_id']]
        saved = read(PROBE / f"c3_next_decision-{row['arm']}-{row['turn']}-response.json")
        assert probe.parse(saved['choices'][0]['message']) == row['plan']
        call = saved['choices'][0]['message']['tool_calls'][0]
        calls.append(call['id'])
        packet = json.loads(wire['messages'][-1]['content'])
        assert packet['evaluation_turn']['turn'] == row['turn']
        assert wire['tool_choice'] == 'auto' and wire['messages'][0]['content'] == frozen['instructions']
        if row['turn'] == 2:
            previous = read(PROBE / f"c3_next_decision-{row['arm']}-1-response.json")['choices'][0]['message']
            assert previous in wire['messages']
            assert packet['evaluation_turn']['previous_plan_tool_ids'] == [previous['tool_calls'][0]['id']]
            assert packet['new_observations'] == frozen['cases']['cases']['c3_next_decision']['round2']
        else:
            assert 'new_observations' not in packet
        for key in ('model', 'max_tokens', 'reasoning_effort', 'thinking', 'stream'):
            assert wire[key] == read(PROBE / f"c3_next_decision-{row['arm']}-{row['turn']}-input.json")[key]
    assert len(set(calls)) == 4
    assert not pending(h) and not state(h)['pilot'].get('unconsumed_response')
    review = dict(g1='failed_scientific_revision_gate', g2='not_started_required_by_user_stop_condition',
        gates=dict(exact_feedback_delivery='passed', study_scoped_startup='passed' if
                   continuity['original_query_permitted_after_handoff'] else 'inconclusive_original_query_filtered_by_closeout',
                   new_plan_each_turn='passed_4_of_4', evidence_based_valid_scientific_revision='failed'),
        rubric_source='decision_protocol.json#/rubric_offline_only',
        manual_scores=[
            dict(arm='baseline', turn=1, evidence_scope=1, testable_hypothesis=2,
                 discriminating_action=1, feedback_revision=None, complete_cost=1),
            dict(arm='evidence', turn=1, evidence_scope=0, testable_hypothesis=2,
                 discriminating_action=0, feedback_revision=None, complete_cost=1),
            dict(arm='baseline', turn=2, evidence_scope=1, testable_hypothesis=2,
                 discriminating_action=1, feedback_revision=1, complete_cost=1),
            dict(arm='evidence', turn=2, evidence_scope=0, testable_hypothesis=2,
                 discriminating_action=0, feedback_revision=1, complete_cost=1)],
        scoring_scope='Human review against frozen anchors; explicit competing hypotheses score separately from invalid causal branches. No response-length score or statistical inference.',
        independent_direction_support='unscored_no_experiment_executed',
        scientific_failures=[
            dict(rows=['evidence:1', 'evidence:2'], fields=['hypothesis', 'interpretation'],
                 issue='Compares CONIC witness with different-control NMPC as speed-channel magnitude/phase error despite partial_comparison and missing aligned samples.'),
            dict(rows=['baseline:2', 'evidence:2'], fields=['hypothesis', 'interpretation'],
                 issue='Two speed norms do not establish monotone decay, exponential dynamics, noise exclusion or threshold crossings; evidence:2 invents an ascending crossing at 0.24 s.'),
            dict(rows=['baseline:1', 'evidence:1', 'evidence:2'], fields=['expected_observation', 'weakening_observation'],
                 issue='Instantaneous braking compared with average required deceleration is not a finite-horizon necessary condition without a validated horizon-wide bound.'),
            dict(rows=['evidence:2'], fields=['expected_observation', 'fixed_conditions'],
                 issue='Confuses update 30 at 0.30 s with the speed peak at 0.31 s; proposes 0.40 s extension outside the frozen 0.35 s protocol.'),
            dict(rows=['baseline:1', 'baseline:2', 'evidence:1', 'evidence:2'], fields=['fixed_conditions', 'expected_observation'],
                 issue='Costs omit preparation/prefixes/internal steps or extra timestep reruns; A2 calls a timestep rerun a free recorded read.')],
        usage=dict(continuity=continuity['usage'], decisions=probe.provider_usage(h)),
        scientific_execution=dict(mathematical_evaluations=0, independent_physics=0, nmpc=0, ppo=0,
                                  reporter_requests=0, mathematical_conclusion='not_computed',
                                  physical_task_acceptance='not_measured'),
        provider_wall_s={name: sum(received(host(name), event['request_id'])['elapsed_s']
            for event in host(name).store.events(name) if event['kind'] == 'r3_request')
            for name in (CONTINUITY_ID, DECISION_ID)})
    for name in (CONTINUITY_ID, DECISION_ID):
        current = host(name)
        previous = next((e['outputs'][0] for e in reversed(current.store.events(name))
                         if e['kind'] == 'bounded_validation_outcome'), None)
        record(current, 'bounded_validation_outcome', dict(review, supersedes=previous))
        engineering_closeout(current, 'G1 scientific revision gate failed; request allocation exhausted; user requires no G2 or repair requests.')
        core.export(current)
    atomic_json(OUT / 'review.json', review)
    return review


def inspect_historical_state():
    """Read the existing native-source interface; do not integrate or bind a new owner."""
    from tools.research.contracts import AnalysisRequest
    from tools.research.numerics import native_point
    old = prior.historical_host()
    s = state(old)
    execution = s['results'][-1]
    result = old.store.artifact(execution)
    candidate = old.store.artifact(result['candidate'])
    query = AnalysisRequest(candidate=result['candidate'], operation='native_dynamics_v1',
        model_source='mujoco', operating_point='saved_state', execution=execution,
        update_id=30, protocol=s['spec']['analysis_protocol'])
    point = native_point(old, query, candidate['configuration'])
    value = dict(owning_study=old.run_id, original_status=s['research_status'], execution=execution,
        candidate=result['candidate'], update_id=30, actual_time_s=point['actual_time_s'],
        phase=point['phase'], native_qpos_dimension=len(point['qpos_rad']),
        native_qvel_dimension=len(point['qvel_rad_s']), tendon_order=point['tendon_order'],
        native_integration_checkpoint_in_selected_source=bool(point.get('integration_state')),
        saved_native_kinematic_data=True, measured_prefix_intervals=len(point['native_replay']['rows']),
        input_n=point['u'], source=point['provenance'],
        prefix_verification='Available source only; reconstruction/checks belong to a charged Worker and were not executed.',
        current_study_candidate_binding='not_attempted_G2_not_started',
        projected_GVS_state_substituted=False, mathematics=0, native_integration_steps=0)
    atomic_json(OUT / 'historical_state_qualification.json', value)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare-g1', 'continuity', 'restore', 'probe-live', 'audit-continuity', 'finalize-g1', 'inspect-state', 'prepare-g2', 'live-g2', 'restore-g2'])
    args = parser.parse_args()
    if args.mode in ('continuity', 'restore', 'probe-live'):
        load_credential(Path('~/.codex/.env').expanduser())
    if args.mode == 'prepare-g2':
        result = prepare_g2()
    elif args.mode in ('live-g2','restore-g2'):
        result = live_g2(args.mode=='restore-g2')
    elif args.mode == 'prepare-g1':
        result = prepare_g1()
    elif args.mode == 'audit-continuity':
        result = audit_continuity()
    elif args.mode == 'finalize-g1':
        result = finalize_g1()
    elif args.mode == 'inspect-state':
        result = inspect_historical_state()
    elif args.mode in ('continuity', 'restore'):
        result = prior.continuity(args.mode == 'restore', study_id=CONTINUITY_ID,
            destination=OUT / 'continuity', provider_requests=2, source=SOURCE, authorization=AUTH)
    else:
        h = host(DECISION_ID)
        try:
            result = prior.decision_probe(True, out=PROBE, destination=OUT, authorization=AUTH, formal_host=h)
        finally:
            core.export(h)
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
