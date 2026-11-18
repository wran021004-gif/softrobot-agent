"""Native MuJoCo stills and shadowed, text-free task videos from archived states.

No integration, optimization, control execution, or new physical evaluation.
"""
from pathlib import Path
import argparse,concurrent.futures,threading,json,csv,math,os,struct,zlib,subprocess,copy
import numpy as np
import mujoco
from extract_render_inputs import O,ROOT,read,save,csvout,native

FFMPEG=Path('D:/Program Files (x86)/英雄联盟(26)/Cross/icreate/recorder-release/ffmpeg.exe')
FFPROBE=FFMPEG.with_name('ffprobe.exe')
PALETTE=dict(shell='#99D8C9',distal='#2CA25F',connector='#536166',guide='#E5F5F9',tendon='#303C3E',target='#557663',actual='#26384B',force='#A35D55',reference='#70849A')
W,H=1600,1200
def rgba(s,a=1):return ' '.join(str(v) for v in [*[int(s[k:k+2],16)/255 for k in [1,3,5]],a])
def rgb(s,a=1):return np.array([*[int(s[k:k+2],16)/255 for k in [1,3,5]],a],np.float32)
def fmt(x):return ' '.join(format(float(v),'.17g') for v in np.asarray(x).ravel())
def load_model(path):
    f=concurrent.futures.Future();threading.stack_size(8*1024*1024)
    def worker():
        try:f.set_result(mujoco.MjModel.from_xml_path(native(path)))
        except BaseException as e:f.set_exception(e)
    t=threading.Thread(target=worker);t.start();t.join();return f.result()
def png(path,pixels):
    h,w,_=pixels.shape
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    raw=b''.join(b'\0'+pixels[i].tobytes() for i in range(h))
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,6))+chunk(b'IEND',b''))
def compare_physics(a,b):
    keys=['body_mass','body_inertia','body_ipos','body_iquat','body_pos','body_quat','jnt_stiffness','dof_damping','dof_armature','jnt_axis','jnt_pos','jnt_range','jnt_limited','tendon_range','tendon_solref_lim','tendon_solimp_lim','wrap_type','wrap_objid','site_pos','site_bodyid','eq_data','pair_friction','qpos0','qpos_spring']
    checks={k:bool(np.array_equal(getattr(a,k),getattr(b,k))) for k in keys if hasattr(a,k)}
    checks.update({k:getattr(a,k)==getattr(b,k) for k in ['nq','nv','njnt','nbody','ntendon','nsite','nu','neq','npair','nexclude']})
    for i in range(a.ngeom):
        name=a.geom(i).name
        if not name:continue
        gi=b.geom(name).id
        for k in ['geom_contype','geom_conaffinity','geom_size','geom_pos','geom_quat','geom_friction','geom_solref','geom_solimp','geom_type','geom_bodyid','geom_margin','geom_gap']:
            checks[name+':'+k]=bool(np.array_equal(getattr(a,k)[i],getattr(b,k)[gi]))
    checks['options']=all(np.array_equal(getattr(a.opt,k),getattr(b.opt,k)) for k in ['timestep','integrator','gravity','iterations','tolerance'])
    assert all(checks.values()),[k for k,v in checks.items() if not v]
    return dict(passed=True,checked_items=len(checks),method='compile-time selected physical arrays and original geometry/contact attributes; no stepping')
