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


def prepare_smoke(leaf,folder):
    source=ROOT/'configs/research'/leaf
    if not (folder/'study.json').exists():
        spec=read(source)
        defaults=read(source.parent/spec['defaults'])
        for key in ('task','control','runtime'):
            defaults[key]=str((source.parent/defaults[key]).resolve())
        atomic_json(folder/'defaults.json',defaults)
        for key in ('family_space','task','control'):
            if key in spec:spec[key]=str((source.parent/spec[key]).resolve())
        for condition in spec.get('task_conditions',[]):
            condition['task']=str((source.parent/condition['task']).resolve())
        count=len(spec.get('task_conditions',[])) or 1
        spec.update(defaults='defaults.json',study_id=folder.name,mode='engineering_numerical',
            authorization='Public benchmark integration authorizes this minimal engineering check: one native baseline and independent replay per condition, zero Provider, NMPC or RL.',
            budgets=dict(physical_launches=count,mathematical_evaluations=count),
            evidence_destination='runs/'+folder.name+'/private-store')
        atomic_json(folder/'study.json',spec)
    host=core.prepare(folder/'study.json',directory=folder/'private-store')
    if 'freeze' not in state(host):core.bind(host)
    return host


def main(task='tracking'):
    folder=ROOT/('runs/integration-'+task+'-smoke')
    summary=folder/'summary.json'
    if summary.exists():
        print(json.dumps(dict(status='already_completed',additional_physics_steps=0,summary=str(summary))))
        return
    folder.mkdir(parents=True,exist_ok=True)
    leaf={'tracking':'study_tracking_public.json','bf5':'study_bf5_public.json','bf6':'study_bf6_public.json'}[task]
    host=prepare_smoke(leaf,folder)
    spec=state(host)['spec']
    scope=dict(study_id=host.run_id,resolved_identity=spec['resolved_identity'],capabilities=spec['capabilities'])
    save(host,dict(user_approval='Public benchmark integration: one baseline Native callback and one independent replay; no search or Provider',scope=scope,
        scope_identity=digest(scope)),'formal_study_authorization')
    request=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],
        segment_count=2,tendon_count=6)
    candidate=core.dispatch(host,plan('generate',generation=request),'generate')['result']['candidate']
    method=mathematical_method_view(host,candidate)['methods']['mujoco_direct_control_v1']
    assert method['formal_execution_authorized']
    seed=core.dispatch(host,plan('initialize_control',candidate,control_seed=dict(candidate=candidate)),'seed')['result']['source']
    query=deepcopy(method['request_template'])
    query['control_optimization']=dict(source=seed,settings=dict(version='local_control_search_v2',
        correction_window_s=[0.,.6],knots_s=[0.,.58],evaluation_requests=1,iterations=1))
    output=analysis.dispatch(host,query,'native',guard=core.guard)
    native=host.store.artifact(output['reference'])
    if task!='bf6':assert native['status']=='computed'
    assert native['task_acceptance']=='unmeasured'
    native_cost=next((native[k]['cost'] for k in ('native_dynamics','native_diagnostic','native_progress')
        if native.get(k,{}).get('cost')),None)
    result=core.dispatch(host,plan('physical_replay',candidate,physical_replay=dict(candidate=candidate,
        source=native.get('control_schedule_reference',seed))),'replay')['result']
    core.read_evidence(host,dict(reference=result['reference'],view='full'))
    raw=host.store.artifact(result['raw_reference'])
    assert _source_issue(result['acceptance']) is None
    if result['acceptance']['status'] in ('accepted','valid_failure'):
        assert _outcome_issue(result['acceptance']) is None
    receipt=json.loads(host.store.lookup(host.run_id,result['request_id'])['receipt'])
    assert receipt['execution_id']==result['execution_id']
    assert host.store.artifact(result['profile_reference'])['execution_id']==receipt['execution_id']
    choice=eligibility(host,result['reference'],selection=True)
    if choice['eligible']:
        core.dispatch(host,plan('select',selected_execution=result['reference']),'select')
    summary_value=dict(implementation=state(host)['freeze'],provider_requests=0,nmpc_updates=0,rl_actions=0,
        native_status=native['status'],native=native_cost,independent_replay=raw.get('cost'),
        physics_steps=native_cost['physics_steps']+raw['physics_steps'] if native_cost and 'physics_steps' in raw else None,
        protocol=result['acceptance']['protocol_id'],acceptance_status=result['acceptance']['status'],
        selected=bool(state(host).get('selected')),selection_eligibility=choice,
        registered_receipt_type=receipt['tool_id'],execution_binding_verified=True,
        rigid_tool_binding=raw.get('rigid_tool_binding'),environment_contact=raw.get('environment_contact'),
        resource_use=core.resource_use(host),private_store='runs/'+folder.name+'/private-store',
        interpretation='Public method discovery and execution engineering check. No autonomous Provider study or benchmark search.')
    atomic_json(summary,summary_value)
    print(json.dumps(summary_value))



