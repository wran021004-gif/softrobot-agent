from pathlib import Path
import json,sqlite3,sys
O=Path(__file__).resolve().parent
P=O.parent;TEN=P/'ten_task_codex_solve_20261112';FIVE=P/'five_task_completion_20261113'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def compact(v):
    if isinstance(v,dict):return {k:(list(x)[:15] if isinstance(x,dict) else f'list[{len(x)}]' if isinstance(x,list) else x) for k,x in v.items()}
    return v
mode=sys.argv[1] if len(sys.argv)>1 else 'overview'
if mode=='overview':
    f=read(FIVE/'FINAL_RESULTS.json')
    print('FIVE',[(t['task_id'],t.get('active_directory'),t.get('directory'),t.get('study_id'),len(t['cases']),list(t)) for t in f['tasks']])
    for t in read(TEN/'ALL_TASKS_TRACE_INDEX.json')['tasks']:
        d=Path(t['folder']);print('TEN',t['task_id'],t.get('active_store'),compact(read(d/'TASK_SPEC.json')))
    print('FIVE_COST',compact(read(FIVE/'COST_REPORT.json')))
    for t in f['tasks']:
        d=FIVE/t['directory'];print('RUNIDX',t['task_id'],read(d/'RUN_INDEX.json') if (d/'RUN_INDEX.json').exists() else None)
elif mode=='task':
    for tid in sys.argv[2:]:
        five=next((t for t in read(FIVE/'FINAL_RESULTS.json')['tasks'] if t['task_id']==tid),None)
        d=FIVE/five['directory'] if five else Path(next(t['folder'] for t in read(TEN/'ALL_TASKS_TRACE_INDEX.json')['tasks'] if t['task_id']==tid))
        print('\nTASK',tid,d)
        for nm in ['CURRENT_SUCCESS.json','TASK_RUNS.json','COST_REPORT.json','STUDY_CONFIG.json','TASK_PROTOCOL.json']:
            if (d/nm).exists():print(nm,compact(read(d/nm)))
        store=Path(next(t['active_store'] for t in read(TEN/'ALL_TASKS_TRACE_INDEX.json')['tasks'] if t['task_id']==tid)) if not five else None
        if five:
            idx=read(d/'RUN_INDEX.json') if (d/'RUN_INDEX.json').exists() else {};active=idx.get('active_run')
            print('ACTIVE',active)
            store=Path(active)/'STORE/platform.sqlite' if active else d/'STORE/platform.sqlite'
        print('STORE',store,store.exists())
        if store.exists():
            c=sqlite3.connect(store.as_uri()+'?mode=ro',uri=True)
            print('TABLES',c.execute("select name from sqlite_master where type='table'").fetchall())
            print('SESSIONS',c.execute('select run_id,status from sessions').fetchall());c.close()
elif mode=='details':
    for t in read(FIVE/'FINAL_RESULTS.json')['tasks']:
        d=FIVE/t['directory'];co=read(d/'COST_REPORT.json');print('TASK',t['task_id'],d);print('COSTSTUDIES',[compact(x) for x in co['studies']]);print('DIRS',[x.name for x in d.iterdir() if x.is_dir()]);print('FILES',[x.name for x in d.iterdir() if x.is_file() and x.suffix=='.json'][:30]);print('CASE',compact(t['cases'][0]))
    for tid in ['T02','T03','T05','T06','T08']:
        d=Path(next(t['folder'] for t in read(TEN/'ALL_TASKS_TRACE_INDEX.json')['tasks'] if t['task_id']==tid))
        print('TEN_RESULT',tid,compact(read(d/'FINAL_RESULT.json')));print('PHYSICALINDEX',read(d/'PHYSICAL_EVIDENCE/INDEX.json') if (d/'PHYSICAL_EVIDENCE/INDEX.json').exists() else None)
elif mode=='rawkeys':
    for t in read(TEN/'ALL_TASKS_TRACE_INDEX.json')['tasks']:
        tid=t['task_id']
        if tid not in ['T02','T03','T05','T06','T08']:continue
        d=Path(t['folder']);f=read(d/'FINAL_RESULT.json');print(tid,'RESULT_KEYS',list(f));pi=read(d/'PHYSICAL_EVIDENCE/INDEX.json');print('PI_TYPE',type(pi).__name__)
        if isinstance(pi,list):print('PI',len(pi),[(a.get('reference'),a.get('accepted'),a.get('condition_id'),a.get('raw_reference')) for a in pi])
        else:print('PI_KEYS',list(pi))
    print('TRACE',read(FIVE/'FINAL_RESULTS.json')['tasks'][0]['directory'])
    for p in [FIVE/'T04_figure_eight_tracking/T04_RUN_03/STUDY_TRACE.jsonl',TEN/'T02_M2_loaded_hold/STUDY_TRACE.jsonl']:
        rr=[json.loads(l) for l in p.read_text(encoding='utf-8-sig').splitlines()];print(p,len(rr));print(json.dumps(rr[0],ensure_ascii=False)[:1700]);dd=[r for r in rr if 'decision' in str(r.get('tool',''))];print('DECISION',json.dumps(dd[0] if dd else rr[1],ensure_ascii=False)[:2000])
