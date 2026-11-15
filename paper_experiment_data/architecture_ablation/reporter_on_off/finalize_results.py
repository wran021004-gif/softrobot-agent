"""Aggregate actual paired decisions, blinded model ratings and explicit token proxies."""
import json,os,sys,statistics
from run_ablation import ROOT,read,write,rows_csv

sys.path.insert(0,str(ROOT/'tokenizer_runtime'))
os.environ['TIKTOKEN_CACHE_DIR']=str(ROOT/'tokenizer_cache')
import tiktoken
encoding=tiktoken.get_encoding('o200k_base')
METRICS=['physical_interpretation','evidence_consistency','limitation_recognition','research_actionability','main_decision_quality']
results=[json.loads(s) for s in (ROOT/'decision_results.jsonl').read_text(encoding='utf8').splitlines()]
assert len(results)==12 and len({r['session_id'] for r in results})==12 and all(r['status']=='completed' for r in results)
assert all(r['main_provider_requests']<=4 and r['new_physics_runs']==r['new_mathematical_solves']==r['new_candidates']==0 for r in results)
keys=read(ROOT/'private_condition_key.json')
costs=[];details={};rating_rows=[]
for r in results:
 sid=r['snapshot_id'];snap=read(ROOT/f'snapshots/{sid}.json');folder=ROOT/'sessions'/r['session_id']
 sent=[]
 for turn in r['requests']:
  if turn.get('http_status')==200:
   wire=read(folder/f"request_{turn['turn']}.json")
   reply=json.loads((folder/f"response_{turn['turn']}.txt").read_text(encoding='utf8'))
   sent.append(dict(visible_context_tokens_proxy=sum(len(encoding.encode(m['content'])) for m in wire['messages']),
       output_text_tokens_proxy=len(encoding.encode(reply['choices'][0]['message']['content'])),
       request_bytes=len(json.dumps(wire,ensure_ascii=False,separators=(',',':')).encode()),wire=wire))
 assert len(sent)==1,'All completed replays used exactly one inference response.'
 details[(sid,r['condition'])]=sent[0]
 h=(snap['historical_reporter_usage'] or {}).get('usage') or {}
 cost=dict(snapshot_id=sid,condition=r['condition'],session_id=r['session_id'],model='gpt-5.6-sol',
     main_input_tokens_actual=None,main_output_tokens_actual=None,total_tokens_actual=None,
     main_visible_context_tokens_proxy=sent[0]['visible_context_tokens_proxy'],main_output_text_tokens_proxy=sent[0]['output_text_tokens_proxy'],
     proxy_encoding='tiktoken 0.12.0 / o200k_base; visible text only; not verified model-specific tokenizer or hidden reasoning/billing',
     request_bytes=sent[0]['request_bytes'],provider_send_attempts=r['main_provider_requests'],successful_main_inference_responses=1,
     local_pre_inference_rejections=1,new_reporter_provider_requests=0,new_reporter_input_tokens=0,new_reporter_output_tokens=0,
     reused_report_generation_input_tokens=h.get('prompt_tokens') if r['condition']=='ON' else 0,
     reused_report_generation_output_tokens=h.get('completion_tokens') if r['condition']=='ON' else 0,
     reporter_added_visible_tokens_proxy=None,main_wall_s=r['wall_s'],
     main_inference_wall_s=sum(q['wall_s'] for q in r['requests'] if q.get('http_status')==200),
     new_reporter_wall_s=0,historical_reporter_wall_s=None)
 costs.append(cost)
 sidkey=next(k for k in keys if k['session_id']==r['session_id']);label=sidkey['anonymous_label']
 review=read(ROOT/f'blind_review/{sid}/independent_model_review.json')
 score=next(e for e in review['review']['evaluations'] if e['label']==label)
 rating_rows.append(dict(snapshot_id=sid,condition=r['condition'],anonymous_label=label,
     **score['scores'],mean_score=statistics.mean(score['scores'].values()),
     unsupported_claims_count=len(score['unsupported_claims']),
     unsupported_claims_severity=json.dumps([c['severity'] for c in score['unsupported_claims']]),
     evidence_reference_correct=score['reference_assessment']['correct'],evidence_reference_total=score['reference_assessment']['total'],
     semantic_reference_issues=json.dumps(score['reference_assessment']['issues'],ensure_ascii=False),
     judge_model=review['model'],judge_wall_s=review['wall_s']))

