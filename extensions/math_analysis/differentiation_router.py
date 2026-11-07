"""Legal normalized two-scale stencils; no solver, Store or derivative certificate."""
import numpy as np


def select_method(*, effect_semantics, capabilities, target=None, operation='differentiate', saved_t1=False, saved_conic=False):
    """Select existing computations; selection never launches a solver or search."""
    missing=list(capabilities.get('missing',[]));actuation=capabilities.get('actuation')
    method=None;strength='not_applicable';preparation=[]
    if not missing and effect_semantics=='finite_time_task_response':
        if capabilities.get('evaluation',{}).get('finite_time_structure_response'):
            method='finite_time_task_paired_response';strength='bounded_directional_comparison'
        else:missing.append('registered_finite_time_structure_response_backend')
    elif not missing and effect_semantics=='re_equilibrated_passive_response':
        if 're_equilibrated' in capabilities.get('state_solution',[]):
            method='passive_kkt_implicit' if target=='re_equilibrated_position_response' else 'passive_re_equilibrated_pairs'
            strength='conditional_implicit_gradient' if method=='passive_kkt_implicit' else 'directional_comparison'
        else:missing.append('qualified_unilateral_equilibrium')
    elif not missing and effect_semantics=='reoptimized_task_capability':
        if saved_conic:method='saved_conic_capability_sensitivity';strength='conditional_optimal_value_sensitivity'
        elif saved_t1:method='saved_native_t1_t2';strength='finite_budget_best_found_secant'
        else:preparation=['Read or explicitly prepare comparable saved T1/Conic evidence. No automatic T1 search.']
    elif not missing and effect_semantics=='mechanism_effect':
        if actuation=='ideal_tension':method='native_instantaneous_finite_difference';strength='local_numerical_derivative_estimate'
        elif 're_equilibrated' in capabilities.get('state_solution',[]):method='passive_re_equilibrated_pairs';strength='directional_comparison'
        else:missing.append('registered_instantaneous_mechanism_backend')
    else:missing.append('registered_effect_semantics')
    if operation=='interact':
        if method and effect_semantics in ('mechanism_effect','re_equilibrated_passive_response','finite_time_task_response'):
            method='matched_two_parameter_four_point_v1';strength='local_finite_interaction_estimate'
        else:
            method=None;missing.append('registered_matched_interaction_backend_for_effect')
    return dict(method=method,effect_semantics=effect_semantics,parameter=None,working_point=None,
        control_treatment=actuation,comparison_scope='same frozen task, model protocol and declared control treatment',
        numerical_consistency='requires_recorded_checks',direction_status=strength,
        validity='unsupported' if missing else 'needs_prerequisite' if preparation else 'conditional',
        missing=missing,preparation=preparation,evidence_source=None,actual_cost=None,
        strict_derivative=False,automatic_expensive_search=False)


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


def matched_points(parameters):
    """Four legal local points from actual continuous registry domains."""
    if len(parameters)!=2:raise ValueError('INTERACTION_REQUIRES_TWO_CONTINUOUS_PARAMETERS')
    plans=[stencil(p) for p in parameters]
    base=[p['current_value'] for p in parameters]
    changed=[plan['coordinates'][1 if plan['scheme']=='central_two_scales' else 0] for plan in plans]
    ids=[p['parameter_id'] for p in parameters]
    if len(set(ids))!=2 or any(a==b for a,b in zip(base,changed)):
        raise ValueError('DISTINCT_NONZERO_PARAMETER_INTERVENTIONS_REQUIRED')
    return [dict(label=label,parameter_values=dict(zip(ids,values))) for label,values in (
        ('00',base),('10',[changed[0],base[1]]),('01',[base[0],changed[1]]),('11',changed))]


