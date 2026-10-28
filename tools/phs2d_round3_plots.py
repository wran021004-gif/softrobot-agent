"""Publication figures from exported third-round evidence; no MuJoCo calls."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from tools.phs2d_round3_export import OUT
from tools.state_io import atomic_json
from extensions.tendon_family.geometry import geometry


def save(fig,name):
    fig.savefig(OUT/(name+'.png'),dpi=180,bbox_inches='tight');fig.savefig(OUT/(name+'.svg'),bbox_inches='tight');plt.close(fig)


def centerline(physics,g):
    points=[];curvature=[];material=[];previous=0.;length=0.
    for part,body in zip(physics['parts'],g['bodies']):
        if not part['dofs']:continue
        start=body['p'];end=start+body['R']@np.array([part['length_m'],0,0]);points.extend([start,end])
        tangent=body['R'][:,0];angle=float(np.arctan2(tangent[0],-tangent[2]));change=np.arctan2(np.sin(angle-previous),np.cos(angle-previous))
        curvature.append(float(change/part['length_m']));material.append(length+part['length_m']/2)
        previous=angle;length+=part['length_m']
    return np.array(points),np.array(material)/length,np.array(curvature)


def plots():
    package=json.loads((OUT/'solution/design.json').read_text());summary=json.loads((OUT/'summary.json').read_text());physics=package['physics'];rows=sorted(package['cases'],key=lambda r:(r['s'],-r['force_n']))
    protocol=package['protocol'];mount=dict(position_m=protocol['mount_position'],quaternion_wxyz=[2**-.5,0,2**-.5,0])
    base=geometry(physics,package['baseline']['qpos'],mount);bc,bs,bk=centerline(physics,base)
    chosen=next(r for r in rows if r['s']==.5 and r['force_n']>0);g=geometry(physics,chosen['qpos'],mount);line,arc,k=centerline(physics,g)
    np.testing.assert_allclose(g['tip'],chosen['positions'][-1],atol=1e-9)
    fig,axes=plt.subplots(2,2,figsize=(12,10));ax=axes[0,0]
    ax.plot(line[:,0]*1000,line[:,2],color='#1659a6',lw=2.4,label='Backbone, s=0.5, +0.10 N')
    ax.plot(bc[:,0]*1000,bc[:,2],'--',color='gray',lw=1,label='Unloaded')
    for part,body in zip(physics['parts'],g['bodies']):
        if part['component'].startswith('guide_'):
            h=np.array(part['envelope_halfsize_m']);corners=np.array([[x,0,z] for x,z in [(-h[0],-h[2]),(-h[0],h[2]),(h[0],h[2]),(h[0],-h[2])]])
            world=body['p']+corners@body['R'].T;ax.add_patch(Polygon(np.c_[world[:,0]*1000,world[:,2]],color='#b7a077',alpha=.55))
    for ti,path in enumerate(g['routes']):
        ax.plot(path[:,0]*1000,path[:,2],color=('#d65523' if ti%2 else '#17a383'),lw=1.1,alpha=.65,label='Paired physical cables' if ti==0 else None)
    ax.scatter([g['tip'][0]*1000],[g['tip'][2]],s=45,c='#222222',zorder=5,label='Tip')
    ax.set(xlabel='World x (mm)',ylabel='World z (m)',title='Actual guides, holes and payload anchors');ax.legend(fontsize=8);ax.grid(alpha=.2)
    ax=axes[0,1];colors={.3:'#2464a8',.5:'#d6722c',.7:'#278752'}
    for row in rows:
        if row['s'] not in colors:continue
        p=np.array(row['positions']);ax.plot(p[:,0]*1000,p[:,2],'-' if row['force_n']>0 else '--',color=colors[row['s']],label=f"s={row['s']}, {'+' if row['force_n']>0 else '-'}0.10 N")
    ax.plot(bc[:,0]*1000,bc[:,2],':',c='gray');ax.set(xlabel='World x (mm)',ylabel='World z (m)',title='Six search shapes on the same structure');ax.grid(alpha=.2);ax.legend(fontsize=8)
    ax=axes[1,0];ax.plot(arc,k-bk,c='#1659a6',lw=2);ax.axhline(0,c='black',lw=.8)
    ax.set(xlabel='Normalized flexible material s',ylabel='Change of x-z curvature (rad/m)',title='Measured opposite-sign curvature, s=0.5 +0.10 N');ax.grid(alpha=.2)
    ax=axes[1,1];tensions=np.array([r['final_tensions_n'] for r in rows]);im=ax.imshow(tensions,aspect='auto',cmap='YlOrRd',vmin=0)
    for i in range(len(rows)):
        for j in range(4):ax.text(j,i,f'{tensions[i,j]:.3f}',ha='center',va='center',fontsize=7,color='black')
    ax.set_xticks(range(4),[f'T{i}' for i in range(4)]);ax.set_yticks(range(len(rows)),[f"{r['s']:.1f} {'+' if r['force_n']>0 else '-'}" for r in rows]);ax.set_title('Complementary taut/slack sets; capacity 8 N');fig.colorbar(im,ax=ax,label='Tension (N)')
    fig.suptitle('PHS-2D: nine flexible segments, four passive guided tendons',fontsize=14);fig.tight_layout();save(fig,'solution_mechanism')
    fig,axes=plt.subplots(2,2,figsize=(11,8));fields=[('point_dx_m',1000,10.,'Force-point |dx| (mm)'),('tip_xy_m',1000,5.,'Tip horizontal displacement (mm)'),('ratio',1,.30,'Tip / force-point displacement'),('out_of_plane_m',1000,2.,'Out-of-plane displacement (mm)')]
    sets=[s for s in summary['final_sets'] if s.get('replicate') in (1,2,3)]
    for ax,(field,scale,limit,title) in zip(axes.flat,fields):
        for rep,style,name in [(1,'o-','Independent'),(2,'x--','Half timestep'),(3,'+:' ,'Initial perturbation')]:
            rr=sorted([r for s in sets if s.get('replicate')==rep for r in s['rows']],key=lambda r:(r['s'],-r['force_n']))
            for sign,color in [(1,'#2464a8'),(-1,'#d6722c')]:
                selected=[r for r in rr if np.sign(r['force_n'])==sign];ax.plot([r['s'] for r in selected],[r[field]*scale for r in selected],style,color=color,alpha=.75,label=name+(' +' if sign>0 else ' -'))
        ax.axhline(limit,c='#bd3030',ls='--',lw=1.2,label='Frozen threshold');ax.set(title=title,xlabel='Force location s');ax.grid(alpha=.2)
        if field=='out_of_plane_m':ax.set_yscale('log')
        else:ax.set_ylim(bottom=0)
    axes[0,0].legend(fontsize=7,ncol=2);fig.suptitle('All ten cases: unchanged acceptance and independent numerical checks');fig.tight_layout();save(fig,'task_validation')
    search=[r for r in rows if r['s'] in protocol['search_s']];local=package['modal']['B_C_unilateral_force_response']['predictions'];stat=package['math_screen']['rows'];fig,axes=plt.subplots(1,2,figsize=(12,4.5));x=np.arange(6)
    for ax,field in zip(axes,['point_dx_m','tip_xy_m']):
        for offset,source,name,color in [(-.25,local,'Local tangent','#9bb3cb'),(0,stat,'Nonlinear hard cable','#3576ad'),(.25,search,'MuJoCo soft cable','#d67839')]:
            ax.bar(x+offset,[r[field]*1000 for r in source],width=.24,label=name,color=color)
        ax.set_xticks(x,[f"{r['s']} {'+' if r['force_n']>0 else '-'}" for r in search]);ax.set(ylabel='Displacement (mm)',title='Force point' if field=='point_dx_m' else 'Tip');ax.grid(axis='y',alpha=.2)
    axes[0].legend(fontsize=8);fig.suptitle('Finite cable geometry matters beyond a perfect local Jacobian match');fig.tight_layout();save(fig,'math_vs_physics')
    curvature=[]
    for row in rows:
        _,_,ki=centerline(physics,geometry(physics,row['qpos'],mount));delta=ki-bk
        curvature.append(dict(s=row['s'],force_n=row['force_n'],minimum_delta_curvature_rad_m=float(delta.min()),maximum_delta_curvature_rad_m=float(delta.max()),opposite_sign_curvature=bool(delta.min()<-.1 and delta.max()>.1)))
    assert all(r['opposite_sign_curvature'] for r in curvature)
    atomic_json(OUT/'curvature_evidence.json',curvature)


if __name__=='__main__':plots()
