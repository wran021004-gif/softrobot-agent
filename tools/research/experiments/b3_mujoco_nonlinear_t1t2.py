"""Frozen three-structure engineering experiment; explicit, persisted stage gates.

Uses only the original FamilySpace, Store, analysis workers and full replays.
No autonomous research loop or provider is started by this entry point.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

from tools.platform_store import plain
from tools.state_io import read,atomic_json,digest
from tools.research import core,analysis
from tools.research.state import state,save,update
from tools.research.design import generate_candidate,set_parameter
from tools.research.numerics import archived
from tools.research.contracts import LocalControlSearchSettings
from tools.research.physical_replay import initialize_schedule,binding
from tools.research.control_correction import task_measure,task_outputs
from tools.research_tasks import task_adapter
from tools.research.optimal_capability import CONIC,SENSITIVITY
from tools.research.nonlinear_capability import T1,T2,T1_OPERATION,T2_OPERATION

ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'runs/b3-mujoco-nonlinear-t1t2'
EVIDENCE=ROOT/'evidence/b3_mujoco_nonlinear_t1t2'
SPEC=ROOT/'configs/research/study_b3_mujoco_nonlinear_t1t2.json'
VARIABLE='segments.1.young_pa'
MODULI=dict(d_minus=4.86e6,d0=5.40e6,d_plus=5.94e6)
SETTINGS=dict(version='local_control_search_v2',method='response',knots_s=[0.,.38,.45,.5],
    correction_window_s=[0.,.5],active_coefficients=[9,10,13,14],coefficient_limit_n=2.,
    difference_step_n=.01,initial_radius_n=.1,minimum_radius_n=.0001,
    evaluation_requests=24,iterations=3,safety_margin_fraction=0.)
SOURCE_FOLDER='evidence/b3_t2_pilot_050_c'
SOURCE=dict(artifact_id='30994c15d28a3b1b434d1f4cdc252199773e3eb4c9888a4b47b3870ac8d004ea',media_type='application/json')


def plan(action,**kwargs):
    return dict(action=action,hypothesis='Fixed three-structure comparison may discriminate finite-budget task responses.',
        expected_observation='Signed J and original independent hard task metrics under matched controls and budgets.',
        weakening_observation='Flat, opposing or search-limited responses; invalid or unmatched evidence.',
        fixed_conditions='Frozen B3 task, own zero states, four tendon channels, same U0, knots and budget.',
        stopping_condition='Three structures, at most 24 callbacks and 3 updates each, 6 full replays, 90000 integration steps.',
        interpretation='Finite-budget mathematical diagnostics and same-model independent replay, no hardware or global inference.',**kwargs)


def host():
    h=core.prepare(SPEC,directory=RUN/'store')
    current=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if state(h).get('freeze')!=current:
        core.bind(h,reason='Committed implementation/experiment stage; preserve all prior evidence and cumulative costs.' if state(h).get('freeze') else None)
    return h


def record(h,name,value):
    ref=save(h,value,'b3_nonlinear_'+name)
    atomic_json(EVIDENCE/(name+'.json'),dict(reference=ref,**value))
    return value


def prepare():
    if (EVIDENCE/'frozen_plan.json').exists():raise ValueError('PLAN_ALREADY_FROZEN')
    h=core.prepare(SPEC,directory=RUN/'store')
    source=archived(SOURCE_FOLDER,SOURCE)
    disposition=read(ROOT/SOURCE_FOLDER/'disposition.json')
    replay_ref=disposition['evidence']['physical_replays'][0]
    replay=archived(SOURCE_FOLDER,replay_ref)
    old=archived(SOURCE_FOLDER,replay['candidate'])
    assert replay['source_reference']==SOURCE
    binding(old['configuration'],source['trajectory'])
    assert old['parameters']['segment_count']==2 and old['parameters']['tendon_count']==4
    variants={}
    for label,young in MODULI.items():
        params=deepcopy(old['parameters']);set_parameter(params,VARIABLE,young)
        generated=generate_candidate(h,params,dict(origin='fixed B3 nonlinear T1/T2',source_candidate=replay['candidate']))
        if generated['status']!='generated':raise ValueError(generated)
        candidate=generated['candidate']
        cfg=h.store.artifact(candidate)['configuration'];adapter=task_adapter(cfg)
        assert cfg['task']==old['configuration']['task'] and cfg['seed']==old['configuration']['seed']
        assert adapter.ranking_limits()==dict(terminal_error_m=.01,holding_max_error_m=.01,holding_max_speed_m_s=.02)
        assert cfg['task']['goal']['data']['target_m']==[.29,-.035,.19]
        assert cfg['task']['timing']==dict(timestep_s=.0005,control_period_s=.01,sample_period_s=.01,duration_s=.5,termination=['duration','numerical_failure'])
        assert abs(adapter.holding_start_s()-.45)<1e-12
        schedule=initialize_schedule(cfg,source,replay['candidate']);binding(cfg,schedule['trajectory'])
        assert schedule['trajectory']['tensions_n']==source['trajectory']['tensions_n']
        assert all(t['force_limit_n']==8. for t in cfg['robot']['structure']['data']['tendons'])
        initial=cfg['task']['initializer']['parameters']['data']
        assert not any(v for f in ('qpos_rad','qvel_rad_s') for v in initial[f].values())
        ref=save(h,schedule,'bound_applied_control_schedule')
        variants[label]=dict(candidate=candidate,source=ref,young_pa=young)
    update(h,reference_candidate=variants['d0']['candidate'],
        control_initializations=[dict(candidate=r['candidate'],source=r['source']) for r in variants.values()])
    settings=plain(LocalControlSearchSettings(**SETTINGS))
    frozen=dict(base_commit='78ca687fd893bfc805cfcaf1370ea62dd14dbf65',spec=str(SPEC.relative_to(ROOT)),
        scope='engineering_numerical; no autonomous Study',source=dict(folder=SOURCE_FOLDER,reference=SOURCE,
            prior_replay=replay_ref,parent=replay['candidate'],inherited_acceptance=False),
        variable=VARIABLE,unit='Pa',moduli_pa=MODULI,variants=variants,settings=settings,
        active_subspace_reason='M2 C recorded four-dimensional late-knot subspace; fixed before any new science.',
        gvs_operating_point='controller_start_input',
        task=cfg['task'],limits=adapter.ranking_limits(),holding_window_s=[.45,.5],
        tendon_order=source['trajectory']['tendon_order'],
        budgets=dict(provider=0,agent=0,gvs_charged_evaluations=22,native_callbacks_per_structure=24,
            updates_per_structure=3,fixed_rollouts=3,independent_best_replays=3,physics_steps=90000,nmpc=0,ppo=0,matlab=0),
        planned_mathematical_charges=dict(gvs_T1=6,gvs_T2=5,native_T1=3,native_T2_aggregation=1),
        maximum_planned_physics_steps=78000,stage_order=['gvs','fixed','t1','decision','verify'],
        decision_rule=dict(version='fixed-direction-rule-v1',
            gvs='Choose the corresponding endpoint only with resolved single-scale T2 direction, discriminating T1 values and no unresolved model validity; otherwise retain d0 and diagnose.',
            mujoco='Choose endpoint only with comparable T1 and conditional/resolved monotone T2 direction, sufficient search quality and equal opportunities; otherwise retain d0 and diagnose.',
            baseline='Always retain d0.',
            no_new_score='Use signed J and original hard metrics; no weighted ranking.',
            reveal='Save recommendations after T2 and before any best-control independent replay.'),
        expected_limits=['Same MuJoCo dynamics for optimization/replay; execution reproduction only.',
            'One shared warm initialization and one control subspace; no other-controller generalization.',
            'Three candidates, one run each; no statistical generalization.'],
        raw_store=str((RUN/'store').relative_to(ROOT)))
    record(h,'frozen_plan',frozen)
    print(json.dumps(dict(status='prepared',variants=variants),ensure_ascii=False))


def frozen():return read(EVIDENCE/'frozen_plan.json')


def completed(name):
    path=EVIDENCE/(name+'.json')
    if path.exists():raise ValueError('STAGE_ALREADY_COMPLETED_NO_AUTOMATIC_RECOMPUTATION: '+name)


def analyze(h,label,row,operation,**kwargs):
    query=dict(candidate=row['candidate'],operation=operation,operating_point='controller_start_input' if kwargs.get('model_source')=='gvs' else 'standardized_initial_pretension',
        protocol=state(h)['spec']['analysis_protocol'],**kwargs)
    out=analysis.dispatch(h,query,'b3-'+label+'-'+operation,guard=core.guard,origin='engineering_preflight')
    if not out.get('reference'):raise ValueError(out)
    value=h.store.artifact(out['reference'])
    if value['status']!='computed':raise ValueError(dict(reference=out['reference'],result=value))
    return dict(reference=out['reference'],value=value)


def gvs():
    completed('gvs');h=host();f=frozen();rows={}
    for label,row in f['variants'].items():
        rows[label]=analyze(h,label,row,'task_capability',model_source='gvs',capability_method=CONIC)
    t2=analyze(h,'gvs-t2',f['variants']['d0'],'task_capability',model_source='gvs',capability_method=CONIC,
        optimal_sensitivity=dict(variable=VARIABLE,steps=[540000.],model_results=[rows[k]['reference'] for k in ('d0','d_minus','d_plus')]))
    record(h,'gvs',dict(T1={k:v['reference'] for k,v in rows.items()},T2=t2['reference'],
        mathematical_evaluations=state(h)['mathematical_evaluations'],revealed_native_results=False))
    print('GVS predictions frozen',flush=True)


def used_steps(h):
    s=state(h)
    native=sum(h.store.artifact(r).get('native_dynamics',{}).get('cost',{}).get('physics_steps',0) for r in s['analysis_results'])
    replay=sum(h.store.artifact(h.store.artifact(r)['raw_reference'])['physics_steps'] for r in s['physical_replays'])
    return native+replay


def budget(h,prospective):
    core.guard(h,True)
    if used_steps(h)+prospective>frozen()['budgets']['physics_steps']:raise ValueError('TOTAL_PHYSICS_STEP_LIMIT')


def replay(h,label,row,source):
    budget(h,1000)
    out=core.dispatch(h,plan('physical_replay',physical_replay=dict(candidate=row['candidate'],source=source)),
        'b3-'+label,origin='engineering')['result']
    value=h.store.artifact(out['reference']);raw=h.store.artifact(value['raw_reference'])
    cfg=h.store.artifact(row['candidate'])['configuration'];adapter=task_adapter(cfg);limits=adapter.ranking_limits()
    measure=task_measure(task_outputs(raw),target=cfg['task']['goal']['data']['target_m'],holding_start=adapter.holding_start_s(),
        position_limit=limits['holding_max_error_m'],terminal_position_limit=limits['terminal_error_m'],speed_limit=limits['holding_max_speed_m_s'])
    samples=[r for r in raw['samples'] if r['time_s']>=adapter.holding_start_s()-1e-12]
    peaks=dict(holding_position_s=max(samples,key=lambda r:np.linalg.norm(np.asarray(r['tip_m'])-cfg['task']['goal']['data']['target_m']))['time_s'],
        holding_speed_s=max(samples,key=lambda r:np.linalg.norm(r['tip_velocity_m_s']))['time_s'])
    tensions=np.asarray([r['actual_tension_n'] for r in raw['samples'][1:]])
    assert raw['physics_steps']==1000
    return dict(reference=out['reference'],raw_reference=value['raw_reference'],measure=measure,
        peak_times=peaks,tensions=dict(order=raw['tendon_order'],minimum_n=float(tensions.min()),maximum_n=float(tensions.max())),
        acceptance=value['acceptance'],physics_steps=raw['physics_steps'])


def fixed():
    completed('fixed');assert (EVIDENCE/'gvs.json').exists();h=host()
    rows={k:replay(h,'fixed-'+k,r,r['source']) for k,r in frozen()['variants'].items()}
    record(h,'fixed',dict(results=rows,physics_steps=used_steps(h)))
    print('Fixed U0 responses saved',flush=True)


def t1():
    completed('t1');assert (EVIDENCE/'fixed.json').exists();h=host();f=frozen();rows={}
    for label,row in f['variants'].items():
        budget(h,24000)
        result=analyze(h,label,row,T1_OPERATION,model_source='mujoco',
            control_optimization=dict(source=row['source'],settings=f['settings']))
        rows[label]=dict(reference=result['reference'],control=result['value']['control_schedule_reference'],
            summary=result['value']['nonlinear_capability'])
    record(h,'t1',dict(results=rows,physics_steps=used_steps(h)))
    print('Finite-budget native T1 complete',flush=True)


def decision():
    completed('decision');h=host();f=frozen();rows=read(EVIDENCE/'t1.json')['results']
    result=analyze(h,'native-t2',f['variants']['d0'],T2_OPERATION,model_source='mujoco',
        nonlinear_response=dict(variable=VARIABLE,unit='Pa',t1_results=[rows[k]['reference'] for k in ('d0','d_minus','d_plus')]))
    native=result['value']['nonlinear_response'];g=read(EVIDENCE/'gvs.json')
    gvs=h.store.artifact(g['T2'])['optimal_sensitivity']
    # A single scale supplies no stable gradient; frozen GVS validity has no
    # cross-model task error bound. This rule deliberately abstains in that case.
    g_reasons=['Single-scale local GVS model has no verified nonlinear task-error bound.']
    choices=dict(gvs=dict(candidate='d0',action='retain_and_diagnose',reasons=g_reasons,
            observed_direction=gvs['direction_status'],evidence=g['T2']),
        mujoco=dict(candidate='d_plus' if native['direction_status'].endswith('increase') else
            'd_minus' if native['direction_status'].endswith('decrease') else 'd0',
            action='retain_and_diagnose' if native['direction_status']=='unresolved' else native['recommendation'],
            reasons=native['reasons'],evidence=result['reference']),
        baseline=dict(candidate='d0',action='retain',reasons=['Frozen no-structure-edit reference.']))
    record(h,'decision',dict(rule=f['decision_rule'],choices=choices,native_T2=result['reference'],
        native_response=native,replay_results_revealed=False,prior_best_control_replays=len(state(h)['physical_replays'])-3))
    print(json.dumps(choices,ensure_ascii=False),flush=True)


def verify():
    completed('verification');assert (EVIDENCE/'decision.json').exists();h=host();f=frozen()
    t=read(EVIDENCE/'t1.json')['results'];rows={}
    for label,row in f['variants'].items():
        rows[label]=replay(h,'best-confirm-'+label,row,t[label]['control'])
        raw=h.store.artifact(rows[label]['raw_reference']);outputs=task_outputs(raw)
        best=h.store.artifact(t[label]['reference'])['native_dynamics']['optimization']['best']['outputs']
        rows[label]['prediction_difference']={k:float(np.max(abs(np.asarray(outputs[k])-best[k]))) for k in outputs}
    choices=read(EVIDENCE/'decision.json')['choices'];baseline=rows['d0']['measure']['signed_maximum_excess']
    comparison={method:dict(selected=c['candidate'],J=rows[c['candidate']]['measure']['signed_maximum_excess'],
        improvement_over_baseline=baseline-rows[c['candidate']]['measure']['signed_maximum_excess']) for method,c in choices.items()}
    costs=dict(shared_ledger=h.store.remaining(),mathematical_evaluations=state(h)['mathematical_evaluations'],
        physics_steps=used_steps(h),numerical_s=state(h)['numerical_s'],
        analysis_costs=state(h)['analysis_costs'],physical_replays=len(state(h)['physical_replays']))
    record(h,'verification',dict(results=rows,decision_comparison=comparison,resources=costs,
        scope='Same-model execution reproduction; neither cross-model prediction nor hardware validation.'))
    from tools.research.budget import engineering_closeout
    engineering_closeout(h,'Fixed B3 three-structure protocol complete; no extension authorized.')
    print(json.dumps(dict(choices=comparison,physics_steps=used_steps(h)),ensure_ascii=False),flush=True)


if __name__=='__main__':
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
    dict(prepare=prepare,gvs=gvs,fixed=fixed,t1=t1,decision=decision,verify=verify)[sys.argv[1]]()
