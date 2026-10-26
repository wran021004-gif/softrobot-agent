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
    def metric_view(row):
        result=deepcopy(row);worst=result.get('worst_constraint')
        fields=dict(terminal_position=('terminal_error_m','terminal_position_error_m'),
            holding_position=('holding_max_error_m','holding_max_position_error_m'),holding_speed=('holding_max_speed_m_s','holding_max_speed_m_s'))
        if worst and worst['kind'] in fields:
            constraint_id,field=fields[worst['kind']]
            c=next((c for c in value.get('task_analysis',{}).get('constraints',[]) if c['constraint_id']==constraint_id),None)
            if c:worst.update(constraint_id=constraint_id,value=result[field],limit=c['radius'],unit=c['signal']['units'])
        return result
    return dict(method=T1,status='finite_budget_diagnostic',
        J=measure['signed_maximum_excess'],best_found_J=measure['signed_maximum_excess'],initial_J=initial['signed_maximum_excess'],
        improvement=initial['signed_maximum_excess']-measure['signed_maximum_excess'],
        initial_metrics=metric_view(initial),best_metrics=metric_view(measure),
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
        problem=dict(task_identity=value.get('binding',{}).get('task_identity'),protocol=value.get('protocol'),
            model=value.get('native_analysis',{}).get('basis'),constraints=value.get('task_analysis',{}).get('constraints',[]),
            time_grid_s=value.get('task_analysis',{}).get('time_grid_s'),
            input_bounds_n=value.get('binding',{}).get('tension_bounds_n'),
            initial_state_pointer='/native_dynamics/initial_state',model_source='model.mujoco_native@1.0.0'),
        search_quality=dict(global_optimality='not_established',convergence='unresolved',
            initialization='candidate-owned frozen zero state and original absolute-tension sequence',
            initialization_pointer='/native_dynamics/original_schedule',
            solver_pointer='/native_dynamics/optimization',numerical_inner_solver=value.get('native_analysis',{}).get('solver'),
            search_dimension=search.get('search_dimension'),active_coefficients=search.get('active_coefficients'),
            finite_budget_observations_retained=True),
        cost=raw['cost'],
        metric_units={k:unit for k,unit in [('terminal_position_error_m','m'),('holding_max_position_error_m','m'),
            ('holding_max_speed_m_s','m/s'),('signed_maximum_excess','1')] if k in measure},
        evidence_level='finite_budget_observation',independent_task_acceptance='unmeasured',
        task_acceptance='unmeasured',detail_pointer='/native_dynamics',limitations=LIMITATIONS)


