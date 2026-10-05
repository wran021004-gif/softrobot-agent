# Limited Milestone 5A closeout — 2026-10-05

Task A completed and stopped. The prepared `feedback-component-full-chunked`
entry point ran once, reusing the hash-checked local DLL and physical function.
Two nonzero-acceleration comparisons passed: residual differences zero,
relative Jacobian differences 5.0822e-21 and 3.2526e-19.

| Sequence | Update | command, s | maximum historical command difference, N |
| --- | ---: | ---: | ---: |
| original075 | 0 | 14.822429 | 2.693496 |
| original075 | 1 | 7.196228 | 2.096580 |
| original075 | 2 | 6.648804 | 1.205849 |
| reset075 | 0 | 12.430100 | 1.834190 |
| reset075 | 1 | 6.580685 | 1.969632 |

Each sequence retained its own state and previous plan. Commands were saved
before its emulated physics advance; historical commands were read afterwards
only for comparison. Timed optimization changes the selected commands, so these
are experimental controller results, not validation of historical backend outcomes.

`complete_command_s` surrounds `controller.command(...)`. `observation_s`
separately covers external state projection and motion/output construction;
configuration/setup and emulated propagation are separate. Their exact values
are in [the component record](../evidence/milestone5_successor_20261005/feedback_component.json).
The sum of observation and command is a component sum, not a directly measured
end-to-end physical-controller interval. Propagation is not automatically part
of physical command computation. All five measured commands exceed 10 ms.

The outer receipt charges 56.312 seconds and one workflow call against the existing
450-second allocation. No provider, complete forecast, compiler experiment or
independent backend ran. Five embedded diagnostic solves and 100 emulated steps
are recorded. All six protected M5 backend slots remain untouched.

No item failed or timed out. Full histories, screening economics, admission,
prospective backend validation and realtime remain unexecuted here. Milestone 5
remains open; this checkpoint establishes only the two comparisons and five
causal component updates. Task B uses a separate grant and stable controller.