def visual_xml(source,outfile):
    import xml.etree.ElementTree as E
    original=load_model(source);root=E.fromstring(Path(native(source)).read_bytes());notes=[];template=None;tid=Path(outfile).parent.parent.name
    prior=ROOT/'paper_experiments/paper_results_master_20261113/VISUAL_XML'
    label={'T01':'T01','T02':'M2','T03':'T03','T04':'tracking','T05':'T05','T06':'T06','T07':'T07','T08':'P3','T09':'T09_guides','T10':'T10'}.get(tid)
    templates=[prior/f'{label}_visual.xml'] if label else [prior/f'{n}_visual.xml' for n in ['PHS2D','PHS2D_F3','PHS2D_F0']]
    for p in templates:
        if not p.exists():continue
        try:
            candidate_model=load_model(p);compare_physics(original,candidate_model)
        except (AssertionError,ValueError,KeyError):continue
        root=E.fromstring(p.read_bytes());template=str(p);notes.append('Reuses the previously completed visual XML including guide plates, terminal anchor plates, rigid-junction sheath and mount. This pass changes lighting/ground/background only; dynamics checked against this exact candidate original XML.');break
    world=root.find('worldbody');assets=root.find('asset')
    if assets is None:assets=E.SubElement(root,'asset')
    # Preserve the already completed appearance. For intermediate candidates with
    # different geometry, transfer the same prior visual rules to their true frames.
    for geom in root.findall('.//geom'):
        name=geom.get('name','');body_color=PALETTE['shell']
        if template is not None:
            if geom.get('type')=='plane':geom.set('rgba','.96 .97 .98 1')
            continue
        if 'cell_' in name:
            try:body_color=PALETTE['shell'] if int(name.split('_')[1])==0 else PALETTE['distal']
            except:pass
            geom.set('rgba',rgba(body_color))
        elif 'guide' in name or 'spoke' in name or 'annulus' in name or '_eye' in name:geom.set('rgba',rgba(PALETTE['guide']))
        elif 'button_cap' in name:geom.set('rgba',rgba(PALETTE['force']))
        elif any(s in name for s in ['connector','payload','tool','housing','mount_plate','button_rod']):geom.set('rgba',rgba(PALETTE['connector']))
        elif geom.get('type')=='plane':geom.set('rgba','.96 .97 .98 1')
        # Make copied file assets portable without touching source files.
    for mesh in assets.findall('mesh'):
        if mesh.get('file'):
            p=Path(template or source).parent/mesh.get('file');mesh.set('file',str(p.resolve()))
    for tendon in root.findall('./tendon/spatial'):
        tendon.set('rgba',rgba(PALETTE['tendon']));tendon.set('width','.0006')
    for site in root.findall('.//site'):
        if site.get('name'):
            site.set('rgba',rgba(PALETTE['tendon'] if site.get('name').startswith('tendon_') else PALETTE['target']))
    if template is None:
        reuse_prior_visual_rules(root,original,E)
        notes.append('Intermediate geometry differs from final template: reused prior render_full.py component rules at this candidate own terminal sites, true junction gap, and fixed_base. Prior schematic anchor/sheath appearance, not new hardware.')
    base=next((b for b in root.findall('.//body') if b.get('name')=='fixed_base'),None)
    if base is not None and not any(g.get('name')=='master_mount_reference_datum' for g in base.findall('geom')):
        starts=[s for s in base.findall('site') if s.get('name','').startswith('tendon_')]
        points=np.array([[float(v) for v in s.get('pos','0 0 0').split()] for s in starts]) if starts else np.array([[0,.02,.02]])
        ext=np.maximum(abs(points[:,1:]).max(0)+.002,.017)
        E.SubElement(base,'geom',name='paper_mount_reference',type='box',pos=fmt([min(points[:,0])-.002,0,0]),size=fmt([.002,*ext]),mass='0',contype='0',conaffinity='0',rgba='.46 .53 .58 .65')
        notes.append('Zero-mass slab marks the true fixed_base frame; physical base envelope unavailable. No new mechanical mount is claimed.')
    planes=root.findall('./worldbody/geom');ground=next((g for g in planes if g.get('type')=='plane' and float(g.get('pos','0 0 0').split()[2])>-1),None)
    if ground is None:
        E.SubElement(world,'geom',name='paper_visual_ground_reference',type='plane',pos='0 0 0',size='2 2 .01',mass='0',contype='0',conaffinity='0',rgba='.96 .97 .98 1')
        ground_z=0.;notes.append('Visual-only ground datum at world z=0 for shadows; original remote physical ground remains unchanged.')
    else:ground_z=float(ground.get('pos','0 0 0').split()[2])
    for light in list(world.findall('light')):world.remove(light)
    # Exact shadow-bearing PHS F3 light family, not the later shadow-free master theme.
    E.SubElement(world,'light',name='paper_key',pos='.35 -.45 .85',dir='-.4 .5 -.7',diffuse='.8 .8 .8',specular='.22 .22 .22',castshadow='true')
    E.SubElement(world,'light',name='paper_fill',pos='-.3 .25 .6',dir='.4 -.2 -.5',diffuse='.5 .5 .5',specular='.1 .1 .1',castshadow='false')
    vis=root.find('visual')
    if vis is None:vis=E.SubElement(root,'visual')
    for child in list(vis):vis.remove(child)
    E.SubElement(vis,'global',offwidth=str(W),offheight=str(H),orthographic='true',fovy='.4')
    E.SubElement(vis,'quality',shadowsize='4096',offsamples='4')
    E.SubElement(vis,'headlight',ambient='.35 .35 .35',diffuse='.45 .45 .45',specular='.1 .1 .1')
    E.SubElement(vis,'rgba',haze='.98 .985 .99 1');E.SubElement(vis,'map',znear='.001',zfar='8')
    for sky in list(assets.findall('texture')):
        if sky.get('type')=='skybox':assets.remove(sky)
    E.SubElement(assets,'texture',name='paper_flat_sky',type='skybox',builtin='flat',rgb1='.98 .985 .99',rgb2='.98 .985 .99',width='64',height='64')
    E.indent(root,space='  ');Path(outfile).parent.mkdir(parents=True,exist_ok=True);E.ElementTree(root).write(outfile,encoding='utf-8',xml_declaration=True)
    model=load_model(outfile);check=compare_physics(original,model)
    save(Path(outfile).with_suffix('.check.json'),dict(source_xml=source,prior_visual_template=template,prior_visual_rules=str(prior.parent/'render_full.py'),visual_xml=str(outfile),validation=check,notes=notes,ground_z=ground_z))
    return model,ground_z

