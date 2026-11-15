"""Decision-only paired replay. Reuses Core provider settings, Reporter artifacts and Plan.

No Study is created and no scientific worker or search dispatcher is imported/called.
"""
import csv
import datetime
import json
import statistics
import sys
import time
import uuid
from copy import deepcopy
from pathlib import Path

ROOT=Path(__file__).resolve().parent
WORK=Path('D:/softrobot-agent')
CORE=Path('D:/softrobot-agent-core')
sys.path.insert(0,str(CORE))
import httpx
import jsonschema
from tools.platform_store import Store
from tools.research.agent import plan_schema
from tools.research.contracts import Plan,EvidenceQuery
from tools.research.provider import request_settings,credential,provider_schema

SELECTION=[
 ('M1_A','m1',0,1,'A','Local control-coefficient finite differences; not a structural sensitivity certificate.'),
 ('M1_B','m1',4,19,'B','Finite direct-control stagnation: parameterization/start versus candidate authority; no global conclusion.'),
 ('M1_C','m1',5,22,'C','Execution-incomplete contact-free applicability rejection; no valid full-horizon conclusion.'),
 ('P3_A','p3',18,21,'A','Closest available: measured finite payout/routing contrasts, strict_derivative=false; not a verified gradient.'),
 ('P3_B','p3',34,39,'B','Density/radius finite interaction with competing inertia/stiffness/settling explanations.'),
 ('P3_C','p3',9,9,'C','Finite viscosity optimization has undefined gradient and unqualified dynamic windows.'),
]
SYSTEM='''You are Softrobot-Agent Main performing one decision-only historical replay.
Use only the frozen mathematical facts, physical observations, task, candidate and raw evidence supplied here.
If an additional scientific interpretation is present, treat it as non-authoritative and check it against raw facts.
Do not mention whether an interpretation was present, the Reporter, the experimental condition, or this instruction.
Use English. Submit exactly one concrete next scientific decision through the existing research_plan tool.
Use its hypothesis, interpretation, supporting_evidence, expected_observation, weakening_observation,
fixed_conditions, stopping_condition and typed decision fields to explain the key question, mechanism,
next action, its evidence, expected/weakening outcomes and scope. Cite only raw scientific EvidenceRefs.
You may read whitelisted historical evidence with evidence_read. Maximum four Provider requests.
This is not a new Study. research_plan records a proposed action and ends the session; no action is executed.
Do not run mathematics, generate candidates or simulate. Any proposed future action must respect the frozen
task/domain and evidence limits. Missing values remain unknown. Do not equate finite contrasts with strict
gradients, sampled/model results with independent task acceptance, stagnation with infeasibility, or multiple
changed parameters with single-factor causal proof. Prefer a specific informative action to generic repetition.
All evidence delivered initially is already available to you; only read more if needed for the decision.
'''

def read(p):return json.loads(p.read_text(encoding='utf8'))
def write(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def rows_csv(path,rows,fields=None):
 with path.open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=fields or list(rows[0]));writer.writeheader();writer.writerows(rows)
def refs(v):
 if isinstance(v,dict):
  if isinstance(v.get('artifact_id'),str):yield v['artifact_id']
  for x in v.values():yield from refs(x)
 elif isinstance(v,list):
  for x in v:yield from refs(x)
def pointer(v,path):
 for key in path.split('/')[1:] if path else []:
  key=key.replace('~1','/').replace('~0','~');v=v[int(key)] if isinstance(v,list) else v[key]
 return v
