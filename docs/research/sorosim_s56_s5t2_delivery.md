# S5.6 and S5-T2 research delivery

Source start: `963b86c242ba4226c716fedd53c6b26ffe627deb`, verified local and
remote on `feat/sorosim-matlab-nmpc`. Target worktree was clean. Upstream
SoRoSim is `24d573a3e864ffda87c42ee462a6ed620133cc7b` and remains untouched.

The authorized sequence is P1 numerical refinement, P2 fixed-design control
optimization, P3 independent physics, P4 separate direct/residual PPO, and P5
KKT/structural sensitivity. Each owns a new frozen Store grant. Historical
studies, failures and budgets remain sealed. No provider requests are authorized.

| Stage | Prospective ceiling | Evidence destination |
|---|---|---|
| P1 | 16/32, conditional 64: three integrations | `evidence/sorosim_s56/refinement/` |
| P2 | Three NLP attempts, three independent high-resolution checks | `evidence/sorosim_s56/codesign/` |
| P3 | Two complete physics evaluations, three local probes | `evidence/sorosim_s56/physics/` |
| P4 | Four stages, 262144 actions, four independent evaluations | `evidence/sorosim_s56/rl/` |
| P5 | Two base NLPs, two conditional perturbation NLPs | `evidence/sorosim_s5t2/` |

The frozen task/compiler/evaluator, physical model, 35 held physical commands,
36 original task samples, force bounds and acceptance thresholds remain the
authority. Integration substeps do not add physical control decisions.

## P1: completed numerical refinement

Execution source: `36d35a35`. MATLAB R2024a / Optimization Toolbox 24.1 and
the pinned source/MEX identities are preserved in the immutable Store export.
Initial preparation without MATLAB's existing Engine PYTHONPATH failed before
any scientific reservation; the installed Engine build path resolved it. MATLAB
and SSH require execution outside the Windows filesystem sandbox. Remote read
then verified the exact authorized starting SHA.

| Internal steps per held command | Complete roots | Terminal error (m) | Holding position (m) | Holding speed (m/s) | Worker time (s) |
|---|---:|---:|---:|---:|---:|
| 16 | 560 | .010718 | .024705 | .791913 | 111.466 |
| 32 | 1120 | .011242 | .025697 | .827020 | 140.116 |
| 64, conditional | 2240 | .011510 | .026199 | .844771 | 235.409 |

All three integrations complete the same 35 commands and 36 output samples;
all fail the unchanged sampled mathematical task. The maximum full implicit
residual is below 3.30e-12. Maximum absolute represented state rises from 631.0
to 634.4; rates are represented curvature rates, not Cartesian speed. Position
and full velocity-vector differences at every original sample and the five
specified time windows are in [the P1 summary](../../evidence/sorosim_s56/refinement/summary.json).
Three integrations used 486.991 worker seconds, zero physical steps, PPO
actions or provider calls. Eight focused refinement/equivalence checks passed.

The decreasing differences support numerical refinement of this fixed sequence,
but do not establish a rigorous continuous-time bound. The 16-to-32 velocity gap
exceeded .020 m/s and prospectively triggered the one authorized 64-step check.
Further refinement is stopped at this ceiling. Use 32 steps as an exploratory
independent validation grid with its measured 32/64 uncertainty; use four steps
only as a cost-controlled intermediate optimization transcription. A task pass
on that intermediate grid alone cannot establish higher-fidelity feasibility.
