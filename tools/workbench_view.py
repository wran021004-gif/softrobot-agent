"""Chinese saved-state dashboard; the existing viewer supplies motion and curves."""
from html import escape
from pathlib import Path
import json
from urllib.parse import quote, unquote, urlsplit
from tools.state_io import read
from tools.workbench_catalog import TOOLS
from tools.spec_tools import ROOT


def render(root, state):
    def text(value):
        return escape(str(value))
    def link(path, label=None):
        return f'<a href="{quote(path, safe="/")}">{text(label or path)}</a>'
    rows, media = [], []
    for cid, paths in state.get('native_replays', {}).items():
        media.append('<p>原生场景回放：' + text(cid) + ' · ' + ' · '.join(link(p) for p in paths) + '</p>')
        media.extend(f'<img src="{quote(p, safe="/")}" alt="MuJoCo 原生机器人、腱线与目标场景">' for p in paths if p.endswith('.gif'))
    for attempt in state['attempts']:
        result = attempt.get('result', {})
        refs = [link(p) for p in result.get('artifacts', [])]
        refs += [link(attempt['result_ref'], '工具结果')] if 'result_ref' in attempt else []
        rows.append(f'<tr><td>{text(TOOLS[attempt["tool"]]["label"])}</td><td>{text(result.get("status", attempt["status"]))}</td><td>{text(result.get("failure_code") or "")}</td><td>{"<br>".join(refs)}</td></tr>')
        for p in result.get('artifacts', []):
            if p.endswith(('.png', '.gif')):
                media.append(f'<a href="{quote(p, safe="/")}"><img src="{quote(p, safe="/")}" alt="保存轨迹动画或曲线"></a>')
    decisions = []
    for row in state['decisions']:
        p = row['proposal']
        if not isinstance(p, dict):
            decisions.append(f'<li>拒绝无效决策：{text(p)}</li>')
            continue
        refs = [link(state['evidence'][r]['path'], r) for r in p.get('evidence', []) if r in state['evidence']]
        decisions.append(f'<li><strong>{text(p.get("tool") or p.get("action"))} · {text(row.get("status"))}</strong>：{text(p.get("reason", ""))}<br>依据：{" · ".join(refs)}<br>参数：{text(p.get("arguments", {}))} {text(row.get("failure_code", ""))}</li>')
    execution = []
    runs = sorted(root.glob('attempts/*/execution/*'))
    if state['request'].get('replay'):
        runs.append(root / state['request']['replay']['path'])
    for run in runs:
        if not run.is_dir():
            continue
        relative = run.relative_to(root).as_posix()
        execution.append('<p>实验：' + text(relative) + '</p>')
        trace = run / 'trace.json'
        if trace.exists():
            events = read(trace)
            execution.append('<p>内部阶段：' + ' → '.join(text(e.get('gate', '')) + ' (' + text(e.get('status', '')) + ')' for e in events) + '</p>')
        for name in ('design_input.yaml', 'controller.json', 'model_result.json', 'robot.xml', 'mujoco_result.json', 'gate_summary.json', 'diagnostic_summary.json', 'error.json', 'trace.jsonl', 'run.json'):
            if (run / name).exists():
                execution.append(link(relative + '/' + name) + ' · ')
        metrics = run / 'metrics.json'
        if metrics.exists():
            data = read(metrics)
            label = '历史回放成绩（本轮 NOT_RUN），由原评价器给出：' if state['request'].get('replay') else '任务成绩由原评价器给出：'
            execution.append('<p>' + label + text(data.get('mujoco', {}).get('task_success', 'NOT_RUN')) +
                             '；末端误差 (m)：' + text(data.get('mujoco', {}).get('position_error_m', '无')) + '</p>')
        execution.append('<p>交互观察命令：<code>python examples/observe.py ' + text(run.relative_to(ROOT).as_posix()) + '</code></p>')
        execution.append('<p>MuJoCo 原生场景窗口：<code>python examples/native_replay.py ' + text(run.relative_to(ROOT).as_posix()) + '</code>；空格暂停/继续，左右逐帧，R 重播，鼠标调视角。导出加 <code>--export runs/native_export_new</code>（新目录）。</p>')
    limits = state['request']['limits']
    used = {k: sum(a['cost'].get(k, 0) for a in state['attempts']) for k in limits}
    used['decisions'] = len(state['decisions'])
    if 'candidates' in used:
        used['candidates'] += 1
        used['model_calls'] = len(state.get('model_calls', []))
    historical = state['request'].get('round_budget', {}).get('baseline', {})
    total_used = dict(used)
    used = {k: v - historical.get(k, 0) for k, v in used.items()}
    budget = '；'.join(f'{text(k)}：{used[k]}/{limits[k]}' for k in limits)
    if historical:
        budget = '本轮新增用量：' + budget + '<br>历史消耗（保留）：' + text(historical) + '<br>累计消耗：' + text(total_used)
    design = (root / 'inputs/design.yaml').read_text(encoding='utf-8')
    history = [link(v['path'], k + '（历史上下文）') for k, v in state['evidence'].items() if k.startswith('history:')]
    design_section = ''
    if state.get('candidates'):
        from tools.design_session import summary, evaluation
        summary_data = summary(state)
        candidate_rows = []
        for c, result in zip(state['candidates'], summary_data['candidates']):
            ev = evaluation(state, c['candidate_id'])
            links = [link(c['path'], '设计')]
            links += [link(c[k], label) for k, label in (('check_candidate_ref', '检查'), ('evaluate_candidate_ref', '评价'), ('observe_candidate_ref', '动画入口')) if k in c]
            status = ('计算完成但任务未达标' if result['canonical_task_status'] == 'FAIL' else
                      '计算完成且任务达标' if result['canonical_task_status'] == 'PASS' else '尚无完成的任务评价')
            available = ev and ev['result']['data'].get('trajectory_available')
            observation = next((a for a in reversed(state['attempts']) if a['tool'] == 'observe_candidate' and a['arguments'].get('candidate_id') == c['candidate_id']), None)
            animation = bool(observation and any(p.endswith('.gif') for p in observation.get('result', {}).get('artifacts', [])))
            status += '；' + ('动画已生成' if animation else '轨迹已保存，尚未生成动画' if available else '没有可用轨迹')
            candidate_rows.append(f'<tr><td>{text(c["candidate_id"])} ← {text(c["parent_id"] or "初始")}</td><td>{text(c["design"])}</td><td>{text(c.get("changes", {}))}<br>{text(c.get("reason", ""))}</td><td>{text(status)} / {text(result["canonical_task_status"])}<br>实际误差：{text(result["position_error_m"])} m<br>{text(result["failure_code"] or "")}</td><td>{" · ".join(links)}</td></tr>')
        calls = []
        inherited = state['request'].get('continuation', {}).get('used', {}).get('model_calls', 0)
        for m in state['model_calls']:
            from tools.deepseek_adapter import input_metrics
            request_path = m['folder'] + '/request.json'
            wire = read(root / request_path)
            sizes = m.get('input_metrics') or input_metrics(wire)
            labels = {'system': '系统指令', 'context': '任务与当前状态', 'assistant': '历史回复', 'tool_feedback': '历史工具反馈', 'reasoning': '其中思考字段', 'tools': '工具定义'}
            components = '；'.join(labels[k] + '：' + str(v) + ' B' for k, v in sizes['components'].items())
            if sizes.get('context_sections'):
                components += '；状态内部各项 (B)：' + text(sizes['context_sections'])
            response_path = m['folder'] + '/response.json'
            response_link = link(response_path, '完整回复（含协议字段）') if (root / response_path).exists() else '没有收到完整回复'
            d = next((d for d in state['decisions'] if d['sequence'] == m['decision_sequence']), None)
            attempt = next((a for a in state['attempts'] if a['decision'] == m['decision_sequence']), None)
            proposal = d['proposal'] if d else {}
            outcome = ''
            if d:
                outcome = '<p>决策：' + text(d.get('status')) + '；拒绝原因：' + text(d.get('failure_code') or '无') + '</p>'
                outcome += '<pre>' + text(json.dumps(proposal, ensure_ascii=False, indent=2)) + '</pre>'
            outcome += '<p>请求模型：' + text(wire.get('model')) + '；响应模型：' + text(m.get('response_model') or '尚无响应') + '；实际请求思考模式：' + text(wire.get('thinking', {}).get('type', '未记录')) + '；生成上限：' + text(wire.get('max_tokens')) + '；实际 token 用量：' + text(m.get('usage', {})) + '</p>'
            if m.get('thinking') == 'enabled':
                outcome += '<p>思考字段已保存：' + text('reasoning_content' in m.get('message', {})) + '（完整字段保留在响应文件，页面只展示简短行动依据）</p>'
            if attempt:
                outcome += '<p>工具结果：' + text(attempt.get('result', {}).get('status', attempt['status'])) + ' · ' + link(attempt['result_ref'], '完整工具结果') + '</p>' if attempt.get('result_ref') else '<p>工具执行中</p>'
            if m.get('feedback'):
                outcome += '<details><summary>回传模型的工具反馈</summary><pre>' + text(json.dumps(m['feedback'], ensure_ascii=False, indent=2)) + '</pre></details>'
            calls.append(f'<details><summary>#{m["index"]} {"继承请求" if m["index"] < inherited else "本运行请求"} · {text(m["status"])} · {sizes["total_bytes"]:,} B</summary><p>{components}</p><p>会话片段起点：{text(m.get("context_start", "旧版完整历史"))}；{link(request_path, "完整请求")} · {response_link}</p><p>{text(m.get("error", ""))}</p>{outcome}</details>')
        preview = state.get('last_input_metrics', {})
        memory_view = '<details><summary>持续工作记忆：已读内容、发现与下一步</summary><pre>' + text(json.dumps(state.get('working_memory', {}), ensure_ascii=False, indent=2)) + '</pre></details>'
        design_section = f'<section><h2>模型与候选设计</h2><p>单决策模型：{text(state["request"]["design_session"]["model"])}；思考模式：{text(state["request"]["design_session"]["thinking"])}；固定指令 C1。成绩来自本次或兼容续接继承的真实评价，NOT_RUN 表示尚无实际成绩。</p><table><tr><th>编号 / 上一版</th><th>参数</th><th>修改与依据</th><th>计算 / 任务成绩</th><th>证据</th></tr>{"".join(candidate_rows)}</table><p>{link("design_report.json", "有证据支持的最终结果")}；流程完成：{text(summary_data["workflow_completed"])}；机器人达标：{text(summary_data["task_achieved"])}</p><p>本运行新增模型请求：{summary_data["new_model_requests"]}；新增仿真预留：{summary_data["new_simulation_reservations"]}</p></section><section><h2>模型请求 → 回复 → 工具反馈（时间顺序）</h2>{"".join(calls)}<p>最新请求或待发送预览：{text(preview)}</p><p>停止原因：{text(state.get("stop_reason"))}</p></section>'
    return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<title>机器人设计工作台</title>
