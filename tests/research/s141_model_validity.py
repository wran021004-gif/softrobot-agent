"""S141: one frozen S140 pair, existing GVS operating points and affine checks.

No physical rollout, target search, nonlinear controller, or Study is launched.
"""
import argparse
from contextlib import ExitStack
from copy import deepcopy
from importlib.metadata import version
import json
from pathlib import Path
import time
from unittest.mock import patch

import numpy as np

from extensions.tendon_family import math_analysis as ma
from extensions.math_analysis.trajectory import sampled_maps
from schemas.platform_analysis import TaskAnalysisProtocol, EndpointLinearizedModel
from tools.platform_store import plain


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def archive_input(root):
    """Audit saved results only; preserve every old file and optimizer failure."""
    summary = read(root/'evidence/s140_structure_effect/summary.json')
    rows = [(r['id'], r['B']) for r in summary['candidates']]
    rows += [(r['structure']+'-'+r['target'], r['C']) for r in summary['comparisons']]
    checks, cases = [], {}
    floor = summary['conclusion']['affine_axial_floor']
    for name, exported in rows:
        raw = read(root/'runs/s140_structure_effect'/f'{name}.json')
        math = raw['mathematics']; t = math['trajectory']
        score = max(r['signed_violation'] for r in t['replay']['records'])
        assert abs(score-exported['signed_violation']) < 1e-12
        assert t['solver']['status'] == 'optimal' and t['optimality_status'] == 'numerically_checked'
        assert t['all_requested_checked'] and t['replay']['numerically_valid']
        assert t['primal_checks']['box_violation_n'] == 0
        invariant = [raw['configuration']['task'][k] for k in ('environment', 'initializer', 'timing')]
        invariant += [raw['configuration']['policy']['controller'], math['model']['x0'], math['model']['u0']]
        if checks:
            assert invariant == first_invariant
        else:
            first_invariant = invariant
        checks.append(dict(case=name, score=score, gap_to_axial_floor=score-floor,
            support_gap=t['dual_checks']['replayed_support_gap'],
            replay_error=t['replay']['max_prediction_replay_error'],
            solver=t['solver']['status'], iterations=t['solver']['iterations'],
            geometry=exported['locality']))
        if name in ('yz_plus', 'near_shorter-yz_plus'):
            cases['baseline' if name == 'yz_plus' else 'near_shorter'] = dict(
                configuration=raw['configuration'], binding=math['binding'],
                saved_model=math['model'], task_analysis=math['task_analysis'],
                saved_states=t['replay']['states'], saved_controls=t['applied_input_n'])
    assert len(checks) == 14 and len(summary['candidates']) == 6
    # Frozen authorization, not a new grant or a modified current study.
    bounds = read(root/'configs/research/study.json')['allowed_parameters']
    from tools.research.design import parameter_value
    for case in cases.values():
        params = case['configuration']['policy']['candidate_builder']['parameters']['data']
        for name, (lo, hi) in bounds.items():
            if name.startswith('segments.'):
                assert lo <= parameter_value(params, name) <= hi
        assert abs(sum(v['length_m'] for v in params['segments'].values())-.27) < 1e-12
    return dict(version='s141-frozen-input-v1', source_commit='2913fbb1122374ca16136b123c79c070a80f65b5',
        baseline_commit='4de5d5d47', source='S140 saved yz_plus and near_shorter-yz_plus; no old code merged',
        audit=dict(cases=checks, targets=6, conic_solves=14, geometry_qualified_pair=False,
            common_environment_initializer_timing_controller=True,
            max_abs_C_minus_B=summary['conclusion']['max_abs_C_minus_B'], budgets=summary['budgets']),
        legal_parameter_bounds=bounds, protocol=summary['protocol'], cases=cases,
        scope='GVS bending-only model: 12 curvature coefficients and 12 rates; six ideal tensions in N; world XYZ in m',
        plan=dict(target='yz_plus', change='near -5 mm, distal +5 mm; fixed total .27 m',
            operating_points=['controller_start_input', 'target_equilibrium', 'halfway_waypoint'],
            construction='Existing single attempts, 20 iterations/evaluations; no recovery',
            displacement_fractions=[.01, .05, .1, 1.],
            parameter_comparison='Two rebuilt structures at a shared solved baseline anchor and identical states/inputs',
            reoptimization='At most one existing CONIC per structure about the same available baseline bent anchor; original zero initial state and full .35 s task, no claim of validity',
            stop='No extra target/structure, no MuJoCo or NMPC; conclude and stop prescreening'))


