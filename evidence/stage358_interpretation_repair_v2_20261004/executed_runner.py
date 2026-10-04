"""New compact interpretation cycle in the unchanged Stage 3.58 project ledger."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from examples import stage358_confirmation as prior
from tools.platform_store import Store, plain, zero, encode
from tools.platform_host import Host
from tools.diagnostic_workflow import save, implementation
from tools.platform_diagnosis_coordinator import run_until_handoff, transfer_recovery
from tools.platform_models import payload_for
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from tools.settling_campaign import campaign_metrics, compare_results
from tools.state_io import read, atomic_json

EVIDENCE = ROOT / 'evidence/stage358_interpretation_repair_v2_20261004'
CYCLE = 'interpretation-repair-v2'
CAPS = dict(model_calls=3, tool_calls=4, wall_s=600., backend_solves=0, worker_calls=0)
INSTRUCTIONS = '''Use decision_packet as the numerical authority. Submit one concise final decision, about 350 words total across its prose fields; cite named fact rows instead of copying all numbers. State which hypothesis clauses are supported, weakened or untested; distinguish moving toward the speed threshold from meeting it. Make recommendation disposition and candidate disposition independently. Select exactly one proposed next continuation route: A varies terminal_tip_speed_weight with holding_tip_speed_weight fixed at zero; B varies holding_tip_speed_weight with terminal_tip_speed_weight fixed at 0.05. Both start at the completed 0/0.05 predecessor; the retained baseline remains 0/0. A justified one-point check is acceptable. Specify proposed_variables with exactly the one varied full builder path and explicit values or coordinate domain/start/step; put the unvaried weight among fixed_conditions. Give one question, a bounded check, evidence, expected supporting/weakening observations, budget and stopping conditions. Proposed budget fits the separate 8-model/20-tool/4200-second/2-backend/zero-worker grant, at most four proposals including starts/duplicates, and reserves at least 600 seconds for interpretation. A proposal is not an execution plan or a launch.
Correct the previous material errors: holding-only has 30 initialization and 5 positive-iteration selections; terminal-only has 17 and 18. Every stated delta must name its correct reference. No joint-positive-weight configuration was tested. Empty proposed variables are a missing decision-critical field. Late-horizon shortening alone establishes no cause and is not a reason to switch direction; a fixed task endpoint naturally shortens remaining horizon. Small one-step position error does not certify holding-speed prediction or exclude relevant mismatch. Read-only associations do not separate causal mechanisms. A few values neither establish a continuous range nor exhaust a coordinate. No real-time, causal, global or hardware claim. Omission of unrelated historical details is acceptable; any number or comparison you state must agree with the packet. Retain prior failures by reference; the missing supplement was an engineering delivery defect, not model refusal. No numerical work, new backend or new evidence query. Use next_action=finish and one advertised design.respond_diagnosis call. No long report.'''


def parent_host():
    store = Store(prior.RUN)
    with store.connect(True) as db:
        run_id = next(r['run_id'] for r in db.execute('SELECT run_id,state FROM sessions')
                      if json.loads(r['state']).get('role_context', {}).get('require_research_route'))
    return Host(prior.RUN, run_id)


def decision_packet():
    """Arithmetic from previously verified complete records, with exact sources."""
    store = Store(prior.RUN)
    chain = read(prior.RUN / 'chain.json')
    summary = store.artifact(chain['batch_summary'])
    history = read(ROOT / 'evidence/stage359_continuation_20261004/offline_references.json')['complete_historical_records']
    rows = []
    roles = ['retained_baseline', 'older_search_start', 'prior_candidate', 'holding_only', 'immediate_predecessor']
    for role, record in zip(roles, history):
        facts = record['facts']
        source_store = Store(record['source_store'])
        # Exact sealed result binding, rather than a retyped metric table.
        from extensions.tendon_family.delivery_facts import bound_result_facts
        binding = dict(reference=record['receipts']['profile']['output'], owner_run_id=record['owner_run_id'],
                       execution_id=record['execution_id'], request_id=record['receipts']['profile']['request_id'])
        actual = bound_result_facts(source_store, dict(profile_report=binding,
            evaluation=record['receipts']['evaluation']['output'], simulation=record['receipts']['simulation']), facts['candidate'])
        if actual != facts:
            raise ValueError('DECISION_PACKET_SEALED_FACTS_CHANGED')
        recipe = source_store.artifact(facts['configuration'])['effective']['policy']['controller']['parameters']['data']['recipe']
        rows.append(dict(role=role, candidate=facts['candidate'],
                         weights=dict(holding=recipe['holding_tip_speed_weight'], terminal=recipe['terminal_tip_speed_weight']),
                         metrics=campaign_metrics(facts)))
    comparisons = []
    for i, record in enumerate(history):
        for j in (0, 4, 1):
            comp = compare_results(history[j]['facts'], record['facts'])
            comparisons.append(dict(candidate=roles[i], reference=roles[j],
                candidate_execution_id=record['execution_id'], reference_execution_id=history[j]['execution_id'],
                candidate_minus_reference=comp['candidate_minus_baseline'], classification=comp['classification']))
    diagnostics = []
    for row in summary['current_update_facts']:
        counts = row['selected_iterations']
        zero_count = counts.get('iteration_zero', {}).get('count', 0)
        synthetic = counts.get('synthetic_initialization', {}).get('count', 0)
        facts = next(r['facts'] for r in history if r['execution_id'] == row['execution_id'])
        tension = max(facts['applied_tension_ranges'], key=lambda x: x['maximum_n'])
        diagnostics.append(dict(execution_id=row['execution_id'], source=chain['batch_summary'],
            source_pointer='/current_update_facts', initialization_selections=zero_count+synthetic,
            synthetic_initialization=synthetic, positive_iteration_selections=counts['positive_iteration']['count'],
            maximum_applied_tension_n=tension['maximum_n'], maximum_tendon=tension['tendon'],
            minimum_upper_margin_n=tension['limit_n']-tension['maximum_n'],
            one_step_position_prediction=facts['one_step_prediction_summary']))
    old = read(prior.EVIDENCE / 'correction_semantic_review.json')
    categories = dict(
        material_contradictions=[old['review'][0], old['review'][3]],
        missing_decision_critical_fields=[old['review'][7]],
        nonessential_not_repeated=['Terminal tension/margin unless used to justify the decision',
            'Archived dual/single queried update lists unless discussed',
            'Self-comparison and remaining prior-budget numbers unless discussed'],
        decision_critical_qualification='Any stated historical number, reference or claim still must be accurate.',
        delivery_defect=old['delivery_defect'])
    return dict(contract='stage358.compact_decision_packet', version='1.0.0',
        source_batch_summary=chain['batch_summary'], source_plan=chain['search_plan'],
        hypothesis=store.artifact(chain['search_plan'])['plan']['hypothesis'],
        original_response=read(prior.EVIDENCE / 'factual_correction_result.json')['original'],
        previous_failed_revision=chain['final_response'], previous_audit=str(prior.EVIDENCE / 'correction_semantic_review.json'),
        configurations=rows, comparisons=comparisons, diagnostics=diagnostics,
        acceptance=dict(terminal_error_m=.01, holding_max_error_m=.01, holding_max_speed_m_s=.02, window_s=.05),
        correction_categories=categories, joint_positive_weight_tested=False,
        recommendations=[{k:r[k] for k in ('recommendation_id','action','rationale')}
                         for r in store.artifact(parent_host().store.session(parent_host().run_id)['state']['role_context']['report'])['recommendations']],
        current_scope=dict(routes=dict(A=dict(varied='control/recipe/terminal_tip_speed_weight', fixed_holding=0.),
                                      B=dict(varied='control/recipe/holding_tip_speed_weight', fixed_terminal=.05)),
                           start_execution_id=history[4]['execution_id'], baseline_execution_id=history[0]['execution_id'],
                           grant=dict(model_calls=8,tool_calls=20,backend_solves=2,worker_calls=0,wall_s=4200.),
                           proposal_cap=4, intended_new_results='Model chooses one or two; no forced second execution',
                           permitted_bounds=[0.,1.], legal_positive_minimum=.0001),
        facts_are_program_generated=True, judgment_is_model_authored=True,
        prior_costs=store.remaining(), correction_cycle_caps=CAPS,
        unresolved_historical_reservation_s=900., raw_evidence='Available in original stores by the linked artifact references; not duplicated in this packet.')


def create_bounded_child(parent, packet, packet_ref, cycle=CYCLE):
    """Sequential same-ledger child; project/parent usage includes its calls."""
    before = parent.store.remaining()
    old_phase = parent.store.phase_remaining(parent.run_id)
    available = parent.store.spendable(parent.run_id)['remaining']
    limits = {k:min(v, available[k]) for k,v in CAPS.items()}
    if limits['model_calls'] < 1 or limits['tool_calls'] < 1 or limits['wall_s'] < 30:
        raise ValueError('INTERPRETATION_CYCLE_CAPACITY_UNAVAILABLE')
    old = parent.store.session(parent.run_id)
    inp = deepcopy(old['snapshot']['input'])
    inp['run_id'] = parent.run_id + '-' + cycle
    inp['policy'].update(budget=limits, route=None, search=None, allowed_tools=[],
                         tool_bindings={'design.respond_diagnosis':'3.0.0'})
    child = Host(parent.store.root, inp['run_id'])
    child.create(inp, parent_run_id=parent.run_id)
    role = deepcopy(old['state']['role_context'])
    role.update(role='design', phase='response_final', instructions=INSTRUCTIONS,
                phase_tools=['design.respond_diagnosis'], native_fixed={'design.respond_diagnosis':
                    dict(report=role['report'])}, memory_identity=child.run_id, native_store_root=str(parent.store.root),
                decision_packet=packet, decision_packet_reference=packet_ref,
                phase_budget=dict(limit=limits, started_usage=zero()), working_memory=[],
                original_phase_budget=old['state']['role_context']['phase_budget'])
    with child.store.transaction() as db:
        state=child.store.session(child.run_id,db)['state']
        state.update(role_context=role, fact_scope=old['state'].get('fact_scope',{}),
                     fact_catalog={}, read_ledger=[], workflow_memory=[])
        child.store.update_state(db,child.run_id,state)
        child.store.event(db,child.run_id,'authorized_interpretation_cycle','bound',inputs=[packet_ref],
                          outputs=[child.store.put(db,dict(cycle=cycle,parent_run_id=parent.run_id,
                              original_phase=old_phase,project_before=before,limits=limits))])
    transfer_recovery(parent,child)
    return child


def check_payload(payload, packet):
    content=json.loads(payload['messages'][1]['content'])
    view=content['role_context']
    if view['decision_packet'] != packet:
        raise ValueError('COMPACT_PACKET_BINDING_CHANGED')
    phrases=['30 initialization and 5 positive', '17 and 18', 'Late-horizon shortening alone',
             'Small one-step position error', 'Read-only associations', 'continuous range',
             'one varied full builder path', 'engineering delivery defect']
    if not all(p in view['instructions'] for p in phrases):
        raise ValueError('REQUIRED_CORRECTION_INSTRUCTION_NOT_DELIVERED')
    size=len(encode(payload).encode())
    if size > 40000 or any(k in view for k in ('reference_view','fact_catalog','report_content','batch_result')):
        raise ValueError('COMPACT_DECISION_PAYLOAD_TOO_LARGE_OR_DUPLICATED')
    return dict(passed=True,payload_bytes=size,required_instructions=phrases,
                packet_sources=[r['metrics']['source'] for r in packet['configurations']],
                max_tokens=payload['max_tokens'], facts_present=True, catalog_omitted=True)


def live():
    guard=prior.RUN / (CYCLE+'_attempt.json')
    if guard.exists():
        raise ValueError('NEW_INTERPRETATION_CYCLE_ALREADY_RECORDED')
    parent=parent_host(); packet=decision_packet()
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    before=parent.store.remaining(); phase=parent.store.session(parent.run_id)['state']['role_context']['phase_budget']
    packet_ref=save(parent.store,packet)
    child=create_bounded_child(parent,packet,packet_ref)
    payload=payload_for(child,EvidenceDrivenAdapter()); checked=check_payload(payload,packet)
    atomic_json(EVIDENCE/'decision_packet.json',packet)
    atomic_json(EVIDENCE/'correction_categories.json',packet['correction_categories'])
    atomic_json(EVIDENCE/'provider_payload_offline.json',payload)
    atomic_json(EVIDENCE/'payload_check.json',checked)
    atomic_json(guard,dict(cycle=CYCLE,child_run_id=child.run_id,packet=packet_ref,
        original_phase_preserved=phase,used_before=before['used'],caps=CAPS,implementation=implementation(),
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    (EVIDENCE/'executed_runner.py').write_bytes(Path(__file__).read_bytes())
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path.home()/'.codex/.env')
    for name in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
        if '127.0.0.1:9' in os.environ.get(name,''):os.environ.pop(name)
    started=time.monotonic(); result=None;error=None
    try:
        result=run_until_handoff(child,'design_response')
        atomic_json(EVIDENCE/'final_response.json',child.store.artifact(result))
    except Exception as exc:
        error=str(exc)
    finally:
        transfer_recovery(child,parent)
    assert parent.store.session(parent.run_id)['state']['role_context']['phase_budget']==phase
    after=parent.store.remaining()
    events=child.store.events(child.run_id)
    raw=[child.store.artifact(e['outputs'][0]) for e in events if e['kind']=='model_raw_response']
    record=dict(cycle=CYCLE,status='response_received_semantic_review_pending' if result else 'failed',
        response=result,error=error,packet=packet_ref,used_before=before['used'],used_after=after['used'],
        cycle_usage={k:after['used'][k]-before['used'][k] for k in zero()},
        provider_usage=[r['raw']['usage'] for r in raw if r.get('raw',{}).get('usage')],
        original_phase_budget_preserved=phase,original_phase_after=parent.store.phase_remaining(parent.run_id),
        elapsed_s=time.monotonic()-started,semantic_gate_passed=False)
    atomic_json(EVIDENCE/'cycle_result.json',record)
    from tools.improvement_workflow import archive_store
    archive_store(parent.store,EVIDENCE/'ledger',source_stores=[prior.prior.CONFIRM,*[x[1] for x in prior.SOURCES]])
    atomic_json(EVIDENCE/'ledger_usage.json',after)
    atomic_json(EVIDENCE/'sha256_manifest.json',{p.relative_to(EVIDENCE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in EVIDENCE.rglob('*') if p.is_file() and p.name!='sha256_manifest.json'})
    print('INTERPRETATION CYCLE',record['status'],'USAGE',record['cycle_usage'],flush=True)


if __name__=='__main__':
    live()
