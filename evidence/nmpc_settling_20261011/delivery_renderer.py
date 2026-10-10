"""Read sealed results to build delivery evidence; never runs scientific work."""
import os,json,time,hashlib,tarfile,sys
os.environ['NMPC_SETTLING_FOLLOWUP']='1'
from copy import deepcopy
from pathlib import Path
from tools.research_casadi_feedback import host
from tools.casadi_feedback_service import SPEC,budget
from tools.state_io import atomic_json,read,digest
from tools.platform_store import plain
from tools.nmpc_settling import OUT,scientific_scope
h=host();s=h.store.session(h.run_id)['state']
base=h.store.artifact(s['source_baseline_reference']);diagnosis=h.store.artifact(s['diagnostic_reference'])
new=[(r,h.store.artifact(r['reference'])) for r in s['results'] if r['operation']=='closed_loop' and not r.get('imported')]
plans=[dict(reference=r['reference'],original=h.store.artifact(r['reference'])) for r in s['plans']]

def metrics(v):
 p=v.get('profile') or {};hold=v.get('holding_motion',[])
 return dict(execution_id=v.get('execution_references',{}).get('execution_id'),owner=v.get('execution_references',{}).get('owner_run_id'),
  status=v['status'],joint_acceptance=v.get('acceptance'),terminal_error_m=p.get('terminal_error_m'),terminal_speed_m_s=p.get('terminal_tip_speed_m_s'),
  holding_max_error_m=max([m['tip_error_m'] for m in hold],default=None),holding_max_speed_m_s=max([m['tip_speed_m_s'] for m in hold],default=None),
  holding_samples=hold,speed_exceedance_times_s=[m['time_s'] for m in hold if m['tip_speed_m_s']>.02],position_exceedance_times_s=[m['time_s'] for m in hold if m['tip_error_m']>.01],
  control=v['control'],costs_s=v['costs_s'],updates=p.get('updates'),applied_updates=p.get('applied_control_updates'),
  plan_selection=dict(initialization=p.get('initialization_selected'),recovered=p.get('recovered_plans'),other_feasible=p.get('other_feasible_deliveries'),accepted_noninitialization=p.get('accepted_noninitialization_plans')),
  recovery=dict(attempts=p.get('recovery_attempts'),selected=p.get('recovered_plans'),failed=p.get('recovery_failures'),root_solves=p.get('recovery_root_solves')),
  stops=p.get('policy_stop_reason_counts'),raw_stops=p.get('raw_termination_counts'),input_range_n=p.get('tension_range_n'),input_bound_violation_n=p.get('force_bound_violation_n'),
  prediction_summary=p.get('one_step_prediction_summary'),real_time=p.get('real_time_demonstrated'),deadline_misses=p.get('deadline_misses'),failure_categories=v.get('failure_categories'),
  feedback=v.get('settling_feedback'))

