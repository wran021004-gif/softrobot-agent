"""Two actual GVS state updates through the production NMPC workspace."""
import argparse
import gzip
import json
import os
import platform
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import casadi as ca
import numpy as np
import scipy
from scipy.integrate import solve_ivp
from extensions.optimization.ipopt import IpoptSolver, _violation
from extensions.tendon_family.contracts import GVSModelParameters, GVSTrajectoryParameters
from extensions.tendon_family.gvs import GVSModel
from extensions.tendon_family.gvs_casadi import expression_from_system, functions_for
from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace
from schemas.platform import RobotDescription, TaskDefinition
from schemas.platform_math import OptimizationProblem, SystemContext
from tools.state_io import atomic_json, digest

ARCHIVE=ROOT/'runs/stage313_trajectory_cost_20260926'
HERE=Path(__file__).resolve().parent

def read(path):return json.loads(path.read_text(encoding='utf8'))
def timed(fn):
    start=time.perf_counter();value=fn();return value,time.perf_counter()-start

def run(output):
    output.mkdir(parents=True,exist_ok=True)
    if (output/'configuration.json').exists():raise ValueError('Use a fresh --output directory to preserve evidence')
    save=lambda name,value:atomic_json(output/(name+'.json'),value)
    fixed=read(ARCHIVE/'fixed_problem.json');bootstrap=read(ARCHIVE/'trajectory.json')
    assert bootstrap['usable'] and bootstrap['reference_scaled_violation']<=1e-5
    robot=RobotDescription.model_validate(fixed['robot']);task=TaskDefinition.model_validate(fixed['task'])
    parameters=GVSTrajectoryParameters.model_validate({**fixed['arguments']['assembler']['parameters']['data'],
        'max_cpu_s':30.,'constraint_jacobian_mode':'reverse'})
    x=np.array(fixed['arguments']['context']['x0']);previous=np.array(fixed['arguments']['context']['u0'])
    n=len(x)//2;m=len(previous);dt=task.timing.control_period_s
    assert parameters.horizon==5 and parameters.substeps==1 and dt==.01 and np.all(x==0)
    save('configuration',dict(robot=fixed['robot'],task=fixed['task'],parameters=parameters.model_dump(mode='json'),
        model_parameters=GVSModelParameters(basis=parameters.basis).model_dump(mode='json'),
        nominal_x=x.tolist(),nominal_u=previous.tolist(),bootstrap_reference=str((ARCHIVE/'trajectory.json').relative_to(ROOT)),
        bootstrap_digest=digest(bootstrap),bootstrap_kind='archived bootstrap evidence, not a new initial solve',
        reference_problem=str((ARCHIVE/'reference_problem.json.gz').relative_to(ROOT)),
        acceptance_scaled_violation=1e-5,simulated_updates_s=[.01,.02],
        integration=dict(method='scipy BDF with exact CasADi AD state Jacobian of nonlinear mass/force dynamics',rtol=1e-7,atol=1e-8,held_input=True),
        environment=dict(interpreter=sys.executable,python=sys.version,platform=platform.platform(),
            numpy=np.__version__,scipy=scipy.__version__,casadi=ca.__version__,
            threads={k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')})))
    print('Constructing production workspace',flush=True)
    workspace,workspace_s=timed(lambda:TrajectoryWorkspace(task,robot,parameters,x.tolist(),previous.tolist()))
    workspace.last=bootstrap
    def reference():
        with gzip.open(ARCHIVE/'reference_problem.json.gz','rt',encoding='utf8') as stream:
            problem=OptimizationProblem.model_validate(json.load(stream))
        return problem,ca.Function.deserialize(problem.objective_function.data['serialized_function'])
    (reference_problem,original),reference_s=timed(reference)
    order=reference_problem.objective_function.data['variable_order']
    assert order==workspace.problem.objective_function.data['variable_order']
    assert reference_problem.variables==workspace.problem.variables
    assert [(c.name,c.lower,c.upper,c.units) for c in reference_problem.constraints]==[(c.name,c.lower,c.upper,c.units) for c in workspace.problem.constraints]
    def integration_functions():
        p=GVSModelParameters(basis=parameters.basis)
        system=GVSModel(p).build_system(robot,p,None,SystemContext(x0=x.tolist(),u0=previous.tolist(),scene=task.environment))
        functions=functions_for(expression_from_system(system))
        sx=ca.MX.sym('integrated_state',2*n);su=ca.MX.sym('held_tension',m)
        terms=functions.implicit_terms(x=sx,u=su)
        rhs=ca.vertcat(sx[n:],ca.solve(terms['mass'],terms['force']))
        return ca.Function('held_rhs',[sx,su],[rhs]),ca.Function('held_jacobian',[sx,su],[ca.jacobian(rhs,sx)])
    print('Constructing accurate integration functions',flush=True)
    (rhs,jac),integration_construction_s=timed(integration_functions)
    save('construction',dict(workspace_s=workspace_s,graph_s=workspace.graph_s,
        reference_deserialization_s=reference_s,integration_functions_s=integration_construction_s))
    scales=workspace.state_scales;limits=np.array([t['force_limit_n'] for t in robot.structure.data['tendons']])
    accepted_plan=bootstrap;summary=[]
    for update in (1,2):
        command=np.asarray(accepted_plan['tensions'][0]);old=x.copy()
        print('Integrating held input to',update*dt,flush=True)
        interval,integration_s=timed(lambda:solve_ivp(lambda t,y:np.asarray(rhs(y,command)).ravel(),
            ((update-1)*dt,update*dt),old,method='BDF',jac=lambda t,y:np.asarray(jac(y,command)),rtol=1e-7,atol=1e-8))
        if not interval.success:raise RuntimeError(interval.message)
        x=interval.y[:,-1];previous=command
        predicted=np.asarray(accepted_plan['states'][parameters.substeps])
        state_record=dict(simulated_time_s=update*dt,initial_state=old.tolist(),applied_tensions_n=command.tolist(),
            integrated_state=x.tolist(),preceding_prediction=predicted.tolist(),
            prediction_difference_q_max_rad_m=float(max(abs(x[:n]-predicted[:n]))),
            prediction_difference_rate_max_rad_m_s=float(max(abs(x[n:]-predicted[n:]))),
            prediction_difference_scaled_max=float(max(abs((x-predicted)/scales))),
            integration_s=integration_s,nfev=interval.nfev,njev=interval.njev,nlu=interval.nlu,
            integration_success=interval.success,message=interval.message)
        save('propagation_'+str(update),state_record)
        print('Integrated',integration_s,'s; solving update',update,flush=True)
        start=time.perf_counter();plan=workspace.solve(x,previous)
        workspace_return_s=time.perf_counter()-start
        diagnostics=plan['diagnostics']
        assert diagnostics['constraint_derivative']=='CasADi exact AD (reverse)'
        assert diagnostics['cached_solver']==(update==2)
        # Reference residuals are frozen, but initial/previous bounds must be current.
        for j,value in enumerate(x):reference_problem.variables[f'x/0/{j}']['bounds']=[float(value)/scales[j]]*2
        for t,value in zip(workspace.tendons,previous):reference_problem.variables['previous_u/'+t]['bounds']=[float(value)]*2
        assert reference_problem.variables==workspace.problem.variables
        lower,upper,_=IpoptSolver._bounds(reference_problem,order)
        lbg=[c.lower for c in reference_problem.constraints];ubg=[c.upper for c in reference_problem.constraints]
        verified={}
        def verify(vector):
            vector=np.asarray(vector);key=vector.tobytes()
            if key not in verified:
                began=time.perf_counter();objective,g=original(vector);g=np.asarray(g).ravel();values=dict(zip(order,vector))
                states=np.array([[values[f'x/{k}/{j}']*scales[j] for j in range(2*n)] for k in range(6)])
                tensions=np.array([[values[f'u/{k}/{t}'] for t in workspace.tendons] for k in range(5)])
                finite=bool(np.isfinite(np.r_[vector,g,float(objective)]).all())
                violation=_violation(vector,g,lower,upper,lbg,ubg)
                verified[key]=dict(reference_objective=float(objective),maximum_scaled_violation=violation,
                    dynamics_scaled_violation=float(max(abs(g))),finite_states_inputs=finite,
                    initial_state_equality_error=float(max(abs(states[0]-x))),
                    previous_input_equality_error=float(max(abs(values['previous_u/'+t]-v) for t,v in zip(workspace.tendons,previous))),
                    tendon_bound_violation_n=float(max(0.,np.max(-tensions),np.max(tensions-limits))),
                    tension_min_n=float(tensions.min()),tension_max_n=float(tensions.max()),
                    independently_feasible=finite and violation<=1e-5,validation_s=time.perf_counter()-began)
            return verified[key]
        selected_vector=np.array([plan['result']['optimum'][k] for k in order])
        selected=verify(selected_vector)
        first=diagnostics['first_feasible_candidate']
        first_check=None if first is None else verify(first['x'])
        validated_delivery_s=time.perf_counter()-start
        accepted=plan['accepted'] and selected['independently_feasible']
        # Verify actual shift indices, scales, initial bounds and previous input.
        guess=workspace.problem.initial_guess
        expected_u=np.vstack([np.asarray(accepted_plan['tensions'])[1:],accepted_plan['tensions'][-1]])
        np.testing.assert_allclose([[guess[f'u/{k}/{t}'] for t in workspace.tendons] for k in range(5)],expected_u,atol=0,rtol=0)
        for k in range(1,5):
            np.testing.assert_allclose([guess[f'x/{k}/{j}']*scales[j] for j in range(2*n)],accepted_plan['states'][k+1],atol=1e-12,rtol=1e-12)
        save('update_'+str(update),dict(plan=plan,warm_start_vector=[guess[k] for k in order],
            verification=dict(first=first_check,selected=selected,unique_reference_evaluations=len(verified)),
            workspace_return_s=workspace_return_s,validated_plan_delivery_s=validated_delivery_s,
            accepted=accepted,simulated_time_s=update*dt))
        row=dict(simulated_time_s=update*dt,initial_violation=diagnostics['initial_scaled_violation'],
            first=None if first is None else {k:first[k] for k in ('iteration','elapsed_s','iteration_zero')},
            selected=None if diagnostics['selected_feasible_candidate'] is None else {k:diagnostics['selected_feasible_candidate'][k] for k in ('iteration','elapsed_s','iteration_zero')},
            solve_s=diagnostics['solve_s'],violation=selected['maximum_scaled_violation'],objective=selected['reference_objective'],
            solver_status=plan['result']['status'],raw_status=diagnostics['return_status'],
            raw_final_violation=diagnostics['returned_iterate_constraint_violation'],accepted=accepted,
            integration_s=integration_s,workspace_return_s=workspace_return_s,validated_plan_delivery_s=validated_delivery_s)
        summary.append(row);save('summary',dict(updates=summary,two_usable_updates=len(summary)==2 and all(r['accepted'] for r in summary)))
        print(json.dumps(row),flush=True)
        if not accepted:
            print('Unusable new plan; stopping sequence for focused diagnosis.',flush=True);break
        accepted_plan=plan

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=HERE)
    args=parser.parse_args();run(args.output.resolve())
