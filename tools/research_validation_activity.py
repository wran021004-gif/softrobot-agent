"""Freeze and archive a bounded validation; execute the existing runner unchanged."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from tools.state_io import atomic_json, digest, read
from tools.platform_store import Store, plain, encode
from tools.research_mainline3 import configuration, interface_proposal, SOURCE

ROOT = Path(__file__).resolve().parents[1]


def prepare(out, authorization):
    if out.exists():
        raise ValueError('FRESH_ACTIVITY_DIRECTORY_REQUIRED')
    cfg = configuration()
    if (cfg['policy']['model']['base_url'], cfg['policy']['model']['model']) != ('https://api.deepseek.com', 'deepseek-flash'):
        raise ValueError('APPROVED_RECIPIENT_DIFFERS')
    identity = 'mainline3-validation-' + uuid4().hex[:12]
    out.mkdir(parents=True)
    files = ['docs/research_mainline3_v1_capabilities.md',
             'evidence/research_evidence_discovery_20261008/delivery_report.json',
             'evidence/research_evidence_discovery_20261008/future_interface_proposals.json',
             'tools/research_mainline3.py', 'tools/research_investigations.py',
             'tools/platform_models.py', 'tools/model_transports/deepseek.py',
             'tools/platform_store.py', 'configs/deepseek.yaml',
             'tools/research_validation_activity.py', 'tools/research_validation_gate.py',
             SOURCE.relative_to(ROOT).as_posix()]
    import hashlib
    hashes = {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files}
    phases = {mode: interface_proposal(mode) for mode in ('direct', 'coordinated')}
    phases['fixed'] = dict(project_budget=dict(model_calls=0, tool_calls=7, backend_solves=1,
        worker_calls=0, wall_s=4000.), scientific_operations=['linearize_configuration', 'control_metrics', 'bounded_endpoint'])
    for mode, phase in phases.items():
        grant = dict(project_id=identity+'-'+mode, grant_id=identity+'-'+mode,
            authorization_source='User authorization 2026-10-08; frozen manifest '+out.relative_to(ROOT).as_posix()+'/validation_manifest.json; phase '+mode,
            budget=phase['project_budget'])
        atomic_json(out/(mode+'_grant.json'), grant)
        phase['grant_identity'] = digest(grant)
        phase['activated'] = False
        phase['output'] = 'runs/'+identity+'-'+mode
    frozen = dict(robot=cfg['robot'], task=cfg['task'], seed=cfg['seed'], policy=cfg['policy'])
    atomic_json(out/'frozen_configuration.json', frozen)
    atomic_json(out/'authorization.json', dict(text=authorization.read_text(encoding='utf-8-sig'),
        external_data_scope='Task-scoped non-secret evidence, directory metadata, source references, versions, metrics, questions, tool results and bounded reports only.',
        forbidden='Credentials, unrelated files and personal data', approved_endpoint='https://api.deepseek.com', approved_model='deepseek-flash'))
    saved = read(ROOT/'evidence/research_evidence_discovery_20261008/offline_verification.json')
    prior = {}
    for mode in ('direct', 'coordinated'):
        record = saved['observations']['wire_'+mode]
        prior[mode] = dict(record_identity=digest(record), status=record['result']['status'],
            request_count=len(record['actual_requests']),
            roles={k:n['order']['role'] for k,n in record['nodes'].items()},
            principal_inspection_count=len(record['principal_reads']),
            disposition_receipts=record['result'].get('dispositions', []),
            actual_provider_interaction='unverified_offline_transport',
            investigator_selected_followup='unverified_real_model_behavior',
            passed_live_gate=False)
    atomic_json(out/'saved_prelaunch_gate.json', dict(version='mainline3_prelaunch@1.0.0',
        source='evidence/research_evidence_discovery_20261008/offline_verification.json',
        source_identity=digest(saved), phases=prior,
        decision='No prior live phase exists. Fresh direct validation permitted by this authorization; coordinator requires its new direct gate.',
        rule='Offline scripted reads and formal status do not establish real investigator selection.'))
    manifest = dict(activity_id=identity, date='2026-10-08', branch='feat/gvs-dynamics',
        code_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        relevant_files_sha256=hashes, configuration_identity=digest(frozen),
        dependencies={p:importlib.metadata.version(p) for p in ('mujoco','numpy','scipy','casadi','pydantic')},
        provider=cfg['policy']['model'], provider_identity=digest(cfg['policy']['model']),
        transport='Existing DeepSeekAdapter/request_completion; redirects refused; no automatic provider retries',
        phases=phases, launch_gates=dict(direct='Frozen inputs, matching recipient and saved prelaunch record',
            coordinated='All deterministic direct gates pass including investigator-selected novel original evidence read and material correctness review',
            fixed='All coordinated gates pass under separate allocation'),
        investigation_scope='Stage336 execution.factual_result; derived directory metadata and completed bounded reports; independent principal reads',
        fixed_source=SOURCE.relative_to(ROOT).as_posix(),
        fixed_changes={'design/near_routing_radius_scale':1.01,'design/far_routing_radius_scale':.99},
        source_permissions='Saved research evidence only, no external arbitrary file reads',
        stopping_rules=['Missing gate stops dependent phases','No retries or another backend attempt','Unconfirmed request retains original reservation','No unused budget transfer','No Version 2 development'],
        repair_ceiling=1, repairs_used=0, backend_attempt_ceiling=1, model_attempt_ceiling=42,
        accounting='Export original calls, events, artifacts and state from read-only SQLite. Provider reported tokens separate from byte estimates and unknown billing. Public math counts separate from internal attempts.',
        checks='Existing offline checks reused; only configuration/version/source identity checks run; no scientific calculation or broad discovery tests')
    atomic_json(out/'validation_manifest.json', manifest)
    print(encode(dict(activity_id=identity, output=str(out), provider_identity=manifest['provider_identity'])))


def export(out, mode, *, run_id=None):
    manifest=read(out/'validation_manifest.json')
    store=Store(ROOT/manifest['phases'][mode]['output'])
    with store.connect(True) as db:
        session=store.session(run_id or 'mainline3-'+mode, db)
        artifacts={r['id']:json.loads(r['body']) for r in db.execute('SELECT id,body FROM artifacts')}
        calls=[]
        for r in db.execute('SELECT * FROM calls ORDER BY rowid'):
            row=dict(r)
            for k in ('reserved','charged','resources','receipt'):
                if row[k] is not None:row[k]=json.loads(row[k])
            calls.append(row)
        bundle=dict(mode=mode, transport='real_configured_deepseek', project=store.config(db),
            state=session['state'], snapshot=session['snapshot'], artifacts=artifacts, calls=calls,
            events=[json.loads(r['body']) for r in db.execute('SELECT body FROM events ORDER BY seq')])
    atomic_json(out/(mode+'_bundle.json'), bundle)
    atomic_json(out/(mode+'_ledger.json'), store.remaining())
    print(encode(dict(mode=mode, nodes={k:dict(status=n['status'],usage=n.get('usage'),reason=n.get('reason'))
        for k,n in bundle['state'].get('investigations',{}).items()}, accounting=store.remaining())))


def execute(out, mode):
    manifest=read(out/'validation_manifest.json')
    cfg=configuration()
    if digest(cfg['policy']['model']) != manifest['provider_identity']:
        raise ValueError('FROZEN_PROVIDER_CONFIGURATION_DIFFERS')
    frozen=dict(robot=cfg['robot'],task=cfg['task'],seed=cfg['seed'],policy=cfg['policy'])
    if digest(frozen)!=manifest['configuration_identity']:
        raise ValueError('FROZEN_CONFIGURATION_DIFFERS')
    import hashlib
    if any(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h for p,h in manifest['relevant_files_sha256'].items()):
        raise ValueError('FROZEN_SOURCE_DIFFERS')
    prior={'coordinated':'direct','fixed':'coordinated'}.get(mode)
    if prior and not read(out/(prior+'_gate.json'))['passed']:
        raise ValueError('DEPENDENT_PHASE_GATE_NOT_PASSED')
    if (ROOT/manifest['phases'][mode]['output']).exists():
        raise ValueError('NO_AUTOMATIC_REPEAT_OR_NEW_BUDGET')
    if mode!='fixed':
        from examples.gvs_nmpc_route_experiment import load_credential
        load_credential(Path.home()/'.codex/.env')
    sys.argv=['tools.research_mainline3','--execute-grant',str(out/(mode+'_grant.json')),
        '--mode',mode,'--directory',str(ROOT/manifest['phases'][mode]['output'])]
    from tools.research_mainline3 import main
    try:
        main()
    finally:
        if (ROOT/manifest['phases'][mode]['output']/'platform.sqlite').exists():
            export(out,mode)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','execute','export'])
    parser.add_argument('directory',type=Path)
    parser.add_argument('--mode',choices=['direct','coordinated','fixed'],default='direct')
    parser.add_argument('--authorization',type=Path)
    args=parser.parse_args()
    if args.action=='prepare':prepare(args.directory.resolve(),args.authorization)
    elif args.action=='execute':execute(args.directory.resolve(),args.mode)
    else:export(args.directory.resolve(),args.mode)


if __name__=='__main__':main()
