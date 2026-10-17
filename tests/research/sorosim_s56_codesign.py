"""Bounded fixed-design control optimization through unified research actions."""
import json
from pathlib import Path

from tests.research.sorosim_s56_refinement import initialize,finish,plan
from tools.research import core
from tools.research.state import state,save
from tools.state_io import atomic_json,read
from extensions.tendon_family.sorosim_codesign import integrated_control_source

ROOT=Path(__file__).resolve().parents[2]


def run():
    fidelity=read(ROOT/'evidence/sorosim_s56/refinement/summary.json')
    if not fidelity['results']['32']['complete']:
        raise ValueError('COMPLETE_32_SUBSTEP_QUALIFICATION_REQUIRED')
    host,candidate,source=initialize('s56_codesign')
    arguments=dict(candidate=candidate,substeps=4,initialization='saved_candidate_controls',
        warm_source=source,objective_mode='maximum_original_violation',max_iterations=60)
    preflight=core.dispatch(host,plan('mechanics',mechanics=dict(arguments,check_only=True)),
        's56-control-preflight')['result']
    atomic_json(host.store.root/'preflight_reference.json',preflight['reference'])
    if not (preflight.get('objective_relative_error',1)<2e-4 and
            preflight.get('constraint_relative_error',1)<2e-4):
        raise ValueError('DERIVATIVE_OR_COST_PREFLIGHT_FAILED_NO_NLP_LAUNCHED')
    result=core.dispatch(host,plan('mechanics',mechanics=arguments),'s56-control-solve-1')['result']
    value=host.store.artifact(result['reference'])
    summary=dict(stage='S5.6-B',source_freeze=state(host)['freeze'],candidate=candidate,
        initial_source=source,preflight=preflight['reference'],optimization=result['reference'],
        intervention='fixed Design B, four internal steps, same 35 held commands; feasibility-first rho>=0',
        higher_fidelity=32,counts=dict(offline_nlp=state(host)['offline_nlp'],
            integrations=state(host)['bdf_replays']),status=value['status'])
    if value.get('trajectory'):
        replay=core.dispatch(host,plan('refine',refinement=dict(candidate=candidate,
            source=result['reference'],substeps=32)),'s56-control-high-resolution-1')['result']
        checked=host.store.artifact(replay['reference'])
        summary.update(validation=replay['reference'],validation_complete=checked.get('complete'),
            high_resolution_original_task_satisfied=checked.get('original_task_satisfied'),
            **{k:checked.get(k) for k in ('terminal_position_error_m','holding_max_position_error_m','holding_max_speed_m_s')},
            optimization_facts=value['mathematical_facts'])
        if checked.get('complete'):
            # A separate physical handoff uses the original sample clock, not internal NLP nodes.
            handoff=integrated_control_source(value,checked)
            handoff.update(source_solve=result['reference'],source_replay=replay['reference'],
                configuration=host.store.artifact(value['original_request'])['configuration'])
            summary['physical_source']=save(host,handoff,'independently_integrated_control_source')
    summary['counts']=dict(offline_nlp=state(host)['offline_nlp'],integrations=state(host)['bdf_replays'])
    summary['numerical_s']=state(host)['numerical_s']
    finish(host,summary,'evidence/sorosim_s56/codesign')
    print(json.dumps({k:v for k,v in summary.items() if k!='optimization_facts'}),flush=True)


if __name__=='__main__':run()
