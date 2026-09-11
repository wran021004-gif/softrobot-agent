# Diagnosis Agent contract (no LLM adapter)

Inputs: run artifacts, ToolResults, model-versus-MuJoCo evidence and canonical
metrics. Output schema: agents.contracts.outputs.DiagnosisOutput. Each failure
hypothesis must reference evidence; output also lists diagnostic tests, attribution
and a recommended repair target. Write proposals/diagnosis only.

Cannot set task pass/fail, rewrite run facts, silently run a retuning search or
modify official inputs/metrics. TASK_FAILED alone does not prove MODEL_MISMATCH,
CONTROL_FAILURE or any particular physical cause. Unknown attribution stays UNKNOWN.