def reuse_prior_visual_rules(root,original,E):
    """Same saved master appearance rules; coordinates from this original model."""
    bodies={b.get('name'):b for b in root.findall('.//body')};owners={s.get('name'):(b,s) for b in bodies.values() for s in b.findall('site')};groups={}
    base=bodies.get('fixed_base')
    if base is not None:
        anchors=[s for s in base.findall('site') if s.get('name','').startswith('tendon_')];xyz=np.array([[float(v) for v in s.get('pos').split()] for s in anchors]) if anchors else np.array([[0,.02,.02]]);extent=np.maximum(abs(xyz[:,1:]).max(0)+.003,.022)
        E.SubElement(base,'geom',name='master_mount_reference_datum',type='box',pos=fmt([xyz[:,0].min()-.004,0,0]),size=fmt([.004,*extent]),mass='0',contype='0',conaffinity='0',rgba=rgba(PALETTE['connector']))
    for tendon in root.findall('./tendon/spatial'):
        end=tendon.findall('site')[-1].get('site');owner,site=owners[end];p=np.array([float(v) for v in site.get('pos','0 0 0').split()]);groups.setdefault((owner.get('name'),round(float(p[0]),9)),[]).append(p)
    for n,((owner,x),points) in enumerate(groups.items()):
        points=np.array(points);center=(points.min(0)+points.max(0))/2;half=(points.max(0)-points.min(0))/2;center[0]=x+.0015;half[0]=.0015;half[1:]=np.maximum(half[1:]+.002,.007)
        E.SubElement(bodies[owner],'geom',name=f'master_anchor_reference_{n}',type='box',pos=fmt(center),size=fmt(half),mass='0',contype='0',conaffinity='0',rgba=rgba(PALETTE['connector']))
    data=mujoco.MjData(original);mujoco.mj_fwdPosition(original,data);assets={m.get('name'):m for m in root.findall('./asset/mesh')}
    for name,body in bodies.items():
        if not name.startswith('connector_'):continue
        try:
            i=int(name.split('_')[1]);nextbody=bodies[f'segment_{i}_cell_0'];bid=original.body(name).id;gid=original.body(f'guide_{i}').id;nid=original.body(f'segment_{i}_cell_0').id
        except (ValueError,KeyError):continue
        R=data.xmat[bid].reshape(3,3);start=R.T@(data.xpos[gid]-data.xpos[bid]);end=R.T@(data.xpos[nid]-data.xpos[bid]);geom=nextbody.find('geom');radius=.003
        if geom is not None and geom.get('mesh') in assets:
            verts=np.array([float(v) for v in assets[geom.get('mesh')].get('vertex').split()]).reshape(-1,3);radius=min(np.ptp(verts[:,1]),np.ptp(verts[:,2]))/2
        E.SubElement(body,'geom',name=f'master_junction_sheath_{i}',type='capsule',fromto=fmt([*start,*end]),size=str(radius),mass='0',contype='0',conaffinity='0',rgba=rgba(PALETTE['shell']))
