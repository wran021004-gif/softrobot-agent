"""Render the compact implementation/evidence report from saved measurements."""
import gzip
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
def read(name):return json.loads((HERE/name).read_text(encoding='utf8'))


def main():
    agreement=read('agreement_cost.json');linear=read('sampled_linear.json');local=read('local_recovery.json')
    reset=read('numerical_reset_review.json') if (HERE/'numerical_reset_review.json').exists() else None
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
        '', 'The graph and solver are cached. Only the measured initial-state equalities, previous tension and shifted warm start change between updates. Finite iteration-limited candidates remain available as optimization guesses even when they cannot supply a command. A callback retains the best feasible iterate within the current solve and current bounds; independent reevaluation confirms feasibility before use. The raw return status and returned-iterate violation remain recorded. Nominal operating metadata stays separate. A converged or iteration-limited plan is usable only when independently evaluated constraint/bound violation is at most 1e-5. Feasible iteration-limited plans are explicitly suboptimal: their raw solver status remains iteration_limit and they count as nonconverged solver failures. They do not count as hold-last fallback. When no usable plan is returned, the sole failure response is hold-last-bounded-tension (clipped nominal tension initially), with every use recorded. The same 10 ms command period, 0.5 ms MuJoCo physics step and authoritative 0.35 s task duration are retained.']
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
        d=read('nmpc_summary.json')
        if reset:
            outcome=f"NUMERICAL FAILURE at {reset['failure_time_s']} s; no valid terminal error or full-task pass. Raw post-reset endpoint error {d['raw_post_reset_endpoint_error_m']*1e3:.5g} mm is not task evidence"
        elif d['terminal_error_m'] is None:
            outcome=f"backend incomplete; no valid terminal error; last recorded error {d['last_recorded_error_m']*1e3:.5g} mm; task_success={d['evaluation']['task_success']}"
        else:
            outcome=f"terminal error {d['terminal_error_m']*1e3:.5g} mm; task_success={d['evaluation']['task_success']}"
        lines += ['',f"Public-path NMPC: {outcome}; {d['solver_failures']} nonconverged/failed solves, {d.get('feasible_suboptimal_updates',0)} feasible suboptimal updates, {d['fallback_uses']} hold-last fallback uses; {d['deadline_misses']} deadline misses. These counts cover the full diagnostic execution. Mean / maximum solve time {d['mean_solve_s']:.4f} / {d['maximum_solve_s']:.4f} s. Full execution wall time {d['wall_s']:.4f} s. It is not real-time control."]
        if reset:
            lines+=['',reset['finding'], '',reset['correction'],
                '', 'The raw public simulation result and evaluation rejection receipt are preserved. Public evaluation correctly rejected DEPENDENCIES_CHANGED because the backend guard was fixed while the process ran; no session snapshot was changed to bypass that check. Read-only finalization invokes the unchanged registered evaluate.reach function on the saved result. nmpc_numerically_reviewed_result.json marks a separate derived BackendResult failed; that same authoritative evaluator returns validity=incomplete, task_success=null, reason=SOLVER_NOT_COMPLETE. This is failure to deliver a valid task trajectory, not a task pass. Reproduction with the corrected backend stops at the first detected numerical failure rather than continuing after a reset.']
        lines += ['', '| Same straight start, 0.35 s task | Minimum / terminal error mm | Actual tension range N | Maximum projection residual rad/m | Task pass |',
            '|---|---:|---:|---:|---|']
        for filename,label in [('lqr_task.json','Sampled LQR'),('offline_backend_replay.json','Offline sequence in MuJoCo'),('nmpc_task.json','NMPC in MuJoCo')]:
            run=read(filename)
            evaluation=run.get('evaluation')
            if filename=='nmpc_task.json' and reset:evaluation=read('nmpc_numerically_reviewed_evaluation.json')
            if evaluation is None and (HERE/'offline_backend_evaluation.json').exists():evaluation=read('offline_backend_evaluation.json')
            passed=evaluation['task_success'] if evaluation is not None else 'not evaluated'
            if passed is None:passed='incomplete'
            endpoint=f"{run['terminal_error_m']*1e3:.4f}" if not (filename=='nmpc_task.json' and reset) else 'invalid after reset'
            if filename=='nmpc_task.json' and run['solver_status']!='completed':endpoint='incomplete'
            minimum=run['minimum_error_m'] if not (filename=='nmpc_task.json' and reset) else min(run['tip_error_m'][:round(reset['last_valid_observation_time_s']/.01)])
            lines.append(f"| {label} | {minimum*1e3:.4f} / {endpoint} | {run['min_tension_n']:.5g} to {run['max_tension_n']:.5g} | {run['max_projection_residual_rad_m']:.5g} | {passed} |")
    if (HERE/'execution_checks.json').exists():
        d=read('execution_checks.json');lines += ['', f"Execution check: {d['nmpc_update_count']} NMPC updates, {d['physics_steps']} physics steps; straight initial state confirmed={d['identical_straight_initial_condition']}. Offline initial equality error {d['measured_initial_equality_max']:.4g}; held-tension replay difference {d['replay_held_tension_difference_max_n']:.4g} N. Maximum optimized-prefix prediction-to-BDF tip discrepancy {d['offline_prediction_to_gvs_replay_max_tip_m']*1e3:.5g} mm."]
        if reset:lines+=['','The update/step totals include the invalid post-reset continuation and do not certify 0.35 s of valid physical integration.']
    if (HERE/'nmpc_task.json').exists():
        from collections import Counter
        updates=read('nmpc_task.json')['observations']
        if reset:
            prefix=[o for o in updates if o['time_s']<=reset['last_valid_observation_time_s']+1e-9]
            last_valid_error=read('nmpc_task.json')['tip_error_m'][round(reset['last_valid_observation_time_s']/.01)-1]*1000
            lines+=['',f"Before the numerical failure: {len(prefix)} control updates, {sum(o['failure_response_used'] for o in prefix)} hold-last uses, {sum(o['feasible_suboptimal_update'] for o in prefix)} feasible suboptimal plans and {sum(not o['solver_failed'] for o in prefix)} converged plans. Last valid sampled tip error: {last_valid_error:.5g} mm. Later updates are post-reset diagnostics only."]
        usable=[o for o in updates if not o['failure_response_used']]
        diagnostics=dict(status_counts=dict(Counter(o['optimization_status'] for o in updates)),
            usable_updates=len(usable),converged_updates=sum(not o['solver_failed'] for o in updates),
            maximum_usable_violation=max((o['optimization_constraint_violation'] for o in usable),default=None),
            maximum_returned_violation=max((o['optimization_returned_violation'] for o in updates if o['optimization_returned_violation'] is not None),default=None),
            solver_construction_total_s=sum(o['solver_construction_s'] or 0 for o in updates),
            selected_prior_iterate_updates=sum(o['optimization_selected_iteration'] is not None for o in updates))
        (HERE/'nmpc_solver_diagnostics.json').write_text(json.dumps(diagnostics,indent=2)+'\n',encoding='utf8')
        lines+=['',f"Solve statuses: {diagnostics['status_counts']}. Usable commands: {diagnostics['usable_updates']}; converged updates: {diagnostics['converged_updates']}; selected earlier feasible iterates: {diagnostics['selected_prior_iterate_updates']}. Maximum violation among usable plans: {diagnostics['maximum_usable_violation']}; maximum raw returned violation: {diagnostics['maximum_returned_violation']}. Total solver construction time across updates: {diagnostics['solver_construction_total_s']:.4f} s."]
        transient={}
        lines+=['','| Trace transient (NMPC truncated at numerical failure) | First sampled entry within 10 mm, s | Peak error mm | Terminal tip speed, m/s |',
            '|---|---:|---:|---:|']
        for label in ('lqr_task','offline_backend_replay','nmpc_task'):
            run=read(label+'.json')
            folder=HERE/'offline_backend' if label=='offline_backend_replay' else ROOT/run['backend_folder']
            with gzip.open(folder/'trajectory.json.gz','rt',encoding='utf8') as stream:rows=json.load(stream)
            valid_pairs=[(r,e) for r,e in zip(rows,run['tip_error_m']) if not (label=='nmpc_task' and reset and r['time_s']>reset['last_valid_observation_time_s']+1e-9)]
            rows=[r for r,e in valid_pairs]
            hits=[r['time_s'] for r,e in valid_pairs if e<=.01]
            first=0. if run['initial_tip_error_m']<=.01 else (hits[0] if hits else None)
            speed=float(np.linalg.norm(np.array(rows[-1]['tip_m'])-rows[-2]['tip_m'])/(rows[-1]['time_s']-rows[-2]['time_s'])) if len(rows)>1 else None
            peak=max([run['initial_tip_error_m']]+[e for r,e in valid_pairs])
            if label=='nmpc_task' and (reset or run['solver_status']!='completed'):speed=None
            transient[label]=dict(first_sample_within_tolerance_s=first,peak_error_m=peak,
                terminal_tip_speed_fd_m_s=speed,within_tolerance_samples=len(hits),total_post_step_samples=len(rows))
            lines.append(f"| {label} | {first if first is not None else 'never'} | {peak*1e3:.5g} | {speed if speed is not None else 'unavailable'} |")
        (HERE/'transient_metrics.json').write_text(json.dumps(transient,indent=2)+'\n',encoding='utf8')
        lines+=['','Tip speed is a finite difference over the final observation interval. First entry into tolerance is not a settling or stability claim.']
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(2,1,figsize=(8,6),sharex=True,gridspec_kw={'height_ratios':[3,1]})
        for label,title in [('lqr_task','Sampled LQR'),('offline_backend_replay','Offline prefix + held continuation'),('nmpc_task','NMPC')]:
            run=read(label+'.json');folder=HERE/'offline_backend' if label=='offline_backend_replay' else ROOT/run['backend_folder']
            with gzip.open(folder/'trajectory.json.gz','rt',encoding='utf8') as stream:rows=json.load(stream)
            pairs=[(r,e) for r,e in zip(rows,run['tip_error_m']) if not (label=='nmpc_task' and reset and r['time_s']>reset['last_valid_observation_time_s']+1e-9)]
            axes[0].plot([0.]+[r['time_s'] for r,e in pairs],np.r_[run['initial_tip_error_m'],[e for r,e in pairs]]*1000,label=title)
        if reset:
            axes[0].axvspan(reset['failure_time_s'],.35,color='grey',alpha=.15,label='NMPC invalid after reset')
        axes[0].axhline(10,color='black',linestyle=':',label='Task tolerance')
        axes[0].set_ylabel('World tip error (mm)');axes[0].legend(fontsize=8);axes[0].grid(alpha=.25)
        axes[0].set_title('Same straight start, 12 cells/segment, authoritative 0.35 s task')
        plotted_updates=prefix if reset else updates
        endpoint=reset['failure_time_s'] if reset else .35
        axes[1].step([o['time_s'] for o in plotted_updates]+[endpoint],[int(o['failure_response_used']) for o in plotted_updates]+[int(plotted_updates[-1]['failure_response_used'])],where='post')
        if reset:axes[1].axvspan(endpoint,.35,color='grey',alpha=.15)
        axes[1].set_yticks([0,1],['Plan','Hold last']);axes[1].set_ylabel('NMPC action');axes[1].set_xlabel('Simulated time (s)')
        axes[1].set_xlim(0,.35);axes[1].grid(alpha=.25)
        fig.tight_layout();fig.savefig(HERE/'same_start_comparison.png',dpi=170);plt.close(fig)
        lines+=['','![Same-start task comparison](same_start_comparison.png)']
    if (HERE/'execution_environment.json').exists():
        d=read('execution_environment.json');lines += ['', f"Optimization software: CasADi {d['casadi']}, SciPy {d['scipy']}; {d['derivative_evaluation_threads']} stage-evaluation threads. The trusted expression wrapper is inlined for differentiation; each implicit stage retains a local derivative boundary. Solver construction and per-update solve times are recorded separately."]
    if (HERE/'interrupted_attempt.json').exists():
        lines += ['', 'An earlier 35-interval solve was interrupted after more than 50 minutes without a returned result. The expensive combined objective/constraint derivative boundary was then corrected. That interrupted attempt supplies no trajectory, feasibility or task-success evidence.']
    if (HERE/'full_horizon_attempt.json').exists():
        d=read('full_horizon_attempt.json');lines += ['',f"The later full-horizon attempt also returned no trajectory within {d['elapsed_wall_s']:.1f} s and was stopped. The first offline problem was therefore reduced to the configured NMPC horizon, while retaining the original task duration for all backend evaluations. Interrupted attempts, including the intermediate thread-configuration attempt, are retained as unsuccessful computation records."]
    lines += ['', 'The final configuration uses a 50 ms horizon, at most 40 IPOPT iterations and a 120 s CPU limit per solve. Reproduction reuses the archived offline_scaled_candidate.json as a numerical initial guess, then performs new offline and closed-loop solves. The interrupted cold starts are not required. Four cancelled public debugging runs and their completed cancellation receipts are retained separately; they supply no full-task success evidence. The final run uses the last backend allocation of the original project grant.',
        '', '## Reproduction','', 'From D:\\softrobot-agent, using the resolved interpreter:', '', '```powershell',
        "Set-Location 'D:\\softrobot-agent'",
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
        'Eight sampled-math/applicability checks pass, plus the existing generic IPOPT check extended to confirm changed fixed initial bounds use a cached solver. A focused real IPOPT parabola test also verifies that an infeasible final iterate does not displace an earlier feasible candidate, while iteration_limit remains the solve status. One real MuJoCo step test reproduces a huge-velocity reset to finite values and verifies the corrected numerical-failure guard. The actual backend executions are the end-to-end evidence. The small-angle value/Jacobian check uses an independent matrix exponential. No full suite or gain/resolution sweep was run.',
        '', 'Agreement covers one fixed state, basis, design and numerical configuration. Local LQR tip success does not establish exact regulation or global stability. GVS omits out-of-subspace backend modes and the first dynamic integrator check covers one interval. Task success, NLP feasibility and real-time feasibility are separate claims. CPU-bounded solves are timing-dependent: reproduction preserves the protocol and archived seed, not bit-identical termination iterates.']
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
