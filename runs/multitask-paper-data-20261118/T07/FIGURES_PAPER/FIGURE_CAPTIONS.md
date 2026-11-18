# T07 figure drafts

## T07_final_physical_constraints

**English caption.** Independent physical outcomes for one shared morphology under all four original T07 conditions. (a) Maximum holding-position error for the three reach-and-hold conditions and maximum tool-position error for M5. (b) Maximum holding speed and geometric tendon speed; holding speed is not a metric of the M5 pose task. (c) Maximum M5 tool-axis angular error. Short dashed marks show the corresponding original hard limits. The same hardware passed all 35 original constraints. Different task quantities are displayed with their original units and limits; no cross-task average is computed. All values are drawn from archived independent physical replays of `codex-expert-T07-20261113`.

**中文用途。** 最终共享形态的四工况量化结果。位置、速度与轴向误差分开量纲；M5 没有 holding speed 指标，显示 n/a。图中位置含两类任务定义，不能据柱高声称 M5 比 Reach 更好。验收全部通过但裕量接近目标约束边界，不能解释为大裕量鲁棒性。

**Files.** `T07_final_physical_constraints.png`, `.svg`; exact plotted values and original limits in `../FIGURE_DATA/T07_final_physical_constraints_plotdata.csv`; source references and plotting command in `../FIGURE_DATA/SOURCE_PROVENANCE.json`.

## T07_evidence_driven_research

**English caption.** Archived finite-budget diagnostics underlying T07 design and control decisions. (a) Condition A evaluated on five tested morphology variants: the ellipse-root design at a 14.1 mm routing radius, a circular root at the same radius, a 1 mm longer root, distributed length increases, and the final circular-root design at the original legal 14 mm radius. Root circularization reduced the remaining diagnostic conflict; the longer designs did not resolve it. (b) On the final unchanged hardware, condition C retained positive diagnostic excess from its historical control initialization; reoptimization from the current condition-A schedule found a feasible diagnostic proxy, subsequently confirmed by an independent original C replay. Positive values denote a violated native proxy; negative values indicate proxy margin. Points are deliberately unconnected: initialization, control resolution, and finite budgets differed. These diagnostics are neither independent physical acceptance nor an isolated causal ablation. The final independent outcomes are reported in the companion physical-constraints figure.

**中文用途。** 把“继续调控制→改根截面→否决加长→改合法布线半径”和“共享硬件不变、改变 C 控制初始化后重新优化”分为两个清晰科学发现。A panel 只比较 A，不把 B/C/M5 混成一条曲线；C panel 是同一最终硬件上的控制路线变化。原始公开假设保留在 `agent_decision_timeline.csv` 的 `recorded_rationale_quote`，本图文字是整理归纳。

**Files.** `T07_evidence_driven_research.png`, `.svg`; per-point raw references, exact values, control schedule settings, solver termination, budgets, and scope in `../FIGURE_DATA/T07_evidence_driven_research_plotdata.csv`.

## Table

`TABLE_T07_FINAL.tex` has six booktabs columns, no cell fills or vertical rules. Position definitions differ between Reach and M5 and are stated beneath the generated tabular source. Missing quantities are `--`. Values are rounded only for display; all exact raw values are retained in CSV.

## Attribution and production

The archived actor is Codex expert/surrogate (`codex_surrogate_main`), not a verified Main SDK/Provider run. The plots use Arial 8–8.5 pt, 7.16-inch two-column width, white backgrounds, thin axes, and the agreed semantic palette. PNG exports are 600 dpi; SVG retains editable text. No robot rendering, optimization, integration, new experiment, or source/XML modification occurs in this plotting script.
