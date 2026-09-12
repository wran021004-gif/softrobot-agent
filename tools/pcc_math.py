"""Differentiation of approved single-section PCC geometry; no mechanics model."""
import math


def analytic_target_matching_length(target):
    """Invert the approved origin/+x PCC tip on theta in [0, pi]."""
    x, y, z = target
    rho = math.hypot(y, z)
    if not all(math.isfinite(v) for v in target) or x < 0 or (x == 0 and rho == 0):
        raise ValueError('No positive-length target match on the approved PCC branch')
    theta = 2*math.atan2(rho, x)
    if rho == 0:
        return {'total_length_m': x, 'theta_rad': 0., 'phi_rad': 0.}
    return {'total_length_m': theta*(x*x+rho*rho)/(2*rho),
            'theta_rad': theta, 'phi_rad': math.atan2(z, y)}


def tip_and_jacobian(length, bend):
    """b=(theta*cos(phi),theta*sin(phi)); J=d(tip)/db, meters/radian.

    Taylor evaluation near zero avoids cancellation; it is the analytic straight
    limit, not an empirical mismatch or controller acceptance threshold.
    """
    u, v = bend
    t = math.hypot(u, v)
    if not all(math.isfinite(x) for x in (length, u, v)) or length <= 0 or t > math.pi:
        raise ValueError("PCC requires finite inputs on the approved [0,pi] branch")
    if t < 1e-4:
        t2 = t * t
        a = 1 - t2 / 6 + t2 * t2 / 120 - t2**3 / 5040
        c = .5 - t2 / 24 + t2 * t2 / 720 - t2**3 / 40320
        da = -1/3 + t2/30 - t2*t2/840
        dc = -1/12 + t2/180 - t2*t2/6720
    else:
        a = math.sin(t) / t
        c = 2 * math.sin(t / 2)**2 / t**2
        da = (t * math.cos(t) - math.sin(t)) / t**3
        dc = (t * math.sin(t) - 4 * math.sin(t / 2)**2) / t**4
    tip = [length * a, length * c * u, length * c * v]
    jac = [[length * da * u, length * da * v],
           [length * (c + dc*u*u), length * dc*u*v],
           [length * dc*u*v, length * (c + dc*v*v)]]
    return tip, jac


def pcc_sensitivity(robot_ir, theta_rad, phi_rad):
    """Local geometric derivative only; not a varied-design experiment."""
    from schemas.tool_result import ToolResult
    bend = [theta_rad * math.cos(phi_rad), theta_rad * math.sin(phi_rad)]
    tip, jac = tip_and_jacobian(robot_ir.total_length_m, bend)
    return ToolResult(tool="pcc_sensitivity", status="pass", metrics={
        "fidelity": "M1/MODEL", "gate_semantics": "SCREENING",
        "tip_m": tip, "tip_jacobian_m_per_rad": jac,
        "tip_length_derivative": [x / robot_ir.total_length_m for x in tip],
        "tendon_jacobian_m_per_rad": [[-robot_ir.tendon_routing_radius_m * math.cos(r.angle_rad),
                                       -robot_ir.tendon_routing_radius_m * math.sin(r.angle_rad)] for r in robot_ir.tendon_routes],
        "causal_attribution": "UNKNOWN"})
