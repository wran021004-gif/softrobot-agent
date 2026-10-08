"""Deterministic local review and summary; never loads credentials or transport."""
from pathlib import Path
import hashlib
import json
import sys
from tools.state_io import read, atomic_json, digest
from tools.context_assembly import _no_secrets
from tools import research_single_validation as single

OUT=Path(__file__).resolve().parent
ROOT=single.ROOT
OFFLINE=ROOT/'evidence/research_request_compatibility_20261008_offline'
manifest=read(OUT/'validation_manifest.json')
config=read(OUT/'frozen_configuration.json')
prepared=read(OUT/'prepared_request.json')
checks=read(OFFLINE/'attempt_03.json')
assert checks['tests']==8 and not checks['failures'] and not checks['errors']
assert digest(config)==manifest['configuration_identity']
assert all(single.sha(ROOT/p)==h for p,h in manifest['relevant_files_sha256'].items())
assert prepared['tool_choice']=='auto' and prepared['model']=='deepseek-flash'
assert prepared['thinking']=={'type':config['policy']['model']['thinking']}
assert prepared.get('reasoning_effort')==config['policy']['model'].get('reasoning_effort')
assert config['policy']['model']['base_url']=='https://api.deepseek.com'
assert config['policy']['budget']==single.PROJECT
assert read(OUT/'order.json')['budget']==single.NODE
assert single.old_review()==read(OUT/'historical_before.json')
for directory in (OUT,OFFLINE):
    for p in directory.glob('*.json'):_no_secrets(read(p))
if sys.argv[-1]=='check':
    assert not (OUT/'launch.json').exists()
    atomic_json(OUT/'launch_review.json',dict(passed=True,code_commit=manifest['code_commit'],
        offline_result=digest(checks),prepared_request_identity=digest(prepared),
        inspected='Complete prepared request, approved resolved model configuration, source page/directory and budgets',
        actual_send_requires_same_frozen_code=True,provider_attempts=0,
        request_settings={k:prepared.get(k) for k in ('model','thinking','reasoning_effort','tool_choice','max_tokens')},
        retries=0,protocol_corrections=0,extra_reports=0,science=0,credentials_loaded=False))
    print('LAUNCH_REVIEW_PASSED; no credentials or requests')
    raise SystemExit(0)

bundle=read(OUT/'bundle.json');gate=read(OUT/'gate.json')
assert digest(bundle)==gate['bundle_identity'] and gate['limits_passed']
assert gate['compatible_actual_requests'] and gate['recorded_attempts']==1
assert bundle['session_status']=='stopped' and read(OUT/'historical_after.json')['unchanged']
node=bundle['state']['investigations']['single-saved-fact'];progress=node['progress']
calls=bundle['calls'];node_call=next(c for c in calls if c['caller']=='investigation-dispatcher')
pending=[dict(request_id=c['request_id'],status=c['status'],reserved=c['reserved'])
    for c in calls if c['charged'] is None]
failure=bundle['artifacts'][node['failure_record']['artifact_id']] if node.get('failure_record') else None
tokens=[bundle['artifacts'][e['outputs'][0]['artifact_id']]['provider_usage']
    for e in bundle['events'] if e['kind']=='investigation_token_accounting']
wire=bundle['artifacts'][next(e for e in bundle['events'] if e['kind']=='investigation_provider_attempt')['outputs'][0]['artifact_id']]['payload']
report=read(OUT/'delivery_report.json')['有效报告']
summary=dict(
    结果=node['status'],单请求报告通过=gate['single_report_passed'],活动=manifest['activity_id'],
    冻结代码=manifest['code_commit'],
    代码身份说明='启动时生产代码已提交并以文件哈希冻结；进度中 code_worktree_dirty=true 包含本轮尚未提交的新证据目录，不表示使用了未冻结的生产代码。',
    请求设置={k:wire.get(k) for k in ('model','thinking','reasoning_effort','tool_choice','max_tokens')},
    兼容性='实际请求消除了 thinking 与 required/指定工具的不兼容组合；保留批准配置和原生返回校验。历史 HTTP 400 原文缺失，不能确认唯一原因。',
    接收与保存={k:progress.get(k) for k in ('transport_attempted','response_received','response_body_received',
        'http_status','provider_request_id','response_saved','valid_report','report_saved','settlement_completed','actual_usage_known')},
    失败证据=failure,有效原生报告=report,
    费用=dict(实际供应商尝试=gate['recorded_attempts'],公共操作=gate['public_operation_count'],
        初始预取=gate['successful_prefetch_count'],已完成追读=gate['followup_read_count'],拒绝追读=gate['rejected_followup_count'],
        节点原预留=node_call['reserved'],节点结算=node_call['charged'],
        项目账本=read(OUT/'ledger.json'),本活动未决预留=pending,
        供应商返回token记录=tokens,供应商金额=None,
        说明='本地模型单位和工具单位是项目账本成本，不等于供应商 token 或金额。仅以供应商返回 usage 记录 token；缺失或金额不明继续未知。'),
    应用收尾=read(OUT/'application_lifecycle.json'),
    历史=dict(原两次未知请求=2,原模型未决预留单位=12,原活动继续停止=True,原文件和账本未改变=True,
        上一次单请求='原 HTTP 400 接收及失败结算记录保持原样；错误原文不能恢复。',
        未知=['原两次请求到达情况、结果、原因、token 和供应商费用','本次供应商金额'],
        说明='本次结果不释放、迁移或重新激活旧预留。12 是旧未决模型单位，不是十二次实际请求。'),
    验证=dict(离线8项通过=True,失败检查=['offline/attempt_01.json','offline/attempt_02.json'],
        按需追读='unverified; only initial prefetch',principal_inspection=0,formal_disposition=0,
        协调调查='unverified',主线三全部通过=False,科学操作=0,机器人改善验证=False,第二版开发=False),
    人工可核查摘要='三项事实的来源及数值与唯一预取页一致：passed=false，max_error_m=0.06672099201814737，max_speed_m_s=0.20679063000945364。解释只比较页内限值，不构成新科学结论。',
    后续建议=('另行授权有界完整直接调查，独立预算与停止条件，显式验收调查者选择的追读、原始来源核查和正式处置；本轮不启动。'
        if gate['single_report_passed'] else '只依据本次明确失败字段做最小离线处理；若缺少结果证据则保持未确认与预留。任何新付费验证均需新授权，不重发本节点。'),
    发布=dict(repository='https://github.com/wran021004-gif/softrobot-agent.git',branch='feat/gvs-dynamics',
        scope='兼容性与安全错误字段修复、针对性检查、现有能力文档追加及本轮非秘密证据；普通推送并核对远端 SHA。'))
_no_secrets(summary)
atomic_json(OUT/'delivery_summary.json',summary)
inventory={p.relative_to(ROOT).as_posix():dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
    for d in (OUT,OFFLINE) for p in sorted(d.iterdir()) if p.is_file() and p.name!='sha256_manifest.json'}
atomic_json(OUT/'sha256_manifest.json',inventory)
print(json.dumps(dict(status=node['status'],single_report_passed=gate['single_report_passed'],
    provider_attempts=gate['recorded_attempts'],http_status=progress.get('http_status'),
    settled=progress.get('settlement_completed'),pending=len(pending),stopped=True,historical_unchanged=True)))
