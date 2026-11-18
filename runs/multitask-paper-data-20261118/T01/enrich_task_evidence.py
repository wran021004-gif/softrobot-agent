"""Add model-specific replay references and compact original-evidence narratives."""
import csv,json,pathlib,sqlite3,collections
ROOT=pathlib.Path('D:/softrobot-agent');OUT=ROOT/'runs/multitask-paper-data-20261118'
TASKS=['T01','T02','T03','T04','T05','T06','T08','T09']
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
for tid in TASKS:
 d=OUT/tid;b=json.loads((d/'evidence_bundle.json').read_text(encoding='utf8'));manifest=[]
 selected={r['execution_id'] for r in b['final_conditions']}
 for sp in b['source_stores']:
  sr=pathlib.Path(sp).parent
  for reqp in sr.glob('physical_replay/*/request.json'):
   req=json.loads(reqp.read_text(encoding='utf8'));eid=reqp.parent.name;cid=req.get('candidate',{}).get('artifact_id')
   for xml in reqp.parent.glob('**/*.xml'):
    state_files=[]
    for csvp in xml.parent.glob('episode_*.csv'):
     with csvp.open(encoding='utf8') as f:hdr=next(csv.reader(f))
     state_files.append({'path':str(csvp),'format':'csv','time_field':'time_s','qpos_fields':[h for h in hdr if h.startswith('qpos_')],'qvel_fields':[h for h in hdr if h.startswith('qvel_')],'stage_field':'stage'})
    if (xml.parent/'samples.json').exists():
     if tid=='T09':state_files.append({'path':str(xml.parent/'result.json'),'format':'json','pointer':'/task_evidence/arrays','time_field':'time_s','qpos_field':'qpos','qvel_field':'qvel','joint_layout_pointer':'/task_evidence/joint_layout','role':'full49_coordinate_scene_including_button_slide; samples.json is only48 robot coordinates'})
     else:state_files.append({'path':str(xml.parent/'samples.json'),'format':'json','pointer':'/','time_field':'time_s','qpos_field':'qpos_rad','qvel_field':'qvel_rad_s'})
    manifest.append({'task_id':tid,'candidate_id':cid,'store':sp,'execution_id':eid,'original_request':str(reqp),'model_xml':str(xml),'state_sources':state_files,'original_timing':req.get('configuration',{}).get('task',{}).get('timing'),'role':'final_original_confirmation' if eid in selected else 'retained_earlier_physical_execution','evidence_scope':'Historical original physics model and its own saved states. Ablation and numerical-confirmation subdirectories keep their original roles; never relabel them as new design candidates.'})
 b['representative_render_sources']=manifest
 if tid=='T04':
  s=ROOT/'paper_experiments/five_task_completion_20261113/T04_figure_eight_tracking'
  b['route_change_evidence']={
   'original_read_knowledge':str(s/'T04_RUN_03/KNOWLEDGE/expert-t04-method-selection@1.json'),
   'original_bank_result':str(s/'T04_RUN_03/NATIVE_REFERENCE_BANK.json'),
   'original_gvs_execution_result':str(s/'INITIAL_EXECUTION.json'),
   'original_gvs_xml':str(s/'STORE_RESEARCH/sessions/codex-expert-T04-20261113-s1-exec-1951b2d6978f46d2/executions/6c99ff396613431295f31b855f96a20a/backend/robot.xml'),
   'original_gvs_initial_state':str(s/'NATIVE_INITIAL_CONSTRUCTION.json'),
   'original_gvs_termination_record':str(s/'SUPERSEDED_NMPC_TERMINATION_REQUEST.json'),
   'precise_interpretation':'The method-selection Knowledge explicitly records GVS NMPC as still running, with timed SoRoSim/PPO applicability gaps. Try native equilibrium feedforward was a prospective original choice. The superseded GVS run was later terminated after independent feedforward success; its incomplete run cannot supply a full tracking error or a completed failure comparison.'}
 if tid=='T08':b['passive_specific_note']='Fixed payout 1.5 and 1.8 mm; no controller, no active actuators. Compare native states at matched loading stages using the respective baseline XML. Paired ablation removes selected passive limits only as the original task-required mechanism check. It is not an additional morphology search.'
 if tid=='T09':b['contact_specific_note']='First retained 20-guide replay dcb0... failed with 9 unexpected contact pairs and 0 s valid hold. Final 450a... preserves explicit source no-contact guide semantics after an interface repair and passes with 0 unexpected collisions and 0.5 s continuous valid hold. Historical midpoint inputs are a control seed; no original physics state or acceptance was imported.'
 dump(d/'evidence_bundle.json',b)
 with (d/'recorded_replay_model_index.csv').open('w',encoding='utf-8-sig',newline='') as f:
  fields=['task_id','candidate_id','store','execution_id','original_request','model_xml','state_sources','original_timing','role','evidence_scope'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in manifest:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})
 # Deduplicate copied legacy trace records without deleting alternate evidence references.
 p=d/'complete_decision_index.csv';rr=list(csv.DictReader(p.open(encoding='utf-8-sig')));unique={}
 for r in rr:
  key=(r['run_id'],r['node_id'],r['decision'],r['exact_input'])
  if key in unique:unique[key]['alternate_original_sources'].append(r['original_source'])
  else:r['alternate_original_sources']=[];unique[key]=r
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(next(iter(unique.values())).keys()));w.writeheader()
  for r in unique.values():r['alternate_original_sources']=json.dumps(r['alternate_original_sources'],ensure_ascii=False);w.writerow(r)
 # Keep the summary count honest about copied source rows.
 txt=(d/'TASK_SUMMARY.md').read_text(encoding='utf8')
 txt=txt.replace(f'{len(rr)} 条原始决策',f'{len(unique)} 条去重原始决策（原始来源行 {len(rr)}，重复副本保留为 alternate_original_sources）')
 (d/'TASK_SUMMARY.md').write_text(txt,encoding='utf8')
 print(tid,'replay model/state records',len(manifest),'unique decisions',len(unique))

