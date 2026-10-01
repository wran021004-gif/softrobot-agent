"""Explicit bounded local experiment, separate from read-only evidence inspection."""
from __future__ import annotations
from copy import deepcopy
import time
from typing import Literal
import numpy as np
from schemas.common import Contract
from schemas.platform import SessionInput
from tools.platform_store import plain
from .control_evidence import capture_snapshot,decode_plan,plan_metrics
from .gvs_trajectory import TrajectoryWorkspace


class LocalComparisonRequest(Contract):
    execution_id: str
    snapshot_id: str
    changed_factor: Literal['truncate_horizon_at_deadline']
    max_local_solves: Literal[2] = 2
    max_preparation_and_solving_s: float = 300.


def freeze_comparison(reader, request: LocalComparisonRequest):
    s=reader.resolve(request.execution_id)
    snapshots=reader.read_file(s,'control_snapshots.json',[])
    snap=next((r for r in snapshots if r['snapshot_id']==request.snapshot_id),None)
    if snap is None:raise ValueError('RECORDED_SNAPSHOT_REQUIRED_NO_RECONSTRUCTION')
    cfg=s['configuration'];recipe=cfg['policy']['controller']['parameters']['data']['recipe']
    remaining=(cfg['task']['timing']['duration_s']-snap['time_s'])/cfg['task']['timing']['control_period_s']
    if abs(remaining-round(remaining))>1e-8 or not 1<=round(remaining)<recipe['horizon']:
        raise ValueError('DEADLINE_MUST_BE_ALIGNED_INSIDE_HORIZON')
    if recipe['max_cpu_s'] is None or recipe['max_cpu_s']>30 or not 0<request.max_preparation_and_solving_s<=1200:
        raise ValueError('LOCAL_COMPARISON_BUDGET_NOT_BOUNDED')
    return dict(schema_version='1.0.0',request=plain(request),source_manifest=s['manifest'],
        ownership=dict(execution_id=request.execution_id,snapshot_id=request.snapshot_id,owner_run_id=s['owner']),
        baseline_horizon=recipe['horizon'],variant_horizon=round(remaining),
        acceptance=dict(finite_inputs=True,independent_feasibility_max_scaled=1e-5,
            deadline_error_improvement_m=.0001,complete_pair_limit_s=request.max_preparation_and_solving_s,
            max_cpu_s_per_solve=recipe['max_cpu_s'],max_iterations=recipe['max_iterations'],
            shared_evaluator='Euclidean world-tip error at official deadline, in m; speed separately in m/s',
            objectives='Different horizon objectives; never compare their scalar costs across variants',
            first_command='Report separately, never a quality gate'),
        fixed_conditions=['robot','task','projected initial state','previous applied input','retained warm prefix',
            'dynamics','residual scaling','bounds','solve budgets','selection logic'],
        classification='Two new local solves from one recorded snapshot; not a historical replay or closed-loop result')


def run_comparison(reader, request, protocol, save_artifact, record_usage):
    """Caller persists protocol/attempt before calling; every solve charged before start."""
    s=reader.resolve(request.execution_id)
    snap=next(r for r in reader.read_file(s,'control_snapshots.json',[]) if r['snapshot_id']==request.snapshot_id)
    inp=SessionInput.model_validate(s['configuration']);control=reader.read_file(s,'control_spec.json')
    baseline_recipe=inp.policy.controller.parameters.data['recipe'];start=time.perf_counter();rows=[]
    for role,horizon in [('baseline',protocol['baseline_horizon']),('variant',protocol['variant_horizon'])]:
        if time.perf_counter()-start+60>request.max_preparation_and_solving_s:raise RuntimeError('LOCAL_TIME_ALLOWANCE_EXHAUSTED')
        record_usage(role,time.perf_counter()-start)
        p=deepcopy(baseline_recipe);p['horizon']=horizon
        ws=TrajectoryWorkspace(inp.task,inp.robot,p,[*control['reference']['q0'],*([0.]*len(control['reference']['q0']))],
            control['reference']['u0'],settling=control.get('settling'))
        ws.solver.diagnostic_trace=True
        # Initial is the actual prepared warm horizon retained at this update.
        # Explicit warm uses the identical physical input prefix, then the normal
        # regeneration rule. No unavailable historical warm data is invented.
        original=snap['plans']['initial']
        warm=dict(states=deepcopy(original['states'][:horizon*p['substeps']+1]),
            tensions=deepcopy(original['tensions'][:horizon]))
        x=snap['measured_initial_state'];u=snap['previous_applied_input_n']
        if not np.isfinite(np.r_[x,u,np.asarray(warm['states']).ravel(),np.asarray(warm['tensions']).ravel()]).all():
            raise ValueError('NONFINITE_RECORDED_INPUT')
        wall=time.perf_counter();solved=ws.solve(x,u,warm=warm,elapsed_s=snap['time_s'])
        verification=ws.solver.evaluate_candidate(ws.problem,solved['result']['optimum'])
        metrics=plan_metrics(ws,np.asarray(solved['states']),np.asarray(solved['tensions']),snap['time_s'])
        full=capture_snapshot(ws,solved,snap['update_id'],snap['time_s'],solved['tensions'][0],{'gvs_projection':snap['projection']})
        ref=save_artifact(dict(source_snapshot=request.snapshot_id,role=role,configuration=s['configuration'],
            parameters=p,result=full,verification=verification))
        rows.append(dict(role=role,horizon=horizon,metrics=metrics,independent_verification=verification,
            selected_iteration=solved['diagnostics']['selected_feasible_iteration'],
            stopping_reason=solved['diagnostics']['policy_stop_reason'],raw_status=solved['diagnostics']['return_status'],
            complete_local_update_s=time.perf_counter()-wall,graph_construction_s=ws.graph_s,
            first_command_change_from_initialization_n=float(np.max(np.abs(np.asarray(solved['tensions'][0])-warm['tensions'][0]))),
            reference=ref))
    a,b=rows;improvement=a['metrics']['deadline']['position_error_m']-b['metrics']['deadline']['position_error_m']
    elapsed=time.perf_counter()-start
    gate=all(r['independent_verification']['feasible'] for r in rows) and improvement>=protocol['acceptance']['deadline_error_improvement_m'] and elapsed<=request.max_preparation_and_solving_s
    return dict(schema_version='1.0.0',protocol=protocol,rows=rows,local_gate_passed=gate,
        shared_deadline_error_improvement_m=improvement,total_preparation_solving_analysis_s=elapsed,
        new_local_solves=2,first_command_difference_n=float(np.max(np.abs(np.asarray(a['metrics']['first_input_n'])-b['metrics']['first_input_n']))),
        interpretation='One snapshot comparison only; no physical unreachability or closed-loop claim; no cross-objective scalar ranking.')
