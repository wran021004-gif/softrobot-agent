"""Offline Stage 3.51 delivery from sealed outcomes; never launches experiments."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.state_io import read,atomic_json
from tools.platform_store import Store
from examples.stage351_settling_campaign import audit,CONFIG,frozen_implementation


def main():
    config=read(CONFIG);base=Path(config['run_directory']);export=Path(config['evidence_directory'])
    result=audit(config);failures=[];integrity=[]
    for directory in sorted(base.iterdir()):
        if not (directory/'outcome.json').exists():continue
        store=Store(directory)
        with store.connect(True) as db:ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
        for run_id in ids:
            for event in store.events(run_id):
                if event['kind']=='model_response' and event['status']=='failed':
                    failures.append(dict(run=directory.name,event=event,artifacts=[dict(reference=ref,content=store.artifact(ref)) for ref in event['outputs']]))
        destination=export/directory.name
        external=read(destination/'external_references.json')
        if external:raise ValueError('UNRESOLVED_PORTABLE_REFERENCES')
        manifest=read(destination/'sha256_manifest.json')
        mismatches=[name for name,digest in manifest.items() if hashlib.sha256((destination/name).read_bytes()).hexdigest()!=digest]
        if mismatches:raise ValueError('EXPORT_HASH_MISMATCH: '+str(mismatches))
        integrity.append(dict(run=directory.name,verified_files=len(manifest),unresolved_references=0,mismatches=[]))
    # The inherited historical auditor selects only kind=model errors. Preserve
    # the actual v4 transport failure events explicitly in this new-stage audit.
    result['transport_failures']=failures;result['portable_integrity']=integrity
    result['provider_usage_available']=any(r['token_usage_records'] for r in result['runs'])
    result['reported_zero_tokens_is_not_proof_of_zero_billed_tokens']=not result['provider_usage_available']
    atomic_json(export/'final_audit.json',result)
    original=read(base/'baseline'/'outcome.json');pilot=read(base/'development_dual'/'outcome.json')
    gate=read(export/'pilot_gate.json');freeze=read(export/'development_freeze.json')
    assert freeze['implementation']['files']==frozen_implementation()['files']
    archived=export/'validated_implementation'
    assert all(hashlib.sha256((archived/name).read_bytes()).hexdigest()==digest for name,digest in freeze['implementation']['files'].items())
    summary=dict(status='Implementation and baseline delivered; live pilot failed before diagnosis; dependent formal runs withheld.',
        implementation_commit=freeze['implementation']['commit'],implementation_hashes_preserved=True,
        offline_delivery_script='Added after the terminal campaign solely for auditing; not part of the live validated implementation.',
        reporting_repairs=['Source-bound counts and ranges with explicit selected coverage.','Separate reach, holding position, holding speed and computation.','Prediction reads include measured endpoints; plans-only reads do not.','Read-ledger history remains distinct from current display.','Synchronous wall overruns do not establish skipped simulated updates.','Insufficient evidence for geometry benefit does not establish geometry irrelevance.'],
        control_grant=original['result']['design_statement']['parameters'],
        experimental_bounds=dict(paths=list(configured_paths()),bounds=[0.,1.],minimum_new_positive=.0001),
        baseline=original['campaign_metrics'],baseline_configuration=original['result']['configuration'],
        baseline_complete_execution=original['result']['execution_id'],baseline_usage=original['usage']['used'],
        pilot=dict(status=pilot['status'],reason=pilot['stop_reason'],capability_gate=gate,
            actual_model_selected_delta=None,candidate_executions=0,accepted_diagnosis=False,accepted_revision=False,accepted_final_decision=False,
            response_returned=False,raw_failure_evidence=failures,usage=pilot['usage']['used']),
        formal_runs=[dict(pair=pair,organization=mode,status='not_launched',reason='Changed-candidate pilot execution/feedback capability gate unmet.') for pair,mode in config['formal_order']],
        candidate_results=[],candidate_minus_baseline=None,joint_task_success=False,workflow_completed=False,
        optimization_demonstrated=False,robot_structure_optimization=False,
        scientific_prose_review=dict(status='not_assessable_no_model_report',reviewer='Implementer review, not independent blind review.',
            masked_copy='masked_review/case_1.json',findings=['No model-authored diagnosis, hypothesis, delta, revision or final decision was returned.','Numerical summary/coverage repairs passed offline checks; live scientific prose quality and feedback-driven decision change were not established.']),
        usage=result['usage'],tokens=dict(provider_reported=result['tokens'],usage_records=sum(r['token_usage_records'] for r in result['runs']),actual_tokens='unknown; transport returned no usage'),
        local_computation=dict(local_solves=0,prediction_solves=0,charged_local_solver_seconds=0.),monetary_cost=None,
        development_revalidation=dict(executed=False,reason='Recorded network failure is not demonstrated evidence of a host/interface defect; no replacement or retry is authorized by this run.'),
        pre_live_repairs=read(export/'focused_check.json')['offline_repairs'],
        next_limitation='Restore or diagnose the connection to the configured DeepSeek endpoint, then obtain a new campaign authorization for a fresh live pilot. The current transport records URLError only as DEEPSEEK_NETWORK_ERROR, so the subtype/root cause is unknown. Changed-candidate capability still needs real complete execution, measured revision and accepted final decision.',
        limits='Sampled simulation only; no continuous-time, real-time or hardware improvement claim. No organization comparison is available.')
    atomic_json(export/'delivery_summary.json',summary)
    atomic_json(export/'scientific_review.json',summary['scientific_prose_review'])
    atomic_json(export/'delivery_manifest.json',{p.relative_to(export).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(export.rglob('*')) if p.is_file() and p.name!='delivery_manifest.json'})
    print(json.dumps(dict(status=summary['status'],usage=result['usage']['used'],integrity=integrity)))


def configured_paths():
    from extensions.tendon_family.candidate import REACH_WEIGHT_PATHS
    return REACH_WEIGHT_PATHS


if __name__=='__main__':main()
