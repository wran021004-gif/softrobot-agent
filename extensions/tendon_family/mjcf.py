"""Named bodies, full COM tensors, explicit tendon sites and ideal length servos."""
import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial.transform import Rotation
from .compiler import rx


def fmt(x):
    return ' '.join(format(float(v),'.17g') for v in np.asarray(x).ravel())


def quaternion(R):
    x,y,z,w = Rotation.from_matrix(R).as_quat()
    return fmt([w,x,y,z])


def compile_xml(physics, scene, config, path):
    p=physics
    root=ET.Element('mujoco',model='serial_tendon_family')
    ET.SubElement(root,'compiler',angle='radian',autolimits='true')
    ET.SubElement(root,'option',timestep=str(scene['timestep_s']),gravity=fmt(scene['gravity']),integrator='implicitfast')
    default=ET.SubElement(root,'default')
    ET.SubElement(default,'joint',limited='false')
    ET.SubElement(default,'geom',contype='1',conaffinity='2',friction='0 0 0')
    assets=ET.SubElement(root,'asset'); world=ET.SubElement(root,'worldbody')
    ET.SubElement(world,'light',pos='0 -0.3 1',dir='0 0 -1')
    ET.SubElement(world,'geom',name=scene['floor_id'],type='plane',pos=fmt([0,0,scene['floor_z_m']]),size='1 1 .01',contype='2',conaffinity='1',rgba='.6 .6 .6 1')
    ET.SubElement(world,'site',name='task_target',pos=fmt(scene['target_world_m']),size='.004',rgba='1 0 0 1')
    base=ET.SubElement(world,'body',name='fixed_base',pos=fmt(scene['mount_position']),quat=quaternion(scene['mount_rotation']))
    bodies=[]
    for i,part in enumerate(p['parts']):
        parent=base if part['parent']<0 else bodies[part['parent']]
        body=ET.SubElement(parent,'body',name=part['entity'],pos=fmt(part['position_m']),quat=quaternion(part['rotation']))
        bodies.append(body)
        I=np.array(part['inertia_com_local_kg_m2'])
        ET.SubElement(body,'inertial',pos=fmt(part['com_local_m']),mass=str(part['mass_kg']),fullinertia=fmt([I[0,0],I[1,1],I[2,2],I[0,1],I[0,2],I[1,2]]))
        for j,k in enumerate(part['dofs']):
            ET.SubElement(body,'joint',name=p['dofs'][k],type='hinge',axis='0 1 0' if j==0 else '0 0 1',
                stiffness=str(part['stiffness_nm_rad'][j]),damping=str(part['damping_nm_s_rad'][j]),springref=str(part['natural_rad'][j]))
        prop=part['section_properties']
        if prop:
            vertices,faces=[],[]
            for ring in [prop['outer_yz_m'],*prop['holes_yz_m']]:
                ring=np.array(ring)@rx(-part['section_axis_rad'])[1:,1:].T
                offset=len(vertices); m=len(ring)
                vertices.extend(np.c_[np.zeros(m),ring].tolist()); vertices.extend(np.c_[np.full(m,part['length_m']),ring].tolist())
                for j in range(m):
                    a,b=offset+j,offset+(j+1)%m
                    faces.extend([[a,b,b+m],[a,b+m,a+m]])
            # Open-ended section wall mesh preserves all contours in rendering.
            # MuJoCo convexifies this same mesh for collision (explicitly recorded).
            mesh=part['entity']+'_section'
            ET.SubElement(assets,'mesh',name=mesh,vertex=fmt(vertices),face=' '.join(str(x) for face in faces for x in face))
            ET.SubElement(body,'geom',name=part['entity']+'_shape',type='mesh',mesh=mesh,rgba='.25 .55 .8 1')
        else:
            ET.SubElement(body,'geom',name=part['entity']+'_shape',type='box',size=fmt(part['envelope_halfsize_m']),rgba='.7 .55 .25 1')
    tip=p['tip']; parent=base if tip['body']<0 else bodies[tip['body']]
    ET.SubElement(parent,'site',name='tip_site',pos=fmt(tip['position_m']),size='.002',rgba='0 1 0 1')
    tendons=ET.SubElement(root,'tendon'); actuators=ET.SubElement(root,'actuator')
    for t in p['tendons']:
        route=ET.SubElement(tendons,'spatial',name=t['entity'],width=str(t['diameter_m']/2),rgba='.8 .15 .15 1')
        for j,point in enumerate(t['points']):
            parent=base if point['body']<0 else bodies[point['body']]
            name=f"{t['entity']}_point_{j}"
            ET.SubElement(parent,'site',name=name,pos=fmt(point['position_m']),size=str(t['diameter_m']/2),rgba='.8 .15 .15 1')
            ET.SubElement(route,'site',site=name)
        # These are tendon force elements, not independent motor descriptions.
        # The shared actuator matrix is applied once per control interval.
        ET.SubElement(actuators,'general',name=t['entity']+'_length_servo',tendon=t['entity'],
            gainprm=str(t['kp_n_m']),biastype='affine',biasprm=fmt([0,-t['kp_n_m'],0]),
            forcelimited='true',forcerange=fmt([-t['force_limit_n'],0]))
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)
    return path
