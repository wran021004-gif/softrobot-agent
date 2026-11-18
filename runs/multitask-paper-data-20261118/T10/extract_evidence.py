"""Read historical T10 Stores; extract evidence only. Never integrates or optimizes."""
from pathlib import Path
import csv, gzip, hashlib, json, sqlite3, math

ROOT = Path('D:/softrobot-agent')
OUT = ROOT/'runs/multitask-paper-data-20261118/T10'
BASE = ROOT/'paper_experiments/five_task_completion_20261113/T10_M7_impact_recovery'
PRE = ROOT/'paper_experiments/ten_task_codex_solve_20261112/T10_M7_impact_recovery'

def lp(p): return Path('\\\\?\\'+str(Path(p).resolve()))
def read(p): return json.loads(lp(p).read_text(encoding='utf-8-sig'))
def write(name,x):
    p=OUT/name; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def csvwrite(name, rows):
    if not rows:return
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with (OUT/name).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else ('unavailable' if v is None else v) for k,v in r.items()})
def artref(store, aid): return str(store)+'#artifacts/'+str(aid)
def aid(x): return x.get('artifact_id') if isinstance(x,dict) else None
def normpath(p): return Path(str(p).removeprefix('\\\\?\\'))

stores=[]
for folder in [PRE,PRE/'T10_RUN_02',BASE,*sorted(BASE.glob('T10_RUN_*'))]:
    sp=folder/('STORE_RESEARCH' if (folder/'STORE_RESEARCH/platform.sqlite').exists() else 'STORE')
    if (sp/'platform.sqlite').exists():
        con=sqlite3.connect('file:'+str(sp/'platform.sqlite').replace('\\','/')+'?mode=ro',uri=True)
        arts={}
        for i,media,body in con.execute('select id,media,body from artifacts'):
            if 'json' not in media:continue
            try: x=json.loads(body)
            except (ValueError,UnicodeDecodeError):continue
            arts[i]=x
        calls=[]
        for r,req,status,rec in con.execute('select run_id,request_id,status,receipt from calls'):
            calls.append({'run_id':r,'request_id':req,'status':status,'receipt':json.loads(rec)})
        stores.append({'folder':folder,'store':sp,'arts':arts,'calls':calls})