def assign(model,data,q,names=None):
    data.qpos[:]=model.qpos0
    if names:
        assert len(q)==len(names)
        for name,val in zip(names,q):data.qpos[int(model.joint(name).qposadr[0])]=val
    else:
        assert len(q)==model.nq,(len(q),model.nq);data.qpos[:]=q
    mujoco.mj_fwdPosition(model,data)
def camera(spec,view='oblique'):
    c=mujoco.MjvCamera();c.type=mujoco.mjtCamera.mjCAMERA_FREE;c.orthographic=1;c.distance=.8;c.lookat[:]=spec['lookat'];c.azimuth=spec['azimuth'];c.elevation=spec['elevation']
    if view=='side':c.azimuth=90;c.elevation=0
    if view=='front':c.azimuth=0;c.elevation=0
    return c
def fit_camera(models_and_states,ground,tid):
    if tid=='PHS-2D':return dict(lookat=[0,0,.318],azimuth=135,elevation=-18,vertical_span_m=.47,distance=.8,orthographic=True,rule='unchanged PHS F3 reference camera and scale')
    points=[]
    for model,states in models_and_states:
        d=mujoco.MjData(model);poses=[(model.qpos0,None)]+[(s['qpos'],s.get('joint_names')) for s in states]
        for q,names in poses:
            assign(model,d,q,names)
            for i in range(model.ngeom):
                if model.geom_type[i]==mujoco.mjtGeom.mjGEOM_PLANE:continue
                p=d.geom_xpos[i];radius=min(float(model.geom_rbound[i]),.055);points.extend([p-radius,p+radius])
    points=np.array(points);lo=points.min(0);hi=points.max(0);lo[2]=min(lo[2],ground)
    # Fit real robot motion and a nearby ground/shadow reference, once per task, never per candidate.
    lo[1]-=.035;hi[1]+=.035;center=(lo+hi)/2
    az,el=120.,-22.;ar,er=np.deg2rad([az,el]);right=np.array([-math.sin(ar),math.cos(ar),0]);toward=np.array([math.cos(ar)*math.cos(er),math.sin(ar)*math.cos(er),-math.sin(er)]);up=np.cross(toward,right)
    corners=np.array([[x,y,z] for x in [lo[0],hi[0]] for y in [lo[1],hi[1]] for z in [lo[2],hi[2]]]);span=max(np.ptp(corners@right)/(W/H),np.ptp(corners@up))*1.22
    if tid=='T08':span=max(span,.48)
    return dict(lookat=center.tolist(),azimuth=az,elevation=el,vertical_span_m=float(span),distance=.8,orthographic=True,rule='shared task camera fitted once across all selected candidates/conditions/states, including ground; never fit per frame')
def geom(scene,typ,pos,size,color):
    g=scene.geoms[scene.ngeom];mujoco.mjv_initGeom(g,typ,np.asarray(size,float),np.asarray(pos,float),np.eye(3).ravel(),np.asarray(color,np.float32));g.category=int(mujoco.mjtCatBit.mjCAT_DECOR);scene.ngeom+=1;return g
