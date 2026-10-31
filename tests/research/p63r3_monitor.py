"""Short read-only observations. Parse/report/wait only after connection closure."""
import argparse,json,sqlite3,time
from contextlib import closing
from pathlib import Path


def read_rows(database,sql,parameters=()):
    with closing(sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro',uri=True,timeout=1)) as db:
        db.execute('PRAGMA query_only=ON')
        return db.execute(sql,parameters).fetchall()


def observe(database):
    raw=read_rows(database,"select run_id,json_extract(state,'$.pilot.live_model_requests','$.research_status','$.profile.version','$.profile.identity','$.pending.kind','$.pilot.unconsumed_response','$.selected','$.success_gate', '$.search_results'),json_array_length(state,'$.analysis_results'),json_array_length(state,'$.physical_replays') from sessions")
    if len(raw)!=1:raise ValueError('ONE_STUDY_MONITOR_REQUIRED')
    run,body,math,physical=raw[0]
    used,status,version,identity,pending,unconsumed,selected,gate,search_refs=json.loads(body)
    searches=[]
    for ref in search_refs:
        body=read_rows(database,'select body from artifacts where id=?',(ref['artifact_id'],))[0][0]
        result=json.loads(body)['result'];best=result.get('best_native_candidate') or {}
        candidate=(best.get('evidence') or {}).get('candidate');profile=None
        if candidate:
            profile=read_rows(database,"select json_extract(body,'$.profile_identity') from artifacts where id=?",(candidate['artifact_id'],))[0][0]
        conditions=(best.get('evidence') or {}).get('conditions') or {}
        searches.append(dict(reference=ref,profile_identity=profile,status=result['status'],
            termination=result.get('termination_reason'),candidate=candidate,conditions=conditions))
    best={}
    for search in searches:
        for condition,row in search['conditions'].items():
            if row.get('status')!='computed' or row.get('J') is None:continue
            key=(search['profile_identity'],condition)
            if key not in best or row['J']<best[key]['J']:
                best[key]=dict(profile_identity=key[0],condition=condition,search=search['reference'],**row)
    open_calls=read_rows(database,'select request_id,status,caller from calls where receipt is null')
    return dict(schema='p63r3_short_observation_v1',study_id=run,provider=used,math=math,physical=physical,
        status=status,profile_version=version,profile_identity=identity,pending_kind=pending,
        unconsumed_response=bool(unconsumed),selected=selected,success_gate=bool(gate),
        searches=len(search_refs),latest_search=searches[-1] if searches else None,
        best_mathematical_by_profile=list(best.values()),unsealed_calls=[dict(request=r,status=s,caller=c) for r,s,c in open_calls],
        scope='Separate short reads, not an atomic scientific certificate; no admission or research choice.')


def main():
    from tools.research.config import ROOT
    p=argparse.ArgumentParser();p.add_argument('--database',type=Path,default=ROOT/'runs/research/p63v1-m3-autonomous-feasibility-sol-20261030/platform.sqlite')
    p.add_argument('--samples',type=int,default=1);p.add_argument('--interval',type=float,default=15)
    a=p.parse_args()
    if a.samples<1 or a.interval<0:p.error('Positive samples and nonnegative interval required')
    for i in range(a.samples):
        try:value=observe(a.database)
        except sqlite3.OperationalError as exc:
            value=dict(schema='p63r3_short_observation_v1',observation='temporarily_unavailable',error=str(exc),research_action=None)
        print(json.dumps(value),flush=True)
        if value.get('status')=='stopped':break
        if i+1<a.samples:time.sleep(a.interval)


if __name__=='__main__':main()