all_candidates=[];all_decisions=[];results=[];resources=[]
for st in stores:
    sp=st['store'];folder=st['folder'];arts=st['arts']
    st['tag']=('precursor_'+folder.name if PRE in folder.parents or folder==PRE else ('expert_run01' if folder==BASE else folder.name))
    st['models']={}
    for p in lp(sp).rglob('robot.xml'):
        p=normpath(p);st['models'][p.parent.parent.name if p.parent.name=='backend' else p.parent.name]=p
    for i,x in arts.items():
        if not isinstance(x,dict):continue
        if 'configuration' in x and 'candidate_id' in x and isinstance(x['configuration'],dict) and 'robot' in x['configuration']:
            cfg=x['configuration']; rob=cfg['robot']; policy=cfg.get('policy',{});task=cfg.get('task',{})
            task=task.get('task',task)
            design=rob.get('structure',{}).get('data',{}).get('design',{})
            if not design:design=rob.get('structure',{}).get('data',{})
            all_candidates.append({'task_id':'T10','source_tag':st['tag'],'candidate_id':x['candidate_id'],'candidate_artifact_id':i,'source_store':str(sp),'source_ref':artref(sp,i),'canonical_task_id':task.get('task_id'),'controller_id':policy.get('controller',{}).get('extension_id'),'segment_count':sum(c.get('kind')=='flexible_segment' for c in design.get('components',[])),'tendon_count':len(design.get('tendons',[])),'structure_identity_local':hashlib.sha256(json.dumps(design,sort_keys=True).encode()).hexdigest() if design else None})
        if 'rationale_summary' in x and 'research_question' in x:
            all_decisions.append({'task_id':'T10','source_tag':st['tag'],'decision_artifact_id':i,'source_store':str(sp),'source_ref':artref(sp,i),**x})
    # Full raw result, or wrapped research result. Dedupe by physical simulation reference.
    bysim={}
    for i,x in arts.items():
        if not isinstance(x,dict):continue
        r=x.get('result') if 'scientific_results' in x else x
        if not isinstance(r,dict):continue
        a=r.get('acceptance') or {}
        if not a:continue
        simid=aid(a.get('evidence_binding',{}).get('simulation')) or aid(r.get('backend_reference'))
        if not simid:continue
        if simid not in bysim or ('execution' in r and 'execution' not in bysim[simid][1]):bysim[simid]=(i,r)
    # Include incomplete controller run02 with completed raw evaluator and failed profile.
    if folder==BASE/'T10_RUN_02':
        simid='77cc72be92676925c9cc684cc696a95989aa57782f342c03b39f593cb5a9fe46'
        ev='c35b41873c7a5b12545af447113df2c6d947ee99f30411d1edc1e881f5225fe2'
        bysim[simid]=('d8d9db07024671bdb7cb173fb0107950a130bfa905098e88b7d1bec8b1c85a2c',{'candidate':{'artifact_id':'0001178538b6092f70e02e9d2b49b2f5ee32e53d881d561cc9bb0b3ceb6d2de1'},'acceptance':{'accepted':None,'status':'execution_incomplete','evidence_binding':{'simulation':{'artifact_id':simid},'evaluation':{'artifact_id':ev}},'metrics':{}},'status':'execution_incomplete'})
    for simid,(rid,r) in bysim.items():
        sim=arts.get(simid,{})
        te=sim.get('data',{}).get('data',{}).get('task_evidence',{}) or sim.get('task_evidence',{})
        tepointer='/data/data/task_evidence/arrays' if 'data' in sim else '/task_evidence/arrays'
        arrays=te.get('arrays',{});a=r['acceptance']; eb=a.get('evidence_binding',{})
        evalid=aid(eb.get('evaluation')) or aid(r.get('evaluation_reference'));ev=arts.get(evalid,{})
        candidateid=aid(r.get('candidate'));cand=arts.get(candidateid,{})
        cfg=cand.get('configuration',{});policy=cfg.get('policy',{});task=cfg.get('task',{})
        task=task.get('task',task)
        condition=cand.get('condition_id') or task.get('task_id','').removeprefix('m7-').replace('-','_')
        if not condition: condition=task.get('name','unavailable')
        execid=a.get('execution_id') or r.get('execution_id')
        for ca in st['calls']:
            receipt=ca['receipt']
            if aid(receipt.get('output'))==simid:execid=receipt.get('execution_id') or execid
        model=st['models'].get(execid)
        if model is None:
            for p in st['models'].values():
                if p.parent.parent.name==execid:model=p;break
        metrics=dict(a.get('metrics') or {})
        conmetrics={c['name']:c.get('observed') for c in ev.get('constraints',[])}
        if not metrics:
            mapping={'final_hold_max_error_m':'final_hold_position','final_hold_max_speed_m_s':'final_hold_speed','pre_hold_max_error_m':'pre_impact_hold_position','pre_hold_max_speed_m_s':'pre_impact_hold_speed','max_tendon_speed_m_s':'actual_speed_limit','max_tendon_stroke_m':'stroke_limit'}
            metrics={k:conmetrics.get(v) for k,v in mapping.items()}
        trajectory=model.parent/'trajectory.json.gz' if model else None
        rec={'task_id':'T10','source_tag':st['tag'],'study_id':r.get('owning_study'),'candidate_id':r.get('candidate_id') or cand.get('candidate_id'),'candidate_artifact_id':candidateid,'condition_id':condition,'protocol_role':'control' if condition.endswith('_frozen') else 'required','original_status':r.get('status'),'accepted':a.get('accepted'),'raw_evaluator_task_success':ev.get('task_success'),'result_ref':artref(sp,rid),'result_artifact_id':rid,'store_path':str(sp),'simulation_artifact_id':simid,'evaluation_artifact_id':evalid,'model_xml':str(model) if model else None,'trajectory_path':str(trajectory) if trajectory and lp(trajectory).exists() else None,'execution_id':execid,'execution_route':r.get('route') or 'registered measured-state controller','controller_id':policy.get('controller',{}).get('extension_id'),'controller':policy.get('controller'),'configuration_ref':r.get('execution',{}).get('configuration'),'metrics':metrics,'raw_constraints':ev.get('constraints',[]),'design_identity':te.get('design_identity'),'physics_identity':te.get('physics_identity'),'controller_identity':te.get('controller_identity'),'model_xml_sha256_recorded':te.get('model_xml_sha256') or sim.get('xml_sha256'),'dense_sample_count':len(arrays.get('time_s',[])),'numerical_steps':sim.get('data',{}).get('data',{}).get('numerical_steps') or sim.get('physics_steps'),'state_source':artref(sp,simid)+tepointer,'arrays_available':list(arrays)}
        rec['_arrays']=arrays;rec['_r']=r;rec['_st']=st
        results.append(rec)
    costfile=folder/'COST_REPORT.json'
    if costfile.exists():resources.append({'source':str(costfile),'source_tag':st['tag'],'raw_cost_report':read(costfile),'aggregation':'Separate source run only; no cross-run sum. Native feedback preparation forward evaluations are separate from charged mathematical-tool evaluations.'})

