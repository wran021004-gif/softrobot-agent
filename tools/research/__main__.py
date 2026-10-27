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
    parser.add_argument('command',choices=['environment','readiness','run','prepare','bind','migrate','execute','rl','diagnose','recover','status','export'])
    parser.add_argument('--spec',type=Path,default=DEFAULT_SPEC)
    parser.add_argument('--plan',type=Path)
    parser.add_argument('--run-id')
    parser.add_argument('--profile')
    parser.add_argument('--request-id')
    parser.add_argument('--reason')
    parser.add_argument('--session-handoff',action='store_true',help='Opt in only after separate live continuation admission')
    parser.add_argument('--restore-only',action='store_true',help='Reopen and verify original SDK/Store recovery without a new Provider request')
    parser.add_argument('--recover-incomplete',action='store_true',help='Dispose a verified settled truncated response via an audited clean-session boundary')
    parser.add_argument('--max-new-provider-requests',type=int,help='Pause after this many new requests including Reporter calls')
    parser.add_argument('--handoff-before-next-request',action='store_true',help='Use independently admitted request-feedback boundary before the next model send')
    parser.add_argument('--handoff-request-bytes',type=int,help='Rotate at a verified paired-feedback boundary when the complete next request reaches this size; requires separate live admission')
    parser.add_argument('--pause-exploration-remaining',type=int,help='Supervisor pause at admitted paired-feedback boundary before remaining science-capable main requests reach this count')
    parser.add_argument('--pause-after-completed-invocations',type=int,help='Supervisor pause after complete SDK invocation and Reporter delivery')
    args=parser.parse_args()
    if args.command=='environment':
        from tools.research.config import resolve
        from tools.research.tool_readiness import execution_environment
        print(json.dumps(execution_environment(resolve(args.spec))))
        return
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
        try:asyncio.run(converse(h,session_handoff=args.session_handoff,
            pause_after_completed_invocations=args.pause_after_completed_invocations,
            handoff_before_next_request=args.handoff_before_next_request,handoff_request_bytes=args.handoff_request_bytes,
            pause_exploration_remaining=args.pause_exploration_remaining,restore_only=args.restore_only,recover_incomplete=args.recover_incomplete,max_new_provider_requests=args.max_new_provider_requests))
        except IncompleteModelOutput as exc:
            print(json.dumps(dict(status='confirmed_incomplete',provider=exc.diagnostic)))
            raise SystemExit(2) from exc
    elif args.command=='export':
        print(json.dumps(export(h)))
        return
    print(json.dumps(packet(h)))

if __name__=='__main__':
    main()
