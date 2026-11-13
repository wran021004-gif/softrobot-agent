"""Assemble an evidence-first paper data package; no new chart generation."""
from pathlib import Path
import csv,json,shutil
O=Path(__file__).resolve().parent;ROOT=O.parents[1];PHS=ROOT/'runs/phs2d-paper-data-20261112'
def rd(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def cr(p):return list(csv.DictReader(Path(p).open(encoding='utf-8-sig')))
def sv(name,text):(O/name).write_text(text.strip()+'\n',encoding='utf-8')
def link(p,label=None):return f'[{label or Path(p).name}](<{Path(p).as_posix()}>)'
tasks=rd(O/'SOURCE_DATA/FULL_TASKS.json');cases=rd(O/'SOURCE_DATA/FULL_CASES.json');nodes=cr(O/'KEY_RESEARCH_NODES.csv');components=cr(O/'HARNESS_COMPONENT_EVIDENCE.csv')
brief={
'T01':'3个目标，同结构3/3通过；最大保持位置误差9.9059 mm',
'T02':'三受力工况3/3；最大保持误差9.8971 mm',
'T03':'0.5 s快速到达；终端误差2.1099 mm，保持最大2.6627 mm',
'T04':'完整22 s双周期；RMSE0.68785 mm，最大1.02066 mm',
'T05':'位置7.4585 mm；有向工具轴0.0518235 rad',
'T06':'20 g时序扫描；位置11.8198 mm；有向轴0.110448 rad',
'T07':'同一四腱结构M1_A/M1_B/M1_C/M5全部通过',
'T08':'双方向刚度比1.63145；低载7.9281 mm，高载22.5085 mm',
'T09':'深度/力联合保持0.5 s；误差0.052753 mm、0.0024651 N',
'T10':'同配方required3/3，control0/2；最终最大保持误差4.1314 mm',
'PHS-2D':'十工况及半步长通过；point最小14.7981 mm，Tip最大4.3470 mm，ratio最大0.153751'}

# Reuse the existing PHS extraction without bringing a duplicate result into the master table.
d=O/'SOURCE_DATA/PHS2D';d.mkdir(exist_ok=True)
for name in ['F8_RIGID_COMPONENTS.json','F8_SEGMENTS.csv','F8_TENDON_ROUTES.json','HALFSTEP_TEN_CASE_RESULTS.csv','LOCAL_DIAGNOSTICS.json']:
    shutil.copyfile(PHS/'FIGURE_DATA'/name,d/name)
half=cr(d/'HALFSTEP_TEN_CASE_RESULTS.csv')
for r in half:r['experiment']='Full_half_timestep'
with (d/'HALFSTEP_TEN_CASE_RESULTS.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,list(half[0]));w.writeheader();w.writerows(half)
fm=rd(PHS/'FINAL_METRICS.json');(d/'FINAL_METRICS.json').write_text(json.dumps(dict(nominal=fm['codex_nominal'],half_timestep=fm['codex_halfstep'],structure=fm['structure'],source_reference=str(PHS/'FINAL_METRICS.json')),ensure_ascii=False,indent=2),encoding='utf-8')
nom=cr(PHS/'TEN_CASE_RESULTS.csv')
for r in nom:r['experiment']='Full_nominal'
with (d/'TEN_CASE_RESULTS.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,list(nom[0]));w.writeheader();w.writerows(nom)

intro='''# Full Study 论文数据整理

本目录统一整理T01–T10与PHS-2D的已有Full Study结果。任务表共11项；逐工况表共32条，其中30条required全部通过，T10两条frozen control均未通过完整验收，另列而不计入required成功数。这是已完成案例的结果快照，不是多随机种子成功率或组件因果收益。

本轮只读取原始Store、候选、Trace与既有物理轨迹，执行数据整理及MuJoCo可视化。未进行结构搜索、数学重算、新物理积分、Main Replay或消融实验。数据统计图暂缓定稿，已生成的统计图仅为草稿；结构截图与任务动画保留为展示材料。

## 数据入口

| 文件 | 用途 |
|---|---|
| ALL_TASK_RESULTS.csv | 11项任务最终结果、正式控制方法、协议分类、run_id与来源 |
| TASK_CASE_RESULTS.csv | 32条逐工况原指标、阈值、结构/控制器身份及验收 |
| KEY_RESEARCH_NODES.csv | 32个关键节点，其中PHS-2D保留11节点 |
| CANDIDATE_EVOLUTION.csv | 原始结构版本、完整结构参数、相邻保存版本的逐字段差异；不虚构父子关系 |
| SOURCE_DATA/PHS_CANDIDATE_INDEX.csv | PHS九个候选的原始候选与模型入口 |
| FIGURE_DATA/PHS_CANDIDATE_PROGRESS.csv | PHS局部、有限载荷、六工况、十工况和半步长，保留评价范围 |
| HARNESS_COMPONENT_EVIDENCE.csv | 11类组件的实际事件、证据强度及合适对照 |
| RESOURCE_COSTS.csv | 23条独立研究运行/复核记录；口径分列，不累加重复来源 |
| SOURCE_DATA/FULL_TASKS.json、FULL_CASES.json | CSV内嵌JSON字段的便捷结构化版本 |
| SOURCE_DATA/MODEL_BINDINGS.json | 原始Store、候选/结果引用、物理XML与执行身份 |
| SOURCE_DATA/TASK_TIME_SERIES/ | 已提取的原始逐步数组、环境状态和关节布局 |
| FIGURE_DATA/*_SAMPLES.json、*_SIGNALS.json | 已保存运动、张力、材料点等信号，直接供后续绘图 |
| SOURCE_DATA/MOTION_INDEX.json | 任务动画所用的已有运动数据和原始来源 |
| RESEARCH_PROCESS.md | 结构变化与决策变化的可读研究过程索引 |
| DATA_DICTIONARY.md | 单位、评价范围、约束、成本及缺失值的用法 |
| ABLATION_DESIGN.md | 少量匹配对照的建议；本轮未执行 |

## 最终结果

'''
intro+='\n'.join('- **'+t['task_id']+' '+t['task_name']+'**：'+brief[t['task_id']]+'。' for t in tasks)
intro+='''

T04最终路线是原生平衡点组构造与周期张力前馈。T10最终路线是原生状态反馈（静力参考、完整切线、离散LQR、有界张力分配），三required和两control使用共同配方。不要将这两个最终结果写成在线NMPC成功。T08保留`task.passive_response / development_valid`和`development_not_registered_SELECT`原分类；T03等任务的原始开发状态也保留在任务表。

PHS-2D F8为7×40 mm柔性段、4根被动腱、6个真实导向板、112自由度、0主动执行器；前3段5 MPa，后4段10 MPa，四根固定放绳均为0.3646169904675268 m。材料商品/配方名称 unavailable。名义十工况352,000积分步；半步长704,000步。Tip指标是原评分末窗中的投影位移，不是整段8 s轨迹的最大瞬态。

## 可展示的研究内容

32节点覆盖机制假设、失败诊断、结构与控制初值修改、方法切换和完整验收。PHS的局部耦合改善未解决有限载荷停稳，随后发现腱路穿实体，转为七段/实体导向并分段调刚度；T07否定较长结构后返回最佳根段并缩路由；T04从全4 N失败转局部平衡/内点续接；T10共同控制器默认值不一致曾阻止组验收。它们是Agent物理推理与调整路线的直接过程证据，不能全归为工具目录的作用。

Task Protocol、Physical Backend/Evaluator、Store/Trace、实际Knowledge/Skill读取及具体后续决策具有直接事件证据。组件独立效率收益尚无匹配消融；Replay材料存在不等于本轮完成端到端复现实验。

## 展示与当前边界

结构和动画均使用MuJoCo原生渲染。保留真实mesh、腱路、负载、孔环/支杆与任务对象；底座、端部锚点板和段间护套仅为附着在真实坐标上的零质量/无碰撞示意外观。T09同段内的星形导向孔环与径向支杆属于原始物理模型，共20组，并非新增装饰。未有制造依据的外观不作为实体硬件声明。

仍缺少：重复试验的成功率/方差、已执行的C1/C2/C3匹配对照、部分研究运行完整CPU/墙钟/失败内部步数，以及没有明确记录的内部求解调用。均标记unavailable或部分覆盖，不推算为零。已有P3历史对照存在协议/适配差异，只支持过程解释；如需数学工具独立收益，建议条件性补充Full-Matched。

图表最终排版和统计图美化留待论文写作阶段。已有数据图不作为出版定稿。完整来源见EVIDENCE_INDEX.md。
'''
sv('PAPER_SUMMARY.md',intro)

sv('DATA_DICTIONARY.md','''# 数据字典与取数规则

## 基本格式

CSV为UTF-8 BOM；数值用SI单位，列名后缀明确m、s、N、rad等。结构化对象以JSON字段保存；建议优先读取`SOURCE_DATA/FULL_CASES.json`以免手工解析单元格。空白缺失字段统一为`unavailable`；未执行、不适用、未暴露不能写成0。布尔passed保留原值。TASK_CASE_RESULTS中的source_reference指向Store artifact或原始评价器记录。

## 任务、结构与工况

`system=Full`；一项任务一行。`required_conditions`与`control_conditions`分列；T10两frozen工况不进入required分母。`candidate_id`是原候选身份，不能把不同候选的最佳工况拼为一个通过结构。T07必须同硬件，T10必须同共同控制器配方。task_version/source_classification保留原分类。

`CANDIDATE_EVOLUTION.csv`每行是某run内唯一物理结构，候选artifact别名全部保留。排序仅依据该Store首次保存顺序，不推定跨run时间或父子关系；`exact_changes_vs_previous_stored_structure`是描述性字段差异，不是因果对照。完整candidate保存在SOURCE_DATA/CANDIDATES；确切研究意图、先前证据与决策见KEY_RESEARCH_NODES和SELECTED_RESEARCH_EVENTS。

## 性能语义

每项task metrics必须同时携带工况、时间窗、采样/聚合方式及原阈值。ALL_TASK_RESULTS中的primary_metrics是原结果字段，不是跨任务统一分数。带单位的同义字段保留原名以便查证。约束上界/下界方向来自原constraint_thresholds和原task定义；不要从正负号猜方向。

T01/T02/T03/T07保持窗或终端误差不是同一指标；T04完整3D RMSE/最大误差不能由y–z图替代。T05/T06有向轴误差单位rad，不能当作位置误差。T09深度、接触力、按钮位移和保持时长含义不同。T10完整验收是密集步检查，10 ms信号曲线只供展示。

PHS-2D：point_x_abs_m为原受力材料点x位移幅值；tip_projected_m为Tip投影位移；评分末窗[7.99,8.0] s，阈值分别≥10 mm、≤5 mm，ratio≤0.30。max_plane_y_m≤2 mm。尾窗是无载[3.75,4]及加载[7.75,8]，漂移≤0.5 mm，Tip/监测点速度≤0.001 m/s，关节速度≤0.01 rad/s，静力残差≤1e-5 N m。几何为被检查保存姿态合法，不是连续时间碰撞证明。半步长独立标识。PHS候选进展的evaluation_kind、scope、case_count不可丢弃；局部QP、2/6/10工况不能直接连成“收敛曲线”。

P3/T08：材料点s=.7，不是Tip；双方向、20 s分段载荷与恢复；低载≥6 mm，高载≤25 mm，残余≤2 mm，刚度比≥1.5，成对机制与其它资格各自检查。当前两段二腱最终任务与历史四腱消融分开。

## 时间序列与动画

`*_SAMPLES.json`为原始存储采样点，并非所有积分步；`*_SIGNALS.json`按spec记录实体、单位、时间与值。SOURCE_DATA/TASK_TIME_SERIES是可用的原始逐步数组，T09包括按钮实际环境关节，不能仅用机器人qpos重放一个不动的按钮。PHS完整CSV较大，保留原始绝对路径和执行manifest，不复制数GB文件。MOTION_INDEX及ANIMATION_INPUTS仅为已有轨迹的抽样视图，不包含新物理解。

动画只将已有qpos写入对应真实关节并做正向位置更新；不积分、不插值优化、不重算任务指标。目标/路径/力箭头来自原task、原参考或实际记录，为视觉提示，不添加物理载荷。慢放或抽样需看动画manifest和屏幕时间；不能按GIF播放时长估算物理速度。

## 资源口径

RESOURCE_COSTS按run_id分列。五项完成任务的Full系列包含其失败/准备studies；另五项使用归档最终研究，避免叠加旧批次重复研究。PHS主搜索+名义、半步长和诊断分支分别记录。

`math_evaluations`是数学评价计费；`math_internal_optimizer_calls`为已保存local_solver调用记录数，旧`math_internal_optimizations`来自对应原成本报告的内部优化调用；两者不能再次相加。`math_objective_evaluations`是内部目标/rollout评价数，不是优化调用数；`math_optimizer_iterations`与`local_optimizer_iterations`分别保留原层级，不能混用。平衡组明确89次构造优化另见原NATIVE_REFERENCE_BANK文件；失败构造不具备完整内部调用总数，不能用收费数推算实际求解数。

`physical_episodes`为原记录的独立物理/注册控制器启动回合，含失败启动；不等于数学内部rollout数。`physical_steps`和`math_internal_physics_steps`不同；integration_steps在可覆盖时为两者的已记录总和。若某失败Profile没有步数，总计unavailable；部分已知总和不能当作完整总数。

`candidate_count`为同run唯一物理robot.structure；artifact数量另列，控制/协议变体不等于新结构。跨run简单相加会重复同硬件。tool_calls有Core ledger units与top-level public operations两种basis，不直接跨口径合计。cpu_time_s可能仅为监控到的worker寿命，coverage列必须保留。wall_time_s有elapsed和PHS charged wall两种口径；charged_numerical_wall_s是嵌套数值时间，不能与elapsed相加。未闭合study历时unavailable。

## 后续绘图建议

先按task_id、candidate/controller身份、condition_role、protocol版本和评价范围分组，再选指标。原值、单位、上下界、原证据列一起导出。任何归一化裕量写明公式及方向。跨任务只比较可解释的资源或能力覆盖，不平均不同单位的任务误差。暂存统计图只供草稿核对，后续论文图应重新设计。
''')

process=['# 结构与决策变化索引','', '原始逐字段结构差异见CANDIDATE_EVOLUTION.csv；PHS原始九候选及模型见SOURCE_DATA/PHS_CANDIDATE_INDEX.csv。下表仅保留真正改变研究方向或确定可行性的节点。Hypothesis列为原rationale的编辑性概括，作用解释不等于已完成因果实验。','']
for t in tasks:
    process+=['## '+t['task_id']+' '+t['task_name'],'','最终：'+brief[t['task_id']]+'。','','| 节点 / 候选 | 观察及假设 | 决策与后果 |','|---|---|---|']
    for n in nodes:
        if n['task_id']!=t['task_id']:continue
        cand=n['candidate_id']
        if len(cand)>35:cand='原始ID见CSV'
        process.append('| '+n['stage_id']+' / '+cand+' | '+n['observation'].replace('|','/')+' '+n['hypothesis'].replace('|','/')+' | '+n['decision'].replace('|','/')+' '+n['measured_result'].replace('|','/')+' |')
    process+=['','证据：KEY_RESEARCH_NODES.csv中的evidence_reference，以及SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json中的决策和相邻原始正式请求。','']
sv('RESEARCH_PROCESS.md','\n'.join(process))

table=['# 论文结果表草稿（数值已整理，排版待定）','','## Table I：全部Full案例','','| 任务 | 原任务分类 | 结构：柔性段/腱 | required通过 | 最终结果摘要 |','|---|---|---|---|---|']
for t in tasks:
    s=t['structure_type'];table.append(f"| {t['task_id']} {t['task_name']} | {t['task_category']} | {s.get('flexible_segments','unavailable')} / {s.get('tendons','unavailable')} | {t['passed_conditions']}/{t['total_conditions']} | {brief[t['task_id']]} |")
table+=['','以上是最终结果快照，不是重复试验成功率。T10 controls单列：positive_y_frozen、negative_y_frozen均FAIL。原source_classification见ALL_TASK_RESULTS；不要将开发任务提升为已注册基准。','','## Table II：代表性物理量与原阈值','','| 任务 / 工况 | 指标 | 观测值 | 原阈值 | 单位 |','|---|---|---|---|---|']
selected={'T02':['holding_position','holding_speed'],'T04':['tracking_rmse','tracking_max','cycle_drift'],'T05':['tool_position','tool_axis_direction'],'T06':['tracking_max_error','tool_axis_direction'],'T08':['low_minimum','high_maximum','stiffness_ratio','residual_maximum'],'T09':['depth_and_force_hold_0p4s'],'T10':['final_hold_position','final_hold_speed'],'PHS-2D':['point_x_abs_m','tip_projected_m','ratio']}
for c in cases:
    for k in selected.get(c['task_id'],[]):
        if k not in c['metrics']:continue
        th=c['constraint_thresholds'].get(k,{})
        table.append(f"| {c['task_id']} / {c['condition_name']} ({c['condition_role']}) | {k} | {c['metrics'][k]:.10g} | {json.dumps(th,ensure_ascii=False)} | {th.get('unit','m' if k.endswith('_m') else '1')} |")
table+=['','完整逐工况结果及所有限制见TASK_CASE_RESULTS.csv。PHS额外保留加载/无载尾窗、残差、腱路几何、约束超长及半步长，见SOURCE_DATA/PHS2D。','','## Table III：组件证据与最小对照','','| 组件 | 直接证据所支持的作用 | 对照/边界 |','|---|---|---|']
for r in components:table.append('| '+r['component']+' | '+r['actual_role']+' | '+r['recommended_ablation']+' |')
sv('TABLE_DRAFTS.md','\n'.join(table))

sv('FIGURE_PLAN.md','''# 后续论文绘图计划

当前优先交付原始结果、结构与任务动画；暂不新增或精修数据统计图。FIGURES已有文件均为草稿，不作为出版定稿，不进行多面板拼接。

建议保留六个主图组的组织：1任务能力覆盖；2代表性真实结构；3PHS F0/F3/F8结构演化；4观察—假设—数学—修改—物理反馈；5任务性能；6资源成本。每个结构视角、动画、数据图均独立文件，最终排版在写论文时决定。结构组和演化组可以共用同一独立图片，不重复制造图。

优先取数：逐工况TASK_CASE_RESULTS；结构版本CANDIDATE_EVOLUTION与PHS候选进展；关键过程KEY_RESEARCH_NODES、RESEARCH_PROCESS；完整时间序列SOURCE_DATA/TASK_TIME_SERIES和FIGURE_DATA原始signals；资源RESOURCE_COSTS。各图保留原协议/工况/评价范围，不把不同范围连成收敛曲线。

配色沿用[ColorBrewer BuGn 3](https://colorbrewer2.org/#type=sequential&scheme=BuGn&n=3)：#E5F5F9、#99D8C9、#2CA25F，搭配深灰、浅灰和白色，并用标记/线型区分。最终统计图布局和字体后续统一设计。

结构与任务动画必须继续采用MuJoCo原生渲染。原负载形状和连接来自物理XML，底座及段间外观仅为零质量示意；目标、参考路径和真实受力箭头采用MuJoCo原生场景元素，不后期绘制机器人。相机、轨迹、帧时间及源XML保存在各manifest。
''')

capt=['# 图注草稿与展示来源','','## 结构截图','', '所有结构图由MuJoCo Renderer直接生成独立PNG。主体mesh、原导向孔/支杆、真实tendon和负载保留；新增底座、端部锚点板及连接护套为零质量、无碰撞的示意外观。形状未提供制造证据时不宣称为真实硬件。PHS早期候选的已记录穿越/松弛缺陷仍见KEY_RESEARCH_NODES，不因外观完整而宣称任务可行。','']
for s in rd(O/'FIGURES_MUJOCO/SCREENSHOT_SOURCES.json'):
    capt.append('- '+Path(s['png']).name+'：'+s['task_id']+'，'+s['label']+'，'+s['view']+'；'+s['pose_source']+'。相机、原模型与视觉XML见SCREENSHOT_SOURCES.json。')
capt+=['','## 任务动画','','由已保存关节姿态及环境状态逐帧更新，在带同款底座、连接、负载和导向件的模型中用MuJoCo原生渲染；无新积分。目标球、参考路径、工具轴和力箭头是依据原任务/记录的视觉提示，不是新增物理结构。T09按钮使用已保存button_slide位移；原始无放大变形。播放时长不等于物理时间，见屏幕时间及ANIMATION_MANIFEST。','','## 暂存数据图（未定稿）','']
for f in rd(O/'FIGURE_DATA/FIGURE_MANIFEST.json'):capt.append('- '+f['name']+'：'+f['caption'])
sv('FIGURE_CAPTIONS.md','\n'.join(capt))

ev=['# 证据入口','','所有最终结果按Full组织；原始run_id与路径仅用于追溯。同一已保存结果不重复累计成本。','','## 最终任务','','| 任务 | run_id | 原协议 | 最终原结果入口 |','|---|---|---|---|']
for t in tasks:ev.append('| '+t['task_id']+' | '+str(t['run_id'])+' | '+json.dumps(t['protocol_source'],ensure_ascii=False)+' | '+json.dumps(t['source_reference'],ensure_ascii=False)+' |')
ev+=['','## 结构和研究过程','','- SOURCE_DATA/MODEL_BINDINGS.json：候选/结果/后端artifact与物理XML。','- CANDIDATE_EVOLUTION.csv：28条run内物理结构版本、候选别名及保存版本差异；SOURCE_DATA/CANDIDATES内保存原候选。','- SOURCE_DATA/PHS_CANDIDATE_INDEX.csv：PHS九候选与原模型。','- SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json：所选关键决策及其相邻原始请求/反馈。','- SOURCE_DATA/DECISION_CATALOG.json：用于关键节点筛选的原始决策索引。','- SOURCE_DATA/KNOWLEDGE_READS.json：实际读取的版本；不以读取数量推断收益。','- SOURCE_DATA/PHS2D：完整F8分段、刚体、腱路、十工况和半步长数据。','','## 时间序列与展示','','- FIGURE_DATA/*_SAMPLES.json及*_SIGNALS.json：从原Store提取的轨迹信号。','- SOURCE_DATA/TASK_TIME_SERIES：可用原始逐步数组、关节布局和环境状态。','- SOURCE_DATA/MOTION_INDEX.json：各动画取数来源。','- FIGURES_MUJOCO/SCREENSHOT_SOURCES.json：每张截图的原XML、视觉XML、相机和姿态。','- VISUAL_XML/PHYSICS_EQUIVALENCE.json：必要的编译与物理属性一致性结果。','- ANIMATIONS_MUJOCO/ANIMATION_MANIFEST.json：逐动画状态、帧源、相机、编码与任务提示。','','PHS完整逐积分步CSV保留在原研究目录，源索引：'+str(PHS/'SOURCE_EXTRACTS/EXECUTION_MANIFEST.json')+'。这批文件较大，保留源引用供后续精确取数，未再复制数GB轨迹。','','## 成本及历史消融','','- RESOURCE_COSTS.csv、SOURCE_DATA/RESOURCE_DETAILS.json：分run统计与内部实际记录。','- '+str(O.parent/'five_task_completion_20261113/CPU_COST_REPORT.json')+'：CPU覆盖范围。','- '+str(O.parent/'ablation/P3_full_vs_no_math_retrospective.md')+'：已有P3对照及证据导航。','- '+str(ROOT/'paper_experiment_data/case_study_extracts/p3_trace_extract.json')+'：历史P3结构化原Trace/结果提取。','- '+str(ROOT/'.worktrees/p3-no-math-account3-restart-20261112/runs/research/p3-ablation-no-math-20261112-account3-restart1/private-evidence')+'：ledger、numerical_evaluations与research_decisions原记录。','','## 复用命令','','`extract_full.py`、`enrich_data.py`、`resource_full.py`、`candidate_evolution.py`、`synthesize_research.py`只读取已有数据；`prepare_motion.py`抽取已有姿态。`render_full.py`与`animate_native.py`只更新姿态并渲染，禁止增加mj_step。`plot_master.py`是暂存统计图草稿脚本，当前不继续执行。','']
sv('EVIDENCE_INDEX.md','\n'.join(ev))

# Explicit missing-value normalization, leaving source files untouched.
for name in ['ALL_TASK_RESULTS.csv','TASK_CASE_RESULTS.csv','RESOURCE_COSTS.csv','KEY_RESEARCH_NODES.csv','HARNESS_COMPONENT_EVIDENCE.csv','CANDIDATE_EVOLUTION.csv']:
    p=O/name;r=cr(p)
    for x in r:
        for k,v in x.items():
            if v=='':x[k]='unavailable'
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,list(r[0]));w.writeheader();w.writerows(r)
print('Master documentation assembled')
