# Gateway text-token counts

These post-hoc local tokenizer estimates supplement, and do not replace, Provider actual usage. Values use o200k_base with one method for all 28 sessions and 62 returned Main requests. No new model calls were made. Reviewer calls and transport failures are excluded.

Every first request was reconstructed from frozen source records, including the original Core schema and any shared-subtree encoding. All 28 serialized byte counts match the saved execution records. Initial message content is tokenized directly. Later request input is estimated by scaling its recorded bytes by its own initial content-token/byte ratio.

Earlier output is estimated from growth of the next request after subtracting recorded user/tool feedback, calibrated by retained final decision token/escaped-byte ratios. Final valid output uses the normalized canonical decision in its text-tool wrapper. The unretained last replies of the two failed sessions use their own previous-draft median. These are especially uncertain output estimates; intermediate draft text cannot be recovered.

Counts exclude service chat framing, hidden reasoning and unknown backend transformations; they cannot establish actual usage, billing, cache effects or model context capacity. Failed sessions remain included. Cumulative differences also reflect unequal repair-request counts. Compare historical measured usage in a separate panel.

| Checkpoint | Flat input | Hierarchical input | Cumulative reduction | Requests F/H |
|---|---:|---:|---:|---:|
| T01-127 | 195,629 | 30,166 | 84.58% | 1/1 |
| T04-216 | 69,485 | 64,380 | 7.35% | 3/4 |
| T07-074 | 803,543 | 33,797 | 95.79% | 3/1 |
| T08-006 | 344,452 | 54,951 | 84.05% | 4/2 |
| T09-213 | 52,977 | 38,384 | 27.55% | 1/2 |
| T10-222 | 80,256 | 58,605 | 26.98% | 1/2 |

Across these six pairs: Flat 1,546,342; Hierarchical 280,283; ratio of summed input counts gives 81.87% reduction. This describes this selected sample and delivery protocol, not measured service efficiency or statistical noninferiority.

| Experiment | Sessions | Requests | Input | Output |
|---|---:|---:|---:|---:|
| context_gateway | 12 | 25 | 1,826,625 | 25,332 |
| knowledge_skill | 16 | 37 | 6,125,281 | 40,932 |