pairs=[]
for sid in ['M1_A','M1_B','M1_C','P3_A','P3_B','P3_C']:
 a=details[(sid,'OFF')];b=details[(sid,'ON')]
 assert a['wire']['model']==b['wire']['model'] and a['wire']['stream']==b['wire']['stream']
 assert a['wire']['messages'][0]==b['wire']['messages'][0]
 assert b['wire']['messages'][1]['content'].startswith(a['wire']['messages'][1]['content']+'\n')
 off=next(c for c in costs if c['snapshot_id']==sid and c['condition']=='OFF')
 on=next(c for c in costs if c['snapshot_id']==sid and c['condition']=='ON')
 on['reporter_added_visible_tokens_proxy']=b['visible_context_tokens_proxy']-a['visible_context_tokens_proxy'];off['reporter_added_visible_tokens_proxy']=0
 so=next(s for s in rating_rows if s['snapshot_id']==sid and s['condition']=='OFF')
 sn=next(s for s in rating_rows if s['snapshot_id']==sid and s['condition']=='ON')
 row=dict(snapshot_id=sid,case=sid[-1])
 for metric in METRICS:
  row[metric+'_OFF']=so[metric];row[metric+'_ON']=sn[metric];row[metric+'_delta']=sn[metric]-so[metric]
 delta=sn['mean_score']-so['mean_score']
 row.update(mean_score_OFF=so['mean_score'],mean_score_ON=sn['mean_score'],mean_score_delta=delta,
     result='ON_win' if delta>1e-10 else 'ON_loss' if delta< -1e-10 else 'tie',
     unsupported_claims_OFF=so['unsupported_claims_count'],unsupported_claims_ON=sn['unsupported_claims_count'],
     context_tokens_proxy_OFF=off['main_visible_context_tokens_proxy'],context_tokens_proxy_ON=on['main_visible_context_tokens_proxy'],
     context_tokens_proxy_delta=on['reporter_added_visible_tokens_proxy'],
     context_proxy_increase_percent=100*on['reporter_added_visible_tokens_proxy']/off['main_visible_context_tokens_proxy'],
     wall_s_OFF=off['main_wall_s'],wall_s_ON=on['main_wall_s'],wall_s_delta=on['main_wall_s']-off['main_wall_s'],
     input_output_tokens_actual=None,quality_source='One independent gpt-6-astra blind review per anonymous pair; human verification pending.')
 pairs.append(row)
rows_csv(ROOT/'token_costs.csv',costs);rows_csv(ROOT/'blind_review/scores_unblinded.csv',rating_rows)
# Keep the condition mapping and unblinded scores outside the material shown to reviewers.
(ROOT/'blind_review/scores_unblinded.csv').replace(ROOT/'scores_unblinded.csv')
rows_csv(ROOT/'pairwise_results.csv',pairs)
aggregates=dict(quality_OFF=statistics.mean(s['mean_score'] for s in rating_rows if s['condition']=='OFF'),
    quality_ON=statistics.mean(s['mean_score'] for s in rating_rows if s['condition']=='ON'),
    delta_mean=statistics.mean(p['mean_score_delta'] for p in pairs),delta_median=statistics.median(p['mean_score_delta'] for p in pairs),
    on_wins=sum(p['result']=='ON_win' for p in pairs),ties=sum(p['result']=='tie' for p in pairs),on_losses=sum(p['result']=='ON_loss' for p in pairs),
    context_token_proxy_delta_mean=statistics.mean(p['context_tokens_proxy_delta'] for p in pairs),
    context_token_proxy_delta_median=statistics.median(p['context_tokens_proxy_delta'] for p in pairs),
    per_metric={metric:dict(delta_mean=statistics.mean(p[metric+'_delta'] for p in pairs),delta_median=statistics.median(p[metric+'_delta'] for p in pairs)) for metric in METRICS})
for condition in ['OFF','ON']:
 aggregates['unsupported_claims_'+condition]=sum(s['unsupported_claims_count'] for s in rating_rows if s['condition']==condition)
