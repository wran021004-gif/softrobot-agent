"""Finite local LTI calculations in declared normalized coordinates."""
import platform
import numpy as np
import scipy
from scipy.linalg import expm
from scipy.optimize import Bounds, minimize, lsq_linear

LIMITATIONS = [
    'Local unconstrained frozen Jacobians; finite Gramians do not establish unilateral bounded-input feasibility.',
    'Open-loop authority does not establish closed-loop stability, settling, or real-time execution.',
    'Numerical agreement is implementation verification, not physical model validation.',
    'Saved non-equilibrium frequency curves are frozen-Jacobian resolvents, not measured steady-state responses.',
]


def normalized(model):
    sx, su, sy = map(np.asarray,(model.state_scales, model.input_scales, model.output_scales))
    A,B,C,D = map(np.asarray,(model.A,model.B,model.C,model.D))
    return A*sx[None,:]/sx[:,None], B*su[None,:]/sx[:,None], C*sx[None,:]/sy[:,None], D*su[None,:]/sy[:,None]


def zoh(A,B,drift,dt):
    n,m=B.shape
    block=np.zeros((n+m+1,n+m+1))
    block[:n,:n]=A; block[:n,n:n+m]=B; block[:n,-1]=drift
    E=expm(dt*block)
    return E[:n,:n],E[:n,n:n+m],E[:n,-1]


def finite_gramian(A,B,T):
    # Van Loan on a short interval plus doubling avoids exp(-A*T) overflow
    # in strongly damped models. This works for stable, marginal and unstable A.
    n=len(A); halves=max(0,int(np.ceil(np.log2(max(1.,np.linalg.norm(A,1)*T/.5)))))
    h=T/2**halves
    E=expm(h*np.block([[A,B@B.T],[np.zeros_like(A),-A.T]]))
    F=E[:n,:n]; W=E[:n,n:]@F.T
    for _ in range(halves):
        W=W+F@W@F.T; F=F@F
    return (W+W.T)/2


def held_gramian(Ad,Bd,dt,steps):
    W=np.zeros_like(Ad)
    for _ in range(steps): W=Ad@W@Ad.T+Bd@Bd.T/dt
    return (W+W.T)/2


def aligned_steps(horizon_s, period_s, atol_s=1e-12):
    """Return an exact sampled horizon; never silently relabel a rounded one."""
    ratio=float(horizon_s)/float(period_s); steps=int(round(ratio)); effective=steps*float(period_s)
    if steps < 1 or abs(effective-float(horizon_s)) > float(atol_s):
        raise ValueError('SAMPLED_HORIZON_NOT_ALIGNED_WITH_PERIOD')
    return steps,effective


def spectrum(W,p):
    e,v=np.linalg.eigh((W+W.T)/2)
    tol=p.rank_atol+p.rank_rtol*max(0.,float(e[-1]))
    return dict(eigenvalues=e.tolist(),rank=int(sum(e>tol)),rank_threshold=tol,
        weak_directions=v[:,:min(3,len(e))].T.tolist(),
        psd_within_tolerance=bool(e[0]>=-tol),
        condition=None if e[0]<=tol else float(e[-1]/e[0]))


def correction(G,delta,p):
    e,v=np.linalg.eigh((G+G.T)/2); tol=p.rank_atol+p.rank_rtol*max(0.,float(e[-1]))
    keep=e>tol; coeff=v.T@delta; unreachable=v[:,~keep]@coeff[~keep]
    valid=np.linalg.norm(unreachable)<=p.comparison_atol+p.comparison_rtol*np.linalg.norm(delta)
    return dict(energy=float(np.sum(coeff[keep]**2/e[keep])) if valid else None,
        reachable=bool(valid),unreachable_output_normalized=unreachable.tolist(),
        projected_energy=float(np.sum(coeff[keep]**2/e[keep])),units='s (normalized input squared integral)',
        reason=None if valid else 'Target component outside numerically reachable output subspace')


def raw_scipy(A,B,C,D,drift,p):
    sampling=[]
    for T in p.windows_s:
        steps,effective=aligned_steps(T,p.period_s,getattr(p,'horizon_alignment_atol_s',1e-12))
        sampling.append(dict(requested_horizon_s=T,effective_horizon_s=effective,step_count=steps,period_s=p.period_s))
    Ad,Bd,gd=zoh(A,B,drift,p.period_s)
    frequencies=[]; singular=[]
    for w in p.frequency_rad_s:
        H=C@np.linalg.solve(1j*w*np.eye(len(A))-A,B)+D
        frequencies.append(dict(real=H.real.tolist(),imag=H.imag.tolist()))
        singular.append(np.linalg.svd(H,compute_uv=False).tolist())
    poles=np.linalg.eigvals(A)
    return dict(A_d=Ad.tolist(),B_d=Bd.tolist(),drift_d=gd.tolist(),
        poles=np.column_stack((poles.real,poles.imag)).tolist(),
        frequency_response=frequencies,singular_values=singular,
        continuous_gramians=[finite_gramian(A,B,T).tolist() for T in p.windows_s],
        held_gramians=[held_gramian(Ad,Bd,p.period_s,row['step_count']).tolist() for row in sampling],
        held_sampling=sampling,
        gramian_algorithms=['scaled Van Loan matrix exponential and doubling']*len(p.windows_s))


