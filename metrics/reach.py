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
        acceptance = task.window_acceptance()
        if acceptance.initial_robot_region == "before_window" and window_evidence.get("initial_side_of_wall") is None:
            raise ValueError("before_window acceptance requires initial whole-body side evidence")
        result.update(initial_required_side_satisfied=(acceptance.initial_robot_region == "unrestricted" or
                      window_evidence.get("initial_side_of_wall") == "before_window"),
                      no_forbidden_window_contact=not result["obstacle_contact_occurred"],
                      acceptance=acceptance.model_dump(mode="json"))
        result["task_success"] = bool(result["target_reached"] and result["aperture_constraint_satisfied"]
                                      and result["initial_required_side_satisfied"] and result["no_forbidden_window_contact"])
    return result


# Evaluator capability metadata; no duplicated metric values or thresholds.
evaluate_reach.supported_task_types = ("reach", "reach_window")
