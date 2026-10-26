"""Pure task translation and existing local-tool applicability; no Store or solver."""
from schemas.platform import Binding, Payload
from tools.platform_store import plain
from tools.research_tasks import task_adapter

SCIENTIFIC_INTERPRETATION = dict(
    version='scientific_interpretation_v1',
    measured_observation='Named model or physical execution observations apply only to recorded states, actual inputs, times and sampling conditions.',
    model_calculation='Calculations depend on the named model, assumptions, operating point, input bounds and horizon; nonlinear physical transfer requires validation.',
    research_hypothesis='A proposed mechanism needs subsequent observations that can support or weaken it.',
    causal_conclusion='Requires controlled conditions or other identifying evidence; unequal outcomes alone do not identify a cause.',
    prediction_difference='Match candidate, task, actual control, initial state, input channels and time grid before computing model prediction differences.',
    time_scope='Finite discrete observations alone do not establish between-sample or extrapolated dynamics; state any additional model assumptions.',
    horizon_scope='Instantaneous dynamics, local sensitivity or single-time braking authority does not establish complete finite-horizon task feasibility or infeasibility.')

METHOD_MEANINGS = {
    'linearization': ('Local dynamics', 'Frozen continuous affine A/B/C/D and drift at the declared operating point; not a trajectory or stability proof.'),
    'controllability': ('Local drive authority', 'Finite continuous/held-input normalized Gramians and output authority; signed unbounded increments do not prove bounded nonnegative tendon feasibility.'),
    'equilibrium': ('Static input construction', 'Bounded local static target construction; static balance does not establish dynamic reach or hold.'),
    'input_sensitivity': ('Static input response', 'Checked local implicit-function response of equilibrium to physical input; SoRoSim fixed-input equilibrium only.'),
    'design_sensitivity': ('Static structural response', 'Paired single-parameter local static sensitivity with fixed physical input; no global design descent guarantee.'),
    'mujoco_direct_control_v1': ('MuJoCo-direct bounded sequence optimization', 'Reach/Hold only. Reuse local response/pattern search with cloned native rollouts covering every holding sample; produces an explicit full schedule for independent physical_replay. No task acceptance or global optimality from optimization.'),
    'native_dynamics_v1': ('Native MuJoCo mechanics', 'Native mass, forces, acceleration, world tip and tendon Jacobians at an exact native state. Small internal force-balance residuals do not establish GVS/MuJoCo prediction agreement; that requires matched state/input/output comparisons.'),
    'short_input_response_v1': ('Native short input response', 'Legal actual-tension FD at two input step sizes, optional bounded correction checked by native integration. Neither two FD sizes nor two integration timesteps prove numerical convergence or a regional bound; a failed local correction does not establish infeasibility.'),
    'fixed_input_structure_v1': ('Native structure and function response', 'Recompile registered one-parameter candidates at fixed input; this response is not reoptimized structural capability or an optimal-value gradient.'),
    'endpoint': ('Bounded terminal feasibility', 'Bounded affine input sequence for covered terminal position conditions; intermediate constraints remain unchecked.'),
    'braking': ('Bounded terminal braking', 'Bounded affine sequence for covered terminal position/speed; not full holding-window compliance.'),
    'instantaneous_braking_v1': ('Instantaneous braking authority', 'Minimum instantaneous speed derivative over the physical input box at an exact saved state. Multiplying by a time interval does not establish finite-horizon braking or controllability.'),
    'trajectory_feasibility': ('Sampled feasible sequence', 'Independent discrete replay within the bounded affine model. Small internal dynamics/replay residuals are not cross-model prediction errors; failed search is inconclusive, not structural infeasibility.'),
    'task_capability': ('Best found task violation', 'Three-start SLSQP minimization of a dimensionless max normalized signed residual; physical conversion depends on the active constraint and its threshold. Negative means a model-sample feasible witness, not a globally optimal control. Condition numbers alone are not task-score error bounds.'),
    'sampled-affine-conic-minimax-v1': ('Numerical optimal task violation', 'min_U max_i g_i over an affine sampled model and physical box. SOCP primal/dual/support/gap checks are floating estimates; strict optimal_value remains unavailable. Free path progress jointly optimizes U and s, enumerating sampled corners in a chosen finite horizon; no unrestricted-time exclusion or geometric acceptance.'),
    'controlled-capability-sensitivity-v1': ('Controlled structural direction', 'Matched baseline and +/-h (optionally +/-h/2) models: reoptimized FD versus fixed U, conditional envelope and dual-face checks. Path progress is reoptimized too. Branch ties/active-set changes withhold a strict gradient; no physical improvement guarantee.')}