def summarize(model,p,raw,implementation):
    A,B,C,D=normalized(model); drift=np.asarray(model.drift)/model.state_scales
    poles=np.asarray(raw['poles']); wn=np.linalg.norm(poles,axis=1)
    residual=float(np.linalg.norm(drift,np.inf))
    qualified=residual<=p.equilibrium_normalized_residual
    windows=[]
    for i,T in enumerate(p.windows_s):
        # delta input is zero: physical input held at u0, includes affine drift.
        _,_,endpoint=zoh(A,B,drift,T)
        yfree=np.asarray(model.y0)+np.asarray(model.output_scales)*(C@endpoint)
        target=model.binding.get('target_m')
        sampled=raw.get('held_sampling',[dict(requested_horizon_s=T,effective_horizon_s=T,
            step_count=aligned_steps(T,p.period_s)[0],period_s=p.period_s) for T in p.windows_s])[i]
        item=dict(window_s=T,effective_held_horizon_s=sampled['effective_horizon_s'],
            held_step_count=sampled['step_count'],remaining_task_s=model.operating_point.get('remaining_task_s'),
            nominal_window=True,zero_perturbation_input_endpoint_m=yfree.tolist(),
            direct_feedthrough_correction_supported=bool(np.all(D==0)))
        for label,key in [('continuous','continuous_gramians'),('held','held_gramians')]:
            W=np.asarray(raw[key][i]); G=C@W@C.T
            item[label]=dict(state=spectrum(W,p),output=spectrum(G,p),output_gramian=G.tolist(),
                energy_definition='integral ||delta u_normalized||^2 dt' if label=='continuous' else 'sum(dt * ||delta u_normalized_k||^2)',
                minimum_energy=None if target is None or np.any(D!=0) else correction(G,(np.asarray(target)-yfree)/model.output_scales,p))
        windows.append(item)
    curve=np.asarray(raw['singular_values'])[:,-1]
    band=None
    if p.authority_threshold is not None and curve[0]>=p.authority_threshold:
        stop=next((i for i,x in enumerate(curve) if x<p.authority_threshold),len(curve))
        band=[p.frequency_rad_s[0],p.frequency_rad_s[stop-1]]
    return dict(binding=model.binding,operating_point=model.operating_point,protocol_identity=model.protocol_identity,
        normalization=dict(state=model.state_scales,input=model.input_scales,output=model.output_scales,derivation=model.normalization_derivation),
        normalized_matrices=dict(A=A.tolist(),B=B.tolist(),C=C.tolist(),D=D.tolist(),drift=drift.tolist()),
        implementation=implementation,raw=raw,windows=windows,
        poles=dict(natural_frequency_rad_s=wn.tolist(),damping_ratio=[None if w==0 else float(-r/w) for r,w in zip(poles[:,0],wn)],
            unstable=int(sum(poles[:,0]>p.pole_margin_s_inv)),marginal=int(sum(abs(poles[:,0])<=p.pole_margin_s_inv))),
        validity=dict(equilibrium=qualified,normalized_drift_inf_s_inv=residual,
            frequency_interpretation='equilibrium LTI transfer' if qualified else 'non-equilibrium local frozen Jacobian'),
        authority=dict(frequency_rad_s=p.frequency_rad_s,minimum_singular_value=curve.tolist(),
            threshold=p.authority_threshold,connected_band_rad_s=band,reason=p.authority_reason,rule=p.authority_rule),
        tension_headroom_n=dict(lower=model.u0,upper=(np.asarray(model.binding['tension_limits_n'])-model.u0).tolist()),
        units=dict(poles='s^-1',frequency='rad/s',gramian='normalized squared coordinates per normalized input energy'))


def endpoint_map(model, horizon_s, period_s, alignment_atol_s=1e-12):
    """Exact-ZOH affine endpoint map from a sequence of physical delta tensions."""
    if model.time_domain != 'continuous':
        raise ValueError('CONTINUOUS_INPUT_MODEL_REQUIRED')
    steps,effective=aligned_steps(horizon_s,period_s,alignment_atol_s)
    A,B=np.asarray(model.A,dtype=float),np.asarray(model.B,dtype=float)
    drift=np.asarray(model.drift,dtype=float)
    Ad,Bd,gd=zoh(A,B,drift,period_s)
    nx,nu=B.shape
    influence=np.zeros((nx,steps*nu)); affine=np.zeros(nx)
    for k in range(steps):
        power=np.linalg.matrix_power(Ad,steps-1-k)
        influence[:,k*nu:(k+1)*nu]=power@Bd
        affine+=power@gd
    return dict(A_d=Ad,B_d=Bd,drift_d=gd,affine_state=affine,influence=influence,
        step_count=steps,effective_horizon_s=effective,period_s=float(period_s))


