"""Small fixed multi-condition experiment driver; original tools own numerics.

Task/configuration files are frozen before running. Private candidate manifests
and all controls/raw evidence stay under ignored runs/. No Provider or Agent.
"""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import argparse
import json
import time

import mujoco
import numpy as np

from examples import b2_fixed_search as b2
from extensions.tendon_family.mujoco_analysis import NativeModel, input_response
from extensions.tendon_family.backends import MujocoFailureSnapshot, playback_tensions
from tools.platform_store import plain
from tools.research.config import same_robot_structure
from tools.research.contracts import NativeAnalysisOptions
from tools.research.control_correction import constrained_response_step
from tools.research.physical_replay import binding, evaluate_playback, schedule_identity
from tools.research_tasks import assemble_acceptance
from tools.state_io import read, digest, atomic_json


def configurations(plan, candidate):
    _, rows = b2.configurations(plan, generation=candidate['generation'])
    base = rows[0][1]
    for _, cfg in rows:
        if not same_robot_structure(base, cfg) or base['policy']['discretization'] != cfg['policy']['discretization']:
            raise ValueError('JOINT_STRUCTURE_OR_MESH_MISMATCH')
    return rows


def initialized(cfg, plan, tension, folder):
    """Original short-response and constrained solver; uniform predeclared rule."""
    _, _, point, _, _ = b2.prepared(cfg, plan, tension)
    native = NativeModel(cfg)
    _, start = native.reconstruct(point)
    position = np.asarray(native.motion(start)[0]['tip_position_m'])
    target = (position + cfg['task']['goal']['data']['target_m']) / 2
    u = np.full(len(native.tendons), tension)
    for i in range(plan['initialization']['calls']):
        response = input_response(native, start, u, NativeAnalysisOptions(
            horizon_s=.05, difference_step_n=.01))
        atomic_json(folder / f'response-{i}.json', response)
        if not response['step_consistency_passed']:
            raise ValueError('INITIALIZATION_TWO_SCALE_CHECK_FAILED')
        baseline = np.asarray(response['baseline']['tip_position_m'])
        solved = constrained_response_step(
            [(baseline-target)/.01], np.asarray([response['position_input_jacobian_m_n']])/.01,
            np.zeros(len(u)), [u], np.eye(len(u)), native.limits[:,1],
            plan['initialization']['radius_n'], 8.)
        atomic_json(folder / f'proposal-{i}.json', {**solved,'delta':solved['delta'].tolist()})
        if not solved['success']:
            break
        proposal = np.clip(u + solved['delta'], 0, native.limits[:,1])
        check = native.rollout(start, proposal, .05)
        atomic_json(folder / f'check-{i}.json', check)
        if np.linalg.norm(np.asarray(check['tip_position_m'])-target) < np.linalg.norm(baseline-target):
            u = proposal
    atomic_json(folder / 'seed.json', dict(tensions_n=u.tolist(), cost=native.cost,
        provenance='Uniform fresh short response; no historical successful control'))
    return u.tolist()


def search(cfg, plan, tension, seed, previous, folder):
    outer, query, point, requirements, context = b2.prepared(cfg, plan, tension)
    schedule = previous or context['schedule']
    schedule = deepcopy(schedule)
    if previous is None:
        schedule['trajectory']['tensions_n'] = [seed] * len(schedule['trajectory']['tensions_n'])
        schedule['provenance'] = dict(control_initialization='fresh_uniform_short_response_v1', inherited_acceptance=False)
    source = dict(artifact_id=digest(schedule), media_type='application/json')
    query = query.model_copy(update={'control_optimization':query.control_optimization.model_copy(update={'source':source})})
    context = dict(schedule=schedule, source=source)
    return b2.calculate(cfg, outer, query, point, requirements, context,
        checkpoint=lambda name,value:atomic_json(folder / (name+'.json'),value))


def independent(cfg, schedule, folder):
    inp, physics, scene = binding(cfg, schedule['trajectory'])
    raw = playback_tensions(inp, physics, scene, schedule['trajectory']['tensions_n'], folder)
    atomic_json(folder/'raw.json', raw)
    rawref = dict(artifact_id=digest(raw), media_type='application/json')
    evaluation, profile = evaluate_playback(cfg, raw, rawref, digest(cfg))
    eref = dict(artifact_id=digest(plain(evaluation)), media_type='application/json')
    profile.update(execution_id=folder.name, simulation=rawref, evaluation=eref)
    pref = dict(artifact_id=digest(profile), media_type='application/json')
    acceptance = assemble_acceptance(cfg, evaluation, profile, evaluation_reference=eref,
        profile_reference=pref, motion=[dict(time_s=r['time_s']) for r in raw.get('samples',[])])
    value = dict(configuration_identity=digest(cfg), structure_identity=digest(cfg['robot']),
        mesh_identity=digest(cfg['policy']['discretization']), task_identity=digest(cfg['task']),
        control_identity=schedule_identity(cfg,schedule['trajectory']), raw_reference=rawref,
        evaluation=plain(evaluation), profile=profile, acceptance=acceptance)
    atomic_json(folder/'acceptance.json', value)
    return value