def mathematical_method_view(host, reference):
    """Existing candidate-bound read view: legacy T2 root plus all method details."""
    from tools.research.state import state, protected
    from tools.research.contracts import AnalysisRequest
    from tools.research.optimal_capability import candidate_methods, CONIC, SENSITIVITY
    from tools.research.design import verify_candidate
    from tools.research.research_context import mathematics_authorization
    s=state(host);spec=s['spec'];c=host.store.artifact(reference)
    if reference not in s.get('candidates',{}).values():raise ValueError('OWNED_RESOLVED_CANDIDATE_REQUIRED')
    try:verify_candidate(host,reference);binding_error=None
    except ValueError as exc:binding_error=str(exc)
    readiness=candidate_methods(host,reference) if binding_error is None else dict(
        method=SENSITIVITY,status='requires_current_profile_candidate',reasons=[binding_error])
    cfg=c['configuration'];requirements=describe_analysis_requirements(cfg,{})
    remaining=max(0,spec['budgets']['mathematical_evaluations']-s.get('mathematical_evaluations',0))
    rows=analysis_capabilities(cfg,requirements,spec['analysis_protocol'],
        remaining_evaluations=remaining,mathematical_methods={CONIC:spec.get('mathematical_methods',{}).get(CONIC),
            SENSITIVITY:spec.get('mathematical_methods',{}).get(SENSITIVITY)})
    models=[]
    for r in s.get('analysis_results',[]):
        v=host.store.artifact(r)
        if (v.get('candidate')==reference and v.get('implementation')==s['freeze'] and
                v.get('status')=='computed' and v.get('model') and v.get('protocol')==spec['analysis_protocol']):models.append(r)
    authorization=mathematics_authorization(host,s);methods={}
    closed=s['research_status']=='stopped' or protected(host)
    for row in rows:
        key=SENSITIVITY if row.get('submode') else row.get('capability_method') or row['operation']
        purpose,meaning=METHOD_MEANINGS[key]
        kinds=row.get('constraint_kinds',['norm_bound','component_interval','path_bound'])
        reasons=[*row['reasons'],*([binding_error] if binding_error else [])]
        if key==SENSITIVITY:
            reasons=[r for r in reasons if r!='candidate_variable_and_saved_model_stencil_validation_required']+readiness.get('reasons',[])
        authorized='analysis' in spec['capabilities'] and (not row.get('capability_method') or
            bool(spec.get('mathematical_methods',{}).get(key) and spec.get('mathematical_methods',{}).get(CONIC)))
        request=dict(candidate=reference,operation=row['operation'],protocol=spec['analysis_protocol'],
            operating_point='target_equilibrium' if key=='equilibrium' else 'fixed_input_equilibrium' if key in
            ('input_sensitivity','design_sensitivity') else 'saved_state' if key=='instantaneous_braking_v1' else 'controller_start_input')
        required=[]
        if key in ('linearization','controllability'):
            required.append('scoring_window_s from protocol.windows_s')
            if spec['analysis_protocol']['windows_s']:request['scoring_window_s']=spec['analysis_protocol']['windows_s'][0]
        if key=='instantaneous_braking_v1':required.append('saved_state OR execution + update_id')
        if key in ('native_dynamics_v1','short_input_response_v1','fixed_input_structure_v1','mujoco_direct_control_v1'):
            request.update(model_source='mujoco',operating_point='standardized_initial_pretension')
            required.append('Frozen initialization needs no saved source; optional saved_state OR execution + update_id uses operating_point=saved_state')
            if key!='mujoco_direct_control_v1':required.append('native={tensions_n,horizon_s,difference_step_n,correction_radius_n}')
        if key=='mujoco_direct_control_v1':
            required.append('control_optimization={source,settings}; v2 settings require explicit correction_window_s and knots_s. Window starts at the selected native state and ends at the frozen task deadline, covering all required samples.')
        if key=='fixed_input_structure_v1':required.append('structure_response={variable,candidates}; registered single-parameter candidates')
        if key=='design_sensitivity':required.append('design_sensitivity={variable,step,minus_candidate,plus_candidate}')
        if row.get('capability_method'):request['capability_method']=CONIC
        if key==SENSITIVITY:required.append('optimal_sensitivity={variable,steps,model_results baseline first}; validated stencil required')
        methods[key]=dict(operation=row['operation'],method=key,method_version=row.get('method_version',key),scientific_purpose=purpose,description=meaning,
            candidate=reference,task_identity=c.get('task_identity'),task_family=cfg['task']['family'],
            kernel_supported=True if key in ('linearization','controllability','instantaneous_braking_v1','native_dynamics_v1','short_input_response_v1','fixed_input_structure_v1','mujoco_direct_control_v1') else
                any(x.kind in kinds for x in requirements.constraints) and
                all(x.kind in kinds or x.kind == 'unsupported' for x in requirements.constraints),
            model_built=bool(models),model_sources=[dict(reference=r,pointer='/model') for r in models],
            coverage=row.get('coverage',[]),full_task_supported=row.get('full_task_supported',False),
            study_authorized=authorized,formal_scope_authorized=authorization['registered_study_scope_authorized'],
            formal_execution_authorized=bool(authorized and authorization['registered_study_scope_authorized'] is True
                and cfg['task']['family']!='task.tracking'),
            execution_status='blocked' if reasons or not authorized or closed else 'conditional_on_admission',
            missing=reasons+row.get('parameter_requirements',[])+([] if authorized else ['study_method_grant_required'])+
                ([] if authorization['registered_study_scope_authorized'] is True else ['formal_study_math_scope_required'])+
                (['study_stopped'] if s['research_status']=='stopped' else ['protected_closeout'] if closed else []),
            estimated_evaluations=row['evaluations'],wall_cost='unknown',
            cost_scope=row.get('evaluation_rule','Model preparation and internal solver attempts are distinct; see original receipts.'),
            limitations=row['limitations'],prerequisites=row['prerequisites'],applicability=row,
            required_parameters=required,request_template=request,
            detail_query=dict(reference=reference,view='mathematical_capabilities',pointer='/methods/'+key),
            schema_query=dict(reference=reference,view='mathematical_capabilities',pointer='/analysis_request_schema'))
        methods[key]['planning_status']=('unauthorized' if not authorized or authorization['registered_study_scope_authorized'] is not True else
            'unsupported' if binding_error or row.get('planning_status')=='unsupported' else
            'insufficient_budget' if row.get('budget_allowed') is False else
            'blocked' if closed else row.get('planning_status','unsupported' if reasons else 'ready'))
        if key==SENSITIVITY:
            methods[key]['readiness']=readiness
            methods[key]['cost_scope']='M*B conic solves + up to 2*k dual-face attempts; M=1+2*k. B=1 except two-segment paths: samples-2. Model preparation additional; wall cost unknown.'
            methods[key].update(registered=True,authorized=methods[key]['formal_execution_authorized'],
                applicable=row['task_applicable'] and any(r.get('parameter') for r in readiness.get('variables',[])),
                executable=bool(methods[key]['formal_execution_authorized'] and not closed and readiness.get('status')=='executable'))
            if not methods[key]['executable']:methods[key]['execution_status']='blocked'
            elif not reasons:methods[key]['planning_status']='ready'
            methods[key]['structural_proposal']='Optional research_plan(action=generate, generation=<copy current parameters with one bounded edit>, supporting_evidence=[T2 result], decision.claimed_inference=empirical_search). Choose direction and step from the evidence; unresolved permits contrasts or no edit. New candidate requires its own T1 control reoptimization (1 model + B solves); physical acceptance remains unmeasured.'
        if key=='mujoco_direct_control_v1':
            if spec.get('native_control_limits'):methods[key]['execution_limits']=spec['native_control_limits']
            executions=[r for r in s.get('results',[]) if host.store.artifact(r).get('candidate')==reference]
            if executions:
                methods[key]['measured_control_initialization']=dict(action='initialize_control',
                    control_seed=dict(candidate=reference,parent=reference,source=executions[-1]),
                    next='Use the returned explicit schedule as control_optimization.source or control_search.source. Full Plan/decision and normal admission required.',
                    scope='Measured applied NMPC tensions only, exact candidate/task/channels/grid/bounds; acceptance is not inherited.')
            methods[key]['cost_scope']='Response search: S=starts, D_i=effective active coefficients in update i; callbacks = S baselines + sum(D_i FD probes + 1 candidate evaluation per completed update), all within evaluation_requests. Partial/failed callbacks also consume the cap; recorded counts own actual cost. Each suffix rollout advances (deadline-state_time)/physics_dt steps. Native cost.physics_steps includes required prefix reconstruction and all native rollouts. evaluation_callbacks and optimization_evaluations describe the same rollouts, not extra runs. Full independent physical_replay is separate with its own physics_steps; new_physical_evaluations=0 does not mean native integration was free.'
            methods[key]['supported_task_families']=['task.reach']
            methods[key]['supported_models']=['model.mujoco_native@1.0.0']
            methods[key]['kernel_supported']=row['planning_status']!='unsupported'
            methods[key]['control_sources']='Use this candidate\'s initialize_control baseline (pretension or explicit tensions), a bound mathematical schedule, or a complete current-Study NMPC actual-input result via source+parent without channel_map. New designs require explicit legal rebinding; a PPO checkpoint is not a schedule.'
            methods[key]['handoff']='physical_replay(candidate=same candidate, source=returned control_schedule_reference); independent acceptance and public evidence_read are required before SELECT.'
        if key=='short_input_response_v1':
            methods[key]['cost_scope']='One baseline + up to four FD rollouts per channel (two input sizes, central or one-sided) + optional one nonlinear candidate rollout. Required prefix reconstruction is already included in native cost.physics_steps; recorded rollouts/physics_steps own actual cost. Full independent physical_replay is additional if requested.'
        if key==CONIC:
            from tools.research.research_context import history_index
            methods[key]['previous_work']=[{k:r[k] for k in ('owning_study','evidence_scope','actual_result',
                'repeat_hint','experimental_equivalence','source')} for r in history_index(host,reference,request)
                if r['method']==key]
            methods[key]['repeat_guidance']='Read the original result and state what new information a repeat adds. Reproducibility, numerical checks and changed conditions are legitimate; this hint never vetoes execution. Configuration/request matching alone does not prove identical models, working points or controls.'
    return dict(**readiness,candidate=reference,methods=methods,scientific_interpretation=SCIENTIFIC_INTERPRETATION,
        analysis_request_schema=AnalysisRequest.model_json_schema())


