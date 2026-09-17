"""统一机器人开发平台：只读检查与创建／运行显式分开。"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf8')


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if arguments and arguments[0] == 'spatial-example':
        from examples.platform_spatial_example import main as spatial_main
        return spatial_main(arguments[1:])
    if arguments and arguments[0] == 'tendon-family':
        from examples.platform_tendon_family import main as family_main
        return family_main(arguments[1:])
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('spatial-example', help='统一场景真实示例：prepare/run/compare；数学运行自动阻断 MuJoCo')
    sub.add_parser('tendon-family', help='串联多段候选与 MATLAB/MuJoCo：prepare/build/run/compare/view')
    sub.add_parser('catalog', help='只读列出任务、工具与扩展能力')
    check = sub.add_parser('check', help='只读检查定义、能力和可执行配置')
    check.add_argument('config')
    init = sub.add_parser('project-create', help='显式创建独立开发项目与授权锚点')
    init.add_argument('root'); init.add_argument('config')
    create = sub.add_parser('create', help='创建冻结会话，不执行模型或后端')
    create.add_argument('root'); create.add_argument('config')
    for command, description in [('status', '只读状态与统一结果'), ('resources', '只读剩余额度'), ('events', '只读因果事件链'),
        ('inputs', '只读模型实际输入'), ('context', '只读下一轮上下文预览'), ('compatibility', '只读恢复／版本迁移检查'),
        ('run', '执行配置中的离线／现有模型闭环'), ('resume', '显式恢复状态，不增加额度'), ('pause', '显式暂停后续调用'),
        ('call', '通过公共边界调用获准工具'), ('search', '执行已登记搜索器'), ('memory', '只读跨运行记忆检索'), ('skills', '只读适用技能')]:
        cmd = sub.add_parser(command, help=description)
        cmd.add_argument('root'); cmd.add_argument('run_id')
        if command == 'call': cmd.add_argument('request')
        if command == 'run': cmd.add_argument('--decisions', help='离线回复 JSON/YAML 文件')
        if command == 'events': cmd.add_argument('--parent')
    evidence = sub.add_parser('evidence', help='只读内容身份对应的证据')
    evidence.add_argument('root'); evidence.add_argument('artifact_id')
    export = sub.add_parser('export', help='显式导出保存结果 HTML，不重新求解')
    export.add_argument('root'); export.add_argument('run_id'); export.add_argument('output')
    history = sub.add_parser('history', help='只读校验历史证据，不补造新字段')
    history.add_argument('root')
    bundle = sub.add_parser('export-bundle', help='显式导出保存原始文件，不求解或评分')
    bundle.add_argument('root'); bundle.add_argument('artifact_id'); bundle.add_argument('output')
    args = parser.parse_args(argv)
    from tools.platform_config import load
    from tools.platform_registry import registry
    from tools.platform_store import Store, plain
    try:
        if args.command == 'catalog':
            result = dict(contract_version='1.0.0', capabilities=registry().catalog())
        elif args.command == 'check':
            from tools.platform_tasks import report
            result = report(load(args.config))
            if 'snapshot' in result:
                snapshot = result.pop('snapshot')
                result['run_config'] = dict(run_id=snapshot['input']['run_id'], input_identity=snapshot['input_identity'],
                    instance_identity=snapshot['instance_identity'], dependencies=len(snapshot['dependencies']))
        elif args.command == 'project-create':
            result = Store(args.root).create(load(args.config))
        elif args.command == 'create':
            from tools.platform_host import Host
            value = load(args.config)
            session = Host(args.root, value['run_id']).create(value)
            result = dict(run_id=session['run_id'], status=session['status'], input_identity=session['snapshot']['input_identity'],
                instance_identity=session['snapshot']['instance_identity'], approval=session['snapshot']['approval'])
        elif args.command == 'evidence':
            from schemas.platform import EvidenceRef
            result = Store(args.root).artifact(EvidenceRef(artifact_id=args.artifact_id))
        elif args.command == 'history':
            from tools.platform_history import inspect_history
            result = inspect_history(args.root)
        elif args.command == 'export-bundle':
            from tools.platform_view import export_bundle
            result = export_bundle(Store(args.root), args.artifact_id, Path(args.output).resolve())
        else:
            from tools.platform_host import Host
            host = Host(args.root, args.run_id)
            if args.command == 'status':
                from tools.platform_view import result_view
                result = result_view(host)
            elif args.command == 'resources': result = host.store.remaining(args.run_id)
            elif args.command == 'events': result = host.store.events(args.run_id, args.parent)
            elif args.command == 'context': result = host.context()
            elif args.command == 'compatibility': result = host.compatibility()
            elif args.command == 'inputs':
                result = [dict(event=e, payloads=[host.store.artifact(r) for r in e['inputs']])
                    for e in host.store.events(args.run_id) if e['kind'] == 'context_delivery']
            elif args.command == 'call': result = host.invoke(load(args.request))
            elif args.command == 'resume': host.resume(); result = dict(status='running')
            elif args.command == 'pause':
                result = host.invoke(dict(request_id='pause-' + __import__('uuid').uuid4().hex, tool_id='session.control',
                    arguments=dict(status='paused', reason='本地用户暂停'), reason='本地用户暂停'))
            elif args.command == 'run':
                adapter = None
                if args.decisions:
                    from tools.platform_models import OfflineAdapter
                    adapter = OfflineAdapter(load(args.decisions)['decisions'])
                session = host.run(adapter)
                result = dict(run_id=session['run_id'], status=session['status'], turns=session['state']['turn'],
                    stop_reason=session['state'].get('stop_reason'), last_receipt=session['state'].get('last_receipt'))
            elif args.command == 'search':
                from tools.platform_search import run_search
                result = run_search(host)
            elif args.command == 'memory':
                inp = host.store.session(args.run_id)['snapshot']['input']
                result = [plain(e) for e in host.store.memories(dict(task_family=inp['task']['family'], task_version=inp['task']['task_version'], tags=[]))]
            elif args.command == 'skills':
                from tools.platform_skills import applicable
                result = applicable(host, None)
            elif args.command == 'export':
                from tools.platform_view import export_html
                result = export_html(host, Path(args.output).resolve())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if isinstance(result, dict) and (result.get('errors') or result.get('execution_status') in ('failed', 'rejected', 'unknown')) else 0
    except (ValueError, KeyError, OSError) as exc:
        print(json.dumps(dict(status='error', message=str(exc)), ensure_ascii=False, indent=2))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
