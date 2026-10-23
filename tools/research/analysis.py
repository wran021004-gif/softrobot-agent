"""Candidate-bound mathematics, persistence and cumulative execution accounting."""
from copy import deepcopy
import json
import math
from pathlib import Path
import subprocess
import time
from tools.research.contracts import AnalysisRequest
from schemas.platform import SessionInput
from schemas.platform_analysis import TaskAnalysisProtocol, EndpointLinearizedModel, EndpointTarget, ScopedMathematicalClaim, TaskAnalysisRequirement
from tools.platform_store import plain, zero
from tools.state_io import digest, atomic_json, read
from tools.research.design import verify_candidate, source_lengths
from tools.research.state import state,update,save
from tools.research.task_constraints import describe_analysis_requirements, model_assessment, check_analysis_applicability


def kkt_reliability(kkt,regularity,replay):
    """Numerical residual checks do not establish a regular optimal-value branch."""
    failures=[]
    for key,tolerance in (('primal_inf',1e-8),('stationarity_inf',1e-6),
            ('dual_violation',1e-8),('complementarity_inf',1e-8)):
        if not math.isfinite(kkt.get(key,float('inf'))) or kkt[key]>tolerance:
            failures.append(key)
    if not replay.get('passed'):failures.append('independent_replay')
    if kkt.get('same_as_selected_trajectory') is not True:
        failures.append('replay_iterate_correspondence')
    activity=regularity.get('activity_diagnostics',[])
    if not activity or not all(row['numerical_LICQ'] for row in activity):
        failures.append('activity_dependent_numerical_LICQ')
    stationary=not failures
    second_order=regularity.get('second_order_sufficiency')=='independently_verified'
    return dict(numerical_KKT_checks_passed=stationary,obstructions=failures,
        regular_local_branch_verified=stationary and second_order,
        reliability='locally_checked_not_certified' if stationary else 'solver_unresolved',
        envelope_gradient_available=stationary and second_order,
        second_order=regularity.get('second_order_sufficiency','not_established'),
        gradient_error_bound=None,regional_lipschitz_bound=None,descent_certificate='unavailable',
        interpretation='Residual/rank diagnostics use finite tolerances; no rigorous regional bounds are inferred')


def complete_lagrangian_sensitivity(minus,plus,step,*,variable,qualification):
    """Paired rebuilt-model partials at identical normalized z and multipliers."""
    if not qualification.get('regular_local_branch_verified'):
        raise ValueError('ENVELOPE_GRADIENT_UNAVAILABLE_WITHOUT_REGULAR_BASE')
    if not (variable.startswith('segments.') and variable.endswith('.length_m') and step>0):
        raise ValueError('SUPPORTED_CONTINUOUS_LENGTH_PARAMETER_REQUIRED')
    terms={key:(plus['lagrangian_terms'][key]-value)/(2*step)
        for key,value in minus['lagrangian_terms'].items()}
    if set(terms)!={'objective','initial_state','complete_dynamics','task','lower_bounds','upper_bounds'}:
        raise ValueError('COMPLETE_LAGRANGIAN_TERMS_REQUIRED')
    return dict(variable=variable,step_m=step,terms=terms,derivative_per_m=sum(terms.values()),
        reliability='locally_checked_not_certified',descent_certificate='unavailable',
        assumptions='same differentiable local solution branch and valid local KKT multipliers; finite differences supply no regional error bound')


