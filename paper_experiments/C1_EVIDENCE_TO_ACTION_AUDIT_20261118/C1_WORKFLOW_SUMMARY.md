# C1 — Aggregate evidence-to-action trace

This publication view reports the aggregate archive-level trace.

| Stage | Count | Interpretation |
|---|---:|---|
| Evidence-linked proposals | 220 | Structured proposals admitted by the strict evidence-link rule |
| Dispatched | 205 | Original tool-dispatch receipts present |
| Executed | 160 | Scientific operation has a successful receipt and inspectable output |
| Later independently validated | 10 | A later independent evaluator PASS is linked to the exact candidate and schedule |

The proposal-to-execution conversion is 160/220 = 72.73%. The dispatched-to-execution conversion is 160/205 = 78.05%. The later-validation linkage is 10/160 = 6.25%; this is not a general task success rate because the 160 executed operations include heterogeneous intermediate research actions, not all of which are expected to terminate in an independent task evaluation.

The audit parsed 25,662 historical event/receipt rows across 283 source-index entries and formed 1,314 candidate action records. A further 1,094 candidate records were outside the strict denominator because their evidence link or execution chain could not be confirmed; they are not counted as failures. The ten later validations establish trace linkage and evaluator outcomes, not a causal effect of each preceding action.

The original audit package is preserved on branch \`paper/t07-m1m2-c1-trace-20261118\` at commit \`206886ff064722eb84f8e85a1509bd9d08d57923\`.
