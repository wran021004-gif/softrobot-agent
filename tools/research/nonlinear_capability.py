"""Finite-budget native T1 interpretation and evidence-only structural T2.

The existing native control search owns T1 computation. T2 never integrates or
optimizes: it compares three admitted, candidate-bound results in the same Store.
"""
from copy import deepcopy
import math
import time

import numpy as np
from tools.platform_store import plain
from tools.state_io import digest

T1 = 'mujoco-nonlinear-task-capability-v1'
T2 = 'mujoco-reoptimized-structure-response-v1'
T1_OPERATION = 'mujoco_nonlinear_task_capability_v1'
T2_OPERATION = 'mujoco_reoptimized_structure_response_v1'
METHODS = {T1_OPERATION: T1, T2_OPERATION: T2}
LIMITATIONS = [
    'Best found signed J under the recorded algorithm, initialization and budget; no global nonlinear optimum.',
    'Structural secants are finite-budget responses, not gradients or KKT/envelope derivatives.',
    'Independent replay uses the same MuJoCo dynamics; no hardware, cross-model or other-controller transfer.',
]


def t1_summary(value, settings):
    """Interpret one existing native search, without another rollout or score."""
    raw=value['native_dynamics'];search=raw['optimization'];best=search['best']
    initial=search['candidates'][0]['measure'];measure=best['measure']
    u=np.asarray(raw['optimized_schedule']['trajectory']['tensions_n'])
    bounds=np.asarray(value['binding']['tension_bounds_n'])
    return dict(method=T1,status='finite_budget_diagnostic',
        J=measure['signed_maximum_excess'],initial_J=initial['signed_maximum_excess'],
        improvement=initial['signed_maximum_excess']-measure['signed_maximum_excess'],
        initial_metrics=initial,best_metrics=measure,
        best_control=dict(rollout=best['reference'],label=best['label'],coefficients_n=best['coefficients_n'],
            schedule_pointer='/native_dynamics/optimized_schedule',source=raw['optimized_schedule']['provenance']),
        settings=plain(settings),stop_reason=search['stop_reason'],
        callbacks=search['cost_feedback']['evaluation_callbacks'],rollouts=raw['cost']['rollouts'],
        physics_steps=raw['cost']['physics_steps'],iterations_started=search['iterations_started'],
        response_steps_completed=sum(r['label']=='local_response_proposal' for r in search['candidates']),
        local_responses=search['local_responses'],
        input_saturation=dict(minimum_n=float(u.min()),maximum_n=float(u.max()),
            lower=bool(np.any(u<=bounds[:,0]+1e-10)),upper=bool(np.any(u>=bounds[:,1]-1e-10))),
        coefficient_boundary=bool(np.max(np.abs(best['coefficients_n']))>=settings.coefficient_limit_n-1e-10),
        task_acceptance='unmeasured',detail_pointer='/native_dynamics',limitations=LIMITATIONS)


def saved_context(host, query):
    """Use original ownership, candidate and FamilySpace checks; no new identities."""
    from tools.research.state import state
    from tools.research.design import verify_candidate, parameter_value, set_parameter
    from tools.research.optimal_capability import family_parameters
    from tools.research.physical_replay import binding
    s=state(host);request=query.nonlinear_response;rows=[]
    try:
        for ref in request.t1_results:
            reference=plain(ref)
            if reference not in s.get('analysis_results',[]):raise ValueError('OWNED_COMPLETED_T1_REQUIRED')
            raw=host.store.artifact(reference)
            if (raw.get('status')!='computed' or raw.get('implementation')!=s['freeze'] or
                    raw.get('protocol')!=plain(query.protocol) or raw.get('nonlinear_capability',{}).get('method')!=T1):
                raise ValueError('CURRENT_IMPLEMENTATION_PROTOCOL_AND_T1_REQUIRED')
            c=verify_candidate(host,raw['candidate']);cfg=c['configuration']
            params,parameter=family_parameters(s['spec'],c,request.variable)
            if request.unit!=parameter['units']:raise ValueError('PARAMETER_UNIT_MISMATCH')
            if raw['binding']['candidate']!=raw['candidate'] or raw['binding']['effective_configuration_identity']!=digest(cfg):
                raise ValueError('T1_CANDIDATE_BINDING_MISMATCH')
            native=raw['native_dynamics'];tr=native['original_schedule']['trajectory']
            binding(cfg,tr);binding(cfg,native['optimized_schedule']['trajectory'])
            point=native['initial_state']
            if point['actual_time_s']!=0. or point['configuration_identity']!=digest(cfg):
                raise ValueError('OWN_FROZEN_INITIAL_STATE_REQUIRED')
            row=dict(reference=reference,candidate=raw['candidate'],parameters=params,configuration=cfg,
                value=parameter_value(params,request.variable),t1=raw['nonlinear_capability'],
                protocol=raw['protocol'],input=tr,initial_state=point,
                cost=native['cost'])
            rows.append(row)
        if rows[0]['candidate']!=plain(query.candidate):raise ValueError('BASELINE_T1_CANDIDATE_REQUIRED')
        base=rows[0]
        for row in rows:
            expected=deepcopy(base['parameters']);set_parameter(expected,request.variable,row['value'])
            a,b=base['configuration'],row['configuration']
            if (expected!=row['parameters'] or a['task']!=b['task'] or a['seed']!=b['seed'] or
                    any(a['policy'][k]!=b['policy'][k] for k in ('controller','backend','dynamics_model','discretization'))):
                raise ValueError('SINGLE_PARAMETER_FIXED_TASK_SCENE_AND_NUMERICS_REQUIRED')
            if (row['t1']['settings']!=base['t1']['settings'] or row['protocol']!=base['protocol'] or
                    any(row['input'][k]!=base['input'][k] for k in ('times_s','tendon_order','tensions_n'))):
                raise ValueError('IDENTICAL_SEARCH_AND_COMMON_LEGAL_INITIAL_CONTROL_REQUIRED')
        values=[r['value'] for r in rows]
        if not (values[1]<values[0]<values[2] and math.isclose(values[0]-values[1],values[2]-values[0],rel_tol=1e-10)):
            raise ValueError('BASELINE_MINUS_PLUS_SYMMETRIC_STENCIL_REQUIRED')
        return dict(rows=rows,parameter=parameter)
    except (ValueError,KeyError) as exc:
        return dict(not_comparable=str(exc))


