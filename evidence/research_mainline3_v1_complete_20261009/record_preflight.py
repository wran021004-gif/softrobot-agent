from pathlib import Path
from tools.state_io import atomic_json,read
out=Path('evidence/research_mainline3_v1_complete_20261009')
g=read(out/'offline_gate.json');g.update(final_persistence_affected_checks=3,final_log='offline_persistence_final.log');atomic_json(out/'offline_gate.json',g)
atomic_json(out/'response_gate_removal.json',dict(removed={
 'transport':'Credential-content, regex and recursive keyword admission on complete responses; server-error field/content/echo admission. Original UTF-8 or original bytes are persisted before business decode.',
 'dispatcher':'_check_response_body and every receive/interact/recovery/revalidation call; native arguments enter normal schema and permission validation after storage.',
 'context':'Whole-payload content guessing in capacity measurement; content checks in generic snapshots and restored working-state persistence. Configuration _no_secrets remains separately used.',
 'handoff':'Whole-bundle checks in direct/single/delivery/validation exports; report_completion raw-response check.',
 'legacy':'Actual-key replacement in model-response values in dynamic campaign and legacy workbench; request/error authentication handling remains.'},
 retained=['Atomic Store and serialization/integrity','Formal tools and argument contracts','Tool/evidence scope','Configuration/execution identity and provenance','Budgets and deadlines','Scientific acceptance','Authentication-only credentials'],
 verification='Focused public-path offline gate; no paid requests or science. Existing false-positive embedded evaluator-version JSON and research credential labels pass storage and processing.',
 no_replacement_response_defense=True))
for name in ('prepare_edits.py','prepare_tests.py'):
 p=(out/name).resolve();assert p.is_relative_to(Path.cwd().resolve());p.unlink()
