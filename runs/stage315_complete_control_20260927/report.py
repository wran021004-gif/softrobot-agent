"""Summarize saved evidence; never invokes an optimizer or simulator."""
import json
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
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
        lines.append(f"| Case {r['case']}, {'policy' if r['policy_enabled'] else 'regenerated only'} | {r['preparation_s']:.2f} s | {r['initial_violation']:.3g} | {r['first_feasible_s']:.2f} s | {r['policy_stop_s']} | {r['validation_s']:.3f} s | {r['delivery_s']:.2f} s | {r['objective']:.6g} | {r['violation']:.3g} |")
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
        lines+=['## Nonlinear GVS execution','', '```json',json.dumps(summary['gvs'],indent=2),'```','',
            'The first 12 actually integrated intervals are reused from the approach check; '
            'later states continue from its actual BDF endpoint. No prediction nodes substitute for observations. '
            'Settling is a separate sampled 50 ms window criterion; it does not redefine official task success.','']
    if (HERE/'recorded_command_replay.json').exists():
        replay=read('recorded_command_replay');summary['replay']=[]
        lines+=['## Recorded-command numerical diagnosis','']
        for r in replay['runs']:
            row={k:v for k,v in r.items() if k!='rows'};row['last_valid']=r['rows'][-1]
            summary['replay'].append(row)
        lines+=['```json',json.dumps(summary['replay'],indent=2),'```','',
            'No optimizer runs in these replays. Commands switch at identical physical times. '
            'The 0.25 ms case is a numerical diagnostic; public execution retains the authoritative 0.5 ms setting.','']
    if (HERE/'public_summary.json').exists():
        summary['mujoco']=read('public_summary');lines+=['## Public MuJoCo execution','',
            '```json',json.dumps(summary['mujoco'],indent=2),'```','',
            'See public_simulation_receipt.json and public_evaluation_receipt.json. '
            'Source and dependencies were kept fixed between simulation and evaluation.','']
    lines+=['## Implementation and focused checks','',
        '- `354c9e0`: full warm-state regeneration, optional feasible return, raw status preservation, '
        'soft terminal rate cost, sustained-unusable stop and controller timing metadata.',
        '- The two saved-state comparisons verify full regenerated guesses, physical scaling and '
        'independently feasible selected plans through the production workspace.',
        '- Two focused optimizer tests pass: intentional stop/current bounds and unchanged '
        'iteration-limited feasible-candidate retention. No full suite or historical investigation was rerun.','',
        '## Reproduction','', 'Run in a fresh output directory for a new immutable public session. '
        'The full GVS command reuses the actual approach checkpoint from the same output directory.','',
        '```powershell',"Set-Location 'D:\\softrobot-agent'", "$py = 'C:\\Users\\gugugaga\\miniconda3\\envs\\softagent\\python.exe'",
        "$env:OPENBLAS_NUM_THREADS='1'; $env:OMP_NUM_THREADS='1'; $env:MKL_NUM_THREADS='1'",
        "$out = 'runs/stage315_reproduction'", "$script = 'runs/stage315_complete_control_20260927/experiment.py'",
        '& $py $script compare --output $out','& $py $script gvs-check --output $out','& $py $script gvs-full --output $out',
        '& $py $script replay --output $out','& $py $script public --output $out','```','',
        'Mathematical feasibility, nonlinear task performance and real-time feasibility remain separate. '
        'Every measured solve is slower than the 10 ms controller deadline. No real-time claim is made.']
    (HERE/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
    (HERE/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    if 'gvs' in summary:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(2,1,figsize=(8,6),sharex=True)
        axes[0].plot([r['time_s'] for r in rows],[1000*r['tip_error_m'] for r in rows],label='GVS actual BDF')
        axes[1].plot([r['time_s'] for r in rows],[r['tip_speed_m_s'] for r in rows])
        axes[0].axhline(10,color='gray',linestyle='--');axes[1].axhline(.02,color='gray',linestyle='--')
        axes[0].set_ylabel('Tip error (mm)');axes[1].set_ylabel('Tip speed (m/s)');axes[1].set_xlabel('Time (s)')
        axes[0].legend();fig.tight_layout();fig.savefig(HERE/'gvs_error_motion.png',dpi=160);plt.close(fig)
if __name__=='__main__':main()
