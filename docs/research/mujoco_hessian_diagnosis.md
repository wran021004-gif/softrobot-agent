# MuJoCo Hessian failure: isolated diagnosis and explicit contact correction

Baseline: `04f58493547e40e327fba6696060fc595cc77c2b`.
Sealed source: `m1-open-topology-restart-20261101-fefefd8c`.
No Provider, Study prepare/bind/resume, formal mathematical charge or independent
scientific Replay was performed. Every engineering baseline was capped at 600
steps. The original 3.13.0 interpreter/environment was preserved; 3.14.0 was
installed without dependencies in a separate workspace environment only.

## Actual frozen models and reproduction

Both failed candidates have three actual mesh entries of 12 cells each. Both
compile to `nq=nv=72`, with four/five actuators respectively. Their actual options
are AUTO Jacobian (sparse=true), Newton, implicitfast, 0.001 s, MuJoCo 3.13.0,
float64. A separately generated legal two-segment reference compiles to 48 DoF
and AUTO dense. The threshold hypothesis is confirmed for these actual models.

The original constant 0.2 N baseline reproduces both failures at the 169th step,
after 168 completed steps. At 0.168 s, reproduced qpos/qvel match the saved
failure snapshots exactly, and ctrl matches. The original snapshots did not save
qacc; reconstructed pre-call qacc is finite, with maximum absolute values
280.175/353.183 rad/s^2. Saved pre-call ncon/nefc and warnings are zero. A single
position-stage diagnostic at that saved state detects two new floor/payload
contacts and eight constraint rows; it performs no time integration. Failed-call
partial counters agree, but are explicitly not a valid complete failure state.

The initial mass matrix is positive definite: minimum eigenvalue about
3.83949e-9 kg m^2, maximum 0.0535385, condition 1.39442e7. Positive body masses
start at 9.49037e-4 kg and inertias at 1.24805e-8 kg m^2. Zero mass/inertia entries
belong to world/fixed_base. Damping spans 0.0257143--0.0525 N m s/rad and joint
stiffness 0.357131--2.76355 N m/rad. Inputs remain legal 0.2 N within 0--8 N;
actual actuator-force bounds are -8--0 N. No physical regularization was added.
The payload reaches the floor at z=-0.02 m; first detected penetration is
0.211/0.438 mm for the four-tendon case. This is a new contact event, not evidence
that the preceding unconstrained state already contained contacts.

## Bounded A/B/C/D results

| Case, same four-tendon baseline | Result |
|---|---|
| A: 3.13 AUTO/Newton/implicitfast | 168 steps; original FatalError on step 169 |
| B: 3.13 dense/Newton/implicitfast | Step 169 produces enormous velocity; step 170 warns BADQVEL and resets |
| C: 3.13 AUTO/CG/implicitfast | 600 steps, finite/no warnings/reset; five-tendon follow-up fails with BADQACC/reset at step 183 |
| D: 3.14 AUTO/Newton/implicitfast | FatalError disappears, but the same step-169 velocity explosion and step-170 reset occur |

