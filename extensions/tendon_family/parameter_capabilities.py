"""Registered candidate.family@1.1 declarations for dimension-preserving research.

This adapter owns semantic IDs and coupling, while schemas own physical types.
Study grants are supplied separately; a declaration is never an execution grant.
"""
from .contracts import GVSTrajectoryParameters
from .design_decisions import ASSUMPTIONS, MATERIAL_FACTORS, expand_segment

CAPABILITY_VERSION = '1.0.0'


def declarations():
    rows = []
    for component in ('near', 'far'):
        rows.extend([
            dict(id=f'components/{component}/length_m', kind='physical_design', type='number', unit='m',
                meaning=f'{component} flexible segment length; attachment station fractions remain fixed.',
                schema='family.design:Segment.length_m', legal_domain=dict(exclusive_minimum=0),
                operation='set', components=[component], effective_locations=[f'robot/structure/data/components/{component}/length_m'],
                coupled_constraints=['Fixed serial topology, cell counts, section stations and tendon routing; compiler checks geometry.'],
                derived_quantities=['cell length', 'mass', 'inertia', 'hinge stiffness/damping', 'tendon site positions']),
            dict(id=f'design/{component}_section_scale', kind='physical_design', type='number', unit='1',
                meaning=f'Uniform positive scale of all {component} section dimensions against original semantic_source.',
                schema='family.space:SemanticDecision.section_scale', legal_domain=dict(exclusive_minimum=0),
                operation='section_scale', components=[component],
                effective_locations=[f'robot/structure/data/components/{component}/sections/*/section/parameters/*'],
                coupled_constraints=['Only ellipse/rectangle; preserve aspect ratios, station layout and section orientation.',
                    'One scale owner per segment; common and per-segment scale selectors cannot overlap.',
                    'Tendon offsets and straight frictionless routing remain fixed; this scale changes the bending section and backend mesh.'],
                derived_quantities=['area', 'bending second moments', 'mass', 'inertia', 'hinge stiffness/damping', 'backend mesh']),
            dict(id=f'design/{component}_material_scenario', kind='physical_design', type='choice', unit='1',
                meaning=f'{component} numerical Young modulus scenario against original semantic_source.',
                schema='family.space:SemanticDecision.material_scenario', legal_domain=dict(options=list(MATERIAL_FACTORS)),
                operation='material_scenario', components=[component],
                effective_locations=[f'robot/structure/data/components/{component}/physics/young_pa'],
                coupled_constraints=[ASSUMPTIONS, 'Density and bending viscosity stay fixed; no independently mixed material properties.',
                    'One scenario owner per segment; common and per-segment material selectors cannot overlap.'],
                derived_quantities=['Young modulus', 'hinge stiffness'])])
    for name in ('terminal_tip_speed_weight', 'holding_tip_speed_weight'):
        rows.append(dict(id='control/recipe/'+name, kind='control_objective', type='number', unit='1',
            meaning=GVSTrajectoryParameters.model_fields[name].description,
            schema='family.gvs_trajectory_parameters:'+name,
            legal_domain=dict(options=[0], intervals=[[.0001, 1.]]), operation='set', components=['controller'],
            effective_locations=['policy/controller/parameters/data/recipe/'+name],
            coupled_constraints=['Squared world tip speed normalized by fixed tip_speed_scale_m_s.',
                'Holding cost follows fixed holding window; this objective does not change task acceptance.'],
            derived_quantities=['controller objective terms']))
    return dict(version=CAPABILITY_VERSION, parameters=rows, integration_backlog=[
        dict(id='segment_count', kind='physical_design', reason='No research mutation adapter or comparable initializer mapping for changed segment topology; historical controller compatibility requires fixed component topology.'),
        dict(id='tendon_count', kind='physical_design', reason='No research mutation adapter for changed input dimension, ordered tension guesses, actuator transmission and NMPC input-order reconstruction.'),
        dict(id='tendon_routing', kind='physical_design', reason='Underlying compiler supports declared routes, but stable reach technical scope freezes routing; changed-route projection, feasible warm guess and controller/backend validation are absent.'),
        dict(id='section_shape', kind='physical_design', reason='Backend compiler supports several shapes; stable reach compatibility only admits fixed ellipse/rectangle shape, station layout and uniform per-segment scaling. Changed-shape projection/controller validation is absent.'),
        dict(id='independent_material_properties', kind='physical_design', reason='Density and viscosity are represented but no manufacturing-consistent material declaration or study-validated coupled material mapping exists; Young-only scenarios are explicitly numerical.'),
        dict(id='natural_curvature', kind='physical_design', reason='Compiler represents rest curvature, but stable reach scope freezes it; no research mutation adapter, preload-consistent initial challenge mapping or changed-rest-shape controller validation is connected.'),
        dict(id='payload_mass_and_inertia', kind='physical_design', reason='Rigid payload mass, COM and full inertia tensor are represented, but stable reach scope freezes rigid components; no coupled physically consistent payload mutation, projection/controller validation or study initialization mapping is connected.'),
        dict(id='discretization/cells', kind='numerical_model', reason='Compiler can rebuild meshes, but first-study state mapping/controller compatibility and candidate cache policy are frozen to 12+12 cells; changed-dimension study adapter is absent.'),
        dict(id='omitted_physics', kind='numerical_model', reason='Serial bending model omits shear, stretch, torsion, tendon friction, rope elasticity and motor dynamics; these are not editable supported physical effects.'),
        dict(id='solver_recipe', kind='numerical_model', reason='First study freezes stable v7 horizon, stopping rules and solver budgets; arbitrary numerical recipe mutation is not connected to this candidate builder.'),
    ])


