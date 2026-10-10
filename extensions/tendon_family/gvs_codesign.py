"""One shared length decision and full-horizon implicit GVS force balance."""
from copy import deepcopy
import time
import casadi as ca
import numpy as np
from scipy.integrate import solve_ivp
from extensions.tendon_family.gvs import GVSModel, _topology
from extensions.tendon_family.contracts import GVSModelParameters
from extensions.tendon_family.gvs_casadi import GVSCasadiFunctions, expression_from_system
from extensions.tendon_family.pcc import quaternion_wxyz_to_rotation
from extensions.optimization.ipopt import expression_payload, IpoptSolver
from schemas.platform import SessionInput, Objective
from schemas.platform_math import SystemContext, OptimizationProblem, OptimizationConstraint


def expression(configuration):
    inp = SessionInput.model_validate(configuration)
    p = GVSModelParameters(basis={'strategy': 'structural_linear'})
    from extensions.tendon_family.gvs_basis import resolve_basis
    n = resolve_basis(inp.robot.structure.data, p.basis).dimension
    system = GVSModel(p).build_system(inp.robot, p, None, SystemContext(
        x0=[0.]*(2*n), u0=[.2]*len(inp.robot.structure.data['tendons']), scene=inp.task.environment))
    return expression_from_system(system)


def parameterized(expr):
    d = ca.MX.sym('d')
    segments = _topology(expr.design)[3]
    if len(segments) != 2:
        raise ValueError('CODESIGN_REQUIRES_TWO_SEGMENTS')
    lengths = {segments[0].id: .16+.0055*d, segments[1].id: .11-.0055*d}
    return GVSCasadiFunctions(expr, lengths=lengths, design_input=d)


