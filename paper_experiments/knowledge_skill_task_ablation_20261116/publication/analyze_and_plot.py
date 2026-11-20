"""Reproducible analysis/figures from compact exports. Never opens a solver."""
import csv,json,math,sys,statistics,gzip,hashlib,shutil
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
csv.field_size_limit(256*1024*1024)
R=Path(__file__).resolve().parents[1]
sys.path.append('C:/Users/gugugaga/miniconda3/envs/softagent/Lib/site-packages')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import FancyBboxPatch
COND=['K0S0','K1S0','K0S1','K1S1'];LABEL=['K−S−','K+S−','K−S+','K+S+']
COLORS=['#707b87','#287ca4','#d38a26','#329669']
TASKS=[f'T{i:02}' for i in range(1,11)]+['PHS2D']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,
 'axes.titleweight':'bold','figure.dpi':150,'savefig.dpi':300,'pdf.fonttype':42,'axes.labelcolor':'#253144','text.color':'#253144'})
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def dump(p,v):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def cv(v):
 if v=='':return None
 if v in ['True','False']:return v=='True'
 try:return json.loads(v)
 except (ValueError,TypeError):return v
def readcsv(name):
 with (R/'summary'/f'{name}.csv').open(encoding='utf8',newline='') as f:return [{k:cv(v) for k,v in r.items()} for r in csv.DictReader(f)]