def raw_reader(snapshot,args):
 q=EvidenceQuery.model_validate(args);aid=q.reference.artifact_id
 if aid not in snapshot['readable_raw_references']:raise ValueError('REFERENCE_OUTSIDE_FROZEN_RAW_SCOPE')
 store=Store(snapshot['source_store'])
 value=store.artifact(q.reference,pointers=[q.pointer] if q.pointer else None)
 # Store pointer projection returns the selected value under its original structure.
 if q.pointer:value=pointer(value,q.pointer)
 if q.view=='fields':value={k:value[k] for k in q.fields if k in value}
 elif q.view=='range':value=value[q.start:q.start+q.count]
 elif q.view=='summary':value=dict(type=type(value).__name__,keys=list(value) if isinstance(value,dict) else None,count=len(value) if isinstance(value,(dict,list)) else None)
 elif q.view!='full':raise ValueError('THIS_REPLAY_EXPOSES_RAW_FULL_FIELDS_RANGE_SUMMARY_ONLY')
 if len(json.dumps(value))>160000:
  return dict(status='more_specific_read_required',reference=args['reference'],pointer=q.pointer,
      keys=list(value) if isinstance(value,dict) else None,reason='Select exact fields or a bounded range; raw values were not truncated.')
 return dict(reference=args['reference'],pointer=q.pointer,raw_value=value)