b=metrics(base);runs=[];configurations=[]
from extensions.tendon_family.control_evidence import ControlEvidence
reader=ControlEvidence(h.store)
for i,(row,v) in enumerate(new):
 role='development' if i==0 else 'exact_confirmation';m=metrics(v);m.update(role=role,reference=row['reference'])
 runs.append(m)
 cfg=h.store.artifact(v['resolved_configuration']);old=h.store.artifact(s['source_binding'])['source']['configuration']
 expected=deepcopy(old)
 for key in ('holding_tip_speed_weight','terminal_tip_speed_weight'):expected['policy']['controller']['parameters']['data']['recipe'][key]=v['control'][key]
 comparisons=dict(role=role,reference=row['reference'],full_scientific_identity=digest(scientific_scope(cfg)),
  baseline_identity=digest(scientific_scope(old)),one_weight_change={k:dict(before=old['policy']['controller']['parameters']['data']['recipe'][k],after=cfg['policy']['controller']['parameters']['data']['recipe'][k]) for k in ('holding_tip_speed_weight','terminal_tip_speed_weight') if old['policy']['controller']['parameters']['data']['recipe'][k]!=cfg['policy']['controller']['parameters']['data']['recipe'][k]},
  only_declared_scientific_change=scientific_scope(expected)==scientific_scope(cfg),recover_returned_tensions=cfg['policy']['controller']['parameters']['data']['recipe']['recover_returned_tensions'],
  seed=cfg['seed'],initializer=cfg['task']['initializer'],timing=cfg['task']['timing'],independent_execution_id=m['execution_id'],saved_future_state_injected=False)
 configurations.append(comparisons)
 atomic_json(OUT/(role+'_configuration.json'),cfg);atomic_json(OUT/(role+'_configuration_comparison.json'),comparisons)
 if v.get('profile'):
  source=reader.resolve(m['execution_id'])
  for filename,target in [('controller_observations.json','controller_observations'),('control_snapshots.json','control_snapshots'),('actual_commands.json','actual_commands')]:
   atomic_json(OUT/(role+'_'+target+'.json'),reader.read_file(source,filename,[]))
  newdiag=h.store.artifact(v['settling_feedback']['diagnostic_reference'])
  atomic_json(OUT/(role+'_diagnostic_timeline.json'),newdiag)
  comparison=[]
  snapshots=reader.read_file(source,'control_snapshots.json',[])
  for update in (29,30):
   oldrow=next(x for x in diagnosis['rows'] if x['update_id']==update);newrow=next(x for x in newdiag['rows'] if x['update_id']==update);snap=next(x for x in snapshots if x['update_id']==update)
   comparison.append(dict(update_id=update,next_sample_s=oldrow['next_prediction']['time_s'],baseline_predicted_speed_m_s=float(sum(x*x for x in oldrow['next_prediction']['tip_velocity_m_s'])**.5),new_predicted_speed_m_s=float(sum(x*x for x in newrow['next_prediction']['tip_velocity_m_s'])**.5),
    measured_next_velocity=newrow['next_aligned_prediction']['velocity'],baseline_full_cost_breakdown=None,baseline_first_node_costs=oldrow['saved_first_node_costs'],new_full_cost_breakdown=snap['plans']['delivered']['objective_components'],
    new_plan_summaries={k:dict(verification=plan['verification'],first_step=plan['metrics']['first_step'],terminal=plan['metrics']['terminal']) for k,plan in snap['plans'].items()},
    raw_solver=snap['selection'],actual_applied_input_n=snap['actual_executed_input_n'],cross_weight_total_objective_ranking_performed=False))
  atomic_json(OUT/(role+'_holding_prediction_comparison.json'),comparison)
  atomic_json(OUT/(role+'_motion.json'),h.store.artifact(v['profile']['motion']))

ledger=h.store.remaining();counts=dict(actual_provider_requests=ledger['used']['model_calls'],pilot_provider_requests=s['pilot']['live_model_requests'],public_calls=ledger['used']['tool_calls'],
 standalone_local_nlp_attempts=s['new_local_nlp_attempts'],mujoco_launches=ledger['used']['backend_solves'],closed_loop_internal_nmpc_attempts=sum(v.get('nmpc_internal_solves',0) for _,v in new),
 internal_recovery_attempts=sum((v.get('profile') or {}).get('recovery_attempts',0) for _,v in new),internal_recovery_root_solves=sum((v.get('profile') or {}).get('recovery_root_solves',0) for _,v in new),
 extra_research_models=0,structure_optimization=0,full_offline_nlp=0,bdf=0,hardware=0)
