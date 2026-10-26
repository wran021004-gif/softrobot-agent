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
    """Admit saved T1 observations; reuse shared baselines without new rollouts."""
    from types import SimpleNamespace
    from tools.research.state import state
    from tools.research.design import verify_candidate, parameter_value, set_parameter
    from tools.research.optimal_capability import family_parameters
    from tools.research.physical_replay import binding
    from tools.research.research_context import recorded_changes
    s=state(host);request=query.nonlinear_response;cache={}
    directions=getattr(request,'directions',None)
    legacy=not directions
    if legacy:
        directions=[SimpleNamespace(direction_id=request.variable,mode='continuous',variables={request.variable:1.},
            coordinate_unit=request.unit,coordinates=None,t1_results=request.t1_results)]
    def load(ref):
        reference=plain(ref);key=reference['artifact_id']
        if key in cache:return cache[key]
        if reference not in s.get('analysis_results',[]):raise ValueError('OWNED_COMPLETED_T1_REQUIRED')
        raw=host.store.artifact(reference)
        if (raw.get('status')!='computed' or raw.get('implementation')!=s['freeze'] or
                raw.get('protocol')!=plain(query.protocol) or raw.get('nonlinear_capability',{}).get('method')!=T1):
            raise ValueError('CURRENT_IMPLEMENTATION_PROTOCOL_AND_T1_REQUIRED')
        c=verify_candidate(host,raw['candidate']);cfg=c['configuration']
        if raw['binding']['candidate']!=raw['candidate'] or raw['binding']['effective_configuration_identity']!=digest(cfg):
            raise ValueError('T1_CANDIDATE_BINDING_MISMATCH')
        native=raw['native_dynamics'];tr=native['original_schedule']['trajectory']
        binding(cfg,tr);binding(cfg,native['optimized_schedule']['trajectory'])
        point=native['initial_state']
        if point['actual_time_s']!=0. or point['configuration_identity']!=digest(cfg):
            raise ValueError('OWN_FROZEN_INITIAL_STATE_REQUIRED')
        row=dict(reference=reference,candidate=raw['candidate'],candidate_record=c,configuration=cfg,
            t1=raw['nonlinear_capability'],protocol=raw['protocol'],input=tr,initial_state=point,cost=native['cost'])
        cache[key]=row
        return row
    def admit(direction):
        rows=[dict(load(ref)) for ref in direction.t1_results]
        if rows[0]['candidate']!=plain(query.candidate):raise ValueError('BASELINE_T1_CANDIDATE_REQUIRED')
        paths=direction.variables if direction.mode=='continuous' else direction.comparison_variables
        parameters={}
        for row in rows:
            values={}
            for path in paths:
                params,domain=(family_parameters(s['spec'],row['candidate_record'],path) if direction.mode=='continuous' else
                    family_parameters(s['spec'],row['candidate_record'],path,continuous=False))
                values[path]=parameter_value(params,path);parameters.setdefault(path,domain)
                row['parameters']=params
            row['parameter_values']=values
        base=rows[0];a=base['configuration']
        coordinates=direction.coordinates
        if direction.mode=='continuous' and legacy:
            path=next(iter(paths));coordinates=[r['parameter_values'][path]-base['parameter_values'][path] for r in rows]
            if request.unit!=parameters[path]['units']:raise ValueError('PARAMETER_UNIT_MISMATCH')
        if direction.mode=='continuous' and (not coordinates[1]<0<coordinates[2] or not math.isclose(-coordinates[1],coordinates[2],rel_tol=1e-10)):
            raise ValueError('BASELINE_MINUS_PLUS_SYMMETRIC_STENCIL_REQUIRED')
        for index,row in enumerate(rows):
            b=row['configuration']
            same_task=a['task']==b['task']
            if direction.mode=='finite_comparison' and base['candidate_record'].get('generation_version'):
                ta,tb=deepcopy(a['task']),deepcopy(b['task'])
                ta.pop('initializer',None);tb.pop('initializer',None)
                same_task=ta==tb and base['candidate_record']['task_identity']==row['candidate_record']['task_identity']
            if (not same_task or a['seed']!=b['seed'] or
                    any(a['policy'][k]!=b['policy'][k] for k in ('controller','backend','dynamics_model')) or
                    (direction.mode=='continuous' and a['policy']['discretization']!=b['policy']['discretization']) or
                    any(base['candidate_record'].get(k)!=row['candidate_record'].get(k) for k in ('source_identity','profile_identity'))):
                raise ValueError('SINGLE_PARAMETER_FIXED_TASK_SCENE_AND_NUMERICS_REQUIRED')
            if row['t1']['settings']!=base['t1']['settings'] or row['input']['times_s']!=base['input']['times_s']:
                raise ValueError('IDENTICAL_SEARCH_AND_COMMON_LEGAL_INITIAL_CONTROL_REQUIRED')
            if direction.mode=='continuous':
                expected=deepcopy(base['parameters'])
                for path,coefficient in direction.variables.items():
                    wanted=base['parameter_values'][path]+coefficient*coordinates[index]
                    if not math.isclose(row['parameter_values'][path],wanted,rel_tol=1e-10,abs_tol=1e-12):
                        raise ValueError('CANDIDATES_DO_NOT_FOLLOW_DECLARED_DIRECTION')
                    set_parameter(expected,path,row['parameter_values'][path])
                if expected!=row['parameters']:raise ValueError('SINGLE_PARAMETER_FIXED_TASK_SCENE_AND_NUMERICS_REQUIRED')
                if any(row['input'][k]!=base['input'][k] for k in ('tendon_order','tensions_n')):
                    raise ValueError('IDENTICAL_SEARCH_AND_COMMON_LEGAL_INITIAL_CONTROL_REQUIRED')
                if any(row['initial_state'].get(k)!=base['initial_state'].get(k) for k in ('dof_order','tendon_order','qpos_rad','qvel_rad_s','phase','input_units','provenance')):
                    raise ValueError('MATCHED_INITIAL_STATE_CONVENTION_REQUIRED')
                if index and a.get('robot')==b.get('robot') and a.get('robot') is not None:
                    raise ValueError('NO_ACTUAL_PHYSICAL_PARAMETER_CHANGE')
                row['value']=coordinates[index]
            else:
                left,right=deepcopy(base['parameters']),deepcopy(row['parameters'])
                masks=[parameters[path].get('comparison_path',path) for path in paths]
                if 'segment_count' in paths:masks+=['segments','spans']
                if 'tendon_count' in paths:masks+=['spans','route_overrides']
                for path in masks:
                    for target in (left,right):
                        try:set_parameter(target,path,None)
                        except (KeyError,IndexError):pass
                if left!=right:raise ValueError('UNDECLARED_FINITE_COMPARISON_PARAMETER_CHANGE')
            row['physical_changes']=recorded_changes(a.get('robot',{}),b.get('robot',{}))
        if direction.mode=='finite_comparison':
            return dict(rows=rows,parameters=parameters,direction_id=direction.direction_id,mode=direction.mode)
        independent=len(paths)==1 and next(iter(direction.variables.values()))==1. and direction.coordinate_unit==next(iter(parameters.values()))['units']
        if legacy:
            for row in rows:row['value']=next(iter(row['parameter_values'].values()))
        return dict(rows=rows,parameter=next(iter(parameters.values())) if legacy else dict(units=direction.coordinate_unit),
            parameters=parameters,direction_id=direction.direction_id,mode='continuous',
            derivative_scope='independent_parameter_secant' if independent else 'coupled_path_secant' if len(paths)>1 else 'scaled_path_secant',
            coefficients=dict(direction.variables),coordinate_unit=direction.coordinate_unit)
    contexts=[]
    for d in directions:
        try:contexts.append(admit(d))
        except (ValueError,KeyError,IndexError) as exc:contexts.append(dict(not_comparable=str(exc),direction_id=d.direction_id))
    if legacy:return contexts[0]
    return dict(directions=contexts,unique_t1_results=len(cache),baseline=plain(directions[0].t1_results[0]))


