"""Reuse original PHS-2D saved episodes as supplementary animation inputs."""
from extract_render_inputs import *
def main():
    phs=ROOT/'runs/psd2d-core-only-20261112';old=ROOT/'runs/phs2d-paper-data-20261112';cases=read(O/'FINAL_CASES.json');cases=[c for c in cases if c['task_id']!='PHS-2D']
    spec=[('F8_s7_positive','F8',phs/'fresh-store/physical_replay/c0bb1929d86e453a89ac6d1ba285ae47/result.json',8),
          ('F8_s7_negative','F8',phs/'fresh-store/physical_replay/c0bb1929d86e453a89ac6d1ba285ae47/result.json',9),
          ('F3_s7_positive','F3',phs/'fresh-store/analyses/400e00da7b404d7cbd3288bdf728f076/result.json',0)]
    cached=None;data=None
    for label,candidate,rp,ei in spec:
        if rp!=cached:data=read(rp);cached=rp
        raw=data if candidate=='F8' else data['structure_research']['records'][0]['mechanics']['dynamic_execution'];e=raw['episodes'][ei];samples=e['samples'];cd=read(old/f'SOURCE_EXTRACTS/{candidate}_CANDIDATE.json');task=cd['configuration']['task'];condition=e['load_condition'];rd=O/'PHS-2D/RENDER_INPUTS'
        motion=dict(task_id='PHS-2D',condition_id=condition,times_s=[s['time_s'] for s in samples],qpos=[s['qpos_rad'] for s in samples],joint_names=raw['coordinate_order'],tip_m=[s['tip_m'] for s in samples],tip_velocity_m_s=[s['tip_velocity_m_s'] for s in samples],source=str(rp)+f'#/episodes/{ei}' if candidate=='F8' else str(rp)+'#/structure_research/records/0/mechanics/dynamic_execution/episodes/0',source_sampling='exact archived 10ms episode samples; shared unloaded record retained, no integration')
        mp=rd/f'{label}_MOTION.json';save(mp,motion);save(rd/f'{label}_CANDIDATE.json',cd);ts=np.array(motion['times_s']);states=[]
        for stage,t in [('unloaded',4.),('loading',4.25),('loaded_final',8.)]:
            i=int(np.argmin(abs(ts-t)));states.append(dict(label=stage,index=i,time_s=float(ts[i]),qpos=motion['qpos'][i],joint_names=motion['joint_names'],source=motion['source']+f'/samples/{i}/qpos_rad'))
        sf=rd/f'{label}_STATES.json';save(sf,states);cp=rd/f'{label}_CUES.json';save(cp,dict(goal_data=task['goal']['data'],environment=task['environment']['data'],target_m=None,path_m=[],source=str(old/f'SOURCE_EXTRACTS/{candidate}_CANDIDATE.json')+'/configuration/task'))
        xp=phs/'fresh-store/physical_replay/c0bb1929d86e453a89ac6d1ba285ae47/passive.xml' if candidate=='F8' else rp.parent/'dynamic_0/passive.xml'
        cases.append(dict(task_id='PHS-2D',condition_id=label,source_condition_id=condition,force_condition_id=condition,condition_role='reference_accepted' if candidate=='F8' else 'rejected_research_episode',run_id='psd2d-core-fresh-20261112',candidate_id=candidate,candidate_ref=read(old/'SOURCE_EXTRACTS/CANDIDATE_MANIFEST.json')[candidate]['reference'],source_xml=str(xp),states_file=str(sf),motion_file=str(mp),cues_file=str(cp),candidate_file=str(rd/f'{label}_CANDIDATE.json'),accepted=candidate=='F8',actor='Codex public API research; not formal Main SDK',saved_samples=len(samples),time_range_s=[float(ts[0]),float(ts[-1])],evidence_scope='PHS reference only; not merged into ten other FULL task results'))
        print('PHS_REFERENCE_INDEXED',label)
    save(O/'FINAL_CASES.json',cases)
if __name__=='__main__':main()
