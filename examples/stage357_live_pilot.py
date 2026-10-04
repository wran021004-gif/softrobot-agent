"""One repaired single-context development pilot; original runs stay immutable."""
import argparse
from copy import deepcopy
from contextlib import closing,ExitStack
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
from examples.stage356_milestone2 import scientific_bundle,import_common,HISTORY,BASELINE
from tools.diagnostic_workflow import EvidenceDrivenWorkflow,implementation,save
from tools.platform_store import Store,plain
from tools.state_io import read,atomic_json,digest
from tools.diagnostic_handoff import accepted_product
from tools.diagnostic_facts import handover
from tools.diagnostic_summary import update_facts,read_coverage
from tools.platform_search import prepare_offline_batch,run_live_batch
from tools.platform_diagnosis_coordinator import configure_role
from tools.runtime_identity import require_softagent_runtime
from extensions.tendon_family.control_evidence import ControlEvidence

EVIDENCE=ROOT/'evidence/stage357_pilot_20261004'
RUN=ROOT/'runs/stage357_pilot_20261004/single_context'
CONFIRM=ROOT/'runs/stage357_confirmation_20261004/single_context'
GATE=ROOT/'evidence/stage357_confirmation_20261004/single_context/acceptance.json'


def archived_audit():
    reader=ControlEvidence(Store(HISTORY));source=reader.resolve('087adee8e8a24fe88e5c85fe89e638c8')
    selected=update_facts(reader,source,[24,26,27,28,29,31,32,33])
    states=read(ROOT/'evidence/stage356_milestone2_20261004/dual_context/evidence_contexts.json')
    confirmation_check=read(CONFIRM/'check.json')['proposal']
    confirmation_states=read(GATE.parent/'evidence_contexts.json')
    return dict(all_updates=update_facts(reader,source),dual_selected_updates=selected,dual_read_coverage=read_coverage(states,35),
        confirmation_selected_updates=update_facts(reader,source,confirmation_check['update_ids']),confirmation_read_coverage=read_coverage(confirmation_states,35),
        predecessor_review='evidence/stage356_milestone2_20261004/model_review.json',
        coverage_conflict='The predecessor review claims 16 queried updates, but preserved context ledgers and SQLite query receipts contain only the eight selected updates. No earlier plans query receipt exists in that workflow. Receipt-supported coverage is 8/35; 27 remain unqueried. Prior-source private reads are not current-context reads.',
        corrected_observations=['Four selected iteration-zero updates: 24,26,27,28.',
            'Update 29 policy stop is relative_seed_improvement; raw termination remains User_Requested_Stop.',
            'Legal near-bound tensions coexist with zero force violation.',
            'actual_tension_n is simulated backend actuator-force readback, distinct from requested commands and hardware force measurement.'])


def import_confirmation(workflow):
    old=Store(CONFIRM);outcome=read(CONFIRM/'outcome.json')
    if not read(GATE)['passed'] or outcome['status']!='completed':raise ValueError('REPAIRED_MILESTONE2_GATE_REQUIRED')
    chain=outcome['chain'];seen=set()
    def copy(value):
        if isinstance(value,dict):
            if set(value)=={'artifact_id','media_type'}:
                if value['artifact_id'] in seen:return
                seen.add(value['artifact_id']);body=old.artifact(value,raw=True)
                with workflow.store.transaction() as db:
                    if plain(workflow.store.put(db,body,value['media_type']))!=value:raise ValueError('IMPORTED_BYTES_CHANGED')
                if value['media_type']=='application/json':copy(json.loads(body))
            else:
                for v in value.values():copy(v)
        elif isinstance(value,list):
            for v in value:copy(v)
    copy(chain)
    for key in ('initial_report','revised_report'):
        accepted_product(old,chain[key],'diagnosis_report')
        with workflow.store.transaction() as db:
            proof=workflow.store.put(db,dict(source_report=chain[key],source_store=str(CONFIRM),source_gate=str(GATE),
                source_outcome_sha256=digest(outcome),classification='Verified prior model-authored accepted diagnosis; historical charges excluded.'))
            workflow.store.event(db,workflow.host('design').run_id,'accepted_saved_report_handoff','verified',inputs=[chain[key]],outputs=[proof])
    workflow.chain.update({k:chain[k] for k in ('initial_report','initial_response','check','feedback','revised_report','revised_handoff')})
    result=workflow.store.artifact(chain['feedback'])
    handover(workflow.host('design'),result['result'],workflow.store.artifact(result['result']),origin=dict(source=str(CONFIRM),receipt=result['receipt']),kind='selected_check_result')
    return outcome


