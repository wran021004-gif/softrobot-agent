"""Re-solve actual recorded update inputs; no preparation or guessed warm vector."""
import json
from pathlib import Path
import sys
import time
import numpy as np
from schemas.platform import SessionInput
from tools.state_io import read, atomic_json, digest
from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace
from schemas.platform_math import OptimizationProblem
from extensions.optimization.ipopt import IpoptSolver
from extensions.tendon_family.contracts import current_nmpc_recipe


def inspect_problem(ws,recorded):
    """Evaluate saved inputs/plans without calling a numerical optimizer."""
    # Artifact JSON sorts dictionary keys. The serialized expression retains
    # the numerical variable order used by the solver.
    order=ws.problem.objective_function.data['variable_order']
    initial={k:v for k,v in zip(order,recorded['initialization']['initialized_vector'])}
    check=ws.solver.evaluate_candidate(ws.problem,initial)
    selected=ws.solver.evaluate_candidate(ws.problem,recorded['selected_feasible_plan'])
    old=recorded['diagnostics']
    return dict(serialized_model_identity_equal=digest(ws.problem.objective_function.model_dump(mode='json'))==recorded['model_identity'],
        complete_original_problem_available='resolved_problem' in recorded,
        initial_objective=check['objective'],original_initial_objective=old['initial_objective'],
        initial_objective_difference=check['objective']-old['initial_objective'],
        initial_violation=check['scaled_violation'],original_initial_violation=old['initial_scaled_violation'],
        selected_objective=selected['objective'],original_selected_objective=old['selected_feasible_candidate']['objective'],
        maximum_selected_constraint_difference=max(abs(a-b) for a,b in zip(selected['constraint_values'],old['constraint_values'])),
        variable_order_equal=order==recorded['initialization']['variable_order'],
        constraint_order_equal=[c.name for c in ws.problem.constraints]==old['constraint_order'],
        constraint_bounds_equal=all((c.lower,c.upper)==(lo,hi) for c,lo,hi in zip(ws.problem.constraints,old['constraint_lower'],old['constraint_upper'])),
        prediction_timing=recorded['prediction_timing'],
        original_mutable_workspace=recorded['mutable_workspace'],
        reconstructed_mutable_workspace=dict(cached_solver=False,tail_solver_ready=ws._tail_solver is not None),
        original_recovery_selection=recorded.get('recovery'),
        qualification='Numeric agreement at saved points does not prove equality of every derivative or recreate timing/cache history.')


