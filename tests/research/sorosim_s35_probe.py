"""Bounded S3.5 interventions from immutable S3 states; no controller rollout."""
import argparse
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time

import numpy as np
from tools.state_io import read, atomic_json
from extensions.tendon_family import mjcf  # preload XML before MATLAB DLL paths
from extensions.tendon_family.sorosim_session import SorosimSession
from extensions.tendon_family.gvs_projection import project, discretize, discretization_jacobian
from extensions.tendon_family.contracts import ResolvedGVSBasis

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT/'evidence/sorosim_control'
RAW = ARCHIVE/'loop_attempt01/closed_loop_raw'


def save(folder, name, value):
    path = folder/(name+'.json')
    if path.exists():
        raise ValueError('PRESERVE_EXISTING_EVIDENCE: '+str(path))
    atomic_json(path, value)


def norm(a, b):
    return float(np.linalg.norm(np.asarray(a)-np.asarray(b)))


def physical_probes(updates, rows, spec, remaining_only=False):
    """Three paired replays, or just the final intervention on failed-batch resume."""
    import mujoco as mj
    model = mj.MjModel.from_xml_path(str(RAW/'robot.xml'))
    physics = read(RAW/'resolved_physics.json')
    scene = read(RAW/'experiment_scene.json')
    basis = ResolvedGVSBasis.model_validate(spec['resolved_basis'])
    jids = [model.joint(j).id for j in physics['dofs']]
    qi, vi = model.jnt_qposadr[jids], model.jnt_dofadr[jids]
    aids = [model.actuator(t['entity']+'_direct_tension').id for t in physics['tendons']]
    assert model.nq == model.nv == len(qi) == 48 and model.na == 0
    assert not scene['forces'] and model.opt.timestep == .0005

    def state(q, v, t, u):
        data = mj.MjData(model)
        data.qpos[qi], data.qvel[vi], data.time, data.ctrl[aids] = q, v, t, u
        mj.mj_forward(model, data)
        return data

    def observe(data):
        J = np.zeros((3, model.nv)); Jr = np.zeros_like(J)
        mj.mj_jacSite(model, data, J, Jr, model.site('tip_site').id)
        mj.mj_energyPos(model, data); mj.mj_energyVel(model, data)
        return dict(qpos=data.qpos[qi].tolist(), qvel=data.qvel[vi].tolist(), time_s=data.time,
            position=data.site_xpos[model.site('tip_site').id].tolist(), velocity=(J@data.qvel).tolist(),
            actual_tension=(-data.actuator_force[aids]).tolist(), contacts=int(data.ncon),
            energy_j=data.energy.tolist(), qacc=data.qacc[vi].tolist(),
            actuator_force_nm=data.qfrc_actuator[vi].tolist(), passive_force_nm=data.qfrc_passive[vi].tolist())

    def advance(data):
        applied=[]
        for _ in range(20):
            mj.mj_forward(model, data); applied.append((-data.actuator_force[aids]).tolist())
            mj.mj_step(model, data)
        mj.mj_forward(model, data)
        out=observe(data); out['all_applied_tension_n']=applied
        out['warnings']=[int(w.number) for w in data.warning]
        return out

    probes=[]
    for i, update in enumerate(updates):
        t=update['time_s']; u=rows[i]['tension_n']  # actual engine force in pre-step row
        q=scene['qpos_rad'] if i==0 else rows[i-1]['qpos_rad']
        v=scene['qvel_rad_s'] if i==0 else rows[i-1]['qvel_rad_s']
        projection=project(physics,basis,q,v)
        x=projection['q_gvs']+projection['qdot_gvs']
        assert norm(x,update['measured_initial_state']) < 1e-10
        rq,rv=discretize(physics,basis,projection['q_gvs'],projection['qdot_gvs'])
        original=state(q,v,t,u); represented=state(rq,rv,t,u)
        initial=observe(original); reconstructed=observe(represented)
        actual_next=observe(state(rows[i]['qpos_rad'],rows[i]['qvel_rad_s'],t+.01,u))
        assert norm(actual_next['position'],rows[i]['tip_m'])<1e-12
        assert norm(actual_next['actual_tension'],u)<1e-12
        # At zero the reconstructed state equals the original; reuse archived next.
        represented_next=actual_next if i==0 else (advance(represented) if i==2 or not remaining_only else None)
        control=advance(original) if i==1 and not remaining_only else None
        probes.append(dict(index=i,projection=projection,x=x,u=u,original=initial,
            reconstructed=reconstructed,actual_next=actual_next,reconstructed_next=represented_next,
            original_replay=control,original_replay_error=None if control is None else dict(
                qpos=norm(control['qpos'],actual_next['qpos']),qvel=norm(control['qvel'],actual_next['qvel'])),
            represented_initial_error=dict(position_m=norm(initial['position'],reconstructed['position']),
                velocity_m_s=norm(initial['velocity'],reconstructed['velocity'])),
            projection_intervention=None if represented_next is None else dict(
                position_m=norm(actual_next['position'],represented_next['position']),
                velocity_m_s=norm(actual_next['velocity'],represented_next['velocity'])),
            original_next_source='archived full qpos/qvel; mj_forward only',
            qualifications='Memoryless direct tendon actuators, no contacts/external forces; reconstructed energy differs. '
                'qacc_warmstart was not archived; engine Newton solve is a qualification.',
            unavailable_reason='attempt01 replay outputs lost before failure persistence; budget prevents repeat'
                if remaining_only and i==1 else None))
    return dict(probes=probes,mujoco_version=mj.__version__,timestep_s=model.opt.timestep,
        gravity=model.opt.gravity.tolist(),mount=spec['mount_rotation'],replays=1 if remaining_only else 3,
        prior_failed_batch_replays=2 if remaining_only else 0,
        input_order=spec['tendon_order'],physics_identity=physics['identity'])


