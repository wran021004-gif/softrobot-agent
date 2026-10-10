# CasADi feedback closeout

This is one new grant, `casadi-feedback-closeout-20261010`, based on fetched
research SHA `d9ce124244697f30df3a609942cb7591c3cf3f15`. The prior activity
is sealed STOP and its 24 sends remain exhausted. Its diagnosis and speed
artifacts are imported unchanged, with provenance and zero new execution cost.

Use the existing environment; do not reinstall dependencies:

```powershell
Set-Location D:\softrobot-agent\.worktrees\casadi-feedback-closeout
$studyPython = 'D:\softrobot-agent\.mainline5-env\Scripts\python.exe'
& $studyPython -m tools.research_casadi_feedback prepare
# Commit the scoped implementation and frozen specification.
& $studyPython -m tools.research_casadi_feedback bind
& $studyPython -m tools.research_casadi_feedback live
& $studyPython -m tools.research_casadi_feedback stop
& $studyPython -m tools.research_casadi_feedback export
```

Preparation preserves the original clock and counters. The specification
records the task-start clock, including engineering. This grant permits two
NLP attempts (one choice per batch), three new BDF replays, 3,600 numerical
seconds, 12 actual provider sends with the last four reserved for feedback and
typed STOP, 48 public calls, zero physical launches, and four hours including
a final 30-minute delivery reserve. The third replay needs a specific diagnostic
question about a new candidate. These ceilings are not permission to restart
after sealing the activity.

Ten focused fixture checks run with `-m unittest tests.test_casadi_feedback -v`.
Their files use the ordinary writable activity `checks` directory. They do not
send requests or launch real NLPs. Record their elapsed time in the activity's
numerical accounting. Historical mechanics, grid and tolerance studies are not
rerun. Local step AD stays reverse; outer NLP derivatives stay exact automatic AD.

Immediately after solver return, `worker_progress.json` saves raw ordered
variables, selected result, retained vectors, diagnostics, timings, grid,
initialization, configuration and original execution provenance. The worker
then calls `package_result`. `recover(checkpoint)` reconstructs that packaging
without invoking IPOPT; it preserves the original identity and solve cost and
reports recovery time separately. The service imports the checkpoint into the
immutable artifact store and attempts one local recovery within the original
900-second worker allowance when export fails. An unresolved extraction or
delivery error pauses the batch and preserves unexecuted choices.

Inspect pending input/output/progress files before repeating any work. A known
killed worker timeout is settled once; an unknown outcome blocks dispatch.
Commit a scoped repair, then use `migrate --reason ...` to preserve the same
grant, task, counters and clock. Dependency compatibility is checked before
each actual provider send, including auxiliary requests. Cancellation exits
to engineering handling. Provider configuration, endpoint and authentication
remain the established DeepSeek client; credentials are never evidence.

`stop` seals either an accepted native model STOP or an explicitly incomplete
engineering closeout. It does not invent a model decision. `export` writes
non-secret plans, results, recoverable checkpoints, candidate schedules, wire
evidence, counters and a hashed artifact archive to
`evidence/casadi_feedback_closeout_20261010`.