class Workspace:
    def __init__(self, configuration, substeps=1, local_ad='reverse'):
        started = time.perf_counter()
        self.configuration = configuration
        self.expression = expression(configuration)
        self.functions = f = parameterized(self.expression)
        self.n = n = len(self.expression.coordinate_order)
        self.m = m = len(self.expression.tendon_order)
        self.substeps = substeps
        self.steps = steps = 35*substeps
        self.h = h = .01/substeps
        self.scales = np.r_[np.full(n, 10.), np.full(n, 1000.)]
        q, v, d = f.q_symbol, ca.MX.sym('v', n), f.design_input
        mount = configuration['task']['environment']['data']['mount']
        rotation = ca.DM(quaternion_wxyz_to_rotation(mount['quaternion_wxyz']))
        tip = rotation@f.tip_position_expression+ca.DM(mount['position_m'])
        self.tip = ca.Function('codesign_tip', [q, d], [tip])
        self.velocity = ca.Function('codesign_tip_velocity', [q, v, d], [ca.jtimes(tip, q, v)])
        previous, following, u = ca.MX.sym('previous', 2*n), ca.MX.sym('following', 2*n), ca.MX.sym('u', m)
        step = ca.vertcat((following[:n]-previous[:n]-h*following[n:])/10.,
            f.implicit_residual(following, u, (following[n:]-previous[n:])/h, d)/.001)
        self.local_ad = local_ad
        self.step = ca.Function('codesign_step', [previous, following, u, d], [step],
            {'cse': True, **({'ad_weight': 1.} if local_ad == 'reverse' else {})})
        self.mechanics_construction_s = time.perf_counter()-started

    def rollout(self, tension, design, *, abstol=1e-11):
        """Reconstruct from zero, retaining each tight root residual and failure."""
        started = time.perf_counter()
        tension = np.asarray(tension, dtype=float)
        if tension.shape != (35, self.m) or not np.isfinite(tension).all():
            raise ValueError('ROLLOUT_REQUIRES_35_FINITE_COMMANDS')
        y=ca.MX.sym('scaled_following',2*self.n); old=ca.MX.sym('old',2*self.n)
        uu=ca.MX.sym('uu',self.m); dd=ca.MX.sym('rollout_d')
        root_fn=ca.Function('guess_residual',[y,old,uu,dd],
            [self.step(old,y*self.scales,uu,dd)])
        root=ca.rootfinder('coherent_guess','newton',root_fn,
            {'abstol':abstol,'max_iter':50,'error_on_fail':True})
        construction=time.perf_counter()-started
        states=[np.zeros(2*self.n)]; residuals=[]; failure=None
        for k in range(self.steps):
            before=time.perf_counter()
            try:
                following=np.asarray(root(states[-1]/self.scales,states[-1],tension[k//self.substeps],design)).ravel()*self.scales
                residual=np.asarray(self.step(states[-1],following,tension[k//self.substeps],design)).ravel()
                if not np.isfinite(np.r_[following,residual]).all():raise ValueError('NONFINITE_ROOT')
                states.append(following)
                residuals.append(dict(step=k,time_s=(k+1)*self.h,
                    max_normalized_residual=float(np.max(np.abs(residual))),
                    kinematic_max_rad_m=float(np.max(np.abs(residual[:self.n]))*10.),
                    force_balance_max_N_m2_rad=float(np.max(np.abs(residual[self.n:]))*.001),
                    elapsed_s=time.perf_counter()-before))
            except Exception as exc:
                failure=dict(step=k,time_s=(k+1)*self.h,message=str(exc));break
        return dict(states=np.asarray(states).tolist(),times_s=(np.arange(len(states))*self.h).tolist(),
            residuals=residuals,failure=failure,status='failed' if failure else 'completed',
            costs_s=dict(construction=construction,total=time.perf_counter()-started),abstol=abstol)

    def assemble(self, case, initialization, research=None, saved_tensions=None):
        started = time.perf_counter()
        n, m, steps = self.n, self.m, self.steps
        variables, symbols = {}, {}
        def variable(name, bounds, scale=1.):
            variables[name] = dict(type='number', bounds=bounds, physical_scale=scale)
            symbols[name] = ca.MX.sym('w_'+str(len(symbols)))
            return symbols[name]*scale
        domain = research['design_bounds'] if research else ([0., 0.] if case=='A' else [-1., 1.])
        design_guess = research['design_initial'] if research else 0.
        d = variable('design/d', domain)
        X = [ca.vertcat(*[variable(f'x/{k}/{j}', [0.,0.] if k==0 else [None,None], self.scales[j])
            for j in range(2*n)]) for k in range(steps+1)]
        U = [ca.vertcat(*[variable(f'u/{k}/{j}', [0.,1.], 8.) for j in range(m)]) for k in range(35)]
        mapped = self.step.map(steps)
        residual = mapped(ca.horzcat(*X[:-1]), ca.horzcat(*X[1:]),
            ca.horzcat(*[U[k//self.substeps] for k in range(steps)]), ca.repmat(d,1,steps))
        constraints, bounds = {}, {}
        for k in range(steps):
            for j in range(2*n):
                name=f'dynamics_{k}_{j}'; constraints[name]=residual[j,k]; bounds[name]=(0.,0.)
        self.research=research
        sp = variable('slack/position',[0.,None]) if research else 0.
        sv = variable('slack/speed',[0.,None]) if research else 0.
        target = ca.DM(self.configuration['task']['goal']['data']['target_m'])
        for k in range(30*self.substeps, steps+1):
            constraints[f'holding_position_{k}']=ca.sumsqr((self.tip(X[k][:n],d)-target)/.01)-sp
            constraints[f'holding_speed_{k}']=ca.sumsqr(self.velocity(X[k][:n],X[k][n:],d)/.02)-sv
            bounds[f'holding_position_{k}']=(None,1.)
            bounds[f'holding_speed_{k}']=(None,1.)
        constraints['terminal_position']=ca.sumsqr((self.tip(X[-1][:n],d)-target)/.01)-sp
        bounds['terminal_position']=(None,1.)
        effort=sum(ca.sumsqr(u/8.) for u in U)/(35*m)
        variation=.1*sum(ca.sumsqr((b-a)/8.) for a,b in zip(U,U[1:]))/(34*m)
        objective=effort+variation
        if research:
            objective=research['position_weight']*sp+research['speed_weight']*sv
            if research['objective_mode']=='task_gap_with_effort':
                objective+=research['secondary_coefficient']*(effort+variation)
        bundle, selectors=expression_payload(list(symbols), dict(variables=symbols, expression=objective), constraints)
        self.value=ca.Function.deserialize(bundle.data['serialized_function'])
        self.components=ca.Function('codesign_objective_components', [ca.vertcat(*symbols.values())], [effort,variation])
        # A coherent implicit rollout from the prescribed zero state; no reach
        # constraint or equilibrium fiction enters this reproducible guess.
        tension=np.full((35,m),.2)
        if initialization=='ramp_0_2_to_0_4': tension[:]=np.linspace(.2,.4,35)[:,None]
        if initialization=='saved_schedule':
            if saved_tensions is None:raise ValueError('SAVED_SCHEDULE_REFERENCE_REQUIRED')
            tension=np.asarray(saved_tensions,dtype=float)
        rollout=self.rollout(tension,design_guess,abstol=1e-10)
        if rollout['failure']:raise ValueError('INITIALIZATION_ROOT_FAILED: '+str(rollout['failure']))
        states=np.asarray(rollout['states'])
        guess={'design/d':design_guess}
        if research:
            metrics=self.metrics(dict(states=states,times_s=rollout['times_s'],d=design_guess))
            guess.update({'slack/position':max(0.,(max(metrics['terminal_position_error_m'],metrics['holding_max_position_error_m'])/.01)**2-1.)+1e-4,
                'slack/speed':max(0.,(metrics['holding_max_speed_m_s']/.02)**2-1.)+1e-4})
        guess.update({f'x/{k}/{j}':float(states[k,j]/self.scales[j]) for k in range(steps+1) for j in range(2*n)})
        guess.update({f'u/{k}/{j}':float(tension[k,j]/8.) for k in range(35) for j in range(m)})
        problem=OptimizationProblem(variables=variables,
            objective=Objective(metric=research['objective_mode'] if research else 'normalized_tension_effort_variation',direction='minimize',units='dimensionless'),
            objective_function=bundle, constraints=[OptimizationConstraint(name=name,expression=selector,
                units='normalized',lower=bounds[name][0],upper=bounds[name][1]) for name,selector in zip(constraints,selectors)],
            initial_guess=guess,horizon=35)
        self.assembly_s=time.perf_counter()-started
        self.initial_states=states
        self.initial_rollout=rollout
        return problem

    def decode(self, values):
        return dict(d=float(values['design/d']), lengths_m=[.16+.0055*values['design/d'],.11-.0055*values['design/d']],
            times_s=(np.arange(self.steps+1)*self.h).tolist(),
            states=[[values[f'x/{k}/{j}']*self.scales[j] for j in range(2*self.n)] for k in range(self.steps+1)],
            tensions_n=[[values[f'u/{k}/{j}']*8. for j in range(self.m)] for k in range(35)],
            coordinate_order=self.expression.coordinate_order, tendon_order=self.expression.tendon_order,
            substeps=self.substeps)

    def metrics(self, candidate):
        X=np.asarray(candidate['states']); d=candidate['d']
        target=np.asarray(self.configuration['task']['goal']['data']['target_m'])
        positions=np.array([np.asarray(self.tip(x[:self.n],d)).ravel() for x in X])
        speeds=np.array([np.asarray(self.velocity(x[:self.n],x[self.n:],d)).ravel() for x in X])
        hold=np.asarray(candidate['times_s'])>=.30-1e-12
        errors=np.linalg.norm(positions-target,axis=1)
        return dict(terminal_position_error_m=float(errors[-1]), holding_max_position_error_m=float(max(errors[hold])),
            holding_max_speed_m_s=float(max(np.linalg.norm(speeds[hold],axis=1))))


def integrate(functions, tip, velocity, candidate, target, *, dense_period=.0005, rtol=1e-8, atol_q=1e-9, atol_v=1e-7):
    """Adaptive BDF integration restarted only at input switches, never states."""
    started=time.perf_counter(); n=len(candidate['coordinate_order']); d=candidate['d']
    X=np.asarray(candidate['states']); times=np.asarray(candidate['times_s']); U=np.asarray(candidate['tensions_n'])
    state=np.zeros(2*n); replay_times=[0.]; replay_states=[state.copy()]; nfev=njev=nlu=0
    x,u,rhs=functions._linearization_symbols
    dd=functions.design_input
    # Use the direct xdot graph: avoid asking a ten-output dynamics wrapper
    # for unused output Jacobians at every adaptive integration update.
    rhs_fn=ca.Function('replay_rhs',[x,u,dd],[rhs],{'cse':True})
    jac_fn=ca.Function('replay_jac',[x,u,dd],[ca.jacobian(rhs,x)],{'ad_weight':1.,'cse':True})
    jacobian_construction_s=time.perf_counter()-started
    failure=None
    for k,tension in enumerate(U):
        a,b=k*.01,(k+1)*.01
        result=solve_ivp(lambda t,y:np.asarray(rhs_fn(y,tension,d)).ravel(), (a,b),state,
            method='BDF', jac=lambda t,y:np.asarray(jac_fn(y,tension,d)), rtol=rtol,
            atol=np.r_[np.full(n,atol_q),np.full(n,atol_v)], dense_output=True)
        nfev+=result.nfev; njev+=result.njev; nlu+=result.nlu
        if not result.success:
            failure=dict(interval=k,message=result.message,time_s=float(result.t[-1])); break
        sample=np.linspace(a,b,round(.01/dense_period)+1)[1:]
        replay_times.extend(sample.tolist()); replay_states.extend(result.sol(sample).T.tolist())
        state=result.y[:,-1]
    rt=np.asarray(replay_times); rx=np.asarray(replay_states)
    rp=np.array([np.asarray(tip(y[:n],d)).ravel() for y in rx])
    rv=np.array([np.asarray(velocity(y[:n],y[n:],d)).ravel() for y in rx])
    op=np.array([np.asarray(tip(y[:n],d)).ravel() for y in X])
    ov=np.array([np.asarray(velocity(y[:n],y[n:],d)).ravel() for y in X])
    valid=times<=rt[-1]+1e-12
    matched_p=np.array([np.interp(times[valid],rt,rp[:,j]) for j in range(3)]).T
    matched_v=np.array([np.interp(times[valid],rt,rv[:,j]) for j in range(3)]).T
    # Also compare dense replay with linearly interpolated optimizer tip outputs.
    dense_op=np.array([np.interp(rt,times,op[:,j]) for j in range(3)]).T
    dense_ov=np.array([np.interp(rt,times,ov[:,j]) for j in range(3)]).T
    errors=np.linalg.norm(rp-np.asarray(target),axis=1); speed=np.linalg.norm(rv,axis=1)
    hold=rt>=.30-1e-12
    result=dict(status='integration_failed' if failure else 'completed', integration_failure=failure,
        method='scipy BDF, exact direct-graph state Jacobian, switch-by-switch continuous state', rtol=rtol,
        atol_q=atol_q,atol_v=atol_v,dense_period_s=dense_period,
        node_max_tip_disagreement_m=float(np.max(np.linalg.norm(matched_p-op[valid],axis=1))),
        node_max_speed_disagreement_m_s=float(np.max(np.linalg.norm(matched_v-ov[valid],axis=1))),
        dense_max_tip_disagreement_m=float(max(np.linalg.norm(rp-dense_op,axis=1))),
        dense_max_speed_disagreement_m_s=float(max(np.linalg.norm(rv-dense_ov,axis=1))),
        terminal_position_error_m=float(errors[-1]) if not failure else None,
        holding_max_position_error_m=float(max(errors[hold])) if any(hold) else None,
        holding_max_speed_m_s=float(max(speed[hold])) if any(hold) else None,
        input_bounds_compliant=bool(np.isfinite(U).all() and U.min()>=0 and U.max()<=8),
        sampled_evaluator=dict(definition='0.01 s position samples; instantaneous world tip Jacobian times velocity, matching existing evaluator evidence'),
        costs_s=dict(jacobian_construction=jacobian_construction_s,total=time.perf_counter()-started),
        integration_counts=dict(nfev=nfev,njev=njev,nlu=nlu))
    si=np.arange(0,len(rt),round(.01/dense_period)); sp=rp[si]; st=rt[si]
    sh=st>=.30-1e-12
    result['sampled_evaluator'].update(holding_max_position_error_m=float(max(np.linalg.norm(sp[sh]-target,axis=1))) if any(sh) else None,
        holding_max_speed_m_s=float(max(np.linalg.norm(rv[si][sh],axis=1))) if any(sh) else None)
    result['gates_passed']=bool(not failure and result['input_bounds_compliant'] and
        result['dense_max_tip_disagreement_m']<=.001 and result['dense_max_speed_disagreement_m_s']<=.002 and
        result['terminal_position_error_m']<=.01 and result['holding_max_position_error_m']<=.01 and result['holding_max_speed_m_s']<=.02)
    return result, dict(times_s=rt.tolist(),states=rx.tolist(),tip_positions_m=rp.tolist(),tip_velocities_m_s=rv.tolist())