def calculate(configuration,binding,query,exact_point=None,*,checkpoint=None,design_context=None):
    """No Host, Route, session, persistence or cost ownership at this boundary."""
    from extensions.math_analysis.tools import calculate_control_metrics
    from extensions.math_analysis.kernels import bounded_endpoint, LIMITATIONS
    import numpy as np
    q=AnalysisRequest.model_validate(query)
    if q.optimal_sensitivity is not None:
        from tools.research.optimal_capability import calculate_sensitivity
        if not design_context or design_context.get('kind')!='controlled-capability-sensitivity-v1':
            raise ValueError('ADMITTED_SAVED_MODEL_CONTEXT_REQUIRED')
        return calculate_sensitivity(design_context,q,checkpoint)
    p=q.protocol
    inp=SessionInput.model_validate(configuration)
    sorosim=inp.policy.controller.extension_id=='controller.sorosim_matlab_nmpc'
    if sorosim:
        from extensions.tendon_family.sorosim_analysis import calculate_candidate_configuration
    else:
        from extensions.tendon_family.math_analysis import calculate_candidate_configuration
    requirements=describe_analysis_requirements(inp,binding)
    assessment=model_assessment(inp,requirements,q.operation)
    applicability=check_analysis_applicability(requirements,q,assessment,exact_point=exact_point)
    if applicability['status']=='not_applicable':
        return scoped_result(dict(status='not_applicable',operation=q.operation,binding=binding,protocol=plain(p),
            operating_point=exact_point or dict(name=q.operating_point),task_acceptance='unmeasured',
            proxy_values={},internal_calculations=[],limitations=LIMITATIONS),requirements,applicability,q)
    if q.capability_method and checkpoint:checkpoint('optimal_model_attempt',dict(kind='model_build',stage='attempt'))
    envelope=plain(calculate_candidate_configuration(inp,binding,p,binding['configuration'],
        operating_points=[q.operating_point],exact_point=exact_point,**({'checkpoint':checkpoint,'design_context':design_context if q.operation=='design_sensitivity' else None,
            'check_instantaneous_braking':q.operation=='instantaneous_braking_v1'} if sorosim else {})))
    rows=envelope['records'][1:]
    if q.capability_method and checkpoint:checkpoint('optimal_model_returned',dict(kind='model_build',stage='returned'))
    row=rows[0]
    construction=row.get('construction') or {}
    internal=[]
    if construction.get('solver'):
        internal.append(dict(solver=construction['solver'],purpose='operating_point_construction',
        iterations=construction.get('iterations'),function_evaluations=construction.get('function_evaluations'),status=construction.get('status')))
    result=dict(status='computed',operation=q.operation,binding=binding,protocol=plain(p),
        operating_point=row.get('point',dict(name=row.get('name'),construction=construction)),
        construction=construction,local_model_constraints=dict(status='unmeasured'),
        task_acceptance='unmeasured',proxy_values={},raw=envelope,internal_calculations=internal,
        limitations=LIMITATIONS+['Local mathematics does not establish nonlinear backend acceptance, holding-window compliance, or design sensitivity.'])
    result['score_semantics']=score_semantics(q,binding,p,row)
    if q.operation in ('input_sensitivity','design_sensitivity'):
        raw=row.get('raw_facts',{});sensitivity=raw.get(q.operation)
        for i,solve in enumerate((sensitivity or {}).get('perturbed_equilibria',[])):
            internal.append(dict(purpose='perturbed_equilibrium_verification',perturbation_index=i,**solve))
        result.update(raw_facts=raw,research_interpretations=[],sensitivity=sensitivity,
            sensitivity_protocol='sorosim_static_ift_v1')
        if row.get('model'):result['model']=row['model']
        if not sensitivity or not sensitivity.get('verification',{}).get('passed'):
            result.update(status='unavailable',unavailable_reason=row.get('reason',raw.get('sensitivity_status','SENSITIVITY_VERIFICATION_FAILED')))
        result['units']=dict(residual='N*m^2',q='rad/m',position='m',input='N',design_variable='SI unit of declared parameter')
        return scoped_result(result,requirements,applicability,q)
    if row.get('model'):
        model=EndpointLinearizedModel.model_validate(row['model'])
        if q.operation in ('trajectory_feasibility', 'task_capability'):
            point = dict(model.operating_point)
            if q.operating_point in ('standardized_initial_pretension','controller_start_input'):
                point.update(actual_time_s=0., time_origin='frozen initializer via existing controller preparation')
            if exact_point is not None:
                point.update(actual_time_s=exact_point.get('actual_time_s',exact_point.get('time_s')),
                    previous_applied_input_n=exact_point['u'])
            model=model.model_copy(update=dict(operating_point=point))
        result.update(model=plain(model),operating_point=model.operating_point)
        applicability=check_analysis_applicability(requirements,q,assessment,model=model)
        if applicability['status']=='not_applicable':
            result['status']='not_applicable'
            return scoped_result(result,requirements,applicability,q)
    if q.operation=='equilibrium':
        result['proxy_values']['target_equilibrium_residual']=construction.get('position_residual_m')
        result['local_model_constraints']=dict(status='satisfied' if row.get('model') else 'unsatisfied_in_this_attempt',
            position_residual_m=construction.get('position_residual_m'),static_residual_inf=construction.get('static_residual_inf'),
            equilibrium_available=bool(row.get('model')),global_infeasibility_proven=False)
        result['units']=dict(position_residual='m',tension='N',static_residual='raw GVS generalized-force residual; coordinate/input units and scaling recorded in model/protocol')
        tensions=construction.get('computed_tensions_n')
        if tensions is not None:
            limits=binding['tension_limits_n']
            result['tension_margins_n']=dict(lower=tensions,upper=[a-b for a,b in zip(limits,tensions)],
                interpretation='Computed attempt tensions; equilibrium validity remains separately reported')
        return scoped_result(result,requirements,applicability,q)
    if not row.get('model'):
        result.update(status='unavailable',unavailable_reason=row.get('reason','Operating point unavailable'))
        return scoped_result(result,requirements,applicability,q)
    if q.operation=='instantaneous_braking_v1':
        from extensions.math_analysis.kernels import instantaneous_braking
        result['instantaneous_braking']=instantaneous_braking(model)
        result['instantaneous_braking']['numerical_check']=row.get('raw_facts',{}).get('acceleration_check')
        if sorosim and not (result['instantaneous_braking']['numerical_check'] or {}).get('passed'):
            result.update(status='unavailable',unavailable_reason='INSTANTANEOUS_ACCELERATION_NUMERICAL_CHECK_FAILED')
        result['units']=dict(velocity='m/s',acceleration='m/s^2',tension='N',objective='m^2/s^3')
        internal.append(dict(purpose='fixed_state_box_minimum_and_acceleration_semantics',solver='componentwise box minimum; MATLAB centered velocity directional differences at working and bounded test input',nonlinear_dynamics_evaluations=6))
    elif q.operation in ('linearization','controllability'):
        remaining=model.operating_point.get('remaining_task_s')
        if q.operating_point=='saved_state' and remaining is not None:
            if q.scoring_window_s>remaining+p.horizon_alignment_atol_s:
                raise ValueError('SCORE_WINDOW_EXCEEDS_ACTUAL_REMAINING_TASK_TIME')
            p=p.model_copy(update={'windows_s':[w for w in p.windows_s if w<=remaining+p.horizon_alignment_atol_s]})
        metrics=calculate_control_metrics(model,p)
        result['metrics']=metrics
        window=next(w for w in metrics['windows'] if w['window_s']==q.scoring_window_s)
        score=window['held']['output']['eigenvalues'][0]
        result['proxy_values']['held_position_min_eigenvalue']=float(score)
        result['units']=metrics['units']
        internal.append(dict(purpose='local_linearization_and_gramian',solver=('SoRoSim MATLAB residual derivatives' if sorosim else 'CasADi AD')+' / SciPy scaled Van Loan and ZOH',windows_s=p.windows_s))
    elif q.operation in ('trajectory_feasibility', 'task_capability'):
        from extensions.math_analysis.trajectory import trajectory_feasibility
        if q.operation == 'task_capability':
            if q.capability_method:
                from extensions.math_analysis.conic_capability import conic_capability
                if checkpoint:checkpoint('optimal_capability_attempt',dict(kind='capability',stage='attempt'))
                trajectory=conic_capability(model,requirements,p)
                if checkpoint:checkpoint('optimal_capability_returned',dict(kind='capability',stage='returned',solver=trajectory.get('solver')))
            else:
                from extensions.math_analysis.task_capability import task_capability
                trajectory=task_capability(model,requirements,p)
        else:
            trajectory=trajectory_feasibility(model,requirements,p)
        if q.capability_comparison is not None:
            from tools.research.capability import compare_control_response
            trajectory['structural_comparison']=compare_control_response(model,requirements,p,trajectory,design_context)
        result['trajectory']=trajectory
        records=trajectory.get('replay',{}).get('records',[])
        if q.operation=='task_capability' and not trajectory.get('replay',{}).get('numerically_valid'):
            records=[]
        for coverage in applicability['constraint_coverage']:
            actual=next((c for c in trajectory['coverage'] if c['constraint_id']==coverage['constraint_id']),None)
            if actual:
                coverage.update(actual)
                coverage['status']='applicable' if not actual['unchecked_indices'] else 'partial' if actual['analyzed_indices'] else 'not_applicable'
            checked=[r for r in records if r['constraint_id']==coverage['constraint_id']]
            coverage.update(checked_indices=[r['sample_index'] for r in checked],
                satisfied_indices=[r['sample_index'] for r in checked if r['passed']])
        applicability['full_task_supported'] &= trajectory.get('full_requested_coverage',False)
        if trajectory['status']=='not_applicable':
            result['status']='not_applicable'
            applicability.update(status='not_applicable',reasons=[trajectory.get('reason','Unsupported trajectory scope.')])
        replay=trajectory.get('replay',{})
        result['local_model_constraints']=dict(status=trajectory['status'],
            max_absolute_violation=replay.get('max_absolute_violation'),
            max_normalized_violation=replay.get('max_normalized_violation'),
            worst_violation=replay.get('worst_violation'),minimum_tension_margin_n=replay.get('minimum_tension_margin_n'))
        internal.append(dict(purpose='sampled_trajectory',solver=trajectory.get('solver'),
            certificate=trajectory.get('certificate',{}).get('kind') if trajectory.get('certificate') else None))
        if q.operation=='task_capability':
            internal[-1].update(starts=[{k:s.get(k) for k in ('success','status','iterations','elapsed_s','objective_evaluations')} for s in trajectory.get('starts',[])],
                kernel_elapsed_s=trajectory.get('kernel_elapsed_s'),
                fixed_control_replay_elapsed_s=trajectory.get('structural_comparison',{}).get('fixed_control',{}).get('kernel_elapsed_s'))
        result['units']=dict(position='m',speed='m/s',tension='N')
        result['limitations']=[s for s in result['limitations'] if 'holding-window compliance' not in s]+[
            'Only explicitly replay-verified samples in the frozen local affine model; no continuous-time, nonlinear, or backend acceptance.']
    else:
        target=EndpointTarget(position_m=inp.task.goal.data['target_m'],position_tolerance_m=inp.task.evaluator.parameters.data['tolerance_m'],
            position_scale_m=p.output_scale_m,tip_speed_limit_m_s=inp.policy.controller.parameters.data['settling']['speed_limit_m_s'])
        endpoint=bounded_endpoint(model,p,target,braking=q.operation=='braking')
        result['endpoint']=endpoint
        result['local_model_constraints']=dict(status=endpoint['status'],checks=endpoint.get('checks'))
        if endpoint.get('solver'):
            internal.append(dict(purpose='endpoint_witness',**endpoint['solver']))
            for purpose,certificate in endpoint['independent_residual_problems'].items():
                internal.append(dict(purpose=purpose+'_box_residual_certificate',solver=certificate['solver'],success=certificate['solver_success']))
        result['units']=dict(position='m',speed='m/s',tension='N')
    result['tension_margins_n']=dict(lower=model.u0,upper=(np.asarray(binding['tension_limits_n'])-model.u0).tolist())
    return scoped_result(result,requirements,applicability,q)


