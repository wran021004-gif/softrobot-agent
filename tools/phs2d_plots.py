"""Static scientific plots of saved P0 evidence; no simulator or Store imports."""
import gzip,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/phs2d_20261028'


def plots():
    summary=json.loads((OUT/'summary.json').read_text())
    package=json.loads(gzip.decompress((OUT/'raw_evidence.json.gz').read_bytes()))
    def get(ref):return package['artifacts'][ref['artifact_id']]
    report=summary['p0'];base=get(report['baseline']);q0=np.array(base['samples'][-1]['positions'])
    trials=[(r['force'],get(r['raw'])) for r in report['trials']]
    s=np.array(summary['protocol']['monitor_s']+[1.05])
    colors={.05:'#679f54',.1:'#1675b8',.2:'#cc8232',-.1:'#ba4160'}
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,2,figsize=(12,9),layout='constrained')
    ax=axes[0,0];ax.plot(q0[:,0]*1000,q0[:,2]*1000,'k--',label='Unloaded terminal (not qualified)')
    for force,raw in trials:
        points=np.array(raw['samples'][-1]['positions']);delta=points-q0
        label=f'{force:+.2f} N'
        ax.plot(points[:,0]*1000,points[:,2]*1000,color=colors[force],label=label)
        axes[0,1].plot(s,delta[:,0]*1000,color=colors[force],label=label)
    ax.set(xlabel='World x (mm)',ylabel='World z (mm)',title='P0 terminal shapes; not equilibrium evidence')
    ax.legend(fontsize=8);ax.set_xlim(-36,36)
    ax.set_title('P0 terminal shapes; horizontal axis expanded')
    axes[0,1].set(xlabel='Normalized flexible arc s (1.05 = tip site)',ylabel='Delta world x (mm)',title='Displacement from unqualified baseline')
    rows=[r for r in summary['conditions'] if r['protocol']=='phs2d_passive_v2' and r['force_n']]
    x=np.arange(len(rows));ax=axes[1,0]
    ax.bar(x-.18,[r['metrics']['point_dx_m']*1000 for r in rows],.36,label='Applied point |dx|')
    ax.bar(x+.18,[r['metrics']['tip_xy_m']*1000 for r in rows],.36,label='Tip horizontal')
    ax.axhline(10,color='#555555',ls='--',lw=1,label='Middle minimum 10 mm');ax.axhline(5,color='#ba4160',ls=':',label='Tip maximum 5 mm')
    ax.set(xticks=x,xticklabels=[f'{r["force_n"]:+.2f} N' for r in rows],ylabel='Displacement (mm)',title='P0 endpoints only; every task result invalid');ax.legend(fontsize=8)
    ax=axes[1,1];math=summary['failure_math'][0]['predictions']
    loc=summary['protocol']['search_s'];ratios=[max(r['unilateral']['ratio'] for r in math if r['s']==ss) for ss in loc]
    ax.plot(loc,ratios,'o--',color='#777777',label='Straight tangent hypothesis (worst sign)')
    ax.scatter([.5],[max(r['metrics']['ratio'] for r in rows if abs(r['force_n'])==.1)],marker='x',s=90,color='#ba4160',label='Unqualified +/-0.10 N terminals')
    ax.axhline(.3,color='black',ls=':',label='Required ratio <=0.30')
    ax.set(xlabel='Force position s',ylabel='Tip / applied-point displacement',title='No validated stable ratio sweep was performed');ax.legend(fontsize=8)
    fig.suptitle('PHS-2D: failed P0 diagnostics — no feasible witness',fontsize=15)
    fig.savefig(OUT/'diagnostic_shapes.png',dpi=180);fig.savefig(OUT/'diagnostic_shapes.svg');plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(12,10),layout='constrained')
    for force,raw in [(0.,base),*trials]:
        trace=raw['samples'];t=[r['time_s'] for r in trace];label=f'{force:+.2f} N';color=colors.get(force,'black')
        axes[0,0].plot(t,[r['speeds'][-1]*1000 for r in trace],label=label,color=color)
        axes[0,1].semilogy(t,np.maximum(1e-12,[r['static_balance_inf_nm'] for r in trace]),color=color)
        if abs(force)==.1:
            for i,style in [(0,'-'),(1,'--')]:
                axes[1,0].plot(t,[r['length_change'][i]*1e6 for r in trace],style,color=color,label=f'{label}, rope {i}')
                axes[1,1].plot(t,[r['tensions_n'][i] for r in trace],style,color=color,label=f'{label}, rope {i}')
            axes[2,0].plot(t,[r['qvel_inf'] for r in trace],color=color,label=label)
            axes[2,1].plot(t,[r['positions'][-1][1]*1000 for r in trace],color=color,label=label)
    axes[0,0].axhline(1,color='#555555',ls=':');axes[0,0].legend(fontsize=8)
    axes[0,1].axhline(1e-5,color='#555555',ls=':')
    axes[1,0].axhline(50,color='#555555',ls=':');axes[1,0].legend(fontsize=8)
    axes[1,1].legend(fontsize=8);axes[2,0].axhline(.01,color='#555555',ls=':')
    names=[('Tip speed (mm/s)','Tail must be <1 mm/s'),('Static balance inf (N m)','Tail must be <=1e-5 N m'),
        ('Length minus payout (micrometers)','Positive is soft limit penetration'),('Tendon tension (N)','Nonnegative constraint multiplier'),
        ('Max joint speed (rad/s)','Tail must be <=0.01 rad/s'),('Tip world y (mm)','3D drift retained')]
    for ax,(ylabel,title) in zip(axes.flat,names):
        ax.set(xlabel='Time (s)',ylabel=ylabel,title=title);ax.axvspan(3.75,4.,color='#999999',alpha=.12)
    fig.suptitle('P0 numerical qualification and unilateral rope records',fontsize=15)
    fig.savefig(OUT/'diagnostic_constraints.png',dpi=180);fig.savefig(OUT/'diagnostic_constraints.svg');plt.close(fig)


if __name__=='__main__':plots()
