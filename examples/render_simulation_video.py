"""Record one registered result, without resuming a campaign or opening a viewer."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.simulation_video import render_simulation_video
from tools.state_io import read, atomic_json
from tools.workbench import owner


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path)
    parser.add_argument('--result-ref',required=True)
    parser.add_argument('--backend',choices=['matlab','mujoco'],required=True)
    parser.add_argument('--t-start-s',type=float)
    parser.add_argument('--t-end-s',type=float)
    parser.add_argument('--fps',type=int,default=25)
    args=parser.parse_args();root=args.root.resolve()
    with owner(root):
        state=read(root/'state.json')
        receipt=render_simulation_video(root,state['evidence'],args.result_ref,args.backend,
                    args.t_start_s,args.t_end_s,args.fps)
        # Human CLI adds only derived evidence. Model dispatch continues using its
        # existing submit/attempt/tool-call accounting. No load/resume/solver here.
        atomic_json(root/'state.json',state)
        if state.get('version')=='dynamic_workbench_v2':
            from tools.dynamic_campaign import DynamicCampaign
            book=DynamicCampaign.__new__(DynamicCampaign)
            book.root=root;book.state=state;book.ledger=read(root/'budget.json')
            book.render()
        print(json.dumps(receipt,ensure_ascii=True))


if __name__=='__main__':main()
