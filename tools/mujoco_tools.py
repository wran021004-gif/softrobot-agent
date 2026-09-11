import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import mujoco

from schemas.design_spec import DesignSpec
from schemas.task_spec import TaskSpec
from schemas.tool_result import ToolResult


# Fixed surrogate/simulator parameters, not DesignSpec morphology fields.
JOINT_STIFFNESS_NM_PER_RAD = 0.1
JOINT_DAMPING_NM_S_PER_RAD = 0.1
BODY_DENSITY_KG_M3 = 1000.0
TENDON_SERVO_KP = 1000.0  # N/m
TENDON_FORCE_LIMIT_N = 20.0  # Pull only: actuator force range [-limit, 0].
MUJOCO_TASK_STEPS = 1000  # 2 seconds at reach_free's 0.002 s timestep.


def compile_mujoco(design: DesignSpec, task: TaskSpec, output_path: Path) -> ToolResult:
    """Compose a fixed environment with a single-section tendon surrogate."""
    if design.robot_family != "tendon_driven_continuum":
        return ToolResult(
            status="fail", tool="compile_mujoco",
            failure_code="UNSUPPORTED_ROBOT_FAMILY",
        )
    if design.sections != 1:
        return ToolResult(
            status="fail", tool="compile_mujoco",
            failure_code="UNSUPPORTED_DESIGN_CONFIGURATION",
            message="Only sections=1 is supported.",
        )
    if design.segments <= 0 or design.tendon_count <= 0 or not all(
        math.isfinite(value) and value > 0 for value in (
            design.total_length_m, design.body_radius_m, design.tendon_routing_radius_m,
        )
    ):
        return ToolResult(
            status="fail", tool="compile_mujoco",
            failure_code="INVALID_DESIGN", message="Counts and dimensions must be positive and finite.",
        )
    segment_length = design.total_length_m / design.segments
    # Select a checked-in environment by ID, never an arbitrary file path.
    if not re.fullmatch(r"[A-Za-z0-9_-]+", task.environment_id):
        return ToolResult(
            status="fail", tool="compile_mujoco",
            failure_code="INVALID_ENVIRONMENT", message="Invalid environment_id.",
        )
    environment_path = (
        Path(__file__).resolve().parents[1] / "mujoco/environments"
        / f"{task.environment_id}.xml"
    )
    try:
        root = ET.parse(environment_path).getroot()
        world = root.find("worldbody")
        if root.tag != "mujoco" or world is None:
            raise ValueError("Environment requires a mujoco root and worldbody.")
    except (OSError, ET.ParseError, ValueError) as exc:
        return ToolResult(
            status="fail", tool="compile_mujoco",
            failure_code="INVALID_ENVIRONMENT", message=str(exc),
        )
    ET.SubElement(
        world, "site", name="target_site", type="sphere", size="0.008",
        pos=" ".join(str(value) for value in task.target_m), rgba="1 0 0 1",
    )
    routing_offsets = [
        (design.tendon_routing_radius_m * math.cos(2 * math.pi * i / design.tendon_count),
         design.tendon_routing_radius_m * math.sin(2 * math.pi * i / design.tendon_count))
        for i in range(design.tendon_count)
    ]
    for i, (y, z) in enumerate(routing_offsets):
        ET.SubElement(
            world, "site", name=f"tendon_{i}_base", pos=f"0 {y} {z}", size="0.002",
        )
    parent = world
    for index in range(design.segments):
        position = "0 0 0" if index == 0 else f"{segment_length} 0 0"
        body = ET.SubElement(parent, "body", name=f"segment_{index}", pos=position)
        for axis_name, axis in (("y", "0 1 0"), ("z", "0 0 1")):
            ET.SubElement(
                body, "joint", name=f"joint_{index}_{axis_name}", type="hinge", axis=axis,
                stiffness=str(JOINT_STIFFNESS_NM_PER_RAD),
                damping=str(JOINT_DAMPING_NM_S_PER_RAD),
            )
        ET.SubElement(
            body, "geom", name=f"capsule_{index}", type="capsule",
            fromto=f"0 0 0 {segment_length} 0 0", size=str(design.body_radius_m),
            density=str(BODY_DENSITY_KG_M3), contype="1", conaffinity="0",
        )
        for i, (y, z) in enumerate(routing_offsets):
            ET.SubElement(
                body, "site", name=f"tendon_{i}_seg_{index}",
                pos=f"{segment_length} {y} {z}", size="0.002",
            )
        parent = body

    ET.SubElement(
        parent, "site", name="tip_site", type="sphere", size="0.005",
        pos=f"{segment_length} 0 0", rgba="0 1 0 1",
    )

    tendons = ET.SubElement(root, "tendon")
    actuators = ET.SubElement(root, "actuator")
    for i in range(design.tendon_count):
        spatial = ET.SubElement(tendons, "spatial", name=f"tendon_{i}", width="0.001")
        ET.SubElement(spatial, "site", site=f"tendon_{i}_base")
        for index in range(design.segments):
            ET.SubElement(spatial, "site", site=f"tendon_{i}_seg_{index}")
        # Unit gear makes ctrl the target path length in meters. Negative force
        # pulls the tendon; the upper bound prevents a cable from pushing.
        ET.SubElement(
            actuators, "position", name=f"tendon_{i}_actuator", tendon=f"tendon_{i}",
            gear="1", kp=str(TENDON_SERVO_KP), forcelimited="true",
            forcerange=f"{-TENDON_FORCE_LIMIT_N} 0",
        )

    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(root)
    ET.ElementTree(root).write(output_path, encoding="utf-8", xml_declaration=True)
    return ToolResult(
        status="pass",
        tool="compile_mujoco",
        artifacts={"mjcf_path": str(output_path)},
    )


