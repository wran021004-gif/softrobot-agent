"""Finite BF7 orchestration using original Study tools; no scientific kernels."""
from copy import deepcopy
import json
import math
import os
import sys
import time

from tools.research import core, analysis
from tools.research.config import ROOT, same_robot_structure
from tools.research.contracts import PLAN_RESEARCH_INTENTS
from tools.research.state import state
from tools.platform_store import Store
from tools.research_tasks import _source_issue, _outcome_issue
from tools.state_io import read, atomic_json


PROTOCOL = ROOT / 'configs/research/bf7_protocol_v1.json'
RUNS = ROOT / 'runs/bf7-v1'


def plan(action, **payload):
    return dict(action=action,
        hypothesis='A shared serial structure may independently reach all three frozen targets; length changes may alter the worst target.',
        expected_observation='Three task-bound solves or complete independent physical results on an identical structure.',
        weakening_observation='Unresolved models, incomplete coverage, or no reduction in comparable physical violations.',
        fixed_conditions='BF7 v1 tasks, 10mm position/30mm_s speed limits, 0.6s, seed17, zero state, original materials/routing/payload and final mesh.',
        stopping_condition='Frozen finite stage caps; first joint independent pass SELECT, otherwise bounded STOP.',
        interpretation='Local reoptimized mathematical capability, fixed-input response and independent physical acceptance are distinct.',
        decision=dict(hypothesis_id='bf7-shared-structure-v1',research_intent=PLAN_RESEARCH_INTENTS[action],selected_method=action), **payload)


def prepare(leaf, folder):
    host=core.prepare(ROOT/'configs/research'/leaf,directory=folder/'private-store')
    os.environ.update(state(host)['spec']['numerical_environment'])
    if 'freeze' not in state(host):core.bind(host)
    if state(host).get('pending'):core.recover(host)
    return host


def dispatch(host, action, key, **payload):
    return core.dispatch(host,plan(action,**payload),key,origin='engineering')['result']


def stop(host, key):
    s=state(host)
    if s['research_status']!='stopped':
        dispatch(host,'stop',key,next_step='stop',supporting_evidence=[*s['analysis_results'],*s['physical_replays'],*s.get('search_results',[])])


def analysis_row(host, reference):
    core.read_evidence(host,dict(reference=reference,view='full'))
    a=host.store.artifact(reference); t=a.get('trajectory') or {}; app=a.get('analysis_applicability',{})
    coverage=app.get('constraint_coverage',[])
    complete=bool(app.get('full_task_supported') and coverage and all(
        not c.get('unchecked_indices') and set(c.get('checked_indices',[]))==set(c.get('analyzed_indices',[])) for c in coverage))
    score=t.get('replayed_violation')
    valid=bool(a['status']=='computed' and complete and t.get('replay',{}).get('numerically_valid')
        and isinstance(score,(float,int)) and math.isfinite(score))
    return dict(reference=reference,status=a['status'],valid_shared_score_component=valid,
        signed_normalized_violation=score if valid else None,coverage=coverage,full_task_supported=complete,
        optimality_status=t.get('optimality_status'),solver=t.get('solver'),
        local_model_constraints=a.get('local_model_constraints'),model_assessment=app.get('model_assessment'),
        actual_mathematical_calls=a.get('actual_mathematical_calls'),
        recorded_attempt_boundaries=a.get('recorded_attempt_boundaries'),recorded_return_boundaries=a.get('recorded_return_boundaries'),
        charged_analysis_evaluations=a.get('charged_analysis_evaluations'),charged_numerical_s=a.get('charged_numerical_s'),
        task_acceptance=a.get('task_acceptance'),limitations=a.get('limitations'))


