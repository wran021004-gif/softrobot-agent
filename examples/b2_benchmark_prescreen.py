"""Frozen B3 six-tendon prescreen; existing family/search/playback kernels only."""
import argparse
from copy import deepcopy
import json
import time

import numpy as np
from scipy.optimize import least_squares

from examples.b2_math_decision_benchmark import (ROOT, OUT, ARCHIVE, read, save, generated,
    initial, options, room, plain, digest, model_context, binding, evaluate_playback,
    assemble_acceptance, NativeModel, LocalControlSearchSettings, search, SearchStopped,
    task_measure, corrected_tensions)


def freeze():
    s=read(OUT/'decision_input.json');cfg=generated(s)
    cfg['task']['task_id']='b3-six-tendon-035-v1'
    cfg['task']['name']='B3 0.35 s six independent tendon reach and stop prescreen v1'
    cfg['task']['source']='B2 frozen prescreen; existing B3 target and evaluation, B1 neutral topology only, no successful control initialization.'
    cfg['task']['goal']['data']['target_m']=[.29,-.035,.19]
    cfg['task']['timing']['duration_s']=.35
    cfg['task']['sampling']['window_s']=[0.,.35]
    settings={**s['control_settings'],'knots_s':[0.,.10,.25,.34],
        'correction_window_s':[0.,.35],'evaluation_requests':126,'iterations':5}
    task=dict(task=cfg['task'],seed=cfg['seed'],
        settling=cfg['policy']['controller']['parameters']['data']['settling'],
        family_space='configs/research/family_space_v1.json',neutral_request=s['neutral_request'],
        design_domain=dict(tendon_count=6,topology='three proximal plus three full spans, phase offset pi/3',
            common_radius_m=[.014,.023],common_young_scale=[.8,1.2],near_length_m=[.14,.18],
            distal_length_m='0.27 minus near_length_m',other_parameters='neutral FamilySpace v1 values'),
        physical_control=dict(kind='independent absolute ideal tensions',bounds_n=[0.,8.],
            cold_start_n=.2,control_period_s=.01,timestep_s=.0005),
        acceptance='Original evaluate.reach plus offline_reach_hold_v1: endpoint and all final 50 ms position <=10 mm and speed <=20 mm/s; execution/solver/force checks unchanged.',
        status='frozen task for exploratory prescreen, feasibility and structure discrimination not yet established')
    path=ROOT/'tasks/b2_b3_six_tendon_035_v1.json'
    if path.exists():raise FileExistsError(path)
    from tools.state_io import atomic_json
    atomic_json(path,task)
    save('benchmark_frozen',dict(configuration=cfg,settings=settings,task_file=str(path.relative_to(ROOT)),
        candidates=read(OUT/'protocol.json')['benchmark']['candidates'],new_cost=dict(physics_steps=0,rollouts=0)))


def config(candidate):
    frozen=read(OUT/'benchmark_frozen.json')
    cfg=generated(read(OUT/'decision_input.json'),young_scale=candidate['young_scale'],lengths=candidate['lengths_m'])
    cfg['task']=deepcopy(frozen['configuration']['task'])
    return cfg


def geometry():
    from extensions.tendon_family.gvs import forward_kinematics
    started=time.perf_counter();rows=[]
    for candidate in read(OUT/'benchmark_frozen.json')['candidates']:
        cfg=config(candidate);design=cfg['robot']['structure']['data']
        def position(q):
            return np.array(forward_kinematics(design,q,samples_per_segment=2)['tip_position_m'])+[0.,0.,.15]
        fit=least_squares(lambda q:position(q)-cfg['task']['goal']['data']['target_m'],
            np.array([-.5,0.,1.,0.,-.5,0.,1.,0.]),bounds=(-20.,20.),max_nfev=100,
            ftol=1e-10,xtol=1e-10,gtol=1e-10)
        rows.append(dict(candidate=candidate,initial_tip_m=position(np.zeros(8)).tolist(),
            fitted_curvature_rad_m=fit.x.tolist(),error_m=float(np.linalg.norm(fit.fun)),evaluations=fit.nfev))
    save('benchmark_geometry',dict(results=rows,new_cost=dict(physics_steps=0,rollouts=0,wall_s=time.perf_counter()-started),
        scope='Nonlinear geometry only, no dynamic/force feasibility or controller initialization.'))


