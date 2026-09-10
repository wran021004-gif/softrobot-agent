from pathlib import Path

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

    def close(self):
        self.eng.quit()
