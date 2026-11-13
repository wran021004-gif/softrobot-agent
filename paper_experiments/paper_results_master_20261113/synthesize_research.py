"""Curate saved research decisions, without running research or physics."""
from pathlib import Path
import csv,json
O=Path(__file__).resolve().parent
PHS=O.parents[1]/'runs/phs2d-paper-data-20261112'
FIVE=O.parent/'five_task_completion_20261113'
def rd(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(name,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with (O/name).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
catalog=rd(O/'SOURCE_DATA/DECISION_CATALOG.json');tasks={a['task_id']:a for a in rd(O/'SOURCE_DATA/FULL_TASKS.json')}
cases=rd(O/'SOURCE_DATA/FULL_CASES.json');nodes=[]
# Hypotheses below are concise editorial paraphrases of saved rationales, not new experiments.
specs=[
('T01','116','密集腱速约束阻碍到达与停稳。','缩小合法腱路半径可降低同样运动引起的腱长变化。','采用较小合法半径，保留完整执行器验收。','后续14 mm边界设计仍有0.199%腱速超限，转向增加可达余量。','Agent Reasoning; Mathematical Research Architecture'),
('T01','127','最小合法半径和完整控制网格仍有0.199%峰值腱速超限，位置在10 mm边界。','增加总柔性长度5 mm可能缓解近伸直目标下的位置—制动冲突。','两段各增2.5 mm，后续工况必须共用新结构。','最终162.5/112.5 mm共同结构通过3/3工况。','Agent Reasoning; Physical Backend / Evaluator'),
('T01','159','正向工况从原初值搜索停滞。','当前同结构中央工况的平滑张力序列可提供不同控制初始盆地。','仅迁移当前控制输入，再按正向原任务重新求值。','最终同结构central_high、negative_low、positive_high全部通过。','Agent Reasoning; Store / Trace / Evidence'),
('T02','004','静力/GVS构造不能覆盖实际外部受力的完整任务。','应在包含真实外力的原生有限时间动力学中优化控制。','转向实际受力下的原生控制响应方法。','14 MPa候选仍呈现位置—制动冲突，随后调整刚度。','Agent Reasoning; Tool Registry / Dispatch'),
('T02','018','当前14 MPa结构在有限控制搜索中停滞。','降低刚度可在保留执行器约束下增加带载可达性。','进行有界刚度比较并独立检查三种受力工况。','12 MPa共同结构三工况通过；最大保持误差9.8971 mm。','Agent Reasoning; Mathematical Research Architecture'),
('T03','005','静力目标输入不证明0.5 s快速到达及0.45–0.5 s保持。','必须同时搜索快速运动、末端制动与密集执行器约束。','在原生完整动力学中搜索后独立验收。','终端误差2.1099 mm，保持最大误差2.6627 mm，正式工况通过。','Task Protocol; Physical Backend / Evaluator'),
('T04','010','历史单段0.27 m几何不满足当前根段设计域。','历史准静态跟踪思路可以迁移，但必须重新构造合法两段结构与初态。','保留冻结连接和2 g负载，构造总长0.258 m的合法两段候选。','后续原GVS控制路线未取得完整成功，转向原生平衡点组。','Knowledge; Agent Reasoning; Task Protocol'),
('T04','216','89点平衡组由全4 N初值触发非法优化试探，未生成可用组。','局部已知平衡初态和内点预张力可避免边界与全局初值问题。','使用当前t0平衡，仅将0.2 N项内移至0.21 N，保留原生守卫。','生成89点平衡组；静态最大位置误差0.6110 mm。','Agent Reasoning; Skill; Mathematical Research Architecture'),
('T04','220','静态组可用仍不能保证22 s双周期动态轨迹通过。','独立初态资格加周期张力前馈可能满足完整路径和执行器约束。','独立执行原22 s任务，不以静态优化终止状态代替验收。','完整22 s通过；RMSE0.68785 mm，最大误差1.02066 mm。','Skill; Task Protocol; Physical Backend / Evaluator'),
('T05','005','位置静力构造不适用于有向工具轴的完整约束。','需在实际局部轴到世界轴变换下联合优化位置与轴向。','采用原生直接控制响应，保留10 g真实工具COM及完整惯量。','位置7.4585 mm、轴向0.0518235 rad，两类约束同时通过。','Agent Reasoning; Research Intent Projection; Physical Backend / Evaluator'),
('T06','004','带时序的20 g负载扫描不能用单目标静力或位置指标代表。','完整非对角惯量和有向轴时序应共同进入原生响应。','搜索原0.6 s位置—轴向序列并独立执行。','最大位置误差11.8198 mm、轴向0.110448 rad，原任务通过。','Task Protocol; Research Intent Projection; Physical Backend / Evaluator'),
('T07','060','历史几何通过B，但A仍约10.6%超限，C接近可行。','圆形8 mm根段可同时改变质量、刚度和跨平面耦合；不是单因素导数。','检验圆形根段，保留长度、材料、路由及四个独立输入。','A超限降至0.875%，再测试长度与路由。','Agent Reasoning; Mathematical Research Architecture'),
('T07','074','分布增长162.5/112.5 mm使A超限增至4.40%。','返回最佳158.5 mm根段并将路由14.1→14 mm可能降低剩余腱速冲突。','放弃较长方案，采用合法边界路由，全部工况重新验收。','当前结构A独立通过，随后B与有向轴M5通过。','Agent Reasoning; Store / Trace / Evidence'),
('T07','106','同一硬件A/B/M5通过，C从历史控制盆地仍超限4.11%。','采用当前A控制作为输入初值可能突破C的局部搜索停滞。','保留共同硬件，仅用当前A张力序列重新优化C。','同一四腱结构最终4/4原工况通过。','Agent Reasoning; Skill; Physical Backend / Evaluator'),
('T08','006','1.5 mm放绳偏置候选刚度比约1.367，小于冻结1.5要求。','在同一二段二腱结构中将偏置改为1.8 mm可改变高载招募区间。','对称调整固定放绳偏置，不更改载荷和验收阈值。','双方向刚度比1.63145475；低载7.9281 mm，高载22.5085 mm。','Agent Reasoning; Physical Backend / Evaluator'),
('T08','009','核心指标通过尚需冻结协议的成对机制及复核。','去除腱限位的配对试验与半步长/初态扰动可检查响应来源和稳定性。','采用已有独立双方向与机制复核结果作最终依据。','双方向最终通过；保留task.passive_response / development_valid分类。','Task Protocol; Physical Backend / Evaluator'),
('T09','210','实际导向孔/支架必须保留质量、COM、惯量；初次接触策略错误重启了附件碰撞。','应修复附件接触保真，不能删除真实导向结构换取通过。','构造包含20个真实孔/支撑总成的候选并修复接触策略。','后续完整独立按钮任务通过。','Agent Reasoning; Skill; Task Protocol'),
('T09','213','修复模型后仍需完整按压、保持和释放任务确认。','包含真实附件的接触响应可满足0.5 s深度/力联合保持。','独立执行完整任务，保留负载与接触要求。','深度最大误差0.052753 mm、力误差0.0024651 N，释放接近零。','Physical Backend / Evaluator; Task Protocol'),
('T10','017','原GVS/NMPC路线存在保持、腱速/行程冲突。','必须先诊断原生启动/制动，不应把开环目标到达当作冲击恢复。','采用原生启动试验检查完整约束，后续切换状态反馈路线。','历史失败促成原生状态反馈方法选择；最终三required通过。','Agent Reasoning; Knowledge'),
('T10','210','需原M2硬件、共同控制器和对外部脉冲未知的反馈执行。','静力参考、完整原生切线、离散LQR与有界张力分配可形成恢复控制。','每次执行重新计算参考与增益，并冻结共同配方。','早期组因默认参数不一致被拒；最终修复后全部五工况同配方。','Agent Reasoning; Skill; Task Protocol'),
('T10','222','正/负脉冲与无脉冲必须共用控制器，冻结控制只作为control。','共同反馈应在原±Y半正弦脉冲后满足完整保持窗。','执行同配方三required及两frozen control，不向控制器提供脉冲时刻。','required3/3通过，frozen control0/2；最终最大保持误差4.1314 mm。','Task Protocol; Physical Backend / Evaluator'),
]
trace_cache={}
def associated(e):
    p=e['source']
    if p not in trace_cache:trace_cache[p]=[json.loads(l) for l in Path(p).read_text(encoding='utf-8-sig').splitlines()]
    arr=trace_cache[p];i=next(i for i,a in enumerate(arr) if a.get('event_id')==e['event_id'])
    # Save the exact immediately following request/response events, to keep early-candidate identity independent of final identity.
    batch=[]
    for a in arr[i+1:]:
        if a.get('kind')=='decision':break
        batch.append(a)
    def refs(x):
        ans=[]
        if isinstance(x,dict):
            for k,v in x.items():
                if k in ['candidate','selected_candidate','source_candidate']:
                    if isinstance(v,dict) and v.get('artifact_id'):ans.append(v['artifact_id'])
                    elif isinstance(v,str):ans.append(v)
                ans.extend(refs(v))
        elif isinstance(x,list):
            for v in x:ans.extend(refs(v))
        return ans
    return list(dict.fromkeys(refs(batch))),batch
saved=[]
for tid,prefix,obs,hyp,decision,result,components in specs:
    e=next(a for a in catalog[tid] if a['event_id'].startswith(tid+'-'+prefix+'-'))
    ids,batch=associated(e);stage=f'{tid}-{prefix}'
    saved.append(dict(stage_id=stage,decision=e,following_events=batch))
    trace_candidate=next((a.get('candidate_id') for a in batch if a.get('candidate_id')),None)
    conf=next((a.get('exact_input',{}).get('arguments',{}).get('configuration',{}).get('artifact_id') for a in batch if isinstance(a.get('exact_input',{}).get('arguments',{}).get('configuration'),dict)),None)
    nodes.append(dict(task_id=tid,stage_id=stage,candidate_id=trace_candidate or ';'.join(ids) or 'unavailable',candidate_artifact_refs=';'.join(ids) or 'unavailable',configuration_reference=conf or 'unavailable',observation=obs,hypothesis=hyp,
        research_intent=e['rationale'],selected_capability=next((a.get('tool_name') for a in batch if a.get('tool_name')),e['selected_tool']),decision=decision,measured_result=result,
        next_action=e.get('next_action') or '见后续结果',evidence_reference=e['source']+'#'+e['event_id']+'; '+json.dumps(tasks[tid]['source_reference'],ensure_ascii=False),
        harness_component=components,hypothesis_basis='原始rationale的编辑性概括；未声明独立因果效果',run_id=next((a['study_id'] for a in batch if a.get('study_id')),tasks[tid]['run_id'])))
with (PHS/'KEY_NODES.csv').open(encoding='utf-8-sig') as f:
    for a in csv.DictReader(f):
        nodes.append(dict(task_id='PHS-2D',stage_id=a['node_id'],candidate_id=a['candidate_id'],observation=a['observed_problem'],
            hypothesis=a['decision_basis'],research_intent=a['title'],selected_capability='见call_ids：'+a['call_ids'],decision=a['decision'],
            measured_result=a['key_data'],next_action=a['followup_result'],evidence_reference=a['evidence_paths']+'; '+a['trace_source'],
            harness_component='Agent Reasoning; Mathematical Research Architecture; Physical Backend / Evaluator',
            hypothesis_basis='保留已整理的11个原始节点；decision_basis为原Trace决策依据',run_id='psd2d-core-halfstep-20261112' if a['node_id']=='N11' else 'psd2d-core-fresh-20261112'))
write('KEY_RESEARCH_NODES.csv',nodes)
(O/'SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf-8')

rows=[]
def add(component,tids,event,role,evidence,display,ablation,strength='直接事件证据；独立收益尚未消融'):
    rows.append(dict(component=component,tasks=tids,key_event=event,actual_role=role,original_evidence=evidence,paper_display=display,
        recommended_ablation=ablation,evidence_strength=strength))
nodefile=str(O/'KEY_RESEARCH_NODES.csv')
add('Agent Reasoning','T01;T07;PHS-2D','根据局部腱速、停稳与几何失败反复改变机制假设，而非固定调用次序。','提出物理假设、识别控制与结构耦合、否定无效分支并选择新初值。',nodefile+'#T01-127,T07-060,T07-074,T07-106,N01–N11','保留观察→假设→实验→改向的真实短链','C1：PHS-2D Full vs Fixed-Plan')
add('Task Protocol','T04;T07;T08;T10','22 s完整周期、同结构四工况、开发任务分类、三required/两control被明确绑定。','约束研究声明与验收范围；默认控制器不一致阻止组验收。',str(O/'SOURCE_DATA/PROTOCOLS.json')+'; '+str(FIVE/'T10_M7_impact_recovery/T10_RUN_06/FINAL_RESULT.md'),'协议范围与逐工况结果表','所有对照保持协议不变；不建议删除验收器作为收益消融')
reads=rd(O/'SOURCE_DATA/KNOWLEDGE_READS.json')
add('Knowledge','T01;T04;T07;T09;T10','归档有实际版本读取；T04决策明确援引准静态历史，T10依据反馈路线历史。','提供候选机制、适用边界和失败经验；历史成功不替代当前验收。',str(O/'SOURCE_DATA/KNOWLEDGE_READS.json')+'; '+nodefile+'#T04-010,T10-210','实际读取版本与后续决策并列，不以读取次数证明收益','C3：T04 Knowledge+Skill ON vs OFF')
add('Skill','T04;T07;T09;T10','平衡初态/平衡组、共同结构、装配保真及状态反馈流程实际读取并执行。','复用结构化研究程序，规定资格门禁与独立物理验收。',str(O/'SOURCE_DATA/KNOWLEDGE_READS.json')+'; '+str(FIVE/'KNOWLEDGE_LIBRARY'),'方法流程与适用条件，不宣称只靠Skill即可成功','C3：T04联合关闭；单独组件效应需要额外分解')
add('Research Intent Projection','T02;T05;T06;PHS-2D','正式研究意图进入带原始输入的dispatch请求。','将实际外力、有向轴和机制问题绑定到合法数学请求，保留变量/固定条件。',str(O/'SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json')+'; '+str(FIVE/'T04_figure_eight_tracking/T04_RUN_03/MAIN_REPLAY_INPUT'),'选取一条意图及其相邻正式请求','C2：选择/问题组织层ON vs 同底层工具直接调用；语义投影细分尚无独立对照')
add('Mathematical Research Architecture','T04;T07;PHS-2D','局部分析支持PHS路由/刚度修改；T07比较后否定增长度；T04失败组转局部内点续接。','组织有边界的研究问题，反馈可用性与局限，支持设计/控制/停止决策。',nodefile+'#T04-216,T07-074,N02–N10; '+str(O/'SOURCE_DATA/RESOURCE_DETAILS.json'),'同时展示有效修改、负面诊断和确认性分析','C2：M2及PHS-2D Full-Selective vs Direct-Math-Tools')
add('Tool Registry / Dispatch','T02;T05;T06;T07','实际适用性拒绝后选择已注册native方法；T07读取候选绑定目录。','工具发现、适用性约束、参数路由和执行；拥有目录不等于算法有效。',str(O/'SOURCE_DATA/DECISION_CATALOG.json')+'#T07-011,T02-004,T05-005,T06-004','一条被拒静力方法与随后可用方法','C2中两臂保留相同注册能力，避免权限差异混淆')
add('Store / Trace / Evidence','T01–T10;PHS-2D','候选、请求、结果及已读证据可按ID连接；已有输入被复用而非移植验收。','保持研究状态与证据可追溯，区分当前同结构控制初值与旧结果。',str(O/'SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json')+'; '+str(O/'SOURCE_DATA/MODEL_BINDINGS.json'),'关键节点旁的原始证据引用','记录设施两臂相同；可复现性检查不等于任务效果消融')
add('Physical Backend / Evaluator','T01–T10;PHS-2D','32条独立工况记录：30 required通过，T10两frozen controls失败；PHS另有半步长复核。','运行真实动力学与完整任务验收，阻止静力/局部结果被当作完整成功。',str(O/'TASK_CASE_RESULTS.csv')+'; '+str(PHS/'FINAL_METRICS.json'),'完整工况与控制失败、真实轨迹','所有消融冻结同一后端/网格/验收；不关闭物理器来证明研究价值')
add('Budget Accounting','T01–T10;PHS-2D','Store与成本记录保留数学收费、实际episodes、内部积分、CPU/墙钟等不同口径。','记录资源使用和失败开销；部分字段不可得时不归零。',str(O/'RESOURCE_COSTS.csv')+'; '+str(O/'SOURCE_DATA/RESOURCE_DETAILS.json'),'资源分开绘图，区分已知步数与完整覆盖','C1/C2/C3设置相同预算；当前无预算管理独立收益对照')
add('Replay','T01;T04;T07;T09;T10','原始正式请求、schema、意图投影和证据入口已归档。','支持决策与调用的重建；本轮未执行任何新的端到端Replay。',str(FIVE/'T04_figure_eight_tracking/T04_RUN_03/MAIN_REPLAY_INPUT')+'; '+str(O/'SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json'),'可重放请求示例和输入文件，而非新增复现实验成功率','未来固定版本重放一致性检查；不作为已完成的因果实验','请求与文件存在是直接证据；端到端自主重放成功 unavailable')
write('HARNESS_COMPONENT_EVIDENCE.csv',rows)
print('Research nodes',len(nodes),'PHS',sum(r['task_id']=='PHS-2D' for r in nodes),'components',len(rows))
