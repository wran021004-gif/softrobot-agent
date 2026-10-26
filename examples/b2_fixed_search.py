"""Bounded B2 fixed-program study; existing generation/search/replay/evaluation.

Default preflight builds models but forbids mj_step. Scientific execution needs
a separately approved, exact-plan-bound budget file. No Provider or Agent calls.
"""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import argparse
import hashlib
import json
import subprocess
import time

import mujoco
import numpy as np

from schemas.platform import SessionInput
from tools.platform_store import plain
from tools.state_io import read, atomic_json, digest
from tools.research.config import resolve
from tools.research.contracts import AnalysisRequest
from tools.research.numerics import native_point
from tools.research.native_analysis import assessment, applicability
from tools.research.native_control import calculate
from tools.research.physical_replay import model_context, binding, evaluate_playback
from tools.research.task_constraints import describe_analysis_requirements
from tools.research_tasks import assemble_acceptance
from extensions.tendon_family.family_space import parse_build
from extensions.tendon_family.generated_serial import generate_family
from extensions.tendon_family.backends import MujocoFailureSnapshot, playback_tensions
from extensions.tendon_family.mujoco_analysis import NativeModel

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'configs/research/b2_fixed_search_v1.json'


def plan():
    value = read(PLAN)
    for name, expected in value['frozen_files'].items():
        # Git may check out CRLF on Windows; preserve text content across OSes.
        if hashlib.sha256((ROOT / name).read_text(encoding='utf8').encode('utf8')).hexdigest() != expected:
            raise ValueError('FROZEN_INPUT_CHANGED: ' + name)
    return value


def configurations(value, radius):
    spec = resolve(ROOT / 'configs/research/study_family_space_dev.json')
    request = dict(family_space_identity=spec['family_space_identity'], segment_count=2,
        tendon_count=4, spans=[dict(last_segment=1, count=4, radius_m=radius)])
    build = parse_build(dict(space=spec['family_space'], request=request))
    robot, mesh, physics = generate_family(build)
    cfg = deepcopy(spec['configuration'])
    cfg['robot']['structure']['data'] = robot
    cfg['policy']['discretization']['data'] = mesh
    cfg['policy']['candidate_builder'] = dict(extension_id='candidate.family', version='5.0.0',
        parameters=dict(contract='family.serial_space_build', version='1.0.0', data=plain(build)))
    rows = []
    for condition, path in value['tasks'].items():
        task = read(ROOT / path)
        current = deepcopy(cfg)
        current.update(task=task['task'], seed=task['seed'])
        current['policy']['controller']['parameters']['data']['settling'] = task['settling']
        current['task']['initializer']['parameters']['data'] = dict(
            qpos_rad={j: 0. for j in physics['dofs']},
            qvel_rad_s={j: 0. for j in physics['dofs']}, unspecified='zero')
        rows.append((condition, plain(SessionInput.model_validate(current))))
    return request, rows


def prepared(cfg, value, initial):
    inp, physics, scene, model = model_context(cfg)
    period = inp.task.timing.control_period_s
    count = round(inp.task.timing.duration_s / period)
    schedule = dict(source_kind='explicit_control_schedule_v1', task_acceptance='unmeasured',
        provenance=dict(control_initialization='constant cold start', tension_n=initial, inherited_acceptance=False),
        trajectory=dict(times_s=[i * period for i in range(count + 1)],
            tensions_n=[[initial] * len(physics['tendons']) for _ in range(count)],
            tendon_order=model['tendon_order'], model_identity=model['identity'],
            design_identity=model['design_identity'], task_identity=digest(plain(inp.task))))
    binding(cfg, schedule['trajectory'])
    candidate = dict(artifact_id=digest(cfg), media_type='application/json')
    source = dict(artifact_id=digest(schedule), media_type='application/json')
    query = AnalysisRequest.model_validate(dict(candidate=candidate, model_source='mujoco',
        operation='mujoco_direct_control_v1', operating_point='standardized_initial_pretension',
        protocol=value['analysis_protocol'], control_optimization=dict(source=source, settings=value['search'])))
    point = native_point(None, query, cfg)
    outer = dict(candidate=candidate, effective_configuration_identity=digest(cfg), task_identity=digest(plain(inp.task)))
    requirements = describe_analysis_requirements(inp, outer)
    fit = applicability(requirements, query, assessment(inp, requirements), point)
    if fit['status'] != 'applicable':
        raise ValueError(json.dumps(fit['reasons']))
    return outer, query, point, requirements, dict(schedule=schedule, source=source)


