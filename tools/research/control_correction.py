"""Pure low-dimensional controls, task violations and scoped discrepancy bounds.

No simulator, solver process, Store or provider ownership belongs here.
"""
import math
import numpy as np


def _norm_interval(a,b):
    """Outward IEEE-754 operations enclose the real norm of stored float arrays."""
    lower=upper=0.
    for x,y in zip(a,b):
        d=float(x)-float(y)
        lo=math.nextafter(d,-math.inf);hi=math.nextafter(d,math.inf)
        amin=0. if lo<=0<=hi else min(abs(lo),abs(hi))
        amax=max(abs(lo),abs(hi))
        lower=max(0.,math.nextafter(lower+max(0.,math.nextafter(amin*amin,-math.inf)),-math.inf))
        upper=math.nextafter(upper+math.nextafter(amax*amax,math.inf),math.inf)
    return max(0.,math.nextafter(math.sqrt(lower),-math.inf)),math.nextafter(math.sqrt(upper),math.inf)


def _scaled_interval(interval,scale):
    return [math.nextafter(interval[0]/scale,-math.inf),math.nextafter(interval[1]/scale,math.inf)]


def corrected_tensions(reference, times, knots, coefficients, limits):
    reference=np.asarray(reference,dtype=float)
    times=np.asarray(times,dtype=float);knots=np.asarray(knots,dtype=float)
    limits=np.asarray(limits,dtype=float)
    coefficients=np.asarray(coefficients,dtype=float).reshape(len(knots),len(limits))
    if (reference.shape!=(len(times),len(limits)) or np.any(np.diff(knots)<=0)
            or not all(np.isfinite(v).all() for v in (reference,times,knots,coefficients,limits))
            or np.any(limits<=0) or np.any(reference<0) or np.any(reference>limits)):
        raise ValueError('FINITE_ORDERED_BOUND_CONTROLS_REQUIRED')
    correction=np.column_stack([np.interp(times,knots,coefficients[:,j]) for j in range(len(limits))])
    return np.clip(reference+correction,0,limits)


def task_outputs(raw):
    if 'samples' in raw:
        return dict(times_s=[v['time_s'] for v in raw['samples']],
            tip_positions_m=[v['tip_m'] for v in raw['samples']],
            tip_velocities_m_s=[v['tip_velocity_m_s'] for v in raw['samples']])
    return {key:raw[key] for key in ('times_s','tip_positions_m','tip_velocities_m_s')}


def task_measure(outputs, target, holding_start, position_limit, speed_limit):
    times=np.asarray(outputs['times_s']);p=np.asarray(outputs['tip_positions_m'])
    v=np.asarray(outputs['tip_velocities_m_s']);target=np.asarray(target)
    if (p.shape!=v.shape or p.shape!=(len(times),3) or np.any(np.diff(times)<=0)
            or not all(np.isfinite(a).all() for a in (times,p,v,target))
            or position_limit<=0 or speed_limit<=0):
        raise ValueError('FINITE_ALIGNED_OUTPUTS_AND_POSITIVE_SCALES_REQUIRED')
    hold=times>=holding_start-1e-12
    if not hold.any():raise ValueError('HOLDING_SAMPLES_REQUIRED')
    error=np.linalg.norm(p-target,axis=1);speed=np.linalg.norm(v,axis=1)
    ratios=np.array([error[-1]/position_limit,max(error[hold])/position_limit,max(speed[hold])/speed_limit])
    excess=np.maximum(ratios-1,0)
    position_intervals=[_scaled_interval(_norm_interval(a,target),position_limit) for a in p]
    velocity_intervals=[_scaled_interval(_norm_interval(a,[0.,0.,0.]),speed_limit) for a in v[hold]]
    intervals=[position_intervals[-1],*[position_intervals[i] for i in np.flatnonzero(hold)],*velocity_intervals]
    gap_interval=[max(0.,math.nextafter(max(a[0] for a in intervals)-1,-math.inf)),
        max(0.,math.nextafter(max(a[1] for a in intervals)-1,math.inf))]
    return dict(normalized_gap=float(max(excess)),sum_normalized_excess=float(sum(excess)),
        terminal_position_error_m=float(error[-1]),holding_max_position_error_m=float(max(error[hold])),
        holding_max_speed_m_s=float(max(speed[hold])),signed_maximum_excess=float(max(ratios-1)),
        returned_array_gap_interval=gap_interval)


def fitting_residual(outputs, target, holding_start, position_limit, speed_limit):
    """Aim inside the original limits; acceptance remains the registered evaluator."""
    hold=np.asarray(outputs['times_s'])>=holding_start-1e-12
    p=(np.asarray(outputs['tip_positions_m'])[hold]-target)/position_limit
    v=np.asarray(outputs['tip_velocities_m_s'])[hold]/speed_limit
    blocks=[]
    for a in (p,v):
        norm=np.linalg.norm(a,axis=1)
        blocks.append(a*(np.maximum(norm-.8,0)/np.maximum(norm,1e-15))[:,None])
    return np.concatenate([a.ravel() for a in blocks])


