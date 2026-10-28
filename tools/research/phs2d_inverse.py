"""Round-three inverse design over existing frozen Study, generation and receipts."""
import json
import numpy as np
from .phs2d import host,request,candidate,build,ROOT
from .state import state,save,update
from extensions.tendon_family.compiler import resolve
from extensions.tendon_family.passive_equilibrium import solve,consistency
from extensions.tendon_family.passive_inverse import modal_target,multicase_metrics,design_sensitivity
from extensions.tendon_family.route_validation import validate_routes
from .phs2d_evaluation import evaluate


def context():return host(round3=True)


def setup(label):
    h,p=context();ar=state(h)['phs']['assemblies'][label];return h,p,ar,h.store.artifact(ar)


def assemble(label,generation,reason,offsets=None,category='guided'):
    h,p=context();v=state(h)['phs']
    if label in v.get('assemblies',{}):
        old=h.store.artifact(v['assemblies'][label])
        if old['generation']!=generation or old['offsets_m']!=(offsets or [0.]*generation['tendon_count']):raise ValueError('IMMUTABLE_LABEL')
        return v['assemblies'][label]
    ref=candidate(h,p,label,generation,reason);cfg=h.store.artifact(ref)['configuration']
    physics=resolve(cfg['robot']['structure']['data'],cfg['policy']['discretization']['data'])
    offsets=offsets or [0.]*len(physics['tendons'])
    if len(offsets)!=len(physics['tendons']) or max(abs(x) for x in offsets)>p['payout_offset_bound_m']:raise ValueError('PAYOUT_DOMAIN')
    a=dict(candidate=ref,generation=generation,reason=reason,category=category,offsets_m=offsets,
        payout_lengths_m={t['entity']:length+shift for t,length,shift in zip(physics['tendons'],physics['reference_lengths_m'],offsets)})
    ar=save(h,a,'phs_inverse_frozen_assembly');v=state(h)['phs'];v.setdefault('assemblies',{})[label]=ar;update(h,phs=v)
    return ar


def analysis(label,kind='modal',source=None,phase='P1'):
    h,p,ar,a=setup(label);source=source or state(h)['phs'].get('static_baselines',{}).get(label)
    def run(_):
        n=build(h,p,a['candidate'],payout_lengths_m=a['payout_lengths_m'])
        if kind=='geometry':return validate_routes(n,[np.zeros(n.model.nv)])
        if kind=='consistency':
            v=consistency(n);v['full_3d_coordinates']=n.model.nv==len(n.physics['dofs'])==2*sum(a['generation']['segments'][str(i)]['cells'] for i in range(a['generation']['segment_count']))
            return v
        return modal_target(n,h.store.artifact(source)['equilibrium'],p['search_s'])
    b,r=request(h,p,dict(kind={'modal':'passive_modal_target_v1','geometry':'route_geometry_validation_v1','consistency':'inverse_native_consistency_v1'}[kind],assembly=ar,source=source),run,math=1,phase=phase)
    v=state(h)['phs'];v.setdefault(kind,{})[label]=r;update(h,phs=v);return b,r


def equilibrium(label,s=.5,force=0.,source=None,phase='P1',multistart=False):
    h,p,ar,a=setup(label)
    def run(_):
        n=build(h,p,a['candidate'],payout_lengths_m=a['payout_lengths_m'])
        initial=None if source is None else h.store.artifact(source)['equilibrium']['qpos']
        result=solve(n,s,force,initial,multistart)
        result['geometry']=validate_routes(n,[result['equilibrium']['qpos']])
        return result
    b,r=request(h,p,dict(kind='passive_equilibrium_v1',revision='inverse_r1',assembly=ar,s=s,force_n=force,source=source,multistart=multistart),run,math=1,phase=phase)
    if force==0:
        v=state(h)['phs'];v.setdefault('static_baselines',{})[label]=r;update(h,phs=v)
    return b,r


def screen(label,nonlinear=False,phase='P1'):
    h,p,ar,a=setup(label);g,gr=analysis(label,'geometry',phase=phase)
    out=dict(method='passive_multicase_design_v1',label=label,assembly=ar,geometry=gr,status='invalid_geometry')
    if g['status']=='legal_at_checked_poses':
        b,br=equilibrium(label,phase=phase);eq=b['equilibrium']
        lateral=float(np.max(np.linalg.norm(np.array(eq['positions'])[:,:2],axis=1)))
        out.update(baseline=br,baseline_status=b['status'],initial_lateral_m=lateral,status='invalid_baseline')
        if b['status']=='qualified_local_minimum' and b['geometry']['status']=='legal_at_checked_poses' and lateral<=p['initial_lateral_limit_m']:
            m,mr=analysis(label,source=br,phase=phase);pred=m['B_C_unilateral_force_response']['predictions']
            out.update(status='local_only',modal=mr,min_point_m=min(x['point_dx_m'] for x in pred),max_tip_m=max(x['tip_xy_m'] for x in pred),max_ratio=max(x['ratio'] for x in pred))
            if nonlinear:
                rows=[]
                for loc in p['search_s']:
                    for force in (p['force_n'],-p['force_n']):
                        loaded,lr=equilibrium(label,loc,force,br,phase)
                        metrics=multicase_metrics(p,eq,loaded['equilibrium'],loc)
                        valid=loaded['status']=='qualified_local_minimum' and loaded['geometry']['status']=='legal_at_checked_poses'
                        rows.append(dict(s=loc,force_n=force,reference=lr,valid=valid,status=loaded['status'],geometry=loaded['geometry']['status'],**metrics))
                valid=all(r['valid'] for r in rows)
                out.update(rows=rows,status='valid_static_set' if valid else 'unknown_or_illegal_loaded',worst_violation=max(r['worst_violation'] for r in rows) if valid else None,
                    all_static_pass=valid and all(r['worst_violation']==0 for r in rows))
    ref=save(h,out,'phs_inverse_screen');v=state(h)['phs'];v.setdefault('screens',{})[label]=ref;update(h,phs=v);return out


