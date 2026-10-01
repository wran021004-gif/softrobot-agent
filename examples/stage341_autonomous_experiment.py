"""One authorized autonomous design session using deterministic control evidence."""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
from examples import stage340_bounded_autonomous_experiment as prior_runner
from examples.gvs_nmpc_route_experiment import load_credential
from examples.gvs_stage334 import historical_sources
from examples.stage337_autonomous_design_experiment import protocol_and_target
from extensions.tendon_family.historical_failure import bind_sources,bind_failure
from extensions.tendon_family.route import create
from tools.platform_host import Host
from tools.platform_store import Store,plain
from tools.platform_models import ReadableDeepSeekAdapter,payload_for,tool_naming_policy,READABLE_TOOL_NAMING
from tools.runtime_identity import require_softagent_runtime
from tools.state_io import atomic_json,read,digest

SOURCE=ROOT/'runs/stage340_bounded_autonomous_20261001'
EVIDENCE=ROOT/'evidence/stage341_control_evidence_20261001'
OUTPUT=ROOT/'runs/stage341_autonomous_20261001'
TOOLS={**prior_runner.TOOLS,'control.inspect_evidence':'1.0.0','control.compare_evidence':'1.0.0'}


def guidance(ref):
    return prior_runner.guidance(ref).replace('compact reconstructed NMPC evidence','deterministic recorded control evidence').replace(
        'The diagnostics support no controller change and do not prove intrinsic design infeasibility.',
        'Read the explicit adoption decision and its scope; local evidence does not prove intrinsic design infeasibility.')+(
        ' Stage 3.40 selected noninitialization plans on 26 updates, initialization on 9; do not describe it as constant tension throughout. '
        'The approximately 2 mm affine residual belongs to a frozen straight-start local model and its witness: world-x control is degenerate, '
        'and it excludes nonlinear closed-loop dynamics and braking. A different backend error neither invalidates that local bound nor proves search useless. '
        'Use control.inspect_evidence for compact saved-update and same-input one-step comparisons after execution if needed. '
        'A revision after failure requires a specific evidence-supported reason, not an attempt to consume the remaining budget. '
        'Stop backend search after a fresh covered reach pass, and deliver through your normal finish. '
        'State observed findings separately from suspected causes. Do not request a diagnostic LLM or workers.')


def identity(host):
    snapshot=host.store.session(host.run_id)['snapshot']
    return dict(dependencies=digest(snapshot['dependencies']),entrypoint=prior_runner.sha256(__file__),
        reused_runner=prior_runner.sha256(prior_runner.__file__))