def casadi_reference(spec, points):
    import casadi as ca
    from extensions.tendon_family.gvs_casadi import GVSCasadiFunctions
    from extensions.tendon_family.contracts import GVSModelParameters,GVSContinuousDynamicsExpression
    design=read(RAW/'robot_description.json')['data']
    settings=read(ARCHIVE/'s2.json')['reference_settings']
    started=time.perf_counter()
    f=GVSCasadiFunctions(GVSContinuousDynamicsExpression(design=design,parameters=GVSModelParameters(**settings),
        gravity_robot_base_m_s2=spec['gravity'],coordinate_order=spec['coordinate_order'],
        tendon_order=spec['tendon_order'],tendon_force_limits_n=[r['force_limit_n'] for r in spec['routes']]))
    x=ca.MX.sym('s35_x',24); u=ca.MX.sym('s35_u',4); a=ca.MX.sym('s35_a',12)
    residual=f.implicit_residual(x,u,a)
    jac=ca.Function('s35_jac',[x,u,a],[ca.jacobian(residual,x),ca.jacobian(residual,a)])
    jp=ca.jacobian(f.tip_position_expression,f.q_symbol)
    motion=ca.Function('s35_motion',[f.q_symbol],[f.tip_position_expression,jp])
    graph_s=time.perf_counter()-started
    from scipy.optimize import root
    R=np.array(spec['mount_rotation']); mount=np.array(spec['mount_position'])
    results=[]
    for point in points:
        initial=np.array(point['x']); tension=point['u']; acceleration=np.linspace(-10,20,12)
        base=f.evaluate(initial,tension); y=initial.copy()
        def equation(next):
            acc=(next[12:]-initial[12:])/.01
            r=np.r_[(next[:12]-initial[:12]-.01*next[12:])/10,
                np.array(f.implicit_residual(next,tension,acc)).ravel()/.001]
            jx,ja=jac(next,tension,acc); jx,ja=np.array(jx),np.array(ja)
            J=np.block([[np.eye(12)/10,-.001*np.eye(12)],
                [jx[:,:12]/.001,(jx[:,12:]+ja/.01)/.001]])
            return r,J
        started=time.perf_counter();sol=root(equation,y,jac=True,tol=1e-10)
        defect=float(np.max(np.abs(equation(sol.x)[0])))
        assert defect<1e-9
        p,J=motion(sol.x[:12]); ip,iJ=motion(initial[:12])
        results.append(dict(initial=initial.tolist(),u=tension,declared_acceleration=acceleration.tolist(),
            local={k:np.asarray(v).tolist() for k,v in base.items()},
            declared_residual=np.asarray(f.implicit_residual(initial,tension,acceleration)).ravel().tolist(),
            initial_position=(R@np.array(ip).ravel()+mount).tolist(),
            initial_velocity=(R@np.array(iJ)@initial[12:]).tolist(),
            x=sol.x.tolist(),position=(R@np.array(p).ravel()+mount).tolist(),
            velocity=(R@np.array(J)@sol.x[12:]).tolist(),scaled_root_residual=defect,
            root_success=bool(sol.success),root_message=str(sol.message),integration_s=time.perf_counter()-started))
    return dict(settings=settings,graph_s=graph_s,probes=results)


