"""Exactly three reconstructed local NMPC updates from sealed saved states.

No provider request, backend rollout, parameter sweep, or retry is performed.
Full historical warm horizons were not retained. Each diagnostic therefore uses
the saved measurement/configuration/time/previous input and lets the existing
controller preparation logic regenerate a constant-input warm horizon.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'

import numpy as np

from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace
from schemas.platform import SessionInput
from tools.platform_store import Store
from tools.runtime_identity import require_softagent_runtime
from tools.state_io import atomic_json,digest


CURRENT_RUN=ROOT/'runs/stage336_manual_20261001_090616'
CURRENT_EXECUTION='494deb38d6374deb8f741e96f2430826'
CURRENT_OWNER='gvs-stage336-b3097f85c72a-fc9e6c1d6d1f4c7a'
CURRENT_CONFIGURATION='803e8fb2cda1fa2035f18c2051cb2cb83c4dabf26b13f9391c2a49e1cc1b4f5c'
HISTORICAL_RUN=ROOT/'runs/stage333_bounded_recovery_independent_lengths_20260929_114923/live'
HISTORICAL_EXECUTION='7575e2c798fa4b66a388f7e277ba51c9'
HISTORICAL_OWNER='gvs-live-f4a6655fe472-2ca2bdf3ffc6811e'
HISTORICAL_CONFIGURATION='a9e2ba04110b8417b9ef6282b0385f3f79d532810d6c43e338a5dc8d55eaf5d5'


def sha256(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()


def backend(root:Path,owner:str,execution:str)->Path:
    return root/'sessions'/owner/'executions'/execution/'backend'


CASES=(
    dict(label='current_failed_t0p00',run=CURRENT_RUN,owner=CURRENT_OWNER,
        execution=CURRENT_EXECUTION,configuration=CURRENT_CONFIGURATION,time_s=0.),
    dict(label='current_failed_t0p23',run=CURRENT_RUN,owner=CURRENT_OWNER,
        execution=CURRENT_EXECUTION,configuration=CURRENT_CONFIGURATION,time_s=.23),
    dict(label='historical_passing_t0p23',run=HISTORICAL_RUN,owner=HISTORICAL_OWNER,
        execution=HISTORICAL_EXECUTION,configuration=HISTORICAL_CONFIGURATION,time_s=.23),
)


def read_json(path:Path):return json.loads(path.read_text(encoding='utf8'))


def saved_case(spec):
    folder=backend(spec['run'],spec['owner'],spec['execution'])
    updates=read_json(folder/'nmpc_updates.json');commands=read_json(folder/'actual_commands.json')
    indices=[i for i,row in enumerate(updates) if abs(row['time_s']-spec['time_s'])<1e-9]
    if len(indices)!=1:raise ValueError('SAVED_TIMESTAMP_MISSING_OR_AMBIGUOUS: '+spec['label'])
    index=indices[0];row=updates[index]
    if row['phase']!='current_state_before_integration':raise ValueError('SAVED_PHASE_MISMATCH')
    plan=read_json(folder/'control_spec.json')
    previous=commands[index-1]['desired_tension_n'] if index else plan['reference']['u0']
    if index and abs(commands[index-1]['time_s']-(spec['time_s']-.01))>1e-9:
        raise ValueError('PREVIOUS_APPLIED_INPUT_ALIGNMENT_FAILED')
    artifact=Store(spec['run']).artifact({'artifact_id':spec['configuration'],'media_type':'application/json'})
    inp=SessionInput.model_validate(artifact['effective'])
    if inp.policy.controller.version!='6.0.0':raise ValueError('UNEXPECTED_CONTROLLER_LINEAGE')
    if plan['effective_parameters']!=inp.policy.controller.parameters.data['recipe']:
        raise ValueError('SAVED_RECIPE_MISMATCH')
    return folder,row,previous,plan,inp


def decoded_plan(workspace,vector,order):
    values=dict(zip(order,vector));steps=workspace.parameters.horizon*workspace.parameters.substeps
    states=np.array([[values[f'x/{k}/{j}']*workspace.state_scales[j]
        for j in range(2*workspace.n)] for k in range(steps+1)])
    tensions=np.array([[values[f'u/{k}/{t}'] for t in workspace.tendons]
        for k in range(workspace.parameters.horizon)])
    previous=np.array([values['previous_u/'+t] for t in workspace.tendons])
    return states,tensions,previous


def objective_components(workspace,states,tensions,previous):
    p=workspace.parameters;h=workspace.period/p.substeps;dt=workspace.period
    tolerance=p.position_error_scale_m or workspace.goal_tolerance
    values=dict(running_position=0.,running_curvature_rate=0.,running_tension=0.,
        running_tension_variation=0.,terminal_position=0.,terminal_curvature_rate=0.,
        terminal_tip_speed=0.,holding_tip_speed=0.)
    for k in range(p.horizon*p.substeps):
        state=states[k+1];tip,speed=workspace._motion(state[:workspace.n],state[workspace.n:])
        values['running_position']+=h*p.tracking_weight*float(np.sum(
            (np.asarray(tip).ravel()-workspace.target)**2/tolerance**2))
        values['running_curvature_rate']+=h*p.velocity_weight*float(np.sum(state[workspace.n:]**2))
        if p.holding_tip_speed_weight and workspace.holding_start is not None:
            node_time=(k+1)*h
            braking=max(0.,workspace.holding_start-p.holding_brake_lead_s)
            if node_time>=braking-1e-9:
                values['holding_tip_speed']+=h*p.holding_tip_speed_weight*float(
                    np.sum(np.asarray(speed).ravel()**2/p.tip_speed_scale_m_s**2))
    for k,u in enumerate(tensions):
        values['running_tension']+=dt*p.tension_weight*float(np.sum(u**2))
        values['running_tension_variation']+=dt*p.variation_weight*float(np.sum(
            (u-(previous if k==0 else tensions[k-1]))**2))
    terminal=states[-1];tip,speed=workspace._motion(terminal[:workspace.n],terminal[workspace.n:])
    values['terminal_position']=p.terminal_weight*float(np.sum(
        (np.asarray(tip).ravel()-workspace.target)**2/tolerance**2))
    values['terminal_curvature_rate']=p.terminal_velocity_weight*float(np.sum(terminal[workspace.n:]**2))
    values['terminal_tip_speed']=p.terminal_tip_speed_weight*float(np.sum(
        np.asarray(speed).ravel()**2/p.tip_speed_scale_m_s**2))
    values['total']=sum(values.values())
    return values


def run_case(spec):
    folder,row,previous,plan,inp=saved_case(spec)
    p=inp.policy.controller.parameters.data['recipe']
    if p['max_cpu_s'] is None or p['max_cpu_s']>30.:raise ValueError('NUMERICAL_SOLVE_BUDGET_EXCEEDS_30_SECONDS')
    started=time.perf_counter()
    ws=TrajectoryWorkspace(inp.task,inp.robot,p,
        [*plan['reference']['q0'],*([0.]*len(plan['reference']['q0']))],plan['reference']['u0'],
        settling=plan.get('settling'))
    graph_and_workspace_s=time.perf_counter()-started
    ws.solver.diagnostic_trace=True
    measured=row['measured_initial_state'];steps=p['horizon']*p['substeps']
    warm=dict(states=[measured]*(steps+1),tensions=[previous]*p['horizon'])
    solved=ws.solve(measured,previous,warm=deepcopy(warm),elapsed_s=spec['time_s'])
    diagnostics=deepcopy(solved['diagnostics']);order=diagnostics['variable_order']
    retained=[]
    for point in diagnostics.pop('retained_diagnostic_points'):
        states,tensions,fixed_previous=decoded_plan(ws,point.pop('vector'),order)
        components=objective_components(ws,states,tensions,fixed_previous)
        point.update(plan=dict(states=states.tolist(),tensions=tensions.tolist(),
            fixed_previous_tension_n=fixed_previous.tolist()),first_tension_command_n=tensions[0].tolist(),
            objective_components=components,objective_component_sum_difference=components['total']-point['objective'])
        retained.append(point)
    diagnostics.pop('diagnostic_plans',None)
    diagnostics.pop('constraint_values',None)
    return dict(label=spec['label'],classification='reconstructed from saved state and configuration',
        reconstruction_limit='Full historical warm starts were not retained; this is not a bitwise historical reproduction.',
        source=dict(run_root=str(spec['run'].relative_to(ROOT)),owner_run_id=spec['owner'],
            execution_id=spec['execution'],configuration_artifact_id=spec['configuration'],
            backend_path=str(folder.relative_to(ROOT)),timestamp_s=spec['time_s'],
            phase=row['phase'],saved_measurement=row['measured_initial_state'],saved_previous_applied_tension_n=previous),
        reconstruction=dict(warm_horizon='saved measured state repeated, saved previous applied tension repeated; all states then regenerated by TrajectoryWorkspace.solve using candidate dynamics',
            warm_states_before_regeneration=len(warm['states']),warm_tensions=len(warm['tensions']),
            retries=0,provider_requests=0,backend_rollouts=0),
        frozen_settings=dict(controller=inp.policy.controller.model_dump(mode='json'),
            effective_parameters=plan['effective_parameters'],objective=solved['cost'],
            integration=solved['integration'],plan_acceptance=plan['plan_acceptance']),
        timing_s=dict(graph_and_workspace_construction=graph_and_workspace_s,
            graph_assembly=ws.graph_s,warm_preparation=solved['warm_start']['preparation_s'],
            solver_construction=diagnostics['construction_s'],numerical_solve=diagnostics['solve_s'],
            validation=diagnostics['validation_s'],complete_local_update=solved['update_wall_s']),
        result=solved['result'],accepted=solved['accepted'],optimization_converged=solved['optimization_converged'],
        retained_points=retained,iteration_trace=diagnostics.pop('iteration_trace'),solver_diagnostics=diagnostics)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve()
    if output.exists():raise FileExistsError(output)
    output.mkdir(parents=True)
    runtime=require_softagent_runtime();sources=[]
    for spec in CASES:
        folder=backend(spec['run'],spec['owner'],spec['execution'])
        for name in ('nmpc_updates.json','actual_commands.json','control_spec.json','solver_configuration.json'):
            path=folder/name;sources.append(dict(path=str(path.relative_to(ROOT)),size_bytes=path.stat().st_size,sha256=sha256(path)))
        db=spec['run']/'platform.sqlite'
        sources.append(dict(path=str(db.relative_to(ROOT)),size_bytes=db.stat().st_size,sha256=sha256(db)))
    atomic_json(output/'protocol.json',dict(kind='exactly three bounded reconstructed local NMPC updates',
        cases=[{k:v for k,v in spec.items() if k not in ('run',)}|{'run':str(spec['run'].relative_to(ROOT))} for spec in CASES],
        interpreter=sys.executable,runtime=runtime,threads={k:os.environ[k] for k in
            ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')},
        limits=dict(local_solves=3,retries=0,max_numerical_solve_s_per_case=30,
            provider_requests=0,backend_rollouts=0,workers=0),sources=sources))
    records=[]
    for spec in CASES:
        record=run_case(spec);records.append(record)
        atomic_json(output/(spec['label']+'.json'),record)
        atomic_json(output/'results.json',dict(status='running',completed=len(records),records=records))
        print(spec['label'],'iterations',record['solver_diagnostics']['iterations'],
            'selected',record['result']['objective_value'],'returned violation',
            record['solver_diagnostics']['returned_iterate_constraint_violation'],flush=True)
    atomic_json(output/'results.json',dict(status='completed',completed=3,
        interpretation='Three local solves only; each reconstructed from saved state and configuration.',records=records,
        usage=dict(local_nmpc_solves=3,retries=0,provider_requests=0,backend_rollouts=0,workers=0)))
    print('completed exactly three reconstructed local NMPC diagnostics: '+str(output),flush=True)


if __name__=='__main__':main()
