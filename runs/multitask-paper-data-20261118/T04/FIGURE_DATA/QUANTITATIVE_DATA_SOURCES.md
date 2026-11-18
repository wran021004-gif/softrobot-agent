# T04 quantitative figure

Figure: T04_figure_eight_path_and_error.png / T04_figure_eight_path_and_error.svg

T04: final independent 22 s native execution and the original timed figure-eight reference. The planar projection shows both lobes; the error uses all three world coordinates. Reference values are arithmetic evaluation of the original integrated quintic phase-ramp definition, not a new optimized path. The dashed error line is the 6 mm instantaneous bound; original RMSE is 0.687853 mm and maximum error 1.020664 mm. The incomplete earlier NMPC comparison is not plotted as a completed failure.

Data: D:\softrobot-agent\runs\multitask-paper-data-20261118\T04\FIGURE_DATA\T04_path_and_error_plotdata.csv

All curves are arithmetic from recorded signals or exact frozen references. No model loading, optimization, dynamics integration, candidate search or changes to task bounds. Arrays copied in the master archive retain original source_store/raw_reference; CSV original_source points to the original Store artifact. Units remain separate; no average of unlike errors and no connected convergence curve across scopes.

Style: 7.16 in two-column width; Arial 8–8.5 pt labels; white background; thin axes; no cards, gradients, decorative shadows or large titles. PNG is 500 dpi; SVG text remains editable.

Exact reference arithmetic follows the frozen implementation at D:/softrobot-agent/.worktrees/core-five-task-figure-eight-evaluator-20261113/extensions/reference/generators.py, lines 24–46, with the parameters recorded in the final candidate task. It does not interpolate the sparse 89-point bank as if it were a dense reference. The original evaluation is preserved separately in final_acceptance_extracted.json.
