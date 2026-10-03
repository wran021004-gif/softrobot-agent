"""Offline final delivery assembly; no model, backend or numerical operations."""
from pathlib import Path
import hashlib
import json
import sys
import subprocess
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.state_io import read,atomic_json
from tools.platform_store import Store

base=ROOT/'runs/stage354_milestone0_20261003'
export=ROOT/'evidence/stage354_milestone0_20261003'
labels=['suffix_single_context','suffix_dual_context','single_context','dual_context']
assert subprocess.run(['git','diff','--quiet','HEAD','--','evidence/stage353_milestone0_20261003'],cwd=ROOT).returncode==0
for organization in ('single_context','dual_context'):
    historical=Store(ROOT/'runs/stage353_milestone0_20261003'/organization)
    assert historical.remaining()==read(historical.root/'outcome.json')['usage']
rows=[];physical=[];sources=[];prose_findings=[]
for label in labels:
    directory=base/label;destination=export/label;store=Store(directory)
    outcome=read(directory/'outcome.json');audit=read(destination/'audit.json');gate=read(destination/'acceptance.json')
    assert gate['passed'] and outcome['status']=='completed',(label,gate)
    assert not read(destination/'portable_closure.json')['unresolved']
    assert audit['used']==store.remaining()['used']==outcome['usage']['used']
    assert all(v<=outcome['usage']['limit'][k]+1e-6 for k,v in audit['used'].items())
    freeze=read(directory/'freeze.json');feedback=read(directory/'feedback.json');final=read(directory/'final_response.json')
    if label=='dual_context':
        revision=store.artifact(outcome['chain']['revised_report'])
        actual=feedback['execution']['factual_result']['candidate']['candidate_id']
        import re
        names=set(re.findall(r'improvement-[a-zA-Z0-9]+',json.dumps(revision)))
        for name in sorted(names-{actual}):
            prose_findings.append(dict(run=label,field='revised_report.report.recommended_actions',submitted_candidate_name=name,
                bound_candidate=actual,source=outcome['chain']['revised_report'],
                disposition='Preserved model prose typo; not a structured citation or selected candidate. Final selected_candidate is null (defer_selection). No silent repair.'))
    scopes={};events=[]
    with store.connect(True) as db:identities=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
    for identity in identities:
        state=store.session(identity)['state'];events+=store.events(identity)
        if state.get('reference_interface'):
            scopes[identity]=dict(context_id=identity,fact_scope=state['fact_scope'],interface=state['reference_interface'],
                resolution='Alias maps exactly to long handle in this context fact_catalog; selector source artifact binds execution identity. Never resolve across contexts.')
    atomic_json(destination/'reference_scopes.json',scopes)
    timestamps=[datetime.fromisoformat(e['timestamp']) for e in events]
    spans=(max(timestamps)-min(timestamps)).total_seconds()
    row=dict(label=label,acceptance=gate,used=audit['used'],limits=outcome['usage']['limit'],
        workflow_elapsed_s=outcome['elapsed_s'],recorded_wall_span_s=spans,reported_tokens=audit['tokens'],
        numerical_work=outcome['numerical_work'],protocol_corrections=outcome['protocol_corrections'],
        final_decision=final,feedback_reference=outcome['chain']['feedback'],revision_reference=outcome['chain']['revised_report'],
        outcome=str((destination/'outcome.json').relative_to(export)),monetary_cost=None,
        implementation=read(directory/'implementation.json'),implementation_transition=read(directory/'implementation_transition.json') if (directory/'implementation_transition.json').exists() else None)
    rows.append(row)
    physical.append(dict(label=label,measurements='Historical Stage 3.53 execution reused' if label.startswith('suffix_') else 'Fresh Stage 3.54 execution',
        actual_diff=store.artifact(outcome['chain']['preparation'])['actual_diff'],comparison=feedback['campaign_comparison'],
        final_candidate_disposition=final['candidate_disposition']))
    if not label.startswith('suffix_'):
        sources.append(freeze)
        assert feedback['execution']['receipts']['simulation']['cache_hit'] is False
        assert audit['used']['backend_solves']==1
    else:assert audit['used']['backend_solves']==0

for field in ('source_manifest','identities','provider_configuration','limits','numerical_limits','scope','memory_policy','phase_budgets','stage_instructions','permissions','capabilities','experiment'):
    assert sources[0][field]==sources[1][field],field
