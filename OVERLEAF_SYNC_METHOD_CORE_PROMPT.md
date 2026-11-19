# Codex task: sync the Phase-5 manuscript revision to the existing Overleaf project

Repository: \`wran021004-gif/softrobot-agent\`  
Source branch: \`paper/manuscript-method-core-20261119\`  
Target Overleaf project: \`https://latex.ustc.edu.cn/read/ckntrxqcwpmc#335124\`

## Objective

Update the existing Overleaf manuscript to match the GitHub source branch. This is a synchronization task only. Do not redesign, regenerate, replace, or re-import the architecture figure.

## Required procedure

1. Inspect the current Overleaf project and its Git remote/status before changing anything.
2. Fetch the source branch and compare it with the Overleaf working tree.
3. Bring over the manuscript files from \`paper/manuscript-method-core-20261119\`, including:
   - \`main.tex\`
   - \`sections/01_introduction.tex\`
   - \`sections/04_method.tex\`
   - \`sections/06_experimental_setup.tex\`
   - \`sections/07_results.tex\`
   - \`sections/09_discussion.tex\`
   - the three Figure 3--5 SVG masters and their LaTeX wrappers
   - the updated figure README and figure plan where appropriate.
4. Preserve the existing approved Figure 1 architecture SVG, its filename, its editable vector content, and the complete Figure 1 figure environment in the current Overleaf `sections/04_method.tex` (including its inclusion command, caption, and label) byte-for-byte. When synchronizing `sections/04_method.tex`, merge the surrounding Method changes from GitHub but retain the Overleaf-side Figure 1 block and its SVG inclusion path. Preserve any package/configuration lines in `main.tex` required by that SVG inclusion. Do not overwrite it with the older GitHub TikZ file `figures/fig01_research_framework.tex`. Do not overwrite it with the older GitHub TikZ file \`figures/fig01_research_framework.tex\`. Do not rename or move the existing architecture asset.
5. Keep Figure 2, Figure 6, and Figure 7 assets unchanged unless a path update is strictly required by the synchronized source. Do not regenerate their data.
6. Export the three new SVG masters to PDF for pdfLaTeX using Inkscape or another installed vector-preserving converter:
   - \`figures/fig03_agent_directed_research.svg\` → \`figures/fig03_agent_directed_research.pdf\`
   - \`figures/fig04_evidence_validation.svg\` → \`figures/fig04_evidence_validation.pdf\`
   - \`figures/fig05_structural_research_outcomes.svg\` → \`figures/fig05_structural_research_outcomes.pdf\`
   Preserve the SVG files as editable masters. Do not rasterize them.
7. Confirm that the three SVGs can resolve their relative image references to the existing files under \`figures/native/\`.
8. Compile \`main.tex\` with pdfLaTeX. Fix only synchronization, path, or compilation issues caused by the update; do not alter the approved architecture figure or invent new experiment data.
9. Verify that the compiled PDF contains Figures 1--7 in the intended order:
   - Fig. 1: existing approved architecture figure
   - Fig. 2: eleven-task benchmark suite
   - Fig. 3: Agent-directed research process
   - Fig. 4: mathematical and physical evidence validation
   - Fig. 5: integrated structural research outcomes
   - Fig. 6: A/B/FULL comparison
   - Fig. 7: research continuity
10. Report the exact files synchronized, whether Figure 1 remained unchanged, SVG-to-PDF export status, compilation result, and any remaining issue. Do not push or overwrite an Overleaf branch with force.

## Important boundaries

- This task is synchronization only; all scientific content and SVG source edits are already in the GitHub branch.
- Do not change task metrics, thresholds, or figure data during synchronization.
- Do not claim multi-random-seed results. The manuscript describes a standardized multi-task benchmark suite.
- Do not edit or replace Figure 1.