def output_error_budget(mathematical, simulated, holding_start, position_limit, speed_limit):
    """Norm/max/positive-part Lipschitz inequality on two evaluated sample arrays.

    This is an a-posteriori bound for these returned arrays, not a prospective
    regional bound, nor a bound to exact ODE solutions or hardware.
    """
    mt=np.asarray(mathematical['times_s']);st=np.asarray(simulated['times_s'])
    if mt.shape!=st.shape or not np.allclose(mt,st,atol=1e-12,rtol=0):
        raise ValueError('IDENTICAL_TASK_SAMPLE_GRIDS_REQUIRED')
    dp=np.asarray(simulated['tip_positions_m'])-mathematical['tip_positions_m']
    dv=np.asarray(simulated['tip_velocities_m_s'])-mathematical['tip_velocities_m_s']
    if dp.shape!=(len(mt),3) or dv.shape!=dp.shape or not np.isfinite(dp).all() or not np.isfinite(dv).all():
        raise ValueError('FINITE_ALIGNED_VECTOR_ERRORS_REQUIRED')
    hold=mt>=holding_start-1e-12
    if not hold.any() or position_limit<=0 or speed_limit<=0:
        raise ValueError('HOLDING_SAMPLES_AND_POSITIVE_SCALES_REQUIRED')
    sp=np.asarray(simulated['tip_positions_m']);mp=np.asarray(mathematical['tip_positions_m'])
    sv=np.asarray(simulated['tip_velocities_m_s']);mv=np.asarray(mathematical['tip_velocities_m_s'])
    components=dict(terminal_position=_scaled_interval(_norm_interval(sp[-1],mp[-1]),position_limit)[1],
        holding_position=max(_scaled_interval(_norm_interval(a,b),position_limit)[1] for a,b in zip(sp[hold],mp[hold])),
        holding_speed=max(_scaled_interval(_norm_interval(a,b),speed_limit)[1] for a,b in zip(sv[hold],mv[hold])))
    return dict(epsilon=max(components.values()),components=components,
        status='a_posteriori_outward_rounded_sample_array_bound',prospective_certified=False,
        numerical_solution_error_bound=None,regional_discrepancy_bound=None,
        scope='Only these evaluated floating-point output arrays; no continuous-time, unvisited-candidate or exact-dynamics guarantee')


def improvement_test(base_model, new_model, base_sim, new_sim, base_budget, new_budget):
    predicted=base_model['normalized_gap']-new_model['normalized_gap']
    observed=base_sim['normalized_gap']-new_sim['normalized_gap']
    base_lower=base_model.get('returned_array_gap_interval',[base_model['normalized_gap']]*2)[0]
    new_upper=new_model.get('returned_array_gap_interval',[new_model['normalized_gap']]*2)[1]
    sufficient=math.nextafter(math.nextafter(math.nextafter(base_lower-new_upper,-math.inf)-
        base_budget['epsilon'],-math.inf)-new_budget['epsilon'],-math.inf)
    return dict(predicted_improvement=predicted,observed_improvement=observed,
        direction_agrees=bool(predicted*observed>0) if predicted!=0 and observed!=0 else None,
        sufficient_improvement_lower_bound=sufficient,
        sufficient_condition_met=bool(sufficient>0),
        prospective_guarantee=False,
        scope='A posteriori at the two evaluated endpoints; prospective guarantee requires independently valid endpoint error bounds before execution')


def constraint_vectors(outputs, target, holding_start, position_limit, speed_limit):
    """Every terminal/holding norm constraint, without averaging away a violation."""
    task_measure(outputs,target,holding_start,position_limit,speed_limit)
    p=(np.asarray(outputs['tip_positions_m'])-target)/position_limit
    v=np.asarray(outputs['tip_velocities_m_s'])/speed_limit
    hold=np.asarray(outputs['times_s'])>=holding_start-1e-12
    return np.vstack([p[-1:],p[hold],v[hold]])


def correction_basis(times, knots, channels):
    knots=np.asarray(knots,dtype=float)
    return np.kron(np.column_stack([np.interp(times,knots,row) for row in np.eye(len(knots))]),np.eye(channels))


def constrained_response_step(vectors, response, coefficients, reference, basis, limits,
                              radius, coefficient_limit, regularization=.01):
    """Numerical SLSQP epigraph step; no global proof or physical acceptance."""
    from scipy.optimize import minimize
    y=np.asarray(vectors);jac=np.asarray(response);x=np.asarray(coefficients)
    if (y.ndim!=2 or y.shape[1]!=3 or jac.shape!=(*y.shape,len(x)) or
            not all(np.isfinite(a).all() for a in (y,jac,x,reference,basis,limits))):
        raise ValueError('FINITE_ALIGNED_LOCAL_RESPONSE_REQUIRED')
    low=np.maximum(-radius,-coefficient_limit-x);high=np.minimum(radius,coefficient_limit-x)
    base=np.asarray(reference).ravel()+basis@x;upper=np.tile(limits,len(reference))
    def norms(z):return np.linalg.norm(y+jac@z[:-1],axis=1)
    def constraints(z):return np.r_[1+z[-1]-norms(z),base+basis@z[:-1],upper-base-basis@z[:-1]]
    def derivatives(z):
        moved=y+jac@z[:-1];normal=moved/np.maximum(np.linalg.norm(moved,axis=1)[:,None],1e-15)
        return np.vstack([np.c_[-np.einsum('ij,ijk->ik',normal,jac),np.ones(len(y))],
            np.c_[basis,np.zeros(len(base))],np.c_[-basis,np.zeros(len(base))]])
    solved=minimize(lambda z:z[-1]+regularization*(z[:-1]@z[:-1]),
        np.r_[np.zeros(len(x)),max(0.,max(np.linalg.norm(y,axis=1))-1)],
        jac=lambda z:np.r_[2*regularization*z[:-1],1.],method='SLSQP',
        bounds=[*zip(low,high),(0,None)],constraints=[dict(type='ineq',fun=constraints,jac=derivatives)],
        options=dict(maxiter=100,ftol=1e-10))
    valid=bool(solved.success and np.isfinite(solved.x).all() and min(constraints(solved.x))>=-1e-8)
    return dict(success=valid,delta=solved.x[:-1],predicted_gap=float(max(0.,max(norms(solved.x))-1)),
        numerical_status=str(solved.message),iterations=int(solved.nit),global_optimality_proved=False)