def geometry_errors(h, model, states, controls):
    x0, u0 = np.asarray(model.x0), np.asarray(model.u0)
    exact = np.array([np.asarray(h(x, u)[0]).ravel() for x, u in zip(states, controls)])
    affine = np.asarray(model.y0)+(states-x0)@np.asarray(model.C).T+(controls-u0)@np.asarray(model.D).T
    error = np.linalg.norm(exact-affine, axis=1)
    return dict(max_m=float(max(error)), holding_max_m=float(max(error[-6:])),
        terminal_m=float(error[-1]), error_m=error.tolist(), exact_world_m=exact.tolist(), affine_world_m=affine.tolist())


def legal_point(point, limits):
    if not point.get('available'):
        return False
    x, u = np.asarray(point['x']), np.asarray(point['u'])
    return bool(np.all(np.isfinite(x)) and np.all(np.isfinite(u)) and np.all(u >= 0) and np.all(u <= limits))


def returned_geometry_point(saved, graph, tolerance):
    """Validate returned IK coordinates independently, without changing solver status.

    This does not admit the failed halfway constructor or assert equilibrium.
    It only provides an actual finite GVS state for conditional Taylor checks.
    """
    waypoint = next(v for v in saved['points'] if v['name'] == 'halfway_waypoint')
    q = next(v['x'] for v in saved['optimizer_returns'] if v['kind'] == 'least_squares_attempts')
    u = [t['pretension_n'] for t in graph[0].robot.structure.data['tendons']]
    x = q+[0.]*len(q)
    achieved = np.asarray(graph[3](x, u)[0]).ravel()
    residual = float(np.linalg.norm(achieved-waypoint['construction']['requested_world_point_m']))
    point = dict(name='returned_ik_geometry', x=x, u=u, available=residual <= tolerance,
        phase='independently_checked_geometry_only', scope='Returned failed-IK iterate; not static equilibrium',
        remaining_task_s=.35, actual_time_s=None,
        construction=dict(source='Saved failed halfway least-squares return, no recovery or extra solve',
            optimizer_success=waypoint['construction']['success'], optimizer_status=waypoint['construction']['status'],
            constructor_available=waypoint['available'], independent_position_residual_m=residual,
            check_tolerance_m=tolerance, static_equilibrium=False, achieved_world_point_m=achieved.tolist()))
    return point


def dynamics_errors(graph, model, states, controls):
    actual = np.array([graph[2].evaluate(x, u)['xdot'].ravel() for x,u in zip(states, controls)])
    predicted = np.asarray(model.drift)+(states-model.x0)@np.asarray(model.A).T+(controls-model.u0)@np.asarray(model.B).T
    scale = np.asarray(model.state_scales)
    residual = np.linalg.norm((actual-predicted)/scale, axis=1)
    denominator = np.maximum(1., np.maximum(np.linalg.norm(actual/scale, axis=1), np.linalg.norm(predicted/scale, axis=1)))
    return dict(relative_residual=(residual/denominator).tolist(), max_relative_residual=float(max(residual/denominator)),
        max_scaled_state_excursion=float(np.max(abs(states-model.x0)/scale)),
        scope='Pointwise continuous vector fields at affine states; not integrated trajectories')


