import math
from pathlib import Path

# Load Python's XML backend before MATLAB's DLLs on Windows; MATLAB's Expat
# can otherwise shadow Conda's library when the compiler later parses MJCF.
import xml.parsers.expat

import matlab.engine

from schemas.design_spec import DesignSpec
from schemas.task_spec import TaskSpec
from schemas.tool_result import ToolResult


class MatlabTools:
    def __init__(self):
        project_root = Path(__file__).resolve().parents[1]
        self.eng = matlab.engine.start_matlab()
        try:
            self.eng.addpath(str(project_root / "matlab"), nargout=0)
        except Exception:
            self.close()
            raise

    def analyze_workspace(self, design: DesignSpec, task: TaskSpec) -> ToolResult:
        if design.robot_family != "tendon_driven_continuum":
            return ToolResult(
                status="fail", tool="analyze_workspace",
                failure_code="UNSUPPORTED_ROBOT_FAMILY",
            )
        reachable, distance, max_reach, margin = self.eng.analyze_workspace(
            design.total_length_m,
            task.target_m[0],
            task.target_m[1],
            task.target_m[2],
            nargout=4,
        )
        reachable = bool(reachable)
        return ToolResult(
            status="pass" if reachable else "fail",
            tool="analyze_workspace",
            failure_code=None if reachable else "DESIGN_INFEASIBLE",
            metrics={
                "target_reachable": reachable,
                "target_distance_m": float(distance),
                "max_reach_m": float(max_reach),
                "reach_margin_m": float(margin),
            },
        )

    def plan_pcc_reach(self, design: DesignSpec, task: TaskSpec) -> ToolResult:
        """Return best-effort PCC tendon targets, even when model tolerance fails."""
        if design.robot_family != "tendon_driven_continuum":
            return ToolResult(
                status="fail", tool="plan_pcc_reach",
                failure_code="UNSUPPORTED_ROBOT_FAMILY",
            )
        if design.sections != 1:
            return ToolResult(
                status="fail", tool="plan_pcc_reach",
                failure_code="UNSUPPORTED_DESIGN_CONFIGURATION",
                message="Only sections=1 is supported.",
            )
        if (
            design.tendon_count <= 0
            or not all(math.isfinite(value) and value > 0 for value in (
                design.total_length_m, design.tendon_routing_radius_m,
            ))
            or not all(math.isfinite(value) for value in task.target_m)
            or not math.isfinite(task.position_error_max_m)
            or task.position_error_max_m < 0
        ):
            return ToolResult(
                status="fail", tool="plan_pcc_reach", failure_code="PCC_INVALID_COMMAND",
                message="PCC requires positive dimensions/count and finite target/tolerance.",
            )
        theta, phi, tip, error, success, lengths, deltas = self.eng.plan_pcc_reach(
            design.total_length_m, float(design.tendon_count), design.tendon_routing_radius_m,
            *task.target_m, task.position_error_max_m, nargout=7,
        )
        # MATLAB returns row vectors; expose only ordinary Python float lists.
        tip = [float(value) for value in tip[0]]
        # Engine converts a 1x1 double to a scalar when tendon_count == 1.
        lengths = ([float(lengths)] if isinstance(lengths, (int, float))
                   else [float(value) for value in lengths[0]])
        deltas = ([float(deltas)] if isinstance(deltas, (int, float))
                  else [float(value) for value in deltas[0]])
        if (
            len(lengths) != design.tendon_count
            or len(deltas) != design.tendon_count
            or len(tip) != 3
            or not all(math.isfinite(value) for value in (
                float(theta), float(phi), float(error), *tip, *lengths, *deltas,
            ))
            or any(value <= 0 for value in lengths)
        ):
            return ToolResult(
                status="fail", tool="plan_pcc_reach", failure_code="PCC_INVALID_COMMAND",
                message="PCC produced invalid or nonpositive tendon targets.",
            )
        return ToolResult(
            status="pass", tool="plan_pcc_reach",
            metrics={
                "theta_rad": float(theta), "phi_rad": float(phi),
                "predicted_tip_m": tip, "target_position_m": list(task.target_m),
                "predicted_position_error_m": float(error),
                "model_task_success": bool(success),
                "tendon_target_lengths_m": lengths, "tendon_delta_lengths_m": deltas,
                "tendon_count": design.tendon_count,
                "tendon_routing_radius_m": design.tendon_routing_radius_m,
            },
        )

    def close(self):
        self.eng.quit()
