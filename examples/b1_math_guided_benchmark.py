"""B1 numerical experiment recipe; reuses family, search, T1/T2 and evaluator kernels.

Run as a module. No provider requests, historical solutions, or alternate evaluator.
Each named experiment writes once; reruns require a new name.
"""
import argparse
from copy import deepcopy
import json
import time

import mujoco
import numpy as np
from scipy.optimize import least_squares

from tools.state_io import read, atomic_json, digest
from tools.platform_store import plain, Store
from tools.research.config import ROOT, resolve
from extensions.tendon_family.family_space import parse_build
from extensions.tendon_family.generated_serial import generate_family
from extensions.tendon_family.mujoco_analysis import NativeModel
from tools.research.contracts import LocalControlSearchSettings
from tools.research.control_correction import task_measure, corrected_tensions
from tools.research.local_control_search import search, SearchStopped
from tools.research.nonlinear_capability import t1_summary
from tools.research.physical_replay import model_context, binding, evaluate_playback
from tools.research_tasks import task_adapter, assemble_acceptance

OUT = ROOT/'evidence/b1_math_guided_benchmark_discovery'
ARCHIVE = Store(ROOT/'runs/b1_math_guided_benchmark_discovery/archive')


def save(name, value):
    path=OUT/(name+'.json')
    if path.exists():
        raise FileExistsError(path)
    ref=ARCHIVE.put_context_checkpoint(value)
    atomic_json(path,value)
    print(json.dumps(dict(saved=name,archive_reference=ref)),flush=True)


def configuration(frozen, radius, target):
    cfg=deepcopy(frozen['configuration_scaffold'])
    request=deepcopy(frozen['neutral_request'])
    # Derived polar norms can round below the inclusive family lower bound.
    # Keep the requested 14 mm endpoint within two representable SI increments.
    if radius==frozen['family_space']['routing_domains']['radius_m']['minimum']:
        radius=float(np.nextafter(np.nextafter(radius,np.inf),np.inf))
    for span in request['spans']:span['radius_m']=radius
    build=parse_build(dict(space=frozen['family_space'],request=request))
    robot,mesh,physics=generate_family(build)
    cfg['robot']['structure']['data']=robot
    cfg['policy']['discretization']['data']=mesh
    cfg['policy']['candidate_builder']=dict(extension_id='candidate.family',version='5.0.0',
        parameters=dict(contract='family.serial_space_build',version='1.0.0',data=plain(build)))
    cfg['task']['initializer']['parameters']['data']={
        **{f:{j:0. for j in physics['dofs']} for f in ('qpos_rad','qvel_rad_s')},'unspecified':'zero'}
    cfg['task']['goal']['data']['target_m']=frozen['targets_m'][target]
    cfg['task']['task_id']='b1-v1-'+target
    return cfg


