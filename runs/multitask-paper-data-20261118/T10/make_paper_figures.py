"""T10 scientific plots from archived states/results only; no model execution."""
from pathlib import Path
import csv,json,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

B=Path(__file__).resolve().parent
I=B/'RENDER_INPUTS';F=B/'FIGURES_PAPER';D=B/'FIGURE_DATA'
F.mkdir(exist_ok=True);D.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'Arial','font.size':8.5,'axes.labelsize':8.5,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'axes.linewidth':.6,'lines.linewidth':1.05,'xtick.major.width':.6,'ytick.major.width':.6,'xtick.major.size':3,'ytick.major.size':3,'svg.fonttype':'none','pdf.fonttype':42,'savefig.facecolor':'white'})
C={'navy':'#26384B','teal':'#527F7B','slate':'#70849A','ochre':'#B08A59','green':'#557663','brick':'#A35D55','gray':'#929BA4'}
def save(name,fig):
    fig.savefig(F/(name+'.png'),dpi=450)
    fig.savefig(F/(name+'.svg'))
    plt.close(fig)
def csvwrite(path,rows):
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def load(n):return json.loads((I/n).read_text(encoding='utf-8-sig'))

cases=['no_impulse','positive_y','negative_y','positive_y_frozen','negative_y_frozen']
labels={'no_impulse':'No impulse (required)','positive_y':r'$+y$ active (required)','negative_y':r'$-y$ active (required)','positive_y_frozen':r'$+y$ frozen (control)','negative_y_frozen':r'$-y$ frozen (control)'}
colors={'no_impulse':C['gray'],'positive_y':C['navy'],'negative_y':C['teal'],'positive_y_frozen':C['navy'],'negative_y_frozen':C['teal']}
rows=[];series={};checks=[]
for condition in cases:
    m=load(condition+'_MOTION.json');r=load(condition+'_RESULT.json')
    t=np.asarray(m['times_s']);p=np.asarray(m['tip_m']);v=np.asarray(m['tip_velocity_m_s'])
    e=np.linalg.norm(p-np.array([.29,-.035,.19]),axis=1);speed=np.linalg.norm(v,axis=1)
    hold=(t>=.9-1e-9)&(t<=1+1e-9)
    for key,val in [('final_hold_max_error_m',float(e[hold].max())),('final_hold_max_speed_m_s',float(speed[hold].max()))]:
        recorded=r['acceptance']['metrics'][key]
        checks.append({'condition':condition,'metric':key,'arithmetic_from_stored_signals':val,'original_result':recorded,'absolute_difference':abs(val-recorded)})
        if abs(val-recorded)>1e-9:raise ValueError((condition,key,val,recorded))
    series[condition]=(t,e*1000,speed*1000)
    for i,ti in enumerate(t):rows.append({'task_id':'T10','condition_id':condition,'protocol_role':'control' if condition.endswith('_frozen') else 'required','time_s':float(ti),'position_error_m':float(e[i]),'tip_speed_m_s':float(speed[i]),'tip_x_m':float(p[i,0]),'tip_y_m':float(p[i,1]),'tip_z_m':float(p[i,2]),'force_y_n':m['force_n'][i][1],'source_motion_file':str(I/(condition+'_MOTION.json')),'source_original_store':str(m['source'])})
csvwrite(D/'T10_final_execution_source.csv',rows)
(D/'T10_plot_arithmetic_checks.json').write_text(json.dumps(checks,indent=2)+'\n')

fig,axs=plt.subplots(1,2,figsize=(7.16,2.85),sharex=True)
for condition in cases:
    t,e,v=series[condition];style=(0,(4,2)) if condition.endswith('_frozen') else '-'
    for ax,y in zip(axs,[e,v]):ax.plot(t,y,color=colors[condition],linestyle=style,label=labels[condition],alpha=.92)
