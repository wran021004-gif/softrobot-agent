"""Shared axis-aligned window geometry derived solely from EnvironmentSpec."""
import numpy as np
from schemas.environment_spec import Window


def window_boxes(window):
    """Return (name, centre, half size) for four disjoint frame bars, in SI."""
    x, y, z = window.position_m
    w, h, b, t = window.width_m / 2, window.height_m / 2, window.frame_width_m, window.thickness_m / 2
    return [
        (window.name + "_left", [x, y - w - b / 2, z], [t, b / 2, h + b]),
        (window.name + "_right", [x, y + w + b / 2, z], [t, b / 2, h + b]),
        (window.name + "_bottom", [x, y, z - h - b / 2], [t, w, b / 2]),
        (window.name + "_top", [x, y, z + h + b / 2], [t, w, b / 2]),
    ]


def constrained_window(environment, task):
    windows = [obj for obj in environment.objects if isinstance(obj, Window)]
    if len(windows) != 1 or task.task_type != "reach_window":
        raise ValueError("CAPABILITY_MISSING: reach_window requires exactly one axis-aligned window")
    window = windows[0]
    if task.environment_id != environment.environment_id:
        raise ValueError("Environment identity mismatch")
    if not 0 < window.position_m[0] - window.thickness_m / 2 or task.target_m[0] <= window.position_m[0] + window.thickness_m / 2:
        raise ValueError("Window must lie ahead of the base and target beyond its far face")
    return window


def aperture_crossing(points, radius, window):
    """Check every polyline segment inside the slab, including backtracking.

    Radius erodes the rectangular opening. Clearance against frame boxes is a
    separate test. Caller accounts for PCC sampling error by inflating radius.
    """
    points = np.asarray(points, dtype=float)
    centre = np.asarray(window.position_m)
    near, far = centre[0] - window.thickness_m / 2, centre[0] + window.thickness_m / 2
    crosses = bool(points[0, 0] < near and points[-1, 0] > far)
    margins = []
    for a, b in zip(points[:-1], points[1:]):
        dx = b[0] - a[0]
        if abs(dx) < 1e-15:
            if not near <= a[0] <= far:
                continue
            lo, hi = 0., 1.
        else:
            u, v = sorted(((near - a[0]) / dx, (far - a[0]) / dx))
            lo, hi = max(0., u), min(1., v)
            if lo > hi:
                continue
        for p in (a + lo * (b - a), a + hi * (b - a)):
            margins.append(min(window.width_m / 2 - abs(p[1] - centre[1]),
                               window.height_m / 2 - abs(p[2] - centre[2])) - radius)
    minimum = min(margins) if margins else None
    return {"crosses_window_slab": crosses, "aperture_margin_m": minimum,
            "aperture_constraint_satisfied": bool(crosses and minimum is not None and minimum >= 0)}