def mathematical_catalog(view):
    """Small per-method facts; full instructions and native schemas stay reachable."""
    from tools.research.optimal_capability import SENSITIVITY
    rows={}
    shared_cost='Model preparation and internal solver attempts are distinct; see original receipts.'
    for row in view['methods'].values():
        item={k:row[k] for k in ('scientific_purpose','description','method_version','kernel_supported','model_built','full_task_supported','study_authorized',
            'formal_execution_authorized','execution_status','planning_status','missing','estimated_evaluations','cost_scope','supported_task_families','execution_limits',
            'registered','authorized','applicable','executable') if k in row}
        item['detail_pointer']='/methods/'+row['method']
        if row.get('measured_control_initialization'):
            item['control_initialization_query']={**row['detail_query'],'pointer':item['detail_pointer']+'/measured_control_initialization'}
        if row['method']==SENSITIVITY and row.get('authorized') and 'missing_validated_model_stencil' in row['missing']:
            item['preparation_query']={**row['detail_query'],'pointer':item['detail_pointer']+'/readiness'}
            item['preparation_hint']='Authorized; model group not prepared. Read allowed variables, bounded h / h/2, generation/model requests and estimated math cost here; other missing items still apply.'
        item['coverage']=[{k:v for k,v in c.items() if k in ('constraint_id','status','expressible')} for c in row['coverage']]
        item['missing']=list(dict.fromkeys(item['missing']))
        if item.get('cost_scope')==shared_cost:item.pop('cost_scope')
        rows[row['method']]=item
    binding=next(iter(view['methods'].values()))
    return dict(version='mathematical_capability_catalog_v1',listed_methods_implemented=True,candidate=view['candidate'],task_identity=binding['task_identity'],task_family=binding['task_family'],
        detail_query=dict(reference=view['candidate'],view='mathematical_capabilities',pointer='/methods'),
        schema_query=dict(reference=view['candidate'],view='mathematical_capabilities',pointer='/analysis_request_schema'),
        formal_scope_authorized=binding['formal_scope_authorized'],model_sources=binding['model_sources'][-1:],cost_scope=shared_cost,
        limitations=['Candidate-bound planning only; all model/state/input/protocol and remaining-budget admission checks still apply.',
            'Agent selected_method is proposal text, not execution admission. Unlisted combinations have no registered executable template; even listed methods require request-specific admission.',
            'Local sampled numerical evidence does not prove physical acceptance or strict/global optimality.'],methods=rows)