def scoped_result(result, requirements, applicability, query):
    """Classify trusted kernel verification fields; solver success is not a proof."""
    conclusion, verification = 'inconclusive', 'insufficient'
    interpretation = 'No verified witness or certificate is available for this attempt.'
    endpoint = result.get('endpoint') or {}
    checks = endpoint.get('checks') or {}
    certificate = endpoint.get('infeasibility_certificate') or {}
    separation = certificate.get('separating_direction') or {}
    pointer = '/endpoint' if endpoint else '/raw' if 'raw' in result else ''
    trajectory = result.get('trajectory') or {}
    if applicability['status'] == 'not_applicable':
        conclusion, verification, pointer = 'not_applicable', 'not_performed', '/analysis_applicability'
        interpretation = '; '.join(applicability['reasons'])
    elif result['status'] == 'computed':
        if result.get('optimal_sensitivity'):
            conclusion,verification,pointer='diagnostic',result['optimal_sensitivity']['direction_status'],'/optimal_sensitivity'
            interpretation='Controlled reoptimized finite differences of sampled local models; no strict structural gradient, regional descent or physical improvement guarantee.'
        elif result.get('instantaneous_braking'):
            conclusion,verification,pointer='diagnostic','fixed_state_box_minimum','/instantaneous_braking'
            interpretation=result['instantaneous_braking']['scope']
        elif result.get('sensitivity',{}).get('verification',{}).get('passed'):
            conclusion,verification,pointer='diagnostic','perturbed_equilibria_checked','/sensitivity'
            interpretation='Local implicit-function sensitivity in the fixed-topology physical model; not a globally improving direction or task feasibility.'
        elif trajectory:
            pointer='/trajectory'
            if trajectory['status']=='feasible_witness' and trajectory.get('replay',{}).get('passed') is True:
                conclusion,verification='feasible_witness','independent_discrete_replay_passed'
                interpretation=('All declared sampled constraints verified' if applicability['full_task_supported'] else
                    'Only the explicitly covered sampled constraints verified; incomplete frozen-task coverage')+' in the specified local affine model only.'
            elif (trajectory['status']=='model_infeasibility_certificate' and trajectory.get('certificate',{}).get('verified') is True
                    and math.isfinite(trajectory['certificate'].get('margin',float('nan'))) and trajectory['certificate']['margin']>0):
                conclusion,verification='model_infeasibility_certificate','necessary_constraint_box_exclusion_verified'
                interpretation='The identified necessary sampled constraint excludes the joint local-model task under the complete declared input box; other constraints need not be analyzed.'
            if query.operation=='task_capability' and trajectory.get('replay',{}).get('numerically_valid'):
                if conclusion=='inconclusive':
                    verification='legal_input_and_signed_score_replay_checked'
                    interpretation='A legal control and its signed sampled score were checked; no feasible witness or infeasibility proof found.'
                interpretation+=(' Finite-tolerance numerical optimality checks: '+trajectory.get('optimality_status','unknown')+
                    '; strict optimal-value bounds and structural optimality remain unavailable.' if query.capability_method else
                    ' Optimal task violation and structural optimality remain unverified.')
        elif endpoint.get('status') == 'feasible_in_local_model' and endpoint.get('applied_input_n') and all(
                checks.get(k) is True for k in ('finite','lower_bounds','upper_bounds','position','speed')):
            conclusion, verification = 'feasible_witness', 'kernel_independent_checks_passed'
            interpretation = 'Verified bounded input for the covered terminal constraints of this frozen local affine model only.'
        elif (endpoint.get('status') == 'infeasible_in_local_model' and certificate.get('certified_infeasible') is True
                and math.isfinite(separation.get('margin_over_limit', float('nan')))
                and separation['margin_over_limit'] > 0):
            conclusion, verification = 'model_infeasibility_certificate', 'kernel_separating_lower_bound_verified'
            interpretation = 'Verified separating lower bound excludes the covered endpoint problem within this model and input box only.'
        elif query.operation in ('linearization','controllability') and result.get('metrics'):
            conclusion, verification, pointer = 'diagnostic', 'not_a_constraint_certificate', '/metrics'
            interpretation = 'Local normalized Gramian/output authority; physical bounded-input task feasibility is unverified.'
        elif query.operation == 'equilibrium' and result.get('local_model_constraints',{}).get('equilibrium_available'):
            conclusion, verification = 'diagnostic', 'static_construction_only'
            interpretation = 'Local static construction residuals only; sampled holding and execution remain unverified.'
    result['task_analysis'] = plain(requirements)
    result['analysis_applicability'] = applicability
    result['scoped_claim'] = plain(ScopedMathematicalClaim(conclusion=conclusion, binding=requirements.binding,
        requirement_identity=digest(plain(requirements)), model_identity=digest(result['model']) if result.get('model') else None,
        model_declaration={k:applicability['model_assessment'][k] for k in ('model_id','model_version','representation_id','relevant_assumptions')},
        protocol_identity=digest(plain(query.protocol)), operating_point=result.get('operating_point') or dict(name=query.operating_point),
        horizon=applicability['horizon'], physical_inputs=requirements.physical_inputs,
        constraint_coverage=applicability['constraint_coverage'], numerical_result_pointer=pointer,
        computation_status=result['status'], verification_status=verification, supported_interpretation=interpretation,
        unsupported_conclusions=['task acceptance', 'continuous-time holding-window compliance' if trajectory else 'whole holding-window compliance', 'global nonlinear feasibility or infeasibility',
            'hardware performance', 'robustness', 'repeatability', 'equilibrium validity at a non-equilibrium point']))
    return result