def csvout(p,rs,fields=None):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);fields=fields or list(dict.fromkeys(k for r in rs for k in r)) or ['task_id','condition','status']
 with p.open('w',encoding='utf8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in rs:w.writerow({k:json.dumps(v,ensure_ascii=False,separators=(',',':')) if isinstance(v,(dict,list)) else '' if v is None else v for k,v in r.items()})
def aid(v):return v.get('artifact_id') if isinstance(v,dict) else v
def finite(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
def rel(p):return Path(p).relative_to(R).as_posix()
def write(p,text):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text.rstrip()+'\n',encoding='utf8')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
T=readcsv('TASK_RESULTS');A=readcsv('RESEARCH_ACTIONS');E=readcsv('DECISION_EVENTS');EV=readcsv('PHYSICAL_EVIDENCE');C=readcsv('RESOURCE_COSTS');RA=readcsv('RESOURCE_TO_ACTION');F=readcsv('FACTORIAL_EFFECTS')
INDEX={(r['task_id'],r['condition']):r for r in T};M={(t,c):load(R/'episode_manifests'/t/f'{c}.json') for t in TASKS for c in COND}
FIG=R/'figures';DATA=FIG/'figure_data';DATA.mkdir(parents=True,exist_ok=True);FIGURES=[]
def save(fig,name,data,caption):
 fig.savefig(FIG/(name+'.png'),bbox_inches='tight',facecolor='white');fig.savefig(FIG/(name+'.pdf'),bbox_inches='tight',facecolor='white');plt.close(fig)
 csvout(DATA/(name+'.csv'),data);FIGURES.append(dict(name=name,png=f'figures/{name}.png',pdf=f'figures/{name}.pdf',data=f'figures/figure_data/{name}.csv',caption=caption))

# Exact public operation refinements from the unmodified bridge logs.
have_originals=all((R/M[t,c]['bridge_calls_source']).exists() for t in TASKS for c in COND)
mathrows=[] if have_originals else readcsv('MATHEMATICAL_EVIDENCE')
interventions=[] if have_originals else readcsv('CANDIDATE_INTERVENTIONS')
resourcechains=[] if have_originals else readcsv('RESOURCE_ACTION_CHAINS')
F=[r for r in F if r['metric'] not in ['completed_mathematical_evidence','time_to_formal_select_s']]
for t in TASKS if have_originals else []:
 for c in COND:
  m=M[t,c];folder=R/m['source_episode'];calls=[json.loads(l) for l in (folder/'CORE_CALLS.jsonl').open(encoding='utf8') if l.strip()]
  for n,call in enumerate(calls,1):
   o=call.get('result') or {};o=(o.get('result') or o) if isinstance(o,dict) else {};o=o if isinstance(o,dict) else {}
   event=call['arguments'].get('event',{});key=dict(task_id=t,condition=c,episode_id=m['episode_id'],request_id=call['request_id'],source_path=m['bridge_calls_source'],source_line=n)
   if call['tool']=='research_analysis':
    sc=o.get('scientific_computation') or {};mathrows.append(dict(**key,transport_status=call.get('status'),native_status=o.get('status'),complete=sc.get('complete'),
     charged_analysis_evaluations=o.get('charged_analysis_evaluations'),charged_numerical_s=o.get('charged_numerical_s'),
     internal_calculations=o.get('internal_calculations'),scientific_computation=sc,reference=o.get('reference'),task_acceptance=o.get('task_acceptance')))
   if event.get('resource_assessments'):
    for assessment in event['resource_assessments']:
     subsequent=next((cc for cc in calls[n:] if cc['tool'] in ['research_analysis','research_plan','core_operation'] and cc['status']=='completed'),None)
     resourcechains.append(dict(**key,resource=assessment['resource'],disposition=assessment['disposition'],declared_hypothesis_changed=assessment['hypothesis_changed'],declared_action_changed=assessment['action_changed'],
      applicability=assessment['applicability'],declared_explanation=assessment['explanation'],decision=event.get('selected_action'),
      linked_action=call['arguments'].get('plan',{}).get('action') or call['tool'],linked_result_references=call.get('new_references',[]),
      next_registered_request_id=subsequent['request_id'] if subsequent else None,
      next_registered_operation=(subsequent['arguments'].get('plan',{}).get('action') or subsequent['tool']) if subsequent else None,
      next_registered_result_references=subsequent.get('new_references') if subsequent else None,
      linkage_scope='explicit model attribution for linked action; next request is chronological, not proof of causation',episode_accepted=INDEX[t,c]['accepted']))
   if call['tool']=='research_plan' and call['arguments'].get('plan',{}).get('action')=='generate':
    interventions.append(dict(**key,timestamp=call.get('started_at'),parameters=call['arguments']['plan'].get('parameters'),hypothesis=event.get('hypothesis'),outcome=event.get('decision_outcome'),transport_status=call['status'],result_references=call.get('new_references',[])))
  start=m['final_native_state'].get('started_unix');sels=[call for call in calls if call['request_id']==INDEX[t,c].get('select_request_id')]
  INDEX[t,c]['time_to_formal_select_s']=sels[0]['started_unix']-start if sels and start else None
  INDEX[t,c]['completed_mathematical_evidence']=sum(r['complete'] is True for r in mathrows if r['episode_id']==m['episode_id'])
  INDEX[t,c]['mathematical_evidence_completion_unknown']=sum(r['complete'] is None for r in mathrows if r['episode_id']==m['episode_id'])
csvout(R/'summary/MATHEMATICAL_EVIDENCE.csv',mathrows);csvout(R/'summary/RESOURCE_ACTION_CHAINS.csv',resourcechains);csvout(R/'summary/CANDIDATE_INTERVENTIONS.csv',interventions);csvout(R/'summary/TASK_RESULTS.csv',T)
for cost in C:
 mr=[r for r in mathrows if r['episode_id']==cost['episode_id']]
 costs=[(r.get('scientific_computation') or {}).get('native_cost') or {} for r in mr]
 for field in ['kernel_wall_s','physics_steps','forward_evaluations','optimization_evaluations','optimization_iterations','rollouts']:
  vals=[r[field] for r in costs if finite(r.get(field))]
  cost['recorded_math_'+field]=sum(vals) if vals else None
  cost['math_records_without_'+field]=len(costs)-len(vals)
csvout(R/'summary/RESOURCE_COSTS.csv',C)

# Attach each physical observation to its recorded Core request/cumulative costs.
byref={}
for a in A:
 for ref in a.get('result_references') or []:byref.setdefault((a['episode_id'],aid(ref)),a)
eventbyid={e['core_request_id']:e for e in E}
for e in EV:
 a=byref.get((e['episode_id'],aid(e['reference'])),{});event=eventbyid.get(a.get('request_id'),{});cost=event.get('cost_information') or {}
 e.update(request_id=a.get('request_id'),timestamp=a.get('timestamp'),core_call_index=int(a['request_id'].rsplit('-',1)[-1]) if a.get('request_id','').rsplit('-',1)[-1].isdigit() else None,
  cumulative_mathematical_cost=cost.get('mathematical_evaluations_after'),cumulative_numerical_charge_s=cost.get('numerical_s_after'),
  cumulative_physical_cost=((cost.get('budget_after') or {}).get('used') or {}).get('backend_solves'))
csvout(R/'summary/PHYSICAL_EVIDENCE.csv',EV)

# Factorial contrasts for mathematics and SELECT timing. Missing/nonacceptance
# are not replaced with a finite time to success.
for metric in ['completed_mathematical_evidence','time_to_formal_select_s']:
 for t in TASKS:
  vals=[INDEX[t,c].get(metric) for c in COND];ok=all(finite(v) for v in vals);a,b,c,d=vals
  F.append(dict(task_id=t,metric=metric,K0S0=a,K1S0=b,K0S1=c,K1S1=d,complete=ok,knowledge_marginal=(b+d-a-c)/2 if ok else None,skill_marginal=(c+d-a-b)/2 if ok else None,interaction=d-b-c+a if ok else None,interpretation='descriptive; SELECT timing missing when not observed'))
 rr=[r for r in F if r['metric']==metric and r['task_id'] in TASKS and r['complete']]
 F.append(dict(task_id='mean_of_matched_tasks',metric=metric,complete=len(rr)==11,matched_tasks=len(rr),**{k:statistics.mean(r[k] for r in rr) if rr else None for k in ['knowledge_marginal','skill_marginal','interaction']}))
csvout(R/'summary/FACTORIAL_EFFECTS.csv',F)
conditions=[]
for i,c in enumerate(COND):
 rs=[r for r in T if r['condition']==c];cs=[r for r in C if r['condition']==c]
 row=dict(condition=c,accepted=sum(r['accepted'] for r in rs),tasks=11,acceptance_rate=sum(r['accepted'] for r in rs)/11,
  comparable_violation_mean=None,comparable_violation_median=None,violation_scope='per-task only; incomplete protocols remain unknown',
  input_tokens=sum(r['input_tokens'] for r in cs if finite(r.get('input_tokens'))),cached_input_tokens=sum(r['cached_input_tokens'] for r in cs if finite(r.get('cached_input_tokens'))),
  output_tokens=sum(r['output_tokens'] for r in cs if finite(r.get('output_tokens'))),token_cells_observed=sum(finite(r.get('total_tokens')) for r in cs))
 for k in ['candidate_count','research_action_count','evidence_count','total_core_calls','total_tokens','mathematical_cost','physics_cost','wall_clock_time','completed_mathematical_evidence','knowledge_reads','skill_reads']:
  vals=[r[k] for r in rs if finite(r.get(k))];row[k+'_sum']=sum(vals) if vals else None;row[k+'_median']=statistics.median(vals) if vals else None;row[k+'_observed_tasks']=len(vals)
 conditions.append(row)
csvout(R/'summary/CONDITION_SUMMARY.csv',conditions)

# 1: Complete endpoint matrix; unaccepted includes censored/user-terminated cells.
matrix=np.array([[int(INDEX[t,c]['accepted']) for c in COND] for t in TASKS]);fig,ax=plt.subplots(figsize=(6.6,6.0));ax.imshow(matrix,cmap=ListedColormap(['#edf0f4','#329669']),vmin=0,vmax=1,aspect='auto')
ax.set_xticks(range(4),LABEL);ax.set_yticks(range(11),TASKS);ax.tick_params(length=0)
for j in range(11):
 for i in range(4):ax.text(i,j,'PASS' if matrix[j,i] else '—',ha='center',va='center',color='white' if matrix[j,i] else '#68717d',fontsize=10)
ax.set_title('Formal task acceptance and SELECT',pad=17);ax.set_xlabel('3/11                6/11                6/11                11/11',labelpad=12)
fig.text(.5,.015,'Recorded final endpoints; — = no accepted SELECT, including time termination.',ha='center',fontsize=8)
save(fig,'figure_01_acceptance_matrix',T,'All 44 native endpoints. No accepted SELECT is not an impossibility result.')

# 2: Exact matched descriptive contrasts, with all task transitions visible.
ar=[r for r in F if r['metric']=='accepted' and r['task_id'] in TASKS];fig,axes=plt.subplots(1,3,figsize=(12,4.4),gridspec_kw={'width_ratios':[1,1.2,1.2]})
axes[0].bar(LABEL,[r['acceptance_rate']*100 for r in conditions],color=COLORS);axes[0].set_ylabel('Accepted tasks (%)');axes[0].set_ylim(0,112);axes[0].tick_params(axis='x',rotation=25);axes[0].set_title('Observed endpoints')
for j,r in enumerate(conditions):axes[0].text(j,r['acceptance_rate']*100+2,f'{r["accepted"]}/11',ha='center')
for ax,k,title in [(axes[1],'knowledge_marginal','Knowledge marginal'),(axes[2],'skill_marginal','Skill marginal')]:
 vals=[r[k] for r in ar];ax.barh(TASKS,vals,color='#287ca4' if k.startswith('knowledge') else '#d38a26');ax.axvline(0,color='#89909a',lw=.8);ax.set_xlim(-1.05,1.05);ax.invert_yaxis();ax.set_title(title);ax.set_xlabel('Paired acceptance contrast')
fig.suptitle('Descriptive 2 × 2 contrasts: K +36.4 pp; S +36.4 pp; interaction +18.2 pp',fontsize=12);fig.tight_layout(rect=(0,0,1,.92))
save(fig,'figure_02_factorial_effects',ar,'Task-paired differences, no significance or resource-isolated causal claim.')

# 3: Transparent observed stages rather than a synthetic research-quality score.
stages=[('Candidate present',lambda r:r['candidate_count']>0),('Math computation complete',lambda r:r['completed_mathematical_evidence']>0),('Valid complete physical evidence',lambda r:r['valid_complete_physical_evidence']>0),('Formal accepted SELECT',lambda r:r['accepted'])]
stage_rows=[dict(condition=c,stage=n,tasks=sum(bool(fn(r)) for r in T if r['condition']==c)) for c in COND for n,fn in stages]
fig,ax=plt.subplots(figsize=(9.8,4.6));x=np.arange(4)
for i,c in enumerate(COND):ax.bar(x+(i-1.5)*.18,[r['tasks'] for r in stage_rows if r['condition']==c],width=.17,color=COLORS[i],label=LABEL[i])
ax.set_xticks(x,[s[0].replace(' ','\n',1) for s in stages]);ax.set_ylim(0,12);ax.set_ylabel('Tasks with observed stage (of 11)');ax.set_title('Observed research stages');ax.legend(ncol=4,loc='upper center');fig.tight_layout()
save(fig,'figure_03_research_progress',stage_rows,'Stages are independently observed, not ordinal scores or useful-decision ratings.')

# 4: Resource/evidence distribution; errors separate from scientific failures.
cats=['mathematical_analysis','structure_generation','physical_evaluation','independent_physical_replay','invalid_or_interrupted_interface','diagnosis_and_evidence_read']
dist=[dict(condition=c,category=k,count=sum(a['condition']==c and (a['operation']=='physical_replay' and a['transport_status']=='completed' if k=='independent_physical_replay' else a['category']==k) for a in A)) for c in COND for k in cats]
fig,ax=plt.subplots(figsize=(11,4.6));x=np.arange(len(cats))
for i,c in enumerate(COND):ax.bar(x+(i-1.5)*.18,[r['count'] for r in dist if r['condition']==c],width=.17,color=COLORS[i],label=LABEL[i])
ax.set_yscale('symlog',linthresh=1);ax.set_xticks(x,[s.replace('_','\n') for s in cats],fontsize=9);ax.set_ylabel('Recorded bridge operations (symlog)');ax.set_title('Actual operations and interface interruptions');ax.legend(ncol=4);fig.tight_layout()
save(fig,'figure_04_action_evidence',dist,'Replay operations are a subset of physical evaluations, not an extra disjoint total or an assumed confirmation requirement. Operation count is not useful-science count.')

# 5: Actual cost and acceptance, matched task lines.
fig,axes=plt.subplots(1,2,figsize=(11,4.8));costdata=[]
for i,c in enumerate(COND):
 for t in TASKS:
  r=INDEX[t,c];axes[0].scatter(r['mathematical_cost'],r['physics_cost'],c=COLORS[i],marker='o' if r['accepted'] else 'x',s=42,alpha=.85)
  costdata.append({k:r[k] for k in ['task_id','condition','accepted','mathematical_cost','physics_cost','total_tokens']})
 axes[0].scatter([],[],color=COLORS[i],label=LABEL[i])
for t in TASKS:
 axes[1].plot(range(4),[INDEX[t,c]['physics_cost'] for c in COND],lw=.7,color='#a5aebb',alpha=.6)
for i,c in enumerate(COND):axes[1].scatter([i]*11,[INDEX[t,c]['physics_cost'] for t in TASKS],s=24,color=COLORS[i],alpha=.8)
axes[0].set(xlabel='Charged mathematical evaluations',ylabel='Charged physical launches',title='All endpoints: ○ accepted; × not selected');axes[0].legend(fontsize=8)
axes[1].set_xticks(range(4),LABEL);axes[1].set(ylabel='Charged physical launches',title='Matched tasks retain heterogeneous costs');fig.tight_layout()
save(fig,'figure_05_progress_cost',costdata,'Shared ledger physical charges; failed or incomplete launches remain in costs. No equal-limit efficiency claim.')

# 6: Three actual full reads and their explicit assessment/action links.
pathrows=resourcechains;fig,ax=plt.subplots(figsize=(12.4,5.8));ax.set_axis_off()
texts=[('T02 / K+S+','diagnostic-static-dynamic@2','Separate static authority\nfrom dynamic qualification','core-24: inspect equilibrium\ncapabilities; adopted','Later accepted SELECT\nCausal benefit unmeasured'),
 ('T10 / K−S+','skill-parameter-model@4','Isolate solver effort\nfrom physical design','core-30: generate matched\nmax_iterations intervention','No accepted SELECT\nProcedure changed, task did not pass'),
 ('T10 / K+S+','diagnostic-convergence@2','Distinguish optimizer failure\nfrom task infeasibility','core-17: evidence read\ncontext_only; no action change','Later accepted SELECT\nNo declared transfer effect')]
for j,row in enumerate(texts):
 y=.79-j*.30;ax.text(.005,y+.08,row[0],fontsize=10,fontweight='bold',transform=ax.transAxes)
 for i,txt in enumerate(row[1:]):
  x=.005+i*.25;box=FancyBboxPatch((x,y-.075),.225,.14,boxstyle='round,pad=.009',facecolor='#edf3f7',edgecolor='#b9c9d4',transform=ax.transAxes);ax.add_patch(box);ax.text(x+.1125,y-.005,txt,ha='center',va='center',fontsize=8.2,transform=ax.transAxes)
  if i<3:ax.annotate('',xy=(x+.247,y-.005),xytext=(x+.226,y-.005),arrowprops={'arrowstyle':'->','color':'#6b7e90'},xycoords=ax.transAxes)
ax.set_title('Recorded resource reads and declared action links',pad=15);fig.text(.5,.015,'Arrows show recorded links or chronology. They do not identify a causal effect on acceptance.',ha='center',fontsize=9)
save(fig,'figure_06_resource_transfer',pathrows,'All three successful resource body reads, including a neutral disposition and an unaccepted endpoint.')

# 7: Six selected tasks and their exact matched endpoint/cost comparisons.
sel=load(R/'selected_cases/SELECTED_TRACE_MANIFEST.json')['selected_tasks'];case_data=[];fig,axes=plt.subplots(2,3,figsize=(11,7.4))
for ax,t in zip(axes.flat,sel):
 rs=[INDEX[t,c] for c in COND];vals=[r['physics_cost'] for r in rs];bars=ax.bar(LABEL,vals,color=COLORS)
 for b,r in zip(bars,rs):ax.text(b.get_x()+b.get_width()/2,b.get_height()+max(vals)*.035,'PASS' if r['accepted'] else '—',ha='center',fontsize=8)
 ax.set_title(t);ax.set_ylabel('Physical charges');ax.set_ylim(0,max(vals)*1.26+1);case_data.extend(rs)
fig.suptitle('Selected tasks retain all four condition traces',fontsize=13);fig.tight_layout(rect=(0,0,1,.95))
save(fig,'figure_07_case_studies',case_data,'Selected for diagnostic value, including empty retrievals and atypical comparisons, not all positive transfer examples.')

# S1: Per-task physical observation histories, ordered by recorded Core call.
fig,axes=plt.subplots(3,4,figsize=(13,9.4));evolution=[]
for ax,t in zip(axes.flat,TASKS):
 for i,c in enumerate(COND):
  rs=sorted([e for e in EV if e['task_id']==t and e['condition']==c and e['valid_complete'] and finite(e.get('normalized_violation')) and e.get('core_call_index')],key=lambda e:e['core_call_index'])
  if rs:ax.plot([e['core_call_index'] for e in rs],[e['normalized_violation'] for e in rs],'.-',lw=.7,ms=3,color=COLORS[i],label=LABEL[i]);evolution.extend(rs)
 ax.set_title(t,fontsize=10);ax.set_yscale('symlog',linthresh=.01);ax.set_xlabel('Recorded Core call',fontsize=8);ax.tick_params(labelsize=7)
axes.flat[-1].axis('off');axes.flat[-1].text(.05,.85,'Each point: one complete physical\nevaluation, possibly one task condition.\nDifferent structures/cases are not pooled\ninto a common-candidate certificate.\nPartial/invalid runs have no gap value.',va='top',fontsize=9)
handles,labels=axes.flat[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=4);fig.suptitle('Observed candidate evaluation histories',fontsize=13);fig.tight_layout(rect=(0,.04,1,.96))
save(fig,'supplement_01_candidate_evolution',evolution,'Violation definition and validity are recorded per evidence artifact. No missing or partial point is assigned zero.')

# S2: Availability versus actual reads.
fig,axes=plt.subplots(1,2,figsize=(10.5,5.7))
for ax,field,title in [(axes[0],'resource_manifest_entries','Authorized catalog entries'),(axes[1],None,'Successful full resource reads')]:
 v=np.array([[INDEX[t,c][field] if field else INDEX[t,c]['knowledge_reads']+INDEX[t,c]['skill_reads'] for c in COND] for t in TASKS]);im=ax.imshow(v,cmap='Blues',aspect='auto');ax.set_xticks(range(4),LABEL);ax.set_yticks(range(11),TASKS);ax.set_title(title)
 for y in range(11):
  for x in range(4):ax.text(x,y,str(v[y,x]),ha='center',va='center',color='white' if v[y,x]>v.max()*.65 and v.max() else '#253144',fontsize=8)
 fig.colorbar(im,ax=ax,shrink=.6)
fig.tight_layout();save(fig,'supplement_02_resource_access',T,'Resource availability is distinct from retrieval, reading, adoption, and beneficial transfer.')

# S3: Cached versus uncached input, output, and operations.
fig,axes=plt.subplots(1,2,figsize=(10.6,4.6));x=np.arange(4)
fresh=np.array([r['input_tokens']-r['cached_input_tokens'] for r in conditions]);cached=np.array([r['cached_input_tokens'] for r in conditions]);output=np.array([r['output_tokens'] for r in conditions])
axes[0].bar(x,cached/1e6,color='#bdcbd7',label='Cached input');axes[0].bar(x,fresh/1e6,bottom=cached/1e6,color='#287ca4',label='Uncached input');axes[0].bar(x,output/1e6,bottom=(cached+fresh)/1e6,color='#d38a26',label='Output');axes[0].set_xticks(x,LABEL);axes[0].set_ylabel('Recorded tokens (millions)');axes[0].legend(fontsize=8);axes[0].set_title('Deduplicated completed-turn counters')
axes[1].bar(LABEL,[r['total_core_calls_sum'] for r in conditions],color=COLORS);axes[1].set_ylabel('Bridge operations');axes[1].set_title('All recorded Core bridge calls');fig.tight_layout()
save(fig,'supplement_03_token_tool_usage',conditions,'Input includes cached tokens; provider request counts and missing interrupted usage remain unknown.')

# S4: Decision timelines for all selected matched cells.
fig,axes=plt.subplots(2,3,figsize=(12,7));timeline=[];catcolor={'structure_generation':'#287ca4','mathematical_analysis':'#8c6bb1','physical_evaluation':'#d38a26','validation_and_stopping':'#329669'}
for ax,t in zip(axes.flat,sel):
 for y,c in enumerate(COND):
  aa=[a for a in A if a['task_id']==t and a['condition']==c and a['category'] in catcolor]
  for a in aa:
   n=int(a['request_id'].rsplit('-',1)[-1]);ax.scatter(n,y,color=catcolor[a['category']],s=9,marker='|');timeline.append(a)
 ax.set_title(t);ax.set_yticks(range(4),LABEL,fontsize=8);ax.set_xlabel('Core request index');ax.invert_yaxis()
fig.suptitle('Recorded decisions and actions across matched conditions');fig.tight_layout(rect=(0,0,1,.94));save(fig,'supplement_04_decision_timelines',timeline,'Colors: structure blue, mathematics purple, physics amber, closeout green. No useful-decision score is inferred.')

# S5: Conditional resource association transitions, including negative/neutral.
trans=[]
for t in TASKS:
 a,b,c,d=[int(INDEX[t,x]['accepted']) for x in COND];trans.append(dict(task_id=t,knowledge_at_S0=b-a,knowledge_at_S1=d-c,skill_at_K0=c-a,skill_at_K1=d-b))
fig,ax=plt.subplots(figsize=(8.8,5.5));arr=np.array([[r[k] for k in ['knowledge_at_S0','knowledge_at_S1','skill_at_K0','skill_at_K1']] for r in trans]);ax.imshow(arr,cmap=ListedColormap(['#d88a7c','#eff1f4','#329669']),vmin=-1,vmax=1,aspect='auto');ax.set_yticks(range(11),TASKS);ax.set_xticks(range(4),['K effect at S−','K effect at S+','S effect at K−','S effect at K+'])
for y in range(11):
 for x in range(4):ax.text(x,y,f'{arr[y,x]:+d}',ha='center',va='center',color='white' if arr[y,x] else '#68717d')
ax.set_title('Positive, neutral and negative endpoint transitions');fig.tight_layout();save(fig,'supplement_05_transfer_contrasts',trans,'Endpoint transitions are descriptive associations. A negative transition alone is not a proven negative-transfer mechanism.')
dump(FIG/'FIGURE_MANIFEST.json',FIGURES)
print(json.dumps({'figures':len(FIGURES),'math_calls':len(mathrows),'resource_assessments':len(resourcechains),'resource_reads':sum(r['read_returned_body'] for r in RA)},ensure_ascii=True))

# Selected case reports are evidence locators and restrained interpretations.
case_notes={
 'T03':('Knowledge 条件对照：快速到达与稳定保持','通过模式 0/1/0/1。K+S− 的 core-295 指出数学预测已满足模型阈值，随后物理结果 9f9958f9… 获得验收；core-299 区分数学结果、物理验收和冻结确认要求。该单元没有 experience_retrieve 记录，故它支持 Knowledge 开关与结果的对应关系，不能作为某条 Knowledge 被读取并改变机制的实例。'),
 'T05':('Knowledge 可用性与空检索对照','通过模式 0/1/1/1。K+S− 的 core-8、core-9 先按任务和结构检索，再调整到 position_tool_axis 标签，两次均未取得资源正文，之后继续实际生成与计算。该案例保留了未奏效的检索，不把资源可用性当成成功迁移。'),
 'T01':('Skill 条件对照：同结构多工况验证','通过模式 0/0/1/1。K−S+ 的 core-897 正式选择同一物理结构 91a964c0… 上的 central_high、negative_low、positive_high 三个完整通过结果。core-895 记录 central 数学预测的保持误差 0.00999836 m 和腱速上限附近的诊断结果，随后才执行物理验证。本单元没有单独 Skill 正文读取，结构化验证过程可复现，其资源因果归因仍未知。'),
 'T04':('Skill 条件对照：跟踪控制与完整回放','通过模式 0/0/1/1。K−S+ 的 core-139 注册 295 节点控制源，core-141 根据独立回放 6efc7adf… 正式选择。回放记录 RMSE 0.002306789 m、最大误差 0.003424919 m、周期漂移 0.000402252 m。研究轨迹显示了方法构造、计算与物理验收的顺序，但没有 Skill 正文读取记录。K+S− 的终态是时间终止，不能写成已穷尽所有可行科学方法。'),
 'T09':('非单调对照：基线与联合条件通过','通过模式 1/0/0/1。K+S+ 的 core-192 将控制源绑定到当前候选，core-206 根据完整回放 2f78173b… 正式选择：按压位移 0.00206324 m、有效保持 0.5 s、最大力误差 0.003039 N、最大腱速 0.0170621 m/s。两个单资源条件未通过并不建立资源有害的机制；本任务不支持“每个任务均有单调增益”的说法。'),
 'PHS2D':('联合条件特有通过：完整十工况物理结果','通过模式 0/0/0/1。core-407 生成 F8D，明确改变对称弯曲黏性 0.00010→0.00011 N·m²·s，之后完整十工况结果 73ae20f6… 被原生验收并在 core-861 正式选择。该案例显示联合条件的特有终态和可追溯机制干预；没有单独 Knowledge/Skill 正文检索链，因此不能把终态差异本身写成已证实的双资源协同机制。')}
lines=['# 代表性科研 Trace','', '六项案例各保留四条件原始决策与 Core 回执压缩日志，共 24 条详细轨迹。完整 44 单元均在总表和 episode_manifests 中，选择案例不改变总样本。','', '“未正式选择”包括完整未通过、部分/无效计算和时间终止，须按原生回执区分。下列过程引用来自模型公开决策；数值验收由原生证据独立核对。','']
caseindex=[]
for t in sel:
 title,note=case_notes[t];lines.extend([f'## {t}：{title}','',note,'','|条件|验收及 SELECT|候选数|数学计数|物理计费次数|','|---|---|---:|---:|---:|'])
 for c,label in zip(COND,LABEL):
  r=INDEX[t,c];lines.append(f'|{label}|{"通过" if r["accepted"] else "未选择"}|{r["candidate_count"]}|{r["mathematical_cost"]}|{r["physics_cost"]}|')
 lines.extend(['','初始公开任务、科学模型、约束和初态身份详见各条件清单。每次 generate 的参数、假设与返回引用保存在 CANDIDATE_INTERVENTIONS.csv。',''])
 for c in COND:
  m=M[t,c];lines.append(f'- [{c} 清单](../episode_manifests/{t}/{c}.json)，原始目录 `{m["source_episode"]}`，最终证据 `{aid(m["final_native_state"].get("selected")) or aid(m["final_native_state"].get("final_disposition"))}`。')
 lines.append('');caseindex.append(dict(task_id=t,title=title,narrative=note,conditions=[INDEX[t,c] for c in COND]))
lines.extend(['## 有实际正文读取的补充链','', 'T02/K+S+ 的 core-23 精确读取 diagnostic-static-dynamic@2，core-24 自述采用静态能力与动态验收分离的诊断，随后查询 equilibrium 能力。这支持一条明确的经验到诊断操作链，尚未独立量化其对最终通过的贡献。','', 'T10/K−S+ 的 core-29 精确读取 skill-parameter-model@4，core-30 明确引用并生成只改变 max_iterations 的匹配干预，后续仍未正式通过。这是 Skill 改变操作组织的可追溯实例，也避免把程序变化与任务成功混为一谈。','', 'T10/K+S+ 的 diagnostic-convergence@2 被明确评为 context_only，模型自述未改变假设或动作。这条中性读取与两次空查询及一次未返回正文的读取都保留在资源总表中。','', 'T07 和 T10 的 K+S− 通过而两个无 Knowledge 条件未通过，但它们同样没有独立正文检索记录，因此列为条件层面的 Knowledge 候选而非已证实的经验迁移。T06 四条件都通过，其成本对照见总表与图 5。'])
write(R/'selected_cases/CASE_STUDIES.md','\n'.join(lines));dump(R/'selected_cases/CASE_INTERPRETATIONS.json',caseindex)

matrixtext=['|任务|K−S−|K+S−|K−S+|K+S+|','|---|---|---|---|---|']
for t in TASKS:matrixtext.append('|'+t+'|'+'|'.join('通过' if INDEX[t,c]['accepted'] else '未选择' for c in COND)+'|')
conditiontext=['|条件|通过|比例|','|---|---:|---:|']+[f'|{LABEL[i]}|{r["accepted"]}/11|{r["acceptance_rate"]:.1%}|' for i,r in enumerate(conditions)]
figuretext=['|文件|内容|','|---|---|']+[f'|[{f["name"]}]({f["png"]})|{f["caption"]}|' for f in FIGURES]
audit=load(R/'publication/DATASET_AUDIT.json');nbytes=audit['source_total_bytes'];gib=nbytes/(1024**3)
limitation='本报告比较已记录的最终工作流结果。各单元的最终上下文和实际资源上限存在差异，物理预算原始值与最终值均逐单元列出；时间终止和接口中断也影响成本与可达阶段。因此这里的因子对比是描述统计，不能解释为严格固定资源、随机重复条件下的独立因果效应。'
write(R/'FINAL_RESULTS_REPORT.md',f'''# 11 项任务的 Knowledge × Skill 最终结果

原生记录重建出 44 个已结束研究单元，26 个同时取得原任务验收与正式 SELECT。K+S+ 在 11 项任务中全部通过。无科研重跑，未修改原始单元。

{chr(10).join(conditiontext)}

{chr(10).join(matrixtext)}

Knowledge 的描述性边际差为 +36.4 个百分点，Skill 为 +36.4 个百分点，差中差交互项为 +18.2 个百分点。计算采用 11 个任务的配对二元终态，逐任务值在 summary/FACTORIAL_EFFECTS.csv。没有据此进行显著性、普遍协同或无限推广的判断。

Knowledge 条件的独特通过模式出现在 T03、T07、T10；Skill 条件的独特通过模式出现在 T01、T04。PHS2D 仅联合条件通过。T02 的基线也通过，T08 的两个单资源条件均通过，因此 T08 不是 Skill 独有贡献案例。T06 四条件通过。T09 的 1/0/0/1 模式和 T02 的 1/0/1/1 模式提醒我们，资源开启与结果不是逐任务单调对应。

## Trace 对论文叙事的支持范围

Knowledge 资源正文确实包含把物理能力、数值收敛和任务验收分开分析的科研经验。T02 的精确读取与后续 equilibrium 能力查询形成明确的诊断链。Skill 正文把匹配参数干预组织成可执行步骤，T10 的精确读取、引用和 max_iterations 单因素构造记录了这种程序变化。它们分别支持“经验供给”和“策略组织”的具体过程描述，但没有单独识别对最终验收概率的因果贡献。

44 单元共有 {audit['actual_resource_accesses']} 次可选 Knowledge/Skill 检索接口操作，其中 {audit['actual_resource_body_reads']} 次实际取得该接口的正文。实际交付的上下文及其显式证据读取另列于 CONTEXT_EXPOSURE.csv 和 CONTEXT_READS.csv，并保存原始交付包，不能将可选检索数误当成全部上下文暴露量。大多数优先候选没有独立 Knowledge/Skill 检索链，所以不能用它们的通过结果补写未发生的特定资源采纳。资源总表区分空搜索、读取、adopted、context_only、显式动作链接和未知因果作用。

“Knowledge 提供物理与科研经验，Skill 提供可执行研究策略，联合条件在本组 11 项任务全部通过”可以作为资源设计与实测终态的叙述。把它写成“Trace 已证明每项任务由双资源协同而成功”则超出证据。

{limitation}

## 过程、成本和可比性

完整候选、数学完成状态、物理证据和实际调用分别统计，操作数不作为有用决策数。物理成本使用原生 shared ledger 的 backend_solves 实际计费，独立保留启动计数，防止把中断或恢复的计数差异混算。数学计数、完整数学证据、物理积分步和保守数值计费也分列。

Token 来自已记录 turn.completed 的去重计数，input 包括 cached input，reasoning 不再次相加。中断而缺失的用量与 provider 请求次数仍未知。物理积分步仅报告有原生记录的合计及缺失条目数。墙钟时间包含等待，不能解释为纯求解器时间。任务违约值按原生有效性和同一结构的完整必需工况计算，未覆盖工况保留缺失；不混合异质任务的量纲与约束强度。

## 案例、盲评和历史参考

六项主案例为 T03、T05、T01、T04、T09、PHS2D，24 条条件匹配详细轨迹见 selected_cases/CASE_STUDIES.md。T02/T10 的资源读取链、T06 的中性对照和 T07 的条件模式另行保留。实际作用链强度限制已写入每项案例，选择主案例不隐去其余单元。

既有盲评报告没有有效评分，仍为 0/44。本次没有制造评分或将非盲阅读伪装成独立盲评。历史 FULL 参考表独立归档，不作为四条件中的额外重复。

## 交付内容

44 个清单、完整决策和操作摘要、资源及费用表、候选演化、逐任务因子差、全部验收与最终回执，以及 7 张主图和 5 张补充图。每张图同时提供 PNG、矢量 PDF 与独立 CSV 源数据。

{chr(10).join(figuretext)}

原始 44 单元目录共索引 {audit['source_file_count']:,} 个文件，合计 {gib:.2f} GiB。原始大型 Store 和逐步数值文件留在本地原目录，完整文件索引为 raw_archive/ORIGINAL_FILE_MANIFEST.csv.gz。Git 交付压缩的精选原始 Trace、全部紧凑统计、证据元数据、配置、图和复现脚本，不宣称把所有大型原始数组上传。实际提交文件及 SHA256 见 raw_archive/DELIVERY_FILES.csv。
''')
write(R/'LIMITATIONS.md',f'''# 解释范围和缺失数据

{limitation}

- 只有 11 项异质任务，每格一个工作流轨迹，没有可支持普遍显著性结论的独立重复。
- 资源可用、搜索、取得正文、模型自述采纳、实际操作链接与改善验收是不同证据层级。只有三次成功正文读取，缺失链不能由最终结果补齐。
- T04/K1S0 是时间终止，不能当作物理额度实际耗尽或任务不可行。其余未选择结果也不能一律称为科学失败。
- 未完成物理轨迹不产生完整任务违约值。零上限失败若无可用归一化尺度，其违约值仍未知。归一化违约用于同任务排序，不代替原生布尔验收。
- 墙钟时间含资源竞争和等待；原生 numerical_s 可能包含退出观测的保守上界，纯求解时长未知。
- Token 去重覆盖现存完整回合记录，未记录用量不估算。cached input 与 fresh input 分开，token 总数不是账单费用。
- 实际有效盲评分为 0/44；当前过程解释属于非盲 Trace 审阅。
- Git 内提供紧凑数据和精选完整日志。大型原始 Store 保留本地，仅有索引，不能将 Git 克隆称为全部原始数值数组的自包含副本。
- 历史 FULL 仅作参考，其模型版本、阶段和成本不与本次端点直接合并。
''')
write(R/'EXPERIMENT_PROTOCOL.md',f'''# 已完成实验的分析协议

样本：T01–T10 与 PHS2D，每项 K0S0、K1S0、K0S1、K1S1，共 44 单元。正式目录由 FORMAL_COHORT_MANIFEST.json 指定，旧的配置无效单元单独归档，费用在 summary/SETUP_INVALID_COSTS.csv，不作为消融科学失败。

研究决策模型记录为 gpt-5.6-sol，reasoning effort high；Main 和 Reporter 关闭。每个单元的初态身份、科学 specification、任务协议、预算、实现提交、Core 回执和终态均保留在 episode_manifests。分析只读 SQLite 和原始日志，禁止调用研究执行入口，禁止重置或重跑。

资源允许角色：K0S0 无，K1S0 knowledge，K0S1 skill，K1S1 二者。可用目录不是正文读取证据。RESOURCE_AVAILABILITY 是可用性目录，RESOURCE_TO_ACTION 是实际接口操作，RESOURCE_ACTION_CHAINS 保存原始自述评估和后续调用定位。科学结论由本单元原生物理验收及 SELECT 核验。

正式通过须 native selected 存在，且 success_gate.observed_task_pass 或已完成 research_plan 原生返回 selected=true 与 task_passed=true。兼容既有六个不同 gate 结构的旧回执，不能只查一个 gate 字段而漏计。研究 stopped、CLI ended、物理完成、原任务通过和 SELECT 分别记录。

{limitation}

接受率边际差：K = ((K1S0 + K1S1) − (K0S0 + K0S1))/2；S = ((K0S1 + K1S1) − (K0S0 + K1S0))/2。交互项 K1S1 − K0S1 − K1S0 + K0S0。对每项任务先计算，再取 11 项均值。全矩阵和负/中性转变均保留。

物理违约使用原生记录的有效完整评估。offline_frozen_task_v1 先核查原生组件和来源绑定，再由 constraint_margins 计算 max(0, −margin/abs(limit))，满足零边界记 0，违反零边界且无尺度记未知。其他协议使用归档 Core 的纯 task_gap 读取逻辑。多工况汇总要求同一物理结构和所有 required 工况；T08/PHS2D 用证据内部完整协议，不把某个局部轨迹当作完整通过。状态、单位、边界和各组件原值完整保留。

费用取实际原生 shared ledger；物理启动计数另存，避免误当计费。数学完整性取 Core scientific_computation.complete。token 为现存已完成回合的去重记录，输入包含缓存，思考 token 不重复加总，不估算 provider 请求或缺失用量。

复现：先在本地完整原始目录中运行 publication/build_dataset.py，再依次运行 publication/audit_contexts.py、publication/analyze_and_plot.py 和 publication/verify_delivery.py。只重绘图可运行 publication/analyze_and_plot.py：没有全量原始日志时自动读取已交付的数学、干预和资源链紧凑表。只读全量提取需要原本地数据；当前 Core 阅读器源码另存 source_snapshot/FINAL_CORE_READER_SOURCE_f252213.zip。运行环境见 publication/ANALYSIS_ENVIRONMENT.json。
''')
write(R/'README.md','''# 11-task Knowledge × Skill ablation archive

44 个原生终态，26 个验收且正式 SELECT。四条件通过数：3/11、6/11、6/11、11/11。

- [最终报告](FINAL_RESULTS_REPORT.md)：完整矩阵、描述性对比和解释范围。
- [分析协议](EXPERIMENT_PROTOCOL.md)与[限制](LIMITATIONS.md)。
- [六项案例及 24 条匹配 Trace](selected_cases/CASE_STUDIES.md)。
- [44 单元结果](summary/TASK_RESULTS.csv)、[资源动作链](summary/RESOURCE_ACTION_CHAINS.csv)、[费用](summary/RESOURCE_COSTS.csv)。
- [图表清单](figures/FIGURE_MANIFEST.json)：7 主图与 5 补充图，每图有 PNG、PDF、CSV。
- [审计](AUDIT_REPORT.md)与[完整本地原始文件索引](raw_archive/ORIGINAL_FILE_MANIFEST.csv.gz)。

所有终态均报告。因子对比描述本组已记录结果，不能替代严格资源一致的因果估计。正文读取、模型自述采纳与验收贡献分别记录。没有新增研究实验。

大型原始 Store 和数值数组留在原本地目录；Git 克隆包含紧凑数据、配置、精选原始日志与证据元数据，不包含全部大型原始数组。
''')
dump(R/'publication/ANALYSIS_ENVIRONMENT.json',dict(python=sys.version,matplotlib=matplotlib.__version__,numpy=np.__version__,analysis_timestamp=datetime.now(timezone.utc).isoformat(),new_scientific_executions=0))
