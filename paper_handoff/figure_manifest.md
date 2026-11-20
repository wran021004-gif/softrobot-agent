# Figure and table handoff

Common style: white background, straight edges, no shadows, gradients, rounded cards or dashboard tiles. Use Arial/Helvetica labels at 8--9 pt at final size. Export SVG and PDF. Palette: Main Agent #26384B; Mathematical Evidence #527F7B; Physical Evidence #70849A; structure modification #B08A59; verified pass #557663; failure #A35D55; baseline #929BA4; auxiliary lines #D9DEE2. Labels and line styles must also distinguish groups.

Figures 1, 2, and 3 are frozen and must not be modified. Figure 2 is included in Results 6.1; it is not a method or setup-only figure.

## Figure 4 — Mathematical Evidence and Physical Validation

Panels A--C preserve the existing implicit/finite-difference comparison, relative-discrepancy plot, and ten-condition physical validation from the independent PHS-2D study. Panel D adds the T07 audit: one complete M1_B fixed-input pair (d0 1.996961 FAIL; d1 2.116883 FAIL; ΔM1 +0.119921), plus four independently evaluated d1 re-optimized PASS endpoints. The four d0 optimizer runs are non-converged; no ΔM2 is plotted or claimed. The T07 data source is branch paper/t07-m1m2-c1-trace-20261118 at commit 206886ff064722eb84f8e85a1509bd9d08d57923.

## Figure 5 — Architecture and Resource Ablation

Four heatmaps use identical task columns (T01--T10, PHS-2D) and method rows (Astra FULL, K−S−, K+S−, K−S+, Sol FULL). Panels show charged mathematical evaluations, physical launches, Core request records, and total tokens. Each panel is normalized per task across methods. Raw totals are in Table III. Astra tokens are estimated; Sol tokens are a recorded lower bound; K+S− T06 is imputed. The K/S source is the full_vs_kplus_splus_20261120 archive on branch codex/paper-evidence-audit-20261114.

## Tables

- Table I: task family and condition coverage.
- Table II: unified task-wise maximum known normalized constraint violation, methods by row and tasks by column, task pass rate at the bottom.
- Table III: aggregate resource totals for the K/S and FULL configurations.

## Figure 6 — Real-world experiments

Reserved for hardware platform, calibration, real-world execution, measured task outcomes, and repeatability. Do not populate with simulation results.
