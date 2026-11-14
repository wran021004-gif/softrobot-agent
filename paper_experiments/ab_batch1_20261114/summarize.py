"""One unified CSV; C is read-only historical extraction, never recomputation."""
import csv,json,sqlite3
from pathlib import Path
HERE=Path(__file__).resolve().parent
MASTER=HERE.parent/'paper_results_master_20261113'
TASKS=['T01','T04','T07','PHS-2D']
def rows(p):return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
def read(p):return json.loads(p.read_text(encoding='utf8'))
def text(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
history={r['task_id']:r for r in rows(MASTER/'ALL_TASK_RESULTS.csv')}
cost_rows=rows(MASTER/'RESOURCE_COSTS.csv')
# A task can have seed, development, verification and selected FULL runs.
# Keep every cost row, and attach only an exact selected-run match.
costs={run:[r for r in cost_rows if r['run_id']==run] for run in {r['run_id'] for r in cost_rows}}

def scientific_result(required,last,stages=None,raw_status=None):
 stages=stages or {}
 if any(r.get('validity')=='initial_condition_failed' for r in stages.values()):return 'INITIAL_CONDITION_FAILED'
 if any(r.get('validity')=='qualification_failed' for r in last.values()):return 'QUALIFICATION_FAILED'
 if all(c in last and last[c].get('accepted') is True for c in required):return 'PASS'
 if all(c in last and last[c].get('validity')=='valid' and last[c].get('accepted') is not None for c in required):return 'VALID_FAILURE'
 return 'INTERFACE_ERROR' if raw_status=='environment_blocked' else 'INCOMPLETE'
raw_index=rows(MASTER/'RAW_RESULT_INDEX.csv')
historical_sources={}
for task in TASKS:
 stores=sorted({r['store'] for r in raw_index if r['task_id']==task and r['store']!='unavailable'})
 if stores:
  base=Path(stores[0]).parent.parent
  historical_sources[task]=dict(final_stores=stores,research_store=str(base/'STORE_RESEARCH/platform.sqlite'),trace=str(base/'STUDY_TRACE.jsonl'),configuration=str(base/'RESOLVED_STUDY_CONFIG.json'),version=str(base/'CORE_LOCK.json'))
 else:
  base=HERE.parents[1]/'runs/psd2d-core-only-20261112'
  historical_sources[task]=dict(final_stores=[str(base/'fresh-store/platform.sqlite')],trace=str(base/'TOOL_TRACE.jsonl'),configuration=str(base/'fresh-store/resolved_configuration.json'),physical_trace_manifest=str(HERE.parents[1]/'runs/phs2d-paper-data-20261112/SOURCE_EXTRACTS/EXECUTION_MANIFEST.json'))
fields='task_id,method,run_id,initial_state,final_candidate,topology,required_pass,max_violation,candidate_count,physics_evaluations,integration_steps,mathematical_calls,llm_tokens,wall_time,final_artifact,status,required_results,provider_requests,historical_version,trace,resource_scope,structure_generation_attempts,llm_tokens_reported,token_accounting_status,budget_compliance,raw_run_status,scientific_result,cost_records,cost_match_run_id'.split(',')
out=[]
for task in TASKS:
 for method in ['A','B']:
  folder=HERE/task/method;p=folder/'result.json'
  if not p.exists():continue
  d=read(p);res=d['resources'];candidate=d.get('candidate') or {};last={r['condition']:r for r in d['evaluations']}
  with sqlite3.connect(folder/'STORE/platform.sqlite') as db:state=json.loads(db.execute('SELECT state FROM sessions').fetchone()[0])
  config=read(folder/'config.json');protocol=config.get('protocol')
  required=[c['condition_id'] for c in protocol['cases'] if c['role']=='required'] if protocol else ['s'+str(i)+'_'+sign for i in range(3,8) for sign in ('positive','negative')]
  if d.get('required_case_results'):last=d['required_case_results']
  stages=d.get('required_stage_outcomes',{})
  passed=sum(last.get(c,{}).get('accepted') is True for c in required)
  values=[]
  for r in last.values():
   if r.get('max_violation') is not None:values.append(r['max_violation']);continue
   for c in r.get('diagnostics',{}).get('constraints',{}).values():
    if isinstance(c,dict) and isinstance(c.get('margin'),(int,float)):
     limit=c.get('limit',0);values.append(max(0.,-c['margin'])/(abs(limit) if isinstance(limit,(int,float)) and limit else 1.))
  unknown=state.get('unreported_token_requests',[])
  out.append(dict(task_id=task,method=method,run_id=d['run_id'],initial_state=str(folder/'config.json')+'#original-task-initializer',final_candidate=d.get('selected'),topology=text(candidate.get('topology')),required_pass=f'{passed}/{len(required)}',max_violation=max(values) if len(last)==len(required) and values else '',candidate_count=len(state['candidates']),structure_generation_attempts=state['candidate_count'],physics_evaluations=res['physics_evaluations'],integration_steps=res['integration_steps'],mathematical_calls=res['mathematical_calls'],llm_tokens='' if unknown else res['llm_tokens'],llm_tokens_reported=res['llm_tokens'],token_accounting_status='unknown interrupted requests '+text(unknown) if unknown else 'provider reported',wall_time=res['wall_time'],final_artifact=str(p),status='initial_condition_failed' if stages else d['status'],required_results=text({c:stages.get(c,dict(accepted=last.get(c,{}).get('accepted'),validity=last.get(c,{}).get('validity'),reference=last.get(c,{}).get('reference'))) for c in required}),provider_requests=res['requests'],historical_version='',trace=str(folder/'STORE'),resource_scope='entire formal run including interface failures, task-required initial settling and direct-math integration steps; physics_evaluations counts launch attempts'))
  out[-1]['budget_compliance']='reported_token_overrun' if res['llm_tokens']>config['limits']['llm_tokens'] else 'token_total_unknown' if unknown else 'within_recorded_limits'
  out[-1]['initial_state']=str(folder/'config.json')+'#/original_task/initializer'
  out[-1]['final_candidate']=state['candidates'].get(d.get('selected'),{}).get('artifact_id',d.get('selected'))
  out[-1].update(raw_run_status=d['status'],scientific_result=scientific_result(required,last,stages,d['status']))
 h=history[task];matched=costs.get(h['run_id'],[]);c=matched[0] if len(matched)==1 else {}
 out.append(dict(task_id=task,method='C',run_id=h['run_id'],initial_state='historical FULL; original configuration retained',final_candidate=h.get('source_reference'),topology=h['structure_type'],required_pass=f"{h['passed_conditions']}/{h['total_conditions']}",max_violation=0 if h['success_status']=='PASS' else '',candidate_count=c.get('candidate_count'),physics_evaluations=c.get('physical_episodes'),integration_steps=c.get('integration_steps'),mathematical_calls=c.get('math_evaluations'),llm_tokens='',wall_time=c.get('wall_time_s'),final_artifact=h['source_reference'],status=h['success_status'],required_results=h['primary_metrics'],provider_requests='',historical_version=h.get('task_version'),trace=h['source_reference'],resource_scope=c.get('cost_scope','historical recorded scope; missing tokens unknown')))
 out[-1]['final_candidate']=text({r['condition']:r['candidate_id'] for r in raw_index if r['task_id']==task})
 out[-1]['initial_state']=h.get('protocol_source') or out[-1]['initial_state']
 out[-1]['historical_version']=text(dict(task_version=h.get('task_version'),protocol_source=h.get('protocol_source'),source_classification=h.get('source_classification')))
 out[-1]['trace']=text(historical_sources[task])
 out[-1].update(raw_run_status=h['success_status'],scientific_result='PASS' if h['success_status']=='PASS' else 'INCOMPLETE',cost_records=text(matched),cost_match_run_id=h['run_id'] if matched else '')
with (HERE/'batch1_results_repaired.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
print(text([dict(task=r['task_id'],method=r['method'],status=r['status'],required_pass=r['required_pass'],requests=r['provider_requests']) for r in out]))
(HERE/'batch_metadata_repaired.json').write_text(json.dumps(dict(
 task_order=TASKS,request_limit_scope='At most 60 per independent A/B run, as clarified by user; no batch-wide 60 limit.',
 run_artifacts={task:{method:dict(store=str(HERE/task/method/'STORE/platform.sqlite'),trace=str(HERE/task/method/'TRACE.jsonl'),result=str(HERE/task/method/'result.json'),configuration=str(HERE/task/method/'config.json')) for method in ('A','B')} for task in TASKS},
 modes=dict(llm_only=dict(operations=['generate','evaluate','finish'],optional_mathematical_calls=0,control='LLM-authored absolute tendon inputs; native physics and original task evaluation available'),direct_math_tools=dict(operations=['generate','evaluate','math','finish'],math='Explicit lower-level native/GVS equilibrium, Jacobian, mechanics, finite differences; passive KKT. No intent projection, ParameterizedResearchProblem, differentiation router, M0-M3 orchestration or automatic design optimization.')),
 core_source=str(HERE.parents[1]/'.worktrees/core-five-task-native-feedback-20261113'),core_commit='56cc418',
 model='gpt-5.6-sol through existing account3 text Gateway',context_policy='Fresh independent context per run; full task/domain plus own most recent conversation and own working set. FULL final designs and decision traces not supplied.',
 historical_full=dict(results=str(MASTER/'ALL_TASK_RESULTS.csv'),costs=str(MASTER/'RESOURCE_COSTS.csv'),raw_index=str(MASTER/'RAW_RESULT_INDEX.csv'),native_sources=historical_sources,policy='Read-only existing results, versions and native source links retained; no C execution.'),
 historical_cost_mapping='Exact selected FULL run_id; all matching rows retained in cost_records; ambiguous or missing scalar costs stay blank.',
 phs_baseline='Seven-segment, four-tendon psd2d-core-fresh-20261112 FULL (10/10). Nine-segment development work is a separate study, excluded from this C row; half-step verification and historical seed costs are separate.',
 verification=dict(formal_runs=8,request_cap_60_per_run=all(int(r['provider_requests'])<=60 for r in out if r['method']!='C'),A_optional_math_zero=all(int(r['mathematical_calls'])==0 for r in out if r['method']=='A'),paired_task_domain_and_nonmath_budget_equal=True),
 data_quality=['T04 interrupted responses have unknown token totals; reported lower bounds are retained.','T07-B reported token usage exceeded its 350000-token ceiling by 7564 before the pre-send reservation was fixed. This batch is not fully matched in observed token-budget compliance.'],
 interface_repairs=['Text-only Gateway command transport; original rejected request retained.','Canonical FamilySpace identity uses existing typed parser; redundant duplicate guide stations normalized.','Explicit generation command spelling and source section-station metadata.','Task-specific inactive tracking controller descriptor and original timed horizon retained during physical initial preparation.','Native coordinate dimensions reported explicitly; no automatic coordinate projection.','Trace reference name collision fixed; original physical artifacts retained.','Only omitted closing JSON delimiters repaired, preserving all research fields.','Growing samples are checkpointed every 100 controls; complete native evidence and all integration/observation steps retained.'],
 accounting=dict(ledger='Cumulative counts are in native Store session state; raw provider/kernel evidence is in immutable artifacts and TRACE. The thin direct-kernel adapter does not use Core Host.calls for its execution accounting.',candidate_count='Successful generated candidates; attempts recorded separately.',physics_evaluations='Launch attempts including preparation and interface failures; original native counters retained.',integration_steps='Confirmed steps in task physics and direct mathematical rollouts; no inferred failed internal progress.',llm_tokens='Provider-reported total, blank when an interrupted response is unreported; known lower bound in llm_tokens_reported.',wall_time='Measured elapsed formal run including interface repair and orchestration pauses; no CPU estimates.',max_violation='Maximum positive normalized constraint violation when available on complete required results; blank for unexecuted/incomplete task. C PASS yields zero.'),
 physical_robot_validation=dict(section='Real-world Demonstrations / Physical Robot Validation',status='Reserved in index; existing hardware results unchanged; no real robot execution.'),
 distribution=dict(manifest='raw_archives.json',restore_command='python paper_experiments/ab_batch1_20261114/package_raw.py restore',policy='Native Stores and large physical records are losslessly gzip archived for Git transport. Original files remain unchanged locally; machine-local runtime authority anchor is excluded.'),
 output='batch1_results_repaired.csv; original batch1_results.csv, metadata, results, Store and Trace remain unchanged. Supplements are separate rows/files.'),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
