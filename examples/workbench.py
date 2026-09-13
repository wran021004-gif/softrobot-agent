"""One entry point for rule decisions, execution, resume and saved-data observation."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description='机器人设计工作台：固定规则、受限工具、持久证据与中文观察')
    sub = parser.add_subparsers(dest='command', required=True)
    start = sub.add_parser('run', help='新建有限闭环；默认最多一次仿真')
    start.add_argument('--root', help='新工作台目录；DeepSeek 默认 runs/deepseek_design')
    start.add_argument('--design', default='configs/design_tendon_arm.yaml')
    start.add_argument('--history', action='append', default=[])
    start.add_argument('--replay-run', help='只读复用已封存 C1 运行；新仿真和 MATLAB 预算均为零')
    start.add_argument('--deepseek', action='store_true', help='使用单个 DeepSeek 决策模型开展候选设计循环')
    start.add_argument('--model-config', default='configs/deepseek.yaml', help='模型、接口地址及预算配置；密钥仅从环境读取')
    start.add_argument('--simulations', type=int, choices=(0, 1), default=1)
    start.add_argument('--steps', type=int)
    resume = sub.add_parser('resume', help='继续保存状态；不增加预算')
    resume.add_argument('root')
    resume.add_argument('--steps', type=int)
    resume.add_argument('--decision', help='提交一个符合 Decision schema 的 JSON 文件')
    observe = sub.add_parser('observe', help='本地只读中文页面，动态读取内部阶段')
    observe.add_argument('root')
    observe.add_argument('--port', type=int, default=8765)
    context = sub.add_parser('context', help='读取模型所需上下文，无工具执行')
    context.add_argument('root')
    sub.add_parser('catalog', help='JSON 工具目录：执行白名单及库工具状态')
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
    state = book.run(steps=args.steps, decision=read(args.decision) if getattr(args, 'decision', None) else None)
    print(f'工作台状态：{state["status"]}；页面：{book.root / "index.html"}')
    # Scientific failure is a valid completed workflow, independent of CLI success.
    return 3 if state['status'] == 'WAITING_FOR_KEY' else 2 if state['status'] in ('CAPABILITY_MISSING', 'WAITING_MODEL_RETRY') else 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('已中断；使用 resume 读取保存状态，已消耗预算不会重置。')
        raise SystemExit(130)
    except (ValueError, OSError) as exc:
        print(f'工作台拒绝执行：{exc}', file=sys.stderr)
        raise SystemExit(2)
