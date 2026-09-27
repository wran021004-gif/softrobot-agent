"""Read-only report assembly from sealed public results and fixed-state timings."""
import json
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.state_io import atomic_json
HERE=Path(__file__).resolve().parent


def read(path):return json.loads(path.read_text(encoding='utf8'))


def archive_sources():
    """Append source bytes only; do not rewrite any sealed execution artifact."""
    from extensions.tendon_family.gvs_profile import load_profile
    from tools.platform_store import Store, plain
    profile=load_profile();entries=[]
    for folder in ('A_run','B'):
        summary=read(HERE/folder/'summary.json');store=Store(HERE/folder)
        run=read(HERE/folder/'workflow.json')['run_id']
        reference=summary['numerical_preparation']['historical_source']
        assert reference==profile['numerical_reference']
        started=time.perf_counter()
        with store.transaction() as db:
            saved=store.put(db,profile['numerical'])
            assert plain(saved)==reference
            store.event(db,run,'post_execution_source_archive','saved',caller='local-human',outputs=[saved])
        assert store.artifact(reference)==profile['numerical']
        entries.append(dict(folder=folder,source=reference,wall_s=time.perf_counter()-started,
            scope='Post-execution source archive only; not numerical preparation during the original run, no replay or result changes'))
    atomic_json(HERE/'source_archive_completion.json',entries)


def diagnose_neighbor(summary):
    import numpy as np
    from tools.platform_store import Store
    store=Store(HERE/'B');run=read(HERE/'B/workflow.json')['run_id']
    refs=next(e['outputs'] for e in store.events(run) if e['kind']=='simulation'
        and e['execution_id']==summary['execution_id'] and e['status']=='completed')
    bundle=next(v for r in refs if r['media_type']=='application/json' for v in [store.artifact(r)]
        if isinstance(v,dict) and 'files' in v)
    files={f['filename']:store.artifact(f['reference'],raw=True) for f in bundle['files']}
    obs=json.loads(files['controller_observations.json']);control=json.loads(files['control_spec.json'])
    material=store.artifact(summary['numerical_preparation']['source'])
    u=np.asarray(material['warm_guess']['tensions'])
    actual=np.asarray([o['desired_tension_n'] for o in obs])
    expected=np.asarray([u[min(k,len(u)-1)] for k in range(len(obs))])
    motion=store.artifact(summary['motion'])
    value=dict(execution_id=summary['execution_id'],target_in_built_control=control['task']['goal']['data']['target_m'],
        max_command_difference_from_shifted_initial_guess_n=float(np.max(abs(actual-expected))),
        selected_initializations=summary['initialization_selected'],updates=summary['updates'],
        minimum_error_sample=min(motion,key=lambda r:r['tip_error_m']),terminal_tip_speed_m_s=summary['terminal_tip_speed_m_s'],
        interpretation='Actual state feedback and full warm regeneration were executed; selected initialization and command differences quantify whether optimization adapted the applied sequence. No hold-last or transfer-success inference.')
    atomic_json(HERE/'B_diagnosis.json',value)
    return value


