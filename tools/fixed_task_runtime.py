"""Metadata and horizon-stratified costing; never dispatch numerical experiments.

Kept outside the frozen controller implementation so an active execution and its
fresh repetition retain identical scientific and runtime configuration bindings.
"""
import argparse
from copy import deepcopy
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

from tools.research import core as core
from tools.research import numerics as numerics
from tools.fixed_task_milestone import HISTORY, host
from tools.state_io import digest


def stratified_cost(historical, measured, maximum_horizon, *, overhead_s=100., margin=1.35):
    """Use separate measured upper ratios for full and shortened horizons.

    No historical speedup is credited. Cold first-update cost is a separate
    floor, rather than a ratio propagated over all 35 updates. Sparse shortened
    horizon measurements conservatively share their largest observed ratio.
    """
    baseline={round(o['time_s'],9):o for o in historical}
    early=[];late=[];cold=[]
    for o in measured:
        prior=baseline.get(round(o['time_s'],9))
        if not prior or prior['effective_horizon']!=o['effective_horizon']:
            raise ValueError('MATCHED_ABSOLUTE_TIME_AND_EFFECTIVE_HORIZON_REQUIRED')
        if o['time_s']==0.:
            cold.append(o['update_wall_s']);continue
        ratio=o['update_wall_s']/prior['update_wall_s']
        (early if o['effective_horizon']==maximum_horizon else late).append(ratio)
    if not early:raise ValueError('MAXIMUM_HORIZON_TIMING_REQUIRED')
    early_ratio=max([1.,*early]);late_ratio=max([1.,*late])
    rows=[]
    for o in historical:
        ratio=early_ratio if o['effective_horizon']==maximum_horizon else late_ratio
        seconds=o['update_wall_s']*ratio
        if o['time_s']==0.:seconds=max([seconds,*cold])
        rows.append(dict(time_s=o['time_s'],effective_horizon=o['effective_horizon'],predicted_s=seconds))
    # Evidence capture, scene/setup and first workspace construction uncertainty.
    predicted=sum(r['predicted_s'] for r in rows)+60.
    simulation=math.ceil(predicted*margin)
    return dict(predicted_simulation_s=predicted,simulation_watchdog_s=simulation,
        total_watchdog_s=simulation+overhead_s,safety_margin=margin,
        full_horizon_ratio=early_ratio,shortened_horizon_ratio=late_ratio,
        full_horizon_updates=sum(r['effective_horizon']==maximum_horizon for r in rows),
        shortened_horizon_updates=sum(r['effective_horizon']<maximum_horizon for r in rows),
        cold_first_update_floor_s=max(cold,default=0.),per_update_estimates=rows)


def record_cost(h, value, *, apply=False):
    s=core.state(h)
    if apply and s['pending']:
        raise ValueError('SETTLE_ACTIVE_EXECUTION_BEFORE_CHANGING_ITS_RESERVATION')
    ref=core.save(h,value,'horizon_stratified_execution_cost_estimate')
    changes=dict(prospective_execution_cost_estimate=ref)
    if apply:
        changes.update(execution_cost_estimate=value,cost_estimates=[*s.get('cost_estimates',[]),ref])
    core.update(h,**changes)
    return dict(reference=ref,applied=apply,estimate=value)


