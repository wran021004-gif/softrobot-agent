"""Development PHS requests over existing Study candidates, Store and reservations.

No TaskAdapter/SELECT claim: construction scaffold is never executed. Physics,
mathematics and independent evaluation remain separate responsibilities.
"""
import json
import time
import subprocess
from pathlib import Path
import numpy as np
from tools.research import core
from tools.research.state import state,save,update
from tools.platform_store import plain,zero
from tools.state_io import read,digest,atomic_json
from extensions.tendon_family.compiler import resolve
from extensions.tendon_family.passive import PassiveModel,material_point,compliance
from tools.research.phs2d_evaluation import evaluate

ROOT=Path(__file__).resolve().parents[2]
OWNER=ROOT/'runs/phs2d'


def host():
    h=core.prepare(ROOT/'configs/research/study_phs2d_v1.json',directory=OWNER/'store')
    if 'freeze' not in state(h):core.bind(h)
    p=read(ROOT/'configs/research/phs2d_protocol_v2.json')
    s=state(h)
    if 'phs' not in s:
        ref=save(h,p,'phs_protocol_freeze')
        update(h,phs=dict(protocol=ref,steps=0,p0_steps=0,math=0,candidates={},results={},pending=None,p0_pass=False))
    elif h.store.artifact(s['phs']['protocol'])!=p:
        old=h.store.artifact(s['phs']['protocol'])
        if old['version']!='phs2d_passive_v1' or s['phs']['pending'] or s['phs']['p0_pass']:
            raise ValueError('FROZEN_PHS_PROTOCOL_CHANGED')
        ref=save(h,p,'phs_presearch_numerical_revision')
        s['phs'].setdefault('protocol_history',[]).append(s['phs']['protocol'])
        s['phs']['protocol']=ref;update(h,phs=s['phs'])
    return h,p


def request(h,p,details,fn,*,steps=0,math=0,phase='P1'):
    """Atomic admission; interrupted work retains reserved upper cost and blocks."""
    core.guard(h)
    spec={**details, 'protocol':state(h)['phs']['protocol'],'phase':phase}
    key='phs-'+digest(spec);old=h.store.lookup(h.run_id,key)
    if old:
        if not old['receipt']:raise ValueError('UNKNOWN_PHS_REQUEST_NO_RELAUNCH')
        ref=json.loads(old['receipt'])['output'];return h.store.artifact(ref),ref
    def guard(db):
        s=h.store.session(h.run_id,db)['state'];v=s['phs'];lim=p['limits']
        if v['pending']:raise ValueError('PHS_PENDING_NO_RELAUNCH')
        if phase=='P1' and not v['p0_pass']:raise ValueError('P0_MUST_PASS')
        if v['steps']+steps>lim['physics_step_attempts'] or v['math']+math>lim['math_requests']:
            raise ValueError('PHS_BUDGET_EXHAUSTED')
        if phase=='P0' and v['p0_steps']+steps>lim['p0_steps']:raise ValueError('P0_BUDGET_EXHAUSTED')
        v['steps']+=steps;v['math']+=math
        if phase=='P0':v['p0_steps']+=steps
        v['pending']=key
        ref=h.store.put(db,spec);h.store.event(db,h.run_id,'phs_request','reserved',inputs=[ref])
        h.store.update_state(db,h.run_id,s)
    cost=zero();cost.update(tool_calls=1,backend_solves=int(steps>0))
    row,fresh=h.store.reserve(h.run_id,key,digest(spec),'phs2d-development',cost,
        resources=['backend.family_mujoco'] if steps else [],guard=guard,kind='phs')
    attempts=0;started=time.perf_counter()
    def attempt():
        nonlocal attempts
        if attempts>=steps:raise ValueError('PHS_STEP_RESERVATION_EXHAUSTED')
        attempts+=1
    try:
        result=fn(attempt)
        execution='completed'
    except Exception as exc:
        result=dict(status='exception',error=repr(exc));execution='failed'
    elapsed=time.perf_counter()-started
    result.update(request=spec,cost=dict(physics_step_attempts=attempts,math_requests=math,elapsed_s=elapsed),
        implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    with h.store.transaction() as db:
        s=h.store.session(h.run_id,db)['state'];v=s['phs'];v['steps']-=steps-attempts
        if phase=='P0':v['p0_steps']-=steps-attempts
        v['pending']=None
        receipt=h.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller='phs2d-development',
            tool_id='research.phs2d_development',execution_status=execution,solver_status=execution,
            analysis_status='development_not_registered',task_success=None,charged=cost),
            output=result,elapsed=elapsed,db=db,kind='phs')
        v['results'][key]=receipt['output'];h.store.update_state(db,h.run_id,s)
    atomic_json(OWNER/'latest_cost.json',state(h)['phs'])
    if execution=='failed':raise ValueError(result)
    return result,receipt['output']


