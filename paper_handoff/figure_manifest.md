# Figure and table handoff

Common style: white background, straight edges, no shadows, gradients, rounded cards or dashboard tiles. Use Arial/Helvetica labels at 8–9 pt at final size. Export PDF/SVG. Palette: Main Agent #26384B; Mathematical Evidence #527F7B; Physical Evidence #70849A; structure modification #B08A59; verified pass #557663; failure #A35D55; baseline #929BA4; auxiliary lines #D9DEE2. Labels and line styles must also distinguish groups. Preserve Figure 1 unchanged.

All plotting files are generated from the normalized tables. SI numerical values remain unrounded in CSV; display lengths in mm with three decimals, angles in rad with four decimals, ratios with four decimals, scores with one decimal, and counts/tokens as integers. Panel-specific derivative units are stated below. Do not silently plot UNKNOWN as zero.

## Figure 2. Task Portfolio and Physical Coverage

**Claim:** one completed FULL case per task spans active/passive, geometry, loads, trajectories, contact and feedback, with task-specific acceptance.

| Panel | Data and coordinates | Color / annotation |
|---|---|---|
| A | `fig02_task_portfolio.csv`: x=task_id in T01–T10/PHS-2D order; y=task family / active-passive / segment-tendon morphology | Navy text; structural thumbnails use original models indexed by `visual_asset_index.csv`. |
| B | Same CSV: x=task_id; y=required_condition_completion or minimum_normalized_constraint_margin, separate axes | Green completion; blue margin. Do not average heterogeneous physical errors. |
| C | Same CSV: named `metric_1..3_id/value/unit`; one small labeled physical output per task | Physical blue. Show within-task aggregation field, not a common raw-error axis. |

**Sources:** Source A FULL_TASKS/FULL_CASES; Source B D1/D2. Eleven rows, 30 required conditions. T10 controls separate. PHS here is **7S**. **Missing:** common-camera native model thumbnails have not been rendered in this package. **Placement:** main text, Table I supplies compact protocol facts rather than repeating all plotted values.

**Caption:** “Task portfolio and physical coverage. Eleven FULL task cases span active and passive soft-robot research under frozen, task-specific contracts. All 30 required conditions are reported with their coverage and constraints; two T10 frozen controls are retained separately. Physical metrics retain their original units and are not averaged across tasks. The portfolio PHS-2D case uses seven segments; the independent nine-segment mechanism study is shown in Fig. 3.”

## Figure 3. Mechanism-Guided Passive Design

**Claim:** the independent nine-segment Study moves from nonlinear slack/qualification problems toward a physical guide-and-routing mechanism that permits local compliance while suppressing tip motion.

| Panel | Data and coordinates | Color / annotation |
|---|---|---|
| A | `fig03_phs2d_evolution.csv`: four original Journal candidates, ordered diagonal stay → dense guides → massive guide plates → final nine-segment | Structure ochre; failed local screens brick. Render actual XML at identical camera, scale, orientation, light and material. State candidate segment/tendon count. |
| B | `fig03_phs2d_performance.csv`: x=material_s; separate positive/negative force markers; y=point_displacement_m×1000 and tip_displacement_m×1000 in separate axes | Physical blue; force direction by marker. Lines are guides between sampled cases. |
| C | Same CSV ratio vs material_s; `phs9_centerlines.csv` x_m/z_m in mm and `phs9_tensions.csv` tension_n by tendon for matched conditions | Threshold line at original ratio 0.3. Tension/taut state must refer to the same signed-force case as the shape. |

**Sources:** Source C independent Journal, final structure, summary replicate 1. Ten cases, four passive tendons, zero active actuators; independent extrema 11.155 mm / 3.068 mm / 0.1093. Other numerical checks remain supplementary. **Missing:** final actual XML is indexed; intermediate candidate XML extraction and the four uniform-camera renders remain to be completed. Do not replace them with seven-segment F0–F8. **Placement:** main text, full 46-candidate history and all 40 final numerical-check rows in supplement.

**Caption:** “Mechanism-guided passive design in an independent PHS-2D Study. Original Journal candidates reveal the progression from diagonal stays and dense guidance to massive physical guide plates, a tapered tendon lever arm and the final nine-segment structure. Independent signed-load evaluations pass all ten original conditions, with minimum force-point displacement 11.155 mm, maximum projected tip displacement 3.068 mm and maximum tip-to-point ratio 0.1093. Shapes, tensions and taut sets are matched by load case. Local mathematical screens and complete physical evaluations retain distinct scopes.”

## Figure 4. Mathematical Evidence and Physical Validation

**Claim:** local derivatives agree with finite differences; the planned M1/M2 test addresses a different, finite physical question and currently lacks matched results.