def conditions_main():
    folder=ROOT/'runs/integration-conditions-smoke'
    if (folder/'summary.json').exists():
        print(json.dumps(dict(status='already_completed',additional_physics_steps=0)))
        return
    folder.mkdir(parents=True,exist_ok=True)
    host=prepare_smoke('study_multicondition_public.json',folder)
    spec=state(host)['spec']
    request=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],segment_count=2,tendon_count=6)
    candidate=core.dispatch(host,plan('generate',generation=request),'generate')['result']['candidate']
    records=[];references=[]
    for index,condition in enumerate(spec['task_conditions']):
        key=condition['condition_id']
        seed=core.dispatch(host,plan('initialize_control',candidate,control_seed=dict(candidate=candidate,
            condition_id=key,tensions_n=[[.2+index*.1]*6])),'seed-'+key)['result']
        duration=host.store.artifact(seed['candidate'])['configuration']['task']['timing']['duration_s']
        period=host.store.artifact(seed['candidate'])['configuration']['task']['timing']['control_period_s']
        query=dict(candidate=seed['candidate'],operation='mujoco_direct_control_v1',model_source='mujoco',
            operating_point='standardized_initial_pretension',protocol=spec['analysis_protocol'],
            control_optimization=dict(source=seed['source'],settings=dict(version='local_control_search_v2',
                correction_window_s=[0.,duration],knots_s=[0.,duration-period],evaluation_requests=1,iterations=1)))
        output=analysis.dispatch(host,query,'native-'+key,guard=core.guard)
        native=host.store.artifact(output['reference'])
        result=core.dispatch(host,plan('physical_replay',seed['candidate'],physical_replay=dict(candidate=seed['candidate'],
            source=native['control_schedule_reference'])),'replay-'+key)['result']
        core.read_evidence(host,dict(reference=result['reference'],view='full'))
        assert _source_issue(result['acceptance']) is None and _outcome_issue(result['acceptance']) is None
        raw=host.store.artifact(result['raw_reference'])
        references.append(result['reference'])
        records.append(dict(condition_id=key,native=native['native_dynamics']['cost'],independent_replay=raw['cost'],
            acceptance_status=result['acceptance']['status']))
    choice=eligibility(host,references,selection=True)
    if choice['eligible']:core.dispatch(host,plan('select',selected_execution=references),'select')
    value=dict(implementation=state(host)['freeze'],conditions=records,provider_requests=0,nmpc_updates=0,rl_actions=0,
        physics_steps=sum(r['native']['physics_steps']+r['independent_replay']['physics_steps'] for r in records),
        selected=bool(state(host).get('selected')),joint_eligible=choice['eligible'],joint_reasons=choice['reasons'],
        resource_use=core.resource_use(host),private_store='runs/integration-conditions-smoke/private-store',
        interpretation='Two independent native baselines and full-condition physical replays; no scientific search or benchmark feasibility claim.')
    atomic_json(folder/'summary.json',value)
    print(json.dumps(value))

if __name__=='__main__':
    import sys
    if sys.argv[1:]==['conditions']:conditions_main()
    elif sys.argv[1:]==['bf5']:main('bf5')
    elif sys.argv[1:]==['bf6']:main('bf6')
    else:main()
