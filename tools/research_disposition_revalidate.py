"""Revalidate an unchanged, received model decision after expansion-only repair.

No provider call, manual report edit, new conclusion or logical-clock reset.
"""
from copy import deepcopy
import subprocess,time
from tools.state_io import read,atomic_json,digest
from tools.platform_store import Store,plain,zero,now
from tools.platform_host import Host
from tools.research_v1_resume import ROOT,history
from tools.research_single_validation import sha,stop
from tools.research_validation_activity import export
from tools.research_execution import invoke
from tools.research_investigations import InvestigationDispatcher,InvestigationOrder


def main():
    out=ROOT/'evidence/research_disposition_facts_20261008/stages'
    manifest=read(out/'validation_manifest.json');stage=manifest['phases']['reuse'];store=Store(ROOT/stage['output'])
    parent='mainline3-reuse-repair1';run_id='mainline3-reuse-repair2';key='principal-historical-disposition'
    if (out/'repair2_launch.json').exists():raise ValueError('NO_REPEATED_LOCAL_REVALIDATION')
    old=store.session(parent);node=old['state']['investigations'][key]
    if old['status']!='stopped' or node['status']!='failed':raise ValueError('SEALED_LOCAL_FAILURE_REQUIRED')
    with store.connect(True) as db:
        if db.execute("SELECT COUNT(*) FROM calls WHERE status IN ('running','unknown')").fetchone()[0]:raise ValueError('DRAIN_ALL_OPERATIONS_FIRST')
    remaining=node['order']['timeout_s']-(time.time()-node['started_unix'])
    if remaining<=0:raise ValueError('ORIGINAL_LOGICAL_NODE_EXPIRED')
    bundle=read(out/'reuse_bundle.json');last=[e for e in bundle['events'] if e['kind']=='investigation_provider_response'][-1]
    raw=bundle['artifacts'][last['outputs'][0]['artifact_id']]
    if raw['choices'][0]['finish_reason']!='tool_calls' or raw['choices'][0]['message']['tool_calls'][0]['function']['name']!='investigation_return':raise ValueError('RECEIVED_NATIVE_DECISION_REQUIRED')
    cfg=read(out/'frozen_configuration.json');cfg['run_id']=run_id
    cfg['policy'].update(route=None,budget=stage['project_budget'],allowed_tools=list(stage['tool_bindings']),tool_bindings=stage['tool_bindings'],
        timeout_s=stage['project_budget']['wall_s'],operation_allowances=stage['operation_allowances'])
    atomic_json(out/'validation_manifest_before_repair2.json',manifest);atomic_json(out/'reuse_bundle_before_repair2.json',bundle)
    manifest['implementation_repairs_used']+=1
    if manifest['implementation_repairs_used']>manifest['implementation_repair_ceiling']:raise ValueError('REPAIR_LIMIT')
    prior=manifest['code_commit'];manifest['code_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    manifest['code_identity']={p:sha(ROOT/p) for p in sorted(set(manifest['code_identity'])|{'tools/research_disposition_revalidate.py'})}
    atomic_json(out/'validation_manifest.json',manifest)
    host=Host(store.root,run_id);host.create(cfg,parent_run_id=parent);host.resume()
    state=deepcopy(old['state']);state.pop('stop_reason',None)
    state['investigations'][key].update(status='running',request_run_id=run_id,continuation_of=node['failure_record'],catalog_origin_run_id=parent)
    with store.transaction() as db:store.update_state(db,run_id,state)
    row,fresh=store.reserve(run_id,'investigation-'+key,digest(dict(original_response=last['outputs'][0],repair=2)),
        'investigation-dispatcher',{**zero(),'wall_s':remaining},kind='investigation')
    if not fresh:raise ValueError('NO_REDISPATCH')
    atomic_json(out/'repair2_launch.json',dict(timestamp=now(),same_project=store.config()['project_id'],original_code=prior,new_code=manifest['code_commit'],
        original_node_started_unix=node['started_unix'],remaining_original_clock_s=remaining,original_model_response=last['outputs'][0],
        original_catalog=node['fact_catalog'],logical_usage_before=node['usage'],new_model_requests=0,paid_corrections=0,
        reason='Original native selection fits 65536 bytes; old program repeated provenance caused report overflow. Only immutable provenance serialization is repaired.'))
    began=time.monotonic()
    try:
        dispatcher=InvestigationDispatcher(host);order=InvestigationOrder.model_validate(node['order'])
        report=dispatcher._decode(raw);dispatcher._validate_return(order,report,node['reads'])
        if time.time()-node['started_unix']>=order.timeout_s:raise ValueError('ORIGINAL_LOGICAL_NODE_EXPIRED')
        sealed=store.complete(row,dispatcher._receipt(row,'completed'),plain(report),elapsed=time.monotonic()-began,actual_cost=zero())
        dispatcher._state(key,status='completed',result=sealed['output'],children=[],
            local_revalidation_of=last['outputs'][0],progress=dict(node['progress'],valid_report=True,report_saved=True,settlement_completed=True,total_node_wall_s=time.time()-node['started_unix']))
        decisions=plain(report)['dispositions'];expected={k:n['result'] for k,n in state['historical_investigations'].items()}
        if len(decisions)!=2 or {d['investigation_id'] for d in decisions}!=set(expected):raise ValueError('TWO_MODEL_DISPOSITIONS_REQUIRED')
        rows=[]
        for d in decisions:
            if d['report']!=expected[d['investigation_id']]:raise ValueError('MODEL_REPORT_BINDING_MISMATCH')
            rows.append(invoke(host,'research.investigation_disposition',d,request_id='dispose-'+d['investigation_id']))
        atomic_json(out/'reuse_result.json',dict(status='formal_dispositions_recorded' if all(r['execution_status']=='completed' for r in rows) else 'failed',receipts=rows))
    except Exception:
        if not store.lookup(run_id,row['request_id'])['receipt']:
            store.complete(row,dict(**dispatcher._receipt(row,'failed'),error='LOCAL_REVALIDATION_FAILED'),elapsed=time.monotonic()-began,actual_cost=zero())
        raise
    finally:
        stop(host,'LOCAL_REVALIDATION_TERMINAL; received decision unchanged; no provider call')
        export(out,'reuse',run_id=run_id);b=read(out/'reuse_bundle.json');b['session_status']='stopped';atomic_json(out/'reuse_bundle.json',b)
        atomic_json(out/'reuse_repair2_lifecycle.json',dict(timestamp=now(),application_wall_s=time.monotonic()-began,all_submitted_nodes_drained=True,new_model_requests=0))
        atomic_json(out/'historical_after.json',dict(unchanged=history()==read(out/'historical_before.json')))


if __name__=='__main__':main()
