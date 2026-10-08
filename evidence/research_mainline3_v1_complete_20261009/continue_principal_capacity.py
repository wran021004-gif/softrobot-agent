from pathlib import Path
import time
from tools import research_v1_continue as activity
from tools.platform_store import plain
from tools.research_investigations import InvestigationDispatcher,InvestigationOrder
from tools.research_execution import invoke
from tools.research_single_validation import stop
from tools.research_validation_activity import export
from tools.state_io import read,atomic_json,digest
activity.OUT=(Path.cwd()/'evidence/research_mainline3_v1_complete_20261009').resolve();host,m,p=activity.host_for('coordinated');s=host.store;key='principal-coordinated-v2';n=s.session(host.run_id)['state']['investigations'][key];order=InvestigationOrder.model_validate(n['order']);assert n['next_request_purpose']=='model_correction' and n['requests_by_purpose']['model_correction']==0
remaining=order.timeout_s-(time.time()-n['started_unix']);assert remaining>0
request='investigation-'+key+'-capacity-continuation1';reservation={k:v-n['usage'][k] for k,v in plain(order.budget).items()};reservation['wall_s']=remaining
with s.transaction() as db:
 state=s.session(host.run_id,db)['state'];state['investigations'][key].update(status='pending',active_request_id=request,request_run_id=host.run_id);s.update_state(db,host.run_id,state)
 s.event(db,host.run_id,'investigation_local_capacity_continuation','authorized',request=request,outputs=[s.put(db,dict(prior_failed_request='investigation-principal-coordinated-v2-engineering-1',next_provider_purpose='model_correction',local_prepare_provider_requests=0,counters_unchanged=True,same_node_deadline=n['started_unix']+order.timeout_s))])
row,fresh=s.reserve(host.run_id,request,digest(dict(repair=1,wire=read(activity.OUT/'principal_capacity_repaired_wire.json'))),'investigation-dispatcher',reservation,kind='investigation');assert fresh
from examples.gvs_nmpc_route_experiment import load_credential
load_credential(Path.home()/'.codex/.env')
from tools.workbench import owner
try:
 with owner(host.folder,'.investigation-'+key+'.lock'):
  InvestigationDispatcher(host)._execute(order,row,reuse_saved_reads=True,resume_payload=read(activity.OUT/'principal_capacity_repaired_wire.json'))
 result=activity.collect(host,key)
 timing=read(activity.OUT/'independent_timing_result.json')['report']
 atomic_json(activity.OUT/'partial_principal_result.json',dict(report=result,targets=[dict(investigation_id='timing-integrity-limits',report=timing)],coordinator_synthesis=None,B_passed=False,missing_gate='Valid new reach report and two-report synthesis/disposition chain',code_commit=m['code_commit']))
finally:
 stop(host,'Partial disposition continuation terminal; full B and C missing reach-report gate remains unchanged')
 export(activity.OUT,'coordinated',run_id=host.run_id)
