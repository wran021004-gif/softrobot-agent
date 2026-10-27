"""Two frozen initialization hypotheses through existing research tools; no optimizer."""
import json
import os
import time
from tools.research import core
from tools.research.config import ROOT,same_robot_structure
from tools.research.state import state
from tools.research_tasks import _outcome_issue,_source_issue
from tools.state_io import read,digest,atomic_json
from tests.research.bf6_oriented_tracking import plan as bf6_plan


def plan(action,**payload):
    value=bf6_plan(action,**payload)
    value.update(hypothesis='A bounded gravity-opposing tendon bias may provide a complete contact-free BF6 control start without changing its model.',
        stopping_condition='At most two frozen initializations; first stable start ends R2, first independent original-task pass SELECTs immediately.',
        interpretation='Complete numerically valid contact-free initialization is separate from original-task position and axis acceptance.')
    return value


def stable_start(acceptance,raw):
    required=('evaluation_validity','execution_complete','solver_errors','force_bounds','tool_axis_sampling','rigid_tool_binding','no_environment_contact')
    return bool(acceptance['protocol_id']=='offline_oriented_tracking_v2'
        and _source_issue(acceptance) is None and _outcome_issue(acceptance) is None
        and raw.get('status')=='completed' and raw.get('physics_steps')==600
        and raw.get('physics_step_attempts')==600
        and all(acceptance['components'].get(k,{}).get('passed') is True for k in required))


def main():
    started=time.perf_counter();destination=ROOT/'runs/bf6-r2';summary=destination/'summary.json'
    if summary.exists():print(json.dumps(dict(status='sealed_r2',additional_computations=0)));return
    frozen=read(ROOT/'configs/research/bf6_r2_stability_freeze.json');seeds=read(ROOT/frozen['private_initializations'])
    assert digest(seeds)==frozen['private_initializations_identity']
    assert digest(read(ROOT/frozen['task_file']))==frozen['task_file_identity']
    host=core.prepare(ROOT/frozen['study_file'],directory=destination/'private-store')
    os.environ.update(state(host)['spec']['numerical_environment'])
    if 'freeze' not in state(host):core.bind(host)
    if state(host).get('pending'):core.recover(host)
    spec=state(host)['spec']
    assert spec['canonical_task_identity']==frozen['canonical_task_identity']
    assert spec['family_space_identity']==frozen['family_space_identity']
    request=read(ROOT/frozen['private_generation']);assert digest(request)==frozen['private_generation_identity']
    candidate=core.dispatch(host,plan('generate',generation=request),'bf6r2-design',origin='engineering')['result']['candidate']
    # Compare the frozen robot bytes, not a transferred acceptance or historical control.
    from tools.platform_store import Store
    old=read(ROOT/'runs/bf6-oriented-tracking/summary.json');previous=Store(ROOT/'runs/bf6-oriented-tracking/private-store')
    assert same_robot_structure(host.store.artifact(candidate)['configuration'],previous.artifact(old['candidate'])['configuration'])
    rows=[];chosen=None
    for seed in seeds:
        label=seed['label'];key='bf6r2-'+label
        source=core.dispatch(host,plan('initialize_control',control_seed=dict(candidate=candidate,tensions_n=seed['tensions_n'])),
            key+'-seed',origin='engineering')['result']['source']
        result=core.dispatch(host,plan('physical_replay',physical_replay=dict(candidate=candidate,source=source)),
            key+'-replay',origin='engineering')['result']
        core.read_evidence(host,dict(reference=result['reference'],view='full'))
        raw=host.store.artifact(result['raw_reference']);a=result['acceptance'];diagnostic=raw.get('numerical_failure',{})
        cost=raw.get('cost') or dict(model_builds=1 if diagnostic else None,
            physics_steps_lower_bound=raw.get('physics_steps_lower_bound',0),physics_step_attempts=diagnostic.get('attempted_steps'),
            failed_call_internal_progress='unknown',accounting='Partial receipt only; no complete rollout inferred')
        row=dict(initialization=label,source=source,replay=result['reference'],raw_reference=result['raw_reference'],
            evaluation_reference=result['evaluation_reference'],execution_id=result['execution_id'],acceptance=a,
            stable_start=stable_start(a,raw),cost=cost,numerical_s=result['charged_numerical_s'],
            environment_contact=raw.get('environment_contact'),rigid_tool_binding=raw.get('rigid_tool_binding'),
            failure=raw.get('reason') or raw.get('failure'),outcome_issue=_outcome_issue(a),source_issue=_source_issue(a))
        rows.append(row);atomic_json(destination/'progress.json',dict(rows=rows,ledger=host.store.remaining()))
        assert row['source_issue'] is None
        print(json.dumps(dict(initialization=label,status=a['status'],stable_start=row['stable_start'],cost=cost)),flush=True)
        if a['accepted']:
            core.dispatch(host,plan('select',selected_execution=result['reference'],supporting_evidence=[r['replay'] for r in rows]),key+'-select',origin='engineering')
        if row['stable_start']:
            chosen=row;break
    if state(host)['research_status']!='stopped':
        core.dispatch(host,plan('stop',next_step='stop',supporting_evidence=state(host)['physical_replays']),'bf6r2-stop',origin='engineering')
    s=state(host)
    attempts=[r['cost'].get('physics_step_attempts') for r in rows]
    assert len(rows)<=2 and all(v is None or v<=600 for v in attempts)
    out=dict(stage='BF6-R2',implementation=s['freeze'],protocol_identity=digest(frozen),resolved_identity=spec['resolved_identity'],
        candidate=candidate,rows=rows,stable_initialization=chosen['initialization'] if chosen else None,
        stable_source=chosen['source'] if chosen else None,stable_replay=chosen['replay'] if chosen else None,
        accepted=bool(s.get('selected')),selected=s.get('selected'),ledger=host.store.remaining(),
        numerical_s=s['numerical_s'],driver_elapsed_s=time.perf_counter()-started,prior_bf6_costs_retained=True)
    atomic_json(summary,out)
    print(json.dumps({k:out[k] for k in ('stage','stable_initialization','accepted','numerical_s','driver_elapsed_s')}),flush=True)


if __name__=='__main__':main()
