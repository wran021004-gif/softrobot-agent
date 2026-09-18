"""Unified metric result view; no simulation, rescoring or budget mutation."""
import html
import json
from schemas.platform import EvaluationResult


def result_view(host):
    events = host.store.events(host.run_id)
    evaluations = []
    seen = set()
    for event in events:
        if event['kind'] != 'evaluation':
            continue
        for ref in event['outputs']:
            if ref['artifact_id'] in seen:
                continue
            seen.add(ref['artifact_id'])
            result = EvaluationResult.model_validate(host.store.artifact(ref))
            evaluations.append(dict(evaluation=ref, candidate_id=event['candidate_id'], result=result.model_dump(mode='json')))
    result = dict(run_id=host.run_id, status=host.store.session(host.run_id)['status'], evaluations=evaluations,
                resources=host.store.remaining(host.run_id), event_count=len(events), rescoring=False, backend_solves=0)
    if host.store.session(host.run_id)['snapshot']['input']['policy'].get('route'):
        from extensions.tendon_family.route import view
        result['route'] = view(host)
    return result


def export_html(host, path):
    view = result_view(host)
    rows = []
    for item in view['evaluations']:
        result = item['result']
        for metric in result['metrics']:
            rows.append('<tr>' + ''.join('<td>' + html.escape(str(v)) + '</td>' for v in
                (item['candidate_id'], metric['name'], metric['value'], metric['units'], result['validity'], result['task_success'])) + '</tr>')
    document = '<!doctype html><meta charset="utf-8"><title>统一机器人开发工作台</title><style>body{font:16px sans-serif;max-width:1100px;margin:40px auto}td,th{padding:12px;border-bottom:1px solid #ddd}pre{white-space:pre-wrap}</style>'
    document += '<h1>统一开发平台 · 保存结果</h1><p>会话：' + html.escape(host.run_id) + '；只读展示，不重新求解或评分。</p>'
    document += '<table><tr><th>候选</th><th>指标</th><th>值</th><th>单位</th><th>计算有效性</th><th>任务成功</th></tr>' + ''.join(rows) + '</table>'
    document += '<details><summary>结果身份、来源与资源</summary><pre>' + html.escape(json.dumps(view, ensure_ascii=False, indent=2)) + '</pre></details>'
    with path.open('x', encoding='utf8') as stream:
        stream.write(document)
    return dict(path=str(path), evaluations=len(view['evaluations']), new_solves=0)


def export_bundle(store, artifact_id, destination):
    from schemas.platform import ExportBundle, EvidenceRef
    from schemas.evidence import safe_relative_path
    bundle = ExportBundle.model_validate(store.artifact(EvidenceRef(artifact_id=artifact_id)))
    checked = []
    for item in bundle.files:
        relative = safe_relative_path(item.filename)
        path = (destination / relative).resolve()
        if not path.is_relative_to(destination):
            raise ValueError('EXPORT_PATH_OUTSIDE_DESTINATION')
        checked.append((path, store.artifact(item.reference, raw=True)))
    destination.mkdir(parents=True, exist_ok=False)
    for path, content in checked:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(content)
    return dict(destination=str(destination), files=len(checked), source=artifact_id, new_solves=0)