accepted=bool(s.get('final_disposition'));final=h.store.artifact(s['final_disposition']) if accepted else None
summary=dict(schema='bounded_nmpc_settling_followup_v1',study_id=SPEC['study_id'],source_commit=SPEC['base_commit'],implementation_commit=s['freeze'],delivery_branch='feat/nmpc-settling-followup',
 status='accepted_native_stop' if accepted else 'protective_program_stop_without_model_completion',specification=SPEC,baseline=dict(b,imported=True,reference=s['source_baseline_reference'],new_cost_s=0),
 diagnostic_reference=s['diagnostic_reference'],diagnostic_file='diagnostic_timeline.json',source_binding=s['source_binding'],source_verification='source_verification.json',
 new_executions=runs,configuration_comparisons=configurations,confirmation_performed=len(runs)==2,
 confirmation_full_scientific_identity_matches=len(configurations)==2 and configurations[0]['full_scientific_identity']==configurations[1]['full_scientific_identity'],
 repeat_identity_audit=read(OUT/'repeat_identity_audit.json'),model_original_plans=plans,model_original_final_disposition_reference=s.get('final_disposition'),model_original_final_disposition=final,
 counts=counts,used_budget=dict(scientific_s=s['numerical_s'],project=ledger['used'],local_nlp_s=s['local_nlp_cost_s'],activity_elapsed_s=time.time()-s['started_unix']),remaining_budget=budget(h.store),
 interpretation=dict(archived_cause_resolved_to='Hold penalty is active and first predictions already overspeed/overpredict actual; interior inputs and configured early-stop policy. Exact whole-horizon cost/iteration causality at late updates was not saved.',
 methods_supplied_by_task='Frozen task, archive diagnosis and bounded action menu',codex_contribution='Engineering, factual arithmetic, guards, tests, evidence/reporting',model_contribution='Actual hypotheses, one weight/value choice, optional experiment/confirmation choices and original STOP',
 supplied_prior_context='Task supplied, not autonomous memory retrieval'),
 limits=['One tested weight/value does not establish ineffectiveness of all in-range speed weights.','One development and at most one exact configuration repeat do not establish robustness.','Complete historical late-iteration and cost decomposition remain unknown.','Sampled acceptance is not a continuous-time, real-time or hardware guarantee.','Wall-time based early termination may produce different numerical trajectories on an unchanged repeat.'])
if runs:
 summary['development_improvement']=dict(holding_max_speed_change_m_s=runs[0]['holding_max_speed_m_s']-b['holding_max_speed_m_s'],
  holding_speed_reduction_fraction=1-runs[0]['holding_max_speed_m_s']/b['holding_max_speed_m_s'],joint_acceptance=runs[0]['joint_acceptance']['status'])
atomic_json(OUT/'scientific_summary.json',summary);atomic_json(OUT/'result_summary.json',summary)
atomic_json(OUT/'configuration_comparison.json',configurations)
atomic_json(OUT/'all_executions_and_costs.json',dict(inherited_baseline_new_cost_s=0,new_executions=runs,preparation_costs_s=s.get('preparation_costs_s'),initial_scoped_checks=s.get('initial_scoped_checks_charged'),final_prebind_checks=s.get('final_prebind_checks_charged'),delivery_initial_state_audit_s=s.get('delivery_initial_state_audit_cost_s'),delivery_final_identity_checks_s=s.get('delivery_final_identity_checks_s'),plan_validation_costs_s=s.get('plan_validation_costs_s'),science_total_s=s['numerical_s'],local_pair_s=s['local_nlp_cost_s'],counts=counts))
events=h.store.events(h.run_id)
atomic_json(OUT/'decision_trace.json',[dict(event=e,original=h.store.artifact(e['outputs'][0]) if e.get('outputs') else None) for e in events if e['kind'] in ('model_original_tool_request','model_original_tool_feedback','model_plan_execution_feedback','model_original_turn','live_cycle_incomplete')])

# Cases and procedure remain recommendation-only, preserving the earlier record.
case=read(Path('memory/nmpc_feasibility_case_draft.json'))
case['settling_followup']=dict(study_id=SPEC['study_id'],status='reference_backed_draft',summary_file='evidence/nmpc_settling_20261011/scientific_summary.json',diagnostic_reference=s['diagnostic_reference'],baseline_reference=s['source_baseline_reference'],
 new_result_references=[r['reference'] for r,_ in new],confirmed_facts=dict(baseline_overspeed_times=b['speed_exceedance_times_s'],prediction_overestimates_at_first_hold_nodes=True,hold_cost_active=True,new_execution_metrics=[dict(role=r['role'],reference=r['reference'],execution_id=r['execution_id'],joint_acceptance=r['joint_acceptance']['status'],terminal_error_m=r['terminal_error_m'],holding_max_error_m=r['holding_max_error_m'],holding_max_speed_m_s=r['holding_max_speed_m_s'],speed_exceedance_times_s=r['speed_exceedance_times_s'],updates=r['applied_updates'],recovery=r['recovery']) for r in runs]),
 scope='Frozen task and sampled acceptance; one tested speed-weight value, optional exact repeat; not robustness or automatic reuse',unknowns=summary['limits'],formal_admission='Not performed; no fabricated approval or automatic reuse')