def saved_context(host, query):
    """Admit saved T1 observations; reuse shared baselines without new rollouts."""
    from types import SimpleNamespace
    from tools.research.state import state
    from tools.research.design import verify_candidate, parameter_value, set_parameter
    from tools.research.optimal_capability import family_parameters
    from tools.research.physical_replay import binding
    from tools.research.research_context import recorded_changes
    s=state(host);request=query.nonlinear_response;cache={};parameter_cache={}
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
            original_charges={k:raw.get(k) for k in ('charged_analysis_evaluations','charged_numerical_s','operation_key')},
            t1=raw['nonlinear_capability'],protocol=raw['protocol'],input=tr,initial_state=point,cost=native['cost'])
        if native.get('optimization',{}).get('candidates'):
            from tools.research.task_constraints import describe_analysis_requirements
            requirements=describe_analysis_requirements(cfg,{})
            search=native['optimization']
            row['task_samples']={scope:sampled_constraints(source['outputs'],requirements) for scope,source in
                [('fixed_control',search['candidates'][0]),('reoptimized_control',search['best'])]}
        cache[key]=row
        return row
    def admit(direction):
        validation_refs=getattr(direction,'validation_t1_results',[])
        rows=[dict(load(ref)) for ref in [*direction.t1_results,*validation_refs]]
        if rows[0]['candidate']!=plain(query.candidate):raise ValueError('BASELINE_T1_CANDIDATE_REQUIRED')
        paths=direction.variables if direction.mode=='continuous' else direction.comparison_variables
        parameters={}
        for row in rows:
            values={}
            for path in paths:
                key=(row['candidate']['artifact_id'],path,direction.mode)
                if key not in parameter_cache:
                    parameter_cache[key]=(family_parameters(s['spec'],row['candidate_record'],path) if direction.mode=='continuous' else
                        family_parameters(s['spec'],row['candidate_record'],path,continuous=False))
                params,domain=parameter_cache[key]
                values[path]=parameter_value(params,path);parameters.setdefault(path,domain)
                row['parameters']=params
            row['parameter_values']=values
        base=rows[0];a=base['configuration']
        coordinates=None if direction.coordinates is None else [*direction.coordinates,*getattr(direction,'validation_coordinates',[])]
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
            if any(row['initial_state'].get(k)!=base['initial_state'].get(k) for k in ('phase','input_units','provenance')):
                raise ValueError('MATCHED_INITIAL_STATE_CONVENTION_REQUIRED')
            if direction.mode=='finite_comparison' and row['candidate_record'].get('initialization_provenance'):
                point=row['initial_state'];frozen=row['candidate_record']['initialization_provenance']['effective']
                if any(dict(zip(point['dof_order'],point[field]))!=frozen[field] for field in ('qpos_rad','qvel_rad_s')):
                    raise ValueError('OWN_FROZEN_INITIAL_STATE_REQUIRED')
            if direction.mode=='continuous':
                expected=deepcopy(base['parameters'])
                for path,coefficient in direction.variables.items():
                    origin=base['parameter_values'][path];delta=row['parameter_values'][path]-origin
                    wanted=coefficient*coordinates[index]
                    if not math.isclose(delta,wanted,rel_tol=1e-9,abs_tol=4*math.ulp(float(origin))):
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
        return dict(rows=rows[:3],validation_rows=rows[3:],parameter=next(iter(parameters.values())) if legacy else dict(units=direction.coordinate_unit),
            parameters=parameters,direction_id=direction.direction_id,mode='continuous',
            derivative_scope='independent_parameter_secant' if independent else 'coupled_path_secant' if len(paths)>1 else 'scaled_path_secant',
            coefficients=dict(direction.variables),coordinate_unit=direction.coordinate_unit)
    contexts=[]
    for d in directions:
        try:contexts.append(admit(d))
        except (ValueError,KeyError,IndexError) as exc:contexts.append(dict(not_comparable=str(exc),direction_id=d.direction_id))
    if legacy:return contexts[0]
    return dict(directions=contexts,unique_t1_results=len(cache),baseline=plain(directions[0].t1_results[0]))


def candidate_responses(host, reference):
    """Derive exact requests from saved observations, using the execution gate."""
    from tools.research.state import state
    from tools.research.design import verify_candidate,parameter_value
    from tools.research.optimal_capability import family_analysis_parameters
    from extensions.tendon_family.family_space import resolved_request
    from tools.research.contracts import AnalysisRequest
    s=state(host);spec=s['spec'];candidate=verify_candidate(host,reference)
    parameters=family_analysis_parameters(spec,candidate);inventory=[];ready=[]
    for ref in s.get('analysis_results',[]):
        raw=host.store.artifact(ref)
        if (raw.get('status')!='computed' or raw.get('implementation')!=s['freeze'] or raw.get('protocol')!=spec['analysis_protocol']
                or raw.get('nonlinear_capability',{}).get('method')!=T1):continue
        c=verify_candidate(host,raw['candidate'])
        inventory.append(dict(reference=ref,candidate=raw['candidate'],parameters=resolved_request(spec['family_space'],c['parameters'])))
    for base in [r for r in inventory if r['candidate']==plain(reference)]:
        for row in parameters:
            if not row['study_authorized'] or not row['continuous_perturbation']:continue
            path=row['parameter_id'];zero=parameter_value(base['parameters'],path);points=[]
            for point in inventory:
                try:points.append((parameter_value(point['parameters'],path)-zero,point))
                except (KeyError,IndexError):continue
            for low,minus in points:
                if low>=0:continue
                for high,plus in points:
                    if high<=0 or not math.isclose(-low,high,rel_tol=1e-10):continue
                    query=dict(candidate=plain(reference),operation=T2_OPERATION,model_source='mujoco',
                        operating_point='standardized_initial_pretension',protocol=spec['analysis_protocol'],
                        nonlinear_response=dict(variable=path,unit=row['unit'],t1_results=[base['reference'],minus['reference'],plus['reference']]))
                    if 'not_comparable' not in saved_context(host,AnalysisRequest.model_validate(query)):
                        ready.append(query)
    batch=None
    if ready:
        baseline=ready[0]['nonlinear_response']['t1_results'][0];directions=[];seen=set()
        for query in ready:
            r=query['nonlinear_response'];path=r['variable']
            if r['t1_results'][0]!=baseline or path in seen:continue
            low=next(p for p in inventory if p['reference']==r['t1_results'][1]);zero=next(p for p in inventory if p['reference']==baseline)
            h=parameter_value(zero['parameters'],path)-parameter_value(low['parameters'],path)
            directions.append(dict(direction_id=path,variables={path:1.},coordinate_unit=r['unit'],coordinates=[0.,-h,h],t1_results=r['t1_results']))
            seen.add(path)
            if len(directions)==32:break
        batch={**ready[0],'nonlinear_response':dict(version='nonlinear_response_v2',directions=directions)}
    return dict(parameters=parameters,ready_requests=ready,batch_request=batch,
        preparation='Choose a legal physical path/step, generate actual candidates, initialize legal controls and run authorized T1 per candidate. Reuse the common baseline. No automatic model, optimization or physical experiment.',
        direction_semantics='V1 is one symmetric parameter; V2 explicitly records independent axes, coupled dp/ds paths or finite discrete contrasts.')


