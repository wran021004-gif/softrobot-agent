"""Legal normalized two-scale stencils; no solver, Store or derivative certificate."""
import numpy as np


def coordinate(parameter):
    """Normalize the actual physical domain; wide positive domains use log scale."""
    lo,hi,x=(float(parameter[k]) for k in ('minimum','maximum','current_value'))
    if not np.isfinite([lo,hi,x]).all() or not lo<=x<=hi or hi<=lo:
        raise ValueError('FINITE_ORDERED_EFFECTIVE_DOMAIN_REQUIRED')
    logarithmic=lo>0 and hi/lo>=100
    width=np.log(hi/lo) if logarithmic else hi-lo
    z=np.log(x/lo)/width if logarithmic else (x-lo)/width
    return dict(kind='normalized_log_domain' if logarithmic else 'normalized_linear_domain',
        origin=z,minimum=lo,maximum=hi,physical_value=x,
        physical_scale=x*width if logarithmic else width,normalized_bounds=[0.,1.])


def physical_value(mapping, z):
    lo,hi=mapping['minimum'],mapping['maximum']
    if z==mapping['origin']:return mapping['physical_value']
    if z<=0:return lo
    if z>=1:return hi
    return float(lo*np.exp(z*np.log(hi/lo)) if mapping['kind']=='normalized_log_domain' else lo+z*(hi-lo))


def stencil(parameter):
    if not parameter.get('continuous_perturbation'):
        raise ValueError('DISCRETE_COMPARISON_ONLY_OR_INEFFECTIVE_PARAMETER')
    mapping=coordinate(parameter);z=mapping['origin'];h=.01
    if min(z,1-z)>=h:scheme='central_two_scales';sign=0
    else:scheme='one_sided_second_order_two_scales';sign=1 if z<=.5 else -1
    offsets=([-h,h,-h/2,h/2] if not sign else [sign*h,sign*2*h,sign*h/2])
    return dict(value=mapping['physical_value'],coordinate=mapping,normalized_steps=[h,h/2],
        offsets=offsets,coordinates=[physical_value(mapping,z+d) for d in offsets],
        steps=[abs(physical_value(mapping,z+(sign or 1)*s)-mapping['physical_value']) for s in (h,h/2)],
        scheme=scheme,one_sided_sign=sign,method='controlled_native_finite_difference',
        unavailable=['Analytic, AD or KKT structural derivatives are not available for this native observable/state binding.'])


def differentiate(parameter, baseline, evaluate, *, goal):
    """One parameter, common baseline, cached legal probes supplied by the caller."""
    plan=stencil(parameter);mapping=plan['coordinate'];origin=mapping['origin']
    y0=baseline['observation']['value'];samples=[];derivatives=[];normalized=[];probes=[]
    if np.asarray(y0).ndim or not np.isfinite(y0):raise ValueError('SCALAR_MECHANISM_TARGET_REQUIRED_FOR_DIRECTION')
    cache={}
    def at(offset):
        value=physical_value(mapping,origin+offset)
        if value not in cache:
            record=evaluate(value);y=record['observation']['value']
            if np.asarray(y).ndim or not np.isfinite(y):raise ValueError('FINITE_SCALAR_STENCIL_REQUIRED')
            cache[value]=dict(coordinate=value,normalized_coordinate=origin+offset,
                value=float(y),record_index=record['record_index'])
            probes.append(cache[value])
        return cache[value]
    for h in plan['normalized_steps']:
        if plan['one_sided_sign']:
            sign=plan['one_sided_sign'];first=at(sign*h);second=at(sign*2*h)
            dz=sign*(-3*y0+4*first['value']-second['value'])/(2*h)
            row=dict(normalized_step=h,first=first,second=second)
        else:
            minus=at(-h);plus=at(h);dz=(plus['value']-minus['value'])/(2*h)
            row=dict(normalized_step=h,minus=minus,plus=plus)
        derivative=dz/mapping['physical_scale'];normalized.append(float(dz));derivatives.append(float(derivative))
        samples.append(dict(**row,derivative=float(derivative),normalized_derivative=float(dz)))
    a,b=normalized;relative=abs(a-b)/max(abs(a),abs(b),1e-15)
    signal_floor=max(1e-12,abs(y0)*1e-9)
    observed_change=max(abs(p['value']-y0) for p in probes)
    resolved=bool(a*b>0 and relative<=.1 and observed_change>signal_floor)
    preference=1 if goal=='increase' else -1
    improvements=[p for p in probes if preference*(p['value']-y0)>signal_floor]
    selected=min(improvements,key=lambda p:abs(p['normalized_coordinate']-origin)) if resolved and improvements else None
    return dict(**plan,samples=samples,derivatives=derivatives,normalized_derivatives=normalized,
        derivative_unit='('+baseline['observation']['unit']+')/('+parameter['unit']+')',
        normalized_derivative_unit=baseline['observation']['unit']+'/normalized_coordinate',
        consistency=dict(same_direction=bool(a*b>0),relative_difference=relative,tolerance=.1,
            observed_change=float(observed_change),signal_floor=signal_floor,passed=resolved,
            scope='Two finite scales and an observed signal check; no rigorous error bound or differentiability proof.'),
        suggested_delta=selected['coordinate']-plan['value'] if selected else None,
        selected_record_index=selected['record_index'] if selected else None,
        direction_status='locally_consistent' if selected else 'unresolved',strict_derivative=False,descent_certificate=False)
