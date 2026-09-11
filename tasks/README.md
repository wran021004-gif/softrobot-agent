# Task packages

Frozen benchmark: reach_free. reach_window tooling is executable using
tests/fixtures/reach_window_dev, explicitly NON_CANONICAL / DEVELOPMENT_ONLY;
no approved window geometry exists and no benchmark has been registered.
Window geometry uses a fixed rectangular y-z aperture derived from EnvironmentSpec.
catch_drop, catch_ramp and stabilize_tip remain planned with no executable package
or evaluator. Their reserved components are rejected by environment compilation.

Each implemented package owns task.yaml, environment.yaml and a validated
MuJoCo representation. MATLAB receives shared semantic inputs through Python,
never an independent environment file. Agents may propose task/environment changes
under proposals/; they cannot modify official packages or benchmark membership.
