"""Bounded R1 experiment: train, freeze prospective predictions, then validate.

Uses the existing FamilySpace, Store, A4 sampled sensitivities and physical
playback/evaluator. No optimizer or provider is called. Each phase is resumable
from saved evidence; failed integration is charged before propagating errors.
"""
from copy import deepcopy
from pathlib import Path
import argparse
import subprocess
import sys
import time

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.state_io import read, atomic_json, digest
from tools.platform_store import plain
from tools.research import core, design
from tools.research.state import state, save, update
from tools.research.control_correction import corrected_tensions, task_outputs
from tools.research.nonlinear_capability import (
    sampled_constraints, task_sensitivities, compare_scales, validate_prediction, active_samples)
from tools.research.physical_replay import initialize_schedule, binding, evaluate_playback
from tools.research.task_constraints import describe_analysis_requirements
from tools.research_tasks import assemble_acceptance
from extensions.tendon_family.mujoco_analysis import NativeModel
from extensions.tendon_family.backends import playback_tensions

OUT = ROOT / 'evidence/a45_full_task_sensitivity_validation'
RUN = ROOT / 'runs/a45-full-task-sensitivity-validation'
PROTOCOL = read(OUT / 'protocol.json')
PACKAGE = read(ROOT / PROTOCOL['source'])


def prepare():
    """Freeze the original task, controller settings and actual FamilySpace."""
    RUN.mkdir(parents=True, exist_ok=True)
    cfg = PACKAGE['configuration']
    atomic_json(RUN / 'task.json', dict(seed=cfg['seed'], task=cfg['task'],
        settling=cfg['policy']['controller']['parameters']['data']['settling']))
    atomic_json(RUN / 'space.json', cfg['policy']['candidate_builder']['parameters']['data']['space'])
    control = read(ROOT / 'configs/research/control.json')
    control['controller_defaults'] = cfg['policy']['controller']
    atomic_json(RUN / 'control.json', control)
    defaults = read(ROOT / 'configs/research/family_study_defaults.json')
    defaults['runtime'] = str(ROOT / 'configs/research' / defaults['runtime'])
    atomic_json(RUN / 'family_study_defaults.json', defaults)
    spec = read(ROOT / 'configs/research/study_variable_segments_dev.json')
    spec.update(study_id='a45-full-task-sensitivity-validation',
        defaults='family_study_defaults.json',
        family_space=str(RUN / 'space.json'), task=str(RUN / 'task.json'),
        control=str(RUN / 'control.json'),
        family_execution={k:cfg['policy'][k] for k in ('backend', 'dynamics_model')},
        authorization='User A4.5: fixed R1 complete-task prediction validation, <=20000 new physics steps; no provider or optimization.',
        execution_instructions='Frozen protocol in evidence/a45_full_task_sensitivity_validation/protocol.json')
    atomic_json(RUN / 'study.json', spec)
    host = core.prepare(RUN / 'study.json', RUN / 'store')
    return host


def persist(host, label, result):
    ref = save(host, result, 'a45_' + label)
    s = state(host)
    update(host, research_mathematics=[*s.get('research_mathematics', []), ref],
        numerical_s=s['numerical_s'] + result.get('cost', {}).get('kernel_wall_s', 0))
    atomic_json(OUT / (label + '.json'), dict(reference=ref, **result))
    return ref


def used_steps(host):
    return sum(host.store.artifact(r).get('cost', {}).get('physics_steps', 0)
        for r in state(host).get('research_mathematics', []))


def candidate(host, kind, factor):
    parameters = deepcopy(PACKAGE['design_parameters'])
    if kind == 'structure':
        p = PROTOCOL['structure']
        design.set_parameter(parameters, p['path'], p['base'] + factor*p['h'])
    generated = design.generate_candidate(host, parameters, dict(origin='A4.5 frozen independent variant'))
    assert generated['status'] == 'generated', generated
    ref = generated['candidate']
    c = design.verify_candidate(host, ref)
    cfg = c['configuration']
    original = PACKAGE['configuration']
    assert cfg['task'] == original['task']
    for field in ('controller', 'backend', 'dynamics_model', 'discretization'):
        assert cfg['policy'][field] == original['policy'][field], field
    if kind != 'structure' or factor == 0:
        assert cfg['robot']['structure'] == original['robot']['structure']
    schedule = initialize_schedule(cfg, PACKAGE['control'], PACKAGE['candidate'])
    tr = schedule['trajectory']
    if kind == 'control':
        p = PROTOCOL['control']
        coefficients = np.zeros(8); coefficients[p['coefficient_index']] = factor*p['h']
        limits = [t['force_limit_n'] for t in cfg['robot']['structure']['data']['tendons']]
        changed = corrected_tensions(tr['tensions_n'], tr['times_s'][:-1], p['knots_s'],
            coefficients, limits, p['window_s'])
        # The selected channel stays strictly inside its original tension box.
        j = p['coefficient_index'] % 4
        assert np.all(changed[:, j] > 0) and np.all(changed[:, j] < limits[j])
        tr['tensions_n'] = changed.tolist()
    else:
        assert tr['tensions_n'] == PACKAGE['control']['trajectory']['tensions_n']
    binding(cfg, tr)
    return ref, cfg, schedule


