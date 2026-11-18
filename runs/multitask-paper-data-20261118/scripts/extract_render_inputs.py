"""Read original selected artifacts and saved states. No model/solver imports."""
from pathlib import Path
import json,csv,sqlite3,os,gc
import numpy as np
O=Path(__file__).resolve().parents[1];ROOT=O.parents[1]
MASTER=ROOT/'paper_experiments/paper_results_master_20261113'
def native(p):
    s=str(Path(p).resolve());return '\\\\?\\'+s if os.name=='nt' and len(s)>240 and not s.startswith('\\\\?\\') else s
def read(p):
    with open(native(p),encoding='utf-8-sig') as f:return json.load(f)
def save(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with open(native(p),'w',encoding='utf-8') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False)
def csvout(p,rs):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);keys=list(dict.fromkeys(k for r in rs for k in r))
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,keys);w.writeheader()
        for r in rs:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else '' if v is None else v for k,v in r.items()})
def db(p):return sqlite3.connect(Path(p).as_uri()+'?mode=ro',uri=True)
def get(c,ref):return json.loads(c.execute('select body from artifacts where id=?',(ref['artifact_id'],)).fetchone()[0])
def uri(b,ref):return str(b['store'])+'#artifacts/'+ref['artifact_id']

def motion_from_arrays(te,source):
    a=te['arrays'];layout=sorted(te['joint_layout'],key=lambda r:r['qpos_address']);names=[r['name'] for r in layout]
    q=np.asarray(a['qpos'],float);ts=np.asarray(a['time_s'],float)
    assert q.ndim==2 and q.shape==(len(ts),len(names)) and np.isfinite(q).all()
    motion=dict(times_s=ts.tolist(),qpos=q.tolist(),joint_names=names,source=source,source_sampling='saved native physics grid; no interpolation',
        tip_m=a.get('tip_m'),tip_velocity_m_s=a.get('tip_velocity_m_s'),contact_force_n=a.get('contact_force_n'),button_q_m=a.get('button_q_m'),
        force_n=a.get('force_n'),control_n=a.get('control_n'),tendon_length_m=a.get('tendon_length_m'),tendon_speed_m_s=a.get('tendon_speed_m_s'))
    return motion
def state_indices(tid,motion,task):
    ts=np.array(motion['times_s']);near=lambda t:int(np.argmin(abs(ts-t)));out=[]
    if tid=='T10':
        tip=np.asarray(motion['tip_m']);target=np.array(task['goal']['data']['target_m']);err=np.linalg.norm(tip-target,axis=1)
        mask=(ts>=.55)&(ts<=ts[-1]);ix=np.where(mask)[0];peak=int(ix[np.argmax(err[ix])]);return [('pre_impact',near(.49)),('impact',near(.525)),('post_impact_peak',peak),('final_hold',len(ts)-1)]
    if tid=='T09':
        force=np.asarray(motion['contact_force_n']);button=np.asarray(motion['button_q_m']);peak=int(np.argmax(button))
        ix=np.where(force>1e-4)[0];contact=int(ix[0]) if len(ix) else near(.5)
        return [('approach',near(.2)),('first_contact',contact),('maximum_depth',peak),('hold',near(1.2)),('release',len(ts)-1)]
    if tid=='T04':return [('initial',0),('first_lobe',near(4.5)),('second_lobe',near(9.5)),('final',len(ts)-1)]
    if tid=='T08':
        return [('initial',0),('low_load',near(7.99)),('middle_load',near(11.99)),('high_load',near(15.99)),('recovery',len(ts)-1)]
    if tid=='T06':return [('initial',0),('middle',near(.3)),('final',len(ts)-1)]
    return [('initial',0),('approach',near(float(ts[-1])*.5)),('final',len(ts)-1)]