def freeze():
    from extensions.tendon_family.gvs import forward_kinematics
    spec=resolve(ROOT/'configs/research/study_family_space_dev.json')
    cfg=spec['configuration']
    cfg['task']['timing']['duration_s']=.7
    cfg['task']['sampling']['window_s']=[0.,.7]
    cfg['task']['source']='B1 v1 cold-start workspace coverage, frozen before dynamics search'
    f=dict(base_commit='a654a7b4f7f54a368f4b390550720ed7b250a4c5',
        configuration_scaffold=cfg,family_space=spec['family_space'],
        neutral_request=dict(family_space_identity=spec['family_space_identity'],tendon_count=6,
            spans=[dict(last_segment=0,count=3,radius_m=.018),
                   dict(last_segment=1,count=3,phase_rad=float(np.pi/3),radius_m=.018)]),
        targets_m=dict(plus_y=[.276,.075,.150],minus_y=[.276,-.075,.150],up_z=[.276,0.,.225]),
        target_order=['plus_y','minus_y','up_z'],
        initial_candidates_radius_m=[.018,.016,.020],
        structure_domain=dict(radius_m=[.014,.023],fixed='all other neutral family choices'),
        control_initialization=dict(kind='constant_pretension',tension_n=.2),
        unguided_order_radius_m=[.014,.022],
        guided_rule='After common neutral state, paired T1 at .016/.020; choose .022 if larger radius improves worst target, else .014. Charge all diagnostic T1s.',
        acceptance='all three independent offline_reach_hold_v1 acceptances AND exactly equal robot structure; no mean score',
        development_calibration='geometry-only inverse kinematics; no physical target-performance screening',
        stopping='Stop primary feasibility search at first independently accepted complete group; P2 only paired diagnostic controls as necessary',
        settings=dict(version='local_control_search_v2',method='response',correction_window_s=[0.,.7],
            knots_s=[0.,.2,.5,.69],coefficient_limit_n=8.,difference_step_n=.02,
            initial_radius_n=1.,minimum_radius_n=.0001,evaluation_requests=101,iterations=4,safety_margin_fraction=.05))
    c=configuration(f,.018,'plus_y');design=c['robot']['structure']['data']
    p0=np.asarray(forward_kinematics(design,np.zeros(8))['tip_position_m'])+np.array([0,0,.15])
    checks={}
    started=time.perf_counter()
    for name,target in f['targets_m'].items():
        def position(q):
            return np.asarray(forward_kinematics(design,q,samples_per_segment=2)['tip_position_m'])+np.array([0,0,.15])
        seed=np.array([-.5,0,1.,0,-.5,0,1.,0])
        fit=least_squares(lambda q:position(q)-target,seed,bounds=(-20,20),max_nfev=80,
            ftol=1e-10,xtol=1e-10,gtol=1e-10)
        checks[name]=dict(target_m=target,achieved_m=position(fit.x).tolist(),q_rad_m=fit.x.tolist(),
            error_m=float(np.linalg.norm(fit.fun)),evaluations=fit.nfev,
            interpretation='nonlinear geometric witness only; not force/dynamic feasibility')
    f['geometry_precheck']=dict(initial_tip_m=p0.tolist(),checks=checks,wall_s=time.perf_counter()-started,
        rationale='75 mm lateral/upward displacement with 22 mm axial shortening; nonlinear bent configurations, not initial tangent-plane targets',
        rejected_route='coangular near/full spans failed TENDON_ATTACHMENT_CLEARANCE before any rollout; interlace 60 degrees')
    save('frozen_v1',f)
    print(json.dumps(f['geometry_precheck']),flush=True)


def optimize(f, radius, target, settings):
    cfg=configuration(f,radius,target);started=time.perf_counter()
    native=NativeModel(cfg);d=mujoco.MjData(native.model)
    d.qpos[native.qi]=native.scene['qpos_rad'];d.qvel[native.vi]=native.scene['qvel_rad_s'];native.forward(d)
    inp,physics,scene,spec=model_context(cfg)
    count=round(.7/.01);times=np.arange(count+1)*.01
    original=dict(source_kind='explicit_control_schedule_v1',provenance=dict(initialization='cold_constant_0.2_N'),
        trajectory=dict(times_s=times.tolist(),tensions_n=np.full((count,len(native.tendons)),.2).tolist(),
            tendon_order=native.tendons,model_identity=spec['identity'],design_identity=spec['design_identity'],task_identity=digest(cfg['task'])))
    adapter=task_adapter(cfg);limits=adapter.ranking_limits()
    options=dict(target=f['targets_m'][target],holding_start=adapter.holding_start_s(),
        position_limit=limits['holding_max_error_m'],terminal_position_limit=limits['terminal_error_m'],speed_limit=limits['holding_max_speed_m_s'])
    initial=dict(id='cold',schedule=original,limits=native.limits[:,1].tolist(),task_options=options)
    failures=[]
    def evaluate(_start,schedule,meta):
        try:
            outputs=native.rollout_sequence(d,times,schedule['trajectory']['tensions_n'])
        except ValueError as error:
            if str(error)!='NATIVE_V1_REQUIRES_FINITE_CONTACT_FREE_UNCONSTRAINED_STATE':raise
            failures.append(dict(reason=str(error),metadata=meta,schedule=schedule,cost_so_far=dict(native.cost)))
            raise SearchStopped('native_contact_free_domain_exit') from error
        measure=task_measure(outputs,**options)
        return dict(reference='native-'+str(native.cost['rollouts']),outputs=outputs,measure=measure,
            task_gap=dict(valid_complete=True,accepted=False,normalized_gap=measure['normalized_gap']),cost_s=0.)
    result=search([initial],evaluate,settings,evaluation_kind='native_short_rollout',
        rank_key=lambda row:(row['measure']['signed_maximum_excess'],row['measure']['sum_normalized_excess']),
        stop_when=lambda row:row['measure']['signed_maximum_excess']<=-settings.safety_margin_fraction)
    best=result['best'];schedule=deepcopy(original)
    schedule['trajectory']['tensions_n']=corrected_tensions(original['trajectory']['tensions_n'],times[:-1],settings.knots_s,
        best['coefficients_n'],native.limits[:,1],settings.correction_window_s).tolist()
    cost=dict(**native.cost,kernel_wall_s=time.perf_counter()-started)
    value=dict(binding=dict(tension_bounds_n=native.limits.tolist()),native_dynamics=dict(optimization=result,
        optimized_schedule=schedule,cost=cost))
    summary=t1_summary(value,settings)
    return dict(configuration=cfg,schedule=schedule,initial_outputs=result['candidates'][0]['outputs'],
        best_outputs=best['outputs'],t1=summary,cost=cost,failed_proposals=failures,
        search={**result,'candidates':[{k:v for k,v in r.items() if k!='outputs'} for r in result['candidates']],
            'best':{k:v for k,v in best.items() if k!='outputs'},'start_feedback':[]})


