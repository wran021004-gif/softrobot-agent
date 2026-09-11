import math
from schemas.task_spec import TaskSpec


def evaluate_reach(tip_position_m, task: TaskSpec) -> dict:
    if task.task_type != "reach":
        raise ValueError("CAPABILITY_MISSING: only final positional reach evaluation is implemented")
    if len(tip_position_m) != 3 or not all(math.isfinite(v) for v in tip_position_m):
        raise ValueError("NONFINITE_STATE: invalid tip position")
    target = [float(value) for value in task.target_m]
    error = math.dist(tip_position_m, target)
    return {"tip_position_m": list(tip_position_m), "target_position_m": target,
            "position_error_m": error, "position_error_max_m": task.position_error_max_m,
            "task_success": error <= task.position_error_max_m}
