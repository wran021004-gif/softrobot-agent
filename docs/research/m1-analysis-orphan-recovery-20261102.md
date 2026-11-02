# Contained analysis orphan recovery

The original 1800-second supervisor boundary stopped a joint-search parent and
its contained analysis Worker before the parent could write `boundary.json`.
The original analysis recovery correctly retained the pending call, but exposed
no trusted operator entry to record the already exited analysis process.

`analysis.record_orphan_exit` now binds the unsealed original request and
execution directory to its durable Worker lifecycle, exact command/request path,
implementation and runtime metadata. `execution_worker` installs a Windows
kill-on-close Job before writing that runtime metadata. The existing Windows
process observation must independently prove the original PID exited; a live,
inaccessible or reused PID remains blocked. No Agent tool exposes this function.

The function writes a separate immutable `recovery_boundary.json`, preserves an
existing original boundary, records no invented return code, and labels elapsed
time as a conservative upper bound through the exit observation. Analysis
recovery accepts that verified boundary and seals the interrupted result under
the original request with partial numerical observations and all original costs.
Existing core recovery packages the interrupted search without relaunching it;
SDK feedback recovery pairs that receipt without repeating completed tools.

Four targeted offline Store tests passed: original identity mismatch; live or
unknown PID retains pending state; verified exit is idempotent and seals an
incomplete unmeasured result with partial cost and no relaunch; and preservation
of the original boundary. The Windows long-path representation is normalized
through the existing `io_path` helper for exact path comparison. No Provider or
scientific Worker was invoked by these tests. Task acceptance, scientific methods,
budget limits and historical results remain unchanged.