def preflight(value):
    rows = []
    def forbidden(*args, **kwargs):
        raise AssertionError('PREFLIGHT_MUST_NOT_INTEGRATE')
    with patch.object(mujoco, 'mj_step', forbidden):
        for radius in value['radii_m']:
            request, configs = configurations(value, radius)
            assert configs[0][1]['robot']['structure'] == configs[1][1]['robot']['structure']
            for condition, cfg in configs:
                _, query, point, _, _ = prepared(cfg, value, value['initial_tensions_n'][0])
                native = NativeModel(cfg)
                native.reconstruct(point)
                force = native.scene['forces']
                for t in (0., .1, .30, .35):
                    data = mujoco.MjData(native.model)
                    data.time = t
                    native.forward(data)
                    actual = data.xfrc_applied[native.model.body('payload').id]
                    expected = [0., .02, -.03] if condition == 'force' and .1 <= t < .35 else [0., 0., 0.]
                    np.testing.assert_array_equal(actual, [*expected, 0., 0., 0.])
                rows.append(dict(radius_m=radius, condition=condition, configuration_identity=digest(cfg),
                    design_identity=native.physics['design_identity'], dofs=len(native.order),
                    tendon_order=native.tendons, limits_n=native.limits.tolist(),
                    native_cost=deepcopy(native.cost), forces=force, request=request))
    return dict(status='legal_frozen_spec_feasibility_unmeasured', plan_identity=digest(value),
        rollouts_executed=0, physics_steps=0, provider_requests=0, rows=rows,
        steps_per_rollout=700, neutral_max_steps=85400, feasibility_max_steps=256200,
        contrast_max_steps=512400)


def approved(path, value, mode):
    approval = read(path)
    ceiling = value['budget_proposals'][mode]['physics_step_attempts']
    if (approval.get('approved') is not True or not approval.get('user_approval')
            or 'PENDING' in str(approval['user_approval']).upper()
            or approval.get('experiment') != 'B2-fixed-search-v1'
            or approval.get('mode') != mode or approval.get('plan_identity') != digest(value)
            or type(approval.get('physics_step_attempts')) is not int
            or not 0 < approval['physics_step_attempts'] <= ceiling):
        raise ValueError('SEPARATE_EXACT_PLAN_BOUND_B2_SCIENTIFIC_APPROVAL_REQUIRED')
    implementation = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
    if approval.get('implementation') != implementation:
        raise ValueError('B2_APPROVAL_IMPLEMENTATION_MISMATCH')
    subprocess.run(['git','diff','--quiet','HEAD','--','tools','schemas','extensions',
        'configs','tasks','examples/b2_fixed_search.py'], cwd=ROOT, check=True)
    return approval


