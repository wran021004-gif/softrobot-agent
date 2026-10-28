# English-native research decision architecture: implementation status

Status: **incomplete engineering increment; not ready for a fresh Study**. The integration base was `91573147e7a2bdf0044cf9621fbf4929568d9377` on `codex/agent-guided-codesign`. The role-profile boundary below is implemented and tested offline. The English-native evidence boundary, decision brief, actual tool-schema projection, token-triggered handoff, and independent fresh Study remain outstanding. Do not launch a Study on the strength of this partial increment.

## Ownership and evidence boundaries

`config.py` resolves and freezes new Study inputs; `schemas/platform.py` validates provider configuration. `agent.py` owns the Strands request, native tool registration, accounted transport and recovery. `research_context.py` derives decision context and navigation; `reporter.py` assembles read-only interpretations, validates cited sources and archives provider output. `provider_context.py` guards complete serialized requests; `session_handoff.py` verifies settled boundaries and SDK snapshot restoration. `core.py`, `evidence_policy.py`, `evidence_views.py` and the registered evaluator retain evidence identity, formal reads, admission and task acceptance. The Reporter does not grant formal read credit.

## Optional frozen role policy

A new Study can add this object within `research_decisions`. The example is configuration only, not execution authorization:

```json
"role_policy": {
  "version": "research_roles_v1",
  "main": {"thinking": "disabled", "reasoning_effort": "none", "max_tokens": 4096},
  "reporter": {"thinking": "enabled", "reasoning_effort": "low", "max_tokens": 2048}
}
```

The resolver freezes the Main settings into the existing provider configuration. Reporter settings are frozen in the same Study policy and overlay only its three inference fields. Model, endpoint, credentials and the shared Store ledger remain common. `LiveBoundary` checks the role's actual wire before a send or exact replay, retaining the existing request hash and receipt checks. A Study without this policy retains its frozen provider behavior. This option alone does **not** enforce English or establish the requested new-Study architecture.

DeepSeek documents these Chat Completions values at [the API reference](https://api-docs.deepseek.com/api/create-chat-completion/). No live provider call was made.

## Offline verification and outstanding work

The following focused command passed eight tests using the existing `.f3-prestudy-env` Python: `python -m unittest tests.research.test_s129_agent_reporting.AgentReportingTests.test_role_policy_freezes_new_study_without_reinterpreting_old_study tests.research.test_s129_agent_reporting.AgentReportingTests.test_versioned_roles_share_ledger_and_reject_wrong_wire tests.research.test_s129_agent_reporting.AgentReportingTests.test_legacy_saved_reporter_response_recovers_without_resend_or_new_charge tests.research.test_provider_context.ProviderContextTests`. Tests use Store fixtures and mock HTTP; no provider or scientific worker was launched. A first attempt with `.mainline5-env` failed five provider-context tests due to missing `matlab.engine` and `tokenizers`; the prepared environment passed them.

No new full-wire baseline or after measurement has been produced. Earlier C3 measurements in [the integration audit](agent_guided_codesign_increment.md) describe a different saved scenario, not a measurement of this change. A complete-request fixture measurement and extra-turn accounting remain required. No frozen P2/P3 configuration or archived evidence was edited.

Before a fresh Study can be prepared and accepted, implement and validate the remaining English-native source and legacy-withholding contract; compact decision brief and provider tool definitions; Reporter trigger and acceptance boundaries; and token-based safe handoff. Then prepare a uniquely identified zero-spend pending-approval Study using existing task and evaluator contracts. Explicit finite launch authorization is still required.
