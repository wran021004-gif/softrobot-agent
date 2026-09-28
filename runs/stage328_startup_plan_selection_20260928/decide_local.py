"""Apply the predeclared gate once to completed paired measurements."""
from startup_analysis import *
assert not (OUT/'local_decision.json').exists()
rule=read(OUT/'local_rule.json')['acceptance']
baseline=read(OUT/'baseline.json');revised=read(OUT/'revised.json')
assert len(baseline['records'])==len(revised['records'])==2
checks=[];pairs=[]
for b,r in zip(baseline['records'],revised['records'],strict=True):
    bs,rs=b['solved'],r['solved']
    assert b['time_s']==r['time_s']
    assert bs['diagnostics']['options']==rs['diagnostics']['options']
    assert bs['prediction_timing']==rs['prediction_timing']
    assert bs['previous_tensions_n']==rs['previous_tensions_n']
    assert bs['measured_initial_state']==rs['measured_initial_state']
    assert bs['diagnostics']['diagnostic_plans']['initial']==rs['diagnostics']['diagnostic_plans']['initial']
    result=dict(time_s=b['time_s'],baseline_peak_m=b['metrics']['peak_m'],revised_peak_m=r['metrics']['peak_m'],
        peak_reduction_m=b['metrics']['peak_m']-r['metrics']['peak_m'],
        baseline_objective=b['independent_check']['objective'],revised_objective=r['independent_check']['objective'],
        baseline_complete_s=b['complete_update_s'],revised_complete_s=r['complete_update_s'],
        added_s=r['complete_update_s']-b['complete_update_s'],ratio=r['complete_update_s']/b['complete_update_s'],
        baseline_terminal_m=b['metrics']['terminal_m'],revised_terminal_m=r['metrics']['terminal_m'],
        baseline_command_change_n=b['metrics']['first_command_change_n'],revised_command_change_n=r['metrics']['first_command_change_n'],
        baseline_recovery_s=bs['recovery']['wall_s'],revised_recovery_s=rs['recovery']['wall_s'],
        baseline_parent_iteration=bs['recovery']['parent_iteration'],revised_parent_iteration=rs['recovery']['parent_iteration'],
        revised_activated=rs['recovery']['activated'],revised_recovery_attempts=rs['recovery']['recovery_attempts'])
    check=dict(feasible=b['independent_check']['feasible'] and r['independent_check']['feasible'],
        objective=r['independent_check']['objective']<=b['independent_check']['objective']*(1+rule['objective_nonincrease_relative_tolerance']),
        added_cost=result['added_s']<=rule['each_added_update_s_at_most'] and result['ratio']<=rule['each_update_ratio_at_most'],
        candidate_cap=rs['recovery']['candidate_count']<=3 and rs['recovery']['recovery_attempts']<=3)
    if b['time_s']==0:
        check['meaningful_startup_peak']=result['peak_reduction_m']>=rule['startup_peak_reduction_at_least_m']
        check['startup_command']=result['revised_command_change_n']<=result['baseline_command_change_n']+rule['startup_first_command_increase_at_most_n']
    else:check['critical_peak']=result['peak_reduction_m']>=-rule['critical_peak_increase_at_most_m']
    checks.append(check);pairs.append(result)
passed=all(all(c.values()) for c in checks)
decision=dict(passed=passed,checks=checks,pairs=pairs,
    full_confirmation_authorized=passed,provider_gate_open=False,
    attempts=dict(diagnostic_nlp=1,baseline_local_nlp=2,revised_invalid_nlp=1,revised_valid_nlp=2,implementation_directions=1,implementation_corrections=1),
    limits='Paired states/warm inputs and all numerical solver options equal. Wall-time stopping may yield different iteration endpoints; no statistical repeatability claim.')
atomic_json(OUT/'local_decision.json',decision)
print(json.dumps(decision,indent=2))
