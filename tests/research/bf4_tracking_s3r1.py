"""Bounded structure-first comparison through original Study tools only."""
import json
import os
import time
from tools.research import core,analysis
from tools.research.config import ROOT,same_robot_structure
from tools.research.state import state
from tools.platform_store import Store
from tools.research_tasks import _source_issue,_outcome_issue
from tools.state_io import read,digest,atomic_json
from tests.research.bf4_tracking_s2 import plan as prior_plan


def plan(action,**payload):
    value=prior_plan(action,**payload)
    value.update(hypothesis='A bounded Study-owned length search may reduce total fresh BF4 time-to-independent-pass after its own full screening overhead is included.',
        fixed_conditions='Original BF4 task/seed/zero state/physics/payload/12 mm and all 30 points. Two segments, six channels, 12 cells each. S0 is first search candidate, Sstar is tool-ranked proxy best. Both arms fresh 0.2 N and identical frozen Native settings.',
        stopping_condition='At most eight structure proposals/ten mathematical units, then each independent arm at most201 callbacks/eight response iterations/one replay. SELECT first independent pass within each arm, otherwise STOP.',
        interpretation='One nominal paired comparison; model proxy is unmeasured, all screen/failure costs count, no general speed or optimality claim.')
    return value


def prepare(path,destination,frozen):
    host=core.prepare(ROOT/path,directory=destination/'private-store')
    os.environ.update(state(host)['spec']['numerical_environment'])
    if 'freeze' not in state(host):core.bind(host)
    elif state(host)['freeze']==frozen['pre_admission_correction']['prior_implementation'] and host.run_id=='bf4-s3r1-structure-search-v1':
        assert state(host)['mathematical_evaluations']==0 and not state(host)['candidates']
        core.bind(host,reason='Correct external manifest fingerprint to the already-frozen topology-scoped family before first science; original budget and startup costs retained.')
    if state(host).get('pending'):core.recover(host)
    spec=state(host)['spec']
    assert spec['canonical_task_identity']==frozen['canonical_task_identity']
    assert spec['family_space_identity']==frozen['family_space_identity']
    return host


def close(host,key):
    s=state(host)
    if s['research_status']!='stopped':
        evidence=[*s['analysis_results'],*s['physical_replays'],*s.get('search_results',[])]
        core.dispatch(host,plan('stop',next_step='stop',supporting_evidence=evidence),key+'-stop',origin='engineering')


def search_structure(frozen):
    started=time.perf_counter();destination=ROOT/'runs/bf4-s3r1/structure-search';summary=destination/'summary.json'
    if summary.exists():return read(summary)
    host=prepare(frozen['search_study'],destination,frozen)
    out=core.dispatch(host,plan('search',search=frozen['search_query']),'bf4s3r1-search',origin='engineering')['result']
    body={}
    if out.get('reference'):
        core.read_evidence(host,dict(reference=out['reference'],view='full'))
        body=host.store.artifact(out['reference']).get('result',{})
    rows=body.get('evaluated',[]);best=body.get('best_mathematical_candidate') or {}
    first=rows[0].get('evidence',{}).get('candidate') if rows else None
    selected=best.get('evidence',{}).get('candidate')
    close(host,'bf4s3r1-search');s=state(host)
    result=dict(stage='structure_search',reference=out.get('reference'),result=body,first_candidate=first,selected_candidate=selected,
        implementation=s['freeze'],resolved_identity=s['spec']['resolved_identity'],ledger=host.store.remaining(),
        mathematical_evaluations=s['mathematical_evaluations'],numerical_s=s['numerical_s'],
        compatibility_preparation_s=s['compatibility_preparation_s'],driver_elapsed_s=time.perf_counter()-started)
    assert result['mathematical_evaluations']<=10
    atomic_json(summary,result)
    print(json.dumps(dict(stage='structure_search',status=body.get('status',out.get('status')),
        evaluated_designs=len(rows),mathematical_evaluations=s['mathematical_evaluations'],numerical_s=s['numerical_s'])),flush=True)
    return result


