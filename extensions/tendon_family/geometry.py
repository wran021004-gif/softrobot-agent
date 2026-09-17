"""Static geometry/virtual work for compilation, control and verification, no dynamics."""
import numpy as np
from .compiler import quat


def geometry(physics, q, mount=None):
    n = len(q); baseR = np.eye(3) if mount is None else quat(mount['quaternion_wxyz'])
    basep = np.zeros(3) if mount is None else np.array(mount['position_m'])
    base = dict(R=baseR,p=basep,A=np.zeros((3,n)),J=np.zeros((3,n)))
    bodies = []
    for p in physics['parts']:
        parent = base if p['parent'] < 0 else bodies[p['parent']]
        r = parent['R']@p['position_m']; origin = parent['p']+r
        J = parent['J']+np.cross(parent['A'].T,r).T
        R = parent['R']@p['rotation']; A = parent['A'].copy()
        for local,k in enumerate(p['dofs']):
            axis = R[:,local+1].copy(); A[:,k] = axis
            c,s = np.cos(q[k]),np.sin(q[k])
            rot = np.array([[c,0,s],[0,1,0],[-s,0,c]]) if local == 0 else np.array([[c,-s,0],[s,c,0],[0,0,1]])
            R = R@rot
        bodies.append(dict(R=R,p=origin,A=A,J=J))
    def point(p):
        b = base if p['body'] < 0 else bodies[p['body']]
        r = b['R']@p['position_m']
        return b['p']+r,b['J']+np.cross(b['A'].T,r).T
    routes, lengths, jl = [], [], []
    for t in physics['tendons']:
        ps,js = zip(*(point(p) for p in t['points']))
        delta = np.diff(ps,axis=0); norms = np.linalg.norm(delta,axis=1)
        if min(norms) <= 1e-12: raise ValueError('DEGENERATE_TENDON_SPAN')
        routes.append(np.array(ps)); lengths.append(sum(norms))
        jl.append(np.einsum('ki,kij->j',delta/norms[:,None],np.diff(js,axis=0)))
    tip,Jtip = point(physics['tip'])
    return dict(bodies=bodies,routes=routes,lengths=np.array(lengths),Jlength=np.array(jl),tip=tip,Jtip=Jtip)
