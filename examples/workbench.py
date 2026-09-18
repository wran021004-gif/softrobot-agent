"""One entry point for rule decisions, execution, resume and saved-data observation."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    if len(sys.argv)>1 and sys.argv[1]=='platform':
        from examples.development_platform import main as platform_main
        return platform_main(sys.argv[2:])
    if len(sys.argv)>1 and sys.argv[1]=='dynamics':
        from examples.reach_dynamics import main as dynamic_main
        return dynamic_main(sys.argv[2:])
    parser = argparse.ArgumentParser(description='Robot design workbench: fixed rules, bounded tools, persistent evidence and a Chinese observation interface')
    sub = parser.add_subparsers(dest='command', required=True)
    start = sub.add_parser('run', help='Create a bounded loop; at most one simulation by default')
    start.add_argument('--root', help='New workbench directory; DeepSeek defaults to runs/deepseek_design')
    start.add_argument('--design', default='configs/design_tendon_arm.yaml')
    start.add_argument('--history', action='append', default=[])
    start.add_argument('--replay-run', help='Reuse a sealed C1 run read-only; zero new simulation and MATLAB budgets')
    start.add_argument('--deepseek', action='store_true', help='Run the candidate design loop with a single DeepSeek decision model')
    start.add_argument('--model-config', default='configs/deepseek.yaml', help='Model, endpoint and budget configuration; keys read only from the environment')
    start.add_argument('--simulations', type=int, choices=(0, 1), default=1)
    start.add_argument('--steps', type=int)
    resume = sub.add_parser('resume', help='Resume saved state without increasing budgets')
    resume.add_argument('root')
    resume.add_argument('--steps', type=int)
    resume.add_argument('--decision', help='Submit a JSON file conforming to the Decision schema')
    continuation = sub.add_parser('continue', help='Copy a previous run when computational conditions are compatible; retain candidates, evidence and all consumed budgets')
    continuation.add_argument('source')
    continuation.add_argument('--root', required=True, help='New run directory that does not exist')
    continuation.add_argument('--model-config', default='configs/deepseek.yaml')
    continuation.add_argument('--steps', type=int)
    round_start = sub.add_parser('round', help='Import two previous candidates with explicitly authorized new budgets; register once, then use resume')
    round_start.add_argument('source')
    round_start.add_argument('--root', required=True)
    round_start.add_argument('--model-config', default='configs/deepseek.yaml')
    round_start.add_argument('--steps', type=int)
    observe = sub.add_parser('observe', help='Local read-only Chinese page showing current internal stages')
    observe.add_argument('root')
    observe.add_argument('--port', type=int, default=8765)
    context = sub.add_parser('context', help='Read model context without tool execution')
    context.add_argument('root')
    sub.add_parser('catalog', help='JSON tool catalog: execution allowlist and library tool status')
    args = parser.parse_args()
    if args.command == 'run' and args.root is None:
        args.root = 'runs/deepseek_design' if args.deepseek else 'runs/workbench_demo'
    if hasattr(args, 'steps') and args.steps is not None and args.steps < 0:
        parser.error('--steps must be nonnegative')
    if args.command == 'catalog':
        from tools.workbench_catalog import catalog
        print(json.dumps(catalog(), ensure_ascii=False, indent=2))
        return 0
    if args.command == 'observe':
        from tools.workbench_view import serve
        serve(args.root, args.port)
        return 0
    from tools.workbench import Workbench, owner
    from tools.state_io import read
    book = Workbench(args.root)
    if args.command == 'context':
        with owner(book.root):
            book.load()
            print(json.dumps(book.context(), ensure_ascii=False, indent=2))
        return 0
    if args.command == 'run':
        book.create(design=args.design, history=args.history, simulations=args.simulations, replay_run=args.replay_run,
                    deepseek_config=args.model_config if args.deepseek else None)
    elif args.command == 'continue':
        from tools.design_continuation import continue_design
        continue_design(book, args.source, args.model_config)
    elif args.command == 'round':
        from tools.design_continuation import start_round
        start_round(book, args.source, args.model_config)
    state = book.run(steps=args.steps, decision=read(args.decision) if getattr(args, 'decision', None) else None)
    print(f'Workbench status: {state["status"]}; page: {book.root / "index.html"}')
    # Scientific failure is a valid completed workflow, independent of CLI success.
    return 3 if state['status'] == 'WAITING_FOR_KEY' else 2 if state['status'] in ('CAPABILITY_MISSING', 'WAITING_MODEL_RETRY') else 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('Interrupted; use resume to load saved state; consumed budgets are not reset.')
        raise SystemExit(130)
    except (ValueError, OSError) as exc:
        print(f'Workbench execution refused: {exc}', file=sys.stderr)
        raise SystemExit(2)