def response(context):
    """Descriptive secants plus a conservative decision, never an optimal gradient."""
    started=time.perf_counter()
    if context.get('directions') is not None:
        results=[response(c) for c in context['directions']]
        costs={r['reference']['artifact_id']:dict(reference=r['reference'],cost=r.get('cost',{}))
            for c in context['directions'] for r in c.get('rows',[])}
        return dict(method=T2,version='nonlinear_response_v2',status='computed_diagnostic' if any(r['status']=='computed_diagnostic' for r in results) else 'not_comparable',
            direction_status='unresolved',baseline=context['baseline'],directions=results,task_acceptance='unmeasured',limitations=LIMITATIONS,
            cost=dict(model_builds=0,rollouts=0,physics_steps=0,optimization_evaluations=0,reused_t1_results=len(costs),kernel_wall_s=time.perf_counter()-started),
            referenced_t1_costs=list(costs.values()),cost_semantics='Referenced T1 costs were already charged; aggregation never charges them again.')
    if context.get('mode')=='finite_comparison':
        rows=context['rows'];base=rows[0]
        common=all(all(r['input'][k]==base['input'][k] for k in ('times_s','tendon_order','tensions_n')) for r in rows)
        return dict(method=T2,status='computed_diagnostic',direction_status='finite_comparison_only',direction_id=context['direction_id'],
            derivative_scope='no_continuous_derivative',parameters=context['parameters'],
            results=[dict(candidate=r['candidate'],reference=r['reference'],J=r['t1']['J'],initial_J=r['t1']['initial_J'],physical_changes=r['physical_changes']) for r in rows],
            fixed_control_comparable=common,control_scope='common_legal_sequence' if common else 'separate_legal_input_sets_and_initial_controls',
            task_acceptance='unmeasured',limitations=LIMITATIONS+['Discrete multi-factor contrast; unequal input channels cannot share a control sequence or establish structural causality.'],
            cost=dict(model_builds=0,rollouts=0,physics_steps=0,optimization_evaluations=0,reused_t1_results=len(rows),kernel_wall_s=time.perf_counter()-started),
            referenced_t1_costs=[dict(reference=r['reference'],cost=r['cost']) for r in rows])
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
    for key in ('direction_id','parameters','derivative_scope','coefficients','coordinate_unit'):
        if key in context:out[key]=context[key]
    out['cost']=dict(model_builds=0,rollouts=0,physics_steps=0,optimization_evaluations=0,
        reused_t1_results=0 if context.get('not_comparable') else 3,kernel_wall_s=time.perf_counter()-started)
    out['referenced_t1_costs']=[dict(reference=r['reference'],cost=r.get('cost',{}),
        accounting='Previously charged T1 computation; referenced, not charged again by T2') for r in context.get('rows',[])]
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
