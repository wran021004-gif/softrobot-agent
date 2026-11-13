"""Native MuJoCo-only still rendering. No simulation or structure construction."""
from pathlib import Path
import json,xml.etree.ElementTree as ET,threading,concurrent.futures,math,struct,zlib,argparse
import numpy as np
import mujoco
O=Path(__file__).resolve().parent;PHS=O.parents[1]/'runs/phs2d-paper-data-20261112'
COLORS=dict(shell='#99D8C9',distal='#2CA25F',guides='#E5F5F9',neutral='#536166',tendon='#303C3E')
def rgb(h):return [int(h[i:i+2],16)/255 for i in [1,3,5]]
def rgba(h,a=1):return ' '.join(str(x) for x in [*rgb(h),a])
def fmt(x):return ' '.join(format(float(v),'.17g') for v in np.asarray(x).ravel())
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def model(p):
    future=concurrent.futures.Future();threading.stack_size(8*1024*1024)
    def run():
        try:future.set_result(mujoco.MjModel.from_xml_path(str(p)))
        except BaseException as e:future.set_exception(e)
    t=threading.Thread(target=run);t.start();t.join();return future.result()
def png(p,array):
    # Encode the exact Renderer RGB buffer, without using any drawing/editing package.
    h,w,_=array.shape
    def chunk(typ,data):return struct.pack('>I',len(data))+typ+data+struct.pack('>I',zlib.crc32(typ+data)&0xffffffff)
    raw=b''.join(b'\0'+array[i].tobytes() for i in range(h))
    Path(p).write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,6))+chunk(b'IEND',b''))
