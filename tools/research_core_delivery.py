"""Post-STOP reporting from saved evidence only; no model or numerical reruns."""
from collections import Counter
from pathlib import Path
import json
import time
from tools import research_core as core
from extensions.tendon_family.control_evidence import ControlEvidence


def deliver(host):
    s=core.state(host)
    if s['pending']: raise ValueError('RECOVER_PENDING_OUTPUT_BEFORE_REPORTING')
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
            update_count=len(obs),complete_update_records=sum('complete_update_record' in o for o in obs),
            recording_capture_s=sum(o.get('snapshot_capture_wall_s',0.)+o.get('complete_record_capture_s',0.)+
                o.get('complete_update_record',{}).get('record_capture_s',0.) for o in obs),
            snapshot_updates=[r['update_id'] for r in reader.read_file(source,'control_snapshots.json',[])] if source else [],
            prediction_summary=profile.get('one_step_prediction_summary'),stopping_counts=dict(Counter(o.get('policy_stop_reason') for o in obs)),
            plan_source_counts=dict(Counter(o.get('plan_source') for o in obs)),
            input_range_n=profile.get('tension_range_n'),deadline_misses=profile.get('deadline_misses'),
            original_files=source['files'] if source else None))
    plans=[dict(reference=r,**host.store.artifact(r)) for r in s['plans']]
    events=host.store.events(host.run_id)
    counts.update(dict(provider_requests=s['pilot']['live_model_requests'],physical_launches=host.store.remaining()['used']['backend_solves'],
        public_operations=host.store.remaining()['used']['tool_calls'],standalone_local_solves=s['local_solves'],offline_joint_nlp=0,bdf_replays=0))
    summary=dict(schema='unified_research_core_delivery_v1',study_id=host.run_id,source_commit=s['spec']['base_commit'],
        implementation_freeze=s['freeze'],status=s['research_status'],
        core=dict(status='implemented',entry='tools.research_core',task='existing reach_and_hold',
            engineering='frozen candidate/evaluation identity, shared receipt accounting, native tools, complete control inputs, diagnosis, export',
            search='existing bounded coordinate method with explicit recovery profile; actual exercised paths recorded in plans'),
        enhancements=dict(offline_schedule_initialization='deferred; core does not require offline NLP',
            legacy_skill_admission='deferred; drafts remain read-only recommendations'),
        scientific_executions=rows,claims=core.claims(host),counts=dict(counts),
        cumulative_resources=core.packet(host)['resource_use'],profile_history=s['profile_history'],
        core_repairs=s.get('core_repairs',[]),original_plans=plans,
        original_model_final_disposition=s.get('final_disposition'),
        original_model_tool_feedback_events=[e['event_id'] for e in events if e['kind']=='model_original_tool_feedback'],
        experience_retrievals=s['retrievals'],retrieval_dispositions=[dict(plan=p['reference'],disposition=p['original_plan']['experience_disposition']) for p in plans if p['original_plan']['experience_disposition']],
        diagnostics=s.get('diagnostics',[]),activity_elapsed_s=time.time()-s['started_unix'],
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
        f"Complete update inputs: {counts['complete_update_records']} of {counts['internal_nmpc_attempts']} attempts. Internal recovery attempts/roots/selections: {counts['internal_recovery_attempts']}/{counts['internal_recovery_roots']}/{counts['internal_recovery_selections']}. Their time is included once in the enclosing simulation. Standalone local solves: {counts['standalone_local_solves']}, {s['local_solve_s']:.3f} s.", '',
        f"Cumulative numerical time: {s['numerical_s']:.3f}/10800 s; physical launches: {counts['physical_launches']}/8; public operations: {counts['public_operations']}/128; provider requests: {counts['provider_requests']}/32. Original clock and all earlier result costs remain intact.", '',
        'Offline schedule initialization and legacy skill admission are deferred. Read-only draft retrieval remains available; startup historical context is distinguished from actual retrieval. No claim of optional enhancement effectiveness is made.', '',
        'The historical .10/.10 development passed and its independent confirmation failed; complete earlier warm starts were not saved. The unique cause remains unresolved. Synchronous wall overruns did not skip simulated-time commands. One seed, ideal tensions and sampled acceptance limit all conclusions.', '',
        '[Runbook](research_core_runbook.md), [machine summary](../evidence/research_core_20261011/scientific_summary.json), [focused verification](../evidence/research_core_20261011/verification.json), [archive manifest](../evidence/research_core_20261011/archive_manifest.json).']
    (core.ROOT/'docs/research_core_completion.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    core.export(host,out)
    return summary


if __name__=='__main__':
    spec=core.read(core.DEFAULT_SPEC)
    host=core.Host(core.ROOT/'runs'/spec['study_id'],spec['study_id'],actor='unified-research')
    result=deliver(host)
    print(json.dumps(dict(status=result['status'],counts=result['counts'],claims=result['claims'])))