def candidate(h,p,label,generation,reason):
    s=state(h)
    if label in s['phs']['candidates']:return s['phs']['candidates'][label]
    if len(s['phs']['candidates'])>=p['limits']['candidates']:raise ValueError('CANDIDATE_LIMIT')
    if generation['tendon_count'] not in (1,2,4,6):raise ValueError('PHS_TENDON_SCOPE')
    if abs(sum(x['length_m'] for x in generation['segments'].values())-.28)>1e-12:raise ValueError('FIXED_LENGTH')
    q=dict(version='serial_family_generation_v2',family_space_identity=s['spec']['family_space_identity'],segment_count=2,**generation)
    plan=dict(action='generate',generation=q,hypothesis=reason,expected_observation='Passive cross-compliance and stable finite-force deformation',
        weakening_observation='Tip follows middle, middle rigid, invalid rope or equilibrium',fixed_conditions='PHS protocol, force, length and mesh',
        stopping_condition='P0 failure, first ten-condition witness, or finite budget',interpretation='Exploratory structural hypothesis; no active control')
    out=core.dispatch(h,plan,'phs-generate-'+label)['result'];ref=out['candidate']
    s=state(h);s['phs']['candidates'][label]=ref;update(h,phs=s['phs'])
    return ref


def build(h,p,ref,*,slack=0.,unrestricted=False):
    cfg=h.store.artifact(ref)['configuration'];design=cfg['robot']['structure']['data']
    physics=resolve(design,cfg['policy']['discretization']['data'])
    assert all(t['points'][0]['body']==-1 for t in physics['tendons'])
    payout=np.array(physics['reference_lengths_m'])+slack
    model=PassiveModel(physics,p,payout,OWNER/'models'/digest(dict(candidate=ref,slack=slack,unrestricted=unrestricted)),unrestricted)
    return model


def equilibrium(h,p,ref,*,s=.5,force=0.,baseline=None,slack=0.,unrestricted=False,phase='P1'):
    native=build(h,p,ref,slack=slack,unrestricted=unrestricted)
    initial=baseline is None
    details=dict(kind='equilibrium',candidate=ref,s=s,force_n=force,baseline=baseline,
        payout_lengths_m=native.payout.tolist(),unrestricted=unrestricted)
    q0=None if initial else h.store.artifact(baseline)['samples'][-1]['qpos']
    steps=round(p['equilibrium_max_s' if initial else 'load_max_s']/p['timestep_s'])
    return request(h,p,details,lambda attempt:native.run(q0,s,force,attempt=attempt,initial=initial),steps=steps,phase=phase)


def score(h,p,ref,base_ref,loaded_ref,s):
    result=evaluate(p,h.store.artifact(base_ref),h.store.artifact(loaded_ref),s)
    return save(h,dict(**result,candidate=ref,baseline=base_ref,loaded=loaded_ref,s=s,protocol=state(h)['phs']['protocol']), 'phs_independent_evaluation')


def math(h,p,ref,base_ref,phase='P1',slack=0.,unrestricted=False):
    native=build(h,p,ref,slack=slack,unrestricted=unrestricted)
    baseline=h.store.artifact(base_ref)
    if baseline['status']!='stable':raise ValueError('KNOWN_STABLE_EQUILIBRIUM_REQUIRED')
    return request(h,p,dict(kind='compliance',candidate=ref,baseline=base_ref,slack=slack,unrestricted=unrestricted),
        lambda _:compliance(native,baseline['samples'][-1]['qpos'],baseline['samples'][-1]['tensions_n'],p['search_s'],p['force_n']),math=1,phase=phase)


