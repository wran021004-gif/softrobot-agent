"""Explicit one-baseline/one-replay engineering check; never a discovery campaign.

Run after commit. Reopening the same Store reuses receipts and never adds runs.
All candidate/control/raw artifacts stay in ignored runs; only counts are public.
"""
import json
import time

from tools.research import core, analysis
from tools.research.state import state
from tools.research.feedback import task_gap
from tools.research_tasks import _outcome_issue, _source_issue
from tools.research.config import ROOT
from tools.state_io import read, atomic_json


def plan(action, **payload):
    return dict(action=action, hypothesis='The existing timed contracts compose through independent native execution.',
        expected_observation='Exact scored grid, original evaluator, separate complete replay, retained receipts and costs.',
        weakening_observation='Grid, execution, cost or evaluator coverage mismatch.',
        fixed_conditions='BF4 frozen v1 task, first prespecified legal structure, zero named state, constant pretension.',
        stopping_condition='One baseline native callback plus one independent replay; no further optimization or science.',
        interpretation='Engineering integration evidence only; no structural benefit or search feasibility conclusion.', **payload)


def main():
    started=time.perf_counter()
    destination=ROOT/'runs/bf4-engineering'
    summary_file=destination/'summary.json'
    if summary_file.exists():
        print(json.dumps(dict(status='sealed_engineering_check',additional_rollouts=0,
            summary=str(summary_file))))
        return
    host=core.prepare(ROOT/'configs/research/study_bf4_tracking_engineering.json',directory=destination/'private-store')
    if 'freeze' not in state(host):core.bind(host)
    if state(host).get('pending'):
        raise ValueError('RECOVER_OWNED_PENDING_RESULT_BEFORE_RESTART; never relaunch an unknown execution')
    freeze=read(ROOT/'configs/research/bf4_tracking_freeze_v1.json')
    candidate=core.dispatch(host,plan('generate',generation=freeze['candidate_requests']['full_span']),
        'bf4-engineering-design',origin='engineering')['result']['candidate']
    seed=core.dispatch(host,plan('initialize_control',control_seed=dict(candidate=candidate)),
        'bf4-engineering-seed',origin='engineering')['result']['source']
    settings={**freeze['search_settings'],'evaluation_requests':1,'iterations':1}
    query=dict(candidate=candidate,operation='mujoco_direct_control_v1',model_source='mujoco',
        operating_point='standardized_initial_pretension',protocol=state(host)['spec']['analysis_protocol'],
        control_optimization=dict(source=seed,settings=settings))
    out=analysis.dispatch(host,query,'bf4-engineering-native',guard=core.guard,origin='engineering_preflight')
    native=host.store.artifact(out['reference'])
    assert native['status']=='computed',native
    assert native['task_acceptance']=='unmeasured'
    assert native['native_dynamics']['cost']['rollouts']==1
    assert native['native_dynamics']['cost']['physics_steps']==600
    source=native['control_schedule_reference']
    result=core.dispatch(host,plan('physical_replay',physical_replay=dict(candidate=candidate,source=source)),
        'bf4-engineering-replay',origin='engineering')['result']
    core.read_evidence(host,dict(reference=result['reference'],view='full'))
    raw=host.store.artifact(result['raw_reference'])
    acceptance=result['acceptance']
    assert result['execution_id']==acceptance['execution_id']
    assert acceptance['protocol_id']=='offline_timed_tracking_v1'
    assert _outcome_issue(acceptance) is None,acceptance
    assert _source_issue(acceptance) is None,acceptance
    assert raw['status']=='completed' and raw['physics_steps']==600
    assert task_gap(result)['valid_complete'] and task_gap(result)['normalized_gap'] is not None
    assert native['scoped_claim']['conclusion']=='diagnostic'
    assert native['native_dynamics']['optimization']['cost_feedback']['new_physical_evaluations']==0
    used=host.store.remaining()['used']
    assert used['model_calls']==0 and used['backend_solves']==1
    assert state(host)['mathematical_evaluations']==1
    # Reuse both exact public request IDs. Neither a native callback nor physics step repeats.
    before=host.store.remaining()
    repeated=analysis.dispatch(host,query,'bf4-engineering-native',guard=core.guard,origin='engineering_preflight')
    replayed=core.dispatch(host,plan('physical_replay',physical_replay=dict(candidate=candidate,source=source)),
        'bf4-engineering-replay',origin='engineering')['result']
    assert repeated['operation_reuse']['additional_analysis_evaluations']==0
    assert replayed['reference']==result['reference']
    assert host.store.remaining()==before
    core.dispatch(host,plan('stop',next_step='stop',supporting_evidence=[out['reference'],result['reference']]),
        'bf4-engineering-stop',origin='engineering')
    summary=dict(kind='engineering_chain_check',scientific_search_executed=False,
        implementation_commit=state(host)['freeze'],canonical_task_identity=state(host)['spec']['canonical_task_identity'],
        native=dict(analyses=1,**native['native_dynamics']['cost']),
        independent_replay=dict(launches=1,**raw['cost']),total_physics_steps=1200,
        complete_original_acceptance_evaluated=True,registered_evaluator='evaluate.tracking@1.0.0',
        protocol='offline_timed_tracking_v1',execution_source_binding_verified=True,
        exact_request_reuse_verified=True,additional_reuse_physics_steps=0,provider_requests=0,
        nmpc_updates=0,rl_actions=0,structural_comparisons=0,scientific_search_callbacks=0,
        ledger=host.store.remaining(),construction_numerical_s=state(host).get('construction_numerical_s',0.),
        compatibility_preparation_s=state(host).get('compatibility_preparation_s',0.),
        cumulative_numerical_s=state(host)['numerical_s'],driver_elapsed_s=time.perf_counter()-started,
        private_store_retained='runs/bf4-engineering/private-store; not uploaded',
        scope='One legal baseline checks plumbing only. No benchmark feasibility or structural effect established.')
    atomic_json(summary_file,summary)
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':
    main()