def line(scene,a,b,r=.00035,color=None,arrow=False):
    if np.linalg.norm(np.array(b)-a)<1e-10:return
    typ=mujoco.mjtGeom.mjGEOM_ARROW if arrow else mujoco.mjtGeom.mjGEOM_CAPSULE;g=geom(scene,typ,[0,0,0],[r,r,r],color if color is not None else rgb(PALETTE['reference']));mujoco.mjv_connector(g,typ,r,np.array(a,float),np.array(b,float))
def sphere(scene,p,r=.002,color=None):geom(scene,mujoco.mjtGeom.mjGEOM_SPHERE,p,[r]*3,color if color is not None else rgb(PALETTE['target']))
def force_at(cues,condition,t):
    force=np.zeros(3);env=cues.get('environment',{})
    forces=[*env.get('external_forces',[]),*env.get('physical_environment',{}).get('wrenches',[])]
    for f in forces:
        start=f.get('start_s',0);end=f.get('end_s',0)
        if start<=t<=end:
            value=np.array(f.get('force_n',f.get('force_world_n',[0,0,0])),float)
            if f.get('waveform')=='half_sine':value=value*math.sin(math.pi*(t-start)/(end-start))
            force+=value
    for p in cues.get('goal_data',{}).get('programs',{}).get(condition,[]):
        if p['start_s']<=t<=p['end_s']:
            start=np.array(p['force_start_world_n']);end=np.array(p['force_end_world_n']);dur=p.get('ramp_until_s',p['end_s'])-p['start_s'];frac=np.clip((t-p['start_s'])/dur,0,1) if dur else 1.
            if p['interpolation']=='smoothstep':frac=frac*frac*(3-2*frac)
            if p['interpolation']=='hold':frac=1.
            force=start+(end-start)*frac
    return force
def material_point(model,data,candidate,s):
    comps=candidate['configuration']['robot']['structure']['data']['components'];segments=[c for c in comps if c.get('kind')=='flexible_segment'];target=s*sum(c['length_m'] for c in segments)
    for seg in segments:
        ids=[i for i in range(model.nbody) if model.body(i).name.startswith(seg['id']+'_cell_')];ids.sort(key=lambda i:int(model.body(i).name.split('_cell_')[1]));length=seg['length_m']/len(ids)
        for bid in ids:
            if target<=length+1e-12:return data.xpos[bid]+data.xmat[bid].reshape(3,3)@np.array([min(target,length),0,0])
            target-=length
    return data.xpos[ids[-1]]
def cues_native(renderer,model,data,cues,record,condition,t,motion=None,index=None,with_trail=True):
    scene=renderer.scene;target=cues.get('target_m');path=cues.get('path_m',[])
    if target is not None:sphere(scene,target,.0018)
    for a,b in zip(path[:-1],path[1:]):line(scene,a,b,r=.00028)
    if target is not None and cues.get('target_axis_world') is not None:line(scene,target,np.array(target)+.025*np.array(cues['target_axis_world']),r=.0008,color=rgb(PALETTE['target']),arrow=True)
    if cues.get('axis_local') is not None:
        try:
            sid=model.site('tip_site').id;pos=data.site_xpos[sid];axis=data.site_xmat[sid].reshape(3,3)@np.array(cues['axis_local']);line(scene,pos,pos+.025*axis,r=.0007,color=rgb(PALETTE['actual']),arrow=True)
        except KeyError:pass
    for p,a in zip(path,cues.get('axis_vertices_world',[])):line(scene,p,np.array(p)+.02*np.array(a),r=.0006,color=rgb(PALETTE['target']),arrow=True)
    if motion and with_trail and motion.get('tip_m') is not None and index is not None and record['task_id'] in ['T04','T06','T09','T10']:
        pts=np.array(motion['tip_m'][:index+1]);idx=np.unique(np.linspace(0,len(pts)-1,min(100,len(pts))).astype(int));pts=pts[idx]
        for a,b in zip(pts[:-1],pts[1:]):line(scene,a,b,r=.00023,color=rgb(PALETTE['actual'],.85))
    force=force_at(cues,record.get('force_condition_id',condition),t);anchor=None
    if np.linalg.norm(force)>1e-9:
        if record['task_id'] in ['T08','PHS-2D']:anchor=material_point(model,data,read(record['candidate_file']),.7);scale=.25 if record['task_id']=='T08' else .45;sphere(scene,anchor,.0017,color=rgb(PALETTE['target']))
        else:
            try:anchor=data.xipos[model.body('payload').id];scale=1.3 if record['task_id']=='T10' else .6
            except KeyError:pass
        if anchor is not None:line(scene,anchor-force*scale,anchor,r=.0015,color=rgb(PALETTE['force']),arrow=True)
    if record['task_id']=='T09' and motion and index is not None and motion.get('contact_force_n'):
        fc=motion['contact_force_n'][index]
        if fc>1e-5:
            anchor=data.xpos[model.body('button_slider').id];line(scene,anchor-np.array([0,.2*fc,0]),anchor,r=.0012,color=rgb(PALETTE['force']),arrow=True)

