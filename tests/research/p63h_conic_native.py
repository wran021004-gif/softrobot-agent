"""One user-authorized numerical comparison using production Store and workers.

Run --phase h1, then inspect evidence before selecting --phase h2 --variable
and --step. No Provider, imported historical control, or alternate optimizer.
Existing receipts are reused; interrupted requests require original recovery.
"""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import time

from tools.research.config import ROOT
from tools.state_io import atomic_json, read
from tools.research import core, analysis, physical_replay
from tools.research.state import state, save
from tools.research.design import generate_candidate, verify_candidate, set_parameter
from tools.research.contracts import ControlSeedRequest, PhysicalReplayRequest
from tools.research.optimal_capability import CONIC, family_parameters
from tools.research.nonlinear_capability import T1_OPERATION, T2_OPERATION

DEST = ROOT/'runs/p63h'


def host():
    h = core.prepare(ROOT/'configs/research/study_p63h_conic_native.json', DEST/'store')
    h.actor = 'operator-p63h'
    for k, v in state(h)['spec']['runtime']['threads'].items():
        os.environ[k] = v
    if 'freeze' not in state(h):
        core.bind(h)
    core.guard(h)
    return h


def run_analysis(h, name, candidate, *, allow_incomplete=False, **fields):
    query = dict(candidate=candidate, operating_point='standardized_initial_pretension',
        protocol=state(h)['spec']['analysis_protocol'], **fields)
    out = analysis.dispatch(h, query, 'p63h-'+name, guard=core.guard, origin='engineering_preflight')
    atomic_json(DEST/(name+'.json'), out)
    raw = h.store.artifact(out['reference']) if out.get('reference') else out
    print(json.dumps(dict(stage=name, status=raw.get('status'), reference=out.get('reference'),
        J=raw.get('nonlinear_capability',{}).get('J'), reason=raw.get('reason'),
        charged_s=raw.get('charged_numerical_s')), allow_nan=False), flush=True)
    if raw.get('status') != 'computed' and not allow_incomplete:
        raise RuntimeError('Retain failed evidence and costs: '+name+' '+str(out.get('reference')))
    return out['reference'], raw


def replay(h, name, candidate, source):
    path = DEST/(name+'.json')
    if path.exists():
        return read(path)
    out = physical_replay.dispatch(h, PhysicalReplayRequest(candidate=candidate,source=source), 'p63h-'+name)
    atomic_json(path, out)
    print(json.dumps(dict(stage=name, status=out.get('status'), acceptance=out.get('acceptance'),
        charged_s=out.get('charged_numerical_s')), allow_nan=False), flush=True)
    return out


def settings(h):
    duration = state(h)['spec']['analysis_protocol']['duration_s']
    return dict(version='local_control_search_v2', method='response',
        knots_s=[0.,duration/3,2*duration/3,duration], correction_window_s=[0.,duration],
        coefficient_limit_n=2., difference_step_n=.01, initial_radius_n=.1,
        minimum_radius_n=.0001, evaluation_requests=200, iterations=60, safety_margin_fraction=0.)


def native(h, name, candidate, source, *, allow_incomplete=False):
    return run_analysis(h,name,candidate,operation=T1_OPERATION,model_source='mujoco',
        control_optimization=dict(source=source, settings=settings(h)),allow_incomplete=allow_incomplete)


