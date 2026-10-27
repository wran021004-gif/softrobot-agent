"""Frozen six-group S2 orchestration; existing Store/search/evaluator own evidence."""
import json
import os
import time

from tools.research import core, analysis
from tools.research.config import ROOT
from tools.research.state import state
from tools.research_tasks import _outcome_issue, _source_issue
from tools.state_io import atomic_json, digest, read
from tests.research.bf4_tracking_s1 import plan as base_plan


def plan(action, **payload):
    value=base_plan(action,**payload)
    value.update(stopping_condition='First independent pass closes this group only; otherwise frozen cumulative 101 callbacks/4 iterations/3 replays. Execute every S2 group.',
        interpretation='Matched finite control reoptimization comparison; finite failures do not establish structural infeasibility.')
    return value


def run_group(frozen, group):
    started=time.perf_counter();key='bf4-s2-'+group['group_id']
    destination=ROOT/'runs/bf4-s2'/group['group_id'];summary=destination/'summary.json'
    if summary.exists():return read(summary)
    host=core.prepare(ROOT/group['study_file'],directory=destination/'private-store')
    os.environ.update(state(host)['spec']['numerical_environment'])
    if 'freeze' not in state(host):core.bind(host)
    if state(host).get('pending'):core.recover(host)
    spec=state(host)['spec'];settings=frozen['search_settings']
    assert spec['canonical_task_identity']==frozen['canonical_task_identity']
    assert spec['family_space_identity']==frozen['family_space_identity']
    candidate=core.dispatch(host,plan('generate',generation=frozen['candidate_requests'][group['design']]),key+'-design',origin='engineering')['result']['candidate']
    source=core.dispatch(host,plan('initialize_control',control_seed=dict(candidate=candidate,tensions_n=[[group['initial_tension_n']]*6])),key+'-seed',origin='engineering')['result']['source']
    attempts=[];failed=[];previous=None
    for index in range(frozen['independent_replays_per_group']):
        optimization=dict(source=source,settings=settings)
        if previous:optimization.update(resume_from=previous,failed_replays=failed)
        query=dict(candidate=candidate,operation='mujoco_direct_control_v1',model_source='mujoco',
            operating_point='standardized_initial_pretension',protocol=spec['analysis_protocol'],control_optimization=optimization)
        out=analysis.dispatch(host,query,key+'-native-'+str(index),guard=core.guard,origin='engineering_preflight')
        native=host.store.artifact(out['reference']);core.read_evidence(host,dict(reference=out['reference'],view='full'))
        entry=dict(analysis=out['reference'],status=native['status']);attempts.append(entry)
        if native['status']!='computed':break
        raw=native['native_dynamics'];search=raw['optimization']
        entry.update(native_cost=raw['cost'],callbacks=search['cost_feedback']['evaluation_callbacks'],
            baseline_measure=search['candidates'][0]['measure'],best_measure=search['best']['measure'],search_stop=search['stop_reason'],
            first_proxy_callback=next((i+1 for i,r in enumerate(search['candidates']) if r['measure']['signed_maximum_excess']<=0),None))
        result=core.dispatch(host,plan('physical_replay',physical_replay=dict(candidate=candidate,source=native['control_schedule_reference'])),key+'-replay-'+str(index),origin='engineering')['result']
        core.read_evidence(host,dict(reference=result['reference'],view='full'))
        physical=host.store.artifact(result['raw_reference'])
        entry.update(replay=result['reference'],execution_id=result['execution_id'],raw_reference=result['raw_reference'],
            evaluation_reference=result['evaluation_reference'],acceptance=result['acceptance'],replay_cost=physical.get('cost'),
            replay_numerical_s=result['charged_numerical_s'])
        assert result['execution_id']==result['acceptance']['execution_id']
        assert _outcome_issue(result['acceptance']) is None and _source_issue(result['acceptance']) is None
        atomic_json(destination/'progress.json',dict(attempts=attempts,ledger=host.store.remaining()))
        if result['acceptance']['accepted']:
            core.dispatch(host,plan('select',selected_execution=result['reference'],supporting_evidence=[out['reference'],result['reference']]),key+'-select',origin='engineering')
            break
        if search['stop_reason']!='local_target_reached':break
        failed.append(result['reference']);previous=out['reference']
    if state(host)['research_status']!='stopped':
        core.dispatch(host,plan('stop',next_step='stop',supporting_evidence=[*state(host)['analysis_results'],*state(host)['physical_replays']]),key+'-stop',origin='engineering')
    s=state(host)
    steps=sum(a.get('native_cost',{}).get('physics_steps',0)+a.get('replay_cost',{}).get('physics_steps',0) for a in attempts)
    callbacks=sum(a.get('native_cost',{}).get('rollouts',0) for a in attempts)
    assert callbacks<=101 and steps<=62400 and len(s['physical_replays'])<=3
    row=dict(group=group,candidate=candidate,study_id=host.run_id,implementation=s['freeze'],resolved_identity=spec['resolved_identity'],
        protocol_identity=digest(frozen),accepted=bool(s.get('selected')),attempts=attempts,native_callbacks=callbacks,physics_steps=steps,
        numerical_s=s['numerical_s'],driver_elapsed_s=time.perf_counter()-started,ledger=host.store.remaining(),selected=s.get('selected'))
    atomic_json(summary,row)
    print(json.dumps(dict(group=group['group_id'],accepted=row['accepted'],callbacks=callbacks,physics_steps=steps),ensure_ascii=False),flush=True)
    return row


def main():
    destination=ROOT/'runs/bf4-s2';summary=destination/'summary.json'
    if summary.exists():
        print(json.dumps(dict(status='sealed_s2',additional_computations=0)));return
    frozen=read(ROOT/'configs/research/bf4_tracking_s2_freeze.json')
    assert digest(read(ROOT/frozen['task_file']))==frozen['task_file_identity']
    rows=[]
    for group in frozen['groups']:
        rows.append(run_group(frozen,group))
        atomic_json(destination/'progress.json',dict(rows=rows,protocol_identity=digest(frozen)))
    result=dict(stage='S2',rows=rows,protocol_identity=digest(frozen),native_callbacks=sum(r['native_callbacks'] for r in rows),
        independent_replays=sum(len([a for a in r['attempts'] if a.get('replay')]) for r in rows),
        physics_steps=sum(r['physics_steps'] for r in rows),numerical_s=sum(r['numerical_s'] for r in rows),
        driver_elapsed_s=sum(r['driver_elapsed_s'] for r in rows),private_evidence_retained=True)
    atomic_json(summary,result)
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)


if __name__=='__main__':main()