def _output_endpoint(model, mapping, name):
    output=next(row for row in model.endpoint_outputs if row.name==name)
    C,D=np.asarray(output.C,dtype=float),np.asarray(output.D,dtype=float)
    base=np.asarray(output.value0,dtype=float)+C@mapping['affine_state']
    matrix=C@mapping['influence']
    # An instantaneous output can depend on the final held input. The current
    # tendon model has D=0, but the affine contract remains dimensionally exact.
    nu=len(model.u0)
    matrix[:,-nu:]+=D
    return output,base,matrix


def _minimum_residual_certificate(matrix, base, target, lower, upper, limit, atol):
    """Return a candidate upper bound and a separately checkable dual lower bound.

    ``lsq_linear`` is useful for finding a small residual, but its success flag is
    not a proof that the returned residual is the global minimum at the scale of
    the problem.  A unit separating direction supplies a sound lower bound over
    the complete box, independently of that flag.
    """
    matrix=np.asarray(matrix,dtype=float); base=np.asarray(base,dtype=float)
    target=np.asarray(target,dtype=float); lower=np.asarray(lower,dtype=float); upper=np.asarray(upper,dtype=float)
    b=target-base
    residual_scale=max(float(np.linalg.norm(b,np.inf)),float(np.max(np.abs(matrix),initial=0.)*
        np.max(np.maximum(np.abs(lower),np.abs(upper)),initial=0.)),float(limit),float(atol),np.finfo(float).tiny)
    fit=lsq_linear(matrix/residual_scale,b/residual_scale,bounds=(lower,upper),tol=1e-12,max_iter=100)
    candidate=np.asarray(fit.x,dtype=float)
    residual_vector=matrix@candidate-b
    candidate_residual=float(np.linalg.norm(residual_vector))
    if candidate_residual>0 and np.all(np.isfinite(residual_vector)):
        direction=residual_vector/candidate_residual
        coefficients=matrix.T@direction
        box_terms=np.minimum(coefficients*lower,coefficients*upper)
        raw_bound=float(-direction@b+np.sum(box_terms))
    else:
        direction=np.zeros_like(b); coefficients=np.zeros(matrix.shape[1]); box_terms=np.zeros(matrix.shape[1])
        raw_bound=0.
    lower_bound=max(0.,raw_bound)
    roundoff=16*np.finfo(float).eps*(1.+abs(float(direction@b))+float(np.sum(np.abs(box_terms))))
    numerical_allowance=float(atol)+float(roundoff)
    margin=float(lower_bound-float(limit)-numerical_allowance)
    certified=bool(np.isfinite(lower_bound) and margin>0.)
    return dict(certified_infeasible=certified,candidate_residual=candidate_residual,
        candidate_residual_role='upper_bound_on_minimum_residual_not_a_proven_lower_bound',limit=float(limit),
        solver='scipy.optimize.lsq_linear',solver_success=bool(fit.success),optimality=float(fit.optimality),
        solver_residual_scale=residual_scale,
        candidate_delta_input=candidate.tolist(),candidate_residual_vector=residual_vector.tolist(),
        separating_direction=dict(direction=direction.tolist(),unit_norm=float(np.linalg.norm(direction)),
            lower_bound=lower_bound,raw_bound=raw_bound,numerical_allowance=numerical_allowance,
            margin_over_limit=margin,target_minus_base=b.tolist(),matrix_transpose_direction=coefficients.tolist(),
            box_min_terms=box_terms.tolist(),lower=lower.tolist(),upper=upper.tolist(),
            formula='max(0, -v.T@(target-base) + sum(min((P.T@v)*lower,(P.T@v)*upper)))'),
        reason='Separating-direction lower bound exceeds the limit with positive numerical margin.' if certified
            else 'No independently checkable lower bound exceeds the permitted residual.')


