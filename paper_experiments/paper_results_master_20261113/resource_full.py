from extract_full import *
from datetime import datetime

def main():
    old=[r for r in csvread(O/'RESOURCE_COSTS.csv') if r['task_id'] not in ['T01','T04','T07','T09','T10']]
    selected=read(O/'SOURCE_DATA/FULL_TASKS.json');cpu=read(FIVE/'CPU_COST_REPORT.json')['processes'];rows=[];details={}
    for tid in ['T01','T04','T07','T09','T10']:
        top=next(d for d in FIVE.iterdir() if d.is_dir() and d.name.startswith(tid+'_'));co=read(top/'COST_REPORT.json')
        for s in co['studies']:
            sp=Path(s['store']);c=db(sp);run=s['study_id'];state=json.loads(c.execute('select state from sessions where run_id=?',(run,)).fetchone()[0])
            objs=[]
            for aid,body in c.execute("select id,body from artifacts where media='application/json' and length(body)<1800000"):
                try:v=json.loads(body)
                except:continue
                if isinstance(v,dict) and 'resolved_parameters' in v and 'configuration' in v and 'candidate_id' in v:objs.append(v)
            uniq={json.dumps(v['configuration']['robot']['structure'],sort_keys=True) for v in objs}
            internal=[x for r in s.get('native_analysis_cost_records',[]) for x in r.get('internal_calculations',[])]
            local_records=[]
            def local_solvers(v,path=''):
                if isinstance(v,dict):
                    for k,x in v.items():
                        if k=='local_solver' and isinstance(x,dict):local_records.append(dict(pointer=path+'/'+k,record=x))
                        else:local_solvers(x,path+'/'+k)
                elif isinstance(v,list):
                    for i,x in enumerate(v):local_solvers(x,path+'/'+str(i))
            for ar in s.get('native_analysis_cost_records',[]):
                if ar.get('reference'):local_solvers(get(c,ar['reference']),ar['reference']['artifact_id'])
            ist=sum(r.get('physics_steps',0) for r in internal) if internal else 0
            optimizer_evals=sum(r.get('optimization_evaluations',0) for r in internal) if internal else None
            optimizer_iters=sum(r.get('optimization_iterations',0) for r in internal) if internal else None
            physics=0;physical_records=0
            for p in sp.glob('physical_replay/*/result.json'):
                r=read(p);physics+=r.get('physics_steps',r.get('cost',{}).get('physics_steps',0));physical_records+=1
            controller=s.get('registered_controller_executions',[])
            controller_steps=0;controller_step_coverage=True
            for execution in controller:
                cr=get(c,execution['reference']);prof=cr.get('profile')
                if not prof or not prof.get('simulation'):controller_step_coverage=False;continue
                sim=get(c,prof['simulation']);data=sim.get('data',{}).get('data',{})
                if 'numerical_steps' in data:controller_steps+=data['numerical_steps']
                else:controller_step_coverage=False
            exact=sp.as_posix().lower()+'/'
            observed=[r for r in cpu if exact in r['command_line'].replace('\\','/').lower()]
            wall=state.get('closed_unix')-state['started_unix'] if state.get('closed_unix') and state.get('started_unix') else None
            row=dict(task_id=tid,run_id=run,cost_scope='full_completion_series',selected_result_study=run==next(r['run_id'] for r in selected if r['task_id']==tid),
                math_evaluations=s.get('charged_mathematical_evaluations'),math_internal_optimizer_calls=len(local_records) if local_records else None,math_objective_evaluations=optimizer_evals,math_optimizer_iterations=optimizer_iters,
                local_optimizer_iterations=sum(x['record'].get('iterations',0) for x in local_records) if local_records else None,
                inner_call_coverage='saved native local_solver records only; other construction/qualification solves not inferred',
                physical_episodes=s.get('physical_replay_launches',0)+len(controller),physical_steps=physics+controller_steps if (physical_records or controller) and controller_step_coverage else None,math_internal_physics_steps=ist,
                integration_steps=physics+controller_steps+ist if (physical_records or controller) and controller_step_coverage else None,integration_step_coverage='independent physical + nested controller numerical_steps + recorded native analysis; failed pre-execution work separately retained',
                candidate_artifact_count=len(objs),candidate_count=len(uniq),candidate_count_basis='unique physical robot.structure among stored candidate artifacts',
                tool_calls=s.get('budget',{}).get('used',{}).get('tool_calls'),tool_call_basis='Core ledger units',cpu_time_s=sum(r['cpu_s'] for r in observed) if observed else None,
                cpu_time_scope='observed Windows worker lifetimes; partial coverage',wall_time_s=wall,wall_time_basis='closed_unix-started_unix; unavailable for unclosed study',charged_numerical_wall_s=s.get('recorded_numerical_wall_s'),
                source_reference=str(top/'COST_REPORT.json'),cpu_source=str(FIVE/'CPU_COST_REPORT.json'))
            # Controller launches include true closed-loop native executions in nested execution Store.
            if controller:
                row['controller_execution_records']=len(controller)
                print(tid,run,'CONTROLLER_RECORD_KEYS',[list(x) for x in controller[:1]],flush=True)
            rows.append(row);details[run]=dict(internal_calculations=internal,local_solver_records=local_records,controller_executions=controller,cpu_observed_process_count=len(observed))
            c.close()
    csvout('RESOURCE_COSTS.csv',sorted(old+rows,key=lambda r:(r['task_id'],r['run_id'])));dump('SOURCE_DATA/RESOURCE_DETAILS.json',details)
    print('Resource rows',len(old+rows),'No Token fields.')

if __name__=='__main__':main()
