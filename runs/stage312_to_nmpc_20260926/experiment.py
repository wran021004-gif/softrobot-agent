"""Deterministic sampled LQR, dynamic optimization and public-path NMPC evidence."""
import argparse
import gzip
import json
import sys
import time
from copy import deepcopy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
from agreement_cost import HERE, ROUTE, SOURCE, read, store
from extensions.tendon_family.backends import MujocoBackend, physics_for
from extensions.tendon_family.contracts import GVSModelParameters, LQRParameters, ResolvedGVSBasis
from extensions.tendon_family.gvs import GVSModel
from extensions.tendon_family.gvs_projection import discretize, project
from extensions.tendon_family.gvs_sampled import DiscreteLQRController, zero_order_hold
from schemas.platform import Binding, Payload, SessionInput
from schemas.platform_math import LinearizedModel, SystemContext
from tools.platform_registry import registry
from tools.platform_tasks import compile_input
from tools.state_io import atomic_json, digest

HISTORY=ROOT/'runs/stage36_controller_attribution_20260924/controller_failure_attribution.json'
BACKEND=ROOT/'runs/stage35_case_b_retry_softagent_20260924/sessions/stage35-case-b-retry-softagent-44efe3ecec6b6acb/executions/5e0f73882b1846edbefb893a84c34d10/backend'


def context(refine_operating_point=False):
    raw=read(ROUTE); frozen=read(SOURCE)['frozen_reference']; saved=read(BACKEND/'control_spec.json')
    raw['policy']['route']=None
    raw['policy']['controller']=dict(extension_id='controller.gvs_sampled_lqr',parameters=dict(
        contract='family.gvs_lqr_control',data=saved['effective_parameters']))
    raw['policy']['controller']['parameters']['data']['task_feedback_gain']=0.
    raw['policy']['discretization']=dict(contract='family.discretization',data=dict(cells={'near':12,'far':12}))
    raw['policy']['model']=dict(adapter='offline')
    raw['policy']['allowed_tools']=['simulation.run','evaluation.run']
    raw['policy']['tool_bindings']={'simulation.run':'1.0.0','evaluation.run':'1.0.0'}
    raw['policy']['budget']=dict(tool_calls=6,model_calls=0,backend_solves=1,worker_calls=0,wall_s=21600.)
    raw['policy']['timeout_s']=20000.
    # Reuse the exact candidate-owned inverse/equilibrium artifact. The public
    # resolver verifies its candidate cache key; no new target or equilibrium.
    from extensions.tendon_family.gvs_lqr import _OPERATING_POINTS
    point=saved['reference']['derivation']
    _OPERATING_POINTS[point['candidate_model_identity']]=deepcopy(point)
    inp=SessionInput.model_validate(raw)
    params=GVSModelParameters.model_validate(frozen['gvs_parameters'])
    system=GVSModel(params).build_system(inp.robot,params,None,SystemContext(
        x0=[*frozen['q0'],*([0.]*12)],u0=frozen['u0_n'],scene=inp.task.environment))
    if refine_operating_point:
        from extensions.tendon_family.gvs_casadi import expression_from_system,functions_for
        f=functions_for(expression_from_system(system));q=np.array(frozen['q0']);u=np.array(frozen['u0_n'])
        original=q.copy()
        for _ in range(4):
            drift=f.evaluate(np.r_[q,np.zeros(12)],u)['xdot'].ravel()
            if np.max(abs(drift))<=1e-7:break
            residual,jac=f.equilibrium_terms(q,u);q-=np.linalg.solve(jac,residual.ravel())
        if np.max(abs(drift))>1e-7:raise ValueError('CURRENT_NUMERICAL_EQUILIBRIUM_REFINEMENT_FAILED')
        if np.any(q!=original):
            point=deepcopy(point);point.update(q0=q.tolist(),source='saved_inverse_point_precision_refinement',
                parent_operating_point_identity=point['identity'],precision_refinement_q_change=(q-original).tolist())
            point.pop('identity');point['identity']=digest(point)
            _OPERATING_POINTS[point['candidate_model_identity']]=point
        atomic_json(HERE/'operating_point_current.json',dict(point=point,drift_inf=float(np.max(abs(drift))),
            q_change_norm=float(np.linalg.norm(q-original)),note='New derived artifact for stable small-angle evaluation; frozen evidence remains unchanged.'))
    return raw, frozen, system


