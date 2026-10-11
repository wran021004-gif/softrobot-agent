"""Closeout from saved current-study evidence, without additional experiments."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time
import importlib.metadata
import platform
import tarfile
import gzip
import io
import os
from tools import research_core as core
from tools.platform_host import Host
from extensions.tendon_family.control_evidence import ControlEvidence


def deliver(host):
    s=core.state(host)
    if s['research_status']!='stopped' or s['pending']:raise ValueError('SEALED_STUDY_AND_KNOWN_OUTCOMES_REQUIRED')
    out=core.ROOT/s['spec']['evidence_destination'];out.mkdir(parents=True,exist_ok=True)
    reader=ControlEvidence(host.store);rows=[];counts=Counter();verified_definitions=set()
    for ref in s['results']:
        r=host.store.artifact(ref); c=host.store.artifact(r['candidate']);obs=[]
        if r['status']=='evaluated':
            source=reader.resolve(r['execution_id']);obs=reader.read_file(source,'controller_observations.json',[])
            for observation in obs:
                record=observation.get('complete_update_record',{});definition=record.get('resolved_problem_reference')
                if definition:
                    file_ref=source['files'][definition['filename']]
                    if file_ref['artifact_id']!=definition['sha256']:raise ValueError('COMPLETE_PROBLEM_LINK_HASH_MISMATCH')
                    pair=(definition['sha256'],record['model_identity'])
                    if pair not in verified_definitions:
                        problem=json.loads(host.store.artifact(file_ref,raw=True))
                        if core.digest(problem['objective_function'])!=record['model_identity']:raise ValueError('COMPLETE_PROBLEM_EXPRESSION_HASH_MISMATCH')
                        verified_definitions.add(pair)
                    counts['resolved_problem_links_verified']+=1
        counts['controller_update_attempts']+=len(obs)
        counts['complete_input_records']+=sum('complete_update_record' in o or 'failed_update_input_record' in o for o in obs)
        counts['complete_resolved_problems']+=sum(bool({'resolved_problem','resolved_problem_reference'} & o.get('complete_update_record',{}).keys()) for o in obs)
        rows.append(dict(reference=ref,parameters=c['parameters'],**core.compact_result(r),operation_key=r['operation_key']))
    for partial in s.get('incomplete_execution_evidence',[]):
        saved=max(partial.get('counts',{}).values(),key=lambda v:v['updates'],default={})
        counts['controller_update_attempts']+=partial.get('computed_updates_before_failure',saved.get('updates',0))
        counts['complete_input_records']+=saved.get('complete_records',0)
        counts['complete_resolved_problems']+=saved.get('complete_records',0)
        counts['missing_complete_input_records']+=partial.get('complete_record_gap',0)
        counts['computed_but_unapplied_updates']+=1
    mechanics=[]
    for ref in s['mechanics_results']:
        v=host.store.artifact(ref)
        mechanics.append(dict(reference=ref,**{k:v.get(k) for k in ('operation','status','execution_id','owning_study',
            'termination_reason','trajectory_reference','checkpoint_reference','variable_order','objective_definition',
            'trajectory_metrics','hard_max_normalized_violation','relaxed_nlp_feasible','original_task_feasible',
            'original_task_gaps','slack_values','costs_s','charged_numerical_s','replay','physical_validation')},
            returned_structure={k:v['candidate'].get(k) for k in ('d','lengths_m','substeps')} if v.get('candidate') else None))
    plans=[dict(reference=r,**host.store.artifact(r)) for r in s['plans']]
    for row in rows:
        row['origin']=next((p['origin'] for p in plans if row['operation_key']==p['request_id'] or
            row['operation_key'].startswith(p['request_id']+':mixed-')),'unknown')
    searches=[]
    for key,v in s['searches'].items():
        evaluated=v.get('evaluated',[])
        actual=[dict(d=(r['resolved']['parameters']['lengths_m'][0]-.16)/.0055,
            **{k:r['resolved']['parameters'][k] for k in ('holding_tip_speed_weight','terminal_tip_speed_weight')}) for r in evaluated]
        requested=next((p['original_plan']['search'] for p in plans if p['request_id']==key),None)
        searches.append(dict(operation_key=key,requested=requested,actual_parameters=actual,
            distinct_configurations=len({r['scientific_identity'] for r in evaluated}),
            execution_references=[r['evidence']['result'] for r in evaluated],termination=v['termination'],
            construction_rejections=v['rejections'],partial_batch=v['pending'] is not None or bool(v.get('known_failed_pending_proposal'))))
    native=[p for p in plans if p['origin']=='model']
    status=host.store.remaining()
    counts.update(provider_requests=s['pilot']['live_model_requests'],public_operations=status['used']['tool_calls'],
        physical_launches=status['used']['backend_solves'],offline_nlp=s['offline_nlp'],bdf_replays=s['bdf_replays'],local_solves=s['local_solves'])
    elapsed=time.time()-s['started_unix'];remaining_engineering=max(0.,elapsed-status['used']['wall_s'])
    row,fresh=host.store.reserve(host.run_id,'engineering-delivery',core.digest({'study':host.run_id}),host.actor,
        {**core.zero(),'wall_s':remaining_engineering},kind='engineering')
    if fresh:
        host.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=host.actor,
            tool_id='engineering.mechanics_delivery',tool_version='1.0.0',execution_status='completed',charged=core.zero()),
            dict(activity_elapsed_s=elapsed,engineering_and_idle_s=remaining_engineering),elapsed=remaining_engineering)
        core.update(host,completed_unix=time.time())
    integration=host.store.artifact(s['integration_demonstration']) if s.get('integration_demonstration') else {}
    evaluated=[r for r in rows if r['status']=='evaluated']
    observed_pairs=[]
    for i,left in enumerate(evaluated):
        for right in evaluated[i+1:]:
            if left['profile_identity']==right['profile_identity'] and left['parameters']['d']==right['parameters']['d']:
                def rank(row):
                    m=row['acceptance']['metrics'];ratios=[m['terminal_error_m']/.01,m['holding_max_error_m']/.01,m['holding_max_speed_m_s']/.02]
                    return [0 if row['acceptance']['accepted'] else 1,max(ratios),sum(ratios)]
                observed_pairs.append(dict(executions=[left['reference'],right['reference']],fixed_structure=True,
                    fixed_task_ranks=[rank(left),rank(right)],later_rank_improved=rank(right)<rank(left),
                    repeated_or_causal_claim=False))
    runtime=dict(python=platform.python_version(),packages={p:importlib.metadata.version(p) for p in
        ('numpy','scipy','casadi','mujoco','strands-agents','strands-harness')},
        lock_sha256=hashlib.sha256((core.ROOT/'requirements-strands-mainline5.lock').read_bytes()).hexdigest())
    configuration=core.read(host.store.root/'framework_configuration.json')
    core.atomic_json(out/'framework_configuration.json',configuration)
    receptions=[dict(request_id=e['request_id'],**host.store.artifact(e['outputs'][0])) for e in
        host.store.events(host.run_id) if e['kind']=='r3_response' and e['status']=='metadata_saved']
    provider_totals={}
    for field in ('prompt_tokens','completion_tokens','total_tokens'):
        values=[(r.get('usage') or {}).get(field) for r in receptions]
        provider_totals[field]=sum(values) if values and all(isinstance(v,int) for v in values) else None
    scientific_costs=dict(offline_and_bdf_s=sum(m['charged_numerical_s'] for m in mechanics),
        physical_including_failed_starts_s=sum(r['numerical_s'] for r in rows),
        standalone_local_s=s['local_solve_s'],provider_response_s=sum(r['elapsed_s'] for r in receptions),
        provider_usage=provider_totals,money=None,money_status='not supplied; no pricing estimate')
    authorization_ref=core.save(host,dict(text=(core.ROOT/'examples/mechanics_control/authorization.txt').read_text(encoding='utf8'),
        source='user attachment 0cef2049-7e4f-4f7e-8a95-367ca8e64560/pasted-text-1.txt'),'delivery_authorization_original')
    fixture_ref=core.save(host,core.read(out/'verification.json'),'delivery_focused_verification')
    configuration_ref=core.save(host,configuration,'delivery_native_configuration')
    summary=dict(schema='mechanics_control_delivery_v1',study_id=host.run_id,base_commit=s['spec']['base_commit'],
        authorization_reference=authorization_ref,focused_verification_reference=fixture_ref,native_configuration_reference=configuration_ref,
        authorization_sha256=hashlib.sha256((core.ROOT/'examples/mechanics_control/authorization.txt').read_bytes()).hexdigest(),
        delivery_tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        runtime=runtime,profile_history=s['profile_history'],observed_fixed_structure_comparisons=observed_pairs,
        measured_costs=scientific_costs,provider_responses=receptions,
        implementation_freeze=s['freeze'],source_versions=s['profile']['science_hashes'],core_versions=s['core_hashes'],
        evaluation_version=s['profile']['version'],status=s['research_status'],counts=dict(counts),
        outcomes=dict(engineering_interfaces_connected=True,
            mechanics_to_closed_loop_handoff=integration.get('status')=='connected',
            actual_control_weight_search=any(v['distinct_configurations']>=2 and v['requested'] and 'd' not in v['requested']['variables'] and
                any(len({p[w] for p in v['actual_parameters']})>=2 for w in ('holding_tip_speed_weight','terminal_tip_speed_weight')) for v in searches),
            native_feedback_consumed_and_legal_decision=bool(native),
            autonomous_research_actions=[p['original_plan']['action'] for p in native],
            native_stop=bool(native and native[-1]['original_plan']['action']=='stop'),
            task_metric_improvement_observed=any(p['later_rank_improved'] for p in observed_pairs),
            structural_superiority_attribution=False,
            improvement_and_confirmation=core.claims(host)),
        mechanics=mechanics,closed_loop=rows,searches=searches,handoffs=s['handoffs'],
        engineering_demonstration=s.get('integration_demonstration'),original_plans=plans,
        diagnostics=[dict(reference=r,**host.store.artifact(r)) for r in s.get('diagnostics',[])],
        imported_diagnostic_sources=s.get('historical_diagnostic_sources',[]),
        diagnostic_inspection_repairs=s.get('diagnostic_inspection_repairs',[]),
        incomplete_execution_evidence=s.get('incomplete_execution_evidence',[]),
        experience_retrievals=s['retrievals'],experience_dispositions=[dict(plan=p['reference'],values=p['original_plan']['experience_disposition'])
            for p in plans if p['original_plan']['experience_disposition']],
        cumulative_resources=core.packet(host)['resource_use'],activity_elapsed_s=elapsed,
        mechanics_resources=core.packet(host)['mechanics_resource_use'],core_repairs=s.get('core_repairs',[]),
        limitations=['One frozen task and seed, ideal tensions, sampled holding acceptance only.',
            'BDF checks independent model integration, not physical validation.',
            'Structure observations lack matched control-adaptation campaigns; no structural superiority claim.',
            'Fresh diagnostics do not recreate historical cache/timing; no unique causal attribution.',
            'Two known failed physical starts are charged; one computed update input was lost before persistence.',
            'Optional offline NMPC trajectory initialization and legacy skill admission deferred.'])
    core.atomic_json(out/'scientific_summary.json',summary)
    core.atomic_json(out/'specification.json',s['spec'])
    # Archive state once; keep the visible index compact.
    ref=core.save(host,core.state(host),'final_state_archive')
    core.export(host,out)
    core.atomic_json(out/'state.json',dict(reference=ref,study_id=host.run_id,status='stopped',results=s['results'],mechanics_results=s['mechanics_results']))
    # Verify the exported bytes and original partial files, without printing secrets.
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path.home()/'.codex'/'.env');secret=os.environ['DEEPSEEK_API_KEY'].encode()
    def inspect_stream(stream):
        digest=hashlib.sha256();tail=b'';found=False
        while block:=stream.read(1024*1024):
            digest.update(block);found=found or secret in tail+block;tail=block[-max(1,len(secret)-1):]
        return digest.hexdigest(),found
    manifest=core.read(out/'archive_manifest.json');expected={m['name']:m['sha256'] for m in manifest['members']}
    verified=0;secret_found=False
    with tarfile.open(out/'immutable_artifacts.tar.gz','r:gz') as archive:
        for member in archive:
            with archive.extractfile(member) as stream:checksum,found=inspect_stream(stream)
            if checksum!=expected.pop(member.name):raise ValueError('DELIVERY_MEMBER_HASH_MISMATCH')
            secret_found=secret_found or found;verified+=1
    if expected:raise ValueError('DELIVERY_ARCHIVE_MISSING_MEMBERS')
    partial_verified=0
    for partial in s.get('incomplete_execution_evidence',[]):
        for file in partial['files']:
            raw=host.store.artifact(file['reference'],raw=True)
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:checksum,found=inspect_stream(stream)
            if checksum!=file['raw_sha256']:raise ValueError('PARTIAL_EVIDENCE_RAW_HASH_MISMATCH')
            secret_found=secret_found or found;partial_verified+=1
    for file in out.iterdir():
        if file.is_file() and file.suffix in ('.json','.md'):
            with file.open('rb') as stream:_,found=inspect_stream(stream)
            secret_found=secret_found or found
    if secret_found:raise ValueError('DELIVERY_SECRET_FOUND')
    physical_ids=[r['execution_id'] for r in rows]
    if len(set(physical_ids))!=len(physical_ids):raise ValueError('FRESH_EXECUTION_ID_COLLISION')
    archive_checksum=hashlib.sha256((out/'immutable_artifacts.tar.gz').read_bytes()).hexdigest()
    if archive_checksum!=manifest['archive_sha256']:raise ValueError('DELIVERY_ARCHIVE_HASH_MISMATCH')
    ceilings=s['spec']['budgets']
    for resource,limit in [('provider_requests','provider_requests'),('public_operations','public_operations'),
        ('physical_launches','physical_launches'),('offline_nlp','offline_nlp'),('bdf_replays','bdf_replays'),('local_solves','local_solves')]:
        if counts[resource]>ceilings[limit]:raise ValueError('DELIVERY_COUNTER_EXCEEDS_CEILING')
    if s['numerical_s']>ceilings['numerical_s'] or s['local_solve_s']>ceilings['local_solve_s'] or elapsed>ceilings['activity_s']:
        raise ValueError('DELIVERY_TIME_EXCEEDS_CEILING')
    events=host.store.events(host.run_id);stop_seen=False;requests_after_stop=0
    for event in events:
        if event['kind']=='model_original_tool_feedback':
            feedback=host.store.artifact(event['outputs'][0])
            if feedback['tool_use']['input'].get('action')=='stop' and feedback['result']['status']=='success':stop_seen=True
        if stop_seen and event['kind']=='r3_request':requests_after_stop+=1
    if not stop_seen or requests_after_stop:raise ValueError('ACCEPTED_STOP_OR_PROVIDER_SEAL_MISSING')
    with host.store.connect(True) as db:
        unsealed=sum(not r['receipt'] for r in db.execute('SELECT receipt FROM calls'))
    if unsealed or s['numerical_reserved_s']:raise ValueError('DELIVERY_UNKNOWN_OUTCOME')
    core.atomic_json(out/'delivery_integrity.json',dict(archive_members_verified=verified,
        original_partial_files_verified=partial_verified,configured_secret_found=False,
        archive_sha256=manifest['archive_sha256'],archive_bytes=(out/'immutable_artifacts.tar.gz').stat().st_size,
        unique_physical_execution_ids=len(physical_ids),unsealed_calls=unsealed,pending=None,
        budget_ceilings_respected=True,provider_requests_after_accepted_stop=requests_after_stop,
        counts=dict(counts),verification='Saved evidence inspection only; no new model requests or numerical solves'))
    report=['# Mechanics and control delivery, 2026-10-11','',
        'The current research core connects offline CasADi/GVS mechanics, retained trajectory evidence, candidate handoff, fixed-structure coordinate search, complete closed-loop records and native feedback decisions. Immutable configuration, fresh execution, historical evidence and cached receipt costs are explicit.','',
        f"Engineering demonstration: `{integration.get('status','incomplete')}`. Native actions: {', '.join(p['original_plan']['action'] for p in native) or 'none'}. These activities are recorded separately.",'',
        '| Execution / origin / role | d | Holding weight | Terminal weight | Holding position mm | Holding speed m/s | Joint acceptance |',
        '|---|---:|---:|---:|---:|---:|---|']
    for r in rows:
        p=r['parameters'];a=r['acceptance'] or {};m=a.get('metrics',{})
        position=f"{m['holding_max_error_m']*1000:.6f}" if 'holding_max_error_m' in m else 'unavailable'
        speed=f"{m['holding_max_speed_m_s']:.6f}" if 'holding_max_speed_m_s' in m else 'unavailable'
        report.append(f"| {r['execution_id'][:12]} / {r['origin']} / {r['role']} | {p['d']:.6g} | {p['holding_tip_speed_weight']:.6g} | {p['terminal_tip_speed_weight']:.6g} | {position} | {speed} | {a.get('status',r['status'])} |")
    report+=['']
    for m in mechanics:
        report.append(f"Mechanics {m['operation']}: `{m['status']}`, charged {m['charged_numerical_s']:.3f}s; original-task feasible={m['original_task_feasible']}, relaxed feasible={m['relaxed_nlp_feasible']}. Returned structure: {m['returned_structure']}. Replay gates and raw/retained selections are preserved in the archive.")
    c=core.claims(host);rs=core.packet(host)['resource_use']
    report+=['',f"Independent post-selection confirmations: {c['independent_confirmation_count']}; failures: {c['confirmation_failures']}; limited repeat-supported acceptance: {c['limited_repeat_supported_acceptance']}. Improvement attribution permitted: {c['parameter_improvement_attribution_permitted']}.",'',
        f"Costs: numerical {rs['numerical_s']:.3f}/10800s; standalone local solves {s['local_solves']}/4, {s['local_solve_s']:.3f}/600s; offline attempts {s['offline_nlp']}/2; BDF replays {s['bdf_replays']}/2; MuJoCo launches {counts['physical_launches']}/8; provider requests {counts['provider_requests']}/32; public operations {counts['public_operations']}/128. Activity elapsed {elapsed/3600:.3f}h/12h including engineering. Internal NMPC recovery is included once.",'',
        f"Measured numerical components: offline and BDF {scientific_costs['offline_and_bdf_s']:.3f}s; physical runs including failed starts {scientific_costs['physical_including_failed_starts_s']:.3f}s; standalone local diagnosis {scientific_costs['standalone_local_s']:.3f}s. Provider response time {scientific_costs['provider_response_s']:.3f}s, usage {provider_totals}; monetary cost is unknown. Actual read-only experience retrievals: {len(s['retrievals'])} (supplied startup history and native context reads are separate).",'',
        f"New controller attempts: {counts['controller_update_attempts']}; complete input records: {counts['complete_input_records']}; resolved serialized problems: {counts['complete_resolved_problems']}; missing complete inputs: {counts['missing_complete_input_records']}. The two failed starts each computed a final command before control assignment; neither has terminal/holding acceptance. All updates of completed runs are saved. Earlier replaced progress and final temporary progress are archived as exact compressed bytes.",'',
        'Offline optimization passed its original sampled task (5.200 mm, 0.019525 m/s), but independent BDF replay failed holding speed (0.065883 m/s). The mechanics structure entered goal-based NMPC as exploratory evidence. BDF is model integration, not physical validation.','',
        'At the engineering-selected fixed structure, lowering holding weight from 0.10 to 0.08125 improved the observed fixed task ranking: holding speed 0.042033 to 0.026947 m/s and position 3.961 to 3.861 mm. Both failed joint acceptance. These are single executions without independent confirmation and cannot establish a causal or stable improvement. Weighted NMPC objectives are not used for this comparison.','',
        'Repeatability: two new local solves preserved original tracing off, matched serialized mathematical identity, ordering, initialized objective and selected constraint values, and agreed with each other. They differed from the original first action by up to 0.666004 N (9 versus 8 selected iterations). Original cached workspace/tail state and timing history were not recreated; the unique mechanism remains unresolved. An inspection-only sorted-JSON vector-order bug was corrected from existing solver checks without another solve; original reports remain archived.','',
        'No structural superiority, stable robustness, autonomous discovery or unique causal diagnosis is claimed. BDF is not physical validation. Optional offline trajectory initialization and legacy skill admission remain unfinished.','',
        '[Runbook](mechanics_control_runbook.md), [scientific summary](../evidence/mechanics_control_20261011/scientific_summary.json), [focused checks](../evidence/mechanics_control_20261011/verification.json), [archive manifest](../evidence/mechanics_control_20261011/archive_manifest.json).']
    (core.ROOT/'docs/mechanics_control_completion.md').write_text('\n'.join(report)+'\n',encoding='utf8')
    return dict(report='docs/mechanics_control_completion.md',counts=dict(counts),outcomes=summary['outcomes'],resources=rs)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--spec',type=Path,required=True);args=parser.parse_args()
    spec=core.read(args.spec);h=Host(core.ROOT/'runs'/spec['study_id'],spec['study_id'],actor='unified-research')
    print(json.dumps(deliver(h)))


if __name__=='__main__':main()
