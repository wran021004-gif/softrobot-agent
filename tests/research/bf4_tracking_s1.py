"""Authorized frozen BF4 feasibility stage through existing Store/workers/search.

Sequential designs, one source per design, original evaluator, first-pass stop.
All scientific records stay under ignored runs; no successful controls are exported.
"""
import json
import time
import argparse

from tools.research import core, analysis
from tools.research.config import ROOT
from tools.research.state import state, save
from tools.platform_store import Store
from tools.research.feedback import task_gap
from tools.research_tasks import _outcome_issue, _source_issue
from tools.state_io import read, atomic_json, digest


def plan(action, **payload):
    return dict(action=action,
        hypothesis='A prespecified legal tendon layout may track the frozen timed path after bounded control reoptimization.',
        expected_observation='A complete independently evaluated trajectory passes every frozen tracking condition.',
        weakening_observation='Search stagnates, encounters numerical failure, or its best trajectory fails independent evaluation.',
        fixed_conditions='Frozen BF4 v1 task, prespecified designs and order, zero physical state, declared candidate-bound control initialization and fidelity.',
        stopping_condition='First complete independent pass, otherwise the exact finite ceiling in the owning S1 or S1b Study.',
        interpretation='A pass is one feasible structure-control combination; finite failure is not structural infeasibility.',
        **payload)