def dynamics(label,s=.5,force=0.,baseline=None,phase='P1',timestep=None,perturbation=0.,source=None):
    h,p,ar,a=setup(label);source=source or state(h)['phs']['static_baselines'][label];eq=h.store.artifact(source)
    if eq['status']!='qualified_local_minimum' or eq['force_n']!=0:raise ValueError('QUALIFIED_UNLOADED_SOURCE_REQUIRED')
    if baseline and h.store.artifact(baseline)['status']!='stable':raise ValueError('STABLE_DYNAMIC_BASELINE_REQUIRED')
    if force and not baseline:raise ValueError('BASELINE_REQUIRED')
    def admit_dynamic():
        v=state(h)['phs'];names=v.setdefault('dynamic_candidates',[])
        if label not in names:
            if len(names)>=p['limits']['dynamic_candidates']:raise ValueError('DYNAMIC_CANDIDATE_LIMIT')
            names.append(label);update(h,phs=v)
    admit_dynamic();protocol={**p}
    if timestep:protocol.update(timestep_s=timestep,sample_every_steps=round(.01/timestep))
    initial=np.array(eq['equilibrium']['qpos'] if baseline is None else h.store.artifact(baseline)['samples'][-1]['qpos'])
    initial+=perturbation*np.sin(np.arange(len(initial)))
    def run(attempt):
        n=build(h,protocol,a['candidate'],payout_lengths_m=a['payout_lengths_m']);raw=n.run(initial,s,force,attempt=attempt,initial=force==0)
        raw['geometry']=validate_routes(n,[r['qpos'] for r in raw['samples']])
        if raw['geometry']['status']!='legal_at_checked_poses':raw['status']='route_geometry_failure'
        raw['numerical_protocol']=protocol;return raw
    steps=round(protocol['load_max_s' if force else 'equilibrium_max_s']/protocol['timestep_s'])
    return request(h,p,dict(kind='inverse_independent_dynamics_v1',assembly=ar,s=s,force_n=force,baseline=baseline,source=source,timestep=timestep,perturbation=perturbation),run,steps=steps,phase=phase)


def dynamic_set(label,holdout=False,phase='P1',timestep=None,perturbation=0.):
    h,p,ar,a=setup(label);v=state(h)['phs']
    if holdout and not any(h.store.artifact(r)['all_pass'] and h.store.artifact(r)['label']==label and not h.store.artifact(r)['holdout'] for r in v.get('dynamic_sets',[])):
        raise ValueError('SIX_SEARCH_PASS_REQUIRED_BEFORE_HOLDOUT')
    base,br=dynamics(label,phase=phase,timestep=timestep,perturbation=perturbation);rows=[]
    if base['status']=='stable':
        for s in p['holdout_s'] if holdout else p['search_s']:
            for force in (p['force_n'],-p['force_n']):
                raw,r=dynamics(label,s,force,br,phase,timestep,source=base['request']['source'])
                e=evaluate(p,base,raw,s);er=save(h,dict(**e,assembly=ar,baseline=br,loaded=r,s=s,force_n=force),'phs_independent_evaluation')
                rows.append(dict(s=s,force_n=force,reference=r,evaluation=er,**{k:e[k] for k in ('status','valid','tip_xy_m','point_dx_m','ratio','out_of_plane_m','worst_violation')}))
    out=dict(label=label,holdout=holdout,baseline=br,baseline_status=base['status'],rows=rows,timestep=timestep or p['timestep_s'],perturbation=perturbation,
        all_valid=len(rows)==(4 if holdout else 6) and all(r['valid'] for r in rows),all_pass=len(rows)==(4 if holdout else 6) and all(r['status']=='development_pass' for r in rows))
    rr=save(h,out,'phs_inverse_dynamic_set');v=state(h)['phs'];v.setdefault('dynamic_sets',[])
    if rr not in v['dynamic_sets']:v['dynamic_sets'].append(rr)
    update(h,phs=v);return out


def admit(label):
    h,p,ar,a=setup(label);static,sr=equilibrium(label,phase='P0',multistart=True)
    sem,cr=analysis(label,'consistency',phase='P0');geo,gr=analysis(label,'geometry',phase='P0')
    raw,dr=dynamics(label,phase='P0',source=sr)
    passed=bool(static['status']=='qualified_local_minimum' and static['multistart_same_branch'] and raw['status']=='stable'
        and max(np.linalg.norm(np.array(r)[:2]) for r in raw['samples'][-1]['positions'])<=p['initial_lateral_limit_m']
        and geo['status']=='legal_at_checked_poses' and sem['full_3d_coordinates'] and sem['no_actuators'] and sem['vertical_down']
        and sem['fixed_unilateral_payout'] and sem['objective_gradient_error']<1e-7 and sem['tendon_gradient_error']<1e-7 and sem['force_consistency_error']<1e-9)
    ref=save(h,dict(passed=passed,static=sr,dynamic=dr,semantics=cr,geometry=gr),'phs_inverse_P0')
    v=state(h)['phs'];v.update(p0_pass=passed,p0_report=ref);update(h,phs=v);return dict(passed=passed,static=static['status'],dynamic=raw['status'],checks=raw.get('checks'))
