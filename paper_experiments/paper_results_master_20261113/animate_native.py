"""Record archived states using MuJoCo only; Pillow is used only as a GIF encoder."""
from pathlib import Path
import json,sys,math,argparse
import numpy as np
import mujoco
from PIL import Image
O=Path(__file__).resolve().parent;sys.path.insert(0,str(O))
from render_full import model,png,read,save
AD=O/'ANIMATIONS_MUJOCO';AD.mkdir(exist_ok=True)
LABELS={'T01':'T01','T02':'M2','T03':'T03','T04':'tracking','T05':'T05','T06':'T06','T07':'T07','T08':'P3','T09':'T09_guides','T10':'T10','PHS-2D':'PHS2D'}
TITLES={'T01':'Reach and hold','T02':'Loaded reach and hold','T03':'Fast reach, then terminal hold','T04':'Two-cycle figure-eight tracking','T05':'Position and directed tool axis','T06':'Loaded timed position-axis scan','T07':'Four-tendon shared structure: M1_A','T08':'Passive progressive stiffness: +X','T09':'Spring button: approach, press, hold, release','T10':'Feedback recovery from +Y impulse','PHS-2D':'Passive force-point compliance and Tip suppression'}
screens=read(O/'FIGURES_MUJOCO/SCREENSHOT_SOURCES.json');bindings=read(O/'SOURCE_DATA/MODEL_BINDINGS.json');tasks={t['task_id']:t for t in read(O/'SOURCE_DATA/FULL_TASKS.json')}
def add_geom(scene,typ,pos,size,color):
    g=scene.geoms[scene.ngeom];mujoco.mjv_initGeom(g,typ,np.asarray(size,dtype=float),np.asarray(pos,dtype=float),np.eye(3).ravel(),np.asarray(color,dtype=np.float32));g.category=int(mujoco.mjtCatBit.mjCAT_DECOR);scene.ngeom+=1;return g
def line(scene,a,b,r=.00035,color=(.33,.38,.40,1),arrow=False):
    if np.linalg.norm(np.array(b)-a)<1e-10:return
    typ=mujoco.mjtGeom.mjGEOM_ARROW if arrow else mujoco.mjtGeom.mjGEOM_CAPSULE
    g=add_geom(scene,typ,[0,0,0],[r,r,r],color);mujoco.mjv_connector(g,typ,r,np.array(a,dtype=float),np.array(b,dtype=float))
def sphere(scene,p,r=.002,color=(.20,.25,.27,1)):add_geom(scene,mujoco.mjtGeom.mjGEOM_SPHERE,p,[r,r,r],color)
def material_point(m,d,tid,s):
    lengths=tasks[tid]['structure_type']['lengths_m'];wanted=sum(lengths)*s
    for i,L in enumerate(lengths):
        if wanted<=L+1e-12:
            ns=sum(m.body(j).name.startswith(f'segment_{i}_cell_') for j in range(m.nbody));cell=min(int(wanted/(L/ns)),ns-1);bid=m.body(f'segment_{i}_cell_{cell}').id
            return d.xpos[bid]+d.xmat[bid].reshape(3,3)@np.array([wanted-cell*L/ns,0,0])
        wanted-=L
    raise ValueError('material coordinate')
