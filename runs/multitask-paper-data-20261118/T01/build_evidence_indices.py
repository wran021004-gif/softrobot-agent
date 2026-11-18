"""Read-only evidence extraction for T01-T06,T08,T09. No simulation/optimization."""
import csv,json,pathlib,sqlite3,collections,hashlib
ROOT=pathlib.Path('D:/softrobot-agent')
OUT=ROOT/'runs/multitask-paper-data-20261118'
TASKS={'T01':'Multi-target Reach-and-Hold','T02':'Load-Conditioned Hold','T03':'Fast Target Reaching','T04':'Figure-Eight Trajectory Tracking','T05':'End-Effector Position and Tool-Axis Alignment','T06':'Loaded Time-Indexed Pose Scanning','T08':'Passive Progressive-Stiffness Response','T09':'Guided Spring-Button Contact Manipulation'}
INDEX=list(csv.DictReader((ROOT/'paper_experiments/paper_results_master_20261113/RAW_RESULT_INDEX.csv').open(encoding='utf-8-sig')))
MASTER={r['task_id']:r for r in json.loads((ROOT/'paper_experiments/paper_results_master_20261113/SOURCE_DATA/FULL_TASKS.json').read_text(encoding='utf8'))}

def compact(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def rows(p,rs,fields=None):
 fields=fields or sorted(set().union(*(r.keys() for r in rs)))
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader()
  for r in rs:w.writerow({k:compact(v) if isinstance(v,(list,dict)) else ('unavailable' if v is None else v) for k,v in r.items()})
def db(p):return sqlite3.connect('file:'+str(p).replace('\\','/')+'?mode=ro',uri=True)
def get(c,r):
 if not r:return None
 a=r.get('artifact_id') if isinstance(r,dict) else r
 rr=c.execute('select body from artifacts where id=?',(a,)).fetchone()
 return json.loads(rr[0]) if rr else None
def ref(p,a):return str(p)+'#artifacts/'+(a.get('artifact_id') if isinstance(a,dict) else a)
def trace_entries(paths):
 es=[]
 for p in paths:
  for line,s in enumerate(p.read_text(encoding='utf8').splitlines(),1):
   if s.strip():
    o=json.loads(s);o['_source']=str(p)+':'+str(line);o['_file']=str(p);es.append(o)
 return es
def physical_signature(o):
 d=o.get('configuration',{}).get('robot',{}).get('structure',{}).get('data',{})
 return hashlib.sha256(compact(d).encode()).hexdigest() if d else None
def structure(o):
 d=o.get('configuration',{}).get('robot',{}).get('structure',{}).get('data',{})
 if not d:return {'segments':None,'tendons':None,'actuators':None,'lengths_m':'unavailable','young_pa':'unavailable','cells':'unavailable','component_kind_counts':'unavailable'}
 flex=[a for a in d.get('components',[]) if a.get('kind')=='flexible_segment']
 return {'segments':len(flex),'tendons':len(d.get('tendons',[])),'actuators':len(d.get('actuators',[])),
  'lengths_m':[a.get('length_m') for a in flex],'young_pa':[a.get('physics',{}).get('young_pa') for a in flex],
  'cells':o.get('configuration',{}).get('policy',{}).get('discretization',{}).get('data',{}).get('cells'),
  'component_kind_counts':dict(collections.Counter(a.get('kind') for a in d.get('components',[])))}
def slim_output(o):
 # Original trace outputs are bounded public evidence, not new analysis.
 keep=['status','acceptance','candidate','reference','source_reference','execution_id','task_acceptance','failure_reason','reason','numerical_s','proxy_values','native_dynamics','native_analysis','analysis_applicability','initial_state_qualification','result','error','charged_mathematical_evaluations','maximum_position_error_m','maximum_static_balance_inf_nm','physics_steps','optimizer_success']
 return {k:o[k] for k in keep if k in o} if isinstance(o,dict) else o
def unwrap(o):
 if isinstance(o,dict) and o.get('contract')=='research.registered_result':return o.get('data',{}).get('result',o)
 if isinstance(o,dict) and isinstance(o.get('data'),dict):return o['data']
 return o
def candidate_refs(o):
 refs=[]
 if isinstance(o,dict):
  for k,v in o.items():
   if k in ['candidate','candidate_reference','selected_candidate'] and isinstance(v,dict) and v.get('artifact_id'):refs.append(v['artifact_id'])
   elif k in ['selected_candidates','candidate_references'] and isinstance(v,list):refs.extend(r['artifact_id'] for r in v if isinstance(r,dict) and r.get('artifact_id'))
 return refs

# Curated actual decisions; stages are editorial labels, all language remains quoted source.
SELECTION={
 'T01':[('T01-115-native-central-dense-actuator-search-decision','Diagnosis'),('T01-116-generate-smaller-radius-hypothesis-decision','Refinement'),('T01-123-test-original-minimum-routing-radius-decision','Refinement'),('T01-127-test-upward-reach-margin-geometry-decision','Refinement'),('T01-174-select-all-current-shared-conditions-decision','Final')],
 'T02':[('T02-001-cold-loaded-structure-decision','Initial'),('T02-007-negative-bounded-pattern-check-decision','Diagnosis'),('T02-018-final-bounded-stiffness-comparison-decision','Refinement'),('T02-022-comparison-negative-independent-acceptance-decision','Validation'),('T02-034-joint-select-all-original-load-conditions-decision','Final')],
 'T03':[('T03-001-cold-fast-reach-structure-decision','Initial'),('T03-003-fresh-fast-target-static-construction-decision','Diagnosis'),('T03-005-full-original-fast-reach-native-search-decision','Refinement'),('T03-008-classification-preserving-fast-reach-close-decision','Final')],
 'T04':[('T04-017-execute-full-tracking-decision','Initial'),('T04-210-generate-legal-quasistatic-tracking-decision','Route change'),('T04-211-construct-native-frozen-reference-bank-decision','Investigation'),('T04-216-construct-local-interior-reference-bank-decision','Refinement'),('T04-223-select-exact-qualified-physical-execution-decision','Final')],
 'T05':[('T05-001-cold-directed-tool-axis-structure-decision','Initial'),('T05-003-fresh-position-static-trial-only-decision','Diagnosis'),('T05-004-cold-native-tension-sequence-decision','Route choice'),('T05-005-native-directed-position-and-axis-search-decision','Refinement'),('T05-008-select-actual-position-and-directed-axis-pass-decision','Final')],
 'T06':[('T06-001-cold-loaded-scan-structure-decision','Initial'),('T06-003-cold-timed-scan-control-source-decision','Route choice'),('T06-004-native-full-loaded-timed-axis-search-decision','Refinement'),('T06-007-select-full-original-loaded-scan-pass-decision','Final')],
 'T08':[('T08-002-generate-decision','Initial'),('T08-006-generate-decision','Refinement'),('T08-008-physical-pair-decision','Validation'),('T08-009-independent-confirmation-decision','Confirmation'),('T08-011-classification-preserving-stop-decision','Final')],
 'T09':[('T09-002-stop-at-original-v1-2-hardware-interface-gap-decision','Blocked precursor'),('T09-014-execute-complete-hardware-baseline-decision','Diagnosis'),('T09-210-generate-collision-faithful-hardware-decision','Interface correction'),('T09-213-replay-complete-collision-faithful-task-decision','Validation'),('T09-215-select-full-hardware-solution-decision','Final')]
}
NOTES={
'T01':'共享结构确有变化：历史路线基线 → 14.1 mm → 14 mm 腱路半径，再将两段各加长 2.5 mm；不同目标的控制分别重新优化。早期无独立物理 XML 的数学候选只能引用配置，不能伪造截图。',
'T02':'结构差别主要是两段材料模量 14 MPa → 12 MPa，几何外观不变；适合受载状态/定量结果比较，不能靠颜色或尺寸制造结构演化。三负载工况分别评价。',
'T03':'单一结构；展示 0–0.5 s 的姿态和终端保持，不是结构演化案例。原任务 development draft 分类保留。',
'T04':'研究路线由长期 GVS NMPC 比较改为原生静力平衡参考库和绝对张力前馈。原 GVS 执行未完整完成并在成功后终止，不应写为已完成的性能失败或全局不可行。89 点静态库不构成轨迹验收。',
'T05':'单一结构，必须展示位置与有方向的真实工具轴同时满足；位置静力入口不适用后从零预张力基线进入原生时变张力优化。未发生可见结构改造。',
'T06':'单一结构，保留真实 20 g 工具、偏心 COM 和完整非对角惯量；时间索引位置与工具轴联合约束，与 T05 常值终点任务不同。',
'T08':'被动 P3、0 主动执行器，2 段 2 腱，每段 2 单元。唯一修改为两腱固定放绳偏置 1.5 → 1.8 mm；正负向受载和撤载回弹应分别显示。不能套用主动控制策略。保留 development_not_registered_SELECT，物理通过不升级为注册基准 SELECT。',
'T09':'最初因缺失 20 个实体导向硬件接口而阻塞；后真实导向质量/COM/惯量齐全，首轮暴露原应禁碰的眼孔/辐条被环境重启碰撞。最终接口修复保留原 no-contact 语义，并非人为删去失败碰撞。使用历史实际中点命令作为新 Store 未测输入，未复制历史状态或验收。'
}

for tid,name in TASKS.items():
 dest=OUT/tid;dest.mkdir(parents=True,exist_ok=True)
 for d in ['VISUAL_XML','FIGURES_MJ','FIGURES_PAPER','FIGURE_DATA']:(dest/d).mkdir(exist_ok=True)
 sources=[]
 for group in ['ten_task_codex_solve_20261112','five_task_completion_20261113']:
  for folder in (ROOT/'paper_experiments'/group).glob(tid+'_*'):sources.append(folder)
 stores=sorted(set(p for f in sources for p in f.glob('**/platform.sqlite') if 'HISTORICAL_SOURCES' not in str(p)))
 traces=sorted(set(p for f in sources for p in f.glob('**/STUDY_TRACE.jsonl') if 'HISTORICAL_SOURCES' not in str(p)))
 es=trace_entries(traces); byid=collections.defaultdict(list)
 for e in es:byid[e.get('event_id')].append(e)
 final_rows=[r for r in INDEX if r['task_id']==tid]
 final_execution_ids=set()
 for r in final_rows:
  c=db(r['store']);final_execution_ids.add((r['store'],get(c,json.loads(r['result_reference'])).get('execution_id')));c.close()
 candidates=[];candidate_objects={};results=[];seen_results=set();source_idx=[]
 for sp in stores:
  c=db(sp)
  runids=[x[0] for x in c.execute('select run_id from sessions')]
  source_idx.append({'kind':'original_store','path':str(sp),'run_ids':runids,'role':'primary'})
  # Filter by length before retrieving blobs; no full-array or full-SHA audit.
  for aid,body in c.execute("select id,body from artifacts where length(body)<250000 and cast(substr(body,1,100) as text) like '%\"candidate_id\"%'"):
   try:o=json.loads(body)
   except (ValueError,TypeError):continue
   if not isinstance(o,dict) or 'configuration' not in o:continue
   candidate_objects[(str(sp),aid)]=o
   candidates.append({'task_id':tid,'candidate_id':aid,'internal_candidate_id':o.get('candidate_id'),'store':str(sp),'candidate_reference':ref(sp,aid),'physical_signature_of_recorded_robot':physical_signature(o),'structure':structure(o),'parameters':o.get('parameters'),'configuration_reference':o.get('configuration_reference'),'task_identity':o.get('task_identity'),'profile_identity':o.get('profile_identity'),'initialization_provenance':o.get('initialization_provenance'),'provenance':o.get('provenance'),'has_offline_trajectory':bool(o.get('offline_trajectory')),'materialized_robot_structure':bool(o.get('configuration',{}).get('robot',{}).get('structure',{}).get('data')),'physical_validation':o.get('physical_validation'),'protocol_binding':o.get('protocol_binding')})
  for aid,body in c.execute("select id,body from artifacts where length(body)<500000 and cast(substr(body,1,100) as text) like '%\"acceptance\"%'"):
   try:o=json.loads(body)
   except (ValueError,TypeError):continue
   if not isinstance(o,dict) or not isinstance(o.get('candidate'),dict) or not isinstance(o.get('acceptance'),dict):continue
   if not o.get('execution_id'):continue
   key=(str(sp),o['execution_id'])
   if key in seen_results:continue
   seen_results.add(key);results.append({'store':str(sp),'artifact_id':aid,'result':o})
  c.close()
 # Complete XML index includes initial qualification, failed and superseded sessions.
 xml_index=[{'task_id':tid,'model_xml':str(p),'role':'original_physics_xml','source_root':str(f)} for f in sources for p in f.glob('**/*.xml')]
 rows(dest/'complete_model_index.csv',xml_index)
 rows(dest/'complete_candidate_index.csv',candidates)
 dump(dest/'candidate_configuration_index.json',candidates)
 all_decisions=[]
 for e in es:
  if e.get('kind')=='decision':all_decisions.append({'task_id':tid,'node_id':e.get('event_id'),'actor':e.get('actor'),'run_id':e.get('study_id'),'timestamp':e.get('timestamp'),'decision':e.get('decision_summary'),'original_source':e['_source'],'evidence_refs':e.get('evidence_refs'),'exact_input':e.get('exact_input')})
 rows(dest/'complete_decision_index.csv',all_decisions)
 metrics=[]
 for r in results:
  o=r['result'];a=o['acceptance'];aid=o['candidate'].get('artifact_id');final_cond=[x['condition'] for x in final_rows if x['candidate_id']==aid]
  co=candidate_objects.get((r['store'],aid),{})
  cond=','.join(final_cond) or (co.get('protocol_binding',{}) or {}).get('condition_id','unavailable')
  for k,v in a.get('components',{}).items():
   if k.startswith('evaluator:') and isinstance(v,dict):metrics.append({'task_id':tid,'run_id':o.get('owning_study'),'candidate_id':aid,'execution_id':o.get('execution_id'),'condition':cond,'metric':k[10:],'value':v.get('value'),'unit':v.get('unit'),'limit':v.get('limit'),'passed':v.get('passed'),'accepted':a.get('accepted'),'evaluation_scope':'independent_original_task_replay','task_identity':co.get('task_identity'),'profile_identity':o.get('profile_identity'),'physical_structure_signature':physical_signature(co),'source':ref(r['store'],r['artifact_id'])+'/acceptance/components/'+k,'final_selected_case':(r['store'],o.get('execution_id')) in final_execution_ids})
 rows(dest/'metric_history.csv',metrics)
 final_cases=[]
 for r in final_rows:
  c=db(r['store']);res=get(c,json.loads(r['result_reference']));co=get(c,json.loads(r['candidate_reference']));c.close()
  xmls=json.loads(r['original_xml_files']);execution=res.get('execution_id');replay=pathlib.Path(r['store']).parent/'physical_replay'/execution
  sources_states=[]
  if tid!='T08':
   for fn in ['samples.json','result.json']:
    p=replay/fn
    if p.exists():
     if tid=='T09' and fn=='samples.json':
      sources_states.append({'path':str(p),'pointer':'/','time_field':'time_s','qpos_field':'qpos_rad','qvel_field':'qvel_rad_s','phase':'robot-only overview; 48 coordinates omit button_slide; not a complete scene state','role':'robot_only_overview_do_not_load_as_full_scene'})
     elif tid=='T09':
      sources_states.append({'path':str(p),'pointer':'/task_evidence/arrays','time_field':'time_s','qpos_field':'qpos','qvel_field':'qvel','joint_layout_pointer':'/task_evidence/joint_layout','phase':'full native scene states; 49 coordinates include button_slide at qpos_address48; no reintegration','role':'preferred_full_scene_state'})
     else:sources_states.append({'path':str(p),'pointer':'/samples' if fn=='result.json' else '/','time_field':'time_s','qpos_field':'qpos_rad','qvel_field':'qvel_rad_s','phase':'recorded native physical states; no reintegration'})
  else:
   for p in replay.glob('**/episode_*.csv'):
    sources_states.append({'path':str(p),'format':'csv','time_field':'time_s','qpos_fields':['qpos_'+str(i) for i in range(8)],'qvel_fields':['qvel_'+str(i) for i in range(8)],'phase':'one post-step state per successful historical mj_step','stage_field':'stage','original_model_xml':str(p.parent/'passive.xml')})
  final_cases.append({'task_id':tid,'condition':r['condition'],'run_id':r['run_id'],'candidate_id':r['candidate_id'],'internal_candidate_id':co.get('candidate_id'),'store':r['store'],'candidate_reference':ref(r['store'],json.loads(r['candidate_reference'])),'configuration_reference':ref(r['store'],co['configuration_reference']) if co.get('configuration_reference') else 'unavailable','result_reference':ref(r['store'],json.loads(r['result_reference'])),'raw_reference':ref(r['store'],json.loads(r['raw_reference'])),'execution_id':execution,'original_xml_files':xmls,'recorded_state_sources':sources_states,'structure':structure(co),'parameters':co.get('parameters'),'accepted':res.get('acceptance',{}).get('accepted'),'acceptance_metrics':res.get('acceptance',{}).get('metrics'),'acceptance_components':res.get('acceptance',{}).get('components'),'constraint_margins':res.get('acceptance',{}).get('constraint_margins'),'resource_consumption_this_execution_only':res.get('actual_resource_consumption'),'evaluation_version':res.get('evaluation_version'),'implementation':res.get('implementation'),'task_timing':co.get('configuration',{}).get('task',{}).get('timing'),'initialization_provenance':co.get('initialization_provenance')})
 # Select 3-5 scientific decisions. Exact source records retained separately from editorial labels.
 timeline=[];decisions=[];selected_evidence=[]
 for iteration,(eid,stage) in enumerate(SELECTION[tid],1):
  matches=byid.get(eid,[])
  if not matches:continue
  # Repeated event IDs in different Studies are resolved to the final Study when available.
  e=next((e for e in reversed(matches) if str(pathlib.Path(final_rows[0]['store']).parent.parent) in e['_file']),matches[-1])
  opid=eid.removesuffix('-decision');ops=byid.get(opid,[])
  op=next((v for v in ops if v.get('study_id')==e.get('study_id')),ops[-1] if ops else {})
  args=op.get('exact_input',{}).get('arguments',{});out=unwrap(op.get('output',{}))
  actual_ref=candidate_refs(out)
  if isinstance(out,dict):
   for k in ['candidate','candidate_reference','reference','source_reference','configuration_reference']:
    if isinstance(out.get(k),dict) and out[k].get('artifact_id'):actual_ref.append(out[k]['artifact_id'])
  existing=[x for x in candidates if x['candidate_id'] in actual_ref]
  cand_ids=[x['candidate_id'] for x in existing]
  if not cand_ids:cand_ids=candidate_refs(args)
  if not cand_ids and stage=='Final':cand_ids=list(dict.fromkeys(r['candidate_id'] for r in final_rows))
  geometric_aliases=list(cand_ids)
  sigs={x['physical_signature_of_recorded_robot'] for x in candidates if x['candidate_id'] in cand_ids}
  geometric_aliases += [x['candidate_id'] for x in candidates if x['physical_signature_of_recorded_robot'] in sigs]
  xmls=[m['model_xml'] for m in xml_index if any(cid in m['model_xml'] for cid in cand_ids)]
  # Mapping to physical XML is filled from original replay requests, without generating models.
  for f in sources:
   for reqp in f.glob('**/physical_replay/*/request.json'):
    req=json.loads(reqp.read_text(encoding='utf8'))
    if req.get('candidate',{}).get('artifact_id') in geometric_aliases:xmls += [str(p) for p in reqp.parent.glob('**/*.xml')]
  record={'task_id':tid,'node_id':eid,'iteration':iteration,'stage':stage,'candidate_id':','.join(cand_ids) or e.get('candidate_id') or 'unavailable','candidate_status':op.get('status','unavailable'),'model_xml':list(dict.fromkeys(xmls)),'state_source':'see evidence_bundle.json final_conditions and selected_node_evidence; unavailable where not recorded','physical_hypothesis':args.get('hypothesis'),'observed_problem':'unavailable as separate field; quoted contemporaneous decision retained','structural_change':args.get('generation') or args.get('request') or 'unavailable; see quoted action','controller_change':args.get('method') or args.get('control_source') or 'unavailable; see quoted action','mathematical_evidence':op.get('output_artifact_ids') if op.get('tool_name')=='research.math' else [],'physical_evidence':op.get('output_artifact_ids') if isinstance(out,dict) and out.get('acceptance') is not None else [],'decision_summary':e.get('decision_summary'),'evaluation_status':out.get('task_acceptance') if isinstance(out,dict) else 'unavailable','resulting_metrics':(out.get('acceptance',{}) or {}).get('metrics') if isinstance(out,dict) else None,'run_id':e.get('study_id'),'actor':e.get('actor'),'original_source':e['_source'],'operation_source':op.get('_source')}
  record['operation_status']=op.get('status','unavailable')
  record['operation_failure_reason']=op.get('failure_reason')
  record['observed_problem']=e.get('decision_summary')
  accepted=(out.get('acceptance',{}) or {}).get('accepted') if isinstance(out,dict) else None
  record['candidate_status']='physical_pass' if accepted is True else 'physical_fail' if accepted is False else 'unmeasured_or_not_separately_classified'
  if stage=='Final':
   record['resulting_metrics']={r['condition']:r['acceptance_metrics'] for r in final_cases}
   record['candidate_status']='physical_pass; preserve original development/SELECT classification'
  timeline.append(record)
  decisions.append({'task_id':tid,'node_id':eid,'stage':stage,'actor':e.get('actor'),'run_id':e.get('study_id'),'observation':e.get('decision_summary'),'hypothesis':args.get('hypothesis') or 'unavailable as separately recorded hypothesis','investigation':{'tool':op.get('tool_name'),'request_id':op.get('event_id'),'exact_arguments':args},'evidence':{'output_artifact_ids':op.get('output_artifact_ids'),'evidence_refs':e.get('evidence_refs')},'decision':e.get('decision_summary'),'action':args,'outcome':slim_output(out),'original_source':e['_source'],'operation_source':op.get('_source'),'interpretation_status':'observation preserves full contemporaneous rationale quote because source combines observation/decision; stages are editorial, no invented internal reasoning'})
  selected_evidence.append({'node_id':eid,'decision_trace':e['_source'],'operation_trace':op.get('_source'),'operation_status':op.get('status'),'failure_reason':op.get('failure_reason'),'original_exact_input':op.get('exact_input'),'recorded_output':slim_output(out),'output_artifact_ids':op.get('output_artifact_ids'),'model_xml':list(dict.fromkeys(xmls)),'model_mapping_scope':'Exact candidate artifact or identical recorded robot-structure serialization; environment/state must use the original model-specific saved source.'})
 rows(dest/'candidate_timeline.csv',timeline)
 rows(dest/'agent_decision_timeline.csv',decisions)
 # Small original result snapshots preserve metrics without copying arrays/Store databases.
 dump(dest/'final_acceptance_extracted.json',final_cases)
 cost_refs=[str(p) for f in sources for p in f.glob('**/COST_REPORT.json')]
 condition_refs=[{'task_id':tid,'condition':r['condition'],'run_id':r['run_id'],'source_locator':r} for r in final_rows]
 rows(dest/'complete_condition_index.csv',condition_refs)
 source_idx += [{'kind':'study_trace','path':str(p),'role':'original_recorded_agent_actions'} for p in traces]
 source_idx += [{'kind':'cost_report','path':p,'role':'separate_original_run_cost_not_summed'} for p in cost_refs]
 rows(dest/'source_index.csv',source_idx)
 ext=[]
 for group in ['direct_math_only_20261114','ab_batch1_20261114','ab_batch2_20261114']:
  gp=ROOT/'paper_experiments'/group
  if gp.exists():
   for p in gp.glob(tid+'*'):ext.append({'path':str(p),'role':'separate_method_or_run_reference_only; never combine with FULL outcomes'})
 bundle={'schema_version':'multitask_evidence_bundle_v1','task_id':tid,'task_name':name,'scope':'historical FULL method C; no new solver, optimizer or mj_step','actor_notice':'Codex surrogate / Codex expert formal trace; not a Main SDK experiment unless separate original evidence says so','editorial_note':NOTES[tid],'source_stores':[str(s) for s in stores],'source_traces':[str(p) for p in traces],'final_conditions':final_cases,'selected_node_evidence':selected_evidence,'complete_indices':{'candidates':str(dest/'complete_candidate_index.csv'),'models':str(dest/'complete_model_index.csv'),'decisions':str(dest/'complete_decision_index.csv'),'conditions':str(dest/'complete_condition_index.csv'),'source_index':str(dest/'source_index.csv')},'separate_cost_sources':cost_refs,'additional_experiments_separate_scope':ext,'known_missing':['Explicit contemporaneous observation/hypothesis fields are unavailable where the source only records a combined rationale.','Original XML or full dynamic state unavailable for some purely mathematical candidate trials; no geometry or state is fabricated.'],'render_policy':'Only original XML plus saved qpos/time. Visual models and screenshots are created separately by parent workflow.','provenance_policy':'Existing master CSV/JSON used only to locate Store artifacts; numeric final values extracted directly from original Store acceptance components.'}
 dump(dest/'evidence_bundle.json',bundle)
 lines=[f'# {tid} — {name}','','本目录仅整理历史研究证据，未运行新实验、优化或动力学积分。','',f'实际研究 actor：{", ".join(sorted(set(str(e.get("actor")) for e in es if e.get("actor"))))}。不能将这些 Codex surrogate/expert 运行写成 Main SDK 研究。','',NOTES[tid],'','最终原始验收：','', '| Condition | Run ID | Accepted | Key metrics (SI) |','| --- | --- | --- | --- |']
 for fc in final_cases:lines.append('| '+fc['condition']+' | '+fc['run_id']+' | '+str(fc['accepted'])+' | '+compact(fc['acceptance_metrics'])+' |')
 lines += ['',f'保留 {len(candidates)} 个 Store 候选记录、{len(xml_index)} 个原 XML 引用、{len(all_decisions)} 条原始决策、{len(timeline)} 个代表节点。候选记录含条件/控制变体，不能当作不同实体结构数量。','','`candidate_timeline.csv` 与 `agent_decision_timeline.csv` 的阶段名称是编辑分类；决策语句及 exact_arguments 为原文，缺失的独立假设字段标记 unavailable。`metric_history.csv` 仅列独立物理验收；不同 run_id / task_identity / profile_identity / condition 不应直接连成收敛线。','','`evidence_bundle.json` 记录最终候选、原 Store artifact、原 XML、保存状态与时间字段。其余候选/条件和被否决步骤见 complete_* 索引。资源成本保留各原 COST_REPORT 引用，不跨 Study 简单相加。','','后续视觉素材应优先使用 final_conditions.recorded_state_sources。没有中间原 XML 或状态的候选保留引用，不能制造截图。']
 (dest/'TASK_SUMMARY.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
 print(tid,'candidates',len(candidates),'xmls',len(xml_index),'decisions',len(all_decisions),'metrics',len(metrics),flush=True)