def bounded_endpoint(model,p,target, *, braking=False, warm_start=None):
    """One convex SLSQP endpoint solve with independently checked witnesses."""
    remaining=model.operating_point.get('remaining_task_s')
    if remaining is None or remaining <= 0:
        return dict(question='position_and_braking' if braking else 'position_only',status='unavailable',
            reason='Positive remaining task duration unavailable.')
    mapping=endpoint_map(model,remaining,p.period_s,p.horizon_alignment_atol_s)
    position,pbase,P=_output_endpoint(model,mapping,'tip_position')
    velocity,vbase,V=_output_endpoint(model,mapping,'tip_velocity')
    desired_p=np.asarray(target.position_m,dtype=float); desired_v=np.asarray(target.tip_velocity_m_s,dtype=float)
    steps,nu=mapping['step_count'],len(model.u0)
    u0=np.tile(np.asarray(model.u0,dtype=float),steps)
    limits=np.tile(np.asarray(model.binding['tension_limits_n'],dtype=float),steps)
    lower,upper=-u0,limits-u0
    scale=np.tile(np.asarray(model.input_scales,dtype=float),steps)
    x0=np.zeros(steps*nu) if warm_start is None else np.clip(np.asarray(warm_start,dtype=float),lower,upper)
    dt=float(p.period_s)
    def objective(z): return float(dt*np.sum((z/scale)**2))
    def objective_jac(z): return 2*dt*z/(scale**2)
    def pos_fun(z):
        r=pbase+P@z-desired_p
        return float(target.position_tolerance_m**2-r@r)
    def pos_jac(z): return -2*(pbase+P@z-desired_p)@P
    constraints=[dict(type='ineq',fun=pos_fun,jac=pos_jac)]
    if braking:
        def speed_fun(z):
            r=vbase+V@z-desired_v
            return float(target.tip_speed_limit_m_s**2-r@r)
        def speed_jac(z): return -2*(vbase+V@z-desired_v)@V
        constraints.append(dict(type='ineq',fun=speed_fun,jac=speed_jac))
    solved=minimize(objective,x0,jac=objective_jac,bounds=Bounds(lower,upper),constraints=constraints,
        method='SLSQP',options=dict(maxiter=p.endpoint_max_iterations,ftol=1e-12,disp=False))
    z=np.asarray(solved.x,dtype=float); applied=(u0+z).reshape(steps,nu)
    pend=pbase+P@z; vend=vbase+V@z
    position_error=float(np.linalg.norm(pend-desired_p)); speed=float(np.linalg.norm(vend-desired_v))
    atol=float(p.endpoint_check_atol)
    checks=dict(finite=bool(np.all(np.isfinite(z))),
        lower_bounds=bool(np.all(applied>=-atol)),upper_bounds=bool(np.all(applied<=limits.reshape(steps,nu)+atol)),
        position=bool(position_error<=target.position_tolerance_m+atol),
        speed=True if not braking else bool(speed<=target.tip_speed_limit_m_s+atol))
    feasible=all(checks.values())
    pc=_minimum_residual_certificate(P,pbase,desired_p,lower,upper,target.position_tolerance_m,atol)
    vc=_minimum_residual_certificate(V,vbase,desired_v,lower,upper,target.tip_speed_limit_m_s,atol)
    certificate=pc if pc['certified_infeasible'] else vc if braking and vc['certified_infeasible'] else None
    status='feasible_in_local_model' if feasible else 'infeasible_in_local_model' if certificate else 'undetermined'
    return dict(question='position_and_braking' if braking else 'position_only',status=status,
        model_scope='Frozen continuous local affine model, exact ZOH held inputs; not nonlinear or physical feasibility.',
        sampled_horizon=dict(requested_s=remaining,effective_s=mapping['effective_horizon_s'],
            period_s=mapping['period_s'],step_count=steps),
        solver=dict(name='scipy.optimize.SLSQP',success=bool(solved.success),status=int(solved.status),
            message=str(solved.message),iterations=int(solved.nit),maximum_iterations=p.endpoint_max_iterations),
        endpoint=dict(position_m=pend.tolist(),position_error_m=position_error,
            tip_velocity_m_s=vend.tolist(),tip_speed_m_s=speed,
            zero_perturbation_position_m=pbase.tolist(),zero_perturbation_tip_velocity_m_s=vbase.tolist()),
        checks=checks,infeasibility_certificate=certificate,
        independent_residual_problems=dict(position=pc,tip_speed=vc),
        tension_bounds_n=dict(lower=[0.]*nu,upper=np.asarray(model.binding['tension_limits_n']).tolist(),
            delta_lower=(-np.asarray(model.u0)).tolist(),delta_upper=(np.asarray(model.binding['tension_limits_n'])-np.asarray(model.u0)).tolist()),
        normalized_input_energy=objective(z),delta_input_n=z.reshape(steps,nu).tolist(),
        applied_input_n=applied.tolist(),warm_start_used=warm_start is not None,
        affine_endpoint=dict(drift_d=mapping['drift_d'].tolist(),affine_state=mapping['affine_state'].tolist()),
        output_contract=dict(position=position.model_dump(mode='json'),tip_velocity=velocity.model_dump(mode='json')))


def versions():
    return dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__)
