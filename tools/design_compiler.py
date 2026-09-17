import math
from schemas.design_spec import DesignSpec
from schemas.robot_ir import RobotIR, SectionIR, TendonRoute
from tools.capability_resolver import resolve_capability, CapabilityState
from tools.spec_tools import load_physics, ROOT

CONTRACTS = ("coordinate_frames.md", "tendon_driven_pcc_v1.md", "tendon_length_mapping_v1.md", "segmented_mujoco_mapping_v1.md", "actuator_model_v1.md")


def build_robot_ir(design: DesignSpec, discretization=None) -> RobotIR:
    """Compile a robot description.

    Family designs require their independent ``family.discretization`` value;
    older DesignSpec callers retain the original one-argument form.
    """
    from extensions.tendon_family.contracts import Design as FamilyDesign
    if isinstance(design, FamilyDesign):
        from extensions.tendon_family.compiler import resolve
        return resolve(design,discretization)
    design = DesignSpec.model_validate(design)
    if design.exploration_physics is not None:
        return build_exploration_ir(design)
    resolved = resolve_capability(design)
    if resolved.state not in (CapabilityState.SUPPORTED, CapabilityState.PARAMETRICALLY_SUPPORTED):
        raise ValueError(f"{resolved.state.value}: {resolved.reason}")
    if any(not (ROOT / "physics_contracts" / name).is_file() for name in CONTRACTS):
        raise ValueError("PHYSICS_ASSUMPTION_REQUIRED: missing approved V1 contract")
    routes = []
    for i in range(design.tendon_count):
        angle = 2 * math.pi * i / design.tendon_count
        routes.append(TendonRoute(index=i, angle_rad=angle, offset_yz_m=(
            design.tendon_routing_radius_m * math.cos(angle), design.tendon_routing_radius_m * math.sin(angle))))
    return RobotIR(robot_family=design.robot_family, section=SectionIR(
        length_m=design.total_length_m, segments=design.segments,
        segment_length_m=design.total_length_m / design.segments, body_radius_m=design.body_radius_m),
        tendon_routing_radius_m=design.tendon_routing_radius_m, tendon_routes=tuple(routes),
        mechanics=load_physics(), physics_contracts=CONTRACTS)


def ensure_robot_ir(value: DesignSpec | RobotIR) -> RobotIR:
    if not isinstance(value, RobotIR):
        return build_robot_ir(value)
    value = RobotIR.model_validate(value.model_dump())
    if value.mechanics.profile == 'equivalent_rod_v2':
        rebuilt = build_exploration_ir(DesignSpec(robot_family=value.robot_family, sections=1,
            segments=value.segments, total_length_m=value.total_length_m, body_radius_m=value.body_radius_m,
            tendon_count=value.tendon_count, tendon_routing_radius_m=value.tendon_routing_radius_m,
            exploration_physics=value.mechanics))
        if rebuilt != value:
            raise ValueError('V2 resolved mechanics or identity mismatch')
        return value
    if (value.mechanics != load_physics() or value.physics_contracts != CONTRACTS
            or any(not (ROOT / "physics_contracts" / name).is_file() for name in CONTRACTS)):
        raise ValueError("PHYSICS_ASSUMPTION_REQUIRED: unapproved IR mechanics or contracts")
    return value


def build_exploration_ir(design):
    from schemas.exploration import ResolvedRod
    if design.robot_family != 'tendon_driven_continuum' or design.sections != 1 or design.segments != 8:
        raise ValueError('V2 reach search fixes one section and the reference eight-segment grid')
    bounds = {'total_length_m':(.05,.8), 'body_radius_m':(.005,.05), 'tendon_routing_radius_m':(.002,.045), 'tendon_count':(3,8)}
    for name,(lo,hi) in bounds.items():
        if not lo <= getattr(design,name) <= hi:
            raise ValueError(f'{name} outside authorized V2 envelope [{lo},{hi}]')
    if design.tendon_routing_radius_m > .9*design.body_radius_m + 1e-14:
        raise ValueError('Routing must lie inside guide/body: r_tendon <= 0.9 r_body')
    p=design.exploration_physics; n=design.segments; ds=design.total_length_m/n; r=design.body_radius_m
    m=p.line_density_kg_m*ds
    rod=ResolvedRod(mass_kg=(m,)*n, inertia_diagonal_kg_m2=((m*r*r/2,m*(3*r*r+ds*ds)/12,m*(3*r*r+ds*ds)/12),)*n,
        stiffness_nm_rad=tuple(p.root_ei_nm2*(1+(p.tip_ei_ratio-1)*i/(n-1))/ds for i in range(n)),
        damping_nm_s_rad=(p.bending_viscosity_nm2_s/ds,)*n, natural_y_rad=(-p.natural_total_angle_rad/n,)*n)
    routes=tuple(TendonRoute(index=i,angle_rad=2*math.pi*i/design.tendon_count,
        offset_yz_m=(design.tendon_routing_radius_m*math.cos(2*math.pi*i/design.tendon_count),
                     design.tendon_routing_radius_m*math.sin(2*math.pi*i/design.tendon_count))) for i in range(design.tendon_count))
    return RobotIR(robot_family=design.robot_family,section=SectionIR(length_m=design.total_length_m,
        segments=n,segment_length_m=ds,body_radius_m=r),tendon_routing_radius_m=design.tendon_routing_radius_m,
        tendon_routes=routes,mechanics=p,resolved_rod=rod,physics_contracts=('equivalent_rod_v2.md',))
