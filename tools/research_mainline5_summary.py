"""Factual export only. No provider request or scientific execution."""
from pathlib import Path
import argparse
import hashlib
import json
import tarfile
import time
from tools import research_mainline5_services as s
from tools.research_mainline4_summary import summarize as business_summary
from tools.state_io import atomic_json,read


def summarize(w):
    result=business_summary(w)
    result['entry']=w.spec.get('selected_template')
    result['search_sources']=[]
    for row in w.rounds:
        plan=row['decision']['decision'].get('plan')
        if not plan:continue
        source=next(r for r in w.records if r['facts']['candidate']==plan['source_candidate'])
        cfg=w.store.artifact(plan['source_candidate']['configuration'])['effective']
        recipe=cfg['policy']['controller']['parameters']['data']['recipe']
        result['search_sources'].append(dict(decision=row['accepted_decision'],source=plan['source_candidate'],
            source_store=source['source_store'],controller=cfg['policy']['controller']['version'],
            metrics=source['acceptance']['metrics'],acceptance=source['acceptance']['status'],
            actual_weights={k:recipe[k] for k in ('holding_tip_speed_weight','terminal_tip_speed_weight')},
            comparison_scope='Identified recorded source; component observations are not statistical or global improvement claims.'))
    from tools.parameter_catalog import effective_catalog
    from tools.candidate_parameters import parameter_value
    for outcome in result['outcomes']:
        cfg=w.store.artifact(outcome['candidate']['configuration'])['effective']
        outcome['applied_structural_values']={p:parameter_value(cfg,p)
            for p in effective_catalog(cfg)['usable_pool'] if not p.startswith('control/')}
        outcome['actual_segment_physics']={c['id']:c['physics']
            for c in cfg['robot']['structure']['data']['components'] if c['kind']=='flexible_segment'}
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
    resources['native_errors']=[dict(reference=e['outputs'][0],
        tool=w.store.artifact(e['outputs'][0])['tool_use']['name'])
        for e in events if e['kind']=='mainline5_native_result'
        and w.store.artifact(e['outputs'][0])['result'].get('status')=='error']
    resources['public_mathematical_attempts']=sum(r['tool_use']['name'].startswith('analysis_') for r in native)
    resources['public_mathematical_and_search_operations']=resources['public_mathematical_attempts']+resources['search_method_invocations']
    reconciled=[w.store.artifact(e['outputs'][0]) for e in events
        if e['kind']=='mainline5_transport_reconciliation']
    resources['confirmed_presend_local_failures']=reconciled
    resources['confirmed_provider_responses']=len(provider)
    resources['actual_provider_sends']=resources['provider_requests']-sum(
        r.get('actual_provider_send') is False for r in reconciled)
    resources['request_count_note']='Conservative charged request slots retain confirmed pre-send failures; every actual send remains charged.'
    math_ids={ref['artifact_id'] for r in w.records for ref in r.get('mathematical_references',{}).values()}
    for event in events:
        if event['kind']!='mainline5_native_result':continue
        saved=w.store.artifact(event['outputs'][0])
        if not saved['tool_use']['name'].startswith('analysis_'):continue
        for block in saved['result'].get('content',[]):
            if not block.get('text','').startswith('{'):continue
            content=json.loads(block['text']);receipt=content.get('receipt') or {}
            if receipt.get('output'):math_ids.add(receipt['output']['artifact_id'])
    grounded_math=[]
    for row in w.rounds:
        selectors=[v for v in row['decision']['evidence_selectors'] if v['reference']['artifact_id'] in math_ids]
        if selectors:grounded_math.append(dict(decision=row['accepted_decision'],selectors=selectors))
    result['mathematical_lexical_mentions']=[dict(decision=m['decision'],
        note='Keyword heuristic only; original text is retrieved through the referenced immutable decision.')
        for m in result['mathematical_decision_evidence']]
    result['mathematical_decision_evidence']=grounded_math
    result['dimensions']['mathematical_evidence_used_in_decisions']=bool(grounded_math)
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
    result['principal_final_selected_candidate']=(result['final_model_decision'] or {}).get('selected_candidate')
    result['verification_nominated_candidate']=w.verification[0]['source'] if w.verification else None
    result['limitations'][1]='Only historical V1 T0 executed controller9; Mainline4 contemporary T0 and all new T2 runs used controller10.'
    review=s.OUT/'material_review.json'
    if review.exists():
        result['material_review']=read(review)
        result['dimensions'].update(result['material_review'].get('reviewed_dimensions',{}))
    return result


def export(w):
    s.export(w)
    result=summarize(w);atomic_json(s.OUT/'result_summary.json',result)
    # Preserve bulky exact bytes once in the established lossless archive style.
    targets=[(s.OUT/'store/artifacts','store/artifacts'),(s.OUT/'executions','executions'),
        (w.directory/'framework_sessions','framework_sessions')]
    archive=s.OUT/'immutable_artifacts.tar.gz';temporary=s.OUT/'immutable_artifacts.tmp.tar.gz'
    members=[];metadata=[]
    metadata_paths=[s.OUT/name for name in ('sessions.json','study_state.json',
        'implementation_freeze.json','material_binding_repair_freeze.json')]
    with tarfile.open(temporary,'w:gz') as tf:
        for folder,prefix in targets:
            if not folder.exists():continue
            for path in sorted(folder.rglob('*')):
                if not path.is_file():continue
                name=prefix+'/'+path.relative_to(folder).as_posix()
                tf.add(path,arcname=name,recursive=False)
                members.append(dict(path=name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size))
        for path in metadata_paths:
            if not path.exists():continue
            name='metadata/'+path.name;tf.add(path,arcname=name,recursive=False)
            row=dict(path=name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
            members.append(row);metadata.append(row)
    if archive.exists() and hashlib.sha256(archive.read_bytes()).digest()==hashlib.sha256(temporary.read_bytes()).digest():
        temporary.unlink()
    else:temporary.replace(archive)
    # Original bytes remain in the authoritative Store/backend directories.
    # The delivery retains only one lossless archive, without expanded copies.
    for folder,prefix in targets[:2]:
        if not folder.exists():continue
        assert folder.resolve().is_relative_to(s.OUT.resolve())
        for path in folder.rglob('*'):
            if path.is_file():path.unlink()
        for path in sorted(folder.rglob('*'),reverse=True):
            if path.is_dir():path.rmdir()
        folder.rmdir()
    for path in metadata_paths:
        assert path.resolve().parent==s.OUT.resolve()
        if path.exists():path.unlink()
    atomic_json(s.OUT/'metadata_archive_index.json',dict(archive=archive.name,members=metadata,
        note='Exact full state, sessions and frozen schemas are preserved here instead of large expanded copies. Original local recovery files remain unchanged.'))
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
