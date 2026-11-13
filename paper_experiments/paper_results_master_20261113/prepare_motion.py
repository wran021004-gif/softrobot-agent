"""Archive recorded motion and environment state. Rendering inputs only."""
from pathlib import Path
import json,sys,csv
import numpy as np
O=Path(__file__).resolve().parent;sys.path.insert(0,str(O))
from extract_full import db,get
def rd(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sv(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
b=rd(O/'SOURCE_DATA/MODEL_BINDINGS.json');index=[];ad=O/'SOURCE_DATA/ANIMATION_INPUTS';ad.mkdir(exist_ok=True)
for tid,bb in b.items():
    v=bb[0];case=v['condition_name'];c=db(Path(v['store']).parent)
    if tid=='T10':
        for vv in bb:
            xs=list(Path(vv['source_directory']).glob(f'STORE_RESEARCH/sessions/*/executions/{vv["execution_id"]}/backend/robot.xml'))
            vv['xml_files']=[str(p) for p in xs]
    if tid=='T08':
        signals=rd(O/'FIGURE_DATA/T08_both_directions_SIGNALS.json');signals=[s for s in signals if s['spec']['entity'].startswith('plus_x__') and s['spec']['name']=='joint_position']
        times=signals[0]['times_s'];names=[s['spec']['entity'].removeprefix('plus_x__') for s in signals];q=np.array([s['values'] for s in signals]).reshape(len(signals),-1).T.tolist()
        motion=dict(task_id=tid,condition='plus_x',times_s=times,joint_names=names,qpos=q,source=str(O/'FIGURE_DATA/T08_both_directions_SIGNALS.json'),force_semantics='original staged +X load at material_s=0.7; original rigid payload remains in XML')
    elif tid=='T10':
        signals=rd(O/'FIGURE_DATA/T10_positive_y_SIGNALS.json');ss=[s for s in signals if s['spec']['name']=='joint_position'];q=np.array([s['values'] for s in ss]).reshape(len(ss),-1).T.tolist()
        motion=dict(task_id=tid,condition=case,times_s=ss[0]['times_s'],joint_names=[s['spec']['entity'] for s in ss],qpos=q,source=str(O/'FIGURE_DATA/T10_positive_y_SIGNALS.json'),force_semantics='original +Y 0.04 N half-sine pulse, 0.50–0.55 s; force marker is a visual cue only')
    else:
        f=O/'FIGURE_DATA'/f'{tid}_{case}_SAMPLES.json';samples=rd(f);motion=dict(task_id=tid,condition=case,times_s=[s['time_s'] for s in samples],qpos=[s['qpos_rad'] for s in samples],source=str(f))
    if v.get('raw_ref'):
        raw=get(c,v['raw_ref']);te=raw.get('task_evidence',{})
        if te:
            fn=O/'SOURCE_DATA/TASK_TIME_SERIES'/f'{tid}_{case}_FULL_ARRAYS.json';sv(fn,dict(source_store=v['store'],raw_reference=v['raw_ref'],task_evidence=te));motion['full_arrays_source']=str(fn)
            if tid=='T09':
                a=te['arrays'];motion['times_s']=a['time_s'];motion['qpos']=a['qpos'];motion['joint_names']=[j['name'] for j in sorted(te['joint_layout'],key=lambda j:j['qpos_address'])];motion['environment_joints']={'button_slide':a['button_q_m']};motion['contact_force_n']=a['contact_force_n'];motion['source']=str(fn)
    sv(ad/f'{tid}.json',motion);index.append(dict(task_id=tid,condition=motion['condition'],motion_file=str(ad/f'{tid}.json'),source=motion['source'],samples=len(motion['times_s'])))
    c.close()
sv(O/'SOURCE_DATA/MODEL_BINDINGS.json',b)
# One complete recorded PHS condition, streamed once. All other full CSVs remain source-linked.
phs=O.parents[1]/'runs/phs2d-paper-data-20261112';ex=rd(phs/'SOURCE_EXTRACTS/EXECUTION_MANIFEST.json')['codex_nominal'];tr=next(t for t in ex['trace_files'] if t['load_condition']=='s7_positive');f=Path(ex['directory'])/tr['path'];times=[];q=[];forces=[];stages=[]
with f.open(encoding='utf-8',newline='') as stream:
    reader=csv.DictReader(stream)
    for i,r in enumerate(reader):
        if i%400!=0 and i!=tr['physics_steps']-1:continue
        times.append(float(r['time_s']));q.append([float(r[f'qpos_{j}']) for j in range(112)]);forces.append([float(r['force_x_n']),float(r['force_y_n']),float(r['force_z_n'])]);stages.append(r['stage'])
sv(ad/'PHS-2D.json',dict(task_id='PHS-2D',condition='s7_positive',times_s=times,qpos=q,force_n=forces,stage=stages,source=str(f),sampling='every 400th archived row plus final row; no state interpolation'))
index.append(dict(task_id='PHS-2D',condition='s7_positive',motion_file=str(ad/'PHS-2D.json'),source=str(f),samples=len(times)))
sv(O/'SOURCE_DATA/MOTION_INDEX.json',index)
print('Motion inputs',len(index))
