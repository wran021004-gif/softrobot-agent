"""Eight task-specific quantitative figures, archived evidence only; no model execution."""
import csv,json,math,pathlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=pathlib.Path('D:/softrobot-agent');B=ROOT/'runs/multitask-paper-data-20261118'
ARR=ROOT/'paper_experiments/paper_results_master_20261113/SOURCE_DATA/TASK_TIME_SERIES'
C=dict(navy='#26384B',teal='#527F7B',slate='#70849A',ochre='#B08A59',green='#557663',brick='#A35D55',gray='#929BA4')
plt.rcParams.update({'font.family':'Arial','font.size':8.5,'axes.labelsize':8.5,'axes.titlesize':8.5,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'axes.linewidth':.6,'lines.linewidth':.9,'xtick.major.width':.5,'ytick.major.width':.5,'xtick.major.size':3,'ytick.major.size':3,'svg.fonttype':'none','savefig.facecolor':'white','figure.facecolor':'white'})
CAPTIONS={}
def read(p):return json.loads(p.read_text(encoding='utf8'))
def csvwrite(tid,name,rs):
 p=B/tid/'FIGURE_DATA'/name
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
 return str(p)
def tidy(ax):
 ax.spines[['top','right']].set_visible(False);ax.tick_params(direction='out',pad=2);ax.set_axisbelow(True)
def save(tid,name,fig,caption,source):
 for ax in fig.axes:tidy(ax)
 p=B/tid/'FIGURES_PAPER';p.mkdir(exist_ok=True)
 fig.savefig(p/(name+'.png'),dpi=500);fig.savefig(p/(name+'.svg'));plt.close(fig)
 CAPTIONS[tid]=(name,caption,source)
def final(tid):return read(B/tid/'final_acceptance_extracted.json')
def task(tid):return read(B/tid/'RENDER_INPUTS/default_TASK.json')
def arrays(tid):
 p=ARR/(tid+'_default_FULL_ARRAYS.json');o=read(p)
 return o['task_evidence']['arrays'],str(p),o['source_store']+'#artifacts/'+o['raw_reference']['artifact_id']
def origins(tid):
 r=final(tid)[0]
 return dict(task_id=tid,run_id=r['run_id'],candidate_id=r['candidate_id'],execution_id=r['execution_id'],original_source=r['raw_reference'])
def getcomp(fc,key):return fc['acceptance_components']['evaluator:'+key]

# Two shared-hardware multi-condition tasks. Units remain on separate axes.
for tid,ordered,labels in [('T01',['central_high','negative_low','positive_high'],['Central','Negative','Positive']),('T02',['negative','positive','zero'],['Negative','Positive','Zero'])]:
 fs={r['condition']:r for r in final(tid)};records=[];fig,axs=plt.subplots(1,2,figsize=(7.16,2.48));fig.subplots_adjust(left=.075,right=.985,bottom=.205,top=.80,wspace=.37)
 xs=np.arange(3);pos=[];hold=[];tendon=[]
 for case in ordered:
  fc=fs[case]
  for metric in ['holding_position','holding_speed','geometric_tendon_speed']:
   q=getcomp(fc,metric);records.append(dict(task_id=tid,condition_id=case,run_id=fc['run_id'],candidate_id=fc['candidate_id'],execution_id=fc['execution_id'],metric=metric,value_SI=q['value'],unit=q['unit'],limit_SI=q['limit'],passed=q['passed'],display_multiplier=1000,source=fc['result_reference'],source_pointer='/acceptance/components/evaluator:'+metric))
  pos.append(getcomp(fc,'holding_position')['value']*1000);hold.append(getcomp(fc,'holding_speed')['value']*1000);tendon.append(getcomp(fc,'geometric_tendon_speed')['value']*1000)
 axs[0].bar(xs,pos,color=C['navy'],width=.52,linewidth=0)
 axs[0].axhline(getcomp(fs[ordered[0]],'holding_position')['limit']*1000,color=C['brick'],lw=.8,ls=(0,(3,2)))
 for x,v in zip(xs,pos):axs[0].text(x,v+.25,f'{v:.2f}',ha='center',va='bottom',fontsize=8)
 axs[0].set(xticks=xs,xticklabels=labels,ylabel='Maximum hold error (mm)',ylim=(0,11.7),yticks=[0,5,10],title='(a) Position')
 axs[1].bar(xs-.16,hold,width=.28,color=C['slate'],label='Tip hold speed',linewidth=0)
 axs[1].bar(xs+.16,tendon,width=.28,color=C['teal'],label='Tendon speed',linewidth=0)
 for x in xs:
  axs[1].plot([x-.31,x-.01],[getcomp(fs[ordered[x]],'holding_speed')['limit']*1000]*2,color=C['brick'],ls=(0,(3,2)),lw=.8)
  axs[1].plot([x+.01,x+.31],[getcomp(fs[ordered[x]],'geometric_tendon_speed')['limit']*1000]*2,color=C['brick'],ls=(0,(3,2)),lw=.8)
 axs[1].set(xticks=xs,xticklabels=labels,ylabel='Maximum speed (mm/s)',ylim=(0,35 if tid=='T01' else 29),title='(b) Motion limits')
 hs,ls=axs[1].get_legend_handles_labels();fig.legend(hs,ls,loc='upper right',bbox_to_anchor=(.985,.995),ncol=2,frameon=False,handlelength=1.3,columnspacing=1.1)
 source=csvwrite(tid,tid+'_final_conditions_plotdata.csv',records)
 save(tid,tid+'_final_condition_constraints',fig,f'{tid}: independent original-task acceptance on one shared final structure, with condition-specific controls. Maximum hold error and maximum tip/tendon speeds are shown in separate units. Red dashed segments are the corresponding frozen limits. Conditions are categorical, not an optimization trajectory. Only final original executions are included.',source)

