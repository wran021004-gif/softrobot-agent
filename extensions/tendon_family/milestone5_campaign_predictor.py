"""Experimental reduced serial mechanics and a five-interval controller predictor.

Only 24 reduced coordinates/rates are integrated. MuJoCo supplies NON-ADVANCING
point mechanics for the constant virtual-work pullback, never a backend rollout.
The production controller and all physical parameters are untouched.
"""
from copy import deepcopy
import time
import numpy as np
from scipy.integrate import solve_ivp
from schemas.platform import SessionInput
from tools.state_io import digest
from .milestone5_serial_output import SerialOutput
from .milestone5_campaign_localization import forward_terms
from .gvs_trajectory import TrajectoryWorkspace
from .gvs_nmpc import deadline_horizon
from .gvs_profile import reach_numerical

VERSION='serial_pullback_replan5@1.0.0'
MODEL_VERSION='represented_serial_mechanics@1.0.0'
CONTROL_VERSION='replan_every_5@1.0.0'
GRIDS=(dict(max_step_s=.0005,rtol=1e-6,atol=1e-8),
       dict(max_step_s=.00025,rtol=3e-7,atol=3e-9),
       dict(max_step_s=.000125,rtol=1e-7,atol=1e-9))


class SerialMechanics(SerialOutput):
    def __init__(self,*args):
        super().__init__(*args)
        if self.compiled['tension_execution_mode']!='ideal_tension':raise ValueError('IDEAL_INPUT_REQUIRED')
        self.max_residual=0.;self.calls=0

    def derivative(self,state,command):
        x=np.asarray(state);B=self.mapping
        t=forward_terms(self,B@x[:self.n],B@x[self.n:],np.asarray(command))
        M=B.T@t['mass']@B;force=B.T@t['force'];a=np.linalg.solve(M,force)
        residual=float(np.max(abs(M@a-force))/.001)
        self.max_residual=max(self.max_residual,residual);self.calls+=1
        if not np.isfinite(a).all() or residual>1e-5:raise ValueError('REDUCED_FORCE_BALANCE')
        return np.r_[x[self.n:],a]

    def propagate(self,state,command,*,duration_s=.01,grid=GRIDS[-1],deadline):
        start=time.perf_counter();self.max_residual=0.;self.calls=0
        def rhs(t,x):
            if time.perf_counter()>deadline:raise RuntimeError('PREDICTOR_PROPAGATION_DEADLINE')
            return self.derivative(x,command)
        sol=solve_ivp(rhs,(0.,duration_s),np.asarray(state),method='Radau',
                      rtol=grid['rtol'],atol=grid['atol'],max_step=grid['max_step_s'])
        if not sol.success or not np.isfinite(sol.y).all() or abs(sol.t[-1]-duration_s)>1e-12:
            raise ValueError('REDUCED_INTEGRATION_INCOMPLETE')
        if self.data.time!=0.:raise ValueError('BACKEND_CLOCK_ADVANCED')
        x=sol.y[:,-1];result=self.motion(x)
        return dict(state=x.tolist(),**result,grid=grid,max_scaled_residual=self.max_residual,
            finite=True,solver_success=sol.success,solver_evaluations=sol.nfev,mechanics_evaluations=self.calls,
            accepted_internal_steps=len(sol.t)-1,cost_s=time.perf_counter()-start,
            backend_steps=0,backend_clock_s=float(self.data.time))