def run(destination, full_update=False, remaining_only=False):
    folder=Path(destination);folder.mkdir(parents=True,exist_ok=False)
    updates=read(RAW/'nmpc_updates.json')
    rows=json.loads(gzip.decompress((RAW/'trajectory.json.gz').read_bytes()))
    spec=read(RAW/'control_spec.json')['specification']
    source_files=[*ROOT.glob('matlab/sorosim_control/*.m'),Path(__file__),
        ROOT/'extensions/tendon_family/gvs_projection.py',ROOT/'extensions/tendon_family/gvs_casadi.py',
        ROOT/'extensions/tendon_family/backends.py',*RAW.glob('*'),ARCHIVE/'s3_callbacks.json',ARCHIVE/'s2.json']
    save(folder,'provenance',dict(start_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        python=platform.python_version(),specification_identity=spec['identity'],
        files={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files if p.is_file()},
        budget=dict(full_updates=int(full_update),mujoco_replays=1 if remaining_only else 3,
            prior_failed_batch_replays=2 if remaining_only else 0,rl_training=0,provider_requests=0),
        units=dict(position='m',velocity='m/s',q='rad/m',qd='rad/(m*s)',residual='N*m^2')))
    physical=physical_probes(updates,rows,spec,remaining_only);save(folder,'physical',physical)
    print('Physical projections and bounded replays complete',flush=True)
    # Long graph build is local CPU work, outside MATLAB session timing.
    reference=casadi_reference(spec,physical['probes']);save(folder,'casadi',reference)
    print('Independent CasADi graph and matched implicit steps complete',flush=True)
    session=SorosimSession()
    try:
        with session:
            construction=session.construct(spec)
            for i,point in enumerate(physical['probes']):
                payload=dict(x=point['x'],u=point['u'],a=reference['probes'][i]['declared_acceleration'])
                kernels=session.evaluate('diagnose',dict(payload,kind='kernels'));save(folder,f'kernels_{i}',kernels)
                forward=session.evaluate('dynamics',dict(q=point['x'][:12],qd=point['x'][12:],u=point['u'],qdd=[]))
                save(folder,f'forward_{i}',forward)
                c=deepcopy(read(ARCHIVE/'s3_callbacks.json')['result']['context'])
                c.update(measured=point['x'],elapsed=updates[i]['time_s'],previous=updates[i]['mathematical_facts']['previous_input'])
                facts=updates[i]['mathematical_facts'];scales=np.array(facts['state_scale'])
                z=np.r_[(np.array(facts['states'])/scales).ravel(),(np.array(facts['tensions'])/8).ravel()]
                callbacks=session.evaluate('diagnose',dict(payload,kind='callbacks',context=c,z=z.tolist()))
                save(folder,f'callbacks_{i}',callbacks)
                integration=session.evaluate('diagnose',dict(payload,kind='integrate',period_s=.01,refinements=[1,2,4,8,16]))
                save(folder,f'integration_{i}',integration)
                print(f'Checkpoint {i}: kernels, callback cache, and integration refinements complete',flush=True)
            # Initial profiling is complete before the sole authorized optimizer run.
            if full_update:
                request=deepcopy(read(ARCHIVE/'s3_update.json')['request'])
                request.update(elapsed_s=.02,measured_state=updates[2]['measured_initial_state'],
                    previous_input=updates[2]['mathematical_facts']['previous_input'],
                    warm={k:updates[1]['mathematical_facts'][k] for k in ('states','tensions')},profile=True)
                result=session.evaluate('nmpc',request)
                save(folder,'update',dict(request=request,result=result))
                print('Sole fresh full-horizon update complete',flush=True)
            save(folder,'environment',dict(matlab=session.environment,dependency=session.dependency,construction=construction))
    finally:
        save(folder,'timings',session.timings)
    return folder


