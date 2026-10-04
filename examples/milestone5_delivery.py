"""Evidence-only delivery from the same stage's saved forecasts and receipts."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from examples import milestone5_validation as stage
from tools.state_io import read,atomic_json
from tools.study_history import study_history


def deliver():
    w=stage.restore();stage.assert_predecessor(w)
    outcome=read(stage.RUN/'outcome.json');batch=read(stage.RUN/'validation_batch_result.json')
    forecast=read(stage.RUN/'forecast_seal.json');assessment=read(stage.RUN/'prediction_assessment.json')
    final=w.store.artifact(w.chain['final_response']);review=read(stage.RUN/'final_semantic_acceptance.json')
    if outcome['status']!='completed' or not review['passed'] or review['final_response']!=w.chain['final_response']:raise ValueError('FINAL_INTERPRETATION_NOT_ACCEPTED')
    if batch['fully_evaluated_distinct_changed_configurations']!=len(forecast['forecasts']):raise ValueError('CANDIDATE_EVALUATION_INCOMPLETE')
    if w.store.artifact(w.chain['forecast_seal'])!=forecast or not assessment['forecast_chronology']['passed']:raise ValueError('FORECAST_SEAL_OR_CHRONOLOGY_CHANGED')
    if final['next_action']!='finish' or final['next_research']['route']!='stop' or any(final['next_research']['proposed_budget'].values()):raise ValueError('FINAL_NEXT_ACTION_NOT_CLOSED')
    accounting=read(stage.EVIDENCE/'accounting.json');numerical=read(stage.RUN/'prediction_numerical.json')
    selected=next((r['facts']['candidate'] for r in w.historical_results if r['facts']['candidate']==final['selected_candidate']),final['selected_candidate'])
    limits=accounting['stage_limits']
    if accounting['occupied'] or any(accounting['new'][k]>limits[k]+1e-8 for k in limits):raise ValueError('DELIVERY_CAPACITY_EXCEEDED_OR_OCCUPIED')
    delivery=dict(status='completed',requested_stage_completed=True,milestone4_closed=True,milestone5_complete=False,
        milestone5_gates=dict(local_direction='Scoped prospective observations completed; repeatability/general reliability remain undemonstrated.',
            local_numerical_fidelity='Assessed at frozen tolerance; see exact errors and within-tolerance count.',
            full_task_discrimination='Four direction opportunities and one secondary speed ordering scored without changing forecasts.',
            joint_acceptance_prediction='Abstained; actual complete evaluations retained.',
            screening_reliability=False,automatic_rejection_authorized=False,real_time_demonstrated=False),
        identities=dict(primary_reference=w.incumbent['candidate'],milestone4_selected_deliverable=w.incumbent['candidate'],
            retained_baseline=w.retained_baseline['candidate'],latest_tested=w.latest_tested,stage_final_selection=selected),
        development_data=stage.DEVELOPMENT,prospective_validation_data=[dict(candidate_id=r['candidate_id'],execution_id=r['execution_id'],
            configuration=r['forecast']['configuration']) for r in assessment['outcomes']],
        forecasts=forecast['forecasts'],full_outcomes=assessment['outcomes'],local_fidelity=assessment['local_fidelity'],
        direction_counts=assessment['direction_counts'],resolved_coverage=assessment['resolved_coverage'],
        accuracy_among_resolved=assessment['accuracy_among_resolved'],local_direction_counts=assessment['local_direction_counts'],
        local_endpoint_within_tolerance=assessment['local_endpoint_within_tolerance'],
        predicted_speed_order=assessment['speed_order_forecast'],observed_speed_order=assessment['observed_speed_order_detail'],
        ordering_verdict=assessment['ordering_verdict'],joint_acceptance_prediction='unresolved',
        accepted_research_model_role=review['accepted_role'],accepted_model_next_action=review['accepted_next_action'],
        final_model_response=w.chain['final_response'],final_model_reasoning=final['reasoning'],semantic_acceptance=review,
        forecast_chronology=assessment['forecast_chronology'],tolerances=forecast['tolerances'],rules_unchanged=True,
        accounting=accounting,numerical_preview_cost_s=assessment['predictor_cost_s'],full_evaluation_cost_s=assessment['full_evaluation_cost_s'],
        additional_local_solves=accounting['numerical_work']['used']['local_solves'],additional_prediction_rollouts=accounting['numerical_work']['used']['prediction_evaluations'],
        embedded_controller_updates=sum(r['metrics']['control_updates'] for r in assessment['outcomes']),embedded_work_separately_identified=True,
        preview_selections=[{k:r[k] for k in ('candidate_id','update_id','selected_iteration','stop_reason','holding_plan_max_speed_m_s','holding_plan_max_error_m')} for r in numerical['rows']],
        original_milestone4_and_pilot_preserved=True,external_authorization=stage.EXTERNAL_AUTHORIZATION,
        prior_automatic_rejection_preserved='delivery_before_resume.json',handoff_versions=read(stage.RUN/'handoff_versions.json'),
        engineering_interventions=w.freeze.get('resume_interventions',[]),resume_focused_checks=4,
        no_historical_replay=True,no_workers=True,no_subagents=True,pushed=False,revision=stage.revision())
    atomic_json(stage.EVIDENCE/'delivery.json',delivery)
    atomic_json(stage.EVIDENCE/'history_final.json',study_history(w.store,w.historical_results,retained_baseline=w.retained_baseline['candidate'],
        selected_source=w.incumbent['candidate'],latest_tested=w.latest_tested,selection=selected))
    for path in [*stage.FILES,'examples/milestone5_delivery.py']:
        target=stage.EVIDENCE/'implementation'/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/path).read_bytes())
    for path in ROOT.joinpath('runs').glob('milestone5_resume*_console.log'):shutil.copyfile(path,stage.EVIDENCE/'single_context'/path.name)
    atomic_json(stage.EVIDENCE/'sha256_manifest.json',{p.relative_to(stage.EVIDENCE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(stage.EVIDENCE.rglob('*')) if p.is_file() and p.name!='sha256_manifest.json'})
    print(json.dumps(dict(status='completed',role=delivery['accepted_research_model_role'],counts=delivery['direction_counts'],
        local_counts=delivery['local_direction_counts'],ordering=delivery['ordering_verdict'],usage=accounting),indent=2))


if __name__=='__main__':deliver()
