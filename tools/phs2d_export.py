"""Read-only portable evidence export and audit; no model construction/integration."""
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np
from tools.platform_store import Store,encode
from tools.state_io import atomic_json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/phs2d_20261028'


def export():
    store=Store(ROOT/'runs/phs2d/store');s=store.session('phs2d-20261028-v1')['state'];v=s['phs']
    artifacts={}
    def collect(value):
        if isinstance(value,list):
            for item in value:collect(item)
        elif isinstance(value,dict):
            if set(value)=={'artifact_id','media_type'} and value['media_type']=='application/json':
                key=value['artifact_id']
                if key not in artifacts:
                    body=store.artifact(value);artifacts[key]=body;collect(body)
            else:
                for item in value.values():collect(item)
    collect(v)
    if s.get('final_disposition'):collect(s['final_disposition'])
    events=store.events('phs2d-20261028-v1')
    # Only PHS-specific event payloads, plus their immutable request/evaluation records.
    relevant=[e for e in events if e['kind'].startswith('phs')]
    collect(relevant)
    calls=[]
    with store.connect(True) as db:
        for row in db.execute("SELECT * FROM calls WHERE caller='phs2d-development'"):
            call=dict(row)
            for key in ('receipt','reserved','charged','resources'):
                call[key]=json.loads(call[key]) if call[key] else None
            calls.append(call)
    raw=[store.artifact(r) for r in v['results'].values()]
    attempts=sum(r['cost']['physics_step_attempts'] for r in raw)
    math=sum(r['cost']['math_requests'] for r in raw)
    assert attempts==v['steps']==v['p0_steps']==100000
    assert math==v['math'] and v['pending'] is None
    assert all(c['receipt'] and c['status']=='completed' for c in calls)
    for key,body in artifacts.items():assert hashlib.sha256(encode(body).encode()).hexdigest()==key
    p=store.artifact(v['protocol']);report=store.artifact(v['p0_report']);base=store.artifact(report['baseline'])
    conditions=[]
    for r in sorted(raw,key=lambda x:(x['request']['protocol']['artifact_id'],x['request'].get('force_n',0.))):
        if r['request']['kind']!='equilibrium':continue
        samples=r['samples'];tail=[x for x in samples if x['time_s']>=samples[-1]['time_s']-.250000001]
        baseline=r['request']['baseline'];last=samples[-1]
        if baseline:
            a=store.artifact(baseline)['samples'][-1];delta=np.array(last['positions'])-a['positions']
            dx=abs(last['force_point'][0]-a['positions'][10][0]);tip=float(np.linalg.norm(delta[-1,:2]))
            metrics=dict(point_dx_m=dx,tip_xy_m=tip,ratio=tip/max(dx,1e-15),out_of_plane_m=float(np.max(abs(delta[:,1]))))
        else:metrics={}
        conditions.append(dict(protocol=store.artifact(r['request']['protocol'])['version'],force_n=r['request']['force_n'],s=.5,
            status=r['status'],checks=r['checks'],tail_speed_m_s=max(x['speeds'][-1] for x in tail),
            tail_qvel_rad_s=max(x['qvel_inf'] for x in tail),tail_balance_nm=max(x['static_balance_inf_nm'] for x in tail),
            tail_drift_m=r['tail_drift_m'],tail_excess_m=r['tail_excess_m'],terminal_tensions_n=last['tensions_n'],
            terminal_length_change_m=last['length_change'],metrics=metrics,cost=r['cost'],
            valid_task_result=False,reason='unqualified no-load baseline; P0 diagnostics only'))
    reference=store.artifact(v['candidates']['reference']);cfg=reference['configuration']
    summary=dict(status='P0_FAILED_STOP_NO_P1',study_status=s['research_status'],selected=s['selected'],p0=report,protocol=p,conditions=conditions,
        budgets=dict(integration_attempts=attempts,confirmed_completed_steps=attempts,p0_cap=100000,total_cap=5000000,
            store_math_requests=math,unledgered_preparation_diagnostics=1,conservative_math_total=math+1,math_cap=250,
            tangent_finite_difference_force_samples=192,tangent_directional_QPs=12,
            unique_candidates=1,zero_integration_precompile_builds=1,full_physics_runs=10,
            elapsed_numerical_s=sum(r['cost']['elapsed_s'] for r in raw),provider_requests=0,
            provider_cost=0,codex_service_cost='unavailable',pending_requests=0),
        search_conditions=[dict(s=loc,force_n=sign*.1,status='not_run_P0_gate') for loc in p['search_s'] for sign in (1,-1)],
        holdout_conditions=[dict(s=loc,force_n=sign*.1,status='not_run_P0_gate') for loc in p['holdout_s'] for sign in (1,-1)],
        controls={key:'not_run_P0_gate' for key in ['A_no_limits','B_stiff','C_alternative_route','D_bilateral_physics']},
        failure_math=store.artifact(v['failure_math']),
        reference_structure=dict(design=cfg['robot']['structure']['data'],discretization=cfg['policy']['discretization']['data'],
            payout_lengths_m=base['request']['payout_lengths_m']),
        audit=dict(artifact_hashes_verified=len(artifacts),receipts_verified=len(calls),all_attempts_accounted=True,
            no_replays_of_unknown_requests=True,independent_registered_acceptance='not_registered',
            active_task_evaluations=0,physics_source_commits=sorted(set(r['implementation_commit'] for r in raw)),
            limitations=['One ad hoc zero-state mechanics inspection before diagnose was not Store-admitted; conservatively counted separately; no integration.',
                'Zero-integration precompile and unit fixtures are not scientific runs.',
                'Sampled shape points are not a continuous backbone guarantee.',
                'No P1 or controls permitted after failed P0; no best valid candidate exists.']))
    OUT.mkdir(parents=True,exist_ok=True)
    package=dict(state=v,study_status=s['research_status'],final_disposition=s.get('final_disposition'),artifacts=artifacts,events=relevant,calls=calls)
    encoded=json.dumps(package,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    path=OUT/'raw_evidence.json.gz';path.write_bytes(gzip.compress(encoded,mtime=0))
    summary['raw_bundle']=dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
    atomic_json(OUT/'summary.json',summary)
    atomic_json(OUT/'reference_structure.json',summary['reference_structure'])
    print(json.dumps(summary['budgets']));print(json.dumps(summary['audit']))


if __name__=='__main__':export()
