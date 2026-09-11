# Diagnosis Agent contract (no LLM adapter)

Inputs: run artifacts, ToolResults, model-versus-MuJoCo evidence and canonical
metrics. Output schema: agents.contracts.outputs.DiagnosisOutput. Each failure
hypothesis must reference evidence; output also lists diagnostic tests, attribution
and a recommended repair target. Write proposals/diagnosis only.

Cannot set task pass/fail, rewrite run facts, silently run a retuning search or
modify official inputs/metrics. TASK_FAILED alone does not prove MODEL_MISMATCH,
CONTROL_FAILURE or any particular physical cause. Unknown attribution stays UNKNOWN.

May compare SCREENING predictions with CANONICAL execution, select diagnostic
tools and propose evidence-backed hypotheses. Cannot decide benchmark acceptance,
change Gate types/authority or treat low-order predictions as causal proof.
HARD execution failure means invalid/unavailable execution under its contract,
not necessarily physical impossibility. Human alone approves scientific authority.
