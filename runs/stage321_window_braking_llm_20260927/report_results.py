"""Consolidate actual sealed evidence; never run a model or numerical rollout."""
import json
import platform
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from tools.platform_store import Store
from tools.state_io import read,atomic_json

def evidence(label):
    folder=HERE/label
    if not (folder/'summary.json').exists():return None
    s=read(folder/'summary.json');store=Store(folder)
    motion=store.artifact(s['motion'])
    window=[r for r in motion if r['time_s']>=s['task']['timing']['duration_s']-s['sampled_settling']['window_s']-1e-9]
    return dict(summary=s,final_window=window,
        margin=dict(position_m=s['sampled_settling']['position_limit_m']-s['sampled_settling']['max_error_m'],
            speed_m_s=s['sampled_settling']['speed_limit_m_s']-s['sampled_settling']['max_speed_m_s']),
        process=read(HERE/(label+'_process_timing.json')),
        ledger=store.remaining()['used'])

def passes(e):
    return bool(e and e['summary']['valid_complete_execution'] and e['summary']['official_task_success'] and e['summary']['sampled_settling']['passed'])

def main():
    frozen=read(HERE/'fixed_inputs.json');checks=read(HERE/'prediction_checks.json')
    comparisons=[]
    for name in ('baseline','lead'):
        for r in read(HERE/(name+'.json'))['rows']:
            k=round((.30-r['time_s'])/.01)
            comparisons.append(dict(variant=name,time_s=r['time_s'],
                entry_speed_m_s=r['quality']['tip_speed_m_s'][k],
                entry_error_m=r['quality']['error_m'][k],
                first_predicted_speed_m_s=r['quality']['tip_speed_m_s'][1],
                accepted=r['plan']['accepted'],violation=r['plan']['result']['constraint_violation'],
                feedback=r['plan']['feedback'],recovery=r['plan']['recovery'],delivery_s=r['plan']['update_wall_s']))
    historical=[]
    for c,r in zip(frozen['cases'],checks['rows']):
        o=c['recorded_observation']
        one=r['one_period_prediction']
        historical.append(dict(time_s=c['time_s'],measurement=c['actual'],reconstruction=r['reconstruction'],
            one_period_prediction=one,scalar_speed_prediction_error_m_s=one['predicted_speed_m_s']-one['actual_speed_m_s'],
            observed_plan=dict(source=o['plan_source'],selected_iteration=o['optimization_selected_iteration'],
                violation=o['optimization_constraint_violation'],returned_violation=o['optimization_returned_violation'],
                feedback=o['feedback'],recovery=o['feasibility_recovery'])))
    diagnosis=dict(source=frozen['source'],rows=historical,reconstructed_plan_comparisons=comparisons,
        findings=[
            'The existing 100 ms horizon anticipates the 300 ms holding start from 200 ms; it is not blind until holding starts.',
            'Stage 3.20 retains 51.70 mm/s measured speed at 280 ms. At 290 ms the actual applied command predicts 3.14 mm/s at 300 ms, versus 25.27 mm/s measured; vector error is 23.56 mm/s. Projection alone differs by 1.38 mm/s in velocity vector before this interval.',
            'The three sampled original plans were selected IPOPT iterates 3, 2, 2, had objective improvements and original-feasible returned iterates. Initialization lock is not the observed local cause; limited optimization progress elsewhere is not excluded.',
            'One-period discrepancies have different signs/directions. They include reduced representation, dynamics and time integration differences; this sample cannot uniquely separate them or certify an error bound.',
            'Use a 50 ms empirical temporal margin: move full holding-speed cost to 250 ms while retaining 300--350 ms acceptance. This allows residual motion to decay before the actual window; no fixed velocity-vector correction, new budget, or gain sweep.',
            'Reconstructed full plans are diagnostic re-solves from current states with regenerated constant-tension seeds, not the missing historical selected plans. The 290 ms lead and baseline schedules are identical; that repeated local solve is not additional candidate evidence.',
            'The 240 ms lead reconstruction brakes earlier but predicts a later speed rebound above threshold; local results support a physical test, not a predicted pass.'
        ],scope='World tip velocity from MuJoCo site Jacobian. Exact state/input/time alignment for one-interval comparisons. Long-horizon plans compared as designs, never against later feedback trajectories as pure model error.')
    atomic_json(HERE/'diagnosis.json',diagnosis)
    results={label:evidence(label) for label in ('B','B_correction','A','live')}
    final_b=results['B_correction'] or results['B']
    liveaudit=read(HERE/'live/behavior_audit.json') if (HERE/'live/behavior_audit.json').exists() else None
    output=dict(starting_revision='dbe49b3',implementation_revision=read(HERE/'candidate.json')['source_revision'],
        candidate=read(HERE/'candidate.json'),diagnosis='diagnosis.json',executions=results,
        environment=dict(interpreter=sys.executable,python=platform.python_version(),os=platform.platform(),
            threads=dict(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')),
        gates=dict(B=passes(final_b),A=passes(results['A']),live=passes(results['live'])),
        fresh_backend_executions=sum(e is not None for e in results.values()),live_audit=liveaudit,
        timing_boundaries='Complete delivery includes warm preparation, solver construction/solve, recovery and validation. Recovery validation is also counted in validation: do not sum overlapping columns. Graph construction and public preparation are once per execution. Process time includes reporting; live additionally includes provider decisions. 0.01 s deadlines differ from the 10 s development target.')
    atomic_json(HERE/'results.json',output)
    lines=['# Stage 3.21: window braking and conditional LLM acceptance','',
        'Implementation `'+output['implementation_revision']+'`; original baseline `dbe49b3`. Historical evidence and fixed v2 profile preserved.','',
        'The new reusable `holding_brake_lead_s` recipe field starts holding-speed cost earlier relative to the task window. Zero preserves the old schedule; the tested 0.05 s value is an empirical temporal margin, not a bound on model error. The authoritative 0.35 s task, 0.30–0.35 s sampled window, 10 mm / 0.02 m/s limits, physical model, ideal tensions, 10 ms control period and 0.5 ms physics step are unchanged.','',
        '## Diagnosis','',*['- '+s for s in diagnosis['findings']],'',
        '| State s | Projected velocity vector error mm/s | Next predicted speed mm/s | Next measured speed mm/s | Next vector error mm/s |',
        '|---:|---:|---:|---:|---:|']
    for r in historical:
        a=r['reconstruction'];b=r['one_period_prediction']
        lines.append(f"| {r['time_s']:.2f} | {a['velocity_difference_m_s']*1000:.3f} | {b['predicted_speed_m_s']*1000:.3f} | {b['actual_speed_m_s']*1000:.3f} | {b['velocity_difference_m_s']*1000:.3f} |")
    lines+=['','## Actual physical acceptance','',
        '| Execution | Reach | Sampled settling | Endpoint mm | Window max mm | Window max mm/s | Speed margin mm/s | Mean update s | Misses |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|']
    for label,e in results.items():
        if e is None:
            lines.append(f'| {label} | Not executed | Not executed | — | — | — | — | — | — |');continue
        s=e['summary'];w=s['sampled_settling']
        lines.append(f"| {label} | {s['official_task_success']} ({s['evaluation_validity']}) | {w['passed']} | {s['terminal_error_m']*1000:.4f} | {w['max_error_m']*1000:.4f} | {w['max_speed_m_s']*1000:.4f} | {e['margin']['speed_m_s']*1000:.4f} | {s['mean_update_s']:.3f} | {s['deadline_misses']}/{s['updates']} |")
    for label,e in results.items():
        if e is None:continue
        s=e['summary']
        lines+=['',f"{label}: execution `{s['execution_id']}`, evaluation `{s['evaluation']['artifact_id']}`. Accepted plans {s['accepted_plans']}/{s['updates']}; converged {s['converged_updates']}; initialization selections {s['initialization_selected']}; recovered {s['recovered_plans']}; maximum residual {s['maximum_plan_violation']:.3g}. Solver errors {s['solver_error_count']}; holds {s['hold_last_responses']}; force violation {s['force_bound_violation_n']} N; tension range {s['tension_range_n']} N.",
            '', '| Sample time s | Error mm | Speed mm/s |','|---:|---:|---:|']
        lines += [f"| {r['time_s']:.2f} | {r['tip_error_m']*1000:.4f} | {r['tip_speed_m_s']*1000:.4f} |" for r in e['final_window']]
    lines+=['','## Computation','',output['timing_boundaries'],'',
        '| Execution | Graph s | Solver construction s | Warm mean s | Solve mean s | Recovery mean s | Validation mean s | Process s |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for label,e in results.items():
        if e is None:continue
        s=e['summary'];columns=[s[k] for k in ('graph_construction_s','solver_construction_s','mean_preparation_s','mean_numerical_solve_s','mean_recovery_s','mean_validation_s')]+[e['process']['process_wall_s']]
        lines.append('| '+label+' | '+' | '.join(f'{v:.3f}' for v in columns)+' |')
    lines+=['','## Public path and live acceptance','',
        'The existing v3 preparation freezes the full task, recipe, initialization provenance and evidence scope. `examples/gvs_nmpc_route_experiment.py --input` now accepts a public parameterized SessionInput, rejects changed inputs on resume, and advertises the frozen combination for model selection. No target-specific controller/Route branches or private cache injection. The real-provider project/session ceilings are 24 model calls, 60 tools, one backend and 3600 s. Child-owned reports remain available in current model context.','']
    if liveaudit:
        lines.append(f"Actual provider requests {liveaudit['real_model_requests']}; tools {liveaudit['tool_calls']}; backend executions {liveaudit['backend_executions']}; current report delivered {liveaudit['fresh_report_delivered']}. See live/behavior_audit.json, live/model_final.txt and live/platform.sqlite for unedited provider decisions, responses, receipts and evidence.")
    else:lines.append('Live session not executed. It is conditional on both fresh B and A reach plus full sampled settling; missing outcomes are not passes.')
    lines+=['','## Focused verification and limitations','',
        'Eight focused tests: seven passed initially; the timing fixture attempted to mutate a frozen Pydantic object and was corrected to model_copy. Its focused rerun passed. No full suite. Local numerical solves used three frozen current states; no historical full rollout was repeated.',
        '', 'Evidence covers this fixed robot, tested explicit targets, free space and ideal tensions. Sampled settling is not continuous-time settling. Feasible unfinished optimization does not establish convergence. These executions do not establish robustness, arbitrary-target transfer, hardware performance or real-time control.','',
        '## Reproduction','', 'Use a fresh output folder for a new execution; archived execute.py deliberately refuses to overwrite executed folders. Read-only report consolidation does not consume a backend or model call.','',
        '```powershell',"Set-Location 'D:\\softrobot-agent'","$py = 'C:\\Users\\gugugaga\\miniconda3\\envs\\softagent\\python.exe'",
        "$env:OPENBLAS_NUM_THREADS='1'","$env:OMP_NUM_THREADS='1'","$env:MKL_NUM_THREADS='1'",
        '& $py runs/stage321_window_braking_llm_20260927/report_results.py',
        '& $py examples/gvs_parameterized_reach.py run --input runs/stage321_window_braking_llm_20260927/B_input.json --output runs/repro321_B',
        '# Only after B passes reach and all sampled settling checks:',
        '& $py examples/gvs_parameterized_reach.py run --input runs/stage321_window_braking_llm_20260927/A_input.json --output runs/repro321_A',
        '# Only after both pass; this starts a fresh paid provider session:',
        '& $py examples/gvs_nmpc_route_experiment.py run --input runs/stage321_window_braking_llm_20260927/B_input.json --output runs/repro321_live --wall-s 3600',
        '```']
    (HERE/'implementation_report.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(json.dumps(output['gates']))

if __name__=='__main__':main()
