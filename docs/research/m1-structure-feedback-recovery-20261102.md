# Saved structure-intent feedback recovery

After the supervised analysis interruption was settled, no-send SDK recovery
exposed a second interface mismatch: the original Main tool input was a
ScientificStructureSearch, while its original receipt hashes the internal
compiled Plan. Feedback recovery handled reference-choice expansion but tried
to validate the scientific input directly as that internal Plan.

Recovery now uses only the existing immutable
`structure_search_intent_binding`. It checks the exact original input, rejects
conflicting saved compilations, verifies the accepted Plan belongs to the Study
and original request, and checks the original receipt hash. It never recompiles
the question, executes a tool, or selects new scientific settings. Legacy Plan
and scientific-question recovery retain their existing paths.

Four targeted offline tests passed: saved compilation restores feedback once
without recompilation or launch; conflicting bindings fail closed; a changed
original input fails closed; and an unowned accepted Plan fails closed. No real
Provider or numerical Worker was called. All scientific outcomes, costs and
frozen acceptance requirements remain unchanged.
