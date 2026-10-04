"""Source-bound review/export of the completed continuation; no new execution."""
from pathlib import Path
import hashlib
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from examples import stage359_live_continuation as live
from tools.state_io import read,atomic_json
from tools.platform_store import Store
from tools.diagnostic_workflow import implementation

directory=Path(__file__).parent
run=live.RUN
packet=read(run/'decision_packet.json')
response=read(run/'final_response.json')
batch=read(run/'batch_result.json')
outcome=read(run/'outcome.json')
row=packet['completed_results'][0]
metrics=row['metrics'];delta=row['against_immediate_predecessor']['candidate_minus_baseline']
baseline_delta=row['against_retained_baseline']['candidate_minus_baseline']
assert round(metrics['terminal_error_m'],5)==.00812
assert round(metrics['holding_max_error_m'],5)==.00833
assert round(metrics['holding_max_speed_m_s'],5)==.04868
assert round(delta['holding_max_speed_m_s'],5)==.01311
assert round(delta['holding_max_error_m'],7)==.0000553
assert round(delta['terminal_error_m'],7)==-.0000634
assert round(baseline_delta['holding_max_speed_m_s'],3)==-1.532
assert round(baseline_delta['holding_max_error_m'],5)==-.04981
assert round(baseline_delta['terminal_error_m'],5)==.00048
assert row['against_immediate_predecessor']['classification']=='physical_tradeoff'
assert row['against_retained_baseline']['classification']=='physical_tradeoff'
assert response['candidate_disposition']=='retain_baseline'
assert response['selected_candidate']['execution_id']==packet['retained_baseline']['source']['execution_id']
assert batch['fully_evaluated_distinct_changed_configurations']==1
assert batch['accounting']['proposals']==1 and batch['accounting']['new_backend_attempts']==1
assert batch['accounting']['reused_evaluations']==0
assert implementation()['files']==read(run/'freeze.json')['implementation']['files']
store=Store(run)
with store.connect(True) as db:
    unsealed=[dict(r) for r in db.execute('SELECT run_id,request_id,status,charged FROM calls WHERE receipt IS NULL')]
assert not unsealed
budget=response['next_research']['proposed_budget']
floor=sum(read(run/'prelaunch.json')['reservations_s'][k] for k in ('simulation','evaluation','profile'))
assert floor==990 and budget['wall_s']==900
history=read(live.repair.EVIDENCE/'decision_packet.json')['configurations']
positive=[dict(candidate=r['candidate'],weights=r['weights'],metrics=r['metrics'])
    for r in history if r['weights']['holding']>0]