def analysis_capabilities(configuration, requirements, protocol, *, model=None, exact_point=None,
                          remaining_evaluations=None, mathematical_methods=None):
    """Candidates for existing operations, using the same execution applicability gate."""
    from types import SimpleNamespace
    from typing import get_args
    from tools.research.contracts import AnalysisRequest,NativeAnalysisOptions
    from schemas.platform_analysis import TaskAnalysisProtocol
    from schemas.platform import SessionInput
    configuration=SessionInput.model_validate(configuration)
    p=TaskAnalysisProtocol.model_validate(protocol)
    rows=[]
    for operation in get_args(AnalysisRequest.model_fields['operation'].annotation):
        native=operation in ('native_dynamics_v1','short_input_response_v1','fixed_input_structure_v1','mujoco_direct_control_v1')
        sampled=operation in ('trajectory_feasibility','task_capability','mujoco_direct_control_v1')
        static=operation in ('equilibrium','input_sensitivity','design_sensitivity')
        point='standardized_initial_pretension' if native else 'target_equilibrium' if operation=='equilibrium' else 'fixed_input_equilibrium' if static else 'controller_start_input'
        if exact_point and not static:point='saved_state'
        query=SimpleNamespace(operation=operation,operating_point=point,protocol=p,
            scoring_window_s=p.windows_s[0] if p.windows_s else None,
            native=NativeAnalysisOptions() if native else None,control_optimization=None)
        parameters=[]
        if operation=='mujoco_direct_control_v1':
            # Probe only required coverage, not a fabricated executable source or search settings.
            start=(exact_point or {}).get('actual_time_s',0.)
            query.control_optimization=SimpleNamespace(settings=SimpleNamespace(correction_window_s=[start,requirements.duration_s]))
            parameters=['control_optimization.source','control_optimization.settings (version=local_control_search_v2, explicit correction_window_s and knots_s)']
        assessment=model_assessment(configuration,requirements,operation,model=model,model_source='mujoco' if native else 'controller')
        applicability=check_analysis_applicability(requirements,query,assessment,model,exact_point)
        reasons=list(applicability['reasons'])
        if operation=='mujoco_direct_control_v1' and configuration.task.family!='task.reach':
            reasons.append('MuJoCo-direct v1 supports Reach/Hold only.')
        if operation=='instantaneous_braking_v1' and exact_point is None:
            reasons.append('Exact saved state required.')
        planning='unsupported' if reasons else 'requires_parameters' if parameters else 'ready'
        count=3 if operation in ('design_sensitivity','fixed_input_structure_v1') else 1
        budget=None if remaining_evaluations is None else remaining_evaluations>=count
        if budget is False:reasons.append('Insufficient mathematical evaluation budget.')
        rows.append(dict(operation=operation,status='not_applicable' if reasons else 'requires_parameters' if parameters else applicability['status'],
            planning_status='unsupported' if planning=='unsupported' else 'insufficient_budget' if budget is False else planning,
            parameter_requirements=parameters,
            reasons=reasons,model=assessment['model_id'],
            constraint_kinds=['norm_bound','component_interval'] if sampled else ['norm_bound'],
            required_outputs=sorted({c.signal.name for c in requirements.constraints}) if sampled else
                ['tip_velocity'] if operation in ('braking','instantaneous_braking_v1') else ['tip_position'],
            category='native_control_diagnostic' if operation=='mujoco_direct_control_v1' else 'task_capability_estimate' if operation=='task_capability' else 'sampled_feasibility' if sampled else 'diagnostic',
            control='bounded native sequence reoptimization' if operation=='mujoco_direct_control_v1' else 'reoptimized; optional fixed baseline replay' if operation=='task_capability' else
                'bounded sequence search' if sampled or operation in ('endpoint','braking') else 'operating-point diagnostic',
            prerequisites=['candidate','frozen protocol',point]+(['paired structure candidates'] if operation=='design_sensitivity' else []),
            time_scope='aligned post-step samples over actual remaining horizon' if sampled else
                'static operating point' if static else 'declared local scoring window or exact instant',
            coverage=applicability['constraint_coverage'],full_task_supported=applicability['full_task_supported'],
            budget_allowed=budget,evaluations=count,wall_cost='unknown',
            limitations=['Model-scoped calculation; independent physical acceptance required.',
                'Final admission checks candidate, exact state, numerical time budget and constructed outputs.']))
    if mathematical_methods:
        from tools.research.optimal_capability import CONIC,SENSITIVITY,dependencies,conic_subproblems
        env=dependencies()
        path=next((c for c in requirements.constraints if c.kind=='path_bound'),None)
        subproblems=conic_subproblems(requirements)
        for method in (CONIC,SENSITIVITY):
            count=1+subproblems if method==CONIC else 3*subproblems+2
            reasons=[]
            if not mathematical_methods.get(method) or not mathematical_methods.get(CONIC):reasons.append('method_not_authorized')
            if not env['available']:reasons.append('worker_dependency_unavailable')
            if remaining_evaluations is not None and remaining_evaluations<count:reasons.append('insufficient_budget')
            if method==SENSITIVITY:reasons.append('candidate_variable_and_saved_model_stencil_validation_required')
            query=SimpleNamespace(operation='task_capability',operating_point='controller_start_input',
                protocol=p,scoring_window_s=None,capability_method=CONIC)
            fit=check_analysis_applicability(requirements,query,model_assessment(configuration,requirements,'task_capability',model),model)
            reasons.extend(fit['reasons'])
            rows.append(dict(operation='task_capability',capability_method=CONIC,
                submode='optimal_sensitivity' if method==SENSITIVITY else None,
                method_version=('sampled-affine-conic-path-progress-v1' if method==CONIC else 'controlled-path-progress-sensitivity-v1') if path is not None else method,
                status='not_applicable' if reasons else 'conditional',reasons=reasons,dependency_environment=env,
                task_applicable=fit['status']!='not_applicable',
                planning_status='unauthorized' if 'method_not_authorized' in reasons else 'unsupported' if fit['reasons'] or not env['available'] else
                    'insufficient_budget' if 'insufficient_budget' in reasons else 'requires_parameters' if method==SENSITIVITY else 'ready',
                evaluations=count,evaluation_rule=(f'One model build plus {subproblems} internal conic subproblems' if method==CONIC else f'(1+2*k)*{subproblems}+2*k kernel/dual-face solves for k central step sizes; existing models required'),
                **(dict(kernel_subproblems_per_model=subproblems) if path is not None else {}),
                **(dict(coverage=fit['constraint_coverage'],full_task_supported=fit['full_task_supported']) if fit is not None else {}),
                remaining_evaluations=remaining_evaluations,
                budget_allowed=None if remaining_evaluations is None else remaining_evaluations>=count,
                prerequisites=['Current owned candidates, applicable task/model, frozen protocol and explicit method grant']+
                    (['Single authorized parameter; model_results baseline first; explicit steps; all model bindings checked'] if method==SENSITIVITY else []),
                limitations=['Floating numerical checks only; no strict optimum, gradient or physical acceptance.']))
    return rows