def admission(host,requested=1,engineering=False):
    s=state(host)
    count=max(0,min(requested,s['spec']['budgets']['mathematical_evaluations']-s.get('mathematical_evaluations',0)))
    return dict(admitted=count,requested=requested,reservation_s=0.,timeout_s=None,remaining_numerical_s=None)


def dispatch(host,query,key,*,guard,origin='model'):
    q=AnalysisRequest.model_validate(query)
    request_id=key+'-analysis'
    identity=digest(plain(q))
    old=host.store.lookup(host.run_id,request_id)
    if old:
        if old['request_hash']!=identity:
            raise ValueError('ANALYSIS_OPERATION_ID_COLLISION')
        if not old['receipt']:
            raise ValueError('PENDING_ANALYSIS_RECOVER_WITHOUT_RECOMPUTATION')
        ref=json.loads(old['receipt'])['output']
        return dict(**compact_result(host.store.artifact(ref),ref),
            operation_reuse=dict(additional_numerical_s=0,additional_analysis_evaluations=0))
    guard(host,origin!='engineering_preflight')
    if state(host)['base_configuration']['task']['family']=='task.tracking':
        return dict(status='not_applicable',reason='TRACKING_ROBOT_MODEL_CONSTRUCTION_UNSUPPORTED',task_acceptance='unmeasured')
    from tools.research.tool_readiness import require
    require(host,'analysis')
    if state(host)['spec'].get('research_decisions') and 'analysis' not in state(host)['spec']['capabilities']:
        raise ValueError('ANALYSIS_CAPABILITY_REQUIRED')
    method_fit=None
    if q.capability_method:
        from tools.research.optimal_capability import method_admission
        current=state(host)
        method_fit=method_admission(current['spec'],q,current.get('mathematical_evaluations',0))
        if method_fit['status']!='admissible':return dict(status='not_applicable',admission=method_fit,task_acceptance='unmeasured')
    try:c=verify_candidate(host,q.candidate)
    except (ValueError,KeyError) as exc:
        if method_fit:return dict(status='not_applicable',reason=str(exc),admission=method_fit,task_acceptance='unmeasured')
        raise
    sensitivity_context=None
    if q.design_sensitivity:
        from extensions.tendon_family.sorosim_analysis import design_context
        sensitivity_context=design_context(c,verify_candidate(host,q.design_sensitivity.minus_candidate),
            verify_candidate(host,q.design_sensitivity.plus_candidate),q.design_sensitivity,q.protocol)
    if q.capability_comparison is not None:
        from tools.research.capability import comparison_context
        sensitivity_context=comparison_context(host,c,q)
    if q.optimal_sensitivity is not None:
        from tools.research.optimal_capability import sensitivity_context as saved_context
        try:sensitivity_context=saved_context(host,q)
        except (ValueError,KeyError) as exc:
            return dict(status='not_applicable',reason=str(exc),admission=method_fit,task_acceptance='unmeasured')
        from tools.research.optimal_capability import sensitivity_cost
        reused=len(q.optimal_sensitivity.model_results)
        method_fit.update(model_reuse=reused,model_reuse_status='validated_current_study_models',
            planning=sensitivity_cost(len(q.optimal_sensitivity.steps),reused,method_fit['remaining_evaluations']))
    s=state(host)
    protocol=plain(q.protocol)
    if protocol!=s['spec']['analysis_protocol'] or (q.scoring_window_s is not None and q.scoring_window_s not in protocol['windows_s']):
        raise ValueError('ANALYSIS_REQUIRES_DECLARED_FROZEN_PROTOCOL')
    count=3 if q.operation=='design_sensitivity' else 2 if q.capability_comparison is not None else 1
    if method_fit:count=method_fit['expected_mathematical_evaluations']
    fit=admission(host,requested=count,engineering=origin=='engineering_preflight')
    if fit['admitted']<count:
        raise ValueError('ANALYSIS_AND_CONFIRMATION_BUDGET_CANNOT_FIT')
    cfg=c['configuration']
    design=cfg['robot']['structure']['data']
    from extensions.tendon_family.gvs_basis import resolve_basis
    basis=cfg['policy']['controller']['parameters']['data']['recipe']['basis']
    binding=dict(candidate_id=c['candidate_id'],candidate=plain(q.candidate),configuration=c['configuration_reference'],
        effective_configuration_identity=digest(cfg),task_identity=digest(cfg['task']),basis=basis,
        coordinate_order=list(resolve_basis(design,basis).coordinate_order),tendon_order=[t['id'] for t in design['tendons']],
        tension_limits_n=[t['force_limit_n'] for t in design['tendons']],tension_bounds_n=[[0.,t['force_limit_n']] for t in design['tendons']],
        target_m=cfg['task']['goal']['data']['target_m'],source_identity=c['source_identity'],
        evaluation_profile_identity=c['profile_identity'])
    if c.get('generation_version'):
        binding.update(canonical_task_identity=c['task_identity'],initialization_provenance=c['initialization_provenance'])
    point=None
    if q.execution:
        from tools.research.numerics import execution_update
        source=execution_update(host,q.execution,q.update_id)
        record=source['record']
        observation=source.get('observation') or {}
        if source['provenance'].get('candidate')!=plain(q.candidate) or source['configuration']!=cfg:
            raise ValueError('EXACT_EXECUTION_STATE_CANDIDATE_MISMATCH')
        if record['coordinate_order']!=binding['coordinate_order'] or record['tendon_order']!=binding['tendon_order']:
            raise ValueError('EXECUTION_STATE_COORDINATE_OR_TENDON_ORDER_MISMATCH')
        t=record['prediction_timing']['current_time_s']
        duration=cfg['task']['timing']['duration_s']
        if not 0<=t<=duration or abs(record['time_s']-t)>1e-12:
            raise ValueError('EXECUTION_STATE_TIME_MISMATCH')
        point=dict(name='saved_state',available=True,x=record['measured_state'],u=record['previous_applied_input_n'],
            phase='interval_start_previous_applied_input',input_units='N',actual_time_s=t,time_s=t,remaining_task_s=max(0.,duration-t),
            coordinate_order=record['coordinate_order'],tendon_order=record['tendon_order'],
            imported_historical_evidence=source.get('imported_historical_evidence',False),
            backend_measurements={k:observation.get(k) for k in ('tip_position_m','tip_velocity_m_s')},
            construction=dict(method='GVS state projected from recorded MuJoCo interval start; linearizes at previous applied input',
                provenance=source['provenance'],new_command_n=record['actual_applied_action_n'],
                interpretation='Backend measurements are observed; endpoint/motion estimates concern the local GVS model.'))
    if q.saved_state:
        point=deepcopy(host.store.artifact(q.saved_state))
        if point.get('candidate')!=plain(q.candidate) or point.get('configuration_identity')!=digest(cfg):
            raise ValueError('EXACT_SAVED_STATE_CANDIDATE_MISMATCH')
        if (len(point['x'])!=2*len(binding['coordinate_order']) or len(point['u'])!=len(binding['tendon_order'])
                or point.get('coordinate_order')!=binding['coordinate_order'] or point.get('tendon_order')!=binding['tendon_order']
                or point.get('phase')!='interval_start_previous_applied_input' or point.get('input_units')!='N'):
            raise ValueError('EXACT_SAVED_STATE_ORDER_AND_PHASE_REQUIRED')
        point.update(name='saved_state',available=True,construction=dict(method='exact immutable saved state',state=plain(q.saved_state)))
    if point and (len(point['x'])!=2*len(binding['coordinate_order']) or len(point['u'])!=len(binding['tendon_order'])):
        raise ValueError('EXACT_STATE_DIMENSION_MISMATCH')
    if point:
        actual=point.get('actual_time_s',point.get('time_s'))
        if actual is None or not 0<=actual<=cfg['task']['timing']['duration_s']:
            raise ValueError('EXACT_SAVED_STATE_ACTUAL_TIME_REQUIRED')
        point['remaining_task_s']=max(0.,cfg['task']['timing']['duration_s']-actual)
        if q.operation in ('linearization','controllability') and q.scoring_window_s>point['remaining_task_s']+q.protocol.horizon_alignment_atol_s:
            raise ValueError('SCORE_WINDOW_EXCEEDS_ACTUAL_REMAINING_TASK_TIME')
    inp=SessionInput.model_validate(cfg)
    requirements=describe_analysis_requirements(inp,binding)
    applicability=check_analysis_applicability(requirements,q,
        model_assessment(inp,requirements,q.operation),exact_point=point)
    reserve=fit['reservation_s']
    def charge(db):
        current=host.store.session(host.run_id,db)['state']
        if current.get('success_gate') or current.get('mathematical_evaluations',0)+count>current['spec']['budgets']['mathematical_evaluations']:
            raise ValueError('MATHEMATICAL_COUNT_OR_SUCCESS_GATE')
        current['mathematical_evaluations']=current.get('mathematical_evaluations',0)+count
        current['numerical_reserved_s']+=reserve
        host.store.update_state(db,host.run_id,current)
    row,_=host.store.reserve(host.run_id,request_id,identity,host.actor,
        {**zero(),'wall_s':reserve,'tool_calls':int(origin=='engineering_preflight')},kind='candidate_analysis',guard=charge)
    folder=host.store.root/'analyses'/row['execution_id']
    folder.mkdir(parents=True,exist_ok=True)
    request=dict(implementation=s['freeze'],rationale=query.get('rationale','Model-requested '+q.operation) if isinstance(query,dict) else q.operation,kind='candidate_analysis',configuration=cfg,binding=binding,query=plain(q),exact_point=point,
        task_analysis=plain(requirements),analysis_applicability=applicability)
    if sensitivity_context:request['design_context']=sensitivity_context
    if method_fit:request['method_admission']=method_fit
    atomic_json(folder/'request.json',request)
    pending=dict(kind='candidate_analysis',worker_request_id=request_id,reserved_s=reserve,folder=str(folder),
        request=plain(q),origin=origin,implementation=s['freeze'],started_unix=time.time(),analysis_evaluations=count)
    if method_fit:pending['method_admission']=method_fit
    update(host,pending=pending)
    from tools.service_execution import _run_contained
    from sys import executable
    started=time.perf_counter()
    try:
        with (folder/'worker.log').open('w',encoding='utf8') as log:
            done=_run_contained([executable,'-m','tools.research.execution_worker',str(folder/'request.json')],log,None)
        boundary=dict(termination_confirmed=True,returncode=done.returncode,timed_out=False)
    except subprocess.TimeoutExpired as exc:
        boundary=dict(termination_confirmed=getattr(exc,'termination_confirmed',False),timed_out=True)
    except Exception as exc:
        boundary=dict(termination_confirmed=False,error=str(exc))
    boundary['elapsed_s']=time.perf_counter()-started
    atomic_json(folder/'boundary.json',boundary)
    return recover(host)


