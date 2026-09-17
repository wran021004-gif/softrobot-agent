"""Area, centroid and central area moments in the section's (y,z) frame.

Green's theorem integrates simple polygon rings, subtracting holes. Jpolar is
reported only as an area moment; it is NOT a noncircular torsion constant.
"""
import math
import numpy as np
from .contracts import Section


def cross(a, b):
    return a[0]*b[1]-a[1]*b[0]


def intersects(a, b, c, d):
    ab, cd = b-a, d-c
    vals = [cross(ab, c-a), cross(ab, d-a), cross(cd, a-c), cross(cd, b-c)]
    if max(min(a[0], b[0]), min(c[0], d[0])) > min(max(a[0], b[0]), max(c[0], d[0])) + 1e-14:
        return False
    if max(min(a[1], b[1]), min(c[1], d[1])) > min(max(a[1], b[1]), max(c[1], d[1])) + 1e-14:
        return False
    return vals[0]*vals[1] <= 0 and vals[2]*vals[3] <= 0


def inside(p, ring):
    result = False
    for a, b in zip(ring, np.roll(ring, -1, axis=0)):
        if (a[1] > p[1]) != (b[1] > p[1]) and p[0] < (b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0]:
            result = not result
    return result


def ring_integral(points):
    p = np.asarray(points, float)
    if len(p) < 3 or len(set(map(tuple, p))) != len(p):
        raise ValueError('POLYGON_REQUIRES_DISTINCT_VERTICES')
    edges = list(zip(p, np.roll(p, -1, axis=0)))
    for i, (a, b) in enumerate(edges):
        for j, (c, d) in enumerate(edges):
            if j > i+1 and (i, j) != (0, len(p)-1) and intersects(a, b, c, d):
                raise ValueError('POLYGON_SELF_INTERSECTION')
    y, z = p.T; yy, zz = np.roll(p, -1, axis=0).T
    w = y*zz-yy*z
    A = w.sum()/2
    if abs(A) < 1e-18:
        raise ValueError('POLYGON_ZERO_AREA')
    first = np.array([((y+yy)*w).sum(), ((z+zz)*w).sum()])/6
    second = np.array([[((y*y+y*yy+yy*yy)*w).sum()/12,
                        ((2*y*z+y*zz+yy*z+2*yy*zz)*w).sum()/24],
                       [0., ((z*z+z*zz+zz*zz)*w).sum()/12]])
    second[1, 0] = second[0, 1]
    sign = np.sign(A)
    return A*sign, first*sign, second*sign


def properties(section):
    s = Section.model_validate(section)
    p = s.parameters
    if s.kind != 'polygon' and (s.outer_yz_m or s.holes_yz_m):
        raise ValueError('ANALYTIC_SECTION_CANNOT_ALSO_DECLARE_POLYGON_CONTOURS')
    keys = {'circle': {'radius_m'}, 'tube': {'outer_radius_m', 'inner_radius_m'},
            'ellipse': {'semi_y_m', 'semi_z_m'}, 'rectangle': {'width_y_m', 'height_z_m'}, 'polygon': set()}
    if set(p) != keys[s.kind] or any(v <= 0 for v in p.values()):
        raise ValueError('SECTION_DIMENSIONS: '+s.kind)
    center = np.zeros(2)
    theta = np.linspace(0, 2*np.pi, 49)[:-1]
    holes = []
    if s.kind in ('circle', 'tube'):
        r = p.get('radius_m', p.get('outer_radius_m')); ri = p.get('inner_radius_m', 0.)
        if ri >= r:
            raise ValueError('TUBE_INNER_MUST_BE_SMALLER_THAN_OUTER')
        A = np.pi*(r*r-ri*ri); C = np.eye(2)*np.pi*(r**4-ri**4)/4
        outer = np.c_[r*np.cos(theta), r*np.sin(theta)]
        if ri: holes = [np.c_[ri*np.cos(theta), ri*np.sin(theta)]]
    elif s.kind == 'ellipse':
        a, b = p['semi_y_m'], p['semi_z_m']
        A = np.pi*a*b; C = np.diag([A*a*a/4, A*b*b/4])
        outer = np.c_[a*np.cos(theta), b*np.sin(theta)]
    elif s.kind == 'rectangle':
        a, b = p['width_y_m'], p['height_z_m']
        A = a*b; C = np.diag([A*a*a/12, A*b*b/12])
        outer = np.array([[-a,-b],[a,-b],[a,b],[-a,b]])/2
    else:
        outer = np.array(s.outer_yz_m); holes = [np.array(h) for h in s.holes_yz_m]
        rings = [outer, *holes]
        integrals = [ring_integral(r) for r in rings]
        for i, ring in enumerate(rings):
            for other in rings[i+1:]:
                if any(intersects(a,b,c,d) for a,b in zip(ring,np.roll(ring,-1,axis=0)) for c,d in zip(other,np.roll(other,-1,axis=0))):
                    raise ValueError('POLYGON_RINGS_TOUCH_OR_INTERSECT')
        for i, hole in enumerate(holes):
            if not inside(hole[0],outer) or any(inside(hole[0],h) or inside(h[0],hole) for h in holes[i+1:]):
                raise ValueError('POLYGON_HOLE_OUTSIDE_OR_NESTED')
        A, first, second = integrals[0]
        for ah, fh, sh in integrals[1:]:
            A, first, second = A-ah, first-fh, second-sh
        if A <= 0: raise ValueError('POLYGON_NONPOSITIVE_AREA')
        center = first/A; C = second-A*np.outer(center,center)
    c, sn = math.cos(s.angle_rad), math.sin(s.angle_rad)
    R = np.array([[c,-sn],[sn,c]])
    center, C = R@center, R@C@R.T
    # bending about y,z: [[int z², -int yz],[-int yz,int y²]]
    B = np.array([[C[1,1],-C[0,1]],[-C[1,0],C[0,0]]])
    return dict(area_m2=float(A), centroid_yz_m=center.tolist(),
        area_covariance_m4=C.tolist(), bending_area_m4=B.tolist(), polar_area_m4=float(np.trace(C)),
        outer_yz_m=(outer@R.T).tolist(), holes_yz_m=[(h@R.T).tolist() for h in holes],
        torsion_constant_m4=None)


def at(segment, s):
    stations = segment.sections
    if stations[0].s != 0 or any(b.s <= a.s for a,b in zip(stations,stations[1:])):
        raise ValueError('SECTION_STATIONS_ORDERED_FROM_ZERO')
    left = max((x for x in stations if x.s <= s), key=lambda x:x.s)
    right = next((x for x in stations if x.s > s), left)
    if segment.interpolation == 'step' or left == right:
        return left.section
    a, b = left.section, right.section
    if a.kind != b.kind or set(a.parameters) != set(b.parameters) or a.kind == 'polygon':
        raise ValueError('LINEAR_SECTION_INTERPOLATION_REQUIRES_SAME_ANALYTIC_KIND')
    t = (s-left.s)/(right.s-left.s)
    return a.model_copy(update=dict(parameters={k:(1-t)*a.parameters[k]+t*b.parameters[k] for k in a.parameters},
        angle_rad=(1-t)*a.angle_rad+t*b.angle_rad))
