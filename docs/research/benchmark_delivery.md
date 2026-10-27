# Local benchmark delivery

Run from this worktree with the project's MuJoCo/NumPy/Pydantic environment:

```powershell
python -m tools.research.benchmark_delivery export
python -m tools.research.benchmark_delivery list
python -m tools.research.benchmark_delivery view --task BF7 --condition positive_high --witness bf7-r2
```

Exports go under ignored `runs/b_line_delivery`; do not commit or publish this directory. The index is the authoritative inventory: the exporter retains distinct accepted witnesses, and writes rejected or incomplete evidence to `audit_failures.json`. Existing directories not listed in the index are not part of the current export. Each indexed case has a standalone `replay.py`, model, frozen task, tension and state CSVs, force schedule and provenance. Read its README and hardware notes. Use `--headless` for an engineering replay with sampled position and velocity differences. This is not a new independent scientific acceptance.

For historic B3, the request ID saved in the replay object is resolved through the original Store call receipt to the actual execution ID in the acceptance and inline profile. The reconstructed XML must match the original SHA-256. BF7 R2 conditions are separate accepted executions, not a joint SELECT. BF7 native refinement has only two individual accepted conditions.

The discovery sources currently cover local B-line worktrees, their fixed-program B1/B2 archives, BF1/BF2 archives and Study Stores. Historical sources with missing or inconsistent data are refused; this does not establish that no other evidence exists elsewhere. Export never searches for new controls.
