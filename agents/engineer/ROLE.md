# Engineer Agent contract (no LLM adapter)

Inputs: TaskSpec, EnvironmentSpec, approved Design Grammar, capability registry;
selected Memory/Skills are future secondary references. Output schema:
agents.contracts.outputs.EngineerOutput. Outputs contain a design hypothesis,
requested model/control levels and tools, optimization variables, and an
execute/stop/escalate decision. The deterministic resolver still decides support.

May write proposals/engineer only; cannot run its own imagined numerical solver,
invent tool results, modify task/environment/physics truth, change thresholds,
or override gates. Use numerical tools for evidence. There is no Agent execution
loop or real LLM client in this version.
