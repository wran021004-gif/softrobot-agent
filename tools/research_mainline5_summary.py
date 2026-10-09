"""Factual export only. No provider request or scientific execution."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import tarfile
import time
from tools import research_mainline5_services as s
from tools.research_mainline4_summary import summarize as business_summary
from tools.state_io import atomic_json,read


def summarize(w):
    result=business_summary(w)
    result['entry']=w.spec.get('selected_template')
    responses={}
    for event in w.store.events(w.host.run_id):
        if event['kind']=='r3_response':
            responses[event['request_id']]=dict(request_id=event['request_id'],
                metadata=event['outputs'][0],**w.store.artifact(event['outputs'][0]))
    provider=list(responses.values())
    resources=result['resources']
    resources['responses']=provider
    resources['provider_reported_tokens']={k:sum((r['usage'] or {}).get(k,0) for r in provider)
        for k in ('prompt_tokens','completion_tokens','total_tokens')}
    resources['provider_reported_tokens']['reasoning_tokens']=sum(r.get('reasoning_tokens') or 0 for r in provider)
    events=w.store.events(w.host.run_id)
    native=[w.store.artifact(e['outputs'][0]) for e in events if e['kind']=='mainline5_native_dispatch']
    resources['native_public_dispatches']=len(native)
    resources['public_mathematical_attempts']=sum(r['tool_use']['name'].startswith('analysis_') for r in native)
    resources['public_mathematical_and_search_operations']=resources['public_mathematical_attempts']+resources['search_method_invocations']
    direct=[r for r in result['outcomes'] if r['applied_values']==dict(holding_tip_speed_weight=.0375,terminal_tip_speed_weight=.1)]
    result['transfer_reporting']=dict(direct_parameter_transfer_tested=bool(direct),exact_pair=[.0375,.1],
        direct_parameter_transfer_outcomes=direct,
        direct_parameter_transfer_joint_acceptance_observed=any(r['acceptance']['accepted'] for r in direct),
        direct_parameter_transfer_fresh_confirmation_accepted=any(v['acceptance']['accepted'] and
            any(v['source']==r['candidate'] for r in direct) for v in w.verification),
        historical_experience_or_method_reuse=dict(history_links=w.spec['history_links'],
            model_decisions=result['original_model_decisions'],
            actual_methods=[r['method'] for r in result['searches']]),
        rule='Only exact 0.0375/0.1 executions test direct transfer; a new search is experience/method reuse. Untested direct transfer is not validated.')
    result['integration']=dict(runtime='accepted create_harness; Strands automatic context and session restoration',
        tool_executor='SequentialToolExecutor',store_authority='one new cumulative Mainline5 Store',
        retired_entry_calls=['research_mainline4.live','research_mainline4.decision','Host.run',
            'platform_models.run_loop','platform_models.input_for','platform_models.payload_for',
            'legacy conversation history/compression/engineering recovery scheduling'],
        scientific_implementation='existing controller10, family2, mathematical and deterministic executor services')
    result['bounded_first_study_only']=True
    result['mainline5_overall_complete']=False
    review=s.OUT/'material_review.json'
    if review.exists():result['material_review']=read(review)
    return result


def export(w):
    s.export(w)
    result=summarize(w);atomic_json(s.OUT/'result_summary.json',result)
    # Preserve bulky exact bytes once in the established lossless archive style.
    targets=[(s.OUT/'store/artifacts','store/artifacts'),(s.OUT/'executions','executions'),
        (w.directory/'framework_sessions','framework_sessions')]
    archive=s.OUT/'immutable_artifacts.tar.gz';temporary=s.OUT/'immutable_artifacts.tmp.tar.gz'
    members=[]
    with tarfile.open(temporary,'w:gz') as tf:
        for folder,prefix in targets:
            if not folder.exists():continue
            for path in sorted(folder.rglob('*')):
                if not path.is_file():continue
                name=prefix+'/'+path.relative_to(folder).as_posix()
                tf.add(path,arcname=name,recursive=False)
                members.append(dict(path=name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size))
    if archive.exists() and hashlib.sha256(archive.read_bytes()).digest()==hashlib.sha256(temporary.read_bytes()).digest():
        temporary.unlink()
    else:temporary.replace(archive)
    # Expanded generated export files live in ignored runs; delivery has one copy.
    for folder,prefix in targets[:2]:
        if not folder.exists():continue
        expanded=w.directory/'delivery_expanded'/prefix
        expanded.parent.mkdir(parents=True,exist_ok=True)
        for path in folder.rglob('*'):
            if path.is_file():
                target=expanded/path.relative_to(folder);target.parent.mkdir(parents=True,exist_ok=True)
                if not target.exists() or target.read_bytes()!=path.read_bytes():shutil.copyfile(path,target)
                path.unlink()
        for path in sorted(folder.rglob('*'),reverse=True):
            if path.is_dir():path.rmdir()
        folder.rmdir()
    atomic_json(s.OUT/'archive_manifest.json',dict(archive=archive.name,members=members,
        sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),lossless=True,
        historical_artifacts='Original commit/identity/owner links in store_manifest.json; historical Stores were not copied.'))
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,default=s.RUN);args=p.parse_args()
    result=export(s.restore(args.directory))
    print(json.dumps(dict(status=result['status'],entry=result['entry'],outcomes=result['outcomes'],
        resources={k:v for k,v in result['resources'].items() if k in ('provider_requests','overall_backend_attempts',
        'provider_reported_tokens','development_backend_attempts','verification_backend_attempts')})))


if __name__=='__main__':main()
