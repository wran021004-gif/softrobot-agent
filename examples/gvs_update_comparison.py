"""Three frozen saved states; no provider transport or backend rollout.

Run freeze once, baseline before the numerical edit, then modified afterward.
Initialization is reconstructed (constant previous tensions), not a replay of
the historical optimizer's unsaved warm plan.
"""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'

import casadi as ca
import numpy as np
from tools.state_io import atomic_json, digest

SOURCE = ROOT / 'runs/stage324_time_reference_tracking_20260928'


def freeze(output):
    source = next((SOURCE / 'deterministic').rglob('controller_observations.json'))
    rows = json.loads(source.read_text())
    plan = json.loads(source.with_name('control_spec.json').read_text())
    samples = []
    for t in (0., .20, .35):
        i = next(i for i, r in enumerate(rows) if abs(r['time_s']-t) < 1e-8)
        row = rows[i]
        previous = rows[i-1]['actual_tension_n'] if i else plan['reference']['u0']
        steps = plan['effective_parameters']['horizon']*plan['effective_parameters']['substeps']
        samples.append(dict(time_s=row['time_s'], measured_x=row['measured_initial_state'],
            previous_u=previous, geometry=dict(tip=row['tip_position_m'],
                gvs_projection=dict(projection_residual_max_rad_m=row['gvs_projection_residual_max_rad_m'])),
            warm=dict(states=[row['measured_initial_state']]*(steps+1),
                tensions=[previous]*plan['effective_parameters']['horizon'])))
    value = dict(input=json.loads((SOURCE/'frozen_input.json').read_text()), plan=plan,
        physics=json.loads(source.with_name('resolved_physics.json').read_text()), samples=samples,
        initialization='reconstructed constant previous applied tensions; repeated measured-state guesses; actual-state implicit regeneration remains enabled',
        observation_source=str(source.relative_to(ROOT)), observation_identity=digest(rows))
    target = output/'selected_states.json'
    if target.exists():
        raise ValueError('SELECTION_ALREADY_FROZEN')
    atomic_json(target, value)


def compare(output, label):
    from schemas.platform import SessionInput
    from extensions.tendon_family.gvs_nmpc import TrackingNMPCController
    from extensions.tendon_family.gvs_profile import candidate_numerical, load_profile
    from extensions.tendon_family.tracking import checked_tracking
    import extensions.optimization.ipopt as ipopt
    if (output/(label+'.json')).exists():
        raise ValueError('COMPARISON_RESULT_ALREADY_EXISTS')
    saved = json.loads((output/'selected_states.json').read_text())
    inp = SessionInput.model_validate(saved['input'])
    numerical = candidate_numerical(inp, checked_tracking(inp), load_profile())
    controller = TrackingNMPCController(inp.policy.controller.parameters.data, inp.task.timing.control_period_s)
    controller.preparation = {}
    controller.profile = dict(numerical=numerical)
    started = time.perf_counter()
    controller.configure(saved['physics'], saved['plan'])
    ws = controller.workspace
    first = saved['samples'][0]
    ws._extend_tail(first['measured_x'], first['previous_u'])
    # Construct the real solver and warm its value function without an NLP solve.
    # The compiled cache retains the real solver, never this temporary proxy.
    original = ca.nlpsol
    class Constructed(Exception):
        pass
    class StopBeforeSolve:
        def __init__(self, solver): self.solver = solver
        def __call__(self, **kwargs): raise Constructed()
    with patch.object(ipopt.ca, 'nlpsol', side_effect=lambda *a, **k: StopBeforeSolve(original(*a, **k))):
        try: ws.solver.solve(ws.problem)
        except Constructed: pass
    for key, (function, solver, selector) in list(ws.solver._compiled.items()):
        ws.solver._compiled[key] = (function, solver.solver, selector)
    construction = time.perf_counter()-started
    records = []
    for sample in saved['samples']:
        controller.previous = np.asarray(sample['previous_u']).copy()
        controller.seed = deepcopy(sample['warm'])
        controller.unusable_updates = 0
        geometry = deepcopy(sample['geometry']); geometry['tip'] = np.asarray(geometry['tip'])
        x = sample['measured_x']; n = len(x)//2
        start = time.perf_counter()
        controller.command(sample['time_s'], geometry, x[:n], x[n:])
        wall = time.perf_counter()-start
        solved = ws.last
        if solved is None: raise RuntimeError(controller.last)
        # Outside operational update: diagnostic evaluation costs at this state.
        y = np.asarray(solved['states'][1]); old = np.asarray(x); u = np.asarray(solved['tensions'][0])
        residual = ws._tail_residual
        jacobian = residual.jacobian()
        jacobian(old,y,u,ca.DM.zeros(2*n))  # consistent derivative-cache warming
        stamp=time.perf_counter(); residual(old,y,u); residual_s=time.perf_counter()-stamp
        stamp=time.perf_counter(); jacobian(old,y,u,ca.DM.zeros(2*n)); jacobian_s=time.perf_counter()-stamp
        record=dict(time_s=sample['time_s'], complete_update_s=wall, observation=controller.observations[-1],
            objective=solved['result']['objective_value'], diagnostics=solved['diagnostics'],
            warm_start=solved['warm_start'], recovery=solved['recovery'],
            selected_states=solved['states'], selected_tensions=solved['tensions'],
            residual_s=residual_s, residual_all_jacobians_s=jacobian_s,
            root_last_statistics=ws._tail_solver.stats())
        records.append(record)
        atomic_json(output/(label+'.json'),dict(label=label, selection_identity=digest(saved),
            one_time_construction_and_cache_warm_s=construction, records=records,
            provider_calls=0, backend_rollouts=0))
        print(label, sample['time_s'], 'complete',wall,'prepare',record['observation']['warm_preparation_s'],
            'solve',record['observation']['optimization_solve_s'],'objective',record['objective'],flush=True)


