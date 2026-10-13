"""Replay one captured tension prefix at three fixed timesteps; no policy updates."""
import argparse
import json
from pathlib import Path
import time

import mujoco
import numpy as np

from experiments.rl_pilot.env import TensionEnv, NumericalFailure, STATE_SPEC, WARNINGS
from experiments.rl_pilot.train import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True, help="failure_episode_N.npz")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--integrator", choices=["implicitfast", "implicit"], default="implicitfast")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    with np.load(args.capture) as saved:
        tensions = saved["tensions"].copy()
        interval_state = saved["interval_start_state"].copy()
        pre_step = saved["pre_step_state"].copy()
    results, trajectories = {}, {}
    for dt in (0.0005, 0.00025, 0.000125):
        env = TensionEnv("direct", physics_dt=dt, trace_dir=args.output / str(dt), integrator=args.integrator)
        _, initial = env.reset(seed=17)
        rows = [[0, *initial["tip_m"], *initial["tip_velocity_m_s"], 0, 0]]
        error = None
        force_gap = 0.0
        for command in tensions:
            try:
                _, _, _, _, info = env.step(command / 4 - 1)
            except NumericalFailure:
                error = env.failure
                break
            force_gap = max(force_gap, float(np.max(abs(info["applied_tension_n"]-command))))
            rows.append([info["time_s"], *info["tip_m"], *info["tip_velocity_m_s"],
                         float(np.max(abs(env.data.qvel))), float(np.max(abs(env.data.qacc)))])
        np.savetxt(args.output / f"trajectory_{dt}.csv", rows, delimiter=",",
                   header="time_s,x,y,z,vx,vy,vz,max_abs_qvel,max_abs_qacc", comments="")
        trajectories[dt] = np.asarray(rows)
        results[str(dt)] = dict(integrator=args.integrator, physics_dt_s=dt, counts=env.counts, numerical_failure=error,
                                max_command_applied_gap_n=force_gap, final_sample=rows[-1])
    # Restore the complete state immediately BEFORE the captured failing step.
    env = TensionEnv("direct")
    env.reset()
    mujoco.mj_setState(env.model, env.data, pre_step, STATE_SPEC)
    before = float(env.data.time)
    mujoco.mj_step(env.model, env.data)
    restored = dict(before_time_s=before, returned_time_s=float(env.data.time),
                    warnings=[w.name for w in WARNINGS if env.data.warning[w].number])
    # Also restore the interval start and apply exactly the recorded last command.
    env = TensionEnv("direct", trace_dir=args.output / "interval_restore")
    env.reset()
    mujoco.mj_setState(env.model, env.data, interval_state, STATE_SPEC)
    env.k = len(tensions)-1
    env.previous_tension = tensions[-2].copy()
    mujoco.mj_forward(env.model, env.data)
    try:
        env.step(tensions[-1]/4-1)
        interval_restored = None
    except NumericalFailure:
        interval_restored = env.failure
    common = min(len(trajectories[0.00025]), len(trajectories[0.000125]))
    delta = trajectories[0.00025][:common, 1:7]-trajectories[0.000125][:common, 1:7]
    write_json(args.output / "result.json", dict(
        capture=str(args.capture.resolve()), trials=results, restore_integrator="implicitfast", restored_substep=restored,
        restored_interval=interval_restored,
        fine_pair_max_position_difference_m=float(np.linalg.norm(delta[:, :3], axis=1).max()),
        fine_pair_max_velocity_difference_m_s=float(np.linalg.norm(delta[:, 3:], axis=1).max()),
        common_samples=common, elapsed_s=time.perf_counter()-started,
        scope="fixed captured prefix only; finite dt agreement is not a convergence proof"))
    print((args.output / "result.json").read_text())


if __name__ == "__main__":
    main()