def prepare():
 assert not (ROOT/'decision_results.jsonl').exists(),'Do not overwrite completed/live decisions.'
 runtime=read(WORK/'paper_experiments/configs/m1_core_full_v1/runtime_m1_core_full_v1.json')
 # Same established Main model and reasoning for all 12 independent sessions.
 provider=runtime['provider'];settings=request_settings(provider)
 schema=plan_schema(['diagnose','generate','initialize_control','physical_replay','mechanics'],decision_required=True,study={})
 tools=[dict(type='function',function=dict(name='evidence_read',description='Read whitelisted immutable historical raw evidence only. No reports or scientific execution.',parameters=provider_schema(EvidenceQuery.model_json_schema()))),
        dict(type='function',function=dict(name='research_plan',description='Record exactly one next proposed research action using the existing Core Plan/ResearchDecision and end this replay. No worker is executed.',parameters=provider_schema(schema)))]
 write(ROOT/'replay_configuration.json',dict(provider=provider,credentials_reference=runtime['credentials_reference'],
     tools=tools,system=SYSTEM,provider_budget_per_session=4,schema_owner=str(CORE/'tools/research/agent.py'),
     execution_entry='Minimal decision-only Provider replay; existing request_settings, Plan schema and original Reporter artifacts. No production Harness changes.',
     independent_review_model=None))
 extracts={n:read(WORK/f'paper_experiment_data/case_study_extracts/{n}_trace_extract.json') for n in ['m1','p3']}
 manifest=[];schedule=[];private=[]
 for index,(sid,name,ai,ri,case,note) in enumerate(SELECTION):
  x=extracts[name];store=Store(x['store']);math=x['analysis_results'][ai]
  rr=x['reports'][ri]['reference'];saved=store.artifact(rr);report=saved['report'];cards=report['results']
  assert saved['interpretation_status']=='available' and report['interpretations']
  assert [c['identity']['result']['reference'] for c in cards]==[math['reference']]
  candidate=math['value']['candidate'];cand=next(c for c in x['candidates'] if c['reference']==candidate)
  config=cand['configuration']
  facts=deepcopy(cards)
  # Deterministic cards contain no LLM interpretation. Remove duplicate F0 text
  # fields only when they are interpretation delivery metadata, not raw math.
  for card in facts:
   card.pop('authoritative_scientific_evidence',None)
  extra={}
  if name=='m1' and ai==0:
   sensitivity=math['value']['native_dynamics']['control_task_sensitivity']
   extra['recorded_control_sensitivity']=sensitivity
  # Preserve exact original parameters, task, limits and solver statuses; no recomputation.
  base=dict(snapshot_id=sid,source_study=x['study_id'],research_state='Settled immediately after this saved mathematical result and its matching Reporter report; no future decisions or final outcomes supplied.',
       current_candidate_reference=candidate,current_candidate_robot=config['robot'],current_policy=config['policy'],
       frozen_task=config['task'],frozen_protocols={k:v for k,v in x['frozen_protocols'].items() if k!='knowledge'},
       raw_deterministic_cards=facts,raw_mathematical_result_reference=math['reference'],
       additional_raw_facts=extra,raw_read_policy='Only referenced original evidence; no Reporter report reading, future results or historical final answer.')
  allowed=set(refs(base))|set(refs(report['interpretations']))
  all_report_ids={r['reference']['artifact_id'] for r in x['reports']};allowed-=all_report_ids
  snapshot=dict(snapshot_id=sid,source_store=x['store'],source_study=x['study_id'],base_context=base,
       readable_raw_references=sorted(allowed),reporter_interpretations=report['interpretations'],
       reused_report_reference=rr,category=case,category_fit=note)
  # Match historical Reporter accounting through its actual completion event.
  completed=[]
  for e in x['event_index']:
   if e['kind']=='reporter_completed':
    event=store.artifact(e['outputs'][0])
    if event.get('report_reference')==rr:completed.append(event)
  assert len(completed)==1
  reqid=completed[0]['provider_request'];usage=[u for u in x['usage_deduplicated'] if u['request_id']==reqid]
  if not usage:usage=[u for u in x['usage'] if u['request_id']==reqid]
  snapshot['historical_reporter_usage']=usage[0] if usage else None
  write(ROOT/f'snapshots/{sid}.json',snapshot)
  write(ROOT/f'reporter_reports/{sid}.json',dict(source_store=x['store'],source_report_reference=rr,
       exactly_matching_math_reference=math['reference'],reused=True,new_provider_requests=0,
       original_saved_report=saved,historical_usage=snapshot['historical_reporter_usage']))
  manifest.append(dict(snapshot_id=sid,task=name.upper(),case=case,category_fit=note,source_extract=f'paper_experiment_data/case_study_extracts/{name}_trace_extract.json',
       source_store=x['store'],source_study=x['study_id'],research_status=math['value'].get('status'),candidate=candidate['artifact_id'],
       mathematical_evidence=math['reference']['artifact_id'],physical_evidence=json.dumps([c['identity']['result'] for c in cards]),
       physical_evidence_scope='Recorded native mathematics rollouts/finite-time observations; independent physical acceptance not supplied where absent.',
       reporter_reference=rr['artifact_id'],reporter_reused=True,source_implementation=math['value'].get('implementation')))
  order=['OFF','ON'] if index%2==0 else ['ON','OFF']
  # Balanced anonymous label assignment, fixed before observing any decisions.
  amap={'OFF':'A','ON':'B'} if index in [0,3,4] else {'OFF':'B','ON':'A'}
  for condition in order:
   session=str(uuid.uuid4());schedule.append(dict(snapshot_id=sid,condition=condition,session_id=session,ordinal=len(schedule)+1))
   private.append(dict(snapshot_id=sid,anonymous_label=amap[condition],condition=condition,session_id=session))
 rows_csv(ROOT/'snapshot_manifest.csv',manifest);write(ROOT/'execution_schedule.json',schedule);write(ROOT/'private_condition_key.json',private)
 (ROOT/'protocol.md').write_text('''# Reporter ON/OFF 决策回放协议

本次为六个历史边界的成对决策实验，不运行完整 Study、数学求解、结构搜索或物理 Worker。M1/P3 各 A/B/C；分类的近似匹配及限制见 snapshot_manifest.csv。类别不是对决策的预评分。

沿用已有 Main gpt-5.6-sol、medium 及已配置 account3 Gateway；十二次请求配置相同，每次独立 UUID Session，最多四次 Provider 请求，形成第一份合法 Core Plan/ResearchDecision 后立即停止。顺序在每对间交替，匿名 A/B 分配事先固定。前一 Session 的输出不进入后一 Session。

OFF/ON 的基础 JSON、候选、冻结任务、全部原始事实、梯度/有限对照数值、单位/归一化、数值状态、原物理观测、原始证据权限、工具 Schema 和预算完全相同。ON 只附加匹配历史 Reporter 的 interpretations，OFF 不交付任何 Reporter prose/报告读取权限。六份报告均复用，保留原报告和实际历史 Provider 用量。既有程序生成的确定性 ResultCard 属于两组共同原始事实层，绝不把其单独当成 Reporter ON 处理。

只提供 evidence_read 和既有 research_plan。前者只读本快照原始 EvidenceRef；后者仅记录准备执行的请求，不调用 Core dispatch 或科研 Worker。schema 来自 Core agent.plan_schema 与 EvidenceQuery。没有现成的独立决策回放入口，因此增加此最小数据/请求脚本；未重构 Main、Reporter 或 Harness，未创建新 Planner/Agent/记忆系统。

历史结果边界包括本次数学结果及对应报告，不包含未来决策、最终成功或历史最终答案。报告中出现的原始科学来源以相同权限供两组读取。缺失信息保持未知，不补算数学或物理证据。上下文不因条件进行不同裁剪。

主要终点：五个 0–4 指标等权平均。独立盲评配置未找到，按任务允许路径交付人工评分入口，未评分保持空值，不由执行者伪造质量分数。评审只获相同事实和匿名 Plan，不获 ON/OFF 标签、报告或成本。条件映射仅置于 blind_review 目录外。

成本区分本次实际 Main/Reporter 用量与复用报告的历史生成成本；ON 输入已经包含报告阅读 Token。本次 Reporter 生成成本为零，另列历史首次生成的完整成本，避免宣称 Reporter 生成免费。六组不能支持充分统计显著性或机器人任务成功率推论。只读原始引用存在率属于程序核对，语义引用准确性和无支持结论须盲评，不填假分。
''',encoding='utf8')
 print(json.dumps(dict(status='prepared',snapshots=6,sessions=12,reused_reports=6,provider=settings,base_context_bytes={s[0]:len(json.dumps(read(ROOT/f'snapshots/{s[0]}.json')['base_context']).encode()) for s in SELECTION})),flush=True)