def observations(context):
    """Source-linked finite facts survive unresolved search/direction decisions."""
    rows=[]
    for r in context.get('rows',[]):
        t=r['t1'];ref=r['reference']
        rows.append(dict(candidate=r['candidate'],reference=ref,coordinate=r.get('value'),
            parameter_values=r.get('parameter_values'),physical_changes=r.get('physical_changes'),
            fixed_control=dict(J=t['initial_J'],metrics=t.get('initial_metrics'),
                source=dict(reference=ref,pointer='/native_dynamics/optimization/candidates/0/measure')),
            reoptimized_control=dict(best_found_J=t['J'],metrics=t.get('best_metrics'),
                source=dict(reference=ref,pointer='/native_dynamics/optimization/best/measure')),
            worst_constraint=t.get('best_metrics',{}).get('worst_constraint'),
            stop_reason=t['stop_reason'],search_quality=t.get('search_quality'),settings=t.get('settings'),
            callbacks=t['callbacks'],iterations_started=t['iterations_started'],
            input_saturation=t['input_saturation'],coefficient_boundary=t['coefficient_boundary'],
            model_scope=t.get('problem'),initialization=dict(reference=ref,pointer='/native_dynamics/initial_state'),
            solver=dict(reference=ref,pointer='/native_dynamics/optimization'),
            recorded_cost=r.get('cost'),original_charges=r.get('original_charges'),
            cost_source=dict(reference=ref,pointer='/native_dynamics/cost'),
            control_schedule=dict(reference=ref,pointer='/native_dynamics/optimized_schedule'),
            evidence_level='finite_budget_observation',task_acceptance='unmeasured'))
    return rows


def metric_responses(rows,step,coordinate_unit):
    units=rows[0]['t1'].get('metric_units',{})
    matrix=[]
    for field,unit in units.items():
        item=dict(metric=field,unit=unit,secant_unit=unit+' / '+coordinate_unit)
        for label,key in [('fixed_control','initial_metrics'),('reoptimized_control','best_metrics')]:
            values=[r['t1'].get(key,{}).get(field) for r in rows]
            if not all(type(v) in (int,float) and math.isfinite(v) for v in values):continue
            zero,low,high=values
            item[label]=dict(values=values,delta_minus=low-zero,delta_plus=high-zero,
                left=(zero-low)/step,right=(high-zero)/step,central=(high-low)/(2*step),
                sources=[dict(reference=r['reference'],pointer='/nonlinear_capability/'+key+'/'+field) for r in rows])
        matrix.append(item)
    return matrix


