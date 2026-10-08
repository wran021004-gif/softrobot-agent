from pathlib import Path
from tools import research_v1_continue as activity
from tools.research_investigations import InvestigationDispatcher
from tools.research_execution import invoke
from tools.research_single_validation import stop
from tools.research_validation_activity import export
from tools.state_io import atomic_json,read
activity.OUT=(Path.cwd()/'evidence/research_mainline3_v1_complete_20261009').resolve();host,m,p=activity.host_for('coordinated');store=host.store;key='principal-coordinated-v2'
node=store.session(host.run_id)['state']['investigations'][key];row=store.lookup(host.run_id,'investigation-'+key);f=store.artifact(node['failure_record'])
if f['cause_exception_type']!='IncompleteRead' or f['details']['http_status']!=200 or f['progress']['transport_callable_invocations']!=1 or node.get('original_body_refs'):raise ValueError('CONFIRMED_NEW_INCOMPLETE_RECEPTION_REQUIRED')
if row['receipt']:raise ValueError('RECONCILIATION_ALREADY_EXECUTED')
# Settle known local invocation/read/time facts. Token/currency charges stay
# unknown; this changes no historical reservation and refunds no actual call.
d=InvestigationDispatcher(host)
receipt=store.complete(row,d._receipt(row,'failed','CONFIRMED_INCOMPLETE_RESPONSE_READ'),elapsed=f['elapsed_s'],actual_cost=node['usage'],kind='investigation')
atomic_json(activity.OUT/'principal_transport_reconciliation.json',dict(original_request=row['request_id'],original_execution=row['execution_id'],failure=node['failure_record'],receipt=receipt,
 actual_provider_invocations=1,provider_tokens='unknown',monetary_charge='unknown',complete_body_available=False,old_reservations_untouched=True,reason='HTTP 200 followed by IncompleteRead; request terminated, no pending output.'))
host.resume()
with store.transaction() as db:
 state=store.session(host.run_id,db)['state'];state['investigations'][key]['submission_phase']='report_delivery';store.update_state(db,host.run_id,state)
from examples.gvs_nmpc_route_experiment import load_credential
load_credential(Path.home()/'.codex/.env')
attempt=[e for e in store.events(host.run_id) if e['kind']=='investigation_provider_attempt' and e['request_id']==row['request_id']][-1]
payload=store.artifact(attempt['outputs'][0])['payload']
try:
 result=d.engineering_recovery(key,'Confirmed new HTTP 200 IncompleteRead irrecoverably lost the response; explicit one-time replacement formal submission, original invocation remains ordinary',resume_payload=payload)
 if result.status!='completed':raise ValueError('PRINCIPAL_REPLACEMENT_NOT_COMPLETE: '+str(result.reason))
 r=invoke(host,'research.investigation_status',dict(investigation_id=key),request_id='collect-principal-engineering-replacement')
 if r['execution_status']!='completed':raise ValueError('PUBLIC_REPLACEMENT_COLLECTION_FAILED')
 timing=read(activity.OUT/'independent_timing_result.json')['report']
 atomic_json(activity.OUT/'partial_principal_result.json',dict(report=result.result.model_dump(mode='json'),targets=[dict(investigation_id='timing-integrity-limits',report=timing)],collection_receipt=r,coordinator_synthesis=None,B_passed=False,missing_gate='Valid new reach report and two-report synthesis/disposition chain'))
finally:
 stop(host,'Available partial principal replacement terminal; full B and C remain blocked by absent reach report')
 export(activity.OUT,'coordinated')
