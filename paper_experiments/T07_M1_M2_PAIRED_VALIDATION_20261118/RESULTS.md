# Results and reproduction

| Required condition | M1 baseline → modified: physical `gmax` | M2 baseline | M2 modified: physical `gmax` | ΔM1 | ΔM2 | Δd1,reopt |
| --- | --- | --- | --- | ---: | ---: | ---: |
| M1_A | Original d0-bound input not found | Iteration limit | −0.010000 PASS | — | — | — |
| M1_B | 1.996961 FAIL → 2.116883 FAIL | Line-search numerical failure | −0.010000 PASS | +0.119921 | — | −2.126883 |
| M1_C | Original d0-bound input not found | Iteration limit | −0.010006 PASS | — | — | — |
| M5 | Original d0-bound input not found | Iteration limit | −0.010000 PASS | — | — | — |

At M1_B the same tension reduced maximum geometric tendon speed from 74.924 to 45.381 mm/s, but worsened maximum holding/terminal error from 8.089 to 31.169 mm. The active worst constraint therefore shifted from tendon speed to position; the modified structure **did not improve** the worst fixed-input constraint. Reoptimized control on the modified structure achieved the archived M1_B independent PASS. This is evidence of the control change **within d1**, not a measured M2 benefit of d1 over d0. Four successful d1 endpoints plus four finite d0 failures do not prove d0 is infeasible.

Reused four exact d1 optimizer records and four d1 independent evaluator records, plus one exact original baseline input. Added four d0 optimization attempts (6,528 internal rollouts; 3,916,800 MuJoCo steps) and two independent M1_B replays (600 steps each). The historical ledger lists ceilings of 300 charged math evaluations and 100 independent physical launches; adding four and two to the archived 16 and 5 stays within those ceilings. The supplement uses the frozen Core kernels and a separate output directory, not the original Store ledger. No FULL Study or Provider run was added.

- `paired_results.csv`: one row per required condition, missing and nonconverged states explicit.
- `cell_results.csv`: per-arm observations, optimizer termination and numerical-only diagnostics.
- `raw_constraint_metrics.csv`: original metrics, SI units, thresholds, constraint direction and row-level PASS/FAIL.
- `t07_m1_m2.svg` and `t07_m1_m2.pdf`: the M1 point-line contrast and all available required-case physical endpoints. No line or imputed zero for the missing M2 arm.

From this directory, with Python 3.11+ and an unchanged copy of the historical archive:

```sh
python analyze.py <archive-root> --output <check-dir>
python plot.py --directory <check-dir>
```

For a fresh physical reproduction, use the frozen Core checkout and environment from the archival `ENVIRONMENT_LOCK.json`. Give the runner an empty, separate output directory; do not point it at the shipped results. This launches two independent physical replays and four optimizer attempts and may take several minutes. Numeric records can be compared by constraint values and status; elapsed-time fields are not deterministic.

```sh
python run_missing.py <archive-root> <frozen-core-checkout> <fresh-runs-dir> M1 M1_A M1_B M1_C M5
python analyze.py <archive-root> --runs <fresh-runs-dir> --output <check-dir>
```
