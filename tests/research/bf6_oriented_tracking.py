"""One frozen loaded scan, orchestrating only existing research dispatch/evidence tools."""
import json
import os
import time
from tools.research import core,analysis
from tools.research.config import ROOT
from tools.research.state import state
from tools.research_tasks import _outcome_issue,_source_issue
from tools.state_io import read,digest,atomic_json


def plan(action,**payload):
    return dict(action=action,
        hypothesis='One legal soft arm carrying the frozen rigid sensor may follow timed position and tool-axis references after bounded native control optimization.',
        expected_observation='Fresh complete independent replay passes both timed task conditions and the compiled inertial-tool binding.',
        weakening_observation='Finite search or independent replay fails any original condition or lacks complete real signals.',
        fixed_conditions='Frozen BF6 sensor task, P1, real 20 g rigid payload, zero state, fresh 0.2 N start, original physics and bounded response settings.',
        stopping_condition='One finite search and one replay, at most 151 native sequences/6 iterations; first complete independent pass SELECTs and seals.',
        interpretation='One nominal sampled loaded-scan witness or finite-search failure; no structural infeasibility, contact, hardware or robustness claim.',**payload)


def main():
    started=time.perf_counter();destination=ROOT/'runs/bf6-oriented-tracking';summary=destination/'summary.json'
    if summary.exists():
        print(json.dumps(dict(status='sealed_bf6',additional_computations=0)));return
    frozen=read(ROOT/'configs/research/bf6_sensor_oriented_tracking_freeze.json')
    generation=read(ROOT/frozen['private_generation'])
    assert digest(generation)==frozen['private_generation_identity']
    assert digest(read(ROOT/frozen['task_file']))==frozen['task_file_identity']
    host=core.prepare(ROOT/frozen['study_file'],directory=destination/'private-store')
    os.environ.update(state(host)['spec']['numerical_environment'])
    if 'freeze' not in state(host):core.bind(host)
    if state(host).get('pending'):core.recover(host)
    spec=state(host)['spec']
    assert spec['canonical_task_identity']==frozen['canonical_task_identity']
    assert spec['family_space_identity']==frozen['family_space_identity']
    candidate=core.dispatch(host,plan('generate',generation=generation),'bf6-design',origin='engineering')['result']['candidate']
    source=core.dispatch(host,plan('initialize_control',control_seed=dict(candidate=candidate,tensions_n=[[frozen['initial_tension_n']]*6])),
        'bf6-seed',origin='engineering')['result']['source']
    out=analysis.dispatch(host,dict(candidate=candidate,operation='mujoco_direct_control_v1',model_source='mujoco',
        operating_point='standardized_initial_pretension',protocol=spec['analysis_protocol'],
        control_optimization=dict(source=source,settings=frozen['search_settings'])),'bf6-native',guard=core.guard,origin='engineering_preflight')
    native=host.store.artifact(out['reference']);core.read_evidence(host,dict(reference=out['reference'],view='full'))
    row=dict(analysis=out['reference'],candidate=candidate,analysis_status=native['status'])
    if native['status']=='computed':
        raw=native['native_dynamics'];search=raw['optimization']
        row.update(native_cost=raw['cost'],callbacks=search['cost_feedback']['evaluation_callbacks'],baseline_measure=search['candidates'][0]['measure'],
            best_measure=search['best']['measure'],search_stop=search['stop_reason'],native_tool_binding=raw['rigid_tool_binding'],
            first_proxy_callback=next((i+1 for i,r in enumerate(search['candidates']) if r['measure']['signed_maximum_excess']<=0),None))
        result=core.dispatch(host,plan('physical_replay',physical_replay=dict(candidate=candidate,source=native['control_schedule_reference'])),
            'bf6-replay',origin='engineering')['result']
        core.read_evidence(host,dict(reference=result['reference'],view='full'))
        physical=host.store.artifact(result['raw_reference'])
        row.update(replay=result['reference'],execution_id=result['execution_id'],raw_reference=result['raw_reference'],
            evaluation_reference=result['evaluation_reference'],acceptance=result['acceptance'],replay_cost=physical['cost'],
            independent_tool_binding=physical['rigid_tool_binding'])
        atomic_json(destination/'progress.json',row)
        assert _outcome_issue(result['acceptance']) is None and _source_issue(result['acceptance']) is None
        if result['acceptance']['accepted']:
            core.dispatch(host,plan('select',selected_execution=result['reference'],supporting_evidence=[out['reference'],result['reference']]),'bf6-select',origin='engineering')
    if state(host)['research_status']!='stopped':
        core.dispatch(host,plan('stop',next_step='stop',supporting_evidence=[*state(host)['analysis_results'],*state(host)['physical_replays']]),'bf6-stop',origin='engineering')
    s=state(host)
    row.update(implementation=s['freeze'],protocol_identity=digest(frozen),resolved_identity=spec['resolved_identity'],
        task_identity=spec['canonical_task_identity'],accepted=bool(s.get('selected')),selected=s.get('selected'),ledger=host.store.remaining(),
        numerical_s=s['numerical_s'],driver_elapsed_s=time.perf_counter()-started)
    assert row.get('callbacks',0)<=151
    assert row.get('native_cost',{}).get('physics_steps',0)+row.get('replay_cost',{}).get('physics_steps',0)<=91200
    atomic_json(summary,row)
    print(json.dumps({k:row.get(k) for k in ('accepted','callbacks','best_measure','native_cost','replay_cost','first_proxy_callback','numerical_s','driver_elapsed_s')}),flush=True)


if __name__=='__main__':main()
