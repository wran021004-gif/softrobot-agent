"""Matched static rod/cell diagnostics. No optimizer, physical stepping or fitting."""
import argparse
from copy import deepcopy
import hashlib
from pathlib import Path
import subprocess
import time

import numpy as np
from scipy.spatial.transform import Rotation
from tools.state_io import read, digest
from sorosim_s35_probe import ROOT, RAW, save
from extensions.tendon_family.compiler import rx
from extensions.tendon_family.contracts import Design, ResolvedGVSBasis
from extensions.tendon_family.gvs import _Kinematics, _topology
from extensions.tendon_family.gvs_projection import discretization_jacobian
from extensions.tendon_family.sorosim_session import SorosimSession
from extensions.tendon_family.pcc import segment_pose_at

BATCH=ROOT/'evidence/sorosim_s35/attempt02'


def samples(spec):
    result=[]
    for k,link in enumerate(spec['links'],1):
        for s in link.get('nodes',[0.]):
            result.append(dict(link=k,s=s,offset=[0.,0.,0.],rotation=np.eye(3).tolist(),
                label=f"{link['id']}:{s:.12g}",kind='centerline' if 'nodes' in link else 'rigid_origin'))
    for route in spec['routes']:
        for j,p in enumerate(route['points']):
            result.append(dict({k:v for k,v in p.items() if k!='role'},label=f"{route['id']}:{j}",kind=p['role']))
    result.append(dict(spec['tip'],label='tip',kind='tip'))
    return result


def cell_attachment(physics,spec,a):
    """Diagnostic reading of compiler.attach convention; never emits a robot."""
    if a['link']==0:return -1,np.array(a['offset']),np.array(a['rotation'])
    link=spec['links'][a['link']-1]; bodies=physics['entity_map'][link['id']]['bodies']
    if link['kind']=='flexible_segment':
        i=min(int(a['s']*len(bodies)),len(bodies)-1); b=bodies[i];part=physics['parts'][b]
        S=rx(-part['section_axis_rad'])
        return b,np.array([(a['s']*len(bodies)-i)*part['length_m'],0,0])+S@a['offset'],S@a['rotation']
    return bodies[0],np.array(a['offset']),np.array(a['rotation'])


def difference(a,b,unit):
    a,b=np.asarray(a),np.asarray(b);err=float(np.linalg.norm(a-b));scale=float(np.linalg.norm(a))
    return dict(absolute_norm=err,relative_norm=None if scale<1e-20 else err/scale,
                reference_norm=scale,units=unit)


def isolate(folder):
    """Controlled kinematic substitutions only, reusing persisted static results."""
    spec=read(RAW/'control_spec.json')['specification'];physics=read(RAW/'resolved_physics.json')
    basis=ResolvedGVSBasis.model_validate(spec['resolved_basis']);L=discretization_jacobian(physics,basis)
    results=[]
    for i,p in enumerate(read(BATCH/'physical.json')['probes']):
        angles=L@p['x'][:12];tips={}
        for mode in ('ordered_hinges_straight','exponential_rotation_straight','constant_curvature_arc'):
            ends={0:np.eye(4)}
            for k,link in enumerate(spec['links'],1):
                pose=ends[link['parent']]@np.array(link['connection'])
                if link['kind']=='flexible_segment':
                    for b in physics['entity_map'][link['id']]['bodies']:
                        cell=physics['parts'][b];ds=cell['length_m'];a,beta=angles[cell['dofs']]
                        S=rx(cell['section_axis_rad']);ky,kz=(S@np.array([0.,a,beta]))[1:]/ds
                        step=segment_pose_at(ds,ky,kz)
                        if mode=='exponential_rotation_straight':
                            step[:3,3]=step[:3,:3]@np.array([ds,0,0])
                        elif mode=='ordered_hinges_straight':
                            step[:3,:3]=S@Rotation.from_rotvec([0,a,0]).as_matrix()@Rotation.from_rotvec([0,0,beta]).as_matrix()@S.T
                            step[:3,3]=step[:3,:3]@np.array([ds,0,0])
                        pose=pose@step
                ends[k]=pose
            tip=spec['tip'];pose=ends[tip['link']]
            tips[mode]=(np.array(spec['mount_rotation'])@(pose[:3,3]+pose[:3,:3]@tip['offset'])+spec['mount_position']).tolist()
        saved=read(folder/f'comparison_{i}.json')['geometry'][-1]
        results.append(dict(time_s=p['original']['time_s'],x=p['x'],u=p['u'],tips=tips,
            physical_reconstruction_error_m=float(np.linalg.norm(np.array(tips['ordered_hinges_straight'])-saved['cell_position'])),
            hinge_order_change=difference(tips['ordered_hinges_straight'],tips['exponential_rotation_straight'],'m'),
            straight_to_arc_change=difference(tips['exponential_rotation_straight'],tips['constant_curvature_arc'],'m'),
            arc_to_rod_remaining=difference(saved['rod_position'],tips['constant_curvature_arc'],'m')))
    out=dict(candidate=read(ROOT/'evidence/sorosim_control/s1.json')['source']['candidate'],
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),results=results,
        interpretation='Sequential single-mechanism geometric substitutions; differences are path-dependent vectors, not additive causal shares of dynamic error.',
        units='m; q rad/m; qdot rad/(m*s); u N',new_matlab_operations=0,new_physical_steps=0)
    save(folder,'isolation',out)


