"""Read-only independent audit of sealed receipts, not a research action."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from examples import research_campaign_v2 as previous
from examples import research_campaign_v3 as current
from examples import research_model_v1 as pilot
from tools.candidate_parameters import parameter_value,project_planning_configuration
from tools.fixed_research import schedule, select_candidate
from tools.research_spec import load_spec,apply_frozen_case
from tools.research_tasks import aggregate_acceptance, compare_acceptance
from tools.state_io import atomic_json, digest, read

DIRECTORY = ROOT / 'runs/research_native_development_v3_20261007'
OUT = Path(__file__).resolve().parent


def review():
    w = pilot.restore(DIRECTORY.resolve())
    spec = load_spec()
    rows = previous.search_rows(w)
    paths = list(spec['parameter_grants'])
    observations = []
    for row in rows:
        effective = w.store.artifact(row['configuration'])['effective']
        record = next(r for r in w.records if r['execution_id'] == row['receipt']['execution_id'])
        facts = record['facts']
        observations.append(dict(candidate_id=row['candidate_id'], execution_id=facts['execution_id'],
            configuration=row['configuration'], parameters={p:parameter_value(effective,p) for p in paths},
            changes=row['changes'], case_id=row['case_id'],seed=row['seed'],
            task_identity=row['acceptance']['task_identity'],
            initial_state=effective['task']['initializer']['parameters']['data'],
            controller=effective['policy']['controller'],acceptance=row['acceptance'],
            force_bound_violation_n=facts['force_bound_violation_n'],solver_error_count=facts['solver_error_count'],
            receipts=record['receipts'],implementation=record['implementation']))
    accepted = read(OUT/'repair_and_plan_resume_boundary.json')['migration']['authorization']['accepted_plan']
    resumed = [r for r in w.rounds if r.get('resumed_accepted_decision')]
    decisions = [dict(index=r['index'], action=r['decision']['decision']['action'],
        accepted_decision=r['accepted_decision'],decision=r['decision']['decision'],
        interpretations=r['decision']['model_interpretations'],
        interpretation_bindings=r['decision'].get('interpretation_bindings'),
        feedback=r.get('feedback'),result=r.get('result'),complete=r.get('complete'),
        execution_only_resume=bool(r.get('resumed_accepted_decision'))) for r in w.rounds]
    model6 = next((r for r in w.rounds if r['accepted_decision']['artifact_id'].startswith('74b1bcf6')),None)
    corrections = []
    if model6:
        near = [r for r in observations if r['candidate_id'].startswith('batch-acf51de37cc32112-')]
        corrections = [dict(decision=model6['accepted_decision'], issue='near_1_05_control_confound_false',
            correction='Both executed near-section candidates held terminal and holding speed weights at 0.05; only near_section_scale changed.',
            configurations=[r['configuration'] for r in near]),
            dict(decision=model6['accepted_decision'],issue='historical_dominance_scope',
                correction='Historical unspecified-zero and fresh explicit-zero task identities differ. Numerical historical comparisons are descriptive, not fresh matched causal comparisons. Nominal joint-pass terminal-weight 0.10 remains eligible under the frozen rule.'),
            dict(decision=model6['accepted_decision'],issue='unsupported_F437_scope_claim',
                correction='F437 binds mean_complete_update_s for the second near candidate; it does not establish untested structural scope.'),
            dict(decision=model6['accepted_decision'],issue='controller_name_typo',
                correction='Authoritative plan and executions use controller.gvs_nmpc@7.0.0; prose gvs_normpc is incorrect.')]
    # Later rejected responses do not appear in accepted research rounds.
    # Retain them as attempted decisions, never as executed research batches.
    native_attempts=[]
    for event in w.store.events(w.host.run_id):
        if event['kind']!='model_raw_response' or event['status']!='completed':continue
        raw=w.store.artifact(event['outputs'][0]);raw=raw.get('raw',raw)
        tool_calls=raw['choices'][0]['message'].get('tool_calls') or []
        for tool in tool_calls:
            try:arguments=json.loads(tool['function']['arguments'])
            except (ValueError,KeyError):continue
            if 'action' not in arguments:continue
            receipt=w.store.lookup(w.host.run_id,event['request_id']+'-tool')
            native_attempts.append(dict(request_id=event['request_id'],raw_response=event['outputs'][0],
                native_arguments=arguments,dispatch_receipt=json.loads(receipt['receipt']) if receipt and receipt['receipt'] else None))
    rejected_budget=next((r for r in native_attempts if r['request_id']=='model-8'),None)
    if rejected_budget and rejected_budget['dispatch_receipt']:
        error=rejected_budget['dispatch_receipt'].get('error','')
        if error.startswith('PLAN_TOTAL_CAPACITY_INSUFFICIENT:'):
            corrections.append(dict(decision_request='model-9',issue='planned_shortfall_misread_as_zero_available_capacity',
                original_rejection=error,actual_planned_budget=rejected_budget['native_arguments']['plan']['planned_budget'],
                correction='The rejection reports planned-budget shortfall wall_s=590 and actual-available shortfall wall_s=0. It does not report available wall_s=0. The proposed 2000s budget omitted part of the complete execution+interpretation requirement. No length candidate executed. Subsequent STOP is retained as a voluntary model decision, not evidence of exhausted resources or an optimal scientific stopping point.',
                conditional_verification_gate=read(DIRECTORY/'conditional_verification_gate.json') if (DIRECTORY/'conditional_verification_gate.json').exists() else None))
    matched = None
    path = DIRECTORY/'verification.json'
    if path.exists():
        result = read(path)
        slots = schedule(spec)
        groups = result['groups']
        recomputed = [aggregate_acceptance(g['records'],10,schedule=slots) for g in groups]
        actual_slots = [(g['role'],r['case_id'],r['seed'],r['repetition'])
            for slot in slots for g in groups for r in g['records']
            if (r['case_id'],r['seed'],r['repetition'])==(slot['case_id'],slot['seed'],slot['repetition'])]
        executions = [r['receipt']['execution_id'] for g in groups for r in g['records'] if r.get('receipt')]
        binding_checks = []
        physical_receipt_checks = []
        for g in groups:
            expected = (w.store.artifact(result['plan']['selected_candidate']['configuration'])['effective']
                if g['role']=='selected_candidate' else spec['starting_configuration']['effective'])
            projected=project_planning_configuration(expected,spec['execution_template']['policy'])
            for r in g['records']:
                effective=w.store.artifact(r['configuration'])['effective']
                expected_case=apply_frozen_case(expected,r['case_id'],r['seed'],spec['cases'])
                binding_checks.append(dict(candidate_id=r['candidate_id'],
                    parameters_match=all(parameter_value(effective,p)==parameter_value(projected,p) for p in paths),
                    frozen_initial_state_matches=effective['task']['initializer']==expected_case['task']['initializer'],
                    frozen_task_timing_matches=effective['task']['timing']==expected_case['task']['timing'],
                    frozen_controller_backend_dynamics_match=all(effective['policy'][k]==expected_case['policy'][k]
                        for k in ('controller','backend','dynamics_model','discretization')),
                    execution_id=r['receipt']['execution_id'],case_id=r['case_id'],seed=r['seed'],
                    acceptance_identity_matches=r['receipt']['execution_id']==r['acceptance']['execution_id']))
                report=w.store.artifact(r['profile'])['detail']
                evaluation=w.store.artifact(r['evaluation'])
                motion=w.store.artifact(report['motion'])
                duration=effective['task']['timing']['duration_s']
                limits=effective['policy']['controller']['parameters']['data']['settling']
                samples=[s for s in motion if duration-limits['window_s']-1e-9<=s['time_s']<=duration+1e-9]
                recomputed_physical=dict(terminal_error_m=next(m['value'] for m in evaluation['metrics'] if m['name']=='position_error'),
                    holding_max_error_m=max(s['tip_error_m'] for s in samples),
                    holding_max_speed_m_s=max(s['tip_speed_m_s'] for s in samples))
                period=effective['task']['timing']['sample_period_s']
                expected_count=round(limits['window_s']/period)+1
                grid=[duration-limits['window_s']+i*period for i in range(expected_count)]
                sample_grid_matches=len(samples)==expected_count and all(abs(s['time_s']-t)<=1e-8 for s,t in zip(samples,grid))
                recomputed_joint=(evaluation['validity']=='valid' and evaluation['task_success'] is True and
                    report['complete'] is True and sample_grid_matches and report['solver_error_count']==0 and
                    0<=report['force_bound_violation_n']<=1e-8 and
                    recomputed_physical['holding_max_error_m']<=limits['position_limit_m'] and
                    recomputed_physical['holding_max_speed_m_s']<=limits['speed_limit_m_s'])
                physical_receipt_checks.append(dict(candidate_id=r['candidate_id'],
                    profile_execution_matches=report['execution_id']==r['receipt']['execution_id'],
                    official_evaluation_execution_matches=evaluation['source_execution_id']==r['receipt']['execution_id'],
                    official_evaluation_validity=evaluation['validity'],
                    inclusive_holding_sample_count=len(samples),
                    inclusive_holding_grid_matches=sample_grid_matches,
                    independently_recomputed_metrics=recomputed_physical,
                    metric_values_match=recomputed_physical==r['acceptance']['metrics'],
                    independently_recomputed_joint=recomputed_joint,
                    joint_acceptance_matches=recomputed_joint==r['acceptance']['accepted'],
                    sample_fields=sorted(samples[0]) if samples else [],
                    profile_holding=report['sampled_settling'],
                    force_bound_violation_n=report['force_bound_violation_n'],
                    solver_error_count=report['solver_error_count'],
                    updates=report['updates'],deadline_misses=report['deadline_misses'],
                    mean_complete_update_s=report['mean_update_s'],
                    backend_wall_s=r['receipt']['charged']['wall_s']))
        order=[]
        with w.store.connect(True) as db:
            for call in db.execute('SELECT run_id,receipt FROM calls ORDER BY rowid'):
                if call['receipt'] and call['run_id'].startswith('v2-verify-'):
                    receipt=json.loads(call['receipt'])
                    if receipt['tool_id']=='simulation.run': order.append(call['run_id'])
        expected_order=[r['candidate_id'] for slot in slots for g in groups for r in g['records']
            if (r['case_id'],r['seed'],r['repetition'])==(slot['case_id'],slot['seed'],slot['repetition'])]
        comparison=compare_acceptance(recomputed[1],recomputed[0]) if len(groups)==2 and result['complete'] else None
        eligible_selected=select_candidate([r for r in rows if r['case_id']=='nominal'])
        eligibility_selection={k:deepcopy(eligible_selected[k]) for k in ('candidate_id','configuration','changes')} if eligible_selected else None
        matched=dict(complete=result['complete'],groups=recomputed,comparison=comparison,
            improvement_supported=result['improvement_supported'], unique_execution_count=len(set(executions)),
            frozen_eligibility_selection_matches=result['plan']['selected_candidate']==eligibility_selection,
            frozen_schedule_matches=result['plan']['schedule']==slots,
            frozen_role_order_matches=[g['role'] for g in groups]==['unchanged_incumbent','selected_candidate'],
            deterministic_candidate_ids_match=all(r['candidate_id']==f'v2-verify-{g["role"]}-{r["case_id"]}-rep{r["repetition"]}' for g in groups for r in g['records']),
            recorded_execution_count=len(executions),original_frozen_order_preserved=order==expected_order,
            actual_dispatch_order=order,binding_checks=binding_checks,
            physical_receipt_checks=physical_receipt_checks,
            aggregate_receipts_match=[a==b['acceptance'] for a,b in zip(recomputed,result['aggregates'])],
            all_rows_actual_fresh_receipts=all(e['fresh_execution'] and e['acceptance_execution_matches']
                for a in recomputed for e in a['entries']))
    authorization=read(OUT/'repair_and_plan_resume_boundary.json')['migration']['authorization']
    final_report_path=DIRECTORY/'final_model_interpretation.json'
    final_report=read(final_report_path) if final_report_path.exists() else None
    final_report_is_current=bool(final_report and w.rounds and
        final_report.get('accepted_decision')==w.rounds[-1]['accepted_decision'] and
        final_report.get('index')==w.rounds[-1]['index'] and final_report.get('index',-1)>6)
    sealed=authorization['sealed_failure']
    sealed_unchanged=hashlib.sha256((ROOT/sealed['path']).read_bytes()).hexdigest()==sealed['sha256']
    calls=[]
    with w.store.connect(True) as db:
        for c in db.execute('SELECT run_id,request_id,status,charged,receipt FROM calls ORDER BY rowid'):
            calls.append(dict(run_id=c['run_id'],request_id=c['request_id'],status=c['status'],charged=json.loads(c['charged']),
                receipt_present=bool(c['receipt'])))
    output=dict(version='independent_structural_results_review@1.0.0',reviewed_unix=time.time(),
        status=w.status,stop_reason=w.stop_reason,repairs=w.repairs,usage=w.store.remaining(),
        same_campaign=w.freeze['campaign_id'] if 'campaign_id' in w.freeze else w.host.run_id,
        original_deadline_preserved=w.freeze['live_clock']==authorization['clock'],
        sealed_previous_delivery_unchanged=sealed_unchanged,
        implementation_files_unchanged=current.seal()['files']==w.freeze['implementation']['files'],
        accepted_plan=accepted,execution_only_resumed_rows=[r['index'] for r in resumed],
        scientific_observations=observations,decisions=decisions,native_attempts=native_attempts,
        latest_final_model_report=final_report if final_report_is_current else None,
        final_model_report_is_current=final_report_is_current,
        final_reporting_blocker=read(OUT/'final_report_blocker_review.json') if (OUT/'final_report_blocker_review.json').exists() else None,
        independent_model_interpretation_corrections=corrections,matched_verification=matched,
        calls=calls,settled_all_calls=all(c['receipt_present'] and c['status'] not in ('running','unknown') for c in calls),
        unresolved_calls=[c for c in calls if not c['receipt_present'] or c['status'] in ('running','unknown')],
        original_limits_unchanged=w.store.remaining()['limit']==authorization['original_limits'],
        standalone_numerical_operations=0,workers=0,new_model_roles=0,
        limitations=['Finite model-proposed enumeration, not numerical optimization.',
            'Sampled holding observations are not continuous-time guarantees.',
            'Real-time feasibility is not demonstrated and is not a frozen acceptance condition.',
            'No global optimum, causal proof, population reliability or LLM superiority established.'])
    checks=dict(original_deadline=output['original_deadline_preserved'],original_limits=output['original_limits_unchanged'],
        sealed_previous_delivery=sealed_unchanged,implementation_files=output['implementation_files_unchanged'])
    if matched and matched['complete']:
        checks.update(unique_twenty=matched['unique_execution_count']==matched['recorded_execution_count']==20,
            frozen_eligibility_selection=matched['frozen_eligibility_selection_matches'],
            frozen_schedule=matched['frozen_schedule_matches'],frozen_role_order=matched['frozen_role_order_matches'],
            deterministic_candidate_ids=matched['deterministic_candidate_ids_match'],
            frozen_order=matched['original_frozen_order_preserved'],aggregates=all(matched['aggregate_receipts_match']),
            actual_fresh_receipts=matched['all_rows_actual_fresh_receipts'],
            parameter_initial_state_scope=all(all(v for k,v in c.items() if k.endswith('_matches') or k.endswith('_match'))
                for c in matched['binding_checks']),
            independent_physical_metrics_and_joint=all(c['metric_values_match'] and c['joint_acceptance_matches'] and
                c['inclusive_holding_grid_matches'] and c['profile_execution_matches'] and c['official_evaluation_execution_matches']
                for c in matched['physical_receipt_checks']))
    output['independent_checks']=checks
    output['independent_checks_passed']=all(checks.values())
    atomic_json(OUT/'independent_results_review.json',output)
    if matched and matched['complete'] and output['independent_checks_passed']:
        promotion=matched['comparison']['relation']=='improved'
        frozen=read(DIRECTORY/'verification.json')['plan']['selected_candidate']
        selection=dict(version='frozen_matched_selection_review@1.0.0',
            complete=True,independent_checks_passed=True,improvement_supported=promotion,
            selected_configuration=frozen if promotion else spec['source']['candidate'],
            outcome='promote_frozen_candidate' if promotion else 'retain_unchanged_incumbent',
            comparison=matched['comparison'],aggregates=matched['groups'],
            independent_review='independent_results_review.json',
            model_selected_at_research_stop=w.selected,
            final_model_report=output['latest_final_model_report'],
            scope='Post-verification frozen-rule delivery; original sealed research STOP and its prior selected identity remain unchanged. No research reopening, tuning, candidate replacement or retries.')
        atomic_json(OUT/'final_frozen_selection.json',selection)
    print(json.dumps(dict(status=output['status'],research_count=len(observations),
        matched_complete=matched['complete'] if matched else None,usage=output['usage']),ensure_ascii=False))
    return output


if __name__=='__main__':
    review()