def initial_controller(configuration,state):
    inp=SessionInput.model_validate(configuration);p=inp.policy.controller.parameters.data['recipe']
    numerical=reach_numerical(inp)
    ws=TrajectoryWorkspace(inp.task,inp.robot,p,
        [*numerical['nominal']['q0'],*([0.]*(len(state)//2))],numerical['nominal']['u0'],
        settling=inp.policy.controller.parameters.data['settling'])
    return inp,p,numerical,ws


def probe(configuration,state,charge):
    """One isolated response approximation: no future state/input argument."""
    start=time.perf_counter();inp,p,numerical,ws=initial_controller(configuration,state)
    previous=np.asarray(numerical['nominal']['u0']);charge()
    solved=ws.solve(state,previous,warm=deepcopy(numerical['warm_guess']),elapsed_s=0.)
    checked=ws.solver.evaluate_candidate(ws.problem,solved['result']['optimum'])
    if not solved['accepted'] or not checked['feasible']:raise ValueError('COST_PROBE_UNUSABLE')
    return dict(version=CONTROL_VERSION,initial_state=list(state),configuration_identity=digest(configuration),
        clock_s=0.,first_five_inputs=solved['tensions'][:5],plan=solved,
        complete_cost_s=time.perf_counter()-start,graph_s=ws.graph_s,
        production_controller_approximation=True,exact_production_execution=False,controller_attempts=1,
        policy='Initial plan is recomputed with the original bundled initial guess; subsequent four plan inputs replace future feedback replans only in the predictor')


def history(configuration,initial_state,model,charge,*,deadline,save_update=lambda r:None):
    """Independent candidate state, previous command and plan; no outcome reader."""
    start=time.perf_counter();inp,p,numerical,ws=initial_controller(configuration,initial_state)
    previous=np.asarray(numerical['nominal']['u0']);x=np.asarray(initial_state).copy()
    seed=deepcopy(numerical['warm_guess']);plan=None;plan_start=None;rows=[];solves=0
    limits=np.array([t['force_limit_n'] for t in inp.robot.structure.data['tendons']])
    period=inp.task.timing.control_period_s;duration=inp.task.timing.duration_s;count=round(duration/period)
    if count!=35 or period!=.01:raise ValueError('FROZEN_35_INTERVAL_SCOPE')
    setup_s=time.perf_counter()-start;graph_s=ws.graph_s
    for i in range(count):
        if time.perf_counter()>deadline:raise RuntimeError('COMPLETE_HISTORY_DEADLINE')
        t=i*period;controller_s=0.;construction_s=0.;replan=i%5==0
        if replan:
            horizon=deadline_horizon(duration,t,period,p['horizon'])
            if plan is not None:
                shift=i-plan_start
                states=plan['states'][shift*p['substeps']:]
                tensions=plan['tensions'][shift:]
                states=states[:horizon*p['substeps']+1];tensions=tensions[:horizon]
                # Fill only the unused seed tail. Production regeneration recomputes
                # states from this candidate's current state before optimization.
                states=states+[states[-1]]*(horizon*p['substeps']+1-len(states))
                tensions=tensions+[tensions[-1]]*(horizon-len(tensions))
                seed=dict(states=states,tensions=tensions)
            if ws.parameters.horizon!=horizon:
                wall=time.perf_counter()
                ws=TrajectoryWorkspace(inp.task,inp.robot,{**p,'horizon':horizon},
                    [*numerical['nominal']['q0'],*([0.]*(len(x)//2))],numerical['nominal']['u0'],
                    settling=inp.policy.controller.parameters.data['settling'])
                construction_s=time.perf_counter()-wall
            charge();solves+=1;wall=time.perf_counter()
            plan=ws.solve(x,previous,warm=seed,elapsed_s=t)
            checked=ws.solver.evaluate_candidate(ws.problem,plan['result']['optimum'])
            controller_s=time.perf_counter()-wall
            if not plan['accepted'] or not checked['feasible']:raise ValueError('APPROXIMATE_CONTROLLER_UNUSABLE')
            plan_start=i;plan_identity=digest(dict(states=plan['states'],tensions=plan['tensions']))
        requested=np.asarray(plan['tensions'][i-plan_start]);command=np.clip(requested,0.,limits)
        initial=x.copy();before=previous.copy()
        end=model.propagate(x,command,deadline=deadline);x=np.asarray(end['state']);previous=command
        row=dict(update_id=i,time_s=t,endpoint_s=t+period,initial_state=initial.tolist(),state=x.tolist(),
            previous_input_n=before.tolist(),input_n=command.tolist(),input_information_time_s=t,
            position_m=end['position_m'],velocity_m_s=end['velocity_m_s'],speed_m_s=end['speed_m_s'],
            error_m=float(np.linalg.norm(np.asarray(end['position_m'])-inp.task.goal.data['target_m'])),
            accepted=True,replanned=replan,plan_start_s=plan_start*period,plan_identity=plan_identity,
            graph_construction_s=construction_s,controller_s=controller_s,propagation_output_s=end['cost_s'],
            max_scaled_residual=end['max_scaled_residual'],backend_clock_s=end['backend_clock_s'])
        rows.append(row);save_update(row)
    holding=[r for r in rows if r['endpoint_s']>=.3-1e-9]
    return dict(version=VERSION,model_version=MODEL_VERSION,controller_approximation=CONTROL_VERSION,
        candidate_id=configuration['run_id'],configuration_identity=digest(configuration),initial_state=list(initial_state),
        complete=len(rows)==35,interval_s=[0.,.35],holding_interval_s=[.30,.35],rows=rows,solves=solves,
        metrics=dict(holding_max_speed_m_s=max(r['speed_m_s'] for r in holding),
            holding_max_error_m=max(r['error_m'] for r in holding),terminal_error_m=rows[-1]['error_m']),
        setup_s=setup_s,initial_graph_s=graph_s,complete_cost_s=time.perf_counter()-start,
        backend_steps=0,exact_production_controller=False,causality='Only initializer, own predicted state and own previously generated plans',
        supported_use='Experimental complete historical forecast; accuracy, safety, ranking and cost require separate assessment')
