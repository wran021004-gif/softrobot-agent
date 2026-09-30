"""Archive the completed Stage 3.34 run and build its compact review package."""
from __future__ import annotations

from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.platform_store import Store, plain
from tools.state_io import atomic_json, read

LIVE=ROOT/'runs/stage334_math_led_design_validation_20260930_final'
DETERMINISTIC=ROOT/'runs/stage334_math_route_validation_20260930_final_v3'
MATLAB=ROOT/'runs/stage334_matlab_endpoint_20260930_final_v2'
TASK_V2=ROOT/'runs/offline_task_analysis_20260930_final_v2'
EVIDENCE=ROOT/'evidence/stage334_math_led_design_20260930'
OPTIMIZER_REF={'artifact_id':'d923766bc6e95bee1de4c6436ccd5158e15013a363bdee2a8fee07f5d2144f5b','media_type':'application/json'}


def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()


def compact_receipt(receipt):
    return {key:receipt.get(key) for key in ('request_id','tool_id','tool_version','execution_id','execution_status',
        'solver_status','output','error','charged','cache_hit','analysis_status') if key in receipt}


def local_archive(store,run_id):
    events=store.events(run_id)
    kinds={'model_request','context_delivery','model_raw_response','model_decision','model_response',
        'model_protocol_correction','tool_argument_correction'}
    records=[]
    for event in events:
        if event['kind'] in kinds:
            records.append(dict(event=event,inputs=[store.artifact(r) for r in event['inputs']],
                outputs=[store.artifact(r) for r in event['outputs']]))
    raw=LIVE/'raw_provider_records.json.gz'
    raw.write_bytes(gzip.compress(json.dumps(records,ensure_ascii=False,separators=(',',':')).encode('utf8')))
    with store.connect(True) as db:
        receipts=[json.loads(row[0]) for row in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL')]
    atomic_json(LIVE/'receipts.json',receipts)
    atomic_json(LIVE/'provider_trace_summary.json',dict(run_id=run_id,event_count=len(events),
        event_kinds=dict(Counter(e['kind'] for e in events)),event_statuses={f"{k}:{s}":n for (k,s),n in
            Counter((e['kind'],e['status']) for e in events).items()},raw_trace=dict(path=str(raw.relative_to(ROOT)),
            sha256=sha256(raw),bytes=raw.stat().st_size),receipts=dict(path=str((LIVE/'receipts.json').relative_to(ROOT)),
            sha256=sha256(LIVE/'receipts.json'),bytes=(LIVE/'receipts.json').stat().st_size)))
    return events,receipts


def optimizer_summary(value):
    evaluations=[]
    for row in value['evaluations']:
        evaluations.append({key:row.get(key) for key in ('evaluation_index','candidate_id','configuration',
            'material_scenario','parameters','objective','unavailable_constructions','provider_called',
            'backend_executed','nmpc_solved')})
    return dict(kind=value['kind'],starting_binding=value['starting_binding'],bounds=value['bounds'],
        material_scenarios=value['material_scenarios'],objective=value['objective'],provenance=value['provenance'],
        proposals=value['proposals'],evaluations=evaluations,limitations=value['limitations'],
        protocol=value['protocol'],target=value['target'],evidence=value['evidence'])


def historical_bindings():
    rows=[]
    for case in read(LIVE/'historical_case.json')['bindings']:
        facts=case['candidate_facts'];result=case['factual_result']
        rows.append(dict(kind=case['kind'],candidate_id=facts['candidate_id'],configuration=facts['configuration'],
            parameters=facts['parameters'],source_session_id=case['source_session_id'],
            execution_id=result['execution_id'],valid_complete_execution=result['valid_complete_execution'],
            task_accepted=result['task_accepted'],terminal_error_m=result['terminal_error_m'],
            sampled_settling=result['sampled_settling'],real_time_demonstrated=result['real_time_demonstrated'],
            report=result['report'],evaluation=result['evaluation'],compatibility=case['compatibility']))
    return rows


def provider_extract(store,events):
    turns=[]
    for event in events:
        if event['kind']=='model_decision':
            decision=store.artifact(event['outputs'][0])
            turns.append(dict(event_id=event['event_id'],status='normalized',request_id=decision.get('request_id'),
                tool_id=decision.get('tool_id'),tool_version=decision.get('tool_version'),reason=decision.get('reason'),
                arguments=decision.get('arguments')))
        elif event['kind']=='model_response' and event['status']=='failed':
            out=store.artifact(event['outputs'][0])
            turns.append(dict(event_id=event['event_id'],status='protocol_failed',error=out.get('error')))
    return turns


def build():
    workflow=read(LIVE/'workflow.json');store=Store(LIVE);run_id=workflow['run_id'];session=store.session(run_id)
    events,receipts=local_archive(store,run_id)
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    optimizer=optimizer_summary(store.artifact(OPTIMIZER_REF))
    route=session['state']['route'];seed=store.artifact(route['nodes'][0]['result'])
    historical=historical_bindings()
    conditions=read(LIVE/'frozen_input.json')
    atomic_json(EVIDENCE/'scientific_conditions.json',dict(run_id=run_id,input_identity=workflow['input_identity'],
        task=conditions['task'],robot=conditions['robot'],design_space=conditions['policy']['candidate_builder'],
        controller=conditions['policy']['controller'],backend=conditions['policy']['backend'],
        dynamics_model=conditions['policy']['dynamics_model'],discretization=conditions['policy']['discretization'],
        seed=conditions['seed'],limits=workflow['limits'],route=conditions['policy']['route'],
        provider_configuration=conditions['policy']['model']))
    atomic_json(EVIDENCE/'protocols.json',dict(analysis=read(LIVE/'analysis_protocol.json'),
        endpoint_target=read(LIVE/'endpoint_target.json'),novelty_rule=read(LIVE/'novelty_rule.json'),
        live_optimizer_objective=optimizer['objective'],shared_optimizer_budget=dict(deterministic_evaluations=8,
            live_evaluations=optimizer['provenance']['distinct_evaluations'],limit=24,total=24)))
    atomic_json(EVIDENCE/'candidate_bindings.json',dict(historical=historical,
        live_seed=dict(candidate_facts=seed['candidate_facts'],evaluated=False,backend_executed=False,
            route_node=route['nodes'][0]),live_changed_candidates=[],live_executed_candidates=[]))
    atomic_json(EVIDENCE/'live_optimizer.json',optimizer)
    atomic_json(EVIDENCE/'route_tool_receipts.json',[compact_receipt(r) for r in receipts])
    atomic_json(EVIDENCE/'provider_turn_extract.json',provider_extract(store,events))
    audit=read(LIVE/'math_influence_audit.json')
    live_summary=dict(run_id=run_id,status='failed',implementation_commit=workflow['implementation_commit'],
        implementation_dirty=workflow['implementation_dirty'],stop_reason=session['state']['stop_reason'],
        usage=store.remaining()['used'],limits=workflow['limits'],provider_response_count=24,
        provider_responses_received=24,tool_calls_ledger=19,backend_executions=0,worker_calls=0,
        optimizer_evaluations=optimizer['provenance']['distinct_evaluations'],optimizer_called=True,
        optimizer_proposals_read=True,math_influenced_executed_design=False,
        qualifying_math_led_execution=audit['qualifying_math_led_execution'],final_candidate=None,
        official_reach=dict(available=False,reason='No changed candidate was executed.'),
        sampled_settling=dict(available=False,reason='No changed candidate was executed.'),
        real_time=dict(available=False,reason='No changed candidate was executed.'),
        delivery=dict(provider_authored_finish=False,fresh_report_delivered=False),
        environment=dict(required_interpreter=r'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe',
            live_invocation_interpreter=r'C:\Users\gugugaga\miniconda3\python.exe',conforming=False,
            post_run_verification_interpreter=sys.executable),
        integration_failure=dict(observed='Candidate-linearization envelope was rejected where a bare model reference was required.',
            repaired_after_run_commit=git('rev-parse','HEAD'),rerun=False))
    atomic_json(EVIDENCE/'live_experiment.json',live_summary)
    shutil.copy2(LIVE/'behavior_audit.json',EVIDENCE/'live_behavior_audit.json')
    shutil.copy2(MATLAB/'matlab_scipy_endpoint_comparison.json',EVIDENCE/'matlab_scipy_endpoint_comparison.json')
    shutil.copy2(MATLAB/'representative_endpoint_matrices.npz',EVIDENCE/'representative_endpoint_matrices.npz')
    deterministic_optimizer=read(DETERMINISTIC/'optimizer.json')
    atomic_json(EVIDENCE/'deterministic_route_validation.json',dict(verification=read(DETERMINISTIC/'verification.json'),
        usage=read(DETERMINISTIC/'usage.json'),report=read(DETERMINISTIC/'route_report.json'),
        optimizer=optimizer_summary(deterministic_optimizer)))
    atomic_json(EVIDENCE/'retained_task_analysis_v2.json',dict(kind='retained_historical_evidence_not_regenerated',
        verification=read(TASK_V2/'verification.json'),report=(TASK_V2/'report.txt').read_text(encoding='utf8'),
        resource_usage=read(TASK_V2/'resource_usage.json'),source_identity=read(TASK_V2/'source_identity.json'),
        control_divergence=read(TASK_V2/'control_divergence_facts.json'),
        shared_screen_callers=read(TASK_V2/'shared_screen_callers.json'),local_full_artifacts={p.name:dict(
            sha256=sha256(p),bytes=p.stat().st_size) for p in (TASK_V2/'primary_remaining_time_analysis.json',
                TASK_V2/'late_remaining_time_all_cases.json',TASK_V2/'configuration_build_bindings.json')}))
    atomic_json(EVIDENCE/'focused_tests.json',dict(interpreter=sys.executable,results=[
        dict(command=r"C:\Users\gugugaga\miniconda3\envs\softagent\python.exe -m unittest tests.test_task_analysis tests.test_math_analysis",
            tests=14,passed=14,failed=0,errors=0,elapsed_s=9.882,scope='Final focused suite after envelope repair.'),
        dict(command='python examples/stage334_math_route_validation.py',passed=True,optimizer_evaluations=8,
            provider_calls=0,backend_calls=0,workers=0,source=str(DETERMINISTIC.relative_to(ROOT))),
        dict(command='MATLAB Engine representative endpoint batch',passed=True,cases=5,session_count=1,
            source=str(MATLAB.relative_to(ROOT)))],notes=[
        'An earlier base-interpreter rerun failed the legacy v1 fixture because matlab.engine is not installed in base Python.',
        'The required softagent interpreter imports matlab.engine and the final 14-test focused suite passed.']))
    relevant=['schemas/platform_analysis.py','extensions/math_analysis/kernels.py','extensions/math_analysis/tools.py',
        'extensions/math_analysis/matlab.py','extensions/math_analysis/manifest.py','extensions/tendon_family/math_analysis.py',
        'extensions/tendon_family/route.py','extensions/tendon_family/optimization.py','extensions/tendon_family/historical_failure.py',
        'examples/gvs_stage334.py','examples/gvs_stage334_evidence.py','matlab/bounded_residual_certificate.m',
        'matlab/analyze_bounded_endpoint.m','tests/test_task_analysis.py','tests/test_math_analysis.py']
    atomic_json(EVIDENCE/'source_identity.json',dict(starting_commit='0c1ddc8',live_implementation_commit=workflow['implementation_commit'],
        evidence_commit_parent=git('rev-parse','HEAD'),branch=git('branch','--show-current'),
        source_hashes={name:sha256(ROOT/name) for name in relevant}))
    report=fr"""# Stage 3.34 math-led design validation

## Outcome

The mathematical layer, bounded optimizer, Route evidence linkage, and MATLAB/SciPy checks were implemented and verified. The one authorized live DeepSeek experiment ran to its frozen provider cap but did not execute a changed candidate. It is therefore a failed live design-and-validation experiment, not a reach result.

The live run used 24 provider requests, 19 charged tool calls, 0 backend attempts, 0 workers, and {live_summary['usage']['wall_s']} charged seconds. It stopped with `{session['state']['stop_reason']}`. The unchanged seed was built only for mathematics and was never executed.

## Mathematical use and live failure

DeepSeek invoked the optimizer for all 16 authorized live evaluations and read its two proposals. Both proposed near=0.15 m, far=0.11 m, scale=0.95; the compliant and stiff local residual-upper-bound ratios were both 0.2. The model never selected and built either proposal, so mathematics did not influence an executed design.

The blocking defect was a public-interface mismatch: `analysis.linearize_candidate` returned an envelope containing model references, while `analysis.control_metrics` and `analysis.bounded_endpoint` accepted only bare model references. Commit `{git('rev-parse','HEAD')}` repairs that post-run and adds a regression test. No second live experiment was run.

## Acceptance dimensions

- Mathematical correctness/reproducibility: focused tests pass; sound witnesses and separating-direction certificates are retained.
- MATLAB/SciPy: five representative cases passed in one MATLAB R2024a Engine session; Control System Toolbox and Optimization Toolbox were present and licensed.
- Deterministic Route/optimizer linkage: passed with eight evaluations and zero provider/backend/worker use.
- Genuine LLM use: optimizer invocation and proposal reading occurred, but selection/execution provenance did not; this item is incomplete.
- Reach, sampled settling, real time, and factual candidate delivery: unavailable because no changed candidate was executed.
- Environment conformance: failed for the live run because unqualified `python` resolved to base Conda Python 3.14 instead of `softagent` Python 3.11. Final verification used the required interpreter.

## Reproduction

From the repository root in PowerShell:

```powershell
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' -m unittest tests.test_task_analysis tests.test_math_analysis
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' examples/stage334_math_route_validation.py --output runs/stage334_math_route_reproduction
```

The paid live experiment must not be reproduced as part of ordinary review. See `manifest.json` for committed versus local-only evidence.
"""
    (EVIDENCE/'report.md').write_text(report,encoding='utf8')
    local_only={p.name:dict(path=str(p.relative_to(ROOT)),sha256=sha256(p),bytes=p.stat().st_size) for p in
        (LIVE/'platform.sqlite',LIVE/'raw_provider_records.json.gz',LIVE/'receipts.json',LIVE/'frozen_input.json',
            LIVE/'historical_case.json',LIVE/'route_status.json')}
    files={p.name:dict(sha256=sha256(p),bytes=p.stat().st_size) for p in sorted(EVIDENCE.iterdir()) if p.name!='manifest.json'}
    atomic_json(EVIDENCE/'manifest.json',dict(package='stage334_math_led_design_20260930',committed_files=files,
        local_only=local_only,credentials_included=False,large_sqlite_included=False,raw_provider_trace_included=False,
        note='Raw provider requests/responses and the SQLite ledger are retained locally with hashes; the committed provider-turn extract and receipts are sufficient compact review evidence.'))
    print(json.dumps(dict(evidence=str(EVIDENCE),files=len(files)+1,live=live_summary,
        manifest_sha256=sha256(EVIDENCE/'manifest.json')),indent=2))


if __name__=='__main__': build()