def summarize(rows, observations, physics, basis, target, q0):
    projections=[project(physics,basis,r['qpos_rad'],r['qvel_rad_s']) for r in rows]
    errors=[float(np.linalg.norm(np.asarray(r['tip_m'])-target)) for r in rows]
    tensions=np.array([r['tension_n'] for r in rows])
    return dict(terminal_error_m=errors[-1],minimum_error_m=min(errors),maximum_error_m=max(errors),
        tip_error_m=errors, final_projected_q_distance=float(np.linalg.norm(np.asarray(projections[-1]['q_gvs'])-q0)),
        max_projection_residual_rad_m=max(p['projection_residual_max_rad_m'] for p in projections),
        max_rate_projection_residual_rad_m_s=max(p['rate_projection_residual_max_rad_m_s'] for p in projections),
        min_tension_n=float(tensions.min()),max_tension_n=float(tensions.max()),
        saturated_updates=sum(any(o.get('lqr_tension_saturated',o.get('force_limit_saturated',[]))) for o in observations),
        initial_tip_error_m=float(np.linalg.norm(np.asarray(observations[0]['tip_position_m'])-target)),
        initial_projected_q_distance=float(np.linalg.norm(np.asarray(observations[0]['gvs_q'])-q0)))


def public_run(raw,label,run_suffix=''):
    from tools.platform_host import Host
    raw=deepcopy(raw);raw['run_id']='stage312-'+label+run_suffix
    inp=SessionInput.model_validate(compile_input(raw)['input'])
    db=store(); host=Host(HERE,inp.run_id); host.create(inp.model_dump(mode='json'))
    start=time.perf_counter()
    sim=host.invoke(dict(request_id='simulate',tool_id='simulation.run',tool_version='1.0.0',
        arguments=dict(candidate_id=label,changes={}),cache='new',reason='User-authorized deterministic control validation'))
    atomic_json(HERE/(label+'_simulation_receipt.json'),sim)
    if sim['execution_status']!='completed': raise RuntimeError(str(sim))
    ev=host.invoke(dict(request_id='evaluate',tool_id='evaluation.run',tool_version='1.0.0',
        arguments=dict(result=sim['output'],execution_id=sim['execution_id']),cache='new',reason='Authoritative independent task evaluation'))
    atomic_json(HERE/(label+'_evaluation_receipt.json'),ev)
    if ev['execution_status']!='completed': raise RuntimeError(str(ev))
    result=db.artifact(sim['output']);evaluation=db.artifact(ev['output'])
    folder=HERE/'sessions'/inp.run_id/'executions'/sim['execution_id']/'backend'
    with gzip.open(folder/'trajectory.json.gz','rt',encoding='utf8') as f: rows=json.load(f)
    obs=read(folder/'controller_observations.json');physics=read(folder/'resolved_physics.json')
    basis=ResolvedGVSBasis.model_validate(read(SOURCE)['frozen_reference']['resolved_basis'])
    summary=summarize(rows,obs,physics,basis,inp.task.goal.data['target_m'],read(SOURCE)['frozen_reference']['q0'])
    summary.update(evaluation=evaluation,solver_status=result['solver_status'],wall_s=time.perf_counter()-start,
        backend_folder=str(folder.relative_to(ROOT)),timings=result['data']['data']['timings_s'],observations=obs)
    atomic_json(HERE/(label+'.json'),summary)
    print(label,{k:summary[k] for k in ('terminal_error_m','max_projection_residual_rad_m','saturated_updates','wall_s','solver_status')},flush=True)
    return summary


