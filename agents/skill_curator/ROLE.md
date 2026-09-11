# Future Skill Curator contract

Not implemented. No LLM, autonomous loop, background job, or automatic approval.

A future curator may collect CandidateFindings, group repeated observations,
propose candidate skills, find duplicates/contradictions, suggest narrower
applicability, request cross-run validation, and suggest deprecation. Proposals
use schemas/skill.py; experiments return SkillValidationEvidence and
SkillValidationRecord. Negative experiments must remain in revision history.

Only Human can approve a validated skill. The curator cannot change task or
benchmark truth, Physics Contracts, canonical gates, permissions, or scientific
laws. Existing agent permissions deny unregistered roles by default. No new write
permissions are granted here; a future executor needs a separately approved scope.

Use TraceEvent and DecisionRecord to expose actions, evidence references and short
public reasons. Never collect private chain-of-thought or internal reasoning tokens.

Recommendation -> Agent decision -> normal permission check -> execution.
A Skill, Trace, Finding, or MemoryRecord is never authority.
