# Experimental Matrix

## Physical portfolio

| Group | Tasks | Required conditions | Main evaluation |
|---|---|---:|---|
| Active reach/load | T01--T03 | 7 | terminal/hold error, speed, load response |
| Tracking/pose | T04--T06 | 3 | trajectory RMSE, position, tool-axis, timed scan |
| Shared morphology | T07 | 4 | per-condition violation under one structure |
| Passive response | T08 | 2 | bilateral stiffness and tendon engagement |
| Contact/impact | T09--T10 | 4 | contact depth/force and impact recovery |
| Passive FULL case | PHS-2D-7S | 10 | loaded-point and tip displacement |
| Independent mechanism study | PHS-2D-9S | 10 | signed-load compliance, tip suppression, sensitivity |

The FULL portfolio is T01--T10 plus PHS-2D-7S: eleven task cases and thirty required conditions. T10 has two additional frozen controls. PHS-2D-9S is a separate independent study.

## Research-mode comparison

A/B/C contains 33 task--method records. A is LLM-only, B exposes direct mathematical tools, and C is the archived FULL process. C is historical; the comparison is task-wise and not a randomized multi-seed benchmark.

## Architecture decision studies

| Study | Sessions | Valid decisions | Reviews | Main measures |
|---|---:|---:|---:|---|
| Reporter ON/OFF | 12 | 12 | 6 paired | five-dimensional paired score, unsupported claims |
| Original K/S E1 | 8 | 8 | 2 joint | historical-experience utilization, original four-dimensional score |
| Supplemental K/S | 16 | 15 | 4 joint | common five-dimensional score, resource use |
| Context E2/E2-R2 | 4 Main sessions across two historical pairs | 4 | 2 | Provider input, decision score, evidence coverage |
| Cross-task context | 12 | 11 | 6 paired | serialized request-text volume, decision score, evidence recall |

The sixteen supplemental K/S sessions contain 37 requests and 6.13M input / 40.9k output serialized request-text tokens. The twelve cross-task context sessions contain 25 requests and 1.83M input / 25.3k output serialized request-text tokens. The 28 sessions together contain 62 requests and 7.95M input / 66.3k output serialized request-text tokens. These text-volume counts are distinct from Provider-reported usage in E2/E2-R2.

## Ongoing experiment

The separate full 11-task K/S research run is ongoing and is not included in the completed decision-replay results or current manuscript claims.
