"""Exact historical execution/state import; no reverse orchestration imports."""
from copy import deepcopy
import hashlib,gzip,json,tarfile,time
from pathlib import Path
import numpy as np
from tools.research.state import save,update,state
from tools.research.design import full_science
from tools.state_io import read,digest
from tools.platform_store import plain
ROOT=Path(__file__).resolve().parents[2]
HISTORY='evidence/research_chain_20261014'
_verified=set()
_manifests={}
def archived(folder, reference, raw=False):
    folder=ROOT/folder
    manifest=read(folder/'archive_manifest.json')
    path=folder/'immutable_artifacts.tar.gz'
    # Cache verified archive identity, retaining per-member verification.
    identity=(str(path),path.stat().st_mtime_ns,path.stat().st_size)
    if identity not in _verified:
        with path.open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest()!=manifest['archive_sha256']:
                raise ValueError('HISTORICAL_ARCHIVE_HASH_MISMATCH')
        _verified.add(identity)
    member=next(m for m in manifest['members'] if m['sha256']==reference['artifact_id'])
    with tarfile.open(path) as archive:body=archive.extractfile(member['name']).read()
    if hashlib.sha256(body).hexdigest()!=reference['artifact_id']:raise ValueError('HISTORICAL_MEMBER_HASH_MISMATCH')
    return body if raw else json.loads(body)

def execution_source(row, folder=HISTORY):
    result=archived(folder,row['reference'])
    target=result['execution']['receipts']['simulation']['output']
    key=(folder,target['artifact_id'])
    if key not in _manifests:
        with tarfile.open(ROOT/folder/'immutable_artifacts.tar.gz') as archive:
            for member in archive:
                if member.name.endswith('.json') and member.size<200000:
                    body=archive.extractfile(member).read();value=json.loads(body)
                    if isinstance(value,dict) and 'files' in value and isinstance(value.get('result'),dict):
                        if hashlib.sha256(body).hexdigest()!=Path(member.name).stem:raise ValueError('MANIFEST_HASH_MISMATCH')
                        _manifests[(folder,value['result']['artifact_id'])]=value
    manifest=_manifests[key]
    files={r['filename']:r['reference'] for r in manifest['files']}
    return dict(result=result,files=files,folder=folder)

def imported_record(host, configuration, record, provenance, observation=None):
    value=dict(configuration=configuration,record=record,provenance=provenance,
        original_study=provenance['study_id'],imported_historical_evidence=True,
        additional_numerical_s=0.,confirmation_eligible=False,
        complete_original_problem_available=bool(record.get('resolved_problem_archive') or record.get('resolved_problem')),
        observation=observation)
    ref=save(host,value,'imported_historical_diagnostic_input')
    update(host,historical_diagnostic_sources=[*state(host).get('historical_diagnostic_sources',[]),ref])
    return ref

