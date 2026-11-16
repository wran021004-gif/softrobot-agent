# Phase 1 manuscript restructure

## Scope

Phase 1 reorganizes the manuscript using the already-pushed publication handoff. It does not wait for the future full-run Knowledge/Skill extension or the matched physical M1/M2 experiment. Figure 1 is unchanged.

## Structural changes

- Removed the standalone System Implementation chapter from the compiled manuscript.
- Merged registries, PPRP compilation, numerical routing, Main Agent/Reporter responsibilities, L0--L3, Knowledge/Skill, evidence storage, and independent physical evaluation into Method.
- Removed the duplicated agentic state-transition formulation from Problem Formulation; the research state/update now appears once in Method.
- Removed the empty Real-World Validation placeholder from the compiled manuscript. Hardware validation can be added when a complete hardware evidence package is available.
- Removed the repeated main-text task table; Figure 2 serves as the integrated portfolio and Appendix B retains detailed task metrics and protocol conventions.

## Scientific corrections

- The eleven-case FULL portfolio uses PHS-2D-7S.
- PHS-2D-9S is an independent ten-condition mechanism study.
- Corrected the nine-segment metrics to 11.155 mm / 3.068 mm / 0.1093.
- The 18 derivative pairs are six loading branches by three metrics along one shared modulus direction.
- The A/B/C matrix covers eleven tasks; C is historical FULL, and T03-B/T05-B are protocol deviations.
- Reporter, Knowledge/Skill, and Context studies are explicitly decision-only and are not counted as physical task successes.
- New cross-task Gateway Provider usage remains UNKNOWN. Local serialized-text token counts remain estimates and are not presented as actual usage.
- The matched physical M1/M2 replay is prepared but not executed; no empirical effect is claimed.

## Figure assets and validation boundary

- Committed seven vector PDF/SVG pairs for Figures 2–8, using normalized numeric and decision data already on GitHub.
- Figure 3 currently uses recorded nine-segment physical centerlines and ten signed-load metric curves; the native MuJoCo candidate-stage renders remain the only planned visual enhancement.
- Figure 1's original TeX blob was rechecked against the baseline and is unchanged.
- All seven PDF objects passed structure/xref/content-length checks; all SVG text bounds were checked, and detected Figure 3 axis-label overlaps were corrected.
- Static LaTeX labels/references and citation keys were checked; full pdfLaTeX/Overleaf compilation and page-by-page float/layout review remain for the Codex synchronization step.
- `OVERLEAF_SYNC_CODEX_PROMPT.md` specifies the safe sync and compile protocol.
