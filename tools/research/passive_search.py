"""Passive physical adapter for the shared search; original Workers own numerics."""
from copy import deepcopy
import math
from tools.platform_store import plain
from tools.research.state import state


def problem(spec, query):
    cfg=spec['configuration'];physical=cfg['task'].get('physical_problem')
    if not physical or physical['mode']!='passive_unilateral_equilibrium':
        raise ValueError('PASSIVE_SEARCH_REQUIRES_FROZEN_UNILATERAL_PROBLEM')
    if not spec.get('mathematical_methods',{}).get('mechanism_structure_v1'):
        raise ValueError('PASSIVE_SEARCH_REQUIRES_REGISTERED_MECHANISM_GRANT')
    if query.evaluation_mode=='passive_task_response':
        if query.objective!='task_violation':raise ValueError('COMPLETE_PASSIVE_RESPONSE_REQUIRES_TASK_OBJECTIVE')
        from tools.research.structure_research import finite_time_discovery
        fit=finite_time_discovery(cfg)
        if fit['status']=='not_applicable':
            raise ValueError('PASSIVE_TASK_SEARCH_REQUIRES_REGISTERED_RESPONSE')
        loads=['all_frozen_conditions']
    else:
        loads=query.diagnostic_load_conditions or [r['name'] for r in physical['loads']]
        if not set(loads)<={r['name'] for r in physical['loads']}:
            raise ValueError('SEARCH_LOADS_OUTSIDE_FROZEN_PROBLEM')
        if query.objective=='task_violation' and not physical.get('observations'):
            raise ValueError('STATIC_TASK_OBJECTIVE_UNAVAILABLE_USE_FULL_RESPONSE_OR_QUALIFICATION_DIAGNOSTIC')
        if query.objective=='task_violation' and not any(o['load_condition'] in loads and
                (o.get('minimum') is not None or o.get('maximum') is not None) for o in physical['observations']):
            raise ValueError('SELECTED_LOADS_HAVE_NO_FROZEN_BOUNDED_OBSERVATION')
    return dict(action='baseline_response' if query.evaluation_mode=='passive_task_response' else 'equilibrium',physical_problem=physical['mode'],conditions=loads,analyses_per_structure=len(loads),
        diagnostic_only=bool(query.diagnostic_load_conditions) or query.evaluation_mode=='passive_equilibrium',
        score_semantics=('Worst normalized frozen static observation; no dynamic task acceptance.' if query.objective=='task_violation'
            else 'Worst dimensionless physical KKT qualification residual; no task-performance objective.')
            if query.evaluation_mode=='passive_equilibrium' else
            'Complete frozen finite-time task violation, including all conditions and validity checks; independent acceptance remains separate.')


def static_score(raw, objective):
    research=raw.get('structure_research',{});records=research.get('records',[])
    if not records:return None,dict(status=raw['status'],reason=raw.get('reason'))
    mechanics=records[0]['mechanics'];constraint=mechanics['constraint_state']
    evidence=dict(constraint_state=constraint,qualification_diagnosis=mechanics.get('qualification_diagnosis'),
        task_observations=mechanics.get('task_observations',[]))
    if raw['status']!='computed' or not constraint.get('qualified'):return None,evidence
    if objective=='equilibrium_qualification':
        result=mechanics['equilibrium'];eq=result['equilibrium'];opts=result['solver_settings']
        score=max(eq['stationarity_inf_nm']/opts['stationarity_tolerance_nm'],
            eq['primal_violation_m']/opts['length_tolerance_m'],
            eq['complementarity_nm']/opts['complementarity_tolerance_nm'])-1
        return score,evidence
    gaps=[]
    evidence['bounded_observation_count']=sum(row.get(side) is not None
        for row in mechanics.get('task_observations',[]) for side in ('minimum','maximum'))
    for row in mechanics.get('task_observations',[]):
        if row.get('minimum') is None and row.get('maximum') is None:continue
        value=row['value']
        if value is None:return None,evidence
        for side in ('minimum','maximum'):
            bound=row.get(side)
            if bound is not None:
                scale=row.get('normalization_scale') or abs(bound)
                if not scale:
                    evidence['reason']='STATIC_ZERO_BOUND_REQUIRES_EXPLICIT_NORMALIZATION_SCALE'
                    return None,evidence
                gaps.append(((value-bound) if side=='maximum' else (bound-value))/scale)
    return max(gaps) if gaps else None,evidence


