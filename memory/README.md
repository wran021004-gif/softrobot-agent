# Future Memory index

Memory DB: not implemented. No SQLite, embeddings, vector database or retrieval loop.

The implemented `schemas.memory.MemoryRecord` is only a small serializable
contract: run ID, bounded summary, searchable metadata and hashed evidence links.
Memory indexes historical runs; it does not copy full traces, numerical artifacts
or skills. A future index must resolve links against finalized run manifests and
retain negative outcomes. It cannot mutate canonical task decisions.

Artifact = observed facts. Trace = execution order and causal links inside one run.
Memory = historical index across runs. Skill = validated reusable strategy.
