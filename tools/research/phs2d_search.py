"""Math-led PHS study operations over the existing candidate and request ledger."""
import argparse,json
import numpy as np
from tools.research.phs2d import host,request,candidate,build,generation,ROOT
from tools.research.state import state,save,update
from tools.state_io import digest
from extensions.tendon_family.passive_equilibrium import solve,tangent,consistency
from tools.research.phs2d_evaluation import evaluate


def prepare(label,gen,offsets=None,reason='Declared reference hypothesis'):
    h,p=host(True);ref=candidate(h,p,label,gen,reason)
    old=state(h)['phs'].get('assemblies',{}).get(label)
    if old:return old
    # Structural build remains in original generated candidate construction chain.
    cfg=h.store.artifact(ref)['configuration'];from extensions.tendon_family.compiler import resolve
    physics=resolve(cfg['robot']['structure']['data'],cfg['policy']['discretization']['data'])
    shifts=offsets or [0.]*len(physics['tendons'])
    if len(shifts)!=len(physics['tendons']) or max(abs(x) for x in shifts)>p['payout_offset_bound_m']:raise ValueError('PAYOUT_DOMAIN')
    assembly=dict(candidate=ref,payout_lengths_m={t['entity']:length+shift for t,length,shift in zip(physics['tendons'],physics['reference_lengths_m'],shifts)},
        generation=gen,reason=reason,all_conditions_share_payout=True)
    ar=save(h,assembly,'phs_frozen_passive_assembly');s=state(h);s['phs'].setdefault('assemblies',{})[label]=ar;update(h,phs=s['phs'])
    return ar


def setup(label):
    h,p=host(True);ar=state(h)['phs']['assemblies'][label];a=h.store.artifact(ar)
    return h,p,ar,a


def static(label,s=.5,force=0.,phase='P0',multistart=False,source=None):
    h,p,ar,a=setup(label)
    def run(_):
        n=build(h,p,a['candidate'],payout_lengths_m=a['payout_lengths_m'])
        initial=None if source is None else h.store.artifact(source)['equilibrium']['qpos']
        return solve(n,s,force,initial=initial,multistart=multistart)
    b,r=request(h,p,dict(kind='passive_equilibrium_v1',serialization_revision=2,assembly=ar,s=s,force_n=force,source=source,multistart=multistart),run,math=1,phase=phase)
    if force==0:
        v=state(h)['phs'];v.setdefault('static_baselines',{})[label]=r;update(h,phs=v)
    return b,r


def local(label,phase='P1',source=None):
    h,p,ar,a=setup(label);source=source or state(h)['phs']['static_baselines'][label]
    base=h.store.artifact(source)
    return request(h,p,dict(kind='passive_constrained_compliance_v2',assembly=ar,source=source),
        lambda _:tangent(build(h,p,a['candidate'],payout_lengths_m=a['payout_lengths_m']),base['equilibrium'],base['s'],base['force_n'],p['search_s']),math=1,phase=phase)


def dynamics(label,s=.5,force=0.,phase='P0',baseline=None,static_source=None,numerics=None,perturbation=0.):
    h,p,ar,a=setup(label)
    static_source=static_source or state(h)['phs']['static_baselines'][label]
    eq=h.store.artifact(static_source)
    if eq['force_n']!=0 or eq['status']!='qualified_local_minimum':raise ValueError('UNLOADED_KKT_INITIAL_REQUIRED')
    if force and not baseline:raise ValueError('DYNAMIC_BASELINE_REQUIRED')
    if baseline and h.store.artifact(baseline)['status']!='stable':raise ValueError('STABLE_UNLOADED_DYNAMICS_REQUIRED')
    protocol={**p,**(numerics or {})}
    initial=eq['equilibrium']['qpos'] if baseline is None else h.store.artifact(baseline)['samples'][-1]['qpos']
    initial=np.array(initial)+perturbation*np.sin(np.arange(len(initial)))
    def run(attempt):
        n=build(h,protocol,a['candidate'],payout_lengths_m=a['payout_lengths_m'])
        result=n.run(initial,s,force,attempt=attempt,initial=force==0)
        result['numerical_protocol']=protocol
        return result
    steps=round(protocol['load_max_s']/protocol['timestep_s'])
    body,ref=request(h,p,dict(kind='passive_independent_dynamics_v2',assembly=ar,s=s,force_n=force,
        baseline=baseline,static_source=static_source,numerics=numerics,perturbation=perturbation),run,steps=steps,phase=phase)
    if force==0:
        v=state(h)['phs'];v.setdefault('dynamic_baselines',{})[label]=ref;update(h,phs=v)
    else:
        result=evaluate(p,h.store.artifact(baseline),body,s)
        evaluation=save(h,dict(**result,assembly=ar,baseline=baseline,loaded=ref,s=s,force_n=force),'phs_independent_evaluation')
        v=state(h)['phs'];v.setdefault('evaluations',[])
        if evaluation not in v['evaluations']:v['evaluations'].append(evaluation)
        update(h,phs=v)
    return body,ref