B/D reach about 1.76e11 rad/s and 5.05e19 J before reset. CG is not a valid
cross-candidate solution either. Neither dense nor the version upgrade is adopted.
The official [3.14 notes](https://mujoco.readthedocs.io/en/3.14.0/changelog.html)
include [35c0631de](https://github.com/google-deepmind/mujoco/commit/35c0631de),
but removing the fatal pivot check does not establish a valid trajectory here.

## Conditioning trigger and scope of the correction

The old compiler emits zero friction but leaves default condim=3 and pyramidal
contact. MuJoCo retains minimum friction 1e-5. At first impact, efc_D is about
7.8e8--9.3e8; a diagnostic `M + J.T D J` has condition about 8.78e18. This is a
position-stage conditioning proxy, not the exact implicit Newton active Hessian.
Its rounded negative tiny eigenvalue does not prove a physically indefinite mass.
The same diagnostic with normal-only contact has two rows and condition 1.87e8.
[MuJoCo's contact definition](https://mujoco.readthedocs.io/en/3.13.0/XMLreference.html#body-geom-condim)
specifies condim=1 for frictionless contact; coefficient zero alone is insufficient
to request that representation.

An explicit new `contact_model="mujoco_frictionless_normal_v1"` compiles condim=1
on both robot and floor. It requires zero declared friction. Legacy
`mujoco_convex_native` remains the default with unchanged serialized parameters
and XML. This is an actual contact-model representation change, not an invisible
solver patch or a reinterpretation of old results. It requires a new scientific
scope and authorization before formal adoption. Existing execution identity
changes from `ee3f72d465d71cfe4d20ffd25544f2bba28679373fa5270e3920f8416a430c4f`
to `730904cc971dca738d349b2882a03ca9767aeeea6115f21d2bcdf838ff3556e4`.
Candidate configuration identities also change; assembly design, mass, inertia,
stiffness, damping, forces, timestep and physical input values are unchanged.

Under 3.13 AUTO/Newton/implicitfast, both failed candidates now complete 600
engineering steps with finite state, no warning or reset, and at most three
engine Newton iterations. The normal 24-DoF and separately generated 48-DoF
references retain exactly identical qpos/qvel over all 600 steps. These are
engineering comparisons, not successful robot designs or supplied Main answers.

## Shared execution and remaining physical limits

The common `mjcf.compile_xml` owns the option. Native and physical playback compile
identical contact settings, masses, inertias, damping, stiffness, force bounds,
Jacobian, solver and integrator. One direct engineering invocation of the existing
playback function completes 600 steps; sampled qpos equals the baseline harness
exactly. No Store-owned Replay or task evaluator is invoked.

Native's existing contact-free gate is retained. Its own sequence call rejects
the newly touching baseline at step 169 with an explicit contact/constraint
diagnostic. Thus the original 0.6 s baseline is still NOT a valid complete Native
control observation. Engineering numerical completion cannot waive this boundary.
The normal-only contact runs reach about 12 mm of soft penetration and contact
accelerations about 2.27e4 rad/s^2; energy stays bounded (maximum about 0.1311 J),
but contact fidelity/hardware accuracy and task acceptance are not established.

A nine-segment/four-tendon legal FamilySpace generation has 108 declared cells
(expected 216 DoF), but Windows crashes with stack overflow while compiling
`MjModel.from_xml_string`, before an actual nv or integration result is available.
A diagnostic rerun confirms exit -1073741571 and zero steps. The first
uninstrumented attempt had no receipt; its conservative maximum remains 600
steps, although the identical compile failure is the identified lead. No broad
dense override, range shrink, physics change or Windows stack workaround is
silently applied. Full 1--9 segment M1 readiness is not claimed.

## Repeated-failure admission and verification

The existing initial callback now records a baseline identity and stage on real
failure; the original Worker preserves that metadata in its incomplete result.
Identity binds candidate, robot/task/numerical configuration, actual selected
state, baseline schedule and MuJoCo version. Within the same implementation,
original dispatch checks existing settled analysis_results before Worker launch
or another mathematical charge. T1/Direct/objective/window labels do not change
the first physical baseline. Changed legal input/state/execution settings retain
original admission. Method details expose these exact recorded failures without
blanket-banning a method, choosing a design, adding a cache or a state machine.
Failure snapshots distinguish saved pre-call counters from partial failed-call
contacts. `mjcf.py` is now included in original scientific source freezing.

Nine focused tests pass: seven new boundary tests plus two existing source/window
and budget gates. They perform no physics steps or Provider calls. Earlier test
collection accidentally imported an unrelated unittest class; a legacy import,
optional missing C1 archive and sandbox temp-file permissions caused failed
attempts. Final collection is explicitly limited to the nine passing tests;
missing archives were not fabricated. A scratch result serialization error also
required one repeated 168-step engineering reproduction; its cost is retained.

Observed engineering cost is 7,199 step attempts (7,196 returned calls, some
invalid/reset), plus a conservative 600-step bound for the first uninstrumented
nine-segment attempt. Each case stayed within 600; no T1/Direct optimization ran.
Persisted numerical-case integration time totals about 0.592 s, excluding model
build/import, playback and diagnostic overhead. Full private outputs retain costs,
configs, state snapshots, trajectories, logs and hashes. Public JSON is derived.

The sealed Study's 133 file hashes, complete ledger and event count still match:
40 Provider, 14 math, zero Replay, stopped. Nothing was resumed or refunded.
The next freeze must use a new ID, implementation, explicit contact scope,
resolved/approval identities and approved resources. No new identity or Study was
prepared here. Full open-topology launch remains blocked by actual Windows
high-topology compilation and the retained Native applicability boundary; no
budget expansion or automatic use of sealed unused allowances is authorized.