# Narrative references are to original records; no retrospective hypothesis is attributed to the actor.
extras={
'T04':'''\n研究路线证据要点：\n\n1. 原已读 `T04_RUN_03/KNOWLEDGE/expert-t04-method-selection@1.json` 明确区分：历史成功使用准静态张力前馈；当前 GVS 2200 更新比较仍在运行；SoRoSim 仅支持 reach，PPO 不支持本任务定时/外力语义。其当时决策为先尝试原生平衡延续，不能写为 Agent 从已完成 NMPC 失败中推断全局不可行。\n2. `T04_RUN_03/NATIVE_REFERENCE_BANK.json` 原始输出：89 次数学评价，零积分步；最大静力残差 5.075230166684541e-12 Nm，最大静态位置误差 0.0006110494311492155 m。`optimizer_success=false`、250 迭代上限必须保留；这些静态点本身不是轨迹通过证明。\n3. 初次全 4 N 初始化导致不允许的优化器试点、未产生 bank（原 Trace T04-211）；随后改为从此前计算的时间零平衡出发、0.2 N 预载移至 0.21 N 内部并重建 bank（T04-216）。\n4. 原 `BANK_FEEDFORWARD_REPLAY.json` / 原 Store f9d19d...：独立完整 22 s 验收后才通过，RMSE 0.687852845 mm、最大误差 1.020663903 mm、周期漂移 1.008878252 mm，两周期各两叶、无接触/警告与行程/速度均通过。\n5. 原 `INITIAL_EXECUTION.json` 的 GVS 比较是 execution_incomplete/worker exit；`SUPERSEDED_NMPC_TERMINATION_REQUEST.json` 明确在前馈方案被选择后终止旧比较，并不给予其完整科学验收信用。\n''',
'T08':'''\n被动机制证据要点：\n\n- 原候选 e87a0bff...（1.5 mm 放绳偏置），执行 e3b1c46...：正/负向刚度比分别 1.3668366483436758 / 1.3668366483437635，低于固定下界 1.5，其余多数位移界满足；不能仅展示最终通过。\n- 原 Trace T08-006 根据该测量只把两腱偏置增至 1.8 mm，固定几何/材料/离散/载荷。新候选 a0438dc... 在执行 264bc9... 的刚度比分别 1.6314547492588845 / 1.631454749259155；最终 d8b294... 完成源任务要求的独立基线、配对去限位机制对照、半步长及初始扰动。\n- 最终最大高载位移 22.508490354 mm、撤载残留约 0.000685896 mm（0.685896 微米）；这是被动 P3 的数值，不能借用 PHS-2D 的 Tip 或传递比指标。\n- `recorded_replay_model_index.csv` 将每个 baseline / ablation / half_timestep / initial_perturbation 的 XML 严格绑定到同文件夹 episode CSV。状态列 qpos_0...7，时间列 time_s，阶段列 stage；无需新积分。\n- 主体和腱路几何形状无大幅变更，放绳长差异应通过相同受载阶段下的真实变形/松紧状态与刚度定量图表达。\n''',
'T09':'''\n接触与硬件证据要点：\n\n- 2026-11-12 前驱原 Trace 因源 v1.2 要求 20 个实体导向眼孔/辐条组件而接口无法表达，明确停止，数学/物理均未启动；该阻塞不是软臂控制或结构的物理失败。\n- 后续完整硬件首轮执行 dcb0b53... 的原验收给出 9 个 unexpected collision 对、有效力/深度保持 0 s。原 Trace T09-210 记录环境装配错误重新启用了源定义禁碰的眼孔/辐条碰撞，接口修复恢复原语义，保持全部 20 组件的真实质量、COM 与惯量。\n- 最终执行 450ac79... 在全 v1.2 任务中保持有效深度/力连续 0.4999999999999559 s（要求 ≥0.4 s），最大保持深度误差 0.05275270018 mm，最大接触力误差 0.002465057425 N，unexpected collisions=0；1.8/2.0 s 释放位置、力和速度均通过。\n- 该案例适合真实接触前—按压—保持—释放姿态序列；不要将接口修复伪写成研究者减少真实硬件或删除源任务接触约束。\n'''}
for tid,txt in extras.items():
 p=OUT/tid/'TASK_SUMMARY.md';p.write_text(p.read_text(encoding='utf8')+txt,encoding='utf8')
