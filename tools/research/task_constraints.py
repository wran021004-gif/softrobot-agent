"""Pure task translation and existing local-tool applicability; no Store or solver."""
from schemas.platform import Binding, Payload
from tools.platform_store import plain
from tools.research_tasks import task_adapter


def analysis_capabilities(configuration, requirements, protocol, *, model=None, exact_point=None,
                          remaining_evaluations=None):
    """Candidates for existing operations, using the same execution applicability gate."""
    from types import SimpleNamespace
    from typing import get_args
    from tools.research.contracts import AnalysisRequest
    from schemas.platform_analysis import TaskAnalysisProtocol
    from schemas.platform import SessionInput
    configuration=SessionInput.model_validate(configuration)
    p=TaskAnalysisProtocol.model_validate(protocol)
    rows=[]
    for operation in get_args(AnalysisRequest.model_fields['operation'].annotation):
        sampled=operation in ('trajectory_feasibility','task_capability')
        static=operation in ('equilibrium','input_sensitivity','design_sensitivity')
        point='target_equilibrium' if operation=='equilibrium' else 'fixed_input_equilibrium' if static else 'controller_start_input'
        if exact_point and not static:point='saved_state'
        query=SimpleNamespace(operation=operation,operating_point=point,protocol=p,
            scoring_window_s=p.windows_s[0] if p.windows_s else None)
        assessment=model_assessment(configuration,requirements,operation)
        applicability=check_analysis_applicability(requirements,query,assessment,model,exact_point)
        reasons=list(applicability['reasons'])
        if operation=='instantaneous_braking_v1' and exact_point is None:
            reasons.append('Exact saved state required.')
        count=3 if operation=='design_sensitivity' else 1
        budget=None if remaining_evaluations is None else remaining_evaluations>=count
        if budget is False:reasons.append('Insufficient mathematical evaluation budget.')
        rows.append(dict(operation=operation,status='not_applicable' if reasons else applicability['status'],
            reasons=reasons,model=assessment['model_id'],
            constraint_kinds=['norm_bound','component_interval'] if sampled else ['norm_bound'],
            required_outputs=sorted({c.signal.name for c in requirements.constraints}) if sampled else
                ['tip_velocity'] if operation in ('braking','instantaneous_braking_v1') else ['tip_position'],
            category='task_capability_estimate' if operation=='task_capability' else 'sampled_feasibility' if sampled else 'diagnostic',
            control='reoptimized; optional fixed baseline replay' if operation=='task_capability' else
                'bounded sequence search' if sampled or operation in ('endpoint','braking') else 'operating-point diagnostic',
            prerequisites=['candidate','frozen protocol',point]+(['paired structure candidates'] if operation=='design_sensitivity' else []),
            time_scope='aligned post-step samples over actual remaining horizon' if sampled else
                'static operating point' if static else 'declared local scoring window or exact instant',
            coverage=applicability['constraint_coverage'],full_task_supported=applicability['full_task_supported'],
            budget_allowed=budget,evaluations=count,wall_cost='unknown',
            limitations=['Model-scoped calculation; independent physical acceptance required.',
                'Final admission checks candidate, exact state, numerical time budget and constructed outputs.']))
    return rows


def describe_analysis_requirements(configuration, binding):
    return task_adapter(configuration).analysis_requirements(binding)


def model_assessment(configuration, requirements, operation):
    """Use the same GVS model binding as the candidate linearization builder."""
    from extensions.tendon_family.model_applicability import assess_model_uses
    from tools.platform_registry import registry
    use = 'static_equilibrium' if operation in ('equilibrium','input_sensitivity','design_sensitivity') else 'linearization'
    model = Binding(extension_id='model.gvs', version='1.0.0', parameters=Payload(
        contract='family.gvs_model', data=dict(basis=configuration.policy.controller.parameters.data['recipe']['basis'])))
    if configuration.policy.controller.extension_id == 'controller.sorosim_matlab_nmpc':
        model = Binding(extension_id='model.sorosim_gvs',version='1.0.0',parameters=Payload(
            contract='family.sorosim_model',data=dict(basis=configuration.policy.controller.parameters.data['recipe']['basis'])))
    reg = registry()
    declaration = reg.mathematical_model(model)
    assessment = plain(assess_model_uses(configuration.robot, configuration.task, model, [use],
        required_physics={use:requirements.required_physics}, registry=reg))
    declared = {name for name, supported in plain(declaration.capabilities).items() if supported}
    unknown = set(requirements.required_physics)-set(declaration.unsupported_physics)-declared
    if unknown:
        assessment['uses'][use]['status'] = 'REJECT'
        assessment['uses'][use]['reasons'].append('Required physics has no declared capability: '+', '.join(sorted(unknown)))
    return assessment


