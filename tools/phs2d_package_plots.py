"""Scientific plots from exported saved states and unchanged original evaluations."""
import argparse
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import mujoco
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from phs2d_io import TASK_DIR,read,write,load_model,restore,centerline,material_point,point,forbid_integration


def generate(package):
    forbid_integration()
    base=package/TASK_DIR;out=base/'previews';out.mkdir(exist_ok=True)
    available={f.name for f in font_manager.fontManager.ttflist}
    for name in ('Microsoft YaHei','SimHei','Noto Sans CJK SC'):
        if name in available:plt.rcParams['font.sans-serif']=[name];break
    plt.rcParams.update({'axes.unicode_minus':False,'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    physics=read(base/'structure.json')['physics'];task=read(base/'task.json');dataset=read(base/'dataset.json')
    model=load_model(base/'robot.xml');data=mujoco.MjData(model)
    finals={};shapes={}
    for entry in dataset['trajectories']:
        with np.load(base/entry['directory']/'states_timestep.npz',allow_pickle=False) as archive:
            finals[entry['condition']]=archive['trajectory'][-1].copy()
        restore(model,data,finals[entry['condition']]);shapes[entry['condition']]=centerline(model,data,physics)
    unloaded=shapes['equilibrium']
    def save(fig,name):
        fig.savefig(out/(name+'.png'),dpi=180,bbox_inches='tight')
        fig.savefig(out/(name+'.svg'),bbox_inches='tight')
        plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(9,6),layout='constrained')
    for ax,coordinate,label in zip(axes,(0,1),('世界 x / mm','世界 y / mm')):
        ax.plot(unloaded[:,coordinate]*1000,unloaded[:,2]*1000,color='#3069a9',marker='.',ms=3)
        ax.scatter(unloaded[[0,-1],coordinate]*1000,unloaded[[0,-1],2]*1000,c=['#333333','#ec9a22'],zorder=3)
        ax.set(xlabel=label,ylabel='世界 z / mm',title='无力基准末态中轴')
        ax.grid(alpha=.2)
    fig.suptitle('原保存状态；横向与纵向刻度独立（非等比例）')
    save(fig,'unloaded_centerline')
    fig,axes=plt.subplots(1,3,figsize=(13,6),layout='constrained')
    for ax,s in zip(axes,(.3,.5,.7)):
        ax.plot(unloaded[:,0]*1000,unloaded[:,2]*1000,'--',c='#777777',label='原无力中轴')
        for sign,color,label in [('positive','#bc4436','+0.10 N'),('negative','#2776a6','−0.10 N')]:
            name=f's{round(s*100):03d}_{sign}';shape=shapes[name]
            ax.plot(shape[:,0]*1000,shape[:,2]*1000,c=color,label=label)
            restore(model,data,finals[name]);p,_=point(model,data,physics,material_point(physics,s))
            ax.scatter(p[0]*1000,p[2]*1000,c=color,marker='s',s=25)
        ax.set(title=f'材料位置 s={s:.2f}',xlabel='世界 x / mm',ylabel='世界 z / mm')
        ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('真实保存末态：正负受力与无力中轴叠加（横纵独立刻度）')
    save(fig,'force_shape_overlays')
    cases=sorted(task['original_cases'],key=lambda r:(r['s'],-r['force_n']))
    labels=[f"{r['s']:.1f}\n{'+' if r['force_n']>0 else '−'}" for r in cases];x=np.arange(len(cases))
    fig,ax=plt.subplots(figsize=(11,4.8),layout='constrained')
    ax.bar(x-.18,[r['point_dx_m']*1000 for r in cases],.36,label='受力点 |Δx|',color='#347fa0')
    ax.bar(x+.18,[r['tip_xy_m']*1000 for r in cases],.36,label='Tip ||Δxy||',color='#dd9243')
    ax.axhline(10,color='#347fa0',ls='--',label='受力点最低 10 mm')
    ax.axhline(5,color='#dd9243',ls=':',label='Tip 上限 5 mm')
    ax.set(xticks=x,xticklabels=labels,xlabel='材料 s / 力方向',ylabel='末态位移 / mm',title='原十工况：受力点与 Tip 位移对照')
    ax.legend(ncol=2,fontsize=9);ax.grid(axis='y',alpha=.2)
    save(fig,'tip_vs_force_point')
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    definitions=[('point_dx_m',1000,10,'受力点 |Δx| / mm（≥10）'),('tip_xy_m',1000,5,'Tip ||Δxy|| / mm（≤5）'),
                 ('ratio',1,.3,'Tip / 受力点（≤0.30）'),('out_of_plane_m',1000,2,'监测点平面外漂移 / mm（≤2）')]
    for ax,(key,scale,limit,title) in zip(axes.flat,definitions):
        values=[r[key]*scale for r in cases]
        ax.bar(x,values,color=['#347fa0' if r['s'] in (.3,.5,.7) else '#799e63' for r in cases])
        ax.axhline(limit,color='#b84840',ls='--',label='原冻结阈值')
        ax.set(xticks=x,xticklabels=labels,title=title,ylim=(0,max(max(values),limit)*1.18))
        ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8)
        if key=='out_of_plane_m':ax.text(.02,.87,f'最大实际值 {max(values):.6f} mm',transform=ax.transAxes)
    fig.suptitle('原评价指标；蓝=搜索、绿=独立验证；显示舍入不用于重新验收')
    save(fig,'ten_case_thresholds')
    fig,axes=plt.subplots(1,3,figsize=(13,4.3),layout='constrained')
    restore(model,data,finals['equilibrium'])
    base_tip=data.site_xpos[model.site('tip_site').id].copy()
    for ax,s in zip(axes,(.3,.5,.7)):
        restore(model,data,finals['equilibrium'])
        base_point=point(model,data,physics,material_point(physics,s))[0]
        with np.load(base/f's{round(s*100):03d}_positive/states_timestep.npz',allow_pickle=False) as a:
            times=a['trajectory'][::80,0]
            tips=a['tip_position_m'][::80]
            points=a['force_point_m'][::80]
        ax.plot(times,np.abs(points[:,0]-base_point[0])*1000,label='受力点 |Δx|',c='#347fa0')
        ax.plot(times,np.linalg.norm(tips[:,:2]-base_tip[:2],axis=1)*1000,label='Tip ||Δxy||',c='#dd9243')
        ax.set(xlabel='原引擎时间 / s',ylabel='相对无力末态位移 / mm',title=f's={s:.2f}, +0.10 N')
        ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('原逐步状态的显示抽样（每 80 帧，仅作画图；全量数据未删减）')
    save(fig,'displacement_time_series')
    write(base/'evidence/plot_provenance.json',dict(physics_steps=0,source='Exported original saved qpos and original evaluation JSON',
        generated=['unloaded_centerline','force_shape_overlays','tip_vs_force_point','ten_case_thresholds','displacement_time_series'],
        shape_axes='Independent horizontal/vertical scales, explicitly labelled',plotting_only_dependencies=['matplotlib']))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package',type=Path,required=True)
    generate(p.parse_args().package.resolve())


if __name__=='__main__':main()
