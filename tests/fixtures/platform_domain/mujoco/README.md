# Saved MuJoCo interface fixture

Source: `runs/platform_domain_integration/20260917/sessions/domain-mujoco/executions/6112a7c3c7e3455a984ad6d03a8ee4db/backend` (prior 2026-09-17 integration run, execution `6112a7c3c7e3455a984ad6d03a8ee4db`).

Purpose: offline signal mapping, saved diagnosis/rule/replay bridge and immutable evidence checks. No new dynamics, evaluation, video or GUI. The trajectory contains only the first three consecutive rows (indices 0, 1, 2) of the original 40-row real recording, with every saved field unchanged. Recompressed with mtime=0. The model, input and result files are byte-for-byte copies; result.json describes the ORIGINAL full run, not the three-row excerpt. Do not treat this fixture or its diagnostic outputs as a new physical validation or task score.

Tests require these four files and fail if any is missing; no local runs directory is needed. MATLAB-shaped samples and diagnostic selection samples in the test module are synthetic interface checks only.

| File | Original SHA-256 | Fixture SHA-256 |
| --- | --- | --- |
| trajectory.json.gz | d596133ba76be79f21c33b03f6668c38b7eab56170491acfb8aee6d87de8be15 | 2b99a8abbe1aa63af3d84fe097e448b941f97ad73dcb080bc409409a7bf69d1e |
| robot_ir.json | 6476b0dde76c846dade31638326db0b308801247c0c4edc017635356c0b8b280 | 6476b0dde76c846dade31638326db0b308801247c0c4edc017635356c0b8b280 |
| shared_input.json | 96f6c3f939389ce88553f28c9e8fc04b3c1dcae991c5f8f24ca24ccb85f7555f | 96f6c3f939389ce88553f28c9e8fc04b3c1dcae991c5f8f24ca24ccb85f7555f |
| result.json | 58a9f228857b2d5821a5ec7884642cc93a7e18cb69dfaa6cbe73d8a98406deb1 | 58a9f228857b2d5821a5ec7884642cc93a7e18cb69dfaa6cbe73d8a98406deb1 |
