"""Fixed five-interval GVS computation experiment; no backend execution."""
import argparse
import cProfile
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
from examples.platform_fixtures import project
from extensions.optimization.ipopt import IpoptSolver
from extensions.tendon_family.gvs_trajectory import trajectory_authorization
from schemas.platform import SessionInput
from schemas.platform_math import OptimizationProblem
from tools.platform_host import Host
from tools.platform_store import Store
from tools.state_io import atomic_json,digest

HERE=Path(__file__).resolve().parent
REFERENCE=HERE/'reference_problem.json.gz'
OLD=ROOT/'runs/stage312_to_nmpc_20260926'
def read(path):return json.loads(path.read_text(encoding='utf8'))
def save(name,value):atomic_json(HERE/(name+'.json'),value)
def timed(fn):
    start=time.perf_counter();value=fn();return value,time.perf_counter()-start

def reference_problem():
    with gzip.open(REFERENCE,'rt',encoding='utf8') as stream:
        return OptimizationProblem.model_validate(json.load(stream))

def setup():
    raw=read(ROOT/'runs/stage35_case_b_retry_softagent_20260924/inputs/route.json')
    frozen=read(ROOT/'runs/stage311_discretization_convergence_20260926/discretization_convergence.json')['frozen_reference']
    archive=read(OLD/'offline_trajectory.json');seed=read(OLD/'offline_scaled_candidate.json')
    parameters=archive['parameters'];n=len(frozen['q0']);u=frozen['u0_n'];x=[0.]*(2*n)
    scales=[parameters['curvature_scale_rad_m']]*n+[parameters['rate_scale_rad_m_s']]*n
    guess={f'x/{k}/{j}':float(v)/scales[j] for k,row in enumerate(seed['states']) for j,v in enumerate(row)}
    guess.update({f'u/{k}/{t}':float(v) for k,row in enumerate(seed['tensions']) for t,v in zip(frozen['tendon_order'],row)})
    guess.update({'previous_u/'+t:v for t,v in zip(frozen['tendon_order'],u)})
    raw['policy'].update(route=None,allowed_tools=['optimization.assemble','optimization.solve'],
        tool_bindings={'optimization.assemble':'1.0.0','optimization.solve':'1.0.0'},timeout_s=300.)
    raw['policy']['budget'].update(tool_calls=4,model_calls=0,backend_solves=0,wall_s=1200.)
    inp=SessionInput.model_validate(raw)
    args=dict(assembler=dict(extension_id='optimization_assembler.gvs_trajectory',
        parameters=dict(contract='family.gvs_trajectory_parameters',data=parameters)),
        specification=dict(variables=list(trajectory_authorization(inp.robot,{},parameters)),
            horizon=5,initial_guess=guess,objectives=[dict(template_id='dynamic_tip_tracking')],
            constraints=[dict(template_id=s) for s in ('initial_state','implicit_dynamics','tendon_force_bounds')]),
        context=dict(x0=x,u0=u))
    options=dict(max_iterations=parameters['max_iterations'],tolerance=parameters['tolerance'],
        max_cpu_s=30.,retain_feasible_iterate=True)
    config=dict(robot=raw['robot'],task=raw['task'],arguments=args,solver_options=options,
        seed_source=str((OLD/'offline_scaled_candidate.json').relative_to(ROOT)),seed_digest=digest(seed),
        historical_parameters_source=str((OLD/'offline_trajectory.json').relative_to(ROOT)),
        seed_objective=seed['result']['objective_value'],acceptance_scaled_violation=1e-5,
        duration_s=.05,period_s=.01,decision_scales=scales,tendon_order=frozen['tendon_order'],
        note='Identical seed for all comparisons; 30 s CPU development cap replaces historical 120 s cap, not an acceleration claim.')
    return raw,config