def baseline():
    raw,frozen,system=context(refine_operating_point=True); saved=read(HISTORY);chain=saved['chain']
    linear=LinearizedModel(state_definition=system.state_definition,input_definition=system.input_definition,
        output_definition=system.output_definition,x0=chain['x0'],u0=chain['u0'],A=chain['A'],B=chain['B'],
        drift=[0.]*24,time_domain='continuous')
    discrete=zero_order_hold(linear,.01)
    params=LQRParameters(Q=np.diag(chain['Q_diagonal']).tolist(),R=np.diag(chain['R_diagonal']).tolist(),
        tendon_order=chain['tendon_order'],force_limits_n=chain['force_limits_n'])
    controller=DiscreteLQRController(params);K=controller.configure_model(discrete)
    A,B,Kc=map(np.asarray,(chain['A'],chain['B'],chain['K']));Ad,Bd=map(np.asarray,(discrete.A,discrete.B))
    atomic_json(HERE/'sampled_linear.json',dict(continuous_max_real_eigenvalue=float(max(np.linalg.eigvals(A-B@Kc).real)),
        historical_held_spectral_radius=float(max(abs(np.linalg.eigvals(Ad-Bd@Kc)))),
        sampled_spectral_radius=controller.spectral_radius,K=K.tolist(),discrete=discrete.model_dump(mode='json'),
        historical_identity=saved['identities'],period_s=.01,physics_step_s=.0005,
        note='Saved matrices assert the documented refined equilibrium. Public synthesis below reevaluates continuous drift and checks it before ZOH. Pure LQR; optional task feedback disabled.'))
    atomic_json(HERE/'system.json',system.model_dump(mode='json'))
    basis=ResolvedGVSBasis.model_validate(frozen['resolved_basis']);p=physics_for(SessionInput.model_validate(raw))
    summaries={}
    for name,fraction in [('lqr_nominal',0.),('lqr_perturbation',.01),('lqr_task',1.)]:
        run=deepcopy(raw); q,v=discretize(p,basis,(1-fraction)*np.array(frozen['q0']),np.zeros(12))
        run['task']['initializer']['parameters']['data']=dict(qpos_rad=dict(zip(p['dofs'],q)),qvel_rad_s={})
        summaries[name]=public_run(run,name)
    atomic_json(HERE/'lqr_comparison.json',{k:{a:b for a,b in v.items() if a!='observations'} for k,v in summaries.items()})
    final_q=[]
    for label in ('lqr_nominal','lqr_perturbation'):
        folder=ROOT/summaries[label]['backend_folder']
        with gzip.open(folder/'trajectory.json.gz','rt',encoding='utf8') as stream: last=json.load(stream)[-1]
        final_q.append(np.asarray(project(p,basis,last['qpos_rad'],last['qvel_rad_s'])['q_gvs']))
    atomic_json(HERE/'local_recovery.json',dict(initial_perturbation_q_norm=.01*float(np.linalg.norm(frozen['q0'])),
        terminal_perturbation_relative_to_nominal_q_norm=float(np.linalg.norm(final_q[1]-final_q[0])),
        nominal_q_drift=float(np.linalg.norm(final_q[0]-frozen['q0'])),
        note='Recovery relative to the drifting nominal trajectory; neither local run regulates exactly about the mapped GVS state.'))