def prepare():
    runtime=require_softagent_runtime()
    if (OUTPUT/'freeze_manifest.json').exists():return Host(OUTPUT,read(OUTPUT/'freeze_manifest.json')['run_id'])
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True):raise RuntimeError('LIVE_FREEZE_REQUIRES_CLEAN_WORKTREE')
    if (OUTPUT/'platform.sqlite').exists():raise RuntimeError('EXISTING_UNFROZEN_SESSION_REQUIRES_INSPECTION')
    diagnosis=read(EVIDENCE/'diagnosis.json')
    if not diagnosis['ready_for_live']:raise RuntimeError('DIAGNOSIS_NOT_READY')
    inp=deepcopy(read(SOURCE/'frozen_input.json'));run='gvs-stage341-'+os.urandom(6).hex();inp['run_id']=run
    budget=dict(model_calls=24,tool_calls=60,backend_solves=3,worker_calls=0,wall_s=3600.)
    inp['policy'].update(budget=budget,timeout_s=1800.,allowed_tools=[],tool_bindings=TOOLS)
    inp['policy']['model'].update(max_turns=24,context_bytes=200000,tool_naming=tool_naming_policy(TOOLS,READABLE_TOOL_NAMING))
    adoption=diagnosis['correction']
    if adoption['adopted']:
        inp['policy']['controller']=deepcopy(adoption['controller'])
        for combination in inp['policy']['route']['data']['combinations'].values():
            if combination['controller']['extension_id']=='controller.gvs_nmpc':combination['controller']=deepcopy(adoption['controller'])
    store=Store(OUTPUT);store.create(dict(project_id=run,grant_id=run,budget=budget,
        authorization_source='User explicitly authorized one new paid DeepSeek design experiment with frozen context and subsequent evidence, Stage 3.41.'))
    protocol,target=protocol_and_target(inp)
    with store.transaction() as db:
        pref=plain(store.put(db,protocol));tref=plain(store.put(db,target));dref=plain(store.put(db,diagnosis))
    historical=bind_sources(historical_sources(),inp,store)
    source_audit=read(SOURCE/'stage340_audit.json');previous=source_audit['evaluated_candidates'][-1]
    index=dict(live_session=source_audit['run_id'],configuration=previous['candidate_facts']['configuration'],
        candidate_id=previous['candidate_id'],profile_report=previous['profile_report'],evaluation=previous['factual_result']['evaluation'])
    case=bind_failure(SOURCE,inp,index,Store(SOURCE))
    with store.transaction() as db:
        case['detail_export']=plain(store.put(db,previous));historical['cases'].append(case);href=plain(store.put(db,historical))
    inp['policy']['route']['data'].update(source='User-authorized Stage 3.41',historical_case=href,historical_math=None,
        analysis_protocol=pref,endpoint_target=tref,max_trials=3,math_evaluation_limit=16,
        analysis_required_before_run=True,math_selection_required_before_run=True,stop_on_task_success=True,
        multi_category_coverage_required=True,stop_on_constant_initialization=True,guidance=guidance(dref))
    create(OUTPUT,inp);host=Host(OUTPUT,run);payload=payload_for(host,ReadableDeepSeekAdapter())
    values=dict(frozen_input=inp,diagnostic_evidence=diagnosis,analysis_protocol=plain(protocol),endpoint_target=plain(target),
        historical_case=dict(reference=href,content=historical),runtime_identity=runtime,
        actual_provider_payload=payload,provider_tools=payload['tools'],provider_configuration=inp['policy']['model'],
        project_configuration=store.config())
    for name,value in values.items():atomic_json(OUTPUT/(name+'.json'),value)
    freeze=dict(run_id=run,status='prepared',implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        implementation_identity=identity(host),scientific_source=dict(path=str(SOURCE.relative_to(ROOT)),sha256=prior_runner.sha256(SOURCE/'frozen_input.json')),
        limits=budget,math_evaluation_limit=16,provider=inp['policy']['model'],diagnostic_reference=dref,
        session_input_identity=digest(inp),files={name+'.json':prior_runner.sha256(OUTPUT/(name+'.json')) for name in values})
    atomic_json(OUTPUT/'freeze_manifest.json',freeze);atomic_json(OUTPUT/'workflow.json',freeze)
    return host


def verify(host):
    freeze=read(OUTPUT/'freeze_manifest.json')
    checks=dict(runtime=require_softagent_runtime()==read(OUTPUT/'runtime_identity.json'),
        files=all(prior_runner.sha256(OUTPUT/name)==value for name,value in freeze['files'].items()),
        implementation=identity(host)==freeze['implementation_identity'],compatibility=host.compatibility()['compatible'],
        session_input=digest(host.store.session(host.run_id)['snapshot']['input'])==freeze['session_input_identity'],
        provider_payload=payload_for(host,ReadableDeepSeekAdapter())==read(OUTPUT/'actual_provider_payload.json'))
    result=dict(checked_at=datetime.now().astimezone().isoformat(),checks=checks,passed=all(checks.values()),
        before_credentials=True,before_provider=True,before_backend=True)
    atomic_json(OUTPUT/'prelaunch_verification.json',result)
    if not result['passed']:raise RuntimeError(result)


def export(host):
    # Reuse the established factual/provenance/finish auditor; its Stage 3.40 filename is local only.
    audit=prior_runner.audit(host);outcome=prior_runner.outcome(audit)
    atomic_json(OUTPUT/'stage341_audit.json',audit);atomic_json(OUTPUT/'outcome_summary.json',outcome)
    return outcome


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','run','inspect']);args=parser.parse_args()
    host=prepare() if args.action!='inspect' else Host(OUTPUT,read(OUTPUT/'freeze_manifest.json')['run_id'])
    if args.action=='run':
        if host.store.remaining(host.run_id)['used']['model_calls'] or (OUTPUT/'live_attempt.json').exists():
            raise RuntimeError('ONE_LIVE_SESSION_ALREADY_ATTEMPTED_NO_REPLACEMENT')
        verify(host)
        atomic_json(OUTPUT/'live_attempt.json',dict(run_id=host.run_id,destination='https://api.deepseek.com',
            authorization='Explicit user request; task/design context, schemas, diagnosis, summaries and tool results only; credentials never in artifacts.'))
        load_credential(Path.home()/'.codex/.env')
        print('Starting the one authorized Stage 3.41 design session: '+host.run_id,flush=True)
        host.run();print(export(host),flush=True)
    elif args.action=='inspect':print(export(host),flush=True)
    else:print('Prepared '+host.run_id,flush=True)


if __name__=='__main__':main()