def prescreen():
    folder=RUNS/'math';summary=folder/'summary.json'
    if summary.exists():return read(summary)
    started=time.perf_counter();f=read(PROTOCOL);host=prepare(f['prescreen']['study'],folder);spec=state(host)['spec']
    query=dict(f['prescreen']['proposal_search'],family_space_identity=spec['family_space_identity'])
    result=dispatch(host,'search','bf7-proposal-search',search=query)
    core.read_evidence(host,dict(reference=result['reference'],view='full'))
    search=host.store.artifact(result['reference'])['result']; designs=[]
    for i,row in enumerate(search['evaluated']):
        if not row.get('evidence',{}).get('candidate'):continue
        root=row['evidence']['candidate']; tasks={}
        for j,condition in enumerate(spec['task_conditions']):
            key='bf7-math-'+str(i)+'-'+condition['condition_id']
            bound=dispatch(host,'initialize_control',key+'-condition',control_seed=dict(candidate=root,
                condition_id=condition['condition_id'],tensions_n=[[.2]*6]))
            if j==0:ref=row['evidence']['analysis']
            else:
                output=analysis.dispatch(host,dict(candidate=bound['candidate'],operation='task_capability',
                    operating_point='standardized_initial_pretension',protocol=spec['analysis_protocol'],
                    capability_method='sampled-affine-conic-minimax-v1'),key,guard=core.guard,origin='engineering_preflight')
                ref=output['reference']
            tasks[condition['condition_id']]=analysis_row(host,ref)
        valid=all(r['valid_shared_score_component'] for r in tasks.values())
        designs.append(dict(index=i,candidate=root,conditions=tasks,
            shared_score=max(r['signed_normalized_violation'] for r in tasks.values()) if valid else None))
    ranked=sorted((d for d in designs if d['shared_score'] is not None),key=lambda d:(d['shared_score'],d['index']))
    selected={}
    if len(ranked)>=2:
        best=ranked[0];peer=next((d for d in ranked if d['index']==0 and d['index']!=best['index']),ranked[1])
        if f['prescreen'].get('physical_selection')=='proposal_order_unvalidated_model':
            best,peer=sorted(ranked,key=lambda d:d['index'])[:2]
        selected=dict(best=best['index'],peer=peer['index'])
    stop(host,'bf7-math-stop');s=state(host)
    value=dict(stage='prescreen',implementation=s['freeze'],family_space_identity=spec['family_space_identity'],
        task_conditions=spec['task_conditions'],search_reference=result['reference'],search_resource_use=search['resource_use'],
        search_termination=search['termination_reason'],designs=designs,selected=selected,
        mathematical_evaluations=s['mathematical_evaluations'],numerical_s=s['numerical_s'],
        compatibility_preparation_s=s['compatibility_preparation_s'],ledger=host.store.remaining(),driver_elapsed_s=time.perf_counter()-started)
    atomic_json(summary,value)
    print(json.dumps(dict(stage='prescreen',scores=[d['shared_score'] for d in designs],selected=selected,
        mathematical_evaluations=s['mathematical_evaluations'],numerical_s=s['numerical_s'])),flush=True)
    return value


def continuation_eligible(row, native):
    if row.get('accepted') or row.get('source_issue') or row.get('outcome_issue'):return False
    if row.get('acceptance',{}).get('status')!='valid_failure':return False
    scores=[c['measure']['signed_maximum_excess'] for c in native['native_dynamics']['optimization']['candidates']]
    return bool(len(scores)>=51 and scores[0]>0 and min(scores)<=.95*scores[0]
        and min(scores[-26:])<min(scores[:51])-1e-4)


def optimize(host, root, condition, settings, key, source=None, parent=None, explicit_tensions=None):
    started=time.perf_counter()
    seed=dispatch(host,'initialize_control',key+'-seed',control_seed=dict(candidate=root,condition_id=condition,
        **(dict(source=source,parent=parent) if source else dict(tensions_n=explicit_tensions if explicit_tensions is not None else [[.2]*6]))))
    candidate=seed['candidate'];spec=state(host)['spec']
    out=analysis.dispatch(host,dict(candidate=candidate,operation='mujoco_direct_control_v1',model_source='mujoco',
        operating_point='standardized_initial_pretension',protocol=spec['analysis_protocol'],
        control_optimization=dict(source=seed['source'],settings=settings)),key+'-native',guard=core.guard,origin='engineering_preflight')
    core.read_evidence(host,dict(reference=out['reference'],view='full'));a=host.store.artifact(out['reference'])
    row=dict(condition_id=condition,candidate=candidate,analysis=out['reference'],analysis_status=a['status'],accepted=False)
    if a['status']!='computed':
        row.update(failure_reason=a.get('reason'),native_progress=a.get('native_progress'),continuation_eligible=False)
    else:
        n=a['native_dynamics'];opt=n['optimization']
        row.update(control_source=a['control_schedule_reference'],native_cost=n['cost'],
            native_callbacks=opt['cost_feedback']['evaluation_callbacks'],baseline=opt['candidates'][0]['measure'],best=opt['best']['measure'],
            stop_reason=opt['stop_reason'],response_steps=opt['iterations_started'],
            progress=[dict(callback=i+1,measure=c['measure']) for i,c in enumerate(opt['candidates']) if i==0 or i==len(opt['candidates'])-1 or i%25==0])
        r=dispatch(host,'physical_replay',key+'-replay',physical_replay=dict(candidate=candidate,source=a['control_schedule_reference']))
        core.read_evidence(host,dict(reference=r['reference'],view='full'));raw=host.store.artifact(r['raw_reference'])
        row.update(replay=r['reference'],raw=r['raw_reference'],evaluation=r['evaluation_reference'],profile=r.get('profile_reference'),
            execution_id=r['execution_id'],acceptance=r['acceptance'],replay_cost=raw.get('cost'),
            replay_progress=dict(status=raw['status'],physics_steps=raw.get('physics_steps'),physics_step_attempts=raw.get('physics_step_attempts'),failure=raw.get('failure')),
            source_issue=_source_issue(r['acceptance']),outcome_issue=_outcome_issue(r['acceptance']),accepted=r['acceptance']['accepted'] is True)
        row['continuation_eligible']=continuation_eligible(row,a)
    row['driver_elapsed_s']=time.perf_counter()-started
    return row