def replay(request):
    started=time.perf_counter()
    inp=SessionInput.model_validate(request['configuration'])
    recorded=request['record']
    recipe=dict(inp.policy.controller.parameters.data['recipe'])
    if recorded.get('resolved_problem_archive') and request['mode']!='research_current':
        from tools.research.numerics import archived
        recorded=dict(recorded,resolved_problem=archived(**recorded['resolved_problem_archive']))
    recipe['horizon']=recorded['effective_horizon']
    if request['mode']=='research_current':
        recipe.update(request['current_recipe'])
        if inp.policy.controller.version in ('7.0.0','8.0.0','9.0.0','10.0.0','11.0.0'):
            from extensions.tendon_family.gvs_nmpc import deadline_horizon
            recipe['horizon']=deadline_horizon(inp.task.timing.duration_s,recorded['prediction_timing']['current_time_s'],
                inp.task.timing.control_period_s,recipe['horizon'])
    policy=current_nmpc_recipe(recipe,request['current_recipe'])
    # Exact-problem mode changes stopping alone. Keep integration, costs and
    # recovery from the original robot/controller; never reconstruct its NLP.
    recipe.update({k:policy[k] for k in ('stopping_policy','max_iterations','tolerance','max_cpu_s','feasible_return')})
    n=len(recorded['coordinate_order'])
    nominal=recorded.get('nominal_workspace',dict(x=[0.]*(2*n),u=[.2]*len(recorded['tendon_order'])))
    ws=TrajectoryWorkspace(inp.task,inp.robot,recipe,nominal['x'],nominal['u'],
        settling=inp.policy.controller.parameters.data['settling'])
    ws.research_position_limit_m = inp.policy.controller.parameters.data['settling']['position_limit_m']
    ws.research_speed_limit_m_s = inp.policy.controller.parameters.data['settling']['speed_limit_m_s']
    if request['mode']=='research_current':
        # Use the actual solve/warm/tail/recovery path with a transformed saved
        # warm guess, not the old serialized Euler problem or old state defects.
        old_s=len(recorded['prediction_timing']['node_times_s'])//recorded['effective_horizon']
        old_x=np.array([[recorded['initial_guess'][f'x/{k}/{j}']*recorded['state_scales'][j]
            for j in range(2*n)] for k in range(recorded['effective_horizon']*old_s+1)])
        times=np.arange(len(old_x))/old_s
        new_times=np.arange(ws.parameters.horizon*ws.parameters.substeps+1)/ws.parameters.substeps
        warm=dict(states=np.stack([np.interp(new_times,times,old_x[:,j]) for j in range(2*n)],axis=1).tolist(),
            tensions=[[recorded['initial_guess'][f'u/{min(k,recorded["effective_horizon"]-1)}/{t}'] for t in recorded['tendon_order']] for k in range(ws.parameters.horizon)])
        ws.solver.complete_record=True
        value=ws.solve(recorded['measured_state'],recorded['previous_applied_input_n'],warm=warm,
            elapsed_s=recorded['prediction_timing']['current_time_s'])
        check=ws.solver.evaluate_candidate(ws.problem,value['result']['optimum'])
        command=[value['result']['optimum']['u/0/'+t] for t in recorded['tendon_order']]
        return dict(mode=request['mode'],result=value['result'],diagnostics=value['diagnostics'],recovery=value['recovery'],
            verification=check,first_input_n=command,delivered_tension_n=command,actual_workspace_output=value,
            task_plans={name:plan_task_metrics(ws,plan,recorded['prediction_timing']['current_time_s'])
                for name,plan in dict(raw=value['complete_update']['raw_returned_plan'],
                    selected=value['complete_update']['selected_feasible_plan'],recovered=value['complete_update']['recovery_candidate'],
                    delivered=value['complete_update']['delivered_plan']).items() if plan is not None},
            numerical_s=time.perf_counter()-started,source_saved_input=recorded['initialization_identity'],
            qualification='Same saved measurement/previous command and control schedule guess; current method regenerates states and constructs a new problem through the actual complete workspace path.')
    ws._set_prediction_time(recorded['prediction_timing']['current_time_s'])
    if 'resolved_problem' in recorded:
        ws.problem=OptimizationProblem.model_validate(recorded['resolved_problem'])
    ws.problem.variables.clear()
    ws.problem.variables.update(recorded['problem_variables'])
    ws.problem.initial_guess.clear()
    ws.problem.initial_guess.update(recorded['initial_guess'])
    if 'resolved_problem' not in recorded:
        raise ValueError('EXACT_ORIGINAL_PROBLEM_UNAVAILABLE_USE_EXPLICIT_RECONSTRUCTION')
    options=dict(recorded['initialization']['solver_options'])
    options.update(max_cpu_s=None,max_wall_s=None,feasible_return=None,
        max_iterations=policy['max_iterations'],tolerance=policy['tolerance'])
    ws.solver=IpoptSolver(options)
    inspection=inspect_problem(ws,recorded)
    ws.solver.complete_record=True
    # Original update 1 had tracing disabled. Do not add timed callbacks when
    # reconstructing production-policy behavior.
    ws.solver.diagnostic_trace=recorded.get('diagnostic_trace_enabled','iteration_trace' in recorded['diagnostics'])
    value=_solve_record(ws,recorded)
    value.update(mode=request['mode'],effective_stopping_policy=policy['stopping_policy'],
        problem_inspection=inspection,diagnostic_trace_enabled=ws.solver.diagnostic_trace,
        iteration_cap=policy['max_iterations'],
        stopping_controls=dict(options=options,callback_policy_enabled=False,
            may_stop_early_on_convergence=True,external_timeout_s=request['external_timeout_s']),
        solver_reused=False,problem_identity=digest(recorded['resolved_problem']),
        numerical_s=time.perf_counter()-started,
        qualification='Exact serialized problem, bounds and initialized vector; fresh solver instance. Timed normal returns disabled. Local comparison does not establish whole-episode repeatability.')
    return value


