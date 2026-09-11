import math
from schemas.design_spec import DesignSpec
from schemas.robot_ir import RobotIR, SectionIR, TendonRoute
from tools.capability_resolver import resolve_capability, CapabilityState
from tools.spec_tools import load_physics, ROOT

CONTRACTS = ("coordinate_frames.md", "tendon_driven_pcc_v1.md", "tendon_length_mapping_v1.md", "segmented_mujoco_mapping_v1.md", "actuator_model_v1.md")


def build_robot_ir(design: DesignSpec) -> RobotIR:
    design = DesignSpec.model_validate(design)
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
    if (value.mechanics != load_physics() or value.physics_contracts != CONTRACTS
            or any(not (ROOT / "physics_contracts" / name).is_file() for name in CONTRACTS)):
        raise ValueError("PHYSICS_ASSUMPTION_REQUIRED: unapproved IR mechanics or contracts")
    return value
