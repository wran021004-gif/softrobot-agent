"""Bounded saved-state GVS experiments. None of these are backend validation."""
from copy import deepcopy
import json
import time
from typing import Literal
import numpy as np
from pydantic import Field
from schemas.common import Contract
from schemas.platform import EvidenceRef,SessionInput
from tools.platform_store import plain,encode
from .diagnostic_evidence import BoundReader,DiagnosticEvidence


def endpoint_acceleration(jacobian,generalized_acceleration,kinematic_acceleration):
    return np.asarray(jacobian)@np.asarray(generalized_acceleration).ravel()+np.asarray(kinematic_acceleration).ravel()


def braking_box_input(velocity,influence,limits,baseline):
    speed=float(np.linalg.norm(velocity))
    if speed<=1e-8:return np.asarray(baseline).copy()
    return np.where(np.asarray(velocity)@np.asarray(influence)/speed<0,np.asarray(limits),0.)


class SavedStateCheck(Contract):
    binding: EvidenceRef
    update_id: int = Field(ge=1)
    operation: Literal['prediction_braking','local_comparison']
    changed_parameter: Literal['terminal_tip_speed_weight','holding_tip_speed_weight'] | None = None
    changed_value: float | None = Field(default=None,ge=.0001,le=1.)
    horizon_s: float = Field(default=.01,gt=0,le=.02)
    integration_step_s: float = Field(default=.002,gt=0,le=.01)
    max_wall_s: float = Field(default=180.,gt=0,le=300.)


def charge_units(ctx,kind,count):
    """Atomic sublimit in the same project ledger; Host charges all elapsed time."""
    with ctx.store.transaction() as db:
        row=db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()
        if row is None:raise ValueError('FROZEN_DIAGNOSTIC_ALLOCATION_REQUIRED')
        work=json.loads(row['value'])
        if work['used'][kind]+count>work['limits'][kind]:raise ValueError('DIAGNOSTIC_WORK_LIMIT_EXHAUSTED')
        work['used'][kind]+=count
        db.execute("UPDATE meta SET value=? WHERE key='diagnostic_work'",(encode(work),))
        ctx.store.event(db,ctx.run_id,'diagnostic_work','charged',request=ctx.row['request_id'],outputs=[ctx.store.put(db,dict(kind=kind,count=count,used=work['used']))])


class NonlinearModel:
    def __init__(self,configuration,state,input_n,step_s):
        import casadi as ca
        from schemas.platform_math import SystemContext
        from .contracts import GVSModelParameters
        from .gvs import GVSModel
        from .gvs_casadi import expression_from_system,functions_for
        from .gvs_trajectory import implicit_step_residual
        from .pcc import quaternion_wxyz_to_rotation
        inp=SessionInput.model_validate(configuration);self.n=len(state)//2;self.m=len(input_n)
        p=GVSModelParameters(basis=inp.policy.controller.parameters.data['recipe']['basis'])
        system=GVSModel(p).build_system(inp.robot,p,None,SystemContext(x0=state,u0=input_n,scene=inp.task.environment))
        self.functions=functions_for(expression_from_system(system));f=self.functions
        q=f.q_symbol;v=ca.MX.sym('endpoint_rate',self.n)
        mount=inp.task.environment.data['mount']
        tip=ca.DM(quaternion_wxyz_to_rotation(mount['quaternion_wxyz']))@f.tip_position_expression+ca.DM(mount['position_m'])
        J=ca.jacobian(tip,q);velocity=J@v
        self.motion=ca.Function('diagnostic_motion',[q,v],[tip,velocity,J,ca.jtimes(velocity,q,v)])
        self.residual=implicit_step_residual(f,self.n,self.m,step_s)
        y=ca.MX.sym('next',2*self.n);old=ca.MX.sym('previous',2*self.n);u=ca.MX.sym('input',self.m)
        self.scales=np.r_[np.full(self.n,10.),np.full(self.n,1000.)]
        scaled=ca.Function('diagnostic_step',[y,old,u],[self.residual(old,y*self.scales,u)])
        self.step=ca.rootfinder('diagnostic_implicit_euler','newton',scaled,{'abstol':1e-10,'max_iter':30})
        self.target=np.array(inp.task.goal.data['target_m']);self.step_s=step_s

    def acceleration(self,state,input_n):
        x=np.asarray(state);p,v,J,kinematic=self.motion(x[:self.n],x[self.n:])
        values=self.functions.evaluate(x,input_n)
        acceleration=endpoint_acceleration(J,values['qdd'],kinematic)
        return np.asarray(p).ravel(),np.asarray(v).ravel(),acceleration,values,np.asarray(J),np.asarray(kinematic).ravel()

    def rollout(self,state,input_n,horizon_s,deadline):
        count=round(horizon_s/self.step_s)
        if count<1 or count>10 or abs(count*self.step_s-horizon_s)>1e-9:raise ValueError('BOUNDED_ALIGNED_INTEGRATION_REQUIRED')
        state=np.array(state);start=np.asarray(self.motion(state[:self.n],state[self.n:])[0]).ravel();rows=[]
        for i in range(count+1):
            if time.perf_counter()>deadline:raise RuntimeError('DIAGNOSTIC_TIME_LIMIT')
            p,v,*_=self.motion(state[:self.n],state[self.n:]);p=np.asarray(p).ravel();v=np.asarray(v).ravel()
            rows.append(dict(time_s=i*self.step_s,position_m=p.tolist(),velocity_m_s=v.tolist(),
                speed_m_s=float(np.linalg.norm(v)),error_m=float(np.linalg.norm(p-self.target)),displacement_m=float(np.linalg.norm(p-start))))
            if i<count:
                new=np.asarray(self.step(state/self.scales,state,input_n)).ravel()*self.scales
                residual=float(np.max(np.abs(self.residual(state,new,input_n))))
                if not np.isfinite(new).all() or residual>1e-5:raise ValueError('NONLINEAR_INTEGRATION_INFEASIBLE')
                state=new;rows[-1]['next_step_max_scaled_residual']=residual
        return rows