def _solve_record(ws,recorded):
    result=ws.solver.solve(ws.problem,seed_settled=recorded['warm_preparation']['seed_settled'])
    selected=dict(result.optimum)
    recovery=dict(enabled=ws.parameters.recover_returned_tensions,attempted=False,selected=False)
    if ws.parameters.recover_returned_tensions and result.status in ('converged','iteration_limit','feasible_early_stop'):
        result,recovery=ws._recover_returned(result,recorded['measured_state'])
    check=ws.solver.evaluate_candidate(ws.problem,result.optimum)
    usable=check['feasible'] and result.status in ('converged','iteration_limit','feasible_early_stop')
    return dict(
        original_input_identity=recorded['initialization_identity'],
        exact_initialized_vector_equal=ws.solver.last_input_record['initialized_vector']==recorded['initialization']['initialized_vector'],
        exact_variable_order_equal=ws.solver.last_input_record['variable_order']==recorded['initialization']['variable_order'],
        exact_bounds_equal=all(ws.solver.last_input_record[k]==recorded['initialization'][k] for k in ('variable_lower','variable_upper')),
        result=result.model_dump(mode='json'),raw_returned_plan=ws.solver.last_returned_optimum,
        selected_feasible_plan=selected,recovery=recovery,diagnostics=ws.solver.last_diagnostics,
        verification=check,first_input_n=[result.optimum['u/0/'+t] for t in recorded['tendon_order']],
        original_applied_action_n=recorded['actual_applied_action_n'],
        accepted_plan=result.optimum,
        delivered_tension_n=[result.optimum['u/0/'+t] for t in recorded['tendon_order']] if usable else None,
        usable_plan=bool(usable),termination=ws.solver.last_diagnostics['return_status'],
        construction_s=ws.graph_s,task_plans={name:plan_task_metrics(ws,plan,recorded['prediction_timing']['current_time_s'])
            for name,plan in dict(raw=ws.solver.last_returned_optimum,selected=selected,
                recovered=recovery.get('candidate_optimum'),delivered=result.optimum).items() if plan is not None})


def plan_task_metrics(ws,plan,time_s):
    ws._prepare_tail()  # Build output functions after solving; saved solve inputs remain untouched.
    times=time_s+np.arange(ws.parameters.horizon*ws.parameters.substeps+1)*ws.period/ws.parameters.substeps
    states=np.array([[plan[f'x/{k}/{j}']*ws.state_scales[j] for j in range(2*ws.n)] for k in range(len(times))])
    motion=[ws._motion(x[:ws.n],x[ws.n:]) for x in states]
    positions=np.array([np.asarray(p).ravel() for p,v in motion])
    velocities=np.array([np.asarray(v).ravel() for p,v in motion])
    hold=(times>=ws.holding_start-1e-12)&(times<=ws.duration+1e-12)
    errors=np.linalg.norm(positions-np.asarray(ws.target),axis=1)
    speeds=np.linalg.norm(velocities,axis=1)
    return dict(times_s=times.tolist(),position_error_m=errors.tolist(),speed_m_s=speeds.tolist(),
        holding_node_count=int(hold.sum()),holding_max_position_error_m=float(errors[hold].max()) if any(hold) else None,
        holding_max_speed_m_s=float(speeds[hold].max()) if any(hold) else None,
        holding_position_violation_m=float(max(0,errors[hold].max()-ws.research_position_limit_m)) if any(hold) else None,
        holding_speed_violation_m_s=float(max(0,speeds[hold].max()-ws.research_speed_limit_m_s)) if any(hold) else None,
        first_action_n=[plan['u/0/'+t] for t in ws.tendons],scope='Actual plan states; sampled prediction diagnostics, independent feasibility reported separately')


if __name__=='__main__':
    request=read(sys.argv[1])
    out=Path(sys.argv[2])
    try:
        value=replay(request)
    except Exception as exc:
        value=dict(status='diagnostic_error',error=type(exc).__name__,message=str(exc))
    atomic_json(out,value)

from tools.research.state import state,save,update
from tools.platform_store import zero
def recover_local(host):
    s=state(host)
    p=s['pending']
    out=Path(p['output'])
    if not out.exists():
        raise ValueError('UNKNOWN_LOCAL_SOLVE_RETAINS_RESERVATION_NO_REPEAT')
    value=read(out)
    row=host.store.lookup(host.run_id,p['worker_request_id'])
    charged=p['reserved_s']
    value.update(execution_id=row['execution_id'],charged_numerical_s=charged,
        source_execution=p['source_execution'],source_update_id=p['source_update_id'],owning_study=host.run_id,
        origin=p['origin'],historical_input=p['historical_input'],recovered_output_without_solve=True)
    with host.store.transaction() as db:
        current=host.store.session(host.run_id,db)['state']
        current.update(pending=None,
            numerical_s=current['numerical_s']+charged,local_solve_s=current['local_solve_s']+charged,
            numerical_reserved_s=current['numerical_reserved_s']-charged)
        host.store.update_state(db,host.run_id,current)
        host.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=host.actor,
            tool_id='research.core_local_solve',tool_version='1.0.0',execution_status='completed',charged=zero()),value,elapsed=charged,db=db)
    return value