class PilotWorkflow(EvidenceDrivenWorkflow):
    limits=dict(model_calls=16,tool_calls=60,backend_solves=3,worker_calls=0,wall_s=7200.)
    numerical_limits=dict(local_solves=0,prediction_evaluations=0)
    scope=None
    tools={**EvidenceDrivenWorkflow.tools,'design.respond_diagnosis':'3.0.0'}
    phases={**EvidenceDrivenWorkflow.phases,
        'improvement':dict(limit=dict(model_calls=6),protect_project=dict(model_calls=4,tool_calls=16,wall_s=3570.)),
        'response_final':dict(limit=dict(model_calls=6))}
    permissions={**EvidenceDrivenWorkflow.permissions,'response_final':['design.respond_diagnosis']}
    instructions={**EvidenceDrivenWorkflow.instructions,
        'improvement':EvidenceDrivenWorkflow.instructions['improvement'].replace('max_candidates 1..12','max_candidates at most 6').replace(
            'backend_solves=max_candidates, tool_calls>=4*max_candidates, wall_s>=990*max_candidates',
            'max_backend_attempts=3, target_changed_configurations=2, failure_policy=stop_on_material_failure; planned_budget backend_solves=3, tool_calls>=12 and <=60, wall_s>=2970 and <=7200, model_calls<=16')+
            ' This is the current authorized development pilot plan, linked to the accepted single-context diagnosis and factual audit. Require both weight paths, nonzero-width domains including saved values, legal step. Proposals include start and duplicates. Stop normally after TWO distinct changed configurations complete simulation/evaluation/profile, even if joint acceptance occurs earlier. Protect 600 seconds and four provider/tool slots for interpretation/delivery. No separate numerical screening or new baseline. Explicitly qualify causal or entire-range hypotheses using the factual audit; do not reuse archived dual-plan assertions as findings.',
        'response_final':'Interpret the supplied compact batch_result using every tested candidate physical vector and both comparison references. Explain improvement, worsening or trade-offs, and which observations support or weaken your hypothesis. State tested-point scope separately from any range claim. Decide whether to retain baseline, select a fully evaluated candidate, recommend further weight search, request a different diagnostic check or defer; the latter proposals authorize no execution. Submit design.respond_diagnosis with separate recommendation disposition and candidate_disposition. selected_candidate is baseline, none, or the exact evaluated candidate_id when adopting. next_action=finish. Your reasoning must state proposed next action independently. No statistical, global, organizational, real-time or hardware claim.'}

    def phase(self,phase,kind,key,**extra):
        if phase=='response_final':
            # Use the existing final response validator, bound to batch evidence.
            return super(EvidenceDrivenWorkflow,self).phase(phase,kind,key,**extra)
        return super().phase(phase,kind,key,**extra)


def prepare():
    bundle=scientific_bundle();runtime=require_softagent_runtime()
    config=deepcopy(read(CONFIRM/'freeze.json')['experiment'])
    config.update(evidence_directory=str(EVIDENCE),project_prefix='gvs-stage357',
        authorization_source='Current user: one Milestone 3 development pilot; DeepSeek evidence transfer; 16 attempts/60 tools/7200 charged seconds/3 backend attempts/zero workers; no screening, baseline rerun or push.')
    workflow=PilotWorkflow(RUN,'single_context',experiment=config)
    workflow.prepare(runtime);import_common(workflow,bundle);import_confirmation(workflow)
    audit=archived_audit();audit_ref=save(workflow.store,audit)
    handover(workflow.host('design'),audit_ref,audit,origin=dict(kind='retained_record_arithmetic'),kind='deterministic_factual_audit')
    workflow.freeze.update(confirmation_gate=read(GATE),current_factual_audit=audit_ref,
        pilot_limits=dict(proposals=6,backend_attempts=3,target_changed_configurations=2,
            reservation_s=dict(simulation=900,evaluation=30,profile=60,delivery=600)))
    atomic_json(RUN/'freeze.json',workflow.freeze);atomic_json(EVIDENCE/'factual_audit.json',audit)
    return workflow


