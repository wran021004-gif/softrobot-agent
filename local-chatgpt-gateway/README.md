# Local research ChatGPT Gateway

This directory owns the loopback HTTP gateway, Responses conversion and tests.
It contains no credentials, account state, installed modules or copied DevKit.
The existing OAuth/DPAPI/plan-usage controls remain authoritative. No backend-api,
paid-key fallback, hosted tools or limit bypass is implemented.

## Dependency and source ownership

Obtain the official Sign-in with ChatGPT DevKit commit
`0a36fefeb913055c8c7a1a29b63d82b96b2e841a` independently. Its package is a private
workspace, not assumed to be published on npm. From this directory run:

```powershell
node scripts/prepare-devkit.mjs PATH_TO_PINNED_DEVKIT
npm ci --ignore-scripts
npm test
```

The preparation script verifies the two changed upstream source hashes, copies
required sources/license/notices to ignored `.devkit`, and adds one optional
inference callback inside the existing authenticated operation. It does not expose
credentials via getSession, change refresh/consent, alter scopes or replace OAuth.
All other upstream authentication and storage code is unchanged. The DevKit's
Noncommercial License v1.0 still applies; read its LICENSE and notices in .devkit.
The dependency lock pins the installed versions. Existing .devkit is never erased.

## Interface

Authenticated loopback endpoints: `/health`, `/v1/models`, `/v1/chat/completions`.
The completion endpoint accepts text strings or text blocks, function definitions,
assistant function calls, matching tool results, and reasoning_effort none/medium.
Function tools are sent in a `research` namespace. Actual call IDs and completed
opaque reasoning items survive continuation. Input is explicitly replayed; upstream
requests always set store:false and stream:true, with no previous_response_id.
Only a terminal response.completed is successful. Incomplete streams, policy errors
and interruptions never produce successful tool calls. Usage is passed through when
present; missing usage is unknown. No prices or cheapest model ordering are inferred.

These mappings follow [plan-usage restrictions](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
and [models/inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference),
checked 2026-10-28. Model/account support for tools and none/medium still requires
an explicitly authorized real test; conversion support is not model verification.
Images and other modalities, hosted tools, output caps and non-auto tool choice are
explicitly unsupported here. The 1 MiB body limit includes tools and replay history.

`npm test` uses mocked remote OAuth/inference and isolated temporary storage. Real
Windows DPAPI/CLI checks do not sign in or perform inference. Production login,
model discovery and smoke are separate explicit operations requiring authorization.
No real account/network verification was performed for Harness V2.

`npm run smoke -- --model <active-account-slug>` requires an explicit model and
sends exactly one text request with `reasoning_effort: none`. Missing or unlisted
models send no inference. Catalog order is not a cost ranking. Smoke has no
medium option; a separately authorized medium probe needs model support evidence.

## Harness configuration

Use `configs/research/runtime_chatgpt_gateway.example.json` as an incomplete
template. Select a model from the active account's actual directory; do not take
the first entry as a cost recommendation. Set its verified model capabilities,
context capacity and source. Keep authentication only in
`~/.softrobot-agent/chatgpt-api.json`; base_url there may omit `/v1`.
The new Harness refuses live sends for offline-only model capability fixtures.
Main and Reporter may select different explicitly configured models and reasoning.
