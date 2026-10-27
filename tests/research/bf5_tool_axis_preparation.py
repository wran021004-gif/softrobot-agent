"""One frozen tool-axis task and finite native search, using original execution owners."""
import json
import os
import time
import argparse
from tools.research import core,analysis
from tools.research.config import ROOT
from tools.research.state import state,save
from tools.platform_store import Store
from tools.research_tasks import _outcome_issue,_source_issue
from tools.state_io import read,digest,atomic_json
from tests.research.bf4_tracking_s2 import plan as comparison_plan


def plan(action,**payload):
    value=comparison_plan(action,**payload)
    value.update(hypothesis='One legal soft arm may independently satisfy world position and directed tool-axis constraints after finite native control optimization.',
        fixed_conditions='Frozen BF5 position/tool-axis task, P1 structure, zero physical state, candidate-bound initialization declared in the owning precheck/continuation Study, 51 callbacks/2 iterations and one full replay per declared stage.',
        stopping_condition='Stop after the single independent replay; no threshold relaxation, structural search, restarts or score polishing.',
        interpretation='A complete independent pass is one same-model position/tool-axis witness; finite failure leaves dynamic feasibility unresolved.')
    return value


def main(continuation=False):
    stage='bf5-tool-axis-continuation' if continuation else 'bf5-tool-axis'
    started=time.perf_counter();destination=ROOT/'runs'/stage;summary=destination/'summary.json'
    if summary.exists():
        print(json.dumps(dict(status='sealed_bf5',additional_computations=0)));return
    protocol='bf5_tool_axis_continuation_freeze.json' if continuation else 'bf5_tool_axis_freeze.json'
    frozen=read(ROOT/'configs/research'/protocol);generation=read(ROOT/frozen['private_generation'])
    assert digest(generation)==frozen['private_generation_identity']
    assert digest(read(ROOT/frozen['task_file']))==frozen['task_file_identity']
    host=core.prepare(ROOT/frozen['study_file'],directory=destination/'private-store')
    os.environ.update(state(host)['spec']['numerical_environment'])
    if 'freeze' not in state(host):core.bind(host)
    if state(host).get('pending'):core.recover(host)
    candidate=core.dispatch(host,plan('generate',generation=generation),'bf5-design',origin='engineering')['result']['candidate']
    seed=dict(candidate=candidate,tensions_n=[[frozen['initial_tension_n']]*6])
    prior=None
    if continuation:
        prior=read(ROOT/'runs/bf5-tool-axis/summary.json')
        previous=Store(ROOT/'runs/bf5-tool-axis/private-store')
        assert prior['acceptance']['status']=='valid_failure' and not prior['accepted']
        original=previous.artifact(prior['analysis'])
        seed=dict(candidate=candidate,source=save(host,previous.artifact(original['control_schedule_reference']),'prior_failing_control_source'),
            parent=save(host,previous.artifact(prior['candidate']),'prior_source_candidate'))
    source=core.dispatch(host,plan('initialize_control',control_seed=seed),
        'bf5-seed',origin='engineering')['result']['source']
    spec=state(host)['spec']
    out=analysis.dispatch(host,dict(candidate=candidate,operation='mujoco_direct_control_v1',model_source='mujoco',
        operating_point='standardized_initial_pretension',protocol=spec['analysis_protocol'],
        control_optimization=dict(source=source,settings=frozen['search_settings'])),'bf5-native',guard=core.guard,origin='engineering_preflight')
    native=host.store.artifact(out['reference']);core.read_evidence(host,dict(reference=out['reference'],view='full'))
    row=dict(analysis=out['reference'],candidate=candidate,analysis_status=native['status'])
    if native['status']=='computed':
        raw=native['native_dynamics'];search=raw['optimization']
        row.update(native_cost=raw['cost'],callbacks=search['cost_feedback']['evaluation_callbacks'],baseline_measure=search['candidates'][0]['measure'],
            best_measure=search['best']['measure'],search_stop=search['stop_reason'])
        result=core.dispatch(host,plan('physical_replay',physical_replay=dict(candidate=candidate,source=native['control_schedule_reference'])),
            'bf5-replay',origin='engineering')['result']
        core.read_evidence(host,dict(reference=result['reference'],view='full'))
        row.update(replay=result['reference'],execution_id=result['execution_id'],raw_reference=result['raw_reference'],
            evaluation_reference=result['evaluation_reference'],acceptance=result['acceptance'],replay_cost=host.store.artifact(result['raw_reference'])['cost'])
        assert _outcome_issue(result['acceptance']) is None and _source_issue(result['acceptance']) is None
        if result['acceptance']['accepted']:
            core.dispatch(host,plan('select',selected_execution=result['reference'],supporting_evidence=[out['reference'],result['reference']]),'bf5-select',origin='engineering')
    if state(host)['research_status']!='stopped':
        core.dispatch(host,plan('stop',next_step='stop',supporting_evidence=[*state(host)['analysis_results'],*state(host)['physical_replays']]),'bf5-stop',origin='engineering')
    s=state(host)
    row.update(implementation=s['freeze'],protocol_identity=digest(frozen),resolved_identity=spec['resolved_identity'],
        task_identity=spec['canonical_task_identity'],accepted=bool(s.get('selected')),selected=s.get('selected'),ledger=host.store.remaining(),
        numerical_s=s['numerical_s'],driver_elapsed_s=time.perf_counter()-started,domain_audit=read(ROOT/frozen['domain_audit']))
    if prior:row.update(prior_stage_summary='runs/bf5-tool-axis/summary.json',prior_stage_analysis=prior['analysis'],
        prior_native_cost=prior['native_cost'],prior_replay_cost=prior['replay_cost'],prior_numerical_s=prior['numerical_s'])
    assert row.get('callbacks',0)<=51
    assert row.get('native_cost',{}).get('physics_steps',0)+row.get('replay_cost',{}).get('physics_steps',0)<=31200
    atomic_json(summary,row)
    print(json.dumps({k:row.get(k) for k in ('accepted','callbacks','best_measure','native_cost','replay_cost','numerical_s','driver_elapsed_s')}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--continuation',action='store_true')
    main(parser.parse_args().continuation)
