"""Publication-exportable plots from sealed data only; no simulations."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path(__file__).resolve().parents[1]/'evidence/phs2d_round2_20261028'
summary=json.loads((OUT/'summary.json').read_text(encoding='utf8'))
data=json.loads((OUT/'plot_data.json').read_text(encoding='utf8'))
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150})
colors={'C_mixed_ends':'#168b83','CD_mixed_stiff':'#b65327','D_soft_prox_stiff_dist':'#4663a3'}
names={'C_mixed_ends':'Mixed termination','CD_mixed_stiff':'Mixed + stiff distal','D_soft_prox_stiff_dist':'Stiff distal / full-span'}


def save(fig,name):
    fig.savefig(OUT/(name+'.png'),dpi=200,bbox_inches='tight')
    svg=OUT/(name+'.svg');fig.savefig(svg,bbox_inches='tight');plt.close(fig)
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf8').splitlines())+'\n',encoding='utf8')


fig,ax=plt.subplots(figsize=(8,5))
for label,row in summary['screens'].items():
    if 'min_point_m' not in row:continue
    color=colors.get(label,'#9aa3ad')
    ax.scatter(row['min_point_m']*1000,row['max_tip_m']*1000,color=color,s=45,alpha=.85)
    if label in colors:ax.annotate(names[label],(row['min_point_m']*1000,row['max_tip_m']*1000),xytext=(8,-13 if label=='CD_mixed_stiff' else 5),textcoords='offset points',fontsize=8)
ax.axvline(10,color='black',ls='--',lw=1);ax.axhline(5,color='black',ls='--',lw=1)
ax.fill_between([10,12],0,5,color='#168b83',alpha=.13)
ax.text(10.15,2.5,'Target region\n(ratio also required)',fontsize=8)
ax.set(xlim=(0,12),ylim=(0,38),xlabel='Worst-case force-point displacement prediction [mm]',ylabel='Worst-case tip displacement prediction [mm]',
       title='Local mathematical screening: no feasible prediction')
ax.text(.37,.97,'23 frozen assemblies; one rejected by unloaded lateral offset\nLocal extrapolation only, not physical acceptance',transform=ax.transAxes,va='top',fontsize=8)
save(fig,'mathematical_screen')

sets=[r for r in summary['dynamic_sets'] if r['all_valid'] and r.get('numerics')=={'timestep_s':.000125,'sample_every_steps':80}]
fig,axs=plt.subplots(1,3,figsize=(13,3.8))
x=np.arange(6)
for r in sets:
    for ax,key,scale in zip(axs,['point_dx_m','tip_xy_m','ratio'],[1000,1000,1]):
        ax.plot(x,[a[key]*scale for a in r['rows']],'-o',ms=4,color=colors[r['label']],label=names[r['label']])
for ax,limit,title in zip(axs,[10,5,.3],['Force-point |dx| [mm] (min 10)','Tip |dxy| [mm] (max 5)','Tip / force-point ratio (max 0.30)']):
    ax.axhline(limit,ls='--',color='#111111',lw=1);ax.set_xticks(x,['.3 +','.3 -','.5 +','.5 -','.7 +','.7 -']);ax.set_title(title,fontsize=10)
    ax.grid(axis='y',alpha=.15);ax.set_xlabel('Material s / force sign (0.10 N)')
axs[0].legend(fontsize=8,loc='upper left');fig.suptitle('Independent dynamics: all plotted sets are valid; none passes performance\nSame 0.125 ms step, 4 s duration, unchanged thresholds and soft constraints',fontsize=12,y=1.08)
fig.tight_layout();save(fig,'valid_dynamic_comparison')

chosen=[r for r in data if r['label']=='CD_mixed_stiff' and r['numeric'].startswith('dt=0.000125;')]
fig,axs=plt.subplots(1,3,figsize=(11,5),sharey=True)
for ax,s in zip(axs,[.3,.5,.7]):
    for row in [r for r in chosen if r['s']==s]:
        pos=np.array(row['positions']);base=np.array(row['baseline']);color='#b65327' if row['force_n']>0 else '#4663a3'
        ax.plot(pos[:,0]*1000,pos[:,2],'-o',ms=2,color=color,label=f"F = {row['force_n']:+.2f} N")
        ax.scatter(pos[-1,0]*1000,pos[-1,2],s=65,facecolor='white',edgecolor=color,zorder=4)
        idx=summary['protocol']['monitor_s'].index(s);ax.scatter(pos[idx,0]*1000,pos[idx,2],marker='s',s=40,color=color)
    ax.plot(base[:,0]*1000,base[:,2],'--',color='black',label='Unloaded');ax.set(xlabel='World x [mm]',title=f's = {s:.2f}',xlim=(-5,5));ax.grid(alpha=.15)
axs[0].set_ylabel('World z [m]');axs[0].legend(fontsize=8)
fig.suptitle('Best valid assembly at 0.125 ms: sampled backbone and tip\nSquares: applied material point; open circles: tip. Middle remains too stiff.',fontsize=12)
fig.tight_layout();save(fig,'best_valid_shapes')

fig,axs=plt.subplots(2,1,figsize=(9,5),sharex=True)
for row in data:
    if row['label']=='C_mixed_ends' and row['s']==.5 and row['force_n']>.0:
        tail=row['tail'];label=row['numeric'].split(';')[0]
        axs[0].semilogy([r['time_s'] for r in tail],[r['static_balance_inf_nm'] for r in tail],'-o',ms=3,label=label)
        axs[1].plot([r['time_s'] for r in tail],[r['qvel_inf'] for r in tail],'-o',ms=3,label=label)
axs[0].axhline(1e-5,color='black',ls='--');axs[1].axhline(.01,color='black',ls='--')
axs[0].set_ylabel('Soft static residual [N m]');axs[1].set(ylabel='Max |qvel| [rad/s]',xlabel='Time [s]')
axs[0].legend();axs[0].set_title('Step-size sensitivity: same mixed-termination structure, s=0.5, +0.10 N')
fig.tight_layout();save(fig,'numerical_tail_comparison')
