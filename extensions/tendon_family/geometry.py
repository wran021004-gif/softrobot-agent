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


def tendon_force_capability(configuration, binding, point, direction):
    """Box support of -Jlength.T T at one candidate-bound native configuration."""
    from .mujoco_analysis import NativeModel
    model=NativeModel(configuration)
    if (point['physics_identity']!=model.physics['identity'] or point['dof_order']!=model.order or
            point['tendon_order']!=model.tendons or binding['tendon_order']!=model.tendons):
        raise ValueError('TENDON_FORCE_EXACT_PHYSICS_AND_CHANNEL_BINDING_REQUIRED')
    q=np.asarray(point['qpos_rad'],dtype=float);w=np.asarray(direction,dtype=float)
    limits=np.asarray(model.limits,dtype=float)
    if q.shape!=(len(model.order),) or w.shape!=q.shape or not np.isfinite(q).all() or not np.isfinite(w).all() or not np.any(w):
        raise ValueError('FINITE_NONZERO_GENERALIZED_DIRECTION_AND_STATE_REQUIRED')
    if limits.shape!=(len(model.tendons),2) or not np.isfinite(limits).all() or np.any(limits[:,0]>limits[:,1]):
        raise ValueError('FINITE_NATIVE_TENSION_BOUNDS_REQUIRED')
    g=geometry(model.physics,q);jac=np.asarray(g['Jlength'])
    if jac.shape!=(len(model.tendons),len(model.order)) or not np.isfinite(jac).all():
        raise ValueError('FINITE_BOUND_TENDON_JACOBIAN_REQUIRED')
    coeff=-jac@w;chosen=np.where(coeff>=0,limits[:,1],limits[:,0]);support=float(coeff@chosen)
    strengths=np.linalg.norm(jac,axis=1);threshold=1e-12
    pairs=[]
    for i in range(len(model.tendons)):
        for j in range(i+1,len(model.tendons)):
            if strengths[i]>threshold and strengths[j]>threshold:
                pairs.append(dict(tendons=[model.tendons[i],model.tendons[j]],
                    cosine=float(jac[i]@jac[j]/(strengths[i]*strengths[j]))))
    pairs.sort(key=lambda row:abs(row['cosine']),reverse=True)
    facts=dict(candidate=binding['candidate'],configuration_identity=binding['effective_configuration_identity'],
        physics_identity=model.physics['identity'],qpos_rad=q.tolist(),coordinate_order=model.order,
        tendon_order=model.tendons,jacobian_m_rad=jac.tolist(),jacobian_shape=list(jac.shape),
        jacobian_source='extensions.tendon_family.geometry.geometry Jlength in compiled serial-hinge order',
        tension_bounds_n=limits.tolist(),bounds_source='compiled MuJoCo ideal-tension actuator ctrlrange',
        generalized_direction=w.tolist(),direction_norm=float(np.linalg.norm(w)),
        direction_unit='dimensionless weights in native hinge coordinate order',
        directional_support_nm=support,selected_tensions_n=chosen.tolist(),
        directional_coefficients_m_rad=coeff.tolist(),weak_tendon_indices=[i for i,v in enumerate(strengths) if v<=threshold],
        strongest_couplings=pairs[:3],scope='Instantaneous support of generalized tendon torque only at this configuration and input box; not tip force, global reachability, dynamic feasibility, or task acceptance.')
    return dict(status='computed',operation='tendon_force_capability_v1',binding=binding,
        operating_point=dict(name='standardized_initial_pretension',actual_time_s=point['actual_time_s'],qpos_rad=q.tolist()),
        tendon_force_capability=facts,proxy_values={},task_acceptance='unmeasured',
        internal_calculations=[dict(purpose='compiled actuator bounds and geometry Jacobian box support',model_builds=1,physics_steps=0,rollouts=0)])
