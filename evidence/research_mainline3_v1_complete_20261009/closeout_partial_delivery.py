"""Publish bounded partial delivery from saved records, without inference or science."""
from pathlib import Path
import json,time,subprocess
from collections import Counter
from tools import research_v1_continue as activity
from tools.platform_store import Store,zero,plain,now
from tools.platform_host import Host
from tools.research_investigations import InvestigationDispatcher,SourceFact
from tools.research_validation_activity import export
from tools.research_single_validation import sha
from tools.state_io import read,atomic_json,digest

activity.OUT=(Path.cwd()/'evidence/research_mainline3_v1_complete_20261009').resolve()
out=activity.OUT;m,cfg=activity.check();p=m['phases']['coordinated'];s=Store(activity.ROOT/p['output']);run=p['active_run_id']
assert s.session(run)['status']=='stopped'
assert not (activity.ROOT/m['phases']['fixed']['output']).exists()
b=read(out/'coordinated_bundle.json');nodes=b['state']['investigations'];arts=b['artifacts']
h=Host(s.root,run);d=InvestigationDispatcher(h);principal=read(out/'principal_last_expanded_return.json');dec=principal['dispositions'][0]
inspections=b['state'].get('principal_investigation_reads',[])
audited=[];missing=[];scopes=[]
for area,rows in [('evidence_used',dec['evidence_used'])]+[(f'adopted_claims/{i}/{area}',c[area]) for i,c in enumerate(dec['adopted_claims']) for area in ('supporting_facts','additional_support','scope')]:
 for i,f in enumerate(rows):
  d._validate_fact(SourceFact.model_validate(f),'PRINCIPAL')
  inspected=any(d._visible(SourceFact.model_validate(f),r) for r in inspections)
  row=dict(location=f'/dispositions/0/{area}/{i}',reference=f['reference'],pointer=f['pointer'],exact_original_value_type_identity=True,independently_inspected=inspected)
  audited.append(row)
  if not inspected:missing.append(row)
for i,c in enumerate(dec['adopted_claims']):
 absent={f['reference']['artifact_id'] for f in (*c['supporting_facts'],*c['additional_support'])}-{f['reference']['artifact_id'] for f in c['scope']}
 if absent:scopes.append(dict(claim=i,missing_source_artifacts=sorted(absent)))
pa=dict(version='coding_agent.material_audit@1.0.0',saved_raw=nodes['principal-coordinated-v2']['provider_response_refs'][-1],expanded_return='principal_last_expanded_return.json',expansion='pass_after_local_catalog_binding_repair',formal_validation='fail',formal_error=read(out/'principal_catalog_local_revalidation.json')['business_error'],source_binding_checks=audited,missing_public_source_inspections=missing,missing_per_source_scope=scopes,material_correctness='fail_for_unqualified_acceptance',defects=[
 dict(location='/dispositions/0/adopted_claims/1/statement',issue="Attributes independent_recomputation='available' and recomputed_result=false to official. The original /official object has neither field."),
 dict(location='/interpretation and /unknowns/2',issue='Leaves whether an archived recomputation happened unresolved. Existing metric-view construction distinguishes a computed failed Boolean from missing result None; no new recomputation was performed in this activity.'),
 dict(location='/dispositions/0/reason',issue="Says the investigator correctly interprets recomputed_result=false as a failed test. The investigator /counterevidence/2/statement instead says no recomputation was performed."),
 ],supported=['Exact historical aggregate timing, integrity, negative recorded reach/holding results and bounded one-step prediction observations','No dominant physical cause or real-robot feasibility is established'],decision_consequence='No accepted public disposition receipt published. Preserve the original model decision and expanded selection without silently revising it.',review_method='Coding agent examined saved exact source values, report prose, original inspection records and existing tools/research_metric_view.py; zero judge-model calls, new analysis computations and backend executions.')