def describe_analysis_requirements(configuration, binding):
    return task_adapter(configuration).analysis_requirements(binding)


def endpoint_target(requirements, protocol, *, braking=False):
    """Project only declared terminal norm conditions into the existing kernel."""
    from schemas.platform_analysis import EndpointTarget
    last=len(requirements.time_grid_s)-1
    def terminal(name):
        return [c for c in requirements.constraints if c.kind=='norm_bound'
                and c.signal.name==name and last in c.indices
                and (c.signal.entity,c.signal.units,c.signal.frame,c.signal.dimension,c.signal.phase)==
                    ('tip','m' if name=='tip_position' else 'm/s','world',3,'post_step')]
    positions=terminal('tip_position');velocities=terminal('tip_velocity')
    if not positions or (braking and not velocities):
        raise ValueError('Terminal norm position (and velocity for braking) conditions required; path progress is not a fixed endpoint problem.')
    def select(rows):
        references=[c.reference[c.indices.index(last)] for c in rows]
        if any(r!=references[0] for r in references):
            raise ValueError('Endpoint kernel requires one consistent terminal reference per output.')
        return references[0],min(c.radius for c in rows)
    position,radius=select(positions)
    args=dict(position_m=position,position_tolerance_m=radius,position_scale_m=protocol.output_scale_m)
    if velocities:
        velocity,limit=select(velocities)
        args.update(tip_velocity_m_s=velocity,tip_speed_limit_m_s=limit)
    return EndpointTarget(**args)


