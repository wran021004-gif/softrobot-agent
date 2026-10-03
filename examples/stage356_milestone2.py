"""One common offline freeze and exactly one live workflow per organization."""
import argparse
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from contextlib import ExitStack,closing
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
from tools.state_io import read,atomic_json,digest
from tools.platform_store import Store,plain,encode
from tools.diagnostic_workflow import EvidenceDrivenWorkflow,implementation,save
from tools.platform_diagnosis_coordinator import configure_role,bind_diagnostic_grant
from tools.diagnostic_handoff import accepted_product,numerical_eligibility
from tools.runtime_identity import require_softagent_runtime
from extensions.tendon_family.control_evidence import ControlEvidence
from extensions.tendon_family.diagnostic_evidence import import_execution

EXPORT=ROOT/'evidence/stage356_milestone2_20261004'
RUNS=ROOT/'runs/stage356_milestone2_20261004'
HISTORY=ROOT/'runs/stage354_milestone0_20261003/single_context'
BASELINE=ROOT/'runs/stage351_settling_20261003/baseline'
EXECUTION='087adee8e8a24fe88e5c85fe89e638c8'
BASELINE_EXECUTION='cf997605885642759ee33920e2c9e2ef'


def scientific_bundle():
    from tools.working_state import project_working_state
    from tools.settling_campaign import compare_results
    from extensions.tendon_family.delivery_facts import bound_result_facts
    old=Store(HISTORY);outcome=read(HISTORY/'outcome.json');chain=outcome['chain']
    source=ControlEvidence(old).resolve(EXECUTION)
    baseline=ControlEvidence(Store(BASELINE)).resolve(BASELINE_EXECUTION)
    source_report=accepted_product(old,chain['revised_report'],'diagnosis_report')
    accepted_product(old,source_report['previous_report'],'diagnosis_report')
    feedback=old.artifact(chain['feedback']);execution=feedback['execution']
    if feedback!=read(HISTORY/'feedback.json') or execution['execution_id']!=EXECUTION:raise ValueError('HISTORICAL_FEEDBACK_MISMATCH')
    if chain['feedback'] not in source_report['check_results']:raise ValueError('SOURCE_REPORT_FEEDBACK_LINEAGE_MISMATCH')
    evaluation=old.artifact(execution['receipts']['evaluation']['output']);profile=old.artifact(feedback['result'])['detail']
    if (evaluation!=execution['evaluation_data'] or evaluation['source_execution_id']!=EXECUTION or
            profile['execution_id']!=EXECUTION or profile['configuration']!=source['metadata']['candidate_input']):
        raise ValueError('HISTORICAL_EVALUATION_PROFILE_BINDING_MISMATCH')
    facts=bound_result_facts(old,dict(profile_report=execution['profile_report'],evaluation=execution['receipts']['evaluation']['output'],
        simulation=execution['receipts']['simulation']),execution['design_statement'])
    if facts!=execution['factual_result'] or compare_results(feedback['baseline_facts'],facts)!=feedback['campaign_comparison']:
        raise ValueError('HISTORICAL_FACT_COMPARISON_MISMATCH')
    if feedback['baseline_facts']['candidate']['execution_id']!=BASELINE_EXECUTION:raise ValueError('BASELINE_BINDING_MISMATCH')
    if feedback['baseline_facts']['candidate']['configuration']!=baseline['metadata']['candidate_input']:raise ValueError('BASELINE_CONFIGURATION_MISMATCH')
    view=project_working_state(old,read(HISTORY/'freeze.json')['hosts']['shared'])
    if source['configuration']['policy']['controller']['version']!='7.0.0':raise ValueError('SOURCE_CONTROLLER_VERSION_MISMATCH')
    return dict(version='1.0.0',historical_store=str(HISTORY),source_report=chain['revised_report'],feedback=chain['feedback'],
        subject=facts['candidate'],baseline=feedback['baseline_facts']['candidate'],
        subject_manifest=source['manifest'],baseline_manifest=baseline['manifest'],task=view.task,acceptance=view.acceptance,
        provider_freeze=str(ROOT/'evidence/stage354_milestone0_20261003/single_context/freeze.json'),
        old_usage=outcome['usage'],classification='Same immutable accepted source products and science for both fresh organizations; historical costs excluded.')


