"""One native baseline and independent replay through public APIs; no Provider.

Run once after commit. The private Store and exact requests are retained in runs.
No BF4 candidate/control witness is read or supplied to the public agent.
"""
from copy import deepcopy
import json

from tools.research import core, analysis
from tools.research.config import ROOT
from tools.research.state import state, save
from tools.research.task_constraints import mathematical_method_view
from tools.research.feedback import eligibility
from tools.research_tasks import _source_issue, _outcome_issue
from tools.state_io import read, atomic_json, digest
from tests.research.test_cross_task_integration import plan


def main():
    folder=ROOT/'runs/integration-tracking-smoke'
    summary=folder/'summary.json'
    if summary.exists():
        print(json.dumps(dict(status='already_completed',additional_physics_steps=0,summary=str(summary))))
        return
    folder.mkdir(parents=True,exist_ok=True)
    source=ROOT/'configs/research/study_tracking_public.json'
    if not (folder/'study.json').exists():
        spec=read(source)
        defaults=read(source.parent/spec['defaults'])
        for key in ('task','control','runtime'):
            defaults[key]=str((source.parent/defaults[key]).resolve())
        atomic_json(folder/'defaults.json',defaults)
        for key in ('family_space','task','control'):
            spec[key]=str((source.parent/spec[key]).resolve())
        spec.update(defaults='defaults.json',study_id='integration-tracking-smoke',
            authorization='Task A-I explicitly authorizes one minimal real public-route engineering execution: one native baseline and one independent replay, zero Provider, NMPC or RL.',
            budgets=dict(physical_launches=1,mathematical_evaluations=1),
            evidence_destination='runs/integration-tracking-smoke/private-store')
        atomic_json(folder/'study.json',spec)
    host=core.prepare(folder/'study.json',directory=folder/'private-store')
    if 'freeze' not in state(host):core.bind(host)
    spec=state(host)['spec']
    scope=dict(study_id=host.run_id,resolved_identity=spec['resolved_identity'],capabilities=spec['capabilities'])
    save(host,dict(user_approval='Task A-I minimal engineering route check only',scope=scope,
        scope_identity=digest(scope)),'formal_study_authorization')
    request=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],
        segment_count=2,tendon_count=6,control_weights=dict(holding_tip_speed_weight=0.,terminal_tip_speed_weight=0.))
    candidate=core.dispatch(host,plan('generate',generation=request),'generate')['result']['candidate']
    method=mathematical_method_view(host,candidate)['methods']['mujoco_direct_control_v1']
    assert method['formal_execution_authorized']
    seed=core.dispatch(host,plan('initialize_control',candidate,control_seed=dict(candidate=candidate)),'seed')['result']['source']
    query=deepcopy(method['request_template'])
    query['control_optimization']=dict(source=seed,settings=dict(version='local_control_search_v2',
        correction_window_s=[0.,.6],knots_s=[0.,.58],evaluation_requests=1,iterations=1))
    output=analysis.dispatch(host,query,'native',guard=core.guard)
    native=host.store.artifact(output['reference'])
    assert native['status']=='computed' and native['task_acceptance']=='unmeasured'
    result=core.dispatch(host,plan('physical_replay',candidate,physical_replay=dict(candidate=candidate,
        source=native['control_schedule_reference'])),'replay')['result']
    core.read_evidence(host,dict(reference=result['reference'],view='full'))
    raw=host.store.artifact(result['raw_reference'])
    assert _source_issue(result['acceptance']) is None
    assert _outcome_issue(result['acceptance']) is None
    receipt=json.loads(host.store.lookup(host.run_id,result['request_id'])['receipt'])
    assert receipt['execution_id']==result['execution_id']
    assert host.store.artifact(result['profile_reference'])['execution_id']==receipt['execution_id']
    choice=eligibility(host,result['reference'],selection=True)
    if choice['eligible']:
        core.dispatch(host,plan('select',selected_execution=result['reference']),'select')
    summary_value=dict(implementation=state(host)['freeze'],provider_requests=0,nmpc_updates=0,rl_actions=0,
        native=native['native_dynamics']['cost'],independent_replay=raw['cost'],
        physics_steps=native['native_dynamics']['cost']['physics_steps']+raw['physics_steps'],
        protocol=result['acceptance']['protocol_id'],acceptance_status=result['acceptance']['status'],
        selected=bool(state(host).get('selected')),selection_eligibility=choice,
        registered_receipt_type=receipt['tool_id'],execution_binding_verified=True,
        resource_use=core.resource_use(host),private_store='runs/integration-tracking-smoke/private-store',
        interpretation='Public method discovery and execution engineering check. No autonomous Provider study or benchmark search.')
    atomic_json(summary,summary_value)
    print(json.dumps(summary_value))


if __name__=='__main__':main()
