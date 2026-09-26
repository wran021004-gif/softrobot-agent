"""Deterministic tendon-family model-use assessment, independent of Route and backends."""

from schemas.platform import Binding, RobotDescription, TaskDefinition
from schemas.platform_math import ModelUse, ModelUseAssessment, ModelUseVerdict, ModelAgreementEvidence
from tools.state_io import digest

from .contracts import Design, Discretization, Reserved, ResolvedGVSBasis, Segment
from .gvs_basis import resolve_basis


USES = ('reachability', 'shape_prediction', 'static_equilibrium',
        'reduced_dynamics', 'control_trend', 'linearization',
        'local_model_control', 'contact_prediction', 'high_fidelity_validation')
FORCE_SENSITIVE = frozenset(('shape_prediction', 'static_equilibrium', 'reduced_dynamics',
                             'control_trend', 'linearization', 'local_model_control'))


def _topology_issue(design, model_id):
    components = {component.id: component for component in design.components}
    if len(components) != len(design.components):
        raise ValueError('DUPLICATE_COMPONENT_ID')
    reserved = [component.kind for component in design.components if isinstance(component, Reserved)]
    if reserved:
        return 'Reserved topology is not implemented: ' + ', '.join(sorted(reserved))
    ancestry = set()
    current = design.tip.part
    while current != 'fixed_base':
        if current in ancestry:
            raise ValueError('CYCLIC_COMPONENT_GRAPH')
        ancestry.add(current)
        component = components.get(current)
        if component is None:
            raise ValueError('UNKNOWN_TIP_ANCESTOR: ' + current)
        current = component.connection.part
    outside = set(components) - ancestry
    if model_id in ('model.pcc', 'model.gvs') and outside:
        return 'Model requires one serial tip chain; components outside it: ' + ', '.join(sorted(outside))
    flexible_outside = sorted(name for name in outside if isinstance(components[name], Segment))
    if flexible_outside:
        return 'Serial bending cells do not support off-tip flexible branches: ' + ', '.join(flexible_outside)
    return None


def _base_verdict(model_id, use):
    if model_id == 'model.pcc':
        if use == 'reachability':
            return 'ALLOW', ['Constant-curvature kinematics supports geometric reachability screening.']
        if use == 'shape_prediction':
            return 'WARN', ['Shape is coarse: curvature is constant within each flexible segment.']
        return 'REJECT', ['PCC does not implement the mechanics required for this use.']
    if model_id == 'model.gvs':
        if use in ('reachability', 'shape_prediction', 'reduced_dynamics'):
            return 'ALLOW', ['Resolved GVS bending coordinates support this reduced-model use.']
        if use == 'static_equilibrium':
            return 'WARN', ['GVS implements static equilibrium, but agreement for this design and representation is unvalidated; validation evidence is unavailable.']
        if use == 'control_trend':
            return 'WARN', ['Reduced dynamics can show control trends, but trend agreement is unvalidated; validation evidence is unavailable.']
        if use == 'linearization':
            return 'WARN', ['GVS exports a DynamicSystem for the separate linearizer, but local physical agreement is unvalidated; validation evidence is unavailable.']
        if use == 'local_model_control':
            return 'WARN', ['Local control can use the reduced model and linearizer, but operating-point and closed-loop agreement are unvalidated; validation evidence is unavailable.']
        return 'REJECT', ['The reduced GVS model does not implement this use.']
    if use == 'reachability':
        return 'ALLOW', ['Cell kinematics supports geometric reachability.']
    if use == 'shape_prediction':
        return 'WARN', ['Detailed cell shape can be computed, but physical agreement has not been validated.']
    if use == 'reduced_dynamics':
        return 'WARN', ['Dynamics are supported at cell resolution; this is not a reduced representation.']
    if use == 'control_trend':
        return 'WARN', ['Cell dynamics can produce a control trend, but physical agreement has not been validated.']
    if use == 'contact_prediction':
        return 'WARN', ['Contact behavior depends on the selected backend contact implementation; model metadata alone does not validate it.']
    if use == 'high_fidelity_validation':
        return 'WARN', ['Cell dynamics provide a simulation reference; backend execution and physical validation evidence are still required.']
    return 'REJECT', ['Serial bending cells do not declare the mathematical operation required for this use.']


