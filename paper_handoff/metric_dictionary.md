# Publication metric dictionary

The authoritative definitions and units are in `registry/metric_registry.csv`. Original row-specific thresholds, normalization scales and qualifications are in `supplementary_data/task_metrics/condition_metrics.csv`. No threshold is changed by this synthesis.

## Physical outcomes

`required_condition_completion` is passed required conditions divided by the frozen required-condition count. The eleven FULL tasks contain **30 required conditions**; the two T10 frozen controls are additional records. The independent nine-segment PHS Study has its own ten conditions and is outside this denominator.

`evaluation_coverage` follows D1's evaluated-constraint denominator. Coverage is not qualified episode completion: qualification failures can have known constraint rows while zero required conditions are completed.

For each D2 constraint, retain the original `bound_type`, `threshold`, `normalization_scale`, `normalization_basis`, `acceptance_tolerance`, and `strict`. The signed normalized violation is supplied by D2. Its positive part measures excess. The margin is its negative. Boolean, interval, lower-bound, strict, qualification and missing-value cases retain D2's original handling; a universal new scaling is not substituted.

The portfolio's `normalized_constraint_violation` uses D1 `violation_fraction`, the fraction of violated expected constraints. It is distinct from the maximum and total **magnitude** of normalized violation, and from mathematical (V_\tau(d)). These three quantities must not be substituted for one another. `minimum_normalized_constraint_margin` uses the known required-constraint rows only; incomplete coverage remains explicitly reported.

Unknown normalized magnitudes and D1 known lower bounds are separate fields. Missing or unexecuted results are never converted to zero. The `is_constraint` flag distinguishes observables from acceptance constraints. Preserve failure, qualification, discretization and development-status labels, including T03-B's deviation and T08-C's development classification.

`full_observables.csv` retains the original FULL scalar observations. Aliases in this source are not extra independent measurements. `fig02_task_portfolio.csv` selects one to three named task-specific metrics and records the within-task max/min operation. Errors remain in SI units. Convert m to mm by ×1000 **for display only**. Do not average meters, radians, newtons or different task contracts.

PHS point displacement, projected tip displacement and their ratio are paired within a condition and a Study. Nine-segment `phs_performance.csv` includes original run, independent recording, half-step and perturbed initial-state checks as separate `replicate_id` values. Figure 3 uses replicate 1, ten cases. The reported 11.155 mm minimum is the independent-run summary; do not silently replace it with a nominal value. The seven-segment nominal result remains separate.

`candidate_improvements.csv` distinguishes native finite-budget optimization's signed excess (J) from independent physical measurements. T01/T07 pairs change structure and/or optimized control and may have different initializations or budgets. Their differences are descriptive trajectory evidence, not the matched M1/M2 experiment or a single-variable causal effect. T08's bilateral stiffness-ratio difference is a physical protocol measurement. No cross-task improvement average is defined.

## Mathematical validation

Eighteen pairs are six load branches × three metrics, along **one common normalized Young's-modulus direction across nine segments**. They are not eighteen independent designs or eighteen parameter directions. Displacements use mm/du; the ratio uses 1/du. Central finite differences are reconstructed from saved endpoint values and the recorded perturbation. Relative discrepancy is the absolute derivative difference divided by the recorded finite-difference magnitude/floor, in matching units. `relative_error_percent = 100 × relative_error`. Maximum discrepancy: approximately 0.1191223%. This establishes local consistency; it does not establish finite-load task acceptance, mesh-independent physics or global sensitivity accuracy.

## Research process and architecture

Research-behavior scores follow `supplementary_data/annotation/annotation_rubric.md`. Physical Outcome has no subjective score. Rank scores are editorial only. `hypothesis_origin`, `outcome_scope`, `execution_status` and `action_executed` prevent retrospective explanations and proposed actions being treated as contemporary completed experiments.

Reporter uses six pairs and the original five-dimension blind mean. Its two positive cases are illustrations of the six-pair dataset, not two extra samples. Provider usage is UNKNOWN where not returned; visible-context tokenizer proxies are not actual usage.

