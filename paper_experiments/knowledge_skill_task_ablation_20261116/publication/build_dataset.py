"""Offline extraction. SQLite connections are read-only; no execution API is imported.

Run with the repository's .pilot-env Python. Writes only publication products,
summary/, episode_manifests/, selected_cases/ and raw_archive/. Never run the old
analyze.py: it writes derived files into original episode directories.
"""
import csv,gzip,lzma,hashlib,json,math,os,re,sqlite3,sys,time,statistics,shutil
from collections import Counter,defaultdict
from pathlib import Path
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[1]
CORE=Path(os.environ.get('SOFTROBOT_CORE_OVERRIDE',json.loads((R/'PREFERRED_CORE_RUNTIME.json').read_text())['core_directory']))
sys.path[:0]=[str(CORE),'C:/Users/gugugaga/miniconda3/envs/softagent/Lib/site-packages']
from tools.platform_store import Store
from tools.research.feedback import task_gap
from tools.state_io import digest
from tools.research_tasks import _outcome_issue,_source_issue
COND=['K0S0','K1S0','K0S1','K1S1']
TASKS=[f'T{i:02}' for i in range(1,11)]+['PHS2D']
EXPECTED={'K0S0':['T02','T06','T09'],'K1S0':['T03','T05','T06','T07','T08','T10'],
 'K0S1':['T01','T02','T04','T05','T06','T08'],'K1S1':TASKS}
SELECTED={'T03':'knowledge_only','T05':'knowledge_only','T01':'skill_only','T04':'skill_only','T09':'joint_knowledge_skill','PHS2D':'joint_knowledge_skill'}
def load(p,default=None):
 return json.loads(Path(p).read_text(encoding='utf-8-sig')) if Path(p).exists() else default
def rows(p):
 if not Path(p).exists():return
 with Path(p).open(encoding='utf-8-sig') as f:
  for n,line in enumerate(f,1):
   if line.strip():
    try:yield n,json.loads(line)
    except json.JSONDecodeError: ISSUES.append({'path':rel(p),'line':n,'issue':'unparseable_json_line'})