atomic_json(out/'principal_material_audit.json',pa)
atomic_json(out/'repair2_affected_checks.json',dict(provider_requests=0,checks_run=2,passed=True,command='softagent python -m unittest tests.test_research_investigation_closeout.InvestigationCloseoutTests.test_resume_catalog_retains_sent_authority_and_rejects_changed_bindings tests.test_research_investigation_closeout.InvestigationCloseoutTests.test_principal_claim_links_values_identities_scope_and_defer',elapsed_s=27.323,scope='Targeted restoration authority, changed catalog rejection, and existing public principal original-value/identity/scope/disposition checks; full suite not run'))

# Close the otherwise uncharged review/delivery interval conservatively. The
# original activity clock already includes preparation, repairs and pauses.
clock=read(out/'activity_start.json');elapsed=time.time()-clock['started_unix'];prior_used=s.remaining()['used']['wall_s'];remaining_interval=max(0,elapsed-prior_used)
cost={**zero(),'wall_s':remaining_interval};row,fresh=s.reserve(run,'partial-delivery-review',digest(dict(activity=m['activity_id'],complete=False)),'coding-agent-delivery',cost,kind='engineering_delivery')
if fresh:s.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],tool_id='engineering.delivery',tool_version='1.0.0',execution_status='completed',caller='coding-agent-delivery',charged=zero(),cache_hit=False),dict(method='Conservative uncovered activity interval through this delivery snapshot; includes all local review and pauses, without refunding or rewriting prior charges'),elapsed=remaining_interval,actual_cost=cost,kind='engineering_delivery')
export(out,'coordinated',run_id=run);b=read(out/'coordinated_bundle.json');arts=b['artifacts']
attempts=[e for e in b['events'] if e['kind']=='investigation_provider_attempt'];responses=[e for e in b['events'] if e['kind']=='investigation_provider_response' and e['status']=='returned']
assert len(attempts)==18 and len(responses)==17
known=[];totals=Counter();code=Counter()
for e in responses:
 raw=arts[e['outputs'][0]['artifact_id']];usage=raw.get('usage');known.append(dict(request_id=e['request_id'],response=e['outputs'][0],provider_usage=usage))
 if usage:
  for k in ('prompt_tokens','completion_tokens','total_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens'):
   if type(usage.get(k)) is int:totals[k]+=usage[k]
for e in attempts:
 a=arts[e['outputs'][0]['artifact_id']];code[a['code_commit']]+=1
roles=[]
for key in ['reach-holding-interpretation','timing-integrity-limits','coordinator-summary','principal-coordinated-v2']:
 n=b['state']['investigations'].get(key);allocation=p['allocations'][key]
 roles.append(dict(investigation_id=key,status=n['status'] if n else 'not_dispatched',actual_requests=n['usage']['model_calls'] if n else 0,purposes=n.get('requests_by_purpose',{}) if n else dict(ordinary=0,model_correction=0,engineering_recovery=0),purpose_limits=allocation['request_purposes'],new_evidence_operations=n['usage']['tool_calls'] if n else 0,imported_query_results=sum(r.get('inspection_origin')=='imported_query_result_supplied_to_current_model' for r in n.get('reads',[])) if n else 0,report=n.get('result') if n else None,started_unix=n.get('started_unix') if n else None,node_deadline_unix=n['started_unix']+n['order']['timeout_s'] if n else None))
