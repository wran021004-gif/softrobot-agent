# BF5 production integration and bounded Provider comparison

2026-10-27, Asia/Shanghai. Target: `integration/research-next`.

## BF5 public route

Selected production changes from B's `ba68617d8`, whose frozen evaluator was
subsequently independently passed and audited on B (`7382e90fa`, `e13939a7b`).
Imported only task contracts/evaluator, task adapter, real tool-axis signal
projection in Native and independent playback, backend declaration, norm/chord
search measurements, acceptance and method discovery. B's BF4 S2 continuation
extensions, experimental drivers/configurations, successful candidate/control,
freeze witness and private Stores were not imported. Existing C-F prerequisites,
Reach/Hold, BF4 timed Tracking and joint-condition protocol remain in place.

The task owns position `(0.290,-0.025,0.120) m`, a directed unit tool axis,
0.6 s horizon, 1 ms physics and 20 ms control/post-step sampling. At 0.58 and
0.60 s both position error <=0.008 m and directed-axis error <=pi/60 rad must
hold. The axis is the real `tip_site` rotation times the declared local axis.
Axial roll and full 3D pose are not task requirements. No Reach holding-speed
objective is added. Native chord constraints are equivalent for unit axes;
independent acceptance computes the actual directed arccos angle in radians.

Fresh entry: `python -m tools.research prepare --spec configs/research/study_bf5_public.json`.
The leaf uses the existing resolver/defaults/runtime, empty history, zero
science/Provider budgets and the existing pending scoped-authorization boundary.
Before preparing an autonomous Study, set a fresh ID and explicit finite shared
budgets, Native callback/iteration/knot limits and replay allowance. B's budget
and witness are not inherited.

Use the same public `evidence_read`, `research_plan`, `research_analysis` tools:
discover the frozen task -> generate from the declared family -> initialize
control -> read the registered `mujoco_direct_control_v1` combined template and
prerequisites -> submit Native optimization with the returned source and explicit
v2 window/knots -> independent physical_replay -> publicly read the completed
evaluation -> SELECT only if eligible. Both position and axis remain visible
in conditions, normalized violations, source binding and formal eligibility.
Affine/GVS direction analysis is explicitly not applicable; backend 1.3's normal
controller solve rejects the unsupported position-only NMPC substitution.

Fifteen focused fixture checks passed: six B geometry/acceptance/applicability
cases, public BF5 generation/discovery/control/replay/read/SELECT, six original
BF4 cases, two-condition joint SELECT/recovery and one Reach Native window check.
Fabricated perfect-motion fixtures are labeled; they are not scientific evidence.
The single-use `python -m tests.research.integration_tracking_smoke bf5` validates
one fresh Native baseline and independent full replay after commit (1,200 steps
maximum); it does not use B's successful structure/control or run a search campaign.

## BF6 compatibility audit (not integrated)

B's audited head is `e67d9d68e`. Its new task, adapter, evaluator, backend 1.4,
rigid-tool family and no-contact protocol are intentionally not registered on
this integration branch. B's incomplete attempt is not a ready research task.

The existing physical kernel already represents a rigid payload with mass,
local COM, full inertia and rigid attachment. B's tool is an actual 20 g body,
COM `(0.007,0.001,-0.002) m`, with a declared full inertia tensor and site offset;
`external_forces=[]`. A timed world force at a body COM changes force, not mass
matrix/inertial coupling, and cannot replace that load. Arbitrary tool-local
attachment quaternions and offset tool forces are not established by this task.

BF6 requires timed position AND directed-axis references at all 30 post-step
samples, and independent compiled mass/COM/inertia/site binding. BF4's timed
position evaluator can be reused for its position component; BF5's constant-axis
adapter alone does not implement moving-axis interpolation or this load binding.
The later `offline_oriented_tracking_v2` additionally requires per-physics-step
environment contact accounting, not just zero contact at recorded sample times.

