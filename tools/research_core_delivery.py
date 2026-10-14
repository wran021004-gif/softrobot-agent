"""Post-STOP reporting from saved evidence only; no model or numerical reruns."""
from collections import Counter
import argparse
import hashlib
from pathlib import Path
import json
import tarfile
import time
from tools.research import core as core
from extensions.tendon_family.control_evidence import ControlEvidence


def read_saved_json(path):
    raw=path.read_bytes()
    return json.loads(raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'))


def deliver(host):
    s=core.state(host)
    if s['pending']: raise ValueError('RECOVER_PENDING_OUTPUT_BEFORE_REPORTING')
    if s['research_status']!='stopped': raise ValueError('ACCEPTED_STOP_REQUIRED_FOR_DELIVERY')
    elapsed=time.time()-s['started_unix']
    engineering=max(0.,elapsed-host.store.remaining()['used']['wall_s'])
    closeout_key='engineering-closeout-'+str(s.get('completed_unix',s['started_unix']))
    row,fresh=host.store.reserve(host.run_id,closeout_key,core.digest({'started':s['started_unix']}),
        host.actor,{**core.zero(),'wall_s':engineering},kind='engineering')
    if fresh:
        host.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=host.actor,
            tool_id='engineering.research_core_delivery',tool_version='1.0.0',execution_status='completed',charged=core.zero()),
            dict(elapsed_activity_s=elapsed,classification='engineering and idle elapsed time; excludes separately charged work'),elapsed=engineering)
        with host.store.transaction() as db:
            current=host.store.session(host.run_id,db)['state'];current['completed_unix']=time.time()
            host.store.update_state(db,host.run_id,current,'stopped')
    s=core.state(host)
    out=core.ROOT/'evidence/research_core_20261011';out.mkdir(parents=True,exist_ok=True)
    reader=ControlEvidence(host.store);rows=[];counts=Counter()
    for ref in s['results']:
        r=host.store.artifact(ref);c=host.store.artifact(r['candidate']);profile=r.get('profile') or {}
        obs=[];source=None
        if r.get('execution_id') and r['status']=='evaluated':
            source=reader.resolve(r['execution_id']);obs=reader.read_file(source,'controller_observations.json',[])
        counts['internal_nmpc_attempts']+=len(obs)
        counts['complete_update_records']+=sum('complete_update_record' in o for o in obs)
        counts['internal_recovery_attempts']+=sum(bool((o.get('feasibility_recovery') or {}).get('attempted')) for o in obs)
        counts['internal_recovery_roots']+=sum((o.get('feasibility_recovery') or {}).get('root_solve_attempts',0) for o in obs)
        counts['internal_recovery_selections']+=sum(bool((o.get('feasibility_recovery') or {}).get('selected')) for o in obs)
        rows.append(dict(reference=ref,role=r['role'],operation_key=r['operation_key'],execution_id=r.get('execution_id'),
            owner=r['owner_run_id'],candidate=r['candidate'],candidate_identity=r['scientific_identity'],
            parameters=c['parameters'],evaluation_version=r['evaluation_version'],profile_identity=r['profile_identity'],
            status=r['status'],acceptance=r['acceptance'],cost_s=r['numerical_s'],
            failure_categories=r.get('failure_categories',[]),
            numerical_failures=dict(solver_errors=profile.get('solver_error_count'),unusable_plans=profile.get('unusable_plans'),
                error_phases=profile.get('error_phases'),execution_failure_reason=profile.get('execution_failure_reason')),
            update_count=len(obs),complete_update_records=sum('complete_update_record' in o for o in obs),
            recording_capture_s=sum(o.get('snapshot_capture_wall_s',0.)+o.get('complete_record_capture_s',0.)+
                o.get('complete_update_record',{}).get('record_capture_s',0.) for o in obs),
            snapshot_updates=[r['update_id'] for r in reader.read_file(source,'control_snapshots.json',[])] if source else [],
            prediction_summary=profile.get('one_step_prediction_summary'),stopping_counts=dict(Counter(o.get('policy_stop_reason') for o in obs)),
            plan_source_counts=dict(Counter(o.get('plan_source') for o in obs)),
            input_range_n=profile.get('tension_range_n'),deadline_misses=profile.get('deadline_misses'),
            original_files=source['files'] if source else None))
    repetition_groups={}
    for row in rows:
        key=str(row['evaluation_version'])+':'+row['candidate_identity']
        group=repetition_groups.setdefault(key,dict(evaluation_version=row['evaluation_version'],
            candidate_identity=row['candidate_identity'],parameters=row['parameters'],executions=[],passed=0,failed=0,confirmations=0))
        group['executions'].append(row['reference'])
        group['passed']+=bool((row['acceptance'] or {}).get('accepted'))
        group['failed']+=not bool((row['acceptance'] or {}).get('accepted'))
        group['confirmations']+=row['role']=='confirmation'
    local_rows={}
    for ref in s.get('diagnostics',[]):
        value=host.store.artifact(ref)
        for row in value.get('rows',[value]):
            if row.get('execution_id') and 'source_update_id' in row: local_rows[row['execution_id']]=row
    local_inputs={}
    for execution_id in local_rows:
        path=core.ROOT/'runs'/host.run_id/'local_diagnostics'/execution_id/'input.json'
        if path.exists(): local_inputs[execution_id]=core.save(host,core.read(path),'local_worker_original_input_archive')
    counts['local_recovery_roots']=sum(r.get('recovery',{}).get('root_solve_attempts',0) for r in local_rows.values())
    plans=[dict(reference=r,**host.store.artifact(r)) for r in s['plans']]
    events=host.store.events(host.run_id)
    responses=[host.store.artifact(e['outputs'][0]) for e in events if e['kind']=='r3_response' and e['status']=='metadata_saved']
    token_totals={}
    for field in ('prompt_tokens','completion_tokens','total_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens'):
        values=[(r.get('usage') or {}).get(field) for r in responses]
        token_totals[field]=sum(values) if values and all(type(v) is int for v in values) else None
    comparison=core.ROOT/'runs'/host.run_id/'repeatability_comparison.json'
    pair=core.ROOT/'runs'/host.run_id/'completed_identical_input_pair.json'
    saved_comparison=core.read(comparison) if comparison.exists() else {}
    saved_pair=core.read(pair) if pair.exists() else {}
    support_files={}
    for name in ('migration_1.json','migration_2.json','migration_3.json','local_output_recovery.json'):
        path=core.ROOT/'runs'/host.run_id/name
        if path.exists(): support_files[name]=core.save(host,read_saved_json(path),'engineering_recovery_archive')
    for name in ('engineering_reference.py','engineering_diagnosis.py','engineering_diagnosis_second.py',
            'reconcile_local_output.py','engineering_identity_facts.py','record_delivery_checks.py'):
        path=core.ROOT/'runs'/host.run_id/name
        if path.exists(): support_files[name]=core.save(host,dict(path=name,source=path.read_text(encoding='utf8')),'original_engineering_command_archive')
    counts.update(dict(provider_requests=s['pilot']['live_model_requests'],physical_launches=host.store.remaining()['used']['backend_solves'],
        public_operations=host.store.remaining()['used']['tool_calls'],standalone_local_solves=s['local_solves'],offline_joint_nlp=0,bdf_replays=0))
    summary=dict(schema='unified_research_core_delivery_v1',study_id=host.run_id,source_commit=s['spec']['base_commit'],
        implementation_freeze=s['freeze'],status=s['research_status'],
        core=dict(status='implemented',entry='tools.research.core',task='existing reach_and_hold',
            engineering='frozen candidate/evaluation identity, shared receipt accounting, native tools, complete control inputs, diagnosis, export',
            search='existing bounded coordinate method with explicit recovery profile; actual exercised paths recorded in plans'),
        enhancements=dict(offline_schedule_initialization='deferred; core does not require offline NLP',
            legacy_skill_admission='deferred; drafts remain read-only recommendations'),
        scientific_executions=rows,repetition_groups=list(repetition_groups.values()),claims=core.claims(host),counts=dict(counts),
        cumulative_resources=core.packet(host)['resource_use'],
        profile_history=[dict(identity=p['identity'],version=p['version'],reference=core.save(host,p,'evaluation_profile_archive')) for p in s['profile_history']],
        core_repairs=s.get('core_repairs',[]),original_plans=plans,
        post_stop_engineering_changes=s.get('post_stop_engineering_changes'),
        original_model_final_disposition=s.get('final_disposition'),
        factual_interpretation_corrections=[
            'Candidate construction may reuse an immutable artifact for identical full parameters; this does not reuse a physical execution.',
            'The model-selected execute produced a new backend launch, independent execution ID and positive numerical cost. Its child owner belongs to this study and its result is eligible for selection.',
            'Original model statements describing that execution as zero-cost replay or lacking an owned result are unsupported. They are preserved as model interpretation, not scientific facts.',
            'd changes the resolved physical lengths near=.16+.0055*d and far=.11-.0055*d. It is part of the candidate recipe and is not needed to create a study-owned execution.',
            'Development/search role is reporting metadata; identical full scientific configuration was executed independently. Three current-version reference executions exist, with two passes and one failure; the disagreement is a real observed run-to-run difference, with cause unresolved.'],
        mathematical_searches=[dict(operation_key=k,reference=core.save(host,v,'mathematical_search_archive'),
            completed_evaluations=len(v.get('evaluated',[])),termination=v.get('termination'),
            actual_parameters=[dict(d=(r['resolved']['parameters']['lengths_m'][0]-.16)/.0055,
                **{w:r['resolved']['parameters'][w] for w in ('holding_tip_speed_weight','terminal_tip_speed_weight')})
                for r in v.get('evaluated',[])]) for k,v in s['searches'].items()],
        original_model_tool_feedback_events=[e['event_id'] for e in events if e['kind']=='model_original_tool_feedback'],
        provider_usage=dict(confirmed_responses=len(responses),tokens=token_totals,money=None,
            elapsed_response_s=sum(r['elapsed_s'] for r in responses),source='actual provider metadata; absent fields unknown'),
        engineering_recovery_records=support_files,
        repeatability_comparison=dict(reference=saved_comparison.get('reference'),
            first_action_divergence=saved_comparison.get('first_action_divergence'),
            unique_cause=saved_comparison.get('unique_cause')),
        identical_input_pair=dict(reference=saved_pair.get('reference'),
            maximum_first_input_difference_n=saved_pair.get('maximum_first_input_difference_n'),
            qualification='Fresh diagnostic-traced workspaces differ from the original physical execution; identical local outputs do not isolate its cause.'),
        experience_retrievals=s['retrievals'],retrieval_dispositions=[dict(plan=p['reference'],disposition=p['original_plan']['experience_disposition']) for p in plans if p['original_plan']['experience_disposition']],
        diagnostics=s.get('diagnostics',[]),diagnostic_facts=s.get('diagnostic_facts',[]),
        local_solve_outcomes=[dict(execution_id=r['execution_id'],reference=core.save(host,r,'local_outcome_archive'),
            original_worker_input=local_inputs.get(r['execution_id']),
            source_update_id=r['source_update_id'],exact_initialized_vector_equal=r.get('exact_initialized_vector_equal'),
            exact_variable_order_equal=r.get('exact_variable_order_equal'),exact_bounds_equal=r.get('exact_bounds_equal'),
            first_input_n=r.get('first_input_n'),worker_numerical_s=r.get('numerical_s'),charged_numerical_s=r['charged_numerical_s'],
            mode=r.get('mode'),iterations=r.get('diagnostics',{}).get('iterations'),
            charge_is_conservative_upper_bound=r.get('charge_is_conservative_upper_bound',False)) for r in local_rows.values()],
        activity_elapsed_s=time.time()-s['started_unix'],
        limitations=['single seed and task','inclusive six-sample holding interval, no continuous-time guarantee',
            'ideal tension; no hardware or actuator dynamics','wall-clock early stopping can change delivered iterates',
            'no global optimum, task generalization or LLM superiority','limited repetitions do not establish general robustness'])
    core.atomic_json(out/'scientific_summary.json',summary)
    decision_rows=[p for p in plans if p['origin']=='model']
    lines=['# Unified research core delivery, 2026-10-11','',
        'The reusable entry connects direct proposals and mathematical search to the same frozen candidate constructor and receipt-backed evaluator. Full resolved parameter/evaluation identity, independent execution identity, confirmation checks and shared internal batch accounting are enforced.', '',
        f"Native study status: `{s['research_status']}`. {counts['provider_requests']} actual configured DeepSeek requests; {len(decision_rows)} original native research plans. Engineering-selected experiments are identified by their operation keys. Original decisions and feedback are preserved in the canonical archive.", '',
        '| Execution / origin | Version | Terminal error mm | Holding position mm | Holding speed m/s | Joint acceptance |',
        '|---|---:|---:|---:|---:|---|']
    for r in rows:
        a=r['acceptance'];m=(a or {}).get('metrics',{})
        def fmt(name,scale=1.): return f"{scale*m[name]:.6f}" if name in m else 'unavailable'
        lines.append(f"| {r['operation_key']} | {r['evaluation_version']} | {fmt('terminal_error_m',1000)} | {fmt('holding_max_error_m',1000)} | {fmt('holding_max_speed_m_s')} | {(a or {}).get('status',r['status'])} |")
    claims=summary['claims']
    lines+=['',f"Independent post-selection confirmations: {claims['independent_confirmation_count']}; failures: {claims['confirmation_failures']}. Limited repeat-supported acceptance: {claims['limited_repeat_supported_acceptance']}. Parameter improvement attribution permitted by the evidence gate: {claims['parameter_improvement_attribution_permitted']}.", '',
        'The actual bounded search evaluated d=0 and d≈0.05 while both tip-speed weights stayed fixed at 0.1. Both evaluations failed holding speed; no passing search candidate was selected. Two confirmation launches still fitted, but the model stopped after invalid identity submissions. The mathematical path was exercised; free control-weight search was checked with substituted evaluators, and read-only draft retrieval was interface-tested but not used autonomously.', '',
        'The native model attempted confirmation with a non-owned artifact and received a rejection, then chose a real fresh reference execution and proposed the same parameters. Identical construction returned the same immutable candidate artifact. The model subsequently described the execution as zero-cost replay and lacking ownership; those explanations are unsupported: the ledger records a fresh backend launch and positive cost, and the result belongs to this study. Original decisions are retained separately from this factual correction. No extra experiment was forced to obtain confirmations.', '',
        'The final model explanation also attributed the repeated reference disagreement to role/phase labeling. Those labels are metadata: the full scientific configuration was identical, and the executions were independent. The current-version reference has two passes and one failure; its unique cause remains unresolved. A comparable reference was established, but the changed-length candidate failed and has no improvement or confirmation support.', '',
        f"Complete update inputs: {counts['complete_update_records']} of {counts['internal_nmpc_attempts']} attempts. Internal recovery attempts/roots/selections: {counts['internal_recovery_attempts']}/{counts['internal_recovery_roots']}/{counts['internal_recovery_selections']}. Their time is included once in the enclosing simulation. Standalone local solves: {counts['standalone_local_solves']}, {s['local_solve_s']:.3f} s.", '',
        f"Cumulative numerical time: {s['numerical_s']:.3f}/10800 s; physical launches: {counts['physical_launches']}/8; public operations: {counts['public_operations']}/128; provider requests: {counts['provider_requests']}/32. Original clock and all earlier result costs remain intact.", '',
        'Offline schedule initialization and legacy skill admission are deferred. Read-only draft retrieval remains available; startup historical context is distinguished from actual retrieval. No claim of optional enhancement effectiveness is made.', '',
        'The historical .10/.10 development passed and its independent confirmation failed; complete earlier warm starts were not saved. The unique cause remains unresolved. Synchronous wall overruns did not skip simulated-time commands. One seed, ideal tensions and sampled acceptance limit all conclusions.', '',
        'Fresh version-2 references also split between failure and acceptance. Their first differing action occurred at update 1 (0.01 s), despite equal measured state, previous input, full warm source and initialized vector. Two standalone production-policy solves reconstructed from that saved input returned identical first actions, but fresh traced workspaces differ from the original execution, so the unique cause remains unresolved. The first local result was recovered after a reporting serialization error without repeating its solve; its full 150 s reservation remains charged conservatively. All three pre-session references and failed model tool submissions remain preserved.', '',
        'Thirteen distinct focused checks passed. The two admission/selection checks were rerun after post-STOP bookkeeping changes; scientific source hashes stayed unchanged. A Windows UTF-16 migration-log decoding issue during export was repaired by reading its recorded encoding, without any numerical rerun. Canonical archive member hashes, unique physical execution IDs, all budget ceilings, sealed operations and zero provider sends after accepted STOP are verified.', '',
        '[Runbook](research_core_runbook.md), [machine summary](../evidence/research_core_20261011/scientific_summary.json), [focused verification](../evidence/research_core_20261011/verification.json), [archive manifest](../evidence/research_core_20261011/archive_manifest.json).']
    (core.ROOT/'docs/research_core_completion.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    state_reference=core.save(host,core.state(host),'complete_final_state_archive')
    core.export(host,out)
    core.atomic_json(out/'state.json',dict(reference=state_reference,study_id=host.run_id,
        research_status=s['research_status'],profile_identity=s['profile']['identity'],
        results=s['results'],selected=s.get('selected'),final_disposition=s.get('final_disposition')))
    manifest=core.read(out/'archive_manifest.json')
    expected={m['name']:m for m in manifest['members']}
    with tarfile.open(out/'immutable_artifacts.tar.gz','r:gz') as archive:
        actual=set()
        for member in archive:
            actual.add(member.name);item=expected[member.name]
            body=archive.extractfile(member).read()
            if len(body)!=item['bytes'] or hashlib.sha256(body).hexdigest()!=item['sha256']:
                raise ValueError('ARCHIVE_MEMBER_INTEGRITY_FAILED')
    if actual!=set(expected): raise ValueError('ARCHIVE_MEMBER_SET_INCOMPLETE')
    if hashlib.sha256((out/'immutable_artifacts.tar.gz').read_bytes()).hexdigest()!=manifest['archive_sha256']:
        raise ValueError('ARCHIVE_INTEGRITY_FAILED')
    used=host.store.remaining()['used'];budget=s['spec']['budgets']
    with host.store.connect(True) as db:
        unsealed=[dict(r) for r in db.execute("SELECT run_id,request_id,status FROM calls WHERE status IN ('running','unknown')")]
    stop=host.store.artifact(s['final_disposition'])
    stop_sequence=max(e['sequence'] for e in host.store.events(host.run_id)
        if e['request_id']==stop['request_id'] and e['kind']=='tool' and e['status']=='completed')
    later_sends=sum(e['kind']=='r3_request' and e['status']=='sent' and e['sequence']>stop_sequence
        for e in host.store.events(host.run_id))
    integrity=dict(archive_members_verified=len(actual),archive_sha256=manifest['archive_sha256'],
        physical_execution_ids_unique=len({r['execution_id'] for r in rows if r['execution_id']})==len([r for r in rows if r['execution_id']]),
        all_budgets_within_limits=all(used[k]<=host.store.remaining()['limit'][k] for k in used)
            and s['numerical_s']<=budget['numerical_s'] and s['local_solves']<=budget['local_solves']
            and s['local_solve_s']<=budget['local_solve_s'],
        unresolved_resources=host.store.remaining()['occupied'],
        unsealed_operations=unsealed,
        numerical_work_repeated_for_export=False,provider_requests_after_accepted_stop=later_sends)
    if later_sends or unsealed or integrity['unresolved_resources'] or not integrity['all_budgets_within_limits']:
        raise ValueError('DELIVERY_CLOSURE_OR_BUDGET_INTEGRITY_FAILED')
    core.atomic_json(out/'delivery_integrity.json',integrity)
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--spec',type=Path,default=core.ROOT/'examples/research_core/specification.json')
    spec=core.read(parser.parse_args().spec)
    host=core.Host(core.ROOT/'runs'/spec['study_id'],spec['study_id'],actor='unified-research')
    result=deliver(host)
    print(json.dumps(dict(status=result['status'],counts=result['counts'],claims=result['claims'])))
