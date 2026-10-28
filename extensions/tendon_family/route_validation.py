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


def validate_routes(native,poses):
    m=native.model;d=mujoco.MjData(m);parts=native.physics['parts'];issues=[];minimum=None;checks=0
    hulls=[ConvexHull(p['collision_vertices_m']).equations for p in parts]
    for pose_index,q in enumerate(poses):
        d.qpos[:]=q;mujoco.mj_forward(m,d)
        for ti,t in enumerate(native.physics['tendons']):
            if t['points'][0]['body']!=-1:issues.append(dict(tendon=ti,reason='not_base_only'))
            ps=[native.point(d,p)[0] for p in t['points']]
            for span,(a,b) in enumerate(zip(ps,ps[1:])):
                for bi,part in enumerate(parts):
                    bid=native.body_ids[bi];R=d.xmat[bid].reshape(3,3);pa=R.T@(a-d.xpos[bid]);pb=R.T@(b-d.xpos[bid])
                    hit=interval(pa,pb,hulls[bi],t['diameter_m']/2);checks+=1
                    if hit is None:continue
                    # A real solid anchor may terminate inside its owning body.
                    end=t['points'][span+1]
                    if end['body']==bi and end['role']=='anchor' and hit[1]>=1-1e-8:continue
                    holes=[]
                    for k in (span,span+1):
                        point=t['points'][k];binding=point['physical_binding']
                        if point['body']==bi and binding.get('hole'):holes.append(np.array(point['position_m']))
                    allowed=False
                    for center in holes:
                        physical=next(c for c in native.design_components if c['id']==part['component'])
                        # Compiler already checks hole identity/overlap/outer envelope.
                        hr=physical['hole_radius_m']
                        ends=[pa+u*(pb-pa) for u in hit]
                        if max(np.linalg.norm((v-center)[1:]) for v in ends)+t['diameter_m']/2<=hr:allowed=True
                    if not allowed:issues.append(dict(pose=pose_index,tendon=ti,span=span,body=part['entity'],reason='cable_solid_intersection',interval=list(hit)))
    return dict(method='route_geometry_validation_v1',status='legal_at_checked_poses' if not issues else 'illegal',issues=issues,
        poses=len(poses),segment_body_checks=checks,all_base_only=all(t['points'][0]['body']==-1 for t in native.physics['tendons']),
        limitations=['Convex compiled body envelopes; supplied poses only, no continuous collision engine.',
        'Friction, cable/cable contact, self contact and manufacturing of flexible offset guides not modeled.',
        'Fixed-base installation sites belong to the same rigid base; no external world anchors.'])
