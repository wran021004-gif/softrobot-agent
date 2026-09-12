"""Geometric tendon commands and Jacobians; no required-force model."""
import math
import numpy as np
from schemas.tool_result import ToolResult
from tools.pcc_math import pcc_sensitivity


def analyze_actuation(robot_ir, model_result):
    if model_result.status != 'pass':
        raise ValueError('Completed M1 PCC result required')
    m = model_result.metrics
    theta, phi = float(m['theta_rad']), float(m['phi_rad'])
    length, radius, count = robot_ir.total_length_m, robot_ir.tendon_routing_radius_m, robot_ir.tendon_count
    target = np.asarray(m['tendon_target_lengths_m'], dtype=float)
    if target.shape != (count,) or not np.all(np.isfinite(target)):
        raise ValueError('Invalid ordered tendon commands')
    expected = np.asarray([length-radius*theta*math.cos(route.angle_rad-phi) for route in robot_ir.tendon_routes])
    if not np.allclose(target, expected, rtol=1e-12, atol=1e-14):
        raise ValueError('PCC command/RobotIR mismatch')
    jac = np.asarray(pcc_sensitivity(robot_ir, theta, phi).metrics['tendon_jacobian_m_per_rad'])
    singular = np.linalg.svd(jac, compute_uv=False)
    rank = int(np.linalg.matrix_rank(jac))
    condition = float(singular[0]/singular[-1]) if rank == 2 else None
    strokes = target-length
    maximum = float(np.max(np.abs(strokes)))
    return ToolResult(tool='analyze_actuation', status='pass', metrics={
        'scope': 'GEOMETRIC_ACTUATION_ONLY', 'neutral_tendon_lengths_m': [length]*count,
        'target_tendon_lengths_m': target.tolist(), 'signed_tendon_strokes_m': strokes.tolist(),
        'absolute_tendon_strokes_m': np.abs(strokes).tolist(), 'maximum_tendon_stroke_m': maximum,
        'stroke_span_m': float(np.ptp(strokes)), 'stroke_over_robot_length': (strokes/length).tolist(),
        'maximum_stroke_over_robot_length': maximum/length,
        'command_positivity': bool(np.all(target > 0)), 'routing_radius_m': radius,
        'tendon_count': count, 'theta_rad': theta, 'phi_rad': phi,
        'bending_coordinates': ['theta*cos(phi)', 'theta*sin(phi)'],
        'tendon_jacobian_m_per_rad': jac.tolist(), 'jacobian_rank': rank,
        'singular_values_m_per_rad': singular.tolist(), 'condition_number': condition,
        'condition_number_status': 'defined' if condition is not None else 'rank_deficient',
        'rank_tolerance': 'numpy matrix_rank machine-precision SVD tolerance; not a scientific feasibility threshold',
        'comparison_context': m.get('comparison_context'),
        'limitation': 'Geometry only. No required tendon force, motor torque, physical feasibility or real mechanical advantage.'})