| Panel | Data and coordinates | Color / annotation |
|---|---|---|
| A | `fig04_gradient_validation.csv`: x=finite_difference_gradient; y=implicit_gradient; facet by metric/unit | Teal points, gray identity line. Displacements mm/du, ratio 1/du. |
| B | x=branch_id; y=relative_error_percent; metric marker | Teal; maximum 0.1191%. Six load branches × three metrics along one common Young's-modulus direction. |
| C | `fig04_m1_m2_comparison.csv`: x=A/B/C; y=normalized_constraint_violation or named physical error, paired by condition_id | A gray, B ochre, C blue. **All current rows are NOT_EXECUTED/UNKNOWN and must not be plotted as empirical results.** |

**Sources:** Source B sealed nine-segment derivative table; `supplementary_experiments/m1_m2/executable_plan.json` for the bounded T07 two-design, three-mode, four-condition experiment. **Missing:** matched complete U0*, initial-state/solver equality confirmation and fixed-input replays; no physical M1/M2 difference is established by this package. **Placement:** A/B main text now; C only after execution, otherwise protocol in supplement.

**Caption:** “Mathematical consistency and finite physical comparison. Eighteen implicit derivative/finite-difference pairs cover three metrics on six signed loading branches of the nine-segment model along one shared normalized modulus perturbation, with maximum relative discrepancy 0.1191%. This is a local numerical consistency check. A separately prepared T07 protocol compares (d0,U0*), (d1,U0*) and (d1,U1*) under unchanged contracts. Its matched physical evaluations remain pending; no empirical M1/M2 effect is inferred from historical re-optimization.”

## Figure 5. Evidence-Guided Agentic Research Trajectories

**Claim:** evidence changes Main Agent hypotheses, morphology and control routes; failure/rejection nodes carry useful scientific information.

| Panel | Data and coordinates | Color / annotation |
|---|---|---|
| A | `fig05_research_trajectories.csv`: x=Research Node within each independent Study, y=task/Study; concise observation → hypothesis → investigation → evidence → action → outcome | Navy Main; teal math; blue physical; ochre modifications; brick failures. M0–M3 are labels of complementary semantics, never a mandatory sequence. |
| B | `fig05_research_metrics.csv`: x=node_id; y=before_value/after_value, separated by metric and evidence scope | Explicitly label finite-budget native diagnostic excess. Do not relabel it as independent full acceptance or matched M1/M2 evidence. |
| C | Research-process annotations from `decision_annotations.csv`, separate initial and blinded rounds | 0–4 ordinal score, UNKNOWN hatched/omitted. No subjective Physical Outcome score; no composite scientific success score. |

**Sources:** Source A requests/events and configuration records, Source C independent Journal; selected tasks T04/T07/T10 and 9S. Full 32 nodes remain supplementary. **Missing:** immediate paired physical changes are UNKNOWN where source records do not establish them. **Placement:** concise four-row trajectory in main; all annotations and editorial ranks in supplement.

**Caption:** “Evidence-guided research trajectories. Main Agent revises physical hypotheses, structures and control methods in response to mathematical and physical evidence. Representative T04, T07, T10 and independent nine-segment PHS-2D nodes include failed constructions, rejected geometry and control-route changes. Original hypotheses and their scope are retained; retrospective indexed outcomes are labeled separately. Quantitative physical outcomes and model-assisted process annotations are distinct evidence layers.”

## Figure 6. Research-Mode Comparison

**Claim:** the complete 11×3 method matrix describes coverage, constraint outcomes and costs under the recorded protocols, including adverse results.

| Panel | Data and coordinates | Color / annotation |
|---|---|---|
| A | `fig06_abc_comparison.csv`: x=method A/B/C; y=11 tasks; cell=status/completion_fraction | Green pass, brick failure, gray unexecuted/qualification markers. C is historical FULL. |
| B | x=task_id with three paired method points; y=violation_fraction; separate inset/axis for maximum_violation if known | A gray, B ochre, C navy. Show unknown magnitudes as unknown; coverage is separate. |
| C | `resource_metrics.csv`: x=method; y=one named cost within the same measurement_population and wall_time_scope | Separate facets for cost populations; no pooled averages across scopes. |

**Sources:** Source B D1/D2/D3 and original resource tables. Preserve T03-B protocol deviation, discretization differences, T04-B qualification failure and T08-C development classification. **Missing:** actual Main token counts and some complete integration-cost scopes are UNKNOWN. **Placement:** main 11×3 matrix; complete 3160 metric and 1927 event/relation rows supplementary. Table II records interpretation/coverage facts without duplicating the whole matrix.

**Caption:** “Research-mode comparison over eleven tasks and three recorded methods. Status, required-condition completion, evaluated coverage and original normalized constraint violations are shown separately. C is the historical FULL reference rather than a newly randomized run. Qualification failures, protocol deviations, discretization notes, development classifications and missing measurements are retained. Resource comparisons use their original measurement populations and are not pooled across incompatible scopes.”

## Figure 7. Research Architecture Ablations

**Claim:** Reporter improves two specific decisions; K/S promotes recorded experience use while original decision-quality scores saturate.

