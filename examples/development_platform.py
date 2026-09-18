"""Unified robot development platform: read-only inspection is explicitly separate from creation and execution."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf8')


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if arguments and arguments[0] == 'route':
        from examples.platform_route import main as route_main
        return route_main(arguments[1:])
    if arguments and arguments[0] == 'spatial-example':
        from examples.platform_spatial_example import main as spatial_main
        return spatial_main(arguments[1:])
    if arguments and arguments[0] == 'tendon-family':
        from examples.platform_tendon_family import main as family_main
        return family_main(arguments[1:])
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('route', help='Persistent LLM cross-layer route: prepare/start/status/resume/result/call')
    sub.add_parser('spatial-example', help='Unified scene example: prepare/run/compare; mathematical runs automatically block MuJoCo')
    sub.add_parser('tendon-family', help='Serial multi-segment candidates and MATLAB/MuJoCo: prepare/build/run/compare/view')
    sub.add_parser('catalog', help='List tasks, tools and extension capabilities without changes')
    check = sub.add_parser('check', help='Inspect definitions, capabilities and executable configurations without changes')
    check.add_argument('config')
    init = sub.add_parser('project-create', help='Explicitly create an independent development project and authorization anchor')
    init.add_argument('root'); init.add_argument('config')
    create = sub.add_parser('create', help='Create a frozen session without running a model or backend')
    create.add_argument('root'); create.add_argument('config')
    for command, description in [('status', 'Read status and unified results'), ('resources', 'Read remaining resources'), ('events', 'Read the causal event chain'),
        ('inputs', 'Read actual model inputs'), ('context', 'Preview the next context without changes'), ('compatibility', 'Check resume and version migration compatibility without changes'),
        ('run', 'Run the configured offline or existing model loop'), ('resume', 'Explicitly resume saved state without increasing budgets'), ('pause', 'Explicitly pause subsequent calls'),
        ('call', 'Call authorized tools through the public boundary'), ('search', 'Run a registered searcher'), ('memory', 'Search memory across runs without changes'), ('skills', 'Read applicable skills')]:
        cmd = sub.add_parser(command, help=description)
        cmd.add_argument('root'); cmd.add_argument('run_id')
        if command == 'call': cmd.add_argument('request')
        if command == 'run': cmd.add_argument('--decisions', help='Offline response JSON/YAML file')
        if command == 'events': cmd.add_argument('--parent')
    evidence = sub.add_parser('evidence', help='Read evidence by content identity')
    evidence.add_argument('root'); evidence.add_argument('artifact_id')
    export = sub.add_parser('export', help='Explicitly export saved results as HTML without new solves')
    export.add_argument('root'); export.add_argument('run_id'); export.add_argument('output')
    history = sub.add_parser('history', help='Verify historical evidence without changes or fabricated fields')
    history.add_argument('root')
    bundle = sub.add_parser('export-bundle', help='Explicitly export saved original files without solving or scoring')
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
                    arguments=dict(status='paused', reason='Paused by local user'), reason='Paused by local user'))
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
