"""Approved fixed-step target: independent SPD solve and algebraic error audit."""
import time
import numpy as np
from scipy.linalg import cho_factor,cho_solve
from .milestone5_fullstate import DiscreteFullState
from .milestone5_campaign_localization import forward_terms

VERSION='fixed_backend_cholesky_audit@1.0.0'


def predict(model,state,command,*,duration_s=.01,deadline):
    start=time.perf_counter();h=float(model.model.opt.timestep)
    if h!=.0005:raise ValueError('REGISTERED_FIXED_BACKEND_STEP_REQUIRED')
    n=model.full_n;x=np.asarray(state).copy();rows=[];steps=round(duration_s/h)
    if abs(steps*h-duration_s)>1e-12:raise ValueError('FIXED_ENDPOINT_ALIGNMENT')
    for i in range(steps):
        if time.perf_counter()>deadline:raise RuntimeError('FIXED_TRANSITION_DEADLINE')
        terms=forward_terms(model,x[:n],x[n:],np.asarray(command));matrix=terms['mass']+h*model.damping
        factor=cho_factor(matrix,lower=True,check_finite=True);a=cho_solve(factor,terms['force'])
        residual=matrix@a-terms['force'];absolute=float(np.linalg.norm(residual,np.inf))
        norm_matrix=float(np.linalg.norm(matrix,np.inf));norm_inverse=float(np.linalg.norm(cho_solve(factor,np.eye(n)),np.inf))
        denominator=norm_matrix*float(np.linalg.norm(a,np.inf))+float(np.linalg.norm(terms['force'],np.inf))
        backward=absolute/max(denominator,np.finfo(float).tiny)
        # A posteriori estimate for THIS linear system, not a global nonlinear
        # propagation error bound and not a physical uncertainty interval.
        bound=norm_inverse*absolute;condition=norm_matrix*norm_inverse
        row=dict(step=i,scaled_residual=absolute/.001,backward_error=backward,condition_estimate_inf=condition,
            acceleration_error_estimate_inf_rad_s2=bound,local_velocity_increment_error_estimate_rad_s=h*bound,
            local_position_increment_error_estimate_rad=h*h*bound)
        if not np.isfinite(a).all() or row['scaled_residual']>1e-5 or backward>1e-12:raise ValueError('FIXED_ALGEBRAIC_CHECK_FAILED')
        x[n:]+=h*a;x[:n]+=h*x[n:];rows.append(row)
    if model.data.time!=0.:raise ValueError('ENGINE_CLOCK_MUST_NOT_ADVANCE')
    return dict(version=VERSION,state=x.tolist(),**model.motion(x),step_s=h,step_count=steps,rows=rows,
        initial_state=list(state),input_n=list(command),duration_s=duration_s,cost_s=time.perf_counter()-start,
        complete=True,backend_steps=0,emulated_physics_steps=steps,reference_scope='Fixed-step simulation transition only; shared MuJoCo point mechanics, independent linear solver, no independent backend validation.')