def run_control(frozen,screen,arm):
    started=time.perf_counter();destination=ROOT/'runs/bf4-s3r1'/arm;summary=destination/'summary.json'
    if summary.exists():return read(summary)
    source_ref=screen['first_candidate'] if arm=='control_only' else screen['selected_candidate']
    if source_ref is None:
        out=dict(arm=arm,status='not_started',reason='Frozen original search returned no required candidate; no manual replacement',accepted=False,
            numerical_s=0.,driver_elapsed_s=0.,native_callbacks=0,physics_step_attempts=0)
        atomic_json(summary,out);return out
    previous=Store(ROOT/'runs/bf4-s3r1/structure-search/private-store');original=previous.artifact(source_ref)
    host=prepare(frozen['control_studies'][arm],destination,frozen);key='bf4s3r1-'+arm
    candidate=core.dispatch(host,plan('generate',generation=original['parameters']),key+'-design',origin='engineering')['result']['candidate']
    actual=host.store.artifact(candidate)['configuration'];assert same_robot_structure(actual,original['configuration'])
    assert actual['policy']['discretization']==original['configuration']['policy']['discretization']
    source=core.dispatch(host,plan('initialize_control',control_seed=dict(candidate=candidate,tensions_n=[[frozen['initial_tension_n']]*6])),
        key+'-seed',origin='engineering')['result']['source']
    spec=state(host)['spec']
    out=analysis.dispatch(host,dict(candidate=candidate,operation='mujoco_direct_control_v1',model_source='mujoco',
        operating_point='standardized_initial_pretension',protocol=spec['analysis_protocol'],
        control_optimization=dict(source=source,settings=frozen['control_settings'])),key+'-native',guard=core.guard,origin='engineering_preflight')
    native=host.store.artifact(out['reference']);core.read_evidence(host,dict(reference=out['reference'],view='full'))
    row=dict(arm=arm,candidate=candidate,search_candidate=source_ref,analysis=out['reference'],analysis_status=native['status'])
    if native['status']!='computed':
        progress=native.get('native_progress',{})
        row.update(native_cost=progress.get('cost'),completed_native_rollouts=progress.get('completed_rollouts'),
            failure_reason=native.get('reason'),native_progress=progress)
    else:
        raw=native['native_dynamics'];opt=raw['optimization']
        row.update(native_cost=raw['cost'],native_callbacks=opt['cost_feedback']['evaluation_callbacks'],
            baseline_measure=opt['candidates'][0]['measure'],best_measure=opt['best']['measure'],search_stop=opt['stop_reason'],
            first_hard_proxy_callback=next((i+1 for i,v in enumerate(opt['candidates']) if v['measure']['signed_maximum_excess']<=0),None))
        replay=core.dispatch(host,plan('physical_replay',physical_replay=dict(candidate=candidate,source=native['control_schedule_reference'])),
            key+'-replay',origin='engineering')['result']
        core.read_evidence(host,dict(reference=replay['reference'],view='full'));physical=host.store.artifact(replay['raw_reference'])
        diagnostic=physical.get('numerical_failure',{})
        cost=physical.get('cost') or dict(physics_steps_lower_bound=physical.get('physics_steps_lower_bound',0),
            physics_step_attempts=diagnostic.get('attempted_steps'),failed_call_internal_progress='unknown')
        row.update(replay=replay['reference'],raw_reference=replay['raw_reference'],evaluation_reference=replay['evaluation_reference'],
            execution_id=replay['execution_id'],acceptance=replay['acceptance'],replay_cost=cost,
            source_issue=_source_issue(replay['acceptance']),outcome_issue=_outcome_issue(replay['acceptance']))
        atomic_json(destination/'progress.json',row);assert row['source_issue'] is None
        if replay['acceptance']['accepted']:
            core.dispatch(host,plan('select',selected_execution=replay['reference'],supporting_evidence=[out['reference'],replay['reference']]),key+'-select',origin='engineering')
    close(host,key);s=state(host)
    row.update(accepted=bool(s.get('selected')),selected=s.get('selected'),implementation=s['freeze'],
        resolved_identity=spec['resolved_identity'],ledger=host.store.remaining(),numerical_s=s['numerical_s'],
        compatibility_preparation_s=s['compatibility_preparation_s'],driver_elapsed_s=time.perf_counter()-started)
    costs=[row.get('native_cost') or {},row.get('replay_cost') or {}]
    row['physics_step_attempts']=sum(v.get('physics_step_attempts') or 0 for v in costs)
    row['native_callbacks']=row.get('native_callbacks',(row.get('native_cost') or {}).get('rollouts',0))
    assert row['physics_step_attempts']<=121200 and row['native_callbacks']<=201
    atomic_json(summary,row)
    print(json.dumps({k:row.get(k) for k in ('arm','accepted','native_callbacks','physics_step_attempts','best_measure','failure_reason','numerical_s','driver_elapsed_s')}),flush=True)
    return row


def main():
    destination=ROOT/'runs/bf4-s3r1';summary=destination/'summary.json'
    if summary.exists():print(json.dumps(dict(status='sealed_s3r1',additional_scientific_calls=0)));return
    frozen=read(ROOT/'configs/research/bf4_tracking_s3r1_freeze.json')
    assert digest(read(ROOT/frozen['task_file']))==frozen['task_file_identity']
    screen=search_structure(frozen)
    arms={arm:run_control(frozen,screen,arm) for arm in frozen['execution_order'][1:]}
    base=arms['control_only'];changed=arms['structure_first'];store=Store(destination/'structure-search/private-store')
    different=None
    if screen['first_candidate'] and screen['selected_candidate']:
        different=not same_robot_structure(store.artifact(screen['first_candidate'])['configuration'],store.artifact(screen['selected_candidate'])['configuration'])
    prior_failed=read(ROOT/frozen['prior_failed_summary'])['screen']
    totals=dict(control_only_numerical_s=base['numerical_s'],structure_first_numerical_s=prior_failed['numerical_s']+screen['numerical_s']+changed['numerical_s'],
        control_only_driver_s=base['driver_elapsed_s'],structure_first_driver_s=prior_failed['driver_elapsed_s']+frozen['pre_admission_correction']['recorded_failed_command_elapsed_s']+screen['driver_elapsed_s']+changed['driver_elapsed_s'])
    comparable=bool(base['accepted'] and changed['accepted'])
    comparison=dict(both_independently_passed=comparable,structure_changed=different,**totals,
        nominal_total_numeric_speedup=totals['control_only_numerical_s']/totals['structure_first_numerical_s'] if comparable else None,
        nominal_total_driver_speedup=totals['control_only_driver_s']/totals['structure_first_driver_s'] if comparable else None,
        native_callback_difference=base['native_callbacks']-changed['native_callbacks'],
        interpretation='One frozen nominal pair including complete screening cost; failures are censored, no global/general speed claim.')
    result=dict(stage='BF4-S3R1',protocol_identity=digest(frozen),screen=screen,arms=arms,comparison=comparison,
        total_native_callbacks=sum(v['native_callbacks'] for v in arms.values()),
        total_physics_step_attempts=sum(v['physics_step_attempts'] for v in arms.values()))
    assert result['total_native_callbacks']<=402 and result['total_physics_step_attempts']<=242400
    atomic_json(summary,result);print(json.dumps(comparison),flush=True)


if __name__=='__main__':main()
