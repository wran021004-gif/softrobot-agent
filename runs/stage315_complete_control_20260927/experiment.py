"""Bounded continuation of Stage 3.14; original task, production workspace."""
import argparse
import gzip
import json
import os
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import casadi as ca
import numpy as np
from scipy.integrate import solve_ivp
from extensions.tendon_family.contracts import GVSModelParameters,GVSTrajectoryParameters
from extensions.tendon_family.gvs import GVSModel
from extensions.tendon_family.gvs_casadi import expression_from_system,functions_for
from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace
from extensions.tendon_family.pcc import quaternion_wxyz_to_rotation
from schemas.platform import RobotDescription,TaskDefinition
from schemas.platform_math import SystemContext
from tools.state_io import atomic_json
HERE=Path(__file__).resolve().parent
OLD=ROOT/'runs/stage314_replanning_20260927'
def read(path):return json.loads(path.read_text(encoding='utf8'))
def save(name,value):atomic_json(HERE/(name+'.json'),value)
def setup():
    cfg=read(OLD/'configuration.json')
    return cfg,RobotDescription.model_validate(cfg['robot']),TaskDefinition.model_validate(cfg['task'])
def compact(plan):
    d=plan['diagnostics'];first=d['first_feasible_candidate'];selected=d['selected_feasible_candidate']
    return dict(preparation_s=plan['warm_start']['preparation_s'],initial_violation=d['initial_scaled_violation'],
        initial_objective=d['initial_objective'],first_feasible_s=None if first is None else first['elapsed_s'],
        first_iteration=None if first is None else first['iteration'],policy_stop_s=d['policy_stop_s'],
        policy_stop_reason=d['policy_stop_reason'],solve_s=d['solve_s'],validation_s=d['validation_s'],
        delivery_s=plan['update_wall_s'],construction_s=d['construction_s'],objective=plan['result']['objective_value'],
        violation=plan['result']['constraint_violation'],status=plan['result']['status'],raw_status=d['return_status'],
        accepted=plan['accepted'],selected_iteration=None if selected is None else selected['iteration'])
def compare():
    cfg,robot,task=setup();rows=[]
    for policy in (None,dict(minimum_s=5.,budget_s=15.,relative_improvement=.1)):
        p=GVSTrajectoryParameters.model_validate({**cfg['parameters'],'feasible_return':policy})
        workspace=TrajectoryWorkspace(task,robot,p,cfg['nominal_x'],cfg['nominal_u'])
        for i in (1,2):
            propagation=read(OLD/f'propagation_{i}.json')
            workspace.last=read(ROOT/'runs/stage313_trajectory_cost_20260926/trajectory.json') if i==1 else read(OLD/'update_1.json')['plan']
            plan=workspace.solve(propagation['integrated_state'],propagation['applied_tensions_n'])
            row=dict(case=i,policy_enabled=policy is not None,**compact(plan))
            rows.append(row);print(json.dumps(row),flush=True)
            save('warm_policy_comparison',dict(rows=rows,plans=locals().get('plans',[])))
            save(f'case_{i}_'+('policy' if policy else 'regenerated'),plan)
    save('warm_policy_comparison',dict(rows=rows,historical=read(OLD/'summary.json')))
def formulation(cfg):
    # 100 ms look-ahead includes deceleration. A soft terminal curvature-rate
    # penalty discourages hitting the target at speed; no terminal equality.
    return GVSTrajectoryParameters.model_validate({**cfg['parameters'],'horizon':10,
        'terminal_weight':5.,'velocity_weight':1e-4,'terminal_velocity_weight':1e-4,
        'max_cpu_s':30.,'feasible_return':dict(minimum_s=5.,budget_s=15.,relative_improvement=.1)})
def integration(robot,task,p,x,u):
    modelp=GVSModelParameters(basis=p.basis)
    system=GVSModel(modelp).build_system(robot,modelp,None,SystemContext(x0=list(x),u0=list(u),scene=task.environment))
    f=functions_for(expression_from_system(system));n=len(x)//2
    sx=ca.MX.sym('x',2*n);su=ca.MX.sym('u',len(u));terms=f.implicit_terms(x=sx,u=su)
    rhs=ca.vertcat(sx[n:],ca.solve(terms['mass'],terms['force']))
    rf=ca.Function('held_rhs',[sx,su],[rhs]);jf=ca.Function('held_jac',[sx,su],[ca.jacobian(rhs,sx)])
    local=ca.Function('local_tip',[f.q_symbol],[f.tip_position_expression])
    rotation=ca.DM(quaternion_wxyz_to_rotation(task.environment.data['mount']['quaternion_wxyz']))
    tip=rotation@local(sx[:n])+ca.DM(task.environment.data['mount']['position_m'])
    q=f.q_symbol;v=ca.MX.sym('v',n);world=rotation@f.tip_position_expression+ca.DM(task.environment.data['mount']['position_m'])
    motion=ca.Function('motion',[q,v],[world,ca.jacobian(world,q)@v])
    return rf,jf,lambda x:motion(x[:n],x[n:])
