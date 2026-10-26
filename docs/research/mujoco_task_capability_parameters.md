# A1/A2/A3 implementation audit

Base: `c153e1731ae0925e756467f75a783b28abce2873`. Reference: `ae3f94f272518fa17fe81d10cea9a61d6a67652b`.

Plan: A1 selectively integrate native T1/T2 using existing analysis/worker/Store; A2 derive executable parameters and legal comparison directions from FamilySpace; A3 expose bounded decision evidence and a reproducible offline example. No sealed Study/configuration/evidence will be changed.

Validation uses targeted offline contracts and capped engineering smoke checks only. No provider, Agent Study, PPO, or broad structural scans.

A1: selected seven integration files plus nonlinear interpretation kernel/test from reference; unrelated Agent changes, Study configurations and historical evidence excluded. Old methods remain unauthorized. Existing `.f3-prestudy-env` supplies all dependencies. Initial regression exposed two pre-existing test assumptions: exact floating solver coefficient equality (differences <1e-15) and the baseline ResultCard's additive scientific interpretation. Corrected assertions without changing solver or reporting semantics; the original reporting failure was reproduced using the sealed baseline analysis functions.