def model_assessment(configuration, requirements, operation,model=None,model_source='controller'):
    """Use the same GVS model binding as the candidate linearization builder."""
    if model_source=='mujoco':
        from tools.research.native_analysis import assessment
        return assessment(configuration,requirements)
    from extensions.tendon_family.model_applicability import assess_model_uses
    from tools.platform_registry import registry
    saved_model=model is not None
    use = 'static_equilibrium' if operation in ('equilibrium','input_sensitivity','design_sensitivity') else 'linearization'
    model = Binding(extension_id='model.gvs', version='1.0.0', parameters=Payload(
        contract='family.gvs_model', data=dict(basis=configuration.policy.controller.parameters.data['recipe']['basis'])))
    if model_source=='sorosim' or (model_source=='controller' and configuration.policy.controller.extension_id == 'controller.sorosim_matlab_nmpc'):
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
    if model_source=='controller' and configuration.policy.controller.extension_id not in ('controller.gvs_nmpc','controller.sorosim_matlab_nmpc'):
        assessment['uses'][use]['status']='REJECT'
        assessment['uses'][use]['reasons'].append('No candidate model preparation implemented for this controller configuration.')
    reference=task_adapter(plain(configuration)).control_reference()
    preparation=[]
    if model_source=='sorosim' and 'solver' not in configuration.policy.controller.parameters.data:
        preparation.append('Explicit SoRoSim needs frozen SoRoSim solver settings; no settings are fabricated from another controller.')
    if not saved_model:
        control=configuration.policy.controller.parameters.data
        if control['recipe'].get('reference_mode','constant')!=reference['kind']:
            preparation.append('Candidate initializer preparation requires a controller recipe matching the task reference kind.')
        if assessment['model_id']=='model.sorosim_gvs' and reference['kind']!='constant':
            preparation.append('Current SoRoSim preparation requires a constant target working point; dynamic-reference preparation is not implemented.')
        if reference['kind']!='constant' and (configuration.policy.controller.extension_id,configuration.policy.controller.version)!=('controller.gvs_nmpc','12.0.0'):
            preparation.append('Dynamic-reference candidate preparation requires the registered GVS 12.0.0 recipe.')
    if preparation:
        assessment['uses'][use]['status']='REJECT'
        assessment['uses'][use]['reasons'].extend(preparation)
    if use=='static_equilibrium' and reference['kind']!='constant' and operation=='equilibrium':
        assessment['uses'][use]['status']='REJECT'
        assessment['uses'][use]['reasons'].append('Target-equilibrium construction assumes a constant target; a timed or free-progress reference supplies no static working point.')
    return assessment