def gvs(check=False):
    cfg,robot,task=setup();p=formulation(cfg);x=np.zeros(len(cfg['nominal_x']));u=np.array(cfg['nominal_u'])
    point=read(ROOT/'runs/stage312_to_nmpc_20260926/operating_point_current.json')['point']
    start=time.perf_counter();workspace=TrajectoryWorkspace(task,robot,p,[*point['q0'],*([0.]*12)],point['u0'])
    rhs,jac,motion=integration(robot,task,p,x,u)
    construction=time.perf_counter()-start;label='gvs_check' if check else 'gvs_full'
    # Fixed budget set before either rollout: 35*(30s solve + 12s BDF + 6s
    # preparation) ~28 min upper estimate; hard wall guard 1800 s.
    config=dict(parameters=p.model_dump(mode='json'),task=cfg['task'],robot=cfg['robot'],
        integration=dict(method='BDF exact AD Jacobian',rtol=1e-7,atol=1e-8),
        settling=dict(window_s=.05,error_m=.01,tip_speed_m_s=.02),wall_budget_s=1800,
        construction_s=construction,interpreter=sys.executable)
    save(label+'_configuration',config);rows=[];plans=[];start=time.perf_counter();dt=task.timing.control_period_s
    count=12 if check else round(task.timing.duration_s/dt)
    for k in range(count):
        if time.perf_counter()-start>1800:break
        if not check and k<12:
            # Reuse actual checkpoint observations and commands, not predictions.
            prefix=read(HERE/'gvs_check.json')
            if prefix['configuration']['parameters']!=p.model_dump(mode='json'):raise ValueError('CHECK_FORMULATION_CHANGED')
            rows.append(prefix['rows'][k]);plans.append(prefix['plans'][k]);x=np.array(rows[-1]['state']);u=np.array(rows[-1]['tensions_n'])
            workspace.last=plans[-1];continue
        plan=workspace.solve(x,u);plans.append(plan)
        if not plan['accepted']:
            save(label,dict(configuration=config,rows=rows,plans=plans,complete=False,reason='unusable_plan'));break
        u=np.clip(np.array(plan['tensions'][0]),0.,[t['force_limit_n'] for t in robot.structure.data['tendons']]);began=time.perf_counter()
        iv=solve_ivp(lambda t,y:np.asarray(rhs(y,u)).ravel(),(k*dt,(k+1)*dt),x,method='BDF',
            jac=lambda t,y:np.asarray(jac(y,u)),rtol=1e-7,atol=1e-8)
        if not iv.success:raise RuntimeError(iv.message)
        x=iv.y[:,-1];tip,speed=motion(x)
        row=dict(time_s=(k+1)*dt,state=x.tolist(),tip_m=np.asarray(tip).ravel().tolist(),
            tip_error_m=float(np.linalg.norm(np.asarray(tip).ravel()-task.goal.data['target_m'])),
            tip_speed_m_s=float(np.linalg.norm(np.asarray(speed))),tensions_n=u.tolist(),
            integration_s=time.perf_counter()-began,nfev=iv.nfev,njev=iv.njev,integration_success=iv.success,**compact(plan))
        rows.append(row);save(label,dict(configuration=config,rows=rows,plans=plans,complete=len(rows)==count,
            elapsed_s=time.perf_counter()-start))
        print(json.dumps({k:v for k,v in row.items() if k not in ('state','tensions_n','tip_m')}),flush=True)
    if len(rows)==count:
        last=[r for r in rows if r['time_s']>=task.timing.duration_s-.05-1e-9]
        save(label,dict(configuration=config,rows=rows,plans=plans,complete=True,
            endpoint_pass=rows[-1]['tip_error_m']<=.01,
            settling_pass=not check and all(r['tip_error_m']<=.01 and r['tip_speed_m_s']<=.02 for r in last),
            elapsed_s=time.perf_counter()-start,reused_prefix_s=sum(r['delivery_s']+r['integration_s'] for r in rows[:12]) if not check else 0))