def interaction_evidence(points, records):
    """Matched finite contrasts only; missing validity never becomes a zero."""
    selected=[next((r for r in records if r.get('parameter_values')==p['parameter_values']),None) for p in points]
    evidence=dict(method='matched_two_parameter_four_point_v1',parameters=list(points[0]['parameter_values']),
        points=[dict(**p,record_index=r['record_index'] if r else None) for p,r in zip(points,selected)],
        strict_derivative=False,error_bound=None,uncertainty='Numerical estimate; no rigorous error bound.',
        scope='Specified local finite region and matched conditions only; no global causal law or strict mixed derivative.')
    issues=[]
    for p,r in zip(points,selected):
        observation=(r or {}).get('observation') or {};value=observation.get('value')
        if r is None or observation.get('status')!='computed' or value is None or np.asarray(value).ndim or not np.isfinite(value):
            issues.append(p['label']+': missing or invalid finite scalar observation')
        elif ((r.get('mechanics') or {}).get('constraint_state',{}).get('qualified') is False
                and not (observation.get('task_gap') or {}).get('valid_complete')):
            issues.append(p['label']+': physical working point not qualified')
    identities=[r.get('matching_identity') for r in selected if r]
    if len(identities)!=4 or any(v is None for v in identities) or len(set(identities))!=1:
        issues.append('Task/model/initial-state/control/environment/nonresearch-parameter match unverified')
    units={r['observation'].get('unit') for r in selected if r}
    if len(units)!=1 or None in units:issues.append('Observable unit unknown or mismatched')
    if issues:return dict(**evidence,status='incomplete',issues=issues,independent_effects=None,interaction_effect=None)
    y00,y10,y01,y11=[float(r['observation']['value']) for r in selected]
    active_sets=[(r.get('mechanics') or {}).get('constraint_state') for r in selected]
    branch_states=[]
    for r in selected:
        equilibrium=((r.get('mechanics') or {}).get('equilibrium') or {}).get('equilibrium') or {}
        branch_states.append({k:equilibrium.get(k) for k in ('active','positive')})
    return dict(**evidence,status='computed_local_interaction',unit=next(iter(units)),
        baseline=y00,independent_effects=dict(delta1=y10-y00,delta2=y01-y00),
        interaction_effect=y11-y10-y01+y00,total_joint_change=y11-y00,
        active_sets=active_sets,branch_changed=(any(b!=branch_states[0] for b in branch_states[1:])
            if any(v is not None for b in branch_states for v in b.values()) else None),
        issues=[],interpretation='Branch changes remain finite comparisons and never authorize a smooth gradient.')


def differentiate(parameter, baseline, evaluate, *, goal, allow_ineligible=False):
    """One parameter, common baseline, cached legal probes supplied by the caller."""
    plan=stencil(parameter);mapping=plan['coordinate'];origin=mapping['origin']
    y0=baseline['observation']['value'];samples=[];derivatives=[];normalized=[];probes=[]
    if np.asarray(y0).ndim or not np.isfinite(y0):raise ValueError('SCALAR_MECHANISM_TARGET_REQUIRED_FOR_DIRECTION')
    cache={}
    def at(offset):
        value=physical_value(mapping,origin+offset)
        if value not in cache:
            record=evaluate(value);y=record['observation']['value']
            valid=y is not None and np.asarray(y).ndim==0 and bool(np.isfinite(y))
            if not valid and not allow_ineligible:raise ValueError('FINITE_SCALAR_STENCIL_REQUIRED')
            cache[value]=dict(coordinate=value,normalized_coordinate=origin+offset,
                value=float(y) if valid else None,record_index=record['record_index'])
            probes.append(cache[value])
        return cache[value]
    for h in plan['normalized_steps']:
        if plan['one_sided_sign']:
            sign=plan['one_sided_sign'];first=at(sign*h);second=at(sign*2*h)
            dz=sign*(-3*y0+4*first['value']-second['value'])/(2*h) if first['value'] is not None and second['value'] is not None else None
            row=dict(normalized_step=h,first=first,second=second)
        else:
            minus=at(-h);plus=at(h)
            dz=(plus['value']-minus['value'])/(2*h) if plus['value'] is not None and minus['value'] is not None else None
            row=dict(normalized_step=h,minus=minus,plus=plus)
        derivative=dz/mapping['physical_scale'] if dz is not None else None
        normalized.append(float(dz) if dz is not None else None);derivatives.append(derivative)
        samples.append(dict(**row,derivative=derivative,normalized_derivative=dz))
    a,b=normalized;complete=a is not None and b is not None
    relative=abs(a-b)/max(abs(a),abs(b),1e-15) if complete else None
    signal_floor=max(1e-12,abs(y0)*1e-9)
    observed_change=max((abs(p['value']-y0) for p in probes if p['value'] is not None),default=0.)
    resolved=bool(complete and a*b>0 and relative<=.1 and observed_change>signal_floor)
    preference=1 if goal=='increase' else -1
    improvements=[p for p in probes if p['value'] is not None and preference*(p['value']-y0)>signal_floor]
    selected=min(improvements,key=lambda p:abs(p['normalized_coordinate']-origin)) if resolved and improvements else None
    return dict(**plan,samples=samples,derivatives=derivatives,normalized_derivatives=normalized,
        derivative_unit='('+baseline['observation']['unit']+')/('+parameter['unit']+')',
        normalized_derivative_unit=baseline['observation']['unit']+'/normalized_coordinate',
        consistency=dict(same_direction=bool(complete and a*b>0),relative_difference=relative,tolerance=.1,
            observed_change=float(observed_change),signal_floor=signal_floor,passed=resolved,
            scope='Two finite scales and an observed signal check; no rigorous error bound or differentiability proof.'),
        suggested_delta=selected['coordinate']-plan['value'] if selected else None,
        selected_record_index=selected['record_index'] if selected else None,
        derivative_status='locally_consistent_estimate' if resolved else 'unreliable' if complete else 'ineligible_stencil',
        candidate_improvement_status='observed_scalar_probe_improvement' if improvements else 'not_observed',
        best_observed_record_index=max(improvements,key=lambda p:preference*p['value'])['record_index'] if improvements else None,
        direction_status='locally_consistent' if selected else 'unresolved',strict_derivative=False,descent_certificate=False)


