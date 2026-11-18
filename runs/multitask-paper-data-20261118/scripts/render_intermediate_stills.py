"""Render archived intermediate states with the already fixed final-task camera.

Only reads recorded states; never steps, optimizes, or invents model geometry.
"""
import csv,json
from pathlib import Path
import numpy as np
import mujoco
from extract_render_inputs import O,read,save,csvout,native
from render_native_assets import visual_xml,assign,camera,png,W,H

CHOICES=[('T01',3,'initial_earlier',[(0.,'initial'),(.3,'mid'),(.6,'final')]),
         ('T02',0,'previous_modulus',[(0.,'initial'),(.3,'loaded'),(.6,'final')]),
         ('T04',0,'earlier_native_route',[(0.,'initial'),(4.5,'tracking'),(9.5,'tracking_later')]),
         ('T08',7,'initial_payout',[(4.,'unloaded'),(7.99,'low_load'),(11.99,'middle_load'),(15.99,'high_load'),(20.,'recovery')]),
         ('T09',0,'first_interface_replay',[(0.,'initial'),(.5,'contact'),(1.2,'hold'),(2.,'final')])]

def select_states(row,desired):
    src=json.loads(row['state_sources'])[0];p=Path(native(src['path']));states=[]
    if p.suffix=='.csv':
        nearest=[None]*len(desired);dist=[float('inf')]*len(desired)
        with p.open(encoding='utf-8-sig',newline='') as f:
            for i,r in enumerate(csv.DictReader(f)):
                t=float(r[src['time_field']])
                for k,(want,label) in enumerate(desired):
                    if abs(t-want)<dist[k]:
                        dist[k]=abs(t-want);nearest[k]=dict(label=label,index=i,time_s=t,qpos=[float(r[v]) for v in src['qpos_fields']],source=src['path']+f'#csvrow/{i}')
        states=nearest
    else:
        d=read(p)
        if isinstance(d,list):
            times=np.array([r[src['time_field']] for r in d]);qs=[r[src['qpos_field']] for r in d]
        else:
            arr=d['task_evidence']['arrays'];times=np.array(arr[src['time_field']]);qs=arr[src['qpos_field']]
        for want,label in desired:
            i=int(np.argmin(abs(times-want)));states.append(dict(label=label,index=i,time_s=float(times[i]),qpos=qs[i],source=src['path']+src.get('pointer','/')+f'/{i}'))
    return states,src

def main():
    manifest=read(O/'SCREENSHOT_MANIFEST.json');extras=[]
    for tid,i,label,desired in CHOICES:
        rows=list(csv.DictReader((O/tid/'recorded_replay_model_index.csv').open(encoding='utf-8-sig')));r=rows[i];states,src=select_states(r,desired)
        # Run provenance stays attached to its own request/Store, never the final run.
        req=read(r['original_request']);run=req.get('run_id',req.get('context',{}).get('run_id','unavailable; exact original request retained'))
        record=dict(task_id=tid,condition_id=label,candidate_id=r['candidate_id'],run_id=run,source_xml=r['model_xml'],state_source=src,states=states,original_request=r['original_request'],original_store=r['store'],role=r['role'],acceptance='stage-specific original evidence; not counted as final acceptance')
        xp=O/tid/'VISUAL_XML'/f'{label}_visual.xml';model,_=visual_xml(r['model_xml'],xp);cam=read(O/tid/'VISUAL_XML/CAMERA_SETTINGS.json');model.vis.global_.fovy=cam['vertical_span_m'];data=mujoco.MjData(model);renderer=mujoco.Renderer(model,height=H,width=W,max_geom=16000)
        manifest=[m for m in manifest if not(m['task_id']==tid and m['condition_id']==label)]
        for stage,state in [('reference',None)]+[(s['label'],s) for s in states]:
            assign(model,data,state['qpos'] if state else model.qpos0);renderer.update_scene(data,camera=camera(cam));renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=True
            fp=O/tid/'FIGURES_MJ'/f'{tid}_{label}_{stage}_oblique.png';png(fp,renderer.render())
            manifest.append(dict(task_id=tid,condition_id=label,run_id=run,candidate_id=r['candidate_id'],stage=stage,view='oblique',png=str(fp),original_xml=r['model_xml'],visual_xml=str(xp),state_source=state['source'] if state else 'original XML qpos0 reference, not a solved pose',source_index=state['index'] if state else None,time_s=state['time_s'] if state else None,camera=cam,resolution=[W,H],shadow_enabled=True,text_overlay=False,renderer='MuJoCo Renderer 3.13.0; native RGB, no image processing',evidence_role=r['role']))
        renderer.close();record['visual_xml']=str(xp);extras.append(record);csvout(O/tid/'render_manifest.csv',[m for m in manifest if m['task_id']==tid]);print('INTERMEDIATE_STILLS',tid,label,flush=True)
    save(O/'SCREENSHOT_MANIFEST.json',manifest);save(O/'SUPPLEMENTARY/INTERMEDIATE_RENDER_INPUTS.json',extras)

if __name__=='__main__':main()