def assemble(label):
    raw,config=setup()
    if not (HERE/'fixed_problem.json').exists():save('fixed_problem',config)
    else:assert config==read(HERE/'fixed_problem.json')
    store=Store(HERE)
    if not store.db.exists():
        grant=project();grant['budget']['wall_s']=7200.
        grant['authorization_source']='User authorized bounded GVS optimization performance repair and public solve; no backend runs.'
        store.create(grant)
    raw['run_id']='gvs-cost-'+label
    host=Host(HERE,raw['run_id']);host.create(raw)
    request=dict(request_id='assemble',tool_id='optimization.assemble',tool_version='1.0.0',
        arguments=config['arguments'],reason='Assemble frozen five-interval optimization with explicit initial state and previous input.')
    profiler=cProfile.Profile()
    receipt,elapsed=timed(lambda:profiler.runcall(host.invoke,request))
    graph_s=sum(e.totaltime for e in profiler.getstats() if not isinstance(e.code,str)
        and e.code.co_name=='assemble' and e.code.co_filename.endswith('gvs_trajectory.py'))
    save(label+'_assembly_receipt',dict(receipt=receipt,wall_s=elapsed,
        graph_assembly_including_serialization_s=graph_s))
    assert receipt['execution_status']=='completed',receipt
    ref=store.artifact(receipt['output'])['problem']
    problem=OptimizationProblem.model_validate(store.artifact(ref))
    function=ca.Function.deserialize(problem.objective_function.data['serialized_function'])
    order=problem.objective_function.data['variable_order']
    vector=np.array([problem.initial_guess.get(k,0.) for k in order])
    return host,ref,problem,function,vector,config,elapsed

def profile(function,vector):
    z=ca.MX.sym('probe',len(vector));f,g=function.call([z],True,False)
    result={}
    for name,expressions in [('objective',[f]),('constraints',[g]),('objective_gradient',[ca.gradient(f,z)]),('constraint_jacobian',[ca.jacobian(g,z)])]:
        fn,build=timed(lambda:ca.Function('probe_'+name,[z],expressions))
        _,first=timed(lambda:fn(vector));_,warm=timed(lambda:fn(vector))
        result[name]=dict(construction_s=build,first_s=first,warm_s=warm,nodes=fn.n_nodes())
        print(name,result[name],flush=True)
    return result

def baseline():
    # Frozen pre-change expressions, not the current implementation. Repeating
    # this phase is optional; it is not needed to produce a new public plan.
    _,config=setup();save('fixed_problem',config)
    problem=reference_problem()
    function=ca.Function.deserialize(problem.objective_function.data['serialized_function'])
    vector=np.array([problem.initial_guess.get(k,0.) for k in problem.objective_function.data['variable_order']])
    save('baseline_profile',profile(function,vector))
    solver=IpoptSolver(config['solver_options'])
    result,total=timed(lambda:solver.solve(problem))
    save('baseline_solve',dict(result=result.model_dump(mode='json'),diagnostics=solver.last_diagnostics,total_s=total))
    print('baseline',result.status,result.objective_value,result.constraint_violation,total,flush=True)

