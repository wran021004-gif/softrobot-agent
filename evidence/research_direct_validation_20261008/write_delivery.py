"""Local deterministic checks and summary; no credential/provider/scientific calls."""
from pathlib import Path
import hashlib
import json
import sys
from datetime import datetime
from tools.state_io import read,atomic_json,digest
from tools.context_assembly import _no_secrets
from tools.research_validation_gate import generate
from tools import research_direct_validation as direct

OUT=Path(__file__).resolve().parent;ROOT=direct.ROOT
OFFLINE=ROOT/'evidence/research_direct_validation_20261008_offline'
manifest=read(OUT/'validation_manifest.json')
assert all(direct.sha(ROOT/p)==h for p,h in manifest['relevant_files_sha256'].items())
assert direct.history()==read(OUT/'historical_before.json')
for directory in (OUT,OFFLINE):
    for p in directory.glob('*.json'):_no_secrets(read(p))
if sys.argv[-1]=='check':
    assert not (OUT/'launch.json').exists()
    checks=read(OFFLINE/'attempt_04.json');assert checks['tests']==5 and not checks['failures'] and not checks['errors']
    plan=read(OUT/'direct_plan.json');cfg=read(OUT/'frozen_configuration.json')
    assert digest(plan)==manifest['plan_identity'] and digest(cfg)==manifest['configuration_identity']
    assert plan['principal_budget']['tool_calls']+len(plan['principal_inspections'])==8
    assert cfg['policy']['model']['base_url']=='https://api.deepseek.com'
    assert set(cfg['policy']['allowed_tools'])=={'research.investigate','research.investigation_status','research.investigation_read','research.investigation_disposition'}
    atomic_json(OUT/'launch_review.json',dict(passed=True,code=manifest['code_commit'],offline_identity=digest(checks),
        source_case=manifest['source'],node_count=3,model_attempt_ceiling=18,node_model_ceiling=6,
        tool_ceiling=512,node_evidence_ceiling=8,combined_principal_evidence_ceiling=8,
        full_prepared_request_review=True,provider_attempts=0,credentials_loaded=False,repair_allowance_remaining=0,
        settings=dict(model='deepseek-flash',thinking='enabled',reasoning_effort='high',tool_choice='auto',max_tokens=3000),
        boundary='Direct only. No coordinator/science/polishing/retries/protocol corrections.'))
    print('DIRECT_LAUNCH_REVIEW_PASSED; no credentials or provider calls')
    raise SystemExit(0)

bundle=read(OUT/'direct_bundle.json');gate=generate(bundle)
nodes=bundle['state']['investigations'];artifacts=bundle['artifacts'];events=bundle['events']
reports={k:artifacts[n['result']['artifact_id']] for k,n in nodes.items() if n.get('result')}
readings={r['investigation_id']:dict(prefetch=r['initial_prefetch'],selected_original=r['investigator_selected_original_reads'],
    selected_directory=r['selected_directory_reads'],unmatched=r['unmatched_reads']) for r in gate['nodes']}
tokens=[artifacts[e['outputs'][0]['artifact_id']]['provider_usage'] for e in events if e['kind']=='investigation_token_accounting']
usage_totals={k:sum(u.get(k,0) for u in tokens if isinstance(u,dict)) for k in ('prompt_tokens','completion_tokens','total_tokens')}
intervals={}
for key,node in nodes.items():
    own=[e for e in events if e.get('request_id')=='investigation-'+key and e['kind'] in ('investigation_provider_attempt','investigation_provider_response')]
    intervals[key]=[dict(sequence=e['sequence'],kind=e['kind'],timestamp=e.get('timestamp')) for e in own]
pending=[dict(request_id=c['request_id'],status=c['status'],reserved=c['reserved']) for c in bundle['calls'] if c['status'] in ('running','unknown')]
summary=dict(活动=manifest['activity_id'],代码=manifest['code_commit'],历史来源=manifest['source'],
    结果=read(OUT/'direct_result.json') if (OUT/'direct_result.json').exists() else read(OUT/'application_failure.json'),
    确定性门禁=gate,调查者材料及追读=readings,原生报告=reports,
    主模型独立检查=bundle['state'].get('principal_investigation_reads',[]),主模型正式处置=gate['dispositions'],
    并行证据=intervals,并行说明='是否重叠依据事件时间核对；配置并发上限二不证明实际重叠。',
    费用=dict(真实供应商尝试=gate['accounting']['provider_attempts'],正常响应=gate['accounting']['provider_responses'],
        公共操作=sum(c['caller']!='investigation-dispatcher' for c in bundle['calls']),
        节点操作={k:n['usage'] for k,n in nodes.items()},已结算=gate['accounting']['charged'],
        项目账本=read(OUT/'direct_ledger.json'),未决预留=pending,供应商返回token=usage_totals,
        token记录完整=all(isinstance(u,dict) for u in tokens) and len(tokens)==gate['accounting']['provider_attempts'],
        供应商金额=None,估算说明='每次请求的字节/保守 token 估算在原始 token_accounting 记录中；不能代替返回 usage 或已知金额。'),
    失败记录={k:artifacts[n['failure_record']['artifact_id']] for k,n in nodes.items() if n.get('failure_record')},
    工程介入=read(OFFLINE/'verification.json')['repair'],应用收尾=read(OUT/'application_lifecycle.json'),
    旧状态=dict(文件及账本未改变=read(OUT/'historical_after.json')['unchanged'],原两次未知请求=2,旧未决模型单位=12,
        旧预留未迁移或释放=True,旧活动仍停止=True,旧原因及供应商费用='unknown'),
    边界='预先安排的两问题直接接口验证；不证明自主组织架构、研究效率、因果收益或机器人改善。无协调者/科学/第二版/润色调用。',
    后续='只有本轮逐项门禁通过后才建议另行授权有界协调调查；本轮不自动执行。失败时按原记录提出最小处理，零追加付费修正。')
_no_secrets(summary)
atomic_json(OUT/'delivery_summary.json',summary)
atomic_json(OUT/'direct_gate.json',gate)
inventory={p.relative_to(ROOT).as_posix():dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
    for d in (OUT,OFFLINE) for p in d.iterdir() if p.is_file() and p.name!='sha256_manifest.json'}
atomic_json(OUT/'sha256_manifest.json',inventory)
print(json.dumps(dict(gates=gate['gates'],passed=gate['passed'],attempts=gate['accounting']['provider_attempts'],
    tokens=usage_totals,pending=len(pending),old_unchanged=summary['旧状态']['文件及账本未改变'])))