csvwrite('complete_candidate_index.csv',all_candidates)
csvwrite('complete_decision_index.csv',all_decisions)
write('resources_per_run.json',resources)

final=[r for r in results if r['source_tag']=='T10_RUN_06']
base_results=[r for r in results if r['source_tag']=='expert_run01']
print('base results',[(r['result_artifact_id'],r['accepted'],r['condition_id']) for r in base_results])

selected=[]
# 6 actual research stages; FINAL stage is represented separately by each final protocol case.
def select(resultid,stage,label,problem,hypothesis,change,decision):
    r=next(x for x in results if x['result_artifact_id']==resultid)
    r['selection']={'stage':stage,'label':label,'observed_problem':problem,'hypothesis_retrospective_summary':hypothesis,'controller_change':change,'decision_summary':decision,'structural_change':'none; mandatory original M2 hardware retained'}
    selected.append(r);return r

select('c83317649791d5f7afb26ab333bd815b524917497269d58dd84a7db62a0339c8','Diagnosis','Held-input replay exposes startup constraints','Nominal final hold looks good, but dense prehold position/speed and actual tendon speed violate original protocol.','Recorded commands/interpolation semantics and startup transient must be checked against dense actuator constraints.','Historical smooth-start nominal command sequence held per interval; diagnostic open loop.','Do not promote sampled nominal hold to feedback success; inspect midpoint command seed.')
select('8abdb9f6edc2c82a9e7feae87b6c0624d3a7b43c7d16a0e0b0a5610f1c1413f5','Refinement','Midpoint no-impulse seed','First held-command replay fails despite final hold passing.','Midpoint samples may better approximate the historical interpolated startup.','Replace held target commands with midpoint initialization; still open loop.','Nominal complete no-impulse protocol passes; active impact feedback remains unresolved.')
select('d8d9db07024671bdb7cb173fb0107950a130bfa905098e88b7d1bec8b1c85a2c','Rejected','Shaped GVS NMPC','Raw no-impulse physical evaluator fails tendon speed, stroke and final speed; profile export also fails.','Smooth approach and tendon-speed cost may improve the registered feedback controller.','GVS NMPC with explicit smooth approach and tendon-speed cost, common planned parameters.','Retain measured failure and incomplete delivery; choose native measured-state feedback route next.')
select('35ebc4d4bc25f5228705d25ecb5e6f89f94dbea0045d0ec6f0875c75235e42b5','Refinement','Native feedback first positive impact pass','GVS route has not established original hardware/hold constraints.','Use native algebraic static reference nodes, full-force tangent, discrete LQR and bounded input.','Registered controller.native_state_feedback; recompute reference nodes/tangent/gains.','Positive impact physical acceptance passes; typed recipe delivery still requires repair.')
select('68a35eeb48b5d27bc7ab68e89b8fcd241d470572ef177cbb79fd72743e0fb8e7','Rejected','Reject mixed resolved controller weights','Individual active cases pass, but first-case actual defaults differ from intended shared recipe.','A valid shared-controller claim requires actual resolved identities to agree.','No structural change; legal default choices must align holding .5 and terminal 0.','Reject joint claim; preserve old results and freshly evaluate all five cases under verified common controller.')
for r in final:
    r['selection']={'stage':'Final' if r['protocol_role']=='required' else 'Control','label':'Common native feedback '+r['condition_id'],'observed_problem':'Frozen inputs isolate post-impact feedback contribution.' if r['protocol_role']=='control' else 'Complete original protocol under one verified common controller.','hypothesis_retrospective_summary':'Shared measured-state feedback should retain hold under both impulse signs.','controller_change':'One verified common native feedback recipe; no case-dependent control information. Environment freezes actual input after 0.5 s for controls.','decision_summary':'PASS required; retain actual failed frozen controls separately.','structural_change':'none; same mandatory two-segment six-tendon M2 hardware'}
    selected.append(r)

