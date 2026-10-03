"""Engine-independent serial assembly; named physical locations survive remeshing."""
import math
import numpy as np
from tools.state_io import digest
from .contracts import Design, Discretization, Segment, Rigid, Reserved
from .sections import properties, at


class Unsupported(ValueError):
    pass


def rx(a):
    c,s = math.cos(a), math.sin(a)
    return np.array([[1,0,0],[0,c,-s],[0,s,c]])


def quat(q):
    w,x,y,z = q
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
        [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
        [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])


def valid_inertia(m, I):
    I = np.array(I)
    eig = np.linalg.eigvalsh(I)
    if m <= 0 or not np.allclose(I,I.T,atol=1e-15) or min(eig) <= 0 or max(eig) > sum(eig)-max(eig)+1e-14:
        raise ValueError('INVALID_MASS_OR_COM_INERTIA')


def normalize_inputs(design, discretization=None):
    """Return a physical Design and explicit model discretization.

    Legacy Segment.cells values are accepted only as a compatibility source.
    An explicit conflicting value is rejected instead of being selected silently.
    """
    parsed = design if isinstance(design, Design) else Design.model_validate(design)
    legacy = {c.id: c.cells for c in parsed.components if isinstance(c, Segment) and c.cells is not None}
    explicit = Discretization.model_validate(discretization) if discretization is not None else None
    segment_ids = {c.id for c in parsed.components if isinstance(c, Segment)}
    if explicit is not None:
        unknown = set(explicit.cells) - segment_ids
        missing = segment_ids - set(explicit.cells)
        if unknown: raise ValueError('DISCRETIZATION_UNKNOWN_SEGMENT: '+','.join(sorted(unknown)))
        if missing: raise ValueError('DISCRETIZATION_MISSING_SEGMENT: '+','.join(sorted(missing)))
        conflicts = {name for name,value in legacy.items() if explicit.cells.get(name) != value}
        if conflicts: raise ValueError('DISCRETIZATION_CONFLICT_WITH_LEGACY_CELLS: '+','.join(sorted(conflicts)))
        disc = explicit
        source = 'explicit_model_configuration'
    else:
        missing = segment_ids - set(legacy)
        if missing: raise ValueError('DISCRETIZATION_REQUIRED_FOR_SEGMENTS: '+','.join(sorted(missing)))
        disc = Discretization(cells=legacy)
        source = 'legacy_segment_cells_compatibility'
    # Segment.cells is excluded from serialization; re-validation yields the
    # canonical physical design with no model mesh values in its source data.
    physical = Design.model_validate(parsed.model_dump(mode='json'))
    return physical, disc, source


