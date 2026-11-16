# Research-node annotation rubric

These are model-assisted annotations. They are not human expert ratings, robot performance, or proof of causal effects. Scores refer only to the evidence available in the annotated record.

| Score | Fixed interpretation |
|---|---|
| 0 | Missing, incorrect, or contradicted by the original evidence |
| 1 | Preliminary description without specific grounds |
| 2 | Partially supported; material evidence or action is incomplete |
| 3 | Clear, generally supported evidence-to-action reasoning |
| 4 | Specific, testable, well-supported reasoning with concrete action |

| Dimension | Required evidence |
|---|---|
| Hypothesis Testability | Explicit expected observation **and** weakening/refuting observation. Generic completion/failure phrases cannot earn a high score. |
| Evidence Grounding | An original mathematical or physical evidence locator supporting the judgment. |
| Method Appropriateness | Suitability of physical model, solver, scope, operating conditions and assumptions. Naming a method is insufficient. |
| Research Adaptation | An actual change of hypothesis, route, design or control in response to evidence. |
| Evidence-to-Action | Distinguish proposed, executed, and independently evaluated actions. A successful generation is not task acceptance. |
| Rejection Quality | A candidate or route is abandoned for evidence-supported reasons. Use UNKNOWN where no rejection is established. |
| Physical Outcome | Quantitative physical measurements only. No subjective 0–4 replacement. |

Every rating records score, rationale, supporting reference, confidence, uncertain fields and annotation round. UNKNOWN is not zero. An absent contemporary prediction remains absent; retrospective source-index explanations retain their retrospective identity.

The initial pass covers all 32 nodes. Independent stateless review covers the key results selected in `blind_protocol.json` before its scores are read. The reviewer receives anonymous nodes and contemporary evidence. Later final success, group labels, previous ratings and editorial ranks are withheld. Original task/source identifiers can reveal research content, so complete semantic blinding is impossible. Same-model judging is a limitation. The two rounds remain separate; they are not averaged into a scientific-performance score.

Editorial selection uses five equally weighted 0–4 dimensions: Scientific Contribution, Physical Evidence Strength, Before–After Difference, Research Decision Value, Visual Presentation Potential. Its mean is an editing priority only. It is neither the research-behavior score nor a robot capability measure. A high visual-potential rating does not imply that a common-camera rendering has been completed.