def run(plan_path, candidates_path, output):
    plan, candidates = read(plan_path), read(candidates_path)
    if digest(candidates) != plan['candidate_manifest_identity']:
        raise ValueError('FROZEN_CANDIDATES_MISMATCH')
    for label,path in plan['tasks'].items():
        if digest(read(b2.ROOT/path)) != plan['task_identities'][label]:
            raise ValueError('FROZEN_TASK_CHANGED: '+label)
    for path,identity in plan['frozen_sources'].items():
        if digest(read(b2.ROOT/path)) != identity:
            raise ValueError('FROZEN_ENGINEERING_SOURCE_CHANGED: '+path)
    if not plan.get('authorization') or not isinstance(plan['physics_step_attempt_cap'], int):
        raise ValueError('EXPLICIT_FINITE_EXPERIMENT_AUTHORIZATION_REQUIRED')
    # One cumulative ledger per frozen experiment, independent of output selection.
    marker = b2.ROOT/'runs'/('bf-budget-'+digest(plan)+'.used')
    marker.parent.mkdir(exist_ok=True)
    with marker.open('x',encoding='utf8') as stream:
        stream.write(str(output.resolve()))
    output.mkdir(parents=True,exist_ok=False)
    ledger = dict(plan_identity=digest(plan), cap=plan['physics_step_attempt_cap'],
        physics_step_attempts=0, completed_step_calls=0, failed_step_calls=0,
        failed_call_internal_progress='unknown', forward_calls=0, provider_requests=0,
        scientific_math_workers=0, native_search_calls=0, independent_replays=0, phases=[])
    atomic_json(output/'plan.json',plan)
    atomic_json(output/'candidates.json',candidates)
    result = dict(status='running',cases=[],joint=[])
    original = MujocoFailureSnapshot.call
    def counted(safety,data,operation,location):
        step = operation is mujoco.mj_step
        if step:
            if ledger['physics_step_attempts'] >= ledger['cap']:
                raise ValueError('BF_CUMULATIVE_ATTEMPT_CAP_EXHAUSTED')
            ledger['physics_step_attempts'] += 1
        try:
            value = original(safety,data,operation,location)
        except Exception:
            if step:ledger['failed_step_calls'] += 1
            raise
        if step:ledger['completed_step_calls'] += 1
        if operation is mujoco.mj_forward:ledger['forward_calls'] += 1
        return value
    def phase(label,fn):
        before=ledger['physics_step_attempts'];started=time.perf_counter()
        try:return fn()
        finally:
            ledger['phases'].append(dict(label=label,attempts=ledger['physics_step_attempts']-before,
                wall_s=time.perf_counter()-started))
            atomic_json(output/'cost.json',ledger)
            atomic_json(output/'summary.json',result)
    started=time.perf_counter()
    try:
        with patch.object(MujocoFailureSnapshot,'call',counted):
            for candidate in candidates:
                rows = configurations(plan,candidate)
                for tension in plan['initial_tensions_n']:
                    case_root=output/f"{candidate['label']}-{tension:g}"
                    try:
                        seed = phase(str(case_root.name)+'-initialization',lambda:initialized(
                            rows[0][1],plan,tension,case_root/'initialization'))
                    except Exception as exc:
                        result['cases'].append(dict(candidate=candidate['label'],start=tension,
                            status='initialization_error',error=str(exc)))
                        atomic_json(case_root/'error.json',dict(error=str(exc),diagnostic=getattr(exc,'native_diagnostic',None)))
                        continue
                    outcomes=[]
                    for condition,cfg in rows:
                        previous=None
                        row=dict(candidate=candidate['label'],start=tension,condition=condition,
                            status='unresolved',stages=[])
                        for stage in plan['stages']:
                            local=deepcopy(plan);local['search'].update(stage['search'])
                            folder=case_root/condition/str(stage['id'])
                            atomic_json(folder/'configuration.json',cfg)
                            try:
                                ledger['native_search_calls']+=1
                                value=phase(str(folder.relative_to(output))+'-native',lambda:search(
                                    cfg,local,tension,seed,previous,folder/'progress'))
                                atomic_json(folder/'native.json',value)
                                previous=value['native_dynamics']['optimized_schedule']
                                atomic_json(folder/'control.json',previous)
                                ledger['independent_replays']+=1
                                evaluated=phase(str(folder.relative_to(output))+'-independent',lambda:independent(
                                    cfg,previous,folder/'playback'))
                                acceptance=evaluated['acceptance']
                                row.update(status=acceptance['status'],metrics=acceptance['metrics'],
                                    components=acceptance['components'],acceptance_path=str(folder/'playback/acceptance.json'))
                                row['stages'].append(dict(stage=stage['id'],status=row['status'],
                                    search_stop=value['native_dynamics']['optimization']['stop_reason'],
                                    callbacks=value['native_dynamics']['cost']['optimization_evaluations']))
                                if row['status']=='accepted':break
                            except Exception as exc:
                                row.update(status='execution_error',error=str(exc))
                                atomic_json(folder/'error.json',dict(error=str(exc),
                                    diagnostic=getattr(exc,'native_diagnostic',getattr(exc,'mujoco_diagnostic',None))))
                                break
                        result['cases'].append(row);outcomes.append(row['status'])
                    result['joint'].append(dict(candidate=candidate['label'],start=tension,
                        all_conditions_accepted=len(outcomes)==len(rows) and all(x=='accepted' for x in outcomes)))
                    atomic_json(output/'summary.json',result)
        result['status']='completed'
    finally:
        ledger['driver_wall_s']=time.perf_counter()-started
        atomic_json(output/'cost.json',ledger);atomic_json(output/'summary.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--candidates',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=run(args.plan,args.candidates,args.output)
    print(json.dumps(dict(status=result['status'],joint=result['joint'])))


if __name__=='__main__':main()
