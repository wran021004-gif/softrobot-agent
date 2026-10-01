"""Inspect sealed Stage 3.37 candidates without repeating any local solve."""
from pathlib import Path
import os
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import casadi as ca
import numpy as np
from examples.stage337_bounded_nmpc_diagnostics import CASES,saved_case,sha256
from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace
from tools.state_io import read,atomic_json


def main():
    started=time.perf_counter();spec=CASES[1]
    path=ROOT/'runs/stage337_bounded_nmpc_diagnostics_20261001/current_failed_t0p23.json'
    saved=read(path);folder,row,previous,plan,inp=saved_case(spec)
    ws=TrajectoryWorkspace(inp.task,inp.robot,plan['effective_parameters'],
        [*plan['reference']['q0'],*([0.]*len(plan['reference']['q0']))],plan['reference']['u0'],
        settling=plan.get('settling'))
    bundle=ws.problem.objective_function.data
    function=ca.Function.deserialize(bundle['serialized_function'])
    order=bundle['variable_order'];constraints=bundle['constraint_order']
    base=dict(zip(saved['solver_diagnostics']['variable_order'],
        saved['solver_diagnostics']['selected_feasible_candidate']['x']))
    coordinates=[ws.problem.variables[f'x/0/{j}']['physical_coordinate'] for j in range(ws.n)]
    points=[]
    for point in saved['retained_points']:
        values=dict(base);states=np.array(point['plan']['states']);u=np.array(point['plan']['tensions'])
        for k,state in enumerate(states):
            for j,value in enumerate(state):values[f'x/{k}/{j}']=value/ws.state_scales[j]
        for k,tensions in enumerate(u):
            for tendon,value in zip(ws.tendons,tensions):values[f'u/{k}/{tendon}']=value
        checked=function(x=[values[name] for name in order]);g=np.array(checked['constraints']).ravel()
        objective=float(checked['objective']);residual=float(np.max(np.abs(g)))
        assert np.isclose(objective,point['objective'],rtol=1e-9,atol=1e-10)
        assert np.isclose(residual,point['scaled_violation'],rtol=1e-6,atol=1e-10)
        dominant=[]
        for index in np.argsort(np.abs(g))[-5:][::-1]:
            name=constraints[index];_,step,component=name.split('_');component=int(component)
            scale=10. if component<ws.n else .001
            dominant.append(dict(equation=name,prediction_step=int(step),coordinate=coordinates[component%ws.n],
                equation_type='implicit_Euler_kinematic' if component<ws.n else 'GVS_generalized_force_balance',
                scaled_residual=float(g[index]),physical_residual=float(g[index]*scale),
                physical_limit=1e-5*scale,physical_unit='rad/m' if component<ws.n else 'N*m^2/rad'))
        points.append(dict(label=point['label'],roles=point['roles'],iteration=point['iteration'],
            objective=objective,scaled_violation=residual,threshold_ratio=residual/1e-5,
            independently_recomputed=True,named_groups=point['named_residuals'],dominant_equations=dominant))
    timing=saved['timing_s'];d=saved['solver_diagnostics'];stats=d['function_statistics']
    result=dict(kind='saved_vector_equation_and_timing_diagnosis',representative=saved['source'],
        selection_reason='Late failed-case update has a retained least-infeasible candidate, full iteration trace and returned candidate; no need to repeat three reconstructed cases.',
        classification=saved['classification'],reconstruction_limit=saved['reconstruction_limit'],
        sources=[dict(path=str(path.relative_to(ROOT)),size_bytes=path.stat().st_size,sha256=sha256(path)),
            dict(path=str((folder/'control_spec.json').relative_to(ROOT)),sha256=sha256(folder/'control_spec.json'))],
        observations=dict(retained_points=points,iteration_trace=saved['iteration_trace'],
            timing_s=timing,complete_including_workspace_s=timing['complete_local_update']+timing['graph_and_workspace_construction'],
            function_statistics=stats,jacobian_fraction_of_numerical_solve=stats['t_wall_nlp_jac_g']/timing['numerical_solve'],
            initial_check_s=d['initial_check_s'],solver_options=d['options'],stop_reason=d['policy_stop_reason']),
        supported_interpretation=[
            'Fixed GVS generalized-force equations dominate; near.kappa_y_node_1 is worst at step 8 in iteration 5 and step 0 in the returned iterate. Initial-state and variable bounds are exact.',
            'Objective falls from 173.34685 to 4.25160. Feasibility is nonmonotonic: best noninitialization residual 0.000321598 at iteration 5; later rises as high as 0.146178. Final iterations 16-19 improve residual from 0.00499007 to 0.00293500, still 293.5 times threshold.',
            'Scaled force residual equals physical generalized-force defect / 0.001. The 1e-5 acceptance threshold means 1e-8 N*m^2/rad; returned worst defect is 2.935e-6. Kinematic defect /10 has a 1e-4 rad/m physical limit.',
            'Decision-state scales (curvature 10, rate 1000) are distinct from fixed equation-residual scales (10, 0.001); objective normalization uses task tolerance. No scaling or tolerance was changed.',
            'Implicit Euler at 0.01 s with one substep defines the prediction transcription. It differs from the 0.0005 s backend integration. These are numerical model choices, not LLM-generated equations.',
            'Feasible-return budget starts immediately before numerical solve; it excludes workspace/graph construction, warm-state generation, solver construction, initial feasibility check and final validation. Callbacks can overshoot the 15 s budget by one expensive iteration. Complete update therefore exceeds the advertised solve budget.',
            'Reverse exact-AD Jacobians take about 93% of numerical solve time. This locates cost but does not establish a derivative defect, a scaling defect, or an isolated remedy.',
            'A feasible starting plan proves this assembled problem has a feasible point; it does not prove useful improvement is easy within the fixed computation limit.'],
        unresolved=['Warm-start quality, nonlinear conditioning, scaling interactions and finite-budget effects remain confounded.',
            'Full historical warm starts were not retained. No bitwise historical reproduction or dominant closed-loop cause is established.'],
        control_decision=dict(controller_changed=False,controller='controller.gvs_nmpc@6.0.0',variant_tested=False,
            reason='The retained vectors and traces answer the diagnosis questions without another solve. No concrete single implementation defect or supported alternative is isolated. Jacobian cost alone does not justify replacing the existing reverse-AD strategy; no recovery/tolerance/budget change is supported.',
            local_acceptance_gate_not_exercised=['finite result','independent initial-state/dynamics/bound consistency',
                'meaningful objective improvement under identical physical problem','unchanged computation limits',
                'first command and complete-update cost reported separately']),
        usage=dict(new_local_nmpc_solves=0,new_backend_rollouts=0,provider_requests=0,workers=0,
            associated_preparation_and_inspection_s=time.perf_counter()-started),
        scope='Saved-vector recomputation only; no optimization, no design evaluation, no backend trajectory, no proof of closed-loop or real-time success.')
    atomic_json(ROOT/'evidence/stage340_bounded_autonomous_20261001/diagnosis.json',result)
    print('Verified',len(points),'retained candidates; zero new local solves; controller unchanged.')


if __name__=='__main__':main()
