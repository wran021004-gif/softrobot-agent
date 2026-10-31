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


def design_sensitivity(native,equilibrium,minus,plus,parameter,step,s,force,*,resolved=None,observation_s=None):
    """Normalized parameter u, supplied models at u +/- step, fixed topology."""
    if any(n.model.nv!=native.model.nv or n.model.ntendon!=native.model.ntendon or n.physics['dofs']!=native.physics['dofs'] for n in (minus,plus)):
        return dict(method='passive_design_sensitivity_v1',status='not_applicable',reason='discrete_topology_change',parameter=parameter)
    observation_s=s if observation_s is None else observation_s
    q=np.array(equilibrium['qpos']);lam=np.array(equilibrium['tensions_n']);a=np.array(equilibrium['active'])
    binding_switch=any(material_point(n.physics,loc)['body']!=material_point(native.physics,loc)['body'] for n in (minus,plus) for loc in (s,observation_s))
    regular=equilibrium['status']=='qualified_local_minimum' and equilibrium['LICQ'] and equilibrium['strict_complementarity'] and not binding_switch
    pm=StaticProblem(minus,s,force);pp=StaticProblem(plus,s,force)
    fm=pm.gradient(q)+pm.jacobian(q).T@lam;fp=pp.gradient(q)+pp.jacobian(q).T@lam
    dc=(pp.constraint(q)-pm.constraint(q))/(2*step)
    J=np.array(equilibrium['Jlength'])[a];H=np.array(equilibrium['H'])
    M=np.block([[H,J.T],[J,np.zeros((len(J),len(J)))]])
    condition=float(np.linalg.cond(M));regular=regular and condition<1e12
    result=dict(method='passive_design_sensitivity_v1',parameter=parameter,coordinate='dimensionless normalized parameter u',
        active=a.tolist(),LICQ=equilibrium['LICQ'],strict_complementarity=equilibrium['strict_complementarity'],KKT_condition=condition if np.isfinite(condition) else None,
        step=step,force_n=force,s=s,status='regular_implicit_gradient' if regular else 'not_applicable',
        reason=None if regular else 'material_point_binding_switch' if binding_switch else 'LICQ, strict complementarity or KKT regularity failed; use resolved finite differences')
    if regular:
        z=np.linalg.solve(M,-np.r_[(fp-fm)/(2*step),dc[a]])
        p=StaticProblem(native,s,force);d=p.at(q);pm.cost['KKT_solves']+=1;rows={}
        for name,b in [('tip',native.physics['tip']),('point',material_point(native.physics,observation_s))]:
            bp=plus.physics['tip'] if name=='tip' else material_point(plus.physics,observation_s)
            bm=minus.physics['tip'] if name=='tip' else material_point(minus.physics,observation_s)
            explicit=(plus.point(pp.at(q),bp)[0]-minus.point(pm.at(q),bm)[0])/(2*step)
            rows[name]=(native.point(d,b)[1]@z[:len(q)]+explicit).tolist()
        residual_derivative=np.array(equilibrium['Jlength'])@z[:len(q)]+dc
        dtension=np.zeros(native.model.ntendon);dtension[a]=z[len(q):]
        result.update(dq_du=z[:len(q)].tolist(),dtension_du=dtension.tolist(),dposition_du=rows,
            dlength_residual_du=residual_derivative.tolist(),dslack_margin_du=(-residual_derivative).tolist(),
            tension_margin_n=[t['force_limit_n']-v for t,v in zip(native.physics['tendons'],lam)],
            dtension_margin_du=(-dtension).tolist())
    # Actual re-equilibrium directional check is kept even on nonsmooth branches.
    rm,rp=resolved if resolved is not None else (solve(minus,s,force,q),solve(plus,s,force,q))
    same=rm['equilibrium']['active']==equilibrium['active']==rp['equilibrium']['active']
    result['resolved_comparison']=dict(minus_status=rm['status'],plus_status=rp['status'],same_active_set=same,
        minus_positions=rm['equilibrium']['positions'],plus_positions=rp['equilibrium']['positions'],
        dq_du=((np.array(rp['equilibrium']['qpos'])-rm['equilibrium']['qpos'])/(2*step)).tolist(),
        dpositions_du=((np.array(rp['equilibrium']['positions'])-rm['equilibrium']['positions'])/(2*step)).tolist())
    if regular:
        error=float(np.linalg.norm(np.array(result['resolved_comparison']['dq_du'])-result['dq_du'])/max(np.linalg.norm(result['dq_du']),1e-12))
        result['gradient_relative_error']=error
        result['gradient_trustworthy']=bool(same and rm['status']==rp['status']=='qualified_local_minimum' and error<.05)
    result['numerical_cost']={k:pm.cost[k]+pp.cost[k]+(p.cost[k] if regular else 0)+(rm['numerical_cost'][k]+rp['numerical_cost'][k] if resolved is None else 0) for k in pm.cost}
    if not same or not result.get('gradient_trustworthy',False):result['status']='directional_comparison'
    return result


def task_design_sensitivity(native,mechanics,minus,plus,minus_mechanics,plus_mechanics,parameter,step,observation_s):
    """Relative displacement includes BOTH design-dependent equilibria."""
    load=mechanics['point_binding']['load'];baseline=native.load(native.problem.baseline_load)
    results={}
    for key,force,s in [('equilibrium',load['force_world_n'],load['material_s']),
                         ('baseline_equilibrium',baseline.force_world_n,baseline.material_s)]:
        results[key]=design_sensitivity(native,mechanics[key]['equilibrium'],minus,plus,parameter,step,s,force,
            observation_s=observation_s,resolved=(minus_mechanics[key],plus_mechanics[key]))
    good=all(r.get('gradient_trustworthy',False) for r in results.values())
    derivative=(np.array(results['equilibrium']['dposition_du']['point'])-results['baseline_equilibrium']['dposition_du']['point']).tolist() if good else None
    return dict(status='regular_implicit_gradient' if good else 'directional_comparison',
        baseline_included=True,drelative_position_du=derivative,branches=results,
        numerical_cost={k:sum(r['numerical_cost'][k] for r in results.values()) for k in next(iter(results.values()))['numerical_cost']},
        strict_derivative=False,scope='Numerically checked local KKT implicit response; no rigorous error bound or dynamic acceptance.')