# Fast reach: complete trace; tolerances apply only in the terminal hold window.
tid='T03';a,ap,raw=arrays(tid);t=np.asarray(a['time_s']);p=np.asarray(a['tip_m']);v=np.asarray(a['tip_velocity_m_s']);ta=task(tid);goal=np.asarray(ta['goal']['data']['target_m']);e=np.linalg.norm(p-goal,axis=1);speed=np.linalg.norm(v,axis=1);pa=ta['acceptance']['parameters'];lo,hi=pa['holding_window_s']
fig,axs=plt.subplots(1,2,figsize=(7.16,2.48));fig.subplots_adjust(left=.075,right=.985,bottom=.205,top=.91,wspace=.37)
for ax,y,label,limit,title in zip(axs,[e*1000,speed*1000],['Tip position error (mm)','Tip speed (mm/s)'],[pa['position_limit_m']*1000,pa['speed_limit_m_s']*1000],['(a) Fast reach','(b) Terminal braking']):
 ax.plot(t,y,color=C['navy']);ax.plot([lo,hi],[limit,limit],color=C['brick'],ls=(0,(3,2)),lw=.8);ax.axvline(lo,color=C['gray'],lw=.6,ls=(0,(2,2)));ax.set(xlabel='Time (s)',ylabel=label,xlim=(0,.5),ylim=(0,max(y)*1.1),title=title)
rs=[dict(**origins(tid),time_s=float(ti),tip_error_m=float(e[i]),tip_speed_m_s=float(speed[i]),in_required_hold_window=bool(lo-1e-10<=ti<=hi+1e-10),position_limit_m=pa['position_limit_m'],hold_speed_limit_m_s=pa['speed_limit_m_s'],array_source=ap) for i,ti in enumerate(t)]
source=csvwrite(tid,tid+'_fast_reach_plotdata.csv',rs)
save(tid,tid+'_fast_reach_execution',fig,'T03: stored native motion over the complete 0.5 s task. The vertical line starts the required 0.45–0.50 s hold; red limits are drawn only in that window. Large approach-phase errors/speeds are not terminal violations. No new rollout was performed.',source)

