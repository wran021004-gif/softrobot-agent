# Notation handoff

The authoritative symbols are in `registry/symbol_registry.csv`. Use τ for task; d for morphology; calligraphic D for admissible design space; θ for controller parameters; U for control input; q for generalized coordinates; gτ,i for task constraints; Vτ(d) for re-optimized task violation.

At research node k use s_k, H_k, E_k, a_k, P_k, **I_k**, O_k, σ_k, B_k for state, working hypothesis, evidence, action, PPRP, selected parameters, observables, analysis semantics and budget. Selected parameters must not be denoted D_k.

E_k = (E_k^math, E_k^phys). Mathematical Evidence and Physical Evidence are independent paths. M0: Mechanism Sensitivity m(d); M1: Fixed-input Physical Response yτ(d,U0); M2: Re-optimized Task Capability Vτ(d); M3: Closed-loop Performance Jτ,H(d,θ). These are complementary semantics, not stages that must execute in order.

Canonical task labels are T01–T10 and PHS-2D, without mathematical-semantic suffixes. PHS-2D-7S and PHS-2D-9S are separate Studies. Architecture scores are model-assisted decision ratings, not human expert assessment or robot capability.
