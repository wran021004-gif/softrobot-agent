"""Explicit opt-in engineering integration; formal research uses python -m tools.research run."""
from copy import deepcopy
import argparse
from tools.research import core
from tools.research.state import state
from tools.research.config import ROOT
from tools.platform_host import Host
from tests.research.s7_study import engineering_plan
from tests.research.s8_audit import live


def engineering(host):
    if state(host)['spec']['mode']!='engineering_numerical':raise ValueError('ENGINEERING_ONLY')
    if state(host)['research_status']=='stopped':return
    if state(host)['pending']:core.recover(host)
    seed=state(host)['control_initializations'][0];candidate=seed['candidate']
    def act(action,intent,key,**payload):
        value=engineering_plan(action,intent,candidate,**payload)
        value['stopping_condition']='First complete pass or at most eight shared engineering launches'
        return core.dispatch(host,value,key,origin='engineering')['result']
    row=act('initialize_control','CONTROL_SEARCH','s8-eng-directed',control_seed=dict(
        candidate=candidate,source=seed['source'],parent=candidate,method='physical_response',
        channels=['tendon_0'],evaluation_requests=2,trust_radius_n=.05))
    if row.get('source') and not state(host).get('success_gate'):
        act('physical_replay','PHYSICAL_VALIDATION','s8-eng-directed-evaluate',physical_replay=dict(candidate=candidate,source=row['source']))
    if not state(host).get('success_gate'):
        other=act('initialize_control','CONTROL_SEARCH','s8-eng-constant',control_seed=dict(candidate=candidate,tensions_n=[[.2]*4]))
        settings=dict(version='local_control_search_v2',method='response',knots_s=[.1,.3],correction_window_s=[.1,.35],
            active_coefficients=[0],evaluation_requests=3,iterations=1,coefficient_limit_n=.1,initial_radius_n=.02,difference_step_n=.01)
        value=engineering_plan('control_search','CONTROL_SEARCH',candidate,control_search=dict(candidate=candidate,source=seed['source'],
            settings=settings,additional_starts=[dict(candidate=candidate,source=other['source'])]))
        value['decision']['requested_budget']=settings['evaluation_requests']
        core.dispatch(host,value,'s8-eng-multistart',origin='engineering')
    if not state(host).get('success_gate'):
        from tools.research.analysis import dispatch
        result=dispatch(host,dict(candidate=candidate,operation='input_sensitivity',operating_point='fixed_input_equilibrium',
            protocol=state(host)['spec']['analysis_protocol']),'s8-eng-math',guard=core.guard,origin='engineering')
        ref=result['reference']
        if host.store.artifact(ref)['status']=='computed':
            act('initialize_control','CONTROL_SEARCH','s8-eng-math-seed',control_seed=dict(candidate=candidate,
                method='mathematical_response',response_evidence=ref,trust_radius_n=.05))
    s=state(host);refs=[*s['physical_replays'],*s['analysis_results']]
    for ref in s['physical_replays']:core.read_evidence(host,dict(reference=ref,pointer='/acceptance'))
    if s.get('success_gate'):
        core.dispatch(host,engineering_plan('select','SELECT',selected_execution=s['success_gate']['evidence'],supporting_evidence=refs),'s8-eng-select',origin='engineering')
    else:
        core.dispatch(host,engineering_plan('stop','STOP',supporting_evidence=refs),'s8-eng-stop',origin='engineering')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--engineering',action='store_true',required=True);args=p.parse_args()
    rid='s8-engineering-integration-20261019'
    host=Host(ROOT/'runs/research'/rid,rid,actor='unified-research')
    engineering(host)
    live(host,ROOT/'evidence/s8_engineering')
