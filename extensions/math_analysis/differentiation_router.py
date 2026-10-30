"""Small legal structural stencils; numerical observations, never certificates.

The existing SoRoSim IFT, Conic/KKT and saved T1/T2 derivatives retain their own
admission. This route implements only native fixed-state mechanism differences.
"""
import numpy as np


def stencil(parameter):
    if not parameter.get('continuous_perturbation'):
        raise ValueError('DISCRETE_COMPARISON_ONLY_OR_INEFFECTIVE_PARAMETER')
    x=parameter['current_value'];lo=parameter['minimum'];hi=parameter['maximum']
    h=min(.01*(hi-lo),.5*min(x-lo,hi-x))
    if h<=max(1.,abs(x))*1e-12:
        raise ValueError('INTERIOR_CONTINUOUS_PARAMETER_REQUIRED_FOR_CENTRAL_STENCIL')
    return dict(value=x,steps=[h,h/2],coordinates=[x-h,x+h,x-h/2,x+h/2],
        scheme='central_two_scales',method='controlled_native_finite_difference',
        unavailable=['Analytic, AD or KKT structural derivatives are not available for this native observable/state binding.'])


def differentiate(parameter, baseline, evaluate, *, goal):
    """Evaluate the two scales under the caller's original charged execution."""
    plan=stencil(parameter);x=plan['value'];samples=[];derivatives=[]
    y0=baseline['observation']['value']
    if np.asarray(y0).ndim or not np.isfinite(y0):raise ValueError('SCALAR_MECHANISM_TARGET_REQUIRED_FOR_DIRECTION')
    for h in plan['steps']:
        minus=evaluate(x-h);plus=evaluate(x+h)
        ym=minus['observation']['value'];yp=plus['observation']['value']
        if np.asarray(ym).ndim or np.asarray(yp).ndim or not np.isfinite([ym,yp]).all():
            raise ValueError('FINITE_SCALAR_STENCIL_REQUIRED')
        derivative=(yp-ym)/(2*h);derivatives.append(derivative)
        samples.append(dict(step=h,
            minus=dict(coordinate=x-h,value=ym,record_index=minus['record_index']),
            plus=dict(coordinate=x+h,value=yp,record_index=plus['record_index']),derivative=derivative))
    a,b=derivatives
    scale=max(abs(a),abs(b),1e-14);relative=abs(a-b)/scale
    resolved=bool(abs(a)>1e-12 and abs(b)>1e-12 and a*b>0 and relative<=.1)
    sign=(1 if b>0 else -1)*(1 if goal=='increase' else -1)
    selected=samples[-1]['plus' if sign>0 else 'minus']
    gain=(selected['value']-y0)*(1 if goal=='increase' else -1)
    supported=resolved and gain>max(1e-12,abs(y0)*1e-10)
    return dict(**plan,samples=samples,derivatives=derivatives,
        derivative_unit=baseline['observation']['unit']+'/'+parameter['unit'],
        consistency=dict(same_direction=bool(a*b>0),relative_difference=relative,
            tolerance=.1,passed=resolved,scope='Two local finite scales; no truncation/roundoff bound or differentiability proof.'),
        suggested_delta=sign*plan['steps'][-1] if supported else None,
        selected_record_index=selected['record_index'] if supported else None,
        direction_status='locally_consistent' if supported else 'unresolved',
        strict_derivative=False,descent_certificate=False)
