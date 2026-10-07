"""Account elapsed review/publication under the original ledger, exactly once.

The remote release explicitly labels its outstanding delivery reservation. The
post-publication closing receipt is local authoritative evidence, not a refund
copied from a report or another grant.
"""
from pathlib import Path
import argparse,json,sys,time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from examples import research_model_v1 as pilot
from tools.platform_store import zero
from tools.state_io import read,atomic_json,digest

D=ROOT/'runs/research_native_development_v3_20261007'
OUT=Path(__file__).resolve().parent

def begin():
    w=pilot.restore(D.resolve());now=time.time()
    with w.store.connect(True) as db:
        pending=[dict(r) for r in db.execute("SELECT run_id,request_id,status FROM calls WHERE receipt IS NULL")]
    if any(r['status']=='running' for r in pending):raise ValueError('LIVE_CALL_STILL_RUNNING')
    auth=read(D/'structural_repair_start.json')['authorization']
    a=read(D/'structural_request_repair_start.json')
    b=read(OUT/'repair_and_plan_resume_boundary.json')
    last=read(D/'structural_repair7_start.json')
    repair5=json.loads(w.store.lookup(w.host.run_id,'structural-historical-read-repair5')['charged'])['wall_s']
    repair6=b['receipt']['charged']['wall_s']
    repair7=json.loads(w.store.lookup(w.host.run_id,'structural-inline-fact-repair7')['charged'])['wall_s']
    used=w.store.remaining()
    end6=a['boundary']['started_unix']+repair6
    span1=last['boundary']['started_unix']-end6
    nested1=last['boundary']['settled_usage']['used']['wall_s']-auth['settled_usage']['used']['wall_s']-repair5-repair6
    end7=last['boundary']['started_unix']+repair7
    span2=now-end7
    nested2=used['used']['wall_s']-last['boundary']['settled_usage']['used']['wall_s']-repair7
    initial=auth['started_unix']-1791346163
    prior=max(0,initial)+max(0,span1-nested1)+max(0,span2-nested2)
    boundary=dict(version='structural-independent-delivery-accounting@1.0.0',started_unix=now,
        goal_created_unix=1791346163,initial_reconciliation_s=max(0,initial),
        between_repair6_and7=dict(start=end6,end=last['boundary']['started_unix'],elapsed_s=span1,
            separately_charged_nested_s=nested1,unaccounted_engineering_s=max(0,span1-nested1)),
        after_repair7=dict(start=end7,end=now,elapsed_s=span2,separately_charged_nested_s=nested2,
            unaccounted_engineering_s=max(0,span2-nested2)),
        prior_unaccounted_s=prior,settled_scientific_usage=used,original_limits=auth['original_limits'],
        original_clock=auth['clock'],incremental_cost_baseline=auth['settled_usage'],unknown_calls_retained=pending,
        new_provider_attempts=0,new_backend_attempts=0,new_numerical_operations=0,new_roles_or_workers=0)
    reservation,_=w.store.reserve(w.host.run_id,'structural-final-independent-review',digest(boundary),'engineering',
        {**zero(),'tool_calls':1,'wall_s':min(1200.,used['remaining']['wall_s'])})
    atomic_json(D/'structural_final_review_start.json',dict(boundary=boundary,reservation=reservation))
    atomic_json(OUT/'publication_inflight_accounting.json',dict(boundary=boundary,reservation=reservation,
        status='Publication snapshot contains an outstanding delivery reservation, not final actual charges. Final closing receipt is in the original local ledger and runs/.../structural_final_settled_costs.json.'))
    print(json.dumps(dict(prior_unaccounted_s=prior,reserved=reservation['reserved'])))

def settle(remote_sha):
    import subprocess
    w=pilot.restore(D.resolve());start=read(D/'structural_final_review_start.json')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if remote_sha!=head:raise ValueError('VERIFIED_REMOTE_SHA_NOT_LOCAL_HEAD')
    if w.store.remaining()['limit']!=start['boundary']['original_limits'] or w.freeze['live_clock']!=start['boundary']['original_clock']:
        raise ValueError('ORIGINAL_GRANT_OR_CLOCK_CHANGED')
    elapsed=time.time()-start['boundary']['started_unix']
    charged=start['boundary']['prior_unaccounted_s']+elapsed
    row=start['reservation']
    receipt=w.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller='engineering',
        tool_id='engineering.independent_review_publication',tool_version='1.0.0',execution_status='completed',charged=zero()),
        dict(boundary=start['boundary'],review_publication_elapsed_s=elapsed,prior_unaccounted_s=start['boundary']['prior_unaccounted_s'],
            verified_remote_sha=remote_sha,remote_sha_source='git ls-remote origin refs/heads/feat/gvs-dynamics',
            scientific_decisions_or_results_changed=False),charged)
    usage=w.store.remaining();before=start['boundary']['incremental_cost_baseline']['used']
    final=dict(status='settled_local_authoritative',usage=usage,incremental={k:usage['used'][k]-before[k] for k in before},
        receipt=receipt,verified_remote_sha=remote_sha,original_clock=w.freeze['live_clock'],repairs=w.repairs,
        remote_publication_costs_are_inflight_snapshot=True,local_ledger_is_accounting_authority=True)
    atomic_json(D/'structural_final_settled_costs.json',final)
    print(json.dumps(final,ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['begin','settle']);p.add_argument('--remote-sha')
    args=p.parse_args()
    if args.mode=='begin':begin()
    else:settle(args.remote_sha)
