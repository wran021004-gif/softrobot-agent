"""Interpret existing stopped evidence under the original grant; never resume physics."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
import json
import os
import time
from copy import deepcopy
from examples.stage357_live_pilot import PilotWorkflow,RUN,EVIDENCE,CONFIRM,HISTORY,BASELINE
from tools.diagnostic_workflow import implementation,save
from tools.platform_host import Host
from tools.state_io import read,atomic_json
from tools.platform_store import plain
from tools.platform_search import offline_batch_result,_save_batch
from tools.diagnostic_facts import handover
from extensions.tendon_family.gvs_profile import execution_scope
from tools.improvement_workflow import archive_store
from examples.gvs_nmpc_route_experiment import load_credential

freeze=read(RUN/'freeze.json')
if implementation()!=freeze['implementation']:raise ValueError('FROZEN_IMPLEMENTATION_CHANGED')
guard=RUN/'stopped_interpretation_attempt.json'
if guard.exists():raise ValueError('INTERPRETATION_ALREADY_ATTEMPTED_NO_REPLACEMENT')
w=PilotWorkflow(RUN,'single_context',experiment=freeze['experiment'])
w.freeze=freeze;w.project=freeze['project_id'];w.hosts={k:Host(RUN,v) for k,v in freeze['hosts'].items()}
for key in ('binding','identities','summary','inventory'):
    setattr(w,key,freeze[key])
w.inventory_ref=freeze['inventory_reference'];w.common=freeze['common_scientific_input'];w.source_record=freeze['source_record']
w.historical_feedback=w.store.artifact(w.common['feedback']);w.eligibility=freeze['numerical_eligibility']
w.limits=freeze['limits'];w.chain=read(RUN/'chain.json');w.previous=w.host('design');w.validate_frozen_configuration()
host=w.host('design');batch=w.store.session(host.run_id)['state']['search_batch'];pending=batch['pending']
if pending is None:raise ValueError('STOPPED_PENDING_EXECUTION_REQUIRED')
effective=w.store.artifact(pending['configuration'])['effective']
baseline=w.store.artifact(batch['retained_baseline']['configuration'])['effective']
if execution_scope(effective)!=execution_scope(baseline):raise ValueError('BASELINE_DUPLICATE_NOT_DEMONSTRATED')
child=Host(RUN,pending['candidate_id']);call=child.store.lookup(child.run_id,'complete-simulation')
if not call or call['receipt']:raise ValueError('EXPECTED_UNSEALED_INTERRUPTED_ATTEMPT')
child.store.mark_unknown(child.run_id,'complete-simulation')
row=batch['configurations'][pending['identity']]
row['stages']['simulation']=dict(execution_status='unknown',request_id='complete-simulation',execution_id=call['execution_id'],
    charged=json.loads(call['charged']),output=None,reason='Stopped after detecting a retained-baseline proposal that should have reused historical evidence; no automatic replay.')
batch['stop_reason']='material_scheduler_failure_retained_baseline_reexecution';_save_batch(host,batch)
result=offline_batch_result(host)
result['unresolved_issues']=['Retained-baseline reuse was missing from the scheduler cache. A second backend attempt started on an already retained baseline and was interrupted.',
    'Second attempt has no sealed simulation result or official evaluation/profile. Its original reservation/charge remains, and it contributes zero complete new configurations.',
    'Only one changed configuration has complete results; the two-candidate pilot target is unmet. No further backend work is allowed in this stopped pilot.']
ref=save(w.store,result);w.chain['batch_result']=ref;atomic_json(RUN/'batch_result.json',result)
atomic_json(RUN/'scheduler_failure.json',dict(reason=batch['stop_reason'],candidate=pending,
    retained_baseline=batch['retained_baseline']['candidate'],exact_execution_scope_equal=True,stopped_attempt=call['execution_id'],
    receipt_sealed=False,retained_reservation=json.loads(call['reserved']),backend_attempt_count=w.store.remaining()['used']['backend_solves']))
handover(host,ref,result,origin=dict(kind='stopped_live_batch_sealed_first_result_unresolved_second_attempt'),kind='batch_result')
load_credential(Path.home()/'.codex/.env')
for name in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
    if '127.0.0.1:9' in os.environ.get(name,''):os.environ.pop(name)
atomic_json(guard,dict(original_grant=w.store.config(),usage_before=w.store.remaining(),implementation=implementation(),physics_replay=False))
started=time.monotonic();reason=batch['stop_reason']
try:
    w.phase('response_final','design_response','final_response',batch_result=result,experiment_plan=w.chain['search_plan'],
        improvement_feedback_content=dict(baseline_facts=w.historical_feedback['baseline_facts'],execution=None),
        check_feedback=[dict(reference=ref)],source_report=w.common['source_report'],source_record=w.source_record,
        required_gate='Pilot incomplete: interpret the one complete changed candidate and unresolved second baseline attempt. Never claim two fully evaluated new candidates. No further physics or batch is authorized.')
except Exception as exc:
    reason+='; final interpretation failed: '+str(exc)
    atomic_json(RUN/'interpretation_failure.json',dict(message=str(exc)))
w.export('incomplete',reason,time.time()-(RUN/'live_attempt.json').stat().st_mtime)
outcome=read(RUN/'outcome.json');outcome.update(elapsed_scope='Wall time since original live-attempt guard file creation, including stopped recovery; not charged computation.',
    interpretation_recovery_elapsed_s=time.monotonic()-started,original_grant_preserved=True,physics_replay=False)
atomic_json(RUN/'outcome.json',outcome);atomic_json(EVIDENCE/'single_context/outcome.json',outcome)
archive_store(w.store,EVIDENCE/'single_context',source_stores=[CONFIRM,HISTORY,BASELINE])
atomic_json(EVIDENCE/'acceptance.json',dict(passed=False,stop_reason=reason,model_decision_present='final_response' in w.chain,
    fully_evaluated_distinct_changed_configurations=1,original_grant_preserved=True,unknown_attempt_replayed=False))
print('STOPPED_PILOT_FINAL_DECISION','final_response' in w.chain,flush=True)
