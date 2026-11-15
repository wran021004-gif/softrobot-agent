"""Prepare anonymous pairs and preserve original P3 Agent decision boundaries."""
import json
from pathlib import Path
from run_ablation import ROOT,WORK,read,write,rows_csv,Store

results=[json.loads(line) for line in (ROOT/'decision_results.jsonl').read_text(encoding='utf8').splitlines()]
assert len(results)==12 and all(r['status']=='completed' for r in results)
mapping=read(ROOT/'private_condition_key.json')
human=[]
for sid in [s['snapshot_id'] for s in read(ROOT/'execution_schedule.json') if s['condition']=='OFF']:
 snap=read(ROOT/f'snapshots/{sid}.json');decisions=[]
 for label in ['A','B']:
  key=next(k for k in mapping if k['snapshot_id']==sid and k['anonymous_label']==label)
  r=next(r for r in results if r['session_id']==key['session_id'])
  decisions.append(dict(label=label,decision=r['decision']))
  human.append(dict(snapshot_id=sid,anonymous_label=label,physical_interpretation='',evidence_consistency='',
      limitation_recognition='',research_actionability='',main_decision_quality='',mean_score='',
      unsupported_claims_count='',unsupported_claims_severity='',evidence_reference_accuracy='',comments=''))
 write(ROOT/f'blind_review/{sid}/evidence.json',snap['base_context'])
 write(ROOT/f'blind_review/{sid}/anonymous_decisions.json',decisions)
rows_csv(ROOT/'blind_review/human_scoring.csv',human)
(ROOT/'blind_review/README.md').write_text('''# 匿名盲评入口

每个快照目录只含共同原始证据和 A/B 两份匿名 Core Plan，不含 Reporter 报告、ON/OFF 映射或成本。条件映射在本目录外，由实验执行者保管。需要人工复核时先完成 human_scoring.csv，再查看条件映射。

五项各 0–4，等权平均：Physical Interpretation、Evidence Consistency、Limitation Recognition、Research Actionability、Main Decision Quality。解释更长不自动加分；两份同样合理可同分。区分待检验假设与声称已证实的事实：带预测/削弱条件的假设不因尚未证实而自动计为无支持结论。检查引用的语义对应，不能只看 ID 存在。有限对照不是严格梯度；未独立验收不是已成功；求解失败不等于不可行。

请依据证据分别列出无支持结论、轻微/一般/严重程度、错误引用及理由。模型盲评是独立模型的评审结果，不是事实真值；人工表保留供复核。原始材料不包含历史下一步决策，避免评审者以历史做法为标准答案。
''',encoding='utf8')

x=read(WORK/'paper_experiment_data/case_study_extracts/p3_trace_extract.json');store=Store(x['store']);events=x['event_index'];historical=[]
for sid in ['P3_A','P3_B','P3_C']:
 snap=read(ROOT/f'snapshots/{sid}.json');target=snap['reused_report_reference'];j=None
 for i,e in enumerate(events):
  if e['kind']=='reporter_completed' and store.artifact(e['outputs'][0]).get('report_reference')==target:j=i;break
 assert j is not None
 requests=[];decision=None;decision_event=None
 for e in events[j+1:]:
  if e['kind']=='r3_request':
   meta=store.artifact(e['outputs'][0])
   if meta.get('purpose')=='conversation':
    usage=next((u for u in x['usage_deduplicated'] if u['request_id']==e['request_id']),None)
    requests.append(dict(request_id=e['request_id'],event_sequence=e['sequence'],metadata=meta,usage=usage))
  if e['kind']=='model_original_tool_request':
   use=store.artifact(e['outputs'][0])['tool_use']
   if use['name']=='research_plan':decision=use;decision_event=e;break
 assert decision is not None and requests
 folder=ROOT/'historical_agent_nodes'/sid
 write(folder/'historical_next_decision.json',dict(source_study=x['study_id'],boundary_report=target,
      boundary_event_sequence=events[j]['sequence'],decision_event=decision_event,tool_use=decision,
      following_main_requests=requests,role='Historical reference only, not paired control or blind-review answer key.'))
 for req in requests:
  wire=store.artifact(req['metadata']['request'])
  write(folder/(req['request_id']+'_original_request.json'),wire)
 input_tokens=sum(r['usage']['usage']['prompt_tokens'] for r in requests if r['usage'])
 output_tokens=sum(r['usage']['usage']['completion_tokens'] for r in requests if r['usage'])
 historical.append(dict(snapshot_id=sid,source_study=x['study_id'],math_reference=snap['base_context']['raw_mathematical_result_reference']['artifact_id'],
      reporter_reference=target['artifact_id'],boundary_event_sequence=events[j]['sequence'],
      next_plan_event_sequence=decision_event['sequence'],historical_main_requests_to_plan=len(requests),
      historical_main_input_tokens=input_tokens,historical_main_output_tokens=output_tokens,
      next_plan_action=decision['input'].get('action'),next_plan_selected_method=(decision['input'].get('decision') or {}).get('selected_method'),
      comparison_scope='Original Agent context and decision, different historical transport/history; not the controlled ON/OFF comparison.'))
rows_csv(ROOT/'P3_historical_agent_nodes.csv',historical)
print(json.dumps(dict(completed_decisions=12,anonymous_pairs=6,p3_historical_nodes=historical)))
