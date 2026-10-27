"""Spend only the frozen BF6 group's unused independent replay; no new optimization."""
import json
import os
import time
from tools.research import core
from tools.research.config import ROOT
from tools.research.state import state,save
from tools.platform_store import Store
from tools.state_io import read,digest,atomic_json
from tools.research_tasks import _outcome_issue,_source_issue
from tests.research.bf6_oriented_tracking import plan as original_plan


def plan(action,**payload):
    value=original_plan(action,**payload)
    value.update(stopping_condition='Consume only the one original unused independent replay slot, without any native analysis or input changes; read and SELECT/STOP.',
        interpretation='Independent validation of the original failed baseline, preserving the 226-step Native contact failure and all costs.')
    return value


def main():
    started=time.perf_counter();destination=ROOT/'runs/bf6-oriented-tracking-validation';summary=destination/'summary.json'
    if summary.exists():print(json.dumps(dict(status='sealed_validation',additional_computations=0)));return
    frozen=read(ROOT/'configs/research/bf6_sensor_validation_freeze.json')
    prior=read(ROOT/frozen['source_summary']);previous=Store(ROOT/frozen['source_store'])
    previous_state=previous.session(frozen['source_study'])['state']
    assert previous_state['research_status']=='stopped' and not previous_state['physical_replays']
    host=core.prepare(ROOT/frozen['study_file'],directory=destination/'private-store')
    os.environ.update(state(host)['spec']['numerical_environment'])
    if 'freeze' not in state(host):core.bind(host)
    if state(host).get('pending'):core.recover(host)
    generation=read(ROOT/frozen['private_generation']);assert digest(generation)==frozen['private_generation_identity']
    candidate=core.dispatch(host,plan('generate',generation=generation),'bf6v-design',origin='engineering')['result']['candidate']
    old_seed=previous_state['control_initializations'][0]
    source=core.dispatch(host,plan('initialize_control',control_seed=dict(candidate=candidate,
        source=save(host,previous.artifact(old_seed['source']),'original_baseline_source'),
        parent=save(host,previous.artifact(old_seed['candidate']),'original_baseline_candidate'))),'bf6v-seed',origin='engineering')['result']['source']
    result=core.dispatch(host,plan('physical_replay',physical_replay=dict(candidate=candidate,source=source)),
        'bf6v-replay',origin='engineering')['result']
    core.read_evidence(host,dict(reference=result['reference'],view='full'))
    assert _outcome_issue(result['acceptance']) is None and _source_issue(result['acceptance']) is None
    if result['acceptance']['accepted']:
        core.dispatch(host,plan('select',selected_execution=result['reference'],supporting_evidence=[result['reference']]),'bf6v-select',origin='engineering')
    else:core.dispatch(host,plan('stop',next_step='stop',supporting_evidence=[result['reference']]),'bf6v-stop',origin='engineering')
    physical=host.store.artifact(result['raw_reference']);native=previous.artifact(prior['analysis'])
    row=dict(implementation=state(host)['freeze'],protocol_identity=digest(frozen),resolved_identity=state(host)['spec']['resolved_identity'],
        accepted=bool(state(host).get('selected')),replay=result['reference'],raw_reference=result['raw_reference'],
        evaluation_reference=result['evaluation_reference'],acceptance=result['acceptance'],execution_id=result['execution_id'],
        independent_tool_binding=physical['rigid_tool_binding'],environment_contact=physical['environment_contact'],replay_cost=physical['cost'],
        prior_summary=frozen['source_summary'],prior_analysis=prior['analysis'],prior_analysis_status=native['status'],prior_reason=native.get('reason'),
        prior_native_cost=native['native_progress']['cost'],prior_numerical_s=prior['numerical_s'],numerical_s=state(host)['numerical_s'],
        ledger=host.store.remaining(),driver_elapsed_s=time.perf_counter()-started)
    assert row['prior_native_cost']['physics_steps']+row['replay_cost']['physics_steps']<=826
    atomic_json(summary,row)
    print(json.dumps({k:row[k] for k in ('accepted','acceptance','environment_contact','replay_cost','prior_native_cost','numerical_s','driver_elapsed_s')}),flush=True)


if __name__=='__main__':main()