<script>setInterval(()=>{{if(!document.querySelector('details[open]'))location.reload()}},5000)</script>
<style>body{{font:16px/1.6 system-ui,sans-serif;max-width:1200px;margin:32px auto;padding:0 24px;background:#f5f7fb;color:#172b45}}section{{background:white;padding:20px;margin:18px 0;border-radius:12px}}table{{width:100%;border-collapse:collapse}}td,th{{border-bottom:1px solid #ddd;padding:10px;text-align:left}}a{{color:#165caa;overflow-wrap:anywhere}}img{{width:100%;max-width:1008px}}pre{{white-space:pre-wrap}}li{{margin:14px 0}}</style>
<h1>机器人自动设计工作台</h1><p>读取任务 → 检查设计 → 数学分析 → 控制生成 → 编译 → 仿真 → 评价诊断 → 下一步决策 → 停止</p>
<section><h2>当前状态：{text(state['status'])}</h2><p>{text(state.get('stop_reason', '按固定规则执行；每 5 秒刷新保存状态'))}</p><p>{budget}</p><p>冻结任务：reach_free_v1；控制器：C1；物理：legacy_v1_surrogate（未标定）</p><details><summary>使用的设计</summary><pre>{text(design)}</pre></details><p>{link('request.json', '任务、预算与代码版本')} · {link('state.json', '完整状态与证据哈希')} · {link('source_snapshot.zip', '执行源代码快照')}</p>{' · '.join(history)}</section>
{design_section}<section><h2>工具执行</h2><table><tr><th>阶段</th><th>状态</th><th>错误</th><th>证据</th></tr>{''.join(rows)}</table><p>缓存复用：{len(state['reuse'])} 次。预算按尝试预扣，中断不返还。</p></section>
<section><h2>为什么选择下一步</h2>{memory_view if state.get('candidates') else ''}<ol>{''.join(decisions)}</ol></section>
<section><h2>实验细节与失败证据</h2>{''.join(execution)}</section>
<section><h2>原生场景、动画与诊断曲线</h2><p>直接打开最佳候选原生窗口：<code>python examples/native_replay.py {text(root.relative_to(ROOT).as_posix())}</code>。空格暂停/继续，左右逐帧，R 重播；鼠标拖动和滚轮调整视角。回放读取保存状态和时间，不推进实验、不重新评分。</p>{''.join(media) or ('轨迹已保存，尚未生成动画。' if any(a.get('result', {}).get('data', {}).get('trajectory_available') for a in state['attempts']) else '没有可用轨迹；请查看评价与错误证据。')}</section></html>'''


def write_dashboard(root, state):
    temporary = root / 'index.html.tmp'
    temporary.write_text(render(root, state), encoding='utf-8')
    temporary.replace(root / 'index.html')


def serve(root, port=8765):
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    root = Path(root).resolve()
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def do_GET(self):
            raw = unquote(urlsplit(self.path).path).lstrip('/')
            path = (root / raw).resolve()
            if not path.is_relative_to(root):
                self.send_error(403)
                return
            if raw in ('', 'index.html'):
                body = render(root, read(root / 'state.json')).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(body)
            elif path.is_file():
                super().do_GET()
            else:
                self.send_error(404)

    print(f'中文工作台：http://127.0.0.1:{port} （Ctrl+C 停止只读服务）', flush=True)
    ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()