def dump(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def csvout(p,rs,fields=None):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 fields=fields or list(dict.fromkeys(k for r in rs for k in r)) or ['task_id','condition','status']
 with p.open('w',newline='',encoding='utf8') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in rs:w.writerow({k:json.dumps(v,ensure_ascii=False,separators=(',',':')) if isinstance(v,(list,dict)) else '' if v is None else v for k,v in r.items() if k in fields})
def rel(p):
 p=Path(str(p).removeprefix('\\\\?\\'))
 try:return Path(p).relative_to(R).as_posix()
 except ValueError:return str(p)
def aid(ref):return ref.get('artifact_id') if isinstance(ref,dict) else ref
def finite(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def compact_result(c):
 o=c.get('result') or {};v=o.get('result',o) if isinstance(o,dict) else {};return v if isinstance(v,dict) else {}
def operation(c):
 a=c.get('arguments') or {};t=c['tool']
 if t=='research_plan':return (a.get('plan') or {}).get('action','invalid_plan')
 if t=='research_analysis':return (a.get('request') or a.get('analysis') or {}).get('method','mathematical_analysis')
 if t=='core_operation':return (a.get('operation') or {}).get('tool_id','unknown_operation')
 if t=='experience_retrieve':return 'resource_'+(a.get('query') or {}).get('operation','search')
 return t
def category(c):
 op=operation(c);t=c['tool']
 if c.get('status')=='failed':return 'invalid_or_interrupted_interface'
 if op in ['select','stop']:return 'validation_and_stopping'
 if op=='generate' or 'structure' in op:return 'structure_generation'
 if op in ['execute','physical_replay'] or any(w in op for w in ['physical.execute','task.evaluate']):return 'physical_evaluation'
 if 'confirm' in op or 'validat' in op:return 'independent_validation'
 if 'match' in op:return 'matched_comparison'
 if 'search' in op or 'optim' in op:return 'optimization_search'
 if t=='research_analysis':return 'mathematical_analysis'
 if t in ['evidence_read','evidence_page','research_state']:return 'diagnosis_and_evidence_read'
 if t=='experience_retrieve':return 'resource_access'
 return 'other_registered_operation'
def token_usage(folder,key):
 seen_files={};turns={};catalog=[]
 paths=[]
 for root,dirs,files in os.walk(folder):
  dirs[:]=[d for d in dirs if d not in ['STORE','receipts','__pycache__']]
  paths.extend(Path(root)/n for n in files if 'CODEX_EVENTS' in n and n.endswith('.jsonl'))
 paths.sort()
 for p in paths:
  if 'STORE' in p.relative_to(folder).parts:continue
  digest=sha(p);thread=None;lastitem=None;num=0
  if digest in seen_files:
   catalog.append(dict(**key,path=rel(p),sha256=digest,duplicate_of=seen_files[digest],completed_turns=0));continue
  seen_files[digest]=rel(p)
  for line,e in rows(p):
   if e.get('type')=='thread.started':thread=e.get('thread_id')
   if e.get('item',{}).get('id'):lastitem=e['item']['id']
   if e.get('type')=='turn.completed' and isinstance(e.get('usage'),dict):
    u=e['usage'];ident=(thread,lastitem,json.dumps(u,sort_keys=True)) if thread else (digest,line)
    if ident not in turns:turns[ident]=dict(usage=u,path=rel(p),line=line,thread_id=thread);num+=1
  catalog.append(dict(**key,path=rel(p),sha256=digest,duplicate_of=None,completed_turns=num))
 sums={k:sum(t['usage'].get(k,0) for t in turns.values()) for k in ['input_tokens','cached_input_tokens','output_tokens','reasoning_output_tokens']} if turns else {}
 # Reasoning is normally a subset of output, never added to total.
 return dict(**sums,total_tokens=(sums.get('input_tokens',0)+sums.get('output_tokens',0)) if turns else None,
  uncached_input_tokens=(sums['input_tokens']-sums['cached_input_tokens']) if turns else None,
  recorded_completed_turns=len(turns),token_coverage='deduplicated recorded completed turns; interrupted usage may be absent'),catalog,list(turns.values())
def artifact(store,ref,paths=None):
 try:return store.artifact(ref,paths=paths)
 except Exception as e:ISSUES.append({'reference':ref,'issue':'artifact_projection_error','detail':str(e)[:500]});return {}
def physical_gap(v):
 a=v.get('acceptance') or {}
 if a.get('protocol_id')!='offline_frozen_task_v1':return task_gap(v)
 valid=_outcome_issue(a) is None and _source_issue(a) is None
 margins=a.get('constraint_margins') or {};gaps={};unscaled=[]
 for name,m in margins.items():
  lim=m.get('limit');margin=m.get('margin')
  if finite(lim) and finite(margin) and lim!=0:gaps[name]=max(0.,-margin/abs(lim))
  elif finite(margin) and margin>=0:gaps[name]=0.
  else:unscaled.append(name)
 return dict(valid_complete=valid,accepted=a.get('accepted'),normalized_gap=max(gaps.values()) if valid and gaps and not unscaled else None,
  components=gaps,unscaled_constraints=unscaled,definition='max(0,-native_margin/abs(native_limit)); satisfied zero bounds contribute zero; violated zero bounds unknown',
  outcome_issue=_outcome_issue(a),source_issue=_source_issue(a))

ISSUES=[];cells=load(R/'FORMAL_COHORT_MANIFEST.json')['cells'];TASKROWS=[];ACTIONS=[];EVENTS=[];RESOURCES=[];COSTS=[];EV=[];CANDIDATES=[];PROGRESS=[];TOKENFILES=[];SOURCES=[];MANIFESTS=[];RESOURCE_AVAILABLE=[]
(R/'raw_archive').mkdir(exist_ok=True)
inventory_stream=gzip.open(R/'raw_archive/ORIGINAL_FILE_MANIFEST.csv.gz','wt',encoding='utf8',newline='')
inventory_writer=csv.DictWriter(inventory_stream,fieldnames=['task_id','condition','episode_id','path','bytes','mtime_ns','sha256','hash_status','storage']);inventory_writer.writeheader()
inventory_count=0;inventory_bytes=0;inventory_hashed=0
start=time.time()
for cell in cells:
 task,cond=cell['task'],cell['condition'];f=R/cell['path'];key=dict(task_id=task,condition=cond,episode_id=cell['episode_id']);print('Indexing',task,cond,flush=True)
 dbpath=f/'STORE/platform.sqlite';before=dbpath.stat();store=Store(f/'STORE')
 with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True) as db:
  db.execute('PRAGMA query_only=ON');s=json.loads(db.execute('select state from sessions where run_id=?',(cell['episode_id'],)).fetchone()[0])
  native_calls=[]
  for rr in db.execute('select run_id,request_id,receipt from calls where run_id=? or substr(run_id,1,?)=?',(cell['episode_id'],len(cell['episode_id'])+1,cell['episode_id']+'-')):
   native_calls.append(dict(run_id=rr[0],request_id=rr[1],receipt=json.loads(rr[2]) if rr[2] else None))
 calls=[];callseen=set()
 for n,c in rows(f/'CORE_CALLS.jsonl'):
  # Retain original physical line as a trace locator. Duplicate IDs are audited.
  if c['request_id'] in callseen:ISSUES.append(dict(**key,issue='duplicate_bridge_request_id',request_id=c['request_id']))
  callseen.add(c['request_id']);c['_line']=n;calls.append(c)
 events=list(rows(f/'DECISION_EVENTS.jsonl'));byid={c['request_id']:c for c in calls}
 for n,e in events:
  EVENTS.append({**key,**e,'source_path':rel(f/'DECISION_EVENTS.jsonl'),'source_line':n})
 for c in calls:
  out=compact_result(c);event=(c.get('arguments') or {}).get('event') or {};refs=c.get('new_references') or []
  if (c.get('core_receipt') or {}).get('output'):refs=refs+[(c['core_receipt'])['output']]
  ACTIONS.append(dict(**key,request_id=c['request_id'],timestamp=c.get('started_at'),operation=operation(c),category=category(c),
   tool=c['tool'],transport_status=c.get('status'),native_status=out.get('status'),wall_s=c.get('wall_s'),
   source_path=rel(f/'CORE_CALLS.jsonl'),source_line=c['_line'],result_references=list({aid(r):r for r in refs if aid(r)}.values()),
   error=c.get('error'),hypothesis=event.get('hypothesis'),decision=event.get('selected_action'),next_step=event.get('next_research_step')))
  if c['tool']=='experience_retrieve':
   q=c['arguments'].get('query') or {};o=c.get('result') or {};resources=o.get('results') or []
   resourceid=q.get('entry_id');revision=q.get('revision');rr=next((x for x in resources if x.get('entry_id',x.get('id'))==resourceid),{})
   assessments=[a for cc in calls for a in ((cc.get('arguments') or {}).get('event') or {}).get('resource_assessments',[]) if a.get('resource')==f'{resourceid}@{revision}'] if resourceid else []
   linked=[cc for cc in calls if f'{resourceid}@{revision}' in (((cc.get('arguments') or {}).get('event') or {}).get('resource_references') or [])] if resourceid else []
   row=dict(**key,resource_id=resourceid,revision=revision,resource_role=rr.get('resource_role',q.get('knowledge_type')),
    access=q.get('operation','search'),detail=q.get('detail','full'),request_id=c['request_id'],timestamp=c.get('started_at'),
    transport_status=c['status'],read_returned_body=bool(resources) and q.get('operation')=='read' and c['status']=='completed',
    matched_count=o.get('matched_count'),receipt=o.get('reference'),trigger=event.get('research_question'),hypothesis=event.get('hypothesis'),
    declared_disposition=assessments[-1].get('disposition') if assessments else 'unassessed',
    self_reported_hypothesis_changed=any(a.get('hypothesis_changed') for a in assessments) if assessments else None,
    self_reported_action_changed=any(a.get('action_changed') for a in assessments) if assessments else None,
    assessment_explanations=[a.get('explanation') for a in assessments],linked_request_ids=[cc['request_id'] for cc in linked],
    linked_operations=[operation(cc) for cc in linked],linked_result_references=[r for cc in linked for r in cc.get('new_references',[])],
    actual_causal_influence='not_established',subsequent_research_change='self-report only' if assessments else 'unknown',
    source_path=rel(f/'CORE_CALLS.jsonl'),source_line=c['_line'])
   RESOURCES.append(row)
   dump(R/'raw_archive/resource_receipts'/f'{task}_{cond}_{c["_line"]}.json',dict(source_path=rel(f/'CORE_CALLS.jsonl'),source_line=c['_line'],original_call=c))
 manifest_resources=load(f/'RESOURCE_MANIFEST.json',{}).get('entries',[])
 for rr in manifest_resources:
  RESOURCE_AVAILABLE.append(dict(**key,entry_id=rr.get('entry_id',rr.get('id')),revision=rr.get('revision'),role=rr.get('resource_role'),summary=rr.get('summary'),availability_only=True))
 token,catalog,turns=token_usage(f,key);TOKENFILES.extend(catalog)
 selected_calls=[c for c in calls if c['tool']=='research_plan' and compact_result(c).get('selected') is True and compact_result(c).get('task_passed') is True and c['status']=='completed']
 selected=bool(s.get('selected'));passed=selected and (bool((s.get('success_gate') or {}).get('observed_task_pass')) or bool(selected_calls))
 if passed!=(task in EXPECTED[cond]):ISSUES.append(dict(**key,issue='acceptance_matrix_discrepancy',reconstructed=passed,expected=task in EXPECTED[cond]))
 if s.get('research_status')!='stopped' or s.get('pending'):ISSUES.append(dict(**key,issue='nonterminal_native_study'))
 # Direct selected/disposition artifacts are compact authoritative receipts.
 selected_doc=artifact(store,s['selected']) if selected else None
 disposition=artifact(store,s['final_disposition']) if s.get('final_disposition') else None
 if selected_doc:dump(R/'raw_archive/final_receipts'/f'{task}_{cond}_selected.json',dict(source_store=rel(dbpath),reference=s['selected'],document=selected_doc))
 if disposition:dump(R/'raw_archive/final_receipts'/f'{task}_{cond}_disposition.json',dict(source_store=rel(dbpath),reference=s['final_disposition'],document=disposition))
 required=[x['condition_id'] for x in s['spec'].get('task_conditions',[]) if x.get('role','required')=='required'] or ['default']
 gate=s.get('success_gate') or {};finalcandidate=gate.get('candidate') or (selected_doc or {}).get('candidate')
 if not finalcandidate and selected_calls:finalcandidate=selected_calls[-1]['arguments'].get('plan',{}).get('candidate')
 if not finalcandidate:
  for c in reversed(calls):
   cand=(c['arguments'].get('plan') or {}).get('candidate')
   if cand:finalcandidate=cand;break
 # Candidates are small. Mathematical artifacts retain potentially huge arrays,
 # so evidence fields are projected and content hashes verified by Store.
 canmap={}
 for identity,ref in s.get('candidates',{}).items():
  cv=artifact(store,ref,paths=['condition_id','physical_design_identity','design_identity','created_at','parent','origin','configuration.robot.structure','configuration.task'])
  cfg=cv.pop('configuration',{});ct=cfg.get('task',{})
  if cfg.get('robot',{}).get('structure'):cv['physical_design_identity']=cv.get('physical_design_identity') or digest(cfg['robot']['structure'])
  if not cv.get('condition_id'):
   exact=[x['condition_id'] for x in s['spec'].get('task_conditions',[]) if all(ct.get(k)==x.get('task',{}).get(k) for k in ['goal','timing','acceptance'])]
   cv['condition_id']=exact[0] if len(exact)==1 else 'default' if len(required)==1 else None
   cv['condition_id_source']='unique exact frozen goal/timing/acceptance match; qualified initializer provenance remains separate'
  canmap[aid(ref)]=dict(identity=identity,**cv)
  CANDIDATES.append(dict(**key,candidate=ref,identity=identity,**cv))
 # All actual physical results, including failures; no reliance on stale exports.
 refs={aid(ref):ref for ref in s.get('results',[])+s.get('physical_replays',[])}
 evaluations=[];cumulative_steps=0;observed_steps=False;unknown_steps=0
 for ref in refs.values():
  v=artifact(store,ref,paths=['kind','task_gap','candidate','status','route','acceptance','profile.physics_steps','profile.complete','profile.solver_status','profile.last_valid_time_s','profile.valid_complete_execution','profile.evaluation_validity','physical_launches','actual_resource_consumption','numerical_s','execution.boundary','boundary','independent_evaluation_executed','passed','episodes','diagnostic_task_gap'])
  try:gap=physical_gap(v)
  except Exception as e:gap={};ISSUES.append(dict(**key,issue='gap_projection_unavailable',reference=ref,detail=str(e)[:300]))
  candidate=aid(v.get('candidate'));cm=canmap.get(candidate,{})
  row=dict(**key,reference=ref,candidate=v.get('candidate'),structure=cm.get('physical_design_identity',cm.get('design_identity')),
   case_id=cm.get('condition_id'),native_status=v.get('status'),accepted=(v.get('acceptance') or {}).get('accepted',v.get('passed')),
   valid_complete=gap.get('valid_complete'),normalized_violation=gap.get('normalized_gap'),gap=gap,
   independent=ref in s.get('physical_replays',[]) or v.get('independent_evaluation_executed') is True,
   solver_status=(v.get('profile') or {}).get('solver_status'),last_valid_time_s=(v.get('profile') or {}).get('last_valid_time_s'),
   physics_steps=(v.get('actual_resource_consumption') or {}).get('physics_steps',(v.get('profile') or {}).get('physics_steps')),physical_launches=v.get('physical_launches'),numerical_s=v.get('numerical_s'))
  if finite(row['physics_steps']):cumulative_steps+=row['physics_steps'];observed_steps=True
  else:unknown_steps+=1
  evaluations.append(row);EV.append(row)
  dump(R/'raw_archive/evidence_metadata'/task/cond/f'{aid(ref)}.json',dict(source_store=rel(dbpath),reference=ref,projection_paths=['acceptance','candidate','profile metadata','task_gap','episodes'],document=v))
 # Exclude partial trajectories from violation scores, and require common
 # structure across original task conditions. Embedded T08/PHS2D protocols
 # cover multiple physical cases inside a single independent evidence artifact.
 valid=[e for e in evaluations if e['valid_complete'] and finite(e['normalized_violation'])]
 groups=defaultdict(list)
 for e in valid:
  if e['independent']:groups[e['structure']].append(e)
 protocol=[]
 for structure,es in groups.items():
  if task in ['T08','PHS2D']:protocol.extend(e['normalized_violation'] for e in es)
  elif structure and set(required)<={e['case_id'] for e in es}:
   protocol.append(max(min(e['normalized_violation'] for e in es if e['case_id']==case) for case in required))
 normmax=max([e['normalized_violation'] for e in valid],default=None)
 # All current native cost counters are observations; solver charge is not
 # automatically treated as measured compute time.
 counters=dict(mathematical_evaluations=s.get('mathematical_evaluations'),nmpc_launches=s.get('nmpc_launches'),physical_replay_launches=s.get('physical_replay_launches'),
  native_charged_numerical_s=s.get('numerical_s'),analysis_cost_records=s.get('analysis_costs'))
 ledger=store.remaining(cell['episode_id'])
 physics=ledger['used']['backend_solves']
 status=load(f/'STATUS.json',{});initial=load(f/'INITIAL_STATE.json',{});sess=load(f/'SESSION.json',{})
 originalbudget=cell.get('initial_budgets',{});currentbudget=s['spec'].get('budgets',{})
 close=(load(R/'FINAL_NATIVE_COHORT_CLOSURE_20261120.json')['cells']);termination=next((x.get('termination_category') for x in close if x['task']==task and x['condition']==cond),None)
 research_actions=[a for a in ACTIONS if a['episode_id']==cell['episode_id']]
 actualresources=[r for r in RESOURCES if r['episode_id']==cell['episode_id']]
 row=dict(**key,knowledge_enabled='K1' in cond,skill_enabled='S1' in cond,initial_candidate=initial.get('reference_candidate'),final_candidate=finalcandidate,
  accepted=passed,formal_select_status='selected' if passed else 'not_selected',required_pass_count=len(required),maximum_violation=normmax,
  final_violation=0.0 if passed and protocol and min(protocol)==0 else None,best_violation=min(protocol,default=None),
  candidate_count=len(s.get('candidates',{})),research_action_count=len(calls),evidence_count=len({aid(x) for k in ['results','physical_replays','analysis_results','search_results','mechanics_results'] for x in s.get(k,[])}),
  total_core_calls=len(calls),total_tokens=token.get('total_tokens'),mathematical_cost=s.get('mathematical_evaluations'),physics_cost=physics,
  wall_clock_time=max(0,s.get('closed_unix',status.get('finished_unix',time.time()))-s.get('started_unix',0)) if s.get('closed_unix') else status.get('wall_s'),
  native_research_status=s.get('research_status'),native_pending=bool(s.get('pending')),termination_category=termination,
  initial_identity=sess.get('initial_identity'),initial_core_commit=sess.get('core_commit'),select_request_id=selected_calls[-1]['request_id'] if selected_calls else None,
  selected_reference=s.get('selected'),final_disposition_reference=s.get('final_disposition'),
  original_physical_limit=originalbudget.get('physical_launches'),recorded_final_physical_limit=currentbudget.get('physical_launches'),
  original_mathematical_limit=originalbudget.get('mathematical_evaluations'),recorded_final_mathematical_limit=currentbudget.get('mathematical_evaluations'),
  knowledge_reads=sum(r['read_returned_body'] and r['resource_role']=='knowledge' for r in actualresources),skill_reads=sum(r['read_returned_body'] and r['resource_role']=='skill' for r in actualresources),
  resource_manifest_entries=len(manifest_resources),valid_complete_physical_evidence=len(valid),complete_protocol_violation_observations=len(protocol),
  independent_physical_evidence=sum(e['independent'] for e in evaluations),source_episode_path=rel(f))
 TASKROWS.append(row)
 costs=dict(**key,**token,provider_requests=None,core_tool_calls=len(calls),native_receipt_count=len(native_calls),native_ledger=ledger,
  native_unsealed_calls=sum(x['receipt'] is None for x in native_calls),
  knowledge_searches=sum(r['access']=='search' and r['resource_role']=='knowledge' for r in actualresources),
  skill_searches=sum(r['access']=='search' and r['resource_role']=='skill' for r in actualresources),
  untyped_searches=sum(r['access']=='search' and r['resource_role'] not in ['skill','knowledge'] for r in actualresources),
  knowledge_reads=row['knowledge_reads'],skill_reads=row['skill_reads'],mathematical_evaluations=row['mathematical_cost'],
  physical_launches=physics,launch_counter_nmpc=s.get('nmpc_launches'),launch_counter_replay=s.get('physical_replay_launches'),recorded_physical_integration_steps=cumulative_steps if observed_steps else None,
  physical_evidence_with_missing_step_count=unknown_steps,measured_solver_runtime_s=None,native_charged_numerical_s=s.get('numerical_s'),
  wall_clock_time_s=row['wall_clock_time'],original_budgets=originalbudget,recorded_final_budgets=currentbudget,
  timing_semantics='calendar duration includes waiting and interface intervals; native charge can contain conservative exit bounds')
 COSTS.append(costs)
 # Milestones are observable operations, not scores of scientific decision quality.
 for a in research_actions:
  index=sum(1 for e in PROGRESS if e['episode_id']==key['episode_id'])+1
  PROGRESS.append(dict(**key,event_index=index,request_id=a['request_id'],timestamp=a['timestamp'],category=a['category'],
   cumulative_core_calls=index,candidate_generation_observed=a['operation']=='generate',physical_action_observed=a['category']=='physical_evaluation',formal_select_observed=a['request_id']==row['select_request_id']))
 native_summary={k:s.get(k) for k in ['research_status','pending','selected','success_gate','reference_candidate','final_disposition','selected_solution','public_prior_manifest','started_unix','closed_unix','nmpc_launches','physical_replay_launches','mathematical_evaluations','numerical_s']}
 manifest=dict(**key,source_episode=rel(f),store=rel(dbpath),initial_identity=sess.get('initial_identity'),initial_state_source=rel(f/'INITIAL_STATE.json'),
  task_protocol=load(f/'TASK_PROTOCOL.json'),session=sess,final_native_state=native_summary,acceptance=row,costs=costs,
  scientific_specification=s['spec'],original_budgets=originalbudget,recorded_final_budgets=currentbudget,
  candidates=canmap,evaluations=evaluations,final_selected_receipt=rel(R/'raw_archive/final_receipts'/f'{task}_{cond}_selected.json') if selected else None,
  bridge_calls_source=rel(f/'CORE_CALLS.jsonl'),decision_source=rel(f/'DECISION_EVENTS.jsonl'),
  counts={'calls':len(calls),'events':len(events),'native_receipts':len(native_calls),'resource_accesses':len(actualresources)},
  source_store_stat_before={'size':before.st_size,'mtime_ns':before.st_mtime_ns},
  raw_availability='Complete originals retained at source_episode; compact projections and selected logs included in Git.')
 dest=R/'episode_manifests'/task/f'{cond}.json';dump(dest,manifest);MANIFESTS.append(dict(task_id=task,condition=cond,path=rel(dest)))
 if task in SELECTED:
  dest=R/'selected_cases'/SELECTED[task]/task/cond;dest.mkdir(parents=True,exist_ok=True)
  for name in ['CORE_CALLS.jsonl','DECISION_EVENTS.jsonl','RESOURCE_TO_ACTION.jsonl','RESOURCE_ACTION_EDGES.jsonl','RESOURCE_ASSESSMENTS.jsonl']:
   p=f/name
   if p.exists():
    with p.open('rb') as inp,lzma.open(dest/(name+'.xz'),'wb',filters=[{'id':lzma.FILTER_LZMA2,'dict_size':64*1024*1024}]) as out:shutil.copyfileobj(inp,out,1024*1024)
  dump(dest/'TRACE_INDEX.json',dict(**key,source_episode=rel(f),manifest=rel(R/'episode_manifests'/task/f'{cond}.json'),
   exact_core_calls='CORE_CALLS.jsonl.xz',exact_decisions='DECISION_EVENTS.jsonl.xz',evaluations=evaluations))
 # A complete local file inventory, without duplicating giant Store arrays.
 for root,dirs,files in os.walk('\\\\?\\'+str(f)):
  dirs[:]=[d for d in dirs if d!='__pycache__']
  for name in files:
   p=Path(root)/name;st=p.stat();critical=Path(str(p).removeprefix('\\\\?\\')).parent==f and name in ['STATUS.json','SESSION.json','INITIAL_STATE.json','STUDY_CONFIG.json','TASK_PROTOCOL.json','CORE_CALLS.jsonl','DECISION_EVENTS.jsonl','RESOURCE_MANIFEST.json']
   ir=dict(**key,path=rel(p),bytes=st.st_size,mtime_ns=st.st_mtime_ns,sha256=sha(p) if critical else None,
    hash_status='sha256_verified' if critical else 'indexed_stat_only',storage='original_local_archive')
   inventory_writer.writerow(ir);inventory_count+=1;inventory_bytes+=st.st_size;inventory_hashed+=critical
   if critical:SOURCES.append(ir)
 inventory_stream.flush()
 after=dbpath.stat()
 if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):ISSUES.append(dict(**key,issue='source_store_stat_changed'))
 dump(R/'publication/BUILD_PROGRESS.json',dict(task=task,condition=cond,cells_done=len(TASKROWS),source_files=inventory_count,elapsed_s=time.time()-start))
 print('  calls',len(calls),'evaluations',len(evaluations),'accepted',passed,'seconds',round(time.time()-start,1),flush=True)