def candidate(label='improved'):
    host,ref,problem,function,vector,config,elapsed=assemble(label)
    reference=reference_problem()
    assert problem.variables==reference.variables and problem.initial_guess==reference.initial_guess
    assert problem.objective_function.data['variable_order']==reference.objective_function.data['variable_order']
    original=ca.Function.deserialize(reference.objective_function.data['serialized_function'])
    equivalence=[]
    for values in (vector,vector+np.linspace(-1e-4,1e-4,len(vector))):
        a=original(values);b=function(values)
        errors=[float(np.max(abs(np.asarray(x)-np.asarray(y)),initial=0)) for x,y in zip(a,b)]
        for x,y in zip(a,b):np.testing.assert_allclose(x,y,rtol=1e-8,atol=1e-9)
        equivalence.append(errors)
    z=ca.MX.sym('z',len(vector));direction=np.sin(np.arange(len(vector))+1.)
    f,g=function.call([z],True,False)
    derivative=ca.Function('directional',[z],[ca.jtimes(ca.vertcat(f,g),z,ca.DM(direction))])
    analytic=np.asarray(derivative(vector)).ravel();eps=1e-5
    pack=lambda values:np.r_[float(values[0]),np.asarray(values[1]).ravel()]
    fd=(pack(original(vector+eps*direction))-pack(original(vector-eps*direction)))/(2*eps)
    np.testing.assert_allclose(analytic,fd,rtol=2e-5,atol=2e-6)
    save(label+'_equivalence',dict(value_max_errors=equivalence,directional_max_error=float(max(abs(analytic-fd)))))
    options={**config['solver_options'],'constraint_jacobian_mode':'reverse'}
    solver=IpoptSolver(options)
    for label in ('cold','warm'):
        result,total=timed(lambda:solver.solve(problem))
        save('improved_'+label,dict(result=result.model_dump(mode='json'),diagnostics=solver.last_diagnostics,total_s=total))
        print(label,result.status,result.objective_value,result.constraint_violation,total,flush=True)
        if result.constraint_violation>1e-5:raise RuntimeError('Inspect failed bounded solve before another attempt')
    prepared_solver=next(iter(solver._compiled.values()))[1]
    evaluations={}
    for name in ('nlp_f','nlp_g','nlp_grad_f','nlp_jac_g'):
        fn=prepared_solver.get_function(name)
        _,first=timed(lambda:fn(vector,[]));_,warm=timed(lambda:fn(vector,[]))
        evaluations[name]=dict(first_s=first,warm_s=warm)
    jacobian=np.asarray(prepared_solver.get_function('nlp_jac_g')(vector,[])[1])
    save('improved_profile',evaluations)
    np.testing.assert_allclose(jacobian@direction,fd[1:],rtol=2e-5,atol=2e-6)
    save('solver_directional_check',dict(max_error=float(max(abs(jacobian@direction-fd[1:])))))
    # Public execution builds/solves the saved artifact; no private optimum is supplied.
    request=dict(request_id='solve',tool_id='optimization.solve',tool_version='1.0.0',
        arguments=dict(problem=ref,options=options),reason='New bounded solve of the frozen 50 ms trajectory from the original seed.')
    receipt,total=timed(lambda:host.invoke(request));save('public_solve_receipt',dict(request=request,receipt=receipt,wall_s=total))
    assert receipt['execution_status']=='completed',receipt
    result=host.store.artifact(receipt['output']);save('public_result',result)
    diagnostics=host.store.artifact(result['solver_evidence']);save('public_solver_diagnostics',diagnostics)
    order=problem.objective_function.data['variable_order'];values=np.array([result['optimum'][k] for k in order])
    evaluated,validation_s=timed(lambda:original(values));objective=float(evaluated[0]);g=np.asarray(evaluated[1]).ravel()
    lo,hi,_=IpoptSolver._bounds(problem,order)
    violation=float(max(np.max(abs(g)),np.max(np.maximum(np.array(lo)-values,values-np.array(hi))),0))
    n=len(config['decision_scales'])//2;tendons=config['tendon_order']
    X=np.array([[result['optimum'][f'x/{k}/{j}']*config['decision_scales'][j] for j in range(2*n)] for k in range(6)])
    U=np.array([[result['optimum'][f'u/{k}/{t}'] for t in tendons] for k in range(5)])
    initial_error=float(np.max(abs(X[0]-config['arguments']['context']['x0'])))
    previous_error=max(abs(result['optimum']['previous_u/'+t]-u) for t,u in zip(tendons,config['arguments']['context']['u0']))
    assert initial_error<=1e-12 and previous_error<=1e-12
    np.testing.assert_allclose(objective,result['objective_value'],rtol=1e-10,atol=1e-12)
    limits=np.array([t['force_limit_n'] for t in config['robot']['structure']['data']['tendons']])
    tension_violation=float(max(np.max(-U),np.max(U-limits),0.))
    usable=result['status'] in ('converged','iteration_limit') and violation<=1e-5 and np.isfinite(values).all()
    save('trajectory',dict(states=X.tolist(),tensions=U.tolist(),period_s=.01,duration_s=.05,
        state_order=[problem.variables[f'x/0/{j}']['physical_coordinate'] for j in range(2*n)],tendon_order=tendons,
        initial_error=initial_error,previous_input_error=previous_error,reference_objective=objective,
        tension_bound_violation_n=tension_violation,finite_states_inputs=bool(np.isfinite(np.r_[X.ravel(),U.ravel()]).all()),
        reference_scaled_violation=violation,reference_validation_s=validation_s,usable=bool(usable),
        solver_status=result['status'],iterations=result['iterations'],public_wall_s=total))
    assert usable,(result['status'],violation)
    print('PUBLIC usable',objective,violation,total,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['baseline','candidate','setup'])
    parser.add_argument('--label',default='improved');parser.add_argument('--output',type=Path);args=parser.parse_args()
    if args.output:HERE=args.output.resolve();HERE.mkdir(parents=True,exist_ok=True)
    if not (HERE/'environment.json').exists():
        save('environment',dict(interpreter=sys.executable,python=sys.version,platform=platform.platform(),
            numpy=np.__version__,scipy=scipy.__version__,casadi=ca.__version__,
            threads={k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')}))
    if args.phase=='baseline':baseline()
    elif args.phase=='setup':assemble(args.label)
    else:candidate(args.label)