for i,ax in enumerate(axs):
    ax.set_xlim(.3,1.0);ax.set_xlabel('Time (s)');ax.spines[['top','right']].set_visible(False)
    ax.set_xticks([.3,.5,.7,.9,1.0]);ax.tick_params(direction='out')
    for ts in [.5,.55]:ax.axvline(ts,color=C['ochre'],lw=.65,alpha=.8,zorder=0)
    # Position/speed tolerance shown only during the corresponding hold windows.
    lim=10 if i==0 else 20
    for lo,hi in [(.3,.5),(.9,1.)]:ax.plot([lo,hi],[lim,lim],color=C['brick'],linestyle=(0,(2,2)),lw=.8,zorder=0)
    ax.text(.01,.98,'('+chr(97+i)+')',transform=ax.transAxes,va='top',ha='left',fontsize=8.5)
axs[0].set_ylabel('Tip position error (mm)');axs[0].set_ylim(0,11.5)
axs[1].set_ylabel('Tip speed (mm/s)');axs[1].set_ylim(0,70)
axs[1].text(.525,68,'Pulse',ha='center',va='top',fontsize=8,color=C['ochre'])
axs[1].text(.94,68,'Final hold',ha='center',va='top',fontsize=8,color=C['navy'])
handles,labs=axs[0].get_legend_handles_labels()
fig.legend(handles,labs,loc='upper center',bbox_to_anchor=(.51,1.0),ncol=3,frameon=False,columnspacing=1.3,handlelength=2.6)
fig.subplots_adjust(left=.078,right=.972,bottom=.18,top=.78,wspace=.30)
save('T10_impact_active_vs_frozen',fig)

bundle=json.loads((B/'evidence_bundle.json').read_text())
nodes={n['node_id']:n for n in bundle['selected_nodes']}
final=[n for n in bundle['selected_nodes'] if n['source_tag']=='T10_RUN_06' and n['protocol_role']=='required']
stages=[('GVS NMPC',nodes['T10_N03'],'run02 no_impulse raw physical evaluation FAIL; profile export incomplete'),('Native feedback',nodes['T10_N04'],'run03 positive_y single-case independent PASS; shared multi-case acceptance unavailable'),('Common feedback',None,'run06 3 required cases independently PASS with verified identical controller')]
metrics=[('final_hold_max_speed_m_s','Final hold speed (mm/s)',.020),('max_tendon_speed_m_s','Tendon speed (mm/s)',.025),('max_tendon_stroke_m','Tendon stroke (mm)',.015)]
records=[];fig,axs=plt.subplots(1,3,figsize=(7.16,2.48))
for k,(metric,ylabel,limit) in enumerate(metrics):
    ax=axs[k];vals=[]
    for j,(name,node,scope) in enumerate(stages):
        value=node['metrics'][metric] if node else max(n['metrics'][metric] for n in final)
        vals.append(value*1000)
        records.append({'task_id':'T10','stage':name,'metric':metric,'value_SI':value,'plot_value':value*1000,'limit_SI':limit,'scope':scope,'source':node['result_ref'] if node else '; '.join(n['result_ref'] for n in final),'case_aggregation':'single no_impulse' if j==0 else ('single positive_y' if j==1 else 'metricwise maximum over 3 required cases'),'line_connection_allowed':False})
        ax.scatter(j,value*1000,s=23,color=[C['brick'],C['teal'],C['navy']][j],zorder=3)
        ax.annotate(f'{value*1000:.1f}',(j,value*1000),xytext=(0,5),textcoords='offset points',ha='center',fontsize=8)
    ax.axhline(limit*1000,color=C['gray'],lw=.8,ls=(0,(3,2)))
    ax.set_ylabel(ylabel);ax.set_xticks([0,1,2],['GVS\nnominal','Native\none case','Common\n3 cases']);ax.set_xlim(-.4,2.4);ax.set_ylim(0,max(vals+[limit*1000])*1.24)
    ax.spines[['top','right']].set_visible(False);ax.text(.02,.98,'('+chr(97+k)+')',transform=ax.transAxes,va='top')
fig.subplots_adjust(left=.074,right=.982,bottom=.24,top=.95,wspace=.50)
save('T10_control_route_constraint_comparison',fig)
csvwrite(D/'T10_control_route_comparison_source.csv',records)

print('Generated two PNG/SVG figure sets; 10 final-hold values match original results within 1e-9 SI; no dynamics executed.')
