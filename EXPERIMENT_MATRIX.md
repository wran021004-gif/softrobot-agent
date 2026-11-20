# Current experimental matrix

## 1. Standardized multi-task benchmark

- Eleven benchmark cases: T01--T10 plus the benchmark PHS-2D instance.
- Thirty required physical conditions.
- Ours (FULL) satisfies all thirty required conditions.
- The independent PHS-2D structural-design study is separate from this benchmark denominator.

## 2. Research-mode comparison

Three modes are reported across the eleven benchmark cases:

- **A — LLM-only:** language-model research without dedicated mathematical research tools.
- **B — Direct Tools:** direct access to low-level mathematical tools, without the PPRP research abstraction.
- **Ours (FULL):** Main Agent, PPRP, complementary M0--M3 analysis semantics, validity-aware method routing, structure/control refinement, and evidence feedback.

Table II reports the maximum known normalized constraint violation, outcome state, evaluated/required condition coverage, and total task pass rate. Figure 6 visualizes outcome state and coverage. Direct Tools has two physical passes under documented protocol variants (T03 and T05); its strict frozen-protocol pass count is zero.

## 3. Independent PHS-2D structural-design study

This study is not part of the eleven-case benchmark denominator. It supplies:

- eighteen implicit-equilibrium derivative/finite-difference pairs;
- a maximum relative gradient discrepancy of 0.1191%;
- ten signed-loading physical conditions;
- independent-process reproduction, half-time-step evaluation, and initial-state perturbation checks.

Figures 4--5 report the mathematical and physical evidence and the associated structural-design process.

## 4. Architecture and context studies

- Reporter: six matched OFF/ON decision pairs.
- Original Knowledge/Skill replay: eight decisions in a 2x2 design at T04 and T07.
- Supplemental Knowledge/Skill replay: sixteen sessions across four checkpoints, fifteen valid decisions.
- Context: two historical PHS-2D checkpoint pairs and six cross-task decision checkpoints.

Figures 7--8 report these decision-level studies separately from physical task completion.

## 5. Cross-model resource profile

Supplementary Figure S1 compares the historical GPT-6 Astra FULL snapshot with the current GPT-5.6 Sol FULL/K+S+ snapshot across all eleven task identifiers. It reports charged mathematical evaluations, physical launches, Core request records, token totals, and final task outcomes. The comparison is descriptive, not an isolated model-only ablation.

## 6. Main paper reporting

- **Table I:** task-family portfolio and required-condition coverage.
- **Table II:** task-wise maximum known normalized violation, status, coverage, and total task pass rate.
- **Figures 1--8:** architecture, benchmark, research process, mathematical/physical evidence, structural outcomes, research-mode matrix, architecture ablations, and context management.
- **Supplementary Figure S1:** cross-model workload profile.