def authorize_study(inp, space, changes):
    from .candidate import authorize
    declared = {row['id'] for row in declarations()['parameters']}
    if set(changes)-declared:
        raise ValueError('RESEARCH_PARAMETER_CAPABILITY_UNAVAILABLE: '+','.join(sorted(set(changes)-declared)))
    authorize(inp, space, changes)


def apply_study(inp, space, changes):
    from .candidate import apply
    authorize_study(inp, space, changes)
    return apply(inp, space, changes, semantic_expander=expand_segment)


def routing_declarations():
    value = declarations()
    value['version'] = '1.1.0'
    for row in value['parameters']:
        row['task_families'] = ['task.reach', 'task.tracking'] if row['id'].endswith('/length_m') else ['task.reach']
    for component in ('near', 'far'):
        value['parameters'].append(dict(id=f'design/{component}_routing_radius_scale',
            kind='physical_design', type='number', unit='1', operation='routing_radius_scale',
            components=[component], schema='family.space:SemanticDecision.routing_radius_scale',
            meaning='Uniform local transverse routing offset scale against immutable semantic_source, owned by physical segment '+component,
            legal_domain=dict(exclusive_minimum=0), task_families=['task.reach'],
            controller_versions=['9.0.0'], effective_locations=['segment-owned tendon attachment offsets and rigid guide holes'],
            coupled_constraints=['Base belongs to root flexible segment; rigid locations belong to closest upstream flexible ancestor.',
                'Boundary guide holes transform once by upstream owner, including distal tendons. Anchors use their physical attachment owner.',
                'Longitudinal stations, angle/layout, hole diameter, sections and actuator drum radius stay separate.',
                'Bounds derived from source guide envelopes/hole separation; full compiler span checks required.'],
            derived_quantities=['tendon lengths and derivatives', 'force mapping', 'reduced routing graph', 'controller preparation']))
    value['integration_backlog'] = [r for r in value['integration_backlog'] if r['id'] != 'tendon_routing']
    for row in value['integration_backlog']:
        row['target_version'] = '2' if row['id'] in ('segment_count', 'tendon_count') else 'later'
    value['integration_backlog'].append(dict(id='tendon_layout', kind='physical_design', target_version='2',
        reason='Finite count/layout choices require topology, input ordering and initialization mappings; v1 permits only source-relative radial offsets.'))
    return value


def authorize_routing(inp, space, changes):
    from .candidate import authorize
    declared = {r['id'] for r in routing_declarations()['parameters']}
    if set(changes)-declared: raise ValueError('RESEARCH_PARAMETER_CAPABILITY_UNAVAILABLE')
    rows={r['id']:r for r in routing_declarations()['parameters']}
    if any(inp.task.family not in rows[p]['task_families'] for p in changes):
        raise ValueError('PARAMETER_OUTSIDE_TASK_ENVELOPE')
    if any('routing_radius_scale' in p for p in changes) and (
            inp.task.family != 'task.reach' or inp.policy.controller.version != '9.0.0'):
        raise ValueError('ROUTING_REQUIRES_REACH_V9')
    authorize(inp, space, changes)


def apply_routing(inp, space, changes):
    from .candidate import apply
    from .routing_radius import expand_routing
    authorize_routing(inp, space, changes)
    return apply(inp, space, changes, semantic_expander=expand_routing)
