# MATLAB analysis and PCC planning

Constructing `MatlabTools()` starts MATLAB and adds `matlab/` to its path.
Call `close()` in a `finally` block. Both methods consume DesignSpec and
TaskSpec and return ToolResult. MATLAB Engine exceptions propagate.
The adapter preloads Python's Expat before MATLAB to avoid a Windows DLL
collision when the downstream compiler parses the environment XML.

## M0: geometric screening

`MatlabTools.analyze_workspace(design, task)` calls `matlab/analyze_workspace.m`.
It checks robot_family and computes `norm(target_m) <= total_length_m`.
Only total_length_m participates numerically; all other design fields are
ignored. Only target_m is used from TaskSpec.

Metrics are target_reachable, target_distance_m, max_reach_m, reach_margin_m.
Unreachable targets return `DESIGN_INFEASIBLE`; unsupported families return
`UNSUPPORTED_ROBOT_FAMILY`. This remains a very cheap M0 geometric bound,
without PCC, tendon routing, dynamics, or actuation feasibility.

## M1: best-effort PCC reach planning

`MatlabTools.plan_pcc_reach(design, task)` calls `matlab/plan_pcc_reach.m`.
It accepts only tendon_driven_continuum with sections=1. The numerical inputs
are total_length_m (L), tendon_count (N), tendon_routing_radius_m (r_t),
target_m, and position_error_max_m. Segments and body_radius_m are ignored.

Coordinates match the compiler: base `[0,0,0]`, straight centerline +x,
cross-section y-z. `phi=atan2(tz,ty)` points toward the target's lateral
direction. Base MATLAB `fminbnd` searches theta in `[0,pi]` and compares the
two endpoints. This limits V1 to a simple non-looping bending branch.

The PCC tip is `[L*sin(theta)/theta, rho*cos(phi), rho*sin(phi)]`, with
`rho=L*(1-cos(theta))/theta`; the straight limit is `[L,0,0]`.
For `alpha_i=2*pi*i/N`, commands are
`l_i=L-r_t*theta*cos(alpha_i-phi)`, ordered tendon_0 through tendon_N-1.
Delta lengths are `l_i-L`.

Metrics: theta_rad, phi_rad, predicted_tip_m, target_position_m,
predicted_position_error_m, model_task_success, tendon_target_lengths_m,
tendon_delta_lengths_m, tendon_count, tendon_routing_radius_m. Vectors are
ordinary Python float lists. No artifact or control class is created.

`status=pass` means a finite prediction and positive finite commands were
produced. Exceeding the task tolerance sets model_task_success=false while
still returning commands. Only MuJoCo's validate_task decides final task success.

Failures are `UNSUPPORTED_ROBOT_FAMILY`, `UNSUPPORTED_DESIGN_CONFIGURATION`
(sections != 1), and `PCC_INVALID_COMMAND` (invalid dimensions/count,
nonfinite target/tolerance, negative tolerance, or invalid output lengths).
Handled failures have empty metrics.

## Fidelity and limitations

M1 is single-section PCC kinematics. It omits dynamics, gravity, stiffness/load,
and contact, and is neither PCS nor Cosserat. Continuous PCC length geometry
and segmented MuJoCo routing can disagree. Use M0 to screen grossly unreachable
targets and M1 to obtain an open-loop command; neither proves physical task
completion. Do not tune the design or target merely to reconcile their results.