assert len(positive)==3
review=dict(passed=False,execution_gate_passed=True,current_result_interpretation_passed=True,
    next_research_proposal_passed=False,milestone3_still_closed=True,milestone4_closed=False,
    model_response=read(run/'chain.json')['final_response'],source_plan=read(run/'chain.json')['search_plan'],
    source_batch_summary=read(run/'chain.json')['batch_summary'],source_packet=str(run/'decision_packet.json'),
    classification='One complete cross-batch result delivered; accurate current-result comparisons, material next-proposal issues; stop without another interpretation or execution campaign.',
    passing_criteria=dict(all_new_results_interpreted=True,both_named_comparisons_accurate=True,
        physical_metrics_and_numeric_rounding_accurate=True,reach_and_holding_separate=True,
        hypothesis_further_speed_reduction_weakened=True,baseline_identity_retained=True,
        no_causal_or_range_claim=True,no_subsequent_direction_executed=True,within_grant=True,
        current_unknown_reservations_absent=True,nonessential_omissions_not_failed=True),
    material_contradictions=[dict(pointer='/next_research/unresolved_question',
        observed='positive control/recipe/holding_tip_speed_weight (never positive-tested; joint_positive_weight_tested false)',
        expected='Holding-positive alone was tested at 0.05, 0.10 and 0.30 with terminal zero. Only the joint-positive branch is untested.',
        sources=positive,qualification='The joint flag cannot establish that holding-positive itself was never tested. If joint-only was intended, the current wording does not state that scope.'),
        dict(pointer='/next_research/proposed_budget/wall_s',observed=900.,
             execution_reservation_floor_s=floor,shortfall_before_any_interpretation_s=floor-budget['wall_s'],
             expected='>=990 s for the complete execution, plus planning/interpretation/delivery capacity. No future grant or budget transfer is authorized.')],
    missing_decision_critical_clarity=[
        dict(pointer='/next_research/proposed_variables',observed=response['next_research']['proposed_variables'],
             expected='If intending Route B from the 0/0.05 predecessor, only holding is varied; terminal 0.05 is an explicitly fixed condition. From the newly tested 0/0.10 source, both numbers would change.'),
        dict(pointer='/disposition',observed='reject with recommendation_id=null; recommendation as stated at this tested point',
             expected='Distinguish rejection of the tested hypothesis from disposition of a named diagnostic deferral. No engineer-substituted model judgment is accepted.')],
    additional_qualification=dict(pointer='/reasoning',observed='real-time behaviour remain untested',
        source=dict(deadline_misses=35,control_updates=35,mean_complete_update_s=metrics['mean_complete_update_s'],control_period_s=.01,real_time_demonstrated=False),
        expected='Complete-update timing was measured and missed every deadline. Real-time feasibility was not demonstrated; hardware behaviour was not tested.'),
    engineering_context=dict(final_payload_bytes=read(run/'response_final_payload_check.json')['payload_bytes'],
        required_instructions_delivered=True,
        packet_limit='Final compact packet supplied both comparisons and the joint-positive flag, but omitted the three earlier holding-only rows. Their references remain archived. This can contribute to loss of scope; no model-refusal attribution.',
        prior_delivery_defect_preserved=True),
    physical_outcome=dict(execution_id=metrics['source']['execution_id'],weights=dict(holding=0.,terminal=.1),
        metrics=metrics,candidate_minus_predecessor=delta,candidate_minus_retained_baseline=baseline_delta,
        classifications=dict(predecessor='physical_tradeoff',retained_baseline='physical_tradeoff'),
        selections=packet['counts'][0]),
    accounting=dict(usage=outcome['usage'],provider_reported_tokens=sum(p['total_tokens'] for p in outcome['provider_usage']),
        proposals=1,backend_attempts=1,completed_evaluations=1,completed_profiles=1,known_result_reuses=0,
        workers=0,local_solves=0,prediction_evaluations=0,protocol_recoveries=0,unsealed_current_calls=unsealed,
        historical_unknown_reservation_s=900.,numerical_check_status_in_outcome='Historical imported check only; no new numerical diagnostic was executed.'),
    stage359_live_work_closed=True,unused_capacity_authorizes_no_further_campaign=True,
    next_direction_executable_or_accepted=False,subsequent_backend_launch_permitted=False,
    review_method='Program source checks plus direct agent review; no judge model or additional provider request.')
atomic_json(directory/'continuation_semantic_review.json',review)
gate=read(directory/'continuation_acceptance.json')
(directory/'continuation_acceptance_before_review.json').write_bytes((directory/'continuation_acceptance.json').read_bytes())
gate.update(passed=False,semantic_review_pending=False,current_result_interpretation_passed=True,
    next_research_proposal_passed=False,semantic_review='continuation_semantic_review.json',milestone3_closed=True,
    milestone4_closed=False,stop_reason='complete_one_result; material_next_proposal_issues; no_additional_campaign')
atomic_json(directory/'continuation_acceptance.json',gate)
# Preserve the old offline manifest, then write a full current evidence manifest.
old_manifest=directory/'sha256_manifest.json'
(directory/'sha256_manifest_offline_preparation.json').write_bytes(old_manifest.read_bytes())
atomic_json(old_manifest,{p.relative_to(directory).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
    for p in directory.rglob('*') if p.is_file() and p!=old_manifest})
print('Execution and current-result interpretation passed; next proposal failed review; no further live work.')
