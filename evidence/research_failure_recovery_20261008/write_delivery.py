"""Offline evidence consolidation; never opens credentials or provider transport."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import subprocess
import sys
from tools.state_io import read, atomic_json
from tools.context_assembly import _no_secrets
from tools.platform_store import Store

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
before=read(OUT/'historical_review_before.json')
store=Store(ROOT/'runs/mainline3-validation-769f832fdbf5-direct')
unchanged=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in before['historical_files_sha256'].items())
unchanged &= hashlib.sha256(store.db.read_bytes()).hexdigest()==before['original_store_sha256']
assert unchanged
assert store.session('mainline3-direct')['status']=='stopped'
assert store.remaining()==before['original_current_ledger']
atomic_json(OUT/'historical_review_after.json',dict(original_files_and_store_byte_unchanged=unchanged,
    stopped=True,ledger_unchanged=True,new_information_about_original_cause=None,
    explanation='Read-only review confirms two recorded attempts, zero saved responses. No historical exception reconstructed; no authorization, reservation or snapshot changed.'))
attempts=[read(p) for p in sorted(OUT.glob('offline_attempt_*.json'))]
assert attempts[-1]['failures']==0 and attempts[-1]['errors']==0
history=[dict(path=p.name,tests=v['tests'],failures=v['failures'],errors=v['errors'],
    command=v.get('command','python -m tests.test_research_failure_recovery (explicit class loader)'),
    failure_cases=v.get('failure_cases'),error_cases=v.get('error_cases'))
    for p,v in zip(sorted(OUT.glob('offline_attempt_*.json')),attempts)]
scope_files=['tools/research_investigations.py','tools/model_transports/deepseek.py',
    'tests/test_research_failure_recovery.py','docs/research_mainline3_v1_capabilities.md',
    str(Path(__file__).relative_to(ROOT).as_posix())]
report=dict(日期='2026-10-08',目标='主线三版本一：失败可诊断性与安全恢复的离线工程交付',
    起点='5eb015ce125cd85f79b5d06d936975b591f70d37',
    修复路径=[
        '去掉统一 TimeoutError 包装，复用既有连接、DNS、TLS、HTTP、超时分类；未知类别保持未知。',
        '公共提交、请求准备、传输边界、HTTP 接收/正文接收、原生解析与校验、响应/有效报告保存、结算分别记录状态。',
        '失败证据关联活动、调查、本地请求/执行身份、代码提交和依赖身份、时间与已测耗时；HTTP 状态、供应商请求编号缺失时留空，不把 completion id 当请求编号。',
        '异常属性采用允许字段清单；仅保留已有脱敏消息且上限 512 字符，不复制完整异常、头、环境或错误正文。响应正文和嵌套原生参数先作秘密检查，再沿原 Store 机制保存。',
        '报告保存失败时可核对已保存的原生报告响应；结算失败先核对原有效报告或已封存账本回执。明确本地失败的结算故障同时保存两次原因与关联，并可据原事实对账。',
        '证据读取失败、正文中断、请求无确认、诊断写入失败保持未决；诊断写入失败仅向既有 stderr 尽力输出最小脱敏记录，不保证故障时必然落盘。',
        '恢复继续检查当前活动、冻结范围、父子工具/来源权限和期限；不会重发、释放不确定预留或解除停止状态。'],
    离线验证=dict(最终覆盖方法数=11,完整针对性检查=dict(tests=10,failures=0,errors=0,path='offline_attempt_04.json'),
        结算处理更新后受影响复核=dict(tests=4,failures=0,errors=0,path='offline_attempt_05.json',新增方法=1),
        实际覆盖=['连接拒绝、DNS、TLS、HTTP 429、超时保留原类别与已知接收事实',
            'HTTP 200 头已收到后正文连接中断：接收头已知、正文结果未知、预留保留',
            '本地准备和线程启动失败：不虚构已发送或已收到响应',
            '响应已收到但原生解析失败、传输 JSON 解析失败',
            '响应保存、有效报告保存和结算故障，以及封存后状态更新故障',
            '暂时无法读取已保存报告时不释放预留；恢复可读后结算原结果',
            '解析失败再结算失败：保留两次失败关联，安全核对已确认本地失败',
            '活跃线程跨进程保持 running；进程中断后新进程识别 unconfirmed，禁止重派',
            '停止后的新进程公共收集被拒绝且账本不变；期限过期被拒绝',
            '伪造敏感异常属性、头、正文和嵌套原生参数不进入错误/证据存储；空 usage 不视为实际用量已知'],
        替身边界='生产 Host、公共调查调度、原生处理、Store、账本和进程所有权；只替换外部传输/假 HTTP 对象/指定保存与结算故障点。独立子进程通过同一公共入口提交或收集。',
        失败及修复历史=history,
        夹具修正=['首轮 7 个清理错误：Windows SQLite 读连接尚未被垃圾回收；补充 gc.collect 后清理。',
            '第二轮 1 个并发拒绝：两项未决调查占用全部两个并发名额；不同传输类别改用独立隔离项目，生产上限未放宽。'],
        本轮真实模型请求=0,本轮凭据加载=0,本轮连通性探测=0,本轮科学计算=0,第二版开发=False),
    原两次请求=dict(已知='两个本地提供方尝试事件、没有保存的响应；具体异常原因未知。原活动仍停止，原文件和 SQLite 字节哈希及账本均未改变。',
        无法确定=['请求是否到达供应商','是否产生回复或计费','原始网络/HTTP/解析异常原因','实际供应商 token 用量'],
        计数区分=dict(历史尝试=2,历史已保存响应=0,
            已结算=dict(model_calls=0,tool_calls=4,wall_s=3.797999999980675),
            原未决预留_每节点=dict(model_calls=6,tool_calls=8,wall_s=180.0),
            原未决预留_两个节点合计=dict(model_calls=12,tool_calls=16,wall_s=360.0),
            历史账本总占用=before['original_current_ledger']['used'],供应商费用=None,
            说明='12 模型单位是未决预留占用，不能读成 12 次实际模型请求。字节/令牌估算不能替代返回用量，返回用量也不等于已知供应商费用。')),
    下一次最小真实验证建议=dict(本轮不执行=True,
        新授权='另行明确授权同一批准端点/模型、限定非秘密研究证据发送和付费调用；创建全新单请求活动，不复活或迁移旧预留。',
        建议预算=dict(调查节点=1,供应商尝试上限=1,自动重试=0,节点证据操作上限=1,
            预取='仅一个小型已保存来源页，计入证据操作',公共提交及收集上限=8,节点时限秒=180,活动时限秒=240,输出上限字节=16384,
            backend_solves=0,worker_calls=0,scientific_operations=0),
        验收='先核对单个公共请求能保留明确结果或分阶段脱敏失败证据，且响应、有效报告、实际用量和结算事实可区分。不是完整直接/协调调查的通过声明。',
        停止条件=['首个完成/失败/未确认终态立即停，不自动重发',
            '端点/模型或冻结权限发生差异即停','期限、预算或证据写入失败即停','未确认保留原预留；供应商费用未知则继续标未知'],
        后续='单请求记录可靠并经审查后，才考虑另行授权完整直接与协调调查；原两项未知请求仍需独立对账。'),
    限制=['没有恢复已丢失的历史异常，也没有解决或复现原事故根因。',
        '离线替身通过不构成真实模型调查成功或供应商端连通性/计费验证。',
        '未证明机器人改善、诊断因果收益或第二版能力；机器人科学路径未执行。',
        'HTTP 头接收与完整正文/有效报告是不同事实；错误类别和本地长度检查都不授权重试。',
        '存储及 stderr 同时失败时，不能保证诊断完整持久化；证据不足则保持未决。'],
    发布=dict(target='https://github.com/wran021004-gif/softrobot-agent.git',branch='feat/gvs-dynamics',
        remote_before='5eb015ce125cd85f79b5d06d936975b591f70d37',normal_push_only=True,
        scope='两处生产代码、一份独立针对性测试、既有能力文档的追加说明和本轮非秘密证据；远端 SHA 与工作区状态在最终答复核对。'),
    环境=dict(python=sys.version,packages={p:importlib.metadata.version(p) for p in ('pydantic','numpy','mujoco')}),
    当前代码文件哈希={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in scope_files})
_no_secrets(report)
atomic_json(OUT/'delivery_report.json',report)
inventory={p.name:dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
    for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='sha256_manifest.json'}
atomic_json(OUT/'sha256_manifest.json',inventory)
print(json.dumps(dict(historical_unchanged=unchanged,final_checks=[history[-2],history[-1]],real_provider_requests=0),ensure_ascii=False))