def run(frozen, output, saved_points=None):
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    budget = dict(model_builds=0, linearizations=0, slsqp_attempts=0, least_squares_attempts=0,
        conic_solves=0, provider_calls=0, mujoco_steps=0, nmpc_updates=0, ppo_training=0, matlab=0, formal_studies=0)
    p = TaskAnalysisProtocol.model_validate(frozen['protocol'])
    import scipy.optimize as opt
    import cvxpy as cp
    originals = (opt.minimize, opt.least_squares, cp.Problem.solve)
    attempts = []

    def optimizer_call(which, *args, **kwargs):
        key = ('slsqp_attempts', 'least_squares_attempts')[which]
        budget[key] += 1
        t = time.perf_counter(); solved = originals[which](*args, **kwargs)
        attempts.append(dict(kind=key, success=bool(solved.success), status=int(solved.status),
            message=str(solved.message), x=solved.x.tolist(), nfev=int(solved.nfev),
            elapsed_s=time.perf_counter()-t))
        return solved

    def conic_call(problem, *args, **kwargs):
        budget['conic_solves'] += 1
        return originals[2](problem, *args, **kwargs)

    result = dict(version='s141-model-validity-v1', cases={}, comparisons={}, budget=budget,
        versions={v: version(v) for v in ('numpy', 'scipy', 'casadi', 'cvxpy', 'clarabel')})
    if saved_points:
        write(output/'plan.json', dict(source=str(saved_points),
            scope='Postprocess saved failed iterates only; retain all constructor failures',
            geometry_gate_m=p.endpoint_check_atol, equilibrium_claim=False,
            max_new_nonlinear_solves=0, max_conic_solves=2,
            parameter_pair='unchanged baseline/near_shorter', target='unchanged yz_plus'))
    graphs, models, points = {}, {}, {}

    def linear(label, point):
        budget['linearizations'] += 1
        case = frozen['cases'][label]
        return ma.linear_model(case, point, p, case['binding']['configuration'], graphs[label])

    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(opt, 'minimize', lambda *a, **kw: optimizer_call(0, *a, **kw)))
            stack.enter_context(patch.object(opt, 'least_squares', lambda *a, **kw: optimizer_call(1, *a, **kw)))
            stack.enter_context(patch.object(cp.Problem, 'solve', conic_call))
            for label, case in frozen['cases'].items():
                old = EndpointLinearizedModel.model_validate(case['saved_model'])
                budget['model_builds'] += 1
                graph = ma.make_graph_from_input(case['configuration'], dict(x=old.x0, u=old.u0))
                graphs[label] = graph
                if saved_points:
                    saved = read(saved_points/f'{label}-points.json')
                    constructed = saved['points']
                    if label == 'baseline':
                        constructed.append(returned_geometry_point(saved, graph, p.endpoint_check_atol))
                else:
                    constructed = ma._candidate_points(graph[0], graph, p, frozen['plan']['operating_points'])
                points[label] = {v['name']: v for v in constructed}
                write(output/f'{label}-points.json', dict(points=constructed, optimizer_returns=attempts[-2:]))
                initial = linear(label, points[label]['controller_start_input'])
                models[label] = initial
                states = np.asarray(case['saved_states'])[1:]+np.asarray(old.x0)
                controls = np.asarray(case['saved_controls'])
                row = dict(points=constructed, saved_witness_geometry=geometry_errors(graph[3], old, states, controls),
                    straight_jacobian_singular_values=np.linalg.svd(np.asarray(initial.C)[:, :12], compute_uv=False).tolist(),
                    current_vs_saved_linearization=dict(A_max_abs=float(np.max(abs(np.asarray(initial.A)-old.A))),
                        B_max_abs=float(np.max(abs(np.asarray(initial.B)-old.B)))), local={})
                for point in constructed:
                    if point['name'] == 'controller_start_input' or not legal_point(point, old.binding['tension_limits_n']):
                        continue
                    m = linear(label, point)
                    x, u = np.asarray(m.x0), np.asarray(m.u0)
                    residual, _ = graph[2].equilibrium_terms(x[:12], u)
                    # Zero velocities: purely geometric probes along the saved terminal bend direction.
                    direction = np.r_[states[-1, :12]-x[:12], np.zeros(12)]
                    xs = np.array([x+alpha*direction for alpha in frozen['plan']['displacement_fractions']])
                    us = np.tile(u, (len(xs), 1))
                    row['local'][point['name']] = dict(model=plain(m),
                        static_residual_inf=float(np.max(abs(residual))),
                        acceleration_inf=float(np.max(abs(graph[2].evaluate(x, u)['qdd']))),
                        jacobian_singular_values=np.linalg.svd(np.asarray(m.C)[:, :12], compute_uv=False).tolist(),
                        displacement_fractions=frozen['plan']['displacement_fractions'], probe_states=xs.tolist(),
                        bent=geometry_errors(graph[3], m, xs, us), straight=geometry_errors(graph[3], initial, xs, us),
                        derivative_check=ma.derivative_check(m, graph, p),
                        full_saved_witness=geometry_errors(graph[3], m, states, controls),
                        local_dynamics=dynamics_errors(graph, m, xs, us))
                result['cases'][label] = row
                print(json.dumps(dict(structure=label, points={k:v['available'] for k,v in points[label].items()})), flush=True)

            available = [name for name in ('target_equilibrium', 'halfway_waypoint', 'returned_ik_geometry')
                if legal_point(points['baseline'].get(name, {}), models['baseline'].binding['tension_limits_n'])]
            if available:
                anchor = deepcopy(points['baseline'][available[0]])
                # This is a Taylor expansion center, never an assumed reached initial state.
                anchor.update(actual_time_s=0., time_origin='Original task initializer retained via initial_delta; anchor is not an observed trajectory state')
                shared = {}
                for label, graph in graphs.items():
                    center = deepcopy(anchor)
                    center['construction'] = dict(method='Shared baseline returned-IK coordinates for matched-structure Taylor comparison',
                        source_point=available[0], source_constructor_available=points['baseline']['halfway_waypoint']['available'],
                        static_equilibrium=False, candidate_halfway_solution_claim=False,
                        achieved_world_point_m=np.asarray(graph[3](center['x'], center['u'])[0]).ravel().tolist())
                    shared[label] = linear(label, center)
                xs = np.asarray(result['cases']['baseline']['local'][available[0]]['probe_states'])
                us = np.tile(anchor['u'], (len(xs), 1))
                pred = {label: geometry_errors(graphs[label][3], m, xs, us) for label,m in shared.items()}
                straight = {label: geometry_errors(graphs[label][3], models[label], xs, us) for label in shared}
                exact_delta = np.array(pred['near_shorter']['exact_world_m'])-pred['baseline']['exact_world_m']
                bent_delta = np.array(pred['near_shorter']['affine_world_m'])-pred['baseline']['affine_world_m']
                straight_delta = np.array(straight['near_shorter']['affine_world_m'])-straight['baseline']['affine_world_m']
                result['comparisons']['fixed_state_parameter_effect'] = dict(anchor=available[0],
                    exact_delta_m=exact_delta.tolist(), bent_delta_m=bent_delta.tolist(), straight_delta_m=straight_delta.tolist(),
                    exact_signal_m=np.linalg.norm(exact_delta, axis=1).tolist(),
                    bent_error_m=np.linalg.norm(bent_delta-exact_delta, axis=1).tolist(),
                    straight_error_m=np.linalg.norm(straight_delta-exact_delta, axis=1).tolist(),
                    scope='Fixed matched curvature/rate and legal input; conditional geometric effect, not optimized structural merit or design derivative')
                from extensions.math_analysis.conic_capability import conic_capability
                from schemas.platform_analysis import TaskAnalysisRequirement
                for label, model in shared.items():
                    case = frozen['cases'][label]
                    initial_delta = np.asarray(models[label].x0)-np.asarray(model.x0)
                    trajectory = conic_capability(model, TaskAnalysisRequirement.model_validate(case['task_analysis']), p,
                        initial_delta=initial_delta)
                    write(output/f'{label}-bent-conic.json', dict(model=plain(model), trajectory=trajectory))
                    result['cases'][label]['bent_reoptimized'] = dict(solver=trajectory.get('solver'),
                        optimality_status=trajectory.get('optimality_status'), status=trajectory['status'],
                        score=trajectory.get('replayed_violation'), initial_delta=initial_delta.tolist(),
                        scope='Full original task in frozen bent affine model; validity checked separately, no nonlinear rollout')
                    if trajectory.get('replay', {}).get('numerically_valid'):
                        states = np.asarray(trajectory['replay']['states'])[1:]+model.x0
                        controls = np.asarray(trajectory['applied_input_n'])
                        check = geometry_errors(graphs[label][3], model, states, controls)
                        result['cases'][label]['bent_reoptimized']['geometry'] = check
                        result['cases'][label]['bent_reoptimized']['dynamics'] = dynamics_errors(graphs[label], model, states, controls)
                        # Confirm the shared sampled-map API preserves the physical initial condition and drift.
                        _, maps = sampled_maps(model, len(controls), p.period_s, initial_delta)
                        mapped = maps[-1][0]+maps[-1][1]@(controls-model.u0).ravel()
                        result['cases'][label]['bent_reoptimized']['sampled_map_terminal_error'] = float(np.max(abs(mapped+model.x0-states[-1])))
            else:
                result['comparisons']['unavailable'] = 'Neither existing baseline bent construction succeeded; no substitute or recovery attempted.'
    finally:
        result.update(optimizer_returns=attempts, elapsed_s=time.perf_counter()-started)
        write(output/'result.json', result)
    return result