def check_analysis_applicability(requirements, query, assessment, model=None, exact_point=None):
    """Describe partial terminal coverage separately from diagnostics and execution.

    Preflight output signatures are the fixed EndpointOutputLinearization exports
    of tendon_family.math_analysis.linear_model; constructed models are checked
    again using their actual outputs before metrics/endpoint computations.
    """
    if assessment['model_id']=='model.mujoco_native':
        from tools.research.native_analysis import applicability
        return applicability(requirements,query,assessment,exact_point)
    reasons = [reason for verdict in assessment['uses'].values() if verdict['status'] == 'REJECT'
               for reason in verdict['reasons']]
    if query.operating_point in ('target_equilibrium','halfway_waypoint'):
        positions=[c for c in requirements.constraints if c.signal.name=='tip_position']
        if any(c.kind!='norm_bound' for c in positions) or len({tuple(r) for c in positions for r in c.reference})!=1:
            reasons.append('Static target/halfway construction requires a single constant position reference, not a moving reference or free path progress.')
    if query.operation in ('endpoint','braking'):
        try:endpoint_target(requirements,query.protocol,braking=query.operation=='braking')
        except ValueError as exc:reasons.append(str(exc))
    if (query.operation in ('input_sensitivity','design_sensitivity') or query.operating_point=='fixed_input_equilibrium') and assessment['model_id']!='model.sorosim_gvs':
        reasons.append('Static IFT v1 is implemented only by the SoRoSim provider.')
    outputs = {'tip_position':('m', 'world', 3), 'tip_velocity':('m/s', 'world', 3)}
    if model is not None:
        if model.binding.get('task_identity')!=requirements.binding['task_identity']:
            reasons.append('Saved model must bind the exact task identity.')
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
        paths=[c for c in requirements.constraints if c.kind=='path_bound']
        if len(paths)>1 or any(len(c.path_vertices_m) not in (2,3) for c in paths):
            reasons.append('Current free-progress kernel supports exactly one path with one or two straight segments.')
        if paths and sampled is not None and (sampled['start_time_s']!=0
                or any(c.indices!=list(range(len(requirements.time_grid_s))) for c in paths)):
            reasons.append('Free path progress requires the complete declared initial horizon; saved partial paths need separate prefix evidence.')
        if any(len(c.path_vertices_m)==3 and len(c.indices)<3 for c in paths):
            reasons.append('A path corner requires an interior analysis sample.')
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
        elif outputs.get(c.signal.name) != signature or c.signal.phase != 'post_step' or c.signal.entity!='tip':
            reason = 'Output identity, units, frame, dimension, or sampling phase is not exposed by this analysis.'
        elif instantaneous:
            status,reason='diagnostic','Instantaneous speed derivative only; no frozen task samples verified.'
        elif query.operation in ('linearization','controllability','equilibrium','input_sensitivity','design_sensitivity'):
            if c.signal.name == 'tip_position' and c.kind in ('norm_bound','path_bound'):
                status, reason = 'diagnostic', 'Local position authority/static construction only; no sampled constraint verification.'
        elif trajectory and c.kind=='path_bound' and getattr(query,'capability_method',None)!='sampled-affine-conic-minimax-v1':
            reason='Free progress requires the conic path formulation; fixed-reference SLSQP is not substituted.'
        elif trajectory and c.kind in ('norm_bound','component_interval','path_bound') and sampled is not None:
            indices = [i for i in c.indices if i in sampled['sample_steps']]
            if indices:
                status = 'applicable' if indices == c.indices else 'partial'
                reason = 'Shared held-input trajectory; past samples require separate evidence.'
        elif c.kind == 'norm_bound':
            if c.signal.name == 'tip_position' and last in c.indices:
                status, indices, reason = ('applicable' if c.indices==[last] else 'partial'), [last], 'Terminal position only under bounded local affine dynamics.'
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
        path_scope=('Free progress within a chosen numerical horizon; sampled corner visits, not unrestricted-time infeasibility or independent geometric acceptance'
            if any(c.kind=='path_bound' for c in requirements.constraints) else None),
        constraint_coverage=coverage, full_task_supported=bool(trajectory and not reasons and sampled['start_time_s'] == 0.
            and all(c['status'] == 'applicable' for c in coverage) and not any(c.kind=='path_bound' for c in requirements.constraints)), execution_support='not_assessed',
        model_assessment=assessment, horizon=dict(task_duration_s=requirements.duration_s,
            remaining_task_s=remaining, analysis_horizon_s=None if query.operation == 'equilibrium' else horizon,
            period_s=p.period_s, origin=point.get('actual_time_s'),
            interpretation='static construction' if query.operation == 'equilibrium' else
                'Actual saved-state remaining horizon, or nominal horizon from the declared configuration operating point.',
            **({'trajectory_grid':sampled} if trajectory else {})))