def evaluate(host, query, proposal, operation, persist, guard):
    """Persist per-load references before continuing; no hidden replay or control input."""
    from tools.research.analysis import dispatch
    spec=state(host)['spec'];binding=problem(spec,query)
    records=proposal.setdefault('passive_conditions',{})
    for index,condition in enumerate(binding['conditions']):
        record=records.setdefault(condition,{})
        key=operation+':passive:'+str(index)
        if 'analysis' not in record:
            dynamic=query.evaluation_mode=='passive_task_response'
            study=dict(operation='inspect',point_semantics='frozen_task_initial_state' if dynamic else 're_equilibrated',
                target=dict(quantity='finite_time_task_violation' if dynamic else 'constraint_active_set',goal='decrease'),
                effect_semantics='finite_time_task_response' if dynamic else 'mechanism_effect',max_evaluations=1)
            if dynamic and query.execution_profile:study['execution_profile']=plain(query.execution_profile)
            if not dynamic:study['load_condition']=condition
            request=dict(candidate=proposal['candidate'],operation='mechanism_structure_v1',model_source='mujoco',
                operating_point='standardized_initial_pretension',protocol=spec['analysis_protocol'],mechanism_study=study)
            output=dispatch(host,request,key,guard=guard,origin='model_search')
            if not output.get('reference'):
                record.update(status='not_admitted',rejection=output);persist();break
            record['analysis']=output['reference'];persist()
        raw=host.store.artifact(record['analysis'])
        if query.evaluation_mode=='passive_equilibrium':score,facts=static_score(raw,query.objective)
        else:
            research=raw.get('structure_research',{});observation=research.get('baseline',{})
            score=observation.get('value') if raw['status']=='computed' and observation.get('status')=='computed' else None
            facts=dict(task_gap=observation.get('task_gap'),diagnostic_task_gap=observation.get('diagnostic_task_gap'),validity=observation.get('status'))
        attributed=raw.get('operation_key')==key+'-analysis'
        unscored=(query.evaluation_mode=='passive_equilibrium' and query.objective=='task_violation' and
            facts.get('bounded_observation_count')==0 and facts.get('constraint_state',{}).get('qualified'))
        record.update(status='computed' if score is not None and math.isfinite(score) else 'qualified_without_objective' if unscored else 'unresolved',score=score,
            facts=facts,charged_analysis_evaluations=raw.get('charged_analysis_evaluations',1) if attributed else 0,
            charged_numerical_s=raw.get('charged_numerical_s',0.) if attributed else 0.)
        persist()
    scores=[r['score'] for r in records.values() if r.get('status')=='computed']
    complete=bool(scores) and len(records)==len(binding['conditions']) and all(
        r.get('status') in ('computed','qualified_without_objective') for r in records.values())
    return dict(kind=query.evaluation_mode,computation_status='computed' if complete else 'unresolved',
        proxy_values={query.objective:max(scores)} if complete else {},
        task_acceptance='unmeasured',physical_problem=binding,
        evidence=dict(candidate=proposal['candidate'],conditions=deepcopy(records)),
        actual_mathematical_evaluations=sum(r.get('charged_analysis_evaluations',0) for r in records.values()),
        mathematical_numerical_s=sum(r.get('charged_numerical_s',0.) for r in records.values()),
        limitations=['Finite local search does not establish global infeasibility or optimum.',
            'Hard static equilibrium and full native soft-limit dynamics are distinct models.'])