def main():
    bindings=read(MASTER/'SOURCE_DATA/MODEL_BINDINGS.json');out=[];metricrows=[];state_manifest=[];source_rows=[]
    for tid,bb in bindings.items():
        for b in bb:
            case=b['condition_name'];con=db(b['store']);result=get(con,b['result_ref']);cand=get(con,b['candidate_ref']);conf=cand.get('configuration',cand.get('effective_configuration'));task=conf['task']
            assert result['candidate']==b['candidate_ref']
            rd=O/tid/'RENDER_INPUTS';save(rd/f'{case}_CANDIDATE.json',cand);save(rd/f'{case}_RESULT.json',result);save(rd/f'{case}_TASK.json',task)
            role='control' if 'frozen' in case else 'required'
            for k,v in result['acceptance']['components'].items():
                metricrows.append(dict(task_id=tid,condition_id=case,condition_role=role,run_id=b['run_id'],candidate_id=b['candidate_ref']['artifact_id'],metric=k,value=v.get('value'),limit=v.get('limit'),unit=v.get('unit'),passed=v.get('passed'),accepted=result['acceptance']['accepted'],source=uri(b,b['result_ref'])+'/acceptance/components/'+k))
            xmls=[p for p in b['xml_files'] if Path(native(p)).exists()]
            assert xmls,(tid,case,b['xml_files'])
            xp=next((p for p in xmls if 'independent' in p and 'baseline' in p),xmls[0])
            variants=[]
            if tid=='T08':
                signalfile=MASTER/'FIGURE_DATA/T08_both_directions_SIGNALS.json';signals=read(signalfile)
                for direction in ['plus_x','minus_x']:
                    ss=[s for s in signals if s['spec']['name']=='joint_position' and s['spec']['entity'].startswith(direction+'__')]
                    tip=next(s for s in signals if s['spec']['name']=='tip_position' and s['spec']['entity'].startswith(direction+'__'))
                    motion=dict(times_s=ss[0]['times_s'],joint_names=[s['spec']['entity'].split('__',1)[1] for s in ss],qpos=np.asarray([s['values'] for s in ss]).reshape(len(ss),-1).T.tolist(),
                        tip_m=tip['values'],source=str(signalfile),original_source=uri(b,b['backend_ref'])+'/signals',source_sampling='exact archived BackendResult signal projection, 10ms grid; no interpolation')
                    variants.append((direction,motion))
            elif b.get('raw_ref'):
                raw=get(con,b['raw_ref']);te=raw['task_evidence'];motion=motion_from_arrays(te,uri(b,b['raw_ref'])+'/task_evidence/arrays');variants.append((case,motion))
                del raw;gc.collect()
            else:
                simref=result['profile']['simulation'];simulation=get(con,simref);te=simulation['data']['data']['task_evidence'];motion=motion_from_arrays(te,uri(b,simref)+'/data/data/task_evidence/arrays');variants.append((case,motion))
                del simulation;gc.collect()
            for condition,motion in variants:
                motion.update(task_id=tid,condition_id=condition,run_id=b['run_id'],candidate_ref=b['candidate_ref'],execution_id=b['execution_id'])
                mp=rd/f'{condition}_MOTION.json';save(mp,motion)
                selected=state_indices(tid,motion,task);states=[]
                for label,index in selected:
                    state=dict(label=label,index=index,time_s=float(motion['times_s'][index]),qpos=motion['qpos'][index],joint_names=motion['joint_names'],source=motion['source']+f'/qpos/{index}',motion_file=str(mp),
                        tip_m=motion['tip_m'][index] if motion.get('tip_m') else None)
                    states.append(state);state_manifest.append(dict(task_id=tid,condition_id=condition,run_id=b['run_id'],candidate_id=b['candidate_ref']['artifact_id'],label=label,time_s=state['time_s'],source_index=index,motion_file=str(mp),original_state_source=state['source'],model_xml=xp))
                sf=rd/f'{condition}_STATES.json';save(sf,states)
                cues=dict(target_m=task['goal']['data'].get('target_m'),axis_local=task['goal']['data'].get('axis_local'),target_axis_world=task['goal']['data'].get('target_axis_world'),
                    path_m=task['goal']['data'].get('vertices_m',[]),axis_vertices_world=task['goal']['data'].get('axis_vertices_world',[]),environment=task['environment']['data'],
                    goal_data=task['goal']['data'],source=uri(b,b['candidate_ref'])+'/configuration/task')
                if tid=='T04':
                    bp=ROOT/'paper_experiments/five_task_completion_20261113/T04_figure_eight_tracking/T04_RUN_03/NATIVE_REFERENCE_BANK.json';bank=read(bp)['reference_bank'];cues['path_m']=[v['target_position_m'] for v in bank];cues['path_source']=str(bp)+'/reference_bank/target_position_m';cues['path_semantics']='polyline through exact stored reference nodes; not new optimized trajectory'
                cp=rd/f'{condition}_CUES.json';save(cp,cues)
                row=dict(task_id=tid,condition_id=condition,source_condition_id=case,condition_role=role,run_id=b['run_id'],candidate_id=b['candidate_ref']['artifact_id'],candidate_ref=b['candidate_ref'],result_ref=b['result_ref'],
                    execution_id=b['execution_id'],source_store=b['store'],source_xml=xp,states_file=str(sf),motion_file=str(mp),cues_file=str(cp),candidate_file=str(rd/f'{case}_CANDIDATE.json'),result_file=str(rd/f'{case}_RESULT.json'),
                    accepted=result['acceptance']['accepted'],actor='Codex expert/surrogate; not a formal Main SDK run',saved_samples=len(motion['times_s']),time_range_s=[motion['times_s'][0],motion['times_s'][-1]],evidence_scope='original selected final execution')
                out.append(row);source_rows.append(dict(task_id=tid,condition_id=condition,source_store=b['store'],result_source=uri(b,b['result_ref']),candidate_source=uri(b,b['candidate_ref']),state_source=motion['source'],model_xml=xp))
            con.close();print('INDEXED',tid,case,flush=True)
    save(O/'FINAL_CASES.json',out);csvout(O/'SUPPLEMENTARY/final_condition_index.csv',out);csvout(O/'SUPPLEMENTARY/selected_state_index.csv',state_manifest);csvout(O/'CROSS_TASK/FINAL_CONSTRAINT_METRICS.csv',metricrows);csvout(O/'SUPPLEMENTARY/source_index_initial.csv',source_rows)
    summary=[dict(task_id=tid,final_cases=sum(r['task_id']==tid and r['condition_role']=='required' for r in out),control_cases=sum(r['task_id']==tid and r['condition_role']=='control' for r in out),all_xml_available=all(Path(native(r['source_xml'])).exists() for r in out if r['task_id']==tid),indexed=True) for tid in bindings]
    csvout(O/'PHASE_A_INVENTORY.csv',summary);print('Phase A final models/states indexed:',len(out),'conditions; no renders and no new science.')
if __name__=='__main__':main()
