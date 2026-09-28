# Stage 3.26 artifact index

Start with implementation_report.md, local_decision.json and confirmation_audit.json. Frozen benchmark selection resolves to runs/stage325_tracking_efficiency_20260928/selected_states.json at commit 1b4c00f; no historical database or selected-state copy is duplicated. The new confirmation Store retains immutable candidate/configuration/evaluation/report closure. Authorization anchors and locks are excluded. controller_observations.json is retained; the redundant incremental nmpc_updates.json is left local.

Checksums use Git LF bytes for text and exact bytes for SQLite/gzip. The index does not hash itself.

| Path relative to this directory | Bytes | SHA-256 |
|---|---:|---|
| archive_verification.json | 278 | 8e0801c25a359cef9e7b82bb262bd1bc8d4b8537f00ae2655541d29aeb37e5c1 |
| audit_confirmation.py | 6658 | 82a4469e56386ba2c0087d7538ed7dabbeae3be8bdbb2471faab8bff3b7ed71d |
| baseline.json | 247092 | 335acc423dd6dc8f16b50465f3fea7faf313c4dfc1b3c7ddc2d0c0571b7d3e45 |
| baseline_kernel.json | 101696 | 64485f904dbfeb42a43ed93476bdb69c51560c0acf5c9ab1ef8f8bd70298439b |
| code_identity.json | 880 | af39f0cd9e7e1b869254912c5dacace2b72fc37209c9f2d5447a45dd5a0fdd2f |
| confirmation_audit.json | 20077 | 9550931cbad994fbf01bc3bf6d1e0d17f4b789ab24d9a033ae8f7c8a6f853d7a |
| confirmation_input.json | 33903 | 3241f37f827105567e0d21c33fce6e0fe90db530926b40e7cb02f511307cba0d |
| cse_graph_probe.json | 279 | 111f441a2cd08088f454fcfed1b9db13789b9ac5054fe29c9c5dd16e6bab656d |
| environment.json | 517 | 3ac7bbb4397eb6459d02af28f999fea2b75d50c1ba8fb56942950cf5a828de9a |
| frozen_comparison.json | 1635 | 3c015d0d514a4be91ba39671457c11d43d1bc5b787d94771ee1b1a762cfc6ef6 |
| implementation_report.md | 13709 | 0657b4b9c43c37f7e549de20f2feb845f6132ee555975f5ce50c0cfbc5dc5008 |
| kernel_check.py | 3936 | c7ae0fc482983ee52862a9d7e1b6ca2029208f01d0dd523ee10ff69d02bc330d |
| local_decision.json | 1594 | c7b1551338e2d8beff3e4b11e8d8c1661b7bba52c9ebb2652a4f223a4b2f4689 |
| modified.json | 248692 | cef7f29a9444881033d69047a42ed0ee001149d630a8196a46a01bc3f141f310 |
| modified_kernel.json | 102270 | 8e9e905be40666cdf17881379fee845baeb15b608d549bc43c7575ced1cde238 |
| numerical_change.patch | 1004 | a015f8730155650858c61c7d8eceb762db3a873906598c899dd6568d3c4d7b49 |
| plan_verification.json | 1537 | 821a0633362c201732de51687370fdd2834c1e0183e32b68b158ad54963540c0 |
| reproduction.ps1 | 2186 | 1f4fd86e5891d415243e732886c84c87490c155d6f0f3cd7203368147481ac01 |
| verification_results.json | 2575 | c6346e23e01c2e58035e3993743b389be068681ea9c2ca8fa0d11519b25b211c |
| confirmation/assessment.json | 4958 | ec59c957b910fc26d2a63035c976cd74876555b84a5c5443317173e57a55adec |
| confirmation/describe_receipt.json | 763 | da7faa6b7cdd7cfb308f54677758a3163d5da9d4e60bc0097cda9088fc3bfd04 |
| confirmation/evaluate_receipt.json | 749 | 089e85bc50d9268a2f66b3f7e0f4b12c8c41e0f5627c9c3e40daa82f91dd2251 |
| confirmation/input.json | 33903 | 3241f37f827105567e0d21c33fce6e0fe90db530926b40e7cb02f511307cba0d |
| confirmation/platform.sqlite | 4173824 | 93bb8c076ed4fa74e33da8774b7109a8b6b7758c55a2d1e17fcbb7b67fd6d335 |
| confirmation/report.md | 2010 | 6d5feff8f36e41ebd2a809bee496c5cee607ec895aac2626df2c165269ecb445 |
| confirmation/report_receipt.json | 758 | afbe6ff5b2f89deb1e638f8e6857b0a0f9cf9a896c29038ba15d1465a190787e |
| confirmation/simulate_receipt.json | 783 | 4415b64b4d9fb57520c69d8ec3525433ffd3aab12c5e844a1bc34899074d63dd |
| confirmation/summary.json | 49327 | e4bd11316ae0c36991967594cbdf62b17fa78a9a836586149f4d6a8ed568287f |
| confirmation/workflow.json | 345 | 937cf8d4384bf6b2542a0a40130b52f50fe1ce95ab5ebfc0d09f36091895a196 |
| confirmation/sessions/gvs-stage326-confirmation-20260928/executions/67f8d7f01c514dc2bab4085eb008630b/backend/actual_commands.json | 32442 | c44b331829161b5467fd45fe9f84c8606a98746488d18c35c8c7b39119a353b9 |
| confirmation/sessions/gvs-stage326-confirmation-20260928/executions/67f8d7f01c514dc2bab4085eb008630b/backend/compiled_physics.json | 10821 | d90134de48b44f6de43e4302771f2bad8fbdabd74e92683ebc75306ebdcabb59 |
| confirmation/sessions/gvs-stage326-confirmation-20260928/executions/67f8d7f01c514dc2bab4085eb008630b/backend/controller_observations.json | 351887 | 3b7785ce2e47cc46ab1df46c37748d021426340bc8a2e415d4c4e22a88ab3ac6 |
| confirmation/sessions/gvs-stage326-confirmation-20260928/executions/67f8d7f01c514dc2bab4085eb008630b/backend/control_spec.json | 39837 | 500097cc23097f23395d40b67b36419277a93eede868864aee0c988ff966adf6 |
| confirmation/sessions/gvs-stage326-confirmation-20260928/executions/67f8d7f01c514dc2bab4085eb008630b/backend/dynamics_execution.json | 1380 | cc1a84dd1af99bacb73da26503126fd6466ba47a98b3914ea1845d4744ff18d6 |
| confirmation/sessions/gvs-stage326-confirmation-20260928/executions/67f8d7f01c514dc2bab4085eb008630b/backend/experiment_scene.json | 51559 | b4acd565687b91cb05dafa4c4c14267a50545ed68b98d24846b5e43c887bf88c |
| confirmation/sessions/gvs-stage326-confirmation-20260928/executions/67f8d7f01c514dc2bab4085eb008630b/backend/experiment_spec.json | 996 | 913c2f179ab2b10ca62f00b454ee2c5dacc67a894af9109ca46580fe304da46d |
| confirmation/sessions/gvs-stage326-confirmation-20260928/executions/67f8d7f01c514dc2bab4085eb008630b/backend/model_discretization.json | 196 | 78cd2ec722dc09ccd1cc0080958ba4a2d67b52c6d46c170c28c86c86637258ba |
| confirmation/sessions/gvs-stage326-confirmation-20260928/executions/67f8d7f01c514dc2bab4085eb008630b/backend/resolved_physics.json | 351570 | 14f96c10f63e28483943ba745257453b942219368548b970c1be1fe152460720 |
| confirmation/sessions/gvs-stage326-confirmation-20260928/executions/67f8d7f01c514dc2bab4085eb008630b/backend/result.json | 633949 | 74d1e01334a3b9dd5c762e79a3679a35af259bd68c7e505f0ed52e1ef2ad6df6 |
| confirmation/sessions/gvs-stage326-confirmation-20260928/executions/67f8d7f01c514dc2bab4085eb008630b/backend/robot.xml | 101776 | 9a061d3ae0b60a51c833211b2fda4cf71e7352fb85738b1b2a4ebfa634084b1f |
| confirmation/sessions/gvs-stage326-confirmation-20260928/executions/67f8d7f01c514dc2bab4085eb008630b/backend/robot_description.json | 20851 | 319dcfdb35c7470ec1c0978806da7404abf02ca90074ffbc2a20f274e6cca243 |
| confirmation/sessions/gvs-stage326-confirmation-20260928/executions/67f8d7f01c514dc2bab4085eb008630b/backend/solver_configuration.json | 172 | c7a9f804d5e3f799d274c47a74131d868aee6f20221e9b545283d2fc054f9737 |
| confirmation/sessions/gvs-stage326-confirmation-20260928/executions/67f8d7f01c514dc2bab4085eb008630b/backend/trajectory.json.gz | 255236 | d3f969fe8013c1cee37d0e089a9998081de213a860b8b3eb0de3ca3233cba217 |