def resolve(design, discretization=None):
    d, discretization, discretization_source = normalize_inputs(design, discretization)
    all_ids = [c.id for c in d.components]+[t.id for t in d.tendons]+[a.id for a in d.actuators]+['fixed_base']
    if len(all_ids) != len(set(all_ids)): raise ValueError('DUPLICATE_ENTITY')
    if any(isinstance(c,Reserved) for c in d.components):
        raise Unsupported('DESCRIPTIVE_TOPOLOGY_ONLY: '+','.join(c.kind for c in d.components if isinstance(c,Reserved)))
    parts, maps, dofs, section_data = [], {}, [], {}
    physical = {c.id:c for c in d.components}

    def attach(a):
        if a.part == 'fixed_base':
            if a.s != 0: raise ValueError('BASE_HAS_NO_ALONG_SEGMENT_POSITION')
            return -1, np.array(a.position_m), quat(a.quaternion_wxyz)
        if a.part not in maps: raise ValueError('UNRESOLVED_ATTACHMENT: '+a.part)
        m = maps[a.part]
        if isinstance(physical[a.part],Segment):
            n = len(m['bodies']); i = min(int(a.s*n), n-1)
            b = m['bodies'][i]; part = parts[b]; S = rx(-part['section_axis_rad'])
            point = np.array([(a.s*n-i)*part['length_m'],0.,0.])+S@a.position_m
            return b, point, S@quat(a.quaternion_wxyz)
        if a.s != 0: raise ValueError('RIGID_ATTACHMENT_USES_LOCAL_POSITION: '+a.part)
        return m['bodies'][0], np.array(a.position_m), quat(a.quaternion_wxyz)

    remaining = list(d.components)
    while remaining:
        ready = [c for c in remaining if c.connection.part == 'fixed_base' or c.connection.part in maps]
        if not ready: raise ValueError('CYCLIC_OR_DANGLING_CONNECTIONS')
        for c in ready:
            parent, pos, R = attach(c.connection)
            if isinstance(c,Segment):
                for station in c.sections:
                    properties(station.section)
                bodies, joints = [], []
                cells = discretization.cells[c.id]
                ds = c.length_m/cells
                for i in range(cells):
                    section = at(c,(i+.5)/cells); prop = properties(section)
                    B = np.array(prop['bending_area_m4']); eig, V = np.linalg.eigh(B)
                    # Principal y,z axes, proper rotation. Preserve circular input orientation.
                    phi = section.angle_rad if abs(eig[1]-eig[0]) < 1e-12*max(eig) else math.atan2(V[1,0],V[0,0])
                    S = rx(phi); Q = S[1:,1:]
                    Ip = Q.T@B@Q
                    phys = c.physics; A = prop['area_m2']; mass = (phys.density_kg_m3*A if phys.mode == 'material' else phys.line_density_kg_m)*ds
                    rho_ds = mass/A
                    I = np.zeros((3,3)); I[0,0] = rho_ds*np.trace(B)
                    I[1:,1:] = rho_ds*Ip+np.eye(2)*mass*ds*ds/12
                    # Equivalent EI/damping explicitly use these section principal axes.
                    K = np.diag(Ip)*phys.young_pa/ds if phys.mode == 'material' else np.array(phys.bending_ei_nm2)/ds
                    C = np.array(phys.bending_viscosity_nm2_s)/ds
                    natural = Q.T@np.array(c.natural_curvature_rad_m)*ds
                    com = np.r_[ds/2, Q.T@prop['centroid_yz_m']]
                    name = f'{c.id}_cell_{i}'; ji = len(dofs)
                    names = [name+'_y',name+'_z']; dofs.extend(names); joints.extend(names)
                    localR = R@S if i == 0 else rx(phi-parts[-1]['section_axis_rad'])
                    body = dict(entity=name, component=c.id, parent=parent, position_m=pos.tolist(), rotation=localR.tolist(),
                        length_m=ds, section_axis_rad=phi, mass_kg=mass, com_local_m=com.tolist(), inertia_com_local_kg_m2=I.tolist(),
                        dofs=[ji,ji+1], stiffness_nm_rad=K.tolist(), damping_nm_s_rad=C.tolist(), natural_rad=natural.tolist(),
                        section=section.model_dump(mode='json'), section_properties=prop, envelope_halfsize_m=None)
                    valid_inertia(mass,I)
                    parts.append(body); bodies.append(len(parts)-1)
                    parent, pos = len(parts)-1, np.array([ds,0.,0.])
                maps[c.id] = dict(bodies=bodies,dofs=joints,kind=c.kind,length_m=c.length_m)
                section_data[c.id] = [parts[b]['section_properties'] for b in bodies]
            else:
                valid_inertia(c.mass_kg,c.inertia_com_local_kg_m2)
                if min(c.envelope_halfsize_m) <= 0: raise ValueError('INVALID_RIGID_ENVELOPE')
                if c.guide_holes:
                    if c.kind != 'guide' or c.hole_radius_m <= 0: raise ValueError('HOLES_REQUIRE_GUIDE_AND_RADIUS')
                    h = np.array(c.envelope_halfsize_m)
                    for p in c.guide_holes.values():
                        if abs(p[0]) > h[0]+1e-12 or np.any(np.abs(p[1:])+c.hole_radius_m > h[1:]):
                            raise ValueError('GUIDE_HOLE_OUTSIDE_ENVELOPE')
                    hp = list(c.guide_holes.values())
                    if any(np.linalg.norm(np.array(a[1:])-b[1:]) <= 2*c.hole_radius_m for i,a in enumerate(hp) for b in hp[i+1:]):
                        raise ValueError('GUIDE_HOLES_OVERLAP')
                parts.append(dict(entity=c.id,component=c.id,parent=parent,position_m=pos.tolist(),rotation=R.tolist(),length_m=0.,
                    section_axis_rad=0., mass_kg=c.mass_kg,com_local_m=list(c.com_local_m),inertia_com_local_kg_m2=c.inertia_com_local_kg_m2,
                    dofs=[],stiffness_nm_rad=[],damping_nm_s_rad=[],natural_rad=[],section=None,section_properties=None,
                    envelope_halfsize_m=c.envelope_halfsize_m))
                maps[c.id] = dict(bodies=[len(parts)-1],dofs=[],kind=c.kind)
            remaining.remove(c)
    if not dofs: raise Unsupported('SERIAL_BENDING_REQUIRES_FLEXIBLE_SEGMENT')
    # All flexible bodies must be ancestors of the designated tip (one serial chain).
    tip_body, tip_pos, _ = attach(d.tip)
    ancestry = set(); b = tip_body
    while b >= 0: ancestry.add(b); b = parts[b]['parent']
    if any(p['dofs'] and i not in ancestry for i,p in enumerate(parts)):
        raise Unsupported('BRANCHING_FLEXIBLE_CHAINS_NOT_IMPLEMENTED')
    routes = []
    for tendon in d.tendons:
        if tendon.points[0].role != 'start' or tendon.points[-1].role != 'anchor' or any(p.role != 'guide' for p in tendon.points[1:-1]):
            raise ValueError('ORDERED_START_GUIDES_ANCHOR_REQUIRED')
        points = []
        for point in tendon.points:
            a = point.attachment
            if point.hole:
                guide = physical.get(a.part)
                if not isinstance(guide,Rigid) or point.hole not in guide.guide_holes: raise ValueError('UNKNOWN_GUIDE_HOLE')
                if a.s or any(a.position_m): raise ValueError('HOLE_AND_POINT_OFFSET_ARE_EXCLUSIVE')
                if tendon.diameter_m >= 2*guide.hole_radius_m: raise ValueError('TENDON_TOO_LARGE_FOR_HOLE')
                a = a.model_copy(update={'position_m':guide.guide_holes[point.hole]})
            b,pos,_ = attach(a)
            points.append(dict(body=b,position_m=pos.tolist(),role=point.role,physical_binding=point.model_dump(mode='json')))
        routes.append(dict(entity=tendon.id,points=points,kp_n_m=tendon.length_servo_gain_n_m,
            pretension_n=tendon.pretension_n,force_limit_n=tendon.force_limit_n,diameter_m=tendon.diameter_m))
    B = np.zeros((len(routes),len(d.actuators))); owners = set()
    for j,a in enumerate(d.actuators):
        for t in a.transmission:
            ids = [t['entity'] for t in routes]
            if t.tendon not in ids or t.tendon in owners: raise ValueError('TENDON_NEEDS_EXACTLY_ONE_TRANSMISSION')
            owners.add(t.tendon); B[ids.index(t.tendon),j] = t.ratio*(a.drum_radius_m or 1.)
    if len(owners) != len(routes): raise ValueError('UNDRIVEN_TENDON')
    physical_source = d.model_dump(mode='json')
    model_source = discretization.model_dump(mode='json')
    result = dict(version='serial_bending_physics_v1',source_identity=digest(physical_source),
        design_identity=digest(physical_source),discretization_identity=digest(model_source),
        source_roles=dict(entity_design='family.design',physical_inputs='component.physics and tendon assumptions',
            model_discretization='family.discretization',discretization_source=discretization_source),
        discretization=model_source,parts=parts,tendons=routes,
        actuators=[a.model_dump(mode='json') for a in d.actuators],transmission=B.tolist(),dofs=dofs,entity_map=maps,
        tip=dict(body=tip_body,position_m=tip_pos.tolist()),section_quantities=section_data,
        applicability=dict(compilable=True,backends=['backend.matlab_spatial','backend.family_mujoco'],
            physics='serial rigid cells with two principal bending hinges; fixed rigid attachments; straight frictionless tendons',
            omitted=['axial stretch','shear','material torsion','friction','elastic rope','motor dynamics','self collision'],
            collision='section convex hull extrusions; holes filled for collision only; exact polygon/circular area moments; guide box envelope'))
    # Independent reference pose checks catch zero-length spans at the public boundary.
    from .geometry import geometry
    for part in parts:
        if part['section_properties'] is not None:
            outline = np.array(part['section_properties']['outer_yz_m'])
            outline = outline@rx(-part['section_axis_rad'])[1:,1:].T
            vertices = np.vstack([np.c_[np.full(len(outline),x),outline] for x in (0.,part['length_m'])])
        else:
            from itertools import product
            vertices = np.array(list(product(*[(-h,h) for h in part['envelope_halfsize_m']])))
        part['collision_vertices_m'] = vertices.tolist()
    g = geometry(result,np.zeros(len(dofs)))
    result['reference_lengths_m'] = g['lengths'].tolist()
    result['identity'] = digest(result)
    return result