def native_trial(host, label, kind, factor):
    path = OUT / (label + '.json')
    if path.exists():return read(path)
    assert used_steps(host) + 1000 <= PROTOCOL['physics_step_cap']
    ref, cfg, schedule = candidate(host, kind, factor)
    started = time.perf_counter(); native = NativeModel(cfg)
    result = dict(kind=kind, factor=factor, candidate=ref, configuration=cfg, schedule=schedule)
    try:
        d = mujoco.MjData(native.model)
        d.qpos[native.qi] = native.scene['qpos_rad']; d.qvel[native.vi] = native.scene['qvel_rad_s']
        native.forward(d)
        assert native.tendons == schedule['trajectory']['tendon_order']
        assert len(native.order) == 48
        tr = schedule['trajectory']
        outputs = native.rollout_sequence(d, tr['times_s'], tr['tensions_n'])
        result.update(status='completed', outputs=outputs,
            task_samples=sampled_constraints(outputs, describe_analysis_requirements(cfg, {})),
            per_physics_step_contact_check='passed: ncon=nefc=0; no warnings or nonfinite acceleration')
        assert len(result['task_samples']) == 13
    except Exception as exc:
        result.update(status='failed', reason=str(exc), diagnostic=getattr(exc, 'native_diagnostic', None))
        raise
    finally:
        result['cost'] = dict(**native.cost, kernel_wall_s=time.perf_counter()-started)
        persist(host, label, result)
        print(label, result['status'], 'cumulative physics steps', used_steps(host), flush=True)
    return read(path)


def row(trial, coordinate):
    return dict(value=coordinate, reference=trial['reference'],
        parameter_values={'axis':0.}, task_samples={'fixed_control':trial['task_samples']})


def metric_summary(samples):
    metrics = {}
    for c in dict.fromkeys(r['constraint_id'] for r in samples):
        worst = max((r for r in samples if r['constraint_id'] == c), key=lambda r:r['value'])
        metrics[c] = dict(value=worst['value'], units=worst['units'], time_s=worst['time_s'],
            margin=worst['limit']-worst['value'])
    return dict(metrics=metrics, signed_J=max(r['normalized_signed_excess'] for r in samples),
        task_constraints_pass=all(r['value'] <= r['limit'] for r in samples), active=active_samples(samples))


def train(host):
    if (OUT / 'predictions.json').exists():return
    base = native_trial(host, 'baseline', 'structure', 0.)
    # Exact saved R1 metric reproduction, without spending another baseline rollout.
    summary = metric_summary(base['task_samples'])
    original = PACKAGE['acceptance']['metrics']
    for key, value in summary['metrics'].items():
        assert abs(value['value']-original[key]) < 1e-10
    directions = []
    for kind in ('structure', 'control'):
        h = PROTOCOL[kind]['h']
        trials = {factor:native_trial(host, f'{kind}_{factor}', kind, factor)
            for factor in PROTOCOL['training_factors']}
        for scale in (1., .5):
            context = dict(rows=[row(base, 0.), row(trials[-scale], -scale*h), row(trials[scale], scale*h)],
                parameter=dict(units=PROTOCOL[kind]['unit']))
            sensitivity = task_sensitivities(context)
            directions.append(dict(direction_id=f'{kind}@{scale}h', coefficients={kind:1.},
                step=scale*h, task_sensitivity=sensitivity))
    compare_scales(directions)
    predictions = {}
    for kind in ('structure', 'control'):
        fine = next(d for d in directions if d['direction_id'] == f'{kind}@0.5h')['task_sensitivity']['fixed_control']
        delta = PROTOCOL[kind]['h']*PROTOCOL['holdout_factor']
        predicted = []
        for sample, derivative in zip(base['task_samples'], fine['finite_difference_per_unit']):
            change = delta*derivative*sample['limit']
            predicted.append(dict(sample, value=sample['value']+change,
                normalized_signed_excess=sample['normalized_signed_excess']+delta*derivative,
                predicted_change=change, change_over_threshold=change/sample['limit'],
                direction='increase' if change > 0 else 'decrease' if change < 0 else 'unchanged'))
        predictions[kind] = dict(coordinate=delta, samples=predicted, **metric_summary(predicted))
    result = dict(status='prospective_predictions_frozen',
        implementation=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        protocol=PROTOCOL, baseline=summary, directions=directions, predictions=predictions,
        physics_steps_before_holdout=used_steps(host), holdout_results_used=False)
    persist(host, 'predictions', result)
    print('PREDICTIONS_SAVED; commit before validate', flush=True)


