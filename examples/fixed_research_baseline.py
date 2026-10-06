"""Executable fixed baseline over the shared first-study path."""
from pathlib import Path
import argparse
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def main():
    from tools.runtime_identity import require_softagent_runtime
    from tools.research_spec import load_spec
    from tools.fixed_research import baseline_plan, run_smoke, run_study, export_evidence
    from tools.state_io import atomic_json
    require_softagent_runtime()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('plan','smoke','study'),default='plan')
    parser.add_argument('--spec',default='configs/research/reach_hold_v1.json')
    parser.add_argument('--output',default='runs/research_first_study_20261006')
    parser.add_argument('--export')
    args=parser.parse_args(); spec=load_spec(args.spec)
    if args.mode=='plan':
        plan=baseline_plan(spec);atomic_json(Path(args.output)/'fixed_plan.json',plan)
        print('Fixed baseline plan prepared; zero simulations or provider requests.')
        return
    delivery=(run_smoke if args.mode=='smoke' else run_study)(args.output,spec)
    if args.export: export_evidence(args.output,args.export)
    print('Mode:',args.mode,'Status:',delivery.get('status',delivery.get('launch_status')))
    print('Actual budget:',delivery['budget']['used'])
    if args.mode=='smoke' and delivery['status']!='complete_integration':sys.exit(1)


if __name__=='__main__':main()
