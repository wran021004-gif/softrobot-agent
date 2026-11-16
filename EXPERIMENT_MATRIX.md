# Experimental matrix — manuscript v1.2

## 1. Completed FULL physical portfolio

Eleven completed task cases: T01–T10 and the nine-segment, four-tendon PHS-2D Round-3 case. The archived summary contains 30 passed required conditions among 30 required records. Two additional T10 frozen controls are reported separately. This is a completed-case portfolio, not a multi-seed success-rate estimate.

## 2. Research-mode comparison

The first comparison batch contains PHS-2D, T01, T04, and T07, with one A and one B run per task; C is the corresponding historical FULL reference. A is LLM-only physical-feedback design. B adds direct bottom-level mathematical tools but not the high-level research-intent projection and mathematical orchestration. C is the complete FULL research process.

The representative A/B/C task-wise comparison focuses on T01, T04, and T07. PHS-2D is presented separately as the principal nine-segment mathematical and passive-design case.

## 3. Architecture decision-replay studies

### Reporter ON/OFF
- Six matched historical checkpoints: M1-A/B/C and P3-A/B/C.
- Twelve Main sessions and six anonymous paired reviews.
- ON reuses six saved Reporter reports; no new Reporter generation is included.
- Five-dimension blind mean: 3.433 OFF, 3.733 ON; paired mean difference +0.300; median 0; wins/ties/losses 2/4/0.
- Unsupported conclusions: 2 OFF, 0 ON in the blind review.
- Main Provider usage unavailable; mean additional visible context 1,450.5 tokens is a generic local tokenizer proxy.

### E1: Knowledge/Skill 2×2
- Two task checkpoints: T04 and T07.
- Four cells per task: K−S−, K+S−, K−S+, K+S+.
- Eight real Main LLM decisions; one observation per cell; one joint blind review per task.
- Historical-experience utilization: 0/3/3/3 for the four cells.
- Decision quality, evidence consistency, and actionability: 4 in every cell; invalid proposed actions: 0.
- K and S main effects on utilization: +1.5 each; interaction contrast: −3; joint minus best single: 0.
- K+S+ was acquired later; frozen inputs/settings match but backend/default reasoning identity is unverified.
- No mathematical or physical follow-up was executed.

### E2: Flat versus L0–L3 at PHS-C035
- One paired decision checkpoint; 66-record corpus.
- Flat receives the complete corpus; hierarchical receives automatic L0 plus a directory.
- No additional evidence reads occurred.
- Accepted-inference actual input: 675,802 Flat vs 78,785 hierarchical tokens (88.34% reduction).
- Blind mean: 4.0 Flat vs 3.8 hierarchical.
- Hierarchical has one initial HTTP 400 request with no usage; all-attempt actual input is unknown.

### E2-R2: preregistered context follow-up at PHS-C037
- C037 admitted and executed with 106 records; C042 excluded before inference by the capacity gate and not replaced.
- Flat receives the complete included corpus; hierarchical receives L0 and makes three parallel L3 reads.
- No L1/L2 reads; exact raw returns and subsequent delivery verified.
- Cumulative actual input: 877,197 Flat vs 174,298 hierarchical tokens (80.13% reduction); one vs two Main requests.
- Blind mean: 3.4 Flat vs 3.6 hierarchical.
- Key-evidence coverage: 5/5 Flat vs 3/5 hierarchical.
- One paired checkpoint and one independent blind review; no physical action executed.

## 4. Reporting rules

- Use each physical task's frozen metrics and required-condition denominator.
- Keep T10 frozen controls separate.
- Do not average raw errors across task families.
- Keep the nine-segment PHS-2D result and its 18-pair gradient audit separate from older topology snapshots.
- Preserve the historical identity of C in all comparisons.
- Treat Reporter, E1, E2, and E2-R2 as decision-only architecture studies. Report ordinal scores, sample counts, actual usage, generic proxies, and evidence coverage separately.
- Do not infer robot-success improvement, statistical significance, or population-level synergy from these small decision samples.