def braking(ctx,args,reader,source,updates):
    start=time.perf_counter();charge_units(ctx,'prediction_evaluations',2)
    u=updates[args.update_id];x=u['measured_initial_state'];baseline=np.array(u['actual_tension_n'])
    model=NonlinearModel(source['configuration'],x,baseline.tolist(),args.integration_step_s)
    physics=reader.read_file(source,'resolved_physics.json')
    # The compiled control contract owns channel order and bounds.
    control=reader.read_file(source,'control_spec.json')
    tendons=[t['id'] for t in source['configuration']['robot']['structure']['data']['tendons']]
    if [t['entity'] for t in physics['tendons']]!=tendons:raise ValueError('RECORDED_TENDON_ORDER_MISMATCH')
    limits=np.array([t['force_limit_n'] for t in physics['tendons']])
    if len(limits)!=len(baseline) or np.any(baseline< -1e-8) or np.any(baseline>limits+1e-8):raise ValueError('RECORDED_FORCE_BOUNDS_MISMATCH')
    p,v,a,values,J,kin=model.acceleration(x,baseline)
    speed=float(np.linalg.norm(v));near_zero=speed<=1e-8
    influence=-J@np.linalg.solve(values['mass_matrix'],values['tendon_length_jacobian'].T)
    # Acceleration is affine in held tension at a fixed q,qdot. A linear
    # objective on the recorded unilateral box is minimized at its corners.
    proposed=braking_box_input(v,influence,limits,baseline)
    rows=[]
    for label,tension in [('recorded_applied',baseline),('instantaneous_braking_box_solution',proposed)]:
        wall=time.perf_counter();_,velocity,acceleration,*_=model.acceleration(x,tension)
        trajectory=model.rollout(x,tension,args.horizon_s,start+args.max_wall_s)
        rows.append(dict(label=label,tension_n=tension.tolist(),tip_velocity_m_s=velocity.tolist(),tip_acceleration_m_s2=acceleration.tolist(),
            velocity_direction_deceleration_m_s2=None if near_zero else -float(velocity@acceleration)/speed,
            kinematic_acceleration_m_s2=kin.tolist(),trajectory=trajectory,
            final_speed_change_m_s=trajectory[-1]['speed_m_s']-trajectory[0]['speed_m_s'],
            position_drift_m=trajectory[-1]['displacement_m'],force_margin_n=(limits-tension).tolist(),
            input_bounds_satisfied=bool(np.all(tension>=0)&np.all(tension<=limits)),computation_s=time.perf_counter()-wall))
    return dict(model='model.gvs@1.0.0',state_scope='recorded projected GVS state, not complete backend state',update_id=args.update_id,
        source_state=dict(reference=source['files']['controller_observations.json'],pointer=f'/{args.update_id}/measured_initial_state'),
        source_input=dict(reference=source['files']['controller_observations.json'],pointer=f'/{args.update_id}/actual_tension_n'),
        time_s=u['time_s'],tendon_order=tendons,force_limits_n=limits.tolist(),near_zero_speed=near_zero,
        applicability='near-zero direction undefined; baseline retained' if near_zero else 'instantaneous affine-input acceleration at fixed recorded pose/rate',
        search='analytic bounded linear objective on unilateral tension box; no iterative input optimizer',
        definition='-v_tip.T @ (J qdd + Jdot qdot) / ||v_tip||',integration='implicit Euler in mass/force form',
        horizon_s=args.horizon_s,integration_step_s=args.integration_step_s,rows=rows,complete_cost_s=time.perf_counter()-start,
        interpretation='Model-predicted possibility only. Instantaneous deceleration need not persist during held-input rollout. No experimental braking claim.',
        advisory_only=True,ranking_changed=False)