def recover(host):
    s=state(host)
    p=s['pending']
    folder=Path(p['folder'])
    if not (folder/'boundary.json').exists() or not read(folder/'boundary.json')['termination_confirmed']:
        raise ValueError('UNKNOWN_ANALYSIS_TERMINATION_RETAINS_RESERVATION; NO_RELAUNCH')
    boundary=read(folder/'boundary.json')
    elapsed=boundary['elapsed_s']
    value=read(folder/'result.json') if (folder/'result.json').exists() else dict(status='incomplete',task_acceptance='unmeasured',boundary=boundary)
    if (folder/'worker_runtime.json').exists():value['worker_runtime']=read(folder/'worker_runtime.json')
    # New failed workers still carry scope; old receipts are never reinterpreted.
    if 'scoped_claim' not in value and (folder/'request.json').exists():
        request=read(folder/'request.json')
        if 'task_analysis' in request:
            value=scoped_result(value,TaskAnalysisRequirement.model_validate(request['task_analysis']),
                request['analysis_applicability'],AnalysisRequest.model_validate(request['query']))
    value.update(candidate=p['request']['candidate'],requested_operation=p['request'],operation_key=p['worker_request_id'],
        owning_study=host.run_id,origin=p['origin'],implementation=p['implementation'],charged_numerical_s=elapsed,
        charged_analysis_evaluations=p.get('analysis_evaluations',1),boundary=boundary,worker_log=save(host,dict(text=(folder/'worker.log').read_text(encoding='utf8',errors='replace')),'analysis_worker_log'))
    if p.get('method_admission'):
        value['method_admission']=p['method_admission']
        value['numerical_call_events']=[read(path) for path in sorted(folder.glob('numerical_optimal_*.json'))]
        cost=value.get('optimal_sensitivity',{}).get('computation_cost')
        value['actual_mathematical_calls']=(dict(capability_kernel_calls=cost['conic_solves'],dual_face_solve_attempts=cost['dual_face_solves'],model_builds=0)
            if cost else dict(status='Returned trajectory establishes a kernel call; interrupted work without a result has unknown call counts.',
                capability_kernel_calls=1 if value.get('trajectory') else None,
                dual_face_solve_attempts=0 if not p['request'].get('optimal_sensitivity') else None))
        value['recorded_attempt_boundaries']={kind:sum(e['kind']==kind and e['stage']=='attempt' for e in value['numerical_call_events'])
            for kind in ('model_build','capability','dual_face')}
        value['recorded_return_boundaries']={kind:sum(e['kind']==kind and e['stage']=='returned' for e in value['numerical_call_events'])
            for kind in ('model_build','capability','dual_face')}
        value['attempt_boundary_semantics']='Durable pre-call boundaries; interruption between checkpoint and call cannot establish that the solver entered. Reserved evaluations never reset.'
    if value['status'] not in ('computed','unavailable','not_applicable'):
        value['internal_calculations']=dict(status='partial_or_unavailable',reason='Worker failed before complete calculation records were published; reservation and analysis attempt remain charged')
    ref=save(host,value,'candidate_analysis_result')
    row=host.store.lookup(host.run_id,p['worker_request_id'])
    with host.store.transaction() as db:
        current=host.store.session(host.run_id,db)['state']
        if not current.get('pending') or current['pending'].get('worker_request_id')!=p['worker_request_id']:
            raise ValueError('ANALYSIS_ALREADY_SETTLED; NO_RECOMPUTATION_OR_DOUBLE_CHARGE')
        current['numerical_s']+=elapsed
        current['numerical_reserved_s']-=p['reserved_s']
        current['pending']=None
        current.setdefault('analysis_results',[]).append(ref)
        current.setdefault('analysis_costs',[]).append(dict(reference=ref,origin=p['origin'],numerical_s=elapsed,
            mathematical_evaluations=p.get('analysis_evaluations',1),internal_calculations=value.get('internal_calculations',[])))
        host.store.update_state(db,host.run_id,current)
        host.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=host.actor,
            tool_id='research.candidate_analysis',tool_version='1.0.0',execution_status='completed',charged=zero()),value,elapsed=elapsed,db=db)
    from tools.research.tool_readiness import observe_failure
    observe_failure(host,value,ref)
    return compact_result(value,ref)


