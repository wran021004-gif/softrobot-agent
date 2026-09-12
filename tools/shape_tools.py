"""Compare normal model/simulator shape artifacts; no debug inputs or causal gate."""
import numpy as np
from schemas.tool_result import ToolResult


def final_centerline(model, data):
    """Proximal segment origins plus distal tip, read after existing final forward."""
    points = []
    i = 0
    while True:
        try:
            body = model.body(f'segment_{i}')
        except KeyError:
            break
        points.append(data.xpos[body.id].tolist())
        i += 1
    if not points:
        raise ValueError('No V1 segment bodies')
    points.append(data.site_xpos[model.site('tip_site').id].tolist())
    return points


def _shape(value):
    points = np.asarray(value, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 2 or not np.all(np.isfinite(points)):
        raise ValueError('Finite Nx3 centerline required')
    distances = np.linalg.norm(np.diff(points, axis=0), axis=1)
    if np.any(distances <= 0):
        raise ValueError('Centerline must have positive segment lengths')
    s = np.concatenate(([0.], np.cumsum(distances)))
    return points, s/s[-1]


def compare_shape_model_sim(model_shape, simulation_result):
    """65 compact correspondences; RMS is over equally spaced normalized arc length."""
    try:
        m, s = model_shape.metrics, simulation_result.metrics
        context = m.get('comparison_context')
        if (m.get('scope') != 'MODEL_SHAPE_EVIDENCE' or not context or context != s.get('comparison_context')
                or 'task_success' not in s or model_shape.status != 'pass'):
            raise ValueError('Matching completed normal model/simulator evidence required')
        commands = m['tendon_target_lengths_m']
        if any(row['command_min_m'] != row['command_max_m'] for row in s['execution_evidence']['actuators']):
            return ToolResult(tool='compare_shape_model_sim', status='pass', metrics={
                'evidence_status':'NOT_APPLICABLE_TIME_VARYING_COMMAND', 'failure_attribution':'UNKNOWN'},
                message='Initial PCC and final C2 do not share a constant command; no same-command mismatch computed.')
        if commands != s.get('tendon_target_lengths_m'):
            raise ValueError('Commands differ')
        for row, command in zip(s['execution_evidence']['actuators'], commands):
            if row['command_min_m'] != command or row['command_max_m'] != command:
                raise ValueError('Time-varying controller lacks a matching PCC shape prediction')
        predicted, _ = _shape(model_shape.artifacts['centerline_m'])
        actual, actual_s = _shape(simulation_result.artifacts['final_centerline_m'])
        model_s = np.asarray(m['normalized_arc_length'], dtype=float)
        if (model_s.shape != (len(predicted),) or not np.all(np.isfinite(model_s)) or
                model_s[0] != 0 or model_s[-1] != 1 or np.any(np.diff(model_s) <= 0)):
            raise ValueError('Invalid normalized PCC arc coordinates')
        uniform = np.linspace(0., 1., 65)
        pred = np.column_stack([np.interp(uniform, model_s, predicted[:,i]) for i in range(3)])
        sim = np.column_stack([np.interp(uniform, actual_s, actual[:,i]) for i in range(3)])
        delta = sim-pred
        norms = np.linalg.norm(delta, axis=1)
        index = int(np.argmax(norms))
        return ToolResult(tool='compare_shape_model_sim', status='pass', metrics={
            'evidence_status': 'available', 'failure_attribution': 'UNKNOWN',
            'comparison_context': context, 'tip_discrepancy_m': float(norms[-1]),
            'centerline_rms_discrepancy_m': float(np.sqrt(np.mean(norms**2))),
            'maximum_centerline_discrepancy_m': float(norms[index]),
            'maximum_discrepancy_normalized_arc_length': float(uniform[index]),
            'maximum_discrepancy_model_location_m': pred[index].tolist(),
            'maximum_discrepancy_simulation_location_m': sim[index].tolist(),
            'threshold': None, 'sampling': '65 uniformly spaced normalized arc-length correspondences; MuJoCo polyline interpolation',
            'per_sample_differences': [{'s':float(u), 'delta_xyz_m':d.tolist(), 'distance_m':float(n)}
                                       for u,d,n in zip(uniform,delta,norms)]},
            artifacts={'evidence_paths': ['model_shape.json','mujoco_result.json']})
    except (KeyError, ValueError, TypeError) as exc:
        return ToolResult(tool='compare_shape_model_sim', status='fail', failure_code='UNKNOWN',
            metrics={'evidence_status':'unavailable','failure_attribution':'UNKNOWN'}, message=str(exc))
