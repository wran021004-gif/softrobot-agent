"""Experimental full-order point-mechanics predictor, never a reduced model.

Retains all serial joint coordinates/rates. Only non-advancing MuJoCo point
evaluations are used; SciPy integrates the independent continuous equation.
"""
import time
import numpy as np
from scipy.integrate import solve_ivp
from .milestone5_serial_output import SerialOutput
from .milestone5_campaign_localization import forward_terms

VERSION='full_serial_continuous@1.0.0'
DISCRETE_VERSION='full_serial_discrete@2.0.0'


class FullState(SerialOutput):
    def __init__(self,*args):
        super().__init__(*args)
        self.full_n=len(self.compiled['qpos_indices'])
        if self.compiled['tension_execution_mode']!='ideal_tension':raise ValueError('IDEAL_INPUT_REQUIRED')

    def motion(self,state):
        x=np.asarray(state,dtype=float)
        if x.shape!=(2*self.full_n,) or not np.isfinite(x).all():raise ValueError('FULL_STATE_REQUIRED')
        r=self.raw(x[:self.full_n],x[self.full_n:])
        return {k:r[k] for k in ('position_m','velocity_m_s','speed_m_s')}

    def propagate(self,state,command,*,grid,deadline,duration_s=.01):
        start=time.perf_counter();maximum=0.;calls=0
        def rhs(t,x):
            nonlocal maximum,calls
            if time.perf_counter()>deadline:raise RuntimeError('FULL_STATE_DEADLINE')
            terms=forward_terms(self,x[:self.full_n],x[self.full_n:],np.asarray(command))
            a=terms['acceleration'];res=float(np.max(abs(terms['mass']@a-terms['force']))/.001)
            maximum=max(maximum,res);calls+=1
            if not np.isfinite(a).all() or res>1e-5:raise ValueError('FULL_FORCE_BALANCE')
            return np.r_[x[self.full_n:],a]
        sol=solve_ivp(rhs,(0.,duration_s),np.asarray(state),method='Radau',rtol=grid['rtol'],atol=grid['atol'],max_step=grid['max_step_s'])
        if not sol.success or not np.isfinite(sol.y).all() or abs(sol.t[-1]-duration_s)>1e-12:raise ValueError('FULL_INTEGRATION_INCOMPLETE')
        if self.data.time!=0.:raise ValueError('BACKEND_CLOCK_ADVANCED')
        x=sol.y[:,-1]
        return dict(state=x.tolist(),**self.motion(x),grid=grid,step_s=grid['max_step_s'],max_scaled_residual=maximum,
            finite=True,solver_success=True,mechanics_evaluations=calls,accepted_steps=len(sol.t)-1,cost_s=time.perf_counter()-start,
            backend_steps=0,version=VERSION,full_order=True)


class DiscreteFullState(FullState):
    """Independent implicit-damping recurrence for the frozen hinge-only plant.

This explicitly reproduces the backend's discrete physics; it is full-order
emulation, not an inexpensive reduced physical model or backend validation.
The finer step comparisons remain visible, even when they invalidate admission.
"""
    def __init__(self,*args):
        super().__init__(*args)
        import mujoco
        m=self.model
        if int(m.opt.integrator)!=int(mujoco.mjtIntegrator.mjINT_IMPLICITFAST):raise ValueError('IMPLICITFAST_REQUIRED')
        if m.nq!=m.nv or m.nv!=self.full_n or np.any(m.jnt_type!=mujoco.mjtJoint.mjJNT_HINGE):raise ValueError('HINGE_ONLY')
        if np.any(m.tendon_damping) or m.opt.viscosity or m.opt.density or np.any(m.actuator_biastype):raise ValueError('UNSUPPORTED_VELOCITY_FORCE')
        self.damping=np.diag(m.dof_damping.copy())

    def propagate(self,state,command,*,grid,deadline,duration_s=.01):
        start=time.perf_counter();x=np.asarray(state).copy();n=self.full_n;h=grid['max_step_s'];count=round(duration_s/h);maximum=0.
        if abs(count*h-duration_s)>1e-12:raise ValueError('DISCRETE_GRID_ALIGNMENT')
        for _ in range(count):
            if time.perf_counter()>deadline:raise RuntimeError('DISCRETE_DEADLINE')
            terms=forward_terms(self,x[:n],x[n:],np.asarray(command))
            matrix=terms['mass']+h*self.damping
            acceleration=np.linalg.solve(matrix,terms['force'])
            residual=float(np.max(abs(matrix@acceleration-terms['force']))/.001)
            maximum=max(maximum,residual)
            if residual>1e-5 or not np.isfinite(acceleration).all():raise ValueError('DISCRETE_FORCE_BALANCE')
            x[n:]+=h*acceleration;x[:n]+=h*x[n:]
        if self.data.time!=0.:raise ValueError('BACKEND_CLOCK_ADVANCED')
        return dict(state=x.tolist(),**self.motion(x),grid=grid,step_s=h,max_scaled_residual=maximum,
            finite=True,solver_success=True,mechanics_evaluations=count,accepted_steps=count,cost_s=time.perf_counter()-start,
            backend_steps=0,version=DISCRETE_VERSION,full_order=True,backend_equivalent_integration_steps=count)


def replan_due(update_id,period_s,duration_s,holding_window_s):
    return update_id%5==0 or update_id*period_s>=duration_s-holding_window_s-1e-10