def compact_result(value, reference):
    """Compatible public tool response, with exact pointers into raw evidence."""
    summary=dict(reference=reference,**{k:value.get(k) for k in (
        'status','candidate','operation','proxy_values','origin','charged_numerical_s','charged_analysis_evaluations',
        'local_model_constraints','internal_calculations','score_semantics','scoped_claim','analysis_applicability')})
    summary['stored_result_keys']=list(value)
    summary['retrieval_note']='This is a tool summary, not the stored artifact layout. Read only the explicit stored pointers; oversized full results may be offloaded.'
    tensions=(value.get('construction') or {}).get('computed_tensions_n')
    if value.get('status')=='computed' and tensions is not None:
        summary['static_input_observation']=dict(tensions_n=tensions,units='N',
            tendon_order=(value.get('binding') or {}).get('tendon_order'),pointer='/construction/computed_tensions_n',
            task_acceptance='unmeasured',scope='Computed static operating input; no dynamic reach or hold guarantee')
    if value.get('sensitivity'):
        summary['input_response_observation']=dict(pointer='/sensitivity',
            verification=value['sensitivity'].get('verification'),task_acceptance='unmeasured')
    summary['control_handoff']=dict(candidate=value.get('candidate'),
        scope={k:(value.get('binding') or {}).get(k) for k in ('task_identity','effective_configuration_identity','tendon_order')},
        operating_point=(value.get('operating_point') or {}).get('name'),
        numerically_verified_input_sensitivity=bool(value.get('operation')=='input_sensitivity' and value.get('status')=='computed'
            and value.get('sensitivity',{}).get('verification',{}).get('passed') is True),
        request_fields=dict(candidate=value.get('candidate'),method='mathematical_response',response_evidence=reference)
            if value.get('operation')=='input_sensitivity' else None,
        remaining_checks='Current registered evidence, candidate/model/task/operating-point/channel binding and Plan admission',
        missing=None if value.get('operation')=='input_sensitivity' else 'Verified input_sensitivity required for mathematical_response; equilibrium alone is not dynamic success',
        task_acceptance='unmeasured')
    trajectory=value.get('trajectory') or {}
    if trajectory.get('method_version')=='sampled-affine-conic-minimax-v1':
        summary['control_handoff'].update(request_fields=dict(candidate=value.get('candidate'),
            method='capability_sequence',response_evidence=reference),
            missing=None,remaining_checks='Current Study/candidate/implementation, original full ZOH horizon, input bounds/order, independent replay and physical execution binding; no automatic execution',
            inherited_acceptance=False)
    cert=trajectory.get('certificate') or {}
    summary.update(task_acceptance='unmeasured',numerical_evidence=dict(reference=reference,
        pointer=(value.get('scoped_claim') or {}).get('numerical_result_pointer','')),
        trajectory_evidence=dict(solver_scope=trajectory.get('solver_scope'),
            witness_pointer='/trajectory/replay' if trajectory.get('replay',{}).get('passed') else None,
            certificate_pointer='/trajectory/certificate' if cert else None,
            certificate={k:cert.get(k) for k in ('constraint_id','sample_index','kind','margin')} if cert else None))
    from tools.research.evidence_policy import summarize_evidence
    summary['evidence_summary']=summarize_evidence(value,reference)
    if value.get('operation') == 'task_capability':
        from tools.research.capability import capability_summary
        summary['task_capability']=capability_summary(trajectory)
    if value.get('optimal_sensitivity'):
        from tools.research.capability import sensitivity_summary
        summary.pop('task_capability',None)
        summary['optimal_sensitivity']=sensitivity_summary(value['optimal_sensitivity'])
    if value.get('instantaneous_braking'):summary['instantaneous_braking']=value['instantaneous_braking']
    return {**{k:summary[k] for k in ('reference','stored_result_keys','control_handoff','static_input_observation',
        'input_response_observation','retrieval_note') if k in summary},**summary}