def comparison_summary(result):
    rows=[]
    for i,d in enumerate(result.get('directions',[result])):
        facts=d.get('observations',[]);base=facts[0]['reoptimized_control']['best_found_J'] if facts else None
        lower=[dict(coordinate=r['coordinate'],delta_J=r['reoptimized_control']['best_found_J']-base) for r in facts[1:]
            if base is not None and r['reoptimized_control']['best_found_J']<base-d.get('practical_J_tolerance',1e-6)]
        rows.append(dict(direction_id=d.get('direction_id'),status=d['direction_status'],derivative_scope=d.get('derivative_scope'),
            parameters=list(d.get('parameters',{})),observed_lower_J=lower,
            observed_changed_metrics=[m['metric'] for m in d.get('metric_responses',[]) if any(
                abs(m.get(label,{}).get(delta,0))>0 for label in ('fixed_control','reoptimized_control') for delta in ('delta_minus','delta_plus'))],
            evidence_level='finite_budget_observation',strict_improvement_direction='unresolved',change_significance='unresolved_without_error_bound',
            followup_hypothesis='Recheck the observed lower J with an independent control initialization' if lower else 'Check another legal step or initialization',
            detail_pointer='/nonlinear_response/directions/'+str(i) if 'directions' in result else '/nonlinear_response'))
        if d.get('task_sensitivity'):
            rows[-1]['task_sensitivity']={k:dict(status=v['status'],reasons=v.get('reasons',[]),
                maximum_validation_error_over_threshold=max((r['maximum_error_over_threshold'] for r in v.get('validation',[])),default=None),
                active_switches=v.get('active_switches',[])) for k,v in d['task_sensitivity'].items()}
    return rows


def sampled_constraints(outputs, requirements):
    """Original adapter constraints at every original sample, normalized by its limit."""
    from tools.research.native_analysis import task_proxy
    limits={c.constraint_id:c.radius for c in requirements.constraints}
    rows=[]
    for t,p,v in zip(outputs['times_s'],outputs['tip_positions_m'],outputs['tip_velocities_m_s']):
        for row in task_proxy(requirements,dict(time_s=t,tip_position_m=p,tip_velocity_m_s=v)):
            limit=limits[row['constraint_id']]
            rows.append({k:row[k] for k in ('constraint_id','sample_index','time_s','value','units')} |
                dict(limit=limit,normalized_signed_excess=-min(row['margins'])/limit))
    return rows


def active_samples(samples):
    active={}
    for row in samples:
        key=row['constraint_id']
        if key not in active or row['normalized_signed_excess']>active[key]['normalized_signed_excess']:
            active[key]=row
    worst=max(samples,key=lambda r:r['normalized_signed_excess'])
    return dict(per_constraint={k:r['sample_index'] for k,r in active.items()},
        worst=[worst['constraint_id'],worst['sample_index']])


def validate_prediction(base, derivative, coordinate, actual):
    """Empirical held-out error, never a bound; retain physical units per sample."""
    zero=np.array([r['normalized_signed_excess'] for r in base]);truth=np.array([r['normalized_signed_excess'] for r in actual])
    predicted=zero+coordinate*np.asarray(derivative);change=truth-zero;expected=predicted-zero;error=predicted-truth
    material=np.maximum(abs(change),abs(expected))>1e-8
    correct=(change*expected>0) | ~material
    comparable=abs(error)<np.maximum(abs(change),1e-8)
    status='validated_local_prediction' if np.all(correct & comparable) and np.any(material) else 'unresolved'
    return dict(coordinate=coordinate,status=status,direction_correct=bool(np.all(correct)),
        maximum_error_over_threshold=float(max(abs(error))),
        maximum_error_over_actual_change=float(max(abs(error)/np.maximum(abs(change),1e-8))),
        predicted_J=float(max(predicted)),actual_J=float(max(truth)),J_error=float(max(predicted)-max(truth)),
        active_prediction=active_samples([dict(r,normalized_signed_excess=float(y)) for r,y in zip(base,predicted)]),
        active_actual=active_samples(actual),
        samples=[dict(constraint_id=r['constraint_id'],sample_index=r['sample_index'],time_s=r['time_s'],units=r['units'],
            predicted_change=float(dp*r['limit']),actual_change=float(da*r['limit']),
            error=float(e*r['limit']),error_over_threshold=float(e),direction_correct=bool(ok))
            for r,dp,da,e,ok in zip(base,expected,change,error,correct)])


