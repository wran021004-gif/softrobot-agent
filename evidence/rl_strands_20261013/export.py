"""Compact export of the one already-sealed real study; never launches work."""
import base64
from datetime import datetime
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools import research_core as core
from tools.platform_host import Host
from tools.rl import run

host=Host(ROOT/'runs/rl-strands-20261013','rl-strands-20261013',actor='unified-research')
s=core.state(host);assert s['research_status']=='stopped'
out=ROOT/'evidence/rl_strands_20261013';out.mkdir(exist_ok=True)
def save(name,value):core.atomic_json(out/name,value)
events=host.store.events(host.run_id)
tools=[dict(kind=e['kind'],sequence=e['sequence'],timestamp=e['timestamp'],value=host.store.artifact(e['outputs'][0]))
       for e in events if e['kind'] in ('model_original_tool_request','model_original_tool_feedback')]
save('tool_trace.json',tools)
provider=[]
for e in events:
    if e['kind']!='r3_request':continue
    metadata=host.store.artifact(e['outputs'][0])
    receptions=[host.store.artifact(v['outputs'][0]) for v in events if v['kind']=='r3_response' and v['request_id']==e['request_id']]
    reception=receptions[-1] if receptions else None
    provider.append(dict(request_id=e['request_id'],sequence=e['sequence'],timestamp=e['timestamp'],metadata=metadata,
        request=host.store.artifact(metadata['request']),reception=reception,
        raw_response_base64=base64.b64encode(host.store.artifact(reception['body'],raw=True)).decode() if reception else None))
with (out/'provider_trace.jsonl.gz').open('wb') as stream:
    with gzip.GzipFile(fileobj=stream,mode='wb',mtime=0) as archive:
        for p in provider:archive.write((json.dumps(p,ensure_ascii=False,separators=(',',':'))+'\n').encode())
save('provider_index.json',[{k:p[k] for k in ('request_id','sequence','timestamp','metadata','reception')} for p in provider])
with host.store.connect(True) as db:save('calls.json',[dict(r) for r in db.execute('SELECT * FROM calls ORDER BY rowid')])
save('ledger.json',host.store.remaining())
run_id,entry=next(iter(s['rl_runs'].items()))
cfg=host.store.artifact(entry['configuration']);candidate=host.store.artifact(entry['candidate'])
save('candidate.json',dict(reference=entry['candidate'],candidate_id=candidate['candidate_id'],identity=candidate['identity'],
    parameters=candidate['parameters'],resolved_parameters=candidate['resolved_parameters'],provenance=candidate['provenance'],
    scientific_configuration=candidate['scientific_configuration'],profile_identity=candidate['profile_identity'],
    historical_lengths_m=[.15758113296570092,.11241886703429908],physical_lengths_m=candidate['resolved_parameters']['lengths_m']))
effective=json.loads(json.dumps(cfg));xml=effective['candidate'].pop('xml')
effective['candidate'].update(xml_bytes=len(xml.encode()),xml_runtime_path=str(run.run_path(run_id)/'config.json')+'#/candidate/xml')
save('effective_configuration.json',dict(immutable_reference=entry['configuration'],config_sha256=hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest(),effective=effective,
    requested_values_reached_worker_ppo=False,reason='Worker failed importing Torch before WorkerContext or PPO creation'))
