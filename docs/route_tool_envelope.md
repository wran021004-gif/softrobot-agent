# Real-model tool-call envelope integration

Inspected HEAD: `0b44d38`, branch `feat/independent-spatial-dynamics`; the starting worktree was clean. This change is limited to the shared model transport boundary, focused protocol tests, a preserved response fixture and documentation. No backend installation, physics validation, commit, push or merge is part of this pass.

## Confirmed cause

The latest matching failure is `runs/route_acceptance_20260918_113918`, session `family-route`. Its saved ledger reports one model request, zero tools, zero backend attempts and zero evaluations; the stop reason is `'reason'`.

- Provider request: `7d6723e52ae3d54801f8c20ec2e54eb1fdd60ea849ff0fccfaf7c7dc51f61367`.
- Raw response artifact: `f8c81d11db64cf9b19728e9eebe45257fd72e22aafc36841d3d5d41384919e9e`.

The request schema required outer `arguments`, `reason` and `tool_version`. The response supplied a single `route.advance` build call, with `arguments.reason` inside the domain arguments and `tool_version` outside, but **no outer `reason`**. `DeepSeekAdapter.decode` indexed that missing field directly, raising `KeyError('reason')`. The old correction handler recognized only tool-count errors, so it stopped immediately. The original request, response, terminal state and budget were inspected read-only and remain unchanged. The complete saved response and its provider tool declaration are copied into `tests/fixtures/deepseek_route_missing_reason.json`, with source artifact references and a hash assertion.

## Minimal boundary change

`ToolEnvelope` in `tools/platform_models.py` is the common source for the provider envelope schema and strict decoding. Required outer fields are `arguments` (object), `reason` (nonempty string, at most 2000 characters), and `tool_version` (exact declared version); `evidence` is an optional array of immutable references. Extra outer fields are rejected. Function structure/name and JSON encoding are checked before constructing a ToolRequest. Nested tool arguments still undergo the existing Host/domain validation.

Outer `reason` explains the tool request. Nested `arguments.reason`, where required, explains the domain action. Likewise, outer evidence metadata and nested route citations have separate roles. Concise English descriptions in the actual provider schema and system instructions explain this distinction. No missing reason is invented or copied from message content, reasoning text or nested arguments.

Malformed envelopes produce `INVALID_TOOL_CALL_ENVELOPE` with exact field paths. Paths below `function.arguments` address fields in its decoded JSON object; the confirmed failure is `choices[0].message.tool_calls[0].function.arguments.reason`. These failures and zero/multiple-call errors share the existing persisted `protocol_corrections_used` allowance. One correction may succeed; another malformed response ends with `MODEL_PROTOCOL_CORRECTION_FAILED`. Invalid responses execute no tools. Saved raw evidence, charged request receipts, turn advancement, model/time reservations, recovery and unknown-request handling remain on the existing path. Transport errors and backend failures do not gain a protocol retry.

## Focused verification and live status

All six selected tests in `tests.test_route_model_protocol.RouteModelProtocol` passed (99 seconds). They cover the actual missing-reason response, a valid synthetic envelope, malformed field/JSON variants, successful correction, repeated malformed responses, mixed envelope/count failures sharing one allowance, the existing count correction, turn/session/project limits, recovery at four seal/state boundaries, and an unrelated transport failure without retry. The actual correction provider payload is also checked for English-only application text. Replay adapters perform no network requests or simulation. Their model-call ledger entries represent synthetic/replayed provider submissions, not actual service usage. The full suite was not run.

The current process has no `DEEPSEEK_API_KEY`; no live acceptance was attempted. Thus real-model completion after this parser change remains unverified. This pass has zero actual model requests, backend attempts, integrations or evaluations, and makes no new robot task-success claim.

For one new real-model acceptance in the existing credential-enabled environment, retain the prepared task, tolerance and budgets (10 model requests, four charged backend attempts). Let the model select operations; do not provide offline decisions or reopen the failed route:

```powershell
Set-Location D:\softrobot-agent
conda activate softagent
if (-not $env:DEEPSEEK_API_KEY) { throw 'DEEPSEEK_API_KEY is required in this process.' }
$freshRoute = "runs/route_envelope_$(Get-Date -Format yyyyMMdd_HHmmss)"
python examples/workbench.py platform route prepare $freshRoute
if ($LASTEXITCODE -eq 0) { python examples/workbench.py platform route start $freshRoute }
$routeExit = $LASTEXITCODE
python examples/workbench.py platform route status $freshRoute
python examples/workbench.py platform route result $freshRoute
Write-Output "Acceptance exit code: $routeExit"
```

Assess explicit evaluated delivery separately from `task_success`. A valid evaluation missing the unchanged 10 mm tolerance is not a parser or program failure. No physics/control tuning is needed to validate this protocol fix.
