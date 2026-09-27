"""Two frozen B measurements, identical reconstructed inputs across variants."""
import argparse
import json
import sys
import time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.platform_store import Store
from tools.state_io import atomic_json,digest
from schemas.platform import SessionInput
from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace
HERE=Path(__file__).resolve().parent
OLD=ROOT/'runs/stage318_parameterized_reach_20260927/B'
def read(path):return json.loads(path.read_text(encoding='utf8'))

def freeze():
    store=Store(OLD);summary=read(OLD/'summary.json');workflow=read(OLD/'workflow.json')
    refs=next(e['outputs'] for e in store.events(workflow['run_id']) if e['kind']=='simulation'
        and e['execution_id']==summary['execution_id'] and e['status']=='completed')
    bundle=next(v for r in refs if r['media_type']=='application/json' for v in [store.artifact(r)]
        if isinstance(v,dict) and 'files' in v)
    ref=next(f['reference'] for f in bundle['files'] if f['filename']=='controller_observations.json')
    obs=json.loads(store.artifact(ref,raw=True))
    material=store.artifact(summary['numerical_preparation']['source'])
    U=np.asarray(material['warm_guess']['tensions']);cases=[]
    for index,label in ((0,'start'),(28,'near_fast')):
        measured=obs[index]['measured_initial_state']
        # B always selected initialization; its U is therefore known exactly.
        # X was not exported. Repeated measurement is an explicitly reconstructed
        # Newton guess, regenerated from the measured initial state on both sides.
        warm=dict(tensions=np.asarray([U[min(index+k,len(U)-1)] for k in range(len(U))]).tolist(),
            states=material['warm_guess']['states'] if index==0 else [measured]*(len(material['warm_guess']['states'])))
        cases.append(dict(label=label,index=index,time_s=obs[index]['time_s'],measured_x=measured,
            previous_u=material['nominal']['u0'] if index==0 else obs[index-1]['desired_tension_n'],warm=warm))
    atomic_json(HERE/'fixed_inputs.json',dict(cases=cases,nominal=material['nominal'],
        source=dict(folder=str(OLD.relative_to(ROOT)),execution_id=summary['execution_id'],observations=ref,
            numerical=summary['numerical_preparation']['source']),
        provenance='Measured states and prior applied tensions from sealed B export. U reconstructed exactly from proven initialization selections; initial X bundled, near-fast X repeated measurement as Newton guess. Not original saved complete plans. Full state regeneration in all comparisons.'))

def metrics(workspace,vector,order,previous):
    values=dict(zip(order,vector));p=workspace.parameters;n=workspace.n;s=p.substeps;N=p.horizon
    X=np.array([[values[f'x/{k}/{j}']*workspace.state_scales[j] for j in range(2*n)] for k in range(N*s+1)])
    U=np.array([[values[f'u/{k}/{t}'] for t in workspace.tendons] for k in range(N)])
    motion=[workspace._motion(x[:n],x[n:]) for x in X]
    errors=np.array([np.linalg.norm(np.asarray(t).ravel()-workspace.target) for t,v in motion])
    speeds=np.array([np.linalg.norm(np.asarray(v)) for t,v in motion]);dt=workspace.period;h=dt/s
    parts=dict(position=h*p.tracking_weight*np.sum((errors[1:]/workspace.goal_tolerance)**2),
        terminal_position=p.terminal_weight*(errors[-1]/workspace.goal_tolerance)**2,
        velocity=h*p.velocity_weight*np.sum(X[1:,n:]**2),terminal_velocity=p.terminal_velocity_weight*np.sum(X[-1,n:]**2),
        tension=dt*p.tension_weight*np.sum(U**2),variation=dt*p.variation_weight*np.sum(np.diff(np.vstack([previous,U]),axis=0)**2))
    return dict(states=X.tolist(),tensions=U.tolist(),cost_parts={k:float(v) for k,v in parts.items()},
        error_m=errors.tolist(),tip_speed_m_s=speeds.tolist(),terminal_error_m=float(errors[-1]),terminal_speed_m_s=float(speeds[-1]))

def run(variant):
    frozen=read(HERE/'fixed_inputs.json');inp=SessionInput.model_validate(read(OLD/'input.json'))
    parameters=dict(inp.policy.controller.parameters.data['recipe'])
    if variant=='long':parameters['feasible_return']={**parameters['feasible_return'],'budget_s':60.,'minimum_s':60.}
    if variant=='reintegrate':parameters['recover_returned_tensions']=True
    point=frozen['nominal'];started=time.perf_counter()
    workspace=TrajectoryWorkspace(inp.task,inp.robot,parameters,point['q0']+[0.]*len(point['q0']),point['u0'])
    workspace.solver.diagnostic_trace=True
    result=dict(variant=variant,input_identity=digest(frozen),parameters=parameters,interpreter=sys.executable,
        graph_s=time.perf_counter()-started,rows=[])
    for case in frozen['cases'][:1] if variant=='long' else frozen['cases']:
        plan=workspace.solve(case['measured_x'],case['previous_u'],warm=case['warm'])
        d=plan['diagnostics'];plans={k:metrics(workspace,v,d['variable_order'],case['previous_u']) for k,v in d['diagnostic_plans'].items()}
        plans['delivered']=metrics(workspace,[plan['result']['optimum'][k] for k in d['variable_order']],d['variable_order'],case['previous_u'])
        d.pop('diagnostic_plans')
        row=dict(label=case['label'],plan=plan,candidates=plans)
        result['rows'].append(row);atomic_json(HERE/(variant+'.json'),result)
        print(json.dumps(dict(label=case['label'],delivery_s=plan['update_wall_s'],solve_s=d['solve_s'],
            initial=d['initial_objective'],selected=plan['result']['objective_value'],returned=d['returned_iterate_objective'],
            returned_violation=d['returned_iterate_constraint_violation'],selected_iteration=d['selected_feasible_iteration'],
            trace=d['iteration_trace'],recovery=plan['recovery'],physical={k:{a:v[a] for a in ('terminal_error_m','terminal_speed_m_s','cost_parts')} for k,v in plans.items()})),flush=True)
    result['experiment_wall_s']=time.perf_counter()-started;atomic_json(HERE/(variant+'.json'),result)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action');args=parser.parse_args()
    freeze() if args.action=='freeze' else run(args.action)
