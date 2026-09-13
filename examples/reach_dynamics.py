"""Round 9 commands, also available as examples/workbench.py dynamics ..."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.dynamic_campaign import DynamicCampaign
from tools.workbench import owner

def main(argv=None):
    p=argparse.ArgumentParser(description='reach_free MATLAB/MuJoCo dynamic workbench')
    p.add_argument('command',choices=['new','resume','tool','observe','context','experiment-start','experiment-resume'])
    p.add_argument('--root',default='runs/round9_reach');p.add_argument('--source',default='runs/round8_ready')
    p.add_argument('--steps',type=int,default=12);p.add_argument('--name');p.add_argument('--arguments',default='{}')
    p.add_argument('--experiment-id',default='llm_reach_v1')
    p.add_argument('--arguments-file');p.add_argument('--reason',default='User-authorized reach development operation')
    p.add_argument('--evidence',action='append');a=p.parse_args(argv)
    if a.steps<0:p.error('steps must be nonnegative')
    book=DynamicCampaign(a.root)
    try:
        if a.command=='new':
            with owner(Path('runs').resolve(),'.round9_budget.lock'):book.create(a.source)
        with owner(book.root):
            if a.command!='new':book.load()
            if a.command=='resume':book.run_model(a.steps)
            elif a.command in ('experiment-start','experiment-resume'):
                if a.command=='experiment-start':book.start_experiment(a.experiment_id)
                elif not book.experiment() or book.experiment()['experiment_id']!=a.experiment_id:
                    p.error('No matching saved experiment; use experiment-start once')
                book.run_model(a.steps);book.render_experiment()
            elif a.command=='tool':
                args=json.loads(Path(a.arguments_file).read_text(encoding='utf8') if a.arguments_file else a.arguments)
                result,ref=book.submit(a.name,args,a.reason,a.evidence or ['history/audit.json']);print(json.dumps(dict(result=result,result_ref=ref),ensure_ascii=True))
            elif a.command=='context':print(json.dumps(book.context(),ensure_ascii=True))
            elif a.command=='observe':
                from tools.dynamic_view import render_candidate
                selected=[book.state['candidates'][0]]
                for backend in ('matlab','mujoco'):
                    cs=[c for c in book.state['candidates'] if c['results'].get(backend,{}).get('complete')]
                    if cs:selected.append(min(cs,key=lambda c:c['results'][backend]['position_error_m']))
                for c in {c['candidate_id']:c for c in selected}.values():
                    for backend,r in c['results'].items():
                        if r.get('complete'):render_candidate(book.root,c,backend)
            book.save();book.render()
            print('status='+book.state['status']+' html='+str(book.root/'index.html'))
    finally:book.close()

if __name__=='__main__':main()
