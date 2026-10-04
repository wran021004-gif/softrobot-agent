"""Seal delivery from completed receipts and unchanged prospective evidence."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from examples import milestone45_continuation as run
from tools.state_io import read,atomic_json
from tools.platform_store import plain
from tools.study_history import study_history
from tools.candidate_parameters import parameter_value
from tools.settling_campaign import campaign_metrics,compare_results


def deliver():
    w=run.restore();run.assert_predecessor(w);destination=run.EVIDENCE
    structure=read(run.RUN/'structure_batch_result.json');adaptation=read(run.RUN/'adaptation_batch_result.json')
    decision=read(run.RUN/'complete_sequence_closed_final_response.json');forecast=read(run.RUN/'pilot_forecast_seal.json')
    assessment=read(run.RUN/'pilot_assessment.json');accounting=read(destination/'accounting.json')
    outcome=read(run.RUN/'outcome.json')
    if outcome['status']!='sequence_complete' or structure['fully_evaluated_distinct_changed_configurations']!=1 or adaptation['fully_evaluated_distinct_changed_configurations'] not in (1,2):raise ValueError('INCOMPLETE_REQUIRED_SEQUENCE')
    if decision['next_action']!='finish' or decision['next_research']['route']!='stop':raise ValueError('FINAL_CAMPAIGN_NOT_CLOSED')
    if w.store.artifact(w.chain['pilot_forecast_seal'])!=forecast:raise ValueError('FROZEN_FORECAST_CHANGED')
    with w.store.connect(True) as db:ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
    events=[e for identity in ids for e in w.store.events(identity)]
    seal=next(e for e in events if e['kind']=='prospective_forecast' and e['status']=='sealed')
    reserved=[e for e in events if e['run_id'] in {r['candidate_id'] for r in adaptation['candidates']} and e['request_id']=='complete-simulation' and e['status']=='reserved']
    if len(reserved)!=len(adaptation['candidates']) or any(e['sequence']<=seal['sequence'] for e in reserved):raise ValueError('FORECAST_NOT_PROSPECTIVE')
    selected=next(r['facts'] for r in w.historical_results if r['facts']['candidate']==decision['selected_candidate'])
    source=next(r['facts'] for r in w.historical_results if r['facts']['candidate']==read(run.RUN/'structure_plan.json')['bindings']['subject'])
    successful=next(r['facts'] for r in w.historical_results if r['facts']['execution_id']==run.CONTROL_EXECUTION)
    before=structure['candidates'][0]['execution']['factual_result']
    references=dict(retained_baseline=w.retained_baseline,declared_research_source=source,earlier_successful_control=successful,changed_structure_before_adaptation=before)
    comparisons={name:compare_results(facts,selected) for name,facts in references.items()}
    cfg=w.store.artifact(selected['configuration'])['effective']
    metrics=[]
    for name,facts in [*references.items(),*[(r['candidate_id'],r['execution']['factual_result']) for r in adaptation['candidates']]]:
        current=w.store.artifact(facts['configuration'])['effective']
        metrics.append(dict(name=name,candidate=facts['candidate'],near_length_m=parameter_value(current,'components/near/length_m'),
            far_length_m=parameter_value(current,'components/far/length_m'),holding_weight=parameter_value(current,'control/recipe/holding_tip_speed_weight'),
            terminal_weight=parameter_value(current,'control/recipe/terminal_tip_speed_weight'),metrics=campaign_metrics(facts)))
    with w.store.connect(True) as db:
        receipts=[json.loads(row[0]) for row in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL')]
        work=json.loads(db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()[0])
    summed={k:sum(r['charged'][k] for r in receipts) for k in run.prior.GRANT}
    if any(abs(summed[k]-accounting['new'][k])>1e-8 for k in summed):raise ValueError('DELIVERY_ACCOUNTING_MISMATCH')
    gates=dict(accepted_structural_plan=True,changed_structure_full_evaluation=True,completed_adaptation_batch=True,
        accepted_complete_sequence_decision=True,intact_ownership_and_combined_accounting=True)
    delivery=dict(status='completed',milestone4_closed=True,milestone4_gates=gates,milestone5_pilot_completed=True,milestone5_complete=False,
        milestone5_result='Inconclusive: no resolved directional or ordering forecast from this saved state.',
        identities=dict(retained_baseline=w.retained_baseline['candidate'],declared_research_source=source['candidate'],earlier_successful_control=successful['candidate'],
            changed_structure=before['candidate'],latest_tested=w.latest_tested,selected_deliverable=selected['candidate']),
        selected_configuration=dict(near_length_m=parameter_value(cfg,'components/near/length_m'),far_length_m=parameter_value(cfg,'components/far/length_m'),
            section_scale=parameter_value(cfg,'design/section_scale'),material_scenario=parameter_value(cfg,'design/material_scenario'),
            holding_weight=parameter_value(cfg,'control/recipe/holding_tip_speed_weight'),terminal_weight=parameter_value(cfg,'control/recipe/terminal_tip_speed_weight'),
            controller='controller.gvs_nmpc@7.0.0'),selected_metrics=campaign_metrics(selected),selected_comparisons=comparisons,
        all_named_metrics=metrics,model_selection_reasoning=decision['reasoning'],pilot_assessment=assessment,accounting=accounting,
        numerical_work=work,embedded_controller_updates=sum(r['execution']['factual_result']['control_updates'] for b in (structure,adaptation) for r in b['candidates']),
        embedded_optimization_separate_from_diagnostic_work=True,forecast_chronology=dict(seal_sequence=seal['sequence'],backend_reservation_sequences=[e['sequence'] for e in reserved],passed=True),
        revision=run.revision(),engineering_interventions=['Explicit linked remaining grant preserves historical terminal state and usage.',
            'Extended existing compatibility review to the completed successful control source.',
            'Repaired missing summary lineage and exporter duplicate key; resumed interpretation without simulation replay.',
            'Preserved and requested model correction of the false structural confounding caveat.',
            'Focused test and Git writes needed sandbox escalation; no automatic approval rejection.'],
        semantic_correction_requests=3,protocol_correction_counts=accounting['corrections'],
        limitations=['Sampled simulation acceptance only; no real-time, hardware or continuous-time proof.',
            'Prospective pilot uses one final-holding projected state and a common cold seed; all three local policy solves stopped at verified_settled_seed and selected iteration zero.',
            'Local endpoint metrics are not full-task holding maxima; no absolute acceptance or overall ordering forecast.',
            'One structure and two control candidates do not establish general screening reliability or structural screening.',
            'No automatic rejection, controller-family comparison, new paired single/dual comparison, or full Milestone 5 closure.'],
        no_extra_campaign=True,pushed=False)
    atomic_json(destination/'delivery.json',delivery)
    atomic_json(destination/'history_final.json',study_history(w.store,w.historical_results,retained_baseline=w.retained_baseline['candidate'],
        selected_source=source['candidate'],latest_tested=w.latest_tested,selection=selected['candidate']))
    # Preserve raw executed implementation alongside commit/hash records.
    for path in ['examples/milestone4.py',*run.FILES,'examples/milestone45_delivery.py']:
        target=destination/'implementation'/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/path).read_bytes())
    for path in ROOT.joinpath('runs').glob('milestone45_*_console.log'):
        shutil.copyfile(path,destination/'single_context'/path.name)
    atomic_json(destination/'sha256_manifest.json',{p.relative_to(destination).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(destination.rglob('*')) if p.is_file() and p.name!='sha256_manifest.json'})
    print(json.dumps(dict(milestone4_closed=True,milestone5_pilot_completed=True,selected=selected['candidate'],metrics=delivery['selected_metrics'],usage=accounting),indent=2))


if __name__=='__main__':deliver()
