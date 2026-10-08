"""Audit saved artifacts and generate delivery; no Host, credentials or network."""
import json
from datetime import datetime
from pathlib import Path

from tools.context_assembly import _no_secrets
from tools.research_direct_validation import ROOT, history, sha
from tools.research_validation_gate import generate
from tools.state_io import atomic_json, digest, read

OUT = Path(__file__).resolve().parent


def main():
    manifest = read(OUT / 'validation_manifest.json')
    assert all(sha(ROOT / p) == h for p, h in manifest['relevant_files_sha256'].items())
    assert history() == read(OUT / 'historical_before.json')
    bundle = read(OUT / 'direct_bundle.json')
    artifacts, events = bundle['artifacts'], bundle['events']
    nodes = bundle['state']['investigations']
    initial = read(OUT / 'direct_gate.json')
    assert initial == generate(bundle)  # Keep the original failed export untouched.
    attempts = [e for e in events if e['kind'] == 'investigation_provider_attempt']
    responses = [e for e in events if e['kind'] == 'investigation_provider_response']
    public = [c for c in bundle['calls'] if c['caller'] != 'investigation-dispatcher']
    node_calls = [c for c in bundle['calls'] if c['caller'] == 'investigation-dispatcher']
    assert len(attempts) == len(responses) == 7
    assert len(nodes) == 2 and all(n['status'] == 'failed' and not n.get('result') for n in nodes.values())
    assert bundle['session_status'] == 'stopped'
    assert not initial['accounting']['unresolved_reservations']
    assert not bundle['state'].get('principal_investigation_reads')
    assert not initial['dispositions']
    rows = []
    for event in responses:
        response = artifacts[event['outputs'][0]['artifact_id']]
        received = [e for e in events if e['kind']=='investigation_progress' and e['status']=='received'
            and e['request_id']==event['request_id'] and e['sequence']<event['sequence']][-1]
        reception = artifacts[received['outputs'][0]['artifact_id']]
        assert reception['response_received'] is True and reception['response_body_received'] is True
        assert reception['http_status']==200
        choice = response['choices'][0]
        calls = choice['message'].get('tool_calls', [])
        parseable = None
        if len(calls) == 1 and calls[0]['function']['name'] == 'investigation_return':
            try:
                json.loads(calls[0]['function']['arguments'])
                parseable = True
            except json.JSONDecodeError:
                parseable = False  # Never repair or turn partial JSON into a report.
        rows.append(dict(sequence=event['sequence'], request_id=event['request_id'],
            timestamp=event['timestamp'], response_reference=event['outputs'][0],
            reception_sequence=received['sequence'], reception_reference=received['outputs'][0], http_status=reception['http_status'],
            provider_completion_id=response.get('id'),
            provider_header_request_id=reception['provider_request_id'],
            finish_reason=choice.get('finish_reason'), native_call_count=len(calls),
            native_function=calls[0]['function']['name'] if len(calls) == 1 else None,
            report_arguments_complete_json=parseable, usage=response.get('usage')))
    terminal = [r for r in rows if r['native_function'] == 'investigation_return']
    assert len(terminal) == 2 and all(r['finish_reason'] == 'length'
        and r['usage']['completion_tokens'] == 3000 and r['report_arguments_complete_json'] is False for r in terminal)
    # Recorded local attempt/response intervals prove overlap, not hardware parallelism.
    windows = {}
    for key in nodes:
        own_start = [e for e in attempts if e['request_id'] == 'investigation-' + key]
        own_end = [e for e in responses if e['request_id'] == 'investigation-' + key]
        windows[key] = dict(first_attempt=own_start[0]['timestamp'], final_response=own_end[-1]['timestamp'],
            attempts=len(own_start), measured_failure_elapsed_s=artifacts[nodes[key]['failure_record']['artifact_id']]['elapsed_s'])
    overlap_start = max(datetime.fromisoformat(w['first_attempt']) for w in windows.values())
    overlap_end = min(datetime.fromisoformat(w['final_response']) for w in windows.values())
    first_pair = {k:dict(start=next(e['timestamp'] for e in attempts if e['request_id'] == 'investigation-' + k),
        end=next(e['timestamp'] for e in responses if e['request_id'] == 'investigation-' + k)) for k in nodes}
    pair_start = max(datetime.fromisoformat(w['start']) for w in first_pair.values())
    pair_end = min(datetime.fromisoformat(w['end']) for w in first_pair.values())
    rejected = [dict(sequence=e['sequence'], request_id=e['request_id'],
        record=artifacts[e['outputs'][0]['artifact_id']]) for e in events
        if e['kind'] == 'investigator_read' and e['status'] == 'rejected']
    assert len(rejected) == 1 and rejected[0]['record']['result']['error'] == 'QUERY_SOURCE_OUT_OF_SCOPE'
    proof = dict(bundle_identity=digest(bundle), raw_responses=rows, terminal_failures=terminal,
        parser_rule='Saved response finish_reason=length takes precedence: ValueError(INVESTIGATION_RESPONSE_TRUNCATED). '
                    'This is a deterministic interpretation of the frozen parser and saved current responses; '
                    'original sealed failure records keep their ValueError and unknown transport-detail fields.',
        received_full_http_body=True, complete_generated_report=False, http_statuses=[r['http_status'] for r in rows],
        failures={k:artifacts[n['failure_record']['artifact_id']] for k,n in nodes.items()},
        original_read_delivery=initial['novel_original_read_closures'], rejected_reads=rejected,
        simultaneous_windows=dict(nodes=windows, first_requests=first_pair,
            node_interaction_overlap_s=max(0.,(overlap_end-overlap_start).total_seconds()),
            first_request_overlap_s=max(0.,(pair_end-pair_start).total_seconds()),
            scope='Local recorded request/response intervals overlap; no provider internal execution timing claim.'),
        valid_reports=0, principal_attempts=0, independent_principal_checks=0, formal_dispositions=0,
        repair_after_launch=0, retries=0, paid_protocol_corrections=0,
        no_secret_check='Existing _no_secrets over all new/retained offline JSON plus explicit scoped publication review.')
    atomic_json(OUT/'trace_checks.json',proof)
    review = dict(bundle_identity=digest(bundle), reports=[], material_correctness='unverified',
        assessor='Local human-readable review of saved current responses; no additional model',
        assessment='Neither truncated return is a valid report. Source/provenance gate has no report facts to assess; '
                   'its pass must not be read as report correctness. No acceptance or principal handling was tested.',
        draft_cautions=[
            'Reach draft retains old execution identity and sampled non-pass; explicit reach tolerance is not in the authorized factual_result page. '
            'Its partial interpretation distinguishes unknown threshold from recorded task_accepted=false. No completed sourced facts or report may be adopted.',
            'Timing draft references the current read values but attempts value=0.35 for original /simulated_duration_s=0.35000000000000003, '
            'and an object value for scalar /converged_updates. Strict source binding would reject such facts if submitted as a complete report. '
            'These are observations of invalid partial text, not a repaired/validated report or a new scientific result.'
        ],
        missing_coverage=['completed investigator reports','novel-page use in a valid report','principal independent checks',
            'formal accept/defer/reject','independently sourced acceptance','explanation quality of valid reports'])
    atomic_json(OUT/'material_review.json',review)
    gate = generate(bundle,review)
    atomic_json(OUT/'direct_acceptance.json',gate)
    totals={k:sum(r['usage'].get(k,0) for r in rows) for k in ('prompt_tokens','completion_tokens','total_tokens')}
    per_node_tokens={k:{t:sum(r['usage'].get(t,0) for r in rows if r['request_id']=='investigation-'+k)
        for t in totals} for k in nodes}
    estimates = [dict(sequence=e['sequence'], request_id=e['request_id'],
        record=artifacts[e['outputs'][0]['artifact_id']]) for e in events if e['kind']=='investigation_token_accounting']
    summary=dict(活动=manifest['activity_id'],代码=manifest['code_commit'],历史来源=manifest['source'],
        总结='停止结果：真实传输及自主原始页选择/回传有证据；两份报告均因 length 截断失败，完整追读闭环和主模型正式处置未验证。',
        确定性验收=gate,
        调查者=[dict(身份=r['investigation_id'],初始预取=r['initial_prefetch'],
            自主追加读取=r['investigator_selected_original_reads'],目录读取=r['selected_directory_reads'],
            状态=r['status'],尝试=r['provider_attempts'],原生报告=None) for r in gate['nodes']],
        读取后续请求关联=proof['original_read_delivery'],越权拒绝=rejected,失败=proof['failures'],
        主模型=dict(提交=False,看到材料=[],独立检查=[],正式处置=[],原因='两份调查报告均未完成，依赖前提失败'),
        响应=dict(尝试传输=7,完整HTTP正文收到并保存=7,HTTP状态=[r['http_status'] for r in rows],有效报告=0,
            正文完整与生成完整的区别='HTTP JSON 正文完整且已保存；正文内 investigation_return 参数被生成上限截断。',
            请求身份='本地 request/execution ID、响应正文 completion ID 分列；供应商响应头 request ID 仍未知。'),
        费用=dict(供应商实际尝试=7,按节点尝试={k:w['attempts'] for k,w in windows.items()},
            公共工具操作=len(public),节点证据操作=sum(n['usage']['tool_calls'] for n in nodes.values()),
            节点证据分类=dict(预取=2,追加原始页=4,被拒绝读取=1,目录分页=0,报告读取=0,主模型独立核查=0),
            项目工具合计=gate['accounting']['charged']['tool_calls'],供应商token=totals,按节点token=per_node_tokens,
            输入估算=estimates,估算说明='按完整请求 UTF-8 字节保守估算；每次含 8192 framing reserve；实际 token 来自七份返回 usage。',
            原始节点预留=[dict(request_id=c['request_id'],reserved=c['reserved']) for c in node_calls],
            已结算=gate['accounting']['charged'],活动结束未决预留=gate['accounting']['unresolved_reservations'],
            供应商金额=None,金额说明='未读取账户账单或费率；token 和本地预算单位不能给出确实已扣金额。'),
        并行=proof['simultaneous_windows'],收尾=read(OUT/'application_lifecycle.json'),
        工程介入=read(ROOT/'evidence/research_direct_validation_20261008_offline/verification.json')['repair'],
        旧状态=dict(文件账本未变=read(OUT/'historical_after.json')['unchanged'],旧活动仍停止=True,
            原两次未知请求=2,旧未决模型单位=12,旧原因接收token金额='unknown',转移释放旧预留=False),
        限制=review['missing_coverage'],解释审查=review['draft_cautions'],
        下一步='建议仅调整调查问题的报告长度约束（少量关键事实、短解释及未知项），保持模型/思考/3000 输出上限及原生严格校验，'
            '先离线覆盖截断和精确值/单字段绑定，再取得新授权及预算开展一场新的有界直接验证。'
            '本轮修复额度已用，不能修复后续跑、改活动清零或继续付费试错；当前不建议进入协调验证。',
        边界='预先安排的两个历史问题，不证明自主选择多代理架构、研究效率或机器人改善。未启动主模型、协调者、递归派单、科学操作或润色请求。')
    _no_secrets(summary)
    atomic_json(OUT/'delivery_summary.json',summary)
    report=f'''主线三版本一：有界真实直接调查停止交付（2026-10-08）

活动：{manifest['activity_id']}；执行代码：{manifest['code_commit']}。
使用生产 Host、公共调查提交/状态路径、原生响应处理、证据 Store 与共用账本。
授权接收方 api.deepseek.com / deepseek-flash；全部七次实际对象保持 thinking=enabled、reasoning_effort=high、tool_choice=auto、max_tokens=3000。
历史来源仅为 Stage336 proposal-build 的 /execution/factual_result，execution_id=494deb38d6374deb8f741e96f2430826；不是本轮机器人运行或后来晋升候选。

结果：未完成两报告及主模型处置链路，整体验收未通过。命令退出成功只表示程序按失败前提完成收尾。
到达/保持调查者预取 /terminal_error_m={nodes['reach-question']['reads'][0]['page']['content']}，自主将根原件分三页读取（offset 0/8/28），结果分别进入后续模型请求；四次模型尝试。
执行时间调查者预取 /deadline_misses=35，自主读完整根原件（limit 50）；该页进入后续请求。随后尝试读取根内引用的 evaluation 原件，因不属于本次目录授权被 QUERY_SOURCE_OUT_OF_SCOPE 拒绝，拒绝内容如实回传；三次模型尝试。
两名调查者均选择了初始未给出的原始材料；但没有有效报告证明新增证据的最终使用，故“追读能力未验证”。不得把部分草稿、目录/读取记录或 HTTP 200 代替合格报告。
两次最后响应都为 finish_reason=length，completion_tokens=3000；investigation_return 参数 JSON 不完整，冻结解析器在 response_parse 抛出 ValueError，严格拒绝截断结果。没有重试、纠正、提高输出限制或转换正文为报告。
七次 HTTP 响应正文完整接收并保存，HTTP 状态为 200；生成被截断不同于传输正文丢失。两份原失败记录已保留。其细分类未知，截断依据来自原始响应及冻结解析器；供应商响应头请求编号未知，正文 completion ID 分列保留。

主模型没有提交，未看到任何材料、未独立读取、未正式采纳/暂缓/拒绝。四页核查方案仍为计划，不能写成执行。本轮没有接受错误或无依据采纳。
来源和值门没有可校验的报告事实，其 pass 不能证明报告归属和解释正确。部分时间草稿把精确时长改为 0.35，并给标量 /converged_updates 配对象值，若完整提交也将触发严格来源值拒绝；没有补齐或恢复为报告。到达草稿区分记录的 task_accepted=false 与页内未显式给出的到达阈值，但也不能当作合格交付。

费用与时间：供应商尝试 7（到达4、时间3）；公共工具操作 {len(public)}（提交2、状态3），节点证据操作7（预取2、原始页4、拒绝1），共用项目工具12；后端/工作进程/科学操作0。
供应商返回 prompt_tokens={totals['prompt_tokens']}，completion_tokens={totals['completion_tokens']}，total_tokens={totals['total_tokens']}（七份 usage 全部可核对）。每请求保守输入估算另列在 delivery_summary/trace_checks；估算不是实际计费。
原两调查节点各预留6模型/8工具/180秒；按原账本结算为4/4/{node_calls[0]['charged']['wall_s']:.3f}秒及3/3/{node_calls[1]['charged']['wall_s']:.3f}秒。
项目已结算7模型/12工具/{gate['accounting']['charged']['wall_s']:.3f}秒，结束未决预留0，未用授权不执行。应用历时{read(OUT/'application_lifecycle.json')['elapsed_s']:.3f}秒。
本地首次请求区间重叠{proof['simultaneous_windows']['first_request_overlap_s']:.3f}秒，两个交互窗口重叠{proof['simultaneous_windows']['node_interaction_overlap_s']:.3f}秒；证明实际时间重叠，不断言供应商内部计算并行。累计结算时间含并发节点，不能和应用墙钟混同。
供应商扣款金额未知；没有账户对账、费率探测或金额假算。活动已停止，调查线程均结束，无新增工作；供应商取消确认未获得。
旧两个未知请求、12未决模型单位及旧停止状态均未变化；12是预留占用而不是12次请求。本轮不能证明旧请求原因、接收或费用，也没有转移/释放旧预留。

工程介入与验证：明确选中的5项离线检查通过，最新4项验收器检查通过，未导入科学测试或运行完整历史套件。唯一局部修复在真实发送前完成，处理主模型预取整根引入不可访问嵌套配置引用的问题，改为四页有限关键事实核查，并使主模型公共4页+节点4次共计8次；随后纠正该方案执行ID页默认长度不足。离线失败记录01/02/03及通过记录04均保存，未扩权、绕过封存或重置真实活动。
真实发送后修复0；代码和配置未改变。当前总体 gate=false；真实交互、边界、配置和账本通过，报告/处置失败，完整追读和解释质量未覆盖。

建议：先在不改变批准模型、思考、3000输出上限和原生校验的前提下，离线验证更短的报告要求（少量精确单字段事实、短解释及未知项）及截断处理。另取得新的非秘密数据授权、尝试/工具/时间预算和停止条件，再开展一场有界直接验证；不得把本轮失败活动续跑或预算清零。完整直接验收通过后才提出协调调查授权。本轮不自动执行任何下一阶段。

可核查依据：direct_bundle.json（原请求/响应/读取/失败/账本），direct_gate.json（原导出门），direct_acceptance.json（含人工审查的确定性门），trace_checks.json，material_review.json，delivery_summary.json，historical_before/after.json，application_lifecycle.json，以及相邻 offline/verification.json。发布与远端SHA核对见 publication_review.json 和最终答复。
'''
    (OUT/'delivery_report.txt').write_text(report,encoding='utf8')
    for directory in (OUT,ROOT/'evidence/research_direct_validation_20261008_offline'):
        for p in directory.glob('*.json'):_no_secrets(read(p))
    atomic_json(OUT/'sha256_manifest.json',{p.relative_to(ROOT).as_posix():dict(sha256=sha(p),bytes=p.stat().st_size)
        for d in (OUT,ROOT/'evidence/research_direct_validation_20261008_offline') for p in d.iterdir()
        if p.is_file() and p.name!='sha256_manifest.json'})
    print(json.dumps(dict(passed=gate['passed'],gates=gate['gates'],tokens=totals,
        unresolved=gate['accounting']['unresolved_reservations'],historical_unchanged=True)))


if __name__=='__main__':main()
