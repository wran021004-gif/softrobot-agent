"""Existing Full studies -> paper data. Read-only Store access; no scientific execution."""
from pathlib import Path
import json,csv,sqlite3,sys,re,gc
O=Path(__file__).resolve().parent;P=O.parent;TEN=P/'ten_task_codex_solve_20261112';FIVE=P/'five_task_completion_20261113';PHS=P.parent/'runs/phs2d-paper-data-20261112'
for name in ['FIGURE_DATA','FIGURES','FIGURES_MUJOCO','VISUAL_XML','SOURCE_DATA']:(O/name).mkdir(exist_ok=True)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def dump(p,x):(O/p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def csvout(p,rs):
    if not rs:return
    with (O/p).open('w',encoding='utf-8-sig',newline='') as f:
        keys=list(dict.fromkeys(k for r in rs for k in r));w=csv.DictWriter(f,keys);w.writeheader()
        for r in rs:w.writerow({k:'unavailable' if v is None else json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})
def db(path):
    path=Path(path);path=path if path.suffix=='.sqlite' else path/'platform.sqlite'
    return sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
def get(c,ref):
    ref=ref['artifact_id'] if isinstance(ref,dict) else ref
    row=c.execute('select body from artifacts where id=?',(ref,)).fetchone()
    if row is None:raise KeyError(ref)
    return json.loads(row[0])
def csvread(p):return list(csv.DictReader(Path(p).open(encoding='utf-8-sig')))
def find_arrays(v,path=''):
    if isinstance(v,dict):
        for k,z in v.items():
            if isinstance(z,(dict,list)):yield from find_arrays(z,path+'/'+k)
            else:yield path+'/'+k,z
    elif isinstance(v,list):
        for i,z in enumerate(v):
            if isinstance(z,(dict,list)):yield from find_arrays(z,path+'/'+str(i))

TITLES={'T01':'多目标到达与保持','T02':'带载受扰保持（M2）','T03':'快速到达（M3）','T04':'双叶八字轨迹跟踪','T05':'工具位置与轴向姿态（M5）','T06':'带载位置—姿态扫描（M6）','T07':'四独立腱共同结构多任务（C1）','T08':'被动渐进刚度（P3）','T09':'复杂导向件弹簧按钮接触','T10':'外部冲击主动恢复（M7）'}
CATEGORIES={'T01':'active_reach_hold','T02':'loaded_hold','T03':'fast_reach','T04':'trajectory_tracking','T05':'position_orientation','T06':'loaded_timed_scan','T07':'shared_structure_multitask','T08':'task.passive_response / development_valid','T09':'contact_manipulation','T10':'dynamic_disturbance_rejection'}
METHODS={'T01':'原生非线性控制响应优化后张力节点执行','T02':'原生非线性控制响应优化后张力节点执行','T03':'原生非线性控制响应优化后张力节点执行','T04':'原生平衡点组连续构造 + 周期张力前馈','T05':'原生直接控制搜索后张力执行','T06':'原生直接控制搜索后定时张力执行','T07':'共同结构 + 各工况原生控制响应优化','T08':'无主动控制；固定放绳单向被动腱','T09':'已归档张力节点 + 原生接触仿真','T10':'原生状态反馈：静力/完整切线/离散 LQR/有界张力分配'}

def main():
    ti={t['task_id']:t for t in read(TEN/'ALL_TASKS_TRACE_INDEX.json')['tasks']};fi={t['task_id']:t for t in read(FIVE/'FINAL_RESULTS.json')['tasks']}
    tasks=[];cases=[];bindings={};allmetrics=[];protocols={};costrows=[]
    for tid in sorted(ti):
        if tid in fi:
            t=fi[tid];d=FIVE/t['directory'];co=read(d/'COST_REPORT.json');sp=next(s['store'] for s in co['studies'] if s['study_id']==t['study_id']);picked=t['cases'];runid=t['study_id']
        else:
            t=ti[tid];d=Path(t['folder']);sp=t['active_store'];co=read(d/'COST_REPORT.json');final=read(d/'FINAL_RESULT.json');pi=read(d/'PHYSICAL_EVIDENCE/INDEX.json');runid=final['study_id']
            # Keep only complete accepted results on the final common structure. Never stitch different structures.
            picked=[r for r in pi if r.get('acceptance',{}).get('accepted')]
            if tid=='T08':picked=[r for r in picked if r['reference']==final['best_evidence']]
            else:
                seen={};
                for r in picked:seen[r['condition_id']]=r
                picked=list(seen.values())
        proto=read(d/'TASK_PROTOCOL.json');protocols[tid]=proto;conn=db(sp);task_cases=[];model_bind=[]
        for index,rec in enumerate(picked):
            result=get(conn,rec['reference']);candref=result['candidate'];candidate=get(conn,candref)
            conf=candidate.get('configuration',candidate.get('effective_configuration'))
            if conf is None:raise KeyError((tid,'configuration',list(candidate)))
            acc=result['acceptance'];rawref=result.get('raw_reference',rec.get('raw_reference'));raw=get(conn,rawref) if rawref else None
            cid=rec.get('condition_id',result.get('condition_id','default'));role=rec.get('role',rec.get('protocol_case_role','required'))
            if tid in ['T01','T07','T10'] and cid=='default':cid={'T01':'central_high','T07':'M1_A','T10':'positive_y'}[tid]
            role=next((x.get('role','required') for x in proto['cases'] if x['condition_id']==cid),role)
            metrics=acc.get('metrics',{});comps=acc.get('components',{})
            parsed={k.removeprefix('evaluator:'):v.get('value') for k,v in comps.items() if k.startswith('evaluator:')}
            parsed.update(metrics)
            bounds={k.removeprefix('evaluator:'):dict(limit=v.get('limit'),unit=v.get('unit'),passed=v.get('passed')) for k,v in comps.items() if k.startswith('evaluator:')}
            prefix=f'{tid}_{cid}';dump(f'SOURCE_DATA/{prefix}_CANDIDATE.json',candidate);dump(f'SOURCE_DATA/{prefix}_RESULT.json',result)
            dump(f'SOURCE_DATA/{prefix}_TASK.json',conf['task'])
            row=dict(task_id=tid,condition_name=cid,condition_role=role,run_id=runid,candidate_id=candref['artifact_id'],controller_identity=result.get('controller_binding_identity',result.get('control',{})),
                input_conditions=conf['task'].get('physical_problem',conf['task'].get('goal')),metrics=parsed,constraint_thresholds=bounds,passed=acc['accepted'],
                task_version=conf['task'].get('task_version'),source_reference=f'{sp}#artifacts/{rec["reference"]["artifact_id"]}',raw_reference=rawref)
            # P3 has two load directions within a single formal multi-direction result.
            if tid=='T08':
                for direction in ['plus_x','minus_x']:
                    dr={**row,'condition_name':direction,'input_conditions':proto['cases'][0]['task']['goal']['data']['programs'][direction],
                        'metrics':{k.removeprefix(direction+'_'):v for k,v in parsed.items() if k.startswith(direction+'_') or k=='no_contact'},
                        'constraint_thresholds':{k.removeprefix(direction+'_'):v for k,v in bounds.items() if k.startswith(direction+'_') or k=='no_contact'}}
                    cases.append(dr);task_cases.append(dr)
            else:cases.append(row);task_cases.append(row)
            for k,v in comps.items():allmetrics.append(dict(task_id=tid,condition_name=cid,condition_role=role,metric=k,value=v.get('value'),limit=v.get('limit'),unit=v.get('unit'),passed=v.get('passed'),source_reference=row['source_reference']+'#/acceptance/components/'+k))
            # Save compact trajectory signals from the original BackendResult, not recomputed physical outputs.
            backendref=result.get('backend_reference')
            if backendref:
                backend=get(conn,backendref);signals=backend.get('signals',[])
                if signals:dump(f'FIGURE_DATA/{prefix}_SIGNALS.json',signals)
                else:dump(f'SOURCE_DATA/{prefix}_BACKEND_KEYS.json',list(backend))
            # Native active result raw data format differs; retain exact raw-field inventory plus source.
            if raw is not None:
                dump(f'SOURCE_DATA/{prefix}_RAW_INDEX.json',dict(source=rawref,keys=list(raw),preview={k:v for k,v in raw.items() if k in ['trace_files','solver_options','coordinate_order','tendon_order','joint_count','kind','status','initial_state','timings_s','cost','actual_resource_consumption','model_paths','xml_path','model_xml']}))
            # Locate model XML only inside the exact selected Store work directory.
            store_dir=Path(sp);store_dir=store_dir.parent if store_dir.suffix=='.sqlite' else store_dir
            exid=acc.get('execution_id',result.get('execution_id'));xmls=[]
            for xdir in [store_dir/'physical_replay'/str(exid),store_dir/'controller'/str(exid),store_dir/'controllers'/str(exid)]:
                if xdir.exists():xmls.extend(str(p) for p in xdir.rglob('*.xml'))
            model_bind.append(dict(task_id=tid,condition_name=cid,run_id=runid,store=str(store_dir/'platform.sqlite'),candidate_ref=candref,result_ref=rec['reference'],raw_ref=rawref,
                backend_ref=backendref,execution_id=exid,xml_files=xmls,candidate_file=f'SOURCE_DATA/{prefix}_CANDIDATE.json',source_directory=str(d)))
            del raw;gc.collect()
        conn.close();bindings[tid]=model_bind
        required=[x for x in task_cases if x['condition_role']=='required'];controls=[x for x in task_cases if x['condition_role']=='control']
        struct=read(O/model_bind[0]['candidate_file'])['configuration']['robot']['structure']['data']
        segs=[x for x in struct.get('components',[]) if x.get('kind')=='flexible_segment'];desc=proto.get('name',TITLES[tid])
        tasks.append(dict(task_id=tid,task_name=TITLES[tid],task_category=CATEGORIES[tid],task_description=desc,system='Full',
            structure_type=dict(flexible_segments=len(segs),lengths_m=[x['length_m'] for x in segs],tendons=len(struct.get('tendons',[])),actuators=len(struct.get('actuators',[])),components=[x.get('kind') for x in struct.get('components',[]) if x.get('kind')!='flexible_segment']),
            control_method=METHODS[tid],required_conditions=[x['condition_name'] for x in required],passed_conditions=sum(x['passed'] for x in required),total_conditions=len(required),
            control_conditions=[dict(name=x['condition_name'],passed=x['passed']) for x in controls],success_status='PASS' if required and all(x['passed'] for x in required) else 'INCOMPLETE',
            primary_metrics={x['condition_name']:x['metrics'] for x in required},secondary_metrics={x['condition_name']:x['metrics'] for x in controls},
            physical_validation='MuJoCo original-task independent acceptance',source_reference=[x['source_reference'] for x in task_cases],run_id=runid,
            protocol_source=str(d/'TASK_PROTOCOL.json'),source_classification=proto.get('source_status'),task_version=read(O/model_bind[0]['candidate_file'])['configuration']['task'].get('task_version')))
        # Historical cost tables are already extracted from raw vectors: keep run scopes; do not add task batches here.
        if tid in fi:
            for s in co['studies']:
                native=s.get('native_analysis_cost_records',[]);bud=s.get('budget',{}).get('used',{})
                costrows.append(dict(task_id=tid,run_id=s['study_id'],cost_scope='selected_completion_study' if s['study_id']==runid else 'preparation_in_same_completion',
                    math_evaluations=s.get('charged_mathematical_evaluations'),math_internal_optimizations=None,math_internal_iterations=None,physical_episodes=s.get('physical_replay_launches'),integration_steps=None,
                    candidate_count=None,tool_calls=bud.get('tool_calls'),cpu_time_s=None,wall_time_s=s.get('recorded_numerical_wall_s'),wall_time_basis='Core charged numerical wall, not elapsed',source_reference=str(d/'COST_REPORT.json')))
        else:
            r=next(x for x in csvread(TEN/'ALL_TASKS_COST.csv') if x['task_id']==tid)
            costrows.append(dict(task_id=tid,run_id=runid,cost_scope='archived_task_study_with_failures',math_evaluations=r['charged_math_evaluations'],math_internal_optimizations=r['recorded_native_inner_optimizer_calls'],math_internal_iterations=r['recorded_native_inner_optimizer_iterations'],
                 physical_episodes=r['recorded_physical_episodes'],integration_steps=r['total_recorded_backend_integration_steps'],physical_steps=r['recorded_physical_steps'],math_internal_physics_steps=r['recorded_native_analysis_steps'],candidate_count=r['structural_candidates'],tool_calls=co.get('top_level_public_operations'),
                 cpu_time_s=r['worker_recorded_process_cpu_s'],cpu_time_scope='observed worker lifetime only',wall_time_s=r['study_elapsed_s'],wall_time_basis='study elapsed',source_reference=str(TEN/'ALL_TASKS_COST.csv')))
        print(tid,len(task_cases),'cases',len(model_bind),'model bindings',flush=True)
    # Reuse the accepted PHS-2D paper extraction, without re-reading or reprocessing its trajectories.
    ph=read(PHS/'FINAL_METRICS.json');chosen=ph['codex_nominal'];phrows=csvread(PHS/'TEN_CASE_RESULTS.csv')
    for r in phrows:
        vals={k:float(r[k]) for k in ['point_x_abs_m','tip_projected_m','ratio','max_plane_y_m','loaded_tail_drift_m','loaded_static_residual_inf_nm']}
        cases.append(dict(task_id='PHS-2D',condition_name=r['load_condition'],condition_role='required',run_id=r['run_id'],candidate_id=chosen['candidate']['artifact_id'],controller_identity='passive_fixed_payout',
            input_conditions=dict(material_s=float(r['material_s']),force_x_n=float(r['force_x_n'])),metrics=vals,constraint_thresholds=dict(point_x_abs_m=dict(lower=.01),tip_projected_m=dict(upper=.005),ratio=dict(upper=.3),max_plane_y_m=dict(upper=.002)),passed=r['accepted']=='True',task_version='1.2.0',source_reference=str(PHS/'TEN_CASE_RESULTS.csv')+'#'+r['load_condition']))
    tasks.append(dict(task_id='PHS-2D',task_name='被动腱结构的受力点柔顺与末端抑制',task_category='passive_shape_design',task_description='7 段/4 腱被动结构，5 个材料位置 × 两种载荷符号',system='Full',structure_type=dict(flexible_segments=7,lengths_m=[.04]*7,tendons=4,actuators=0),control_method='无主动控制；固定放绳单向被动腱',required_conditions=[r['load_condition'] for r in phrows],passed_conditions=10,total_conditions=10,control_conditions=[],success_status='PASS',primary_metrics={k:chosen[k] for k in ['min_point_m','max_tip_m','max_ratio']},secondary_metrics=dict(half_timestep_accepted=ph['codex_halfstep']['accepted'],half_timestep_result_ref=ph['codex_halfstep']['result']),physical_validation='原十工况 + 半步长十工况',source_reference=str(PHS/'FINAL_METRICS.json'),run_id=chosen['run_id'],protocol_source=str(PHS/'SOURCE_EXTRACTS/FROZEN_TASK.json'),source_classification='development_valid',task_version='1.2.0'))
    pc=read(PHS/'RESOURCE_USAGE.json')
    for s in pc['stores']:
        if not s['run_id'].startswith('psd2d-'):continue
        count=pc['codex']['math_evaluations_by_run'][s['run_id']];steps=pc['codex']['halfstep_physics_steps'] if 'halfstep' in s['run_id'] else pc['codex']['fresh_search_physics_steps']+pc['codex']['nominal_physics_steps'] if 'fresh' in s['run_id'] else 0
        costrows.append(dict(task_id='PHS-2D',run_id=s['run_id'],cost_scope=s['scope'],math_evaluations=count,math_internal_optimizations=None,physical_episodes=s['receipt_totals']['backend_solves'],integration_steps=steps,candidate_count=9 if 'fresh' in s['run_id'] else 1,tool_calls=s['receipt_totals']['tool_calls'],tool_call_basis='Core ledger units',cpu_time_s=None,wall_time_s=s['receipt_totals']['wall_s'],wall_time_basis='Core charged wall, not elapsed',source_reference=str(PHS/'RESOURCE_USAGE.json')))
    csvout('ALL_TASK_RESULTS.csv',tasks);csvout('TASK_CASE_RESULTS.csv',cases);csvout('RESOURCE_COSTS.csv',costrows);csvout('FIGURE_DATA/ALL_CONSTRAINT_METRICS.csv',allmetrics)
    dump('SOURCE_DATA/MODEL_BINDINGS.json',bindings);dump('SOURCE_DATA/PROTOCOLS.json',protocols);dump('SOURCE_DATA/FULL_TASKS.json',tasks);dump('SOURCE_DATA/FULL_CASES.json',cases)
    print('EXTRACTED',len(tasks),'tasks',len(cases),'cases; no Provider or scientific execution')

if __name__=='__main__':main()