def run(args):
    f=read(OUT/'frozen_v1.json');settings=LocalControlSearchSettings.model_validate({**f['settings'],
        'evaluation_requests':args.evaluations,'iterations':args.iterations})
    results={}
    for target in ([args.target] if args.target else f['target_order']):
        row=optimize(f,args.radius,target,settings)
        save(args.name+'_'+target,row)
        results[target]=dict(t1=row['t1'],cost=row['cost'])
        print(json.dumps(dict(target=target,J=row['t1']['J'],stop=row['t1']['stop_reason'],cost=row['cost'])),flush=True)
    if args.target:
        results={target:{key:read(OUT/(args.name+'_'+target+'.json'))[key] for key in ('t1','cost')}
            for target in f['target_order']}
    save(args.name+'_group',dict(radius_m=args.radius,results=results,
        J=max(r['t1']['J'] for r in results.values()),settings=plain(settings),
        cost={k:sum(r['cost'][k] for r in results.values()) for k in results['plus_y']['cost']}))


def replay(args):
    from extensions.tendon_family.backends import playback_tensions
    results={};robot=None;label=args.replay_name or args.name
    for target in read(OUT/'frozen_v1.json')['target_order']:
        row=read(OUT/(args.name+'_'+target+'.json'));cfg=row['configuration'];schedule=row['schedule']
        structure=cfg['robot']['structure']
        if robot is None:robot=structure
        assert robot==structure
        inp,physics,scene=binding(cfg,schedule['trajectory']);started=time.perf_counter()
        folder=ROOT/'runs/b1_math_guided_benchmark_discovery'/('replay_'+label+'_'+target)
        raw=playback_tensions(inp,physics,scene,schedule['trajectory']['tensions_n'],folder)
        ref=ARCHIVE.put_context_checkpoint(raw)
        evaluation,profile=evaluate_playback(cfg,raw,ref,'b1-independent-'+label+'-'+target)
        acceptance=assemble_acceptance(cfg,evaluation,profile,motion=raw['samples'])
        results[target]=dict(acceptance=acceptance,evaluation=plain(evaluation),profile=profile,raw=raw,
            cost=dict(rollouts=1,physics_steps=raw['physics_steps'],wall_s=time.perf_counter()-started))
        print(json.dumps(dict(target=target,accepted=acceptance['accepted'],metrics=acceptance['metrics'])),flush=True)
    save(label+'_independent',dict(accepted=all(r['acceptance']['accepted'] is True for r in results.values()),
        same_structure=True,results=results,scope='fresh backend model, original initializer, registered evaluator plus original Reach/Hold protocol'))


