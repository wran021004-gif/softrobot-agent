"""Re-solve actual recorded update inputs; no preparation or guessed warm vector."""
import json
from pathlib import Path
import sys
import time
import numpy as np
from schemas.platform import SessionInput
from tools.state_io import read, atomic_json, digest
from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace


def replay(request):
    started=time.perf_counter(); inp=SessionInput.model_validate(request['configuration'])
    recorded=request['record']; recipe=dict(inp.policy.controller.parameters.data['recipe'])
    recipe['horizon']=recorded['effective_horizon']
    n=len(recorded['coordinate_order'])
    ws=TrajectoryWorkspace(inp.task,inp.robot,recipe,[0.]*(2*n),[.2]*len(recorded['tendon_order']),
        settling=inp.policy.controller.parameters.data['settling'])
    ws.problem.variables.clear(); ws.problem.variables.update(recorded['problem_variables'])
    ws.problem.initial_guess.clear(); ws.problem.initial_guess.update(recorded['initial_guess'])
    ws.solver.complete_record=True;ws.solver.diagnostic_trace=True
    if request['mode']=='fixed_iteration': ws.solver.diagnostic_work_cap=request['iteration_cap']
    result=ws.solver.solve(ws.problem,seed_settled=recorded['warm_preparation']['seed_settled'])
    selected=dict(result.optimum)
    result,recovery=ws._recover_returned(result,recorded['measured_state'])
    check=ws.solver.evaluate_candidate(ws.problem,result.optimum)
    return dict(mode=request['mode'],production_stopping_policy_unchanged=request['mode']=='production',
        iteration_cap=request['iteration_cap'] if request['mode']=='fixed_iteration' else None,
        original_input_identity=recorded['initialization_identity'],
        exact_initialized_vector_equal=ws.solver.last_input_record['initialized_vector']==recorded['initialization']['initialized_vector'],
        exact_variable_order_equal=ws.solver.last_input_record['variable_order']==recorded['initialization']['variable_order'],
        exact_bounds_equal=all(ws.solver.last_input_record[k]==recorded['initialization'][k] for k in ('variable_lower','variable_upper')),
        result=result.model_dump(mode='json'),raw_returned_plan=ws.solver.last_returned_optimum,
        selected_feasible_plan=selected,recovery=recovery,diagnostics=ws.solver.last_diagnostics,
        verification=check,first_input_n=[result.optimum['u/0/'+t] for t in recorded['tendon_order']],
        original_applied_action_n=recorded['actual_applied_action_n'],
        numerical_s=time.perf_counter()-started,
        qualification='Local identical-input comparison only; not physical task performance or unique causal attribution')


if __name__=='__main__':
    request=read(sys.argv[1]); out=Path(sys.argv[2])
    try: value=replay(request)
    except Exception as exc:value=dict(status='diagnostic_error',error=type(exc).__name__,message=str(exc))
    atomic_json(out,value)
