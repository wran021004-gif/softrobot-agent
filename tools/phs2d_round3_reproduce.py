"""Explicit fresh isolated reproduction using the existing Study/Store services."""
import argparse
from copy import deepcopy
import hashlib
import json
import numpy as np
from tools.research import core
from tools.research.phs2d import ROOT,request,candidate,build
from tools.research.state import state,save,update
from tools.state_io import read,atomic_json
from extensions.tendon_family.passive_equilibrium import solve,consistency
from extensions.tendon_family.route_validation import validate_routes
from tools.research.phs2d_evaluation import evaluate


def reproduce():
    out=ROOT/'evidence/phs2d_round3_20261028';package=read(out/'solution/design.json');audit=read(out/'summary.json')
    assert audit['budgets']['physics_step_attempts']+500000<=20000000
    assert audit['budgets']['math_requests']+20<=1200 and audit['budgets']['generation_attempts']+1<=300
    h=core.prepare(ROOT/'configs/research/study_phs2d_reproduction_v1.json',directory=ROOT/'runs/phs2d-isolated-reproduction/store')
    if state(h)['research_status']=='stopped':
        print(json.dumps(h.store.artifact(state(h)['phs']['reproduction_result'])));return
    if 'freeze' not in state(h):core.bind(h)
    p=deepcopy(package['protocol']);p.update(version='phs2d_passive_inverse_reproduction_v1')
    p['limits']=dict(physics_step_attempts=500000,p0_steps=32000,p1_steps=468000,final_reserved_steps=0,math_requests=20,candidates=1)
    if 'phs' not in state(h):
        update(h,phs=dict(protocol=save(h,p,'isolated_reproduction_protocol'),steps=0,p0_steps=0,math=0,candidates={},results={},pending=None,p0_pass=False))
    ref=candidate(h,p,'frozen_solution',package['generation'],'Explicit independent reproduction of delivered physical design, same payout; no design search.')
    def native():
        n=build(h,p,ref,payout_lengths_m=package['payout_lengths_m'])
        assert n.physics['identity']==package['physics']['identity'] and n.model.nu==0
        return n
    def preflight(_):
        n=native();result=solve(n,multistart=True);sem=consistency(n);sem['full_3d_coordinates']=n.model.nv==len(n.physics['dofs'])
        result.update(consistency=sem,geometry=validate_routes(n,[result['equilibrium']['qpos']]))
        for k,v in sem['numerical_cost'].items():result['numerical_cost'][k]+=v
        return result
    eq,er=request(h,p,dict(kind='independent_reproduction_preflight_v1',candidate=ref),preflight,math=1,phase='P0')
    sem=eq['consistency']
    assert eq['status']=='qualified_local_minimum' and eq['multistart_same_branch'] and eq['geometry']['status']=='legal_at_checked_poses'
    assert sem['full_3d_coordinates'] and sem['no_actuators'] and sem['vertical_down'] and sem['fixed_unilateral_payout']
    assert sem['objective_gradient_error']<1e-7 and sem['tendon_gradient_error']<1e-7 and sem['force_consistency_error']<1e-9
    steps=round(p['load_max_s']/p['timestep_s'])
    def run(q,s,force,initial,attempt):
        n=native();raw=n.run(q,s,force,attempt=attempt,initial=initial)
        raw['geometry']=validate_routes(n,[r['qpos'] for r in raw['samples']])
        if raw['geometry']['status']!='legal_at_checked_poses':raw['status']='route_geometry_failure'
        return raw
    baseline,br=request(h,p,dict(kind='independent_reproduction_baseline_v1',candidate=ref,equilibrium=er),
        lambda attempt:run(eq['equilibrium']['qpos'],.5,0.,True,attempt),steps=steps,phase='P0')
    assert baseline['status']=='stable'
    assert np.max(np.linalg.norm(np.array(baseline['samples'][-1]['positions'])[:,:2],axis=1))<=p['initial_lateral_limit_m']
    v=state(h)['phs'];v['p0_pass']=True;update(h,phs=v);rows=[]
    for loc in (*p['search_s'],*p['holdout_s']):
        for force in (p['force_n'],-p['force_n']):
            raw,rr=request(h,p,dict(kind='independent_reproduction_loaded_v1',candidate=ref,baseline=br,s=loc,force_n=force),
                lambda attempt:run(baseline['samples'][-1]['qpos'],loc,force,False,attempt),steps=steps,phase='P1')
            row=dict(s=loc,force_n=force,reference=rr,**evaluate(p,baseline,raw,loc));rows.append(row)
            print(json.dumps({k:row[k] for k in ('s','force_n','status','point_dx_m','tip_xy_m','ratio')}),flush=True)
    result=dict(status='ten_case_pass' if all(r['status']=='development_pass' for r in rows) else 'reproduction_failure',rows=rows,
        candidate=ref,payout_lengths_m=package['payout_lengths_m'],cost=state(h)['phs'],origin_model_sha256=package['exact_model_sha256'])
    result_ref=save(h,result,'isolated_reproduction_result');v=state(h)['phs'];v['reproduction_result']=result_ref;update(h,phs=v)
    core.dispatch(h,dict(action='stop',hypothesis='Explicit fixed-design independent reproduction complete.',expected_observation='All ten original conditions pass.',weakening_observation='Any invalid or failed condition.',fixed_conditions='Delivered physical design, original task and fixed passive payout.',stopping_condition='One ten-case run only, no search.',interpretation='Independent development evaluation, not a formal SELECT or hardware claim.'),'reproduction-stop')
    atomic_json(h.store.root.parent/'result.json',result);core.export(h,h.store.root.parent/'export')
    print(json.dumps(dict(status=result['status'],physics_step_attempts=state(h)['phs']['steps'])))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    if args.execute:reproduce()
    else:
        path=ROOT/'evidence/phs2d_round3_20261028/solution';p=read(path/'design.json')
        assert hashlib.sha256((path/'model.xml').read_bytes()).hexdigest()==p['exact_model_sha256']
        print('Model identity verified. --execute creates one fresh bounded Study; sealed studies are never reopened.')
