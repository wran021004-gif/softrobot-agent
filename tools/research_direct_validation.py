"""Freeze and run only the bounded direct public scenario; no scientific path."""
import argparse
from contextlib import closing
import importlib.metadata
import json
from pathlib import Path
import subprocess
import threading
import time
from uuid import uuid4
from tools.state_io import atomic_json,read,digest
from tools.platform_store import Store,plain,encode,now
from tools.platform_host import Host
from tools.context_assembly import _no_secrets
from tools.research_mainline3 import configuration,interface_proposal,direct_validation_plan,live_interface_scenario
from tools.research_investigations import InvestigationDispatcher
from tools.research_single_validation import sha,stop,old_review

ROOT=Path(__file__).resolve().parents[1]
BASE='20839fe62d0c5200caa3a0114e213e0b4dbface9'
SOURCE='runs/stage336_manual_20261001_090616/stage336_audit.json'
RUN='mainline3-direct'
FILES=('tools/research_direct_validation.py','tools/research_mainline3.py','tools/research_validation_gate.py',
    'tools/research_investigations.py','tools/platform_host.py','tools/platform_store.py',
    'tools/platform_models.py','tools/model_transports/deepseek.py','configs/deepseek.yaml',SOURCE)

def history():
    previous=ROOT/'evidence/research_request_compatibility_20261008'
    manifest=read(previous/'validation_manifest.json');store=Store(ROOT/manifest['store'])
    return dict(earlier=old_review(),last_single=dict(db_sha256=sha(store.db),ledger=store.remaining(),
        status=store.session(manifest['activity_id'])['status'],
        files={p.relative_to(ROOT).as_posix():sha(p) for p in previous.iterdir() if p.is_file()}))

def prepare(out):
    if out.exists():raise ValueError('FRESH_ACTIVITY_REQUIRED')
    subprocess.check_call(['git','merge-base','--is-ancestor',BASE,'HEAD'],cwd=ROOT)
    proposal=interface_proposal('direct');cfg=configuration()
    approved=read(ROOT/'evidence/research_request_compatibility_20261008/frozen_configuration.json')['policy']['model']
    if cfg['policy']['model']!=approved or (approved['base_url'],approved['model'],approved['thinking'],approved['reasoning_effort'])!=(
        'https://api.deepseek.com','deepseek-flash','enabled','high'):raise ValueError('APPROVED_MODEL_CONFIGURATION_DIFFERS')
    out.mkdir(parents=True);identity='mainline3-direct-'+uuid4().hex[:12]
    cfg['run_id']=RUN
    cfg['policy'].update(route=None,budget=proposal['project_budget'],allowed_tools=list(proposal['tool_bindings']),
        tool_bindings=proposal['tool_bindings'],timeout_s=2400.,operation_allowances=proposal['operation_allowances'])
    grant=dict(project_id=identity,grant_id=identity,budget=proposal['project_budget'],
        authorization_source='User 2026-10-08 bounded real direct investigations only; '+out.relative_to(ROOT).as_posix())
    store=Store(ROOT/'runs'/identity);store.create(grant);host=Host(store.root,RUN);host.create(cfg);host.resume()
    with store.transaction() as db:
        factual=read(ROOT/SOURCE)['execution']['factual_result'];_no_secrets(factual)
        source=plain(store.put(db,factual))
        state=store.session(RUN,db)['state']
        ig=dict(max_count=3,max_concurrency=2,allowed_tools=['evidence.read'],evidence=[source],
            include_completed_reports=True,per_node_budget=proposal['node_budget'],total_budget=proposal['total_node_budget'])
        state['role_context']=dict(role='principal',investigation_grant=ig)
        state['investigation_grant_identity']=digest(ig);store.update_state(db,RUN,state)
    plan=direct_validation_plan(source)
    wires={}
    try:
        # Offline bounded page assembly only; actual prefetch is charged at execution.
        for order in plan['questions']:
            _,wire,reads,measurement=InvestigationDispatcher(host).prepare(order)
            assert len(reads)==1 and wire['tool_choice']=='auto'
            assert wire['thinking']=={'type':'enabled'} and wire['reasoning_effort']=='high'
            assert wire['max_tokens']==3000 and wire['model']=='deepseek-flash'
            _no_secrets(wire);wires[order['investigation_id']]=dict(payload=wire,reads=reads,measurement=measurement)
        from schemas.platform_operations import ReadEvidence
        from tools.platform_tools import bounded_evidence_page
        for query in plan['principal_inspections']:
            inspection=plain(bounded_evidence_page(factual,ReadEvidence.model_validate(query)))
            assert inspection['next_offset'] is None and inspection['kind']=='content'
    finally:stop(host,'PREPARED_ONLY_NO_PROVIDER_CALL')
    atomic_json(out/'authorization.json',dict(project=grant,proposal=proposal,
        permitted_roles=['investigator','investigator','principal'],forbidden=['coordinator','children','science','workers','Version 2','retries','protocol corrections','polishing'],
        data_scope='Non-secret Stage336 saved facts, source directory, question/tool context, checked reports and principal inspections',
        recipient='https://api.deepseek.com',model='deepseek-flash',repair_ceiling=1))
    atomic_json(out/'frozen_configuration.json',cfg);atomic_json(out/'direct_plan.json',plan)
    atomic_json(out/'prepared_requests.json',wires);atomic_json(out/'historical_before.json',history())
    manifest=dict(activity_id=identity,run_id=RUN,phases=dict(direct=dict(output=store.root.relative_to(ROOT).as_posix())),
        code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        relevant_files_sha256={p:sha(ROOT/p) for p in FILES},configuration_identity=digest(cfg),provider_identity=digest(approved),
        plan_identity=digest(plan),source=dict(path=SOURCE,sha256=sha(ROOT/SOURCE),pointer='/execution/factual_result',reference=source,
            execution_id=factual['execution_id'],case='Stage336 math-compliant proposal-build; no new robot execution'),
        dependencies={p:importlib.metadata.version(p) for p in ('pydantic','numpy','scipy','casadi','mujoco')},
        model_output_tokens=3000,report_bytes=16384,node_timeout_s=180,project_wall_s=2400,
        retries=0,protocol_corrections=0,repair_ceiling=1,repairs_used=1,
        preparation_passed=True,stopping=['Terminal failed/incomplete/unconfirmed prerequisite stops further submissions',
            'No qualifying investigator follow-up means unverified, never add paid coverage calls',
            'Stop after direct delivery, drift, budget/time exhaustion or unsafe recovery; retain unknown reservations'])
    atomic_json(out/'validation_manifest.json',manifest)
    from tools.research_validation_gate import generate
    old_bundle=read(ROOT/'evidence/research_mainline3_validation_20261008/direct_bundle.json')
    atomic_json(out/'saved_prelaunch_gate.json',dict(historical_direct_gate=generate(old_bundle),
        single_gate=read(ROOT/'evidence/research_request_compatibility_20261008/gate.json'),
        decision='Fresh direct authority only; prior single report is not a direct/follow-up gate',provider_calls=0))
    print(encode(dict(activity=identity,prepared=True,provider_calls=0)))