def semantic_check(label):
    h,p,ar,a=setup(label)
    return request(h,p,dict(kind='P0A_potential_gradient_and_virtual_work',assembly=ar),
        lambda _:consistency(build(h,p,a['candidate'],payout_lengths_m=a['payout_lengths_m'])),math=1,phase='P0')


def admit_p0(label):
    h,p,ar,a=setup(label);v=state(h)['phs'];sr=v['static_baselines'][label];dr=v['dynamic_baselines'][label]
    static_result=h.store.artifact(sr);dynamic=h.store.artifact(dr)
    sem,semref=semantic_check(label)
    a_ok=bool(sem['objective_gradient_error']<1e-7 and sem['tendon_gradient_error']<1e-7 and sem['force_consistency_error']<1e-9
        and dynamic.get('checks',{}).get('rope_direction') and dynamic.get('checks',{}).get('rope_excess'))
    b_ok=bool(static_result['status']=='qualified_local_minimum' and static_result['multistart_same_branch'] and dynamic['status']=='stable'
        and max(np.linalg.norm(np.array(r)[:2]) for r in dynamic['samples'][-1]['positions'])<=p['initial_lateral_limit_m'])
    rr=save(h,dict(version='P0_split_v1',P0A=a_ok,P0B=b_ok,assembly=ar,static=sr,dynamic=dr,semantics=semref,
        old_P0_verdict='unchanged_failed',loaded_task_pass_required=False),'phs_round2_P0_gate')
    v=state(h)['phs'];v.update(p0_pass=a_ok and b_ok,p0_report=rr);update(h,phs=v)
    return dict(passed=a_ok and b_ok,reference=rr)


def screen(label,nonlinear=False):
    h,p,ar,a=setup(label)
    b,br=static(label,phase='P1')
    lateral=float(np.max(np.linalg.norm(np.array(b['equilibrium']['positions'])[:,:2],axis=1)))
    result=dict(label=label,assembly=ar,baseline=br,baseline_status=b['status'],initial_lateral_m=lateral)
    if b['status']=='qualified_local_minimum' and lateral<=p['initial_lateral_limit_m']:
        t,tr=local(label);rows=t['predictions'];result.update(tangent=tr,tangent_status=t['status'],
            min_point_m=min(x['point_dx_m'] for x in rows),max_tip_m=max(x['tip_xy_m'] for x in rows),max_ratio=max(x['ratio'] for x in rows))
        if nonlinear:
            solved=[]
            for loc in p['search_s']:
                for force in (p['force_n'],-p['force_n']):
                    loaded,lr=static(label,loc,force,phase='P1',source=br);eq=loaded['equilibrium']
                    delta=np.array(eq['positions'])-b['equilibrium']['positions'];dx=abs(delta[p['monitor_s'].index(loc),0]);tip=float(np.linalg.norm(delta[-1,:2]));y=float(np.max(abs(delta[:,1])))
                    solved.append(dict(s=loc,force_n=force,reference=lr,status=loaded['status'],point_dx_m=float(dx),tip_xy_m=tip,ratio=tip/max(float(dx),1e-15),out_of_plane_m=y))
            result['nonlinear_static']=solved
    rr=save(h,result,'phs_mathematical_screen');v=state(h)['phs'];v.setdefault('screens',{})[label]=rr;update(h,phs=v)
    return result


def dynamic_six(label,numerics=None):
    h,p,ar,a=setup(label);base,br=dynamics(label,phase='P1',numerics=numerics)
    summary=dict(label=label,baseline=br,baseline_status=base['status'],rows=[])
    if base['status']=='stable':
        for loc in p['search_s']:
            for force in (.1,-.1):
                raw,rr=dynamics(label,loc,force,phase='P1',baseline=br,numerics=numerics)
                e=evaluate(p,base,raw,loc)
                summary['rows'].append(dict(s=loc,force_n=force,reference=rr,**{k:e[k] for k in ('status','valid','tip_xy_m','point_dx_m','ratio','out_of_plane_m','worst_violation')}))
    summary['all_valid']=len(summary['rows'])==6 and all(r['valid'] for r in summary['rows'])
    summary['all_pass']=len(summary['rows'])==6 and all(r['status']=='development_pass' for r in summary['rows'])
    ref=save(h,summary,'phs_six_condition_result');v=state(h)['phs'];v.setdefault('dynamic_sets',[]).append(ref);update(h,phs=v)
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['reference','static','local','dynamics','consistency']);parser.add_argument('--label',default='A_two_full');args=parser.parse_args()
    if args.action=='reference':result=prepare(args.label,generation(),'','Original full-span symmetric reference')
    elif args.action=='static':b,r=static(args.label,multistart=True);result=dict(reference=r,status=b['status'],kkt={k:b['equilibrium'][k] for k in ('stationarity_inf_nm','primal_violation_m','complementarity_nm','active_rank','tensions_n','optimizer_message')},cost=b['numerical_cost'])
    elif args.action=='local':b,r=local(args.label,phase='P0');result=dict(reference=r,status=b['status'],predictions=b['predictions'])
    elif args.action=='consistency':result=semantic_check(args.label)
    else:b,r=dynamics(args.label);result=dict(reference=r,status=b['status'],checks=b.get('checks'),cost=b['cost'])
    print(json.dumps(result))
