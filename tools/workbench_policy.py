"""No tool execution here. Replace decide(context) with a JSON model adapter."""
from schemas.workbench import Decision


def decide(context):
    attempts = context['attempts']
    done = {a['tool']: a for a in attempts if a.get('result', {}).get('status') == 'completed'}
    last = attempts[-1] if attempts else None
    refs = [last['result_ref']] if last else ['request']

    def proposal(action, reason, tool=None, arguments=None):
        return Decision(action=action, tool=tool, arguments=arguments or {}, evidence=refs, reason=reason)

    if last and last.get('result', {}).get('status') != 'completed':
        return proposal('capability_missing', '上一步未完成：' + last['result'].get('failure_code', 'UNKNOWN') + '。保留失败证据和已消耗预算，不自动重试。')
    history = [r for r in context['evidence'] if r.startswith('history:')]
    if history and 'read_evidence' not in done:
        refs = history[:1]
        return proposal('continue', '读取已登记历史证据作为上下文；不将历史成绩当成本次评价。', 'read_evidence', {'evidence_id': history[0]})
    if 'inspect_task' not in done:
        return proposal('continue', '先解析任务合同并核对当前设计的执行能力。', 'inspect_task')
    if 'analyze_design' not in done:
        return proposal('continue', '设计检查通过；记录已有 PCC 数学分析作为设计依据。', 'analyze_design')
    if 'evaluate_design' not in done:
        if context['request'].get('replay'):
            refs = [context['request']['replay']['path'] + '/run.json', *refs]
            return proposal('continue', '校验并复用已封存运行的真实评价、控制和轨迹；历史回放，零新仿真，不生成本轮任务成绩。', 'evaluate_design', {'controller': 'C1'})
        if context['remaining']['simulations'] < 1 or context['remaining']['matlab_calls'] < 2:
            return proposal('stop', '剩余后端预算不足，停止；不因尚无任务成绩追加预算。')
        return proposal('continue', '使用冻结 C1 路线执行一次完整评价，数学预测不替代任务成绩。', 'evaluate_design', {'controller': 'C1'})
    result = done['evaluate_design']['result']['data']
    truth = result.get('canonical_task_status', 'NOT_RUN')
    if result.get('evidence_role') == 'historical_replay':
        truth = '历史回放 ' + truth + '（本轮 NOT_RUN）'
    if 'diagnose' not in done:
        return proposal('continue', f'既有评价结果为 {truth}；读取诊断证据，分析预测与实际反馈。', 'diagnose')
    if truth == 'NOT_RUN':
        return proposal('capability_missing', '已保存未完成评价的门控与错误证据；没有任务成绩，不追加后端尝试。')
    if 'observe' not in done and result.get('trajectory_available'):
        return proposal('continue', f'评价为 {truth}；生成保存轨迹的动画和曲线，方便检查失败证据。', 'observe')
    return proposal('stop', f'有限闭环完成，任务成绩 {truth}。已读取反馈并完成后续处理；本轮无设计搜索或物理标定权限，不追加仿真。')