# Exact frozen T04 analytical reference: identical integrated quintic speed-ramp phase.
tid='T04';a,ap,raw=arrays(tid);t=np.asarray(a['time_s']);p=np.asarray(a['tip_m']);ta=task(tid);r=ta['goal']['data']['reference'];start=r['start_ramp_s'];stop=r['stop_ramp_s'];duration=r['duration_s'];integ=lambda u:2.5*u**4-3*u**5+u**6
u=np.clip(t/start,0,1);clock=np.where(t<start,start*integ(u),t-start/2);onset=duration-stop;u=np.clip((t-onset)/stop,0,1);clock=np.where(t>=onset,onset-start/2+stop*(u-integ(u)),clock);phase=2*np.pi*r['frequency_hz']*clock
reference=np.broadcast_to(r['center_m'],p.shape).copy();reference[:,1]+=r['amplitude_y_m']*np.sin(phase);reference[:,2]+=r['amplitude_z_m']*np.sin(2*phase);e=np.linalg.norm(p-reference,axis=1)
fig,axs=plt.subplots(1,2,figsize=(7.16,2.55),gridspec_kw={'width_ratios':[1,1.3]});fig.subplots_adjust(left=.075,right=.985,bottom=.20,top=.88,wspace=.36)
axs[0].plot(reference[:,1]*1000,reference[:,2]*1000,color=C['gray'],ls=(0,(4,2)),lw=1.35,label='Frozen reference',zorder=1);axs[0].plot(p[:,1]*1000,p[:,2]*1000,color=C['navy'],lw=.85,label='Native execution',zorder=2);axs[0].set(xlabel='World y (mm)',ylabel='World z (mm)',title='(a) Figure-eight path');axs[0].set_aspect('equal',adjustable='box');hs,ls=axs[0].get_legend_handles_labels();fig.legend(hs,ls,loc='upper left',bbox_to_anchor=(.07,.995),ncol=2,frameon=False,columnspacing=.9,handlelength=1.6)
axs[1].plot(t,e*1000,color=C['navy']);axs[1].axhline(ta['acceptance']['parameters']['tracking_max_m']*1000,color=C['brick'],lw=.8,ls=(0,(3,2)));axs[1].set(xlabel='Time (s)',ylabel='Tip tracking error (mm)',xlim=(0,22),ylim=(0,6.5),xticks=[0,5,10,15,20,22],title='(b) Complete 22 s execution')
rs=[dict(**origins(tid),time_s=float(ti),phase_rad=float(phase[i]),reference_x_m=float(reference[i,0]),reference_y_m=float(reference[i,1]),reference_z_m=float(reference[i,2]),tip_x_m=float(p[i,0]),tip_y_m=float(p[i,1]),tip_z_m=float(p[i,2]),tracking_error_m=float(e[i]),array_source=ap,reference_source=str(B/tid/'RENDER_INPUTS/default_TASK.json')+'/goal/data/reference') for i,ti in enumerate(t)]
source=csvwrite(tid,tid+'_path_and_error_plotdata.csv',rs)
save(tid,tid+'_figure_eight_path_and_error',fig,'T04: final independent 22 s native execution and the original timed figure-eight reference. The planar projection shows both lobes; the error uses all three world coordinates. Reference values are arithmetic evaluation of the original integrated quintic phase-ramp definition, not a new optimized path. The dashed error line is the 6 mm instantaneous bound; original RMSE is 0.687853 mm and maximum error 1.020664 mm. The incomplete earlier NMPC comparison is not plotted as a completed failure.',source)

