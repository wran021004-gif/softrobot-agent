# Softrobot-Agent — authoritative TRO manuscript figure and table plan

This file is the single authoritative publication layout plan. The source of normalized numerical data is the paper_handoff directory. The existing Figure 1 artwork is unchanged. New results are rendered as editable native TikZ/PGFPlots sources in figures/, using the same semantic distinction between agent, mathematical evidence, and physical evidence.

## Central scientific argument

Physics-grounded agentic research transforms a physical hypothesis into a task-conditioned mathematical investigation, uses independent mathematical and physical evidence to make the next decision, and preserves reusable findings across tasks.

- C1, evidence-guided adaptive investigation: representative research trajectories (Fig. 5), passive mechanism change (Fig. 3), and task coverage (Fig. 2).
- C2, task-conditioned mathematical research: PPRP/M0–M3 (Fig. 1), local gradient consistency (Fig. 4), and physical comparisons.
- C3, evidence-grounded research continuity: Reporter (Fig. 7), Knowledge/Skill (Fig. 8), and context efficiency/coverage (Fig. 9).

## Main figure sequence

| Figure | Scientific role | Composed artwork | Evidence |
|---|---|---|---|
| 1. Physics-Grounded Agentic Research Framework | Method definition | Approved editable fig01_research_framework.tex; never redraw or replace | Section 4 |
| 2. Task Portfolio and Physical Coverage | Breadth across eleven task contracts | Native fig02_task_portfolio.tex condition atlas; existing MuJoCo assets may later supply matching morphology insets | fig02_task_portfolio.csv |
| 3. Mechanism-Guided Passive Design | Meaningful structural mechanism and actual physical response | Native fig03_phs2d_mechanism.tex: indexed research topology stages and signed-load response curves | PHS-2D-9S original Journal, fig03_phs2d_performance.csv |
| 4. Local Mathematical Consistency | Derivative correctness at a task-relevant operating point | Native fig04_gradient_validation.tex: three facet parity plots and signed-load discrepancy matrix | fig04_gradient_validation.csv |
| 5. Evidence-Guided Research Trajectories | Hypothesis/evidence-driven changes in research actions | Native fig05_research_trajectories.tex: PHS-2D-9S, T04, T07, T10; short evidence-to-action tracks | research_nodes/ and fig05_research_trajectories.csv |
| 6. Research-Mode Comparison | Whole-system capability vs A/B research modes | Native fig06_abc_comparison.tex: 11x3 status matrix and three physical-violation insets | fig06_abc_comparison.csv |
| 7. Reporter-Guided Decisions | Discriminative experimental planning and constraint awareness | Native fig07_reporter.tex: all six pairs and M1-C/P3-A examples | reporter ON/OFF pair and clip data |
| 8. Knowledge and Skill in Research Decisions | Independent experience resource effects | Native fig08_knowledge_skill.tex: E1 historical utilization and later-checkpoint decision quality | original E1 and KS16 decision data |
| 9. Hierarchical Context | Cost, decision quality, and evidence coverage | Native fig09_context.tex: two historical provider-input pairs and six task-level reconstructed-input pairs | E2/E2-R2 and cross-task context data |

All eight result artworks are vector TeX inputs. Figure 3's current upper progression is a topology and decision index; it does not pretend to be a metrically accurate 3-D render. Replacement or augmentation with native MuJoCo common-camera screenshots is a separate visual improvement. Figure 4 currently shows validated derivative data; do not insert a hypothetical fixed-input/re-optimized comparison until matched physical evaluations exist.

The planned complete 11-task Knowledge x Skill factorial research studies will eventually replace or augment the decision-only component view only after their actual task outcomes and process traces are available. The current manuscript is complete without attributing future outcomes to those runs.

## Main text tables

Only Table I remains in the main text: canonical task names, morphology (flexible segments / tendons), and required-condition counts. Task outcome values are primarily displayed in Figures 2–6 and Appendix B. A/B/C statuses, Reporter pairs, K/S cells, and context input/quality are not duplicated as long main-body tables.

- Appendix A: A/B/C task-mode definitions and resource measurement scope.
- Appendix B: detailed eleven-task physical metrics; PHS-2D-9S separately.
- Appendix C: Study identities and evidence layers, including 7S versus 9S.
- Appendix D: Reporter, Knowledge/Skill, and context replay protocols/rubrics.
- paper_handoff: complete normalized numeric and evidence/action tables.

## Uniform publication style

- White background, no rounded cards, shadows, or decorative gradients.
- Thin hairline rules, consistent sans-serif figure labels, serif journal body.
- Deep navy #26384B for Main Agent; muted teal #527F7B for mathematical evidence; slate blue #70849A for physical evidence; ochre #B08A59 for design changes; forest green #557663 for verified pass; muted brick #A35D55 for violated constraints; neutral gray #929BA4 for reference and baseline.
- Small multiples, paired data, shared figure legends, direct metric labels, and task-specific units.
- Use native TikZ/PGFPlots where possible; include editable source alongside PDF compiled by IEEEtran.
- Missing/qualification-limited measurements must remain visually distinct from measured zero.
- PHS-2D-7S belongs to the original eleven FULL tasks; PHS-2D-9S is an independent mechanism Study.
- No pooled cross-task means of heterogeneous raw m/rad/N metrics, fabricated confidence intervals, or invented physical effects.

## Future updates without blocking the current manuscript

1. Replace the indexed topology strip in Fig. 3 with native, common-camera material and tendon-route renders once generated from the nine-segment original models.
2. Add the T07 three-mode fixed-input/re-optimized comparison when matched complete physical evaluations have been performed; do not use current all-UNKNOWN rows as physical data.
3. On completion of the end-to-end 11-task Knowledge/Skill study matrix, update Fig. 8 from decision replays to full research outcomes, retaining earlier studies as supplementary evidence.
4. Add hardware validation only if actual platform/protocol/measurement records support it.
5. Compile IEEEtran, check all labels, review two-column floats and panel fonts, and synchronize to Overleaf only after build passes.

The current figures are generated from the numerical handoff already committed to the paper branch. They should be refreshed if data are superseded, not manually manipulated to improve presentation.
