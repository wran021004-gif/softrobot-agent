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


def correct_final():
    """Request a paid semantic repair using completed evidence, without execution."""
    import time
    w=stage.restore();stage.assert_predecessor(w)
    attempt=w.freeze.get('semantic_corrections',0)+1
    if attempt>2:raise ValueError('SEMANTIC_REPAIR_ALLOWANCE_EXHAUSTED')
    original=w.chain['final_response']
    issues=[
        'Separate six historical development intervals (retrospective,6/6 signs,0/6 numerical passes) from FOUR new production one-step predictions sealed prospectively before backend advancement (4/4 signs,0/4 endpoint passes). Prospective chronology is verified; this is scoped evidence, not general reliability.',
        'The frozen direction and pairwise mapping uses the .30 s cold holding-entry plans: all maxima are .01991554683358343 m/s, tie. The .0046 m/s values belong to .20 s and do not define that mapping. Four full-task directions unresolved, zero resolved coverage, conditional accuracy undefined; actual order resolves but predicted order abstained.',
        'Choose ONE narrowest supported role. An abstained speed-order forecast does not demonstrate execution ordering usefulness. Local diagnostic evidence is permitted but assess it yourself. No screening or automatic rejection authority.',
        'The planned pointwise expectations (.075 passes,.15 fails) were both contradicted. Do not claim this falsifies the entire interval (.05,.15] as a boundary: .075 failure alone is consistent with some boundary in that interval, and .15 passing rejects only the stated high-point failure. No continuous threshold or monotonic law was validated.',
        'Compare primary directional outcomes to the selected .05/.05 incumbent, not the earlier retained baseline: BOTH candidates deteriorate holding error and speed at frozen tolerances; .15 remains a physical tradeoff with better terminal error. Distinguish this from any improvement against a different baseline.',
        'Keep exact acceptance (.075 lost,.15 preserved), 35/35 deadline misses each, M4 closed/M5 open, retained incumbent, and finish/stop with zero future budget. State an accepted operational next action, not only a proposed experiment.'
    ]
    if attempt==2:
        issues=['The previous corrected prose is scientifically acceptable, but its formal retain_baseline result bound to the old Stage351 baseline-replay, contradicting its explicit retention of the M4 incumbent. This request fixes the final-phase baseline_facts binding to the selected .05/.05 incumbent; retain_baseline/baseline now refers exactly to batch-ebbeadbdaca10732-0, execution 91c3ba1b01d6499fb26df8f95409401b. Preserve the supported local diagnostic role, mixed prospective evidence, no promotion, finish/stop/zero budget. Distinguish original Stage351 failing baseline, passing 0/.05 pre-adaptation reference, and selected .05/.05 incumbent; do not infer general reliability or a continuous boundary.']
    review=dict(passed=False,final_response=original,issues=issues,repair='Same-stage model semantic correction; no numerical or backend replay.')
    atomic_json(stage.RUN/f'final_semantic_rejection_v{attempt}.json',review)
    w.freeze['semantic_corrections']=attempt
    w.freeze.setdefault('resume_interventions',[]).append(dict(kind='semantic_review',rejected_response=original,issues=issues))
    atomic_json(stage.RUN/'freeze.json',w.freeze)
    packet=read(stage.RUN/'validation_decision_packet.json')
    packet.update(prediction_assessment=read(stage.RUN/'prediction_assessment.json'),frozen_forecast=read(stage.RUN/'forecast_seal.json'),
        all_planned_candidates_completed=True,primary_reference=w.incumbent['candidate'],development_data=stage.DEVELOPMENT,
        semantic_correction=review,previous_final_response=w.store.artifact(original))
    for row in packet['prediction_assessment']['outcomes']:row['comparison']={k:v for k,v in row['comparison'].items() if k not in ('baseline','candidate')}
    packet['history']=stage.predecessor.compact_decision_packet(dict(history=packet['history']),None)['history']
    packet['frozen_forecast'].pop('predictor_fingerprint',None)
    w.current_stage='prediction_semantic_correction'
    w.instructions={**w.instructions,'response_final':stage.shared.FINAL+' Final evidence-only semantic correction. Address every semantic_correction issue using unchanged forecasts and saved complete observations. Choose the narrowest supported role and an explicit next action. No new execution. Finish; next_research.route=stop and all proposed_budget values zero. M4 closed, M5 overall open. About 500 words.'}
    start=time.monotonic()
    try:
        w.phase('response_final','design_response','final_response',decision_packet=packet,decision_packet_reference=stage.save(w.store,packet),
            batch_result=w.store.artifact(w.chain['batch_summary']),require_research_route=True,require_research_budget=True,
            research_records=w.historical_results,latest_tested=w.latest_tested,improvement_feedback_content=dict(baseline_facts=w.incumbent,execution=None),
            check_feedback=[dict(reference=w.chain['batch_summary'])],source_report=w.common['source_report'],source_record=w.source_record)
    finally:stage.export(w,'completed_pending_semantic_review','Evidence-only final correction requested; saved evaluations unchanged.',time.monotonic()-start)