def dynamic():
    import casadi as ca
    import os, platform, scipy, mujoco
    from scipy.integrate import solve_ivp
    from scipy.optimize import root
    from extensions.tendon_family.gvs_casadi import expression_from_system,functions_for
    from extensions.tendon_family.gvs_trajectory import GVSTrajectoryParameters,TrajectoryWorkspace
    from extensions.tendon_family.gvs_nmpc import _WORKSPACES,_SEEDS,workspace_key
    raw,frozen,system=context();inp=SessionInput.model_validate(raw)
    atomic_json(HERE/'execution_environment.json',dict(interpreter=sys.executable,python=sys.version,
        platform=platform.platform(),processor=platform.processor(),numpy=np.__version__,
        scipy=scipy.__version__,casadi=ca.__version__,mujoco=mujoco.__version__,derivative_evaluation_threads=1,
        blas_environment={k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')}))
    start=time.perf_counter();functions=functions_for(expression_from_system(system))
    graph_s=time.perf_counter()-start;print('dynamics graph',graph_s,flush=True)
    n=12;xinitial=np.zeros(24);u=np.array(frozen['u0_n']);h=.01
    local_tip=ca.Function('probe_tip',[functions.q_symbol],[functions.tip_position_expression])
    from extensions.tendon_family.pcc import quaternion_wxyz_to_rotation
    rotation=quaternion_wxyz_to_rotation(frozen['mount']['quaternion_wxyz']);mount=np.array(frozen['mount']['position_m'])
    tip=lambda x:rotation@np.asarray(local_tip(np.asarray(x)[:n])).ravel()+mount
    def rhs(t,x,command=u):
        terms=functions.implicit_terms(x=x,u=command)
        return np.r_[x[n:],np.linalg.solve(np.asarray(terms['mass']),np.asarray(terms['force']).ravel())]
    start=time.perf_counter();rhs(0,xinitial);eval_s=time.perf_counter()-start
    print('dynamics call',eval_s,flush=True)
    import hashlib
    model_hash=hashlib.sha256((ROOT/'extensions/tendon_family/gvs_casadi.py').read_bytes()).hexdigest()
    prior=read(HERE/'prediction_interval.json') if (HERE/'prediction_interval.json').exists() else None
    if prior is not None and prior.get('model_source_sha256')==model_hash:
        print('Reusing verified interval for identical model source',flush=True)
    else:
        # BDF's numerical Jacobian at the straight, very stiff initial state caused
        # excessive work. Reuse exact AD of this same mass/force function.
        sx=ca.MX.sym('interval_x',24);su=ca.MX.sym('interval_u',6)
        st=functions.implicit_terms(x=sx,u=su)
        srhs=ca.vertcat(sx[n:],ca.solve(st['mass'],st['force']))
        start=time.perf_counter();jacobian=ca.Function('interval_jac',[sx,su],[ca.jacobian(srhs,sx)])
        jac=lambda t,x,command=u:np.asarray(jacobian(x,command))
        print('interval Jacobian construction',time.perf_counter()-start,flush=True)
        start=time.perf_counter()
        trusted=solve_ivp(rhs,(0,h),xinitial,method='BDF',jac=jac,rtol=1e-7,atol=1e-8)
        print('trusted interval',trusted.success,trusted.nfev,trusted.njev,time.perf_counter()-start,flush=True)
        if not trusted.success:raise RuntimeError(trusted.message)
        trusted_s=time.perf_counter()-start
        def implicit_interval(x,command,substeps):
            for _ in range(substeps):
                old=x.copy();dt=h/substeps
                def residual(y):
                    values=functions.implicit_terms(x=y,u=command)
                    return np.r_[(y[:n]-old[:n]-dt*y[n:])/10.,
                        (np.asarray(values['mass'])@((y[n:]-old[n:])/dt)-np.asarray(values['force']).ravel())/.001]
                sol=root(residual,old,tol=1e-9)
                if not sol.success and np.max(abs(residual(sol.x)))>1e-6:raise RuntimeError(sol.message)
                x=sol.x
            return x
        predicted=implicit_interval(xinitial,u,1)
        verification=dict(graph_construction_s=graph_s,dynamics_call_s=eval_s,reference_wall_s=trusted_s,
            interval_s=h,initial_state=xinitial.tolist(),tensions=u.tolist(),trusted_method='scipy BDF exact AD Jacobian, rtol=1e-7 atol=1e-8',
            trusted_endpoint=trusted.y[:,-1].tolist(),implicit_endpoint=predicted.tolist(),
            q_error_norm=float(np.linalg.norm(predicted[:n]-trusted.y[:n,-1])),
            rate_error_norm=float(np.linalg.norm(predicted[n:]-trusted.y[n:,-1])),
            tip_difference_m=float(np.linalg.norm(tip(predicted)-tip(trusted.y[:,-1]))))
        verification['model_source_sha256']=model_hash
        atomic_json(HERE/'prediction_interval.json',verification);print('interval check',verification['tip_difference_m'],flush=True)
    p=GVSTrajectoryParameters(horizon=5,evaluation_threads=1,max_cpu_s=120.)
    if (HERE/'offline_trajectory.json').exists():
        solved=read(HERE/'offline_trajectory.json')
        print('Reusing saved offline solution',flush=True)
    else:
        workspace=TrajectoryWorkspace(inp.task,inp.robot,p,system.x0,system.u0)
        workspace.solver.parameters=workspace.solver.parameters.model_copy(update={'print_level':5})
        print('offline assembly',workspace.graph_s,flush=True)
        # Reproduction reuses this archived, physically identical candidate;
        # it need not repeat the unsuccessful cold-start computation.
        warm_path=Path(__file__).resolve().parent/'offline_scaled_candidate.json'
        warm=read(warm_path)
        solved=workspace.solve(xinitial,u,warm=warm)
        solved['warm_start_source']=str(warm_path.relative_to(ROOT))
        solved['outputs_world_m']=[tip(x).tolist() for x in solved['states']]
        solved['parameters']=p.model_dump(mode='json')
        atomic_json(HERE/'offline_trajectory.json',solved)
    print('offline solve',solved['result']['status'],solved['result']['constraint_violation'],solved['total_s'],flush=True)
    execution_tensions=list(solved['tensions'])
    execution_tensions += [execution_tensions[-1]]*(round(inp.task.timing.duration_s/h)-len(execution_tensions))
    atomic_json(HERE/'offline_execution_sequence.json',dict(tensions=execution_tensions,
        optimized_intervals=len(solved['tensions']),total_intervals=len(execution_tensions),period_s=h,
        continuation='Hold the last optimized tension through the authoritative task duration. Only the prefix is optimized.'))
    # Replay the held sequence with independent adaptive integration.
    start=time.perf_counter();states=[xinitial];integration_calls=0
    cached_replay=(HERE/'offline_gvs_replay.json').exists()
    for command in ([] if cached_replay else execution_tensions):
        interval=solve_ivp(lambda t,x:rhs(t,x,command),(0,h),states[-1],method='BDF',
            rtol=2e-6,atol=1e-8)
        if not interval.success:raise RuntimeError(interval.message)
        states.append(interval.y[:,-1]);integration_calls+=interval.nfev
    replay=dict(states=np.array(states).tolist(),outputs_world_m=[tip(x).tolist() for x in states],
        terminal_error_m=float(np.linalg.norm(tip(states[-1])-inp.task.goal.data['target_m'])),
        wall_s=time.perf_counter()-start,rhs_calls=integration_calls,
        duration_s=inp.task.timing.duration_s,method='adaptive BDF each held 10 ms input')
    if cached_replay:replay=read(HERE/'offline_gvs_replay.json')
    else:atomic_json(HERE/'offline_gvs_replay.json',replay)
    print('GVS replay',replay['terminal_error_m'],flush=True)
    # Replay through the real backend with the same observation/hold loop.
    if not (HERE/'offline_backend_replay.json').exists():replay_backend(inp,execution_tensions,frozen)
    parameters=GVSTrajectoryParameters(horizon=5,max_iterations=40,evaluation_threads=1,max_cpu_s=120.)
    mpc=TrajectoryWorkspace(inp.task,inp.robot,parameters,system.x0,system.u0)
    mpc.solver.parameters=mpc.solver.parameters.model_copy(update={'print_level':5})
    key=workspace_key(inp.task,inp.robot,parameters);_WORKSPACES[key]=mpc
    # Explicit seeds are unshifted; only a workspace's previous solution shifts.
    _SEEDS[key]=dict(states=solved['states'][:parameters.horizon+1],tensions=solved['tensions'][:parameters.horizon])
    raw['policy']['controller']=dict(extension_id='controller.gvs_nmpc',parameters=dict(
        contract='family.gvs_trajectory_parameters',data=parameters.model_dump(mode='json')))
    raw['policy']['candidate_builder']['parameters']['data']['control_parameters']={}
    raw['task']['initializer']['parameters']['data']=dict(qpos_rad={},qvel_rad_s={})
    summary=public_run(raw,'nmpc_task',run_suffix='-feasible')
    observations=summary['observations'];times=[o['optimization_solve_s'] for o in observations if o['optimization_solve_s'] is not None]
    atomic_json(HERE/'nmpc_summary.json',dict(terminal_error_m=summary['terminal_error_m'],
        evaluation=summary['evaluation'],solver_failures=sum(o['solver_failed'] for o in observations),
        fallback_uses=sum(o['failure_response_used'] for o in observations),
        feasible_suboptimal_updates=sum(o['feasible_suboptimal_update'] for o in observations),
        deadline_misses=sum(o['deadline_missed'] for o in observations),solve_times_s=times,
        mean_solve_s=float(np.mean(times)) if times else None,maximum_solve_s=max(times) if times else None,
        graph_construction_s=mpc.graph_s,wall_s=summary['wall_s'],parameters=parameters.model_dump(mode='json')))


def replay_backend(inp,tensions,frozen):
    from extensions.tendon_family.control import execute_ideal_tension
    from extensions.tendon_family.scene import assemble
    class Replay:
        def __init__(self):
            self.resolved_basis=ResolvedGVSBasis.model_validate(frozen['resolved_basis']);self.observations=[];self.last={}
        def command(self,t,g,q,v):
            command,self.last=execute_ideal_tension(backend.physics,tensions[round(t/.01)])
            self.observations.append(dict(time_s=t,tip_position_m=g['tip'].tolist(),gvs_q=q.tolist(),gvs_qdot=v.tolist(),**self.last))
            return command
    backend=MujocoBackend();backend.physics=physics_for(inp)
    baseline=read(HERE/'lqr_task.json')
    backend.scene=read(ROOT/baseline['backend_folder']/'experiment_scene.json')
    backend.config=registry().parse(inp.policy.backend.parameters);backend.timings={};backend.controller=Replay()
    backend.folder=HERE/'offline_backend';backend.folder.mkdir(exist_ok=True)
    start=time.perf_counter();rows,obs,complete,reason,steps=backend.solve(120.)
    with gzip.open(backend.folder/'trajectory.json.gz','wt',encoding='utf8') as f:json.dump(rows,f)
    summary=summarize(rows,obs,backend.physics,backend.controller.resolved_basis,inp.task.goal.data['target_m'],frozen['q0'])
    summary.update(complete=complete,reason=reason,steps=steps,wall_s=time.perf_counter()-start)
    atomic_json(HERE/'offline_backend_replay.json',summary);print('backend replay',summary['terminal_error_m'],flush=True)


def finalize():
    """Evaluate the saved replay; no additional integration or optimization."""
    from schemas.platform import BackendResult
    from extensions.tendon_family.contracts import Data
    from extensions.tendon_family.signals import export
    raw,frozen,_=context();inp=SessionInput.model_validate(raw);reg=registry();db=store()
    baseline=read(HERE/'lqr_task.json');folder=ROOT/baseline['backend_folder']
    physics=read(folder/'resolved_physics.json');scene=read(folder/'experiment_scene.json')
    replay=read(HERE/'offline_backend_replay.json');trajectory=read(HERE/'offline_trajectory.json')
    with gzip.open(HERE/'offline_backend/trajectory.json.gz','rt',encoding='utf8') as stream:rows=json.load(stream)
    execution=read(HERE/'offline_execution_sequence.json')
    sequence_identity=digest(execution['tensions'])
    result=BackendResult(solver_status='completed' if replay['complete'] else 'failed',
        backend_id='backend.family_mujoco',model_id='mujoco_serial_bending_v1',
        signals=export(rows,physics,True,'ideal_tension'),
        data=Payload(contract='family.backend_data',data=Data(physics_identity=physics['identity'],
            scene_identity=digest(dict(source_scene=scene['identity'],held_sequence=sequence_identity)),
            timings_s={'replay':replay['wall_s']},numerical_steps=replay['steps'],reason=replay['reason'],
            applicability=physics['applicability'],exported_files=['trajectory.json.gz','robot.xml','compiled_physics.json'],
            control_identity=sequence_identity).model_dump(mode='json')),
        limitations=['Open-loop transfer of a GVS optimized held-tension sequence; no feedback or real-time claim.'],
        initial_state=Payload(contract='family.initial',data=scene['initial']),seed=inp.seed)
    with db.transaction() as conn:source=db.put(conn,result)
    evaluator=reg.bind(inp.task.evaluator,'evaluator')[0].resolve()
    evaluation=evaluator(inp.task,result,source,reg,digest(dict(task=inp.task.model_dump(mode='json'),source=source.model_dump())))
    atomic_json(HERE/'offline_backend_result.json',result.model_dump(mode='json'))
    atomic_json(HERE/'offline_backend_evaluation.json',evaluation.model_dump(mode='json'))
    residuals=np.array(trajectory['diagnostics']['constraint_values']).reshape(-1,24)
    commanded=np.array([row['desired_tension_n'] for row in rows]);predicted=np.array(execution['tensions'])
    gvs=read(HERE/'offline_gvs_replay.json');nmpc=read(HERE/'nmpc_task.json');observations=nmpc['observations']
    consistency=dict(offline_q_dynamics_residual_max_rad_m=float(np.max(abs(residuals[:,:12]))*10),
        offline_force_dynamics_residual_max=float(np.max(abs(residuals[:,12:]))*.001),
        measured_initial_equality_max=float(np.max(abs(np.array(trajectory['states'][0])))),
        replay_held_tension_difference_max_n=float(np.max(abs(commanded-predicted))),
        offline_prediction_to_gvs_replay_max_tip_m=float(np.max(np.linalg.norm(np.array(trajectory['outputs_world_m'])-np.array(gvs['outputs_world_m'])[:len(trajectory['outputs_world_m'])],axis=1))),
        nmpc_update_count=len(observations),nmpc_update_times_s=[o['time_s'] for o in observations],
        physics_steps=read(ROOT/nmpc['backend_folder']/'result.json')['data']['data']['numerical_steps'],
        identical_straight_initial_condition=bool(np.max(abs(observations[0]['measured_initial_state']))==0),
        final_current_sampled_build=read(HERE/'sampled_current_build.json') if (HERE/'sampled_current_build.json').exists() else None)
    atomic_json(HERE/'execution_checks.json',consistency)
    print('offline backend task_success',evaluation.task_success,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['baseline','dynamic','finalize'])
    parser.add_argument('--output',type=Path,help='Fresh evidence directory for reproduction; existing public run IDs are immutable.')
    args=parser.parse_args()
    if args.output:
        import agreement_cost
        HERE=args.output.resolve();agreement_cost.HERE=HERE;HERE.mkdir(parents=True,exist_ok=True)
    if args.phase=='baseline': baseline()
    elif args.phase=='dynamic': dynamic()
    else: finalize()
