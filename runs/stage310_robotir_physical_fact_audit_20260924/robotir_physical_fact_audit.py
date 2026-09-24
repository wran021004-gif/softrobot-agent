"""Audit physical fact ownership in the frozen RobotIR and its two generators."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from extensions.tendon_family.contracts import (  # noqa: E402
    Actuator, Design, Discretization, GVSModelParameters, PhysicalInput,
    Rigid, Section, Segment, Tendon,
)
from schemas.platform import RobotDescription  # noqa: E402
from tools.state_io import atomic_json, digest  # noqa: E402

HERE = Path(__file__).resolve().parent
SOURCE = ROOT / 'runs/stage35_case_b_retry_softagent_20260924/inputs/route.json'
STAGE37 = ROOT / 'runs/stage37_gvs_backend_consistency_20260924/gvs_backend_consistency.json'
STAGE38 = ROOT / 'runs/stage38_physics_alignment_20260924/physics_alignment.json'
STAGE39 = ROOT / 'runs/stage39_physics_consistency_20260924/physics_consistency.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def fields(contract):
    return list(contract.model_fields)


def main():
    source, s37, s38, s39 = (read(path) for path in (SOURCE, STAGE37, STAGE38, STAGE39))
    robot = RobotDescription.model_validate(source['robot'])
    design = Design.model_validate(robot.structure.data)
    mesh = Discretization.model_validate(source['policy']['discretization']['data'])
    assert robot.structure.contract == 'family.design'
    assert source['policy']['discretization']['contract'] == 'family.discretization'
    assert digest(robot.model_dump(mode='json')) == s39['reference_state']['robot_identity'] == s37['identities']['robot']
    assert digest(mesh.model_dump(mode='json')) == s39['reference_state']['backend_discretization_identity']
    assert s37['identities']['dynamic_system'] == s39['reference_state']['gvs_dynamic_system_identity']
    assert s38['reference_state']['basis_identity'] == s39['reference_state']['basis_identity']
    assert Segment.model_fields['cells'].exclude is True
    assert design.metadata == robot.structure.data['metadata']

    segment_examples = {part.id: dict(length_m=part.length_m, interpolation=part.interpolation,
        section_stations=[station.s for station in part.sections],
        material_mode=part.physics.mode, density_kg_m3=part.physics.density_kg_m3,
        young_pa=part.physics.young_pa, natural_curvature_rad_m=part.natural_curvature_rad_m)
        for part in design.components if isinstance(part, Segment)}
    rigid_examples = {part.id: dict(mass_kg=part.mass_kg, com_local_m=part.com_local_m,
        inertia_com_local_kg_m2=part.inertia_com_local_kg_m2)
        for part in design.components if isinstance(part, Rigid)}
    assert set(segment_examples) == set(mesh.cells)
    assert set(rigid_examples) == set(s39['robot_ir_rigid_components'])

    traces = [
        dict(quantity='flexible_mass', owner='family.design', source='Segment.physics density_kg_m3 or line_density_kg_m; Segment.sections, length_m',
             explicit_fact='material density or line density, section geometry and length',
             gvs='Gauss section quadrature along the continuous segment',
             backend='cell-midpoint section area times density and cell length',
             independent_choice='quadrature versus cell midpoint sampling',
             observation='total mass gap 2.33e-6 kg, 0.0031%'),
        dict(quantity='flexible_com', owner='derived from family.design', source='Section centroid and density; no single flexible COM field',
             explicit_fact='cross-section shape and its along-segment stations',
             gvs='quadrature material points placed by continuous strain kinematics',
             backend='body COM at cell half-length plus rotated section centroid, placed by hinges',
             independent_choice='continuous pose integration versus rigid-cell pose and lumping',
             observation='far COM gap 9.321 mm; payload world COM gap 16.673 mm at q0'),
        dict(quantity='inertia', owner='mixed', source='Rigid.inertia_com_local_kg_m2 explicit; flexible inertia derived from density and section area moments',
             explicit_fact='rigid tensor, flexible density and section geometry',
             gvs='quadrature cross-section inertia plus distributed translation',
             backend='cell body inertia including m*ds^2/12, rotated into XML inertial frame',
             independent_choice='distributed versus cell-local inertial approximation',
             observation='rigid local tensors preserved; far deformed component inertia gap 13.34%'),
        dict(quantity='gravity', owner='task.environment, not RobotIR', source='Assembly.environment.gravity_m_s2 and mount quaternion',
             explicit_fact='world gravity and mount pose in the scene',
             gvs='sum m J_com.T g over continuous mass quadrature',
             backend='MuJoCo body COM Jacobians, equivalently -qfrc_bias at zero speed',
             independent_choice='COM pose and Jacobian from each representation',
             observation='generalized gravity gap 1.771e-3 N*m^2 at q0'),
        dict(quantity='bending_elasticity', owner='family.design', source='PhysicalInput material E or equivalent EI; sections; natural_curvature_rad_m',
             explicit_fact='restricted linear bending constitutive inputs',
             gvs='integral of basis.T E I(s) (basis*q - natural curvature)',
             backend='cell-center principal E I / ds hinge stiffness and springref',
             independent_choice='basis/quadrature versus hinge stiffness conversion',
             observation='mapped stiffness matrix gap 18.3%; elastic force gap 0.442e-3 N*m^2'),
        dict(quantity='tendon_geometry_and_force', owner='family.design', source='Tendon ordered attachment points and holes; straight_frictionless model; force limit and pretension',
             explicit_fact='route topology, anchor/guide locations, ideal frictionless span semantics',
             gvs='continuous attachment poses and -J_length.T tension',
             backend='compiler attachment sites, MuJoCo spatial tendon, negative gain direct tension',
             independent_choice='moment arms are derivatives of different deformed geometries',
             observation='route bindings and force sign match; Jacobian gap 2.33e-4 m^2/rad'),
        dict(quantity='actuation', owner='family.design plus control plan', source='Actuator command type, drum, transmission ratio, travel and speed limits; tendon servo gain',
             explicit_fact='kinematic transmission and command limits',
             gvs='ideal tendon tension as model input; no motor state',
             backend='ideal_tension or actuator_realistic control mode from scene/control, XML actuator implementation',
             independent_choice='command-to-tension dynamics and execution mode belong to model/control',
             observation='Stage 3.7 direct-tension u0 matches exactly; motor dynamics omitted'),
        dict(quantity='shape_and_discretization', owner='family.design plus separate model configuration',
             source='section stations, connections and guide positions in design; cells in family.discretization; basis in GVS model parameters',
             explicit_fact='physical geometry and topology; numerical resolution is separate',
             gvs='structural_linear basis and 24 integration steps per segment',
             backend='three principal-hinge cells per segment in this case',
             independent_choice='deformation space, quadrature and cell placement',
             observation='q transfer exact; tip gap 16.743 mm at q0'),
        dict(quantity='boundary_and_task_interface', owner='RobotDescription and Task/Assembly',
             source='Design.tip and RobotDescription.channels; mount, gravity, external forces and target in task environment',
             explicit_fact='named tip/channel interface and scene boundary conditions',
             gvs='requires assembly and rejects external applied forces in build_system',
             backend='scene mount, gravity, external forces and floor compiled into XML/execution',
             independent_choice='supported load/contact physics differ by model',
             observation='Stage 3.7 reference scene has no external forces'),
    ]

    gaps = [
        dict(id='cross_model_equivalence', priority='HIGH', kind='missing validation contract',
             finding='No shared requirement says how a GVS state and cell state must agree in shape, COM, tendon Jacobian or force residual at a reference pose.',
             evidence='exact q transfer but 16.743 mm tip, 9.321 mm far COM and 1.771e-3 N*m^2 gravity gaps',
             scope='cross-model validation; not necessarily a new physical RobotIR field'),
        dict(id='deformation_and_quadrature_policy', priority='HIGH', kind='separate model choice',
             finding='GVS basis/integration and serial cell count/sample rule are separate numerical policies. RobotIR physical geometry alone cannot force equal deformed states.',
             evidence='structural_linear versus three cells; 18.3% stiffness matrix gap',
             scope='backend-specific approximation that needs explicit provenance and convergence criteria'),
        dict(id='full_continuum_constitutive_law', priority='HIGH for full Cosserat/FEM; outside current bending model', kind='absent physical inputs',
             finding='PhysicalInput supplies E or bending EI and bending viscosity, not a full shear/torsion/axial or nonlinear 3D material law.',
             evidence='PhysicalInput schema; GVS and serial model capabilities explicitly omit shear, stretch and material torsion',
             scope='only needed if those richer physics are claimed'),
        dict(id='tendon_contact_mechanics', priority='MEDIUM for current comparison; HIGH for contact-rich models', kind='restricted explicit semantics',
             finding='Ordered straight frictionless spans and guide points are explicit; guide contact/wrap, friction, cable elasticity and motor dynamics are not modeled.',
             evidence='Tendon.model literal and generator paths; route bindings agree but moment arms differ',
             scope='do not infer richer cable physics from current attachment data'),
        dict(id='flexible_mass_distribution', priority='MEDIUM', kind='derived physical quantity',
             finding='Flexible mass/COM/inertia are generated from section and density. Material-mode RobotIR defines a continuum distribution, but sampling/lumping is independent.',
             evidence='0.0031% total mass gap but 9.321 mm far world COM gap',
             scope='preserve source density/sections; record generator sampling and reference-state COM'),
        dict(id='equivalent_mode_density', priority='MEDIUM for future volumetric models', kind='conditional information gap',
             finding='Equivalent mode authorizes line density and principal bending EI without a volumetric Young modulus or density.',
             evidence='PhysicalInput.authority validator',
             scope='sufficient for reduced bending; cannot uniquely determine a 3D material law'),
        dict(id='volumetric_geometry_and_interfaces', priority='HIGH for FEM; outside current rod scope', kind='absent physical representation',
             finding='Sections and envelopes describe rods and rigid bodies, not a material-labelled 3D solid with bonded/contact interfaces.',
             evidence='Section/Segment/Rigid contracts and compiler convex collision approximation',
             scope='required only when claiming volumetric fidelity'),
        dict(id='scene_separation', priority='LOW', kind='intentional ownership boundary',
             finding='Mount, gravity, external forces and target belong to task assembly, not RobotIR.',
             evidence='route.json task.environment and GVS build_system scene requirement',
             scope='keep boundary conditions explicit in a composed experiment; not missing robot facts'),
    ]

    suitability = [
        dict(model='PCC', assessment='SUFFICIENT for current kinematics',
             reason='The existing PCC provider reads family.design components/tip plus explicit curvature query; it does not claim loads or dynamics.'),
        dict(model='current bending GVS', assessment='SUFFICIENT for declared restricted model; cross-model fidelity unverified',
             reason='Design supplies geometry/material/tendon inputs; basis and quadrature remain model parameters; no shear, stretch, torsion or contact.'),
        dict(model='serial MuJoCo', assessment='SUFFICIENT for declared cell model; not continuum-equivalent by construction',
             reason='Design plus family.discretization and scene compile into cells, hinge springs, masses and spatial tendons.'),
        dict(model='general Cosserat or SoRoSim-style model', assessment='PARTIAL',
             reason='Rod sections and connections exist, but full strain constitutive inputs, richer actuation and boundary semantics are absent; basis and strain modes must be chosen.'),
        dict(model='volumetric FEM', assessment='INSUFFICIENT for general high-fidelity claims',
             reason='Cross sections could seed a simple rod mesh, but 3D material law, volumetric domains/interfaces and contact/boundary semantics are not specified.'),
    ]

    result = dict(reference=dict(robot_identity=s39['reference_state']['robot_identity'],
        design_id=design.id, structure_contract=robot.structure.contract,
        design_identity=digest(design.model_dump(mode='json')),
        discretization_identity=s39['reference_state']['backend_discretization_identity'],
        basis_identity=s39['reference_state']['basis_identity'],
        source='runs/stage35_case_b_retry_softagent_20260924/inputs/route.json'),
        contract_inventory={name:fields(contract) for name, contract in (
            ('RobotDescription',RobotDescription),('Design',Design),('Segment',Segment),
            ('Section',Section),('PhysicalInput',PhysicalInput),('Rigid',Rigid),
            ('Tendon',Tendon),('Actuator',Actuator),('Discretization',Discretization),
            ('GVSModelParameters',GVSModelParameters))},
        ownership=dict(physical_design='robot.structure:family.design',
            numerical_mesh='policy.discretization:family.discretization',
            gvs_basis='GVSModelParameters.basis',
            task_scene='task.environment:experiment.assembly',
            legacy_cells='Segment.cells compatibility input excluded from canonical Design'),
        case_inventory=dict(flexible_segments=segment_examples, rigid_components=rigid_examples,
            tendon_count=len(design.tendons), actuator_count=len(design.actuators),
            backend_cells=mesh.cells, gvs_basis=s38['reference_state']['basis']['specification']),
        physical_traces=traces, gaps=gaps, future_model_suitability=suitability,
        conclusion=dict(shared_source_of_supported_robot_design_inputs=True,
            cross_model_physical_equivalence_guaranteed=False,
            main_issue='model-dependent reconstruction and missing equivalence criteria, with conditional gaps for richer physics',
            recommended_next_step='Define one frozen reference-state equivalence contract for shape, COM, gravity, stiffness and tendon Jacobian, including approximation provenance and tolerances, before proposing new RobotIR fields.'))
    atomic_json(HERE / 'robotir_physical_fact_audit.json', result)
    print(json.dumps(dict(design_id=design.id, trace_count=len(traces),
        high_priority_gaps=sum(item['priority'].startswith('HIGH') for item in gaps),
        conclusion=result['conclusion']), indent=2))


if __name__ == '__main__':
    main()