timelines=[];metric_rows=[];snapshots=[];modelchecks=[]
for n,r in enumerate(selected,1):
    sel=r['selection'];a=r['_arrays'];sp=Path(r['store_path']);st=r['_st'];node=f'T10_N{n:02d}';r['node_id']=node
    timelines.append({'task_id':'T10','candidate_id':r['candidate_id'],'candidate_artifact_id':r['candidate_artifact_id'],'node_id':node,'iteration':n,'stage':sel['stage'],'candidate_status':r['original_status'],'model_xml':r['model_xml'],'state_source':r['state_source'],'physical_hypothesis':sel['hypothesis_retrospective_summary'],'hypothesis_provenance':'retrospective summary of recorded action; exact original rationale in agent_decision_timeline.csv','observed_problem':sel['observed_problem'],'structural_change':sel['structural_change'],'controller_change':sel['controller_change'],'mathematical_evidence':'native_feedback_preparation.json in matching backend; algebraic static residual / centered full-force tangent / DARE; no nonlinear-stability guarantee' if 'native' in (r['controller_id'] or '') else 'see original research result; no new analysis computed','physical_evidence':r['result_ref'],'decision_summary':sel['decision_summary'],'evaluation_status':r['accepted'],'raw_evaluator_status':r['raw_evaluator_task_success'],'resulting_metrics':r['metrics'],'condition_id':r['condition_id'],'protocol_role':r['protocol_role'],'source_tag':r['source_tag'],'study_id':r['study_id'],'display_label':sel['label']})
    for key,v in r['metrics'].items():metric_rows.append({'task_id':'T10','node_id':node,'candidate_id':r['candidate_id'],'condition_id':r['condition_id'],'protocol_role':r['protocol_role'],'source_tag':r['source_tag'],'metric':key,'value':v,'metric_scope':'original dense physical grid including initial' if a else 'original acceptance result','source':r['result_ref'],'compare_group':'same mandatory hardware and original protocol; controller and implementation versions differ; use grouped points, no convergence line','accepted':r['accepted'],'raw_evaluator_task_success':r['raw_evaluator_task_success']})
    if not a:continue
    ts=a['time_s'];err=[math.dist(x,[.29,-.035,.19]) for x in a['tip_m']]
    keys=[('initial',0.0),('approach',.15),('pre_impact_hold',.49),('pulse_peak',.525),('pulse_end',.55),('recovery',.65),('final_hold',.9),('final',1.0)]
    for label,targett in keys:
        i=min(range(len(ts)),key=lambda i:abs(ts[i]-targett))
        snapshots.append({'node_id':node,'task_id':'T10','source_tag':r['source_tag'],'candidate_id':r['candidate_id'],'candidate_artifact_id':r['candidate_artifact_id'],'condition_id':r['condition_id'],'protocol_role':r['protocol_role'],'stage':label,'time_s':ts[i],'dense_index':i,'source':r['state_source'],'original_model_xml':r['model_xml'],'qpos':a['qpos'][i],'qvel':a['qvel'][i],'tip_m':a['tip_m'][i],'force_n':a['force_n'][i],'control_n':a['control_n'][i],'tension_n':a['tension_n'][i],'tip_speed_m_s':a.get('tip_speed_m_s',[None]*len(ts))[i]})
    # Save compact quantitative series, preserving original 0.5 ms grid.
    csvwrite('FIGURE_DATA/'+node+'_'+r['condition_id']+'_signals.csv',[{'time_s':t,'tip_x_m':a['tip_m'][i][0],'tip_y_m':a['tip_m'][i][1],'tip_z_m':a['tip_m'][i][2],'position_error_m':err[i],'tip_speed_m_s':a.get('tip_speed_m_s',[None]*len(ts))[i],'force_y_n':a['force_n'][i][1],'max_tension_n':max(a['tension_n'][i]),'max_tendon_speed_m_s':max(map(abs,a.get('tendon_speed_m_s',a.get('tendon_velocity_m_s'))[i])),'max_tendon_stroke_from_initial_m':max(abs(x-y) for x,y in zip(a['tendon_length_m'][i],a['tendon_length_m'][0]))} for i,t in enumerate(ts)])
    prep=Path(r['model_xml']).parent/'native_feedback_preparation.json' if r['model_xml'] else None
    if prep and lp(prep).exists():
        p=read(prep);r['native_preparation_summary']={k:p[k] for k in ['method','scope','equilibrium_diagnostics','native_cost','physics_steps'] if k in p}
    # Export exact raw selected evidence (no model changes, no numerical reruns).
    # The incomplete NMPC episode has no completed acceptance object. Preserve
    # literal null from its original result; the separately completed evaluator
    # remains a raw failure, never a fabricated completed acceptance.
    original_result=st['arts'].get(r['result_artifact_id'],{})
    if 'scientific_results' in original_result:original_result=original_result.get('result',{})
    write('SOURCE_EXTRACTS/'+node+'_acceptance.json',original_result.get('acceptance'))
    write('SOURCE_EXTRACTS/'+node+'_raw_evaluation.json',st['arts'].get(r['evaluation_artifact_id']))