def check(a,b):
    keys=['body_mass','body_inertia','body_ipos','body_iquat','body_pos','body_quat','jnt_stiffness','dof_damping','jnt_axis','jnt_pos','jnt_range','tendon_range','tendon_solref_lim','tendon_solimp_lim','wrap_type','wrap_objid','site_pos','site_bodyid']
    result={k:bool(np.array_equal(getattr(a,k),getattr(b,k))) for k in keys if hasattr(a,k)}
    result.update({k:getattr(a,k)==getattr(b,k) for k in ['nq','nv','njnt','nbody','ntendon','nsite','nu']})
    for i in range(a.ngeom):
        name=a.geom(i).name
        if not name:continue
        q=b.geom(name).id
        for key in ['geom_contype','geom_conaffinity','geom_size','geom_pos','geom_quat','geom_friction','geom_solref','geom_solimp']:
            result[name+':'+key]=bool(np.array_equal(getattr(a,key)[i],getattr(b,key)[q]))
    result['options']=all(np.array_equal(getattr(a.opt,k),getattr(b.opt,k)) for k in ['timestep','integrator','gravity','iterations','tolerance'])
    for i in range(b.ngeom):
        if b.geom(i).name.startswith('master_'):result['visual_collision_'+str(i)]=int(b.geom_contype[i])==0 and int(b.geom_conaffinity[i])==0
    assert all(result.values()),[k for k,v in result.items() if not v]
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--only',nargs='*');args=parser.parse_args()
    b=read(O/'SOURCE_DATA/MODEL_BINDINGS.json');specs=[]
    for task,label in [('T01','T01'),('T02','M2'),('T03','T03'),('T04','tracking'),('T05','T05'),('T06','T06'),('T07','T07'),('T08','P3'),('T09','T09_guides'),('T10','T10')]:
        binding=b[task][0];xs=binding['xml_files'];source=next((x for x in xs if 'independent' in x and 'baseline' in x),xs[0])
        specs.append(dict(task_id=task,label=label,source=source,binding=binding,views=['oblique']+(['guides_detail'] if task=='T09' else [])))
    for name,label,views in [('F0','PHS2D_F0',['oblique']),('F3','PHS2D_F3',['oblique']),('F8','PHS2D',['oblique','side','front'])]:
        specs.append(dict(task_id='PHS-2D',label=label,source=str(PHS/'VISUAL_XML'/f'{name}_visual.xml'),physical_source=str(PHS/'VISUAL_XML'/f'{name}_physical_reference.xml'),views=views,phs=True))
    if args.only:specs=[s for s in specs if s['label'] in args.only]
    labels={s['label'] for s in specs}
    screens=[s for s in read(O/'FIGURES_MUJOCO/SCREENSHOT_SOURCES.json') if s['label'] not in labels] if args.only else []
    validation=[s for s in read(O/'VISUAL_XML/PHYSICS_EQUIVALENCE.json') if s['label'] not in labels] if args.only else []
    for spec in specs:
        source=Path(spec['source']);physical_source=Path(spec.get('physical_source',source));root=ET.parse(source).getroot();original=model(physical_source)
        # Pure color/light/camera edits; existing true shells and guide meshes are reused exactly.
        for geom in root.findall('.//geom'):
            name=geom.get('name','')
            if not name:continue
            if 'cell_' in name:geom.set('rgba',rgba(COLORS['shell'] if int(name.split('_')[1])%2==0 else COLORS['distal']))
            elif 'spoke' in name:geom.set('rgba',rgba(COLORS['neutral']))
            elif '_eye' in name:geom.set('rgba',rgba(COLORS['distal']))
            elif 'guide' in name:geom.set('rgba',rgba(COLORS['guides']))
            elif name=='floor':geom.set('rgba','1 1 1 0')
            elif 'connector' in name or 'payload' in name or 'tool' in name or 'spoke' in name:geom.set('rgba',rgba(COLORS['neutral']))
            elif name.startswith('vis_'):geom.set('rgba',rgba(COLORS['neutral'],.65 if 'datum' in name else 1))
        for tendon in root.findall('./tendon/spatial'):tendon.set('rgba',rgba(COLORS['tendon']));tendon.set('width','.0006')
        for site in root.findall('.//site'):
            if site.get('name'):
                site.set('rgba',rgba(COLORS['neutral']))
                if site.get('name','').startswith('tendon_'):site.set('size','.001')
        world=root.find('worldbody')
        body_elements={v.get('name'):v for v in root.findall('.//body')};base=body_elements.get('fixed_base')
        if base is not None:
            anchors=[v for v in base.findall('site') if v.get('name','').startswith('tendon_')]
            xyz=np.array([[float(x) for x in s.get('pos').split()] for s in anchors]) if anchors else np.array([[0,.02,.02]])
            extent=np.maximum(np.max(abs(xyz[:,1:]),axis=0)+.003,.022)
            for old in base.findall('geom'):
                if old.get('name')=='vis_mount_datum':old.set('rgba','0 0 0 0')
            ET.SubElement(base,'geom',name='master_mount_reference_datum',type='box',pos=fmt([float(xyz[:,0].min())-.004,0,0]),size=fmt([.004,*extent]),mass='0',contype='0',conaffinity='0',rgba=rgba(COLORS['neutral']))
        # Schematic anchor plates land on the exact terminal sites and remain attached to their true owners.
        site_owners={s.get('name'):(body,s) for body in body_elements.values() for s in body.findall('site')}
        terminal_groups={}
        for t in root.findall('./tendon/spatial'):
            end=t.findall('site')[-1].get('site');owner,s=site_owners[end];pos=np.array([float(x) for x in s.get('pos','0 0 0').split()]);key=(owner.get('name'),round(float(pos[0]),9))
            terminal_groups.setdefault(key,[]).append(pos)
        for n,((owner,x),points) in enumerate(terminal_groups.items()):
            points=np.array(points);center=(points.min(0)+points.max(0))/2;half=(points.max(0)-points.min(0))/2;center[0]=x+.0015;half[0]=.0015;half[1:]=np.maximum(half[1:]+.002,.007)
            ET.SubElement(body_elements[owner],'geom',name=f'master_anchor_reference_{n}',type='box',pos=fmt(center),size=fmt(half),mass='0',contype='0',conaffinity='0',rgba=rgba(COLORS['neutral']))
        # Visual sheath bridges the exact rigid junction gap; it changes no skeleton spacing or mechanics.
        od=mujoco.MjData(original);mujoco.mj_fwdPosition(original,od)
        assets={m.get('name'):m for m in root.findall('./asset/mesh')}
        def section_radius(body):
            g=body.find('geom')
            if g is not None and g.get('mesh') in assets:
                verts=np.array([float(x) for x in assets[g.get('mesh')].get('vertex').split()]).reshape(-1,3)
                return min(np.ptp(verts[:,1]),np.ptp(verts[:,2]))/2
            return .003
        for nm,body in body_elements.items():
            if not nm.startswith('connector_'):continue
            try:idx=int(nm.split('_')[1]);nextname=f'segment_{idx}_cell_0';guide=f'guide_{idx}';bid=original.body(nm).id;gid=original.body(guide).id;nid=original.body(nextname).id
            except (ValueError,KeyError):continue
            R=od.xmat[bid].reshape(3,3);start=R.T@(od.xpos[gid]-od.xpos[bid]);end=R.T@(od.xpos[nid]-od.xpos[bid]);radius=section_radius(body_elements[nextname])
            ET.SubElement(body,'geom',name=f'master_junction_sheath_{idx}',type='capsule',fromto=fmt([*start,*end]),size=str(radius),mass='0',contype='0',conaffinity='0',rgba=rgba(COLORS['shell']))
        for l in list(world.findall('light')):world.remove(l)
        ET.SubElement(world,'light',name='paper_master_key',pos='.3 -.4 .9',dir='-.3 .4 -.8',diffuse='.7 .7 .7',specular='.12 .12 .12',castshadow='false')
        ET.SubElement(world,'light',name='paper_master_fill',pos='-.25 .3 .6',dir='.2 -.3 -.5',diffuse='.45 .45 .45',castshadow='false')
        visual=root.find('visual')
        if visual is None:visual=ET.SubElement(root,'visual')
        for tag in ['global','quality','headlight','rgba']:
            for el in list(visual.findall(tag)):visual.remove(el)
        ET.SubElement(visual,'global',offwidth='2400',offheight='1800',orthographic='true',fovy='.47')
        ET.SubElement(visual,'quality',offsamples='4');ET.SubElement(visual,'headlight',ambient='.45 .45 .45',diffuse='.45 .45 .45',specular='.08 .08 .08')
        asset=root.find('asset')
        if asset is None:asset=ET.SubElement(root,'asset')
        for sky in asset.findall('texture'):
            if sky.get('type')=='skybox':sky.set('rgb1','1 1 1');sky.set('rgb2','1 1 1')
        if not any(s.get('type')=='skybox' for s in asset.findall('texture')):ET.SubElement(asset,'texture',name='master_white_background',type='skybox',builtin='flat',rgb1='1 1 1',rgb2='1 1 1',width='32',height='32')
        xp=O/'VISUAL_XML'/f'{spec["label"]}_visual.xml';ET.indent(root,space='  ');ET.ElementTree(root).write(xp,encoding='utf-8',xml_declaration=True)
        m=model(xp);checks=check(original,m);data=mujoco.MjData(m)
        # Prefer an existing recorded starting pose when one is available; otherwise label XML reference pose.
        samplefile=O/'FIGURE_DATA'/f'{spec["task_id"]}_{spec.get("binding",{}).get("condition_name","default")}_SAMPLES.json'
        pose='XML qpos0 reference pose'
        if samplefile.exists():
            samples=read(samplefile);q=samples[0].get('qpos_rad')
            if q is not None and len(q)==m.nq:data.qpos[:]=q;pose=str(samplefile)+'#/0/qpos_rad'
        mujoco.mj_fwdPosition(m,data)
        # Fit only the robot and its true mounted accessories, excluding planes/task fixtures.
        names=[m.geom(i).name for i in range(m.ngeom)];ids=[i for i,name in enumerate(names) if name and ('cell_' in name or 'guide_' in name or 'connector_' in name or 'payload' in name or 'probe'==name)]
        if not ids:ids=[i for i in range(m.ngeom) if m.geom_type[i]!=mujoco.mjtGeom.mjGEOM_PLANE]
        lo=data.geom_xpos[ids].min(0);hi=data.geom_xpos[ids].max(0);center=(lo+hi)/2;span=max(hi-lo)*1.35+.06
        if spec.get('phs'):center=np.array([0,0,.318]);span=.47
        renderer=mujoco.Renderer(m,height=1800,width=2400)
        for view in spec['views']:
            cam=mujoco.MjvCamera();cam.type=mujoco.mjtCamera.mjCAMERA_FREE;cam.orthographic=1;cam.distance=.8;cam.lookat[:]=center;cam.azimuth=135;cam.elevation=-18
            display_span=span
            if not spec.get('phs'):
                # Active arms extend along +X: show lateral and vertical geometry together.
                cam.azimuth=120;cam.elevation=-22
                az,el=np.deg2rad([cam.azimuth,cam.elevation]);right=np.array([-math.sin(az),math.cos(az),0]);toward=np.array([math.cos(az)*math.cos(el),math.sin(az)*math.cos(el),-math.sin(el)]);up=np.cross(toward,right)
                pts=data.geom_xpos[ids];radii=m.geom_rbound[ids];px=pts@right;py=pts@up
                display_span=max((max(px+radii)-min(px-radii))/(2400/1800),max(py+radii)-min(py-radii))*1.25
            if view=='side':cam.azimuth=90;cam.elevation=0
            if view=='front':cam.azimuth=0;cam.elevation=0
            if view=='guides_detail':
                cam.azimuth=100;cam.elevation=-12;display_span*=1.1
            m.vis.global_.fovy=display_span
            stem=f'fig_robot_{spec["label"]}_{view}' if view!='guides_detail' else 'fig_robot_T09_guides_detail'
            renderer.update_scene(data,camera=cam);pixels=renderer.render();fp=O/'FIGURES_MUJOCO'/f'{stem}.png';png(fp,pixels)
            screens.append(dict(task_id=spec['task_id'],label=spec['label'],view=view,png=str(fp),source_xml=str(source),original_physical_xml=str(physical_source),visual_xml=str(xp),resolution=[2400,1800],pose_source=pose,
                visual_additions='Zero-mass mounting datum and exact terminal-site anchor plates; zero-mass sheath along actual rigid junction gap. Schematic appearance, not additional physical hardware.',
                camera=dict(lookat=cam.lookat.tolist(),azimuth=cam.azimuth,elevation=cam.elevation,orthographic=True,vertical_span_m=display_span,distance=.8),
                renderer='MuJoCo Renderer 3.13.0, original RGB PNG encoding only; no image editing/compositing',palette=COLORS))
            print('RENDER',fp.name,flush=True)
        renderer.close();validation.append(dict(label=spec['label'],source_xml=str(source),original_physical_xml=str(physical_source),visual_xml=str(xp),checks=checks,passed=True))
    save(O/'VISUAL_XML/PHYSICS_EQUIVALENCE.json',validation);save(O/'FIGURES_MUJOCO/SCREENSHOT_SOURCES.json',screens)

if __name__=='__main__':main()