def compare(point,rod,spec,physics,stations):
    import mujoco as mj
    model=mj.MjModel.from_xml_path(str(RAW/'robot.xml'));data=mj.MjData(model)
    jids=[model.joint(j).id for j in physics['dofs']];qi=model.jnt_qposadr[jids];vi=model.jnt_dofadr[jids]
    L=np.zeros((model.nv,12));L[vi]=discretization_jacobian(physics,ResolvedGVSBasis.model_validate(spec['resolved_basis']))
    q,v=np.array(point['x'][:12]),np.array(point['x'][12:]);data.qpos[qi]=(L@q)[vi];data.qvel=L@v
    aids=[model.actuator(t['entity']+'_direct_tension').id for t in physics['tendons']]
    data.ctrl[aids]=point['u'];data.time=point['original']['time_s'];mj.mj_forward(model,data)
    assert data.ncon==data.nefc==0
    R=np.array(spec['mount_rotation']);mount=np.array(spec['mount_position'])
    topology=_topology(Design.model_validate(read(RAW/'robot_description.json')['data']))
    gvs=[_Kinematics(topology,q,n,spec['resolved_basis']['specification']) for n in (200,400)]
    geometry=[]
    for a,f in zip(stations,rod['routing']['sample_frames']):
        b,offset,rotation=cell_attachment(physics,spec,a)
        bid=model.body('fixed_base' if b<0 else physics['parts'][b]['entity']).id
        rb=data.xmat[bid].reshape(3,3);pos=data.xpos[bid]+rb@offset;rot=rb@rotation
        jp=np.zeros((3,model.nv));jr=np.zeros_like(jp);mj.mj_jac(model,data,jp,jr,pos,bid)
        pose=np.array(f['pose']);J=np.array(f['jacobian']);rp=R@pose[:3,3]+mount;rj=np.vstack((R@J[:3],R@J[3:]))
        part='fixed_base' if a['link']==0 else spec['links'][a['link']-1]['id']
        refs=[]
        for kin in gvs:
            gp=kin.point_pose(part,a['s']);refs.append(R@(gp[:3,3]+gp[:3,:3]@a['offset'])+mount)
        geometry.append(dict(sample=a,rod_position=rp.tolist(),cell_position=pos.tolist(),
            rod_rotation=(R@pose[:3,:3]).tolist(),cell_rotation=rot.tolist(),
            rod_jacobian=rj.tolist(),cell_jacobian=(np.vstack((jr,jp))@L).tolist(),
            position=difference(rp,pos,'m'),orientation_rad=float(Rotation.from_matrix((R@pose[:3,:3]).T@rot).magnitude()),
            velocity=difference(rj[3:]@v,jp@L@v,'m/s'),
            jacobian=difference(rj,np.vstack((jr,jp))@L,'angular:m; linear:m^2'),
            rod_gvs_position_m=float(np.linalg.norm(rp-refs[1])),
            gvs_refinement_m=float(np.linalg.norm(refs[0]-refs[1]))))
    # Independently check diagnostic attachment mapping against actual compiled sites.
    compiled_sites=[*[(f"{t['entity']}_point_{j}",t['points'][j]) for t in physics['tendons'] for j in range(len(t['points']))],
        ('tip_site',physics['tip'])]
    route_rows=[g for g in geometry if g['sample']['kind'] not in ('centerline','rigid_origin')]
    site_error=max(np.linalg.norm(np.array(g['cell_position'])-data.site_xpos[model.site(name).id])
                   for g,(name,_) in zip(route_rows,compiled_sites))
    M=np.empty((model.nv,model.nv));mj.mj_fullM(model,data,M);Mg=L.T@M@L
    # One term at a time, same q: zero rate separates gravity and velocity bias.
    zero=mj.MjData(model);zero.qpos[:]=data.qpos;zero.ctrl[:]=data.ctrl;mj.mj_forward(model,zero)
    gravity=-L.T@zero.qfrc_bias;elastic=-L.T@zero.qfrc_passive
    viscous=-L.T@(data.qfrc_passive-zero.qfrc_passive);bias=L.T@(data.qfrc_bias-zero.qfrc_bias)
    tendon=L.T@data.qfrc_actuator;residual=bias+elastic+viscous-gravity-tendon
    cell=dict(mass_matrix=Mg,gravity_force=gravity,elastic_force=elastic,viscous_force=viscous,
              velocity_bias=bias,tendon_force=tendon,residual=residual)
    d=rod['dynamics'];mechanics={k:difference(d[k],value,'kg*m^4' if k=='mass_matrix' else 'N*m^2') for k,value in cell.items()}
    # Exact additive body kinetic energy. No mass or inertia is changed.
    terms=[]
    for link in spec['links']:
        mass=np.zeros((12,12));grav=np.zeros(12)
        for b in physics['entity_map'][link['id']]['bodies']:
            bid=model.body(physics['parts'][b]['entity']).id
            jp=np.zeros((3,model.nv));jr=np.zeros_like(jp);mj.mj_jacBodyCom(model,data,jp,jr,bid)
            jp,jr=jp@L,jr@L;ri=data.ximat[bid].reshape(3,3)
            mass+=model.body_mass[bid]*jp.T@jp+jr.T@ri@np.diag(model.body_inertia[bid])@ri.T@jr
            grav+=jp.T@(model.body_mass[bid]*model.opt.gravity)
        reference=next(t for t in rod['link_terms'] if t['link']==link['id'])
        terms.append(dict(link=link['id'],kind=link['kind'],cell_mass=mass.tolist(),cell_gravity=grav.tolist(),
            mass=difference(reference['mass'],mass,'kg*m^4'),gravity=difference(reference['gravity'],grav,'N*m^2')))
    checks=dict(compiled_site_error_m=float(site_error),
        rod_mass_decomposition=difference(d['mass_matrix'],sum(np.array(t['mass']) for t in rod['link_terms']),'kg*m^4'),
        cell_mass_decomposition=difference(Mg,sum(np.array(t['cell_mass']) for t in terms),'kg*m^4'),
        rod_gravity_decomposition=difference(d['gravity_force'],sum(np.array(t['gravity']) for t in rod['link_terms']),'N*m^2'),
        cell_gravity_decomposition=difference(gravity,sum(np.array(t['cell_gravity']) for t in terms),'N*m^2'))
    conditions=dict(rod=float(np.linalg.cond(d['mass_matrix'])),cell=float(np.linalg.cond(Mg)))
    # Report sensitivity of acceleration to conditioning, never call this an exact reduced backend.
    accelerations=dict(rod=np.linalg.solve(d['mass_matrix'],-np.array(d['residual'])).tolist(),
                      cell=np.linalg.solve(Mg,-residual).tolist(),mass_condition=conditions)
    return dict(geometry=geometry,mechanics=mechanics,cell={k:a.tolist() for k,a in cell.items()},
        link_terms=terms,checks=checks,accelerations=accelerations,mujoco_version=mj.__version__,
        limitation='Instantaneous constant-L pullback only; no equivalent nonlinear reduced cell dynamics or trajectory attribution.')


