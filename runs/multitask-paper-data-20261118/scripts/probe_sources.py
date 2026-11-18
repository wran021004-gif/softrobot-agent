from pathlib import Path
import json,csv,sqlite3,sys
O=Path(__file__).resolve().parents[1]
ROOT=O.parents[1]
MASTER=ROOT/'paper_experiments/paper_results_master_20261113'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def outline(v):
    if isinstance(v,dict):return {k:(list(z)[:20] if isinstance(z,dict) else ['list',len(z),list(z[0])[:12] if z and isinstance(z[0],dict) else ''] if isinstance(z,list) else z) for k,z in v.items()}
    if isinstance(v,list):return dict(length=len(v),first=outline(v[0]) if v else None)
    return v
def get(db,ref):
    aid=ref['artifact_id'] if isinstance(ref,dict) else ref
    return json.loads(db.execute('select body from artifacts where id=?',(aid,)).fetchone()[0])
def main():
    mode=sys.argv[1] if len(sys.argv)>1 else 'overview'
    bindings=read(MASTER/'SOURCE_DATA/MODEL_BINDINGS.json')
    if mode=='overview':
        for tid in bindings:
            bb=bindings[tid];p=MASTER/'SOURCE_DATA/ANIMATION_INPUTS'/f'{tid}.json'
            motion=read(p) if p.exists() else {}
            print(tid,'BIND',outline(bb),'MOTION',outline(motion),flush=True)
    elif mode=='raw':
        tids=sys.argv[2:] or ['T04','T07','T09','T10']
        for tid in tids:
            b=bindings[tid][0];con=sqlite3.connect(Path(b['store']).as_uri()+'?mode=ro',uri=True)
            print(tid,outline(b));r=get(con,b['result_ref']);print('RESULT',outline(r))
            cand=get(con,b['candidate_ref']);print('CAND',outline(cand));print('CONF',outline(cand.get('configuration',cand.get('effective_configuration',{}))))
            if b.get('raw_ref'):
                raw=get(con,b['raw_ref']);print('RAW',outline(raw));print('RAW task_evidence',outline(raw.get('task_evidence',{})))
            con.close()
    elif mode=='sizes':
        for tid,bb in bindings.items():
            b=bb[0];con=sqlite3.connect(Path(b['store']).as_uri()+'?mode=ro',uri=True)
            print(tid,{k:con.execute('select length(body) from artifacts where id=?',(v['artifact_id'],)).fetchone()[0] for k,v in b.items() if k.endswith('_ref') and isinstance(v,dict) and v.get('artifact_id')});con.close()
    elif mode=='t10':
        b=bindings['T10'][0];con=sqlite3.connect(Path(b['store']).as_uri()+'?mode=ro',uri=True);r=get(con,b['result_ref'])
        print('PROFILE',outline(r['profile']));print('SIM',r['profile'].get('simulation'));print('EXECSTRUCT',outline(r['execution'].get('structured_feedback',{})));print('ENV',read(MASTER/'SOURCE_DATA/T10_positive_y_TASK.json')['environment']);print('GOAL',read(MASTER/'SOURCE_DATA/T10_positive_y_TASK.json')['goal'])
        sim=r['profile'].get('simulation')
        if isinstance(sim,dict) and sim.get('artifact_id'):
            v=get(con,sim);print('SIMOBJ',outline(v));print('SIGNAL1',outline(v.get('signals',[{}])[0]));print('DATA',outline(v.get('data',{})))
    elif mode=='activegoal':
        for tid in ['T01','T04','T05','T06','T09']:
            c=bindings[tid][0]['condition_name'];t=read(MASTER/f'SOURCE_DATA/{tid}_{c}_TASK.json');print(tid,'GOAL',t['goal'],'ENV',t['environment'])
if __name__=='__main__':main()
