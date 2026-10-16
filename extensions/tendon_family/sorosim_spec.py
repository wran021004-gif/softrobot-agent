"""Canonical family conversion; no independent robot defaults or model schema."""
import numpy as np
from tools.state_io import digest
from .contracts import SorosimModelParameters, Design, Segment, Rigid
from .compiler import resolve, quat, Unsupported
from .gvs_basis import resolve_basis, basis_matrix, basis_quadrature
from .sections import at, properties
from .gvs import _stiffness_and_damping
from .sorosim_session import UPSTREAM


def specification(design, discretization, assembly, *, basis=None, solver=None):
    """Derived integration data, bound to the authoritative compiler and design."""
    from .contracts import SorosimSolver
    from extensions.experiment_dynamics.contracts import Assembly
    design = Design.model_validate(design)
    assembly = Assembly.model_validate(assembly)
    settings = SorosimSolver.model_validate(solver or {})
    physics = resolve(design, discretization)
    resolved = resolve_basis(design, basis)
    if assembly.external_forces:
        raise Unsupported('SOROSIM_UNSUPPORTED_EXTERNAL_APPLIED_FORCES')
    components = {c.id:c for c in design.components}
    chain = []; current = design.tip.part
    while current != 'fixed_base':
        chain.append(current); current=components[current].connection.part
    chain.reverse()
    if set(chain) != set(components):
        raise Unsupported('SOROSIM_REQUIRES_SERIAL_TIP_CHAIN')
    indices = {name:i+1 for i,name in enumerate(chain)}
    segments = {s.segment:s for s in resolved.segments}
    links = []; scales=[]
    for name in chain:
        c = components[name]; connection=c.connection
        if connection.part != 'fixed_base':
            parent=components[connection.part]
            if connection.s != (1. if isinstance(parent,Segment) else 0.):
                raise Unsupported('SOROSIM_UNSUPPORTED_INTERIOR_COMPONENT_CONNECTION: '+name)
        transform=np.eye(4); transform[:3,:3]=quat(connection.quaternion_wxyz)
        transform[:3,3]=connection.position_m
        entry=dict(id=name,kind=c.kind,parent=indices.get(connection.part,0),connection=transform.tolist())
        if isinstance(c, Segment):
            local=segments[name]; knots=local.knots
            nodes_weights=list(basis_quadrature(local,settings.gauss_per_interval))
            samples={float(x):float(w)*c.length_m for x,w in nodes_weights}
            extra=set(knots)|{s.s for s in c.sections}|{0.,1.}
            for tendon in design.tendons:
                extra.update(p.attachment.s for p in tendon.points if p.attachment.part==name)
            if design.tip.part==name: extra.add(design.tip.s)
            for x in extra: samples.setdefault(x,0.)
            nodes=sorted(samples); matrices=[]; elastic=[]; viscous=[]; natural=[]
            for x in nodes:
                prop=properties(at(c,x)); area=prop['area_m2']
                if np.linalg.norm(prop['centroid_yz_m'])>1e-15:
                    raise Unsupported('SOROSIM_UNSUPPORTED_ECCENTRIC_DISTRIBUTED_SECTION: '+name)
                rho=(c.physics.density_kg_m3 if c.physics.mode=='material' else c.physics.line_density_kg_m/area)
                inertia=np.zeros((3,3)); inertia[0,0]=rho*prop['polar_area_m4']
                inertia[1:,1:]=rho*np.asarray(prop['bending_area_m4'])
                mass=np.zeros((6,6));mass[:3,:3]=inertia;mass[3:,3:]=np.eye(3)*rho*area
                stiffness,damping=_stiffness_and_damping(c,x)
                e=np.zeros((6,6));e[1:3,1:3]=stiffness
                v=np.zeros((6,6));v[1:3,1:3]=damping
                matrices.append(mass.tolist());elastic.append(e.tolist());viscous.append(v.tolist())
                natural.append([0.,*c.natural_curvature_rad_m,0.,0.,0.])
            probes=np.linspace(0,1,max(17,4*len(knots)))
            reconstruction=np.vstack([basis_matrix(resolved,local,x) for x in probes])
            if np.linalg.matrix_rank(reconstruction) != 2*len(knots):
                raise Unsupported('SOROSIM_RANK_DEFICIENT_BASIS: '+name)
            scales.extend([c.length_m]*(2*len(knots)))
            entry.update(length=c.length_m,start=local.start,knots=list(knots),
                basis_strategy=resolved.specification.strategy,nodes=nodes,weights=[samples[x] for x in nodes],
                mass=matrices,elastic=elastic,viscous=viscous,natural=natural,
                canonical_sections=[s.model_dump(mode='json') for s in c.sections],
                canonical_physics=c.physics.model_dump(mode='json'))
        elif isinstance(c,Rigid):
            entry.update(mass_kg=c.mass_kg,com=list(c.com_local_m),inertia=c.inertia_com_local_kg_m2)
        else:
            raise Unsupported('SOROSIM_UNSUPPORTED_COMPONENT: '+c.kind)
        links.append(entry)

    def attachment(a, override=None):
        return dict(link=indices.get(a.part,0),s=a.s,offset=list(a.position_m if override is None else override),
                    rotation=quat(a.quaternion_wxyz).tolist())
    routes=[]
    for tendon in design.tendons:
        route=[]
        for point in tendon.points:
            offset=components[point.attachment.part].guide_holes[point.hole] if point.hole else None
            route.append(dict(attachment(point.attachment,offset),role=point.role))
        routes.append(dict(id=tendon.id,points=route,force_limit_n=tendon.force_limit_n))
    mount_rotation=quat(assembly.mount.quaternion_wxyz)
    result=dict(version='sorosim_compiled_spec_v1',model='model.sorosim_gvs@1.0.0',
        upstream=UPSTREAM,physics_identity=physics['identity'],design_identity=physics['design_identity'],
        resolved_basis=resolved.model_dump(mode='json'),coordinate_order=resolved.coordinate_order,
        coordinate_scale=scales,links=links,routes=routes,tip=attachment(design.tip),
        transmission=physics['transmission'],tendon_order=[t['entity'] for t in physics['tendons']],
        gravity=(mount_rotation.T@assembly.environment.gravity_m_s2).tolist(),
        mount_rotation=mount_rotation.tolist(),mount_position=list(assembly.mount.position_m),solver=settings.model_dump(mode='json'),
        units=dict(q='rad/m',qdot='rad/(m*s)',force='N*m^2',length='m'),
        convention='q_s=T*q_g; tau_g=T^T*tau_s; M_g=T^T*M_s*T; endpoint chords; actual geometric curvature')
    result['identity']=digest(result)
    return result


class SorosimModel:
    def __init__(self, parameters):
        self.parameters = SorosimModelParameters.model_validate(parameters)

    def convert(self, design, discretization, assembly, *, solver=None):
        from .contracts import SorosimSolver
        settings=SorosimSolver.model_validate(solver or {})
        if solver is not None and settings.gauss_per_interval!=self.parameters.gauss_per_interval:
            raise ValueError('SOROSIM_INTEGRATION_CONFIGURATION_CONFLICT')
        settings=settings.model_copy(update=dict(gauss_per_interval=self.parameters.gauss_per_interval))
        return specification(design,discretization,assembly,basis=self.parameters.basis,solver=settings)

    def evaluate(self, session, q, qd, u, qdd=None, *, derivatives=False):
        return session.evaluate('derivatives' if derivatives else 'dynamics',dict(q=list(q),qd=list(qd),
            u=list(u),qdd=[] if qdd is None else list(qdd)))
