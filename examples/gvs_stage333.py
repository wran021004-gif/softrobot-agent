"""Stage 3.33 preparation and evidence retention; execution uses the normal launcher."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.state_io import read, atomic_json, digest
from tools.platform_store import Store
from tools.platform_host import Host
from tools.platform_models import payload_for, DeepSeekAdapter
from examples.gvs_revision_input import independent_lengths_input
from examples.gvs_nmpc_route_experiment import prepare, inspect
from extensions.tendon_family.candidate_comparison import exploration_summary

SOURCE=Path('runs/stage331_autonomous_revision_execution_20260929_014645')
SOURCE32=Path('runs/stage332_evidence_guided_design_exploration_20260929_090221')


def descriptors():
    return [dict(directory=str(SOURCE),source_session_id='gvs-live-c0f08900d76e',
        candidate_ids=['rev_compliant_max','c2_stiff_scale1p01','c3_compliant_scale1p02'],
        records='actual_revised_candidates.json',live_store='live',ledger='platform.sqlite.gz',
        frozen_input='resolved_frozen_input.json',backend_evidence='backend_evidence.zip'),
        dict(directory=str(SOURCE32),source_session_id='gvs-live-b8f4ab5f17f2',
        candidate_ids=['fresh_near0p165_far0p125_compliant_s1p05','fresh_near0p168_far0p128_compliant_s1p05',
            'b4_n1666_f1266_compliant_s1p05','b6_n1675_f1275_compliant_s1p05'],
        records='actual_new_candidates.json',live_store='live_network',ledger='live_network_platform.sqlite.gz',
        frozen_input='replacement_resolved_input.json',backend_evidence='backend_evidence.zip')]


def identity():
    files=subprocess.check_output(['git','ls-files'],text=True).splitlines()
    return dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        hashes={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in files
            if Path(p).is_file() and not p.startswith('runs/')})


def freeze(root):
    if (root/'freeze.json').exists(): raise ValueError('ALREADY_FROZEN')
    atomic_json(root/'frozen_input.json',independent_lengths_input(SOURCE))
    atomic_json(root/'historical_sources.json',descriptors())
    host=prepare(root/'live',SOURCE,root/'frozen_input.json',historical_sources=descriptors())
    snapshot=host.store.session(host.run_id)['snapshot']['input']
    prior=read(root/'live/historical_case.json')
    atomic_json(root/'resolved_frozen_input.json',snapshot)
    atomic_json(root/'prior_case_bindings.json',prior)
    atomic_json(root/'model_configuration.json',snapshot['policy']['model'])
    atomic_json(root/'frozen_provider_request.json',payload_for(host,DeepSeekAdapter()))
    atomic_json(root/'exploration_initial.json',exploration_summary(host,snapshot,prior['content']))
    atomic_json(root/'freeze.json',dict(run_id=host.run_id,source=identity(),
        input_identity=digest(read(root/'frozen_input.json')),resolved_identity=digest(snapshot),
        descriptor_identity=digest(descriptors()),usage=host.store.remaining()))


def archive(root):
    host=Host(root/'live',read(root/'freeze.json')['run_id']);store=host.store
    audit=inspect(host);session=store.session(host.run_id);snapshot=session['snapshot']['input']
    events=store.events(host.run_id)
    records=[]
    for event in events:
        if event['kind'] in ('context_delivery','model_raw_response','model_protocol_correction','model_length_recovery','tool_argument_correction'):
            records.append(dict(event=event,inputs=[store.artifact(r) for r in event['inputs']],
                outputs=[store.artifact(r) for r in event['outputs']]))
    (root/'raw_provider_records.json.gz').write_bytes(gzip.compress(json.dumps(records,ensure_ascii=False).encode()))
    with store.connect(True) as db:
        receipts=[json.loads(r[0]) for r in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL')]
    atomic_json(root/'receipts.json',receipts)
    atomic_json(root/'usage_audit.json',store.remaining())
    atomic_json(root/'recovery_events.json',dict(counters={k:session['state'].get(k,0) for k in
        ('protocol_corrections_used','protocol_corrections_consecutive','length_retries_used')},
        stop_reason=session['state'].get('stop_reason'),events=[r for r in records if 'correction' in r['event']['kind'] or 'recovery' in r['event']['kind']]))
    prior=read(root/'prior_case_bindings.json')['content']
    summary=exploration_summary(host,snapshot,prior)
    atomic_json(root/'exploration_final.json',summary)
    from extensions.tendon_family.route import trial_facts
    from extensions.tendon_family.delivery_facts import bound_result_facts
    candidates=[]
    for node in session['state']['route']['nodes']:
        if node['action']=='run' and node['status']=='completed':
            trial=store.artifact(node['result']);facts=trial_facts(store,snapshot,trial)
            candidates.append(dict(node_id=node['node_id'],evidence=node['result'],candidate_facts=facts,
                factual_result=bound_result_facts(store,trial,facts),motion_summary=trial.get('profile_report_summary',{}).get('motion_summary')))
    atomic_json(root/'actual_fresh_candidates.json',candidates)
    final=session['state']['route'].get('final')
    deliveries=[a for a in audit['actions'] if (a.get('decision') or {}).get('arguments',{}).get('action')=='finish']
    atomic_json(root/'original_provider_delivery.json',dict(formal_completed=bool((final or {}).get('explicit_delivery')),
        attempts=deliveries,final=final,absence_reason=None if deliveries else session['state'].get('stop_reason')))
    atomic_json(root/'freeze_audit.json',dict(source_unchanged=identity()['hashes']==read(root/'freeze.json')['source']['hashes'],
        input_unchanged=digest(read(root/'frozen_input.json'))==read(root/'freeze.json')['input_identity'],
        resolved_unchanged=digest(snapshot)==read(root/'freeze.json')['resolved_identity']))
    import sqlite3
    backup=root/'retained.sqlite'
    with store.connect(True) as source, sqlite3.connect(backup) as dest: source.backup(dest)
    source.close();dest.close()
    (root/'platform.sqlite.gz').write_bytes(gzip.compress(backup.read_bytes()));backup.unlink()
    with zipfile.ZipFile(root/'backend_evidence.zip','w',zipfile.ZIP_DEFLATED) as archive_file:
        for p in sorted((root/'live').rglob('*')):
            if p.is_file() and ('executions' in p.parts or p.name in ('trajectory.json.gz','controller_observations.json')):
                archive_file.write(p,p.relative_to(root/'live'))
    atomic_json(root/'evidence_index.json',dict(run_id=host.run_id,artifacts=[p.name for p in root.iterdir() if p.is_file()],
        live_store='live/platform.sqlite',host_summary='live/behavior_audit.json'))


def verify(root):
    frozen=read(root/'freeze.json')
    host=Host(root/'live',frozen['run_id'])
    if (identity()['hashes']!=frozen['source']['hashes'] or
        digest(read(root/'frozen_input.json'))!=frozen['input_identity'] or
        digest(host.store.session(host.run_id)['snapshot']['input'])!=frozen['resolved_identity'] or
        digest(read(root/'historical_sources.json'))!=frozen['descriptor_identity']):
        raise ValueError('FROZEN_ATTEMPT_CHANGED')
    print('Frozen source, input, historical descriptors and resolved snapshot verified.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['freeze','archive','verify']);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();globals()[args.action](args.output)
