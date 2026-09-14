"""Focused native video dispatch check on one explicitly supplied saved candidate."""
import argparse
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from schemas.dynamic_workbench import RenderVideo
from tools.artifact_tools import file_hash
from tools.dynamic_campaign import DynamicCampaign
from tools.state_io import read, atomic_json
from tools.workbench import owner


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path)
    parser.add_argument('--candidate',required=True)
    args=parser.parse_args();root=args.root.resolve()
    with owner(root):
        # Deliberately use the real dispatch with no submit/resume: this offline
        # check must not reserve model/tool/decision budgets or restart an experiment.
        book=DynamicCampaign.__new__(DynamicCampaign)
        book.root=root;book.state=read(root/'state.json');book.ledger=read(root/'budget.json')
        before=copy.deepcopy(book.state);budget_hash=file_hash(root/'budget.json')
        payload,metrics=book.build_model_request()
        schema=next(t['function'] for t in payload['tools'] if t['function']['name']=='render_simulation_video')
        assert 'result_ref' in schema['parameters']['required'] and metrics['total_bytes']<=60000
        assert 'do not claim visual understanding' in payload['messages'][0]['content']
        c=book.candidate(args.candidate);receipts=[]
        for backend in ('matlab','mujoco'):
            params=RenderVideo(result_ref=c['results'][backend]['result_ref'],backend=backend,
                               t_start_s=.2,t_end_s=.6,fps=10).model_dump()
            print('Dispatching native video: '+backend,flush=True)
            receipt=book.dispatch('render_simulation_video',params,[params['result_ref']],
                                  'Inspect the saved motion during this short interval.')
            assert receipt['status']=='completed' and receipt['backend_solves']==0
            manifest=read(root/receipt['metadata_ref'])
            assert receipt['frame_count']==5
            assert abs(receipt['t_start_s']-.2)<1e-9 and abs(receipt['t_end_s']-.6)<1e-9
            assert max(len(json.dumps(receipt).encode()),0)<2000
            assert (root/receipt['video_ref']).read_bytes()[4:8]==b'ftyp'
            assert all(file_hash(root/ref)==h for ref,h in manifest['source_hashes'].items())
            receipts.append(receipt)
        print('Repeating the identical MuJoCo dispatch to check cache',flush=True)
        cached=book.dispatch('render_simulation_video',params,[params['result_ref']],'Reuse the same saved-motion recording.')
        assert cached['cached'] and cached['video_ref']==receipts[-1]['video_ref']
        assert {k:v for k,v in book.state.items() if k!='evidence'}=={k:v for k,v in before.items() if k!='evidence'}
        assert all(book.state['evidence'][k]==v for k,v in before['evidence'].items())
        assert file_hash(root/'budget.json')==budget_hash
        # Publish only new derived evidence; preserve status, selection and all counters.
        atomic_json(root/'state.json',book.state)
        version=metrics['prompt_version']
        atomic_json(root/f"inputs/prompt_versions/{version['effective_sha256']}.json",version)
        book.render()
        from tools.dynamic_view import render_candidate
        for backend in ('matlab','mujoco'):render_candidate(root,c,backend)
        page=(root/'index.html').read_text(encoding='utf8')
        assert all(r['video_ref'] in page for r in receipts)
        report=dict(status='PASS',candidate_id=args.candidate,request_bytes=metrics['total_bytes'],
                    receipts=receipts,cache_receipt=cached,model_calls=0,backend_solves=0,scoring_calls=0,
                    campaign_fields_and_budget_unchanged=True)
        atomic_json(root/'observations/video_tool_validation.json',report)
        print(json.dumps(report,ensure_ascii=True),flush=True)


if __name__=='__main__':main()
