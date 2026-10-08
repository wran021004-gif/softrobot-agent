from pathlib import Path
from copy import deepcopy
from datetime import datetime
import subprocess,time
from tools import research_v1_continue as activity
from tools.platform_store import Store,zero
from tools.platform_host import Host
from tools.state_io import read,atomic_json,digest
from tools.research_single_validation import sha
activity.OUT=(Path.cwd()/'evidence/research_mainline3_v1_complete_20261009').resolve();out=activity.OUT;m=read(out/'validation_manifest.json');p=m['phases']['coordinated'];s=Store(activity.ROOT/p['output']);oldrun='mainline3-coordinated';old=s.session(oldrun)
assert old['status']=='stopped' and m['implementation_repairs_used']==0
newrun='mainline3-coordinated-capacity-repair1';cfg=deepcopy(old['snapshot']['input']);cfg['run_id']=newrun;h=Host(s.root,newrun);h.create(cfg);h.resume();state=deepcopy(old['state']);state['original_stopped_run']=oldrun
for n in state['investigations'].values():n.setdefault('request_run_id',oldrun)
state['repair_binding']=dict(original_run=oldrun,kind='explicit_code_revision_same_activity_grant',new_node_capacity=0,counters_and_node_deadlines_preserved=True)
with s.transaction() as db:s.update_state(db,newrun,state)
revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();atomic_json(out/'validation_manifest_before_repair1.json',m);m['code_identity']['tools/research_investigations.py']=sha(activity.ROOT/'tools/research_investigations.py');m['code_commit']=revision;m['implementation_repairs_used']=1;m['phases']['coordinated']['active_run_id']=newrun
record=dict(repair=1,defect='Correction wire duplicated 14KB historical Host execution metadata; complete request overflowed before provider call',code_revision=revision,affected_paths=['tools/research_investigations.py'],checks=['repair1_saved_wire_check.json','repair1_affected_checks.log'],same_defect_cycle=1,original_activity_deadline_unchanged=True,request_and_category_counters_unchanged=True,original_stopped_run=oldrun,new_run=newrun,new_grant_or_node_capacity=0,model_history_and_scientific_evidence_unchanged=True)
m.setdefault('repairs',[]).append(record);atomic_json(out/'repair1.json',record);atomic_json(out/'validation_manifest.json',m)
f=s.artifact(state['investigations']['principal-coordinated-v2']['failure_record']);began=datetime.fromisoformat(f['timestamp']).timestamp();elapsed=max(0,time.time()-began);cost={**zero(),'wall_s':elapsed};r,fresh=s.reserve(newrun,'engineering-repair1',digest(record),'coding-agent-repair',cost,kind='engineering_repair')
if fresh:s.complete(r,dict(request_id=r['request_id'],execution_id=r['execution_id'],tool_id='engineering.repair',tool_version='1.0.0',execution_status='completed',caller='coding-agent-repair',charged=zero(),cache_hit=False),record,elapsed=elapsed,actual_cost=cost,kind='engineering_repair')
atomic_json(out/'repair1_accounting.json',dict(wall_s=elapsed,method='Conservative full interval since new activity local capacity failure, including diagnosis, review, pauses, focused checks and commit; not claimed as pure coding measured time',ledger=s.remaining()))
activity.check();print(dict(code_revision=revision,active_run=newrun,repair_wall_s=elapsed))
