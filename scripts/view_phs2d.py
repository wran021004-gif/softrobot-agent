"""PHS saved-state animation; no mj_step. Space pause, R restart, L loop, +/- speed."""
import json
from pathlib import Path
import time

import mujoco
import numpy as np
from phs2d_io import (parser,locate,read,load_model,restore,states,point,centerline,
                     forbid_integration,require,write_png)


def playback_key(state,code):
    if code==32:state['paused']=not state['paused']
    if code in (82,114):state['restart']=True
    if code in (76,108):state['loop']=not state['loop']
    if code in (61,334):state['speed']=min(64.,state['speed']*2.)
    if code in (45,333):state['speed']=max(1/64,state['speed']/2.)


def decorate(scene, unloaded, current, tip_path, force_point, force, tip):
    def connector(a,b,width,color,kind=mujoco.mjtGeom.mjGEOM_LINE):
        if scene.ngeom >= scene.maxgeom: return
        geom=scene.geoms[scene.ngeom];scene.ngeom+=1
        mujoco.mjv_initGeom(geom,kind,np.zeros(3),np.zeros(3),np.eye(3).ravel(),np.asarray(color,dtype=np.float32))
        mujoco.mjv_connector(geom,kind,width,np.asarray(a),np.asarray(b))
    def sphere(position,color,label):
        if scene.ngeom >= scene.maxgeom: return
        geom=scene.geoms[scene.ngeom];scene.ngeom+=1
        mujoco.mjv_initGeom(geom,mujoco.mjtGeom.mjGEOM_SPHERE,np.array([.0025]*3),position,
                           np.eye(3).ravel(),np.asarray(color,dtype=np.float32))
        geom.label=label
    for path,color,width in [(unloaded,[.35,.55,1.,1.],2),(current,[.1,.8,.35,1.],2),
                              (tip_path,[1.,.55,.0,1.],3)]:
        stride=max(1,len(path)//250)
        sampled=path[::stride]
        if len(sampled) and not np.array_equal(sampled[-1],path[-1]):sampled=np.vstack([sampled,path[-1]])
        for a,b in zip(sampled[:-1],sampled[1:]):connector(a,b,width,color)
    sphere(force_point,[1.,.25,.1,1.],'F')
    sphere(tip,[1.,.6,.0,1.],'Tip')
    if force:
        connector(force_point,force_point+np.array([.045*np.sign(force),0.,0.]),.002,
                  [1.,.2,.1,1.],mujoco.mjtGeom.mjGEOM_ARROW)


def main():
    forbid_integration()
    p=parser(__doc__)
    p.add_argument('--speed',type=float,default=1.)
    p.add_argument('--loop',action='store_true')
    p.add_argument('--check-states',action='store_true')
    p.add_argument('--check-only',action='store_true')
    p.add_argument('--render',type=Path)
    p.add_argument('--frame-time',type=float,default=4.)
    p.add_argument('--smoke-seconds',type=float)
    args=p.parse_args()
    require(args.speed>0,'POSITIVE_PLAYBACK_SPEED_REQUIRED')
    base,folder,entry=locate(args)
    model=load_model(base/'robot.xml');data=mujoco.MjData(model)
    physics=read(base/'structure.json')['physics']
    saved=states(folder/'states_timestep.npz');rows=saved['trajectory']
    with np.load(base/'equilibrium/states_timestep.npz',allow_pickle=False) as archive:
        unloaded_row=archive['trajectory'][-1].copy()
    restore(model,data,unloaded_row)
    unloaded=centerline(model,data,physics)
    if args.check_states:
        maximum=0.
        for index,row in enumerate(rows):
            restore(model,data,row)
            sid=model.site('tip_site').id
            maximum=max(maximum,float(np.max(abs(data.site_xpos[sid]-saved['tip_position_m'][index]))),
                        float(np.max(abs(data.site_xmat[sid].reshape(3,3)-saved['tip_rotation'][index]))))
        require(maximum<=1e-12,'FORWARD_POSE_INCONSISTENT')
        print(json.dumps(dict(condition=entry['condition'],saved_state_rows=len(rows),
                             maximum_pose_error=maximum,physics_steps=0)),flush=True)
    if args.check_only:
        print(json.dumps(dict(nq=model.nq,nv=model.nv,ntendon=model.ntendon,nu=model.nu,
                             loaded_rows=len(rows),physics_steps=0)),flush=True)
        return
    camera=mujoco.MjvCamera();mujoco.mjv_defaultCamera(camera)
    camera.lookat[:]=[0.,0.,.30];camera.distance=.66;camera.azimuth=115;camera.elevation=-12
    option=mujoco.MjvOption();option.flags[mujoco.mjtVisFlag.mjVIS_TENDON]=True
    def show(scene,index):
        decorate(scene,unloaded,centerline(model,data,physics),saved['tip_position_m'][:index+1],
                 saved['force_point_m'][index],rows[index,1],saved['tip_position_m'][index])
    if args.render:
        index=min(len(rows)-1,max(0,int(np.searchsorted(rows[:,0],args.frame_time,side='left'))))
        restore(model,data,rows[index])
        with mujoco.Renderer(model,height=480,width=640) as renderer:
            renderer.update_scene(data,camera=camera,scene_option=option)
            show(renderer.scene,index)
            rgb=renderer.render()
        write_png(args.render,rgb)
        print(json.dumps(dict(rendered_saved_frame=index,time_s=float(rows[index,0]),physics_steps=0)),flush=True)
        return
    if args.check_states:return
    from mujoco import viewer as mj_viewer
    state=dict(paused=False,loop=args.loop,restart=False,speed=args.speed)
    def key(code):playback_key(state,code)
    cursor=0.;previous=time.perf_counter();started=previous;frames=0
    print('Saved states only. Space pause/resume; R restart; L loop; +/- speed. Blue unloaded, green current, orange Tip trail.',flush=True)
    with mj_viewer.launch_passive(model,data,key_callback=key) as viewer:
        viewer.cam.lookat[:]=camera.lookat;viewer.cam.distance=camera.distance
        viewer.cam.azimuth=camera.azimuth;viewer.cam.elevation=camera.elevation
        viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_TENDON]=True
        while viewer.is_running():
            now=time.perf_counter();elapsed=now-previous;previous=now
            if args.smoke_seconds is not None and now-started>=args.smoke_seconds:break
            if state['restart']:cursor=0.;state['restart']=False
            if not state['paused']:cursor+=elapsed*state['speed']
            if state['loop']:cursor%=rows[-1,0]
            index=min(len(rows)-1,max(0,int(np.searchsorted(rows[:,0],cursor,side='right')-1)))
            with viewer.lock():
                restore(model,data,rows[index]);viewer.user_scn.ngeom=0;show(viewer.user_scn,index)
            viewer.sync();frames+=1;time.sleep(.01)
    print(json.dumps(dict(gui_frames=frames,physics_steps=0)),flush=True)


if __name__=='__main__':main()