atomic_json(Path('memory/nmpc_feasibility_case_draft.json'),case)
procedure=Path('docs/nmpc_feasibility_procedure.md')
addition="""
## Recovery-enabled holding-speed follow-up

The [follow-up summary](../evidence/nmpc_settling_20261011/scientific_summary.json)
extends the earlier case. Use the latest recovery-enabled configuration and its
owned immutable state; never substitute the older recovery-disabled state.
Align sample t with update t-dt, check that predicted input equals actual input,
and retain velocity vectors, not just scalar speed. At .30/.31s the archived
predictions already overestimated actual speed and holding cost was active.
Inspect h/dt factors and normalization; soft penalties do not impose hard
sampled speed limits. Compute only saved first-node/terminal terms; missing
whole-horizon vectors/cost decompositions and iteration traces remain unknown.

A new local comparison, if chosen, uses one identical newly constructed seed in
both arms and is not historical optimizer reproduction. Change one permitted
speed weight, keep recovery True and all scientific settings frozen. Return
actual local feedback before any closed-loop decision. A local gain need not
transfer to the simulator. One unsuccessful tested value does not assess the
whole allowed range. Preserve negative outcomes and all failed samples.

An unchanged confirmation uses its own explicit native action, verifies complete
scientific identity and starts independently from the prescribed initial state.
Report exact configuration repetition separately from repeatability of numerical
outputs and from robustness. Wall-time based solver stopping may differ across
repeats. Use only one development and one optional exact confirmation. STOP
binds latest execution/reference and timestamped used/remaining budget; concrete
ledger corrections are returned before accepting STOP. No provider send follows
accepted STOP. These remain reference-backed drafts with no legacy admission
recheck, database, validation claim, human approval or automatic reuse.
"""
if '## Recovery-enabled holding-speed follow-up' not in procedure.read_text():procedure.write_text(procedure.read_text()+addition)

answers=dict(control_adjustment_improved=bool(runs and runs[0]['holding_max_speed_m_s']<b['holding_max_speed_m_s']),original_joint_acceptance=[r['joint_acceptance']['status'] for r in runs],confirmation_performed=len(runs)==2,confirmation_result=None if len(runs)<2 else runs[1]['joint_acceptance']['status'],remaining_overspeed_cause='Active soft cost, predicted overspeed, interior inputs and early termination verified; dominant full-horizon cost/unique cause unknown')
summary['task_answers']=answers
atomic_json(OUT/'scientific_summary.json',summary);atomic_json(OUT/'result_summary.json',summary)
lines=['# Bounded recovery-enabled holding-speed follow-up','',
 'The one-weight development passed, but its exact scientific-configuration confirmation failed holding speed. A repeatable improvement has not been demonstrated.' if len(runs)==2 else f"Development improvement: {answers['control_adjustment_improved']}; confirmation not performed.",'',
 'The archived failure occurs with active holding cost and predicted speed already above actual speed. The new study used the existing DeepSeek model and frozen task; the model chose the actual weight and experiments.','',
 '| Execution | Terminal error mm | Holding max error mm | Holding max speed m/s | Overspeed samples s | Joint acceptance |',
 '|---|---:|---:|---:|---|---|']
for label,m in [('Inherited recovery baseline',b)]+[(r['role'],r) for r in runs]:
 lines.append(f"| {label} | {1000*m['terminal_error_m']:.3f} | {1000*m['holding_max_error_m']:.3f} | {m['holding_max_speed_m_s']:.9f} | {[round(t,2) for t in m['speed_exceedance_times_s']]} | {m['joint_acceptance']['status']} |")
