import math
from schemas.task_spec import TaskSpec


def evaluate_reach(tip_position_m, task: TaskSpec, window_evidence=None) -> dict:
    if task.task_type not in ("reach", "reach_window"):
        raise ValueError("CAPABILITY_MISSING: only final positional reach evaluation is implemented")
    if len(tip_position_m) != 3 or not all(math.isfinite(v) for v in tip_position_m):
        raise ValueError("NONFINITE_STATE: invalid tip position")
    target = [float(value) for value in task.target_m]
    error = math.dist(tip_position_m, target)
    result = {"tip_position_m": list(tip_position_m), "target_position_m": target,
            "position_error_m": error, "position_error_max_m": task.position_error_max_m,
            "task_success": error <= task.position_error_max_m}
    if task.task_type == "reach_window":
        if window_evidence is None:
            raise ValueError("Window evaluation requires observed constraint evidence")
        result.update(target_reached=result["task_success"],
                      aperture_constraint_satisfied=window_evidence["aperture_constraint_satisfied"],
                      obstacle_contact_occurred=window_evidence["obstacle_contact_occurred"])
        result["task_success"] = bool(result["target_reached"] and result["aperture_constraint_satisfied"]
                                      and not result["obstacle_contact_occurred"])
    return result
