"""One frozen recentered search through existing research tools; no new optimizer."""
import json
import os
import time
from tools.research import core,analysis
from tools.research.config import ROOT,same_robot_structure
from tools.research.state import state,save
from tools.platform_store import Store
from tools.research_tasks import _outcome_issue,_source_issue
from tools.state_io import read,digest,atomic_json
from tests.research.bf6_oriented_tracking import plan as bf6_plan
from tests.research.bf6_r2_stability import stable_start


def plan(action,**payload):
    value=bf6_plan(action,**payload)
    value.update(hypothesis='Recenter the bounded response search on BF6-R6 own independently stable best failure to coordinate loaded position and tool-axis errors.',
        fixed_conditions='Original BF6 task/P1/zero physical state/real 20 g inertia/floor/physics, original 30 points and thresholds, v2 acceptance. Only R6 own best failed control, no acceptance transfer.',
        stopping_condition='One new Native request, at most 151 callbacks/six response iterations and one independent replay, 91200 integration attempts; first full pass SELECTs, otherwise STOP.')
    return value


def rank(measure):
    return measure['signed_maximum_excess'],measure['sum_normalized_excess']


def main():
    started=time.perf_counter();destination=ROOT/'runs/bf6-r7';summary=destination/'summary.json'
    if summary.exists():print(json.dumps(dict(status='sealed_r7',additional_computations=0)));return
    frozen=read(ROOT/'configs/research/bf6_r7_feasibility_freeze.json');prior=read(ROOT/frozen['prior_summary'])
    assert digest(prior)==frozen['prior_summary_identity'] and not prior['accepted']
    previous=Store(ROOT/frozen['prior_store']);old_analysis=previous.artifact(prior['analysis'])
    old_raw=previous.artifact(prior['raw_reference'])
    assert previous.session('bf6-r6-expanded-feasibility-v1')['state']['research_status']=='stopped'
    assert stable_start(prior['acceptance'],old_raw) and prior['acceptance']['status']=='valid_failure'
    assert prior['analysis']==frozen['prior_analysis'] and prior['replay']==frozen['prior_independent_replay']
    assert old_analysis['control_schedule_reference']==frozen['prior_control_source']==old_raw['source_reference']
    assert digest(read(ROOT/frozen['task_file']))==frozen['task_file_identity']
    host=core.prepare(ROOT/frozen['study_file'],directory=destination/'private-store')
    os.environ.update(state(host)['spec']['numerical_environment'])
    if 'freeze' not in state(host):core.bind(host)
    if state(host).get('pending'):core.recover(host)
    spec=state(host)['spec']
    assert spec['canonical_task_identity']==frozen['canonical_task_identity']
    assert spec['family_space_identity']==frozen['family_space_identity']
    generation=read(ROOT/frozen['private_generation']);assert digest(generation)==frozen['private_generation_identity']
    candidate=core.dispatch(host,plan('generate',generation=generation),'bf6r7-design',origin='engineering')['result']['candidate']
    assert same_robot_structure(host.store.artifact(candidate)['configuration'],previous.artifact(prior['candidate'])['configuration'])
    seed=dict(candidate=candidate,source=save(host,previous.artifact(frozen['prior_control_source']),'bf6r6_best_failing_control_source'),
        parent=save(host,previous.artifact(prior['candidate']),'bf6r6_source_candidate'))
    source=core.dispatch(host,plan('initialize_control',control_seed=seed),'bf6r7-seed',origin='engineering')['result']['source']
    out=analysis.dispatch(host,dict(candidate=candidate,operation='mujoco_direct_control_v1',model_source='mujoco',
        operating_point='standardized_initial_pretension',protocol=spec['analysis_protocol'],
        control_optimization=dict(source=source,settings=frozen['search_settings'])),'bf6r7-native',guard=core.guard,origin='engineering_preflight')
    native=host.store.artifact(out['reference']);core.read_evidence(host,dict(reference=out['reference'],view='full'))
    row=dict(stage='BF6-R7',analysis=out['reference'],candidate=candidate,analysis_status=native['status'],
        prior_independent_replay=frozen['prior_independent_replay'],prior_control_source=frozen['prior_control_source'])
    if native['status']!='computed':
        progress=native.get('native_progress',{})
        row.update(native_cost=progress.get('cost'),native_callback_attempts=progress.get('cost',{}).get('rollouts'),
            completed_native_rollouts=progress.get('completed_rollouts'),failure_reason=native.get('reason'),native_progress=progress,
            replay_skipped_reason='Native returned no complete new optimized schedule')
    else:
        raw=native['native_dynamics'];search=raw['optimization'];baseline=search['candidates'][0];best=search['best']
        improved=rank(best['measure'])<rank(baseline['measure']) and best['sequence_hash']!=baseline['sequence_hash']
        row.update(native_cost=raw['cost'],callbacks=search['cost_feedback']['evaluation_callbacks'],
            baseline_measure=baseline['measure'],best_measure=best['measure'],search_stop=search['stop_reason'],
            native_tool_binding=raw['rigid_tool_binding'],new_complete_better_control=improved,
            first_proxy_callback=next((i+1 for i,r in enumerate(search['candidates']) if r['measure']['signed_maximum_excess']<=0),None))
        if improved:
            result=core.dispatch(host,plan('physical_replay',physical_replay=dict(candidate=candidate,source=native['control_schedule_reference'])),
                'bf6r7-replay',origin='engineering')['result']
            core.read_evidence(host,dict(reference=result['reference'],view='full'))
            physical=host.store.artifact(result['raw_reference']);diagnostic=physical.get('numerical_failure',{})
            cost=physical.get('cost') or dict(physics_steps_lower_bound=physical.get('physics_steps_lower_bound',0),
                physics_step_attempts=diagnostic.get('attempted_steps'),failed_call_internal_progress='unknown')
            row.update(replay=result['reference'],execution_id=result['execution_id'],raw_reference=result['raw_reference'],
                evaluation_reference=result['evaluation_reference'],acceptance=result['acceptance'],replay_cost=cost,
                independent_tool_binding=physical.get('rigid_tool_binding'),environment_contact=physical.get('environment_contact'),
                stable_start=stable_start(result['acceptance'],physical),source_issue=_source_issue(result['acceptance']),
                outcome_issue=_outcome_issue(result['acceptance']))
            atomic_json(destination/'progress.json',row)
            assert row['source_issue'] is None
            if result['acceptance']['accepted']:
                core.dispatch(host,plan('select',selected_execution=result['reference'],supporting_evidence=[out['reference'],result['reference']]),'bf6r7-select',origin='engineering')
        else:row['replay_skipped_reason']='No strictly better new complete control; no duplicate replay of original R6 control'
    if state(host)['research_status']!='stopped':
        core.dispatch(host,plan('stop',next_step='stop',supporting_evidence=[*state(host)['analysis_results'],*state(host)['physical_replays']]),'bf6r7-stop',origin='engineering')
    s=state(host)
    row.update(implementation=s['freeze'],protocol_identity=digest(frozen),resolved_identity=spec['resolved_identity'],
        task_identity=spec['canonical_task_identity'],accepted=bool(s.get('selected')),selected=s.get('selected'),
        ledger=host.store.remaining(),numerical_s=s['numerical_s'],driver_elapsed_s=time.perf_counter()-started)
    callbacks=row.get('callbacks',row.get('native_callback_attempts'))
    assert callbacks is None or callbacks<=frozen['maximum_native_rollouts']
    costs=(row.get('native_cost') or {},row.get('replay_cost') or {})
    assert sum(cost.get('physics_step_attempts') or 0 for cost in costs)<=frozen['maximum_physics_step_attempts']
    assert len(s['analysis_results'])<=1 and len(s['physical_replays'])<=1
    atomic_json(summary,row)
    print(json.dumps({k:row.get(k) for k in ('accepted','analysis_status','callbacks','best_measure','native_cost','replay_cost','failure_reason','numerical_s','driver_elapsed_s')}),flush=True)


if __name__=='__main__':main()
