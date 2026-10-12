"""fc1012: bounded fixed-structure work using the existing ledger and workers."""
import argparse
from copy import deepcopy
import json
import math
import time
from tools import research_core as core
from tools import numerical_repair as repair
from tools import research_core_numerics as numerics
from tools.platform_host import Host
from tools.state_io import atomic_json,digest

SPEC=core.ROOT/'examples/fixed_task_milestone/specification.json'
HISTORY='evidence/numerical_repair_20261012'


def host():
    spec=core.read(SPEC)
    return Host(core.ROOT/'runs'/spec['study_id'],spec['study_id'],actor='unified-research')


def local(h,update,iterations,key,current=False):
    result=core.local_diagnostic(h,dict(execution=core.state(h)['repair_history']['records'][str(update)],
        update_id=update,mode='research_current' if current else 'research_policy',iteration_cap=iterations,
        repetitions=1,prepare_tail=True),key)
    value=result['rows'][0]
    return dict(reference=result['reference'],status=value.get('status'),
        iterations=value.get('diagnostics',{}).get('iterations'),
        termination=value.get('diagnostics',{}).get('return_status'),
        cost_s=value['charged_numerical_s'],verification=value.get('verification',{}).get('scaled_violation'),
        plans=value.get('task_plans'),action=value.get('first_input_n'))


def estimate(h,reference):
    """Estimate each update from measured construction, solve and recovery costs.

    Historical costs supply update-shape variation; a fresh same-configuration
    local check calibrates the new work limit/horizon/mesh. Watchdogs include a
    35% margin and protect two full launches until a passing source is selected.
    """
    s=core.state(h);v=h.store.artifact(reference)['rows'][0]
    if v.get('status') or not v.get('diagnostics'):raise ValueError('COMPLETED_CALIBRATION_REQUIRED')
    request=core.read(next((h.store.root/'local_diagnostics'/v['execution_id']).glob('input.json')))
    recipe=deepcopy(request['configuration']['policy']['controller']['parameters']['data']['recipe'])
    if request['mode']=='research_current':recipe.update(request['current_recipe'])
    recipe['max_iterations']=request['iteration_cap']
    if recipe!=s['profile']['recipe']:raise ValueError('CALIBRATION_RECIPE_MUST_MATCH_SELECTED_RECIPE')
    summary=core.read(core.ROOT/HISTORY/'scientific_summary.json')
    old=next(r for r in summary['physical'] if r['execution_id']==s['repair_history']['source_execution'])
    source=numerics.execution_source(old,HISTORY)
    observations=numerics.archived(HISTORY,source['files']['controller_observations.json'])
    original=observations[v['source_update_id']]
    diagnostics=v['diagnostics'];warm=v.get('actual_workspace_output',{}).get('warm_start',{}).get('preparation_s',original['warm_preparation_s'])
    recovery=v.get('recovery',{}).get('wall_s',0.)
    fresh_update=diagnostics['solve_s']+diagnostics['validation_s']+recovery+warm
    baseline_update=original['optimization_solve_s']+original['plan_validation_s']+original['recovery_wall_s']+original['warm_preparation_s']
    ratio=fresh_update/baseline_update
    predicted=sum(o['update_wall_s'] for o in observations)*ratio
    construction=diagnostics.get('construction_s',0.)+v.get('construction_s',0.)
    # Conservative first construction and preparation, plus complete evidence.
    predicted+=construction+60.
    simulation=math.ceil(predicted*1.35)
    overhead=sum(value for name,value in s['spec']['execution_allowances'].items() if name!='simulation_s')
    value=dict(recipe_identity=digest(recipe),recipe=recipe,science_hashes=s['profile']['science_hashes'],
        measured_calibration=reference,source_update_id=v['source_update_id'],fresh_update_s=fresh_update,
        historical_matched_update_s=baseline_update,measured_cost_ratio=ratio,
        predicted_simulation_s=predicted,simulation_watchdog_s=simulation,total_watchdog_s=simulation+overhead,
        safety_margin=1.35,estimated_unix=time.time(),
        method='Fresh matched configuration calibrated against all 35 measured historical update costs; overhead and 35% margin',
        uncertainty='One saved-state calibration; watchdog is conservative and interruptions remain incomplete')
    ref=core.save(h,value,'configuration_execution_cost_estimate')
    core.update(h,execution_cost_estimate=value,cost_estimates=[*s.get('cost_estimates',[]),ref])
    return dict(reference=ref,**value,admission=core.capacity(h))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['prepare','import','local','solve','verify','rollout','estimate','execute','repeat','status','recover'])
    parser.add_argument('--update',type=int,default=29);parser.add_argument('--iterations',type=int,default=3)
    parser.add_argument('--substeps',type=int,default=32);parser.add_argument('--key',default='')
    parser.add_argument('--source');parser.add_argument('--current',action='store_true');args=parser.parse_args()
    h=core.prepare(SPEC) if args.command=='prepare' else host();s=core.state(h)
    if args.command=='prepare':value=dict(prepared=h.run_id)
    elif args.command=='import':value=repair.history_inputs(h,folder=HISTORY,
        execution_id=s['spec']['baseline_execution_id'],offline_execution_id=s['spec']['baseline_offline_execution_id'])
    elif args.command=='local':value=local(h,args.update,args.iterations,args.key,args.current)
    elif args.command=='recover':value=core.recover(h)
    elif args.command=='status':value=dict(pending=s['pending'],numerical_s=s['numerical_s'],local_solves=s['local_solves'],
        local_solve_s=s['local_solve_s'],offline_nlp=s['offline_nlp'],bdf_replays=s['bdf_replays'],
        full_executions=len(s['results']),activity_s=time.time()-s['started_unix'],admission=core.capacity(h))
    elif args.command=='estimate':value=estimate(h,repair.reference(args.source))
    elif args.command=='execute':value=core.execute(h,s['reference_candidate'],args.key,role='fixed_validation')
    elif args.command=='repeat':
        ref=repair.reference(args.source);row=h.store.artifact(ref)
        if not (row.get('acceptance') or {}).get('accepted'):raise ValueError('FAILED_FULL_RUN_MUST_NOT_BE_REPEATED')
        value=core.execute(h,row['candidate'],args.key,role='engineering_repetition',selected=ref)
    else:
        source=repair.reference(args.source) if args.source else s['repair_history']['mechanics']
        if args.command=='solve':
            from schemas.casadi_feedback import Candidate
            d=s['spec']['reference_parameters']['d']
            payload=Candidate(design_bounds=(d,d),design_initial=d,initialization='saved_schedule',source_candidate=source,
                **s['spec']['offline_recipe']).model_dump(mode='json');operation='solve'
        else:
            payload=dict(source=source);operation='integrate'
            if args.command=='verify':payload.update(method='BDF')
            else:payload.update(integration_method='implicit_midpoint',substeps=args.substeps)
        value=numerics.experiment(h,operation,payload,args.key,
            'Repair midpoint all-node consistency with fixed physical task and matched schedule',
            'Offline internal resolution only; NMPC resolution is selected separately',
            'Original physical zero state, material, tendon order, 35 commands at .01s and unchanged acceptance',
            'Require numerical feasibility, independent sampled task and all-node vector consistency separately')
    atomic_json(h.store.root/'last_operation.json',value)
    if args.command in ('solve','verify','rollout'):value={k:v for k,v in value.items() if k not in ('handoff','replay')}
    print(json.dumps(value,ensure_ascii=True))


if __name__=='__main__':main()
