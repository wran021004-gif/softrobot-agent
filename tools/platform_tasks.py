"""Definition -> capability -> executable development snapshot, without engines."""
from schemas.platform import SessionInput, TaskDefinition, Payload, VERSION
from tools.state_io import digest
from tools.platform_registry import registry, dependency_identity


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
    task = check_definition(inp.task, reg)
    reg.parse(inp.robot.structure)
    if task.status != 'development_valid':
        raise ValueError('DEVELOPMENT_HOST_REQUIRES_DEVELOPMENT_VALID: draft 不可运行；正式批准需独立真实审批策略')
    if task.sampling.split != 'development':
        raise ValueError('DEVELOPMENT_POLICY_CANNOT_PRODUCE_FORMAL_EVALUATION_SCORE')
    if inp.seed not in task.sampling.seeds:
        raise ValueError('SEED_NOT_IN_TASK_INSTANCES')
    if inp.robot.family not in task.robot_families or set(task.actuator_channels) - set(inp.robot.channels):
        raise ValueError('ROBOT_OR_ACTUATOR_INCOMPATIBLE')
    backend, params = reg.bind(inp.policy.backend, 'backend')
    controller, control_params = reg.bind(inp.policy.controller, 'controller')
    if inp.policy.search:
        search, _ = reg.bind(inp.policy.search, 'search')
        if len(task.objectives) != 1 and not search.capabilities.get('multiobjective'):
            raise ValueError('MULTIOBJECTIVE_SEARCH_ADAPTER_REQUIRED')
    caps = backend.capabilities
    checks = [('families', [task.family]), ('robots', [inp.robot.family]),
              ('channels', task.actuator_channels), ('environments', [task.environment.contract]),
              ('signals', [s.name for s in task.observations]), ('controllers', [controller.extension_id])]
    for key, required in checks:
        missing = set(required) - set(caps.get(key, []))
        if missing:
            raise ValueError(f'BACKEND_INCOMPATIBLE {key}: {sorted(missing)}')
    if any(s.phase not in caps.get('signal_phases', []) for s in task.observations):
        raise ValueError('BACKEND_SIGNAL_PHASE_UNSUPPORTED')
    if set(controller.capabilities.get('observations', [])) - set(caps['signals']):
        raise ValueError('CONTROL_OBSERVATION_UNSUPPORTED')
    if controller.capabilities['channel'] not in task.actuator_channels:
        raise ValueError('CONTROL_CHANNEL_UNSUPPORTED')
    for key, limits in inp.policy.editable.items():
        if key not in controller.capabilities.get('editable', []):
            raise ValueError('PARAMETER_NOT_EDITABLE: ' + key)
        if limits[0] >= limits[1]:
            raise ValueError('INVALID_PARAMETER_BOUNDS: ' + key)
    backend.resolve().check(inp, params, control_params)
    init, init_params = reg.bind(task.initializer, 'initializer')
    initial = init.resolve()(init_params, inp.seed)
    reg.parse(initial)
    definitions = [backend, controller, init, reg.get(task.family), reg.get(task.evaluator.extension_id, task.evaluator.version)]
    if inp.policy.search:
        definitions.append(reg.get(inp.policy.search.extension_id, inp.policy.search.version))
    for tool_id in inp.policy.allowed_tools:
        matches = [d for (name, _), d in reg.extensions.items() if name == tool_id and d.kind == 'tool']
        if len(matches) != 1:
            raise ValueError('TOOL_VERSION_SELECTION_REQUIRED_OR_MISSING: ' + tool_id)
        definitions.append(matches[0])
    for d in definitions:
        availability = reg.inspect(d, [d.extension_id])
        if not availability['executable']:
            raise ValueError('CAPABILITY_UNAVAILABLE: ' + d.extension_id + ': ' + ';'.join(availability['reasons']))
    dependencies = {d.extension_id + '@' + d.version: dependency_identity(d) for d in definitions}
    return dict(input=inp.model_dump(mode='json'), input_identity=digest(inp.model_dump(mode='json')),
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