def import_execution(host, folder, reference, update_ids):
    """Read a declared immutable execution; no solver or backend dispatch."""
    s=state(host);source=execution_source(dict(reference=reference),folder)
    result=source['result'];candidate=archived(folder,result['candidate'])
    for ref,value in ((result['candidate'],candidate),(candidate['configuration_reference'],candidate['configuration']),
                      (reference,result)):
        if save(host,value,'imported_archived_execution')!=ref:raise ValueError('ARCHIVED_REFERENCE_IDENTITY_MISMATCH')
    if candidate['scientific_configuration']!=full_science(candidate['configuration']):raise ValueError('ARCHIVED_CANDIDATE_CONFIGURATION_MISMATCH')
    state_path=ROOT/folder/'state.json'
    historical_state=read(state_path) if state_path.exists() else json.loads(gzip.decompress(state_path.with_suffix('.json.gz').read_bytes()))
    profile=historical_state['profile']
    if digest({k:v for k,v in profile.items() if k!='identity'})!=profile['identity']:raise ValueError('ARCHIVED_PROFILE_IDENTITY_MISMATCH')
    if candidate['profile_identity']!=profile['identity']:raise ValueError('ARCHIVED_CANDIDATE_PROFILE_MISMATCH')
    candidates=dict(s['candidates']);candidates[candidate['identity']]=result['candidate']
    update(host,candidates=candidates,imported_candidates=list({r['artifact_id']:r for r in
        [*s.get('imported_candidates',[]),result['candidate']]}.values()),imported_candidate_profile=profile,
        scoped_context=[*s.get('scoped_context',[]),reference],
        historical_confirmations=[*s.get('historical_confirmations',[]),*([reference] if result.get('role')=='confirmation' else [])])
    observations=archived(folder,source['files']['controller_observations.json'])
    motion_ref=(result.get('profile') or {}).get('motion')
    motion=archived(folder,motion_ref) if motion_ref else []
    if motion_ref:save(host,motion,'imported_backend_motion')
    refs=[]
    for update_id in update_ids:
        observation=next(r for i,r in enumerate(observations) if r.get('complete_update_record',{}).get('update_id',i)==update_id)
        observation=deepcopy(observation)
        measured=next((r for r in motion if abs(r['time_s']-observation['time_s'])<=1e-12),{})
        observation.update({k:measured[k] for k in ('tip_velocity_m_s','tip_speed_m_s') if k in measured})
        record=deepcopy(observation.get('complete_update_record'))
        if not record:raise ValueError('ACTUAL_COMPLETE_UPDATE_INPUT_REQUIRED')
        definition=record.get('resolved_problem_reference')
        if definition:
            problem_ref=source['files'][definition['filename']];problem=archived(folder,problem_ref)
            if problem_ref['artifact_id']!=definition['sha256'] or digest(problem['objective_function'])!=record['model_identity']:
                raise ValueError('ARCHIVED_RESOLVED_PROBLEM_IDENTITY_MISMATCH')
            record['resolved_problem_archive']=dict(folder=folder,reference=problem_ref)
        refs.append(imported_record(host,candidate['configuration'],record,
            dict(study_id=result['owning_study'],folder=folder,execution_reference=reference,
                execution_id=result['execution_id'],candidate=result['candidate'],update_id=update_id),observation))
    return dict(execution=reference,candidate=result['candidate'],updates=refs,additional_numerical_s=0.)

def execution_update(host, reference, update_id):
    """Shared exact-state/problem lookup for analysis and local diagnostics."""
    reference=plain(reference);s=state(host)
    for ref in s.get('historical_diagnostic_sources',[]):
        source=host.store.artifact(ref)
        if reference==ref or reference==source['provenance'].get('execution_reference'):
            if source['record']['update_id']==update_id:return source
    if reference not in s['results']:raise ValueError('OWNED_EXECUTION_AND_RECORDED_UPDATE_REQUIRED')
    from extensions.tendon_family.control_evidence import ControlEvidence
    result=host.store.artifact(reference);reader=ControlEvidence(host.store);source=reader.resolve(result['execution_id'])
    observation=reader.read_file(source,'controller_observations.json',[])[update_id]
    motion=host.store.artifact(result['profile']['motion']) if result.get('profile',{}).get('motion') else []
    measured=next((r for r in motion if abs(r['time_s']-observation['time_s'])<=1e-12),{})
    observation.update({k:measured[k] for k in ('tip_velocity_m_s','tip_speed_m_s') if k in measured})
    record=deepcopy(observation.get('complete_update_record'))
    if not record:raise ValueError('ACTUAL_COMPLETE_UPDATE_INPUT_REQUIRED')
    definition=record.get('resolved_problem_reference')
    if definition:
        body=host.store.artifact(source['files'][definition['filename']],raw=True)
        if hashlib.sha256(body).hexdigest()!=definition['sha256']:raise ValueError('RESOLVED_PROBLEM_DEFINITION_HASH_MISMATCH')
        record['resolved_problem']=json.loads(body)
        if digest(record['resolved_problem']['objective_function'])!=record['model_identity']:raise ValueError('RESOLVED_PROBLEM_EXPRESSION_IDENTITY_MISMATCH')
    return dict(configuration=host.store.artifact(result['candidate'])['configuration'],record=record,observation=observation,
        imported_historical_evidence=False,provenance=dict(candidate=result['candidate'],execution_reference=reference,
            execution_id=result['execution_id'],study_id=host.run_id,update_id=update_id))

