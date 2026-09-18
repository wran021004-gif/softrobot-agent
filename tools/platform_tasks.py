"""Definition -> capability -> executable development snapshot, without engines."""
from schemas.platform import SessionInput, TaskDefinition, Payload, VERSION
from tools.state_io import digest
from tools.platform_registry import registry, dependency_identity, tool_bindings, dependency_closure


def check_definition(value, reg=None):
    reg = reg or registry()
    task = TaskDefinition.model_validate(value)
    reg.parse(task.goal)
    reg.parse(task.environment)
    evaluator, parameters = reg.bind(task.evaluator, 'evaluator')
    reg.bind(task.initializer, 'initializer')
    family = reg.get(task.family, VERSION, 'task')
    family.resolve()(task, reg)
    return task


def compile_input(value, reg=None):
    reg = reg or registry()
    inp = SessionInput.model_validate(value)
    bound, normalized = tool_bindings(inp.policy, reg)
    inp = inp.model_copy(update={'policy': inp.policy.model_copy(update={'tool_bindings': bound, 'allowed_tools': list(bound)})})
    task = check_definition(inp.task, reg)
    reg.parse(inp.robot.structure)
    if inp.policy.discretization is not None:
        reg.parse(inp.policy.discretization)
    if task.status != 'development_valid':
        raise ValueError('DEVELOPMENT_HOST_REQUIRES_DEVELOPMENT_VALID: drafts cannot execute; formal approval requires an independent approval policy')
    if task.sampling.split != 'development':
        raise ValueError('DEVELOPMENT_POLICY_CANNOT_PRODUCE_FORMAL_EVALUATION_SCORE')
    if inp.seed not in task.sampling.seeds:
        raise ValueError('SEED_NOT_IN_TASK_INSTANCES')
    if inp.robot.family not in task.robot_families or set(task.actuator_channels) - set(inp.robot.channels):
        raise ValueError('ROBOT_OR_ACTUATOR_INCOMPATIBLE')
    backend, params = reg.bind(inp.policy.backend, 'backend')
    controller, control_params = reg.bind(inp.policy.controller, 'controller')
    dynamics_model = None
    if inp.policy.dynamics_model is not None:
        dynamics_model, _ = reg.bind(inp.policy.dynamics_model,'dynamics_model')
        if dynamics_model.extension_id not in backend.capabilities.get('models',{}):
            raise ValueError('DYNAMICS_MODEL_BACKEND_UNSUPPORTED: '+dynamics_model.extension_id+' -> '+backend.extension_id)
    if inp.policy.search:
        search, _ = reg.bind(inp.policy.search, 'search')
        if len(task.objectives) != 1 and not search.capabilities.get('feedback_adapter'):
            raise ValueError('MULTIOBJECTIVE_SEARCH_ADAPTER_REQUIRED')
    caps = backend.capabilities
    if inp.robot.structure.contract not in caps.get('robot_contracts', [inp.robot.structure.contract]):
        raise ValueError('BACKEND_ROBOT_REPRESENTATION_UNSUPPORTED')
    from schemas.platform import SignalSpec
    resolver = backend.hook('signal_specs_resolver')
    available = [SignalSpec.model_validate(s) for s in
                 (resolver(inp, reg) if resolver else caps.get('signal_specs', []))]
    if controller.capabilities.get('observation_specs'):
        if any(SignalSpec.model_validate(s) not in available for s in controller.capabilities['observation_specs']):
            raise ValueError('CONTROL_OBSERVATION_SEMANTICS_UNSUPPORTED')
    checks = [('robots', [inp.robot.family]),
              ('channels', task.actuator_channels), ('environments', [task.environment.contract]),
              ('signals', [s.name for s in task.observations])]
    for key, required in checks:
        missing = set(required) - set(caps.get(key, []))
        if missing:
            raise ValueError(f'BACKEND_INCOMPATIBLE {key}: {sorted(missing)}')
    if caps.get('conversion'):
        for key, required in [('families', task.family), ('controllers', controller.extension_id)]:
            if required not in caps.get(key, []):
                raise ValueError('BACKEND_CONVERSION_ADAPTER_REQUIRED: ' + required)
    if resolver or caps.get('signal_specs'):
        if any(s not in available for s in task.observations):
            raise ValueError('BACKEND_SIGNAL_SEMANTICS_MISMATCH')
    if any(s.phase not in caps.get('signal_phases', []) for s in task.observations):
        raise ValueError('BACKEND_SIGNAL_PHASE_UNSUPPORTED')
    if set(controller.capabilities.get('observations', [])) - set(caps['signals']):
        raise ValueError('CONTROL_OBSERVATION_UNSUPPORTED')
    if controller.capabilities['channel'] not in task.actuator_channels:
        raise ValueError('CONTROL_CHANNEL_UNSUPPORTED')
    if inp.policy.candidate_builder is None:
        from schemas.platform import Binding, Payload
        default_builder = Binding(extension_id='candidate.controller', parameters=Payload(contract='platform.empty', data={}))
        inp = inp.model_copy(update={'policy': inp.policy.model_copy(update={'candidate_builder': default_builder})})
    builder, builder_params = reg.bind(inp.policy.candidate_builder, 'candidate_builder')
    editable = builder.capabilities.get('editable', controller.capabilities.get('editable', []))
    declared = set(getattr(builder_params, 'parameters', {})) | set(getattr(builder_params, 'discretization_parameters', {})) | set(getattr(builder_params, 'control_parameters', {}))
    for key, limits in inp.policy.editable.items():
        if key not in editable and not (builder.hook('authorize_changes') and key in declared):
            raise ValueError('PARAMETER_NOT_EDITABLE: ' + key)
        if limits[0] >= limits[1]:
            raise ValueError('INVALID_PARAMETER_BOUNDS: ' + key)
    backend.resolve().check(inp, params, control_params)
    init, init_params = reg.bind(task.initializer, 'initializer')
    initial = init.resolve()(init_params, inp.seed)
    reg.parse(initial)
    definitions = [backend, controller, init, reg.get(task.family), reg.get(task.evaluator.extension_id, task.evaluator.version)]
    if dynamics_model is not None:
        definitions.append(dynamics_model)
    if inp.policy.search:
        definitions.append(reg.get(inp.policy.search.extension_id, inp.policy.search.version))
    definitions.append(builder)
    model = reg.get(inp.policy.model.adapter, inp.policy.model.adapter_version, 'model_adapter')
    model.input_schema.model_validate(inp.policy.model.parameters)
    definitions.extend([model, reg.get(inp.policy.model.strategy, inp.policy.model.strategy_version, 'strategy')])
    definitions.extend(reg.get(n, v, 'tool') for n, v in bound.items())
    for d in definitions:
        availability = reg.inspect(d, [d.extension_id])
        if not availability['executable']:
            raise ValueError('CAPABILITY_UNAVAILABLE: ' + d.extension_id + ': ' + ';'.join(availability['reasons']))
    dependencies = dependency_closure(definitions, reg)
    return dict(normalization=dict(legacy_tools=normalized, location='policy.tool_bindings'), input=inp.model_dump(mode='json'), input_identity=digest(inp.model_dump(mode='json')),
                initial=initial.model_dump(mode='json'), dependencies=dependencies,
                instance_identity=digest(dict(task=task.model_dump(mode='json'), seed=inp.seed, initial=initial.model_dump(mode='json'))),
                approval=dict(definition_valid=True, capabilities_ready=True, formally_approved=False,
                              purpose='独立开发接口验证，不是正式科研批准'))


def report(value, reg=None):
    reg = reg or registry()
    definition = value.get('task', value)
    result = dict(definition_valid=False, capabilities_ready=False, executable=False, formally_approved=False, errors=[])
    try:
        TaskDefinition.model_validate(definition)
        result['definition_valid'] = True
        check_definition(definition, reg)
        if 'task' in value:
            result['snapshot'] = compile_input(value, reg)
            result['executable'] = True
        result['capabilities_ready'] = True
    except (ValueError, TypeError) as exc:
        result['errors'].append(str(exc))
        result['implementation_location'] = 'extensions/<package>/contracts.py + manifest.py + implementation.py'
    return result
