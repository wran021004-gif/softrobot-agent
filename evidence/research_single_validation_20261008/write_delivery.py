"""Deterministic offline summary of sealed records; no provider/credential calls."""
from pathlib import Path
import hashlib
import json
from tools.state_io import read, atomic_json, digest
from tools.context_assembly import _no_secrets

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
bundle=read(OUT/'bundle.json')
gate=read(OUT/'gate.json')
assert digest(bundle)==gate['bundle_identity']
node=bundle['state']['investigations']['single-saved-fact']
failure=bundle['artifacts'][node['failure_record']['artifact_id']]
progress=node['progress']
attempts=[e for e in bundle['events'] if e['kind']=='investigation_provider_attempt']
actual=bundle['artifacts'][attempts[0]['outputs'][0]['artifact_id']]
node_call=next(c for c in bundle['calls'] if c['caller']=='investigation-dispatcher')
public=[c for c in bundle['calls'] if c['caller']!='investigation-dispatcher']
assert len(attempts)==1 and len(public)==2
assert bundle['session_status']=='stopped'
assert failure['details']['http_status']==400 and failure['details']['category']=='http'
assert progress['response_received'] is True and progress['response_body_received'] is True
assert node_call['status']=='failed' and progress['settlement_completed'] is True
assert read(OUT/'historical_after.json')['unchanged']
assert read(OUT/'application_lifecycle.json')['thread_completed_before_close']
offline=ROOT/'evidence/research_single_validation_20261008_offline'
checks=[dict(path=p.relative_to(ROOT).as_posix(),result=read(p)) for p in sorted(offline.glob('attempt_*.json'))]
assert checks[-1]['result']['tests']==3 and not checks[-1]['result']['failures'] and not checks[-1]['result']['errors']
summary=dict(
    结果='单请求真实公共验证失败：收到 HTTP 400 拒绝。失败记录与结算路径可核查；未得到有效调查报告。',
    活动=bundle['project']['project_id'],起点=read(OUT/'validation_manifest.json')['code_commit'],
    本地真正尝试传输=True,依据='一次 investigation_provider_attempt、transport_callable_invocations=1，原始 HTTPError 与 HTTP 400 接收事实相互支持。',
    响应=dict(响应头已接收=True,错误正文已完整读取=True,正文已保存=False,有效报告=False,
        脱敏失败证据已保存=True,供应商请求编号=None,
        说明='response_received 与 response_body_received 均为 true。正常 completion 响应计数 received_responses=0 不表示没有收到 HTTP 错误响应。错误正文未归档，不能从当前封存证据还原其详细拒绝内容。'),
    失败=dict(环节=failure['progress']['stage'],异常包装类别=failure['exception_type'],
        原始异常类别=failure['details']['exception_type'],已有脱敏分类=failure['details']['category'],
        HTTP状态=failure['details']['http_status'],脱敏消息=failure['details']['reason_message'],
        发生时间=failure['timestamp'],失败记录耗时秒=failure['elapsed_s'],
        本地请求编号=failure['request_id'],执行编号=failure['execution_id'],
        原失败证据=node['failure_record'],持久化失败=failure['persistence_failed']),
    费用与边界=dict(供应商实际尝试=1,公共提交=1,公共状态收集=1,初始预取=1,额外读取=0,
        共用项目工具使用=read(OUT/'ledger.json')['used']['tool_calls'],
        节点原预留=node_call['reserved'],节点已结算=node_call['charged'],
        总账本占用=read(OUT/'ledger.json')['used'],本活动未决预留=0,
        实际供应商token=None,实际供应商费用=None,
        说明='本地模型调用单位按一次已确认尝试结算；这不是已知 token 数或供应商收费金额。错误分类和 HTTP 拒绝不证明没有费用。',
        节点总时限秒=180,活动总时限秒=240,返回上限字节=16384,
        实际请求输出限制=actual['payload']['max_tokens'],实际请求测量=actual['measurement'],
        请求字节估算不等于服务端接收或实际token=True),
    收尾=read(OUT/'application_lifecycle.json'),
    历史=dict(原活动继续停止=True,原封存文件与账本未改变=True,
        原尝试数=2,原保存响应=0,原未决模型单位=12,
        原两项预留未转移或释放=True,
        说明='本次 HTTP 400 不能归因为旧两次请求。旧请求原因、到达情况、实际用量和费用仍未知。'),
    验证边界=dict(离线最终检查=checks[-1]['result']['tests'],早期失败记录=checks[0]['path'],
        离线夹具修正='首轮将收尾压缩到两秒，公共准备尚未结束便停止；改用五秒起的间隔和四十秒收尾，并在清理前等待线程退出。未缩短真实入口的活动期限。',
        外部接收方='https://api.deepseek.com',模型='deepseek-flash',既有配置未变=True,
        自动重试=0,协议纠正请求=0,额外模型报告=0,额外探测=0,
        后端操作=0,工作进程操作=0,科学操作=0,第二版开发=False,
        真实有效调查报告=False,按需追读='unverified',协调调查='unverified',主线三全部通过=False),
    最小后续处理=['仅依据本次记录将问题收窄到 HTTP 请求被拒绝；不再使用笼统超时描述。',
        '离线核对已保存的实际 payload 与当前适配器的请求结构，包括工具定义及 schema 引用；本次没有足够证据确认具体被拒绝字段，不能断言模型不可用或网络故障。',
        '当前没有保存错误正文或供应商请求编号，缺少细化 HTTP 400 原因的证据。后续如需改进，先做允许字段、有限长度的错误信息保存工程与离线检查，再另行授权一个新的付费公共请求。',
        '不复用旧未决授权、不追加本次请求，不进入完整直接/协调调查或变半径实验。'],
    发布=dict(repository='https://github.com/wran021004-gif/softrobot-agent.git',branch='feat/gvs-dynamics',
        内容='单节点包装、三项针对性离线检查及失败历史、中文能力说明和本轮非秘密证据；普通推送，远端SHA在最终答复核对。'))
_no_secrets(summary)
atomic_json(OUT/'delivery_summary.json',summary)
inventory={p.relative_to(ROOT).as_posix():dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
    for directory in (OUT,offline) for p in sorted(directory.iterdir()) if p.is_file() and p.name!='sha256_manifest.json'}
atomic_json(OUT/'sha256_manifest.json',inventory)
print(json.dumps(dict(http_status=400,provider_attempts=1,public_calls=2,node_prefetch=1,stopped=True,historical_unchanged=True)))