def task_sensitivities(context):
    rows=context['rows'];h=rows[2]['value']-rows[0]['value'];result={}
    if any(not r.get('task_samples') for r in rows):return {}
    # A coupled path is normalized by its feasible coordinate interval, not mixed units.
    lower=[];upper=[]
    for path,coefficient in context.get('coefficients',{}).items():
        p=context['parameters'][path];origin=rows[0]['parameter_values'][path]
        if p.get('minimum') is not None and p.get('maximum') is not None:
            ends=sorted([(p['minimum']-origin)/coefficient,(p['maximum']-origin)/coefficient])
            lower.append(ends[0]);upper.append(ends[1])
    span=min(upper)-max(lower) if upper else None
    for scope in ('fixed_control','reoptimized_control'):
        samples=[r['task_samples'][scope] for r in rows]
        keys=lambda ss:[(r['constraint_id'],r['sample_index']) for r in ss]
        if not samples[0] or any(keys(s)!=keys(samples[0]) for s in samples[1:]):continue
        y=np.array([[r['normalized_signed_excess'] for r in s] for s in samples])
        left=(y[0]-y[1])/h;right=(y[2]-y[0])/h;central=(y[2]-y[1])/(2*h)
        active=[active_samples(s) for s in samples]
        switches=[k for k in active[0]['per_constraint'] if len({a['per_constraint'][k] for a in active})>1]
        if any(a['worst']!=active[0]['worst'] for a in active[1:]):switches.append('signed_J')
        reasons=['ACTIVE_CONSTRAINT_OR_TIME_SWITCH'] if switches else []
        if np.any(left*right<0):reasons.append('OPPOSING_ONE_SIDED_RESPONSES')
        validation=[]
        for row in context.get('validation_rows',[]):
            actual=row.get('task_samples',{}).get(scope)
            if actual and keys(actual)==keys(samples[0]):
                check=validate_prediction(samples[0],central,row['value']-rows[0]['value'],actual)
                check['reference']=row['reference'];validation.append(check)
                if check['status']=='unresolved':reasons.append('HELD_OUT_PREDICTION_FAILED_OR_TOO_SMALL')
                if check['active_actual']!=active[0]:reasons.append('HELD_OUT_ACTIVE_CONSTRAINT_OR_TIME_SWITCH')
        if scope=='reoptimized_control':
            reasons.append('FINITE_BUDGET_CONTROL_OPTIMALITY_UNRESOLVED')
        result[scope]=dict(status='unresolved' if reasons else 'validated_local_prediction' if validation else 'local_estimate_unvalidated',
            reasons=sorted(set(reasons)),coordinate_unit=context['parameter']['units'],step=h,
            samples=samples[0],finite_difference_per_unit=central.tolist(),
            left_per_unit=left.tolist(),right_per_unit=right.tolist(),legal_coordinate_span=span,
            dimensionless_sensitivity=None if span is None else (central*span).tolist(),
            active_samples=active,active_switches=switches,validation=validation,
            source_results=[r['reference'] for r in rows],
            interpretation='Sampled normalized constraint secants. No ordinary max gradient at active switches; no strict error bound.')
    return result


def control_sensitivities(search, requirements):
    """Reuse the actual local_control_search probes without extra integration."""
    indexed={r['reference']:r for r in search['candidates']};responses=[]
    for probe in search['candidates']:
        if probe['label']!='finite_difference':continue
        base=indexed[probe['prediction_base']]
        delta=np.asarray(probe['coefficients_n'])-base['coefficients_n'];selected=np.flatnonzero(delta)
        if len(selected)!=1:continue
        j=int(selected[0]);a=sampled_constraints(base['outputs'],requirements);b=sampled_constraints(probe['outputs'],requirements)
        derivative=[(v['normalized_signed_excess']-u['normalized_signed_excess'])/delta[j] for u,v in zip(a,b)]
        responses.append(dict(coefficient_index=j,delta_n=float(delta[j]),samples=a,finite_difference_per_n=derivative,
            scheme=probe.get('derivative_scope','one-sided control response'),projected=probe.get('projected_response'),
            baseline_rollout=base['reference'],probe_rollout=probe['reference'],
            active_baseline=active_samples(a),active_probe=active_samples(b),status='local_estimate_unvalidated'))
    return dict(parameterization='original local_control_search knot-major absolute-tension offsets',responses=responses,
        new_physics_steps=0,scope='Full frozen control intervals; no single-physics-step Jacobian substitution.')


