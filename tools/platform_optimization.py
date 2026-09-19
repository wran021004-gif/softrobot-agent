"""Deterministic assembly dispatch; no solver, search, backend or Agent execution."""
from schemas.platform import Binding, RobotDescription, TaskDefinition
from schemas.platform_math import (MathematicalModel, OptimizationProblem,
    OptimizationSpecification, ParameterDefinitions, SystemContext)
from schemas.platform_protocols import OptimizationAssembler
from tools.platform_registry import Registry


def assemble_optimization(registry: Registry, binding: Binding, *, task: TaskDefinition,
                          robot: RobotDescription, space: ParameterDefinitions,
                          mathematical_model: MathematicalModel,
                          specification: OptimizationSpecification,
                          context: SystemContext) -> OptimizationProblem:
    """Check choices against trusted Space paths and registered template metadata.

    The caller projects existing Space parameter maps into space, preserving
    their paths/specifications and any applicable authorization conditions.
    Only specification is Agent-owned. The registered assembler reads physical
    meaning from task/robot/model/context and constructs the actual expressions.
    """
    definition, parameters = registry.bind(binding, 'optimization_assembler')
    unknown = set(specification.variables) - space.keys()
    if unknown:
        raise ValueError('OPTIMIZATION_VARIABLE_NOT_AUTHORIZED: ' + ', '.join(sorted(unknown)))
    for name in ('objectives', 'constraints'):
        supported = definition.capabilities.get('supported_' + name, ())
        for selection in getattr(specification, name):
            if selection.template_id not in supported:
                raise ValueError('UNSUPPORTED_' + name.upper() + '_TEMPLATE: ' + selection.template_id)
    assembler: OptimizationAssembler = definition.resolve()(parameters)
    return assembler.assemble(task, robot, space, mathematical_model, specification, context)
