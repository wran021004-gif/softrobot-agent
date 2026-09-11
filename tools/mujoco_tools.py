import math
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco

from schemas.design_spec import DesignSpec
from schemas.task_spec import TaskSpec
from schemas.tool_result import ToolResult
from schemas.robot_ir import RobotIR
from schemas.environment_spec import EnvironmentSpec
from schemas.settings import SimulatorSpec, RunSettings
from tools.design_compiler import ensure_robot_ir
from tools.spec_tools import load_environment, load_simulator, load_run_settings, environment_xml, validate_frozen_environment, ROOT
from controllers.base import Controller
from controllers.open_loop_length import OpenLoopLength
from metrics.reach import evaluate_reach
from tools.mujoco_evidence import ExecutionEvidence


def compile_mujoco(design: DesignSpec | RobotIR, task: TaskSpec, output_path: Path,
                   environment: EnvironmentSpec | None = None, simulator: SimulatorSpec | None = None) -> ToolResult:
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
    design = ensure_robot_ir(design)
    segment_length = design.section.segment_length_m
    try:
        if environment is None:
            package = ROOT / "tasks" / task.environment_id
            environment = load_environment(package / "environment.yaml")
            validate_frozen_environment(environment, package / "mujoco.xml")
        if environment.environment_id != task.environment_id or environment.coordinate_frame != design.coordinate_frame:
            raise ValueError("Environment identity/frame mismatch")
        root = environment_xml(environment)
        root.find("option").set("timestep", str((simulator or load_simulator()).timestep_s))
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
    routing_offsets = [route.offset_yz_m for route in design.tendon_routes]
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
                stiffness=str(design.mechanics.joint_stiffness_nm_per_rad),
                damping=str(design.mechanics.joint_damping_nm_s_per_rad),
            )
        ET.SubElement(
            body, "geom", name=f"capsule_{index}", type="capsule",
            fromto=f"0 0 0 {segment_length} 0 0", size=str(design.body_radius_m),
            density=str(design.mechanics.body_density_kg_m3), contype="1", conaffinity="0",
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
            gear="1", kp=str(design.mechanics.tendon_servo_kp_n_per_m), forcelimited="true",
            forcerange=f"{-design.mechanics.tendon_force_limit_n} 0",
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


def run_task(
    xml_path: str | Path, task: TaskSpec,
    controller: Controller | None = None,
    run_settings: RunSettings | None = None,
    environment: EnvironmentSpec | None = None,
    evaluator=None,
) -> ToolResult:
    """Check finite simulation state and the final tip-to-target distance."""
    evidence = None
    window_evidence = None
    def observed():
        result = {"execution_evidence": evidence.summary(model, data), "steps_completed": evidence.steps} if evidence else {}
        if window_evidence:
            result["window_evidence"] = window_evidence.summary()
        return result
    try:
        settings = run_settings or load_run_settings()
        if task.task_type not in ("reach", "reach_window"):
            return ToolResult(status="fail", tool="run_task", failure_code="CAPABILITY_MISSING")
        model = mujoco.MjModel.from_xml_path(str(xml_path))
        data = mujoco.MjData(model)
        tip_site_id = model.site("tip_site").id
        # Kinematics on a separate data object cannot alter the executed state or
        # solver warm start. No extra forward/step calls enter the baseline loop.
        initial_data = mujoco.MjData(model)
        mujoco.mj_kinematics(model, initial_data)
        initial_tip = initial_data.site_xpos[tip_site_id].tolist()
        evidence = ExecutionEvidence(model, data, settings.steps, initial_tip, controller)
        if task.task_type == "reach_window":
            from tools.window_geometry import constrained_window
            from tools.window_evidence import WindowEvidence
            if environment is None:
                raise ValueError("reach_window execution requires its EnvironmentSpec")
            window_evidence = WindowEvidence(model, constrained_window(environment, task))
        commands = None
        for step in range(settings.steps):
            try:
                command = controller.command(float(data.time), {"qpos": data.qpos.tolist(), "qvel": data.qvel.tolist()}) if controller else None
                commands = list(command.tendon_target_lengths_m) if command is not None else None
            except Exception as exc:
                return ToolResult(
                    status="fail", tool="run_task", failure_code="CONTROL_FAILURE",
                    metrics=observed(), message=str(exc),
                )
            if commands is not None and (
                len(commands) != model.nu or model.nu != model.ntendon
                or not all(math.isfinite(value) and value > 0 for value in commands)
                or any(value != mujoco.mjtTrn.mjTRN_TENDON for value in model.actuator_trntype)
                or any(int(model.actuator_trnid[i, 0]) != i for i in range(model.nu))
            ):
                return ToolResult(
                    status="fail", tool="run_task", failure_code="INVALID_TENDON_COMMAND",
                    metrics=observed(),
                    message="Expected one positive length per tendon actuator in tendon order.",
                )
            if commands is not None:
                model.opt.disableflags &= ~int(mujoco.mjtDisableBit.mjDSBL_ACTUATION)
                data.ctrl[:] = commands
            else:
                # Zero ctrl means zero length; disable forces for passive execution.
                model.opt.disableflags |= int(mujoco.mjtDisableBit.mjDSBL_ACTUATION)
            mujoco.mj_step(model, data)
            evidence.observe_step(model, data, commands)
            if not (
                all(math.isfinite(value) for value in data.qpos)
                and all(math.isfinite(value) for value in data.qvel)
            ):
                return ToolResult(
                    status="fail", tool="run_task",
                    failure_code="NONFINITE_STATE",
                    metrics=observed(),
                    message="qpos or qvel contains a non-finite value.",
                )
            if window_evidence:
                # mj_step's geom/contact arrays describe the pre-integration pose.
                window_evidence.observe(model, data, data.time - model.opt.timestep)
        # Refresh site positions from qpos after the final integration step.
        mujoco.mj_forward(model, data)
        if window_evidence:
            window_evidence.observe(model, data, data.time)
        tip_position = [float(value) for value in data.site_xpos[tip_site_id]]
        if not all(math.isfinite(value) for value in tip_position):
            return ToolResult(
                status="fail", tool="run_task",
                failure_code="NONFINITE_STATE",
                metrics=observed(),
                message="tip_site position contains a non-finite value.",
            )
        metrics = {
            **observed(),
            "steps": settings.steps, "nq": model.nq, "nv": model.nv,
            **(evaluator or evaluate_reach)(tip_position, task, window_evidence.summary() if window_evidence else None),
        }
        if commands is not None:
            metrics.update({
                "tendon_target_lengths_m": commands,
                "final_tendon_lengths_m": [float(value) for value in data.ten_length],
                "actuator_controls": [float(value) for value in data.ctrl],
                "actuator_force": [float(value) for value in data.actuator_force],
            })
        return ToolResult(
            status="pass" if metrics["task_success"] else "fail", tool="run_task",
            failure_code=None if metrics["task_success"] else "TASK_FAILED",
            metrics=metrics,
            artifacts={"final_state": {"time_s": float(data.time), "qpos": data.qpos.tolist(), "qvel": data.qvel.tolist()}},
        )
    except Exception as exc:
        return ToolResult(
            status="fail", tool="run_task",
            failure_code="PHYSICS_ERROR", metrics=observed(), message=str(exc),
        )


def validate_task(xml_path: str | Path, task: TaskSpec,
                  tendon_target_lengths_m: list[float] | None = None) -> ToolResult:
    """V1 compatibility entry point, with the unchanged canonical reach gate."""
    try:
        controller = OpenLoopLength(tendon_target_lengths_m) if tendon_target_lengths_m is not None else None
    except (TypeError, ValueError) as exc:
        return ToolResult(status="fail", tool="validate_task", failure_code="INVALID_TENDON_COMMAND", message=str(exc))
    result = run_task(xml_path, task, controller)
    return result.model_copy(update={"tool": "validate_task"})
