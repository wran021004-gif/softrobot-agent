"""Display saved states only; space pauses, R restarts, L toggles looping."""
import json
import time
from pathlib import Path

import mujoco
import numpy as np
from package_io import parser,locate,csv_read,restore


def decorate(scene, positions, reference, current, axis):
    def line(a,b,width,color,kind=mujoco.mjtGeom.mjGEOM_LINE):
        if scene.ngeom>=scene.maxgeom:return
        geom=scene.geoms[scene.ngeom];scene.ngeom+=1
        mujoco.mjv_initGeom(geom,kind,np.zeros(3),np.zeros(3),np.eye(3).ravel(),np.asarray(color,dtype=np.float32))
        mujoco.mjv_connector(geom,kind,width,np.asarray(a),np.asarray(b))
    if len(reference) and scene.ngeom<scene.maxgeom:
        geom=scene.geoms[scene.ngeom];scene.ngeom+=1
        mujoco.mjv_initGeom(geom,mujoco.mjtGeom.mjGEOM_SPHERE,np.array([.004]*3),reference[-1],
            np.eye(3).ravel(),np.array([1.,.6,0,1],dtype=np.float32))
    for path,color in [(reference,[1.,.6,0,1]),(positions,[0,.8,.4,1])]:
        stride=max(1,len(path)//350)
        points=path[::stride]
        if len(points) and not np.array_equal(points[-1],path[-1]):points=np.vstack([points,path[-1]])
        for a,b in zip(points[:-1],points[1:]):line(a,b,2,color)
    line(current,current+.035*axis,.002,[.2,.3,1,1],mujoco.mjtGeom.mjGEOM_ARROW)


def main():
    p=parser(__doc__);p.add_argument('--speed',type=float,default=1.)
    p.add_argument('--loop',action='store_true');p.add_argument('--check-states',action='store_true')
    p.add_argument('--render',type=Path);p.add_argument('--smoke-seconds',type=float)
    args=p.parse_args()
    if args.speed<=0:p.error('--speed must be positive')
    root,folder,entry,task,mapping,model=locate(args);data=mujoco.MjData(model)
    try:model.site_rgba[model.site('task_target').id,3]=0
    except KeyError:pass
    rows=csv_read(folder/'trajectory_timestep.csv');ref=csv_read(folder/'reference.csv')
    positions=np.array([[r['tip_position_m_'+a] for a in 'xyz'] for r in rows])
    reference=np.array([[r['reference_position_m_'+a] for a in 'xyz'] for r in ref])
    if args.check_states:
        maximum=0.
        for row,expected in zip(rows,positions):
            restore(model,data,row,mapping)
            maximum=max(maximum,float(np.max(np.abs(data.site_xpos[model.site('tip_site').id]-expected))))
            rotation=np.array([[row[f'tip_rotation_r{i}{j}'] for j in range(3)] for i in range(3)])
            maximum=max(maximum,float(np.max(np.abs(data.site_xmat[model.site('tip_site').id].reshape(3,3)-rotation))))
        print(json.dumps(dict(rows=len(rows),maximum_pose_error=maximum,physics_steps=0)))
        if maximum>1e-12:raise ValueError('SAVED_POSE_INCONSISTENT_WITH_QPOS')
        if not args.render:return
    camera=mujoco.MjvCamera();mujoco.mjv_defaultCamera(camera)
    camera.lookat[:]=[.15,0,.15];camera.distance=.65;camera.azimuth=135;camera.elevation=-25
    if args.render:
        import struct,zlib
        row=rows[-1];restore(model,data,row,mapping)
        with mujoco.Renderer(model,height=480,width=640) as renderer:
            renderer.update_scene(data,camera=camera)
            decorate(renderer.scene,positions,reference,positions[-1],np.array([row['tool_axis_world_'+a] for a in 'xyz']))
            rgb=renderer.render()
        def chunk(kind,body):return struct.pack('!I',len(body))+kind+body+struct.pack('!I',zlib.crc32(kind+body)&0xffffffff)
        png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',rgb.shape[1],rgb.shape[0],8,2,0,0,0))
        png+=chunk(b'IDAT',zlib.compress(b''.join(b'\0'+r.tobytes() for r in rgb)))+chunk(b'IEND',b'')
        args.render.write_bytes(png);return
    from mujoco import viewer as mj_viewer
    state=dict(paused=False,loop=args.loop,restart=False)
    def key(code):
        if code==32:state['paused']=not state['paused']
        if code in (82,114):state['restart']=True
        if code in (76,108):state['loop']=not state['loop']
    print('Saved-state playback; Space pause/resume, R restart, L loop. Green actual, orange reference, blue tool +X.')
    cursor=0.;previous=time.perf_counter();started=previous
    with mj_viewer.launch_passive(model,data,key_callback=key) as viewer:
        viewer.cam.lookat[:]=camera.lookat;viewer.cam.distance=camera.distance
        viewer.cam.azimuth=camera.azimuth;viewer.cam.elevation=camera.elevation
        while viewer.is_running():
            now=time.perf_counter();elapsed=now-previous;previous=now
            if args.smoke_seconds is not None and now-started>=args.smoke_seconds:break
            if state['restart']:cursor=0.;state['restart']=False
            if not state['paused']:cursor+=elapsed*args.speed
            if state['loop']:cursor%=rows[-1]['time_s']
            index=min(len(rows)-1,int(cursor/model.opt.timestep));row=rows[index]
            restore(model,data,row,mapping)
            with viewer.lock():
                viewer.user_scn.ngeom=0
                decorate(viewer.user_scn,positions[:index+1],reference,positions[index],
                    np.array([row['tool_axis_world_'+a] for a in 'xyz']))
            viewer.sync();time.sleep(.01)


if __name__=='__main__':main()
