"""Round4 explicit finite commands; viewing/export never calls this executor."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['freeze','length','development','catalog','audit','derive','package'])
    parser.add_argument('--resume',action='store_true',help='Explicit charged retry of an interrupted length candidate')
    parser.add_argument('--root',default='runs/round4',help='Saved evidence directory for offline commands')
    args=parser.parse_args()
    if args.action=='freeze':
        from tools.round4_campaign import freeze
        print(freeze())
    elif args.action=='length':
        from tools.round4_campaign import run_campaign
        print(json.dumps(run_campaign(resume=args.resume),ensure_ascii=False))
    elif args.action=='development':
        from tools.round4_validation import run_development
        print(json.dumps(run_development(),ensure_ascii=False))
    elif args.action=='catalog':
        from capabilities.registry import query_tools
        print(json.dumps(query_tools(),ensure_ascii=False,indent=2))
    else:
        from tools import round4_evidence
        print(json.dumps(str(getattr(round4_evidence,args.action)(args.root)),ensure_ascii=False))