csvwrite('candidate_timeline.csv',timelines)
csvwrite('metric_history.csv',metric_rows)
write('STATE_SNAPSHOTS.json',snapshots)

# Exact original rationale plus clearly separated curatorial analysis.
decision_rows=[]
selection_ids={'expert_run01':['77a4a9320e4f56030543b2bfd8a6ba8e7f78f77385782fa7d5a6bbf22476fdce','dce15e536648c0ec0f321826f5a78817dcc2a07e2f6f64017732bb9430f5ba8a','b8db2e142d5dc9582ba4141853ded3b82cefb2c3228dad5ff7c7fcb1eede4e27'],'T10_RUN_02':['428a13ff0dae161c5b7262e5e4f9c26ced52be23fdb9ae63889761290c8f540d','90263f3109d3abf414884b7d1dce7a135b2653417c131a839823cf48ab58c6a2'],'T10_RUN_03':['93212a99b4ba111ba58bf8a74809f0ec3e793e81bc1f7686cc8899603f40ab3a','cf129b7efdb5873696907caf08c32cfcec9366713e2bb8f772a1160b36ca75de'],'T10_RUN_06':['48b6866f8e36a60944a640c1bc9fee3d86afc70f8f2fd3c6c03b15cb55b08a25','567bae4500d3abeb15ebd9a866c8ccd3204732dda1bd49e42ff7f621f087a49a']}
for d in all_decisions:
    if d['decision_artifact_id'] not in selection_ids.get(d['source_tag'],[]):continue
    decision_rows.append({'task_id':'T10','source_tag':d['source_tag'],'decision_id':d['decision_artifact_id'],'actor_original':d['actor'],'actor_interpretation':'Codex surrogate / expert; no formal Main/Provider execution','timestamp':d['timestamp'],'observation':'See exact recorded rationale; not inferred hidden reasoning','hypothesis':'unavailable as separately named original field','investigation':d['selected_tool'],'evidence':d['evidence'],'decision':d['rationale_summary'],'action':d['next_operation'],'outcome':'Matched physical results in candidate_timeline.csv; rationale text is retained verbatim','research_question_original':d['research_question'],'source':d['source_ref'],'evidence_type':'original trace.decision artifact'})