def export_evidence(frozen, construction_dir, local_dir, destination):
    """Export already computed results only; no model build or solver calls."""
    construction, local = read(construction_dir/'result.json'), read(local_dir/'result.json')
    write(destination/'construction.json', construction)
    write(destination/'diagnostic.json', local)
    for label in frozen['cases']:
        raw = read(local_dir/f'{label}-bent-conic.json')
        # Correct shared-center annotation only. Original run files remain intact;
        # model matrices, states, controls, residuals and solver statuses are unchanged.
        raw['model']['operating_point']['construction'] = dict(
            method='Shared baseline returned-IK coordinates for matched-structure Taylor comparison',
            source_point='returned_ik_geometry', source_constructor_available=False,
            static_equilibrium=False, candidate_halfway_solution_claim=False,
            achieved_world_point_m=raw['model']['y0'])
        raw['metadata_correction'] = 'Original raw construction annotation inherited baseline halfway metadata; this center is shared, not a newly solved candidate waypoint. No numerical fields changed.'
        write(destination/f'{label}-bent-conic.json', raw)
    write(destination/'resources.json', dict(
        budget={k: construction['budget'][k]+local['budget'][k] for k in construction['budget']},
        compute_elapsed_s=construction['elapsed_s']+local['elapsed_s'],
        stages=dict(construction_s=construction['elapsed_s'], saved_iterate_diagnostic_s=local['elapsed_s']),
        observed_process_exits=dict(construction=1, saved_iterate_diagnostic=0, focused_tests=0,
            note='Construction wrote complete result.json; final process poll returned 1 without additional error text. Cause unresolved; no rerun to conceal this exit.'),
        engineering_preflight='One bounds-path KeyError corrected before any model build or solve; no scientific attempt lost',
        execution='Offline GVS only; no simulator trajectory, provider request, NMPC, RL or Study',
        stop='Prescreening finished; B1 paused; next research is an independent mainline Agent Cold-start Study'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--s140', type=Path)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--saved-points', type=Path, help='Postprocess saved returns; no repeated nonlinear solves')
    parser.add_argument('--export', type=Path, help='Export existing output and saved-points results only')
    args = parser.parse_args()
    if args.s140:
        write(args.input, archive_input(args.s140))
    if args.export:
        export_evidence(read(args.input), args.saved_points, args.output, args.export)
    else:
        run(read(args.input), args.output, args.saved_points)
