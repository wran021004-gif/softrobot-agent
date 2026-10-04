"""Source checks and human-reviewed interpretation disposition; no model or solve."""
from pathlib import Path
import sys
import hashlib
import json
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from examples import stage358_interpretation_repair as cycle
from tools.state_io import read, atomic_json
from tools.platform_store import plain
from tools.diagnostic_workflow import save

directory=Path(__file__).parent
packet=read(directory/'decision_packet.json')
response=read(directory/'final_response.json')
result=read(directory/'cycle_result.json')
rows={r['role']:r for r in packet['configurations']}
comparisons={(r['candidate'],r['reference']):r for r in packet['comparisons']}
assert [r['initialization_selections'] for r in packet['diagnostics']]==[30,17]
assert [r['positive_iteration_selections'] for r in packet['diagnostics']]==[5,18]
assert response['selected_candidate']==rows['retained_baseline']['candidate']
assert response['candidate_disposition']=='retain_baseline' and response['disposition']=='defer'
assert round(comparisons['holding_only','retained_baseline']['candidate_minus_reference']['mean_complete_update_s'],4)==.1298
assert round(comparisons['holding_only','older_search_start']['candidate_minus_reference']['mean_complete_update_s'],4)==-.3857
assert round(comparisons['immediate_predecessor','retained_baseline']['candidate_minus_reference']['holding_max_speed_m_s'],3)==-1.545
assert round(rows['immediate_predecessor']['metrics']['terminal_error_m'],4)==.0082
assert not rows['immediate_predecessor']['metrics']['holding_speed_passed']
assert set(response['next_research']['proposed_variables'])=={'control/recipe/terminal_tip_speed_weight'}
assert all(result['cycle_usage'][k]<=v for k,v in cycle.CAPS.items())
review=dict(passed=True, review_kind='Program source checks plus direct human-agent review; no judge model',
    response=result['response'], packet=result['packet'], supersedes=packet['previous_failed_revision'],
    previous_audit=packet['previous_audit'], source_batch_summary=packet['source_batch_summary'],
    criteria=dict(correct_initialization_and_positive_counts=True, named_differences_accurate=True,
        concise_numeric_rounding_accurate=True,joint_positive_untested=True,
        movement_distinct_from_acceptance=True, independent_recommendation_and_candidate_dispositions=True,
        one_route_explicit_varied_and_fixed_weights=True, no_horizon_only_causal_switch=True,
        position_prediction_does_not_certify_speed=True, no_range_or_global_claim=True,
        nonessential_omissions_not_failures=True, original_caps_preserved=True),
    model_decision=dict(candidate='retain_baseline',recommendation='defer',route='A',
        holding_weight=0.,proposed_terminal_weight=.10, intended_new_complete_results=1),
    operational_preconditions=[
        'This advisory decision is not an executable plan. A new immutable model-authored plan is mandatory.',
        'The 1200 s proposed check allocation is not sufficient as an all-workflow limit with the 990 s execution reservations and 600 s interpretation reserve. It fits the 4200 s grant only as a partial allocation; do not launch under a total 1200 s cap.',
        'Saved-state execution wording confers no local solve or initialization change. The new plan must require a complete backend run using the fixed Task initializer and warm-start policy.',
        'The exact 0.10 point needs an explicit finite proposal implementation; prose and an unspecified coordinate step are not an executable generator.',
        'No early in-run reach test is implemented. Stop after a complete evaluation/profile, or on material failure; reconcile stopping prose in the new plan.'],
    gate_scope='Accurate interpretation and advisory research direction. Future operational plan is separately validated before launch.',
    engineering_delivery_defect=packet['correction_categories']['delivery_defect'],
    physical_joint_acceptance_required_for_workflow_closure=False,
    stage359_plan_authoring_permitted=True, stage359_backend_launch_permitted=False,
    cycle_usage=result['cycle_usage'], provider_reported_tokens=17653,
    historical_unknown_reservation_s=900., old_evidence_overwritten=False)
atomic_json(directory/'semantic_review.json',review)
parent=cycle.parent_host()
ref=save(parent.store,review)
with parent.store.transaction() as db:
    parent.store.event(db,parent.run_id,'superseding_interpretation','accepted',
        inputs=[result['response'],result['packet'],packet['previous_failed_revision']],outputs=[ref])
atomic_json(cycle.prior.RUN/'superseding_interpretation.json',dict(response=result['response'],review=ref,passed=True))
result.update(status='interpretation_accepted_executable_next_plan_required',semantic_gate_passed=True,semantic_review=ref)
atomic_json(directory/'cycle_result.json',result)
gate_path=cycle.prior.EVIDENCE/'milestone3_acceptance.json'
(directory/'milestone3_acceptance_before_v2.json').write_bytes(gate_path.read_bytes())
gate=read(gate_path)
gate.update(passed=True,status='execution_and_interpretation_complete',unmet_criteria=[],
    superseding_interpretation=result['response'],superseding_review=ref,
    superseding_review_file=str(directory/'semantic_review.json'),previous_gate=str(directory/'milestone3_acceptance_before_v2.json'))
gate['criteria']['accurate_model_interpretation_and_final_decision']=True
atomic_json(gate_path,gate)
atomic_json(directory/'sha256_manifest.json',{p.relative_to(directory).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
    for p in directory.rglob('*') if p.is_file() and p.name!='sha256_manifest.json'})
print('Milestone 3 interpretation accepted; future executable plan remains mandatory.')