assert sum(r['actual_requests'] for r in roles)==18
assert all(sum(r['purposes'].values())==r['actual_requests'] for r in roles)
assert all(all(r['purposes'].get(k,0)<=v for k,v in r['purpose_limits'].items()) for r in roles)
unknown_reservations=[c['request_id'] for c in b['calls'] if c['status'] in ('running','unknown')]
assert not unknown_reservations
source=m['historical_parent']['order']['evidence'][0];original=read(activity.ROOT/'runs/stage336_manual_20261001_090616/stage336_audit.json')['execution']['factual_result'];assert s.artifact(source)==original
sealed=all(sha(activity.ROOT/path)==value for path,value in read(out/'sealed_history.json').items());assert sealed
gate=dict(version='mainline3.partial_closeout_gate@1.0.0',passed=False,gates=dict(preserved_A='pass',historical_coordinator_plan='pass',two_new_valid_reports='fail',actual_two_report_synthesis='not_executed',formal_principal_dispositions='fail',independent_material_audit='fail',historical_sources_unchanged='pass',actual_request_purpose_bounds='pass',response_content_gate_removal='pass_affected_paths',focused_offline_gate='pass'),missing_gate='Reach/holding exhausted both authorized model corrections and two consecutive corrections without a valid report. Do not use unused ordinary/engineering requests, another role, or a renamed node to bypass this hard limit.',C_automatic_execution='blocked_by_B_gate')
atomic_json(out/'coordinated_gate.json',gate)
facts=dict(activity_id=m['activity_id'],delivered_at=now(),V1_complete=False,A=dict(status='accepted_preserved',paid_new_requests=0,scope='Historical reports with previously accepted new principal dispositions; no broadened claim'),B=dict(status='incomplete',valid_new_reports=1,expected_new_reports=2,timing_report=nodes['timing-integrity-limits']['result'],actual_synthesis=False,completed_public_dispositions=0,material_audit='fail_unqualified_adoption',missing_gate=gate['missing_gate'],principal_attempt='Expanded saved model decision after local program repair; formal inspection and scientific interpretation still fail'),C=dict(status='not_executed_B_gate_failed',provider_requests=0,public_tools=0,mathematical_evaluations=0,backend_executions=0,engineering_validity='not_assessed',physical_acceptance='not_assessed',fixed_changes=m['fixed_changes'],source_and_recipe='Frozen source, candidate.family@1.2.0/controller.gvs_nmpc@9.0.0 and inherited V7 conditions unchanged'),usage=dict(provider_requests=18,ordinary=sum(r['purposes'].get('ordinary',0) for r in roles),model_correction=sum(r['purposes'].get('model_correction',0) for r in roles),engineering_recovery=sum(r['purposes'].get('engineering_recovery',0) for r in roles),by_role=roles,ledger=s.remaining(),complete_original_responses=17,irrecoverably_lost_outputs=1,unknown_current_reservations=unknown_reservations,provider_reported_token_totals=dict(totals),provider_usage_records=known,unknown_usage='The original principal ordinary HTTP200/IncompleteRead call has no complete response, usage or known supplier charge. It remains one ordinary invocation; the engineering replacement is a separate invocation.',monetary_costs=None,monetary_cost_reason='No billing statement/currency data supplied; no price assumptions',conditional_length_probes=0,automatic_provider_retries=0),repairs=m['repairs'],code_portions=dict(code),final_code_identity=m['code_commit'],offline_gate=read(out/'offline_gate.json'),historical_uncertainties=read(out/'historical_uncertainties.json'),history_sealed_and_unchanged=sealed,original_stage336_factual_result_unchanged=True,clock=dict(clock,snapshot_elapsed_s=elapsed,snapshot_ledger_wall_s=s.remaining()['used']['wall_s'],delivery_protection_unchanged=True),V2=dict(status='conditional_handoff_prepared_not_ready_for_scientific_execution',next_scope=['Limited tendon counts and actuator layouts','Segment-count changes','Finite necessary combinations'],topology_implementation_or_experiments_performed=False,remaining_material_defects=['Missing new reach report, two-report synthesis and final dispositions/material audit','Fixed C remains unexecuted','Large full principal correction wire remains a capacity limit; no send-boundary check loosened','Formal source inspection and per-source applicability requirements remain','Meaning of available recomputation and Boolean false must be handled scientifically'] ))
atomic_json(out/'delivery_facts.json',facts)
atomic_json(out/'coordinated_lifecycle.json',dict(status='stopped',active_nodes=[],pending_provider_responses=0,all_existing_nodes_terminal=True,unknown_current_reservations=unknown_reservations,old_activities_still_sealed=True,no_paid_retry_or_quota_reset=True))

