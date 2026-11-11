# Evidence audit notes for manuscript v0.1

## Repository snapshots inspected

- `wran021004-gif/softrobot-agent`
  - default branch: `main`
  - paper snapshot branch: `codex/paper-full-results-phase0-20261111`
  - paper snapshot HEAD inspected: `6a1e8ea21ee454b9f693361f460f2decb259f78e`
  - V2 development baseline referenced by the branch README: `mainline/research-harness-v2`
- `wran021004-gif/softrobot-demo-showcase`
  - paper-figure branch: `codex/paper-figures-spring-button-20261111`
  - button v1.1 branch: `codex/button-routing-designspace-v1-1-20261111`
  - button v1.1 HEAD: `16ce8a663aef30f1ef25d7801f4f7b948722d1db`

## Critical provenance distinctions

1. The nine-task showcase README explicitly says that the task demonstrations are engineering designs or existing experiments and are not all Main autonomous Studies.
2. M1 Main Full is a separate autonomous Study with 3/3 independent acceptance. Its historical trace spans Core commits `2c83f8...` and `7f034a...`, and includes user-authorized knot-limit changes.
3. P3 Main v1.2 is a four-segment/two-cell study with candidate `candidate_2915`. It has saved bilateral finite-time numerical responses, but no fresh independent Replay and no formal evaluator acceptance certificate.
4. The exported P3 figure set `fig03_p3_stiffness_*` in the showcase paper-figure branch uses the historical three-segment/one-cell P3 v1 trajectory (160,000 rows; stiffness ratio about 3.699). It is not the Main P3 v1.2 candidate_2915 result (four segments/two cells; stiffness ratio about 1.537).
5. Figure-eight is a nominal periodic cubic-spline quasi-static feedforward result, not closed-loop feedback tracking and not hardware validation.
6. PHS-2D demonstrates horizontal XY tip stabilization only; Z changes and no unloading/recovery record is available.
7. Button Press v1.1 is explicitly Codex-assisted engineering, not Main autonomous research. Final S4 outcome is FAIL: actual rope speed 27.832 mm/s > 25 mm/s and negative button travel exceeds the frozen lower-stop tolerance.
8. The P3 full-results summary reports 150/160 Provider requests. A saved live-status snapshot reports a different earlier request count; reconcile final counts from the original Store before final publication.
9. Ablations and three-backbone comparisons are plans in the current manuscript, not completed evidence.

10. M1 Main used five Native nonlinear task-capability analyses, two Direct-control analyses, and two local physical-response probes (tendon_0 failed; tendon_1 passed). The two full-grid requests were blocked by a contact-related applicability boundary.

11. The precise planned P3 ablation label is No-Pairwise-Interaction. The historical shorthand No-Coupling must not be interpreted as disabling a dedicated Coupled-Block solver, because execution of that solver is UNKNOWN; the recorded interact operations were finite-scale pairwise comparisons.
