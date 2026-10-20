"""Explicit engineering handoff test; formal research remains the existing CLI."""
from tools.research import core
from tools.research.state import state
from tools.research.config import ROOT
from tools.platform_host import Host
from tools.state_io import atomic_json
from tests.research.s7_study import engineering_plan
from tests.research.s8_audit import live


def engineering(host):
    if state(host)['spec']['mode']!='engineering_numerical':raise ValueError('ENGINEERING_ONLY')
    if state(host)['research_status']=='stopped':return
    if state(host)['pending']:core.recover(host)
    candidate=state(host)['control_initializations'][0]['candidate']
    from tools.research.analysis import dispatch
    equilibrium=dispatch(host,dict(candidate=candidate,operation='equilibrium',operating_point='target_equilibrium',
        protocol=state(host)['spec']['analysis_protocol']),'s9-eng-equilibrium',guard=core.guard,origin='engineering')
    sensitivity=dispatch(host,dict(candidate=candidate,operation='input_sensitivity',operating_point='fixed_input_equilibrium',
        protocol=state(host)['spec']['analysis_protocol']),'s9-eng-sensitivity',guard=core.guard,origin='engineering')
    def act(action,intent,key,**payload):
        return core.dispatch(host,engineering_plan(action,intent,candidate,**payload),key,origin='engineering')['result']
    seed=act('initialize_control','CONTROL_SEARCH','s9-eng-seed',control_seed=dict(candidate=candidate,
        method='mathematical_response',response_evidence=sensitivity['reference'],trust_radius_n=.05))
    from tools.research.physical_replay import binding
    source=host.store.artifact(seed['source'])
    binding(host.store.artifact(candidate)['configuration'],source['trajectory'])
    assert source['task_acceptance']=='unmeasured'
    result=act('physical_replay','PHYSICAL_VALIDATION','s9-eng-physics',physical_replay=dict(candidate=candidate,source=seed['source']))
    core.read_evidence(host,dict(reference=result['reference'],pointer='/acceptance'))
    # Repeating the same completed operation must preserve every cost and hash.
    before=host.store.remaining()['used']
    repeated=act('physical_replay','PHYSICAL_VALIDATION','s9-eng-physics',physical_replay=dict(candidate=candidate,source=seed['source']))
    assert host.store.remaining()['used']==before
    assert result['reference']==repeated['reference']
    refs=state(host)['analysis_results']+state(host)['physical_replays']
    gate=state(host).get('success_gate')
    disposition=engineering_plan('select' if gate else 'stop','SELECT' if gate else 'STOP',
        selected_execution=gate['evidence'] if gate else None,supporting_evidence=refs)
    core.dispatch(host,disposition,'s9-eng-close',origin='engineering')
    atomic_json(ROOT/'evidence/s9_engineering/handoff.json',dict(engineering_only=True,provider_requests=0,
        equilibrium=equilibrium,sensitivity=sensitivity,seed=seed,physical_result=result,
        binding_verified=True,recovered_operation_preserved_cost_and_reference=True))


if __name__=='__main__':
    host=Host(ROOT/'runs/research/s9-engineering-20261020','s9-engineering-20261020',actor='unified-research')
    engineering(host)
    live(host,ROOT/'evidence/s9_engineering')
