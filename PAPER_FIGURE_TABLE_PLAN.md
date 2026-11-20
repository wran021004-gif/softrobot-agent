# Figure and table plan

The main narrative retains Figures 1--3 unchanged and concentrates the remaining simulation evidence into Figures 4--5. Figure 6 is reserved for the real-world experiment section.

## Main figures

| Figure | Main message | Main-text location |
|---|---|---|
| 1 | Softrobot-Agent architecture, Main Agent decision authority, PPRP, mathematical and physical evidence paths | Method overview |
| 2 | Eleven-task benchmark portfolio and four task families | Results 6.1 |
| 3 | Agent-directed research trajectories, including hypotheses, investigations, structure/control changes, and outcomes | Results 6.2 |
| 4 | Mathematical evidence and physical validation: implicit/FD consistency, independent passive checks, and the T07 M1/M2 structure--control audit | Results 6.3 |
| 5 | Architecture and resource ablation: four task-normalized heatmaps for mathematical operations, physical launches, Core requests, and token consumption | Results 6.5 |
| 6 | Real-world hardware experiments | Reserved in Section VII |

## Main tables

- **Table I:** task families, physical capabilities, and required-condition coverage.
- **Table II:** one unified method-by-task matrix. Methods are rows; T01--T10 and PHS-2D are columns. Each cell reports only the maximum known normalized constraint violation, with a dash and status when no complete task-level maximum exists. The bottom row reports task pass rate. Both Ours rows are bold.
- **Table III:** aggregate mathematical operations, physical operations, Core request records, and total tokens for the K/S configurations and FULL model snapshots. This table belongs to the architecture/resource ablation subsection.

## Figure 5 plotting rules

- Use the Figure 1 palette: Main Agent navy #26384B, mathematical teal #527F7B, physical slate #70849A, and structure/interaction ochre #B08A59.
- Each of the four panels uses the same eleven task columns and five method rows: historical GPT-6 Astra FULL, K−S−, K+S−, K−S+, and current GPT-5.6 Sol FULL (K+S+).
- Normalize each resource independently within each task by the largest value across the five methods. These are resource profiles, not performance scores.
- Raw eleven-task totals remain in Table III. Historical Astra tokens are estimates; current Sol tokens are a recorded lower bound; the K+S− T06 token entry is imputed.
- Use discrete solid-color swatches rather than gradients. Do not use radar charts or pool unlike resource units.

## Reserved real-world material

Section VII and Figure 6 are reserved for hardware platform, calibration, real-world task execution, quantitative measurements, and repeatability. No simulation result is substituted for a hardware result.
