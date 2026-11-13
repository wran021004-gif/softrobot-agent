"""Independent scientific charts from archived numeric data only."""
from pathlib import Path
import json,csv,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
O=Path(__file__).resolve().parent
def rd(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def csvread(p):return list(csv.DictReader(Path(p).open(encoding='utf-8-sig')))
def csvwrite(name,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    p=O/'FIGURE_DATA'/f'{name}.csv'
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
    return str(p)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','axes.labelcolor':'#303C3E','text.color':'#303C3E','axes.edgecolor':'#536166','savefig.facecolor':'white'})
C=['#E5F5F9','#99D8C9','#2CA25F'];GRAY='#536166'
tasks=rd(O/'SOURCE_DATA/FULL_TASKS.json');cases=rd(O/'SOURCE_DATA/FULL_CASES.json');manifest=[]
def finish(name,fig,rows,caption,source):
    data=csvwrite(name,rows);fig.tight_layout()
    for ext in ['png','svg']:fig.savefig(O/'FIGURES'/f'{name}.{ext}',dpi=300,bbox_inches='tight')
    plt.close(fig);manifest.append(dict(name=name,data_csv=data,png=str(O/'FIGURES'/f'{name}.png'),svg=str(O/'FIGURES'/f'{name}.svg'),caption=caption,source=source))
def axnew(w=6.4,h=3.6):return plt.subplots(figsize=(w,h))
def grid(ax):ax.grid(axis='y',color='#DDE3E3',linewidth=.55);ax.set_axisbelow(True)

# Protocol capability coverage, not empirical scores.
cols=['Reach / hold','Timed path','Directed axis','Contact','Passive design','Shared cases','Disturbance']
coverage=[[0],[0,6],[0],[1],[2],[1,2],[0,2,5],[4],[3],[0,6],[4,5]]
A=np.zeros((11,7));rows=[]
for i,t in enumerate(tasks):
    for j,col in enumerate(cols):A[i,j]=int(j in coverage[i]);rows.append(dict(task_id=t['task_id'],capability=col,protocol_contains=int(A[i,j]),source_reference=json.dumps(t['protocol_source'],ensure_ascii=False)))
fig,ax=axnew(8.0,4.7);ax.imshow(A,cmap=matplotlib.colors.ListedColormap(['white',C[1]]),vmin=0,vmax=1,aspect='auto')
ax.set_xticks(range(7),cols,rotation=30,ha='right');ax.set_yticks(range(11),[t['task_id'] for t in tasks]);ax.tick_params(length=0)
for i in range(11):
    for j in range(7):
        if A[i,j]:ax.text(j,i,'●',ha='center',va='center',color=C[2],fontsize=10)
ax.set_title('Full Study task portfolio',loc='left',pad=12)
finish('fig_portfolio',fig,rows,'Protocol-defined capability coverage of eleven Full Study cases; filled cells identify task requirements rather than independent performance scores.',str(O/'SOURCE_DATA/PROTOCOLS.json'))

# Evidence-linked decision graph, not a candidate metric convergence curve.
decision=[
 ('F0','Slack tendons','0 N in all four tendons'),
 ('F1','Diagnose motion coupling','Local Tip/point = 1.7992'),
 ('F2','Taper route / compliance','Local ratio = 0.1518'),
 ('F2–F4','Reject finite-load settling','Tail drift 0.693→0.062 mm'),
 ('F3 / F5','Check solid crossings','Route intersects cell / connector'),
 ('F5 / F6','Seven segments + guides','Distal Tip still 6.390 mm'),
 ('F7','Screen six signed cases','s7− Tip 5.161 mm > 5 mm'),
 ('F8','Freeze and independently test','10/10 + half-step 10/10')]
fig,ax=axnew(8.2,6.3);ax.set_xlim(0,1);ax.set_ylim(-.02,1.04);ax.axis('off')
positions=[(.02,.79),(.52,.79),(.52,.54),(.02,.54),(.02,.29),(.52,.29),(.52,.04),(.02,.04)]
rows=[]
for i,((cand,title,value),(x,y)) in enumerate(zip(decision,positions)):
    ax.add_patch(FancyBboxPatch((x,y),.45,.18,boxstyle='round,pad=.008,rounding_size=.01',facecolor=C[i%3],edgecolor=GRAY,linewidth=.7))
    ax.text(x+.018,y+.141,cand,weight='bold',fontsize=10,va='center');ax.text(x+.018,y+.092,title,fontsize=9.2,va='center');ax.text(x+.018,y+.035,value,fontsize=8.7,va='center')
    rows.append(dict(order=i+1,candidate=cand,decision=title,observation=value,source_reference=str(O/'KEY_RESEARCH_NODES.csv')+'#PHS-2D'))
    if i:
        px,py=positions[i-1]
        start=(px+.45,py+.09) if x>px else (px,py+.09) if x<px else (px+.225,py)
        end=(x,y+.09) if x>px else (x+.45,y+.09) if x<px else (x+.225,y+.18)
        ax.annotate('',xy=end,xytext=start,arrowprops=dict(arrowstyle='->',color=GRAY,lw=1.1,shrinkA=6,shrinkB=6))
finish('fig_research_decisions',fig,rows,'Selected PHS-2D decisions link local diagnostics, failed finite-load tests and geometry checks to the frozen design. Local and finite-load quantities have different scopes and do not form a convergence curve.',str(O/'KEY_RESEARCH_NODES.csv'))

# Archived trajectory and exact stored reference nodes; no synthetic reference interpolation.
samples=rd(O/'FIGURE_DATA/T04_default_SAMPLES.json')
bankp=O.parent/'five_task_completion_20261113/T04_figure_eight_tracking/T04_RUN_03/NATIVE_REFERENCE_BANK.json'
bank=rd(bankp)['reference_bank'];rows=[]
for a in samples:rows.append(dict(series='recorded trajectory',time_s=a['time_s'],x_m=a['tip_m'][0],y_m=a['tip_m'][1],z_m=a['tip_m'][2],source_reference=str(O/'FIGURE_DATA/T04_default_SAMPLES.json')))
for a in bank:rows.append(dict(series='stored reference node',time_s=a['reference_time_s'],x_m=a['target_position_m'][0],y_m=a['target_position_m'][1],z_m=a['target_position_m'][2],source_reference=str(bankp)))
fig,ax=axnew(5.6,3.8);actual=np.array([a['tip_m'] for a in samples]);target=np.array([a['target_position_m'] for a in bank])
ax.plot(actual[:,1]*1e3,actual[:,2]*1e3,color=C[2],lw=1.7,label='Recorded trajectory (22 s)')
ax.scatter(target[:,1]*1e3,target[:,2]*1e3,facecolors='none',edgecolors=GRAY,s=18,linewidths=.7,label='Stored reference nodes',zorder=3)
ax.set(xlabel='World y (mm)',ylabel='World z (mm)');ax.set_aspect('equal',adjustable='datalim');ax.legend(frameon=False,fontsize=8.4,loc='upper right')
finish('fig_tracking_path',fig,rows,'World y–z projection of the complete 22 s archived trajectory and 89 stored target nodes. Full 3D evaluator RMSE is 0.68785 mm and maximum error is 1.02066 mm; no interpolated target/error curve is introduced.',str(O/'SOURCE_DATA/T04_default_RESULT.json'))

# Dynamic error derived only by arithmetic on saved signals; acceptance remains the full-step evaluator result.
target=rd(O/'SOURCE_DATA/T10_positive_y_TASK.json')['goal']['data']['target_m']
names=['positive_y','negative_y','no_impulse','positive_y_frozen','negative_y_frozen'];labels=['+Y feedback','−Y feedback','No impulse','+Y frozen control','−Y frozen control']
styles=[(C[2],'-','o'),(GRAY,'-','s'),(C[1],'-','^'),(C[2],'--','x'),(GRAY,'--','+')]
for name,signal,unit,limit in [('position','tip_position','mm',10),('speed','tip_velocity','mm/s',20)]:
    fig,ax=axnew(6.6,3.7);rows=[]
    for condition,label,(color,ls,marker) in zip(names,labels,styles):
        sig=next(s for s in rd(O/'FIGURE_DATA'/f'T10_{condition}_SIGNALS.json') if s['spec']['name']==signal)
        v=np.array(sig['values']);v=v-np.array(target) if name=='position' else v;norm=np.linalg.norm(v,axis=1)*1e3;t=sig['times_s']
        ax.plot(t,norm,color=color,linestyle=ls,marker=marker,markevery=7,ms=3,lw=1.4,label=label)
        rows.extend(dict(condition=condition,role='control' if 'frozen' in condition else 'required',time_s=tt,value=float(vv),unit=unit,source_reference=str(O/'FIGURE_DATA'/f'T10_{condition}_SIGNALS.json')) for tt,vv in zip(t,norm))
    ax.axvspan(.5,.55,color=C[0],zorder=-2);ax.axvspan(.9,1,color='#F1F3F3',zorder=-2);ax.axhline(limit,color=GRAY,lw=.9,ls=':')
    shown=[r['value'] for r in rows if r['time_s']>=.35]
    ax.set_xlim(.35,1.0);ax.set_ylim(0,max(max(shown)*1.1,limit*1.12));ax.set(xlabel='Time (s)',ylabel='Tip '+('position error' if name=='position' else 'speed')+f' ({unit})')
    ax.legend(frameon=False,ncol=3,fontsize=7.8,loc='lower left',bbox_to_anchor=(0,1.01));grid(ax)
    finish('fig_impact_'+name,fig,rows,'Archived 10 ms sampled '+name+' signals under one common feedback recipe. Pulse: 0.50–0.55 s; final hold: 0.90–1.00 s. Dotted line denotes the hold bound, applicable to required hold windows. Three required cases pass; both frozen controls fail the complete evaluator. Sampled curves do not replace full-step acceptance.',str(O/'TASK_CASE_RESULTS.csv')+'#T10')

phs=[c for c in cases if c['task_id']=='PHS-2D']
for key,label,scale,bound,typ in [('point_x_abs_m','Force-point displacement (mm)',1e3,10,'lower'),('tip_projected_m','Projected Tip displacement (mm)',1e3,5,'upper'),('ratio','Tip / force-point ratio',1,.3,'upper')]:
    rows=[dict(condition=c['condition_name'],value=c['metrics'][key]*scale,bound=bound,bound_type=typ,unit='1' if scale==1 else 'mm',source_reference=c['source_reference']) for c in phs]
    fig,ax=axnew(7.0,3.4);x=np.arange(len(rows));vals=[r['value'] for r in rows]
    ax.bar(x,vals,color=[C[1] if i%2==0 else C[2] for i in range(len(x))],edgecolor=GRAY,linewidth=.45,width=.7);ax.axhline(bound,color=GRAY,ls='--',lw=1,label=typ+' bound')
    ax.set_xticks(x,[r['condition'].replace('_positive','+').replace('_negative','−') for r in rows],rotation=0);ax.set_ylabel(label);grid(ax);ax.legend(frameon=False,fontsize=8)
    finish('fig_phs_'+key,fig,rows,'Frozen F8 in ten formal conditions. '+label+' is evaluated per condition; dashed line is the original '+typ+' bound. No search-stage values are connected to formal acceptance.',str(O/'TASK_CASE_RESULTS.csv')+'#PHS-2D')

rows=[]
for tid,keys in [('T05',['tool_position','tool_axis_direction']),('T06',['tracking_max_error','tool_axis_direction'])]:
    c=next(c for c in cases if c['task_id']==tid)
    for key in keys:
        value=c['metrics'][key];bound=c['constraint_thresholds'][key]['limit']
        rows.append(dict(task_id=tid,metric=key,value=value,unit=c['constraint_thresholds'][key]['unit'],upper_bound=bound,fraction_of_bound=value/bound,source_reference=c['source_reference']))
fig,ax=axnew(5.8,3.5);x=np.arange(4);ax.bar(x,[r['fraction_of_bound'] for r in rows],color=[C[1],C[2]]*2,edgecolor=GRAY,linewidth=.5)
ax.axhline(1,color=GRAY,ls='--',lw=1);ax.set_xticks(x,['T05 position','T05 axis','T06 position','T06 axis']);ax.set_ylabel('Fraction of original upper bound');ax.set_ylim(0,1.12);grid(ax)
finish('fig_position_axis_constraints',fig,rows,'Position and directed-axis errors divided by their respective original upper bounds. Quantities retain their units and thresholds in the CSV; normalized bars are not a common task score.',str(O/'TASK_CASE_RESULTS.csv')+'#T05,T06')

# Aggregate only disjoint studies within the selected task series; keep PHS half-step separate.
costs=csvread(O/'RESOURCE_COSTS.csv');aggregate=[]
for tid in [f'T{i:02}' for i in range(1,11)]+['PHS-2D']:
    rr=[r for r in costs if r['task_id']==tid and (tid!='PHS-2D' or r['run_id']=='psd2d-core-fresh-20261112')]
    vals=[float(r['integration_steps']) for r in rr if r['integration_steps'] not in ['', 'unavailable']]
    aggregate.append(dict(task_id=tid,math_evaluations=sum(float(r['math_evaluations']) for r in rr),physical_episodes=sum(float(r['physical_episodes']) for r in rr),
        known_integration_steps=sum(vals),steps_complete=all(r['integration_steps'] not in ['','unavailable'] for r in rr),
        run_ids=';'.join(r['run_id'] for r in rr),scope='Selected Full task series; disjoint study rows only; PHS main search+nominal, excluding half-step',source_reference=str(O/'RESOURCE_COSTS.csv')))
for field,ylabel in [('math_evaluations','Charged mathematical evaluations'),('physical_episodes','Recorded physical episodes'),('known_integration_steps','Recorded integration steps')]:
    fig,ax=axnew(7.0,3.5);x=np.arange(11);vals=[r[field] for r in aggregate]
    ax.bar(x,vals,color=C[1],edgecolor=GRAY,linewidth=.5)
    if field=='known_integration_steps':
        for i,r in enumerate(aggregate):
            if not r['steps_complete']:ax.plot(i,vals[i],marker='^',color=GRAY,ms=6)
        ax.text(.01,.97,'▲ incomplete step coverage: recorded lower bound',transform=ax.transAxes,ha='left',va='top',fontsize=8)
        ax.ticklabel_format(axis='y',style='sci',scilimits=(6,6))
    else:
        for i,v in enumerate(vals):ax.text(i,v+max(vals)*.018,str(int(v)),ha='center',va='bottom',fontsize=8)
    ax.set_xticks(x,[r['task_id'] for r in aggregate],rotation=0);ax.set_ylabel(ylabel);ax.set_ylim(0,max(vals)*1.18);grid(ax)
    finish('fig_resource_'+field,fig,aggregate,'Resource use of the selected Full task series, including its failed/preparatory studies. Only disjoint run IDs within a series are summed; superseded batch duplicates and PHS half-step verification are excluded. Math charges, physical episode launches and nested integration steps use different definitions and are shown separately. Incomplete step totals are explicitly lower bounds.',str(O/'RESOURCE_COSTS.csv'))
(O/'FIGURE_DATA/FIGURE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('Independent data charts',len(manifest))
