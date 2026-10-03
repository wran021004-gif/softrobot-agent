"""Bounded v5 suffix gates followed by exactly two fresh Milestone 0 workflows."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
from tools.state_io import read,atomic_json
from tools.platform_store import Store,plain
from tools.diagnostic_workflow import DiagnosticWorkflow,save
from tools.diagnostic_facts import handover
from tools.settling_campaign import SettlingWorkflow,compare_results
from tools.runtime_identity import require_softagent_runtime
from extensions.tendon_family.control_evidence import ControlEvidence
from examples.stage352_settling_campaign import verify_baseline
from examples.stage353_milestone0 import implementation as prior_implementation
from examples.stage351_settling_campaign import capability_gate
from examples.stage350_delivery_audit import audit_run,export_closure

CONFIG=ROOT/'examples/stage354_experiment.json'
SUFFIX_LIMITS=dict(model_calls=8,tool_calls=20,wall_s=600.,backend_solves=0,worker_calls=0)


def implementation():
    value=prior_implementation()
    for name in ('examples/stage354_milestone0.py','examples/stage354_experiment.json','tests/test_stage354_references.py'):
        value['files'][name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    return value


class MilestoneWorkflow(SettlingWorkflow):
    tools={**SettlingWorkflow.tools,'design.respond_diagnosis':'3.0.0'}

    def phase(self,phase,kind,key,**extra):
        if phase in ('revision','response_final') and self.chain.get('preparation'):
            extra['preparation_content']=self.store.artifact(self.chain['preparation'])
        return super().phase(phase,kind,key,**extra)


def import_suffix(workflow,old_root):
    old=Store(old_root);outcome=read(old_root/'outcome.json');chain=outcome['chain']
    if any(chain.get(k)!=v for k,v in read(old_root/'chain.json').items()):raise ValueError('HISTORICAL_CHAIN_MISMATCH')
    feedback=old.artifact(chain['feedback']);result=feedback['execution']
    if feedback!=read(old_root/'feedback.json') or result['status']!='evaluated':raise ValueError('COMPLETE_SAVED_FEEDBACK_REQUIRED')
    source=ControlEvidence(old).resolve(result['execution_id'])
    evaluation=old.artifact(result['receipts']['evaluation']['output']);profile=old.artifact(feedback['result'])['detail']
    if evaluation!=result['evaluation_data'] or evaluation['source_execution_id']!=source['execution_id'] or profile['execution_id']!=source['execution_id']:
        raise ValueError('SAVED_EVALUATION_PROFILE_IDENTITY_MISMATCH')
    if profile['configuration']!=source['metadata']['candidate_input'] or evaluation['source']!=result['receipts']['simulation']['output']:
        raise ValueError('SAVED_CONFIGURATION_SIMULATION_MISMATCH')
    from extensions.tendon_family.delivery_facts import bound_result_facts
    facts=bound_result_facts(old,dict(profile_report=result['profile_report'],evaluation=result['receipts']['evaluation']['output'],
        simulation=result['receipts']['simulation']),result['design_statement'])
    if facts!=result['factual_result'] or compare_results(feedback['baseline_facts'],facts)!=feedback['campaign_comparison']:
        raise ValueError('SAVED_DERIVED_FACTS_MISMATCH')
    request=old.artifact(chain['request'])
    if request['binding']!=workflow.binding or request['execution_id']!=workflow.execution:raise ValueError('SAVED_BASELINE_BINDING_MISMATCH')
    with old.connect(True) as db:ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
    if not any(e['kind']=='role_transition' and e['status']=='diagnosis_report' and chain['initial_report'] in e['outputs'] for i in ids for e in old.events(i)):
        raise ValueError('SAVED_INITIAL_REPORT_NOT_ACCEPTED')
    workflow.chain={k:chain[k] for k in ('request','initial_report','improvement_decision','preparation','feedback')}
    stores=[old,Store(workflow.source)];seen={}
    def collect(value):
        if isinstance(value,dict):
            if set(value)=={'artifact_id','media_type'}:
                key=value['artifact_id']
                if key in seen:return
                for store in stores:
                    with store.connect(True) as db:exists=db.execute('SELECT 1 FROM artifacts WHERE id=?',(key,)).fetchone()
                    if exists:body=store.artifact(value,raw=True);break
                else:raise ValueError('SAVED_REFERENCE_UNRESOLVED: '+key)
                seen[key]=(value,body)
                if value['media_type']=='application/json':collect(json.loads(body))
            else:
                for child in value.values():collect(child)
        elif isinstance(value,list):
            for child in value:collect(child)
    collect(workflow.chain)
    with workflow.store.transaction() as db:
        for ref,body in seen.values():
            if plain(workflow.store.put(db,body,ref['media_type']))!=ref:raise ValueError('ARCHIVED_BYTES_CHANGED')
        provenance=dict(classification='supplementary saved-evidence suffix; new grant, historical failure unchanged',
            original_store=str(old_root),original_outcome=outcome,execution=source['execution_id'],manifest=source['manifest'],
            imported_references=[r for r,b in seen.values()],new_backend_executions=0)
        workflow.store.event(db,workflow.host('diagnostic').run_id,'accepted_saved_report_handoff','verified',
            inputs=list(workflow.chain.values()),outputs=[workflow.store.put(db,provenance)])
    atomic_json(workflow.directory/'continuation_provenance.json',provenance)
    for key,ref in workflow.chain.items():atomic_json(workflow.directory/(key+'.json'),workflow.store.artifact(ref))
    return feedback


def run_suffix(workflow,old_root):
    started=time.monotonic();feedback=import_suffix(workflow,old_root)
    retained=[dict(reference=workflow.chain['feedback'],result=feedback['result'],receipt=feedback['receipt'],result_content=workflow.store.artifact(feedback['result']))]
    status='incomplete';reason=None
    atomic_json(workflow.directory/'live_attempt.json',dict(classification='supplementary suffix',started_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()))
    try:
        for role in ('diagnostic','design'):
            handover(workflow.host(role),workflow.chain['feedback'],feedback,origin=dict(kind='verified_saved_feedback'),kind='campaign_comparison')
        report=workflow.chain['initial_report']
        workflow.phase('revision','diagnosis_report','revised_report',previous_report=report,previous_report_content=workflow.store.artifact(report),
            check_feedback=retained,improvement_feedback_content=feedback)
        workflow.phase('response_final','design_response','final_response',check_feedback=retained,improvement_feedback_content=feedback)
        status='completed';reason='Accepted diagnostic revision and model-authored final candidate disposition from sealed historical feedback.'
    except Exception as exc:reason=str(exc);print('STOP',reason,flush=True)
    DiagnosticWorkflow.export(workflow,status,reason,time.monotonic()-started)
    outcome=read(workflow.directory/'outcome.json');outcome.update(classification='supplementary saved-evidence suffix',
        feedback_complete=all(k in workflow.chain for k in ('revised_report','final_response')))
    atomic_json(workflow.directory/'outcome.json',outcome)
    return outcome


def verify(config,affected=False):
    marker=Path(config['evidence_directory'])/'focused_check.json'
    if marker.exists():
        history=marker.parent/'offline_checks';history.mkdir(exist_ok=True)
        atomic_json(history/(str(time.time_ns())+'.json'),read(marker))
    started=time.monotonic();command=[sys.executable,'-m','unittest','tests.test_stage354_references']
    if not affected:command+=['tests.test_stage353_completion','tests.test_stage351_settling','tests.test_stage352_context']
    result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    record=dict(status='passed' if result.returncode==0 else 'failed',command=command,elapsed_s=time.monotonic()-started,
        output=result.stdout+result.stderr,implementation_files=implementation()['files'])
    atomic_json(Path(config['evidence_directory'])/'focused_check.json',record);print(record['output'],flush=True)
    if result.returncode:raise ValueError('FOCUSED_CHECK_FAILED')


def live(config,label,credential):
    current=implementation();export=Path(config['evidence_directory']);suffix=label.startswith('suffix_');mode=label.removeprefix('suffix_')
    check=read(export/'focused_check.json')
    if check['status']!='passed' or check['implementation_files']!=current['files']:raise ValueError('FOCUSED_CHECK_REQUIRED')
    dirty=subprocess.check_output(['git','diff','HEAD','--',*current['files']],cwd=ROOT,text=True)
    if dirty:raise ValueError('COMMIT_IMPLEMENTATION_BEFORE_PAID_VALIDATION')
    directory=Path(config['run_directory'])/label
    if directory.exists():raise ValueError('PRESERVE_EXISTING_RUN_AND_COSTS: no replacement launch')
    if not suffix:
        for organization in ('single_context','dual_context'):
            gate=read(export/('suffix_'+organization)/'acceptance.json')
            if not gate['passed']:raise ValueError('BOTH_SUFFIXES_MUST_PASS_BEFORE_SIMULATION')
        freeze=export/'fresh_freeze.json'
        if freeze.exists() and read(freeze)['implementation']!=current:raise ValueError('FRESH_IMPLEMENTATION_CHANGED')
        if not freeze.exists():atomic_json(freeze,dict(implementation=current,configuration=config))
    baseline=verify_baseline(config)
    atomic_json(export/'baseline_verification.json',dict(execution_id=config['execution_id'],hashes=baseline['artifact_hashes'],new_backend_executions=0))
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(credential)
    experiment={**config,'source_manifest':baseline['source']['manifest'],'baseline_facts':baseline['result']['factual_result']}
    workflow=MilestoneWorkflow(directory,mode,experiment=experiment)
    if suffix:workflow.limits=SUFFIX_LIMITS;workflow.numerical_limits=dict(local_solves=0,prediction_evaluations=0)
    workflow.prepare(require_softagent_runtime());atomic_json(directory/'implementation.json',current)
    old_root=Path(config['historical_workflows'])/mode
    outcome=run_suffix(workflow,old_root) if suffix else workflow.run()
    sources=[Path(config['source_store'])]+([old_root] if suffix else [])
    export_closure(directory,export/label,sources)
    audit=audit_run(directory);atomic_json(export/label/'audit.json',audit)
    if suffix:
        revised=workflow.store.artifact(workflow.chain['revised_report']) if 'revised_report' in workflow.chain else None
        feedback=workflow.store.artifact(workflow.chain['feedback'])
        cited=bool(revised and any(s['reference']==feedback['result'] and isinstance(s['value'],(float,int)) and not isinstance(s['value'],bool)
            for rows in revised['fact_selectors'].values() for s in rows))
        gate=dict(passed=outcome['status']=='completed' and cited and 'final_response' in workflow.chain,
            accepted_revision='revised_report' in workflow.chain,accepted_final='final_response' in workflow.chain,candidate_measurements_cited=cited)
    else:gate=capability_gate(directory)
    atomic_json(export/label/'acceptance.json',gate)
    print('ACCEPTANCE',label,json.dumps(gate),flush=True)


def recover_suffix(config,credential):
    """One host-defect recovery of an already-paid response; no revision retry.

    The failed model receipt is immutable. A separately recorded normalization
    feeds the ordinary pending-tool path, which rechecks all phase/project
    allowances. No budget, phase-start usage, correction count or turn is reset.
    """
    from tools.platform_host import Host
    from tools.platform_models import payload_for,run_loop
    from tools.platform_registry import dependency_closure
    from tools.diagnostic_reference_adapter import ScopedReferenceAdapter
    from schemas.platform import ModelResponse
    label='suffix_dual_context';directory=Path(config['run_directory'])/label;export=Path(config['evidence_directory'])/label
    current=implementation();check=read(Path(config['evidence_directory'])/'focused_check.json')
    if check['status']!='passed' or check['implementation_files']!=current['files']:raise ValueError('FOCUSED_CHECK_REQUIRED')
    if subprocess.check_output(['git','diff','HEAD','--',*current['files']],cwd=ROOT,text=True):raise ValueError('COMMIT_REPAIR_BEFORE_RECOVERY')
    marker=directory/'implementation_transition.json'
    if marker.exists():raise ValueError('RECOVERY_ALREADY_ATTEMPTED: preserve this run; no replay')
    freeze=read(directory/'freeze.json');original=read(directory/'outcome.json');store=Store(directory)
    if original['status']!='incomplete' or 'revised_report' in original['chain']:raise ValueError('EXPECTED_FAILED_SUFFIX_REQUIRED')
    host=Host(directory,freeze['hosts']['diagnostic']);session=store.session(host.run_id);state=session['state']
    if session['status']!='budget_exhausted' or state['role_context']['phase']!='revision':raise ValueError('EXPECTED_REVISION_PHASE_STOP_REQUIRED')
    if state.get('pending') or store.lookup(host.run_id,'model-3-tool'):raise ValueError('SAVED_TOOL_ALREADY_PENDING_OR_EXECUTED')
    row=store.lookup(host.run_id,'model-3');receipt=json.loads(row['receipt'])
    if receipt['execution_status']!='failed' or receipt['error']!="INVALID_TOOL_CALL_ENVELOPE: business_parameters: 'arguments'":
        raise ValueError('ONLY_THE_RECORDED_DRAFT_ROOT_DECODER_DEFECT_CAN_BE_RECOVERED')
    event=next(e for e in store.events(host.run_id) if e['kind']=='model_raw_response' and e['request_id']=='model-3')
    response=ModelResponse.model_validate(store.artifact(event['outputs'][0]));adapter=ScopedReferenceAdapter()
    before=store.remaining();prior_state=deepcopy(state)
    payload=payload_for(host,adapter)
    decoded=adapter.decode(response,3,session['snapshot']['input']['policy']['tool_bindings'],payload['tools'])
    if decoded['tool_id']!='diagnosis.submit' or decoded['request_id']!='model-3-tool':raise ValueError('RECOVERY_MUST_NORMALIZE_ONLY_SAVED_SUBMISSION')
    transition=dict(reason='Host bug: advertised draft-root correction pointer was interpreted relative to arguments only. Revalidate exact saved model-3 bytes; no generated replacements.',
        original_outcome=original,old_implementation=read(directory/'implementation.json'),new_implementation=current,
        response=event['outputs'][0],request=event['inputs'][0],failed_receipt=receipt,usage_before=before,
        provider_attempts_added_for_revision=0,budget_changes={},phase_limit_changes={},state_counter_resets=[])
    # Rebind implementation fingerprints explicitly, preserving immutable old
    # snapshots and all input/grant identities; science and provider are unchanged.
    with store.transaction() as db:
        transitions=[]
        for identity in freeze['hosts'].values():
            saved=store.session(identity,db);snapshot=deepcopy(saved['snapshot']);changes=[]
            for key,expected in list(snapshot['dependencies'].items()):
                name,version=key.rsplit('@',1);actual=dependency_closure([host.reg.get(name,version)],host.reg)[key]
                if actual!=expected:
                    if key not in ('deepseek@5.0.0','design.respond_diagnosis@3.0.0'):raise ValueError('UNEXPECTED_RECOVERY_DEPENDENCY_CHANGE: '+key)
                    changes.append(key);snapshot['dependencies'][key]=actual
            old_ref=db.execute('SELECT snapshot FROM sessions WHERE run_id=?',(identity,)).fetchone()[0]
            new_ref=store.put(db,snapshot);db.execute('UPDATE sessions SET snapshot=? WHERE run_id=?',(new_ref.artifact_id,identity))
            transitions.append(dict(context=identity,old_snapshot=old_ref,new_snapshot=plain(new_ref),changed=changes))
        transition['snapshots']=transitions
        current_state=store.session(host.run_id,db)['state']
        for key in ('turn','protocol_corrections_used','protocol_corrections_consecutive','business_failures_total','repairs'):
            if current_state.get(key)!=prior_state.get(key):raise ValueError('RECOVERY_CHANGED_ACCOUNTING_STATE')
        if current_state['role_context']['phase_budget']!=prior_state['role_context']['phase_budget']:raise ValueError('RECOVERY_CHANGED_PHASE_BUDGET')
        decision_ref=store.put(db,decoded)
        current_state['pending']=dict(decision=decoded,parent=row['parent_id'],input=event['inputs'][0])
        # This status change authorizes only the saved pending tool. It neither
        # permits another revision provider attempt nor replenishes its limit.
        store.update_state(db,host.run_id,current_state,'paused')
        store.event(db,host.run_id,'host_decoder_recovery','pending_saved_decision',inputs=[event['outputs'][0],event['inputs'][0]],
            outputs=[decision_ref,store.put(db,transition)])
    atomic_json(marker,transition);atomic_json(directory/'before_repair_outcome.json',original)
    for name in ('acceptance.json','audit.json'):
        (directory/('before_repair_'+name)).write_bytes((export/name).read_bytes())
    started=time.monotonic();status='incomplete';reason=None
    workflow=MilestoneWorkflow(directory,'dual_context',experiment=freeze['experiment'])
    workflow.freeze=freeze;workflow.project=freeze['project_id'];workflow.chain=deepcopy(original['chain']);workflow.limits=freeze['limits']
    workflow.hosts={k:Host(directory,v) for k,v in freeze['hosts'].items()};workflow.binding=freeze['binding'];workflow.identities=freeze['identities']
    workflow.summary=freeze['summary'];workflow.inventory=freeze['inventory'];workflow.inventory_ref=freeze['inventory_reference'];workflow.previous=host
    try:
        # No provider transport may be used while recovering this paid response.
        adapter.respond=lambda *args: (_ for _ in ()).throw(RuntimeError('RECOVERY_REVISION_MUST_NOT_CALL_PROVIDER'))
        run_loop(host,adapter)
        if store.remaining()['used']['model_calls']!=before['used']['model_calls']:raise ValueError('RECOVERY_MADE_NEW_REVISION_ATTEMPT')
        revised=store.session(host.run_id)['state'].get('handoffs',{}).get('diagnosis_report')
        if not revised:raise ValueError('RECOVERED_REVISION_NOT_ACCEPTED')
        workflow.chain['revised_report']=revised;atomic_json(directory/'revised_report.json',store.artifact(revised));atomic_json(directory/'chain.json',workflow.chain)
        from examples.gvs_nmpc_route_experiment import load_credential
        load_credential(credential)
        feedback=store.artifact(workflow.chain['feedback'])
        retained=[dict(reference=workflow.chain['feedback'],result=feedback['result'],receipt=feedback['receipt'],result_content=store.artifact(feedback['result']))]
        workflow.phase('response_final','design_response','final_response',check_feedback=retained,improvement_feedback_content=feedback)
        status='completed';reason='Saved model-authored correction recovered after host decoder repair, then accepted final decision; original failures and ceilings retained.'
    except Exception as exc:reason=str(exc);print('STOP',reason,flush=True)
    DiagnosticWorkflow.export(workflow,status,reason,original['elapsed_s']+time.monotonic()-started)
    outcome=read(directory/'outcome.json');outcome.update(classification='supplementary saved-evidence suffix with recorded host-decoder recovery',
        feedback_complete=all(k in workflow.chain for k in ('revised_report','final_response')))
    atomic_json(directory/'outcome.json',outcome)
    export_closure(directory,export,[Path(config['source_store']),Path(config['historical_workflows'])/'dual_context'])
    atomic_json(export/'audit.json',audit_run(directory))
    gate=dict(passed=outcome['status']=='completed' and outcome['feedback_complete'],accepted_revision='revised_report' in workflow.chain,
        accepted_final='final_response' in workflow.chain,candidate_measurements_cited='revised_report' in workflow.chain,
        recovery='Exact saved response through ordinary pending-tool validation, zero new revision provider attempts, unchanged ceilings.')
    atomic_json(export/'acceptance.json',gate);print('ACCEPTANCE',label,json.dumps(gate),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['verify','suffix_single_context','suffix_dual_context','recover_suffix_dual_context','single_context','dual_context'])
    p.add_argument('--credential',type=Path,default=Path.home()/'.codex/.env');p.add_argument('--affected',action='store_true');args=p.parse_args()
    require_softagent_runtime();config=read(CONFIG)
    if args.action=='verify':verify(config,args.affected)
    elif args.action=='recover_suffix_dual_context':recover_suffix(config,args.credential)
    else:live(config,args.action,args.credential)


if __name__=='__main__':main()
