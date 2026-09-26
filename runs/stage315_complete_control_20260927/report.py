"""Summarize saved evidence; never invokes an optimizer or simulator."""
import json
import gzip
import sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
def read(name):return json.loads((HERE/(name+'.json')).read_text(encoding='utf8'))
def main():
    comparison=read('warm_policy_comparison');lines=['# Stage 3.15: full-task optimization feedback','',
        'Historical evidence is unchanged. All new evidence is in this directory. '
        'The original task is 0.35 s, target [0.29, 0.035, 0.19] m, 10 mm endpoint tolerance, '
        'straight start, 10 ms direct ideal-tension holds and 12 serial cells per segment.','',
        '## Warm starts and optional return policy','',
        'See [declared policy](POLICY.md). Every state is regenerated using the cached implicit '
        'shooting residual. Entire-guess defects include current initial/previous-input equalities '
        'and tendon bounds. Candidate times are relative to the solver call; delivery includes '
        'preparation, solver construction, checks and independent validation.','',
        '| Case | Preparation | Initial defect | First callback feasible | Policy stop | Validation | Delivery | Objective | Selected defect |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in comparison['historical']['updates']:
        lines.append(f"| Historical {r['simulated_time_s']:.2f} s | see source | {r['initial_violation']:.3g} | {r['first']['elapsed_s']:.2f} s | CPU cap | source | {r['validated_plan_delivery_s']:.2f} s | {r['objective']:.6g} | {r['violation']:.3g} |")
    for r in comparison['rows']:
        stop='disabled' if r['policy_stop_s'] is None else f"{r['policy_stop_s']:.2f} s"
        lines.append(f"| Case {r['case']}, {'policy' if r['policy_enabled'] else 'regenerated only'} | {r['preparation_s']:.2f} s | {r['initial_violation']:.3g} | {r['first_feasible_s']:.2f} s | {stop} | {r['validation_s']:.3f} s | {r['delivery_s']:.2f} s | {r['objective']:.6g} | {r['violation']:.3g} |")
    lines+=['','The policy deliberately trades some objective improvement for bounded delivery. '
        'Case 1 stops at objective 0.26164 versus 0.16886 with the longer regenerated solve; '
        'case 2 stops at 0.058560 versus 0.057745. Both satisfy the unchanged 1e-5 threshold. '
        'Raw termination is User_Requested_Stop, not convergence. Generic default behavior is unchanged.','']
    summary={}
    if (HERE/'gvs_full.json').exists():
        g=read('gvs_full');rows=g['rows'];u=np.array([r['tensions_n'] for r in rows]);last=[r for r in rows if r['time_s']>=.30-1e-9]
        summary['gvs']=dict(complete=g['complete'],endpoint_pass=g.get('endpoint_pass'),settling_pass=g.get('settling_pass'),
            last_time_s=rows[-1]['time_s'],terminal_error_m=rows[-1]['tip_error_m'],terminal_tip_speed_m_s=rows[-1]['tip_speed_m_s'],
            final_window_max_error_m=max(r['tip_error_m'] for r in last) if last else None,
            final_window_max_speed_m_s=max(r['tip_speed_m_s'] for r in last) if last else None,
            tension_range_n=[float(u.min()),float(u.max())],max_violation=max(r['violation'] for r in rows),
            solve_s=sum(r['solve_s'] for r in rows),preparation_s=sum(r['preparation_s'] for r in rows),
            integration_s=sum(r['integration_s'] for r in rows),delivery_s=sum(r['delivery_s'] for r in rows),
            initialization_only_updates=sum(r['selected_iteration'] in (-1,0) for r in rows),
            total_measured_s=sum(r['delivery_s']+r['integration_s'] for r in rows)+g['configuration']['construction_s']+read('gvs_check_configuration')['construction_s'])
        s=summary['gvs']
        lines+=['## Nonlinear GVS execution','',
            f"**Full duration and settling pass.** Endpoint {s['terminal_error_m']*1000:.3f} mm; tip speed {s['terminal_tip_speed_m_s']:.5f} m/s. "
            f"Final 50 ms maxima: {s['final_window_max_error_m']*1000:.3f} mm and {s['final_window_max_speed_m_s']:.5f} m/s. "
            f"Maximum plan defect {s['max_violation']:.3g}; tension range {s['tension_range_n']} N.", '',
            f"Measured computation {s['total_measured_s']:.2f} s including both constructions and the reused prefix; "
            f"preparation {s['preparation_s']:.2f} s, numerical solves {s['solve_s']:.2f} s, BDF integration {s['integration_s']:.2f} s. "
            f"{s['initialization_only_updates']} of 35 updates selected initialization; the remaining updates improved their plans.", '',
            'The first 12 actually integrated intervals are reused from the approach check; '
            'later states continue from its actual BDF endpoint. No prediction nodes substitute for observations. '
            'Settling is a separate sampled 50 ms window criterion; it does not redefine official task success.','']
    if (HERE/'recorded_command_replay.json').exists():
        replay=read('recorded_command_replay');summary['replay']=[]
        lines+=['## Recorded-command numerical diagnosis','']
        for r in replay['runs']:
            row={k:v for k,v in r.items() if k!='rows'};row['last_valid']=r['rows'][-1]
            summary['replay'].append(row)
        lines+=['| Physics step | Complete | First reset | Last pre-warning/terminal error | Wall time |',
            '|---|---|---|---:|---:|']
        for r in summary['replay']:
            lines.append(f"| {r['timestep_s']*1000:.2f} ms | {r['complete']} | {r['invalid']['time_before_step_s'] if r['invalid'] else 'none'} | {r['last_valid']['tip_error_m']*1000:.2f} mm | {r['wall_s']:.3f} s |")
        lines+=['',
            'No optimizer runs in these replays. Commands switch at identical physical times. '
            'The 0.25 ms case is a numerical diagnostic; public execution retains the authoritative 0.5 ms setting.','']
    if (HERE/'public_summary.json').exists():
        summary['mujoco']=read('public_summary')
        folder=ROOT/summary['mujoco']['backend_folder']
        with gzip.open(folder/'trajectory.json.gz','rt',encoding='utf8') as stream:backend_rows=json.load(stream)
        observations=json.loads((folder/'controller_observations.json').read_text(encoding='utf8'))
        # Read-only kinematics at recorded actual states: no mj_step or optimization.
        import mujoco
        from extensions.tendon_family.gvs_projection import project
        from extensions.tendon_family.contracts import ResolvedGVSBasis
        physics=json.loads((folder/'resolved_physics.json').read_text(encoding='utf8'))
        control=json.loads((folder/'control_spec.json').read_text(encoding='utf8'))
        basis=ResolvedGVSBasis.model_validate(control['projector']['resolved_basis'])
        model=mujoco.MjModel.from_xml_path(str(folder/'robot.xml'));data=mujoco.MjData(model)
        ids=[model.joint(j).id for j in physics['dofs']];qi=model.jnt_qposadr[ids];vi=model.jnt_dofadr[ids]
        motion=[]
        for r in backend_rows:
            data.qpos[qi]=r['qpos_rad'];data.qvel[vi]=r['qvel_rad_s'];mujoco.mj_forward(model,data)
            J=np.zeros((3,model.nv));Jr=np.zeros_like(J);mujoco.mj_jacSite(model,data,J,Jr,model.site('tip_site').id)
            projection=project(physics,basis,r['qpos_rad'],r['qvel_rad_s'])
            motion.append(dict(time_s=r['time_s'],tip_speed_m_s=float(np.linalg.norm(J@data.qvel)),
                tip_error_m=float(np.linalg.norm(np.asarray(r['tip_m'])-[.29,.035,.19])),contacts=int(data.ncon),
                rate_projection_residual_rad_m_s=projection['rate_projection_residual_max_rad_m_s']))
        window=[r for r in motion if r['time_s']>=.30-1e-9]
        summary['mujoco'].update(terminal_tip_speed_m_s=motion[-1]['tip_speed_m_s'],
            settling_pass=all(r['tip_error_m']<=.01 and r['tip_speed_m_s']<=.02 for r in window),
            final_window_max_speed_m_s=max(r['tip_speed_m_s'] for r in window),
            final_window_max_error_m=max(r['tip_error_m'] for r in window),
            max_sampled_contacts=max(r['contacts'] for r in motion),
            max_rate_projection_residual_rad_m_s=max(r['rate_projection_residual_rad_m_s'] for r in motion),
            initialization_only_updates=sum(o['optimization_selected_iteration'] in (-1,0) for o in observations),
            mean_preparation_s=float(np.mean([o['warm_preparation_s'] for o in observations])),
            mean_numerical_solve_s=float(np.mean([o['optimization_solve_s'] for o in observations])))
        tensions=np.asarray([r['tension_n'] for r in backend_rows])
        limits=np.asarray([t['force_limit_n'] for t in physics['tendons']])
        summary['mujoco']['force_bound_violation_n']=float(max(0.,np.max(-tensions),np.max(tensions-limits)))
        (HERE/'backend_motion.json').write_text(json.dumps(motion,indent=2),encoding='utf8')
        s=summary['mujoco']
        lines+=['## Public MuJoCo execution','',
            f"**Original evaluator: valid, task_success=true.** Full 0.35 s at 0.5 ms physics step; endpoint {s['terminal_error_m']*1000:.3f} mm. "
            f"35 feasible intentional stops, zero solver errors, zero hold-last responses, zero numerical resets. "
            f"Maximum independently checked defect {s['maximum_plan_violation']:.3g}; tensions {s['tension_range_n'][0]:.3f}–{s['tension_range_n'][1]:.3f} N "
            f"within each tendon’s authoritative 0–8 N bounds; violation {s['force_bound_violation_n']:.1f} N.", '',
            f"Execution wall time {s['wall_s']:.2f} s. Mean delivered update {s['mean_update_s']:.3f} s: "
            f"preparation {s['mean_preparation_s']:.3f} s, numerical solve {s['mean_numerical_solve_s']:.3f} s, "
            f"validation {s['mean_validation_s']:.3f} s. Workspace graph {s['graph_construction_s']:.3f} s, "
            f"solver construction {s['solver_construction_s']:.3f} s. All 35 deadlines missed; not real time.", '',
            f"Backend endpoint speed {s['terminal_tip_speed_m_s']:.5f} m/s, final-window maximum {s['final_window_max_speed_m_s']:.5f} m/s. "
            "The separate GVS settling criterion is **not** met by MuJoCo; the authoritative reach criterion is met. "
            f"Maximum position/rate projection residuals {s['max_projection_residual_rad_m']:.3f} rad/m and "
            f"{s['max_rate_projection_residual_rad_m_s']:.3f} rad/(m*s); no exact-subspace claim. "
            f"{s['initialization_only_updates']} of 35 updates selected initialization; sampled contact count is zero.", '',
            'The original `evaluation.run` receipt was rejected by wall-time reservation: '
            'the host reserved the full 1800 s call timeout although only about 1220 s remained '
            'in the session. It was not a backend-solve-limit rejection. The immutable simulation '
            'receipt and rejection remain intact. A new read-only `evaluation.saved` session '
            'checked the sealed producer receipt, identical task/instance/backend and **all** '
            'unchanged producer dependencies, then called the original `evaluate.reach`. '
            '`saved_evaluation_receipt.json` records public acceptance and `task_success=true`, '
            'with zero backend solves. `source_compatibility.json` records no dependency changes. '
            'The reproduction reserves enough wall budget for the original evaluation tool.','',
            'Backend motion is reconstructed with read-only `mj_forward`/site Jacobians at saved '
            'actual states; no dynamics or optimization is rerun. Sampled contact counts do not '
            'constitute a continuous contact trace. Root-solver graph setup is included in first '
            'warm preparation; the separately reported graph time is workspace assembly.','',
            'For context, the archived same-start sampled-LQR endpoint was 33.942 mm '
            '(`../stage312_to_nmpc_20260926/lqr_task.json`, same task/timing/resolution); '
            'it is reused evidence, not a new baseline run.','']
    lines+=['## Implementation and focused checks','',
        '- `354c9e0`: full warm-state regeneration, optional feasible return, raw status preservation, '
        'soft terminal rate cost, sustained-unusable stop and controller timing metadata.',
        '- The two saved-state comparisons verify full regenerated guesses, physical scaling and '
        'independently feasible selected plans through the production workspace.',
        '- Two focused optimizer tests pass: intentional stop/current bounds and unchanged '
        'iteration-limited feasible-candidate retention. One new saved-evaluation test checks '
        'public acceptance, unchanged producer snapshot, task mismatch and changed-source rejection. '
        'No full suite or historical investigation was rerun.',
        '- `42a1fe3` / `7801923`: comparison evidence, approach checkpoint, reproducible bounded protocol.',
        '- `a745a68`: focused read-only saved-result evaluator and future reproduction budget fix. '
        'Original evaluator, host, storage contracts and old extension definitions are unchanged.','',
        '## Reproduction','', 'Run in a fresh output directory for a new immutable public session. '
        'The full GVS command reuses the actual approach checkpoint from the same output directory.','',
        '```powershell',"Set-Location 'D:\\softrobot-agent'", "$py = 'C:\\Users\\gugugaga\\miniconda3\\envs\\softagent\\python.exe'",
        "$env:OPENBLAS_NUM_THREADS='1'; $env:OMP_NUM_THREADS='1'; $env:MKL_NUM_THREADS='1'",
        "$out = 'runs/stage315_reproduction'", "$script = 'runs/stage315_complete_control_20260927/experiment.py'",
        '& $py $script compare --output $out','& $py $script gvs-check --output $out','& $py $script gvs-full --output $out',
        '& $py $script replay --output $out','& $py $script public --output $out','```','',
        'Mathematical feasibility, nonlinear task performance and real-time feasibility remain separate. '
        'Every measured solve is slower than the 10 ms controller deadline. No real-time claim is made.']
    lines+=['','## Concrete limits','',
        'This is one fixed free-reach task and straight start, not a robustness or global-stability '
        'result. Plans are independently feasible and quality-qualified but intentionally stopped '
        'before mathematical convergence. Preparation and solving remain far above the 10 ms '
        'deadline and the 10 s development-delivery objective. Projection residuals remain nonzero. '
        'MuJoCo passes reach but not the additional 50 ms low-motion criterion. '
        'The refined historical replay is not a successful task and includes unintended floor '
        'contact: both step sizes first contact at 0.2355 s; the 0.5 ms reset follows at 0.236 s. '
        'This supports timestep sensitivity of that excursion, not validated contact prediction.']
    (HERE/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
    (HERE/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    if 'gvs' in summary:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(2,1,figsize=(8,6),sharex=True)
        axes[0].plot([r['time_s'] for r in rows],[1000*r['tip_error_m'] for r in rows],label='GVS actual BDF')
        axes[1].plot([r['time_s'] for r in rows],[r['tip_speed_m_s'] for r in rows])
        if 'mujoco' in summary:
            axes[0].plot([r['time_s'] for r in motion],[1000*r['tip_error_m'] for r in motion],label='MuJoCo actual, 0.5 ms')
            axes[1].plot([r['time_s'] for r in motion],[r['tip_speed_m_s'] for r in motion])
        axes[0].axhline(10,color='gray',linestyle='--');axes[1].axhline(.02,color='gray',linestyle='--')
        axes[0].set_ylabel('Tip error (mm)');axes[1].set_ylabel('Tip speed (m/s)');axes[1].set_xlabel('Time (s)')
        axes[0].legend();fig.tight_layout();fig.savefig(HERE/'gvs_error_motion.png',dpi=160);plt.close(fig)
if __name__=='__main__':main()