def extra_specs(cases):
    # Only archived XML + archived qpos. Do not manufacture unavailable intermediate geometry.
    extras=[]
    phs0=ROOT/'runs/phs2d-paper-data-20261112/VISUAL_XML/F0_physical_reference.xml'
    if phs0.exists():
        extras.append(dict(task_id='PHS-2D',condition_id='F0',source_xml=str(phs0),candidate_id='F0; exact artifact in original PHS EVIDENCE_INDEX.md',run_id='PHS original reference study; see original EVIDENCE_INDEX.md',states=[],state_source='original F0 XML qpos0 reference only',kind='initial_structure_reference',accepted=False))
    t7=O/'T07/selected_render_inputs.csv'
    if t7.exists():
        rr=list(csv.DictReader(t7.open(encoding='utf-8-sig')));r=next(x for x in rr if x['node_id']=='S1');s=read(r['state_json']);samples=s.get('samples',s) if isinstance(s,dict) else s
        states=[dict(label='initial',index=0,time_s=samples[0]['time_s'],qpos=samples[0]['qpos_rad']),dict(label='final',index=len(samples)-1,time_s=samples[-1]['time_s'],qpos=samples[-1]['qpos_rad'])]
        extras.append(dict(task_id='T07',condition_id='S1_ellipse_B',source_xml=r['original_xml'],candidate_id=r['candidate_id'],run_id=r['run_id'],states=states,state_source=r['state_json'],kind='structural_intermediate',accepted=True))
    ts=O/'T10/STATE_SNAPSHOTS.json'
    if ts.exists():
        snaps=read(ts)
        for node in ['T10_N03','T10_N04','T10_N05']:
            ss=[r for r in snaps if r['node_id']==node];r=ss[0]
            extras.append(dict(task_id='T10',condition_id=node,source_xml=r['original_model_xml'],candidate_id=r['candidate_artifact_id'],run_id=r.get('source_tag'),states=[dict(label=x['stage'],index=x['dense_index'],time_s=x['time_s'],qpos=x['qpos'],source=x['source']) for x in ss],state_source=str(ts)+'#'+node,kind='controller_research_stage',accepted='refer to stage-specific evidence; not final common-controller group'))
    return extras