def summarize(folder, destination):
    """Recompute scalar evidence and virtual-work probes; no stepping or solves."""
    import mujoco as mj
    from schemas.platform_analysis import ScopedMathematicalClaim
    from tools.state_io import digest
    physical=read(folder/'physical.json');reference=read(folder/'casadi.json')
    spec=read(RAW/'control_spec.json')['specification'];updates=read(RAW/'nmpc_updates.json')
    physics=read(RAW/'resolved_physics.json');model=mj.MjModel.from_xml_path(str(RAW/'robot.xml'))
    mapping=discretization_jacobian(physics,ResolvedGVSBasis.model_validate(spec['resolved_basis']))
    jids=[model.joint(j).id for j in physics['dofs']];qi=model.jnt_qposadr[jids];vi=model.jnt_dofadr[jids]
    aids=[model.actuator(t['entity']+'_direct_tension').id for t in physics['tendons']]
    R=np.array(spec['mount_rotation']);mount=np.array(spec['mount_position']);table=[];local=[];pullback=[]
    for i,p in enumerate(physical['probes']):
        kernel=read(folder/f'kernels_{i}.json')['base'];old=reference['probes'][i]
        refinements=read(folder/f'integration_{i}.json')['refinements']
        if (folder/'refinement.json').exists():
            refinements+=read(folder/'refinement.json')['probes'][i]['refinements']
        one=refinements[0];fine=refinements[-1]
        pred=updates[i]['one_step_prediction'];next=p['actual_next'];rep=p['reconstructed_next']
        table.append(dict(time_s=i*.01,total_position_m=norm(pred['tip_position_m'],next['position']),
            total_velocity_m_s=norm(pred['tip_velocity_m_s'],next['velocity']),
            projection_max_rad_m=p['projection']['projection_residual_max_rad_m'],
            represented_initial_error=p['represented_initial_error'],projection_intervention=p['projection_intervention'],
            production_reintegration_position_m=norm(pred['tip_position_m'],one['position']),
            production_reintegration_velocity_m_s=norm(pred['tip_velocity_m_s'],one['velocity']),
            sorosim_gvs_position_m=norm(one['position'],old['position']),
            sorosim_gvs_velocity_m_s=norm(one['velocity'],old['velocity']),
            sorosim_gvs_q_rad_m=norm(np.array(one['x'])[:12],np.array(old['x'])[:12]),
            sorosim_gvs_qd_rad_m_s=norm(np.array(one['x'])[12:],np.array(old['x'])[12:]),
            integration_position_m=norm(one['position'],fine['position']),
            integration_velocity_m_s=norm(one['velocity'],fine['velocity']),
            last_refinement_position_m=norm(fine['position'],refinements[-2]['position']),
            last_refinement_velocity_m_s=norm(fine['velocity'],refinements[-2]['velocity']),
            last_refinement_q_rad_m=norm(np.array(fine['x'])[:12],np.array(refinements[-2]['x'])[:12]),
            last_refinement_qd_rad_m_s=norm(np.array(fine['x'])[12:],np.array(refinements[-2]['x'])[12:]),
            refined_vs_original_position_m=norm(fine['position'],next['position']),
            refined_vs_original_velocity_m_s=norm(fine['velocity'],next['velocity']),
            remaining_position_m=None if rep is None else norm(fine['position'],rep['position']),
            remaining_velocity_m_s=None if rep is None else norm(fine['velocity'],rep['velocity']),
            confidence='Matched local numerical comparison; finite refinement, nonlinear interventions are not additive; '
                'checkpoint 1 paired replay unavailable in this recorded batch.'))
        pairs=[('mass_matrix','mass_matrix'),('residual','declared_residual'),('tendon_force','tendon_generalized_force'),
            ('tip_velocity','initial_velocity')]
        errors={}
        for key,other in pairs:
            actual=R@np.array(kernel[key]) if key=='tip_velocity' else np.array(kernel[key])
            expected=np.array(old[other] if other in old else old['local'][other])
            delta=float(np.max(np.abs(actual.ravel()-expected.ravel())))
            errors[key]=dict(absolute_max=delta,relative_max=delta/max(1e-30,float(np.max(np.abs(expected)))))
        forward=read(folder/f'forward_{i}.json')
        errors['forward_acceleration']=dict(absolute_max=float(np.max(np.abs(np.array(forward['qdd'])-
            np.array(old['local']['qdd']).ravel()))),mass_condition=float(np.linalg.cond(kernel['mass_matrix'])))
        errors['forward_acceleration']['relative_max']=errors['forward_acceleration']['absolute_max']/float(np.max(np.abs(old['local']['qdd'])))
        errors['s2_probe_bounds_exceeded']=dict(
            acceleration_absolute=errors['forward_acceleration']['absolute_max']>100,
            tip_velocity_absolute=errors['tip_velocity']['absolute_max']>2e-6,
            tendon_force_absolute=errors['tendon_force']['absolute_max']>2e-7,
            scope='Comparison to historical S2 probe bounds only, not a revised acceptance rule or uniform guarantee.')
        errors['initial_position_m']=norm(R@np.array(kernel['tip_position'])+mount,old['initial_position'])
        errors['initial_reduced_vs_reconstructed_position_m']=norm(R@np.array(kernel['tip_position'])+mount,p['reconstructed']['position'])
        errors['initial_reduced_vs_reconstructed_velocity_m_s']=norm(R@np.array(kernel['tip_velocity']),p['reconstructed']['velocity'])
        local.append(errors)
        data=mj.MjData(model);data.qpos[qi]=p['reconstructed']['qpos'];data.qvel[vi]=p['reconstructed']['qvel']
        data.ctrl[aids]=p['u'];mj.mj_forward(model,data);M=np.empty((model.nv,model.nv));mj.mj_fullM(model,data,M)
        L=np.zeros((model.nv,12));L[vi]=mapping
        reduced_mass=L.T@M@L
        passive=L.T@data.qfrc_passive;tendon=L.T@data.qfrc_actuator;bias=L.T@data.qfrc_bias
        # Virtual-work restriction is an instantaneous diagnostic, not a new backend.
        pullback.append(dict(mass_matrix=reduced_mass.tolist(),passive_force=passive.tolist(),
            tendon_force=tendon.tolist(),bias_minus_gravity=bias.tolist(),
            constraint_dimension=int(data.nefc),constraint_force_max_nm=float(np.max(np.abs(data.qfrc_constraint))),
            actuator_state_dimension=model.na,
            mass_relative_fro=float(np.linalg.norm(reduced_mass-kernel['mass_matrix'])/np.linalg.norm(kernel['mass_matrix'])),
            passive_difference_nm2=norm(passive,-np.array(kernel['elastic_force'])-np.array(kernel['viscous_force'])),
            tendon_difference_nm2=norm(tendon,kernel['tendon_force']),
            balance_difference_nm2=norm(bias-passive-tendon,np.array(kernel['residual'])-
                np.array(kernel['mass_matrix'])@np.array(old['declared_acceleration'])),
            qualification='Same represented cells and virtual-work map; mass, joint forces, geometry and modes interact. '
                'No isolated attribution to connector/payload inertia or distributed mass.'))
    claim=ScopedMathematicalClaim(conclusion='diagnostic',binding=dict(physics_identity=physics['identity']),
        requirement_identity=digest(read(RAW/'control_spec.json')['task']),model_identity=spec['identity'],
        model_declaration=dict(predictor=spec['model'],reference='GVS CasADi at S2 200-step resolution',execution='frozen MuJoCo XML'),
        protocol_identity=digest(dict(period_s=.01,refinements=[1,2,4,8,16,32,64]
            if (folder/'refinement.json').exists() else [1,2,4,8,16],input='recorded actual force')),
        operating_point=dict(checkpoints_s=[0,.01,.02]),horizon=dict(period_s=.01),
        physical_inputs=dict(order=spec['tendon_order'],bounds_n=[0,8]),constraint_coverage=[],
        numerical_result_pointer='/raw_facts/checkpoints',computation_status='returned',verification_status='passed_local_checks',
        supported_interpretation='Matched implementation, integration and represented-state interventions at three saved checkpoints only.',
        unsupported_conclusions=['additive causal decomposition','unique dominant physics cause','physical task success',
            'global optimality','uniform transient accuracy','S4-S6 completion'])
    measured=read(folder/'update.json')['result'] if (folder/'update.json').exists() else None
    kernels=[]
    for i in range(3):
        k=read(folder/f'kernels_{i}.json');timing=np.median(k['warmed_s'],axis=0)
        kernels.append(dict(first_s=k['first_s'],median_derivative_s=timing[0],median_routing_s=timing[1],
            median_dynamics_s=timing[2],median_base_routing_s=timing[3],profiled_s=k['profiled_s'],
            profiled_to_warmed_ratio=k['profiled_s']/timing[0]))
    performance=dict(kernels=kernels,
        historical=[{k:o['mathematical_facts'][k] for k in ('elapsed_s','warm_preparation_s','optimization_s',
            'validation_s','iterations','function_evaluations','initial_objective','objective')} for o in updates],
        fresh=None if measured is None else {k:measured[k] for k in ('warm_preparation_s','optimization_s',
            'validation_s','update_s','iterations','function_evaluations','exitflag','callback_profile')},
        mean_distinct_evaluation_s=None if measured is None else measured['callback_profile']['evaluation_s']/measured['callback_profile']['misses'])
    value=dict(raw_facts=dict(checkpoints=table,local_implementation=local,virtual_work_probes=pullback,performance=performance),
        verified_conclusions=[claim.model_dump(mode='json')],research_interpretations=[dict(status='inconclusive',
            hypothesis='Remaining discrepancy combines rigid-cell versus rod mechanics and unresolved finite-step effects; '
                'local virtual-work differences do not establish a unique trajectory cause.')])
    save(destination.parent,destination.stem,value)
    return value


