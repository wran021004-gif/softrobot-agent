# Numerical diagnosis nd1011

Use the existing mechanics-control worktree and `D:\softrobot-agent\.mainline5-env\Scripts\python.exe`.
The specification is `examples/numerical_diagnosis/specification.json`; nd1011 starts at the actual goal clock, 2026-10-11 21:26:41 Asia/Shanghai.
Historical studies remain sealed. No application model endpoint or credential probe is permitted.

Prepare with `python -m tools.research_core prepare --spec examples/numerical_diagnosis/specification.json`, commit the implementation/specification, then bind using the same module's `bind` command. Commit subsequent repairs and use `migrate --reason ...`; retain all counters and clocks.

`tools.research_core_numerics.import_history` verifies archive/member hashes and imports the retained mechanics candidate and two update-1 inputs with original source ownership. The current controller record links the original serialized problem; the older controller input and offline checkpoint lack the original serialized resolved problem. Large graphs stay in the historical archive.

Before numerical dispatch, record the question, changed factor, fixed conditions, discriminating observation and maximum cost through `numerics.experiment` or a native engineering `diagnose` plan. `mechanics.dispatch` runs one `inspect`, `integrate` or `solve` configuration per reservation. Independent substeps 1, 2 and 4 are three integration jobs. The legacy `bdf_replays` counter now counts all independent forward integrations in this diagnostic specification. Inspection of saved residuals does not integrate a new trajectory.

Maximum costs: local worker 150 seconds per solve (300 for one counted prefix plus a reused solve), inspection 120 seconds, integration 450 seconds, offline solve 900 seconds, complete physical execution 1900 seconds. A refinement reserves one independent verification job and 450 seconds before starting, retains the reservation until its own schedule is integrated, and is rejected if it cannot fit. One further identical physical launch is protected before the first launch; `execute(..., role='diagnostic_repetition', selected=result_ref)` may repeat an evaluated failure. Internal NMPC computations remain part of the enclosing physical execution.

Production comparisons retain original tracing and all stopping options. Fixed-work diagnostics disable feasible-return wall timers and IPOPT CPU/wall limits, cap callback work, retain convergence termination and an external process timeout. A reused comparison performs a separately charged identical-input prefix; it does not claim to reproduce the original preceding update. Tail preparation is an explicit factor.

Use `recover` for pending outputs, never silently repeat computation. Finish by sealing with an engineering STOP that cites every new result and exporting the existing immutable archive/manifest. Record sampled acceptance separately from dense diagnostics and do not infer stable parameter rankings from unrepeated time-limited runs.
