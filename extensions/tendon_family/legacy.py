"""Lossless adapter of old eight-cell physics to the NEW MATLAB model identity."""
import numpy as np
from tools.state_io import digest
from extensions.robot_domain.contracts import RodDesign
from extensions.experiment_dynamics.physics import resolve_physics


def resolve_legacy(data):
    old=resolve_physics(RodDesign.model_validate(data)); parts=[]; dofs=[]
    for i,p in enumerate(old.parts):
        dofs.extend([f'joint_{i}_y',f'joint_{i}_z'])
        theta=np.arange(32)*2*np.pi/32; ring=np.c_[p.radius_m*np.cos(theta),p.radius_m*np.sin(theta)]
        vertices=np.vstack([np.c_[np.full(32,x),ring] for x in (0,p.length_m)])
        parts.append(dict(entity=p.entity,component='legacy_rod',parent=i-1,position_m=list(p.origin_parent_m),rotation=np.eye(3).tolist(),
            length_m=p.length_m,section_axis_rad=0.,mass_kg=p.mass_kg,com_local_m=list(p.com_local_m),
            inertia_com_local_kg_m2=p.inertia_com_local_kg_m2,dofs=[2*i,2*i+1],stiffness_nm_rad=p.stiffness_nm_rad,
            damping_nm_s_rad=p.damping_nm_s_rad,natural_rad=p.natural_rad,section=None,
            section_properties=dict(outer_yz_m=ring.tolist(),holes_yz_m=[]),envelope_halfsize_m=None,collision_vertices_m=vertices.tolist()))
    tendons=[]; actuators=[]
    for t in old.tendons:
        points=[dict(body=-1,position_m=[0.,*t.offset_yz_m],role='start')]
        points += [dict(body=i,position_m=[p.length_m,*t.offset_yz_m],role='anchor' if i==len(parts)-1 else 'guide') for i,p in enumerate(old.parts)]
        tendons.append(dict(entity=t.entity,points=points,kp_n_m=t.kp_n_m,pretension_n=0.,force_limit_n=t.force_limit_n,diameter_m=.001))
        actuators.append(dict(id=t.actuator,command_type='displacement',units='m',drum_radius_m=None,
            transmission=[dict(tendon=t.entity,ratio=1.)],limits=[-.02,.02],velocity_limit=.05))
    design_source=RodDesign.model_validate(data).model_dump(mode='json')
    discretization=dict(version='serial_bending_discretization_v1',model='serial_bending_cells_v1',
        cells={'legacy_rod':len(parts)},coordinates='two_principal_bending_angles_per_cell')
    p=dict(version='serial_bending_physics_v1',source_identity=old.identity,
        design_identity=digest(design_source),discretization_identity=digest(discretization),discretization=discretization,
        source_roles=dict(entity_design='domain.rod_design',physical_inputs='resolved legacy V2 equivalent rod',
            model_discretization='RodDesign.segments compatibility derivation'),parts=parts,tendons=tendons,actuators=actuators,
        transmission=np.eye(len(tendons)).tolist(),dofs=dofs,entity_map={'legacy_rod':dict(bodies=list(range(len(parts))),dofs=dofs,kind='flexible_segment')},
        tip=dict(body=len(parts)-1,position_m=[old.parts[-1].length_m,0.,0.]),section_quantities={},
        applicability=dict(compilable=True,backends=['backend.matlab_spatial','backend.family_mujoco'],physics='legacy rod adapted to serial bending',
            omitted=['axial stretch','shear','material torsion','friction'],collision='polygonal cylinder approximation'))
    from .geometry import geometry
    p['reference_lengths_m']=geometry(p,np.zeros(len(dofs)))['lengths'].tolist(); p['identity']=digest(p)
    return p