def run(name):
    f=read(OUT/'benchmark_frozen.json');candidate=next(c for c in f['candidates'] if c['name']==name)
    if (OUT/('benchmark_'+name+'.json')).exists():raise FileExistsError(name)
    settings=LocalControlSearchSettings.model_validate(f['settings']);room(126*700)
    started=time.perf_counter();cfg=config(candidate);native=NativeModel(cfg);d=initial(native)
    _,_,_,spec=model_context(cfg);times=np.arange(36)*.01
    source=dict(source_kind='explicit_control_schedule_v1',provenance=dict(initialization='cold_constant_0.2_N'),
        trajectory=dict(times_s=times.tolist(),tensions_n=np.full((35,6),.2).tolist(),
            tendon_order=native.tendons,model_identity=spec['identity'],design_identity=spec['design_identity'],task_identity=digest(cfg['task'])))
    start=dict(id='cold',schedule=source,limits=native.limits[:,1].tolist(),task_options=options(cfg))
    prep_s=time.perf_counter()-started;failures=[];solver=[]
    def evaluate(_start,schedule,metadata):
        try:outputs=native.rollout_sequence(d,times,schedule['trajectory']['tensions_n'])
        except ValueError as error:
            if str(error)!='NATIVE_V1_REQUIRES_FINITE_CONTACT_FREE_UNCONSTRAINED_STATE':raise
            failures.append(dict(reason=str(error),metadata=metadata,schedule=schedule,
                diagnostic=getattr(error,'native_diagnostic',None),cost=dict(native.cost)))
            raise SearchStopped('native_contact_free_domain_exit') from error
        measure=task_measure(outputs,**options(cfg))
        return dict(reference=name+'-'+str(native.cost['rollouts']),outputs=outputs,measure=measure,
            task_gap=dict(valid_complete=True,accepted=False,normalized_gap=measure['normalized_gap']),cost_s=0.)
    # Time the existing SLSQP kernel without changing its inputs or result.
    import tools.research.local_control_search as module
    original=module.constrained_response_step
    def timed(*args,**kwargs):
        tick=time.perf_counter();result=original(*args,**kwargs)
        solver.append(dict(wall_s=time.perf_counter()-tick,success=result['success'],iterations=result['iterations']))
        return result
    module.constrained_response_step=timed
    try:
        result=search([start],evaluate,settings,evaluation_kind='native_short_rollout',
            rank_key=lambda r:(r['measure']['signed_maximum_excess'],r['measure']['sum_normalized_excess']),
            stop_when=lambda r:r['measure']['signed_maximum_excess']<=-settings.safety_margin_fraction)
    finally:module.constrained_response_step=original
    best=result['best'];schedule=deepcopy(source)
    if best is not None:
        schedule['trajectory']['tensions_n']=corrected_tensions(source['trajectory']['tensions_n'],times[:-1],settings.knots_s,
            best['coefficients_n'],native.limits[:,1],settings.correction_window_s).tolist()
    compact={**result,'candidates':[{k:v for k,v in row.items() if k!='outputs'} for row in result['candidates']],
        'best':None if best is None else {k:v for k,v in best.items() if k!='outputs'},'start_feedback':[]}
    save('benchmark_'+name,dict(candidate=candidate,configuration=cfg,schedule=schedule,search=compact,
        best_outputs=None if best is None else best['outputs'],
        initial_outputs=result['candidates'][0]['outputs'] if result['candidates'] else None,failures=failures,
        solver=solver,new_cost={**native.cost,'preparation_s':prep_s,'solver_s':sum(r['wall_s'] for r in solver),
            'solver_calls':len(solver),'solver_iterations':sum(r['iterations'] for r in solver),'wall_s':time.perf_counter()-started}))
    print(json.dumps(dict(name=name,best=None if best is None else best['measure'],stop=result['stop_reason'],cost=native.cost)),flush=True)


def replay(name):
    from extensions.tendon_family.backends import playback_tensions
    if (OUT/('benchmark_'+name+'_independent.json')).exists():raise FileExistsError(name)
    row=read(OUT/('benchmark_'+name+'.json'));cfg=row['configuration'];room(700)
    started=time.perf_counter();inp,physics,scene=binding(cfg,row['schedule']['trajectory'])
    folder=ROOT/'runs/b2_math_decision_benchmark'/('replay_'+name)
    failure=folder/'numerical_failure.json';recovered=failure.exists()
    if not recovered:
        try:raw=playback_tensions(inp,physics,scene,row['schedule']['trajectory']['tensions_n'],folder)
        except ValueError as error:
            if str(error)!='MUJOCO_NUMERICAL_FAILURE':raise
            recovered=True
    if recovered:
        snapshot=read(failure)
        save('benchmark_'+name+'_independent',dict(raw=dict(status='incomplete',failure=snapshot,samples=read(folder/'samples.json')),
            acceptance=None,evaluation=None,independent_execution_completed=False,
            interpretation='Saved actual failure from this B2 run, no reintegration. Original evaluator not invoked on incomplete execution. No infeasibility conclusion.',
            new_cost=dict(model_builds=1,physics_steps=snapshot['confirmed_completed_steps'],rollouts=1,failed_step_calls=1),
            failed_call_internal_steps='unknown',wall_s=None))
        return
    ref=ARCHIVE.put_context_checkpoint(raw)
    evaluation,profile=evaluate_playback(cfg,raw,ref,'b2-benchmark-'+name)
    acceptance=assemble_acceptance(cfg,evaluation,profile,motion=raw['samples'])
    save('benchmark_'+name+'_independent',dict(raw=raw,evaluation=plain(evaluation),profile=profile,acceptance=acceptance,
        new_cost=dict(model_builds=1,physics_steps=raw['physics_steps'],rollouts=1,wall_s=time.perf_counter()-started)))
    print(json.dumps(dict(name=name,accepted=acceptance['accepted'],metrics=acceptance['metrics'])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['freeze','geometry','run','replay'])
    p.add_argument('--name',choices=['neutral','soft','stiff','length_exchange']);args=p.parse_args()
    if args.command in ['run','replay']:globals()[args.command](args.name)
    else:globals()[args.command]()
