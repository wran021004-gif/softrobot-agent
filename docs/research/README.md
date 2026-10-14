# Research mainline

Run from this worktree with PowerShell. The single editable entry is `configs/research/study.json`, referencing physical robot, task and runtime inputs. Preparation resolves and freezes those values under `runs/research/<study_id>/resolved_configuration.json`. Existing numerical environments are reused.

```powershell
Set-Location D:/softrobot-agent/.worktrees/research-mainline
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$researchPython='D:/softrobot-agent/.mainline5-env/Scripts/python.exe'
& $researchPython -m tools.research prepare
# Commit implementation before binding and numerical dispatch.
& $researchPython -m tools.research bind
& $researchPython -m tools.research run
& $researchPython -m tools.research status
& $researchPython -m tools.research recover
& $researchPython -m tools.research export
```

Study IDs are single use. Never reopen sealed studies or reset counters. Repairs require a commit and explicit `migrate --reason '...'`. Read historical evidence with its original identity; old artifact bytes/hashes remain intact. A timeout is incomplete execution. Provider credentials are loaded only into the process from the existing credential file and never exported.

The 24 provider requests include four protected requests. The 14,400 live seconds include 600 closeout seconds. Independent RL evaluations keep the configured 120-second process cap and also consume the remaining cumulative numerical/activity budgets. Extra confirmations are zero; one independent RL evaluation is still required after training.
