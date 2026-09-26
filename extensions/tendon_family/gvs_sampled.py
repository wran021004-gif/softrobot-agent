"""Exact held-input linearization and discrete-stage-cost LQR."""
import numpy as np
from scipy.linalg import expm, solve_discrete_are
from schemas.platform_math import LinearizedModel
from .gvs_casadi import ContinuousLQRController
from .gvs_lqr import GVSLQRController


def zero_order_hold(model, period_s):
    model = LinearizedModel.model_validate(model)
    if model.time_domain != 'continuous' or period_s <= 0:
        raise ValueError('ZOH_REQUIRES_CONTINUOUS_MODEL_AND_POSITIVE_PERIOD')
    A, B = np.asarray(model.A), np.asarray(model.B)
    n, m = B.shape
    augmented = np.zeros((n+m+1,n+m+1))
    augmented[:n,:n], augmented[:n,n:n+m] = A, B
    augmented[:n,-1] = np.zeros(n) if model.drift is None else model.drift
    transition = expm(period_s*augmented)
    return model.model_copy(update=dict(A=transition[:n,:n].tolist(),
        B=transition[:n,n:n+m].tolist(), drift=transition[:n,-1].tolist(),
        time_domain='discrete', timestep=period_s))


class DiscreteLQRController(ContinuousLQRController):
    """Q/R are discrete stage weights in the declared x/u coordinates."""
    def configure_model(self, model):
        model = LinearizedModel.model_validate(model)
        if model.time_domain != 'discrete':
            raise ValueError('DISCRETE_LQR_REQUIRES_DISCRETE_MODEL')
        if np.linalg.norm(model.drift if model.drift is not None else np.zeros(len(model.x0)),np.inf)>self.parameters.equilibrium_tolerance:
            raise ValueError('LQR_OPERATING_POINT_NOT_EQUILIBRIUM')
        if [s.entity for s in model.input_definition] != self.parameters.tendon_order:
            raise ValueError('LQR_TENDON_ORDER_MISMATCH')
        A,B,Q,R = map(np.asarray,(model.A,model.B,self.parameters.Q,self.parameters.R))
        if Q.shape != A.shape or R.shape != (B.shape[1],B.shape[1]):
            raise ValueError('LQR_MODEL_WEIGHT_DIMENSION_MISMATCH')
        if not np.allclose(Q,Q.T) or min(np.linalg.eigvalsh(Q)) < 0 or not np.allclose(R,R.T) or min(np.linalg.eigvalsh(R)) <= 0:
            raise ValueError('LQR_INVALID_COST_WEIGHTS')
        P=solve_discrete_are(A,B,Q,R)
        self.K=np.linalg.solve(R+B.T@P@B,B.T@P@A)
        self.spectral_radius=float(max(abs(np.linalg.eigvals(A-B@self.K))))
        if self.spectral_radius >= 1:
            raise ValueError('DISCRETE_LQR_NOT_STABLE')
        self.model=model
        return self.K.copy()


class GVSSampledLQRController(GVSLQRController):
    """Backend adapter: inherited bounded law, called once per control interval."""