def export(out,live):
    from tools.research_validation_activity import export as export_existing
    export_existing(out,'direct')
    manifest=read(out/'validation_manifest.json');store=Store(ROOT/manifest['phases']['direct']['output'])
    bundle=read(out/'direct_bundle.json');bundle['transport']='real_configured_deepseek' if live else 'deterministic_offline_substitute'
    bundle['session_status']=store.session(RUN)['status'];_no_secrets(bundle)
    atomic_json(out/'direct_bundle.json',bundle)
    atomic_json(out/'historical_after.json',dict(unchanged=history()==read(out/'historical_before.json'),review=history()))
    from tools.research_validation_gate import generate
    atomic_json(out/'direct_gate.json',generate(bundle))

def execute(out,*,live=True):
    manifest=read(out/'validation_manifest.json')
    if (out/'launch.json').exists():raise ValueError('NO_REPEATED_LAUNCH')
    cfg=read(out/'frozen_configuration.json');plan=read(out/'direct_plan.json')
    assert manifest['preparation_passed'] and digest(cfg)==manifest['configuration_identity'] and digest(plan)==manifest['plan_identity']
    assert all(sha(ROOT/p)==h for p,h in manifest['relevant_files_sha256'].items())
    assert digest(configuration()['policy']['model'])==manifest['provider_identity']
    assert history()==read(out/'historical_before.json')
    host=Host(ROOT/manifest['phases']['direct']['output'],RUN)
    assert host.store.session(RUN)['status']=='stopped' and not host.store.session(RUN)['state'].get('investigations')
    assert host.compatibility()['compatible']
    atomic_json(out/'launch.json',dict(timestamp=now(),live=live,repeat_forbidden=True))
    started=time.monotonic()
    try:
        if live:
            from examples.gvs_nmpc_route_experiment import load_credential
            load_credential(Path.home()/'.codex/.env')
        host.resume()
        with host.store.transaction() as db:
            state=host.store.session(RUN,db)['state'];grant=state['role_context']['investigation_grant']
            grant['deadline_unix']=time.time()+2400.-(time.monotonic()-started)
            state['investigation_grant_identity']=digest(grant);host.store.update_state(db,RUN,state)
            host.store.event(db,RUN,'direct_validation_authorization','activated',outputs=[host.store.put(db,grant)])
        result=live_interface_scenario(host,'direct',plan=plan)
        atomic_json(out/'direct_result.json',result)
    except Exception as exc:
        atomic_json(out/'application_failure.json',dict(timestamp=now(),exception_type=type(exc).__name__,
            elapsed_s=time.monotonic()-started,provider_outcome='Use original events; no replay or assumed billing'))
        raise
    finally:
        # Blocks further model/evidence consumption before waiting on owned work.
        stop(host,'DIRECT_VALIDATION_TERMINAL_OR_FAILED_PREREQUISITE_NO_NEXT_PHASE')
        threads=[t for t in threading.enumerate() if t.name.startswith('investigation-')]
        for thread in threads:thread.join(190.)
        atomic_json(out/'application_lifecycle.json',dict(elapsed_s=time.monotonic()-started,
            thread_active_at_close=[t.name for t in threads if t.is_alive()],
            thread_completed_before_close=not any(t.is_alive() for t in threads),
            provider_cancellation_confirmed=False,stopped=True,remote_completion_not_inferred=True))
        export(out,live)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','execute'])
    parser.add_argument('directory',type=Path);args=parser.parse_args();out=args.directory.resolve()
    if not out.is_relative_to(ROOT/'evidence'):raise ValueError('TASK_EVIDENCE_DIRECTORY_REQUIRED')
    (prepare if args.action=='prepare' else execute)(out)

if __name__=='__main__':main()
