# Research architecture ablation: plotting materials

This directory contains the completed Reporter, Knowledge/Skill and Context studies, including plotting tables, decisions, blind-review materials and saved Provider request/response records. Local environments, downloaded dependencies, credentials and caches are excluded.

| Study | Plotting entry point | Interpretation boundary |
| --- | --- | --- |
| Reporter ON/OFF | [positive cases](reporter_on_off/figure_data/) | P3-A and M1-C are selected case illustrations; preserve the full paired results and their original blind scores. |
| E1 Knowledge / Skill | [complete four-condition table](knowledge_skill/figure_data/factorial_results.csv), [main effects](knowledge_skill/figure_data/factorial_effects.csv), [interactions](knowledge_skill/figure_data/interaction_effects.csv) | Eight real Main LLM decisions. Two K+S+ sessions supplement the original six; authored engineering Core Plans are excluded from current factorial scores. |
| E2 Flat / L0–L3 | [comparison table](context_flat_vs_l0_l3/figure_data/context_comparison_table.csv) | C035 checkpoint: accepted-inference input reduction with a small score decline; one rejected request lacks usage. |
| E2-R2 decision-relevant context | [paired results](context_flat_vs_l0_l3_v2/figure_data/pairwise_results.csv), [retrieval path](context_flat_vs_l0_l3_v2/figure_data/retrieval_path.csv) | C037: actual L0 → L3 reads, lower cumulative input and a modest blind-score advantage, with lower evidence coverage. C042 was omitted before inference by the capacity rule. |

## Current E1 figures and data

- [T04 figure: SVG](knowledge_skill/figure_data/T04_knowledge_skill_2x2.svg), [PNG](knowledge_skill/figure_data/T04_knowledge_skill_2x2.png), [PDF](knowledge_skill/figure_data/T04_knowledge_skill_2x2.pdf).
- [T07 figure: SVG](knowledge_skill/figure_data/T07_knowledge_skill_2x2.svg), [PNG](knowledge_skill/figure_data/T07_knowledge_skill_2x2.png), [PDF](knowledge_skill/figure_data/T07_knowledge_skill_2x2.pdf).
- [Structured four-condition comparison](knowledge_skill/figure_data/ks_four_condition_comparison.json).
- [Original decision clips](knowledge_skill/figure_data/knowledge_skill_clips.md).
- [Current review index](knowledge_skill/figure_data/blind_review/CURRENT_REVIEW_INDEX.json). Older mixed-origin tables/reviews remain preserved as superseded material under `knowledge_skill/ks_completion/prior_figure_data/`.

For both tasks, historical-experience utilization is 0 / 3 / 3 / 3 for K−S− / K+S− / K−S+ / K+S+. Decision quality, evidence consistency and actionability are 4 in every cell. Utilization main effects are K=+1.5 and S=+1.5; the interaction contrast is −3, and joint minus best single is 0. No incremental joint score benefit was observed. These are descriptive contrasts with one sample per cell and human review pending.

The E1 figure script reads repository-relative CSV files and can be rerun in a Python plotting environment with Matplotlib and NumPy installed:

```sh
python paper_experiment_data/architecture_ablation/knowledge_skill/ks_completion/plot_factorial.py
```

The publication artifacts were rendered with Matplotlib 3.11.2 and NumPy 2.4.6. No simulation or Provider inference is needed to redraw these figures.

## Provenance and measurement

`PLOTTING_INDEX.json` lists portable repository-relative data locations. Absolute `D:/softrobot-agent/...` and original source locators inside raw records are historical provenance, retained verbatim. For plotting after cloning, use the relative paths in this index and the local `figure_data/` tables. Frozen snapshots/corpora contain the supplied evidence; original FULL Stores are not bundled here.

Provider-measured usage and local estimates are separate. E1/Reporter Gateway usage may be absent; missing usage is not zero. Estimates using `o200k_base` are generic proxies, not a verified tokenizer mapping or billing measure. Context studies retain every sent request and include re-sent context in cumulative accounting.

No result here measures an improvement in robot success rate. Do not add statistical-significance claims or present separate views of one paired case as independent findings. Each study's protocol, blind-review materials, limitations and exact decision clips remain alongside its plotting tables.
