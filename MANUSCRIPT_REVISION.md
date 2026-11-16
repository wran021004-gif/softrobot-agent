# TRO manuscript pass — consolidated method and evidence-led results

Base revision: paper/research-restructure-v1.0 with the committed paper_handoff data. This pass edits the scholarly manuscript, not the experimental source data.

## Editorial changes

- Eight primary sections: Introduction, Related Work, Problem Formulation, Method, Experimental Setup, Results and Analysis, Discussion, Conclusion.
- System Implementation is incorporated into the five-subsection Method, removing repeated definitions of Main Agent, registries, PPRP, Reporter, and evidence storage. Real-World Validation is no longer a standalone placeholder chapter; hardware evidence is not invented.
- All task names follow paper_handoff/registry/task_registry.csv.
- PHS-2D-7S is in the eleven-task FULL portfolio; PHS-2D-9S is an independent passive-mechanism study.
- PPRP uses I_k for selected parameters and D for admissible designs; M3 closed-loop design variables are xi; passive equilibrium KKT variables are z_eq.
- Results follow evidence chains instead of chronologically listing tools. Reporter, Knowledge/Skill, and context evaluation are separated from robot task success.
- One main-text task/protocol table remains, with detailed metrics moved into Appendix B. A/B/C method rules, study scope, and architecture protocols are moved to other appendices.
- The original Figure 1 TeX artwork has not been modified. Figures 2–9 are new editable native TikZ/PGFPlots source drawings. 
- PAPER_FIGURE_TABLE_PLAN.md is the sole authoritative figure/table plan. The old plan is a redirect.

## Planned follow-up

Common-camera MuJoCo renders of original nine-segment intermediate structures, a physical T07 M1/M2 matched comparison, complete 11-task K/S research-mode outcomes, and eventual hardware measurement may enhance the Results but are not pre-claimed in this revision.

No source experiment, numerical threshold, or raw evidence was modified for this manuscript pass.
