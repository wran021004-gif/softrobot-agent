"""Straight cable swept-radius versus compiled convex bodies, at supplied poses."""
import numpy as np
import mujoco
from scipy.spatial import ConvexHull


def interval(a,b,planes,radius):
    lo,hi=0.,1.
    for plane in planes:
        n=plane[:3];v=float(n@(b-a));c=float(n@a+plane[3]-radius)
        if abs(v)<1e-14:
            if c>0:return None
        elif v>0:hi=min(hi,-c/v)
        else:lo=max(lo,-c/v)
        if lo>hi:return None
    return (lo,hi) if hi-lo>1e-9 else None


def intersections(a,b,planes,radii):
    C=a@planes[:,:3].T+planes[:,3]-np.asarray(radii)[:,None]
    V=(b-a)@planes[:,:3].T
    ratio=np.divide(-C,V,out=np.zeros_like(C),where=abs(V)>1e-14)
    lo=np.maximum(0.,np.max(np.where(V < -1e-14,ratio,-np.inf),axis=1))
    hi=np.minimum(1.,np.min(np.where(V > 1e-14,ratio,np.inf),axis=1))
    valid=(hi-lo>1e-9)&~np.any((abs(V)<=1e-14)&(C>0),axis=1)
    return lo,hi,valid


def validate_routes(native,poses):
    m=native.model;d=mujoco.MjData(m);parts=native.physics['parts'];issues=[];checks=0
    hulls=[ConvexHull(p['collision_vertices_m']).equations for p in parts]
    spans=[];radii=[]
    for ti,t in enumerate(native.physics['tendons']):
        if t['points'][0]['body']!=-1:issues.append(dict(tendon=ti,reason='not_base_only'))
        for k in range(len(t['points'])-1):spans.append((ti,k));radii.append(t['diameter_m']/2)
    for pose_index,q in enumerate(poses):
        d.qpos[:]=q;mujoco.mj_forward(m,d);routes=[]
        for t in native.physics['tendons']:
            ps=[]
            for point in t['points']:
                bid=native.base if point['body']<0 else native.body_ids[point['body']]
                ps.append(d.xpos[bid]+d.xmat[bid].reshape(3,3)@point['position_m'])
            routes.append(ps)
        aa=np.array([routes[ti][k] for ti,k in spans]);bb=np.array([routes[ti][k+1] for ti,k in spans])
        for bi,part in enumerate(parts):
            bid=native.body_ids[bi];R=d.xmat[bid].reshape(3,3)
            pa=(aa-d.xpos[bid])@R;pb=(bb-d.xpos[bid])@R
            lower,upper,hits=intersections(pa,pb,hulls[bi],radii);checks+=len(spans)
            for idx in np.flatnonzero(hits):
                ti,span=spans[idx];t=native.physics['tendons'][ti];end=t['points'][span+1]
                if end['body']==bi and end['role']=='anchor' and upper[idx]>=1-1e-8:continue
                allowed=False
                for k in (span,span+1):
                    point=t['points'][k];binding=point['physical_binding']
                    if point['body']!=bi or not binding.get('hole'):continue
                    physical=next(c for c in native.design_components if c['id']==part['component'])
                    ends=[pa[idx]+u*(pb[idx]-pa[idx]) for u in (lower[idx],upper[idx])]
                    if max(np.linalg.norm((v-point['position_m'])[1:]) for v in ends)+radii[idx]<=physical['hole_radius_m']:allowed=True
                if not allowed:issues.append(dict(pose=pose_index,tendon=ti,span=span,body=part['entity'],reason='cable_solid_intersection',interval=[float(lower[idx]),float(upper[idx])]))
    return dict(method='route_geometry_validation_v1',status='legal_at_checked_poses' if not issues else 'illegal',issues=issues,
        poses=len(poses),segment_body_checks=checks,all_base_only=all(t['points'][0]['body']==-1 for t in native.physics['tendons']),
        limitations=['Convex compiled body envelopes; supplied poses only, no continuous collision engine.',
        'Friction, cable/cable contact, self contact and manufacturing of flexible offset guides not modeled.',
        'Fixed-base installation sites belong to the same rigid base; no external world anchors.'])