def decision_result(value, reference):
    """Small deterministic Agent view; the immutable scientific result is untouched."""
    claim=value.get('scoped_claim') or {}
    trajectory=value.get('trajectory') or {}
    replay=trajectory.get('replay') or {}
    if value.get('operation')=='task_capability' and not replay.get('numerically_valid'):
        replay={}
    constraints={c['constraint_id']:c for c in (value.get('task_analysis') or {}).get('constraints',[])}
    rows=[]
    for i,r in enumerate(replay.get('records',[])):
        c=constraints.get(r['constraint_id'])
        if not c: continue
        rows.append(dict(constraint_id=r['constraint_id'],signal=r['signal'],absolute_time_s=r['absolute_time_s'],
            observed_value=r['value'],bound=c['radius'] if c['kind']=='norm_bound' else dict(lower=c['lower'],upper=c['upper']),
            margin=r['margins'],violation=r['violation'],units=r['units'],
            status='satisfied_sample' if r['passed'] else 'attempted_sequence_violation',
            source_pointer=f'/trajectory/replay/records/{i}'))
    # Prefer the kernel's worst normalized violation; otherwise retain a tight
    # sampled margin. Ranking only selects records, never recomputes their values.
    records=replay.get('records',[])
    def rank(row):
        record=records[int(row['source_pointer'].rsplit('/',1)[1])]
        return (-record.get('signed_violation',record['normalized_violation']),min(row['margin']))
    rows.sort(key=rank)
    conclusion=claim.get('conclusion','inconclusive')
    meanings={
        'feasible_witness':('Bounded local-model witness for checked samples.',
            'Controller/nonlinear/backend realization unresolved.', 'Compare compatible execution or solver diagnosis.'),
        'model_infeasibility_certificate':('Verified necessary-constraint exclusion in this model/input box.',
            'Other structures, models and nonlinear paths unresolved.', 'Inspect assumptions or compare actuation geometry.'),
        'inconclusive':('No verified witness or exclusion certificate.',
            'Task expressibility does not resolve feasibility.', 'Inspect solver, operating point or another design hypothesis.'),
        'not_applicable':('Requested model/operation cannot represent declared requirements.',
            'Robot-task feasibility unresolved.', 'Select an applicable model or specialized tool.'),
        'diagnostic':('Local model diagnostic only.',
            'Bounded task feasibility unresolved.', 'Check task constraints with an applicable operation.')}
    fact,unresolved,check=meanings[conclusion]
    applicability=value.get('analysis_applicability') or {}
    coverage='full' if applicability.get('full_task_supported') else 'partial' if any(
        c.get('analyzed_indices') for c in applicability.get('constraint_coverage',[])) else 'unchecked'
    result=dict(reference=reference,candidate=value.get('candidate'),task_identity=(value.get('binding') or {}).get('task_identity'),
        operation=value.get('operation'),status=value.get('status'),conclusion=conclusion,
        scope_pointer='/scoped_claim',coverage=coverage,
        margins=rows[:1],certificate_verified=claim.get('verification_status') if conclusion=='model_infeasibility_certificate' else None,
        numerical_s=value.get('charged_numerical_s'),evaluations=value.get('charged_analysis_evaluations'),
        detail_pointer=claim.get('numerical_result_pointer',''),
        decision_relevance=dict(supported_facts=[fact],unresolved_questions=[unresolved],potential_discriminating_checks=[check],
            unsupported_inferences=['Global/physical feasibility, structural necessity or surrounding-region exclusion.']),
        failure_pointer='' if value.get('status') not in ('computed','not_applicable') else None)
    from tools.research.evidence_policy import summarize_evidence
    evidence=summarize_evidence(value,reference)
    # Scope/operating-point payloads repeat the original claim and model config.
    # Keep inference strength inline; exact scope remains at scope_pointer.
    result['evidence_summary']={k:v for k,v in evidence.items() if k not in
        ('operating_point','covered_samples','assumptions')}
    if value.get('operation') == 'task_capability':
        from tools.research.capability import capability_summary
        result['task_capability']=capability_summary(trajectory)
    if value.get('optimal_sensitivity'):
        from tools.research.capability import sensitivity_summary
        result.pop('task_capability',None)
        result['optimal_sensitivity']=sensitivity_summary(value['optimal_sensitivity'])
    if value.get('instantaneous_braking'):result['instantaneous_braking']=value['instantaneous_braking']
    return result


