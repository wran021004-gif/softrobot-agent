"""Saved structural versions and exact parameter diffs; no inferred ancestry."""
from pathlib import Path
import json,csv,sqlite3
O=Path(__file__).resolve().parent;ROOT=O.parents[1];FIVE=O.parent/'five_task_completion_20261113'
def rd(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(name,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with (O/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
def changes(a,b,path=''):
    if a==b:return []
    if isinstance(a,dict) and isinstance(b,dict):return [v for k in sorted(set(a)|set(b)) for v in changes(a.get(k,'unavailable'),b.get(k,'unavailable'),path+'/'+k)]
    if isinstance(a,list) and isinstance(b,list) and len(a)==len(b):return [v for i,(aa,bb) in enumerate(zip(a,b)) for v in changes(aa,bb,path+'/'+str(i))]
    return [dict(path=path,before=a,after=b)]
bindings=rd(O/'SOURCE_DATA/MODEL_BINDINGS.json');sources=[]
for tid,bb in bindings.items():
    if tid in ['T01','T04','T07','T09','T10']:
        top=next(p for p in FIVE.iterdir() if p.is_dir() and p.name.startswith(tid+'_'))
        for s in rd(top/'COST_REPORT.json')['studies']:sources.append((tid,s['study_id'],Path(s['store'])/'platform.sqlite'))
    else:sources.append((tid,bb[0]['run_id'],Path(bb[0]['store'])))
rows=[]
for tid,run,sp in sources:
    c=sqlite3.connect(sp.as_uri()+'?mode=ro',uri=True);groups={}
    for rowid,aid,body in c.execute("select rowid,id,body from artifacts where media='application/json' and length(body)<1800000 order by rowid"):
        try:v=json.loads(body)
        except Exception:continue
        if not isinstance(v,dict) or not all(k in v for k in ['resolved_parameters','configuration','candidate_id']):continue
        st=v.get('configuration',{}).get('robot',{}).get('structure')
        if not st:continue
        key=json.dumps(st,sort_keys=True)
        if key not in groups:groups[key]=dict(first_rowid=rowid,refs=[],candidate_ids=[],candidate=v,structure=st)
        groups[key]['refs'].append(aid);groups[key]['candidate_ids'].append(v['candidate_id'])
    previous=None
    for i,g in enumerate(groups.values()):
        st=g['structure'];data=st.get('data',st);comps=data.get('components',[]);segments=[v for v in comps if v.get('kind')=='flexible_segment'];td=data.get('tendons',[])
        p=O/'SOURCE_DATA/CANDIDATES'/tid/(g['refs'][0]+'.json');p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(dict(task_id=tid,run_id=run,store=str(sp),candidate_artifact_refs=g['refs'],candidate=g['candidate']),ensure_ascii=False,indent=2),encoding='utf-8')
        delta=changes(previous['structure'],st) if previous else []
        rows.append(dict(task_id=tid,run_id=run,structure_version_within_run=i+1,ordering_basis='first artifact insertion rowid within this run; not inferred parentage',candidate_artifact_refs=json.dumps(g['refs']),candidate_ids=json.dumps(list(dict.fromkeys(g['candidate_ids']))),
            segment_count=len(segments),segment_lengths_m=json.dumps([v['length_m'] for v in segments]),segment_young_pa=json.dumps([v.get('physics',{}).get('young_pa','unavailable') for v in segments]),
            sections_json=json.dumps([v.get('sections') for v in segments]),tendon_count=len(td),tendon_routes_json=json.dumps(td),
            rigid_components_json=json.dumps([v for v in comps if v.get('kind')!='flexible_segment']),previous_comparison_ref=previous['refs'][0] if previous else 'unavailable',
            exact_changes_vs_previous_stored_structure=json.dumps(delta,ensure_ascii=False),causal_parent='unavailable; see explicitly stated research decisions',source_reference=str(sp)+'#artifacts/'+g['refs'][0],saved_candidate=str(p)))
        previous=g
    c.close()
# Preserve all nine physical PHS candidates and existing scope-labelled progress.
phs=ROOT/'runs/phs2d-paper-data-20261112';pr=[]
for name in ['F0','F1','F2','F3','F4','F5','F6','F7','F8']:
    p=phs/'SOURCE_EXTRACTS'/f'{name}_CANDIDATE.json'
    if p.exists():pr.append(dict(task_id='PHS-2D',candidate=name,source_reference=str(p),model_xml=str(phs/'VISUAL_XML'/f'{name}_physical_reference.xml'),visual_xml=str(phs/'VISUAL_XML'/f'{name}_visual.xml')))
write('CANDIDATE_EVOLUTION.csv',rows);write('SOURCE_DATA/PHS_CANDIDATE_INDEX.csv',pr)
progress=list(csv.DictReader((phs/'CANDIDATE_PROGRESS.csv').open(encoding='utf-8-sig')))
for r in progress:
    for k,v in r.items():
        if v=='':r[k]='unavailable'
write('FIGURE_DATA/PHS_CANDIDATE_PROGRESS.csv',progress)
print('Physical structure rows',len(rows),'PHS candidates',len(pr),'progress rows',len(progress))