history=read(ROOT/'historical_agent_nodes/P3_A/historical_next_decision.json')
accounting=dict(main_sessions=12,main_inference_responses=12,local_pre_inference_rejections=12,main_send_attempts=24,
    new_reporter_requests=0,reused_reporter_reports=6,independent_review_requests=6,total_send_attempts=30,
    new_math_solves=0,new_physics_runs=0,new_candidates=0,new_studies=0,main_actual_token_usage=None,
    main_token_usage_status='Gateway omits usage; null is not zero.',context_proxy_encoding='o200k_base',
    proxy_limit='Visible message text only; no verified GPT-5.6-Sol tokenizer, framing or hidden reasoning count.',
    historical_reporter_input_tokens=sum(c['reused_report_generation_input_tokens'] or 0 for c in costs),
    historical_reporter_output_tokens=sum(c['reused_report_generation_output_tokens'] or 0 for c in costs))
write(ROOT/'experiment_results.json',dict(pairs=pairs,aggregates=aggregates,accounting=accounting,
    causal_control=dict(shared_raw_context=True,only_reporter_interpretations_added=True,identical_model_and_default_settings=True,
       isolated_sessions=True,scientific_execution=False,textual_Core_schema_transport=True),
    limitations=['Six single replays, one judge model; no statistical significance or task-success inference.',
      'Snapshot-state restart, not restoration of the full cumulative historical Agent memory. Historical full requests and decisions are separate reference material.',
      'Current gateway does not support explicit reasoning or native functions; same unexposed default and identical textual Core schemas used in both conditions.',
      'Actual billing/input/output tokens unavailable; context/output proxies and historical actual counts clearly separated.',
      'Model blind ratings are not ground truth; human scoring form retained.',
      'Schema-valid future action was recorded but task-specific execution admission was not tested.']))
table='\n'.join(f"| {p['snapshot_id']} | {p['mean_score_OFF']:.2f} | {p['mean_score_ON']:.2f} | {p['mean_score_delta']:+.2f} | {p['context_tokens_proxy_OFF']:,} | {p['context_tokens_proxy_ON']:,} | {p['context_tokens_proxy_delta']:+,} |" for p in pairs)
metric_table='\n'.join(f"| {m} | {v['delta_mean']:+.3f} | {v['delta_median']:+.3f} |" for m,v in aggregates['per_metric'].items())
historical_rows=[]
import csv
with (ROOT/'P3_historical_agent_nodes.csv').open(encoding='utf-8-sig') as f:historical_rows=list(csv.DictReader(f))
history_table='\n'.join(f"| {p['snapshot_id']} | {int(p['historical_main_input_tokens']):,} | {int(p['historical_main_output_tokens']):,} | {p['next_plan_action']} / {p['next_plan_selected_method']} |" for p in historical_rows)
comments=[]
for sid in ['M1_A','M1_B','M1_C','P3_A','P3_B','P3_C']:
 review=read(ROOT/f'blind_review/{sid}/independent_model_review.json')['review']
 comments.append(f"- **{sid}**：{review['rationale']}")
