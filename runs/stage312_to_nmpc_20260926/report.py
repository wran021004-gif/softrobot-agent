"""Render the compact implementation/evidence report from saved measurements."""
import json
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
def read(name):return json.loads((HERE/name).read_text(encoding='utf8'))


def main():
    agreement=read('agreement_cost.json');linear=read('sampled_linear.json');local=read('local_recovery.json')
    lines=['# Stage 3.12 through first GVS NMPC','',
        'Physical design and frozen Stage 3.6/3.11 artifacts are unchanged. This report separates implementation, single-state agreement, task performance and computational feasibility.','',
        '## Agreement and measured cost','',
        'Errors below reuse Stage 3.11; units: tip/shape/COM m, generalized gravity N*m^2/rad, constitutive stiffness N*m^3/rad^2, tendon Jacobian m^2/rad. Parentheses are relative errors. Geometry relatives use world-position norms and are frame-dependent; no composite score is defined. Full per-tendon errors remain linked by EvidenceRef and source location.','',
        '| Cells/segment | Tip | Shape RMS | Whole COM | Gravity | Stiffness | Tendon Jacobian |',
        '|---:|---:|---:|---:|---:|---:|---:|']
    for row in agreement['rows']:
        m=row['record']['metrics']; vals=[]
        for name in ('tip','shape','com','gravity','constitutive_stiffness','tendon_jacobian'):
            v=m[name];r='undefined' if v['relative_error'] is None else f"{v['relative_error']:.4g}"
            vals.append(f"{v['absolute_error']:.6g} ({r})")
        lines.append(f"| {row['cells']} | "+' | '.join(vals)+' |')
    lines += ['', '| Cells | Resolve ms | MJCF ms | Compile ms | Warm forward us | 0.1 s stepping ms | Valid / max contacts |',
        '|---:|---:|---:|---:|---:|---:|---|']
    for row in agreement['rows']:
        repeats=row['record']['costs']['repetitions']
        med=lambda k,scale:float(np.median([r[k] for r in repeats]))*scale
        values=[med(k,scale) for k,scale in [('resolve_s',1e3),('mjcf_s',1e3),('compile_s',1e3),('forward_s',1e6),('step_wall_s',1e3)]]
        lines.append(f"| {row['cells']} | "+' | '.join(f'{v:.4f}' for v in values)+f" | {all(r['numerical_valid'] for r in repeats)} / {max(r['max_contacts'] for r in repeats)} |")
    machine=agreement['rows'][0]['record']['costs']['machine']
    lines += ['', 'Three repetitions; ten forward and ten step warm-ups; 100 forward calls and 200 actual steps per batch. Physics timestep 0.5 ms, implicitfast, mapped q0, held u0, native floor enabled, no observed contacts, no rendering. Medians above; raw wall times and machine/software information are in agreement_cost.json.',
        '',f"Machine: {machine['platform']}; {machine['processor']}; {machine['logical_cpus']} logical CPUs; Python {machine['python']}; NumPy {machine['numpy']}; MuJoCo {machine['mujoco']}.",
        '',agreement['choice'],
        '', 'Production mapping integrates each cell basis across structural knots and preserves principal-axis rotations. Reverse projection uses the same cell-average basis; virtual work uses its transpose. The knot-crossing and represented-state round-trip checks pass. Historical midpoint records are not relabeled. Exact basis integration does not make finite-chain SE(3) geometry exact.',
        '', 'ModelAgreementEvidence retains metric vectors, numerical/model/design identity, exact measured state/input/environment, scope, sources and costs. assess_model_uses consumes matching EvidenceRefs through the existing Store. It reports measured_local only for explicitly matched uses and scope, without changing capability status or authorizing dynamic/contact control. Old records retain validation=unavailable.',
        '', '## Sampled-data LQR and historical interpretation','',
        f"Saved continuous max real eigenvalue: {linear['continuous_max_real_eigenvalue']:.10g} /s. Holding the same K for 10 ms gives rho(Ad-Bd K)={linear['historical_held_spectral_radius']:.10g}. New discrete Riccati gain: rho={linear['sampled_spectral_radius']:.10g}.",
        '', 'Stage 3.6 L0-L2 recomputed feedback continuously during integration; MuJoCo held input for 10 ms while stepping physics every 0.5 ms. They are different closed-loop systems. The held-input instability is an additional explanation, not an attribution of all historical failure to sampling or spatial discretization. The quoted radius describes the pure, unsaturated saved LQR law near its operating point; optional task feedback is disabled in these new runs.',
        '', 'controller.gvs_sampled_lqr is a separate registry identity. Augmented matrix exponential transports A, B and affine drift without inverting A. Continuous and discrete equilibrium checks precede the equilibrium-centered law. Q/R retain the historical numeric diagonals (q=1, qdot=0.1, tension=1), explicitly interpreted as discrete stage weights, with reciprocal squared state/input units. They are not an exact continuous-cost integral. Commands are updated once per 10 ms and executed as bounded ideal tendon tensions.',
        '', '| Run | Initial tip mm | Terminal tip mm | Saturated updates | Max projection residual rad/m | Task pass |',
        '|---|---:|---:|---:|---:|---|']
    for label in ('lqr_nominal','lqr_perturbation','lqr_task'):
        d=read(label+'.json');lines.append(f"| {label} | {d['initial_tip_error_m']*1e3:.4f} | {d['terminal_error_m']*1e3:.4f} | {d['saturated_updates']} | {d['max_projection_residual_rad_m']:.5g} | {d['evaluation']['task_success']} |")
    lines += ['', f"Nominal projected q drift: {local['nominal_q_drift']:.6g} rad/m. The 1% perturbation relative to the nominal trajectory shrinks from {local['initial_perturbation_q_norm']:.6g} to {local['terminal_perturbation_relative_to_nominal_q_norm']:.6g} rad/m. Nominal drift is not perturbation recovery. The refined backend develops modes outside the represented GVS subspace. No backend equilibrium adjustment was substituted into the historical operating point.",
        '', '## Dynamic trajectory and NMPC','',
        'The registered optimization_assembler.gvs_trajectory uses the existing OptimizationProblem, trusted CasADi expression transport and IpoptSolver. Physical states are [q,qdot] in resolved order; inputs are physical tensions in frozen tendon order. Internal state decisions are dimensionless, with declared 10 rad/m and 1000 rad/(m*s) scales; saved states and measured-state inputs retain physical units. Initial states are fixed equalities via variable bounds. Implicit Euler uses mass/force balance with declared residual scaling; physical tension bounds come from RobotIR. Tip output is world-frame. The objective combines tolerance-normalized tip tracking and terminal error, velocity, tension effort and input variation. Smoothing is a control penalty, not an actuator law.',
        '', 'The graph and solver are cached. Only the measured initial-state equalities, previous tension and shifted warm start change between updates. Nominal operating metadata stays separate. A converged or iteration-limited plan is usable only when independently evaluated constraint/bound violation is at most 1e-5. Feasible iteration-limited plans are explicitly suboptimal: their raw solver status remains iteration_limit and they count as nonconverged solver failures. They do not count as hold-last fallback. When no usable plan is returned, the sole failure response is hold-last-bounded-tension (clipped nominal tension initially), with every use recorded. The same 10 ms command period, 0.5 ms MuJoCo physics step and authoritative 0.35 s task duration are retained.']
    if (HERE/'prediction_interval.json').exists():
        d=read('prediction_interval.json');lines += ['',f"One 10 ms prediction check against {d['trusted_method']}: tip discrepancy {d['tip_difference_m']:.6g} m, q norm error {d['q_error_norm']:.6g}, rate norm error {d['rate_error_norm']:.6g}. This verifies only the recorded interval."]
    if (HERE/'offline_trajectory.json').exists():
        d=read('offline_trajectory.json');lines += ['',f"Offline IPOPT: {d['result']['status']}, independently evaluated maximum scaled constraint/bound violation {d['result']['constraint_violation']:.6g}, objective {d['result']['objective_value']:.6g}, total call time {d['total_s']:.4f} s; graph assembly {d['graph_s']:.4f} s; solver construction {d['diagnostics']['construction_s']:.4f} s; optimization {d['diagnostics']['solve_s']:.4f} s. Full states, tensions and world outputs are saved."]
    if (HERE/'offline_execution_sequence.json').exists():
        d=read('offline_execution_sequence.json');lines += ['',f"The offline OCP optimizes {d['optimized_intervals']} intervals ({d['optimized_intervals']*d['period_s']:.3f} s), the same prediction horizon used by NMPC. The full-duration open-loop experiment executes {d['total_intervals']} intervals ({d['total_intervals']*d['period_s']:.3f} s), holding the last optimized tension after the prefix. The continuation is not an optimized trajectory, and the short-horizon endpoint is not reported as task success. Both replays and the authoritative evaluator retain the original 0.35 s duration."]
    for filename,label in [('offline_gvs_replay.json','Independent nonlinear GVS replay'),('offline_backend_replay.json','MuJoCo held-input replay')]:
        if (HERE/filename).exists():
            d=read(filename);lines += ['',f"{label}: terminal error {d['terminal_error_m']*1e3:.5g} mm; elapsed {d['wall_s']:.4f} s."]
    if (HERE/'nmpc_summary.json').exists():
        d=read('nmpc_summary.json');lines += ['',f"Public-path NMPC: terminal error {d['terminal_error_m']*1e3:.5g} mm; task_success={d['evaluation']['task_success']}; {d['solver_failures']} nonconverged/failed solves, {d.get('feasible_suboptimal_updates',0)} feasible suboptimal updates, {d['fallback_uses']} hold-last fallback uses; {d['deadline_misses']} deadline misses. Mean / maximum solve time {d['mean_solve_s']:.4f} / {d['maximum_solve_s']:.4f} s. Full execution wall time {d['wall_s']:.4f} s. It is not real-time control."]
        lines += ['', '| Same straight start, 0.35 s task | Minimum / terminal error mm | Actual tension range N | Maximum projection residual rad/m | Task pass |',
            '|---|---:|---:|---:|---|']
        for filename,label in [('lqr_task.json','Sampled LQR'),('offline_backend_replay.json','Offline sequence in MuJoCo'),('nmpc_task.json','NMPC in MuJoCo')]:
            run=read(filename)
            evaluation=run.get('evaluation')
            if evaluation is None and (HERE/'offline_backend_evaluation.json').exists():evaluation=read('offline_backend_evaluation.json')
            passed=evaluation['task_success'] if evaluation is not None else 'not evaluated'
            lines.append(f"| {label} | {run['minimum_error_m']*1e3:.4f} / {run['terminal_error_m']*1e3:.4f} | {run['min_tension_n']:.5g}–{run['max_tension_n']:.5g} | {run['max_projection_residual_rad_m']:.5g} | {passed} |")
    if (HERE/'execution_checks.json').exists():
        d=read('execution_checks.json');lines += ['', f"Execution check: {d['nmpc_update_count']} NMPC updates, {d['physics_steps']} physics steps; straight initial state confirmed={d['identical_straight_initial_condition']}. Offline initial equality error {d['measured_initial_equality_max']:.4g}; held-tension replay difference {d['replay_held_tension_difference_max_n']:.4g} N. Maximum optimized-prefix prediction-to-BDF tip discrepancy {d['offline_prediction_to_gvs_replay_max_tip_m']*1e3:.5g} mm."]
    if (HERE/'execution_environment.json').exists():
        d=read('execution_environment.json');lines += ['', f"Optimization software: CasADi {d['casadi']}, SciPy {d['scipy']}; {d['derivative_evaluation_threads']} stage-evaluation threads. The trusted expression wrapper is inlined for differentiation; each implicit stage retains a local derivative boundary. Solver construction and per-update solve times are recorded separately."]
    if (HERE/'interrupted_attempt.json').exists():
        lines += ['', 'An earlier 35-interval solve was interrupted after more than 50 minutes without a returned result. The expensive combined objective/constraint derivative boundary was then corrected. That interrupted attempt supplies no trajectory, feasibility or task-success evidence.']
    if (HERE/'full_horizon_attempt.json').exists():
        d=read('full_horizon_attempt.json');lines += ['',f"The later full-horizon attempt also returned no trajectory within {d['elapsed_wall_s']:.1f} s and was stopped. The first offline problem was therefore reduced to the configured NMPC horizon, while retaining the original task duration for all backend evaluations. Interrupted attempts, including the intermediate thread-configuration attempt, are retained as unsuccessful computation records."]
    lines += ['', '## Reproduction','', 'From D:\\softrobot-agent, using the resolved interpreter:', '', '```powershell',
        "$py = 'C:\\Users\\gugugaga\\miniconda3\\envs\\softagent\\python.exe'",
        "$env:OPENBLAS_NUM_THREADS = '1'",
        "$env:OMP_NUM_THREADS = '1'",
        "$env:MKL_NUM_THREADS = '1'",
        "$out = 'runs/stage312_nmpc_reproduction' # choose a fresh directory",
        '& $py runs/stage312_to_nmpc_20260926/agreement_cost.py --output $out',
        '& $py runs/stage312_to_nmpc_20260926/experiment.py baseline --output $out',
        '& $py runs/stage312_to_nmpc_20260926/experiment.py dynamic --output $out',
        '& $py runs/stage312_to_nmpc_20260926/experiment.py finalize --output $out',
        '& $py runs/stage312_to_nmpc_20260926/report.py --output $out',
        '```', '', 'Public execution receipts and per-run backend folders contain the authoritative evaluator evidence. Existing run IDs are immutable; reproduction uses a fresh evidence directory. No paid LLM calls, pushes or merges are part of this experiment.',
        '', '## Focused validation and limits','',
        'Eight sampled-math/applicability checks pass, plus the existing generic IPOPT check extended to confirm changed fixed initial bounds use a cached solver. The actual backend executions are the end-to-end evidence. The small-angle value/Jacobian check uses an independent matrix exponential. No full suite or gain/resolution sweep was run.',
        '', 'Agreement covers one fixed state, basis, design and numerical configuration. Local LQR tip success does not establish exact regulation or global stability. GVS omits out-of-subspace backend modes and the first dynamic integrator check covers one interval. Task success, NLP feasibility and real-time feasibility are separate claims.']
    if (HERE/'dynamics_cost.json').exists():
        d=read('dynamics_cost.json');lines += ['',f"Current graph check: Christoffel bias finite-difference maximum error {d['christoffel_finite_difference_max_error']:.6g}; A/B maximum differences from saved matrices {d['saved_A_max_error']:.6g} / {d['saved_B_max_error']:.6g} (rtol=1e-8, atol=1e-5). Graph construction {d['graph_s']:.4f} s; full dynamics call {d['call_s']:.4f} s; derivative construction plus first call {d['derivative_construction_and_call_s']:.4f} s."]
    if (HERE/'operating_point_current.json').exists():
        d=read('operating_point_current.json');lines += ['',f"Stable small-angle evaluation changes the saved point's numerical acceleration residual. The separately saved precision-refinement artifact moves q by {d['q_change_norm']:.6g} rad/m and reduces the residual to {d['drift_inf']:.6g}. Reproduction uses this derived point for sampled synthesis, while preserving frozen historical matrices and initial states. The archived local/backend results were obtained before this numerical-only refinement."]
    (HERE/'implementation_report.md').write_text('\n'.join(lines)+'\n',encoding='utf8')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args()
    if args.output:HERE=args.output.resolve()
    main()