def import_common(workflow,bundle):
    stores=[Store(HISTORY),Store(BASELINE)];seen={}
    def collect(value):
        if isinstance(value,dict):
            if set(value)=={'artifact_id','media_type'}:
                if value['artifact_id'] in seen:return
                for store in stores:
                    with closing(store.connect(True)) as db:exists=db.execute('SELECT 1 FROM artifacts WHERE id=?',(value['artifact_id'],)).fetchone()
                    if exists:body=store.artifact(value,raw=True);break
                else:raise ValueError('SOURCE_REFERENCE_UNRESOLVED: '+value['artifact_id'])
                seen[value['artifact_id']]=(value,body)
                if value['media_type']=='application/json':collect(json.loads(body))
            else:
                for child in value.values():collect(child)
        elif isinstance(value,list):
            for child in value:collect(child)
    collect(bundle)
    with workflow.store.transaction() as db:
        for ref,body in seen.values():
            if plain(workflow.store.put(db,body,ref['media_type']))!=ref:raise ValueError('IMPORTED_BYTES_CHANGED')
        record=dict(source_report=bundle['source_report'],feedback=bundle['feedback'],subject=bundle['subject'],baseline=bundle['baseline'],
            verified_source_bundle=digest(bundle),imported_references=[ref for ref,body in seen.values()],original_source=str(HISTORY),
            original_acceptance='Verified role_transition diagnosis_report and exact previous-report/feedback/execution lineage; no historical sessions or private memories imported.')
        workflow.source_record=plain(workflow.store.put(db,record))
        workflow.store.event(db,workflow.host('diagnostic').run_id,'accepted_saved_report_handoff','verified',
            inputs=[bundle['source_report'],bundle['feedback']],outputs=[workflow.source_record])
    import_execution(ControlEvidence(stores[1]),BASELINE_EXECUTION,workflow.store,workflow.hosts['executor'].run_id,bundle['baseline_manifest'])
    workflow.common=bundle;workflow.historical_feedback=workflow.store.artifact(bundle['feedback'])
    workflow.eligibility=numerical_eligibility(workflow.store,workflow.binding)
    design=workflow.host('design')
    configure_role(design,'design','Bind the current diagnostic source and ceilings; this deterministic request contains no model-authored assessment.',
        diagnostic_tools=list(workflow.tools),protocol=dict(saved_state_check=workflow.scope),phase_tools=['diagnosis.request'])
    design.resume()
    args=dict(question='Evidence-driven assessment of the saved reach/holding result; distinguish useful explanations with a recorded check.',
        subject='control',binding=workflow.binding,**{k:workflow.identities[k] for k in ('candidate_id','execution_id','task_identity','controller_identity','evidence_manifest')},
        permitted_tools=['diagnosis.inspect_evidence','diagnosis.check_request','diagnosis.submit','diagnosis.propose_check','diagnosis.revise_assessment','evidence.read'],
        scope=['Retained-evidence queries or at most one existing saved-state check. No backend simulation or production change.'],
        saved_state_check=workflow.scope,budget=workflow.limits,stopping_conditions=['One selected check, interpretation, valid future plan and final decision; stop within frozen ceilings.'])
    receipt=design.invoke(dict(request_id='bind-current-diagnostic-request',tool_id='diagnosis.request',tool_version='1.0.0',arguments=args,reason='Host-bound current request',cache='new'))
    if receipt['execution_status']!='completed':raise ValueError('CURRENT_REQUEST_FAILED: '+str(receipt['error']))
    workflow.chain['request']=workflow.store.artifact(receipt['output'])['reference']
    if workflow.mode=='dual_context':bind_diagnostic_grant(workflow.host('diagnostic'),workflow.chain['request'])
    workflow.freeze.update(common_scientific_input=bundle,source_record=workflow.source_record,numerical_eligibility=workflow.eligibility)
    atomic_json(workflow.directory/'freeze.json',workflow.freeze)
    atomic_json(workflow.directory/'chain.json',workflow.chain)


def prepare(mode,directory=None):
    bundle=scientific_bundle();runtime=require_softagent_runtime()
    config=dict(source_store=str(HISTORY),execution_id=EXECUTION,source_manifest=bundle['subject_manifest'],
        provider_freeze=bundle['provider_freeze'],adapter_version='6.0.0',context_bytes=400000,fact_handles=True,
        context_guard=read(Path(bundle['provider_freeze']))['provider_configuration']['context_guard'],
        evidence_directory=str(EXPORT),project_prefix='gvs-stage356',
        authorization_source='User Milestone 2: exactly one fresh workflow per organization, 24 attempts/60 tools/1800 charged seconds, zero backends/workers, at most one saved-state request, 2 local solves/2 prediction evaluations. Reserve interpretation capacity. No push.')
    workflow=EvidenceDrivenWorkflow(directory or RUNS/mode,mode,experiment=config)
    workflow.prepare(runtime);import_common(workflow,bundle)
    return workflow


def verify(names=None):
    names=names or ['tests.test_stage356_milestone2','tests.test_stage355_working_state','tests.test_stage354_references']
    EXPORT.mkdir(parents=True,exist_ok=True);stream=io.StringIO();started=time.monotonic()
    with ExitStack() as guards:
        for target in ('tools.model_transports.deepseek.request_completion','extensions.tendon_family.backends.MujocoBackend.run',
                'extensions.tendon_family.gvs_trajectory.TrajectoryWorkspace.solve'):
            guards.enter_context(patch(target,side_effect=AssertionError('OFFLINE_FORBIDS_EXECUTION: '+target)))
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    path=EXPORT/('focused_checks.json' if names==['tests.test_stage356_milestone2','tests.test_stage355_working_state','tests.test_stage354_references'] else 'affected_checks.json')
    if path.exists():path=path.with_name(path.stem+'_'+str(time.time_ns())+'.json')
    record=dict(passed=result.wasSuccessful(),tests_run=result.testsRun,command=[sys.executable,'examples/stage356_milestone2.py','verify',*names],
        elapsed_s=time.monotonic()-started,output=stream.getvalue(),implementation=implementation(),new_paid_requests=0,new_backend_simulations=0)
    atomic_json(path,record);print(record['output'],flush=True)
    if not result.wasSuccessful():raise ValueError('FOCUSED_CHECKS_FAILED')
    atomic_json(EXPORT/'verification_current.json',record)


