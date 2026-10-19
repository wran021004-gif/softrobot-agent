"""Pure bounded target-directed seed calculation; evidence, costs and execution belong to callers."""
import numpy as np
from scipy.optimize import lsq_linear


def directed_inputs(reference, response, displacement, limits, radius, regularization):
    """Constant local input offsets, bounded at every interval; no acceptance claim."""
    u=np.asarray(reference,dtype=float);r=np.asarray(response,dtype=float)
    target=np.asarray(displacement,dtype=float);limits=np.asarray(limits,dtype=float)
    if (u.ndim!=2 or r.shape!=(3,u.shape[1]) or target.shape!=(3,) or limits.shape!=(u.shape[1],)
            or not all(np.isfinite(x).all() for x in (u,r,target,limits))
            or np.any(u<0) or np.any(u>limits) or radius<=0 or regularization<=0):
        raise ValueError('FINITE_BOUND_LOCAL_SEED_INPUTS_REQUIRED')
    singular=np.linalg.svd(r,compute_uv=False);rank=int(np.linalg.matrix_rank(r))
    diagnostic=dict(rank=rank,singular_values=singular.tolist(),response_m_per_n=r.tolist(),
        prospective_guarantee=False,task_acceptance='unmeasured')
    if rank<min(r.shape) or singular[rank-1]<1e-10 or singular[0]/singular[rank-1]>1e8:
        return dict(status='unreliable_response',**diagnostic)
    lower=np.maximum(-radius,np.max(-u,axis=0));upper=np.minimum(radius,np.min(limits-u,axis=0))
    free=upper-lower>1e-12
    if not np.any(free):return dict(status='no_input_room',**diagnostic)
    a=np.vstack([r,np.sqrt(regularization)*np.eye(u.shape[1])]);b=np.r_[target,np.zeros(u.shape[1])]
    delta=(lower+upper)/2
    fit=lsq_linear(a[:,free],b-a[:,~free]@delta[~free],bounds=(lower[free],upper[free]),tol=1e-12)
    if not fit.success:return dict(status='numerical_failure',reason=fit.message,**diagnostic)
    delta[free]=fit.x
    return dict(status='generated',inputs=np.clip(u+delta,0,limits).tolist(),delta_n=delta.tolist(),
        predicted_displacement_m=(r@delta).tolist(),prediction_residual_m=float(np.linalg.norm(r@delta-target)),
        **diagnostic)