summary=R/'summary'
for name,data in [('TASK_RESULTS',TASKROWS),('RESEARCH_ACTIONS',ACTIONS),('DECISION_EVENTS',EVENTS),('RESOURCE_TO_ACTION',RESOURCES),('RESOURCE_COSTS',COSTS),('PHYSICAL_EVIDENCE',EV),('CANDIDATE_EVOLUTION',CANDIDATES),('RESEARCH_PROGRESS',PROGRESS),('TOKEN_SOURCE_FILES',TOKENFILES),('RESOURCE_AVAILABILITY',RESOURCE_AVAILABLE)]:csvout(summary/f'{name}.csv',data)
inventory_stream.close()
csvout(R/'raw_archive/CRITICAL_SOURCE_HASHES.csv',SOURCES)
dump(R/'selected_cases/SELECTED_TRACE_MANIFEST.json',dict(selected_tasks=list(SELECTED),matched_cells=24,cases=[dict(task_id=t,category=k,conditions=[m for m in MANIFESTS if m['task_id']==t]) for t,k in SELECTED.items()]))
shutil.copyfile(R/'aggregate/HISTORICAL_FULL_REFERENCE.csv',summary/'HISTORICAL_FULL_REFERENCE.csv')
for name in ['SETUP_INVALID_COSTS.csv','T10_CONTROLLER_SETUP_INVALID_COSTS.csv']:
 if (R/'aggregate'/name).exists():shutil.copyfile(R/'aggregate'/name,summary/name)
