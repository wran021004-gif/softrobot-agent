"""Bounded core-risk checks. Static calculations only, never time integration."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from numpy.testing import assert_allclose
from tools.state_io import atomic_json


def shared_design():
    from extensions.tendon_family.contracts import Design
    point=lambda s,y,role:dict(attachment=dict(part='arm' if s else 'fixed_base',s=s,position_m=[0.,y,0.]),role=role)
    return Design.model_validate(dict(id='shared_antagonistic',components=[dict(id='arm',kind='flexible_segment',length_m=.12,cells=2,
        sections=[dict(s=0.,section=dict(kind='circle',parameters=dict(radius_m=.006)))],
        physics=dict(mode='equivalent',line_density_kg_m=.2,bending_ei_nm2=[.02,.025],bending_viscosity_nm2_s=[.001,.001]))],
        tendons=[dict(id='rope'+str(i),points=[point(0.,y,'start'),point(.5,y,'guide'),point(1.,y,'anchor')],diameter_m=.001,
            length_servo_gain_n_m=1000.,pretension_n=.1,force_limit_n=.8) for i,y in enumerate([.012,-.012])],
        actuators=[dict(id='differential',command_type='rotation',units='rad',drum_radius_m=.01,
            transmission=[dict(tendon='rope0',ratio=1.),dict(tendon='rope1',ratio=-1.)],limits=[-.3,.3],velocity_limit=2.)],
        tip=dict(part='arm',s=1.)))


def section_checks():
    from extensions.tendon_family.sections import properties
    def rect(a,b,offset=(0,0)):
        return (np.array([[-a,-b],[a,-b],[a,b],[-a,b]])/2+offset).tolist()
    p=properties(dict(kind='polygon',outer_yz_m=rect(.04,.03),holes_yz_m=[rect(.01,.008,(.004,.002))]))
    A=.04*.03-.01*.008; center=-.01*.008*np.array([.004,.002])/A
    assert_allclose(p['area_m2'],A,rtol=1e-13); assert_allclose(p['centroid_yz_m'],center,atol=1e-17)
    C=np.diag([.03*.04**3/12,.04*.03**3/12])-np.diag([.008*.01**3/12,.01*.008**3/12])-.01*.008*np.outer([.004,.002],[.004,.002])-A*np.outer(center,center)
    assert_allclose(p['area_covariance_m4'],C,rtol=1e-13)
    a=properties(dict(kind='rectangle',parameters=dict(width_y_m=.02,height_z_m=.01)))
    b=properties(dict(kind='rectangle',parameters=dict(width_y_m=.02,height_z_m=.01),angle_rad=np.pi/2))
    assert_allclose(np.diag(b['bending_area_m4']),np.diag(a['bending_area_m4'])[::-1],rtol=1e-13)
    tube=properties(dict(kind='tube',parameters=dict(outer_radius_m=.02,inner_radius_m=.01)))
    assert_allclose(tube['area_m2'],np.pi*.0003)
    assert_allclose(tube['bending_area_m4'],np.eye(2)*np.pi*(.02**4-.01**4)/4)
    ellipse=properties(dict(kind='ellipse',parameters=dict(semi_y_m=.02,semi_z_m=.01)))
    assert_allclose(np.diag(ellipse['bending_area_m4']),[np.pi*.02*.01**3/4,np.pi*.02**3*.01/4])
    return dict(polygon_with_offset_hole_area_m2=A,centroid_yz_m=center.tolist(),rotated_rectangle_axes_swapped=True,torsion_constant_not_claimed=tube['torsion_constant_m4'] is None)


def engine_static(p,s,path,q,v):
    import mujoco
    from extensions.tendon_family.mjcf import compile_xml
    compile_xml(p,s,None,path); model=mujoco.MjModel.from_xml_path(str(path)); data=mujoco.MjData(model)
    ids=[model.joint(n).id for n in p['dofs']]; qi=model.jnt_qposadr[ids]; vi=model.jnt_dofadr[ids]
    data.qpos[qi]=q; data.qvel[vi]=v; mujoco.mj_forward(model,data)
    M=np.zeros((model.nv,model.nv)); mujoco.mj_fullM(model,data,M)
    tids=[model.tendon(t['entity']).id for t in p['tendons']]
    jac=np.zeros((model.ntendon,model.nv))
    if data.ten_J.size==model.ntendon*model.nv: jac[:]=data.ten_J.reshape(model.ntendon,model.nv)
    else:
        for k in range(model.ntendon):
            adr=model.ten_J_rowadr[k]; nnz=model.ten_J_rownnz[k]
            jac[k,model.ten_J_colind[adr:adr+nnz]]=data.ten_J[adr:adr+nnz]
    jac=jac[tids][:,vi]
    assert_allclose([model.body_mass[model.body(b['entity']).id] for b in p['parts']],[b['mass_kg'] for b in p['parts']],rtol=1e-13)
    from extensions.tendon_family.compiler import quat
    for b in p['parts']:
        bid=model.body(b['entity']).id; R=quat(model.body_iquat[bid]); I=R@np.diag(model.body_inertia[bid])@R.T
        assert_allclose(I,b['inertia_com_local_kg_m2'],atol=1e-14)
    return model,data,dict(mass=M[np.ix_(vi,vi)],bias_gravity=data.qfrc_bias[vi].copy(),lengths=data.ten_length[tids].copy(),Jlength=jac.copy(),tip=data.site_xpos[model.site('tip_site').id].copy())


def checks(root,matlab=False):
    from extensions.tendon_family.compiler import resolve
    from extensions.tendon_family.geometry import geometry
    from extensions.tendon_family.control import Controller
    from extensions.tendon_family.contracts import Control,Parameters
    from extensions.tendon_family.scene import assemble
    from examples.platform_tendon_family import session,design_space
    from schemas.platform import SessionInput
    from tools.platform_tasks import compile_input
    from examples.platform_spatial_example import session_input
    root=Path(root); out=dict(sections=section_checks(),complete_dynamics_solves=0)
    shared=shared_design(); ps=resolve(shared)
    atomic_json(root/'shared_design.json',shared.model_dump(mode='json')); atomic_json(root/'shared_physics.json',ps)
    pairs=[]
    for label in ('continuous','structural','shared'):
        if label=='shared':
            d=shared; p=ps
            # Same frozen environment; remove the payload force absent in this small robot.
            inp=json.loads((root/'inputs/family_mujoco.json').read_text(encoding='utf8'))
            inp['robot']['structure']['data']=d.model_dump(mode='json'); inp['task']['environment']['data']['external_forces']=[]
            inp['policy']['controller']['parameters']['data']=dict(mode='deterministic',commands={'differential':10.},ramp_s=.001)
            ctrl=Control.model_validate(inp['policy']['controller']['parameters']['data']); s=assemble(SessionInput.model_validate(inp),p)
        else:
            inp=json.loads((root/(label+'_family_mujoco_input.json')).read_text(encoding='utf8')); p,s=inp['physics'],inp['scene']; ctrl=Control()
        q=np.linspace(-.03,.04,len(p['dofs'])); v=np.linspace(.04,-.02,len(q))
        mount=s['assembly']['mount']; g=geometry(p,q,mount)
        eps=1e-7; direction=np.linspace(.2,.8,len(q))
        fd=(geometry(p,q+eps*direction,mount)['lengths']-geometry(p,q-eps*direction,mount)['lengths'])/(2*eps)
        assert_allclose(fd,g['Jlength']@direction,atol=2e-9)
        model,data,mj=engine_static(p,s,root/(label+'_static.xml'),q,v)
        assert_allclose(g['tip'],mj['tip'],atol=1e-12); assert_allclose(g['lengths'],mj['lengths'],atol=1e-12); assert_allclose(g['Jlength'],mj['Jlength'],atol=1e-12)
        if label!='shared':
            near=[i for i,n in enumerate(p['dofs']) if n.startswith('near_')]; far=[i for i,n in enumerate(p['dofs']) if n.startswith('far_')]
            assert np.linalg.norm(g['Jlength'][3:,near])>1e-3
            assert_allclose(g['Jlength'][:3,far],0.,atol=1e-14)
        control=Controller(ctrl,s['control_period_s']); control.configure(p,s['target_world_m']); target=control.command(0.,g,q,v)
        if label=='shared':
            assert_allclose(control.u,[.02]); delta=target-np.array(p['reference_lengths_m'])+.0001
            assert_allclose(delta,[.0002,-.0002],atol=1e-14)
            for k,t in enumerate(p['tendons']): data.ctrl[model.actuator(t['entity']+'_length_servo').id]=target[k]
            import mujoco
            mujoco.mj_forward(model,data)
            assert np.all(data.actuator_force<=0) and np.all(data.actuator_force>=-.8)
            for step in range(30): control.command(step*.01,g,q,v)
            assert_allclose(control.u,[.3])
        out[label]=dict(jacobian_directional_error=float(np.max(np.abs(fd-g['Jlength']@direction))),dofs=len(q),actuators=len(p['actuators']),full_inertia_consumed=True)
        config=Parameters().model_dump(mode='json'); ss={**s,'qpos_rad':q.tolist(),'qvel_rad_s':v.tolist()}
        cc=ctrl.model_dump(mode='json'); cc.update(target_world_m=s['target_world_m'],command_vector=[cc['commands'].get(a['id'],0.) for a in p['actuators']])
        pairs.append((label,dict(physics=p,scene=ss,config=config,control=cc,timeout_s=60.),mj,target))
    # Necessary old public entry compatibility: compile only, no extra solve.
    compile_input(session_input('math_spatial')); compile_input(session_input('math_planar','C1'))
    out['legacy_entries']='math_spatial and math_planar compile_input passed; no extra solve'
    if matlab:
        from tools.matlab_tools import MatlabTools
        tool=MatlabTools()
        try:
            for label,shared_input,mj,target in pairs:
                result=json.loads(tool.eng.tf_static(json.dumps(shared_input),nargout=1)); atomic_json(root/(label+'_matlab_static.json'),result)
                for key in ('mass','lengths','Jlength','tip'): assert_allclose(result[key],mj[key],rtol=1e-9,atol=1e-11)
                assert_allclose(np.array(result['bias'])-result['gravity'],mj['bias_gravity'],rtol=1e-9,atol=1e-11)
                assert_allclose(result['target_lengths_m'],target,atol=1e-12)
                out[label]['matlab_mass_max_error']=float(np.max(np.abs(np.array(result['mass'])-mj['mass'])))
                out[label]['matlab_bias_gravity_max_error']=float(np.max(np.abs(np.array(result['bias'])-result['gravity']-mj['bias_gravity'])))
            # Native saved Figure smoke-check without new dynamics or user window.
            folder=root/'saved/matlab_spatial'
            if folder.exists():
                tool.eng.set(0.,'DefaultFigureVisible','off',nargout=0); tool.eng.tf_view(str(folder.resolve()),nargout=0)
                tool.eng.exportgraphics(tool.eng.gcf(),str((root/'matlab_saved_figure.png').resolve()),nargout=0)
                tool.eng.close('all',nargout=0); out['matlab_saved_figure']='native Figure exported from saved states; zero solve'
        finally: tool.close()
    atomic_json(root/('static_checks_matlab.json' if matlab else 'static_checks.json'),out); return out


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('root',type=Path); parser.add_argument('--matlab',action='store_true'); args=parser.parse_args()
    print(json.dumps(checks(args.root,args.matlab),indent=2))
