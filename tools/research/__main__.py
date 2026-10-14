"""Unified research composition entrypoint."""
import argparse,asyncio,json
from pathlib import Path
from uuid import uuid4
from tools.research.core import prepare,bind,dispatch,diagnose,recover,export,packet,ROOT,DEFAULT_SPEC
from tools.research.state import state
from tools.platform_host import Host
from tools.state_io import read

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('command',choices=['run','prepare','bind','migrate','execute','diagnose','live','recover','status','export'])
    parser.add_argument('--spec',type=Path,default=DEFAULT_SPEC); parser.add_argument('--plan',type=Path)
    parser.add_argument('--request-id'); parser.add_argument('--reason'); args=parser.parse_args()
    from tools.research.config import resolve
    spec=resolve(args.spec); h=prepare(args.spec) if args.command=='prepare' else Host(ROOT/'runs/research'/spec['study_id'],spec['study_id'],actor='unified-research')
    if args.command in ('bind','migrate'): bind(h,args.reason if args.command=='migrate' else None,spec)
    elif args.command=='execute': print(json.dumps(dispatch(h,read(args.plan),args.request_id or 'manual-'+uuid4().hex,origin='engineering'))); return
    elif args.command=='diagnose': print(json.dumps(diagnose(h,state(h)['results']))); return
    elif args.command=='recover': print(json.dumps(recover(h))); return
    elif args.command in ('run','live'):
        from tools.research.agent import converse
        asyncio.run(converse(h))
    elif args.command=='export': print(json.dumps(export(h))); return
    print(json.dumps(packet(h)))

if __name__=='__main__': main()