def run(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    spec=read(RAW/'control_spec.json')['specification'];physics=read(RAW/'resolved_physics.json')
    stations=samples(spec);points=read(BATCH/'physical.json')['probes']
    files=[Path(__file__),ROOT/'tests/research/sorosim_s35_probe.py',*ROOT.glob('matlab/sorosim_control/*.m'),*RAW.glob('*')]
    save(folder,'provenance',dict(stage='S3.6',operation='matched_geometry_mechanics',
        starting_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        candidate=read(ROOT/'evidence/sorosim_control/s1.json')['source']['candidate'],
        physics_identity=physics['identity'],design_identity=spec['design_identity'],model_identity=spec['identity'],
        coordinate_order=spec['coordinate_order'],tendon_order=spec['tendon_order'],
        convention=spec['convention'],sample_frame='world; angular rows then linear rows',
        units=spec['units'],samples=stations,source_sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()},
        budget=dict(scope='authorized S3.6 engineering diagnostic',mathematical_checkpoints=3,new_mujoco_replays=0,nmpc_solves=0),
        settings=dict(sorosim=spec['solver'],gvs_midpoint_steps=[200,400],physical_state_source='S3.5 attempt02/physical.json')))
    session=SorosimSession();started=time.perf_counter();last=None
    try:
        with session:
            construction=session.construct(spec)
            save(folder,'environment',dict(environment=session.environment,dependency=session.dependency,construction=construction))
            for i,p in enumerate(points):
                rod=session.evaluate('diagnose',dict(kind='geometry_mechanics',x=p['x'],u=p['u'],a=[0.]*12,samples=stations))
                save(folder,f'rod_{i}',dict(input=p,result=rod));last=f'rod_{i}.json'
                result=compare(p,rod,spec,physics,stations);save(folder,f'comparison_{i}',result);last=f'comparison_{i}.json'
                print(f'Checkpoint {i}: {len(stations)} frames and force decomposition persisted',flush=True)
    except BaseException as exc:
        save(folder,'failure',dict(status='incomplete',error_type=type(exc).__name__,error=str(exc),last_valid_result=last))
        raise
    finally:
        save(folder,'timings',dict(session=session.timings,total_s=time.perf_counter()-started))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('destination',type=Path)
    parser.add_argument('--isolate',action='store_true');args=parser.parse_args()
    isolate(args.destination) if args.isolate else run(args.destination)