def run(value, folder, approval, mode):
    # Record this exact grant once, independent of the selected output directory.
    folder.mkdir(parents=True, exist_ok=False)
    grant = {k:v for k,v in approval.items() if k not in ('_path','witness_directory')}
    used = ROOT / 'runs' / ('b2-budget-' + digest(grant) + '.used')
    used.parent.mkdir(parents=True, exist_ok=True)
    with used.open('x', encoding='utf8') as stream:
        stream.write(str(folder.resolve()))
    cap = approval['physics_step_attempts']
    ledger = dict(physics_step_attempts=0, physics_steps=0, forward_calls=0, phases=[], cap=cap,
        provider_requests=0, mode=mode, plan_identity=digest(value), scientific_wall_s=0.)
    atomic_json(folder / 'inputs.json', dict(plan=value, approval=approval,
        implementation=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
        runtime=dict(mujoco=mujoco.__version__, numpy=np.__version__)))
    summary = dict(status='running', mode=mode, complete_witness=False, results=[])
    original = MujocoFailureSnapshot.call
    def counted(safety, data, operation, location):
        if operation is mujoco.mj_step:
            if ledger['physics_step_attempts'] >= cap:
                raise ValueError('B2_PHYSICS_STEP_ATTEMPT_CAP_EXHAUSTED')
            ledger['physics_step_attempts'] += 1
        result = original(safety, data, operation, location)
        if operation is mujoco.mj_step:
            ledger['physics_steps'] += 1
        if operation is mujoco.mj_forward:
            ledger['forward_calls'] += 1
        return result

    def phase(name, operation):
        before = ledger['physics_step_attempts']; started = time.perf_counter()
        try:
            return operation()
        finally:
            ledger['phases'].append(dict(name=name, attempted_steps=ledger['physics_step_attempts']-before,
                wall_s=time.perf_counter()-started))
            atomic_json(folder / 'cost.json', ledger)

    started = time.perf_counter()
    try:
        with patch.object(MujocoFailureSnapshot, 'call', counted):
            starts = value['initial_tensions_n'] if mode == 'contrast' else value['initial_tensions_n'][:1]
            radii = value['radii_m'][:1] if mode == 'neutral' else value['radii_m']
            for initial in starts:
                for radius in radii:
                    _, configs = configurations(value, radius)
                    candidate = dict(radius_m=radius, initial_tension_n=initial, conditions={})
                    for condition, cfg in configs:
                        label = f'{initial:g}-{radius:g}-{condition}'
                        args = prepared(cfg, value, initial)
                        atomic_json(folder / (label+'-configuration.json'), cfg)
                        result = phase(label+'-search', lambda: calculate(cfg, *args,
                            checkpoint=lambda name, data: atomic_json(folder / (label+'-progress.json'), data)))
                        atomic_json(folder / (label+'-search.json'), result)
                        schedule = result['native_dynamics']['optimized_schedule']
                        inp, physics, scene = binding(cfg, schedule['trajectory'])
                        raw = phase(label+'-replay', lambda: playback_tensions(inp, physics, scene,
                            schedule['trajectory']['tensions_n'], folder / label))
                        # Save raw before evaluation; a later error must retain paid observations.
                        atomic_json(folder / (label+'-raw.json'), raw)
                        ref = dict(artifact_id=digest(raw), media_type='application/json')
                        evaluation, profile = evaluate_playback(cfg, raw, ref, digest(cfg))
                        eref = dict(artifact_id=digest(plain(evaluation)), media_type='application/json')
                        profile.update(execution_id=label, simulation=ref, evaluation=eref)
                        pref = dict(artifact_id=digest(profile), media_type='application/json')
                        acceptance = assemble_acceptance(cfg, evaluation, profile, evaluation_reference=eref,
                            profile_reference=pref, motion=[dict(time_s=r['time_s']) for r in raw['samples']])
                        accepted = dict(evaluation=plain(evaluation), profile=profile, acceptance=acceptance)
                        atomic_json(folder / (label+'-acceptance.json'), accepted)
                        candidate['conditions'][condition] = dict(status=acceptance['status'],
                            search_stop=result['native_dynamics']['optimization']['stop_reason'],
                            baseline=result['native_dynamics']['optimization']['candidates'][0]['measure'],
                            best=result['native_dynamics']['optimization']['best']['measure'])
                        if result['native_dynamics']['optimization']['stop_reason'].startswith('numerical_failure'):
                            summary['results'].append(candidate)
                            summary['status'] = 'needs_solver_diagnosis'
                            return summary
                    summary['results'].append(candidate)
                    passes = all(r['status'] == 'accepted' for r in candidate['conditions'].values())
                    if passes and mode != 'contrast':
                        summary.update(status='first_complete_witness', complete_witness=True)
                        return summary
            summary['status'] = 'contrast_completed' if mode == 'contrast' else 'bounded_search_unresolved'
            return summary
    except Exception as exc:
        summary.update(status='stopped_with_error', error=str(exc),
            native_diagnostic=getattr(exc, 'native_diagnostic', None),
            mujoco_diagnostic=getattr(exc, 'mujoco_diagnostic', None))
        raise
    finally:
        ledger['scientific_wall_s'] = time.perf_counter()-started
        atomic_json(folder / 'cost.json', ledger)
        atomic_json(folder / 'summary.json', summary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['preflight','neutral','feasibility','contrast'], default='preflight')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--approval-file', type=Path)
    parser.add_argument('--witness-directory', type=Path)
    args = parser.parse_args(); value = plan()
    if args.mode == 'preflight':
        args.output.mkdir(parents=True, exist_ok=False)
        result = preflight(value)
        atomic_json(args.output / 'preflight.json', result)
    else:
        if args.approval_file is None:
            parser.error('scientific execution requires separate B2 authorization via --approval-file')
        approval = approved(args.approval_file, value, args.mode)
        if args.mode == 'contrast':
            if args.witness_directory is None:
                parser.error('contrast requires --witness-directory from a complete paired witness')
            witness = read(args.witness_directory / 'summary.json')
            costs = read(args.witness_directory / 'cost.json')
            if not witness['complete_witness'] or costs['plan_identity'] != digest(value):
                parser.error('contrast requires an independently accepted witness under this frozen plan')
            approval['witness_directory'] = str(args.witness_directory.resolve())
        approval['_path'] = str(args.approval_file.resolve())
        result = run(value, args.output, approval, args.mode)
    print(json.dumps({k:v for k,v in result.items() if k != 'rows'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