def validate_task(
    xml_path: str | Path, task: TaskSpec,
    tendon_target_lengths_m: list[float] | None = None,
) -> ToolResult:
    """Check finite simulation state and the final tip-to-target distance."""
    try:
        model = mujoco.MjModel.from_xml_path(str(xml_path))
        data = mujoco.MjData(model)
        tip_site_id = model.site("tip_site").id
        commands = None
        if tendon_target_lengths_m is not None:
            try:
                commands = [float(value) for value in tendon_target_lengths_m]
            except (TypeError, ValueError):
                return ToolResult(
                    status="fail", tool="validate_task", failure_code="INVALID_TENDON_COMMAND",
                    message="Tendon targets must be a sequence of finite positive lengths.",
                )
            if (
                len(commands) != model.nu or model.nu != model.ntendon
                or not all(math.isfinite(value) and value > 0 for value in commands)
                or any(value != mujoco.mjtTrn.mjTRN_TENDON for value in model.actuator_trntype)
                or any(int(model.actuator_trnid[i, 0]) != i for i in range(model.nu))
            ):
                return ToolResult(
                    status="fail", tool="validate_task", failure_code="INVALID_TENDON_COMMAND",
                    message="Expected one positive length per tendon actuator in tendon order.",
                )
            data.ctrl[:] = commands
        else:
            # Zero ctrl would command zero LENGTH and pull hard. Disable actuator
            # forces explicitly to preserve unactuated validation when omitted.
            model.opt.disableflags |= int(mujoco.mjtDisableBit.mjDSBL_ACTUATION)
        for _ in range(MUJOCO_TASK_STEPS):
            mujoco.mj_step(model, data)
            if not (
                all(math.isfinite(value) for value in data.qpos)
                and all(math.isfinite(value) for value in data.qvel)
            ):
                return ToolResult(
                    status="fail", tool="validate_task",
                    failure_code="NONFINITE_STATE",
                    message="qpos or qvel contains a non-finite value.",
                )
        # Refresh site positions from qpos after the final integration step.
        mujoco.mj_forward(model, data)
        tip_position = [float(value) for value in data.site_xpos[tip_site_id]]
        if not all(math.isfinite(value) for value in tip_position):
            return ToolResult(
                status="fail", tool="validate_task",
                failure_code="NONFINITE_STATE",
                message="tip_site position contains a non-finite value.",
            )
        target_position = [float(value) for value in task.target_m]
        position_error = math.dist(tip_position, target_position)
        task_success = position_error <= task.position_error_max_m
        metrics = {
            "steps": MUJOCO_TASK_STEPS, "nq": model.nq, "nv": model.nv,
            "tip_position_m": tip_position,
            "target_position_m": target_position,
            "position_error_m": position_error,
            "position_error_max_m": task.position_error_max_m,
            "task_success": task_success,
        }
        if commands is not None:
            metrics.update({
                "tendon_target_lengths_m": commands,
                "final_tendon_lengths_m": [float(value) for value in data.ten_length],
                "actuator_controls": [float(value) for value in data.ctrl],
                "actuator_force": [float(value) for value in data.actuator_force],
            })
        return ToolResult(
            status="pass" if task_success else "fail", tool="validate_task",
            failure_code=None if task_success else "TASK_FAILED",
            metrics=metrics,
        )
    except Exception as exc:
        return ToolResult(
            status="fail", tool="validate_task",
            failure_code="PHYSICS_ERROR", message=str(exc),
        )
