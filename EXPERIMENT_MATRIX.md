# Experimental matrix and interpretation rules (v0.3)

| Study / test | Main comparison | Contribution |
|---|---|---|
| P3 Full | Historical integrated system | C1 + C2 + C3 |
| P3 No-Math | Full vs no optional math operations | C2 overall |
| P3 No-Intent-Projection | Adaptive intent-to-problem projection vs fixed templates | C2-A |
| P3 No-Pairwise-Interaction | Full vs no finite-scale `interact` | C2-C |
| P3 No-Knowledge | Full vs no domain Knowledge/Skill retrieval | C3 |
| P3 Fixed-Plan | Full vs fixed research route | C1 |
| P3 One-shot Plan | Optional follow-up if Full vs Fixed-Plan warrants it | C1 |
| Reporter | Six paired historical snapshots, ON/OFF | C3 |
| M1 | Full vs No-Automated-Physical-Probe pilot | C1 / active-control transfer |
| Backbone | DeepSeek Flash, GPT-5.6 Sol, GPT Astra on M1 Full | Model portability |
| Tracking | Light mathematical transfer validation | C2 task transfer |
| Math correctness | Independent numerical references | C2 numerical validity |

## Important distinctions
- No-Math removes mathematical research but retains adaptive research decisions.
- Fixed-Plan retains mathematical research but removes evidence-driven replanning.
- No-Intent-Projection retains mathematical operations and task contracts; it replaces adaptive custom problem construction with fixed templates.
- No-Pairwise-Interaction disables only the finite-scale four-point interaction operation.
- No-Math and No-Pairwise-Interaction are nested because No-Math also removes `interact`.
- No-Automated-Physical-Probe disables the registered automated probe method, not every possible manually constructed physical test.