def withhold_gradient(response,reason):
    """Keep measured comparisons while withholding an inadmissible gradient."""
    response['diagnostic_secants']=dict(derivatives=response.get('derivatives'),
        normalized_derivatives=response.get('normalized_derivatives'),scope='Finite comparisons only; not a gradient')
    response.update(derivatives=[None]*len(response.get('derivatives',[])),
        normalized_derivatives=[None]*len(response.get('normalized_derivatives',[])),
        derivative_status=reason,direction_status='directional_comparison',
        suggested_delta=None,selected_record_index=None,strict_derivative=False)
    for sample in response.get('samples',[]):
        sample['derivative']=None;sample['normalized_derivative']=None
    if 'implicit_sensitivity' in response:
        response['implicit_sensitivity']=dict(status='directional_comparison',reason=reason,
            gradient_trustworthy=False,strict_derivative=False)
    response['consistency'].update(passed=False,reason=reason)
    return response


def re_equilibrated(parameter,baseline,records,models,response,study):
    """Reuse legal two-scale rebuilt models; add qualified implicit state checks."""
    from extensions.tendon_family.passive_inverse import task_design_sensitivity
    sample=response['samples'][0]
    if 'minus' not in sample:return dict(status='directional_comparison',reason='BOUNDARY_PARAMETER_USES_ONE_SIDED_STENCIL',strict_derivative=False)
    mi=sample['minus']['record_index'];pi=sample['plus']['record_index'];base=baseline['record_index']
    result=task_design_sensitivity(models[base],baseline['mechanics'],models[mi],models[pi],records[mi]['mechanics'],records[pi]['mechanics'],
        parameter['parameter_id'],sample['normalized_step'],study.target.material_s)
    for key,value in result['numerical_cost'].items():models[base].cost[key]=models[base].cost.get(key,0)+value
    if result['status']=='regular_implicit_gradient':
        v=np.array(baseline['mechanics']['re_equilibrated_position_response']);dv=np.array(result['drelative_position_du'])
        reduction=study.target.reduction
        if reduction in ('directional_norm','directional_component'):
            v=np.asarray(study.target.direction_world)@v;dv=np.asarray(study.target.direction_world)@dv
        if reduction=='directional_component' or reduction in ('norm','directional_norm') and np.linalg.norm(v)>1e-12:
            predicted=float(dv) if reduction=='directional_component' else float(np.sum(v*dv)/np.linalg.norm(v))
            measured=response['normalized_derivatives'][-1]
            error=abs(predicted-measured)/max(abs(predicted),abs(measured),1e-10)
            result.update(target_normalized_derivative=predicted,relative_error=error,
                gradient_trustworthy=bool(error<.05 and response['consistency']['passed']))
            if not result['gradient_trustworthy']:result['status']='directional_comparison'
        else:result.update(status='directional_comparison',reason='NONDIFFERENTIABLE_OR_UNADAPTED_REDUCTION')
    return result