def run(text_only=False,resume_rejected=False):
 cfg=read(ROOT/'replay_configuration.json');provider=cfg['provider'];key=credential(provider,cfg['credentials_reference'])
 schedule=read(ROOT/'execution_schedule.json');result_path=ROOT/'decision_results.jsonl'
 done={r['session_id'] for r in [json.loads(line) for line in result_path.read_text(encoding='utf8').splitlines()]} if result_path.exists() else set()
 if text_only:
  # Current gateway accepts text only; Core tool schemas/Plan remain unchanged.
  # The same serialization and unexposed default reasoning apply to both conditions.
  cfg['system']+='\nTransport: Return ONLY JSON {"tool":"research_plan","arguments":<Core Plan>} or {"tool":"evidence_read","arguments":<Core EvidenceQuery>}. No markdown fences or other text. These are the exact tool schemas:\n'+json.dumps(cfg['tools'],separators=(',',':'))
 with httpx.Client(timeout=provider['timeout_s'],follow_redirects=False,trust_env=False) as client:
  for item in schedule:
   if item['session_id'] in done:continue
   snapshot=read(ROOT/f"snapshots/{item['snapshot_id']}.json");folder=ROOT/'sessions'/item['session_id'];folder.mkdir(parents=True,exist_ok=True)
   old=read(folder/'result.json') if resume_rejected and (folder/'result.json').exists() else None
   if any(folder.glob('request_*.json')) and not old:raise RuntimeError('UNKNOWN/PARTIAL SESSION MUST NOT BE AUTOMATICALLY RETRIED: '+item['session_id'])
   if old:
    assert len(old['requests'])==1 and old['requests'][0].get('http_status')==400
    assert read(folder/'response_1.txt')['error']['code']=='unsupported_parameter'
   messages=[dict(role='system',content=cfg['system']),dict(role='user',content=json.dumps(snapshot['base_context'],separators=(',',':')))]
   if item['condition']=='ON':messages[-1]['content']+='\n'+json.dumps(dict(supplemental_scientific_interpretations=snapshot['reporter_interpretations']),separators=(',',':'))
   write(folder/'session.json',dict(**item,source_study=snapshot['source_study'],new_study_created=False,scientific_execution_allowed=False))
   record=dict(**item,status='no_valid_decision',decision=None,requests=deepcopy(old['requests']) if old else [],evidence_reads=[],errors=deepcopy(old['errors']) if old else [],
       effective_reasoning='gateway_default_not_exposed' if text_only else provider['reasoning'],decision_transport='text_serialized_existing_Core_tool_schema' if text_only else 'native_function_call');started=time.perf_counter()
   print(json.dumps(dict(status='session_started',**item)),flush=True)
   for turn in range(len(record['requests'])+1,5):
    wire=dict(model=provider['model'],messages=messages,stream=False) if text_only else dict(**request_settings(provider),messages=messages,tools=cfg['tools'],tool_choice='auto')
    if len(json.dumps(wire).encode())>provider['model_capabilities']['max_request_bytes']:raise RuntimeError('CAPACITY_EXCEEDED_BEFORE_SEND')
    write(folder/f'request_{turn}.json',wire);t=time.perf_counter();outcome=dict(turn=turn,sent_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    try:
     response=client.post(provider['base_url'].rstrip('/')+'/chat/completions',json=wire,headers=dict(Authorization='Bearer '+key))
     (folder/f'response_{turn}.txt').write_text(response.text,encoding='utf8');outcome.update(http_status=response.status_code,wall_s=time.perf_counter()-t)
     response.raise_for_status();body=response.json();outcome.update(usage=body.get('usage'),model=body.get('model'),response_id=body.get('id'))
     message=body['choices'][0]['message'];messages.append(message);calls=message.get('tool_calls') or []
     if text_only:
      content=message['content'].strip()
      if content.startswith('```'):content='\n'.join(content.splitlines()[1:-1])
      parsed=json.loads(content)
      if 'action' in parsed:parsed=dict(tool='research_plan',arguments=parsed)
      calls=[dict(id='text-call-'+str(turn),function=dict(name=parsed['tool'],arguments=json.dumps(parsed['arguments'])))]
     for call in calls:
      name=call['function']['name'];args=json.loads(call['function']['arguments'])
      if name=='research_plan':
       jsonschema.Draft202012Validator(cfg['tools'][1]['function']['parameters']).validate(args);Plan.model_validate(args)
       assert args.get('decision') is not None
       record.update(status='completed',decision=args,decision_tool_call=call)
       break
      elif name=='evidence_read':
       try:value=raw_reader(snapshot,args)
       except Exception as exc:value=dict(error=type(exc).__name__+': '+str(exc))
       record['evidence_reads'].append(dict(request=args,response=value))
       messages.append(dict(role='user',content='evidence_read result: '+json.dumps(value,separators=(',',':'))) if text_only else dict(role='tool',tool_call_id=call['id'],content=json.dumps(value,separators=(',',':'))))
      else:raise ValueError('UNAVAILABLE_TOOL: '+name)
     if not calls:messages.append(dict(role='user',content='Submit one concrete next decision with research_plan now. No research execution is permitted.'))
    except (httpx.HTTPError,KeyError) as exc:
     record['errors'].append(str(exc));outcome['error']=str(exc);record['requests'].append(outcome);break
    except Exception as exc:
     record['errors'].append(str(exc));outcome['error']=str(exc)
     # A returned validation error is known, not an automatic retry of an unknown send.
     for call in calls if 'calls' in locals() else []:
      feedback=json.dumps(dict(validation_error=str(exc),remaining_provider_requests=4-turn))
      messages.append(dict(role='user',content=feedback) if text_only else dict(role='tool',tool_call_id=call['id'],content=feedback))
    record['requests'].append(outcome);write(folder/'progress.json',record)
    if record['status']=='completed':break
   record.update(wall_s=time.perf_counter()-started+(old['wall_s'] if old else 0),main_provider_requests=len(record['requests']),main_inference_responses=sum(r.get('http_status')==200 for r in record['requests']),new_reporter_provider_requests=0,
      new_mathematical_solves=0,new_physics_runs=0,new_candidates=0)
   used=[r.get('usage') for r in record['requests']]
   record['usage']={key:sum(u.get(key,0) for u in used if u is not None) if all(u is not None for u in used) else None for key in ['prompt_tokens','completion_tokens','total_tokens']}
   write(folder/'result.json',record)
   with result_path.open('a',encoding='utf8') as stream:stream.write(json.dumps(record,ensure_ascii=False)+'\n')
   print(json.dumps(dict(status=record['status'],snapshot=item['snapshot_id'],condition=item['condition'],requests=len(record['requests']),tokens=record['usage'],wall_s=record['wall_s'])),flush=True)
   if record['status']!='completed':raise RuntimeError('Stop cohort after first unresolved session; no further sends.')

def resume_text():
 # All initial 400s were rejected by convertRequest before requirePlan/upstream.
 # They remain counted in the same Session's four-send budget and fully archived.
 rejection=ROOT/'transport_rejections.jsonl'
 if not rejection.exists():
  current=ROOT/'decision_results.jsonl';rejected=[json.loads(line) for line in current.read_text(encoding='utf8').splitlines()]
  assert len(rejected)==12 and all(r['requests'][0].get('http_status')==400 for r in rejected)
  current.rename(rejection)
  for r in rejected:write(ROOT/'sessions'/r['session_id']/'result_before_transport_fix.json',r)
  cfg=read(ROOT/'replay_configuration.json');write(ROOT/'replay_configuration_before_transport_fix.json',cfg)
  cfg.update(effective_reasoning='gateway_default_not_exposed',transport='text_only_existing_gateway',
      initial_400s_counted=True,upstream_for_initial_400s=False,
      original_explicit_medium_not_supported=True,usage_reporting='Not exposed by current gateway; unknown remains null.')
  write(ROOT/'replay_configuration.json',cfg)
  # Latest user steering prioritizes the three complete P3 Agent decision nodes.
  schedule=read(ROOT/'execution_schedule.json');write(ROOT/'execution_schedule_before_p3_priority.json',schedule)
  schedule.sort(key=lambda row:(not row['snapshot_id'].startswith('P3'),row['ordinal']))
  write(ROOT/'execution_schedule.json',schedule)
  with (ROOT/'protocol.md').open('a',encoding='utf8') as stream:
   stream.write('\n## 执行前传输修正\n\n当前 Gateway 与历史 v8 接口不同，只支持 model/messages/stream:false。首批十二次请求都在 convertRequest 阶段因不支持 tools/reasoning_effort 返回 400，未进入 requirePlan 或上游推理。原请求/拒绝全部保留在 transport_rejections.jsonl 与 Session 文件，计入各自最多四次发送。此前没有形成任何 Main 决策。其后所有条件统一改用相同模型 gpt-5.6-sol、相同网关默认推理设置（具体档位不暴露，不能声称 medium）、完全相同的文本化 Core 工具 Schema。返回的 Plan/EvidenceQuery 用原 Schema 校验，未新增决策类型或改动生产 Harness。当前网关不返回 usage，真实 I/O Token 保持未知，不能据此声称额外 Token 成本为零。按用户补充要求优先完成 P3 三个节点。\n')
 run(text_only=True,resume_rejected=True)

if __name__=='__main__':
 {'prepare':prepare,'run':run,'resume_text':resume_text}[sys.argv[1]]()
