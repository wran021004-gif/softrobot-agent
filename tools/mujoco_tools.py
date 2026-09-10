import math
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco

from schemas.design_spec import DesignSpec
from schemas.tool_result import ToolResult


def compile_mujoco(design: DesignSpec, output_path: Path) -> ToolResult:
    """MVP segmented approximation.

    TODO: add physical tendon routing and actuation.
    Sections and tendon fields are reserved; this MVP builds one passive chain.
    """
    segment_length = design.total_length_m / design.segments
    root = ET.Element("mujoco", model="segmented_arm")
    ET.SubElement(root, "option", gravity="0 0 -9.81", timestep="0.002")
    defaults = ET.SubElement(root, "default")
    ET.SubElement(defaults, "joint", type="hinge", axis="0 1 0", damping="0.1")
    # Contact masks allow arm-floor contact without arm self-contact.
    ET.SubElement(defaults, "geom", density="1000", contype="1", conaffinity="0")
    world = ET.SubElement(root, "worldbody")
    ET.SubElement(
        world, "geom", name="floor", type="plane", size="2 2 0.1",
        contype="0", conaffinity="1",
    )
    parent = world
    for index in range(design.segments):
        position = (
            f"0 0 {design.total_length_m + design.body_radius_m}"
            if index == 0 else f"{segment_length} 0 0"
        )
        body = ET.SubElement(parent, "body", name=f"segment_{index}", pos=position)
        ET.SubElement(body, "joint", name=f"joint_{index}")
        ET.SubElement(
            body, "geom", name=f"capsule_{index}", type="capsule",
            fromto=f"0 0 0 {segment_length} 0 0", size=str(design.body_radius_m),
        )
        parent = body

    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(root)
    ET.ElementTree(root).write(output_path, encoding="utf-8", xml_declaration=True)
    return ToolResult(
        status="pass",
        tool="compile_mujoco",
        artifacts={"mjcf_path": str(output_path)},
    )


def validate_physics(xml_path: str | Path) -> ToolResult:
    try:
        model = mujoco.MjModel.from_xml_path(str(xml_path))
        data = mujoco.MjData(model)
        for _ in range(100):
            mujoco.mj_step(model, data)
            if not (
                all(math.isfinite(value) for value in data.qpos)
                and all(math.isfinite(value) for value in data.qvel)
            ):
                return ToolResult(
                    status="fail", tool="validate_physics",
                    failure_code="NONFINITE_STATE",
                    message="qpos or qvel contains a non-finite value.",
                )
        return ToolResult(
            status="pass", tool="validate_physics",
            metrics={"steps": 100, "nq": model.nq, "nv": model.nv},
        )
    except Exception as exc:
        return ToolResult(
            status="fail", tool="validate_physics",
            failure_code="PHYSICS_ERROR", message=str(exc),
        )
