# Task packages

Implemented: reach_free. Planned identifiers: reach_window, catch_drop,
catch_ramp, stabilize_tip. No executable package or evaluator is provided for
these future tasks. EnvironmentSpec reserves typed component names; all parameters
and laws beyond the existing plane environment require Human-approved contracts
before implementation. Reserved components are rejected by environment compilation.

Each implemented package owns task.yaml, environment.yaml and a validated
MuJoCo representation. MATLAB receives shared semantic inputs through Python,
never an independent environment file. Agents may propose task/environment changes
under proposals/; they cannot modify official packages or benchmark membership.