def estimate(h, *, apply=False):
    s=core.state(h);recipe=s['profile']['recipe']
    old_summary=core.read(core.ROOT/HISTORY/'scientific_summary.json')
    old=next(r for r in old_summary['physical'] if r['execution_id']==s['repair_history']['source_execution'])
    source=numerics.execution_source(old,HISTORY)
    historical=numerics.archived(HISTORY,source['files']['controller_observations.json'])
    measured=[];sources=[]
    # Exact current-path local checks, with actual deadline horizons. The earlier
    # accidental extended-horizon diagnostic is retained but excluded here.
    for ref in s.get('diagnostics',[]):
        for row in h.store.artifact(ref)['rows']:
            request=core.read(h.store.root/'local_diagnostics'/row['execution_id']/'input.json')
            if request['mode']!='research_current' or row.get('status'):continue
            local_recipe=deepcopy(request['configuration']['policy']['controller']['parameters']['data']['recipe'])
            local_recipe.update(request['current_recipe']);local_recipe['max_iterations']=request['iteration_cap']
            environment=request.get('numerical_environment',dict(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1'))
            if local_recipe!=recipe or environment!=s['spec']['numerical_environment']:continue
            index=row['source_update_id'];prior=historical[index]
            actual=row.get('actual_workspace_output',{}).get('complete_update',{}).get('effective_horizon',request['record']['effective_horizon'])
            if actual!=prior['effective_horizon']:continue
            measured.append(dict(time_s=prior['time_s'],effective_horizon=actual,update_wall_s=row['charged_numerical_s']))
            sources.append(dict(reference=ref,source='matched_local',update=index))
    # Complete executions and the live execution supply existing real wall times;
    # no new local or performance solve is dispatched for this estimate.
    for ref in s['results']:
        row=h.store.artifact(ref)
        if row['profile_identity']!=s['profile']['identity'] or row['status']!='evaluated':continue
        from extensions.tendon_family.control_evidence import ControlEvidence
        reader=ControlEvidence(h.store);src=reader.resolve(row['execution_id'])
        measured.extend(reader.read_file(src,'controller_observations.json',[]))
        sources.append(dict(reference=ref,source='complete_frozen_execution'))
    if s['pending']:
        p=s['pending']
        if p['profile_identity']!=s['profile']['identity']:raise ValueError('ACTIVE_PROFILE_MISMATCH')
        for path in (h.store.root/'sessions'/p['owner']/'executions').glob('*/backend/nmpc_updates.json'):
            measured.extend(core.read(path))
            sources.append(dict(path=str(path.relative_to(core.ROOT)),source='live_frozen_execution',partial=True))
    overhead=sum(v for k,v in s['spec']['execution_allowances'].items() if k!='simulation_s')
    value=stratified_cost(historical,measured,recipe['horizon'],overhead_s=overhead)
    value.update(recipe_identity=digest(recipe),recipe=deepcopy(recipe),science_hashes=s['profile']['science_hashes'],
        numerical_environment=s['spec']['numerical_environment'],profile_identity=s['profile']['identity'],
        timing_sources=sources,estimated_unix=time.time(),
        method='Separate full-horizon and deadline-shortened timing strata; measured upper ratios with no credited speedup; cold first update floor; 60s setup/evidence and 35% margin',
        uncertainty='Saved-state timings and current execution do not establish universal performance. Prior unset-environment abort retained, excluded from matching-runtime calibration; its environment is not a proven cause.',
        estimator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    return record_cost(h,value,apply=apply)


def runtime_metadata():
    """Read actual library thread counters in this identical-startup metadata process.

    No optimization, integration, simulation or throughput measurement is run.
    A metadata process is explicitly distinguished from live process observation.
    """
    import numpy as np
    import scipy
    import scipy.linalg
    import casadi as ca
    import mujoco
    ca.load_nlpsol('ipopt')
    candidates=[*Path(np.__file__).resolve().parents[1].glob('numpy.libs/*openblas*.dll'),
        *Path(scipy.__file__).resolve().parents[1].glob('scipy.libs/*openblas*.dll'),
        *Path(ca.__file__).resolve().parent.glob('*openblas*.dll')]
    libraries=[]
    for path in candidates:
        dll=ctypes.CDLL(str(path));count=None;symbol=None
        for name in ('scipy_openblas_get_num_threads64_','scipy_openblas_get_num_threads','openblas_get_num_threads','openblas_get_num_threads64_'):
            try:function=getattr(dll,name)
            except AttributeError:continue
            function.restype=ctypes.c_int;function.argtypes=[];count=function();symbol=name;break
        libraries.append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),thread_count=count,counter_symbol=symbol))
    return dict(observed_unix=time.time(),pid=os.getpid(),interpreter=sys.executable,
        environment={k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')},
        versions=dict(python=sys.version.split()[0],numpy=np.__version__,scipy=scipy.__version__,casadi=ca.__version__,mujoco=mujoco.__version__),
        libraries=libraries,scope='Actual library counters in a metadata-only process started under the frozen environment. Live process DLL paths and OS threads are separately observed; no injection or causal performance claim.')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['estimate','metadata'])
    parser.add_argument('--apply',action='store_true');args=parser.parse_args();h=host()
    if args.command=='metadata':
        value=runtime_metadata();ref=core.save(h,value,'frozen_runtime_metadata')
        core.update(h,runtime_metadata=ref);output=dict(reference=ref,**value)
    else:
        output=estimate(h,apply=args.apply)
        if args.apply:output['admission']=core.capacity(h)
        output['estimate']={k:v for k,v in output['estimate'].items() if k not in ('recipe','science_hashes','per_update_estimates')}
    print(json.dumps(output,ensure_ascii=True))


if __name__=='__main__':main()
