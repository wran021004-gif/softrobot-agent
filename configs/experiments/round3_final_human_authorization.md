# Round 3 FINAL: Human-owned reusable surrogate authorization

Source: the user's Round 3 FINAL request, followed by the explicit correction
"保留 0.05 m 的长期下界". The correction sets total_length_m to [0.05,0.80] m.
The remaining approved representation, optimization, relation and route bounds
are recorded in SURROGATE_EXPLORATION_ENVELOPE_V1 in the family envelope.yaml.
This is permission for legacy_v1_surrogate exploration only, not manufacturing
certification, validated material behavior or real-robot physical validation.

Engineer may select a task-relevant subset of this envelope, reference design,
finite budget and deterministic seed through ExperimentPolicy without another
variable scientific approval. The validator must check the envelope, relational
constraints, existing task truth and supported model/controller routes. Policy
files are choices under this authorization, not independent scientific authority.

Only length, tendon routing radius and integer tendon count are design-search
variables. Body radius is representable but optimization is blocked by mechanics
coupling. Segments may change only in NUMERICAL_SENSITIVITY, with other design
fields and C1 commands held fixed. Sections remain one. No new physics, C2 tuning,
MPC, RL, LLM connection, benchmark, automatic Skill admission, commit or push.

This round authorizes length screening (including the analytic PCC matching
length), routing-radius and tendon-count studies, small joint search and the
4/6/8/12/16/24 segment audit. Joint search is capped at 30 screening candidates
and 10 MuJoCo validations. Other stage budgets are fixed before each stage runs.
Reuse completed canonical runs and a single MATLAB session rather than repeat
identical evaluations. The frozen task/environment/metric/Gate and physics
constants are unchanged. Existing HARD geometry rejection remains authoritative.