def video(record,model,cam_spec,cues):
    motion=read(record['motion_file']);times=np.asarray(motion['times_s']);duration=times[-1]-times[0];tid=record['task_id'];condition=record['condition_id'];fps=25
    playback_duration=duration if duration>=8 else 6. if tid=='T09' else 4.
    count=min(len(times),max(2,round(playback_duration*fps)))
    desired=np.linspace(times[0],times[-1],count);ix=np.searchsorted(times,desired);ix=np.clip(ix,0,len(times)-1);left=np.maximum(ix-1,0);ix=np.where(abs(times[left]-desired)<abs(times[ix]-desired),left,ix);ix=np.unique(ix)
    folder=O/tid/'VIDEOS_MJ';folder.mkdir(exist_ok=True);path=folder/f'{tid}_{condition}_native_shadows.mp4'
    log=folder/f'{tid}_{condition}_encode.log';command=[str(FFMPEG),'-hide_banner','-loglevel','error','-y','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(fps),'-i','pipe:0','-an','-c:v','h264_nvenc','-preset','p7','-tune','hq','-rc','constqp','-qp','18','-profile:v','high','-pix_fmt','yuv420p','-movflags','+faststart',str(path)]
    model.vis.global_.fovy=cam_spec['vertical_span_m'];renderer=mujoco.Renderer(model,height=H,width=W,max_geom=16000);data=mujoco.MjData(model);cam=camera(cam_spec);frame_rows=[]
    with log.open('wb') as f:
        proc=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=f,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            for frame,i in enumerate(ix):
                t=float(times[i]);assign(model,data,motion['qpos'][i],motion['joint_names']);data.time=t;renderer.update_scene(data,camera=cam)
                renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=True
                cues_native(renderer,model,data,cues,record,condition,t,motion,int(i));pixels=renderer.render();proc.stdin.write(pixels.tobytes())
                if frame in {0,len(ix)//2,len(ix)-1}:png(folder/f'{tid}_{condition}_frame_{frame:04d}.png',pixels)
                frame_rows.append(dict(frame=frame,video_time_s=frame/fps,source_index=int(i),simulation_time_s=t,motion_source=motion['source']))
            proc.stdin.close();code=proc.wait()
            if code:raise RuntimeError(log.read_text(errors='replace'))
        finally:
            renderer.close()
            if proc.poll() is None:proc.kill()
    csvout(folder/f'{tid}_{condition}_frame_sources.csv',frame_rows)
    probe=subprocess.run([str(FFPROBE),'-v','error','-show_entries','stream=codec_name,width,height,nb_frames','-show_entries','format=duration','-of','json',str(path)],capture_output=True,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));assert probe.returncode==0;info=json.loads(probe.stdout)
    assert int(info['streams'][0]['nb_frames'])==len(ix)
    return dict(task_id=tid,condition_id=condition,condition_role=record.get('condition_role'),run_id=record['run_id'],candidate_id=record['candidate_id'],video=str(path),source_xml=record['source_xml'],visual_xml=record['visual_xml'],motion_source=motion['source'],motion_file=record['motion_file'],frame_sources=str(folder/f'{tid}_{condition}_frame_sources.csv'),frames=len(ix),fps=fps,simulation_duration_s=float(duration),playback_duration_s=len(ix)/fps,playback_speed=float(duration/(len(ix)/fps)),resolution=[W,H],camera=cam_spec,shadow_enabled=True,text_overlay=False,native_cues='goal/reference path, past recorded Tip trail when relevant, original directed tool axis, task-prescribed force/contact arrow only',physical_integration_performed=False,encoding='H264 NVENC, RGB native frames -> yuv420p MP4, no image manipulation; encoder changes color subsampling only',ffprobe=info)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--only',nargs='*');ap.add_argument('--mode',choices=['stills','video','all'],default='all');args=ap.parse_args();cases=read(O/'FINAL_CASES.json');extras=extra_specs(cases)
    selected=args.only or sorted({r['task_id'] for r in cases});existing_screens=read(O/'SCREENSHOT_MANIFEST.json') if (O/'SCREENSHOT_MANIFEST.json').exists() else [];existing_videos=read(O/'VIDEO_MANIFEST.json') if (O/'VIDEO_MANIFEST.json').exists() else []
    if args.mode in ['stills','all']:existing_screens=[r for r in existing_screens if r['task_id'] not in selected]
    if args.mode in ['video','all']:existing_videos=[r for r in existing_videos if r['task_id'] not in selected]
    for tid in selected:
        records=[dict(r) for r in cases if r['task_id']==tid];ex=[dict(r) for r in extras if r['task_id']==tid];models={};all_for_fit=[];ground=0
        for r in [*records,*ex]:
            xp=O/tid/'VISUAL_XML'/f'{r["condition_id"]}_visual.xml';model,g=visual_xml(r['source_xml'],xp);ground=g;r['visual_xml']=str(xp);models[r['condition_id']]=model
            states=r['states'] if 'states' in r else read(r['states_file']);r['states']=states;all_for_fit.append((model,states))
        cam_spec=fit_camera(all_for_fit,ground,tid);save(O/tid/'VISUAL_XML/CAMERA_SETTINGS.json',cam_spec)
        if args.mode in ['stills','all']:
            for ri,r in enumerate([*records,*ex]):
                model=models[r['condition_id']];model.vis.global_.fovy=cam_spec['vertical_span_m'];data=mujoco.MjData(model);renderer=mujoco.Renderer(model,height=H,width=W,max_geom=16000)
                cues=read(r['cues_file']) if r.get('cues_file') else {};motion=read(r['motion_file']) if r.get('motion_file') else None
                poses=[('reference',None,'oblique')]+[(s['label'],s,'oblique') for s in r['states']]
                if ri==0:poses+=[('reference',None,'side'),('reference',None,'front')]
                for label,state,view in poses:
                    if state:assign(model,data,state['qpos'],state.get('joint_names'));t=state['time_s']
                    else:assign(model,data,model.qpos0);t=0
                    renderer.update_scene(data,camera=camera(cam_spec,view));renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=True
                    if state and cues:cues_native(renderer,model,data,cues,r,r['condition_id'],t,motion,state['index'])
                    pixels=renderer.render();fp=O/tid/'FIGURES_MJ'/f'{tid}_{r["condition_id"]}_{label}_{view}.png';fp.parent.mkdir(exist_ok=True);png(fp,pixels)
                    existing_screens.append(dict(task_id=tid,condition_id=r['condition_id'],run_id=r['run_id'],candidate_id=r['candidate_id'],stage=label,view=view,png=str(fp),original_xml=r['source_xml'],visual_xml=r['visual_xml'],state_source=state.get('source',r.get('state_source',r.get('states_file'))) if state else 'original XML qpos0 reference, not a solved pose',source_index=state['index'] if state else None,time_s=t if state else None,camera=dict(cam_spec,azimuth=float(camera(cam_spec,view).azimuth),elevation=float(camera(cam_spec,view).elevation)),resolution=[W,H],shadow_enabled=True,text_overlay=False,renderer='MuJoCo Renderer 3.13.0 native RGB buffer; exact PNG encoding, no crop or retouch'))
                renderer.close()
            save(O/'SCREENSHOT_MANIFEST.json',existing_screens);csvout(O/tid/'render_manifest.csv',[r for r in existing_screens if r['task_id']==tid]);print('STILLS',tid,flush=True)
        if args.mode in ['video','all']:
            for r in records:
                print('VIDEO_START',tid,r['condition_id'],flush=True);v=video(r,models[r['condition_id']],cam_spec,read(r['cues_file']));existing_videos.append(v);save(O/'VIDEO_MANIFEST.json',existing_videos);csvout(O/tid/'video_manifest.csv',[r for r in existing_videos if r['task_id']==tid]);print('VIDEO_DONE',tid,r['condition_id'],v['frames'],flush=True)
    save(O/'RENDER_STYLE.json',dict(reference=str(ROOT/'runs/phs2d-paper-data-20261112/FIGURES_MJ/F3_reference_oblique.png'),prior_visual_components=str(ROOT/'paper_experiments/paper_results_master_20261113/VISUAL_XML'),palette=PALETTE,native_shadows=True,text_overlay=False,source_states_only=True,physical_integration_performed=False,appearance='Reuse previously completed guides, terminal anchor plates, rigid-junction sheaths and mount. Change native lighting/ground/background, retain actual route and all physical parameters.',visual_dimensions_notice='Previously completed schematic anchor/sheath appearance remains visual only; no new physical hardware or fabricated state is claimed.'))
if __name__=='__main__':main()