def gvs(args):
    from tools.research.analysis import calculate
    from tools.research.contracts import AnalysisRequest
    from extensions.tendon_family.gvs_basis import resolve_basis
    f=read(OUT/'frozen_v1.json');started=time.perf_counter()
    cfg=configuration(f,args.radius,'up_z');ref=ARCHIVE.put_context_checkpoint(cfg)
    tendons=cfg['robot']['structure']['data']['tendons']
    bound=dict(candidate_id='b1-cold-radius-'+str(args.radius),candidate=ref,configuration=ref,
        task_identity=digest(cfg['task']),effective_configuration_identity=digest(cfg),
        evaluation_profile_identity='b1-v1-original-reach-hold',source_identity=digest(f['neutral_request']),
        basis=cfg['policy']['controller']['parameters']['data']['recipe']['basis'],
        tension_limits_n=[t['force_limit_n'] for t in tendons],tendon_order=[t['id'] for t in tendons])
    bound['coordinate_order']=list(resolve_basis(cfg['robot']['structure']['data'],bound['basis']).coordinate_order)
    p=resolve(ROOT/'configs/research/study_family_space_dev.json')['analysis_protocol']
    p.update(duration_s=.7,windows_s=[.05,.1,.7],samples_s=[0.,.2,.5,.65,.69])
    q=AnalysisRequest(candidate=ref,operation='task_capability',operating_point='standardized_initial_pretension',
        protocol=p,capability_method='sampled-affine-conic-minimax-v1')
    result=calculate(cfg,bound,q)
    save(args.name,dict(result=result,cost=dict(wall_s=time.perf_counter()-started,model_builds=1,
        mujoco_rollouts=0,mujoco_physics_steps=0),
        interpretation='GVS T1 in the declared initial affine model only; inspect axial-output degeneracy before structural use'))
    print(json.dumps(dict(status=result['status'],J=result.get('trajectory',{}).get('replayed_violation'),
        conclusion=result.get('scoped_claim',{}).get('conclusion'))),flush=True)


