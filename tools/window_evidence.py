"""Bounded window observations from MuJoCo collision geometry and contacts."""
import math
import numpy as np
import mujoco
from tools.window_geometry import window_boxes, aperture_crossing


class WindowEvidence:
    def __init__(self, model, window):
        self.window = window
        self.robot = [i for i in range(model.ngeom) if model.geom(i).name.startswith("capsule_")]
        self.obstacles = [model.geom(name).id for name, _, _ in window_boxes(window)]
        for name, centre, size in window_boxes(window):
            geom = model.geom(name)
            if (int(geom.type[0]) != int(mujoco.mjtGeom.mjGEOM_BOX) or int(geom.bodyid[0]) != 0
                    or not np.allclose(geom.pos, centre, rtol=0, atol=1e-12)
                    or not np.allclose(geom.size, size, rtol=0, atol=1e-12)
                    or not np.allclose(geom.quat, [1, 0, 0, 0], rtol=0, atol=1e-12)
                    or int(geom.contype[0]) != window.contype or int(geom.conaffinity[0]) != window.conaffinity):
                raise ValueError("Compiled window geometry differs from EnvironmentSpec")
        self.minimum = None
        self.closest = None
        self.contacts = {}
        self.samples = 0
        self.crossing = None
        self.ever_satisfied = False
        self.initial = None
        # Larger than any distance between the fixed frame and this rooted arm.
        self.distance_cutoff = 2 * sum(float(model.geom_size[i, 1]) for i in self.robot) + math.dist(window.position_m, [0, 0, 0]) + window.width_m + window.height_m + 2 * window.frame_width_m + window.thickness_m + 1

    def observe(self, model, data, time_s):
        self.samples += 1
        for i in self.robot:
            for j in self.obstacles:
                distance = float(mujoco.mj_geomDistance(model, data, i, j, self.distance_cutoff, None))
                if not math.isfinite(distance) or distance >= self.distance_cutoff:
                    raise ValueError("Window distance query did not return an uncensored finite distance")
                if self.minimum is None or distance < self.minimum:
                    self.minimum = distance
                    self.closest = {"robot_geom": model.geom(i).name, "obstacle_geom": model.geom(j).name,
                                    "time_s": float(time_s)}
        for c in data.contact:
            pair = (int(c.geom1), int(c.geom2))
            if pair[1] in self.robot and pair[0] in self.obstacles:
                pair = pair[::-1]
            if pair[0] in self.robot and pair[1] in self.obstacles and c.dist <= 0:
                names = (model.geom(pair[0]).name, model.geom(pair[1]).name)
                self.contacts[names] = self.contacts.get(names, 0) + 1
        points = []
        for i in self.robot:
            centre = data.geom_xpos[i]
            offset = data.geom_xmat[i].reshape(3, 3)[:, 2] * model.geom_size[i, 1]
            if not points:
                points.append((centre - offset).tolist())
            points.append((centre + offset).tolist())
        self.crossing = aperture_crossing(points, float(model.geom_size[self.robot[0], 0]), self.window)
        self.ever_satisfied |= self.crossing["aperture_constraint_satisfied"]
        if self.initial is None:
            self.initial = {"minimum_clearance_m": self.minimum, "obstacle_contact_occurred": bool(self.contacts),
                            **self.crossing}

    def summary(self):
        return {"scope": "robot capsules versus EnvironmentSpec window frame; floor excluded",
                "minimum_observed_robot_obstacle_clearance_m": self.minimum,
                "closest_pair": self.closest, "obstacle_contact_occurred": bool(self.contacts),
                "contact_count": sum(self.contacts.values()),
                "contact_pairs": [{"robot_geom": a, "obstacle_geom": b, "contact_samples": count}
                                  for (a, b), count in sorted(self.contacts.items())],
                "observation_samples": self.samples, "ever_aperture_satisfied": self.ever_satisfied,
                "initial_configuration": self.initial,
                **(self.crossing or {}),
                "limitation": "Discrete initial/pre-integration and final samples; contact_count counts contact points across samples, not unique impacts; no continuous collision guarantee"}