def generation(count=2,young=(2e6,2e6),lengths=(.14,.14),spans=None):
    import math
    return dict(tendon_count=count,segments={str(i):dict(cells=12,length_m=lengths[i],young_pa=young[i]) for i in range(2)},
        spans=spans or [dict(last_segment=1,count=count,phase_rad=math.pi/2,radius_m=.02,anchor_s=1.,guide_s=[.5])])


def p0():
    import mujoco
    from extensions.tendon_family.geometry import geometry
    h,p=host();ref=candidate(h,p,'reference',generation(),'Symmetric opposing full-span ropes constrain total bend while permitting differential bending')
    native=build(h,p,ref);m=native.model;d=mujoco.MjData(m);mujoco.mj_forward(m,d)
    def verify(_):
        zero=np.array([native.point(d,b)[0] for b in native.points]);q=.01*np.sin(np.arange(m.nv))
        d.qpos[:]=q;mujoco.mj_forward(m,d)
        mount=dict(position_m=p['mount_position'],quaternion_wxyz=[2**-.5,0,2**-.5,0])
        g=geometry(native.physics,q,mount);errors=[]
        for s in p['monitor_s']:
            b=material_point(native.physics,s);point,J,bid=native.point(d,b)
            body=g['bodies'][b['body']];r=body['R']@b['position_m']
            errors.append(float(np.max(np.abs(point-body['p']-r))))
            errors.append(float(np.max(np.abs(J-body['J']-np.cross(body['A'].T,r).T))))
            native.apply_force(d,s,.1);errors.append(float(np.max(np.abs(d.qfrc_applied-.1*J[0]))))
        native.apply_force(d,.5,0.)
        return dict(status='verified',zero_positions=zero.tolist(),max_material_mapping_error=max(errors),
            tendon_length_error=float(np.max(np.abs(d.ten_length-g['lengths']))),
            tendon_jac_error=float(np.max(np.abs(native.tendon_jac(d)-g['Jlength']))),
            zero_force=bool(not np.any(d.qfrc_applied)),no_actuators=m.nu==0,
            down=bool(np.all(np.diff(zero[:,2])<=1e-10)),lateral=float(np.max(np.abs(zero[:,:2]))),
            mu_version=mujoco.__version__)
    checks,checkref=request(h,p,dict(kind='P0_geometry',candidate=ref),verify,math=1,phase='P0')
    base,br=equilibrium(h,p,ref,phase='P0')
    trials=[]
    for force in (.05,.10,.20,-.10):
        result,rr=equilibrium(h,p,ref,force=force,baseline=br,phase='P0')
        er=score(h,p,ref,br,rr,.5);trials.append(dict(force=force,raw=rr,evaluation=er,status=result['status']))
    mr=None
    if base['status']=='stable':_,mr=math(h,p,ref,br,phase='P0')
    passed=(checks['max_material_mapping_error']<1e-8 and checks['tendon_jac_error']<1e-8 and
        checks['tendon_length_error']<1e-8 and checks['zero_force'] and checks['no_actuators'] and
        checks['down'] and checks['lateral']<1e-8 and base['status']=='stable' and
        all(h.store.artifact(r['raw']).get('checks',{}).get('rope_direction',False) and
            h.store.artifact(r['raw']).get('checks',{}).get('rope_excess',False) for r in trials))
    report=dict(passed=passed,geometry=checks,geometry_ref=checkref,baseline=br,trials=trials,math=mr,
        stable_cases=[r['status']=='stable' for r in trials],force_frozen_n=p['force_n'])
    sr=save(h,report,'phs_P0_verdict');s=state(h);s['phs'].update(p0_pass=passed,p0_report=sr);update(h,phs=s['phs'])
    atomic_json(OWNER/'p0.json',report)
    return report


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['p0','status','bind']);args=parser.parse_args()
    if args.action=='p0':print(json.dumps(p0(),ensure_ascii=False))
    elif args.action=='bind':
        h,p=host();core.bind(h,reason='PHS implementation refinement; all prior evidence and costs retained');print('bound')
    else:
        h,p=host();print(json.dumps(state(h)['phs']))