def response(context):
    """Descriptive secants plus a conservative decision, never an optimal gradient."""
    started=time.perf_counter()
    out=dict(method=T2,status='not_comparable',direction_status='not_comparable',
        task_acceptance='unmeasured',limitations=LIMITATIONS,
        cost=dict(model_builds=0,rollouts=0,physics_steps=0,optimization_evaluations=0,
            reused_t1_results=0 if context.get('not_comparable') else 3,kernel_wall_s=0.))
    if context.get('not_comparable'):out['reasons']=[context['not_comparable']]
    else:
        rows=context['rows'];base,minus,plus=rows;h=base['value']-minus['value']
        summaries=[r['t1'] for r in rows];reasons=[]
        numeric=all(math.isfinite(t[k]) for t in summaries for k in ('J','initial_J'))
        searched=all(t['callbacks']>1 and t['iterations_started']>0 for t in summaries)
        if not numeric or not searched:
            out['reasons']=['VALID_NUMERICS_AND_ACTUAL_CONTROL_REOPTIMIZATION_REQUIRED']
            out['cost']['kernel_wall_s']=time.perf_counter()-started
            return out
        def secants(key):
            zero,low,high=[t[key] for t in summaries]
            return dict(left=(zero-low)/h,right=(high-zero)/h,central=(high-low)/(2*h))
        fixed=secants('initial_J');optimized=secants('J')
        # This is an explicit practical discrimination threshold, not an error bound.
        tolerance=max(1e-6,1e-4*max(1.,*(abs(t['J']) for t in summaries)))
        left=base['t1']['J']-minus['t1']['J'];right=plus['t1']['J']-base['t1']['J']
        monotone=left*right>0 and min(abs(left),abs(right))>tolerance
        if not monotone:reasons.append('FLAT_OR_OPPOSING_LEFT_RIGHT_RESPONSE')
        opportunities=[(t['callbacks'],t['response_steps_completed']) for t in summaries]
        if len(set(opportunities))!=1:reasons.append('UNEQUAL_ACTUAL_SEARCH_OPPORTUNITIES')
        if any(t['stop_reason'] in ('iteration_limit','evaluation_request_budget') or
                t['stop_reason'].startswith('numerical_failure') for t in summaries):
            reasons.append('CONTROL_SEARCH_QUALITY_UNRESOLVED_AT_LIMIT_OR_FAILURE')
        if any(t['stop_reason']=='local_target_reached' for t in summaries):
            reasons.append('TARGET_STOP_DOES_NOT_ESTABLISH_COMPARABLE_OPTIMAL_MARGIN')
        if any(r['diagnostic']!='resolved_local_response' for t in summaries for r in t['local_responses']):
            reasons.append('RANK_DEFICIENT_CONTROL_RESPONSE')
        if any(t['response_steps_completed']==0 for t in summaries):
            reasons.append('NO_COMPLETED_RESPONSE_UPDATE')
        if any(t['coefficient_boundary'] for t in summaries):reasons.append('COEFFICIENT_DOMAIN_LIMITS_BEST_FOUND_CONTROL')
        direction='unresolved' if reasons else 'conditional_increase' if left<0 else 'conditional_decrease'
        out.update(status='computed_diagnostic',direction_status=direction,reasons=reasons,
            parameter=context['parameter'],step=h,secant_unit='signed J / '+context['parameter']['units'],
            fixed_control=fixed,reoptimized=optimized,nonmonotonic=left*right<0,
            practical_J_tolerance=tolerance,monotone_observed=monotone,
            actual_search_opportunities=opportunities,
            results=[dict(candidate=r['candidate'],value=r['value'],reference=r['reference'],
                initial_J=r['t1']['initial_J'],J=r['t1']['J'],stop_reason=r['t1']['stop_reason'],
                input_saturation=r['t1']['input_saturation']) for r in rows],
            recommendation='retain_baseline_and_diagnose' if reasons else direction,
            uncertainty='No numerical or optimization error bound; a conditional direction concerns this local search only.')
    out['cost']=dict(model_builds=0,rollouts=0,physics_steps=0,optimization_evaluations=0,
        reused_t1_results=0 if context.get('not_comparable') else 3,kernel_wall_s=time.perf_counter()-started)
    return out


def calculate(configuration, binding, query, requirements, context):
    from tools.research.analysis import scoped_result
    from tools.research.native_analysis import assessment, applicability
    from schemas.platform import SessionInput
    result=response(context)
    value=dict(status='computed' if result['status']=='computed_diagnostic' else 'not_comparable',
        operation=query.operation,binding=binding,protocol=plain(query.protocol),
        model_identity=binding['effective_configuration_identity'],
        nonlinear_response=result,task_acceptance='unmeasured',proxy_values={},
        internal_calculations=[dict(purpose=T2,**result.get('cost',{}))],limitations=LIMITATIONS)
    fit=applicability(requirements,query,assessment(SessionInput.model_validate(configuration),requirements),None)
    return scoped_result(value,requirements,fit,query)