def independent_trial(host, kind, trial):
    label = kind + '_independent_playback'
    path = OUT / (label + '.json')
    if path.exists():return read(path)
    assert used_steps(host) + 1000 <= PROTOCOL['physics_step_cap']
    cfg = trial['configuration']; tr = trial['schedule']['trajectory']
    inp, physics, scene = binding(cfg, tr)
    started = time.perf_counter()
    raw = playback_tensions(inp, physics, scene, tr['tensions_n'], RUN / label)
    rawref = save(host, raw, 'a45_independent_backend_raw')
    # Charge actual completed backend steps before any evaluation/comparison assertion.
    cost = dict(physics_steps=raw['physics_steps'], rollouts=1, model_builds=1,
        forward_evaluations=len(raw['samples'])+raw['command_intervals'], mechanics_evaluations=0,
        kernel_wall_s=time.perf_counter()-started)
    persist(host, label+'_cost', dict(status=raw['status'], raw_reference=rawref, cost=cost))
    evaluation, profile = evaluate_playback(cfg, raw, rawref, digest([trial['candidate'], tr]))
    evref = save(host, plain(evaluation), 'a45_original_registered_evaluation')
    profref = save(host, profile, 'a45_original_playback_profile')
    acceptance = assemble_acceptance(cfg, evaluation, profile, evaluation_reference=evref,
        profile_reference=profref, motion=raw['samples'])
    outputs = task_outputs(raw)
    differences = {k:float(np.max(abs(np.asarray(outputs[k])-trial['outputs'][k])))
        for k in outputs}
    result = dict(status=raw['status'], raw_reference=rawref, raw=raw,
        evaluation_reference=evref, evaluation=plain(evaluation), profile_reference=profref,
        profile=profile, acceptance=acceptance, native_backend_max_difference=differences,
        task_samples=sampled_constraints(outputs, describe_analysis_requirements(cfg, {})))
    persist(host, label, result)
    assert max(differences.values()) < 1e-10, differences
    assert acceptance['accepted'] == metric_summary(trial['task_samples'])['task_constraints_pass']
    return result


def validate(host):
    prediction = read(OUT / 'predictions.json')
    tracked = subprocess.check_output(['git', 'status', '--porcelain', '--',
        str(OUT / 'predictions.json')], cwd=ROOT, text=True).strip()
    assert not tracked, 'Commit prospective predictions before any holdout integration'
    checks = {}
    for kind in ('structure', 'control'):
        trial = native_trial(host, kind+'_holdout', kind, PROTOCOL['holdout_factor'])
        actual = independent_trial(host, kind, trial)
        predicted = prediction['predictions'][kind]
        fine = next(d for d in prediction['directions'] if d['direction_id'] == f'{kind}@0.5h')['task_sensitivity']['fixed_control']
        base = read(OUT / 'baseline.json')['task_samples']
        check = validate_prediction(base, fine['finite_difference_per_unit'], predicted['coordinate'], actual['task_samples'])
        checks[kind] = dict(validation=check, predicted=metric_summary(predicted['samples']),
            actual=metric_summary(actual['task_samples']), acceptance=actual['acceptance'],
            two_scale=fine['scale_comparisons'], training_active_switches=fine['active_switches'],
            baseline_to_holdout_active_switch=active_samples(base) != active_samples(actual['task_samples']),
            reoptimization_status='reoptimized_capability_unresolved')
    costs = [host.store.artifact(r).get('cost', {}) for r in state(host)['research_mathematics']]
    total = {k:sum(c.get(k, 0) for c in costs) for k in
        ('physics_steps', 'rollouts', 'model_builds', 'forward_evaluations', 'mechanics_evaluations', 'kernel_wall_s')}
    summary = dict(status='stopped', protocol=PROTOCOL, cost=total, budget=20000,
        unused_physics_steps=20000-total['physics_steps'], checks=checks,
        provider_calls=0, agent_calls=0, nmpc_calls=0, ppo_calls=0, optimization_calls=0,
        baseline_reproduction='all three original metrics within 1e-10; 51 world-frame samples, 48 named hinges, four tendon channels',
        store=str(host.store.root), research_mathematics=state(host)['research_mathematics'])
    persist(host, 'summary', summary)
    update(host, research_status='stopped', closed_unix=time.time())
    print('A45_COMPLETE', total, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('phase', choices=['prepare', 'train', 'validate'])
    args = parser.parse_args(); host = prepare()
    if args.phase == 'train':train(host)
    elif args.phase == 'validate':validate(host)
    else:print('Prepared; no physics integration', flush=True)
