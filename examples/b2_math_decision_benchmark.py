"""Finite B2 decision replay and benchmark recipe using existing numerical kernels.

Historical evidence stays in B1; only the frozen decision input is projected here.
No research Agent, provider, alternative optimizer or alternative evaluator.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import time

import mujoco
import numpy as np

from tools.state_io import read, atomic_json, digest
from tools.platform_store import plain, Store
from tools.research.config import ROOT
from tools.research.contracts import LocalControlSearchSettings
from tools.research.control_correction import task_measure, corrected_tensions
from tools.research.local_control_search import search, SearchStopped
from tools.research.nonlinear_capability import (sampled_constraints, task_sensitivities,
    validate_prediction, control_sensitivities)
from tools.research.physical_replay import model_context, binding, evaluate_playback
from tools.research_tasks import task_adapter, assemble_acceptance
from extensions.tendon_family.family_space import parse_build
from extensions.tendon_family.generated_serial import generate_family
from extensions.tendon_family.mujoco_analysis import NativeModel

HISTORY = '305abc2509995ea796c7ef57eb3f4ff19f158b54'
HISTDIR = 'evidence/b1_math_guided_benchmark_discovery/'
OUT = ROOT/'evidence/b2_math_decision_benchmark'
ARCHIVE = Store(ROOT/'runs/b2_math_decision_benchmark/archive')
CAP = 500000


def historical(name):
    return json.loads(subprocess.check_output(['git', 'show', HISTORY+':'+HISTDIR+name+'.json'], cwd=ROOT))


def save(name, value):
    path = OUT/(name+'.json')
    if path.exists():
        raise FileExistsError(path)
    reference = ARCHIVE.put_context_checkpoint(value)
    atomic_json(path, value)
    print(json.dumps(dict(saved=name, reference=reference)), flush=True)


def used_steps():
    return sum(read(p).get('new_cost', {}).get('physics_steps', 0) for p in OUT.glob('*.json'))


def room(steps):
    if used_steps()+steps > CAP:
        raise ValueError('B2_FROZEN_STEP_CAP')


def options(cfg):
    adapter = task_adapter(cfg)
    limits = adapter.ranking_limits()
    return dict(target=cfg['task']['goal']['data']['target_m'], holding_start=adapter.holding_start_s(),
        position_limit=limits['holding_max_error_m'], terminal_position_limit=limits['terminal_error_m'],
        speed_limit=limits['holding_max_speed_m_s'])


def initial(native):
    d = mujoco.MjData(native.model)
    d.qpos[native.qi] = native.scene['qpos_rad']
    d.qvel[native.vi] = native.scene['qvel_rad_s']
    native.forward(d)
    return d


def requirements(cfg):
    return task_adapter(cfg).analysis_requirements(dict(task_identity=digest(cfg['task'])))


def freeze():
    started = time.perf_counter()
    frozen = historical('frozen_v1')
    rows = {target: historical('neutral101_'+target) for target in frozen['target_order']}
    independent = historical('neutral101_independent')
    snapshot = dict(historical_source=dict(commit=HISTORY, directory=HISTDIR),
        visibility='Only frozen_v1 and neutral101_{target,independent}; no later outcomes or explanations.',
        configuration=rows['up_z']['configuration'], control_settings=frozen['settings'],
        family_space=frozen['family_space'], neutral_request=frozen['neutral_request'], targets_m=frozen['targets_m'],
        targets={target: dict(metrics=row['t1']['best_metrics'], initial_metrics=row['t1']['initial_metrics'],
            schedule=row['schedule'], best_outputs=row['best_outputs'], cost=row['cost'],
            stop_reason=row['search']['stop_reason'], local_responses=row['search']['local_responses'],
            final_solver=row['search']['best'].get('local_solver'),
            best_proposal=row['search']['best'],
            accepted=independent['results'][target]['acceptance']['accepted']) for target,row in rows.items()},
        historical_common_cost={key:sum(row['cost'][key] for row in rows.values()) for key in rows['up_z']['cost']},
        historical_common_validation_cost={key:sum(r['cost'][key] for r in independent['results'].values())
            for key in ('rollouts','physics_steps','wall_s')}, new_cost=dict(physics_steps=0,rollouts=0,wall_s=time.perf_counter()-started))
    save('decision_input', snapshot)
    protocol = dict(kind='Historical decision replay; investigator has read B1 report; no prospective blinding claim.',
        cap_new_mujoco_steps=CAP,
        A=dict(visible=['metrics','best proposal improvement','budget exit'],
            rule='If max J <= 0.1 and last proposal improved, add exactly one response iteration to failed target; otherwise test radius 20 mm cold.',
            action='Replay sealed 126/5 cold run for up_z only, verify 101-prefix identity, retain already passing targets.'),
        B=dict(visible='A plus saved trajectories, saturation, response condition and optimizer status; no new integration.',
            rule='If upper tension headroom and a budget exit coexist with small residual, same extra iteration; ill-conditioning prevents sufficiency claims.',
            action='Same paired continuation as A.'),
        C=dict(diagnostic='Actual B1 up_z best control: 24 +0.02 N control probes; strongest useful coefficient at +0.01 and held-out +0.015 N. Coupled radius ±10/±5 micrometers and held-out +7.5 micrometers. Original constraints at every holding sample.',
            rule='Prefer unchanged-structure continuation unless held-out local radius evidence removes the full residual inside ±10 micrometers while preserving every position constraint. No extrapolation to 2 mm or optimal capability.',
            applicability='No initial affine GVS-T1/T2 or dense single-step transition Jacobian: whole-trajectory sampled constraints are the question. No transplantation of A4 engineering sensitivities.'),
        paired_validation='Only after A/B/C actions saved: read sealed neutral126 up_z; exact prefix audit; charge historical acquisition and separable suffix, never new wall time.',
        benchmark=dict(priority='B3 six-tendon reach/hold 0.35 s; preserve existing world target [0.29,-0.035,0.19] and thresholds.',
            reason='Mature independent evaluation and native control; dynamic braking tradeoff without changing goals to favor a structure.',
            other_candidates='B1 v2 multi-target costs more per fair control opportunity; load hold blocked by Native external-force support, defer both.',
            candidates=[dict(name='neutral',young_scale=1.,lengths_m=[.16,.11]),
                dict(name='soft',young_scale=.8,lengths_m=[.16,.11]),
                dict(name='stiff',young_scale=1.2,lengths_m=[.16,.11]),
                dict(name='length_exchange',young_scale=1.,lengths_m=[.14,.13])],
            settings=dict(evaluation_requests=126,iterations=5,knots_s=[0.,.10,.25,.34],
                initialization='constant 0.2 N for every candidate; no B1 success controls',
                other_settings='same original local_control_search response settings'),
            stopping='Execute four declared candidates once; stop before cap. No target or score changes. Independent replay each best. No global or statistical structural superiority claim.',
            criteria='Prefer benchmark only if reoptimized structural differences remain and neutral is not trivially solved. Pass witness alone does not establish discrimination.'),
        new_cost=dict(physics_steps=0,rollouts=0))
    save('protocol', protocol)
    target=snapshot['targets']['up_z']
    common=dict(maximum_violation='up_z holding speed', constraints=target['metrics'],
        sufficient_control_optimization=False, sufficiency_reason='101 callbacks / four iterations is a resource limit, not convergence.',
        distinguishing_experiment='Same structure and original cold-start algorithm with one additional iteration on failed target only.',
        expected_maximum_acquisition_cost=dict(extra_suffix_rollouts=25,extra_suffix_physics_steps=35000,
            full_cold_restart_rollouts=126,full_cold_restart_physics_steps=176400),
        alternative_result='If still failed or stagnated, inspect control parameterization and model domain before claiming structural limitation.')
    save('decision_A', dict(**common,action=protocol['A']['action'],
        rationale='Small performance residual and improving last proposal meet predeclared allocation rule; no new mathematical evidence.',
        new_cost=dict(physics_steps=0,rollouts=0)))
    u=np.asarray(target['schedule']['trajectory']['tensions_n'])
    save('decision_B', dict(**common, action=protocol['B']['action'],
        maximum_tension_n=float(u.max()),upper_limit_n=8.,lower_bound_active=bool(np.any(u<1e-10)),
        response_conditions=[r['resolved_subspace_condition'] for r in target['local_responses']],
        rationale='Upper tension far from saturation; response ill-conditioned and stopping budget-limited. Continue control, do not infer globally adequate actuation or convergence.',
        new_cost=dict(physics_steps=0,rollouts=0)))


def generated(snapshot, radius=.018, young_scale=1., lengths=None):
    request=deepcopy(snapshot['neutral_request'])
    for span in request['spans']:
        span['radius_m']=radius
    if young_scale!=1. or lengths:
        request['segments']={str(i):dict(young_pa=[7.2e6,5.4e6][i]*young_scale,
            length_m=(lengths or [.16,.11])[i]) for i in range(2)}
    build=parse_build(dict(space=snapshot['family_space'],request=request))
    robot,mesh,physics=generate_family(build)
    cfg=deepcopy(snapshot['configuration'])
    cfg['robot']['structure']['data']=robot
    cfg['policy']['discretization']['data']=mesh
    cfg['policy']['candidate_builder']=dict(extension_id='candidate.family',version='5.0.0',
        parameters=dict(contract='family.serial_space_build',version='1.0.0',data=plain(build)))
    cfg['task']['initializer']['parameters']['data']={
        **{field:{j:0. for j in physics['dofs']} for field in ('qpos_rad','qvel_rad_s')},'unspecified':'zero'}
    return cfg


def diagnose():
    s=read(OUT/'decision_input.json');cfg=s['configuration'];source=s['targets']['up_z']['schedule']
    settings=LocalControlSearchSettings.model_validate({**s['control_settings'],'evaluation_requests':25,'iterations':1})
    native=NativeModel(cfg);d=initial(native);times=source['trajectory']['times_s'];req=requirements(cfg)
    start=dict(id='frozen-up-z',schedule=source,limits=native.limits[:,1].tolist(),task_options=options(cfg))
    started=time.perf_counter();room(25*1400)
    def evaluate(_start,schedule,meta):
        outputs=native.rollout_sequence(d,times,schedule['trajectory']['tensions_n'])
        measure=task_measure(outputs,**options(cfg))
        return dict(reference='b2-control-'+str(native.cost['rollouts']),outputs=outputs,measure=measure,
            task_gap=dict(valid_complete=True,accepted=False,normalized_gap=measure['normalized_gap']),cost_s=0.)
    if (OUT/'a4_control_probes.json').exists():
        saved=read(OUT/'a4_control_probes.json');result=saved['search'];sensitivity=saved['sensitivity']
    else:
        result=search([start],evaluate,settings,evaluation_kind='native_short_rollout',
            rank_key=lambda r:(r['measure']['signed_maximum_excess'],r['measure']['sum_normalized_excess']))
        sensitivity=control_sensitivities(result,req)
        save('a4_control_probes',dict(search=result,sensitivity=sensitivity,
            new_cost={**native.cost,'wall_s':time.perf_counter()-started},
            scope='Offset parameterization around original B1 best control; positive one-sided probes may clip at 0 N. No reoptimization claim.'))
    base_samples=sampled_constraints(result['candidates'][0]['outputs'],req)
    useful=[]
    for response in sensitivity['responses']:
        deriv=np.asarray(response['finite_difference_per_n'])
        predicted=np.array([r['normalized_signed_excess'] for r in base_samples])+.01*deriv
        useful.append((float(max(predicted)),response['coefficient_index'],deriv))
    _,coefficient,derivative=min(useful,key=lambda row:row[0])
    if not (OUT/'a4_control_holdout_plan.json').exists():
        save('a4_control_holdout_plan',dict(coefficient_index=coefficient,selection='min predicted whole-task J at +0.01 N using 0.02 N probes; held-out +0.015 N not read',
            new_cost=dict(physics_steps=0,rollouts=0)))
    started=time.perf_counter();native=NativeModel(cfg);d=initial(native);room(2*1400)
    checks=[]
    for delta in (() if (OUT/'a4_control_validation.json').exists() else (.01,.015)):
        x=np.zeros(24);x[coefficient]=delta
        u=corrected_tensions(source['trajectory']['tensions_n'],times[:-1],settings.knots_s,x,native.limits[:,1],settings.correction_window_s)
        outputs=native.rollout_sequence(d,times,u)
        checks.append(dict(delta_n=delta,outputs=outputs,samples=sampled_constraints(outputs,req)))
    if checks:
        fine=(np.array([r['normalized_signed_excess'] for r in checks[0]['samples']])-
            np.array([r['normalized_signed_excess'] for r in base_samples]))/.01
        save('a4_control_validation',dict(coefficient_index=coefficient,checks=checks,
            two_scale_relative_difference=float(np.linalg.norm(fine-derivative)/max(np.linalg.norm(fine),1e-30)),
            validation=validate_prediction(base_samples,fine,.015,checks[1]['samples']),
            new_cost={**native.cost,'wall_s':time.perf_counter()-started}))
    started=time.perf_counter();room(5*1400);rows=[];total={}
    # Baseline is the newly verified exact same control, reused without integration.
    rows.append(dict(value=.018,parameter_values={'coupled_radius_m':.018},reference='a4_control_probes/candidates/0',
        task_samples=dict(fixed_control=base_samples,reoptimized_control=[])))
    raw=[]
    for delta in (-.00001,.00001,-.000005,.000005,.0000075):
        variant=generated(s,radius=.018+delta);native=NativeModel(variant);d=initial(native)
        outputs=native.rollout_sequence(d,times,source['trajectory']['tensions_n'])
        row=dict(value=.018+delta,parameter_values={'coupled_radius_m':.018+delta},
            reference='a4_radius/'+str(delta),task_samples=dict(fixed_control=sampled_constraints(outputs,req),reoptimized_control=[]))
        rows.append(row);raw.append(dict(delta_m=delta,configuration=variant,outputs=outputs))
        for k,v in native.cost.items():total[k]=total.get(k,0)+v
    save('a4_radius_raw',dict(rows=rows,raw=raw,new_cost={**total,'wall_s':time.perf_counter()-started}))
    contexts=[dict(rows=[rows[0],rows[lo],rows[hi]],validation_rows=[rows[5]],
        parameter=dict(units='m'),coefficients={'coupled_radius_m':1.},
        parameters={'coupled_radius_m':dict(bounds=[.014,.023])}) for lo,hi in [(1,2),(3,4)]]
    sensitivities=[task_sensitivities(context) for context in contexts]
    save('a4_radius',dict(raw_source='a4_radius_raw.json',sensitivities=sensitivities,
        new_cost=dict(physics_steps=0,rollouts=0),
        scope='Actual six-tendon two-segment B1, same full sequence and zero state. Coupled legal span radius perturbation only.'))
    fine=sensitivities[1]['fixed_control'];control=read(OUT/'a4_control_validation.json')
    base=np.array([r['normalized_signed_excess'] for r in base_samples])
    radius_can_fix=any(max(base+step*np.asarray(fine['finite_difference_per_unit']))<=0 for step in [-.00001,.00001])
    save('decision_C',dict(action='Same paired continuation as A/B.' if not radius_can_fix else 'Investigate local radius correction before continuation.',
        largest_violation=s['targets']['up_z']['metrics'],radius_can_remove_residual_locally=bool(radius_can_fix),
        radius_prediction_status=fine['status'],control_prediction_status=control['validation']['status'],
        rationale='Compare full original sampled constraints, not moment-arm change. Local radius effect cannot establish 2 mm reoptimized gain. Continuation tests optimization sufficiency.',
        expected_validation='Read only sealed failed-target fifth iteration, verify prefix identity and original independent acceptance.',
        alternative_result='If continuation failed, examine parameterization and constraints; no structural infeasibility inference.',
        new_cost=dict(physics_steps=0,rollouts=0)))


def validate_history():
    decisions={label:read(OUT/('decision_'+label+'.json')) for label in 'ABC'}
    old=historical('neutral101_up_z');later=historical('neutral126_up_z');independent=historical('neutral126_independent')
    prefix=all(a['sequence_hash']==b['sequence_hash'] for a,b in zip(old['search']['candidates'],later['search']['candidates']))
    assert prefix and len(old['search']['candidates'])==101
    accepted=independent['results']['up_z']['acceptance']
    snapshot=read(OUT/'decision_input.json')
    save('paired_historical_validation',dict(decisions=decisions,prefix_identical=prefix,prefix_length=101,
        source=dict(commit=HISTORY,search=HISTDIR+'neutral126_up_z.json',independent=HISTDIR+'neutral126_independent.json'),
        before=old['t1']['best_metrics'],after=later['t1']['best_metrics'],independent_acceptance=accepted,
        group_with_retained_original_targets=bool(accepted['accepted'] and all(snapshot['targets'][t]['accepted'] for t in ['plus_y','minus_y'])),
        historical_acquisition_cost=later['cost'],
        historical_separable_suffix_cost={k:later['cost'][k]-old['cost'][k] for k in ('rollouts','physics_steps')},
        historical_independent_cost=independent['results']['up_z']['cost'],
        first_suffix_nonpositive_callback=next((i+1 for i,r in enumerate(later['search']['candidates'])
            if i>=101 and r['measure']['signed_maximum_excess']<=0),None),
        new_cost=dict(physics_steps=0,rollouts=0),
        limitation='Identical action gets identical sealed outcome, not three independently sampled trials. Suffix is a cost counterfactual; cold rerun acquisition actually paid the prefix again.'))


def validate_control_probe():
    """Secondary information check; does not revise the frozen strategy decision."""
    from extensions.tendon_family.backends import playback_tensions
    check=read(OUT/'a4_control_validation.json');s=read(OUT/'decision_input.json')
    save('a4_secondary_validation_plan',dict(action='Independently execute +0.015 N at the selected control coefficient.',
        coefficient_index=check['coefficient_index'],comparison_status='Secondary validation after A/B/C actions and historical check; not a new prospective policy.',
        expected='Native held-out execution satisfied metrics; test original full-backend acceptance.',
        budget=dict(rollouts=1,physics_steps=1400),new_cost=dict(physics_steps=0,rollouts=0)))
    cfg=s['configuration'];schedule=deepcopy(s['targets']['up_z']['schedule']);settings=s['control_settings']
    x=np.zeros(24);x[check['coefficient_index']]=.015
    tr=schedule['trajectory']
    tr['tensions_n']=corrected_tensions(tr['tensions_n'],tr['times_s'][:-1],settings['knots_s'],x,[8.]*6,settings['correction_window_s']).tolist()
    room(1400);started=time.perf_counter();inp,physics,scene=binding(cfg,tr)
    raw=playback_tensions(inp,physics,scene,tr['tensions_n'],ROOT/'runs/b2_math_decision_benchmark/replay_control_holdout')
    ref=ARCHIVE.put_context_checkpoint(raw);evaluation,profile=evaluate_playback(cfg,raw,ref,'b2-a4-secondary-control')
    acceptance=assemble_acceptance(cfg,evaluation,profile,motion=raw['samples'])
    save('a4_control_independent',dict(schedule=schedule,raw=raw,evaluation=plain(evaluation),profile=profile,acceptance=acceptance,
        new_cost=dict(model_builds=1,physics_steps=raw['physics_steps'],rollouts=1,wall_s=time.perf_counter()-started)))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['freeze','diagnose','validate_history','validate_control_probe'])
    args=p.parse_args()
    marker={'freeze':'decision_input','diagnose':'decision_C','validate_history':'paired_historical_validation',
        'validate_control_probe':'a4_secondary_validation_plan'}[args.command]
    if (OUT/(marker+'.json')).exists():raise FileExistsError(marker)
    globals()[args.command]()


if __name__=='__main__':
    main()
