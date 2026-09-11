import math
from pathlib import Path

# Load Python's XML backend before MATLAB's DLLs on Windows; MATLAB's Expat
# can otherwise shadow Conda's library when the compiler later parses MJCF.
import xml.parsers.expat

from schemas.design_spec import DesignSpec
from schemas.robot_ir import RobotIR
from schemas.environment_spec import EnvironmentSpec
from schemas.task_spec import TaskSpec
from schemas.tool_result import ToolResult
from tools.design_compiler import ensure_robot_ir
from tools.spec_tools import load_environment


class MatlabTools:
    def __init__(self):
        import matlab.engine
        project_root = Path(__file__).resolve().parents[1]
        self.eng = matlab.engine.start_matlab()
        try:
            self.eng.addpath(str(project_root / "matlab"), nargout=0)
        except Exception:
            self.close()
            raise

    def analyze_workspace(self, design: DesignSpec | RobotIR, task: TaskSpec, environment: EnvironmentSpec | None = None) -> ToolResult:
        if design.robot_family != "tendon_driven_continuum":
            return ToolResult(
                status="fail", tool="analyze_workspace",
                failure_code="UNSUPPORTED_ROBOT_FAMILY",
            )
        design = ensure_robot_ir(design)
        self._check_environment(design, task, environment)
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

    def plan_pcc_reach(self, design: DesignSpec | RobotIR, task: TaskSpec, environment: EnvironmentSpec | None = None) -> ToolResult:
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
        design = ensure_robot_ir(design)
        self._check_environment(design, task, environment)
        import matlab
        theta, phi, tip, error, success, lengths, deltas = self.eng.plan_pcc_reach(
            design.total_length_m, float(design.tendon_count), design.tendon_routing_radius_m,
            *task.target_m, task.position_error_max_m,
            matlab.double([[route.angle_rad for route in design.tendon_routes]]), nargout=7,
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

    def analyze_clearance(self, robot_ir: RobotIR, task: TaskSpec,
                          environment: EnvironmentSpec, model_result: ToolResult) -> ToolResult:
        """Conservative full PCC shape check against the shared window frame."""
        from tools.window_geometry import constrained_window, window_boxes, aperture_crossing
        import matlab
        self._check_environment(robot_ir, task, environment)
        window = constrained_window(environment, task)
        if robot_ir.sections != 1 or model_result.status != "pass":
            raise ValueError("CAPABILITY_MISSING: clearance requires a completed single-section PCC plan")
        boxes = window_boxes(window)
        # Numerical resolution, not a physical tolerance or optimization bound.
        max_spacing = min(0.001, robot_ir.body_radius_m / 4, window.thickness_m / 4)
        points, lower, sampled, index, box, spacing = self.eng.analyze_clearance(
            robot_ir.total_length_m, model_result.metrics["theta_rad"], model_result.metrics["phi_rad"],
            robot_ir.body_radius_m, matlab.double([centre + size for _, centre, size in boxes]),
            max_spacing, nargout=6)
        points = [list(map(float, row)) for row in points]
        i, j = int(index) - 1, int(box) - 1
        crossing = aperture_crossing(points, robot_ir.body_radius_m + float(spacing) / 2, window)
        return ToolResult(tool="analyze_clearance", status="pass", metrics={
            "predicted_minimum_clearance_m": float(lower),
            "sampled_minimum_clearance_m": float(sampled),
            "predicted_intersection": bool(sampled < 0),
            "predicted_clearance_violation": bool(lower < 0),
            "closest_location_m": points[i], "closest_sample_index": i,
            "closest_segment_index": min(robot_ir.segments - 1, int(i / (len(points) - 1) * robot_ir.segments)),
            "closest_obstacle": boxes[j][0], "sample_spacing_m": float(spacing),
            "sampling_bound_m": float(spacing) / 2, "body_radius_m": robot_ir.body_radius_m,
            "sample_count": len(points), **crossing,
            "window": window.model_dump(mode="json"),
            "comparison_context": model_result.metrics.get("comparison_context"),
            "fidelity": "low/geometric", "limitation": "PCC shape approximation; window only, no gravity, dynamics or floor analysis; negative lower bound alone is not proof of intersection",
        }, artifacts={"predicted_centerline_m": points})

    @staticmethod
    def _check_environment(robot_ir, task, environment):
        environment = environment or load_environment()
        if environment.environment_id != task.environment_id or environment.coordinate_frame != robot_ir.coordinate_frame:
            raise ValueError("Environment identity/frame mismatch")
        # M0/M1 are kinematic. Gravity and objects are intentionally not used;
        # no separate MATLAB environment file or implicit transform exists.

    def version(self):
        return str(self.eng.version(nargout=1))

    def close(self):
        self.eng.quit()