def replay():
    import mujoco
    from extensions.tendon_family.backends import _mujoco_state_failed
    historical=read(ROOT/'runs/stage312_to_nmpc_20260926/nmpc_task.json')
    folder=ROOT/historical['backend_folder'];scene=read(folder/'experiment_scene.json')
    physics=read(folder/'resolved_physics.json');observations=read(folder/'controller_observations.json')
    commands=[o['desired_tension_n'] for o in observations]
    result=dict(source=str(folder.relative_to(ROOT)),command_period_s=scene['control_period_s'],
        commands=commands,interpretation='Fixed recorded commands; no optimizer and no use of post-reset states as trajectory evidence.',runs=[])
    for h in (.0005,.00025):
        model=mujoco.MjModel.from_xml_path(str(folder/'robot.xml'));model.opt.timestep=h;data=mujoco.MjData(model)
        jids=[model.joint(j).id for j in physics['dofs']];qi=model.jnt_qposadr[jids];vi=model.jnt_dofadr[jids]
        aids=[model.actuator(t['entity']+'_direct_tension').id for t in physics['tendons']]
        data.qpos[qi]=scene['qpos_rad'];data.qvel[vi]=scene['qvel_rad_s'];mujoco.mj_forward(model,data)
        sid=model.site('tip_site').id;rows=[];invalid=None;start=time.perf_counter()
        for k,u in enumerate(commands):
            data.ctrl[aids]=u
            for j in range(round(scene['control_period_s']/h)):
                before=float(data.time);velocity=float(np.max(abs(data.qvel)))
                mujoco.mj_step(model,data)
                if _mujoco_state_failed(data,before):
                    invalid=dict(time_before_step_s=before,engine_time_after_s=float(data.time),
                        prior_max_velocity_rad_s=velocity,warnings={w.name:int(data.warning[w].number) for w in
                        (mujoco.mjtWarning.mjWARN_BADQPOS,mujoco.mjtWarning.mjWARN_BADQVEL,mujoco.mjtWarning.mjWARN_BADQACC)})
                    break
                mujoco.mj_forward(model,data)
                J=np.zeros((3,model.nv));Jr=np.zeros_like(J);mujoco.mj_jacSite(model,data,J,Jr,sid)
                rows.append(dict(time_s=(k*round(scene['control_period_s']/h)+j+1)*h,
                    tip_m=data.site_xpos[sid].tolist(),tip_speed_m_s=float(np.linalg.norm(J@data.qvel)),
                    max_velocity_rad_s=float(np.max(abs(data.qvel))),max_acceleration_rad_s2=float(np.max(abs(data.qacc))),
                    contacts=int(data.ncon),
                    tip_error_m=float(np.linalg.norm(data.site_xpos[sid]-scene['target_world_m']))))
            if invalid:break
        result['runs'].append(dict(timestep_s=h,complete=invalid is None,invalid=invalid,rows=rows,wall_s=time.perf_counter()-start))
        save('recorded_command_replay',result)
        print(json.dumps({k:v for k,v in result['runs'][-1].items() if k!='rows'}),flush=True)