def force_from_program(program,t):
    for a in program:
        if a['start_s']<=t<=a['end_s']:
            u=np.clip((t-a['start_s'])/(a['ramp_until_s']-a['start_s']),0,1);u=u*u*(3-2*u)
            return (1-u)*np.array(a['force_start_world_n'])+u*np.array(a['force_end_world_n']),a['name']
    return np.zeros(3),'outside program'
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--only',nargs='*');args=parser.parse_args()
    tids=args.only or list(LABELS);manifest=read(AD/'ANIMATION_MANIFEST.json') if (AD/'ANIMATION_MANIFEST.json').exists() else []
    manifest=[r for r in manifest if r['task_id'] not in tids]
    for tid in tids:
        mo=read(O/'SOURCE_DATA/ANIMATION_INPUTS'/f'{tid}.json');label=LABELS[tid];screen=next(s for s in screens if s['label']==label and s['view']=='oblique');xp=O/'VISUAL_XML'/f'{label}_visual.xml';m=model(xp);d=mujoco.MjData(m)
        # Same visual XML and fixed camera family as the stills; additional room accommodates recorded motion and task cues.
        m.vis.global_.offwidth=1280;m.vis.global_.offheight=960;m.vis.headlight.ambient[:]=[.45]*3
        cam=mujoco.MjvCamera();cam.type=mujoco.mjtCamera.mjCAMERA_FREE;cam.orthographic=1;cam.lookat[:]=screen['camera']['lookat'];cam.azimuth=screen['camera']['azimuth'];cam.elevation=screen['camera']['elevation'];cam.distance=.8
        m.vis.global_.fovy=screen['camera']['vertical_span_m']*1.3
        if tid=='T04':m.vis.global_.fovy=max(m.vis.global_.fovy,.19)
        if tid in ['T08','PHS-2D']:m.vis.global_.fovy=.49
        b=bindings.get(tid,[{}])[0];task=read(O/'SOURCE_DATA'/f'{tid}_{b.get("condition_name")}_TASK.json') if tid in bindings else None
        gd=task['goal']['data'] if task else {};target=gd.get('target_m');path=gd.get('vertices_m',[]);axes=gd.get('axis_vertices_world',[])
        if tid=='T04':path=[a['target_position_m'] for a in read(O.parent/'five_task_completion_20261113/T04_figure_eight_tracking/T04_RUN_03/NATIVE_REFERENCE_BANK.json')['reference_bank']]
        robot_joints=[m.joint(i).name for i in range(m.njnt) if m.joint(i).name.startswith('segment_')]
        joint_names=mo.get('joint_names',robot_joints);q=np.asarray(mo['qpos']);assert q.shape[1]==len(joint_names),(tid,q.shape,len(joint_names))
        addresses=[int(m.joint(n).qposadr[0]) for n in joint_names]
        ts=np.asarray(mo['times_s']);stride=max(1,int(round(len(ts)/280))) if ts[-1]>5 else max(1,int(round(len(ts)/180)))
        selected=list(range(0,len(ts),stride))
        if selected[-1]!=len(ts)-1:selected.append(len(ts)-1)
        fps=12 if ts[-1]>5 else 20
        if tid in ['T01','T03','T05','T06','T07']:fps=10
        fd=AD/'FRAMES'/tid;fd.mkdir(parents=True,exist_ok=True);images=[];frame_index=[];renderer=mujoco.Renderer(m,height=960,width=1280,max_geom=12000)
        payload_id=m.body('payload').id if any(m.body(i).name=='payload' for i in range(m.nbody)) else None
        payload_mass=float(m.body_mass[payload_id])*1e3 if payload_id else None
        cue_source=[]
        for fi,i in enumerate(selected):
            t=float(ts[i]);d.qpos[:]=m.qpos0;d.qpos[addresses]=q[i]
            for joint,values in mo.get('environment_joints',{}).items():d.qpos[int(m.joint(joint).qposadr[0])]=values[i]
            d.time=t;mujoco.mj_fwdPosition(m,d);renderer.update_scene(d,camera=cam);scene=renderer.scene
            if target is not None:sphere(scene,target)
            for a,z in zip(path[:-1],path[1:]):line(scene,a,z)
            if gd.get('target_axis_world') is not None:line(scene,target,np.array(target)+.022*np.array(gd['target_axis_world']),r=.001,arrow=True)
            for a,axis in zip(path,axes):line(scene,a,np.array(a)+.017*np.array(axis),r=.0007,arrow=True)
            force=np.zeros(3);phase=''
            if tid=='T02':
                for f in task['environment']['data'].get('external_forces',[]):
                    if f['start_s']<=t<=f['end_s']:force+=np.array(f['force_n'])
                phase='hold / external load' if np.linalg.norm(force)>0 else 'reach / hold'
            elif tid=='T10':
                if .5<t<.55:force=np.array([0,.04*math.sin(math.pi*(t-.5)/.05),0])
                phase='impulse' if .5<=t<=.55 else 'recovery' if t>.55 else 'pre-impact hold'
            elif tid=='T08':force,phase=force_from_program(gd['programs']['plus_x'],t)
            elif tid=='PHS-2D':force=np.array(mo['force_n'][i]);phase=mo['stage'][i]
            if tid in ['T08','PHS-2D']:
                anchor=material_point(m,d,tid,.7);sphere(scene,anchor,.0035,(.17,.64,.37,1))
            else:anchor=d.xipos[payload_id].copy() if payload_id else None
            if anchor is not None and np.linalg.norm(force)>1e-10:
                # Visual force direction has a fixed display scale; it is not a deformed/fictitious rope.
                line(scene,anchor-force/np.linalg.norm(force)*.06,anchor,r=.0022,color=(.2,.25,.27,1),arrow=True)
            renderer.render()
            left=TITLES[tid]+'\nRecorded simulation time: %.3f s'%t
            if payload_mass is not None:left+='\nOriginal rigid payload: %.4g g'%payload_mass
            if target is not None:left+='\nDark sphere: target position'
            if path:left+='\nDark path: stored reference'+(' nodes' if tid=='T04' else '')
            if axes or gd.get('target_axis_world'):left+='\nDark arrow at target: required tool axis'
            if phase:left+='\nPhase: '+phase
            if tid in ['T02','T08','T10','PHS-2D']:left+='\nApplied-load cue: [%.3g, %.3g, %.3g] N'%tuple(force)
            if tid in ['T08','PHS-2D']:left+='\nGreen point: loaded material coordinate s=0.7'
            if tid=='T09':left+='\nButton depth: %.3f mm; contact: %.3g N'%(mo['environment_joints']['button_slide'][i]*1e3,mo['contact_force_n'][i])
            left+='\nArchived states; no new physics integration'
            mujoco.mjr_overlay(mujoco.mjtFont.mjFONT_NORMAL,mujoco.mjtGridPos.mjGRID_TOPLEFT,renderer._rect,left,'',renderer._mjr_context)
            pixels=np.empty((960,1280,3),dtype=np.uint8);mujoco.mjr_readPixels(pixels,None,renderer._rect,renderer._mjr_context);pixels=np.flipud(pixels).copy()
            fp=fd/f'{fi:05}.png';png(fp,pixels)
            # GIF container encoding only: no drawing, compositing, cropping or geometric image manipulation.
            images.append(Image.fromarray(pixels));frame_index.append(dict(frame=fi,source_index=i,time_s=t,png=str(fp)))
        renderer.close();gif=AD/f'anim_{tid}_{mo["condition"]}.gif'
        images[0].save(gif,save_all=True,append_images=images[1:],duration=int(round(1000/fps)),loop=0,optimize=False,disposal=2)
        for im in images:im.close()
        save(fd/'FRAME_INDEX.json',frame_index)
        manifest.append(dict(task_id=tid,condition=mo['condition'],animation=str(gif),renderer='MuJoCo 3.13.0 native Renderer + native mjr_overlay',encoding='GIF container only via Pillow; original native RGB PNG frames retained',
            visual_xml=str(xp),original_physical_xml=screen.get('original_physical_xml',screen['source_xml']),motion_source=mo['source'],motion_input=str(O/'SOURCE_DATA/ANIMATION_INPUTS'/f'{tid}.json'),frame_index=str(fd/'FRAME_INDEX.json'),
            simulated_time_range_s=[float(ts[0]),float(ts[-1])],frames=len(selected),playback_fps=fps,nominal_playback_duration_s=len(selected)/fps,state_selection='nearest existing sampled rows; no pose interpolation',resolution=[1280,960],
            camera=dict(screen['camera'],vertical_span_m=float(m.vis.global_.fovy)),task_cues='MuJoCo native geometry and text: original goal/reference/axis; original applied-load direction; original payload; T09 recorded button joint',
            original_payload_mass_g=payload_mass,physical_integration_performed=False,visual_additions='same zero-mass mounting datum, anchor plates and junction sheath as structure stills'))
        save(AD/'ANIMATION_MANIFEST.json',manifest);print('NATIVE ANIMATION',tid,len(selected),'frames',flush=True)
if __name__=='__main__':main()