def acceptance(workflow,outcome):
    from tools.diagnostic_handoff import consume_handoff
    chain=outcome['chain'];required=['initial_report','initial_response','check','feedback','revised_report','revised_handoff','search_plan','final_response']
    gates={k:k in chain for k in required};gates['completed']=outcome['status']=='completed'
    if all(gates.values()):
        check=accepted_product(workflow.store,chain['check'],'diagnostic_check');feedback=workflow.store.artifact(chain['feedback'])
        revision=accepted_product(workflow.store,chain['revised_report'],'diagnosis_report');plan=accepted_product(workflow.store,chain['search_plan'],'search_batch_plan')
        accepted_product(workflow.store,chain['final_response'],'design_response')
        gates.update(recorded_before_result=True,completed_check=feedback['receipt']['execution_status']=='completed',
            exact_revision_lineage=revision['previous_report']==chain['initial_report'] and revision['check_results']==[chain['feedback']],
            valid_plan=plan['structurally_operationally_valid'],future_execution_unauthorized=not plan['execution_authorized'])
        with closing(workflow.store.connect(True)) as db:
            events=[json.loads(r[0]) for r in db.execute('SELECT body FROM events')]
            interpreted=[e for e in events if e['kind']=='assessment_revision']
        proposal_sequence=next(e['sequence'] for e in events if e['kind']=='role_transition' and e['status']=='diagnostic_check' and chain['check'] in e['outputs'])
        result_sequence=next(e['sequence'] for e in events if e['execution_id']==feedback['receipt']['execution_id'] and e['status']=='reserved')
        gates['recorded_before_result']=proposal_sequence<result_sequence
        gates['new_information_interpreted']=bool(interpreted and workflow.store.artifact(interpreted[-1]['outputs'][0])['new_information'])
    used=outcome['usage']['used'];limit=outcome['usage']['limit'];work=outcome['numerical_work']
    gates['within_limits']=all(v<=limit[k]+1e-6 for k,v in used.items()) and all(v<=work['limits'][k] for k,v in work['used'].items())
    gates['no_backend_or_workers']=used['backend_solves']==used['worker_calls']==0
    gate=dict(passed=all(gates.values()),gates=gates,semantic_assessment='Review model questions, relationships, interpretation and promise separately; host gates do not prove causality.')
    atomic_json(EXPORT/workflow.mode/'acceptance.json',gate)
    return gate


def live(mode):
    checked=read(EXPORT/'verification_current.json')
    if not checked['passed'] or checked['implementation']['files']!=implementation()['files']:raise ValueError('CURRENT_FOCUSED_VERIFICATION_REQUIRED')
    if subprocess.check_output(['git','diff','HEAD','--',*implementation()['files']],cwd=ROOT,text=True):raise ValueError('COMMIT_IMPLEMENTATION_BEFORE_PAID_VALIDATION')
    bundle=scientific_bundle();path=EXPORT/'common_input_freeze.json'
    if path.exists():
        if read(path)!=dict(scientific_input=bundle,implementation=implementation()):raise ValueError('COMMON_FREEZE_CHANGED')
    else:atomic_json(path,dict(scientific_input=bundle,implementation=implementation()))
    if (RUNS/mode).exists():raise ValueError('PRESERVE_PRIOR_RUN: no replacement workflow')
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path.home()/'.codex/.env')
    # Existing permitted direct route: remove only the known injected dead proxy,
    # keeping provider identity, certificate verification and other network setup.
    removed=[]
    for name in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
        if '127.0.0.1:9' in os.environ.get(name,''):os.environ.pop(name);removed.append(name)
    workflow=prepare(mode)
    atomic_json(workflow.directory/'transport_configuration.json',dict(removed_dead_proxy_variable_names=removed,tls_verification=True,provider='https://api.deepseek.com',paid_preflight=False))
    outcome=workflow.run();gate=acceptance(workflow,outcome)
    atomic_json(EXPORT/mode/'sha256_manifest.json',{p.relative_to(EXPORT/mode).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((EXPORT/mode).rglob('*.json')) if p.name!='sha256_manifest.json'})
    print('MILESTONE2',mode,gate['passed'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['verify','single_context','dual_context']);parser.add_argument('tests',nargs='*');args=parser.parse_args()
    if args.action=='verify':verify(args.tests or None)
    else:live(args.action)
