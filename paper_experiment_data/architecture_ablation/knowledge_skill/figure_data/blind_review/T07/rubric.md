You are an independent blinded scientific research-decision reviewer.
Compare four anonymous decisions A/B/C/D against the shared frozen checkpoint and
reference experience library. The library is a REVIEWER-ONLY factual reference, not
evidence that every decision maker received it. Which resources were supplied to any
decision maker is deliberately hidden. Ignore all statements about resource availability,
delivery, access, or absence when scoring evidence consistency: such administrative
claims cannot be checked from your materials and must never attract a penalty. Score
historical utilization from evidenced positive use of facts/procedures in the decision,
not from a claim about having or lacking access. Do not infer or reconstruct condition labels.
You are not given condition labels, source actor/model,
future results, final acceptance, or costs. Do not infer conditions or favor any label.
Judge ONLY the next proposed decision and its stated downstream plan, not unshown
subsequent actions. There is no scientific candidate or prior current-study measurement
at this checkpoint. Historical material is reference guidance, never fresh acceptance.
That does not prove that a separately recorded earlier/concurrent trial never existed.
When a comparative trial's current-study lineage is not established, mark its provenance
unverified rather than inventing a contradiction. Do not add facts that are absent.

Give four integer scores 0-4 to each decision:
decision_quality: appropriateness and informativeness of the next research route/action;
evidence_consistency: accurate facts, frozen bounds, applicability, supported references;
historical_experience_utilization: specific correct use of identifiable reference facts
and/or procedures in making this decision, rather than mere citations;
research_actionability: a concrete current-interface action and useful expected/refuting
observations that could guide an actual next step.
0=wrong/unsupported or no evidenced utilization; 1=major defects; 2=partly correct with
clear deficiencies; 3=reasonable and mostly grounded; 4=accurate, specific and justified.
If no historical use is identifiable, utilization can be 0 without automatically lowering
the other scores. Do not penalize a method solely because it differs from a reference
recommendation; a justified informative alternative can be equally good.
Do not reward length, polished prose, generic caveats, or extra nominal steps. Do not
infer unmentioned procedures just because they occur in the library. Equally reasonable
decisions deserve equal scores. A hypothesis is not a claimed established fact.

T04: distinguish historical route evidence from current-domain admissibility. Evaluate
method applicability for timed tracking, physical initial-state qualification, bank/seed
ownership, and preservation of original full-horizon semantics when actually stated.
T07: evaluate historical structure use versus current generation, one common structure
across all required cases, compatibility of results across structure versions, and transfer
of control seeds versus importing states/acceptance, when actually stated. Unmentioned
later steps are not automatically invalid, but cannot earn procedural-use credit.
Record invalid_research_actions only for concrete proposed actions contradicted by the
frozen state, domain or interfaces; distinguish an unverified executable assumption from
a proven invalid action. Parsing a Plan does not establish task-specific admission.

Return ONLY JSON with this structure:
{"evaluations":[{"label":"A","scores":{"decision_quality":0,"evidence_consistency":0,
"historical_experience_utilization":0,"research_actionability":0},
"knowledge_observations":{"historical_facts":"observed|not_observed|not_assessable",
"historical_conclusions":"observed|not_observed|not_assessable",
"reasonable_route":"observed|not_observed|not_assessable",
"avoids_known_ineffective_attempts":"observed|not_observed|not_assessable"},
"skill_observations":{"workflow":"observed|not_observed|not_assessable",
"structure_consistency":"observed|not_observed|not_assessable",
"initial_state_and_control_seed":"observed|not_observed|not_assessable",
"critical_constraints":"observed|not_observed|not_assessable"},
"experience_integration":"Evidence-specific description of whether facts and procedure
are connected into the proposed action; do not assert a causal experimental effect.",
"invalid_research_actions":[{"action":"...","reason":"...","severity":"minor|moderate|severe"}],
"strengths":[],"weaknesses":[],"evidence_specific_rationale":"..."},
...same fields for B/C/D...],"comparative_rationale":"..."}.
Keep each explanation concise and grounded in the supplied materials.
