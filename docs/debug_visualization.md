# Optional reach observability

The default `python examples/run_reach_pipeline.py` stays headless. Add `--debug`
to save MATLAB PCC figures, a separate trajectory and five trajectory plots under
`runs/<run_id>/debug/`. Add `--visualize` to display MATLAB figures and the passive
MuJoCo viewer. Both flags can be combined. MATLAB display lives for the Engine
session; the viewer closes when the unchanged finite simulation completes. Viewer
pacing affects wall time only. Camera/UI input cannot become a simulation command.

Every debug JSON includes DEBUG_ONLY and NON_CANONICAL labels; every plot has a
visible label (Python PNGs also include metadata). `status.json` records optional
failures. Debug files are hashed by the existing final run manifest, but the factual
evidence admission API rejects `debug/` references. Gate, diagnostic, optimizer and
Skill code never reads these files. No timestep values enter trace.jsonl.

`trajectory.json` follows `schemas/json/debug_trajectory.schema.json`. After each
existing mj_step it copies time/qpos/qvel/commands/tendon lengths/forces. Current tip
kinematics run on an independent MjData buffer. Tendon lengths and forces are the
untouched work arrays from that step's dynamics evaluation; they are not refreshed
at the new qpos. The legacy final mj_forward still supplies canonical final metrics.
Consequently the final debug tendon/force sample need not equal the final canonical
work arrays. This timing distinction must be retained when inspecting plots.

The viewer receives the exact executed MjModel and MjData. MuJoCo's sync operation
is bidirectional even with `state_only=True`; the adapter preserves full MjData,
model arrays and numerical options across launch/sync/close, discarding GUI writes.
It adds no mj_step or mj_forward call on the executed data. See the upstream
[passive viewer contract](https://mujoco.readthedocs.io/en/stable/python.html#passive-viewer).
Tests inject control, pose, force, warm-start, gravity, timestep and solver changes,
including a sync exception, and require identical complete ToolResults.

MATLAB's `plot_saved_pcc.m` reads a labeled `matlab_inputs.json` assembled from saved
run snapshots/results. It draws the base, target/tolerance, predicted centerline
and tip, plus saved clearance/window geometry when present. Numerical MATLAB
tools and their ToolResults are unchanged. Engine arguments carry paths directly;
no path is interpolated into MATLAB code. Headless tests exercise Windows paths
with spaces and Chinese MATLAB output directories. The current MuJoCo Windows
native file loader still requires an ASCII model path; that pre-existing limitation
is outside the plotting adapter.

Matplotlib is needed only for debug trajectory plots; rendering uses Agg without a
desktop. For restricted Windows profiles, set MPLCONFIGDIR to a writable directory
such as `D:\softrobot-agent\runs\.matplotlib`. Tests use fake viewers and never
require a desktop; optional retained validation can separately exercise the real GUI.
