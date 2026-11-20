# Figure and table plan

The current manuscript uses eight main figures and one supplementary resource figure. Figures 1--3 are retained as the established narrative entry; the remaining figures are organized to separate physical capability, mathematical evidence, architecture ablations, and context management.

## Main figures

| Figure | Main message | Evidence / source |
|---|---|---|
| 1 | Softrobot-Agent architecture and evidence flow | Frozen architecture artwork |
| 2 | Eleven-task benchmark portfolio and task-family coverage | Benchmark task registry and required-condition data |
| 3 | Agent-directed research decisions | Representative research traces; Main Agent retains decision authority |
| 4 | Mathematical sensitivity consistency and independent physical validation | Eighteen implicit/FD pairs and ten signed-loading checks from the independent PHS-2D structural-design study |
| 5 | Structural research outcomes and structure/control interaction | Independent PHS-2D structural-design study plus T07 M1/M2 comparison |
| 6 | LLM-only / Direct Tools / Ours comparison across eleven tasks | Status and required-condition coverage matrix; numeric maximum violation is in Table II |
| 7 | Reporter and Knowledge/Skill component ablations | Six matched Reporter pairs, original K/S 2x2 replay, supplemental five-dimensional review |
| 8 | Hierarchical context management | Historical token/input pairs and cross-task decision-quality/evidence-recall replay |

## Supplementary figure

| Figure | Main message | Evidence / source |
|---|---|---|
| S1 | Cross-model research workload profile | Historical GPT-6 Astra FULL vs current GPT-5.6 Sol FULL/K+S+; four paired task-wise resource panels |

## Main tables

- **Table I:** benchmark task families, required conditions, and portfolio coverage.
- **Table II:** maximum known normalized constraint violation for each task/method, outcome status, evaluated/required coverage, and total task pass rate.

## Plotting rules

- Use the restrained navy/teal/slate/brick/ochre palette established by Figure 1.
- Use a status matrix for Figure 6; do not repeat the numeric violation magnitudes already reported in Table II.
- Use separate small multiples for the four resource metrics in Supplementary Figure S1; do not use radar charts because the metrics have different units and scales.
- Keep decision-level Knowledge/Skill, Reporter, and context results separate from physical task-violation results. They do not have a physical maximum-violation value.
- Keep the benchmark PHS-2D instance distinct from the independent PHS-2D structural-design study in all captions and text.
