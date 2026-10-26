"""M2 operator checks, adapted to the authorized R1 caps; original CLI owns run."""
import math
import os
import runpy
import sys
from tools.platform_host import Host
from tools.research import core, analysis
from tools.research.agent import record
from tools.research.config import ROOT
from tools.research.design import verify_candidate, final_fidelity_matches
from tools.research.state import state, guard

RUN='b3-r1-history-assisted-050'
original_dispatch=core.dispatch
original_analysis=analysis.dispatch


def supervised_dispatch(host, value, request_id, **kwargs):
    action=value.get('action')
    if action in ('execute','physical_replay'):
        payload=value if action=='execute' else (value.get('physical_replay') or {})
        ref=payload.get('candidate')
        if ref is None:return original_dispatch(host,value,request_id,**kwargs)
        s=state(host);candidate=verify_candidate(host,ref)
        recipe=candidate['configuration']['policy']['controller']['parameters']['data']['recipe']
        expected=dict(replan_period_s=.1,horizon=10,substeps=1,tolerance=1e-6)
        if any(recipe[k]!=v for k,v in expected.items()) or recipe['max_iterations']>120:
            raise ValueError('R1_FROZEN_CONTROLLER_COMPUTATION_LIMITS_REQUIRED')
        if not final_fidelity_matches(s['spec'],candidate):
            raise ValueError('R1_FINAL_FIDELITY_REQUIRED_BEFORE_PHYSICAL_LAUNCH')
        prior=[(host.store.artifact(r),route) for key,route in
            (('results','execute'),('physical_replays','physical_replay')) for r in s.get(key,[])]
        if (sum(route=='execute' for _,route in prior)!=s.get('nmpc_launches',0) or
                sum(route=='physical_replay' for _,route in prior)!=s.get('physical_replay_launches',0)):
            raise ValueError('R1_UNSETTLED_PHYSICAL_OPPORTUNITY_REQUIRES_REVIEW')
        used=[(host.store.artifact(p['candidate'])['physical_design_identity'],route) for p,route in prior]
        physical=candidate['physical_design_identity']
        reference=host.store.artifact(s['control_initializations'][0]['candidate'])['physical_design_identity']
        if len({reference,physical,*(p for p,_ in used)})>2 or (physical,action) in used:
            raise ValueError('R1_TWO_STRUCTURES_ONE_NMPC_ONE_REPLAY_EACH')
        record(host,'supervisor_physical_preflight',dict(candidate=ref,action=action,
            request_id=request_id,physical_design_identity=physical,prior_opportunities=used,admitted=True))
    return original_dispatch(host,value,request_id,**kwargs)


def supervised_analysis(host, query, key, **kwargs):
    # Completed operation IDs retain original idempotent receipts and zero extra cost.
    if host.store.lookup(host.run_id,key+'-analysis') or query.get('model_source')!='mujoco' or not query.get('candidate'):
        return original_analysis(host,query,key,**kwargs)
    guard(host,True)
    s=state(host);candidate=verify_candidate(host,query['candidate'])
    prior=[host.store.artifact(r) for r in s.get('analysis_results',[])]
    native=[r for r in prior if r.get('requested_operation',{}).get('model_source')=='mujoco']
    if any(r.get('status') not in ('computed','not_applicable') for r in native):
        raise ValueError('R1_NATIVE_PARTIAL_COST_REQUIRES_REVIEW_BEFORE_NEW_LAUNCH')
    used=sum(r.get('native_dynamics',{}).get('cost',{}).get('physics_steps',0) for r in native)
    cfg=candidate['configuration'];duration=cfg['task']['timing']['duration_s'];dt=cfg['task']['timing']['timestep_s']
    full_steps=round(duration/dt)
    if query.get('operation')=='mujoco_direct_control_v1':
        done=[r for r in native if r.get('operation')=='mujoco_direct_control_v1' and r.get('charged_analysis_evaluations',0)]
        physical=candidate['physical_design_identity']
        if len(done)>=2 or any(host.store.artifact(r['candidate'])['physical_design_identity']==physical for r in done):
            raise ValueError('R1_NATIVE_OPTIMIZATION_TWO_TOTAL_ONE_PER_STRUCTURE')
        settings=(query.get('control_optimization') or {}).get('settings',{})
        if 'evaluation_requests' not in settings:return original_analysis(host,query,key,**kwargs)
        upper=full_steps*(settings['evaluation_requests']+1)  # Includes any saved-state prefix.
    else:
        channels=len(cfg['robot']['structure']['data']['tendons'])
        horizon=(query.get('native') or {}).get('horizon_s',.01)
        # Existing native kernels: at most three model prefixes, four FD probes
        # per channel, one baseline and one optional correction, or 3 branches.
        upper=3*full_steps+max(3,2+4*channels)*math.ceil(horizon/dt)
    if used+upper>60000:raise ValueError('R1_NATIVE_PHYSICS_STEPS_LIMIT: remaining='+str(60000-used)+' conservative_request_upper='+str(upper))
    record(host,'supervisor_native_preflight',dict(request_id=key,candidate=query['candidate'],
        previous_actual_steps=used,request_upper_steps=upper,study_limit=60000,admitted=True,
        accounting='Derived from original analysis receipts; not an additional ledger or charge'))
    return original_analysis(host,query,key,**kwargs)


def main():
    host=Host(ROOT/'runs/research'/RUN,RUN,actor='unified-research');guard(host)
    reviewed='--reviewed' in sys.argv[1:]
    if reviewed:
        pauses=[e for e in host.store.events(RUN) if e['kind']=='supervisor_pause']
        if not pauses:raise ValueError('R1_REVIEW_REQUIRES_ORIGINAL_SETTLED_SUPERVISOR_PAUSE')
        record(host,'supervisor_budget_review',dict(pause=pauses[-1]['outputs'][0],
            budget=host.store.remaining(),additional_budget=0,protected_provider_requests=4,
            decision='Continue same Agent within original scope and remaining counts; no scientific direction supplied'))
    core.dispatch=supervised_dispatch;analysis.dispatch=supervised_analysis
    record(host,'supervisor_run',dict(pid=os.getpid(),runner=__file__,
        scope='M2 legality supervision with R1 caps; original CLI, Agent, Store, Worker and ledger'))
    sys.argv=['tools.research','run','--run-id',RUN,'--session-handoff','--handoff-request-bytes','160000']
    if not reviewed:sys.argv+=['--pause-exploration-remaining','4']
    runpy.run_module('tools.research',run_name='__main__')


if __name__=='__main__':main()