| Panel | Data and coordinates | Color / annotation |
|---|---|---|
| A | `fig07_reporter_knowledge_skill.csv` panel A: x=six checkpoint IDs; y=score_off/score_on (0–4), connected within pair | OFF gray, ON navy; no mean-only bar chart. Selected M1-C and P3-A relation diagrams use `reporter_positive_cases.csv`. |
| B | panel B: two task-specific 2×2 grids, x=Skill −/+, y=Knowledge −/+; value=experience_utilization | Gray-to-navy sequential scale 0–4. Quality, grounding and actionability all 4; +1.5/+1.5/−3/0 descriptive contrasts. |
| C | Supplementary new KS16 rows: separate checkpoint facets, x=the four K/S cells; y=each unchanged score | Keep protocol separate; display ties/saturation and adverse effects. Do not claim synergy or physical improvement. |

**Sources:** complete original six Reporter pairs and eight E1 Main decisions, plus separately labeled supplemental decisions. M1-C 2.8→3.6: budget/unsupported initialization awareness. P3-A 3.0→4.0: directional passive-tendon mechanism ablations. Six-pair means 3.433→3.733; wins/ties/losses 2/4/0; unsupported conclusions 2→0. **Missing:** original Provider usage and any unreturned supplemental usage are UNKNOWN; no physical follow-up was run. **Placement:** A/B main; detailed decisions and supplemental four-checkpoint experiment in supplement.

**Caption:** “Architecture decision studies. Reporter OFF/ON results retain all six paired checkpoints; two positive cases illustrate constraint-aware planning and discriminating passive-mechanism experiments. The original two-task Knowledge/Skill factorial replay increases identifiable experience utilization from 0 to 3 with either resource, while decision quality, evidence consistency and actionability remain 4 in every cell. Descriptive interaction is −3 and the joint condition does not exceed the best single resource. Supplemental frozen decisions are reported separately under the unchanged rubric. These are decision-level outcomes.”

The requested common five-dimensional reassessment is in `fig07_knowledge_skill_five_dimension.csv`: x=dimension, y=K/S cell, facet=task/checkpoint/protocol, value=score (0–4). Dimensions: physical interpretation, evidence consistency, limitation recognition, research actionability and evidence-reference accuracy. Original E1 and supplemental checkpoints retain separate identities. Historical utilization remains separate. Do not pool original four-dimensional and added five-dimensional ratings. Retain saturated cells. Put the full profile matrix in the supplement and choose only a supported contrast for the main figure.

## Figure 8. Hierarchical Context and Evidence Utilization

**Claim:** historical measured savings coexist with quality/coverage tradeoffs; new cross-task decisions extend evidence-utilization assessment, with actual-usage missingness explicit.

| Panel | Data and coordinates | Color / annotation |
|---|---|---|
| A | `fig08_context_comparison.csv`: x=checkpoint grouped by protocol; y=actual_cumulative_input_tokens, Flat/Hierarchical connected | Flat gray, Hierarchical navy. E2 accepted-only and E2-R2 cumulative scopes labeled. UNKNOWN Gateway usage is not plotted as zero or as a proxy. |
| B | Same file: x=checkpoint; y=blind_decision_quality (0–4) and key_evidence_recall (0–1) on separate aligned axes | Paired markers; descriptive quality-tolerance reference 0.2 only. No formal noninferiority claim. |
| C | `context_retrieval_path.csv` for E2-R2 and measured new retrieval rows: x=request/read sequence; y=original evidence_id/level | L0 navy; L3 physical blue/teal according to content. Draw only actual reads, including a direct L0→decision path where no reads occurred. |

**Sources:** historical E2/C035, E2-R2/C037 and the separately frozen six-checkpoint cross-task protocol. E2 675802→78785 (88.34%), scores 4.0→3.8, no reads. E2-R2 877197→174298 (80.13%), 3.4→3.6, evidence 5/5→3/5 and three L3 reads. **Missing:** actual Gateway usage is unavailable unless returned; these new cases cannot establish measured token savings. Prior API-quota and unsupported-wire attempts are retained separately. Backend/default-reasoning identity is unverified. **Placement:** main with grouped protocols and explicit missingness; full decisions, key checklist, blind reviews and retrieval paths supplementary.

**Caption:** “Hierarchical context efficiency and evidence utilization under separate protocols. Historical C035 reduces accepted-inference input by 88.34% with blind score 4.0→3.8 and no evidence reads. Preregistered C037 reduces cumulative input by 80.13%, with scores 3.4→3.6 but key-evidence coverage 5/5→3/5 after three L3 reads. Six additional task checkpoints retain their own frozen evidence, anonymous reviews and usage records. Unreturned usage remains UNKNOWN and cannot support an actual token-efficiency claim. The small descriptive sample does not establish statistical noninferiority.”

## Figure 9 and three main tables

Figure 9 is not supplied as a measured result: this source package does not establish a complete hardware platform/protocol/trial/measurement dataset. Retain only when those records exist. Simulation and hardware must stay separate.

Table I: canonical task names, morphology, required-condition counts and contract family. Table II: method definitions, coverage and protocol qualifications, with full matrix in Fig. 6/supplement. Table III: architecture sample counts, decision-only scope, quality/evidence/cost endpoints and actual-usage availability. Avoid repeating Figure values in large main-text tables.