from tools.research.state import (ROOT, state, update, save, guard)
from tools.platform_store import plain, zero
import os, subprocess

def diagnose(host, refs):
    from extensions.tendon_family.control_evidence import ControlEvidence
    s=state(host)
    reader=ControlEvidence(host.store)
    records=[]
    numerical=[]
    incomplete=[]
    for ref in refs:
        r=host.store.artifact(ref)
        if plain(ref) not in s['results'] and r.get('status')=='evaluated':
            from tools.research.feedback import result_view
            numerical.append(dict(reference=plain(ref),historical=True,**result_view(host,ref)))
            continue
        if plain(ref) in s.get('mechanics_results',[]):
            numerical.append(dict(reference=plain(ref),physical_validation=False,**{k:r.get(k) for k in
                ('operation','status','execution_id','trajectory_metrics','relaxed_nlp_feasible','original_task_feasible','replay','charged_numerical_s')}))
            continue
        if plain(ref) in s['results'] and r.get('status')!='evaluated':
            incomplete.append(dict(reference=plain(ref),**compact_result(r),acceptance_available=False,
                archived_partial_evidence=s.get('incomplete_execution_evidence',[])))
            continue
        if not r.get('execution_id') or r.get('status')!='evaluated':
            continue
        source=reader.resolve(r['execution_id'])
        obs=reader.read_file(source,'controller_observations.json',[])
        records.append(dict(execution_id=r['execution_id'],observations=obs,source=source,
            scientific_configuration=r.get('scientific_configuration'),profile_identity=r.get('profile_identity')))
    comparison=[]
    if len(records)>=2:
        a,b=records[-2:]
        left=a['observations']
        right=b['observations']
        for index,(x,y) in enumerate(zip(left,right)):
            if x['actual_tension_n']!=y['actual_tension_n']:
                rx=x.get('complete_update_record',{})
                ry=y.get('complete_update_record',{})
                comparison.append(dict(update_id=index,time_s=x['time_s'],
                    scientific_configuration_equal=a['scientific_configuration']==b['scientific_configuration'],
                    evaluation_profile_equal=a['profile_identity']==b['profile_identity'],
                    maximum_action_difference_n=max(abs(i-j) for i,j in zip(x['actual_tension_n'],y['actual_tension_n'])),
                    measured_state_equal=x['measured_initial_state']==y['measured_initial_state'],
                    previous_input_equal=rx.get('previous_applied_input_n')==ry.get('previous_applied_input_n'),
                    warm_source_equal=rx.get('warm')==ry.get('warm'),
                    initialized_vector_equal=rx.get('initialization',{}).get('initialized_vector')==ry.get('initialization',{}).get('initialized_vector'),
                    selection=[rx.get('selection'),ry.get('selection')],iterations=[x.get('optimization_selected_iteration'),y.get('optimization_selected_iteration')]))
    value=dict(status='read_only_diagnosis',sources=refs,
        numerical_evidence=numerical,incomplete_executions=incomplete,
        execution_evidence=[dict(execution_id=r['execution_id'],source=r['source'],updates=len(r['observations']),
            complete_records=sum('complete_update_record' in o for o in r['observations']),
            capture_s=sum(o.get('complete_record_capture_s',0.)+o.get('complete_update_record',{}).get('record_capture_s',0.)+o.get('snapshot_capture_wall_s',0.) for o in r['observations'])) for r in records],
        first_action_divergence=comparison[0] if comparison else None,action_divergences=comparison,
        unique_cause='unresolved; equality and differences are recorded, no causal rule imposed')
    ref=save(host,value,'diagnosis')
    update(host,diagnostic_facts=[*state(host).get('diagnostic_facts',[]),dict(reference=ref,
        status=value['status'],first_action_divergence=value['first_action_divergence'],
        numerical_evidence=numerical,incomplete_executions=incomplete,
        unique_cause=value['unique_cause'],execution_evidence=[{k:r[k] for k in ('execution_id','updates','complete_records','capture_s')} for r in value['execution_evidence']])])
    return dict(reference=ref,**value)