# Pose tasks: actual local-tool-axis direction, with task-specific time/reference semantics.
for tid in ['T05','T06']:
 a,ap,raw=arrays(tid);t=np.asarray(a['time_s']);p=np.asarray(a['tip_m']);axis=np.asarray(a['tool_axis_world']);ta=task(tid);g=ta['goal']['data'];lo,hi=ta['sampling']['window_s']
 if tid=='T05':refp=np.broadcast_to(g['target_m'],p.shape);refaxis=np.broadcast_to(g['target_axis_world'],axis.shape)
 else:
  nodes=np.asarray(g['vertices_m']);clocks=np.asarray(g['times_s']);axes=np.asarray(g['axis_vertices_world']);refp=np.column_stack([np.interp(t,clocks,nodes[:,j]) for j in range(3)]);refaxis=np.column_stack([np.interp(t,clocks,axes[:,j]) for j in range(3)])
 axis=axis/np.linalg.norm(axis,axis=1)[:,None];refaxis=refaxis/np.linalg.norm(refaxis,axis=1)[:,None];e=np.linalg.norm(p-refp,axis=1);angle=np.arccos(np.clip(np.sum(axis*refaxis,axis=1),-1,1));ev=ta['evaluator']['parameters']['data'];poslim=ev.get('position_tolerance_m',ev.get('max_error_m'))*1000;anglim=np.degrees(ev['angle_tolerance_rad'])
 fig,axs=plt.subplots(1,2,figsize=(7.16,2.48));fig.subplots_adjust(left=.075,right=.985,bottom=.205,top=.91,wspace=.37)
 for ax,y,label,lim,title in zip(axs,[e*1000,np.degrees(angle)],['Tip position error (mm)','Directed tool-axis error (deg)'],[poslim,anglim],['(a) Position','(b) Tool axis']):
  ax.plot(t,y,color=C['navy']);ax.plot([lo,hi],[lim,lim],color=C['brick'],lw=.8,ls=(0,(3,2)));ax.axvline(lo,color=C['gray'],lw=.6,ls=(0,(2,2)));ax.set(xlabel='Time (s)',ylabel=label,xlim=(0,.6),ylim=(0,max(max(y),lim)*1.13),title=title)
 rs=[dict(**origins(tid),time_s=float(ti),position_error_m=float(e[i]),directed_axis_error_rad=float(angle[i]),reference_x_m=float(refp[i,0]),reference_y_m=float(refp[i,1]),reference_z_m=float(refp[i,2]),reference_axis_x=float(refaxis[i,0]),reference_axis_y=float(refaxis[i,1]),reference_axis_z=float(refaxis[i,2]),in_evaluation_window=bool(lo-1e-10<=ti<=hi+1e-10),position_limit_m=poslim/1000,axis_limit_rad=float(np.radians(anglim)),array_source=ap) for i,ti in enumerate(t)]
 source=csvwrite(tid,tid+'_position_axis_plotdata.csv',rs)
 caption=('T05: stored native position and directed local-tool-axis error. Original acceptance covers 0.58–0.60 s; tolerances are shown only there. Position alone is insufficient for a pass.' if tid=='T05' else 'T06: stored native execution with the full 20 g off-axis tool and non-diagonal inertia. Reference positions are linearly interpolated at the original time vertices and reference axes use original normalized-linear interpolation. Limits apply over 0.02–0.60 s. Position and angle remain separate quantities.')
 save(tid,tid+'_position_and_directed_axis',fig,caption,source)

# Passive P3: actual two-direction physical observations at both payout settings.
tid='T08';hist=list(csv.DictReader((B/tid/'metric_history.csv').open(encoding='utf-8-sig')));executions=[('1.5','e3b1c46ddd1945348baea5a0d31b268c'),('1.8','d8b294000d274e2b918ba1da44d4dc85')];fig,axs=plt.subplots(1,2,figsize=(7.16,2.48));fig.subplots_adjust(left=.075,right=.985,bottom=.22,top=.80,wspace=.37);records=[]
for k,(metric,ylabel,factor,ylim,title) in enumerate([('stiffness_ratio','Progressive stiffness ratio',1,(0,1.95),'(a) Passive stiffness'),('high_maximum','High-load displacement (mm)',1000,(0,28),'(b) Displacement constraint')]):
 ax=axs[k]
 for j,(payout,eid) in enumerate(executions):
  for direction,offset,color,marker in [('plus_x',-.09,C['navy'],'o'),('minus_x',.09,C['teal'],'s')]:
   q=next(x for x in hist if x['execution_id']==eid and x['metric']==direction+'_'+metric);v=float(q['value']);lim=float(q['limit']);ax.scatter(j+offset,v*factor,s=28,color=color,marker=marker,zorder=3,label=('+x' if direction=='plus_x' else '-x') if j==0 else None)
   records.append(dict(task_id=tid,payout_offset_mm=payout,load_condition=direction,candidate_id=q['candidate_id'],execution_id=eid,metric=metric,value_SI=v,unit=q['unit'],limit_SI=lim,passed=q['passed'],original_source=q['source'],comparison_scope='same frozen P3 load protocol, independent recorded physical observations; screening pair and final confirmation retain their separate execution IDs'))
 ax.axhline(lim*factor,color=C['brick'],lw=.8,ls=(0,(3,2)));ax.set(xticks=[0,1],xticklabels=['1.5','1.8'],xlabel='Fixed payout offset (mm)',ylabel=ylabel,xlim=(-.4,1.4),ylim=ylim,title=title)
hs,ls=axs[0].get_legend_handles_labels();fig.legend(hs,ls,loc='upper left',bbox_to_anchor=(.13,.995),ncol=2,frameon=False,handlelength=1.2,columnspacing=1)
source=csvwrite(tid,tid+'_passive_payout_plotdata.csv',records)
save(tid,tid+'_passive_payout_comparison',fig,'T08: original passive P3 results for ±x loading, comparing the actual 1.5 mm and 1.8 mm fixed-payout designs. Both stiffness ratios rise from 1.36684 (failed 1.5 lower bound) to 1.63145, while high-load displacement remains below 25 mm. Markers are unconnected categorical observations. The earlier screening pair and final independent confirmation retain separate execution IDs; no active controller or PHS-2D metric is implied.',source)