lines+=['','The development changes only holding_tip_speed_weight from .05 to .10; terminal speed weight remains .10 and recovery True. Complete generated physics/task/initial state/seed/timing/solver/evaluation identity is checked. No baseline or historical optimization was rerun.','',
 'The .29s update predicted .30s speed .026699464m/s versus measured .020493825; the .30s update predicted .31s speed .031330296 versus .024642722. Both first-node hold flags are active. Late inputs are interior; .29/.30s early-stop reasons are relative_seed_improvement, selected iteration4. At .32s verified_settled_seed selected iteration0 carries changed prior inputs. No exception fallback is implied.','',
 'The identical-configuration executions share the same numerical guess and independent zero physical initial state. Their first applied command divergence is update8/.08s: measured state, previous input and prediction timing are identical and no holding node is active. Both stop by budget_best_feasible, but raw recovery parents are iterations16/19 and delivery selections differ. Earlier complete warm plans are unrecorded, so this identifies optimizer/selection path variability without isolating its unique source.','',
 'The saved first-node holding cost is .000891077/.001226984 at updates29/30. Running terms include h=.01; terminal speed does not. Position and velocity normalization matter. These supported partial terms cannot establish the dominant complete horizon cost. The archived full snapshot is only update20; missing late vectors, intermediate nodes and full iteration/cost decompositions remain unknown.','',
 f"Actual counts: {counts['actual_provider_requests']} provider sends, {counts['public_calls']} public calls, {counts['standalone_local_nlp_attempts']} standalone local NLP attempts, {counts['mujoco_launches']} MuJoCo launches, {counts['closed_loop_internal_nmpc_attempts']} internal NMPC attempts, {counts['internal_recovery_attempts']} internal recoveries / {counts['internal_recovery_root_solves']} roots. No codesign/BDF/hardware/extra research model.",'',
 f"Scientific time charged {s['numerical_s']:.3f}s of3600s; remaining {3600-s['numerical_s']:.3f}s. Actual project ledger and six-hour activity/delivery reserve are in the machine summary. All updates and wall-clock real-time performance are separate below. Repeated artifact references are not repeated executions.",'',
 f"Confirmation performed: {len(runs)==2}; exact scientific identity matches: {summary['confirmation_full_scientific_identity_matches']}.",'',
 'Original model decisions, hypotheses and STOP are preserved in plan files and immutable events/archive. Codex supplied implementation, arithmetic and task context, not autonomous model memory or its scientific decisions. The original model causal hypothesis remains a hypothesis: the historical complete dominant cost and unique cause are unknown. One tested value cannot establish all weights ineffective; a repeated configuration cannot establish robustness or continuous-time/hardware performance.','',
 'Validation: nine focused new checks passed; no full suite, broad benchmark or repeated old mechanics validation. The initial policy compile failure was repaired without a provider send or numerical experiment, and its cost/time were retained. Existing Python/dependencies were reused without upgrades.','',
 f"Implementation freeze: `{s['freeze']}`. Source: `{SPEC['base_commit']}`. Delivery: `feat/nmpc-settling-followup`.",'',
 '[Machine-readable summary](../evidence/nmpc_settling_20261011/scientific_summary.json), [diagnostic timeline](../evidence/nmpc_settling_20261011/diagnostic_timeline.json), [commands](../evidence/nmpc_settling_20261011/execution_commands.json), [runbook](nmpc_settling_runbook.md), [case draft](../memory/nmpc_feasibility_case_draft.json), [procedure draft](nmpc_feasibility_procedure.md).','']
for r in runs:
 lines+=['```json',json.dumps({k:r[k] for k in ['role','execution_id','control','applied_updates','plan_selection','recovery','stops','raw_stops','input_range_n','prediction_summary','real_time','deadline_misses','costs_s']},indent=2),'```','']
if accepted:lines+=['Original final disposition (preserved, not rewritten):','',final['disposition'],'',*['- '+x for x in final['limitations']],'']
Path('docs/nmpc_settling_completion.md').write_text('\n'.join(lines))
print(json.dumps(dict(counts=counts,runs=[{k:r[k] for k in ['role','terminal_error_m','holding_max_error_m','holding_max_speed_m_s','speed_exceedance_times_s']} for r in runs],accepted_stop=accepted,scientific_s=s['numerical_s'])))