assert rows[2]['implementation']==rows[3]['implementation']==read(export/'fresh_freeze.json')['implementation']
usage={k:sum(r['used'][k] for r in rows) for k in rows[0]['used']}
assert usage['backend_solves']==2 and usage['worker_calls']==0
assert sum(r['numerical_work']['used']['local_solves'] for r in rows)==0
tokens={k:sum(r['reported_tokens'][k] for r in rows) for k in ('prompt_tokens','completion_tokens','total_tokens')}
summary=dict(milestone0_accepted=all(r['acceptance']['passed'] for r in rows),unmet_reliability_conditions=[],
    suffixes=rows[:2],fresh_workflows=rows[2:],physical_results=physical,usage=usage,reported_tokens=tokens,
    workflow_elapsed_s=sum(r['workflow_elapsed_s'] for r in rows),preflight_usage=dict(model_calls=0,tool_calls=0,backend_solves=0,worker_calls=0,wall_s=0.),
    numerical_work=dict(local_solves=0,prediction_evaluations=0),monetary_cost=None,
    cost_note='Actual sealed operation charges; reported provider tokens include failed responses. Saved-response normalization adds a tool charge, no provider attempt. Workflow elapsed excludes preparation/export and engineer repair downtime; recorded wall span includes pauses. Controller optimization is included in backend execution, not extra optional numerical checks.',
    implementation_commits=['541f426','e925723'],fresh_implementation=rows[2]['implementation'],
    focused_verification='11 affected reference/revision/recovery checks passed; 12 existing completion/settling/context checks passed. Preserved logs are in focused_check.json and offline_checks/.',
    milestone1_inventory='../../docs/stage354_milestone_interfaces.md',milestone1_completed=False,
    next_target='Read-only projection joining existing task, effective candidate, accepted decision, completion, scoped evidence and remaining-budget references, with explicit rebuild requirements for the two supported controller weights.',
    limitations=['One fresh run per organization on one task; no statistical claim of organizational superiority.',
        'Both fresh models independently selected holding_tip_speed_weight 0.05; only the two registered speed weights were editable.',
        'Sampled holding is not a continuous-time or hardware guarantee. Citation validation does not establish causality.',
        'The dual suffix needed a recorded host decoder repair. Its failed receipts, original outcome and original phase ceilings remain preserved.',
        'Stage 3.53 remains incomplete and immutable; the suffixes are supplementary grants.',
        'A dual revision prose candidate-name typo remains in the archived model output. Structured feedback/candidate bindings and final defer_selection are exact; see scientific_review.json.'],pushed=False)
atomic_json(export/'delivery_summary.json',summary)
atomic_json(export/'scientific_review.json',dict(scope='Implementer review of accepted products, separate from exact-selector validation; no causal certification.',
    candidate_feedback_used=True,final_dispositions={r['label']:r['final_decision']['candidate_disposition'] for r in rows},
    prose_findings=prose_findings,physical_result='Both fresh candidates: reach passes, holding position and speed fail; componentwise tradeoff; real-time not demonstrated.',
    original_assessment_revision='Suffixes use actual worsening to decline candidate adoption. Fresh revisions acknowledge measured holding improvement, worse reach/computation and remaining joint failure; dominant-cause claims remain unresolved.'))
for label in labels:
    directory=export/label
    atomic_json(directory/'sha256_manifest.json',{p.relative_to(directory).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(directory.rglob('*')) if p.is_file() and p.name!='sha256_manifest.json'})
files=[p for p in export.rglob('*') if p.is_file() and p!=export/'sha256_manifest.json']
secret_candidates=[]
import re
for p in files:
    if p.suffix in ('.json','.md','.txt') and re.search(rb'\bsk-[A-Za-z0-9]{24,}\b',p.read_bytes()):secret_candidates.append(str(p.relative_to(export)))
assert not secret_candidates,secret_candidates
atomic_json(export/'export_integrity.json',dict(exact_archived_bytes=True,unresolved_references=0,
    stage353_files_modified=False,secret_pattern_matches=0,final_source_checks='All four portable closure exports resolved every reference; fresh configuration equality and accounting checked offline.'))
atomic_json(export/'sha256_manifest.json',{p.relative_to(export).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
    for p in sorted(export.rglob('*')) if p.is_file() and p!=export/'sha256_manifest.json'})
print(json.dumps(dict(accepted=summary['milestone0_accepted'],usage=usage,tokens=tokens,
    rows=[dict(label=r['label'],used=r['used'],elapsed=r['workflow_elapsed_s'],tokens=r['reported_tokens']['total_tokens']) for r in rows],
    physical=[dict(label=r['label'],metrics=r['comparison']['candidate'],classification=r['comparison']['classification']) for r in physical]),indent=2))
