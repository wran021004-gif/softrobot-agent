"""Chinese saved-state dashboard; the existing viewer supplies motion and curves."""
from html import escape
from pathlib import Path
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
    limits = state['request']['limits']
    used = {k: sum(a['cost'].get(k, 0) for a in state['attempts']) for k in limits}
    used['decisions'] = len(state['decisions'])
    budget = '；'.join(f'{text(k)}：{used[k]}/{limits[k]}' for k in limits)
    design = (root / 'inputs/design.yaml').read_text(encoding='utf-8')
    history = [link(v['path'], k + '（历史上下文）') for k, v in state['evidence'].items() if k.startswith('history:')]
    return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta http-equiv="refresh" content="5"><title>机器人设计工作台</title>
<style>body{{font:16px/1.6 system-ui,sans-serif;max-width:1200px;margin:32px auto;padding:0 24px;background:#f5f7fb;color:#172b45}}section{{background:white;padding:20px;margin:18px 0;border-radius:12px}}table{{width:100%;border-collapse:collapse}}td,th{{border-bottom:1px solid #ddd;padding:10px;text-align:left}}a{{color:#165caa;overflow-wrap:anywhere}}img{{width:100%;max-width:1008px}}pre{{white-space:pre-wrap}}li{{margin:14px 0}}</style>
<h1>机器人自动设计工作台</h1><p>读取任务 → 检查设计 → 数学分析 → 控制生成 → 编译 → 仿真 → 评价诊断 → 下一步决策 → 停止</p>
<section><h2>当前状态：{text(state['status'])}</h2><p>{text(state.get('stop_reason', '按固定规则执行；每 5 秒刷新保存状态'))}</p><p>{budget}</p><p>冻结任务：reach_free_v1；控制器：C1；物理：legacy_v1_surrogate（未标定）</p><details><summary>使用的设计</summary><pre>{text(design)}</pre></details><p>{link('request.json', '任务、预算与代码版本')} · {link('state.json', '完整状态与证据哈希')} · {link('source_snapshot.zip', '执行源代码快照')}</p>{' · '.join(history)}</section>
<section><h2>工具执行</h2><table><tr><th>阶段</th><th>状态</th><th>错误</th><th>证据</th></tr>{''.join(rows)}</table><p>缓存复用：{len(state['reuse'])} 次。预算按尝试预扣，中断不返还。</p></section>
<section><h2>为什么选择下一步</h2><ol>{''.join(decisions)}</ol></section>
<section><h2>实验细节与失败证据</h2>{''.join(execution)}</section>
<section><h2>动画与曲线</h2><p>由现有观察器读取保存轨迹生成；观看不启动仿真。</p>{''.join(media) or '暂无完整轨迹；请查看上方门控或错误证据。'}</section></html>'''


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