def verify(names):
    EVIDENCE.mkdir(parents=True,exist_ok=True);stream=io.StringIO();start=time.monotonic()
    with ExitStack() as guards:
        for target in ('tools.model_transports.deepseek.request_completion','extensions.tendon_family.backends.MujocoBackend.run','extensions.tendon_family.gvs_trajectory.TrajectoryWorkspace.solve'):
            guards.enter_context(patch(target,side_effect=AssertionError('OFFLINE_FORBIDS_EXECUTION: '+target)))
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    record=dict(passed=result.wasSuccessful(),tests_run=result.testsRun,names=names,output=stream.getvalue(),elapsed_s=time.monotonic()-start,
        implementation=implementation(),new_provider_requests=0,new_backend_attempts=0,new_numerical_solves=0)
    atomic_json(EVIDENCE/('checks_'+str(time.time_ns())+'.json'),record)
    if result.wasSuccessful():atomic_json(EVIDENCE/'verification_current.json',record)
    print(stream.getvalue(),flush=True)
    if not result.wasSuccessful():raise ValueError('AFFECTED_CHECKS_FAILED')


def live():
    checked=read(EVIDENCE/'verification_current.json')
    if not checked['passed'] or checked['implementation']['files']!=implementation()['files']:raise ValueError('CURRENT_VERIFICATION_REQUIRED')
    if subprocess.check_output(['git','diff','HEAD','--',*implementation()['files']],cwd=ROOT,text=True):raise ValueError('COMMIT_BEFORE_PILOT')
    if RUN.exists():raise ValueError('PRESERVE_PRIOR_PILOT_NO_REPLACEMENT_GRANT')
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path.home()/'.codex/.env')
    removed=[]
    for name in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
        if '127.0.0.1:9' in os.environ.get(name,''):os.environ.pop(name);removed.append(name)
    workflow=prepare();started=time.monotonic();status='incomplete';reason=None
    atomic_json(RUN/'live_attempt.json',dict(implementation=implementation(),tls_verification=True,removed_dead_proxy_variable_names=removed))
    try:
        workflow.phase('improvement','search_batch_plan','search_plan',predecessor_plan=read(CONFIRM/'chain.json')['search_plan'],
            factual_audit=workflow.store.artifact(workflow.freeze['current_factual_audit']))
        host=workflow.host('design');configure_role(host,'executor','Execute the current accepted bounded plan only.',phase_budget={})
        host.resume()
        feedback=workflow.historical_feedback
        prepare_offline_batch(host,workflow.chain['search_plan'],mode='live',starting_facts=feedback['execution']['factual_result'],retained_baseline=feedback['baseline_facts'])
        atomic_json(RUN/'bound_batch.json',host.store.session(host.run_id)['state']['search_batch'])
        result=run_live_batch(host);ref=save(workflow.store,result)
        workflow.chain['batch_result']=ref;atomic_json(RUN/'batch_result.json',result)
        handover(host,ref,result,origin=dict(kind='sealed_live_batch'),kind='batch_result')
        workflow.phase('response_final','design_response','final_response',batch_result=result,experiment_plan=workflow.chain['search_plan'],
            improvement_feedback_content=dict(baseline_facts=feedback['baseline_facts'],execution=None),check_feedback=[dict(reference=ref)],
            source_report=workflow.common['source_report'],source_record=workflow.source_record)
        target=result['fully_evaluated_distinct_changed_configurations']>=2
        status='completed' if target and result['stop_reason']=='pilot_target_complete' else 'incomplete';reason=result['stop_reason']
    except Exception as exc:
        reason=str(exc);atomic_json(RUN/'workflow_failure.json',dict(type=type(exc).__name__,message=reason));print('STOP',reason,flush=True)
    workflow.export(status,reason,time.monotonic()-started)
    from tools.improvement_workflow import archive_store
    archive_store(workflow.store,EVIDENCE/'single_context',source_stores=[CONFIRM,HISTORY,BASELINE])
    atomic_json(EVIDENCE/'acceptance.json',dict(passed=status=='completed',stop_reason=reason,
        model_decision_present='final_response' in workflow.chain,implementation=implementation()))
    print('PILOT',status,reason,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['verify','live','audit']);p.add_argument('tests',nargs='*');a=p.parse_args()
    if a.action=='verify':verify(a.tests)
    elif a.action=='audit':atomic_json(EVIDENCE/'factual_audit.json',archived_audit())
    else:live()
