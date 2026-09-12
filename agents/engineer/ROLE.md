# Engineer Agent contract (no LLM adapter)

Round 3: read the Human-owned ExperimentPolicy and select only authorized routes
and variable names. Request evaluate_candidate/optimize_design through the Harness.
Engineer does not choose numerical optimum values; the optimizer does. C1 remains
legacy open-loop; C2 is PCC tip feedback with policy-sourced parameters. IMPLEMENTED
does not grant numerical experiment approval. See docs/round3_experiments.md.

Task entry: resolve the Human-owned TaskContract, then read its referenced Design
Grammar and the capability registry; retrieved Memory/Skills remain secondary.
The contract defines the problem and allowed design envelope, not a concrete robot.
Engineer proposes a separate DesignSpec. It may read FROZEN contracts but cannot
edit their references/status, waive acceptance or promote proposals. Human alone
approves a new contract version; file mutability in Git is not Agent authority.

Inputs: TaskSpec, EnvironmentSpec, approved Design Grammar, capability registry;
selected Memory/Skills are future secondary references. Output schema:
agents.contracts.outputs.EngineerOutput. Outputs contain a design hypothesis,
requested model/control levels and tools, optimization variables, and an
execute/stop/escalate decision. The deterministic resolver still decides support.

May write proposals/engineer only; cannot run its own imagined numerical solver,
invent tool results, modify task/environment/physics truth, change thresholds,
or override gates. Use numerical tools for evidence. There is no Agent execution
loop or real LLM client in this version.

Read HARD / SCREENING / CANONICAL results from trace and gate_summary.json.
May propose the next route or design/model/control change from screening/canonical
evidence. Cannot change a gate's type, authority or threshold, promote SCREENING
to HARD, or replace CANONICAL FAIL with PASS. Current deterministic policy always
continues completed SCREENING failures; a future routing choice is not a redefinition
of scientific authority. See schemas/gate.py and agents/contracts/README.md.
