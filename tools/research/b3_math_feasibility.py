"""B3 B-line experiments using existing numerical kernels and frozen acceptance.

Run prepare, optimize, then replay as separate processes. Only prepare reads the
archived passing control; optimize reads the archived FAILED NMPC input only.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import importlib.metadata
from pathlib import Path
import subprocess
import sys
import time

from tools.platform_store import plain
from tools.state_io import atomic_json, digest, read

ROOT = Path(__file__).resolve().parents[2]
HISTORY = 'evidence/b3_r1_history_assisted_050'
CANDIDATE = 'e85fc8e3eb57e05bfef71db74885db619ce316f90cb9e9b88dc3e971e01f7543'
FAILED = 'e3a06aa1b8d89ec98216cf6d86edfe264c22f8f725b453ded02e1ed0cfaa4a48'
ARCHIVED_PASS = 'b34d0feb1a38617f8b7dadd8c7aea92c08940042124786de359ccc0d5c8f2115'


def ref(identity):
    return dict(artifact_id=identity, media_type='application/json')


def runtime():
    return dict(code_sha=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        driver_identity=digest(Path(__file__).read_text(encoding='utf8')),
        utc=datetime.now(timezone.utc).isoformat(), python=sys.executable, python_version=sys.version,
        packages={k: importlib.metadata.version(k) for k in ('mujoco', 'numpy', 'scipy', 'casadi', 'pydantic')},
        research_llm_calls=0, seed=17)


def replay(configuration, schedule, folder, label):
    from extensions.tendon_family.backends import playback_tensions
    from tools.research.physical_replay import binding, evaluate_playback
    from tools.research_tasks import assemble_acceptance
    folder.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    inp, physics, scene = binding(configuration, schedule['trajectory'])
    raw = playback_tensions(inp, physics, scene, schedule['trajectory']['tensions_n'], folder)
    atomic_json(folder/'raw.json', raw)
    raw_ref = ref(digest(raw))
    evaluation, profile = evaluate_playback(configuration, raw, raw_ref, digest(schedule['trajectory']))
    evaluation_ref = ref(digest(plain(evaluation)))
    profile.update(execution_id=label, simulation=raw_ref, evaluation=evaluation_ref)
    acceptance = assemble_acceptance(configuration, evaluation, profile,
        evaluation_reference=evaluation_ref, motion=[dict(time_s=r['time_s']) for r in raw['samples']])
    atomic_json(folder/'evaluation.json', plain(evaluation))
    atomic_json(folder/'profile.json', profile)
    atomic_json(folder/'acceptance.json', acceptance)
    result = dict(label=label, runtime=runtime(), acceptance=acceptance,
        configuration_identity=digest(configuration), trajectory_identity=digest(schedule['trajectory']),
        raw_reference=raw_ref, evaluation_reference=evaluation_ref,
        cost=dict(wall_s=time.perf_counter()-started, model_builds=1, full_rollouts=1,
            physics_steps=raw['physics_steps'], physical_evaluations=1, nmpc_updates=0, ppo_steps=0))
    atomic_json(folder/'result.json', result)
    print(label, acceptance['status'], acceptance['metrics'], flush=True)
    return result


def prepare(output):
    from tools.research.numerics import archived
    from tools.research.physical_replay import binding
    output.mkdir(parents=True, exist_ok=True)
    if (output/'preparation.json').exists():
        raise ValueError('Use a new output directory to preserve completed experiments.')
    started = time.perf_counter()
    candidate = archived(HISTORY, ref(CANDIDATE))
    failed = archived(HISTORY, ref(FAILED))
    passing = archived(HISTORY, ref(ARCHIVED_PASS))
    configuration = candidate['configuration']
    package = read(ROOT/HISTORY/'design_package.json')
    assert configuration == package['configuration']
    initial = configuration['task']['initializer']['parameters']['data']
    assert initial == candidate['initialization_provenance']['effective']
    assert all(v == 0. for key in ('qpos_rad', 'qvel_rad_s') for v in initial[key].values())
    canonical = deepcopy(configuration['task'])
    canonical['initializer']['parameters']['data'] = dict(rule=candidate['initialization_provenance']['rule'])
    assert canonical == package['canonical_task']
    binding(configuration, failed['trajectory'])
    frozen = read(ROOT/HISTORY/'configuration.json')
    atomic_json(output/'configuration.json', configuration)
    atomic_json(output/'design_parameters.json', candidate['parameters'])
    atomic_json(output/'canonical_task.json', canonical)
    atomic_json(output/'analysis_protocol.json', frozen['analysis_protocol'])
    atomic_json(output/'failed_nmpc_schedule.json', failed)
    atomic_json(output/'archived_schedule.json', passing)
    positive = replay(configuration, passing, output/'archived_solution_replay', 'archived_solution_replay')
    baseline = replay(configuration, failed, output/'failed_nmpc_replay', 'failed_nmpc_replay')
    assert positive['acceptance']['accepted'] is True
    assert baseline['acceptance']['accepted'] is False
    for key, value in package['acceptance']['metrics'].items():
        assert abs(positive['acceptance']['metrics'][key]-value) < 1e-12
    result = dict(runtime=runtime(), base_sha='c153e1731ae0925e756467f75a783b28abce2873',
        candidate=ref(CANDIDATE), failed_source=ref(FAILED), archived_positive_source=ref(ARCHIVED_PASS),
        task_identity=digest(configuration['task']), canonical_task_identity=digest(canonical),
        configuration_identity=digest(configuration),
        archived_solution_replay=positive['acceptance']['metrics'], failed_start=baseline['acceptance']['metrics'],
        preparation_wall_s=time.perf_counter()-started,
        tools=dict(mujoco='executed full replay', native_control='available; next experiment',
            gvs='installed existing implementation; not executed', nmpc='CasADi installed; archived inputs reused; no fresh NLP',
            ppo='not needed; torch/SB3 absent in selected numerical environment'),
        next_experiment='Late piecewise-linear tension correction; all coefficients start at zero; same structure.')
    atomic_json(output/'preparation.json', result)


def optimize(output, name):
    from tools.research.contracts import AnalysisRequest
    from tools.research.native_control import calculate
    from tools.research.numerics import native_point
    from tools.research_tasks import task_adapter
    folder = output/name
    folder.mkdir(parents=True, exist_ok=False)
    configuration = read(output/'configuration.json')
    source = read(output/'failed_nmpc_schedule.json')
    # Independent zero-offset restart: never read archived_schedule or old native states.
    settings = dict(version='local_control_search_v2', method='response',
        correction_window_s=[0., .5], knots_s=[0., .30, .41, .50],
        active_coefficients=list(range(8, 16)), coefficient_limit_n=2., difference_step_n=.04,
        initial_radius_n=.15, minimum_radius_n=.0001, iterations=4, evaluation_requests=60,
        safety_margin_fraction=0.)
    query = AnalysisRequest.model_validate(dict(candidate=ref(CANDIDATE),
        operation='mujoco_direct_control_v1', model_source='mujoco',
        operating_point='standardized_initial_pretension', protocol=read(output/'analysis_protocol.json'),
        control_optimization=dict(source=ref(FAILED), settings=settings)))
    binding = dict(candidate=ref(CANDIDATE), effective_configuration_identity=digest(configuration))
    point = native_point(None, query, configuration)
    requirements = task_adapter(configuration).analysis_requirements(binding)
    atomic_json(folder/'request.json', dict(runtime=runtime(), query=plain(query),
        source_identity=digest(source), initial_coefficients_n=[0.]*16, initial_state=point,
        reason='Position passes; reduce the maximum of all six holding speeds through late braking inputs.',
        expected_cost='At most 60 complete 1000-step native rollouts; stop at first feasible prediction.'))
    started = time.perf_counter()
    result = calculate(configuration, binding, query, point, requirements,
        dict(schedule=source, source=ref(FAILED)),
        checkpoint=lambda label, value: atomic_json(folder/(label+'.json'), value))
    result['experiment_wall_s'] = time.perf_counter()-started
    atomic_json(folder/'optimization.json', result)
    schedule = deepcopy(result['native_dynamics']['optimized_schedule'])
    schedule['provenance'].update(experiment=name, source_branch='research/b3-math-tool-feasibility',
        fresh_numeric_execution=True, initial_coefficients_n=[0.]*16)
    atomic_json(folder/'schedule.json', schedule)
    best = result['native_dynamics']['optimization']['best']
    print(name, result['native_analysis']['comparison'], result['cost'], flush=True)
    print('stop', result['native_dynamics']['optimization']['stop_reason'], flush=True)
    validated = replay(configuration, schedule, folder/'independent_replay', name)
    predicted = best['measure']
    for official, proxy in [('terminal_error_m', 'terminal_position_error_m'),
            ('holding_max_error_m', 'holding_max_position_error_m'), ('holding_max_speed_m_s', 'holding_max_speed_m_s')]:
        assert abs(validated['acceptance']['metrics'][official]-predicted[proxy]) < 1e-12


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare', 'optimize', 'replay'])
    parser.add_argument('--output', type=Path, default=ROOT/'evidence/b3_math_tool_feasibility')
    parser.add_argument('--name', default='search_01')
    args = parser.parse_args()
    if args.stage == 'prepare':
        prepare(args.output)
    elif args.stage == 'optimize':
        optimize(args.output, args.name)
    else:
        replay(read(args.output/'configuration.json'), read(args.output/'search_01/schedule.json'),
            args.output/args.name, args.name)


if __name__ == '__main__':
    main()
