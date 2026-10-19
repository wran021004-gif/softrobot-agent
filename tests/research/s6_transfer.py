"""Explicit engineering migration validation, never attributed to Agent choices."""
from copy import deepcopy
from pathlib import Path
from tools.platform_host import Host
from tools.research import core
from tools.research.state import state, save
from tools.research.contracts import Plan
from tools.research.numerics import archived
from tools.research.physical_replay import initialize_schedule, binding, evaluate_schedule
from tools.state_io import read, atomic_json, digest
from tests.research.s6_audit import audit

ROOT=Path(__file__).resolve().parents[2]
RUN='s6-mirror-transfer-20261019'


def plan(action,intent,candidate=None,budget=0,**kwargs):
    return dict(action=action,hypothesis='Engineering interface validation on a separately frozen mirror task',
        expected_observation='Candidate-specific control initialization and independent acceptance',
        weakening_observation='Explicit unsupported result, binding failure or incomplete execution',
        fixed_conditions='Frozen mirror task, physics, bounds and evaluator',stopping_condition='Four shared backend launches or first complete pass',
        interpretation='Engineering migration evidence only; no Agent research attribution or efficacy claim',
        decision=dict(version='research_decision_v1',hypothesis_id='ENGINEERING_TRANSFER_INTERFACE',
            claimed_inference='empirical_search',research_intent=intent,selected_method='engineering_contract_validation',
            selected_candidate=candidate,selected_variables=[],requested_budget=budget),**kwargs)


def main():
    host=Host(ROOT/'runs/research'/RUN,RUN,actor='unified-research')
    if state(host)['research_status']=='stopped':
        audit(host,ROOT/'evidence/s6_transfer');return
    core.guard(host,True)
    best=read(ROOT/'evidence/control_search_p1/best_control.json')
    old=archived('evidence/control_search_p1/study',best['candidate'])
    source=archived('evidence/control_search_p1/study',best['source_reference'])
    binding(old['configuration'],source['trajectory'])
    parent=save(host,old,'engineering_cross_task_parent')
    parameters=deepcopy(old['parameters']);parameters['family_space_identity']=state(host)['spec']['family_space_identity']
    candidate=core.dispatch(host,plan('generate','DESIGN_MODIFICATION',generation=parameters),'mirror-candidate',origin='engineering')['result']['candidate']
    cfg=host.store.artifact(candidate)['configuration']
    if digest(cfg['task'])==digest(old['configuration']['task']):raise ValueError('NEW_TRANSFER_TASK_IDENTITY_REQUIRED')
    mirrored=initialize_schedule(cfg,source,parent)
    mirrored['provenance']['purpose']='Explicit independent mirror-task initialization; historical outcome not transferred'
    def factory(action,**kwargs):return plan(action,'PHYSICAL_VALIDATION',candidate,1,**kwargs)
    first,cached=evaluate_schedule(host,candidate,mirrored,factory)
    core.read_evidence(host,dict(reference=first['reference']))
    if not state(host).get('success_gate'):
        revised=deepcopy(parameters);revised['segments']['0']['young_pa']*=1.01
        new=core.dispatch(host,plan('generate','DESIGN_MODIFICATION',generation=revised),'mirror-revised-material',origin='engineering')['result']['candidate']
        source_ref=save(host,mirrored,'engineering_mirror_initialization')
        control=plan('control_search','CONTROL_SEARCH',new,3,control_search=dict(candidate=new,source=source_ref,
            adaptation_from=candidate,settings=dict(version='local_control_search_v2',method='pattern',knots_s=[.30,.34],
                correction_window_s=[.30,.35],evaluation_requests=3,initial_radius_n=.001,difference_step_n=.001)))
        core.dispatch(host,control,'mirror-new-design-adaptation',origin='engineering')
    s=state(host)
    for ref in s['physical_replays']:core.read_evidence(host,dict(reference=ref))
    if s.get('success_gate'):
        ref=s['success_gate']['evidence']
        core.dispatch(host,plan('select','SELECT',selected_execution=ref,supporting_evidence=[ref]),'mirror-select',origin='engineering')
    else:
        core.dispatch(host,plan('stop','STOP',supporting_evidence=s['physical_replays']),'mirror-stop',origin='engineering')
    audit(host,ROOT/'evidence/s6_transfer')
    atomic_json(ROOT/'evidence/s6_transfer/validation.json',dict(engineering=True,agent_attribution=False,
        distinct_task_identity=True,old_task_identity=digest(old['configuration']['task']),new_task_identity=digest(cfg['task']),
        physical_evaluations=len(state(host)['physical_replays']),control_adaptation_executed=bool(state(host).get('control_search_results')),
        inherited_acceptance=False))


if __name__=='__main__':main()