summary=f'''# Reporter ON/OFF Research Architecture Ablation

已实际完成六个真实历史节点、六份完全匹配的历史 Reporter 报告复用、十二个独立 Main 决策 Session，以及六次独立模型匿名成对盲评。未执行数学求解、结构搜索、MuJoCo 或完整 Study。M1/P3 各 A/B/C；类别近似匹配和原证据引用见 snapshot_manifest.csv。

## 成对结果

质量分为独立模型 gpt-6-astra 的五项 0–4 盲评分等权平均。评审只获共同原始证据和 A/B Plan，不获条件标签、Reporter 报告、历史下一步决策或成本。分词数字为标准 o200k_base 对**可见上下文文本**的统一代理计数，不能当作 Provider 实测或账单 Token。

| 节点 | OFF 质量分 | ON 质量分 | ON−OFF | OFF 上下文代理 Token | ON 上下文代理 Token | 增量 |
|---|---:|---:|---:|---:|---:|---:|
{table}

六组 OFF 均分 **{aggregates['quality_OFF']:.3f}**，ON 均分 **{aggregates['quality_ON']:.3f}**；配对差均值 **{aggregates['delta_mean']:+.3f}**，中位数 **{aggregates['delta_median']:+.3f}**。ON 胜/平/负为 **{aggregates['on_wins']}/{aggregates['ties']}/{aggregates['on_losses']}**。这是小样本、单次回放和单模型评审结果，不构成充分统计显著性或机器人任务成功率改善证明。

| 指标 | 配对差均值 | 配对差中位数 |
|---|---:|---:|
{metric_table}

无证据支持结论数由盲评模型判定：OFF {aggregates['unsupported_claims_OFF']}，ON {aggregates['unsupported_claims_ON']}。逐条结论、严重程度、引用语义问题及理由保留在 blind_review/*/independent_model_review.json，条件解盲后的逐项表在 scores_unblinded.csv。解释更长本身不加分；假设不因尚未证实而自动算作无支持事实。模型评分仍须人工复核，human_scoring.csv 留空供复核，未伪造人工分数。

## 对实验问题的直接回答

- **整体质量是否提高：** 本轮独立模型盲评均分提高 {aggregates['delta_mean']:.2f}/4，但中位配对差为零，四组持平；不能写成普遍改善。
- **哪类证据体现价值：** 胜出的两个节点分别是 M1 C 的适用性/执行约束边界，以及 P3 A 的有限参数对照与缺失成对机制验收。两个竞争解释 B 节点均未拉开差距。
- **物理机制理解：** 指标均差 {aggregates['per_metric']['physical_interpretation']['delta_mean']:+.3f}；P3 A 的 ON 将实际参与承载的腱与所需的干预对照联系起来，OFF 的完整未消融 Replay 未明确覆盖缺失的成对机制指标。
- **限制识别：** 指标均差 {aggregates['per_metric']['limitation_recognition']['delta_mean']:+.3f}；M1 C 的 OFF 提议 120 次迭代，超过冻结 100 次上限，并假设了未被所给证据证明的初始化选项，ON 避免这些缺陷。P3 C 两组仍同分，不能说 Reporter 一定能解决证据边界理解。
- **无支持解释是否减少：** 盲评模型识别的无支持结论由 {aggregates['unsupported_claims_OFF']} 降至 {aggregates['unsupported_claims_ON']}，两条 OFF 问题均判为 moderate；这是模型评审记录，仍待人工复核。
- **行动是否更具体有效：** Research Actionability 均差 {aggregates['per_metric']['research_actionability']['delta_mean']:+.3f}。P3 A 的区别是成对腱约束消融与仅完整协议 Replay，比较的是补齐机制证据的针对性，不是行动文本长短。
- **额外 Token 成本：** ON 平均增加 {aggregates['context_token_proxy_delta_mean']:.1f} 个可见上下文代理 Token。P3 三节点分别增加 956/1585/1667，约 0.51%/0.83%/1.82%。Provider 实测和隐藏推理用量未返回；报告历史生成成本另计，不能把代理数当成精确总成本。
- **是否有 ON 更差：** 本轮主要指标下有 {aggregates['on_losses']} 组 ON 落后；样本太少，不能据此排除 Reporter 在其他节点产生负效应。

## 逐节点解释与是否值得写入论文

{chr(10).join(comments)}

最值得写入论文的是**按证据类型报告差异和无改善案例**，并说明 Reporter 的价值是否落在机制解释、证据边界或行动选择上。应按以上真实分数和逐条理由报告，不预设 ON 必须更好。两个行动不同本身不是质量提升；行动相同也可能在证据忠实度和限制识别上存在差异。

## P3 完整 Agent 历史节点参照

按用户补充要求，已保存三个节点的完整历史 Main 请求、下一步原始 ResearchDecision/Plan 和实际 Provider 用量，入口为 P3_historical_agent_nodes.csv 与 historical_agent_nodes/。

| 节点 | 历史下一次 Main 输入实测 Token | 输出实测 Token | 历史下一步行动 |
|---|---:|---:|---|
{history_table}

这些是原 Agent 的完整累积上下文，不是本次受控 ON/OFF 的对照分数。本次是相同数学节点状态的独立重启决策回放，并未恢复整段历史记忆。因此不能直接用历史 Main 输入 Token 减去本次 OFF 代理 Token，声称这是关闭 Reporter 节约的量。

## 成本与 Token 口径

每个 Main Session 实际获得一次完整模型响应。首批十二次原接口请求因本地 Gateway 不支持 tools/reasoning_effort，在入口检查阶段被明确 400 拒绝，未进入上游推理；拒绝记录保留且计入各 Session 四次发送上限。修正后每 Session 共两次发送（一次拒绝、一次推理），累计 Main 发送 24 次、成功 Main 推理 12 次。另有独立盲评 6 次，Reporter 新生成 0 次，已复用报告 6 份。

当前网关不返回 usage，Main/评审模型实测输入/输出及实际总 Token 记为 null，**不是零**。本地使用 tiktoken 0.12.0 / o200k_base 统一计数可见文本，尚无该模型精确 tokenizer、聊天 framing 或隐藏推理用量的验证；因此只作为上下文和可见输出的代理指标。ON 可见上下文增量均值 **{aggregates['context_token_proxy_delta_mean']:.1f}**、中位数 **{aggregates['context_token_proxy_delta_median']:.1f}**；含报告阅读开销。

复用的六份已完成 Reporter 报告均由历史 gpt-5.6-sol、medium 配置生成（历史传输包含 API 和 Gateway）。历史生成用量另列：输入 {accounting['historical_reporter_input_tokens']:,}、输出 {accounting['historical_reporter_output_tokens']:,} Token。本次无新增生成费用，不意味着从零部署 Reporter 免费；历史完成请求用量也不等于所有历史失败尝试成本。token_costs.csv 同时保留实际值缺失、代理计数、报告历史生成用量和墙钟，未混为一个精确总账。墙钟单次测量含服务/网络波动，不做速度优劣的统计推论。

## 执行口径与限制

Main 均为 gpt-5.6-sol、相同当前网关默认推理设置（具体档位不可见，不能声称 medium）、相同原始 JSON、候选、冻结任务、证据权限、文本化工具 Schema 和四次发送预算。ON 仅追加匹配报告的 interpretations。成对原始请求已核对共同前缀完全一致。前一 Session 输出未进入后一 Session。

当前网关只提供文本，返回的工具请求按现有 Core Plan/ResearchDecision、EvidenceQuery 校验；这是最小决策回放入口，不是已恢复生产 native function-call Harness。记录了下一步请求但未测试其任务专属执行 admission。M1 A 是局部控制系数响应，P3 A 是有限尺度对照而非严格梯度，结论应保留这些证据类型限制。

独立评审配置在确认已连接模型目录有 gpt-6-astra 后为本实验建立，复用现有网关，未新增科研 Agent/Planner 或修改生产 Main、Reporter、Harness。它与 Main 模型不同，所有匿名材料也保留人工复核入口。

实验已在六组完成后停止；未启动 Knowledge/Skill 或 Context 消融，未改动原主实验结果。
'''
(ROOT/'REPORTER_ABLATION_SUMMARY.md').write_text(summary,encoding='utf8')
protocol=(ROOT/'protocol.md').read_text(encoding='utf8').split('\n## 最终计数与评审口径')[0]
protocol=protocol.replace('沿用已有 Main gpt-5.6-sol、medium 及已配置 account3 Gateway；','Main 模型沿用 gpt-5.6-sol 和 account3 Gateway；原准备采用历史 medium，但当前网关不暴露推理档位，实际各组统一使用其默认设置，详见传输修正。')
protocol=protocol.replace('独立盲评配置未找到，按任务允许路径交付人工评分入口，未评分保持空值，不由执行者伪造质量分数。','准备时未找到现成独立盲评配置，先交付人工入口；后确认已连接网关有独立模型 gpt-6-astra，为本实验配置并实际完成六组模型盲评。人工评分仍为空，不伪造人工分数。')
(ROOT/'protocol.md').write_text(protocol.rstrip()+'\n\n## 最终计数与评审口径\n\n十二次独立决策回放及六组匿名盲评已完成。确认已连接网关可用独立模型 gpt-6-astra 后建立本实验评审配置，人工入口保留；初始“无现成评审配置”的准备状态不是最终执行状态。Token 使用统一 o200k_base 可见文本代理，Provider 实测未知保持 null。详细差值及限制见 REPORTER_ABLATION_SUMMARY.md。\n',encoding='utf8')
print(json.dumps(dict(aggregates=aggregates,accounting=accounting,pairs=[{k:p[k] for k in ['snapshot_id','mean_score_OFF','mean_score_ON','mean_score_delta','context_tokens_proxy_delta']} for p in pairs]),ensure_ascii=False))