status=run.read_json(run.run_path(run_id)/'state.json');save('run_status.json',status)
evaluation=host.store.artifact(s['rl_evaluations'][0]);save('evaluation_unavailable.json',dict(reference=s['rl_evaluations'][0],**evaluation))
decision=host.store.artifact(s['final_disposition']);save('model_decision.json',dict(reference=s['final_disposition'],**decision))
save('evidence_reads.json',[t for t in tools if t['kind']=='model_original_tool_request' and t['value']['tool_use']['name']=='evidence_read'])
(out/'worker_failure.txt').write_text((run.run_path(run_id)/'worker.log').read_text(encoding='gbk'),encoding='utf8')
stop_event=next(e for e in events if e['kind']=='original_research_plan' and e['outputs'][0]==s['final_disposition'])
ended=datetime.fromisoformat(stop_event['timestamp']).timestamp()
elapsed=ended-s['live_started_unix']
summary=dict(study_id=host.run_id,real_provider='https://api.deepseek.com',model='deepseek-flash',
    initial_implementation=s['core_repairs'][0]['previous_commit'],repaired_implementation=s['freeze'],
    started_unix=s['live_started_unix'],closed_unix=ended,live_elapsed_s=elapsed,
    ceilings=s['spec']['budgets'],rl_ceilings=s['spec']['rl_limits'],provider_requests=len(provider),
    public_operations=host.store.remaining()['used']['tool_calls'],training_runs=1,training_allocation=entry['allocation'],
    attempted_training_actions=status['consumed']['attempted_actions'],completed_training_actions=status['consumed']['completed_actions'],
    attempted_training_physics_steps=status['consumed']['attempted_physics_steps'],optimization_batches=0,optimization_epochs=0,
    training_active_seconds_conservatively_charged=status['consumed']['active_seconds'],training_active_seconds_durable_lower_bound=0,
    actual_training_active_seconds='unknown; worker failed before timing state publication',uncertain_consumption=True,
    independent_evaluation_episodes=0,evaluation_public_requests=sum(t['value']['tool_use']['name']=='research_rl' and t['value']['tool_use']['input'].get('operation')=='evaluate' for t in tools if t['kind']=='model_original_tool_request'),
    evaluation_physics_steps=0,diagnostic_replays=0,diagnostic_physics_steps=0,task_performance='unmeasured',
    interface_acceptance=False,next_step=decision['original_plan']['next_step'],read_evidence=s['rl_evidence_reads'],
    acceptance_requirements=[
        dict(requirement='Real Strands model selects new candidate and RL configuration',status='partial',evidence=['candidate.json','effective_configuration.json','tool_trace.json'],limitation='Candidate/mode/overrides chosen and frozen; worker did not reach PPO/reward execution'),
        dict(requirement='Start short training with at least two complete PPO batches',status='failed',evidence=['run_status.json','worker_failure.txt'],limitation='One launch failed before sampling; zero optimizations and no checkpoint'),
        dict(requirement='Query actual progress and cumulative consumption',status='passed',evidence=['tool_trace.json','run_status.json']),
        dict(requirement='Independently evaluate saved policy from frozen candidate/task',status='failed',evidence=['evaluation_unavailable.json'],limitation='No saved checkpoint; zero evaluation episodes; no performance metrics'),
        dict(requirement='Public evidence read and evidence-based next-step decision',status='partial',evidence=['evidence_reads.json','model_decision.json'],limitation='Model read unavailable-evaluation failure evidence and recommended adjust_training; no policy-evaluation result exists')],
    focused_checks=dict(rl_runtime=28,research_integration=4,passed=True,training_campaigns=0,physical_replays=0),
    limitations=['Full five-part interface acceptance failed','Task performance unmeasured; not a task-threshold failure or design infeasibility finding','Environment repair verified by import, focused fixture and untrained PPO construction, not a second live training run','No compatible failure capture, no replay','Current bridge rejects external XML assets and supports selected hinge/ideal-tension reach-and-hold only','Original cooperative active-time overrun recording remains; this run retained uncertain startup charge','Model raw interpretation is preserved; design metadata pretension is not an RL initializer applied tension'])
