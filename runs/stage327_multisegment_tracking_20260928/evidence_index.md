# Stage 3.27 artifact index

Start with implementation_report.md, deterministic_audit.json, failure_diagnostics.json and live_gate_decision.json. The single deterministic task failed; no live session or provider delivery occurred. Historical baseline/negative evidence is referenced by baseline_record.json without duplication.

Implementation commit: 3fa014cc12a9878e48d24159f90548bc28c589c8. Frozen computational baseline: 2b2fb6da3e941f3c939fe79e3fb1dbf5b9096aef.

The deterministic/platform.sqlite Store contains the immutable candidate configuration, numerical preparation, simulation/evaluation/report and backend export closure. Read it with tools.platform_store.Store; artifact_id values below resolve in that Store. The archive verification checks all 34 artifact bodies and 73 reference occurrences. Raw trajectory and controller observations are also retained as files. Locks, authorization anchors and redundant incremental nmpc_updates.json are excluded.

There are no live candidate builds, candidate-bound analyses, raw provider requests/responses, protocol corrections or final provider text: the failed deterministic gate prevented that stage. live_input.json is an unexecuted conditional input; provider_delivery_review.json records not_performed.

## Evidence bindings

```json
{
  "candidate": {
    "candidate_id": "parameterized-tracking",
    "configuration": {
      "artifact_id": "acc3107480f65492fa8024434cd16ad2f9f108bdfef0f01be48b18416ebbe30d",
      "media_type": "application/json"
    },
    "frozen_baseline_identity": "e82116094cd94f93126929585a8535d03044837ff1c9e88108dbda4b1ab6c5cd",
    "effective_identity": "e82116094cd94f93126929585a8535d03044837ff1c9e88108dbda4b1ab6c5cd",
    "owner_run_id": "gvs-stage327-multisegment-20260928",
    "execution_id": "6e54d5b00a9e4447a78000dc470ebf1e",
    "parameters": []
  },
  "configuration": {
    "artifact_id": "acc3107480f65492fa8024434cd16ad2f9f108bdfef0f01be48b18416ebbe30d",
    "media_type": "application/json"
  },
  "execution_id": "6e54d5b00a9e4447a78000dc470ebf1e",
  "simulation": {
    "artifact_id": "cf694c9d665be55655ff82c23357f14543d53a283046cf501c86ab241da9f0c3",
    "media_type": "application/json"
  },
  "evaluation": {
    "artifact_id": "7a835ead847c89b9c973c52e496b63fb663882fe36382515a49627bef8c30c14",
    "media_type": "application/json"
  },
  "report": {
    "artifact_id": "1efc533fddc93115823aeee4d8d2896c0156829e7ecdcc100a3609247305db81",
    "media_type": "application/json"
  },
  "motion": {
    "artifact_id": "b7f6d1782aeef75778efdce3fe3f6818f00adec4d658bdda8a5bb174a8e138d9",
    "media_type": "application/json"
  },
  "reference_identity": "d26a8eeba954f122653b24cc25519f1446d457e163ed7135db263edd8441c7e2",
  "task_identity": "032622bc8070a7383892e51f8e04031afbb9c718720a3319a79645f981c46cee",
  "robot_identity": "ba16d1977581e01edd9b36839eedc9c8e29b4255fb7f94576264cc4ef353899a",
  "candidate_analysis": "Not required by deterministic public chain; no Route build or historical analysis substituted"
}
```

## Repository-byte checksums

Hashes below are SHA-256 over staged Git blob bytes (LF-normalized text; exact binary bytes), not Windows checkout text bytes. This index excludes itself.