def refine(folder):
    """Two further integration resolutions after inspecting the initial sequence."""
    physical=read(folder/'physical.json');spec=read(RAW/'control_spec.json')['specification'];results=[]
    with SorosimSession() as session:
        session.construct(spec)
        for i,p in enumerate(physical['probes']):
            results.append(session.evaluate('diagnose',dict(kind='integrate',x=p['x'],u=p['u'],
                a=[0]*12,period_s=.01,refinements=[32,64])))
            print(f'Checkpoint {i}: final integration refinement complete',flush=True)
    save(folder,'refinement',dict(probes=results,timings=session.timings,environment=session.environment))


def calibrate(folder):
    """Small serialization and line-profile batch; no solve or physical step."""
    physical=read(folder/'physical.json');p=physical['probes'][2]
    sample=read(folder/'update.json')['result'];times=[]
    for _ in range(3):
        t=time.perf_counter();encoded=json.dumps(sample,allow_nan=False);encode=time.perf_counter()-t
        t=time.perf_counter();json.loads(encoded);times.append([encode,time.perf_counter()-t])
    with SorosimSession() as session:
        session.construct(read(RAW/'control_spec.json')['specification'])
        args=dict(x=p['x'],u=p['u'],a=np.linspace(-10,20,12).tolist())
        kernels=session.evaluate('diagnose',dict(args,kind='kernels'))
        serialization=session.evaluate('diagnose',dict(args,kind='serialization',sample=sample))
    save(folder,'calibration',dict(kernels=kernels,serialization=serialization,python_encode_decode_s=times,
        timings=session.timings,scope='Serialization microbenchmark of same returned data; live dispatch remains aggregated.'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('destination',type=Path)
    parser.add_argument('--full-update',action='store_true')
    parser.add_argument('--remaining-replay-only',action='store_true')
    parser.add_argument('--summarize',type=Path);parser.add_argument('--refine',action='store_true')
    parser.add_argument('--calibrate',action='store_true');args=parser.parse_args()
    new_batch=not args.destination.exists()
    try:
        if args.summarize:
            summarize(args.destination,args.summarize)
        elif args.refine:
            refine(args.destination)
        elif args.calibrate:
            calibrate(args.destination)
        else:
            run(args.destination,args.full_update,args.remaining_replay_only)
    except BaseException as exc:
        if new_batch and args.destination.is_dir():
            save(args.destination,'failure',dict(type=type(exc).__name__,error=str(exc)))
        raise
