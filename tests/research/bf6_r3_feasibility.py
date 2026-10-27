"""One frozen native search from BF6-R2's own independently stable control."""
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
    value.update(fixed_conditions='Original BF6 task, P1, zero physical state, real 20 g rigid tool, floor and physics; only BF6-R2 own stable G1 source; v2 acceptance.',
        stopping_condition='New allowance of one native search, at most 151 callbacks/6 iterations and one independent replay; first full pass SELECTs, otherwise STOP.')
    return value


def main():
    started=time.perf_counter();destination=ROOT/'runs/bf6-r3';summary=destination/'summary.json'
    if summary.exists():print(json.dumps(dict(status='sealed_r3',additional_computations=0)));return
    frozen=read(ROOT/'configs/research/bf6_r3_feasibility_freeze.json');prior=read(ROOT/frozen['prior_summary'])
    assert digest(prior)==frozen['prior_summary_identity'] and not prior['accepted']
    previous=Store(ROOT/frozen['prior_store']);r2=prior['rows'][-1]
    assert stable_start(r2['acceptance'],previous.artifact(r2['raw_reference']))
    assert prior['stable_source']==frozen['prior_stable_source'] and r2['replay']==frozen['prior_independent_replay']
    assert digest(read(ROOT/frozen['task_file']))==frozen['task_file_identity']
    host=core.prepare(ROOT/frozen['study_file'],directory=destination/'private-store')
    os.environ.update(state(host)['spec']['numerical_environment'])
    if 'freeze' not in state(host):core.bind(host)
    if state(host).get('pending'):core.recover(host)
    spec=state(host)['spec']
    assert spec['canonical_task_identity']==frozen['canonical_task_identity']
    assert spec['family_space_identity']==frozen['family_space_identity']
    generation=read(ROOT/frozen['private_generation']);assert digest(generation)==frozen['private_generation_identity']
    candidate=core.dispatch(host,plan('generate',generation=generation),'bf6r3-design',origin='engineering')['result']['candidate']
    assert same_robot_structure(host.store.artifact(candidate)['configuration'],previous.artifact(prior['candidate'])['configuration'])
    seed=dict(candidate=candidate,source=save(host,previous.artifact(prior['stable_source']),'bf6r2_stable_control_source'),
        parent=save(host,previous.artifact(prior['candidate']),'bf6r2_stable_source_candidate'))
    source=core.dispatch(host,plan('initialize_control',control_seed=seed),'bf6r3-seed',origin='engineering')['result']['source']
    out=analysis.dispatch(host,dict(candidate=candidate,operation='mujoco_direct_control_v1',model_source='mujoco',
        operating_point='standardized_initial_pretension',protocol=spec['analysis_protocol'],
        control_optimization=dict(source=source,settings=frozen['search_settings'])),'bf6r3-native',guard=core.guard,origin='engineering_preflight')
    native=host.store.artifact(out['reference']);core.read_evidence(host,dict(reference=out['reference'],view='full'))
    row=dict(stage='BF6-R3',analysis=out['reference'],candidate=candidate,analysis_status=native['status'],
        prior_stable_replay=frozen['prior_independent_replay'])
    if native['status']!='computed':
        progress=native.get('native_progress',{})
        row.update(native_cost=progress.get('cost'),native_callback_attempts=progress.get('cost',{}).get('rollouts'),
            completed_native_rollouts=progress.get('completed_rollouts'),failure_reason=native.get('reason'),native_progress=progress)
    else:
        raw=native['native_dynamics'];search=raw['optimization']
        row.update(native_cost=raw['cost'],callbacks=search['cost_feedback']['evaluation_callbacks'],
            baseline_measure=search['candidates'][0]['measure'],best_measure=search['best']['measure'],search_stop=search['stop_reason'],
            native_tool_binding=raw['rigid_tool_binding'],
            first_proxy_callback=next((i+1 for i,r in enumerate(search['candidates']) if r['measure']['signed_maximum_excess']<=0),None))
        result=core.dispatch(host,plan('physical_replay',physical_replay=dict(candidate=candidate,source=native['control_schedule_reference'])),
            'bf6r3-replay',origin='engineering')['result']
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
            core.dispatch(host,plan('select',selected_execution=result['reference'],supporting_evidence=[out['reference'],result['reference']]),'bf6r3-select',origin='engineering')
    if state(host)['research_status']!='stopped':
        core.dispatch(host,plan('stop',next_step='stop',supporting_evidence=[*state(host)['analysis_results'],*state(host)['physical_replays']]),'bf6r3-stop',origin='engineering')
    s=state(host)
    row.update(implementation=s['freeze'],protocol_identity=digest(frozen),resolved_identity=spec['resolved_identity'],
        task_identity=spec['canonical_task_identity'],accepted=bool(s.get('selected')),selected=s.get('selected'),
        ledger=host.store.remaining(),numerical_s=s['numerical_s'],driver_elapsed_s=time.perf_counter()-started)
    observed_callbacks=row.get('callbacks',row.get('native_callback_attempts'))
    assert observed_callbacks is None or observed_callbacks<=frozen['maximum_native_rollouts']
    costs=(row.get('native_cost') or {},row.get('replay_cost') or {})
    attempts=[c.get('physics_step_attempts') for c in costs]
    assert sum(v or 0 for v in attempts)<=frozen['maximum_physics_step_attempts']
    atomic_json(summary,row)
    print(json.dumps({k:row.get(k) for k in ('accepted','analysis_status','callbacks','best_measure','native_cost','replay_cost','failure_reason','numerical_s','driver_elapsed_s')}),flush=True)


if __name__=='__main__':main()