conditionrows=[]
for cond in COND:
 rs=[r for r in TASKROWS if r['condition']==cond];cs=[r for r in COSTS if r['condition']==cond]
 row=dict(condition=cond,tasks=len(rs),accepted=sum(r['accepted'] for r in rs),acceptance_rate=sum(r['accepted'] for r in rs)/len(rs),
  average_violation=None,median_violation=None,violation_note='not pooled across heterogeneous tasks or incomplete protocols')
 for k in ['research_action_count','candidate_count','total_core_calls','total_tokens','mathematical_cost','physics_cost','wall_clock_time','valid_complete_physical_evidence','knowledge_reads','skill_reads']:
  vals=[r[k] for r in rs if finite(r.get(k))];row[k+'_sum']=sum(vals) if vals else None;row[k+'_observed_tasks']=len(vals)
 conditionrows.append(row)
csvout(summary/'CONDITION_SUMMARY.csv',conditionrows)
effects=[]
for metric in ['accepted','candidate_count','research_action_count','mathematical_cost','physics_cost','total_tokens','wall_clock_time','best_violation']:
 for task in TASKS:
  rs={r['condition']:r for r in TASKROWS if r['task_id']==task};v=[rs[c][metric] for c in COND]
  ok=all(isinstance(x,(int,float,bool)) and math.isfinite(x) for x in v)
  if metric=='best_violation':ok=ok and all(rs[c]['complete_protocol_violation_observations']>0 for c in COND)
  a,b,c,d=v
  effects.append(dict(task_id=task,metric=metric,K0S0=a,K1S0=b,K0S1=c,K1S1=d,complete=ok,
   knowledge_marginal=(b+d-a-c)/2 if ok else None,skill_marginal=(c+d-a-b)/2 if ok else None,interaction=d-b-c+a if ok else None,
   interpretation='descriptive recorded endpoint; resource exposure, accounting and stopping differ across cells'))
 foragg=[e for e in effects if e['metric']==metric and e['complete']]
 if metric!='best_violation':effects.append(dict(task_id='mean_of_matched_tasks',metric=metric,complete=len(foragg)==11,matched_tasks=len(foragg),
  **{k:statistics.mean(e[k] for e in foragg) if foragg else None for k in ['knowledge_marginal','skill_marginal','interaction']}))
csvout(summary/'FACTORIAL_EFFECTS.csv',effects)
dump(R/'publication/DATASET_AUDIT.json',dict(timestamp=datetime.now(timezone.utc).isoformat(),formal_cells=len(TASKROWS),
 reconstructed_passed=sum(r['accepted'] for r in TASKROWS),expected_passed=26,by_condition=conditionrows,
 source_file_count=inventory_count,source_total_bytes=inventory_bytes,source_hashed_files=inventory_hashed,
 selected_tasks=list(SELECTED),actual_resource_accesses=len(RESOURCES),actual_resource_body_reads=sum(r['read_returned_body'] for r in RESOURCES),
 issues=ISSUES,original_sources_opened_readonly=True,elapsed_s=time.time()-start))
print('Complete',len(TASKROWS),'cells;',len(ISSUES),'issues;',round(time.time()-start,1),'s',flush=True)
