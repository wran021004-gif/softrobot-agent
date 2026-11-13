from extract_full import *
import numpy as np

def main():
    b=read(O/'SOURCE_DATA/MODEL_BINDINGS.json');rs=csvread(O/'RESOURCE_COSTS.csv');cost_details={};models={}
    for tid,bindings in b.items():
        for bind in bindings:
            c=db(bind['store']);result=get(c,bind['result_ref']);raw=get(c,bind['raw_ref']) if bind['raw_ref'] else None
            if raw and raw.get('samples'):
                samples=raw['samples'];dump(f'FIGURE_DATA/{tid}_{bind["condition_name"]}_SAMPLES.json',samples)
                if bind['condition_name']==bindings[0]['condition_name']:print(tid,'SAMPLE_KEYS',list(samples[0]),flush=True)
            elif tid=='T10':
                simref=result['profile']['simulation'];sim=get(c,simref)
                print(tid,bind['condition_name'],'SIM',list(sim),flush=True)
                if sim.get('signals'):dump(f'FIGURE_DATA/{tid}_{bind["condition_name"]}_SIGNALS.json',sim['signals'])
                if sim.get('data'):
                    dump(f'SOURCE_DATA/{tid}_{bind["condition_name"]}_SIM_INDEX.json',dict(keys=list(sim['data']),source=simref))
                    print('SIM_DATA_KEYS',list(sim['data']),flush=True)
                    data=sim['data'].get('data',sim['data'])
                    if data.get('samples'):dump(f'FIGURE_DATA/{tid}_{bind["condition_name"]}_SAMPLES.json',data['samples'])
                # Search only exact execution folders from the selected result refs.
                sd=Path(bind['store']).parent
                for top in ['controller_executions','controllers','control_executions','controller','execution','nmpc']:
                    xp=sd/top/bind['execution_id']
                    if xp.exists():print('EXDIR',xp,[p.name for p in xp.iterdir()][:20],flush=True)
            c.close()
        # All raw vectors for a selected completion Study, plus its recorded failed analyses, retain distinct units.
        if tid in ['T01','T04','T07','T09','T10']:
            co=read(Path(bindings[0]['source_directory'])/'COST_REPORT.json')
            for s in co['studies']:
                sp=Path(s['store']);c=db(sp);session=json.loads(c.execute('select state from sessions where run_id=?',(s['study_id'],)).fetchone()[0])
                print('STATE',tid,list(session),flush=True)
                calls=[]
                for runid,requestid,charge,res in c.execute('select run_id,request_id,charged,resources from calls'):
                    calls.append(dict(run_id=runid,request_id=requestid,charged=json.loads(charge),resources=json.loads(res)))
                # Count distinct stored result types with bounded JSON sizes, avoiding trajectory blob scans.
                candidates=[];phys=[];native=[]
                for aid,body in c.execute("select id,body from artifacts where media='application/json' and length(body)<1800000"):
                    try:x=json.loads(body)
                    except:continue
                    if isinstance(x,dict) and 'resolved_parameters' in x and 'configuration' in x and 'candidate_id' in x:candidates.append(aid)
                details=dict(study_id=s['study_id'],state_keys=list(session),state_counters={k:session[k] for k in ['mathematical_evaluations','physical_replay_launches','numerical_s','construction_numerical_s','created_at','updated_at','elapsed_s'] if k in session},
                    native_analysis_cost_records=s.get('native_analysis_cost_records'),controller_executions=s.get('registered_controller_executions'),calls=calls,candidate_count=len(candidates))
                cost_details[s['study_id']]=details
                row=next(r for r in rs if r['run_id']==s['study_id']);row['candidate_count']=len(candidates)
                # Physical actual counters are present in work-directory raw/progress records and completion reports.
                physics_files=list(sp.glob('physical_replay/*/result.json'))
                steps=0
                for p in physics_files:
                    x=read(p);steps+=x.get('physics_steps',x.get('cost',{}).get('physics_steps',0))
                row['physical_steps']=steps if physics_files else None
                row['integration_steps']=steps if physics_files else None
                row['integration_step_coverage']='independent physical result.json only; internal analysis/controller steps require supplementary vectors'
                c.close()
    dump('SOURCE_DATA/COMPLETION_COST_DETAILS.json',cost_details);csvout('RESOURCE_COSTS.csv',rs)

if __name__=='__main__':main()