def local_pair(ctx,args,reader,source,updates):
    from .gvs_trajectory import TrajectoryWorkspace
    from .control_evidence import plan_metrics,capture_snapshot
    if args.changed_parameter is None or args.changed_value is None:raise ValueError('SINGLE_PARAMETER_CHANGE_REQUIRED')
    inp=SessionInput.model_validate(source['configuration']);recipe=inp.policy.controller.parameters.data['recipe']
    u=updates[args.update_id];previous=updates[args.update_id-1]['actual_tension_n'];state=u['measured_initial_state']
    horizon=u.get('effective_horizon',recipe['horizon']);start=time.perf_counter();rows=[]
    for label in ('baseline','variant'):
        if time.perf_counter()-start+60>args.max_wall_s:raise RuntimeError('LOCAL_PAIR_TIME_ALLOWANCE')
        charge_units(ctx,'local_solves',1);p=deepcopy(recipe);p['horizon']=horizon
        if label=='variant':p[args.changed_parameter]=args.changed_value
        wall=time.perf_counter()
        ws=TrajectoryWorkspace(inp.task,inp.robot,p,state,previous,settling=inp.policy.controller.parameters.data['settling'])
        ws.solver.diagnostic_trace=True
        # New, common cold seed: repeat previous applied tensions, regenerate
        # candidate-model states. This is explicitly not a historical warm plan.
        solved=ws.solve(state,previous,elapsed_s=u['time_s'])
        checked=ws.solver.evaluate_candidate(ws.problem,solved['result']['optimum'])
        metrics=plan_metrics(ws,np.array(solved['states']),np.array(solved['tensions']),u['time_s'])
        initial_tip=np.asarray(ws._motion(state[:ws.n],state[ws.n:])[0]).ravel()
        physical_motion=[]
        for i,x in enumerate(solved['states']):
            tip,velocity=ws._motion(x[:ws.n],x[ws.n:]);tip=np.asarray(tip).ravel();velocity=np.asarray(velocity).ravel()
            physical_motion.append(dict(time_s=u['time_s']+i*ws.period/p['substeps'],position_m=tip.tolist(),
                displacement_from_initial_m=float(np.linalg.norm(tip-initial_tip)),tip_velocity_m_s=velocity.tolist(),
                tip_speed_m_s=float(np.linalg.norm(velocity)),target_error_m=float(np.linalg.norm(tip-ws.target))))
        limits=np.array([t['force_limit_n'] for t in inp.robot.structure.data['tendons']]);inputs=np.array(solved['tensions'])
        snap=capture_snapshot(ws,solved,args.update_id,u['time_s'],solved['tensions'][0],
            {'gvs_projection':dict(residual_max_rad_m=u.get('gvs_projection_residual_max_rad_m'))})
        ref=ctx.save_artifact(dict(snapshot=snap,independent_verification=checked,parameters=p),'local_control_snapshot')
        rows.append(dict(label=label,parameters=p,metrics=metrics,physical_motion=physical_motion,
            input_bounds_satisfied=bool(np.all(inputs>=-1e-8)&np.all(inputs<=limits+1e-8)),
            lower_input_margin_n=inputs.min(axis=0).tolist(),upper_input_margin_n=(limits-inputs.max(axis=0)).tolist(),
            verification=checked,reference=plain(ref),
            selected_iteration=solved['diagnostics']['selected_feasible_iteration'],
            stop_reason=solved['diagnostics']['policy_stop_reason'],complete_cost_s=time.perf_counter()-wall))
    return dict(update_id=args.update_id,time_s=u['time_s'],changed_factor=args.changed_parameter,
        initial_state_reference=dict(reference=source['files']['controller_observations.json'],pointer=f'/{args.update_id}/measured_initial_state'),
        previous_input_reference=dict(reference=source['files']['controller_observations.json'],pointer=f'/{args.update_id-1}/actual_tension_n'),
        baseline_value=recipe[args.changed_parameter],variant_value=args.changed_value,rows=rows,
        fixed=['robot','task','recorded projected state','previous applied input','horizon','integration','bounds','solver budgets','cold-seed protocol'],
        seed='New constant previous-input seed with dynamics regeneration, no historical warm reconstruction',
        criteria=dict(independent_feasibility_max_scaled=1e-5,speed_reduction_fraction=.2,error_limit_m=.01),
        objectives='Differing objective definitions: raw scalar objectives are not ranked across variants',
        new_local_solves=2,complete_cost_s=time.perf_counter()-start,
        applicability='One local model comparison, not closed-loop or historical optimizer replay')


def execute(ctx,args):
    reader=BoundReader(ctx.store,args.binding);source=reader.resolve(reader.binding['execution_id'])
    updates=reader.read_file(source,'controller_observations.json')
    if args.update_id>=len(updates):raise ValueError('RECORDED_UPDATE_REQUIRED')
    protocol=ctx.save_artifact(dict(request=plain(args),source_manifest=source['manifest'],
        criteria=dict(force_bounds=True,finite=True,max_scaled_residual=1e-5),
        warning='All preparation, failed attempts, optimization and instrumentation charged.'),'diagnostic_protocol')
    result=(braking if args.operation=='prediction_braking' else local_pair)(ctx,args,reader,source,updates)
    result['protocol']=plain(protocol)
    return DiagnosticEvidence(detail=result)


def preflight(inp,args,reg):
    return dict(cost=dict(wall_s=args.max_wall_s))