assert len(provider)==s['pilot']['live_model_requests']<=24
assert summary['public_operations']<=60 and elapsed<=900
assert status['consumed']['active_seconds']<=120
assert len(s['rl_runs'])==1 and not status['workers']
save('summary.json',summary)
completion=f'''本次代码集成与聚焦验证已完成，真实模型验收未全部通过。唯一训练进程在 Torch 导入阶段因 Windows 服务提供程序错误退出，未采样、未优化、未生成 checkpoint；因此独立策略评估未执行，任务性能未测量。

模型通过现有 Strands 公开工具生成候选 `{candidate['candidate_id']}`，`d=0.5`，长度 `0.16275 / 0.10725 m`；旧 RL 机器人为 `0.15758113296570092 / 0.11241886703429908 m`。结构参数与编译后的 XML 身份均改变。任务目标、零关节初态、0.35 s 时长、0.01 s 控制周期、0.0005 s 物理步、含端点的 .30–.35 s holding 窗口与 .01 m/.02 m/s 阈值保留。

模型选择 direct，无兼容 residual reference；PPO `n_steps=128, batch_size=64, n_epochs=4, learning_rate=0.0005, gamma=0.99`；holding-speed 奖励权重由 1 改为 2，其他奖励项保持默认。配置已保存，但本次 worker 未到达 PPO 与奖励计算，不宣称这些覆盖项已经通过真实训练验收。

累计消耗：{len(provider)} 次实际 provider 请求、{summary['public_operations']} 次公开工具操作，包含错误与修正；live study {elapsed:.3f} s。唯一训练 allocation 为 1024 动作/90 s，实际动作与物理步均 0，完成优化/epochs 均 0；启动时间未可靠写回，原账本保守计费 90 s（已知下界 0 s），未退款或重置。评估 episode、评估物理步、诊断回放均 0。另一次带不兼容 `failure` 字段的 evaluate 请求在 schema 层被拒绝，不是第二次评估 episode。

| 五项要求 | 结果 | 证据 |
|---|---|---|
| 真实模型生成新候选并配置 RL | 部分完成；配置选择/保存成功，真实 PPO 参数应用未验证 | [候选](candidate.json)、[有效配置](effective_configuration.json) |
| 启动短训练并完成至少两批优化 | 失败；零动作、无 checkpoint | [状态](run_status.json)、[worker 错误](worker_failure.txt) |
| 查询真实进度和累计成本 | 通过；公开终态查询保留保守计费 | [工具原始记录](tool_trace.json) |
| 独立评估保存策略 | 未完成；无保存策略，性能未测量 | [不可执行评估证据](evaluation_unavailable.json) |
| 明确读证据并作下一步决定 | 部分完成；读的是评估不可执行证据，非策略评估结果 | [读取记录](evidence_reads.json)、[模型决定](model_decision.json) |

模型明确读取失败证据 `{s['rl_evaluations'][0]['artifact_id']}`，选择 `adjust_training` 并通过 STOP 关闭当前 study，建议将来在健康 worker 上重试训练；本次没有执行第二次训练。其完整原话与不准确的早期解释均保留，未由开发者改写。事实校正：设计/数值参考的 0.2 N pretension 元数据不等于 RL 初态施加了 0.2 N 张力；RL 初态仍为任务冻结的零 qpos/qvel。

已修复桥接层枚举 Windows 环境变量时遗漏 `SystemRoot` 的具体缺陷。32 项聚焦检查通过，包括真实生成 XML 的加载、不同维度及无关 scene joint、张力符号/限幅、时间网格、奖励独立验收、重复 receipt/状态幂等、checkpoint 恢复，以及无训练的真实 PPO 构造和无凭据 Torch/asyncio 子进程导入。新增异常评估子进程测试保留未知消耗，不把未知成本伪装为零。没有运行全仓库测试、恢复 campaign、NMPC/BDF/MATLAB 或物理诊断 replay。

桥接实现复用原 Store/receipt、候选验证、XML 生成链和 RL 命令边界。`strands_pilot.py` 未改；`strands_pilot_r3.py` 仅增加 opt-in 的剩余时间预留，避免原固定 600 s 预留阻断 900 s study 后期请求。研究反馈 helper 添加 scoped RL 事实，避免数值实验 confirmation 逻辑误处理 RL。

完整非秘密 provider 请求、原始响应字节与接收 metadata 在 [压缩原始记录](provider_trace.jsonl.gz)，索引见 [provider_index.json](provider_index.json)。[共享账本](ledger.json)、[操作 receipts](calls.json)、[机器摘要](summary.json) 保留所有消耗。大 XML 和运行目录留在既有 `runs/` 存储；有效配置证据给出 SHA 与 runtime 路径。

剩余限制：五项接口验收未全部通过；短训练、保存 checkpoint、独立评估与真实 PPO/奖励覆盖应用仍缺实证。仅支持选定 hinge、ideal-tension、reach-and-hold；外部 XML assets 明确拒绝。原运行时协作式 active-time 超限记录机制仍保留。没有机器人不可行性、鲁棒性、泛化、数值根因已解决或完整自主研究结论。交付分支为 `feat/rl-control-pilot`，完整推送 SHA 由最终答复和 Git remote 校验给出。
'''
(out/'completion.md').write_text(completion,encoding='utf8')
manifest={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in out.iterdir() if p.is_file() and p.name!='manifest.json'}
save('manifest.json',manifest)
print(json.dumps({k:summary[k] for k in ('provider_requests','public_operations','live_elapsed_s','task_performance','interface_acceptance','next_step')},ensure_ascii=False))
print(json.dumps({name:item['bytes'] for name,item in manifest.items()}))
