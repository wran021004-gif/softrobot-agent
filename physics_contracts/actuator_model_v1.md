# Actuator model — V1

Human-owned legacy surrogate contract. Each ordered spatial tendon receives a
MuJoCo position servo, unit gear, kp=1000 N/m and force range [-20,0] N. Controls
are target path lengths in meters. Negative force pulls; the upper bound prevents
pushing. Gains and force limits are physics/actuator-model constants from
legacy_v1_surrogate.yaml, not controller gains to be tuned implicitly.

The outer C1 open_loop_length controller supplies the same PCC target each step.
This is open-loop command execution even though the simulated actuator contains
a position servo. Without a command the runner disables actuation; zero ctrl would
incorrectly request zero cable length. The runner consumes a Controller protocol,
so a future approved controller can use time and qpos/qvel observations without
replacing the task evaluator. C0 passive exists; C2 and C3 remain planned.

Finite positive lengths and one command per correctly ordered tendon transmission
are required. Force-limited actuation does not guarantee length tracking. No motor
dynamics, validated compliance, cable slack/elasticity or actuator calibration has
been established. Introducing those assumptions requires Human scientific review.