def main():
    baseline=read(HERE/'baseline.json');candidate=read(HERE/'velocity.json')
    fixed=read(HERE/'fixed_inputs.json');historical=read(ROOT/'runs/stage317_live_route_20260927/summary.json')
    summaries={label:read(HERE/folder/'summary.json') for label,folder in (('A','A_run'),('B','B'))}
    diagnosis=diagnose_neighbor(summaries['B'])
    commits=read(HERE/'verification.json')['implementation_commits']
    assert baseline['input_identity']==candidate['input_identity']
    total_before=sum(r['delivery_s'] for r in baseline['rows'])
    total_after=sum(r['delivery_s'] for r in candidate['rows'])
    costs=[]
    for before,after in zip(baseline['rows'],candidate['rows']):
        costs.append(dict(state=before['label'],baseline={k:v for k,v in before.items() if k!='tail'},
            rejected_candidate={k:v for k,v in after.items() if k!='tail'}))
    overview=dict(implementation_commits=commits,historical_baseline_commit='58aa9eb',
        fixed_state_input_identity=baseline['input_identity'],candidate_retained=False,
        candidate_total_delivery_change_fraction=total_after/total_before-1,
        neighboring_target_diagnosis=diagnosis,
        cost_comparison=costs,target_selection={k:fixed[k] for k in ('new_target_m','old_terminal_tip_m','old_terminal_error_new_target_m','target_selection')},
        outcomes={label:{k:s[k] for k in ('execution_id','official_task_success','terminal_error_m','sampled_settling',
            'accepted_plans','updates','converged_updates','initialization_selected','solver_error_count','hold_last_responses',
            'maximum_plan_violation','mean_update_s','mean_preparation_s','mean_numerical_solve_s','mean_validation_s',
            'graph_construction_s','solver_construction_s','deadline_misses','simulation_wall_s','force_bound_violation_n',
            'tension_range_n','maximum_error_m','minimum_error_m','max_projection_residual_rad_m','real_time_demonstrated')}
            for label,s in summaries.items()})
    atomic_json(HERE/'results.json',overview)
    lines=['# Stage 3.18: parameterized reach and bounded cost investigation','',
        'Based on clean `feat/gvs-dynamics` at `58aa9eb`. Implementation commits: '+', '.join('`'+c+'`' for c in commits)+'. The two executions use `6b0105c`; the last correction changes source archiving only. One agent; no paid model requests, full-suite run, target sweep or changes to historical artifacts. The attached Stage 3.18 request is the active assignment; the older Stage 3.12–NMPC IDE selection is completed background.','',
        '## Delivered public path','',
        '`controller.gvs_nmpc@3.0.0` / `family.gvs_reach_control` accept task-owned targets, small named initial states and timing, plus explicit recipe and sampled settling. The v2 fixed asset and strict identity check remain unchanged. Registry, candidate builder, existing budgeted preparation hook, Host/Route execution and sealed reporting are reused. There is no second execution architecture.','',
        'Technical compatibility/model-use assessment, historical performance coverage, preparation state, and authorization/budgets are separate. Both fresh v3 inputs are initially unvalidated configurations. Old numerical values are compatible guesses with original target/provenance, never a newly solved target equilibrium or new success evidence. A cold initial-state/pretension guess is also available; its preparation was checked, but no full cold-start control experiment was added.','',
        'The same robot, materials, free-space scene, mount/gravity, 12-cell execution model and GVS basis remain fixed. Named initial perturbations are bounded by 0.05 rad and 0.5 rad/s. Each execution owns mutable workspace/solver state; current target enters its graph, current measurements enter equality constraints and full warm regeneration. Explicit source identity/order/units/bounds checks remain.','',
        'Internal seed acceptance defaults to half the task tolerance and 0.02 m/s, recorded in the recipe. Final sampled settling independently uses its frozen window/position/speed settings. Neither changes the authoritative reach evaluator.','',
        '## Fixed three-state cost experiment','',
        'Measured states and prior actual tensions are from the sealed Stage 3.17 MuJoCo execution at 0, 0.15 and 0.34 s. Original complete MuJoCo optimization plans were not exported. Both benchmark variants therefore use the SAME explicitly identified bundled initial seed and corresponding saved Stage 3.15 GVS plans as later guesses. This is a controlled solver-cost comparison, not a reconstruction of historical per-update timing. `fixed_inputs.json` freezes all inputs and source references. One sample per state/variant; single-threaded environment in `verification.json`.','',
        'The candidate eliminated implicit Euler’s linear position equality and solved only for next velocity, retaining the force residual, tolerance, measured feedback and independent plan validation. No gain/solver budget, force/dynamics constraint or task criterion changed.','',
        '| State | Baseline preparation / solve / validation / full (s) | Candidate preparation / solve / validation / full (s) | Selected objective before / after | Scaled violation before / after |',
        '|---|---:|---:|---:|---:|']
    for row in costs:
        b=row['baseline'];a=row['rejected_candidate']
        fmt=lambda r:' / '.join(f'{r[k]:.3f}' for k in ('preparation_s','solve_s','validation_s','delivery_s'))
        lines.append(f"| {row['state']} | {fmt(b)} | {fmt(a)} | {b['objective']:.9g} / {a['objective']:.9g} | {b['violation']:.3g} / {a['violation']:.3g} |")
    lines += ['',f"Graph construction: {baseline['graph_construction_s']:.3f} / {candidate['graph_construction_s']:.3f} s; first solver construction: {baseline['rows'][0]['solver_construction_s']:.3f} / {candidate['rows'][0]['solver_construction_s']:.3f} s (included in full first update). Later solver objects are reused. Initial plan checks are separately recorded in JSON. Historical point/guess loading incurred no new inverse solve; its load time was not separately timed in this microbenchmark. Actual public import/generation time is recorded below.",
        '',f"Total delivery changed by {(total_after/total_before-1)*100:.2f}%; a single sample with this small difference does not establish a benefit. The candidate was REJECTED and removed from production; `rejected_velocity.py` preserves only the reproducible experiment. Production retains the original Newton method. No full-update cost reduction or ten-second target is claimed. The remaining measured costs are warm regeneration and nonlinear solving, not validation. No broader optimization campaign followed.",
        '', '## Two new backend experiments','',
        'Both use a straight initial state, 0.35 s authoritative task, 0.01 s control period, 0.0005 s physics step, original 10 mm reach tolerance and 12 cells/segment. Predictions use 10 intervals with the original recipe and ideal bounded tensions. Final sampled acceptance is the last 0.05 s, <=10 mm error and <=0.02 m/s speed. A and B run sequentially in separate fresh Python processes, without competing numerical benchmarks.',
        '',f"A uses `[0.29, 0.035, 0.19]` m. B changes only target to `{fixed['new_target_m']}` m. The +15 mm world-y offset was frozen before execution; the historical endpoint would miss it by {fixed['old_terminal_error_new_target_m']*1000:.6f} mm. The target was not searched or changed after results.",
        '', '| Result | A: original target | B: neighboring target |','|---|---:|---:|']
    a,b=summaries['A'],summaries['B']
    metrics=[('Complete execution','complete'),('Official reach success','official_task_success'),('Terminal error (mm)',None),
        ('Minimum sampled error (m)','minimum_error_m'),('Maximum projection residual (rad/m)','max_projection_residual_rad_m'),('Accepted plans','accepted_plans'),
        ('Converged updates','converged_updates'),('Initialization selections','initialization_selected'),
        ('Solver errors','solver_error_count'),('Hold-last responses','hold_last_responses'),('Maximum scaled plan violation','maximum_plan_violation'),
        ('Mean full update (s)','mean_update_s'),('Mean warm preparation (s)','mean_preparation_s'),('Mean numerical solve (s)','mean_numerical_solve_s'),
        ('Mean independent validation (s)','mean_validation_s'),('Graph construction (s)','graph_construction_s'),
        ('Total solver construction (s)','solver_construction_s'),('Simulation tool charged wall (s)','simulation_wall_s'),('Deadline misses','deadline_misses'),
        ('Tension range (N)','tension_range_n'),('Force-bound violation (N)','force_bound_violation_n')]
    for title,key in metrics:
        vals=[s[key] if key else (s['terminal_error_m']*1000 if s['terminal_error_m'] is not None else None) for s in (a,b)]
        lines.append('| '+title+' | '+' | '.join(f'{v:.6g}' if isinstance(v,float) else str(v) for v in vals)+' |')
    for title,key in [('Sampled settling passed','passed'),('Window max error (m)','max_error_m'),('Window max speed (m/s)','max_speed_m_s')]:
        lines.append(f"| {title} | {a['sampled_settling'][key]} | {b['sampled_settling'][key]} |")
    lines += ['',f"Numerical preparation (included in tool wall): A {a['numerical_preparation']['wall_s']:.6f} s, B {b['numerical_preparation']['wall_s']:.6f} s. Both explicitly reused historical guesses, without a new inverse solve. Full update includes warm preparation, first solver construction, initial feasibility checks, numerical solving, independent validation and command processing; graph creation occurs before updates. Solver construction totals are not additional costs to add again to full-update time.",
        '',f"Historical Stage 3.17 (NOT a new run): terminal error {historical['terminal_error_m']*1000:.6f} mm; mean full delivery {historical['mean_update_s']:.6f} s. New A mean is {a['mean_update_s']:.6f} s. Because no performance candidate was retained and early-stop timing is wall-budget dependent, differences between complete runs are not evidence of a speedup.",
        '',f"B failure diagnosis: the frozen target reaches the built control graph and numerical preparation completes. All 35 updates regenerate prediction states from actual measurements, but all 35 select initialization rather than a later optimization iterate. The applied command sequence differs from the shifted historical seed by at most {diagnosis['max_command_difference_from_shifted_initial_guess_n']:.3g} N. Thus this run demonstrates no effective optimized command adaptation to the new target. It reaches a minimum sampled error of {diagnosis['minimum_error_sample']['tip_error_m']*1000:.3f} mm at {diagnosis['minimum_error_sample']['time_s']:.2f} s, then leaves the tolerance by the authoritative endpoint (terminal speed {diagnosis['terminal_tip_speed_m_s']:.6f} m/s). This is a control/plan-quality limitation under the declared recipe, not an interface rejection, missing numerical preparation, solver exception or hold-last response. It does not establish a unique causal split between finite-solve quality and model transfer error. The failed result is retained without a third experiment, target change or criterion relaxation.",
        '', 'Each official task outcome comes from the unchanged independent evaluator. Numerical completion, feasible early stopping, objective convergence, sampled settling and real-time delivery remain distinct. The two specific targets have only their recorded execution evidence; no neighborhood-wide success, robustness, continuous settling, changed-material, actuator or contact generalization is established. Small initial perturbations and the cold guess path have interface/preparation checks only, not a third full rollout.',
        '', '## Verification and provenance','',
        'Five existing profile/Route tests passed using saved exports, without extra rollouts. Three focused new tests passed after correcting a duplicate preparation provenance key. The first A launch was rejected during candidate preflight because the old parser recognized only the v2 wrapper; zero backend solves/wall were charged. The v3 dispatch was fixed and the real preflight check added to the focused tests, which passed. The stale prepared session is retained as preflight evidence; the actual A execution uses a new session. There are exactly two new full backend executions.',
        '', 'Implementation files: `gvs_profile.py`, `gvs_nmpc.py`, `gvs_trajectory.py`, `gvs_reporting.py`, `contracts.py`, `candidate.py`, `manifest.py`, `route.py`; public example `examples/gvs_parameterized_reach.py`, focused tests and `docs/gvs_parameterized_reach.md`. No changes to the fixed profile asset or historical result files.',
        '', 'Each experiment folder contains its frozen input/assessment, workflow, public describe/simulate/evaluate/report receipts, summary, report, and `platform.sqlite` with sealed numerical preparation and backend exports. Backend working files are not duplicated in Git. `results.json` is the compact comparison; saved code and JSON make the three-state comparison reproducible.',
        '', 'A final provenance-only correction imports the original historical source artifact alongside the derived guess, so its EvidenceRef is locally readable. The two runs already sealed the complete derived numerical material and checked the packaged source hash; source bytes were subsequently appended to their Stores as explicitly post-execution archive events. `source_archive_completion.json` records this extra archive time, excluded from original simulation timing. No original receipt/result was rewritten and no control rerun was made. Future executions import both through the ordinary budgeted hook. A focused test checks source-reference resolution.',
        '', '## Reproduce','', '```powershell',"Set-Location 'D:\\softrobot-agent'", "$py = 'C:\\Users\\gugugaga\\miniconda3\\envs\\softagent\\python.exe'", "$env:OPENBLAS_NUM_THREADS='1'", "$env:OMP_NUM_THREADS='1'", "$env:MKL_NUM_THREADS='1'",
        '# Read-only regeneration of this report:', '& $py runs/stage318_parameterized_reach_20260927/report_results.py',
        '# Fresh original-target execution; make-input assigns a new run/project identity:',
        '& $py examples/gvs_parameterized_reach.py make-input --target 0.29 0.035 0.19 --output runs/repro318_A_input.json',
        '& $py examples/gvs_parameterized_reach.py prepare --input runs/repro318_A_input.json --output runs/repro318_A',
        '& $py examples/gvs_parameterized_reach.py run --output runs/repro318_A',
        '# Separate neighboring-target process/project:',
        '& $py examples/gvs_parameterized_reach.py make-input --target 0.29 0.05 0.19 --output runs/repro318_B_input.json',
        '& $py examples/gvs_parameterized_reach.py prepare --input runs/repro318_B_input.json --output runs/repro318_B',
        '& $py examples/gvs_parameterized_reach.py run --output runs/repro318_B', '```','',
        'The fresh-run commands consume new backend budgets; they are reproduction instructions, not additional experiments performed this round. Cost samples can be reproduced with `cost_comparison.py baseline` and `cost_comparison.py velocity`; choose a copy of the evidence directory to preserve these measurements. No `freeze` or historical replay is needed.','']
    (HERE/'implementation_report.md').write_text('\n'.join(lines),encoding='utf8')


if __name__=='__main__':
    if '--archive-sources' in sys.argv:archive_sources()
    main()
