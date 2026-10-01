# Current status

This archive is authoritative for the saved-evidence diagnosis of manual execution `494deb38d6374deb8f741e96f2430826`. The original Windows working-tree byte manifest remains unchanged in `sha256_manifest.json`; `newline_policy.json` and `git_blob_sha256_manifest.json` define and verify the separate committed-blob byte domain. The exact generator invocation and its current parser/read-only verification are in `reproduction_command.json`.

Implementation evidence is the cited source/commit comparison in `selection_rule.json`; it explains selection semantics but is not robot performance. LLM behavior is recorded separately in the Stage 3.35 and Stage 3.36 decision/audit records; the earlier model selection and later manual execution are not one uninterrupted autonomous experiment. Manual execution provenance is bound in `provenance_chain.json`. Robot performance is the official valid but failed reach result in `execution_outcome.json`: terminal error `0.06672099201814737` m against `0.01` m, failed sampled settling, and no demonstrated complete-update real-time feasibility.

The follow-on three-update reconstructed diagnostics and the new autonomous design experiment are separate Stage 3.37 evidence under `evidence/stage337_bounded_autonomous_design_20261001/`; they do not rewrite this archive’s historical outcomes.
