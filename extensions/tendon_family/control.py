"""Physical realization of independent ideal-tension commands."""
import numpy as np
def execute_ideal_tension(physics, requested_tensions):
    """Clip a model-space tension command without applying actuator kinematics."""
    requested=np.asarray(requested_tensions,dtype=float)
    force=np.array([x['force_limit_n'] for x in physics['tendons']])
    if requested.shape!=force.shape or not np.isfinite(requested).all():
        raise ValueError('IDEAL_TENSION_INPUT_REQUIRES_FINITE_TENDON_VECTOR')
    desired=np.clip(requested,0.,force)
    telemetry=dict(requested_tension_n=requested.tolist(),desired_tension_n=desired.tolist(),
        predicted_tension_n=desired.tolist(),tension_tracking_error_n=np.zeros_like(desired).tolist(),
        force_limit_saturated=(requested!=desired).tolist())
    return desired,telemetry
