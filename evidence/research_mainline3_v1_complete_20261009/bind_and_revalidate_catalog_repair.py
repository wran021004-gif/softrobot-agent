"""Explicit same-grant code migration and saved-response revalidation; no provider."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime
import json,subprocess,time
from tools import research_v1_continue as activity
from tools.platform_store import Store,zero,plain,encode
from tools.platform_host import Host
from tools.research_investigations import InvestigationDispatcher,InvestigationOrder
from tools.research_single_validation import stop,sha
from tools.research_validation_activity import export
from tools.state_io import read,atomic_json,digest

activity.OUT=(Path.cwd()/'evidence/research_mainline3_v1_complete_20261009').resolve()
out=activity.OUT;m=read(out/'validation_manifest.json');p=m['phases']['coordinated']
s=Store(activity.ROOT/p['output']);oldrun=p['active_run_id'];old=s.session(oldrun)
assert old['status']=='stopped' and m['implementation_repairs_used']==1
key='principal-coordinated-v2';prior=old['state']['investigations'][key]
wire=read(out/'principal_capacity_repaired_wire.json')
sent=json.loads(wire['messages'][1]['content'])['fact_catalog']['reference']
a=s.artifact(sent);b=s.artifact(prior['fact_catalog'])
assert {k:v for k,v in a.items() if k!='activity_run_id'}=={k:v for k,v in b.items() if k!='activity_run_id'}
# The immutable provider-attempt record proves what this model actually received.
attempts=[e for e in s.events(oldrun) if e['kind']=='investigation_provider_attempt' and e['request_id']==prior['active_request_id']]
actual_wire=s.artifact(attempts[-1]['outputs'][0])['payload']
assert json.loads(actual_wire['messages'][1]['content'])['fact_catalog']['reference']==sent
atomic_json(out/'validation_manifest_before_repair2.json',m)
newrun='mainline3-coordinated-catalog-repair2';cfg=deepcopy(old['snapshot']['input']);cfg['run_id']=newrun
h=Host(s.root,newrun);h.create(cfg);h.resume();state=deepcopy(old['state'])
for node in state['investigations'].values():node.setdefault('request_run_id',oldrun)
state['repair_binding']=dict(original_run=oldrun,kind='explicit_code_revision_same_activity_grant',new_node_capacity=0,counters_and_node_deadlines_preserved=True)
n=state['investigations'][key];n.update(fact_catalog=sent,catalog_origin_run_id=a['activity_run_id'],status='running')
with s.transaction() as db:s.update_state(db,newrun,state)
revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
m['code_identity']['tools/research_investigations.py']=sha(activity.ROOT/'tools/research_investigations.py')
m.update(code_commit=revision,implementation_repairs_used=2);m['phases']['coordinated']['active_run_id']=newrun
repair=dict(repair=2,defect='prepare regenerated catalog under migration run while resume payload retained original sent catalog; only activity_run_id differed',same_defect_cycle=1,code_revision=revision,provider_requests=0,checks=['Two affected unittest checks passed: restoration binding and public principal source/scope/disposition validation','principal_catalog_local_revalidation.json'],original_stopped_run=oldrun,new_run=newrun,new_grant_or_node_capacity=0,counters_and_node_deadlines_preserved=True,scientific_model_output_unchanged=True)
m.setdefault('repairs',[]).append(repair);atomic_json(out/'repair2.json',repair);atomic_json(out/'validation_manifest.json',m)
activity.check()
d=InvestigationDispatcher(h);order=InvestigationOrder.model_validate(n['order']);start=time.monotonic()
raw=s.artifact(n['provider_response_refs'][-1]);raw_identity=digest(raw)
result=dict(provider_requests=0,source_response=n['provider_response_refs'][-1],actual_sent_catalog=sent,discarded_regenerated_catalog=prior['fact_catalog'],catalog_content_and_report_bindings_identical=True,original_call_category_unchanged=prior['requests_by_purpose'],host_stale_catalog_feedback_was_incorrect=True,unsent_scheduled_correction_not_a_provider_request=True,model_output_unchanged=True)
try:
 retained=deepcopy(n)
 d.prepare(order,executing=True,reuse_saved_reads=True)
 d._bind_resume_catalog(order,actual_wire,retained)
 report=d._decode(raw);atomic_json(out/'principal_last_expanded_return.json',plain(report))
 result['expansion']='pass'
 d._validate_return(order,report,n['reads'])
 result['formal_validation']='pass'
 # Do not publish an adopted claim until the independent semantic material audit passes.
except Exception as exc:
 result.update(formal_validation='fail',exception_type=type(exc).__name__,business_error=str(exc),issue=getattr(exc,'issue',None))
finally:
 assert digest(s.artifact(n['provider_response_refs'][-1]))==raw_identity
 atomic_json(out/'principal_catalog_local_revalidation.json',result)
 with s.transaction() as db:
  current=s.session(newrun,db)['state'];current['investigations'][key].update(status='failed',local_revalidation=plain(s.put(db,result)));s.update_state(db,newrun,current)
 failure=s.artifact(prior['failure_record']);began=datetime.fromisoformat(failure['timestamp']).timestamp();elapsed=max(0,time.time()-began)
 cost={**zero(),'wall_s':elapsed};row,fresh=s.reserve(newrun,'engineering-repair2',digest(repair),'coding-agent-repair',cost,kind='engineering_repair')
 if fresh:s.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],tool_id='engineering.repair',tool_version='1.0.0',execution_status='completed',caller='coding-agent-repair',charged=zero(),cache_hit=False),repair,elapsed=elapsed,actual_cost=cost,kind='engineering_repair')
 atomic_json(out/'repair2_accounting.json',dict(wall_s=elapsed,method='Full interval since latest local capacity failure, including diagnosis, focused checks, review, commit and local replay; no old requests or reservations refunded',ledger=s.remaining()))
 stop(h,'Saved principal output revalidated locally after catalog repair; missing reach report blocks B and C. No new provider request.')
 export(out,'coordinated',run_id=newrun)
print(json.dumps(result,ensure_ascii=True))
