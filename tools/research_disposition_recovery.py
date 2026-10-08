"""One confirmed local request-capacity repair; same project/node/clock/usage."""
from copy import deepcopy
from pathlib import Path
import subprocess,time
from tools.state_io import read,atomic_json,digest
from tools.platform_store import Store,plain,zero,now
from tools.platform_host import Host
from tools.research_v1_resume import ROOT,history,collect
from tools.research_single_validation import sha,stop
from tools.research_validation_activity import export
from tools.research_execution import invoke
from tools.research_investigations import InvestigationDispatcher,InvestigationOrder


def main():
    out=ROOT/'evidence/research_disposition_facts_20261008/stages'
    manifest=read(out/'validation_manifest.json');stage=manifest['phases']['reuse'];store=Store(ROOT/stage['output'])
    key='principal-historical-disposition';parent='mainline3-reuse';run_id='mainline3-reuse-repair1'
    if (out/'repair1_launch.json').exists():raise ValueError('NO_REPEATED_REPAIR')
    old=store.session(parent);node=old['state']['investigations'][key]
    if old['status']!='stopped' or node['status']!='failed':raise ValueError('CONFIRMED_STOPPED_LOCAL_FAILURE_REQUIRED')
    if node['progress']['received_responses']!=node['progress']['transport_callable_invocations']:raise ValueError('UNKNOWN_NOT_REPLAYABLE')
    with store.connect(True) as db:
        if db.execute("SELECT COUNT(*) FROM calls WHERE status IN ('running','unknown')").fetchone()[0]:raise ValueError('DRAIN_ALL_OPERATIONS_FIRST')
    remaining=node['order']['timeout_s']-(time.time()-node['started_unix'])
    if remaining<=0:raise ValueError('ORIGINAL_LOGICAL_NODE_EXPIRED')
    bundle=read(out/'reuse_bundle.json');events=[e for e in bundle['events'] if e['kind']=='investigation_provider_response']
    response_ref=events[-1]['outputs'][0];raw=bundle['artifacts'][response_ref['artifact_id']]
    calls=raw['choices'][0]['message'].get('tool_calls',[])
    if raw['choices'][0]['finish_reason']!='tool_calls' or len(calls)!=1 or calls[0]['function']['name']!='evidence_read':raise ValueError('CONFIRMED_EVIDENCE_READ_REQUIRED')
    read_record=node['reads'][-1]
    cfg=read(out/'frozen_configuration.json');cfg['run_id']=run_id
    cfg['policy'].update(route=None,budget=stage['project_budget'],allowed_tools=list(stage['tool_bindings']),tool_bindings=stage['tool_bindings'],
        timeout_s=stage['project_budget']['wall_s'],operation_allowances=stage['operation_allowances'])
    atomic_json(out/'validation_manifest_before_repair1.json',manifest)
    atomic_json(out/'reuse_bundle_before_repair1.json',bundle)
    manifest['implementation_repairs_used']+=1
    if manifest['implementation_repairs_used']>manifest['implementation_repair_ceiling']:raise ValueError('REPAIR_LIMIT')
    previous_code=manifest['code_commit'];manifest['code_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    paths=set(manifest['code_identity'])|{'tools/research_disposition_recovery.py'}
    manifest['code_identity']={p:sha(ROOT/p) for p in sorted(paths)}
    atomic_json(out/'validation_manifest.json',manifest)
    host=Host(store.root,run_id);host.create(cfg,parent_run_id=parent);host.resume()
    state=deepcopy(old['state']);state.pop('stop_reason',None)
    state['investigations'][key].update(status='pending',request_run_id=run_id,continuation_of=node['failure_record'])
    # Backfill only the public reference to the already archived complete body.
    state['investigations'][key]['provider_response_refs']=[e['outputs'][0] for e in events]
    with store.transaction() as db:store.update_state(db,run_id,state)
    reserve={k:node['order']['budget'][k]-node['usage'][k] for k in zero()};reserve['wall_s']=remaining
    row,fresh=store.reserve(run_id,'investigation-'+key,digest(dict(original_execution=node['failure_record'],repair=1)),
        'investigation-dispatcher',reserve,kind='investigation')
    if not fresh:raise ValueError('NO_REDISPATCH')
    atomic_json(out/'repair1_launch.json',dict(timestamp=now(),same_project=store.config()['project_id'],original_code=previous_code,new_code=manifest['code_commit'],
        original_node_started_unix=node['started_unix'],remaining_original_clock_s=remaining,logical_usage_before=node['usage'],reserve=reserve,
        reason='Confirmed local complete-request capacity failure after received read; no transport retry or paid protocol correction.',
        old_responses_and_failed_requests_unchanged=True))
    began=time.monotonic()
    try:
        from examples.gvs_nmpc_route_experiment import load_credential
        load_credential(Path.home()/'.codex/.env')
        dispatcher=InvestigationDispatcher(host);order=InvestigationOrder.model_validate(node['order'])
        # Reuse saved prefetch; present the exact confirmed selected read/result
        # in a new user turn, not the old failed oversized native continuation.
        context=dict(kind='explicit_confirmed_read_recovery',received_native_calls=calls,confirmed_read=read_record,
            prior_response_archive=dict(reference=response_ref,query=dict(reference=response_ref,pointer='/choices/0/message/reasoning_content',offset=0,limit=3000,byte_limit=4096)),
            presentation='Full prior thinking and responses remain immutable and callable; prior reasoning is archive-only. All complete reports, source inspections, supplemental pages, counterevidence and unknowns remain. Original clock, usage and permissions unchanged.')
        dispatcher._execute(order,row,reuse_saved_reads=True,correction_context=context)
        result=invoke(host,'research.investigation_status',dict(investigation_id=key),request_id='collect-repaired-principal')
        returned=store.artifact(result['output'])
        if returned['status']!='completed':atomic_json(out/'reuse_result.json',returned);return
        decisions=store.artifact(returned['result'])['dispositions'];expected={k:n['result'] for k,n in state['historical_investigations'].items()}
        if len(decisions)!=2 or {d['investigation_id'] for d in decisions}!=set(expected):raise ValueError('TWO_MODEL_DISPOSITIONS_REQUIRED')
        rows=[]
        for d in decisions:
            if d['report']!=expected[d['investigation_id']]:raise ValueError('MODEL_REPORT_BINDING_MISMATCH')
            rows.append(invoke(host,'research.investigation_disposition',d,request_id='dispose-'+d['investigation_id']))
        atomic_json(out/'reuse_result.json',dict(status='formal_dispositions_recorded' if all(r['execution_status']=='completed' for r in rows) else 'failed',receipts=rows))
    finally:
        stop(host,'SAME_AUTHORIZED_ACTIVITY_REPAIR_TERMINAL; no original clock/cost reset')
        export(out,'reuse',run_id=run_id);b=read(out/'reuse_bundle.json');b['session_status']='stopped';atomic_json(out/'reuse_bundle.json',b)
        atomic_json(out/'reuse_repair1_lifecycle.json',dict(timestamp=now(),application_wall_s=time.monotonic()-began,all_submitted_nodes_drained=True))
        atomic_json(out/'historical_after.json',dict(unchanged=history()==read(out/'historical_before.json')))


if __name__=='__main__':main()