def score_semantics(query,binding,protocol,row):
    common=dict(candidate_identity=binding['candidate_id'],model_identity=digest(row.get('model') or dict(
            candidate=binding['candidate_id'],configuration=binding.get('effective_configuration_identity'),availability='no_local_model_constructed')),
        operating_point=dict(name=(row.get('point') or {}).get('name',getattr(query,'operating_point',None)),construction=row.get('construction'),source=row.get('point')),
        scoring_window_s=query.scoring_window_s,
        comparison_conditions='Same protocol, window, normalization, input treatment, operating-point construction, task and model implementation. Changed candidates use their own compiled model.',
        unsupported_conclusions=['backend task acceptance','whole holding-window compliance','damping margin or decay rate','global feasibility/infeasibility','structural improvement attribution','manufacturable material validation'])
    return dict(held_position_min_eigenvalue=dict(**common,
        definition='Minimum eigenvalue of local finite-horizon position-output controllability Gramian for input held over each control interval',
        preference='larger',units='dimensionless under declared input/output normalization',
        normalization=dict(input_scale_n=protocol.input_scale_n,output_scale_m=protocol.output_scale_m),
        input_treatment='Unconstrained signed incremental input held per control interval; physical unilateral bounded tensions are reported separately and not fully represented by this scalar',
        represented_constraints='Local linear model and held-input sampling only',
        supported_interpretation='Local normalized position-output authority; held means held input, not task holding success'),
        target_equilibrium_residual=dict(**{**common,'scoring_window_s':None,'scoring_horizon':'static operating-point construction; no dynamic horizon'},definition='Euclidean target position residual from bounded local equilibrium construction',
            preference='smaller',units='m',normalization='none for scalar position residual',
            input_treatment='Attempt tensions bounded by actual candidate limits',represented_constraints='Bounded local static solve and independently checked residuals',
            supported_interpretation='Quality of this local construction; failure is not proof of global infeasibility'))
