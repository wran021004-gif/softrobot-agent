# Stage 3.28 artifact index

Outcome: local gate failed; selection change withdrawn. No full confirmation or live session. Start with [implementation_report.md](implementation_report.md), [local_decision.json](local_decision.json), and [usage_audit.json](usage_audit.json).

[baseline_identities.json](baseline_identities.json) resolves the original frozen task, robot, policy, 17 historical repository sources, and the numerical-preparation artifact in the existing Stage 3.27 Store. No historical databases were copied. [executed_commands.md](executed_commands.md) lists the actual numerical commands; [reproduction.ps1](reproduction.ps1) uses a fresh location and stops after local comparison.

The hashes below are SHA-256 of Git repository blob bytes (the staged content at archive creation), not a claim that Windows working files have identical line endings. The index excludes itself. Each listed file is committed alongside this index. Patch context whitespace is preserved intentionally.

| Artifact | Repository-byte SHA-256 | Bytes |
|---|---|---:|
| [attempt1_implementation.patch](attempt1_implementation.patch) | `0fc06b467a18e4d69a2d8ecb06f5c20176b9d1c1620bd1df3ecce3a10d7c9d1c` | 12728 |
| [attempt1_local_compare.py](attempt1_local_compare.py) | `5837538210d811a3f868cc2c693e83eee742e3bf11d38e2c1334e27e6eb9162b` | 3577 |
| [baseline.json](baseline.json) | `7cd04a9e7779df690c15b7347600b196e4bfd6b9aa7c63007eabb982ceaaced0` | 311922 |
| [baseline_console.log](baseline_console.log) | `0e882f104cb8e049e70de26ba73538834e564890014859b61ad7d02d5a7de599` | 3984 |
| [baseline_identities.json](baseline_identities.json) | `4af3b21522e26a44f57cde08df5e169ab3ffeb31d6152099821ed1c5af891ac9` | 7332 |
| [baseline_started.json](baseline_started.json) | `13cc3d9f8f61b9cbc18fb879c87eac53de51470d476b665b50b40cdb87f8e488` | 51 |
| [decide_local.py](decide_local.py) | `fb93b4f002f7f651c1cb2375c83a5e492a25266a41cd342cf5fb937d98429a70` | 3450 |
| [diagnostic_raw.json](diagnostic_raw.json) | `4e2838ca2bdbd1b2474bf8e3f187e9a05a6629d785fcdf8d56b749fdc001eedd` | 155921 |
| [diagnostic_recovered.json](diagnostic_recovered.json) | `50622614a9e95e36e42611d7bdee9b24bb2385632cf6be91dfe789471d6bb7d3` | 84091 |
| [diagnostic_started.json](diagnostic_started.json) | `ee369efc0075f8b462847fdb30caba2af2cf9101eb3b95d874dedfb98840eac4` | 131 |
| [diagnostic_summary.json](diagnostic_summary.json) | `fb50a7852b6b927f26e72e56ae07141bdf5800d00b3c4f02228cdb6de5c1a8d6` | 3255 |
| [environment.json](environment.json) | `da44a59037b1068a83230d804b86edb8406bdb3ede2f700730a153ac0727ae1d` | 574 |
| [executed_commands.md](executed_commands.md) | `2de759e4767d296c8b62ba81b98779e09ced76b32539330b6c78d6b4c61971fb` | 2279 |
| [implementation_report.md](implementation_report.md) | `f2a765da9bc7684aa41d57a8618890267a31312be9964b85a60d39c3ff7d453c` | 12425 |
| [live_gate_decision.json](live_gate_decision.json) | `d735a348ec5b83932eaadce3d91ce9e9f810cc5384ad59c98a0d7fb58f5c9121` | 312 |
| [local_compare.py](local_compare.py) | `18fd2275f4a9f8e1e87d538e8cd97d8db73cb31b46790bbcf8e9a0e6d50bfb97` | 3955 |
| [local_decision.json](local_decision.json) | `2e66120fbbf229181b075d5be814bcdfccabf898d027a4aeca907126edb1aced` | 2586 |
| [local_rule.json](local_rule.json) | `cabf06f62f919b04cecd46a34135ac7e2879e00e9badb93f5749c097721d511a` | 1244 |
| [original_graph_verification.json](original_graph_verification.json) | `8bf2d7f8bb2138cd831e987901cbbe91409936c09b9b717a3a9eda24ceef892b` | 788 |
| [provider_delivery_review.json](provider_delivery_review.json) | `a11b24ece9f9bcdc57912df2efbad591dcc8fda4bc8ab483d8d86d488a9053db` | 184 |
| [reproduction.ps1](reproduction.ps1) | `9656ced6b264c966cadcd3b0ed9aa7d7cccf5f6d3b41f7bbba2db52daa2392a3` | 2145 |
| [revised.json](revised.json) | `96f3ba9763b15fdca2919f9b02a98ec964f7ce776c63c17a5bdc16d4bd488f74` | 318279 |
| [revised_attempt1_console.log](revised_attempt1_console.log) | `9f5304983f8f48dbac0eb3c9e7f552942a0e9c50f30ef846667cd6cbfc8d6a9c` | 3730 |
| [revised_attempt1_failure.json](revised_attempt1_failure.json) | `745a272f5d3d8a614bc86bdbb9b6cc64e83cc902b8563cec8a5dd69e8ce1f7ad` | 925 |
| [revised_attempt2_console.log](revised_attempt2_console.log) | `11ed54b10ee4bddc5c7b3029a4274151d88801ff3920f640ea72e18a85cecf1b` | 8188 |
| [revised_attempt2_progress.json](revised_attempt2_progress.json) | `618e3f8eb1d959c7f29995e06e596b4be5367fe99772964be329c44898bc3839` | 87784 |
| [revised_attempt2_started.json](revised_attempt2_started.json) | `2f36476565ce647dd25af7519bac79e3f9c4739d158e3d64b76b8285c8b39bec` | 68 |
| [revised_console.log](revised_console.log) | `9f5304983f8f48dbac0eb3c9e7f552942a0e9c50f30ef846667cd6cbfc8d6a9c` | 3730 |
| [revised_started.json](revised_started.json) | `698485a3e34fc3ca0fff525acc8de75464b4dfa889aeab4b6136c94101c1b02f` | 50 |
| [saved_diagnosis.json](saved_diagnosis.json) | `c12f7d0f7d3f5add2c607050853909e8737bbdc987106fad945cff61725a337d` | 33362 |
| [selected_states.json](selected_states.json) | `2e7bcb3902a054a04344ecdfc064cda18d6d20f71833ad63be0b7147f19051e0` | 488850 |
| [startup_analysis.py](startup_analysis.py) | `ed494dff2fcdbfb353a9acb4c29f5847d996cb056a2e8e0d9a20cff92c7c1962` | 8354 |
| [test_withdrawn_selection.py](test_withdrawn_selection.py) | `7626217625c5549c1d67043b0f5d9c4bb7dee29ba007bf24deb5247937d823d5` | 2813 |
| [usage_audit.json](usage_audit.json) | `48b18d77b9787edcc0b700f3aeb812e00630b2604f545e50b39c05e7552ab50b` | 2027 |
| [verification_results.json](verification_results.json) | `dad3baf51196fb23d076dcaa17e9fcc8aa29a3d881f08793602bf69b8f9c69d7` | 519 |
| [verify_saved_plans.py](verify_saved_plans.py) | `8b5f87b9faf3bab44462b03c84e5014f43fd107a55b51fbb4e4f70590be9f5dc` | 1796 |
| [withdrawn_selection.patch](withdrawn_selection.patch) | `b68e49fb556f3c4f6cac279b1482b6e57d08020cb209809d4eaf4e3ebd17969d` | 12734 |

## Reading the evidence

- saved_diagnosis.json and selected_states.json: two historical operating points and exact/reconstructed warm provenance.
- diagnostic_raw.json, diagnostic_recovered.json, diagnostic_summary.json: one isolated capped solve and retained adjacent plans.
- local_rule.json: selection direction and acceptance thresholds declared before revised measurements.
- baseline.json and revised.json: four completed production-policy updates, full plans, diagnostics and costs.
- revised_attempt1_failure.json and revised_attempt1_console.log: invalid measurement and bounded accounting uncertainty; original code/script retained.
- withdrawn_selection.patch and test_withdrawn_selection.py: corrected but withdrawn implementation and focused checks.
- original_graph_verification.json: four value-only checks after production restoration.
- live_gate_decision.json and provider_delivery_review.json: conditional stages not entered.