# Full contact scene: use the stored complete state and true mj_contactForce signal.
tid='T09';a,ap,raw=arrays(tid);t=np.asarray(a['time_s']);q=np.asarray(a['button_q_m']);force=np.asarray(a['contact_force_n']);ta=task(tid);pa=ta['acceptance']['parameters'];lo,hi=pa['hold_window_s'];depthlo,depthhi=pa['hold_depth_m'];forcelo,forcehi=pa['hold_normal_contact_force_n']
fig,axs=plt.subplots(1,2,figsize=(7.16,2.48));fig.subplots_adjust(left=.075,right=.985,bottom=.205,top=.90,wspace=.37)
for ax,y,label,bounds,ylim,title in zip(axs,[q*1000,force],['Button depth (mm)','Normal contact force (N)'],[(depthlo*1000,depthhi*1000),(forcelo,forcehi)],[(0,3.2),(0,.145)],['(a) Button displacement','(b) Actual contact force']):
 ax.plot(t,y,color=C['navy']);ax.axvline(lo,color=C['gray'],lw=.6,ls=(0,(2,2)));ax.axvline(hi,color=C['gray'],lw=.6,ls=(0,(2,2)))
 for lim in bounds:ax.plot([lo,hi],[lim,lim],color=C['brick'],lw=.8,ls=(0,(3,2)))
 ax.set(xlabel='Time (s)',ylabel=label,xlim=(0,2),ylim=ylim,xticks=[0,.5,1,1.5,2],title=title)
 axs[0].text((lo+hi)/2,3.07,'Hold',ha='center',va='top',fontsize=8,color=C['gray']) if ax is axs[0] else None
hold=(t>=lo-1e-9)&(t<=hi+1e-9);valid=hold&(q>=depthlo)&(q<=depthhi)&(force>=forcelo)&(force<=forcehi)&(np.asarray(a['lateral_error_m'])<=pa['lateral_xz_error_max_m'])&(np.asarray(a['contact_pairs'])>0)
rs=[dict(**origins(tid),time_s=float(ti),button_depth_m=float(q[i]),normal_contact_force_n=float(force[i]),in_required_hold_window=bool(hold[i]),all_contact_hold_conditions_valid=bool(valid[i]),hold_depth_min_m=depthlo,hold_depth_max_m=depthhi,hold_contact_force_min_n=forcelo,hold_contact_force_max_n=forcehi,array_source=ap,button_state_source='/task_evidence/arrays/qpos/'+str(i)+'/48; joint_layout button_slide qpos_address48') for i,ti in enumerate(t)]
source=csvwrite(tid,tid+'_button_depth_force_plotdata.csv',rs)
save(tid,tid+'_contact_depth_and_force',fig,'T09: original 2 s full-hardware contact execution, including all twenty guide assemblies and the button slider. Depth and actual normal contact force (mj_contactForce, not spring-force substitution) are shown separately. Dotted vertical lines delimit the required 0.9–1.4 s hold; red segments delimit legal depth 1.75–2.25 mm and force 0.08–0.12 N only in that window. Original complete acceptance reports 0.5 s continuous valid hold, exceeding the 0.4 s requirement, followed by release checks at 1.8 and 2.0 s.',source)

for tid,(name,cap,source) in CAPTIONS.items():
 doc='\n'.join([f'# {tid} quantitative figure','',f'Figure: {name}.png / {name}.svg','',cap,'',f'Data: {source}','','All curves are arithmetic from recorded signals or exact frozen references. No model loading, optimization, dynamics integration, candidate search or changes to task bounds. Arrays copied in the master archive retain original source_store/raw_reference; CSV original_source points to the original Store artifact. Units remain separate; no average of unlike errors and no connected convergence curve across scopes.','','Style: 7.16 in two-column width; Arial 8–8.5 pt labels; white background; thin axes; no cards, gradients, decorative shadows or large titles. PNG is 500 dpi; SVG text remains editable.',''])
 (B/tid/'FIGURES_PAPER/QUANTITATIVE_FIGURE_CAPTION.md').write_text(doc,encoding='utf8')
 (B/tid/'FIGURE_DATA/QUANTITATIVE_DATA_SOURCES.md').write_text(doc,encoding='utf8')
 print(tid,name,flush=True)
