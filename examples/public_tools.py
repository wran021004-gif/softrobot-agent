"""Public directory and task-independent offline service CLI."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description='Versioned public tool contracts; no implicit simulation.')
    sub = parser.add_subparsers(dest='command', required=True)
    cat = sub.add_parser('catalog')
    cat.add_argument('--runtime', choices=('services','workbench','dynamics'))
    cat.add_argument('--output')
    cat.add_argument('--markdown',action='store_true',help='Generate the reviewable inventory from the same live directory')
    init = sub.add_parser('init')
    init.add_argument('--root', required=True)
    init.add_argument('--config', required=True)
    init.add_argument('--source')
    init.add_argument('--evidence-ref', action='append', default=[])
    call = sub.add_parser('call')
    call.add_argument('--root', required=True)
    call.add_argument('--request', required=True)
    args = parser.parse_args()
    from tools.state_io import read, atomic_json
    from tools.public_catalog import catalog
    from tools.public_services import ServiceSession
    if args.command == 'catalog':
        output = catalog(args.runtime)
        if args.markdown:
            from tools.public_catalog import markdown_catalog
            text=markdown_catalog(output)
            if args.output:
                Path(args.output).write_text(text,encoding='utf8')
            else:
                print(text)
            return 0
        if args.output:
            atomic_json(Path(args.output), output)
            return 0
    elif args.command == 'init':
        output = ServiceSession(args.root).create(read(Path(args.config)), source_root=args.source, evidence_refs=args.evidence_ref)
    else:
        output = ServiceSession(args.root).invoke(read(Path(args.request)),
            caller=dict(actor_id='local-human', origin='human_cli', transport='cli'))
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 2 if output.get('execution_status') in ('failed','rejected','interrupted','capability_missing') else 0


if __name__ == '__main__':
    raise SystemExit(main())