base='../evidence/research_mainline3_v1_complete_20261009/'
table='\n'.join(f"| {r['investigation_id']} | {r['purposes'].get('ordinary',0)} | {r['purposes'].get('model_correction',0)} | {r['purposes'].get('engineering_recovery',0)} | {r['actual_requests']} | {r['new_evidence_operations']} |" for r in roles)
text=f'''# Research Mainline 3 V1 partial delivery — 2026-10-09

V1 remains incomplete. Accepted A and the valid historical coordinator plan are preserved. This fresh activity completed one new timing/integrity report; the reach/holding investigator exhausted its two model corrections without a valid report. B therefore fails its two-report gate, and the fixed C case was not executed. V2 remains a conditional handoff.

The [delivery facts]({base}delivery_facts.json), [failed B gate]({base}coordinated_gate.json), [saved public bundle]({base}coordinated_bundle.json) and [ledger]({base}coordinated_ledger.json) distinguish formal validity, scientific support, execution and billing uncertainty.

## Completed work and exact missing gates

The [new timing report]({base}timing_report.json) is formally valid and persisted, with 17 exact source/value/type bindings. Its [material audit]({base}timing_material_audit.json) rejects unqualified adoption: it treats a failed recomputed Boolean as no computation and attributes absent fields to the official-result object. Narrow historical timing/integrity observations remain supported. All numbers refer to historical Stage 3.36, not a new scientific run.

Reach used 7 ordinary requests and 2 genuine model corrections. Its final submission omits the original `/reach/sources` array from a whole-object fact. [Local revalidation]({base}reach_final_local_revalidation.json) confirms the formal mismatch. Unused ordinary or engineering allowances cannot substitute for exhausted correction capacity. No old report was substituted, invalid report silently edited, or new node opened to evade the limit.

With reach unavailable, two-report synthesis was not dispatched. A bounded principal attempt on the completed timing report used one ordinary request (HTTP200 with irrecoverably incomplete body), one explicit engineering replacement and one model correction. The final response was saved. A local restoration defect regenerated the same catalog under another run ID; [repair and replay]({base}principal_catalog_local_revalidation.json) restore the exact sent authority without another provider request. Expansion passes, but original-source inspection and per-source scope remain deficient. The [principal material audit]({base}principal_material_audit.json) also rejects unsupported prose. No accepted public disposition receipt was published and no two-report principal judgment exists.

C's eight public operations, mathematics and backend execution all remain at zero. The frozen near/far routing-radius scales are 1.01/0.99 with `candidate.family@1.2.0`, `controller.gvs_nmpc@9.0.0` and the inherited V7 recipe. Engineering validity and physical acceptance are unassessed. A complete valid physical failure would satisfy C's execution gate, but B must pass first.

## Response handling and focused validation

Removed the actual model-response content gates across transport reception/error bodies, dispatcher interaction and recovery, context snapshot/capacity/storage, report handoff/export, replacement paths and legacy response rewriting. See [path inventory]({base}response_gate_removal.json). Complete original UTF-8 or bytes enter atomic Store persistence before normal parsing and business validation. Serialization, tool permissions, source provenance, identities, quotas, deadlines and scientific acceptance remain enforced. No replacement content-defense framework was added; authentication/configuration handling remains separate.

The [focused offline gate]({base}offline_gate.json) passes after four affected initial failures were diagnosed and rerun, followed by three affected persistence checks. These use production public paths with an offline transport substitute, preserve every rejected tool-call ID and reasoning field, and exercise report delivery, local restoration and purpose accounting. No paid connectivity test, full repository suite, paired historical validation or scientific solve was run. Repair 1 had two affected checks plus a saved-wire capacity check; repair 2 had two affected checks plus local replay. Their limitations remain explicit.

## Actual usage and code identity

| Role | Ordinary | Model correction | Engineering recovery | Total | New evidence operations |
| --- | ---: | ---: | ---: | ---: | ---: |
{table}

New B usage is **18/40 provider requests**, **25/512 public operations**, and **{s.remaining()['used']['wall_s']:.3f}/12000 ledger seconds** at the delivery snapshot. New role evidence operations total 17; six historical query-result pages were imported and supplied with provenance, without charging them as new reads. Seventeen complete original responses were saved. One principal transport output remains irrecoverably incomplete, with unknown usage/charge. Known provider totals are prompt {totals['prompt_tokens']}, completion {totals['completion_tokens']}, total {totals['total_tokens']} tokens. Currency costs are unknown for all calls; no invoice or estimated price is substituted. Historical 14-request usage and all old missing-body/unknown-reservation facts remain sealed.

Actual dispatch code: `c55b7ded9ed3f996ecd414a57785b298eb6e9ac5` for 17 requests; `13c4bdc4367d662fdad438d15525ae369820ee61` for one principal correction. `{m['code_commit']}` is the catalog repair/local-replay revision and sent zero requests. Two of four post-freeze repairs were used. Repair 1 compacted duplicate historical execution metadata while preserving current evidence and native reasoning/history; a later larger correction still exceeded the unchanged input limit. Repair 2 preserved the immutable catalog actually sent during explicit restoration. Neither migration extended authority, reset counts/deadlines or reopened a stopped run. Records and code hashes are in the [manifest]({base}validation_manifest.json).

The ten-hour activity began 2026-10-08 15:55:23 UTC (23:55:23 Shanghai). Its delivery cutoff and deadline remain fixed at 2026-10-09 01:25:23/01:55:23 UTC (09:25:23/09:55:23 Shanghai). Preparation, repairs, pauses and review are conservatively charged. All current nodes are terminal, with no pending response or unresolved new reservation. Old scientific artifacts and activity hashes remain unchanged.

The [V2 handoff](research_mainline3_v2_handoff.md) retains concrete interface locations and the order limited tendon/actuator layouts → segment counts → necessary finite combinations. No V2 topology was implemented or executed. Missing B/C evidence and the remaining report/capacity defects are explicit prerequisites; old missing bodies need not be recovered to work under a future authorization.

## Previous activity report — preserved historical record

The following dated content describes earlier sealed activities. Its response-gate requirements are superseded by this authorization, and its activity status/counters are historical.

'''
old=(out/'previous_research_mainline3_v1_completion.md').read_text(encoding='utf-8')
(activity.ROOT/'docs/research_mainline3_v1_completion.md').write_text(text+old,encoding='utf-8')
v2=(out/'previous_research_mainline3_v2_handoff.md').read_text(encoding='utf-8');boundary=v2.index('\n## ')
prefix=f'''# Research Mainline 3 V2 interface handoff — conditional, 2026-10-09

V2 is prepared as the next separately scoped development goal, but V1 has not passed. A remains accepted; B has one valid new timing report, no valid new reach report, no two-report synthesis or completed final dispositions, and a failed material audit. C was not executed. See the [current V1 delivery](research_mainline3_v1_completion.md) and [facts]({base}delivery_facts.json). Historical missing responses and unresolved reservations remain sealed; their recovery is not a prerequisite for fresh authorized work.

The next development order remains limited tendon counts and actuator layouts, then segment-count changes, then finite necessary combinations. No topology combinations were implemented or validated here. The existing concrete interfaces and comparison requirements below remain the handoff; no architecture or scheduler redesign is proposed.

Changed or exposed gaps: the model-response content gates were removed throughout the affected paths; full original responses now persist before business processing. Request purposes are enforced separately with actual dispatch counts and original role deadlines. Explicit restoration must retain the immutable catalog supplied to the model; the local repair verifies unchanged contents/owners before binding it. Large principal correction histories can still exceed full-input capacity. New reports must correctly distinguish an available failed recomputation from an absent result, and must satisfy original-evidence inspection and per-source applicability requirements. These are material closeout gaps, not evidence of reasoning-token exhaustion.

The [timing report]({base}timing_report.json) and [audits]({base}principal_material_audit.json) preserve useful partial work. Completing the missing new reach report under appropriately scoped authority, then two-report synthesis/dispositions/audit and the fixed C case, remains necessary before declaring V1 closed. No unused ordinary or recovery quota can be transferred to bypass the exhausted reach correction allowance.
'''
# Retain every concrete interface and historical section; only the superseded
# opening status is replaced (the exact old file is already preserved above).
(activity.ROOT/'docs/research_mainline3_v2_handoff.md').write_text(prefix+v2[boundary:],encoding='utf-8')
print(json.dumps(dict(B='incomplete',C='not_executed',provider_requests=18,tokens=dict(totals),ledger=s.remaining(),source_inspection_gaps=len(missing),scope_gaps=scopes,code_portions=dict(code)),ensure_ascii=True))
