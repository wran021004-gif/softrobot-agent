"""Seal the current Milestone 4 evidence without any provider or backend work."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from examples import milestone4 as campaign
from tools.platform_store import plain,zero
from tools.state_io import atomic_json,read
from tools.study_history import study_history
from tools.settling_campaign import campaign_metrics


def main():
    w=campaign.restore();host=w.host('design');state=w.store.session(host.run_id)['state'];before=w.store.remaining()
    stop=state.get('stop_reason')
    if 'MODEL_PROTOCOL_CORRECTION_TOTAL_LIMIT' not in str(stop):raise ValueError('EXPECTED_SEALED_RECOVERY_STOP')
    if before['occupied']:raise ValueError('UNRESOLVED_RESERVATIONS_REQUIRE_RECONCILIATION')
    campaign.export(w,'stopped_correction_limit',stop,0.)
    destination=campaign.EVIDENCE/'single_context'
    receipts=[];raw=[];resolved=[];snapshots=[]
    with w.store.connect(True) as db:
        sessions=[r[0] for r in db.execute('SELECT run_id FROM sessions ORDER BY run_id')]
        for row in db.execute('SELECT run_id,request_id,receipt FROM calls WHERE receipt IS NOT NULL ORDER BY run_id,request_id'):
            receipts.append(dict(run_id=row[0],request_id=row[1],receipt=json.loads(row[2])))
    for run in sessions:
        session=w.store.session(run)
        snapshots.append(dict(run_id=run,parent_run_id=session.get('parent_run_id'),status=session['status'],
            snapshot=session['snapshot'],state=session['state']))
        for event in w.store.events(run):
            if event['kind']=='model_raw_response':raw.append(dict(run_id=run,reference=event['outputs'][0],response=w.store.artifact(event['outputs'][0])))
            if event['kind']=='model_decision':resolved.append(dict(run_id=run,reference=event['outputs'][0],invocation=w.store.artifact(event['outputs'][0])))
    atomic_json(destination/'campaign_receipts.json',receipts)
    atomic_json(destination/'campaign_raw_calls.json',raw)
    atomic_json(destination/'campaign_resolved_calls.json',resolved)
    atomic_json(destination/'campaign_contexts.json',snapshots)
    charged=zero()
    for row in receipts:
        for key,value in row['receipt']['charged'].items():charged[key]+=value
    for key in ('model_calls','tool_calls','backend_solves','worker_calls'):
        if charged[key]!=before['used'][key]:raise ValueError('RECEIPT_LEDGER_COUNT_MISMATCH: '+key)
    if abs(charged['wall_s']-before['used']['wall_s'])>1e-5:raise ValueError('RECEIPT_LEDGER_WALL_MISMATCH')
    control=read(w.directory/'control_batch_result.json');row=next(r for r in control['candidates'] if r.get('execution'))
    facts=row['execution']['factual_result'];decision=read(w.directory/'control_final_response.json')
    response_refs=[]
    for request in ('model-0','model-1'):
        receipt=json.loads(w.store.lookup(host.run_id,request)['receipt'])
        response_refs.append(w.store.artifact(receipt['output'])['response'])
    review=dict(status='rejected_unexecuted',original_responses=response_refs,
        proposal=dict(source_candidate=facts['candidate'],path='components/far/length_m',source_value=.11,proposed_value=.12),
        material_errors=['No native function call; planning request advertised zero tools.',
            'Saved prose does not satisfy SearchBatchPlan: missing canonical variables/method/evidence/fidelity_limits/scientific_promise; nested invented search fields and dictionary fixed_conditions.'],
        scientific_text_changed=False,proposal_executed=False,extra_provider_retry=False)
    atomic_json(destination/'structural_proposal_review.json',review)
    delivery=dict(status='incomplete',milestone4_passed=False,milestone4_closed=False,
        gates=dict(shared_research_state=True,control_continuation=True,structural_workflow_offline=True,
            changed_structure_full_evaluation=False,new_structure_control_adaptation=False,final_full_sequence_model_decision=False),
        stop_reason=stop,root_cause='Research host inherited execution-only tool bindings from evaluated child; zero planning tools were advertised. Host repair is verified offline; correction ceiling prevents another request in this campaign.',
        project_id=w.project,usage=before,receipt_charge_sum=charged,
        recovery=dict(total_corrections=state['protocol_corrections_used'],consecutive=state['protocol_corrections_consecutive'],
            total_limit=4,consecutive_limit=2,business_failures_total=state.get('business_failures_total',0),counters_reset=False),
        actual_new_executions=[dict(candidate=facts['candidate'],metrics=campaign_metrics(facts),
            changes=row['changes'],source=read(w.directory/'control_plan.json')['bindings']['subject'])],
        comparisons=read(w.directory/'control_decision_packet.json')['completed_results'],
        retained_baseline=w.retained_baseline['candidate'],latest_tested=facts['candidate'],
        last_accepted_substage_selection=decision['selected_candidate'],full_sequence_selection=None,
        control_substage_model_decision=decision,structural_proposal_review=review,
        organization=dict(live='single_context',dual_context='shared-interface offline checks only',paired_comparison=False),
        structural_coverage=dict(offline=['length','section_scale','material_scenario'],live=[]),
        historical=dict(milestones2_and3_closed=True,unknown_reservation_s=900.,charges_transferred=False,
            archived_interpretations_and_failures_rewritten=False),
        forbidden_extra_work=dict(separate_diagnostic_solves=0,prediction_sweeps=0,workers=0,new_controller=False,new_campaign=False,push=False),
        last_live_revision=read(w.directory/'structure_freeze.json')['revision'],offline_repair_revision=campaign.revision(),
        limitations=['Only the tested control candidate gained joint sampled acceptance.',
            'No changed structure was executed; proposed far length 0.12 m has no performance evidence.',
            'No structural/adaptation success, global optimum, physical impossibility, causal identification, continuous-time, hardware, or real-time feasibility claim.'])
    atomic_json(campaign.EVIDENCE/'delivery.json',delivery)
    status=read(campaign.EVIDENCE/'campaign_status.json');status.update(delivery='delivery.json',milestone4_passed=False)
    atomic_json(campaign.EVIDENCE/'campaign_status.json',status)
    if w.store.remaining()!=before:raise ValueError('CLOSEOUT_CHANGED_PAID_LEDGER')
    atomic_json(destination/'sha256_manifest.json',{p.relative_to(destination).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(destination.rglob('*')) if p.is_file() and p.name!='sha256_manifest.json'})
    print(json.dumps(dict(status=delivery['status'],gates=delivery['gates'],usage=before['used'],receipt_ledger_match=True)))


if __name__=='__main__':main()
