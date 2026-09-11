# MATLAB model tools

MatlabTools lazily starts MATLAB; the module preloads Python Expat before Engine
DLLs for Windows compatibility. Close it in finally. analyze_workspace and
plan_pcc_reach accept RobotIR, TaskSpec and EnvironmentSpec; legacy DesignSpec
inputs go through the shared compiler. Environment identity/frame are checked;
M0/M1 need no gravity/contact parameters because those effects are omitted.

M0 tests norm(target)<=IR.section.length_m. M1 retains the existing fminbnd
search and endpoint comparison on theta in [0,pi], with phi=atan2(tz,ty).
RobotIR routing angles determine tendon command order. See physics_contracts/
coordinate_frames.md, tendon_driven_pcc_v1.md and tendon_length_mapping_v1.md.

M1 pass means a finite prediction and positive finite commands. Predicted tolerance
failure is separately reported as model_task_success=false; MuJoCo still executes.
Only the canonical actual-tip evaluator decides final success. Shared IR mechanics,
segment count, body radius and environment gravity/objects are intentionally unused
by these kinematic models. Engine errors propagate and the Harness records them.
Spec/IR validation may raise before a numerical call; no unsupported physics is guessed.

analyze_clearance consumes the completed PCC plan and the same RobotIR, TaskSpec
and EnvironmentSpec. Python derives four box bars through window_boxes and passes
their centres and half sizes to matlab/analyze_clearance.m. MATLAB samples the
entire PCC arc (spacing <= min(1 mm, body radius/4, thickness/4)), computes signed
box distance minus body radius, and subtracts half the arc spacing for a conservative
continuous-shape clearance bound. Sampled intersection and uncertain negative bound
are distinct. Closest location/segment/bar and sampled centreline are retained.
The aperture check clips every centreline segment against both slab faces and
erodes the opening by radius plus sampling bound. It rejects routes around the frame.
This is low/geometric PCC analysis, not a dynamic collision certificate; floor and
gravity are excluded. Tool pass denotes completed analysis. Screening never prevents
the Harness from collecting physical execution evidence.

Future actuation, stiffness, equilibrium and dynamics analyses exist
only as PLANNED manifests, with no fake numerical functions.
