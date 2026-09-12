"""Plan, execute once, resume, inspect, replay/export and audit without rerunning history."""
from pathlib import Path
import argparse
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['plan-only','execute','resume','audit','report','worker','inspect','environment','replay'])
    p.add_argument('path',nargs='?'); p.add_argument('--output'); args=p.parse_args()
    from tools.closeout_state import read,atomic_json
    from tools.spec_tools import ROOT
    if args.mode=='audit':
        from tools.closeout_audit import audit,audit_bundle
        path=Path(args.path); result=audit_bundle(path) if path.suffix=='.zip' else audit(path.parent,path.name)
        print(json.dumps(result,indent=2)); return
    if args.mode=='report':
        from tools.closeout_audit import export_report
        export_report(args.path,args.output or ROOT/'docs/round3_deterministic_closeout_result.md'); return
    if args.mode=='inspect':
        print(json.dumps(read(Path(args.path)/'closeout_summary.json'),indent=2)); return
    if args.mode=='environment':
        from tools.closeout_validation import environment_check
        print(json.dumps(environment_check(),indent=2)); return
    if args.mode=='replay':
        from tools.closeout_validation import replay
        print(json.dumps(replay(args.path,args.output),indent=2)); return
    from tools.closeout_campaign import make_plan,run_campaign,worker
    if args.mode=='plan-only':
        output=Path(args.output or ROOT/'configs/experiments/round3_closeout_plan.json')
        atomic_json(output,make_plan()); print(output)
    elif args.mode=='worker': worker(args.path)
    elif args.mode=='execute': run_campaign(args.path or ROOT/'configs/experiments/round3_closeout_plan.json')
    elif args.mode=='resume': run_campaign(resume=args.path)


if __name__=='__main__': main()