# Control default mismatch is an explicitly recorded provenance observation, not a fabricated trace decision.
p=BASE/'T10_RUN_05/REPAIR_VARIANT_PROVENANCE.json';pr=read(p)
decision_rows.append({'task_id':'T10','source_tag':'T10_RUN_05','decision_id':'COMMON_CONTROLLER_DEFAULT_ALIGNMENT','actor_original':'unavailable in this provenance file','actor_interpretation':'recorded implementation/provenance action; not Main internal reasoning','observation':pr['reason'],'hypothesis':'unavailable as separately named original field','investigation':'strict joint validation / resolved common controller identity','evidence':pr.get('previous_results'),'decision':'Align legal default choices only, keep physical domains/control bounds','action':pr.get('only_default_choices_changed'),'outcome':'run06 prephysics common controller check passed; all five newly executed','source':str(p),'evidence_type':'original repair provenance; separate from scientific controller-route change'})
csvwrite('agent_decision_timeline.csv',decision_rows)

final_rows=[]
for r in final:
    final_rows.append({'task_id':'T10','condition_id':r['condition_id'],'role':r['protocol_role'],'accepted':r['accepted'],'source_study':r['study_id'],'candidate_id':r['candidate_id'],**r['metrics'],'failed_constraints':[c['name'] for c in r['raw_constraints'] if not c['satisfied']],'source':r['result_ref'],'raw_evaluation':artref(Path(r['store_path']),r['evaluation_artifact_id']),'model_xml':r['model_xml']})
csvwrite('FINAL_CASE_RESULTS.csv',final_rows)
csvwrite('all_physical_result_index.csv',[{k:v for k,v in r.items() if not k.startswith('_') and k not in ['controller','raw_constraints','selection']} for r in results])

bundle={'task_id':'T10','task_name':'Impact-Recovery Control','scope':'historical FULL/C result plus retained control-route history; no new solver, integration or optimization','actor':'Codex expert / codex_surrogate_main; codex-surrogate-no-provider','official_full_study':'codex-expert-T10-20261113-verified-common','original_protocol':str(BASE/'T10_RUN_06/TASK_PROTOCOL.json'),'original_required_cases':['positive_y','negative_y','no_impulse'],'control_cases':['positive_y_frozen','negative_y_frozen'],'structural_evolution':False,'structure_note':'mandatory original M2 hardware; two flexible segments 0.16/0.11 m, six tendons, six actuators, 12 cells each and 48 hinge DOFs','selected_nodes':[{k:v for k,v in r.items() if not k.startswith('_')} for r in selected],'all_physical_results':[{k:v for k,v in r.items() if not k.startswith('_') and k not in ['controller','selection']} for r in results],'render_snapshots':str(OUT/'STATE_SNAPSHOTS.json'),'render_recommendation':'Final negative_y initial/prehold/pulse_peak/recovery/final plus negative_y_frozen recovery/final, and rejected GVS no_impulse final. State loading + mj_forward only. No dynamics integration. Use same camera/scale for the same fixed robot.','comparison_warning':'Do not connect different cases, open-loop seeds, GVS controllers, native feedback or different implementation versions into one convergence curve.','missing':['authoritative Codex host token usage unavailable','no formal Main/Provider repeat run','separate original hypothesis field unavailable; exact rationale retained','XML/state load validation delegated to unified renderer; snapshots taken from actual stored dense arrays'],'source_stores':[str(s['store']) for s in stores]}
write('evidence_bundle.json',bundle)
print('wrote',len(timelines),'nodes',len(results),'physical results',len(all_candidates),'candidate artifacts',len(all_decisions),'original decision artifacts',len(snapshots),'saved snapshots')