def history(configuration,initial_state,model,physics,charge,*,deadline,save_update):
    """Causal phase-based replanning, with each candidate's complete own history."""
    from copy import deepcopy
    from .milestone5_campaign_predictor import initial_controller,GRIDS
    from .gvs_projection import project
    from .gvs_basis import resolve_basis
    from .gvs_nmpc import deadline_horizon
    from .gvs_trajectory import TrajectoryWorkspace
    from schemas.platform import SessionInput
    from tools.state_io import digest
    start=time.perf_counter();x=np.asarray(initial_state).copy();n=model.full_n
    inp=SessionInput.model_validate(configuration);basis=resolve_basis(inp.robot.structure.data,inp.policy.controller.parameters.data['recipe']['basis'])
    def observe(x):
        reduced=project(physics,basis,x[:n],x[n:]);return reduced['q_gvs']+reduced['qdot_gvs']
    inp,p,numerical,ws=initial_controller(configuration,observe(x))
    previous=np.asarray(numerical['nominal']['u0']);seed=deepcopy(numerical['warm_guess'])
    period=inp.task.timing.control_period_s;duration=inp.task.timing.duration_s
    settling=inp.policy.controller.parameters.data['settling']
    holding_start=duration-settling['window_s']
    limits=np.array([t['force_limit_n'] for t in inp.robot.structure.data['tendons']])
    rows=[];plan=None;plan_start=None;solves=0;setup_s=time.perf_counter()-start
    for i in range(round(duration/period)):
        if time.perf_counter()>deadline:raise RuntimeError('FULL_HISTORY_DEADLINE')
        t=i*period;replan=replan_due(i,period,duration,settling['window_s']);controller_s=0.;construction_s=0.;diagnostics=None
        if replan:
            horizon=deadline_horizon(duration,t,period,p['horizon'])
            if plan is not None:
                shift=i-plan_start;states=plan['states'][shift*p['substeps']:][:horizon*p['substeps']+1];tensions=plan['tensions'][shift:][:horizon]
                seed=dict(states=states+[states[-1]]*(horizon*p['substeps']+1-len(states)),tensions=tensions+[tensions[-1]]*(horizon-len(tensions)))
            if ws.parameters.horizon!=horizon:
                wall=time.perf_counter()
                ws=TrajectoryWorkspace(inp.task,inp.robot,{**p,'horizon':horizon},[*numerical['nominal']['q0'],*([0.]*basis.dimension)],numerical['nominal']['u0'],settling=settling)
                construction_s=time.perf_counter()-wall
            charge();solves+=1;wall=time.perf_counter()
            plan=ws.solve(observe(x),previous,warm=seed,elapsed_s=t)
            checked=ws.solver.evaluate_candidate(ws.problem,plan['result']['optimum']);controller_s=time.perf_counter()-wall
            if not plan['accepted'] or not checked['feasible']:raise ValueError('CAUSAL_PREVIEW_CONTROLLER_UNUSABLE')
            plan_start=i;plan_identity=digest(dict(states=plan['states'],tensions=plan['tensions']))
            diagnostics=dict(warm_preparation_s=plan['warm_start']['preparation_s'],optimizer_and_validation_s=plan['total_s'],accepted=plan['accepted'])
        command=np.clip(np.asarray(plan['tensions'][i-plan_start]),0.,limits);before=x.copy()
        end=model.propagate(x,command,grid=GRIDS[0],deadline=deadline);x=np.asarray(end['state']);previous=command
        row=dict(update_id=i,time_s=t,endpoint_s=t+period,initial_full_state=before.tolist(),state=x.tolist(),
            input_n=command.tolist(),position_m=end['position_m'],velocity_m_s=end['velocity_m_s'],speed_m_s=end['speed_m_s'],
            error_m=float(np.linalg.norm(np.asarray(end['position_m'])-inp.task.goal.data['target_m'])),
            accepted=True,replanned=replan,plan_start_s=plan_start*period,plan_identity=plan_identity,
            controller_s=controller_s,graph_construction_s=construction_s,propagation_output_s=end['cost_s'],diagnostics=diagnostics,
            max_scaled_residual=end['max_scaled_residual'],emulated_physics_steps=end['backend_equivalent_integration_steps'])
        rows.append(row);save_update(row)
    holding=[r for r in rows if r['endpoint_s']>=holding_start-1e-10]
    return dict(version=DISCRETE_VERSION+'+holding_feedback@1.0.0',candidate_id=configuration['run_id'],
        configuration_identity=digest(configuration),initial_state=list(initial_state),rows=rows,complete=len(rows)==35,solves=solves,
        metrics=dict(holding_max_speed_m_s=max(r['speed_m_s'] for r in holding),holding_max_error_m=max(r['error_m'] for r in holding),terminal_error_m=rows[-1]['error_m']),
        setup_s=setup_s,complete_cost_s=time.perf_counter()-start,full_order=True,backend_steps=0,
        emulated_physics_steps=sum(r['emulated_physics_steps'] for r in rows),
        exact_production_controller=False,controller_version='controller.gvs_nmpc@7.0.0 unchanged solves; experimental preview schedule',
        controller_policy='Every fifth update before holding, every update during configured holding window',
        causality='Only initializer, own predicted full state and previous own plans; no outcome reader',
        scope='Development full-order backend-equivalent physics forecast, not independent backend validation or a cheap reduced model')