def verify(output):
    """Check every saved selected plan against the original production graph.

    Value evaluation only: no optimization, implicit reintegration or rollout.
    """
    from schemas.platform import SessionInput
    from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace
    from extensions.optimization.ipopt import _EXPRESSION_FUNCTIONS, _violation
    saved=json.loads((output/'selected_states.json').read_text())
    inp=SessionInput.model_validate(saved['input'])
    first=saved['samples'][0]
    ws=TrajectoryWorkspace(inp.task,inp.robot,inp.policy.controller.parameters.data['recipe'],
        first['measured_x'],first['previous_u'])
    bundle=ws.problem.objective_function.data
    function=_EXPRESSION_FUNCTIONS[bundle['expression_digest']][1]
    checks=[]
    for label in ('baseline','modified'):
        result=json.loads((output/(label+'.json')).read_text())
        assert result['selection_identity']==digest(saved)
        for sample,record in zip(saved['samples'],result['records'],strict=True):
            ws._set_prediction_time(sample['time_s'])
            values=dict(ws.problem.initial_guess)
            for k,row in enumerate(record['selected_states']):
                for j,value in enumerate(row):values[f'x/{k}/{j}']=value/ws.state_scales[j]
            for k,row in enumerate(record['selected_tensions']):
                for tendon,value in zip(ws.tendons,row):values[f'u/{k}/{tendon}']=value
            for j,value in enumerate(sample['measured_x']):
                ws.problem.variables[f'x/0/{j}']['bounds']=[value/ws.state_scales[j]]*2
            for tendon,value in zip(ws.tendons,sample['previous_u']):
                values['previous_u/'+tendon]=value
                ws.problem.variables['previous_u/'+tendon]['bounds']=[value]*2
            vector=np.asarray([values[k] for k in bundle['variable_order']])
            evaluated=function(x=vector)
            lb,ub,_=ws.solver._bounds(ws.problem,bundle['variable_order'])
            violation=_violation(vector,np.asarray(evaluated['constraints']).ravel(),lb,ub,
                [0.]*len(ws.problem.constraints),[0.]*len(ws.problem.constraints))
            objective=float(evaluated['objective'])
            assert violation<=1e-5
            assert np.isclose(objective,record['objective'],rtol=1e-10,atol=1e-10)
            checks.append(dict(variant=label,time_s=sample['time_s'],original_graph_scaled_violation=violation,
                original_graph_objective=objective,objective_difference=objective-record['objective'],feasible=True))
    atomic_json(output/'plan_verification.json',dict(checks=checks,provider_calls=0,backend_rollouts=0))
    print(json.dumps(checks,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['freeze','baseline','modified','verify'])
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    if args.action=='freeze':freeze(args.output)
    elif args.action=='verify':verify(args.output)
    else:compare(args.output,args.action)
