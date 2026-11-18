# Codex task: synchronize revised TRO manuscript and visually review agent traces

Authoritative GitHub branch: origin/paper/manuscript-phase2-revision-20261118.
Existing Overleaf Git remote: overleaf (latex.ustc.edu.cn), main. The previously verified Overleaf commit was 1f158b9d14d3bd7bd98f8bf798ffef032181080a. Fetch and check the actual current remote HEAD first; do not assume it is still that commit.

## Goal
Synchronize the new publication-style manuscript and its source-backed figures into the EXISTING Overleaf project. This revision is not a generic plot swap: it uses integrated Agent Observation / Decision / Action / Native MuJoCo Structure / Quantitative Evidence traces. The main results are now:
- Fig. 1: existing approved framework (frozen, preserve original Overleaf PDF, SVG, entire figure environment/caption/label verbatim).
- Fig. 2: native structure evolution PHS-2D and T07, with short hypothesis/action/outcome annotations.
- Fig. 3: native T04/T10 research traces with agent decision excerpts, action, physical states and quantitative curves.
- Fig. 4: native T09 contact execution and force/depth curves.
- Fig. 5: original gradient validation vector PDF.
- Fig. 6: Reporter and K/S vector PDF.
- Fig. 7: Context vector PDF.
- Table I: physical task portfolio (booktabs, grouped task rows).
- Table II: 11-task A/B/FULL comparison (booktabs, grouped task rows).

## Safe synchronization
1. Inspect local git status, worktrees, GitHub branch HEAD, existing Overleaf main HEAD and diff. Protect uncommitted work. No force-push, reset, clean or destructive overwrite.
2. Fetch the source branch and selectively reconcile the compiled sections and appendices, two table TeX files, three new figure TeX files, 16 original native PNGs under figures/native/, and three renamed vector PDF/SVG pairs.
3. Preserve the approved Overleaf Figure 1 PDF/SVG byte-for-byte and its full existing figure environment. Do not use the GitHub older TikZ Figure 1.
4. In the compiled reader-facing manuscript use PHS-2D, not 7S/9S suffixes. Keep exact study identities only in internal source metadata. Do not merge distinct studies' numeric metrics.
5. Keep existing archives and unused files intact. Do not upload the whole runs/ directory, source Store or large video archive.
6. Maintain a strict IEEEtran / TRO style: Times-like IEEE body, booktabs tables with no vertical rules or shading, no card backgrounds, readable 8-9 pt figure labels at final width, concise captions, no overlapping labels.

## Mandatory visual inspection
- The new Figure 3 trace is the priority. Its three-column tabularx layout has text inside cells; verify no row-break parsing errors, no overflow, and no unintended text compression. If needed, replace the trace layout with aligned minipages or a two-figure arrangement. Preserve exact scientific content and agent/action/physical result correspondence. Do not revert to a simple two-photo montage.
- Verify T04's early route is not falsely shown as a complete physically accepted baseline. Verify T10's three robot images are states of one fixed morphology, not different designs.
- Figure 2 must show the actual PHS and T07 native renders, with a consistent camera within each study. Keep action/evidence labels visually legible; remove any annotation that cannot be grounded in archived decisions.
- Figure 4 should clearly show the button contact and depth/force curve at publication print size.
- Table I is wide: if needed abbreviate long task names to canonical task IDs plus a short task descriptor, or use tabularx p-columns and slightly smaller font; avoid resizebox shrinkage below readable print size.
- Table II: compare status categories correctly. Distinguish valid failures, incomplete, qualification failure. Mark T03-B protocol variant. Do not imply repeated randomized trials or confidence intervals.
- Review all captions and references, including renumbered Figure 2-7 labels. Ensure no old Figure 2-8 results PDF remains compiled accidentally.
- Validate 30 required conditions, T04 RMSE 0.688 mm, T07 4/4, T09 0.5 s hold, T10 3/3, PHS-2D 10/10, and mathematical audit 18 pairs/0.1191%. Keep each metric tied to its correct study.
- Compile pdfLaTeX + BibTeX + repeated pdfLaTeX. Inspect every page and figure at 100% and 200%. Fix missing graphics, undefined references, overfull boxes, float placement, table overflow, and inconsistent fonts. Report the final page count.
- The current GitHub revision was authored remotely and has NOT been compiled here; you must actually compile it locally before claiming success.

## Delivery
After local compilation and visual review, commit only the intended changes on the existing Overleaf main history, push by normal fast-forward and verify with git ls-remote. Report GitHub source SHA, Overleaf commit SHA, compile result, pages, any remaining visual issues, and confirmation that approved Figure 1 was preserved.
