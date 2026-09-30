"""Read completed Route cases (success or failure); never write source ledgers."""
import gzip
import hashlib
import json
import sqlite3
import zipfile
from pathlib import Path
from tools.platform_store import Store, plain
from tools.state_io import digest
from .route import trial_facts
from .delivery_facts import bound_result_facts


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_cases(descriptor,destination):
    source=Path(descriptor['directory']); live=source/descriptor['live_store']
    target=Path(destination)/'source_ledgers'/descriptor['source_session_id']
    target.mkdir(parents=True,exist_ok=True)
    original=live/'platform.sqlite'
    if original.exists():
        # sqlite backup accounts for a possible WAL; query-only source connection.
        with sqlite3.connect(original.resolve().as_uri()+'?mode=ro',uri=True) as src, sqlite3.connect(target/'platform.sqlite') as dst:
            src.execute('PRAGMA query_only=ON'); src.backup(dst)
        ledger=original
    else:
        ledger=source/descriptor['ledger']
        (target/'platform.sqlite').write_bytes(gzip.decompress(ledger.read_bytes()))
    store=Store(target); session=store.session(descriptor['source_session_id'])
    frozen=json.loads((source/descriptor['frozen_input']).read_text(encoding='utf8'))
    if session['snapshot']['input']!=frozen: raise ValueError('SOURCE_SNAPSHOT_MISMATCH')
    selected=set(descriptor.get('candidate_ids',[])); cases=[]
    for node in session['state']['route']['nodes']:
        if node['action']!='run' or node['status']!='completed': continue
        trial=store.artifact(node['result'])
        if selected and trial['candidate_id'] not in selected: continue
        facts=trial_facts(store,frozen,trial)
        result=bound_result_facts(store,trial,facts)
        if not result or not result['valid_complete_execution']: raise ValueError('COMPLETE_EXECUTION_REQUIRED')
        config=store.artifact(facts['configuration'])
        report=store.artifact(result['report']['reference'])['detail']
        owner=facts['owner_run_id']; eid=facts['execution_id']
        metadata=store.session(owner)['state']['result_executions'][eid]
        if metadata['candidate_input']!=facts['configuration']: raise ValueError('EXECUTION_CONFIGURATION_MISMATCH')
        prefix=Path('sessions')/owner/'executions'/eid/'backend'
        arrays={}; hashes={}; locations={}
        for name in ('controller_observations.json','actual_commands.json','nmpc_updates.json'):
            path=live/prefix/name
            if path.exists(): body=path.read_bytes(); location=str(path)
            elif (source/descriptor.get('backend_evidence','backend_evidence.zip')).exists():
                archive=source/descriptor.get('backend_evidence','backend_evidence.zip')
                with zipfile.ZipFile(archive) as z:
                    member=(prefix/name).as_posix()
                    if member not in z.namelist(): continue
                    body=z.read(member); location=str(archive)+'!'+member
            else: continue
            arrays[name]=json.loads(body); hashes[name]=hashlib.sha256(body).hexdigest(); locations[name]=location
        cases.append(dict(binding=dict(candidate_id=facts['candidate_id'],source_session_id=descriptor['source_session_id'],
            owner_run_id=owner,execution_id=eid,run_node=node['node_id'],build_node=node['selection']['source_node'],
            source_directory=str(source),source_commit=session['snapshot'].get('project_commit'),
            configuration=facts['configuration'],effective_configuration_identity=digest(config['effective']),
            task_identity=digest(config['effective']['task']),controller=config['effective']['policy']['controller'],
            model='model.gvs@1.0.0',discretization=config['effective']['policy']['discretization'],
            evaluation=result['evaluation'],simulation=result['simulation'],report=result['report'],
            ledger_sha256=file_hash(ledger),frozen_input_sha256=file_hash(source/descriptor['frozen_input']),
            saved_signal_sha256=hashes,saved_signal_locations=locations),
            effective=config['effective'],factual_result=result,evaluation=store.artifact(result['evaluation']),
            report=report,saved=arrays))
    if selected!={c['binding']['candidate_id'] for c in cases} and selected:
        raise ValueError('EXPLICIT_CASE_COVERAGE_MISMATCH')
    return cases