def deliver():
    w=stage.restore();stage.assert_predecessor(w)
    outcome=read(stage.RUN/'outcome.json');batch=read(stage.RUN/'validation_batch_result.json')
    forecast=read(stage.RUN/'forecast_seal.json');assessment=read(stage.RUN/'prediction_assessment.json')
    final=w.store.artifact(w.chain['final_response']);review=read(stage.RUN/'final_semantic_acceptance.json')
    if outcome['status']!='completed' or not review['passed'] or review['final_response']!=w.chain['final_response']:raise ValueError('FINAL_INTERPRETATION_NOT_ACCEPTED')
    if batch['fully_evaluated_distinct_changed_configurations']!=len(forecast['forecasts']):raise ValueError('CANDIDATE_EVALUATION_INCOMPLETE')
    if w.store.artifact(w.chain['forecast_seal'])!=forecast or not assessment['forecast_chronology']['passed']:raise ValueError('FORECAST_SEAL_OR_CHRONOLOGY_CHANGED')
    if final['next_action']!='finish' or final['next_research']['route']!='stop' or any(final['next_research']['proposed_budget'].values()):raise ValueError('FINAL_NEXT_ACTION_NOT_CLOSED')
    if final['selected_candidate']!=w.incumbent['candidate']:raise ValueError('FINAL_SELECTION_NOT_RETAINED_INCUMBENT')
    accounting=read(stage.EVIDENCE/'accounting.json');numerical=read(stage.RUN/'prediction_numerical.json')
    accounting['semantic_corrections']['lifetime']=sum(accounting['semantic_corrections'][k] for k in ('old','new'))
    accounting['numerical_work_by_segment']=dict(old=dict(local_solves=3,prediction_evaluations=3,embedded_controller_updates=140),
        new={**accounting['numerical_work']['used'],'embedded_controller_updates':sum(r['metrics']['control_updates'] for r in assessment['outcomes'])})
    accounting['numerical_work_by_segment']['cumulative']={k:accounting['numerical_work_by_segment']['old'][k]+accounting['numerical_work_by_segment']['new'][k]
        for k in accounting['numerical_work_by_segment']['old']}
    atomic_json(stage.EVIDENCE/'accounting.json',accounting)
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
            retained_baseline=w.retained_baseline['candidate'],
            passing_pre_adaptation_reference=next(r['facts']['candidate'] for r in w.historical_results if r['facts']['execution_id']==stage.DEVELOPMENT[0]),
            latest_tested=w.latest_tested,stage_final_selection=selected),
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
        engineering_interventions=[
            'Recorded explicit transmission authorization beside the original rejection; refreshed the actual serialized handoff with all six results and current capacity.',
            'Restored historical_feedback from the saved common artifact after an offline refresh failure; no provider attempt or usage reset.',
            'Implemented predeclared tolerance-based speed ordering and neutral local speed-change labels; four focused resume checks passed.',
            *w.freeze.get('resume_interventions',[])],resume_focused_checks=4,
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


if __name__=='__main__':
    if '--correct-final' in sys.argv:correct_final()
    else:deliver()
