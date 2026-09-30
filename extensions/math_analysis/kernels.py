"""Finite local LTI calculations in declared normalized coordinates."""
import platform
import numpy as np
import scipy
from scipy.linalg import expm

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
        held_gramians=[held_gramian(Ad,Bd,p.period_s,round(T/p.period_s)).tolist() for T in p.windows_s],
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
        item=dict(window_s=T,remaining_task_s=model.operating_point.get('remaining_task_s'),
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


def versions():
    return dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__)
