"""Read-only audit of the one public confirmation; no solves or provider calls."""
import gzip
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
from tools.platform_store import Store
from tools.state_io import digest
from extensions.tendon_family.tracking import reference_at

folder=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent
run=folder/'confirmation'
summary=json.loads((run/'summary.json').read_text())
store=Store(run)
inp=json.loads((run/'input.json').read_text())
original=json.loads((ROOT/'runs/stage324_time_reference_tracking_20260928/frozen_input.json').read_text())
assert {k:v for k,v in inp.items() if k!='run_id'}=={k:v for k,v in original.items() if k!='run_id'}
receipt=json.loads((run/'simulate_receipt.json').read_text())
backend=run/'sessions'/inp['run_id']/'executions'/receipt['execution_id']/'backend'
rows=json.loads(gzip.decompress((backend/'trajectory.json.gz').read_bytes()))
observations=json.loads((backend/'controller_observations.json').read_text())
facts=summary['factual_result']
configuration=store.artifact(facts['configuration'])
effective=configuration['effective']
assert effective['task']==inp['task'] and effective['robot']==inp['robot']
assert effective['policy']['controller']==inp['policy']['controller']
evaluation=store.artifact(summary['evaluation'])
report=json.loads((run/'report_receipt.json').read_text())
assert facts['execution_id']==receipt['execution_id']==evaluation['source_execution_id']
assert store.artifact(report['output'])['detail']['execution_id']==receipt['execution_id']
assert facts['report']['reference']==report['output']
times=np.asarray([r['time_s'] for r in rows])
positions,_=reference_at(inp['task']['goal']['data'],times)
errors=np.linalg.norm(np.asarray([r['tip_m'] for r in rows])-positions,axis=1)
limits=np.asarray([t['force_limit_n'] for t in inp['robot']['structure']['data']['tendons']])
tensions=np.asarray([r['tension_n'] for r in rows])
prediction=[]
for observation in observations:
    pred=observation.get('one_step_prediction')
    if pred is None:continue
    endpoint=next((r for r in rows if abs(r['time_s']-pred['time_s'])<1e-8),None)
    if endpoint is None:continue
    prediction.append(dict(start_s=observation['time_s'],end_s=pred['time_s'],
        position_difference_m=float(np.linalg.norm(np.asarray(pred['tip_position_m'])-endpoint['tip_m'])),
        applied_command_difference_n=float(np.max(abs(np.asarray(pred['applied_tension_n'])-endpoint['tension_n'])))))
violations=[o['optimization_constraint_violation'] for o in observations if o.get('optimization_constraint_violation') is not None]
complete_grid=len(times)==40 and bool(np.allclose(times,np.arange(1,41)*.01,rtol=0,atol=1e-8))
sampled_bounds=float(max(0.,np.max(-tensions),np.max(tensions-limits)))
maximum=float(np.max(errors))
assert np.isclose(maximum,summary['maximum_error_m'],rtol=0,atol=1e-12)
checks=dict(complete_evaluation_grid=complete_grid,samples=len(times),maximum_position_error_m=maximum,
    rms_position_error_m=float(np.sqrt(np.mean(errors**2))),terminal_position_error_m=float(errors[-1]),
    limit_m=.01,task_accepted=summary['official_task_success'],valid_complete_execution=summary['valid_complete_execution'],
    sampled_tension_bound_violation_n=sampled_bounds,
    accepted_plans=summary['accepted_plans'],converged_updates=summary['converged_updates'],
    hold_last_responses=summary['hold_last_responses'],solver_errors=summary['solver_error_count'],
    solver_failure_flags=summary['solver_failure_flags'],deadline_misses=summary['deadline_misses'],
    independent_plan_checks=dict(source='Production independent objective/constraint reevaluation and recovery validation, retained per update',
        available=len(violations),maximum_scaled_residual=max(violations),threshold=1e-5,
        all_passed=len(violations)==len(observations) and max(violations)<=1e-5,
        limitation='Full-horizon plans were not exported by the public backend. Original-graph cross-check covers the six saved-state plans; no claim of a second full-run plan replay.'),
    costs=dict(mean_complete_update_s=summary['mean_update_s'],sum_complete_updates_s=sum(o['update_wall_s'] for o in observations),
        minimum_update_s=min(o['update_wall_s'] for o in observations),maximum_update_s=max(o['update_wall_s'] for o in observations),
        mean_state_preparation_s=float(np.mean([o['state_preparation_s'] for o in observations])),
        charged_simulation_s=summary['simulation_wall_s'],backend_timings_s=summary['backend_timings_s'],
        scope='Backend current measurement/geometry, projection, command preparation, solver, recovery/validation, conversion, prediction and observation; per-update disk evidence serialization outside controller cost and inside backend total'),
    prediction=dict(aligned_intervals=len(prediction),maximum_difference_m=max(p['position_difference_m'] for p in prediction),
        rms_difference_m=float(np.sqrt(np.mean([p['position_difference_m']**2 for p in prediction]))),
        maximum_command_difference_n=max(p['applied_command_difference_n'] for p in prediction),rows=prediction,
        interpretation='Endpoint prediction/execution disagreement under the command applied over that interval; does not isolate a physical cause'),
    bindings=dict(candidate=facts['candidate'],configuration=facts['configuration'],execution_id=receipt['execution_id'],
        simulation=receipt['output'],evaluation=summary['evaluation'],report=report['output'],
        reference_identity=digest(inp['task']['goal']),task_identity=digest(inp['task']),robot_identity=digest(inp['robot']),
        numerical_preparation=summary.get('numerical_preparation'),
        candidate_analysis=dict(required=False,invoked=False,reason='Existing deterministic simulation/evaluation/report entry has no Route owned-build analysis prerequisite. No historical candidate analysis was substituted.'),
        frozen_input_change='Only run_id changed for new session/authorization identity; task, robot, policy and all numerical settings exactly equal'),
    usage=dict(provider_requests=store.remaining()['used']['model_calls'],backend_rollouts=store.remaining()['used']['backend_solves'],
        local_saved_state_optimization_solves=6,full_run_controller_updates=len(observations)),real_time_demonstrated=summary['real_time_demonstrated'])
(folder/'confirmation_audit.json').write_text(json.dumps(checks,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in checks.items() if k not in ('bindings','prediction')},indent=2))
