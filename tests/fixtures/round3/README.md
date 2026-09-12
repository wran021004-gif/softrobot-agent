# TEST_ONLY Round 3 software fixtures

All bounds, gains, clipping values, periods, budgets and seed in policy.yaml are
synthetic test inputs. They have no Human scientific approval and cannot be used
on frozen reach_free. The grammar's human_approved flag exists solely to exercise
the authorization algorithm; it is isolated by TEST_ONLY policy and source paths.

contract.yaml references the existing reach_window_dev TaskSpec/EnvironmentSpec
without copying either. This is DEVELOPMENT_ONLY, not a benchmark. Production
grammar remains unchanged. Unit tests use an explicitly labelled model double;
opt-in integration tests run real MATLAB and MuJoCo with these test inputs only.