def assess_model_uses(robot: RobotDescription, task: TaskDefinition, model: Binding,
                      uses: list[ModelUse], *, resolved_basis: ResolvedGVSBasis | None = None,
                      discretization: Discretization | None = None,
                      required_physics: dict[ModelUse, list[str]] | None = None,
                      evidence=(), evidence_loader=None, evidence_context: dict | None = None,
                      registry=None) -> ModelUseAssessment:
    """Assess requested uses from frozen contracts; no simulation or model fitting.

    ``required_physics`` expresses explicit per-use physical requirements not
    encoded by Task. Task external forces are read directly from its assembly.
    Optional evidence references are resolved by the existing artifact store.
    Matching requires an explicit, exact local query scope; measurements do not
    change the capability verdict or imply an unmeasured acceptance threshold.
    """
    from extensions.experiment_dynamics.contracts import Assembly
    from tools.platform_registry import registry as default_registry

    robot = RobotDescription.model_validate(robot)
    task = TaskDefinition.model_validate(task)
    model = Binding.model_validate(model)
    if robot.structure.contract != 'family.design' or robot.family not in task.robot_families:
        raise ValueError('TENDON_FAMILY_ROBOT_TASK_REQUIRED')
    if task.environment.contract != 'experiment.assembly':
        raise ValueError('EXPERIMENT_ASSEMBLY_REQUIRED')
    if not uses or any(use not in USES for use in uses):
        raise ValueError('UNKNOWN_OR_EMPTY_MODEL_USE')
    required_physics = required_physics or {}
    if set(required_physics) - set(uses):
        raise ValueError('PHYSICS_REQUIREMENT_USE_NOT_REQUESTED')
    design = Design.model_validate(robot.structure.data)
    assembly = Assembly.model_validate(task.environment.data)
    reg = registry if registry is not None else default_registry()
    definition, parameters = reg.bind(model, 'dynamics_model')
    model_id = definition.extension_id
    if model_id not in ('model.pcc', 'model.gvs', 'model.serial_bending_cells'):
        raise ValueError('TENDON_FAMILY_MODEL_REQUIRED: ' + model_id)
    declaration = reg.mathematical_model(model)
    issue = _topology_issue(design, model_id)

    representation_id = representation_kind = representation_strategy = None
    coordinate_dimension = state_dimension = None
    missing_locations = []
    if issue is None and model_id == 'model.gvs':
        expected = resolve_basis(design, parameters.basis)
        if resolved_basis is not None:
            resolved_basis = ResolvedGVSBasis.model_validate(resolved_basis)
        if resolved_basis is not None and resolved_basis != expected:
            raise ValueError('GVS_RESOLVED_BASIS_MISMATCH')
        basis = expected if resolved_basis is None else resolved_basis
        representation_id = digest(basis.model_dump(mode='json'))
        representation_kind = basis.representation_id
        representation_strategy = basis.specification.strategy
        coordinate_dimension = basis.dimension
        state_dimension = 2 * basis.dimension
        missing_locations = [(segment.segment, location.s)
                             for segment in basis.segments for location in segment.locations
                             if location.s not in segment.knots]
    elif model_id == 'model.serial_bending_cells':
        if discretization is None:
            raise ValueError('SERIAL_BENDING_DISCRETIZATION_REQUIRED')
        discretization = Discretization.model_validate(discretization)
        segment_names = {component.id for component in design.components if isinstance(component, Segment)}
        if set(discretization.cells) != segment_names:
            raise ValueError('DISCRETIZATION_SEGMENTS_MISMATCH')
        representation_id = digest(discretization.model_dump(mode='json'))
        representation_kind = discretization.version
        coordinate_dimension = 2 * sum(discretization.cells.values())
        state_dimension = 2 * coordinate_dimension

    verdicts = {}
    unsupported = set()
    for use in dict.fromkeys(uses):
        status, reasons = _base_verdict(model_id, use)
        reasons = list(reasons)
        requested = set(required_physics.get(use, ()))
        if use == 'static_equilibrium':
            requested.add('static_equilibrium')
        elif use == 'reduced_dynamics':
            requested.add('dynamics')
        if use == 'contact_prediction':
            requested.add('contact_response')
        omitted = requested.intersection(declaration.unsupported_physics)
        unsupported.update(omitted)
        force_omitted = (model_id in ('model.pcc', 'model.gvs') and
                         bool(assembly.external_forces) and use in FORCE_SENSITIVE)
        if force_omitted:
            unsupported.add('external_applied_forces')
        if issue is not None:
            status, reasons = 'REJECT', [issue]
        else:
            if model_id == 'model.gvs' and missing_locations and use in (
                    'shape_prediction', 'static_equilibrium', 'reduced_dynamics',
                    'control_trend', 'linearization', 'local_model_control'):
                if status == 'ALLOW':
                    status = 'WARN'
                reasons.append('Resolved basis omits interior structural locations: ' +
                               ', '.join(f'{name}@{s:g}' for name, s in missing_locations))
            if force_omitted:
                status = 'REJECT'
                reasons.append('Task has external applied forces omitted by this model.')
            if omitted:
                status = 'REJECT'
                reasons.append('Requested physics omitted by model: ' + ', '.join(sorted(omitted)))
        matched = []
        # An explicit query scope is required: measurements at one state do not
        # validate a whole task, even if its design and model names match.
        if evidence_context is not None and evidence_loader is not None:
            for ref in evidence:
                item = ModelAgreementEvidence.model_validate(evidence_loader(ref))
                if (item.design_identity == digest(design.model_dump(mode='json'))
                    and Assembly.model_validate(item.environment) == assembly
                    and any(b.extension_id==model_id and b.version==definition.version
                        and reg.bind(b,'dynamics_model')[1].model_dump(mode='json')==parameters.model_dump(mode='json')
                        for b in item.model_bindings)
                    and item.representation_ids.get(model_id) == representation_id
                    and use in item.measured_uses
                    and evidence_context == dict(numerical_settings=item.numerical_settings,
                        mapping_convention=item.mapping_convention,
                        reference_state_input=item.reference_state_input, environment=item.environment)):
                    matched.append(ref)
        if matched:
            reasons = [r.replace('validation evidence is unavailable', 'matched local measurements are available')
                       for r in reasons]
            reasons.append('Measured errors apply only to the exact supplied scope; no global agreement or task acceptance is implied.')
        verdicts[use] = ModelUseVerdict(status=status, reasons=reasons,
            validation='measured_local' if matched else 'unavailable', evidence=matched)
    return ModelUseAssessment(model_id=model_id, model_version=definition.version,
        design_id=design.id,
        design_identity=digest(design.model_dump(mode='json')),
        representation_id=representation_id, representation_kind=representation_kind,
        representation_strategy=representation_strategy,
        generalized_coordinate_dimension=coordinate_dimension, state_dimension=state_dimension,
        uses=verdicts, relevant_assumptions=declaration.assumptions,
        unsupported_requested_physics=sorted(unsupported))
