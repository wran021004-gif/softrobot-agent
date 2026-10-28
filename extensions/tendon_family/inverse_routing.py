"""Versioned route parameterizations compile to existing RoutePoint semantics."""
import numpy as np


def point(part,s,y,z,role):
    return dict(attachment=dict(part=part,s=s,position_m=[0.,float(y),float(z)]),role=role)


def route_pair(lengths,radii,stations=None,payload_anchor=False,plane_phase=np.pi/2):
    """radius values at global material knots; mirrored same-side routes."""
    knots=np.linspace(0,1,len(radii));total=sum(lengths);routes={}
    for index,sign in enumerate((1,-1)):
        def p(part,s,r,role):return point(part,s,sign*r*np.cos(plane_phase),sign*r*np.sin(plane_phase),role)
        route=[p('fixed_base',0.,radii[0],'start')]
        if stations is not None:
            cumulative=0.
            for i,L in enumerate(lengths):
                for s in stations:
                    u=(cumulative+s*L)/total;r=np.interp(u,knots,radii)
                    route.append(p('segment_'+str(i),s,r,'guide'))
                cumulative+=L
        route.append(p('payload' if payload_anchor else 'segment_'+str(len(lengths)-1),0. if payload_anchor else 1.,radii[-1],'anchor'))
        routes[str(index)]=route
    return routes


def generation(lengths=(.28,),young=None,cells=24,width=.006,height=.006,radii=(.084,.004),stations=None,payload_anchor=True):
    young=young or [2e6]*len(lengths)
    segments={}
    for i,L in enumerate(lengths):
        section=dict(kind='rectangle',parameters=dict(width_y_m=width,height_z_m=height),angle_rad=0.)
        segments[str(i)]=dict(length_m=L,young_pa=young[i],cells=cells,sections=[section]*(1 if i==0 else 2))
    return dict(segment_count=len(lengths),tendon_count=2,segments=segments,
        spans=[dict(last_segment=len(lengths)-1,count=2,phase_rad=float(np.pi/2),radius_m=max(.0035,radii[-1]),guide_s=[])],
        route_overrides=route_pair(lengths,radii,stations,payload_anchor))


def guided_generation(lengths=(.28,),young=None,cells=24,zbase=.04,yoffset=.007,end_factor=1.,viscosity=.00006):
    """Four quadrant mirror routes with physical boundary holes and payload anchors.

    Taper is a design initialization; native Jacobian matching owns its quality.
    Rigid boundary lengths and measured payload-tip offset are included.
    """
    g=generation(lengths,young,cells);g['tendon_count']=4;g['spans'][0].update(count=4,radius_m=.018)
    for seg in g['segments'].values():seg['physical_parameters']=dict(viscosity_y_nm2_s=viscosity,viscosity_z_nm2_s=viscosity)
    total=sum(lengths)+.014*(len(lengths)-1);tip=total+.014
    holes={};routes={};stations=np.arange(1,23)/23 if len(lengths)==1 and cells==24 else np.arange(1,10)/10 if cells>=12 else [.25,.5,.75]
    for k,(sy,sz) in enumerate(((1,1),(1,-1),(-1,1),(-1,-1))):
        def p(part,s,x,role):return point(part,s,sy*yoffset,sz*zbase*(tip-x)/tip*end_factor if part=='payload' else sz*zbase*(tip-x)/tip,role)
        route=[p('fixed_base',0.,0.,'start')];x=0.
        for i,L in enumerate(lengths):
            if i:
                gid='guide_'+str(i);hole='tendon_'+str(k)+'_hole'
                holes.setdefault(gid,{})[hole]=[0.,sy*yoffset,sz*zbase*(tip-(x-.014))/tip]
                route.append(dict(attachment=dict(part=gid,s=0.,position_m=[0.,0.,0.]),role='guide',hole=hole))
            for u in stations:route.append(p('segment_'+str(i),float(u),x+u*L,'guide'))
            x+=L+.014
        route.append(p('payload',0.,total,'anchor'));routes[str(k)]=route
    g.update(route_overrides=routes,guide_hole_positions_m=holes);return g