def compare_scales(results):
    for i,direction in enumerate(results):
        peers=[other for j,other in enumerate(results) if i!=j and direction.get('coefficients') and
            direction.get('coefficients')==other.get('coefficients') and direction.get('step')!=other.get('step')]
        for scope,value in direction.get('task_sensitivity',{}).items():
            comparisons=[]
            for peer in peers:
                other=peer.get('task_sensitivity',{}).get(scope)
                if not other or value['samples']!=other['samples']:continue
                a=np.asarray(value['finite_difference_per_unit']);b=np.asarray(other['finite_difference_per_unit'])
                relative=float(np.max(abs(a-b))/max(float(np.max(abs(b))),1e-15))
                agrees=not bool(np.any((a*b<0)&(np.maximum(abs(a),abs(b))*min(value['step'],other['step'])>1e-8)))
                comparisons.append(dict(direction_id=peer['direction_id'],relative_difference=relative,direction_agrees=agrees))
                if relative>.05 or not agrees:
                    value['status']='unresolved';value['reasons'].append('TWO_SCALE_DISAGREEMENT')
            value['scale_comparisons']=comparisons
            if not comparisons and value['status']=='validated_local_prediction':
                value['status']='unresolved';value['reasons'].append('SECOND_SCALE_NOT_AVAILABLE')


def response(context):
    """Descriptive secants plus a conservative decision, never an optimal gradient."""
    started=time.perf_counter()
    if context.get('directions') is not None:
        results=[response(c) for c in context['directions']]
        compare_scales(results)
        costs={r['reference']['artifact_id']:dict(reference=r['reference'],cost=r.get('cost',{}))
            for c in context['directions'] for r in [*c.get('rows',[]),*c.get('validation_rows',[])]}
        out=dict(method=T2,version='nonlinear_response_v2',status='computed_diagnostic' if any(r['status']=='computed_diagnostic' for r in results) else 'not_comparable',
            direction_status='unresolved',baseline=context['baseline'],directions=results,task_acceptance='unmeasured',limitations=LIMITATIONS,
            cost=dict(model_builds=0,rollouts=0,physics_steps=0,optimization_evaluations=0,reused_t1_results=len(costs),kernel_wall_s=time.perf_counter()-started),
            referenced_t1_costs=list(costs.values()),cost_semantics='Referenced T1 costs were already charged; aggregation never charges them again.')
        out['comparison_summary']=comparison_summary(out)
        return out
    if context.get('mode')=='finite_comparison':
        rows=context['rows'];base=rows[0]
        common=all(all(r['input'][k]==base['input'][k] for k in ('times_s','tendon_order','tensions_n')) for r in rows)
        return dict(observations=observations(context),method=T2,status='computed_diagnostic',direction_status='finite_comparison_only',direction_id=context['direction_id'],
            derivative_scope='no_continuous_derivative',parameters=context['parameters'],
            results=[dict(candidate=r['candidate'],reference=r['reference'],J=r['t1']['J'],initial_J=r['t1']['initial_J'],physical_changes=r['physical_changes']) for r in rows],
            fixed_control_comparable=common,control_scope='common_legal_sequence' if common else 'separate_legal_input_sets_and_initial_controls',
            task_acceptance='unmeasured',limitations=LIMITATIONS+['Discrete multi-factor contrast; unequal input channels cannot share a control sequence or establish structural causality.'],
            cost=dict(model_builds=0,rollouts=0,physics_steps=0,optimization_evaluations=0,reused_t1_results=len(rows),kernel_wall_s=time.perf_counter()-started),
            referenced_t1_costs=[dict(reference=r['reference'],cost=r['cost']) for r in rows])
    out=dict(observations=observations(context),method=T2,status='not_comparable',direction_status='not_comparable',
        task_acceptance='unmeasured',limitations=LIMITATIONS,
        cost=dict(model_builds=0,rollouts=0,physics_steps=0,optimization_evaluations=0,
            reused_t1_results=0 if context.get('not_comparable') else 3,kernel_wall_s=0.))
    if context.get('not_comparable'):out['reasons']=[context['not_comparable']]
    else:
        rows=context['rows'];base,minus,plus=rows;h=base['value']-minus['value']
        out['task_sensitivity']=task_sensitivities(context)
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
        out['metric_responses']=metric_responses(rows,h,context['parameter']['units'])
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
        reused_t1_results=0 if context.get('not_comparable') else 3+len(context.get('validation_rows',[])),kernel_wall_s=time.perf_counter()-started)
    out['referenced_t1_costs']=[dict(reference=r['reference'],cost=r.get('cost',{}),
        accounting='Previously charged T1 computation; referenced, not charged again by T2') for r in
        [*context.get('rows',[]),*context.get('validation_rows',[])]]
    out['comparison_summary']=comparison_summary(out)
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
