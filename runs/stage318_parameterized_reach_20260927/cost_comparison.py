"""Three fixed measured backend states; identical explicit guesses for both runs."""
import argparse
import gzip
import json
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.platform_store import Store
from tools.state_io import atomic_json, digest
from schemas.platform import SessionInput
from extensions.tendon_family.gvs_profile import load_profile
from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def freeze():
    old = ROOT/'runs/stage317_live_route_20260927'
    store = Store(old)
    summary = read(old/'summary.json')
    with store.connect(True) as db:
        events = [json.loads(r[0]) for r in db.execute('SELECT body FROM events')]
    refs = next(e['outputs'] for e in events if e['kind']=='simulation'
                and e['execution_id']==summary['execution_id'] and e['status']=='completed')
    bundle = next(v for r in refs if r['media_type']=='application/json'
                  for v in [store.artifact(r)] if isinstance(v,dict) and 'files' in v)
    files = {f['filename']:store.artifact(f['reference'],raw=True) for f in bundle['files']}
    obs = json.loads(files['controller_observations.json'])
    rows = json.loads(gzip.decompress(files['trajectory.json.gz']))
    profile = load_profile()
    # Backend exports retain measured states and applied inputs, not complete
    # optimized plans. Use explicitly identified corresponding GVS rollout plans
    # as guesses for BOTH sides; never reconstruct a claimed backend warm plan.
    source = read(ROOT/'runs/stage315_complete_control_20260927/gvs_full.json')
    cases=[]
    for index, label in ((0,'start'),(15,'near_target'),(34,'final_hold')):
        guess = profile['numerical']['warm_guess'] if index==0 else source['plans'][index-1]
        cases.append(dict(label=label,index=index,time_s=obs[index]['time_s'],
            measured_x=obs[index]['measured_initial_state'],
            previous_u=profile['numerical']['nominal']['u0'] if index==0 else obs[index-1]['desired_tension_n'],
            warm={k:guess[k] for k in ('states','tensions')},shift=index!=0))
    target = [.29,.05,.19]
    import numpy as np
    value=dict(profile=profile['profile_id'],parameters=profile['parameters'],cases=cases,
        measured_source=dict(folder=str(old.relative_to(ROOT)),execution_id=summary['execution_id']),
        guess_source='Bundled seed at start; saved Stage 3.15 GVS rollout plan at prior corresponding interval otherwise; not claimed original MuJoCo warm plan',
        new_target_m=target,old_terminal_tip_m=rows[-1]['tip_m'],
        old_terminal_error_new_target_m=float(np.linalg.norm(np.asarray(rows[-1]['tip_m'])-target)),
        target_selection='Fixed +15 mm world-y shift before either new execution; original 10 mm tolerance unchanged')
    atomic_json(HERE/'fixed_inputs.json',value)


def run(label):
    frozen=read(HERE/'fixed_inputs.json');p=load_profile()
    inp=SessionInput.model_validate(p['session_input']);point=p['numerical']['nominal']
    started=time.perf_counter()
    parameters=dict(frozen['parameters'])
    cls=TrajectoryWorkspace
    if label=='velocity':
        from rejected_velocity import VelocityWorkspace
        cls=VelocityWorkspace
    workspace=cls(inp.task,inp.robot,parameters,
        point['q0']+[0.]*len(point['q0']),point['u0'])
    result=dict(label=label,input_identity=digest(frozen),interpreter=sys.executable,
        graph_construction_s=time.perf_counter()-started,rows=[])
    for case in frozen['cases']:
        workspace.last=case['warm'] if case['shift'] else None
        plan=workspace.solve(case['measured_x'],case['previous_u'],warm=None if case['shift'] else case['warm'])
        d=plan['diagnostics']
        row=dict(label=case['label'],preparation_s=plan['warm_start']['preparation_s'],
            solve_s=d['solve_s'],validation_s=d['validation_s'],initial_check_s=d['initial_check_s'],
            solver_construction_s=d['construction_s'],delivery_s=plan['update_wall_s'],
            initial_objective=d['initial_objective'],initial_violation=d['initial_scaled_violation'],
            objective=plan['result']['objective_value'],violation=plan['result']['constraint_violation'],
            status=plan['result']['status'],selected_iteration=d['selected_feasible_iteration'],
            accepted=plan['accepted'],tail=plan['warm_start']['tail_initialization'])
        result['rows'].append(row);atomic_json(HERE/(label+'.json'),result)
        print(json.dumps({k:v for k,v in row.items() if k!='tail'}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action');args=parser.parse_args()
    freeze() if args.action=='freeze' else run(args.action)
