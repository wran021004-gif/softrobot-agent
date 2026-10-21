"""Unified research composition entrypoint."""
import argparse,asyncio,json
from pathlib import Path
from uuid import uuid4
from tools.research.core import prepare,bind,dispatch,diagnose,recover,export,packet,ROOT,DEFAULT_SPEC
from tools.research.state import state
from tools.platform_host import Host
from tools.state_io import read

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['readiness','run','prepare','bind','migrate','execute','rl','diagnose','recover','status','export'])
    parser.add_argument('--spec',type=Path,default=DEFAULT_SPEC)
    parser.add_argument('--plan',type=Path)
    parser.add_argument('--run-id')
    parser.add_argument('--profile')
    parser.add_argument('--request-id')
    parser.add_argument('--reason')
    parser.add_argument('--session-handoff',action='store_true',help='Opt in only after separate live continuation admission')
    args=parser.parse_args()
    if args.command in ('prepare','readiness'):
        h=prepare(args.spec,profile=args.profile)
    else:
        if not args.run_id:
            parser.error('existing-study commands require --run-id; editable sources are not loaded')
        h=Host(ROOT/'runs/research'/args.run_id,args.run_id,actor='unified-research')
        state(h)  # Require an existing frozen session, without source resolution.
    spec=state(h)['spec']
    if args.command=='readiness':
        from tools.research.tool_readiness import check
        print(json.dumps(check(h)))
        return
    if args.command in ('bind','migrate'):
        bind(h,args.reason if args.command=='migrate' else None,spec)
    elif args.command=='rl':
        from tools.research.rl import dispatch as rl_dispatch
        print(json.dumps(rl_dispatch(h,read(args.plan),args.request_id or 'manual-'+uuid4().hex)))
        return
    elif args.command=='execute':
        print(json.dumps(dispatch(h,read(args.plan),args.request_id or 'manual-'+uuid4().hex,origin='engineering')))
        return
    elif args.command=='diagnose':
        print(json.dumps(diagnose(h,state(h)['results'])))
        return
    elif args.command=='recover':
        print(json.dumps(recover(h)))
        return
    elif args.command in ('run','live'):
        from tools.research.agent import converse,IncompleteModelOutput
        try:asyncio.run(converse(h,session_handoff=args.session_handoff))
        except IncompleteModelOutput as exc:
            print(json.dumps(dict(status='confirmed_incomplete',provider=exc.diagnostic)))
            raise SystemExit(2) from exc
    elif args.command=='export':
        print(json.dumps(export(h)))
        return
    print(json.dumps(packet(h)))

if __name__=='__main__':
    main()