def diagnose():
    from tools.research.nonlinear_capability import response
    from extensions.math_analysis.task_capability import task_capability
    from schemas.platform_analysis import EndpointLinearizedModel,TaskAnalysisRequirement,TaskAnalysisProtocol
    from extensions.tendon_family.backends import playback_tensions
    def diagnostic_playback(cfg,controls,folder):
        inp,physics,scene,_=model_context(cfg);started=time.perf_counter()
        snapshot=folder/'numerical_failure.json'
        recovered=snapshot.exists()
        if not recovered:
            try:return playback_tensions(inp,physics,scene,controls,folder),time.perf_counter()-started
            except ValueError as error:
                if str(error)!='MUJOCO_NUMERICAL_FAILURE':raise
        failure=read(snapshot)
        return dict(status='incomplete',samples=read(folder/'samples.json'),
            physics_steps=failure['confirmed_completed_steps'],failed_step_calls=1,
            tendon_order=[t['entity'] for t in physics['tendons']],failure=failure,
            recovered_saved_failure=recovered),None if recovered else time.perf_counter()-started
    f=read(OUT/'frozen_v1.json');t2={};started=time.perf_counter()
    for target in f['target_order']:
        rows=[]
        for name,radius in [('neutral101',.018),('radius016_101',.016),('radius020_101',.020)]:
            row=read(OUT/(name+'_'+target+'.json'))
            assert row['configuration']['task']==configuration(f,.018,target)['task']
            rows.append(dict(value=radius,t1=row['t1'],cost=row['cost'],
                candidate=ARCHIVE.put_context_checkpoint(row['configuration']),
                reference=ARCHIVE.put_context_checkpoint(row)))
        t2[target]=response(dict(rows=rows,parameter=dict(units='m',name='both span radii'),
            derivative_scope='coupled path r_near=r_full, other generated choices fixed'))
    if not (OUT/'native_t2_radius.json').exists():
        save('native_t2_radius',dict(results=t2,cost=dict(wall_s=time.perf_counter()-started,
            rollouts=0,physics_steps=0),interpretation='Direct existing T2 kernel on explicit saved T1 inputs; referenced T1 costs already charged'))
    source=read(OUT/'gvs_initial018.json')['result']
    model=EndpointLinearizedModel.model_validate(source['model'])
    req=TaskAnalysisRequirement.model_validate(source['task_analysis'])
    protocol=TaskAnalysisProtocol.model_validate(source['protocol'])
    row=read(OUT/'neutral101_up_z.json');started=time.perf_counter()
    affine=task_capability(model,req,protocol,applied_input_n=row['schedule']['trajectory']['tensions_n'])
    gvs_controls=source['trajectory']['applied_input_n']
    raw,playback_wall=diagnostic_playback(row['configuration'],gvs_controls,ROOT/'runs/b1_math_guided_benchmark_discovery/gvs_control')
    from tools.research.control_correction import task_outputs
    real=task_outputs(raw)
    options=dict(target=f['targets_m']['up_z'],holding_start=.65,position_limit=.01,speed_limit=.02)
    save('same_input_affine_native',dict(native_control_affine_prediction=affine,
        native_control_native_measure=row['t1']['best_metrics'],
        gvs_control_native_outputs=real,gvs_control_native_raw=raw,
        gvs_control_native_measure=task_measure(real,**options) if raw['status']=='completed' else None,
        gvs_control_affine_J=source['trajectory']['replayed_violation'],
        initial_axial_C_norm=float(np.linalg.norm(np.asarray(model.C)[0])),
        cost=dict(rollouts=1,physics_steps=raw['physics_steps'],failed_step_calls=raw.get('failed_step_calls',0),
            playback_wall_s=playback_wall,recovery_and_affine_wall_s=time.perf_counter()-started),
        scope='identical initial state and input; GVS affine initial-output linearization versus full nonlinear MuJoCo'))
    row=read(OUT/'radius016_101_up_z.json');proposal=row['failed_proposals'][0]['schedule']
    binding(row['configuration'],proposal['trajectory']);started=time.perf_counter()
    raw,playback_wall=diagnostic_playback(row['configuration'],proposal['trajectory']['tensions_n'],
        ROOT/'runs/b1_math_guided_benchmark_discovery/contact_proposal016')
    ref=ARCHIVE.put_context_checkpoint(raw)
    evaluation,profile=evaluate_playback(row['configuration'],raw,ref,'b1-contact-diagnostic')
    acceptance=assemble_acceptance(row['configuration'],evaluation,profile,motion=raw['samples'])
    native=NativeModel(row['configuration']);contacts=[]
    for sample in raw['samples']:
        d=mujoco.MjData(native.model);d.qpos[native.qi]=sample['qpos_rad'];d.qvel[native.vi]=sample['qvel_rad_s']
        mujoco.mj_forward(native.model,d)
        if d.ncon:
            contacts.append(dict(time_s=sample['time_s'],ncon=d.ncon,nefc=d.nefc,
                pairs=[[native.model.geom(int(c.geom1)).name,native.model.geom(int(c.geom2)).name] for c in d.contact]))
    save('contact_proposal016_independent',dict(raw=raw,acceptance=acceptance,evaluation=plain(evaluation),
        profile=profile,contacts=contacts,cost=dict(rollouts=1,physics_steps=raw['physics_steps'],
            model_builds=2,forward_state_checks=len(raw['samples']),wall_s=time.perf_counter()-started),
        interpretation='Full backend can execute contacts; NativeModel declines this domain. Failed optimizer proposal is not proof of structural infeasibility.'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['freeze','run','replay','gvs','diagnose'])
    parser.add_argument('--name',default='neutral101');parser.add_argument('--radius',type=float,default=.018)
    parser.add_argument('--replay-name',help='New output label for independent replay of an existing source')
    parser.add_argument('--target',choices=['plus_y','minus_y','up_z'])
    parser.add_argument('--evaluations',type=int,default=101);parser.add_argument('--iterations',type=int,default=4)
    args=parser.parse_args()
    # Reject existing output names before numerical work or backend file writes.
    if args.command=='freeze':outputs=['frozen_v1']
    elif args.command=='run':
        targets=[args.target] if args.target else ['plus_y','minus_y','up_z']
        outputs=[args.name+'_'+target for target in targets]+[args.name+'_group']
    elif args.command=='replay':outputs=[(args.replay_name or args.name)+'_independent']
    elif args.command=='gvs':outputs=[args.name]
    else:outputs=['contact_proposal016_independent']
    for name in outputs:
        if (OUT/(name+'.json')).exists():raise FileExistsError(OUT/(name+'.json'))
    if args.command=='freeze':freeze()
    elif args.command=='run':run(args)
    elif args.command=='replay':replay(args)
    elif args.command=='gvs':gvs(args)
    else:diagnose()


if __name__=='__main__':main()
