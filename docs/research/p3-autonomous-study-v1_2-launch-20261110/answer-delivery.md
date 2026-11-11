# Main final-answer delivery

The user requests that Main deliver its final research answer after necessary verification, without repeated or complex validation. Replay, extra experiments and Reporter reviews are not required for this delivery goal. Existing evidence keeps its original scope; no formal task-acceptance certificate is manufactured.

The existing research harness now supports `run --delivery-only`: Main can read saved evidence and recall history, writes its own final answer into the Store, and pauses after that answer. With an allocated request limit, the last request is reserved for the answer itself and exposes no further navigation tools. Existing provider accounting and session persistence remain in use. The operator composition in `answer_delivery.py` continues this Study with the explicit user directive and the remaining original budget. Six requests completed the evidence-reading phase; the final continuation allocates one request to writing the answer.

The feedback repair distinguishes successful computation from incomplete qualification coverage and preserves that distinction through handoff. Execution-profile descriptions advertise explicit exploration and full-protocol choices without prescribing a new experiment. The exact previously missing frozen protocol artifact is restored from its versioned source; the original source hash is unchanged. Future preparation imports this artifact through the existing supplied-evidence mechanism.

Validation: 12 targeted offline tests passed (`test_answer_delivery`, `test_p3_schema_recovery`, `test_context_diagnostic_projection`). They cover delivery tool availability, explicit profile scopes, coverage feedback surviving handoff, exact source identity, schema validity and context projection. No scientific kernel or task threshold is changed.

Delivery receipts: `answer-delivery-before.json`, `answer-delivery-bound.json`, `answer-delivery-after.json`. Main's unedited answer is saved as `main-final-answer-20261111.md` after the accounted live delivery completes.
