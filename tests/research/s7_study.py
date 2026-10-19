"""Explicit S7 engineering integration driver and generic evidence export; no automatic science."""
import argparse
from copy import deepcopy
from tools.platform_host import Host
from tools.research import core
from tools.research.config import ROOT
from tools.research.state import state
from tests.research.s6_audit import audit
from tests.research.s7_audit import verify_package
from tools.state_io import atomic_json


def engineering_plan(action,intent,candidate=None,**payload):
    return dict(action=action,hypothesis='Engineering-only structure/control contract integration',
        expected_observation='Legal candidate-specific control and independent registered evaluation',
        weakening_observation='Explicit invalid/unsupported candidate or incomplete execution',
        fixed_conditions='Frozen task, original thresholds, shared counts and ideal tension',
        stopping_condition='First complete pass or two physical evaluations',
        interpretation='Engineering capability proof; never attributed to autonomous Agent decisions',
        decision=dict(hypothesis_id='S7_ENGINEERING_INTEGRATION',research_intent=intent,selected_method='contract_validation',
            selected_candidate=candidate,requested_budget=1 if action=='physical_replay' else 0),**payload)


def engineering(host):
    if state(host)['research_status']=='stopped':return
    if state(host)['spec']['mode']!='engineering_numerical':raise ValueError('ENGINEERING_STUDY_REQUIRED')
    core.guard(host,True)
    seed=state(host)['control_initializations'][0]
    parent=host.store.artifact(seed['candidate'])
    for channels in (4,3):
        generation=deepcopy(parent['parameters'])
        generation['segments']['0']['physical_parameters']=dict(density_kg_m3=1200.)
        if channels==3:generation.update(tendon_count=3,spans=[],route_overrides={})
        made=core.dispatch(host,engineering_plan('generate','DESIGN_MODIFICATION',generation=generation),f'engineering-design-{channels}',origin='engineering')['result']
        if made['status']!='generated':raise ValueError(str(made))
        candidate=made['candidate']
        control_seed=dict(candidate=candidate,parent=seed['candidate'],source=seed['source'])
        source=core.dispatch(host,engineering_plan('initialize_control','CONTROL_SEARCH',candidate,control_seed=control_seed),f'engineering-seed-{channels}',origin='engineering')['result']['source']
        core.dispatch(host,engineering_plan('physical_replay','PHYSICAL_VALIDATION',candidate,
            physical_replay=dict(candidate=candidate,source=source)),f'engineering-physical-{channels}',origin='engineering')
        if state(host).get('success_gate'):break
    s=state(host)
    for ref in s['physical_replays']:core.read_evidence(host,dict(reference=ref,pointer='/acceptance'))
    if s.get('success_gate'):
        core.dispatch(host,engineering_plan('select','SELECT',selected_execution=s['success_gate']['evidence'],supporting_evidence=s['physical_replays']),'engineering-select',origin='engineering')
    else:
        core.dispatch(host,engineering_plan('stop','STOP',supporting_evidence=s['physical_replays']),'engineering-stop',origin='engineering')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['engineering','audit']);parser.add_argument('run_id');parser.add_argument('destination')
    args=parser.parse_args();host=Host(ROOT/'runs/research'/args.run_id,args.run_id,actor='unified-research')
    if args.command=='engineering':engineering(host)
    destination=ROOT/args.destination
    audit(host,destination)
    verification=verify_package(destination/'study/design_package.json')
    atomic_json(destination/'package_verification.json',verification)
    print(verification)


if __name__=='__main__':main()