| Path relative to this directory | Bytes | SHA-256 |
|---|---:|---|
| archive_verification.json | 313 | cf8df3b8b1a9ba74d3c5ae93847d1aeaa8e176616a1fbbc0e5c3672109ec6e76 |
| audit_deterministic.py | 5900 | 257e8896771b968637ab0752e787624823ecb218791cc5d92d5bb199e53e3f87 |
| audit_usage.py | 3062 | 5503f193f2a6092d2911a137c6b2e38d48301d0f967574c4e2ab4701734c11c3 |
| baseline_record.json | 1375 | 3d08efcb6f2942959f7d37451a2144c0c6f2cd093176bf368693154a7b4dcfe9 |
| code_identity.json | 802 | 5e61b82628c3a816526e4fdf12f52ff2cec4f2bad34f197629a4b8bb01172fc9 |
| deterministic/assessment.json | 4958 | 0894bffc08bfa9065400034f7ac14f1683d96d2736bd4985a42b64cb291ec0bd |
| deterministic/describe_receipt.json | 763 | db72f63090cd4b43ed9764659beca922db7ac4d73854b1dc4f1242074139857a |
| deterministic/evaluate_receipt.json | 750 | fec7c58672658d2b75ef26f76bb092975359b412beb2759afc6a65ddc161d4a1 |
| deterministic/input.json | 34554 | ddf0917fbfade61237c1d83c19980d619bd88d467941f25ac2ae4281280ce186 |
| deterministic/platform.sqlite | 5627904 | 0af5ad99c140597b3802cd4451aaaf5b7b4b32c9b25db40bf04a586913a32d3c |
| deterministic/report.md | 2030 | e4399b99e4677fa90586ead2ec28495344848df8c3bfe1fbd4b893ee02f42cd8 |
| deterministic/report_receipt.json | 759 | 8d73084f5ff91ce27c5d9ed94dc0a5f9d3fcdfa4288a32eb3bbe83bd86a126b4 |
| deterministic/sessions/gvs-stage327-multisegment-20260928/executions/6e54d5b00a9e4447a78000dc470ebf1e/backend/actual_commands.json | 56734 | 7596d374ee0e2db3263ed2aa915301b365f35cffdd6daa8f7245b3f57111370b |
| deterministic/sessions/gvs-stage327-multisegment-20260928/executions/6e54d5b00a9e4447a78000dc470ebf1e/backend/compiled_physics.json | 10821 | d90134de48b44f6de43e4302771f2bad8fbdabd74e92683ebc75306ebdcabb59 |
| deterministic/sessions/gvs-stage327-multisegment-20260928/executions/6e54d5b00a9e4447a78000dc470ebf1e/backend/control_spec.json | 41056 | 0322bee6f066a0e943d692113e8d618c558fde547ea1a5b4379a308cc6dd969c |
| deterministic/sessions/gvs-stage327-multisegment-20260928/executions/6e54d5b00a9e4447a78000dc470ebf1e/backend/controller_observations.json | 620086 | f6f167d7070c16ddcf10b06844484b5550bb6855d223e12da94bb02d507d4472 |
| deterministic/sessions/gvs-stage327-multisegment-20260928/executions/6e54d5b00a9e4447a78000dc470ebf1e/backend/dynamics_execution.json | 1380 | cc1a84dd1af99bacb73da26503126fd6466ba47a98b3914ea1845d4744ff18d6 |
| deterministic/sessions/gvs-stage327-multisegment-20260928/executions/6e54d5b00a9e4447a78000dc470ebf1e/backend/experiment_scene.json | 53450 | d5b54b26371fffe660fc7914e3c9ae9df83e666767224c7ab3fbcd962c9043e4 |
| deterministic/sessions/gvs-stage327-multisegment-20260928/executions/6e54d5b00a9e4447a78000dc470ebf1e/backend/experiment_spec.json | 996 | 8958b70c1b278c8b4cb0d5d90e2388b3046a374072393cc70bd573ef2dc4124b |
| deterministic/sessions/gvs-stage327-multisegment-20260928/executions/6e54d5b00a9e4447a78000dc470ebf1e/backend/model_discretization.json | 196 | 78cd2ec722dc09ccd1cc0080958ba4a2d67b52c6d46c170c28c86c86637258ba |
| deterministic/sessions/gvs-stage327-multisegment-20260928/executions/6e54d5b00a9e4447a78000dc470ebf1e/backend/resolved_physics.json | 351570 | 14f96c10f63e28483943ba745257453b942219368548b970c1be1fe152460720 |
| deterministic/sessions/gvs-stage327-multisegment-20260928/executions/6e54d5b00a9e4447a78000dc470ebf1e/backend/result.json | 1066661 | b060061b72341b4b34f8d2ed7246b733333837e1b1c49b20349db3c96c9b2036 |
| deterministic/sessions/gvs-stage327-multisegment-20260928/executions/6e54d5b00a9e4447a78000dc470ebf1e/backend/robot.xml | 101776 | 9a061d3ae0b60a51c833211b2fda4cf71e7352fb85738b1b2a4ebfa634084b1f |
| deterministic/sessions/gvs-stage327-multisegment-20260928/executions/6e54d5b00a9e4447a78000dc470ebf1e/backend/robot_description.json | 20851 | 319dcfdb35c7470ec1c0978806da7404abf02ca90074ffbc2a20f274e6cca243 |
| deterministic/sessions/gvs-stage327-multisegment-20260928/executions/6e54d5b00a9e4447a78000dc470ebf1e/backend/solver_configuration.json | 172 | c7a9f804d5e3f799d274c47a74131d868aee6f20221e9b545283d2fc054f9737 |
| deterministic/sessions/gvs-stage327-multisegment-20260928/executions/6e54d5b00a9e4447a78000dc470ebf1e/backend/trajectory.json.gz | 445989 | ac33eac2f0c2c43ec5b68f4fc6c221c11f50ea698b3221fc39b6036bf8faa041 |
| deterministic/simulate_receipt.json | 784 | 9bd70552f1d46de0e099612ddbc02b90068a36284fbac6846d28029a36758f00 |
| deterministic/summary.json | 70719 | e582c9fdd9b90c11d491503044a24dd4fa040ef54cc6162126f514f5feaa9f59 |
| deterministic/workflow.json | 345 | 25e630a0d63e93b5c76d6189d3a4fae6a42670096fc9c4c0e44e5de90d2a693d |
| deterministic_audit.json | 27881 | 2000cd3fa42ef67ca87075067dc2624935b66a1132adb7e12600805223a3b813 |
| deterministic_console.log | 6730 | f5cac387b9ad7f92dddd0f012153d6056fe67dafc8b87e2f39b6bcb7e1d7b5e8 |
| environment.json | 442 | 7bcfb3e28efc7876b3045fcd06ac1dce3fbb04735d7d91d56df68fe59c49f19f |
| failure_diagnostics.json | 13365 | 1a0500bd7361e1247076f511d0b673e65ba51538f2d4adce78359345e9fe2591 |
| failure_diagnostics.py | 3783 | 6b4a6067dfaa88c805fce1fbd0ed2c9ed66d39293ca6ccfcae4740d9062eea18 |
| freeze.py | 3135 | c2a55026fa7f86c568c6c424e3dcdbb533306dba1431e22258099d482d00c873 |
| frozen_input.json | 34554 | ddf0917fbfade61237c1d83c19980d619bd88d467941f25ac2ae4281280ce186 |
| implementation_report.md | 8834 | 7808e65a17a2b25f00bec507ea58fd638948aa6923520b132dbd52b8a90c6389 |
| live_gate_decision.json | 406 | cb9fc98d131ad5389daf7bf7eac9f7ee928d67ccd269147404a0efae45289090 |
| live_input.json | 39421 | 2a5d709b9f9f6c98250d08c1a6e22d20edfbfcf344e4651b19dda8ab9f57d57e |
| provider_delivery_review.json | 371 | 06fc6598c853a16fecc9b653087f6022b9ec777d47abdf00363839f50f96924b |
| usage_audit.json | 2547 | 24dd955decc8eada416d4606c86475fc9725ea33c110f7f852ecc9b8cef8a306 |
| verification_results.json | 794 | f7563bd14f8b2cf96cd2e82166ef070d6aaebe8ba47b2c17cec6ea410e73b841 |