def check_analysis_applicability(requirements, query, assessment, model=None, exact_point=None):
    """Describe partial terminal coverage separately from diagnostics and execution.

    Preflight output signatures are the fixed EndpointOutputLinearization exports
    of tendon_family.math_analysis.linear_model; constructed models are checked
    again using their actual outputs before metrics/endpoint computations.
    """
    reasons = [reason for verdict in assessment['uses'].values() if verdict['status'] == 'REJECT'
               for reason in verdict['reasons']]
    if (query.operation in ('input_sensitivity','design_sensitivity') or query.operating_point=='fixed_input_equilibrium') and assessment['model_id']!='model.sorosim_gvs':
        reasons.append('Static IFT v1 is implemented only by the SoRoSim provider.')
    outputs = {'tip_position':('m', 'world', 3), 'tip_velocity':('m/s', 'world', 3)}
    if model is not None:
        outputs = {o.name:(o.units, o.frame, o.dimension) for o in model.endpoint_outputs}
    p = query.protocol
    if abs(p.duration_s-requirements.duration_s) > p.horizon_alignment_atol_s:
        reasons.append('Protocol duration differs from the frozen task horizon.')
    if abs(p.period_s-requirements.physical_inputs['control_period_s']) > p.horizon_alignment_atol_s:
        reasons.append('Protocol period differs from the frozen physical input grid.')
    point = model.operating_point if model is not None else exact_point or {}
    trajectory = query.operation in ('trajectory_feasibility', 'task_capability')
    sampled = None
    if trajectory:
        from extensions.math_analysis.trajectory import time_scope
        start = point.get('actual_time_s', point.get('time_s'))
        if start is None and query.operating_point in ('standardized_initial_pretension','controller_start_input'):
            start = 0.
        try:
            sampled = time_scope(requirements, p, start)
        except ValueError as exc:
            reasons.append(str(exc))
    remaining = point.get('remaining_task_s', requirements.duration_s)
    horizon = query.scoring_window_s if query.operation in ('linearization','controllability') else remaining
    instantaneous=query.operation=='instantaneous_braking_v1'
    if instantaneous:horizon=0.
    if query.operation != 'equilibrium' and not trajectory and not instantaneous and (horizon is None or horizon <= 0 or horizon > remaining+p.horizon_alignment_atol_s
            or abs(round(horizon/p.period_s)*p.period_s-horizon) > p.horizon_alignment_atol_s):
        reasons.append('Positive aligned horizon within actual remaining task time is required.')
    if model is not None:
        inputs = requirements.physical_inputs
        if (model.time_domain != 'continuous'
                or any((s.name,s.units,s.frame) != ('tendon_tension','N','tendon_path') for s in model.input_definition)
                or model.binding.get('tendon_order') != inputs['tendon_order']
                or model.binding.get('tension_limits_n') != inputs['upper']
                or len(model.u0) != len(inputs['upper'])
                or any(not lo <= u <= hi for lo,u,hi in zip(inputs['lower'],model.u0,inputs['upper']))):
            reasons.append('Model physical input order, bounds, or operating input mismatch.')
    last = len(requirements.time_grid_s)-1
    coverage = []
    for c in requirements.constraints:
        status, indices, reason = 'not_applicable', [], 'Existing tools do not enforce this constraint kind or sampled window.'
        signature = (c.signal.units, c.signal.frame, c.signal.dimension)
        if c.kind == 'unsupported':
            reason = 'Unsupported requirement retained verbatim; no compatible mathematical tool.'
        elif outputs.get(c.signal.name) != signature or c.signal.phase != 'post_step':
            reason = 'Output identity, units, frame, dimension, or sampling phase is not exposed by this analysis.'
        elif instantaneous:
            status,reason='diagnostic','Instantaneous speed derivative only; no frozen task samples verified.'
        elif query.operation in ('linearization','controllability','equilibrium','input_sensitivity','design_sensitivity'):
            if c.signal.name == 'tip_position' and c.kind == 'norm_bound':
                status, reason = 'diagnostic', 'Local position authority/static construction only; no sampled constraint verification.'
        elif trajectory and c.kind in ('norm_bound','component_interval') and sampled is not None:
            indices = [i for i in c.indices if i in sampled['sample_steps']]
            if indices:
                status = 'applicable' if indices == c.indices else 'partial'
                reason = 'Shared held-input trajectory; past samples require separate evidence.'
        elif c.kind == 'norm_bound':
            if c.signal.name == 'tip_position' and c.indices == [last]:
                status, indices, reason = 'applicable', [last], 'Terminal position only under bounded local affine dynamics.'
            elif query.operation == 'braking' and c.signal.name == 'tip_velocity' and last in c.indices:
                status, indices, reason = 'partial', [last], 'Terminal speed only; other holding samples are not checked.'
        coverage.append(dict(constraint_id=c.constraint_id, expressible=c.kind != 'unsupported',
            status=status, analyzed_indices=indices, reason=reason))
        if trajectory:
            coverage[-1]['unchecked_indices'] = [i for i in c.indices if i not in indices]
    available = any(c['status'] != 'not_applicable' for c in coverage)
    if not available:
        reasons.append('No constraint has a compatible operation; no unrelated calculation will run.')
    if reasons:
        coverage = [{**c, 'status':'not_applicable', 'analyzed_indices':[],
                     'reason':'; '.join(reasons)+' '+c['reason']} for c in coverage]
        if trajectory:
            for c, source in zip(coverage, requirements.constraints):
                c['unchecked_indices'] = source.indices
    return dict(status='not_applicable' if reasons else 'applicable', reasons=reasons,
        constraint_coverage=coverage, full_task_supported=bool(trajectory and not reasons and sampled['start_time_s'] == 0.
            and all(c['status'] == 'applicable' for c in coverage)), execution_support='not_assessed',
        model_assessment=assessment, horizon=dict(task_duration_s=requirements.duration_s,
            remaining_task_s=remaining, analysis_horizon_s=None if query.operation == 'equilibrium' else horizon,
            period_s=p.period_s, origin=point.get('actual_time_s'),
            interpretation='static construction' if query.operation == 'equilibrium' else
                'Actual saved-state remaining horizon, or nominal horizon from the declared configuration operating point.',
            **({'trajectory_grid':sampled} if trajectory else {})))