def public():
    from copy import deepcopy
    from tools.platform_store import Store
    from tools.platform_host import Host
    from tools.platform_tasks import compile_input
    from schemas.platform import SessionInput
    from extensions.tendon_family.gvs_lqr import _OPERATING_POINTS
    from extensions.tendon_family.gvs_nmpc import _SEEDS,workspace_key
    cfg,robot,task=setup();p=formulation(cfg)
    point=read(ROOT/'runs/stage312_to_nmpc_20260926/operating_point_current.json')['point']
    _OPERATING_POINTS[point['candidate_model_identity']]=point
    raw=read(ROOT/'runs/stage35_case_b_retry_softagent_20260924/inputs/route.json')
    raw['run_id']='stage315-nmpc';raw['task']=cfg['task'];raw['robot']=cfg['robot']
    raw['policy']['route']=None
    raw['policy']['controller']=dict(extension_id='controller.gvs_nmpc',parameters=dict(
        contract='family.gvs_trajectory_parameters',data=p.model_dump(mode='json')))
    raw['policy']['discretization']=dict(contract='family.discretization',data=dict(cells={'near':12,'far':12}))
    raw['policy']['model']=dict(adapter='offline');raw['policy']['allowed_tools']=['simulation.run','evaluation.run']
    raw['policy']['tool_bindings']={'simulation.run':'1.0.0','evaluation.run':'1.0.0'}
    raw['policy']['budget']=dict(tool_calls=4,model_calls=0,backend_solves=1,worker_calls=0,wall_s=2100.)
    raw['policy']['timeout_s']=1800.
    inp=SessionInput.model_validate(compile_input(raw)['input'])
    seed=read(HERE/'gvs_full.json')['plans'][0]
    _SEEDS[workspace_key(inp.task,inp.robot,p)]=seed
    db=Store(HERE)
    if not db.db.exists():db.create(dict(project_id='stage315',grant_id='stage315-control',
        authorization_source='User authorized bounded full-task public NMPC execution, no paid model calls',
        budget=dict(tool_calls=8,model_calls=0,backend_solves=2,worker_calls=0,wall_s=4200)))
    host=Host(HERE,inp.run_id);host.create(inp.model_dump(mode='json'));start=time.perf_counter()
    sim=host.invoke(dict(request_id='simulate',tool_id='simulation.run',tool_version='1.0.0',arguments=dict(
        candidate_id='nmpc',changes={}),cache='new',reason='Full-duration 12-cell measured-state predictive feedback'))
    save('public_simulation_receipt',sim)
    if sim['execution_status']!='completed':print(sim,flush=True);return
    ev=host.invoke(dict(request_id='evaluate',tool_id='evaluation.run',tool_version='1.0.0',arguments=dict(
        result=sim['output'],execution_id=sim['execution_id']),cache='new',reason='Original authoritative reach criterion'))
    save('public_evaluation_receipt',ev)
    result=db.artifact(sim['output']);save('public_result',result)
    evaluation=db.artifact(ev['output']) if ev['execution_status']=='completed' else None
    save('public_evaluation',evaluation)
    folder=HERE/'sessions'/inp.run_id/'executions'/sim['execution_id']/'backend'
    with gzip.open(folder/'trajectory.json.gz','rt',encoding='utf8') as stream:rows=json.load(stream)
    obs=read(folder/'controller_observations.json')
    summary=dict(evaluation=evaluation,solver_status=result['solver_status'],wall_s=time.perf_counter()-start,
        backend_folder=str(folder.relative_to(ROOT)),updates=len(obs),valid_samples=len(rows),
        terminal_error_m=None if not rows else float(np.linalg.norm(np.array(rows[-1]['tip_m'])-task.goal.data['target_m'])),
        last_valid_time_s=None if not rows else rows[-1]['time_s'],fallbacks=sum(o['failure_response_used'] for o in obs),
        mean_update_s=float(np.mean([o['update_wall_s'] for o in obs])) if obs else None,
        deadline_misses=sum(o['deadline_missed'] for o in obs))
    if rows:
        tensions=np.array([r['tension_n'] for r in rows]);summary['tension_range_n']=[float(tensions.min()),float(tensions.max())]
        summary['max_projection_residual_rad_m']=max(o['gvs_projection_residual_max_rad_m'] for o in obs)
        summary['maximum_plan_violation']=max(o['optimization_constraint_violation'] for o in obs if o['optimization_constraint_violation'] is not None)
        summary['max_error_m']=max(float(np.linalg.norm(np.array(r['tip_m'])-task.goal.data['target_m'])) for r in rows)
        summary['minimum_error_m']=min(float(np.linalg.norm(np.array(r['tip_m'])-task.goal.data['target_m'])) for r in rows)
        summary['solver_failures']=sum(o['solver_failed'] for o in obs)
        summary['intentional_stops']=sum(o['optimization_status']=='feasible_early_stop' for o in obs)
        summary['mean_validation_s']=float(np.mean([o['plan_validation_s'] for o in obs if o['plan_validation_s'] is not None]))
        summary['solver_construction_s']=sum(o['solver_construction_s'] or 0 for o in obs)
        summary['graph_construction_s']=obs[0]['graph_construction_s']
    save('public_summary',summary);print(json.dumps(summary),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['compare','gvs-check','gvs-full','replay','public'])
    parser.add_argument('--output',type=Path);args=parser.parse_args()
    if args.output:HERE=args.output.resolve();HERE.mkdir(parents=True,exist_ok=True)
    if args.phase=='compare':compare()
    elif args.phase=='replay':replay()
    elif args.phase=='public':public()
    else:gvs(args.phase=='gvs-check')