def local_diagnostic(host, query, key):
    guard(host,True)
    from tools.research.contracts import LocalDiagnostic
    from tools.research.numerics import execution_update
    q=LocalDiagnostic.model_validate(query)
    s=state(host)
    b=s['spec']['budgets']
    source=execution_update(host,q.execution,q.update_id)
    record=source['record']
    imported=source.get('imported_historical_evidence',False)
    if not record:
        raise ValueError('ACTUAL_COMPLETE_UPDATE_INPUT_REQUIRED')
    seconds=s['spec']['standalone_watchdog_s']
    reserve=0.
    solves=q.repetitions
    if s['local_solves']+solves>b['local_solves']:
        raise ValueError('LOCAL_DIAGNOSTIC_COUNT_EXHAUSTED')
    rows=[]
    for index in range(q.repetitions):
        request_id=key+'-local-'+str(index)
        request=dict(configuration=source['configuration'],record=record,mode=q.mode,
            current_recipe=s['profile']['recipe'],external_timeout_s=seconds,
            numerical_environment=dict(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1'))
        old=host.store.lookup(host.run_id,request_id)
        if old:
            if old['request_hash']!=digest(request):
                raise ValueError('DIAGNOSTIC_OPERATION_COLLISION')
            if not old['receipt']:
                raise ValueError('UNKNOWN_LOCAL_SOLVE_RECONCILE_OUTPUT_NO_REPEAT')
            rows.append(host.store.artifact(json.loads(old['receipt'])['output']))
            continue
        def charge(db):
            current=host.store.session(host.run_id,db)['state']
            count=1
            if current['local_solves']+count>b['local_solves']:
                raise ValueError('LOCAL_SOLVE_CEILING')
            current['local_solves']+=count
            current['numerical_reserved_s']+=reserve
            host.store.update_state(db,host.run_id,current)
        row,_=host.store.reserve(host.run_id,request_id,digest(request),host.actor,{**zero(),'wall_s':reserve},kind='local_diagnostic',guard=charge)
        folder=host.store.root/'local_diagnostics'/row['execution_id']
        folder.mkdir(parents=True,exist_ok=True)
        inp,out=folder/'input.json',folder/'output.json'
        atomic_json(inp,request)
        update(host,pending=dict(kind='local_diagnostic',worker_request_id=request_id,input=str(inp),output=str(out),
            reserved_s=reserve,source_execution=plain(q.execution),source_update_id=q.update_id,historical_input=imported,
            started_unix=time.time(),origin='engineering' if s['spec'].get('mode')=='engineering_numerical' or key.startswith('engineering') else 'model'))
        start=time.perf_counter()
        env=os.environ.copy()
        env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
        try:
            process=subprocess.run([str(s['spec']['runtime']['research_python']),'-m','tools.research.diagnostic',str(inp),str(out)],cwd=ROOT,
                env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=seconds)
            value=read(out) if out.exists() else dict(status='diagnostic_no_output',returncode=process.returncode)
        except subprocess.TimeoutExpired:
            value=dict(status='known_killed_waited_diagnostic_timeout',timeout_s=seconds)
        elapsed=time.perf_counter()-start
        value.update(execution_id=row['execution_id'],charged_numerical_s=elapsed,source_execution=plain(q.execution),
            implementation=s['freeze'],science_hashes=s['profile']['science_hashes'],
            original_request=save(host,request,'local_diagnostic_request'),
            historical_input=imported,owning_study=host.run_id,
            source_update_id=q.update_id,origin='engineering' if s['spec'].get('mode')=='engineering_numerical' or key.startswith('engineering') else 'model',
            charged_solve_attempts=1)
        with host.store.transaction() as db:
            current=host.store.session(host.run_id,db)['state']
            current['numerical_s']+=elapsed
            current['local_solve_s']+=elapsed
            current['numerical_reserved_s']-=reserve
            current['pending']=None
            host.store.update_state(db,host.run_id,current)
            host.store.complete(row,dict(request_id=request_id,execution_id=row['execution_id'],caller=host.actor,
                tool_id='research.core_local_solve',tool_version='1.0.0',execution_status='completed',charged=zero()),value,elapsed=elapsed,db=db)
        rows.append(value)
    difference=max(abs(a-b) for a,b in zip(rows[0]['first_input_n'],rows[1]['first_input_n'])) if len(rows)==2 and all('first_input_n' in r for r in rows) else None
    detail=dict(rows=rows,maximum_first_input_difference_n=difference,mode=q.mode,
        interpretation='Exact saved problem under declared iteration/convergence policy; local agreement does not establish episode repeatability or unique cause.')
    ref=save(host,detail,'local_diagnostic_comparison')
    update(host,diagnostics=[*state(host).get('diagnostics',[]),ref])
    return dict(reference=ref,**detail)