Original E1 Knowledge/Skill uses eight decisions, one per task/cell. Utilization main effects are the mean difference between factor levels over the two other-factor cells. Interaction is (y_{11}-y_{10}-y_{01}+y_{00}). Joint minus best single is (y_{11}-\max(y_{10},y_{01})\). Original quality/grounding/actionability are saturated at 4; descriptive utilization effects are +1.5, +1.5, −3, and 0. New decision supplements retain their own protocol and checkpoint identity and the unchanged rubric. They do not establish synergy or robot-success improvements.

Context recall is correctly used predeclared key evidence / frozen key-evidence count. It is a decision-content measure, not an inference about unread records. Critical omissions, unsupported claims and wrong references are judged from anonymous decisions. Retrieval counts and original source paths are measured separately from session records. Quality tolerance 0.2 is descriptive only; six checkpoints do not establish statistical noninferiority.

E2/C035 cost is **accepted inference only**; the rejected Hierarchical HTTP400 has no usage, so all-attempt input is UNKNOWN. E2-R2/C037 cost is cumulative actual input over its accepted Main requests. Keep these protocols separate. New Gateway experiments form another protocol; Gateway default reasoning/backend identity is not exposed. Missing usage remains UNKNOWN, which prevents a measured token-efficiency conclusion for those pairs.

The requested common five-dimensional reassessment is a separate score set: physical interpretation, evidence consistency, limitation recognition, research actionability and evidence-reference accuracy. The same five-dimensional rubric is applied to original E1 and supplemental decisions. Historical-experience utilization remains separate. Original four-dimensional scores are not overwritten. Original `decision_quality` is not relabeled from `physical_interpretation`; supplemental four-score reviews use the original E1 definitions. Separate ratings/protocols are not averaged to manufacture a condition difference.

## Resource measurement

`resource_record_id` identifies one original measurement population. Preserve `measurement_population`, `cost_scope`, `wall_time_scope`, `integration_cost_status`, lower bounds and source basis. FULL multi-store/confirmation costs and A/B/C original-run summaries overlap and cannot be summed. Numerical charged time is not elapsed wall-clock time. Candidate artifacts are not automatically distinct structure candidates. Integration steps, internal optimizer physics, independent physical evaluations and Provider requests are separate quantities.

Input and output tokens require Provider-returned usage. A combined historical `llm_tokens` field is retained with its original meaning; it is not split into invented input/output counts. Generic tokenizer estimates are allowed only for offline capacity gates or explicitly labeled proxies. An API quota failure, unreturned usage or an unexecuted physical replay has UNKNOWN cost, never zero.

The post-hoc `gateway-text-tokens-v1` calculation adds `input_tokens_text_estimate` and `output_tokens_text_estimate` to new-session views, without replacing actual-usage fields. The fixed local encoding is o200k_base. `initial_input_text_tokens` counts reconstructed initial message content; all 28 serialized request byte counts match the saved records. Later input uses the session's initial token/byte ratio. Earlier output uses request growth minus recorded feedback and final-text calibration; the two failed final replies use their own earlier-draft median. `retained_final_decision_text_tokens` counts normalized canonical final decision text, and remains UNKNOWN for failed submissions. These counts omit chat framing, hidden reasoning, backend transformations and cache/billing semantics. See `supplementary_data/architecture_metrics/gateway_token_summary.md` and `supplementary_experiments/gateway_token_method.json`. Cumulative Context differences include unequal repair counts; keep historical measured usage in a separate panel.

## Source and column conventions

CSV is UTF-8 with BOM; numeric values use decimal dots and retain sufficient source precision. UNKNOWN is the missing-value sentinel. IDs and artifact identifiers are text. `source_reference`/`source_locator` refer to immutable Git objects or original repository-relative record identifiers. A source artifact ID is retained as an identifier; no hashes are calculated or verified.

`study_id` is canonical. `source_study_id` or `run_id` preserves an original run identity. The independent PHS Studies never share a candidate trajectory. New decision sessions carry their own protocol ID. `condition_role=control` records never enter required-condition denominators.

Plotting-ready CSVs are generated views of authoritative normalized tables. Do not edit them manually. Figure 4C contains explicit NOT_EXECUTED rows and UNKNOWN measurements until the paired protocol is actually completed.
