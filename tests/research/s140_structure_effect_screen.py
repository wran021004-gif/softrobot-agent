"""S140 bounded exploratory screening; no Study or physical execution.

Run from the repository with python -m tests.research.s140_structure_effect_screen
--output runs/s140_structure_effect. Existing output directories are preserved.
Reuses S138 generation, calculate/CONIC, fixed-control replay and evaluator.
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

from tests.research.s138_structure_precheck import (
    ROOT, SOURCE, calculate, resolved_configuration, source_lengths,
    resolve_basis, digest, plain, evaluate_prediction, task_capability,
    EndpointLinearizedModel, TaskAnalysisProtocol, TaskAnalysisRequirement, CONIC,
)
from tools.research.design import parameter_value


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def configuration(source, parameters, target, label):
    base = deepcopy(source)
    base['task']['task_id'] += '-s140-' + label
    base['task']['goal']['data']['target_m'] = list(target)
    cfg = resolved_configuration(source, base, parameters, 's140-offline-' + label)
    ref = dict(artifact_id=digest(cfg), media_type='application/json')
    design = cfg['robot']['structure']['data']
    basis = cfg['policy']['controller']['parameters']['data']['recipe']['basis']
    binding = dict(candidate_id=digest(dict(configuration=cfg, parameters=parameters)),
        configuration=ref, candidate=ref, source_identity=digest(source),
        effective_configuration_identity=digest(cfg), task_identity=digest(cfg['task']),
        basis=basis, coordinate_order=list(resolve_basis(design, basis).coordinate_order),
        tendon_order=[t['id'] for t in design['tendons']],
        tension_limits_n=[t['force_limit_n'] for t in design['tendons']])
    return cfg, binding


def locality(model, graph, trajectory, tolerance):
    """Evaluate nonlinear outputs/dynamics AT affine states, never integrate them."""
    if not trajectory.get('replay', {}).get('numerically_valid'):
        return dict(geometry_screen_pass=False, reason='No finite affine witness')
    dx = np.asarray(trajectory['replay']['states'])[1:]
    inputs = np.asarray(trajectory['applied_input_n'])
    x0, u0 = np.asarray(model.x0), np.asarray(model.u0)
    output = next(o for o in model.endpoint_outputs if o.name == 'tip_position')
    affine = np.asarray(output.value0) + dx @ np.asarray(output.C).T + (inputs-u0) @ np.asarray(output.D).T
    h, f = graph[3], graph[2]
    nonlinear = np.asarray([np.asarray(h(x0+x, u)[0]).ravel() for x, u in zip(dx, inputs)])
    errors = np.linalg.norm(nonlinear-affine, axis=1)
    # All six holding samples, including 0.30 s, match inherited task adapter.
    holding = errors[-6:]
    residuals = []
    for k in (4, 9, 14, 19, 24, 29, 34):
        actual = f.evaluate(x0+dx[k], inputs[k])['xdot'].ravel()
        linear = np.asarray(model.drift) + np.asarray(model.A) @ dx[k] + np.asarray(model.B) @ (inputs[k]-u0)
        scale = np.asarray(model.state_scales)
        residuals.append(dict(sample_index=k+1,
            scaled_residual_norm=float(np.linalg.norm((actual-linear)/scale)),
            relative_residual=float(np.linalg.norm((actual-linear)/scale) /
                max(np.linalg.norm(actual/scale), np.linalg.norm(linear/scale), 1.))))
    return dict(geometry_screen_pass=bool(max(errors) <= tolerance and max(holding) <= tolerance/2),
        max_position_linearization_error_m=float(max(errors)),
        holding_max_position_linearization_error_m=float(max(holding)),
        terminal_nonlinear_geometry_m=nonlinear[-1].tolist(),
        max_scaled_state_excursion=float(np.max(abs(dx)/np.asarray(model.state_scales))),
        sampled_dynamics_residuals=residuals,
        max_relative_dynamics_residual=max(r['relative_residual'] for r in residuals),
        validated_locality_radius=None,
        scope='Nonlinear GVS outputs/dynamics evaluated at affine states; no nonlinear trajectory, feasibility or error bound')


def summarize(cfg, model, trajectory, graph, tolerance):
    evaluated = evaluate_prediction(cfg, model, trajectory)
    replay = trajectory.get('replay', {})
    controls = np.asarray(trajectory.get('applied_input_n', []))
    dual = trajectory.get('dual_checks', {})
    diagnostics = {}
    if controls.size:
        limits = np.asarray(model.binding['tension_limits_n'])
        diagnostics = dict(min_n=float(controls.min()), max_n=float(controls.max()),
            minimum_box_margin_n=float(min(controls.min(), (limits-controls).min())),
            rms_n=float(np.sqrt(np.mean(controls**2))),
            squared_tension_integral_n2_s=float(np.sum(controls**2)*cfg['task']['timing']['control_period_s']),
            mean_per_tendon_n=np.mean(controls, axis=0).tolist(),
            note='Descriptive witness costs only: minimax has no energy/margin tie-break, so these are not optimized cost comparisons')
    records = replay.get('records', [])
    return dict(signed_violation=replayed_score(trajectory),
        status=trajectory['status'], solver=trajectory.get('solver'),
        optimality_status=trajectory.get('optimality_status', 'not_checked_fixed_control'),
        numerical_feasibility=trajectory.get('numerical_feasibility'),
        all_requested_checked=trajectory.get('all_requested_checked'),
        coverage_counts=trajectory.get('coverage_counts'),
        independent_evaluator=evaluated.get('evaluation'),
        replay=dict(numerically_valid=replay.get('numerically_valid'), passed=replay.get('passed'),
            max_prediction_replay_error=replay.get('max_prediction_replay_error'),
            max_absolute_violation=replay.get('max_absolute_violation'),
            constraints={name:dict(max_value=max(r['value'] for r in records if r['constraint_id']==name),
                max_signed_violation=max(r['signed_violation'] for r in records if r['constraint_id']==name))
                for name in sorted({r['constraint_id'] for r in records})}),
        primal_checks=trajectory.get('primal_checks'),
        dual_checks={k:dual.get(k) for k in ('stationarity_inf','epigraph_stationarity_abs',
            'dual_cone_violation','complementarity_abs','raw_duality_gap','support_lower_estimate','replayed_support_gap')},
        kernel_elapsed_s=trajectory.get('kernel_elapsed_s'), tensions=diagnostics,
        locality=locality(model, graph, trajectory, tolerance))


def replayed_score(trajectory):
    # S138 fixed-control and CONIC expose the verified score at different paths.
    if not trajectory.get('replay', {}).get('numerically_valid'):
        return None
    return max(r['signed_violation'] for r in trajectory['replay']['records'])


def candidate_targets(model, graph):
    """Six fixed directions; bounded static support guides radius, geometry supplies X."""
    C = np.asarray(model.C)
    n = len(model.x0)//2
    J = C[:, :n]
    A, B, drift = map(np.asarray, (model.A, model.B, model.drift))
    steady = -np.linalg.solve(A, B)
    offset = -np.linalg.solve(A, drift)
    lower, upper = -np.asarray(model.u0), np.asarray(model.binding['tension_limits_n'])-model.u0
    rows = []
    for label, yz in [('y_plus',(1,0)),('y_minus',(-1,0)),('z_plus',(0,1)),
                      ('z_minus',(0,-1)),('yz_plus',(1,1)),('minus_y_plus_z',(-1,1))]:
        direction = np.r_[0., yz] / np.linalg.norm(yz)
        gain = direction @ C @ steady
        support = float(direction @ C @ offset + np.maximum(gain*lower, gain*upper).sum())
        # A support projection is an optimistic bound, NOT a radial feasible point.
        radius = float(np.clip(.8*max(0., support), .035, .060))
        q = np.linalg.pinv(J) @ (radius*direction)
        x = np.asarray(model.x0) + np.r_[q, np.zeros(n)]
        target = np.asarray(graph[3](x, model.u0)[0]).ravel()
        rows.append(dict(id=label, direction=direction.tolist(), requested_lateral_m=radius,
            target_m=target.tolist(), geometric_seed_q_rad_m=q.tolist(),
            static_direction_support_m=support,
            geometric_shortening_m=float(model.y0[0]-target[0]),
            reason='Known nonlinear GVS kinematic point in a fixed Y/Z direction; 80% linear static box support capped at 60 mm; no static/dynamic feasibility claim'))
    return rows, dict(initial_world_tip_m=model.y0,
        position_jacobian_singular_values=np.linalg.svd(J, compute_uv=False).tolist(),
        axial_jacobian_norm=float(np.linalg.norm(J[0])),
        static_state_matrix_condition=float(np.linalg.cond(A)))


def select_targets(rows):
    """Geometry first, then difficult baseline score; require differing directions."""
    eligible = [r for r in rows if r['B']['locality']['geometry_screen_pass']
        and r['B']['optimality_status']=='numerically_checked']
    qualified = len(eligible) >= 2
    if not qualified:
        # Diagnostic pair only. Same upward component, opposite Y; do not rank
        # geometrically unqualified cases using meaningless 1e-11 score ties.
        return ['yz_plus', 'minus_y_plus_z'], False
    pool = sorted(eligible, key=lambda r: (-round(r['B']['signed_violation'], 6), r['id']))
    first = pool[0]
    second = next((r for r in pool[1:] if np.dot(first['direction'], r['direction']) <= .5), pool[1])
    return [first['id'], second['id']], qualified


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    saved = json.loads(SOURCE.read_text(encoding='utf8'))
    baseline = saved['baseline']
    candidate = saved['supporting_artifacts'][baseline['candidate']['artifact_id']]
    source, original_parameters = candidate['configuration'], candidate['parameters']
    protocol = baseline['protocol']
    tolerance = source['task']['evaluator']['parameters']['data']['tolerance_m']
    bounds = json.loads((ROOT/'configs/research/study.json').read_text())['allowed_parameters']
    variants = []
    for label, delta, modulus in [('baseline',0.,1.),('near_shorter',-.005,1.),
            ('near_longer',.005,1.),('distal_softer',0.,.9),('distal_stiffer',0.,1.1)]:
        p = deepcopy(original_parameters)
        p['segments']['near']['length_m'] += delta
        p['segments']['distal1']['length_m'] -= delta
        p['segments']['distal1']['young_pa'] *= modulus
        for name, (lo, hi) in bounds.items():
            assert lo <= parameter_value(p, name) <= hi, name
        assert abs(sum(v['length_m'] for v in p['segments'].values())-.27) < 1e-12
        variants.append(dict(id=label, parameters=p))
    budget = dict(model_builds=0, linearizations=0, internal_conic_solves=0,
        fixed_control_replays=0, provider_calls=0, mujoco_steps=0, ppo_training=0,
        matlab_nmpc=0, formal_studies=0)
    plan = dict(scope='exploratory screening only', source_commit='fc509271b',
        source_path=SOURCE.relative_to(ROOT).as_posix(),
        source_control_pointer='/baseline/trajectory/applied_input_n',
        control_meaning='S129 saved mathematical witness inherited by S138; not NMPC execution',
        protocol=protocol, structures=variants, bounds_source='configs/research/study.json@fc509271b',
        target_rule='Six fixed Y/Z and oblique directions; exact nonlinear geometry of minimum-norm initial-Jacobian bend; radius clip(0.8*static_direction_support,35,60) mm',
        selection_rule='Before C: retain numerically checked B with max geometry error <=10 mm and holding error <=5 mm; rank descending B violation rounded to 1e-6, then ID; choose second direction with dot<=0.5. If fewer than two survive, use the two opposite-Y upward diagonals only for diagnostic A/B/C and do not freeze formal tasks.',
        primary_metric='Inherited signed minimax violation plus independent Reach evaluator; numerical differences <=1e-6 ignored',
        secondary_metric='Witness tension RMS/integral/margins descriptive only, not minimum-energy claims',
        limits=dict(model_builds=24, internal_conic_solves=30),
        task_acceptance='unmeasured', locality_validated_radius=None)
    write(output/'plan.json', plan)
    # Count actual boundaries, including unsuccessful calls, not status strings.
    import cvxpy as cp
    from extensions.tendon_family import math_analysis as math_model
    real_graph, real_linear, real_solve = math_model.make_graph_from_input, math_model.linear_model, cp.Problem.solve
    current_graph = None

    def graph_call(*args, **kwargs):
        nonlocal current_graph
        if budget['model_builds'] >= 24:
            raise RuntimeError('S140 model budget exhausted')
        budget['model_builds'] += 1
        current_graph = real_graph(*args, **kwargs)
        return current_graph

    def linear_call(*args, **kwargs):
        budget['linearizations'] += 1
        return real_linear(*args, **kwargs)

    def solve_call(problem, *args, **kwargs):
        if budget['internal_conic_solves'] >= 30:
            raise RuntimeError('S140 conic budget exhausted')
        budget['internal_conic_solves'] += 1
        return real_solve(problem, *args, **kwargs)

    def compute(parameters, target, label, seed=False):
        cfg, binding = configuration(source, parameters, target, label)
        query = dict(candidate=binding['configuration'], operation='linearization' if seed else 'task_capability',
            operating_point='controller_start_input', protocol=protocol)
        if seed:
            query['scoring_window_s'] = .35
        else:
            query['capability_method'] = CONIC
        raw = calculate(cfg, binding, query)
        model = EndpointLinearizedModel.model_validate(raw['model'])
        return cfg, raw, model, current_graph

    rows, cases = [], []
    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(math_model, 'make_graph_from_input', graph_call))
            stack.enter_context(patch.object(math_model, 'linear_model', linear_call))
            stack.enter_context(patch.object(cp.Problem, 'solve', solve_call))
            cfg, raw, model, graph = compute(original_parameters, source['task']['goal']['data']['target_m'], 'geometry-seed', seed=True)
            candidates, geometry = candidate_targets(model, graph)
            write(output/'candidates-before-solves.json', dict(candidates=candidates, geometry=geometry))
            write(output/'geometry-seed.json', dict(configuration=cfg, mathematics=raw))
            for item in candidates:
                cfg, raw, model, graph = compute(original_parameters, item['target_m'], item['id'])
                row = dict(item, B=summarize(cfg, model, raw['trajectory'], graph, tolerance))
                # Keep all A controls/replays too, so no additional build is needed after selection.
                fixed = task_capability(model, TaskAnalysisRequirement.model_validate(raw['task_analysis']),
                    TaskAnalysisProtocol.model_validate(protocol), applied_input_n=baseline['trajectory']['applied_input_n'])
                budget['fixed_control_replays'] += 1
                row['A'] = summarize(cfg, model, fixed, graph, tolerance)
                write(output/(item['id']+'.json'), dict(configuration=cfg, mathematics=raw, original_control_replay=fixed))
                rows.append(row)
                print(json.dumps(dict(stage='screen', target=item['id'], B=row['B']['signed_violation'], locality=row['B']['locality']['geometry_screen_pass'])), flush=True)
            selected, qualified = select_targets(rows)
            write(output/'selection-before-C.json', dict(selected=selected, geometry_qualified_pair=qualified,
                rule=plan['selection_rule'], frozen_for='S140 structure comparisons only; no future Agent or formal Study started'))
            for row in rows:
                row['selected'] = row['id'] in selected
                row['selection_reason'] = (('Qualified selection before structure results' if qualified else
                    'Unqualified diagnostic diagonal; not a recommended formal target') if row['selected'] else
                    'Excluded by geometry screen' if not row['B']['locality']['geometry_screen_pass'] else
                    'Lower baseline difficulty or redundant direction under fixed pair rule')
            for variant in variants[1:]:
                for name in selected:
                    target = next(r for r in rows if r['id']==name)
                    cfg, raw, model, graph = compute(variant['parameters'], target['target_m'], variant['id']+'-'+name)
                    score = summarize(cfg, model, raw['trajectory'], graph, tolerance)
                    b = target['B']
                    cases.append(dict(structure=variant['id'], target=name, C=score,
                        C_minus_B=score['signed_violation']-b['signed_violation']))
                    write(output/(variant['id']+'-'+name+'.json'), dict(configuration=cfg, mathematics=raw))
                    print(json.dumps(dict(stage='structure', structure=variant['id'], target=name,
                        C=score['signed_violation'], C_minus_B=cases[-1]['C_minus_B'])), flush=True)
            summary = dict(plan=plan, geometry=geometry, candidates=rows, selected_targets=selected,
                geometry_qualified_pair=qualified, comparisons=cases, budgets=budget,
                elapsed_s=time.perf_counter()-started,
                versions={name:version(name) for name in ('numpy','scipy','casadi','cvxpy','clarabel')},
                detailed_artifacts='runs/s140_structure_effect/*.json (ignored; regenerate with the recorded command)',
                reproduction='python -m tests.research.s140_structure_effect_screen --output runs/s140_structure_effect',
                physical_task_acceptance='unmeasured',
                limitations=['Single initial affine model; no nonlinear integration or physical execution',
                    'Geometry/dynamics residual samples are diagnostics, not validated error bounds',
                    'No minimum-energy tie-break; different feasible control costs do not prove optimal cost gains',
                    'Exploratory selected targets are not independent validation; hide reference comparison outcomes from future study agents'])
            write(output/'summary.json', summary)
            return summary
    finally:
        write(output/'actual-budget.json', dict(budgets=budget, elapsed_s=time.perf_counter()-started))


def export_summary(output, destination):
    """Compact saved results without rebuilding models or resolving controls."""
    result = json.loads((output/'summary.json').read_text(encoding='utf8'))
    rows = result['candidates']
    for row in rows:
        raw = json.loads((output/(row['id']+'.json')).read_text(encoding='utf8'))
        row['A']['signed_violation'] = replayed_score(raw['original_control_replay'])
    assert select_targets(rows)[0] == result['selected_targets']

    def compact(score):
        evaluation = score['independent_evaluator']
        local = score['locality']
        return dict(signed_violation=score['signed_violation'], status=score['status'],
            evaluator_pass=evaluation['task_success'],
            evaluator_position_error_m=evaluation['metrics'][0]['value'],
            all_requested_checked=score['all_requested_checked'],
            constraints=score['replay']['constraints'],
            replay_valid=score['replay']['numerically_valid'],
            prediction_replay_error=score['replay']['max_prediction_replay_error'],
            solver_status=(score['solver'] or {}).get('status', 'fixed_control'),
            solver_iterations=(score['solver'] or {}).get('iterations'),
            solver_wall_s=(score['solver'] or {}).get('wall_s'),
            optimality_status=score['optimality_status'],
            support_gap=score['dual_checks']['replayed_support_gap'],
            primal_checks=score['primal_checks'],
            tension_rms_n=score['tensions']['rms_n'],
            tension_minimum_box_margin_n=score['tensions']['minimum_box_margin_n'],
            tension_min_max_n=[score['tensions']['min_n'], score['tensions']['max_n']],
            tension_integral_n2_s=score['tensions']['squared_tension_integral_n2_s'],
            locality={k:local[k] for k in ('geometry_screen_pass',
                'max_position_linearization_error_m','holding_max_position_linearization_error_m',
                'max_scaled_state_excursion','max_relative_dynamics_residual')})

    p = result['plan']
    evidence = dict(version='s140-structure-prescreen-v1', scope=p['scope'],
        source=dict(commit=p['source_commit'], path=p['source_path'],
            configuration_pointer='/supporting_artifacts[/baseline/candidate/artifact_id]/configuration',
            parameters_pointer='/supporting_artifacts[/baseline/candidate/artifact_id]/parameters',
            control_pointer=p['source_control_pointer'], control_meaning=p['control_meaning']),
        protocol=p['protocol'], geometry=result['geometry'], target_rule=p['target_rule'],
        original_selection_rule=p['selection_rule'],
        selection_audit=('Original run ranked raw B scores; all six failed geometry and were tied within 1e-6. The selected opposite-Y upward diagonals are diagnostic only. Final script uses this fixed diagnostic fallback and rounds qualified ranking to 1e-6; same pair, no extra solves.'
            if 'rounded to 1e-6' not in p['selection_rule'] else
            'Uses rounded qualified ranking and fixed unqualified diagnostic fallback.'),
        selected_targets=result['selected_targets'], formal_targets_frozen=False,
        geometry_qualified_pair=result['geometry_qualified_pair'],
        structures=[dict(id=v['id'], lengths_m={k:a['length_m'] for k,a in v['parameters']['segments'].items()},
            young_pa={k:a['young_pa'] for k,a in v['parameters']['segments'].items()}) for v in p['structures']],
        bounds_source=p['bounds_source'], primary_metric=p['primary_metric'], secondary_metric=p['secondary_metric'],
        candidates=[dict(id=r['id'], target_m=r['target_m'], direction=r['direction'],
            requested_lateral_m=r['requested_lateral_m'], static_direction_support_m=r['static_direction_support_m'],
            geometric_seed_q_rad_m=r['geometric_seed_q_rad_m'], geometric_shortening_m=r['geometric_shortening_m'],
            selected=r['selected'], selection_reason='Unqualified diagnostic diagonal' if r['selected'] else
                'Excluded: failed predeclared nonlinear geometry consistency screen',
            A=compact(r['A']), B=compact(r['B'])) for r in rows],
        comparisons=[dict(structure=r['structure'], target=r['target'], C=compact(r['C']),
            C_minus_B=r['C_minus_B']) for r in result['comparisons']],
        budgets=result['budgets'], elapsed_s=result['elapsed_s'], versions=result['versions'],
        conclusion=dict(additional_reach_passes=0, effective_structural_gain_found=False,
            max_abs_C_minus_B=max(abs(r['C_minus_B']) for r in result['comparisons']),
            affine_axial_floor=-1+rows[0]['geometric_shortening_m']/.01,
            physical_task_acceptance='unmeasured', recommended_next_step='Validate local-model agreement before expanding workspace search or pursuing B3 settling'),
        limitations=result['limitations'],
        reproduction=result['reproduction']+' --summary evidence/s140_structure_effect/summary.json',
        export_only='python -m tests.research.s140_structure_effect_screen --output runs/s140_structure_effect --summary evidence/s140_structure_effect/summary.json --summarize-only',
        validation_command='python -m unittest tests.research.test_s140_screen -v')
    write(destination, evidence)
    return evidence


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--summary', type=Path)
    parser.add_argument('--summarize-only', action='store_true')
    args = parser.parse_args()
    if args.summary is not None and args.summary.exists():
        parser.error('Summary exists; preserve previous evidence.')
    if args.summarize_only:
        if args.summary is None:
            parser.error('--summarize-only requires --summary')
        export_summary(args.output, args.summary)
        raise SystemExit(0)
    if args.output.exists():
        parser.error('Output exists; preserve previous results.')
    run(args.output)
    if args.summary is not None:
        export_summary(args.output, args.summary)