def h1(h):
    prepared = DEST/'preparation.json'
    if prepared.exists():
        info = read(prepared)
    else:
        request = dict(version='serial_family_generation_v2',
            family_space_identity=state(h)['spec']['family_space_identity'], segment_count=2,tendon_count=6)
        candidate = generate_candidate(h,request,dict(origin='P6.3-H unevaluated FamilySpace defaults; no historical answer'))['candidate']
        start = time.perf_counter()
        seed = physical_replay.seed_control(h,ControlSeedRequest(candidate=candidate,method='baseline'),'p63h-baseline')
        info = dict(candidate=candidate,baseline_source=seed['source'],baseline_source_wall_s=time.perf_counter()-start,
            generation=request,settings=settings(h),study_id=h.run_id,freeze=state(h)['freeze'],
            ownership='operator controlled numerical research; not Main discovery or Benchmark',historical_controls_imported=[])
        atomic_json(prepared,info)
    candidate = info['candidate']
    conic_ref, conic = run_analysis(h,'conic',candidate,operation='task_capability',model_source='gvs',capability_method=CONIC)
    if 'conic_source' not in info:
        started=time.perf_counter()
        seed=physical_replay.seed_control(h,ControlSeedRequest(candidate=candidate,method='capability_sequence',response_evidence=conic_ref),'p63h-conic-source')
        info.update(conic_result=conic_ref,conic_source=seed['source'],conic_source_wall_s=time.perf_counter()-started)
        atomic_json(prepared,info)
    a, ar = native(h,'direct',candidate,info['baseline_source'])
    b, br = native(h,'guided',candidate,info['conic_source'],allow_incomplete=True)
    assert ar['requested_operation']['control_optimization']['settings']==br['requested_operation']['control_optimization']['settings']
    sources=[('replay-direct',ar['control_schedule_reference']),('replay-conic',info['conic_source'])]
    if br.get('control_schedule_reference'):
        sources.insert(1,('replay-guided',br['control_schedule_reference']))
    for label,source in sources:
        replay(h,label,candidate,source)
    atomic_json(DEST/'h1-completed.json',dict(preparation=info,direct=a,guided=b,
        numerical_s=state(h)['numerical_s'],ledger=h.store.remaining(),mathematical_evaluations=state(h)['mathematical_evaluations']))


def h2(h, variable, step):
    info=read(DEST/'preparation.json');base=info['candidate']
    params,domain=family_parameters(state(h)['spec'],verify_candidate(h,base),variable)
    origin=domain['current_value']
    assert step>0 and domain['bounds'][0]<=origin-step<origin+step<=domain['bounds'][1]
    refs=[info['conic_result']];t1=[read(DEST/'direct.json')['reference']]
    contrasts=[]
    for label,offset in [('minus',-step),('plus',step),('minus-half',-step/2),('plus-half',step/2)]:
        p=deepcopy(params);set_parameter(p,variable,origin+offset)
        c=generate_candidate(h,p,dict(origin='P6.3-H single parameter contrast',variable=variable,offset=offset))['candidate']
        model,_=run_analysis(h,'model-'+label,c,operation='linearization',model_source='gvs',scoring_window_s=.5)
        refs.append(model);contrasts.append(dict(label=label,candidate=c,offset=offset))
    sensitivity,sraw=run_analysis(h,'sensitivity',base,operation='task_capability',model_source='gvs',capability_method=CONIC,
        optimal_sensitivity=dict(variable=variable,model_results=refs,steps=[step,step/2]))
    # Predict first; only then measure Native responses. Same absolute pretensions,
    # algorithm and full callback cap as the saved base Direct Native result.
    for row in contrasts:
        existing=[e for e in state(h).get('control_initializations',[]) if e['candidate']==row['candidate']
            and h.store.artifact(e['source']).get('provenance',{}).get('control_initialization')=='bounded_candidate_control_v1']
        seed=existing[0] if existing else physical_replay.seed_control(h,ControlSeedRequest(candidate=row['candidate'],method='baseline'),'p63h-'+row['label']+'-baseline')
        original=h.store.artifact(seed['source'])['trajectory']['tensions_n']
        assert original==h.store.artifact(info['baseline_source'])['trajectory']['tensions_n']
        ref,raw=native(h,'native-'+row['label'],row['candidate'],seed['source'])
        t1.append(ref);row.update(t1=ref,source=seed['source'])
        replay(h,'replay-'+row['label'],row['candidate'],raw['control_schedule_reference'])
    aggregates=[]
    for label,indices in [('full',[0,1,2]),('half',[0,3,4])]:
        ref,raw=run_analysis(h,'structure-'+label,base,operation=T2_OPERATION,model_source='mujoco',
            nonlinear_response=dict(variable=variable,unit=domain['units'],t1_results=[t1[i] for i in indices]))
        aggregates.append(ref)
    atomic_json(DEST/'h2-completed.json',dict(variable=variable,units=domain['units'],baseline=origin,step=step,
        domain=domain,sensitivity=sensitivity,contrasts=contrasts,aggregates=aggregates,
        numerical_s=state(h)['numerical_s'],ledger=h.store.remaining(),mathematical_evaluations=state(h)['mathematical_evaluations']))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=['h1','h2'],required=True)
    parser.add_argument('--variable');parser.add_argument('--step',type=float)
    args=parser.parse_args()
    h=host()
    if args.phase=='h1':h1(h)
    else:h2(h,args.variable,args.step)
