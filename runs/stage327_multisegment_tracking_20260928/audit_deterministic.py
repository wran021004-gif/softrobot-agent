"""Audit saved public execution/evaluation/report evidence; no solves or provider calls."""
import gzip
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.platform_store import Store
from tools.state_io import atomic_json, digest
from extensions.tendon_family.tracking import reference_at

folder=Path(__file__).resolve().parent
run=folder/'deterministic';store=Store(run)
read=lambda p:json.loads(p.read_text(encoding='utf8'))
inp=read(run/'input.json');frozen=read(folder/'frozen_input.json')
assert inp==frozen
s=read(run/'summary.json');facts=s['factual_result']
receipt=read(run/'simulate_receipt.json');report=read(run/'report_receipt.json')
backend=run/'sessions'/inp['run_id']/'executions'/receipt['execution_id']/'backend'
rows=json.loads(gzip.decompress((backend/'trajectory.json.gz').read_bytes()))
observations=read(backend/'controller_observations.json')
configuration=store.artifact(facts['configuration']);effective=configuration['effective']
assert effective['task']==inp['task'] and effective['robot']==inp['robot']
assert effective['policy']['controller']==inp['policy']['controller']
evaluation=store.artifact(s['evaluation'])
assert facts['execution_id']==receipt['execution_id']==evaluation['source_execution_id']
assert store.artifact(report['output'])['detail']['execution_id']==receipt['execution_id']
assert facts['report']['reference']==report['output']
times=np.array([r['time_s'] for r in rows]);desired,velocity=reference_at(inp['task']['goal']['data'],times)
actual=np.array([r['tip_m'] for r in rows]);errors=np.linalg.norm(actual-desired,axis=1)
complete=len(times)==70 and bool(np.allclose(times,np.arange(1,71)*.01,rtol=0,atol=1e-8))
metrics={m['name']:m['value'] for m in evaluation['metrics']}
calculated=dict(max_position_error=float(max(errors)),rms_position_error=float(np.sqrt(np.mean(errors**2))),terminal_position_error=float(errors[-1]))
for key,value in calculated.items():assert np.isclose(value,metrics[key],rtol=0,atol=1e-12)
tensions=np.array([r['tension_n'] for r in rows])
limits=np.array([t['force_limit_n'] for t in inp['robot']['structure']['data']['tendons']])
prediction=[]
for o in observations:
    pred=o.get('one_step_prediction')
    if pred is None:continue
    endpoint=next((r for r in rows if abs(r['time_s']-pred['time_s'])<1e-8),None)
    if endpoint is None:continue
    prediction.append(dict(start_s=o['time_s'],end_s=pred['time_s'],
        difference_m=float(np.linalg.norm(np.array(pred['tip_position_m'])-endpoint['tip_m'])),
        applied_command_difference_n=float(np.max(abs(np.array(pred['applied_tension_n'])-endpoint['tension_n'])))))
motion=store.artifact(s['motion'])
knot=[]
for i,t in enumerate(times):
    if .38-1e-9<=t<=.42+1e-9:
        knot.append(dict(time_s=float(t),reference_m=desired[i].tolist(),actual_m=actual[i].tolist(),error_m=float(errors[i]),
            actual_tip_speed_m_s=motion[i]['tip_speed_m_s'],reference_velocity_m_s=velocity[i].tolist()))
audit=dict(complete_evaluation_grid=complete,samples=len(times),metrics_m=calculated,
    limit_m=.010,deterministic_gate_passed=complete and evaluation['validity']=='valid' and evaluation['task_success'] is True,
    global_maximum_time_s=float(times[int(np.argmax(errors))]),
    segment_diagnostics=s['tracking']['segment_diagnostics'],knot_diagnostics=knot,
    tension_range_n=[float(tensions.min()),float(tensions.max())],
    tension_bound_violation_n=float(max(0.,np.max(-tensions),np.max(tensions-limits))),
    plans={k:s[k] for k in ('updates','accepted_plans','converged_updates','hold_last_responses','solver_error_count','solver_failure_flags','maximum_plan_violation','raw_termination_counts','recovered_plans')},
    costs={**{k:s[k] for k in ('mean_update_s','deadline_misses','graph_construction_s','solver_construction_s','backend_timings_s','simulation_wall_s')},
        'sum_complete_updates_s':sum(o['update_wall_s'] for o in observations),
        'minimum_update_s':min(o['update_wall_s'] for o in observations),'maximum_update_s':max(o['update_wall_s'] for o in observations),
        'construction_scope':'Graph cost recorded once; solver construction timer includes subsequent microsecond cache lookups.',
        'knot_solver_construction_or_lookup_s':[{k:o[k] for k in ('time_s','graph_construction_s','solver_construction_s')} for o in observations if .38-1e-9<=o['time_s']<=.42+1e-9]},
    prediction=dict(aligned_intervals=len(prediction),maximum_difference_m=max(p['difference_m'] for p in prediction),
        rms_difference_m=float(np.sqrt(np.mean([p['difference_m']**2 for p in prediction]))),
        maximum_command_difference_n=max(p['applied_command_difference_n'] for p in prediction),intervals=prediction),
    bindings=dict(candidate=facts['candidate'],configuration=facts['configuration'],execution_id=receipt['execution_id'],
        simulation=receipt['output'],evaluation=s['evaluation'],report=report['output'],motion=s['motion'],
        reference_identity=digest(inp['task']['goal']),task_identity=digest(inp['task']),robot_identity=digest(inp['robot']),
        numerical_preparation=s.get('numerical_preparation'),
        candidate_analysis='Not required by deterministic public chain; no Route build or historical analysis substituted'),
    usage=dict(charged=store.remaining()['used'],controller_optimization_updates=len(observations)),
    real_time_demonstrated=s['real_time_demonstrated'],
    limitations='Sampled acceptance only: no continuous-time accuracy, actual stopping at knot, optimizer convergence, robustness or real-time claim. Prediction discrepancy does not identify a physical cause.')
atomic_json(folder/'deterministic_audit.json',audit)
print(json.dumps({k:audit[k] for k in ('deterministic_gate_passed','metrics_m','segment_diagnostics','plans','costs','usage')},indent=2))
