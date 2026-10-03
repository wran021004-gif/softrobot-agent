"""Assemble offline delivery from observed saved state and focused check logs."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from unittest.mock import patch
from contextlib import ExitStack
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.platform_store import Store,plain,encode
from tools.platform_host import Host
from tools.platform_models import payload_for
from tools.diagnostic_reference_adapter import ScopedReferenceAdapter
from tools.working_state import project_working_state
from tools.diagnostic_handoff import engineering_fixture
from tools.state_io import read,atomic_json
from tools.runtime_identity import require_softagent_runtime


def deliver():
    runtime=require_softagent_runtime()
    destination=ROOT/'evidence/stage355_milestone1_20261003'
    checks=['focused_checks','affected_rerun','affected_rerun2','affected_rerun3','affected_rerun4','affected_rerun5']
    latest={}
    for label in checks:
        for match in re.finditer(r'^(test_\w+) \(([^)]+)\) \.\.\. (ok|FAIL|ERROR)$',
                (destination/(label+'.txt')).read_text(encoding='utf8'),re.MULTILINE):
            latest[match[2]+'.'+match[1]]=dict(status=match[3],source=label+'.txt')
        assert read(destination/(label+'.json'))['forbidden_live_attempts']==[0,0,0]
    assert len(latest)==31 and all(row['status']=='ok' for row in latest.values()),latest
    rows=[]
    with ExitStack() as guards:
        for target in ('tools.model_transports.deepseek.request_completion',
                       'extensions.tendon_family.backends.MujocoBackend.run',
                       'extensions.tendon_family.gvs_trajectory.TrajectoryWorkspace.solve'):
            guards.enter_context(patch(target,side_effect=AssertionError('Delivery is offline')))
        for stage in ('stage353','stage354'):
            for mode in ('single_context','dual_context'):
                store=Store(ROOT/f'runs/{stage}_milestone0_20261003'/mode)
                with store.connect(True) as db:
                    ids=[r[0] for r in db.execute('SELECT run_id FROM sessions') if r[0].endswith(('shared','design','diagnostic'))]
                    before=hashlib.sha256('\n'.join(db.iterdump()).encode()).hexdigest()
                for identity in ids:
                    view=project_working_state(store,identity)
                    payload=payload_for(Host(store.root,identity),ScopedReferenceAdapter())
                    assert json.loads(payload['messages'][1]['content'])['working_state']==plain(view)
                    size=len(encode(payload).encode())
                    assert size<=400000
                    filename=f'{stage}_{mode}_{view.workflow["role"]}_working_state.json'
                    atomic_json(destination/filename,plain(view))
                    rows.append(dict(stage=stage,organization=mode,context=identity,view=filename,
                        payload_bytes=size,context_cap_bytes=400000,computation_complete=view.workflow['computation_complete'],
                        delivery_complete=view.workflow['delivery_complete'],selection=view.selection,
                        latest_tested=view.latest_tested,acceptance_missing=view.acceptance['missing']))
                    if stage=='stage354' and mode=='dual_context' and view.workflow['role']=='design':
                        atomic_json(destination/'milestone2_engineering_fixture.json',plain(engineering_fixture(store,view)))
                with store.connect(True) as db:
                    assert before==hashlib.sha256('\n'.join(db.iterdump()).encode()).hexdigest()
    changed=subprocess.check_output(['git','diff','5abe016','--name-only','--','evidence/stage353_milestone0_20261003','evidence/stage354_milestone0_20261003'],cwd=ROOT,text=True).splitlines()
    assert changed==['evidence/stage354_milestone0_20261003/scientific_review.json','evidence/stage354_milestone0_20261003/sha256_manifest.json'],changed
    review_root=ROOT/'evidence/stage354_milestone0_20261003'
    manifest=read(review_root/'sha256_manifest.json')
    assert manifest['scientific_review.json']==hashlib.sha256((review_root/'scientific_review.json').read_bytes()).hexdigest()
    summary=dict(stage='3.55',milestone1_passed=True,unmet_conditions=[],milestone2_completed=False,
        runtime=runtime,starting_commit='5abe016b78fa5cebffcad0e9bc9c04beac681182',
        implementation_commits=['8490e2a','b54517c','99a40b6'],delivery_date='2026-10-04',
        implemented_contract='platform.working_state@1.0.0',
        consumers=['Host.context','platform_models.input_for/payload_for','FlatDiagnosticAdapter/BoundSavedStateAdapter/ScopedReferenceAdapter','examples/stage355_inspect.py','diagnostic_handoff.consume_handoff'],
        saved_cases=rows,focused_checks=dict(unique_tests_passed=len(latest),new_checks=8,affected_existing_checks=23,latest_results=latest),
        acceptance_sources='docs/stage355_milestone1.md#acceptance-sources',
        change_impacts='tools/parameter_impacts.py: two reach speed weights only',
        review_amendment=dict(commit='685c7c7',changed_evidence_files=changed,
            verified_submitted_name='improvement-744833040049',correct_bound_candidate='improvement-744833804049',
            affected_field='dual_context.final_response.reasoning',original_records_preserved=True),
        stage_activity=dict(new_provider_requests=0,new_backend_simulations=0,new_optimization_runs=0,workers=0,subagents=0),
        accounting_note='Mocked regression workflows may seal fixture model/backend receipts and return saved results; those fixture ledger totals are not this stage activity or new historical executions.',
        verification_limitations=['Offline only; no paid provider or backend validation.',
            'First run hit Windows sandbox temporary-directory permissions; affected offline reruns used approved local filesystem access.',
            'Initial native-name rewrite, infrastructure fingerprint guard, fixture SQLite cleanup and autospec blocker issues were fixed; original logs retained.',
            'The explicit historical import infrastructure allowlist now includes platform_store.py because ledger capacity checks were factored without changing evaluator/scientific contracts.',
            'One task and the saved organizations; no statistical or causal claim, performance campaign or full repository suite.',
            'Projection action permission is phase-level; exact arguments, preflight/resource costs and compatibility still require existing Host validation.'],
        milestone2=dict(prepared='Typed evidence-driven diagnostic consumer, exact-scope validator and engineer-authored saved-evidence handoff.',
            next_executable_target='Materialize accepted report/revision into the diagnostic handoff and validate a bounded search-batch plan with hypothesis/evidence, variables, fixed conditions, objectives/constraints, method/budget, verification/stopping.',
            unimplemented=['Model-authored handoff','Search-plan execution','Search executor','Automatic memory','Skill discovery','Coding agents','New optimization campaigns']),pushed=False)
    atomic_json(destination/'delivery_summary.json',summary)
    atomic_json(destination/'sha256_manifest.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(destination.iterdir()) if p.is_file() and p.name!='sha256_manifest.json'})
    print(json.dumps(dict(milestone1_passed=True,unique_checks_passed=31,payload_bytes=[r['payload_bytes'] for r in rows],stage_activity=summary['stage_activity']),indent=2))


if __name__=='__main__':
    deliver()
