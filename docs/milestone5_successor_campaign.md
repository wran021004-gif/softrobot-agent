# Milestone 5 successor checkpoint — 2026-10-05

This is the user's requested **commit/push checkpoint**, not completion of the
campaign. Milestone 5 remains open. The successor starts at
`c848fea82856971777397d83fa95330d8c50a6c5`; all previous STOP/NO_GO decisions,
charges and evidence remain unchanged. The historical v7 incumbent remains
candidate `batch-ebbeadbdaca10732-0`, execution
`91c3ba1b01d6499fb26df8f95409401b`. Milestones 2–4 remain closed.

## Completed evidence and implementation

The user explicitly approved targeting the existing **0.5 ms backend transition**
for this round's local prediction, with separately versioned numerical rules.
There is no meaningful two-level tolerance in the direct linear solve. Protocol
`fixed_backend_transition_validation@2.0.0` instead checks a separate Cholesky
implementation against saved LU results, per-step scaled residuals, backward
errors, conditioning and local linear-algebra error estimates. State, input,
physical step, output times, physical parameters and accuracy limits are fixed.

All six cases pass position, speed, velocity-vector, direction and numerical
checks, with zero local position/speed false-safe or false-unsafe results. Maximum
backward error is approximately `1.53e-16`; the maximum independent solver endpoint
velocity difference is approximately `6.36e-17 m/s`. These are fixed-discrete-map
checks, not continuous accuracy, hardware credibility, global error bounds or
independent backend validation. The old continuous comparison and physical-step
sensitivity remain visible: continuous-versus-backend position differences are
approximately **2.18–36.02 micrometres**.

Saved histories localize the first command divergence to 0.02 s in original
histories and 0.01 s in reset histories. At that point current states and previous
inputs match, but the old forecast continues its plan while production replans.
The new experimental history implementation replans every configured update,
retains each candidate's own state and plan, and seals commands before its own
emulated advance. Its five-update numerical experiment has **not run**.

An execution-scoped function provider in `gvs_trajectory.py` permits experimental
evaluation without changing the default production function or mutating its
cached object. The native implementation preserves equations and exact AD, and
checks both the DLL hash and physical-function identity before reuse.

The successful `gvs_native_chunked_kernel@2.0.0` partitions generated force and
full-Jacobian code at complete MX-operation boundaries into functions containing
at most 250 operations. Scalar and read-only pointer temporaries persist across
chunks. All six residual/Jacobian comparisons pass. Median speedup against the
saved same-input baseline is **1.6555×**, with measured force-plus-Jacobian times
**43.5–64.1 ms**. Compilation took 599.757 s, charged within the 612.141 s phase.
These are single samples per point, not complete-control timing or a latency
distribution. Even this kernel exceeds the complete **10 ms** deadline.

Negative results are retained: scalar expansion, unoptimized native variants,
scalar reverse AD, split/shared-runtime variants and the equivalent mass-form
expression were slower. Monolithic and attribute-only optimized builds timed
out. Failed compiler children and one receipt-format failure were recovered and
charged, including conservative cleanup time. Separate translation units solved
the build problem but did not themselves accelerate evaluation. The attribute
experiment follows [Clang's documented `optnone` behavior](https://clang.llvm.org/docs/AttributeReference.html#optnone).

Two authorized native DeepSeek calls, including one factual correction, advised
continued bounded development and NO_GO for admission at that earlier state.
Their original and corrected answers are retained. They **do not assess the
subsequently completed successful full-Jacobian kernel**.

## Acceptance and remaining work

| Requirement | Checkpoint result |
| --- | --- |
| Approved fixed-step local numerical and quantitative checks | 6/6 pass; limited scope above |
| Complete feedback and position classification | Implementation prepared; full-history repair unvalidated |
| Feasibility-qualified ranking and full operational cost | Still open; preserve original/reset failures, useful historical comparisons 0/2 |
| Complete production update ≤0.01 s | Not met; no new complete update measurement |
| Current native research admission | Not obtained for the final kernel |
| Two untouched paired scenarios and independent repeat | Not admitted or executed; all six backend slots preserved |

Actual exclusions and savings remain zero. Historical forecast costs and outcomes
are retained as development evidence; they do not validate an altered controller
or provide economics for the new implementation. Full-order physics emulation
is still diagnostic work, not a cheap reduced predictor or independent backend.

Next bounded command in the existing workspace:

```powershell
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' examples/milestone5_successor.py --phase feedback-component-full-chunked
```

It checks two nonzero-acceleration points, then measures original075's first three
and reset075's first two actual complete command boundaries, using their own
causal full-state histories. This is development only. Subsequent work must repair
both complete histories, establish useful ranking and all-in economics, meet the
production deadline, obtain current admission, and only then freeze and execute
the prospective pairs and fresh repeat. The experimental controller retains timed
stopping; acceleration can change its response, so old backend outcomes cannot
automatically validate it.

## Accounting and reproducibility

| Scope | Charged seconds | Provider | Workflow | New full backend |
| --- | ---: | ---: | ---: | ---: |
| Successor actual | 3,420.897 | 2 | 21 | 0 |
| Fullscope + successor actual | 4,358.759 | 5 | 31 | 0 |
| Remaining shared authorization | 25,641.241 | 15 | 129 | 6 |

Successor numerical work: six local propagations / 120 emulated steps, 54 kernel
point evaluations, zero controller solves and zero complete forecasts. Development
has 7,641.241 s / 3 provider / 69 workflow remaining; this includes the protected
1,265 s finalization allocation. Three validation allocations separately protect
18,000 s / 12 provider / 60 workflow / 6 backend attempts. Lifetime totals are
separate: 12,689.422 s / 53 provider / 135 workflow / 8 backend attempts. No workers.

Eleven focused checks pass: seven historical checks and four successor checks
covering the fixed recurrence, rejection of non-SPD systems, scoped evaluator
isolation and command sealing before causal advancement. Numerical/provider work
was not replayed to test or export wrappers. No new experiment was started after
the checkpoint request.

The existing Conda environment was not upgraded. A portable LLVM-MinGW compiler
was used under ignored `runs/`. Compiler archives, binaries and large generated
C/object files stay local; exact commands, source/library hashes, versions,
receipts, research artifacts and implementation snapshots are exported. This
checkpoint is not a self-contained binary installation: rebuilding requires the
recorded toolchain and predecessor inputs. The next command can reuse the verified
DLL already present in this workspace.

Evidence: [acceptance audit](../evidence/milestone5_successor_20261005/acceptance_audit.json),
[assessment](../evidence/milestone5_successor_20261005/assessment.json),
[accounting](../evidence/milestone5_successor_20261005/accounting.json),
[fixed target protocol](../evidence/milestone5_successor_20261005/fixed_target_protocol.json),
[successful kernel](../evidence/milestone5_successor_20261005/native_full_chunked.json),
[file hashes](../evidence/milestone5_successor_20261005/sha256_manifest.json).
