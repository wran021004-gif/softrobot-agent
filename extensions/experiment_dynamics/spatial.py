"""Coupled 16-DOF rigid-link dynamics, independent of simulation engines.

M=sum(m Jv.T Jv + Jw.T I_world Jw).
b=sum(m Jv.T a_bias + Jw.T (I_world alpha_bias + w x I_world w)).
qdd=M^-1(tau_gravity + tau_elastic + tau_damping - Jlength.T T
         + tau_contact + tau_external - b).
Axes are ordered Ry(q_y) Rz(q_z) at each link origin. No axial/twist DOF.
"""
import numpy as np


def rotation_y(q):
    c, s = np.cos(q), np.sin(q)
    return np.array(((c, 0., s), (0., 1., 0.), (-s, 0., c)))


def rotation_z(q):
    c, s = np.cos(q), np.sin(q)
    return np.array(((c, -s, 0.), (s, c, 0.), (0., 0., 1.)))


def mount_rotation(mount):
    w, x, y, z = mount.quaternion_wxyz
    return np.array(((1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)),
                     (2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)),
                     (2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y))))


class SpatialModel:
    def __init__(self, physics, scene, parameters):
        self.physics, self.scene, self.parameters = physics, scene, parameters
        self.n = 2*len(physics.parts)
        self.base_R = mount_rotation(scene.assembly.mount)
        self.base_p = np.array(scene.assembly.mount.position_m)
        self.gravity = np.array(scene.assembly.environment.gravity_m_s2)
        self.floor = next(o for o in scene.assembly.environment.objects if o.name == scene.assembly.floor_id)
        self.k = np.array([x for p in physics.parts for x in p.stiffness_nm_rad])
        self.c = np.array([x for p in physics.parts for x in p.damping_nm_s_rad])
        self.natural = np.array([x for p in physics.parts for x in p.natural_rad])

    def geometry(self, q, v=None):
        v = np.zeros(self.n) if v is None else v
        R, p = self.base_R.copy(), self.base_p.copy()
        A, Jp = np.zeros((3, self.n)), np.zeros((3, self.n))
        w, alpha, ab = np.zeros(3), np.zeros(3), np.zeros(3)
        nodes, node_J, links = [p.copy()], [Jp.copy()], []
        routes = [[p+R@np.array((0., *t.offset_yz_m))] for t in self.physics.tendons]
        route_J = [[Jp.copy()] for _ in routes]
        for i, part in enumerate(self.physics.parts):
            for j, (local, rot) in enumerate(((np.array((0.,1.,0.)), rotation_y), (np.array((0.,0.,1.)), rotation_z))):
                index = 2*i+j
                axis = R@local
                A[:, index] = axis
                alpha = alpha + np.cross(w, axis)*v[index]
                w = w + axis*v[index]
                R = R@rot(q[index])
            rcom = R@np.array(part.com_local_m)
            Jcom = Jp + np.cross(A.T, rcom).T
            acom = ab + np.cross(alpha, rcom) + np.cross(w, np.cross(w, rcom))
            I = R@np.array(part.inertia_com_local_kg_m2)@R.T
            links.append(dict(com=p+rcom, J=Jcom, A=A.copy(), inertia=I, w=w.copy(), alpha=alpha.copy(), ab=acom, R=R.copy()))
            r = R@np.array((part.length_m, 0., 0.))
            p = p+r
            Jp = Jp+np.cross(A.T, r).T
            ab = ab+np.cross(alpha, r)+np.cross(w, np.cross(w, r))
            nodes.append(p.copy()); node_J.append(Jp.copy())
            for k, tendon in enumerate(self.physics.tendons):
                offset = R@np.array((0., *tendon.offset_yz_m))
                routes[k].append(p+offset)
                route_J[k].append(Jp+np.cross(A.T, offset).T)
        routes, route_J = np.array(routes), np.array(route_J)
        delta, dJ = np.diff(routes, axis=1), np.diff(route_J, axis=1)
        lengths = np.linalg.norm(delta, axis=2)
        if np.any(lengths <= 1e-12):
            raise ValueError('DEGENERATE_TENDON_SPAN')
        Jlength = np.einsum('tka,tkaj->tj', delta/lengths[:,:,None], dJ)
        return dict(nodes=np.array(nodes), node_J=np.array(node_J), links=links,
                    routes=routes, lengths=lengths.sum(axis=1), Jlength=Jlength)

    def terms(self, q, v, command, external):
        g = self.geometry(q, v)
        M, bias, gravity, applied = np.zeros((self.n,self.n)), np.zeros(self.n), np.zeros(self.n), np.zeros(self.n)
        for part, link in zip(self.physics.parts, g['links']):
            J, A, I, w = (link[k] for k in ('J','A','inertia','w'))
            M += part.mass_kg*J.T@J + A.T@I@A
            bias += part.mass_kg*J.T@link['ab'] + A.T@(I@link['alpha']+np.cross(w,I@w))
            gravity += part.mass_kg*J.T@self.gravity
            applied += J.T@np.array(external.get(part.entity, (0.,0.,0.)))
        tension = np.clip(np.array([t.kp_n_m for t in self.physics.tendons])*(g['lengths']-command),
                          0., [t.force_limit_n for t in self.physics.tendons])
        drive = -g['Jlength'].T@tension
        spring, damping = -self.k*(q-self.natural), -self.c*v
        contact, normal, gaps = np.zeros(self.n), [], []
        for i, part in enumerate(self.physics.parts):
            total = 0.
            gaps.append(min(g['nodes'][i:i+2,2])-part.radius_m-self.floor.position_m[2])
            for j in (i,i+1):
                penetration = self.floor.position_m[2]+part.radius_m-g['nodes'][j,2]
                if penetration > 0:
                    J = g['node_J'][j,2]
                    force = .5*max(0., self.parameters.contact_stiffness_n_m*penetration-
                        self.parameters.contact_damping_n_s_m*min(1.,penetration/self.parameters.contact_taper_m)*(J@v))
                    total += force; contact += J*force
            normal.append(total)
        return dict(geometry=g, mass=M, bias=bias, gravity=gravity, external=applied, tension=tension,
            drive=drive, spring=spring, damping=damping, contact=contact, normal=np.array(normal), gaps=np.array(gaps))

    def acceleration(self, q, v, command, external):
        a = self.terms(q,v,command,external)
        return np.linalg.solve(a['mass'], sum(a[k] for k in ('gravity','external','drive','spring','damping','contact'))-a['bias'])
