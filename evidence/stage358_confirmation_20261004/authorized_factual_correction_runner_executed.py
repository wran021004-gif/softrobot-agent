"""One source-bound interpretation correction in the existing Stage 3.58 ledger."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from examples.stage358_confirmation import ConfirmationWorkflow, RUN, EVIDENCE, SOURCES
from examples import stage357_live_pilot as prior
from tools.platform_store import Store, plain
from tools.platform_host import Host
from tools.platform_diagnosis_coordinator import run_until_handoff
from tools.diagnostic_facts import handover
from tools.diagnostic_workflow import implementation, save
from tools.improvement_workflow import archive_store
from tools.state_io import read, atomic_json

guard = RUN / 'factual_correction_attempt.json'
if guard.exists():
    raise ValueError('ONE_FACTUAL_CORRECTION_ATTEMPT_ALREADY_RECORDED')
freeze = read(RUN / 'freeze.json')
if implementation()['files'] != freeze['implementation']['files']:
    raise ValueError('FROZEN_IMPLEMENTATION_CHANGED')
workflow = ConfirmationWorkflow(RUN, 'single_context', experiment=freeze['experiment'])
workflow.freeze = freeze
workflow.chain = read(RUN / 'chain.json')
workflow.historical_results = freeze['historical_results']
workflow.hosts = {}
with workflow.store.connect(True) as db:
    for row in db.execute('SELECT run_id,state FROM sessions'):
        state = json.loads(row['state'])
        if state.get('role_context', {}).get('require_research_route'):
            workflow.hosts['shared'] = Host(RUN, row['run_id'])
        elif row['run_id'].endswith('-executor'):
            workflow.hosts['executor'] = Host(RUN, row['run_id'])
host = workflow.host('design')
state = workflow.store.session(host.run_id)['state']
phase_before = state['role_context']['phase_budget']
before = workflow.store.remaining()
original = workflow.chain['final_response']
request = read(EVIDENCE / 'factual_correction_request.json')
if request['original_response_reference'] != original or request['source_batch_summary'] != workflow.chain['batch_summary']:
    raise ValueError('REVIEWED_CORRECTION_PAYLOAD_BINDING_CHANGED')
if request['project_usage_before']['used'] != before['used']:
    raise ValueError('REVIEWED_CORRECTION_ACCOUNTING_CHANGED')
ref = save(workflow.store, request)
supplement = read(EVIDENCE / 'factual_correction_supplement.json')
supplement_ref = save(workflow.store, supplement)
atomic_json(guard,dict(request=ref,original=original,used_before=before['used'],phase_budget_preserved=phase_before,runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
for filename in ('final_response.json','outcome.json'):
    for directory in (RUN,EVIDENCE/'single_context'):
        path=directory/filename
        preserved=directory/(Path(filename).stem+'_before_factual_correction.json')
        if preserved.exists():raise ValueError('PRESERVE_CORRECTION_ORIGINAL')
        preserved.write_bytes(path.read_bytes())
acceptance=EVIDENCE/'acceptance.json'
(EVIDENCE/'acceptance_before_factual_correction.json').write_bytes(acceptance.read_bytes())
handover(host,ref,request,origin=dict(kind='exact_source_bound_factual_contradictions'),kind='bounded_factual_correction')
handover(host,supplement_ref,supplement,origin=dict(kind='user_required_research_conditions',request=ref),kind='factual_correction_supplement')
with workflow.store.transaction() as db:
    state=workflow.store.session(host.run_id,db)['state']
    state['role_context']['factual_correction']=ref
    state['role_context']['factual_correction_supplement']=supplement_ref
    state['role_context']['instructions']+=' One bounded factual correction is now required. Read bounded_factual_correction in current evidence and correct all exact contradictions there AND every additional_required_correction in factual_correction_supplement; return one full design.respond_diagnosis response. Execute no experiments or extra retained-data checks. Existing project budget, original phase started_usage and all protocol counters remain in force.'
    workflow.store.update_state(db,host.run_id,state)
    workflow.store.event(db,host.run_id,'role_context','bounded_factual_correction',inputs=[ref,original],outputs=[workflow.store.put(db,state['role_context'])])
assert workflow.store.session(host.run_id)['state']['role_context']['phase_budget']==phase_before
from examples.gvs_nmpc_route_experiment import load_credential
load_credential(Path.home()/'.codex/.env')
for name in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
    if '127.0.0.1:9' in os.environ.get(name,''):os.environ.pop(name)
started=time.monotonic()
try:
    corrected=run_until_handoff(host,'design_response')
    workflow.chain['final_response']=corrected
    atomic_json(RUN/'final_response.json',workflow.store.artifact(corrected))
    atomic_json(RUN/'chain.json',workflow.chain)
    with workflow.store.transaction() as db:
        state=workflow.store.session(host.run_id,db)['state']
        state['workflow_memory'].append(dict(phase='bounded_factual_correction',reference=corrected))
        workflow.store.update_state(db,host.run_id,state)
    atomic_json(EVIDENCE/'factual_correction_result.json',dict(status='model_response_received_requires_factual_review',request=ref,original=original,corrected=corrected,semantic_cycles=1,provider_attempts=workflow.store.remaining()['used']['model_calls']-before['used']['model_calls'],supplement=supplement_ref,used_before=before['used'],used_after=workflow.store.remaining()['used'],phase_budget_preserved=phase_before,elapsed_s=time.monotonic()-started))
    status='completed';reason='pilot_target_complete'
except Exception as exc:
    status='incomplete';reason='BOUNDED_FACTUAL_CORRECTION_FAILED: '+str(exc)
    atomic_json(EVIDENCE/'factual_correction_result.json',dict(status='failed',request=ref,original=original,error=reason,semantic_cycles=1,provider_attempts=workflow.store.remaining()['used']['model_calls']-before['used']['model_calls'],supplement=supplement_ref,used_after=workflow.store.remaining()['used']))
workflow.export(status,reason,read(RUN/'outcome_before_factual_correction.json')['elapsed_s']+time.monotonic()-started)
archive_store(workflow.store,EVIDENCE/'single_context',source_stores=[prior.CONFIRM,*[path for _,path,_ in SOURCES]])
atomic_json(EVIDENCE/'acceptance.json',dict(passed=status=='completed',stop_reason=reason,current_model_plan_present=True,model_consumed_batch=True,target=2,completed_new_configurations=2,implementation=implementation(),offline_verification=str(EVIDENCE/'verification_current.json'),factual_correction='factual_correction_result.json',semantic_review_pending=True))
print('BOUNDED CORRECTION',status,reason,flush=True)