B's initial Native center stopped with contact after 226 completed steps. Its
one independent replay failed on the 227th step call, with 226 completed steps
and samples only through 0.22 s. Evaluator validity is incomplete and acceptance
unknown. Total completed steps are a 452-step lower bound; 453 calls were
attempted, and progress inside the failed call is unknown. The failure does not
establish reliable physical causality or structural infeasibility. Some binding/
contact summaries were missing from that original failed replay; B's later
persistence repair was only syntax-checked and does not backfill old evidence.

Before formal integration B must deliver a complete numerically stable,
no-environment-contact initialization under the unchanged actual rigid load,
plus independently registered full-horizon position/axis/load/contact evidence.
Future numerical changes need a new recorded version. No force surrogate,
changed floor, lighter load, relaxed thresholds or joint-protocol extension is
introduced here. No BF6 worker is launched by A.

## Flash / Pro decision comparison

An independent bounded Provider-only comparison will reuse the production
Harness, Plan/Analysis/Evidence schemas and LiveBoundary/Store accounting.
It will not dispatch scientific requests or access the current C Study. Only
fresh, labeled interface fixtures/public frozen task information are eligible
inputs. Exact model IDs and common request settings are checked against the
[DeepSeek Chat API](https://api-docs.deepseek.com/api/create-chat-completion/)
and [thinking/tool-call rules](https://api-docs.deepseek.com/guides/thinking_mode/).
Raw responses/reasoning and credentials remain local; public output contains
legality checks, evidence-interpretation review and actual usage counters.
No population/model ranking or scientific performance claim follows from this
small comparison. Actual execution configuration and results are recorded in
the follow-up below.

## Recorded BF5 engineering execution

Production commit `3eb1f408e` was pushed before the Provider work. Its one fresh
Native baseline and independent replay completed 600+600=1,200 steps, with
`offline_position_tool_axis_v1`, real Store/profile binding and a `valid_failure`
outcome. SELECT correctly refused the failing result. Store cumulative numerical
cost was 5.6372076 s, including 5.1245592 s in independently settled worker
receipts. Provider/NMPC/RL counts were zero. The successful SELECT fixture remains
explicitly fabricated; this baseline is not a new feasibility witness.

## Frozen small model comparison protocol

`configs/research/provider_flash_pro.json` fixes `deepseek-flash` versus
`deepseek-v4-pro`, thinking enabled/high, max_tokens=8,192, two cases and at most
two Provider requests per case/model (eight total). Case/model order is Flash/Pro
for BF5 and Pro/Flash for BF6. Each has a separate existing Store grant/session
with zero tool/backend/worker allowance, a fresh SDK session and the same frozen
case input/schema. Credentials, raw responses and retained reasoning stay local.
The original `build_harness`, `live_model_class`, `LiveBoundary` and production
Plan/Analysis/Evidence contracts are reused. No alternative SDK, tools router or
scientific dispatcher is added. Only a test-side read/validation interceptor runs.

BF5 input is this integration's fresh failed baseline and its frozen task;
BF6 input is a filtered public B incomplete receipt/audit. No C evidence or B
successful design/control is supplied. The evidence reference is content-identical
between model arms. The production evidence reader handles static pointer/views;
there is no synthetic scientific feedback. Provider tool proposals record schema,
reference/intent checks and, where available, pure applicability. These partial
checks do not claim full scientific admission; all science budgets are zero.

One mock-HTTP end-to-end check passed using the real Harness/ledger with worker
and science dispatch replaced by failing sentinels. Synthetic usage in that unit
test is not reported as real cost. The live runner is
`python -m tests.research.flash_pro_decision_probe --live`. Request IDs, response
receipts and actual usage/cache counters are retained in its own ignored Store.
No uncertain or existing attempt is automatically resent. Hitting the two-request
cap after a valid tool proposal may stop the Harness before a prose follow-up;
that is distinct from invalid requests or absent evidence understanding.