def physical(role, phase='initial'):
    if phase not in ('initial','continuation'):raise ValueError('UNKNOWN_FROZEN_PHASE')
    f=read(PROTOCOL);folder=RUNS/role;summary=folder/(phase+'.json')
    if phase=='continuation' and not f['physical'].get('allow_continuation',True):raise ValueError('NO_CONTINUATION_AUTHORIZED_IN_THIS_GRANT')
    if summary.exists():return read(summary)
    started=time.perf_counter();screen=read(RUNS/'math/summary.json')
    if not screen['selected']:raise ValueError('NO_TWO_COMPLETE_THREE_TARGET_MATHEMATICAL_CANDIDATES')
    index=screen['selected'][role];chosen=next(d for d in screen['designs'] if d['index']==index)
    original=Store(RUNS/'math/private-store').artifact(chosen['candidate'])
    host=prepare(f['physical']['studies'][role],folder)
    settings=deepcopy(f['physical']['initial_settings']);previous=None;extension={}
    if phase=='continuation':
        extension=read(ROOT/'configs/research/bf7_v1_continuation.json')
        settings.update(extension['settings'])
        previous=read(folder/'initial.json')
        assert role in extension['roles'] and settings['evaluation_requests']<=100
    root=dispatch(host,'generate','bf7-'+role+'-design',generation=original['parameters'])['candidate']
    actual=host.store.artifact(root)['configuration']
    assert same_robot_structure(actual,original['configuration']) and actual['policy']['discretization']==original['configuration']['policy']['discretization']
    progress=folder/(phase+'-progress.json');rows=read(progress) if progress.exists() else {}
    for condition in state(host)['spec']['task_conditions']:
        key=condition['condition_id']
        if key in rows:continue
        prior=previous['conditions'][key] if previous else None
        repair=extension.get('initialization_repairs',{}).get(role,{}).get(key)
        initial_seed=f['physical'].get('initial_seeds',{}).get(key) if phase=='initial' else None
        if prior and (prior['accepted'] or (not prior['continuation_eligible'] and not repair)):rows[key]=prior
        else:
            local=deepcopy(settings);inputs=None
            if repair:
                failed=Store(ROOT/repair['store']).artifact(repair['control_source'])
                assert failed['task_acceptance']=='unmeasured'
                inputs=failed['trajectory']['tensions_n']
                local.update(repair['settings'])
            elif initial_seed:
                failed=Store(ROOT/initial_seed['store']).artifact(initial_seed['control_source'])
                assert failed['task_acceptance']=='unmeasured'
                inputs=failed['trajectory']['tensions_n']
            rows[key]=optimize(host,root,key,local,'bf7-'+role+'-'+phase+'-'+key,
                source=prior['control_source'] if prior and not repair else None,
                parent=prior['candidate'] if prior and not repair else None,explicit_tensions=inputs)
            if repair:rows[key]['initialization_repair']=repair
            if initial_seed:rows[key]['initial_seed']=initial_seed
        atomic_json(progress,rows)
        print(json.dumps(dict(role=role,phase=phase,condition=key,accepted=rows[key]['accepted'],
            callbacks=rows[key].get('native_callbacks'),metrics=rows[key].get('acceptance',{}).get('metrics'),
            continuation_eligible=rows[key].get('continuation_eligible'))),flush=True)
    accepted=all(r['accepted'] for r in rows.values())
    if accepted:
        dispatch(host,'select','bf7-'+role+'-joint-select',selected_execution=[r['replay'] for r in rows.values()],supporting_evidence=[r['analysis'] for r in rows.values()])
    if accepted or phase=='continuation' or not f['physical'].get('allow_continuation',True) or not any(r.get('continuation_eligible') for r in rows.values()):stop(host,'bf7-'+role+'-stop')
    s=state(host)
    value=dict(role=role,phase=phase,screen_index=index,candidate=root,conditions=rows,all_independently_accepted=accepted,
        selected=s.get('selected'),research_status=s['research_status'],implementation=s['freeze'],
        numerical_s=s['numerical_s'],mathematical_evaluations=s['mathematical_evaluations'],ledger=host.store.remaining(),
        compatibility_preparation_s=s['compatibility_preparation_s'],driver_elapsed_s=time.perf_counter()-started)
    atomic_json(summary,value)
    return value


if __name__=='__main__':
    args=sys.argv[1:]
    if args[:1]==['r2']:
        PROTOCOL=ROOT/'configs/research/bf7_r2_protocol.json';RUNS=ROOT/'runs/bf7-r2';args=args[1:]
    if args==['prescreen']:prescreen()
    elif len(args) in (2,3) and args[0]=='physical' and args[1] in ('best','peer'):
        physical(args[1],args[2] if len(args)==3 else 'initial')
    else:raise SystemExit('[r2] prescreen | [r2] physical {best,peer} [initial|continuation]')