def main(continuation=False):
    started=time.perf_counter()
    stage='s1b' if continuation else 's1'
    destination=ROOT/('runs/bf4-'+stage)
    summary_file=destination/'summary.json'
    if summary_file.exists():
        print(json.dumps(dict(status='sealed_s1',additional_computations=0,summary=str(summary_file))))
        return
    host=core.prepare(ROOT/('configs/research/study_bf4_tracking_'+stage+'.json'),directory=destination/'private-store')
    if 'freeze' not in state(host):core.bind(host)
    if state(host).get('pending'):
        raise ValueError('RECOVER_OWNED_PENDING_RESULT_BEFORE_RESUME; no unknown worker may be relaunched')
    frozen=read(ROOT/'configs/research/bf4_tracking_freeze_v1.json')
    spec=state(host)['spec']
    assert spec['canonical_task_identity']==frozen['canonical_task_identity']
    assert spec['family_space_identity']==frozen['family_space_identity']
    assert digest(read(ROOT/frozen['task_file']))==frozen['task_file_identity']
    settings=dict(frozen['search_settings'])
    prior=None;previous=None
    if continuation:
        prior=read(ROOT/'runs/bf4-s1/summary.json')
        previous=Store(ROOT/'runs/bf4-s1/private-store')
        assert not prior['accepted'] and prior['task_identity']==spec['canonical_task_identity']
        assert previous.session('bf4-tracking-s1-v1')['state']['research_status']=='stopped'
        settings.update(evaluation_requests=101,iterations=4)
    rows=[]
    for name in frozen['candidate_order']:
        key='bf4-'+stage+'-'+name
        generated=core.dispatch(host,plan('generate',generation=frozen['candidate_requests'][name]),
            key+'-design',origin='engineering')['result']
        assert generated['status']=='generated',generated
        candidate=generated['candidate']
        seed_request=dict(candidate=candidate)
        parent_analysis=None
        if continuation:
            ancestor=next(r for r in prior['rows'] if r['design']==name)
            original=previous.artifact(ancestor['analysis'])
            parent_analysis=ancestor['analysis']
            # Candidate-specific executable initialization only; no prior acceptance transfer.
            seed_request.update(source=save(host,previous.artifact(original['control_schedule_reference']),'prior_failing_control_source'),
                parent=save(host,previous.artifact(ancestor['candidate']),'prior_source_candidate'))
        source=core.dispatch(host,plan('initialize_control',control_seed=seed_request),
            key+'-seed',origin='engineering')['result']['source']
        query=dict(candidate=candidate,operation='mujoco_direct_control_v1',model_source='mujoco',
            operating_point='standardized_initial_pretension',protocol=spec['analysis_protocol'],
            control_optimization=dict(source=source,settings=settings))
        out=analysis.dispatch(host,query,key+'-native',guard=core.guard,origin='engineering_preflight')
        native=host.store.artifact(out['reference'])
        core.read_evidence(host,dict(reference=out['reference'],view='full'))
        row=dict(design=name,candidate=candidate,analysis=out['reference'],analysis_status=native['status'],
            prior_analysis_initialization=parent_analysis)
        if native['status']=='computed':
            raw=native['native_dynamics'];search=raw['optimization']
            row.update(native_cost=raw['cost'],search_stop=search['stop_reason'],
                baseline_measure=search['candidates'][0]['measure'],best_measure=search['best']['measure'],
                callbacks=search['cost_feedback']['evaluation_callbacks'],local_responses=search['local_responses'])
            assert row['callbacks']<=settings['evaluation_requests']
            assert raw['cost']['physics_steps']<=settings['evaluation_requests']*600
            result=core.dispatch(host,plan('physical_replay',physical_replay=dict(
                candidate=candidate,source=native['control_schedule_reference'])),key+'-replay',origin='engineering')['result']
            core.read_evidence(host,dict(reference=result['reference'],view='full'))
            acceptance=result['acceptance'];physical=host.store.artifact(result['raw_reference'])
            row.update(replay=result['reference'],acceptance=acceptance,
                replay_cost=physical.get('cost'),task_gap=task_gap(result))
            assert result['execution_id']==acceptance['execution_id']
            assert _outcome_issue(acceptance) is None and _source_issue(acceptance) is None
            if acceptance['accepted']:
                core.dispatch(host,plan('select',selected_execution=result['reference'],
                    supporting_evidence=[out['reference'],result['reference']]),key+'-select',origin='engineering')
        rows.append(row)
        atomic_json(destination/'progress.json',dict(rows=rows,ledger=host.store.remaining()))
        print(json.dumps(dict(design=name,status=row.get('acceptance',{}).get('status',native['status']),
            callbacks=row.get('callbacks'),best_error_m=row.get('best_measure',{}).get('max_position_error_m'),
            physics_steps=row.get('native_cost',{}).get('physics_steps'),search_stop=row.get('search_stop')),ensure_ascii=False),flush=True)
        if state(host).get('success_gate'):break
    if state(host)['research_status']!='stopped':
        core.dispatch(host,plan('stop',next_step='stop',supporting_evidence=[
            *state(host)['analysis_results'],*state(host)['physical_replays']]),'bf4-'+stage+'-stop',origin='engineering')
    s=state(host)
    summary=dict(stage=stage.upper(),implementation=s['freeze'],task_identity=spec['canonical_task_identity'],
        family_space_identity=spec['family_space_identity'],freeze_identity=digest(frozen),
        rows=rows,accepted=bool(s.get('selected')),selected=s.get('selected'),
        stop_reason='first_complete_independent_pass' if s.get('selected') else 'finite_frozen_stage_complete',
        ledger=host.store.remaining(),mathematical_evaluations=s['mathematical_evaluations'],
        analysis_costs=s['analysis_costs'],cumulative_numerical_s=s['numerical_s'],
        construction_numerical_s=s.get('construction_numerical_s',0.),
        control_initialization_s=s.get('control_initialization_s',0.),
        compatibility_preparation_s=s.get('compatibility_preparation_s',0.),
        driver_elapsed_s=time.perf_counter()-started,private_store_retained=True,
        prior_stage_summary='runs/bf4-s1/summary.json' if continuation else None,
        prior_stage_mathematical_evaluations=prior['mathematical_evaluations'] if continuation else 0,
        prior_stage_cumulative_numerical_s=prior['cumulative_numerical_s'] if continuation else 0.,
        interpretation='Feasibility only. No causal structural benefit, theoretical infeasibility, robustness or global optimum established.')
    atomic_json(summary_file,summary)
    print(json.dumps(dict(status='sealed',accepted=summary['accepted'],designs=len(rows),
        mathematical_evaluations=summary['mathematical_evaluations'],ledger=summary['ledger'],
        elapsed_s=summary['driver_elapsed_s']),ensure_ascii=False),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--continuation',action='store_true')
    main(parser.parse_args().continuation)
