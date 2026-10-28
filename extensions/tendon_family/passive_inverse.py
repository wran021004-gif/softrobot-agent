"""Local inverse passive mechanics on native 3D equilibria; no Store or acceptance."""
import numpy as np
from scipy.linalg import null_space, eigh
from .passive import material_point
from .passive_equilibrium import StaticProblem, tangent, solve


def row_match(Jlength,Jtip):
    """Scale-free row-space coverage, including both horizontal task rows."""
    sv=np.linalg.svd(Jlength,compute_uv=False)
    rank=int(np.sum(sv>max(1e-12,sv[0]*1e-8))) if len(sv) else 0
    P=np.linalg.pinv(Jlength,rcond=1e-8)@Jlength
    errors=[float(np.linalg.norm(j-j@P)/max(np.linalg.norm(j),1e-15)) for j in Jtip[:2]]
    return dict(rank=rank,singular_values=sv.tolist(),condition=float(sv[0]/sv[rank-1]) if rank else None,
                horizontal_row_residuals=errors)


def matching(native,q):
    p=StaticProblem(native);d=p.at(q);Jl=p.jacobian(q);Jtip=native.point(d,native.physics['tip'])[1]
    target=row_match(Jl,Jtip)
    # Four piecewise-curvature groups form a cheap mechanism prototype on the
    # actual native Jacobians. It is not a separate final acceptance model.
    B=np.zeros((native.model.nv,8));cells=[part for part in native.physics['parts'] if part['dofs']]
    for i,part in enumerate(cells):
        group=min(3,4*i//len(cells))
        for axis,k in enumerate(part['dofs']):B[k,2*group+axis]=part['length_m']
    Z=null_space((Jtip@B)[:2]);H,_=p.hessian(np.array(q),np.zeros(native.model.ntendon))
    response=[]
    for s in native.protocol['search_s']:
        j=native.point(p.at(q),material_point(native.physics,s))[1][0]@B
        K=Z.T@B.T@H@B@Z
        v=Z@np.linalg.solve(K,Z.T@j) if K.size and np.min(np.linalg.eigvalsh(K))>0 else np.zeros(8)
        response.append(dict(s=s,curvature_coordinates=v.tolist(),point_dx_per_n=float(j@v),
            required_tendon_gradient_changes=(Jl@B@v).tolist()))
    return dict(method='tendon_jacobian_matching_v1',pose='supplied geometric operating pose; not a new equilibrium certificate',
        **target,Jlength=Jl.tolist(),Jtip=Jtip.tolist(),tip_row_coefficients=(Jtip[:2]@np.linalg.pinv(Jl)).tolist(),
        low_dimensional_prototype=dict(method='four_piecewise_curvature_groups_v1',basis=B.tolist(),tip_nullspace=Z.tolist(),responses=response),
        numerical_cost=p.cost,limitations='All-row coverage does not imply tension activation or force excitation; modal and nonlinear tools must check these separately.')


def modal_target(native,equilibrium,locations):
    if equilibrium['status']!='qualified_local_minimum':raise ValueError('QUALIFIED_EQUILIBRIUM_REQUIRED')
    q=np.array(equilibrium['qpos']);p=StaticProblem(native);d=p.at(q)
    Jtip=native.point(d,native.physics['tip'])[1];Jl=p.jacobian(q)
    H=np.array(equilibrium['H']);active=np.array(equilibrium['active']);positive=np.array(equilibrium['positive'])
    # A: ideal zero-tip kinematic directions, independent of actual cable feasibility.
    Z=null_space(Jtip[:2]);K=Z.T@H@Z;ideal=[]
    for s in locations:
        j=native.point(d,material_point(native.physics,s))[1][0]
        if np.min(np.linalg.eigvalsh(K))<=0:
            ideal.append(dict(s=s,status='no_positive_energy_metric'));continue
        v=Z@np.linalg.solve(K,Z.T@j);scale=max(abs(j@v),1e-15);v=v/scale*.01
        ideal.append(dict(s=s,dq_for_10mm=v.tolist(),tip_xy_m=float(np.linalg.norm(Jtip[:2]@v)),
            elastic_lagrangian_energy_j=float(.5*v@H@v),
            positive_length_changes_m=(Jl[positive]@v).tolist(),boundary_length_changes_m=(Jl[active&~positive]@v).tolist(),
            unilateral_direction_feasible=bool(np.max(abs(Jl[positive]@v),initial=0)<1e-8 and np.max(Jl[active&~positive]@v,initial=0)<=1e-8)))
    # B/C: actual one-sided active cone and actual material-point generalized force.
    response=tangent(native,equilibrium,.5,0.,locations)
    return dict(method='passive_modal_target_v1',model='native_3d_bending_cells',
        A_ideal_tip_null_modes=ideal,B_C_unilateral_force_response=response,
        matching_all=row_match(Jl,Jtip),matching_positive=row_match(Jl[positive],Jtip),
        active=active.tolist(),positive=positive.tolist(),slack=(~active).tolist(),Jtip=Jtip.tolist(),Jlength=Jl.tolist(),
        Jpoints={str(s):native.point(d,material_point(native.physics,s))[1].tolist() for s in locations},
        H=H.tolist(),positive_nullspace=null_space(Jl[positive]).tolist(),
        numerical_cost={k:p.cost[k]+response['numerical_cost'].get(k,0) for k in p.cost},
        scope='A is kinematics only; B/C is local unilateral force excitation, finite load requires nonlinear solve and independent dynamics.')


def design_sensitivity(native,equilibrium,minus,plus,parameter,step,s,force):
    """Normalized parameter u, supplied models at u +/- step, fixed topology."""
    if any(n.model.nv!=native.model.nv or n.model.ntendon!=native.model.ntendon for n in (minus,plus)):
        return dict(method='passive_design_sensitivity_v1',status='not_applicable',reason='discrete_topology_change',parameter=parameter)
    q=np.array(equilibrium['qpos']);lam=np.array(equilibrium['tensions_n']);a=np.array(equilibrium['active'])
    regular=equilibrium['status']=='qualified_local_minimum' and equilibrium['LICQ'] and equilibrium['strict_complementarity']
    pm=StaticProblem(minus,s,force);pp=StaticProblem(plus,s,force)
    fm=pm.gradient(q)+pm.jacobian(q).T@lam;fp=pp.gradient(q)+pp.jacobian(q).T@lam
    dc=(pp.constraint(q)-pm.constraint(q))/(2*step)
    J=np.array(equilibrium['Jlength'])[a];H=np.array(equilibrium['H'])
    M=np.block([[H,J.T],[J,np.zeros((len(J),len(J)))]])
    condition=float(np.linalg.cond(M));regular=regular and condition<1e12
    result=dict(method='passive_design_sensitivity_v1',parameter=parameter,coordinate='dimensionless normalized parameter u',
        active=a.tolist(),LICQ=equilibrium['LICQ'],strict_complementarity=equilibrium['strict_complementarity'],KKT_condition=condition if np.isfinite(condition) else None,
        step=step,force_n=force,s=s,status='regular_implicit_gradient' if regular else 'not_applicable',
        reason=None if regular else 'LICQ, strict complementarity or KKT regularity failed; use resolved finite differences')
    if regular:
        z=np.linalg.solve(M,-np.r_[(fp-fm)/(2*step),dc[a]])
        p=StaticProblem(native,s,force);d=p.at(q);rows={}
        for name,b in [('tip',native.physics['tip']),('point',material_point(native.physics,s))]:
            bp=plus.physics['tip'] if name=='tip' else material_point(plus.physics,s)
            bm=minus.physics['tip'] if name=='tip' else material_point(minus.physics,s)
            explicit=(plus.point(pp.at(q),bp)[0]-minus.point(pm.at(q),bm)[0])/(2*step)
            rows[name]=(native.point(d,b)[1]@z[:len(q)]+explicit).tolist()
        residual_derivative=np.array(equilibrium['Jlength'])@z[:len(q)]+dc
        dtension=np.zeros(native.model.ntendon);dtension[a]=z[len(q):]
        result.update(dq_du=z[:len(q)].tolist(),dtension_du=dtension.tolist(),dposition_du=rows,
            dlength_residual_du=residual_derivative.tolist(),dslack_margin_du=(-residual_derivative).tolist(),
            tension_margin_n=[t['force_limit_n']-v for t,v in zip(native.physics['tendons'],lam)],
            dtension_margin_du=(-dtension).tolist())
    # Actual re-equilibrium directional check is kept even on nonsmooth branches.
    rm=solve(minus,s,force,q);rp=solve(plus,s,force,q)
    same=rm['equilibrium']['active']==equilibrium['active']==rp['equilibrium']['active']
    result['resolved_comparison']=dict(minus_status=rm['status'],plus_status=rp['status'],same_active_set=same,
        dq_du=((np.array(rp['equilibrium']['qpos'])-rm['equilibrium']['qpos'])/(2*step)).tolist(),
        dpositions_du=((np.array(rp['equilibrium']['positions'])-rm['equilibrium']['positions'])/(2*step)).tolist())
    if regular:
        error=float(np.linalg.norm(np.array(result['resolved_comparison']['dq_du'])-result['dq_du'])/max(np.linalg.norm(result['dq_du']),1e-12))
        result['gradient_relative_error']=error
        result['gradient_trustworthy']=bool(same and rm['status']==rp['status']=='qualified_local_minimum' and error<.05)
    result['numerical_cost']={k:pm.cost[k]+pp.cost[k]+rm['numerical_cost'][k]+rp['numerical_cost'][k] for k in pm.cost}
    return result


def multicase_metrics(protocol,baseline,loaded,s):
    """Minimax surrogate avoids dividing by a vanishing material-point response."""
    delta=np.array(loaded['positions'])-baseline['positions'];dx=abs(delta[protocol['monitor_s'].index(s),0])
    tip=float(np.linalg.norm(delta[-1,:2]));y=float(np.max(abs(delta[:,1])))
    violations=dict(tip=tip/protocol['tip_horizontal_limit_m']-1,
        point=1-dx/protocol['force_point_x_min_m'],
        ratio_equivalent=(tip-protocol['ratio_limit']*dx)/(protocol['ratio_limit']*protocol['force_point_x_min_m']),
        plane=y/protocol['out_of_plane_limit_m']-1)
    return dict(point_dx_m=float(dx),tip_xy_m=tip,ratio=tip/max(float(dx),1e-15),out_of_plane_m=y,
        violations=violations,worst_violation=max(0.,max(violations.values())))
