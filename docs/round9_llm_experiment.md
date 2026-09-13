# Round 9 runtime correction and llm_reach_v1

Reviewed baseline: `95a0276`, branch `feat/round9-matlab-dynamics-design-loop`.

The current implementation adds one correction for an invalid tool-call count,
English runtime instructions, question-driven evidence progress, and one persistent
experiment inside the existing campaign. Numerical implementation, source identities,
task, duration, evaluator and campaign grant remain unchanged.

## Commands

Use the existing `softagent` environment in `D:\softrobot-agent`. Start once:

```powershell
python examples/workbench.py dynamics experiment-start --root runs/round9_reach --experiment-id llm_reach_v1 --steps 24
```

Resume the saved experiment after making `DEEPSEEK_API_KEY` available to that shell:

```powershell
python examples/workbench.py dynamics experiment-resume --root runs/round9_reach --experiment-id llm_reach_v1 --steps 24
```

`--steps` bounds new model requests in this invocation, including corrections. It
does not replenish either budget. Repeating start is idempotent; resume requires
the existing experiment. The ordinary dynamics resume path also honors an active
experiment's saved limits. No credentials are written to artifacts.

## Correction and effective prompt

Provider responses are saved before interpreting tool calls. Zero or multiple
calls dispatch nothing. `state.json.tool_call_corrections` records the original
response, count, proposed names and the one allowed corrective request. The compact
English correction travels through `build_model_request()` with current evidence
context. Its request row, correction link and campaign/experiment charge are saved
before HTTP I/O. Another malformed correction pauses; another resume cannot grant
a second correction for that failure. Missing responses retain conservative activity
reservations. No request budget leaves the correction pending.

The effective prompt version is `dynamic_english_question_reading_v2`. It replaces
the historical Chinese-statement instruction in memory and appends explicit English
output and question-driven reading instructions. The original prompt file and old
version records remain intact; actual requests save the effective version through
the existing `inputs/prompt_versions/` mechanism. No translation service or language
retry/filter was added.

Each request includes phase/objective, specific questions, recent findings, next
decision and the last three successful reads. Evidence pointers, offsets/ranges,
continuations and source hashes come from persisted attempts/results. An unchanged
repeat gets a notice; legitimate pagination and child reads remain available.
`has_more` is not an instruction to scan every page. The complete UTF-8 JSON request
cap remains 60000 bytes with a 50000-byte target; bounded evidence pages are retained.

## Experiment accounting and authorship

The baseline is the existing unsuccessful V2 c032: MuJoCo error
`0.014192521136991725 m`, with the unchanged `0.01 m` threshold. The saved experiment
records starting request/decision positions, existing candidate IDs, starting
campaign counters, and ceilings of 24 requests, 40 MATLAB dynamic trials, 3 MuJoCo
trials and 1800 activity seconds. These remain subordinate to campaign remainders
and closeout reserves. Each new search batch is at most 24 trials. Force stays 20 N.

DeepSeek chooses the hypothesis, variables and settings using existing tools.
Deterministic MATLAB search continues generating trial values. Decisions, receipts,
searches and newly generated candidates record the originating model request and
decision; candidate/search-trial provenance also names the generator and search.
Numerical actions are restricted to c032 and new experimental descendants.

Fresh completion requires a new experimental MATLAB search trial and fresh MuJoCo
verification of it or a subsequent experimental adjustment derived from it. Cache
reuse and old candidates cannot supply those receipts. Closeout tracks checked
experiment diagnoses and `stop_design`, with separate workflow, numerical experiment
and MuJoCo-success fields. The workbench exposes errors/corrections, counters and
baseline/best new playback links generated exclusively from saved trajectories.

c057/c065/c066 are historical MuJoCo successes; c066 has the smallest reported error.
Development-time Codex selected the prior 40/24-trial plans; tools generated their
numerical proposals. c065 is the length comparison and c066 the C1-to-C2 comparison.
None of this is attributed to runtime DeepSeek.

## Validation and current outcome

Only the three focused offline groups were run:

```powershell
python -m unittest tests.test_dynamic_runtime -v
```

All three passed: count correction/recovery/accounting; evidence progress,
pagination, effective English and request bytes; experiment provenance, cache
exclusion and resource ceilings. The interruption/activity and descendant-adjustment
cases were checked again after their targeted fixes. Provider and solver doubles
are confined to `runs/round9_runtime_tests/`; their synthetic results are not live
experiment evidence. No full suite, solver sweep, historical replay or endurance
campaign was run.

The real start command above was executed. The execution environment has no
`DEEPSEEK_API_KEY`, so the campaign is `WAITING_FOR_KEY` and llm_reach_v1 is **NOT_RUN**.
Starting positions are model request 47 (next ID `047`) and decision sequence 70.
Request `046` remains failed and unchanged, with its original two calls unexecuted.
Its correction is **pending**, with no corrective request allocated or sent yet.
Assuming no intervening action, resume will issue corrective request `047` linked
to `046`, charged within the experiment's 24-request ceiling.

Actual new model/MATLAB/MuJoCo counts: **0 / 0 / 0**. New experiment candidate IDs:
**none**. Current complete request including progress and the pending correction:
**32673 bytes**. All 67 historical candidate records, the original 046 row/response
and original prompt were verified unchanged.

Local delivery:

- Workbench: `runs/round9_reach/index.html`.
- Baseline playback: `observations/c032_matlab.html` and
  `observations/c032_mujoco.html` under the campaign. No new best exists yet.
- Metadata/results: `experiments/llm_reach_v1/experiment.json`, `summary.json`,
  `preparation.json` and `validation.json` under the campaign.

Implementation and offline validation are complete. Runtime workflow completion,
new numerical experiment completion and new MuJoCo task success are all unverified
because the live experiment has not run. Historical success remains separate.
