"""Closeout from saved current-study evidence, without additional experiments."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time
from tools import research_core as core
from tools.platform_host import Host
from extensions.tendon_family.control_evidence import ControlEvidence


def deliver(host):
    s=core.state(host)
    if s['research_status']!='stopped' or s['pending']:raise ValueError('SEALED_STUDY_AND_KNOWN_OUTCOMES_REQUIRED')
    out=core.ROOT/s['spec']['evidence_destination'];out.mkdir(parents=True,exist_ok=True)
    reader=ControlEvidence(host.store);rows=[];counts=Counter()
    for ref in s['results']:
        r=host.store.artifact(ref); c=host.store.artifact(r['candidate']);obs=[]
        if r['status']=='evaluated':
            source=reader.resolve(r['execution_id']);obs=reader.read_file(source,'controller_observations.json',[])
        counts['controller_update_attempts']+=len(obs)
        counts['complete_input_records']+=sum('complete_update_record' in o or 'failed_update_input_record' in o for o in obs)
        counts['complete_resolved_problems']+=sum('resolved_problem' in o.get('complete_update_record',{}) for o in obs)
        rows.append(dict(reference=ref,parameters=c['parameters'],**core.compact_result(r),operation_key=r['operation_key']))
    mechanics=[]
    for ref in s['mechanics_results']:
        v=host.store.artifact(ref)
        mechanics.append(dict(reference=ref,**{k:v.get(k) for k in ('operation','status','execution_id','owning_study',
            'termination_reason','trajectory_reference','checkpoint_reference','variable_order','objective_definition',
            'trajectory_metrics','hard_max_normalized_violation','relaxed_nlp_feasible','original_task_feasible',
            'original_task_gaps','slack_values','costs_s','charged_numerical_s','replay','physical_validation')},
            returned_structure={k:v['candidate'].get(k) for k in ('d','lengths_m','substeps')} if v.get('candidate') else None))
    plans=[dict(reference=r,**host.store.artifact(r)) for r in s['plans']]
    searches=[]
    for key,v in s['searches'].items():
        evaluated=v.get('evaluated',[])
        actual=[dict(d=(r['resolved']['parameters']['lengths_m'][0]-.16)/.0055,
            **{k:r['resolved']['parameters'][k] for k in ('holding_tip_speed_weight','terminal_tip_speed_weight')}) for r in evaluated]
        requested=next((p['original_plan']['search'] for p in plans if p['request_id']==key),None)
        searches.append(dict(operation_key=key,requested=requested,actual_parameters=actual,
            distinct_configurations=len({r['scientific_identity'] for r in evaluated}),
            execution_references=[r['evidence']['result'] for r in evaluated],termination=v['termination'],
            construction_rejections=v['rejections'],partial_batch=v['pending'] is not None))
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
    summary=dict(schema='mechanics_control_delivery_v1',study_id=host.run_id,base_commit=s['spec']['base_commit'],
        implementation_freeze=s['freeze'],source_versions=s['profile']['science_hashes'],core_versions=s['core_hashes'],
        evaluation_version=s['profile']['version'],status=s['research_status'],counts=dict(counts),
        outcomes=dict(engineering_interfaces_connected=True,
            mechanics_to_closed_loop_handoff=integration.get('status')=='connected',
            actual_control_weight_search=any(v['distinct_configurations']>=2 and v['requested'] and 'd' not in v['requested']['variables'] and
                any(len({p[w] for p in v['actual_parameters']})>=2 for w in ('holding_tip_speed_weight','terminal_tip_speed_weight')) for v in searches),
            native_feedback_consumed_and_legal_decision=bool(native),
            autonomous_research_actions=[p['original_plan']['action'] for p in native],
            native_stop=bool(native and native[-1]['original_plan']['action']=='stop'),
            structural_superiority_attribution=False,
            improvement_and_confirmation=core.claims(host)),
        mechanics=mechanics,closed_loop=rows,searches=searches,handoffs=s['handoffs'],
        engineering_demonstration=s.get('integration_demonstration'),original_plans=plans,
        diagnostics=[dict(reference=r,**host.store.artifact(r)) for r in s.get('diagnostics',[])],
        imported_diagnostic_sources=s.get('historical_diagnostic_sources',[]),
        experience_retrievals=s['retrievals'],experience_dispositions=[dict(plan=p['reference'],values=p['original_plan']['experience_disposition'])
            for p in plans if p['original_plan']['experience_disposition']],
        cumulative_resources=core.packet(host)['resource_use'],activity_elapsed_s=elapsed,
        mechanics_resources=core.packet(host)['mechanics_resource_use'],core_repairs=s.get('core_repairs',[]),
        limitations=['One frozen task and seed, ideal tensions, sampled holding acceptance only.',
            'BDF checks independent model integration, not physical validation.',
            'Structure observations lack matched control-adaptation campaigns; no structural superiority claim.',
            'Fresh diagnostics do not recreate historical cache/timing; no unique causal attribution.',
            'Optional offline NMPC trajectory initialization and legacy skill admission deferred.'])
    core.atomic_json(out/'scientific_summary.json',summary)
    core.atomic_json(out/'specification.json',s['spec'])
    # Archive state once; keep the visible index compact.
    ref=core.save(host,core.state(host),'final_state_archive')
    core.export(host,out)
    core.atomic_json(out/'state.json',dict(reference=ref,study_id=host.run_id,status='stopped',results=s['results'],mechanics_results=s['mechanics_results']))
    report=['# Mechanics and control delivery, 2026-10-11','',
        'The current research core connects offline CasADi/GVS mechanics, retained trajectory evidence, candidate handoff, fixed-structure coordinate search, complete closed-loop records and native feedback decisions. Immutable configuration, fresh execution, historical evidence and cached receipt costs are explicit.','',
        f"Engineering demonstration: `{integration.get('status','incomplete')}`. Native actions: {', '.join(p['original_plan']['action'] for p in native) or 'none'}. These activities are recorded separately.",'',
        '| Execution / origin | d | Holding weight | Terminal weight | Holding position mm | Holding speed m/s | Joint acceptance |',
        '|---|---:|---:|---:|---:|---:|---|']
    for r in rows:
        p=r['parameters'];a=r['acceptance'] or {};m=a.get('metrics',{})
        report.append(f"| {r['operation_key']} | {p['d']:.6g} | {p['holding_tip_speed_weight']:.6g} | {p['terminal_tip_speed_weight']:.6g} | {m.get('holding_max_error_m',float('nan'))*1000:.6f} | {m.get('holding_max_speed_m_s',float('nan')):.6f} | {a.get('status',r['status'])} |")
    report+=['']
    for m in mechanics:
        report.append(f"Mechanics {m['operation']}: `{m['status']}`, charged {m['charged_numerical_s']:.3f}s; original-task feasible={m['original_task_feasible']}, relaxed feasible={m['relaxed_nlp_feasible']}. Returned structure: {m['returned_structure']}. Replay gates and raw/retained selections are preserved in the archive.")
    c=core.claims(host);rs=core.packet(host)['resource_use']
    report+=['',f"Independent post-selection confirmations: {c['independent_confirmation_count']}; failures: {c['confirmation_failures']}; limited repeat-supported acceptance: {c['limited_repeat_supported_acceptance']}. Improvement attribution permitted: {c['parameter_improvement_attribution_permitted']}.",'',
        f"Costs: numerical {rs['numerical_s']:.3f}/10800s; standalone local solves {s['local_solves']}/4, {s['local_solve_s']:.3f}/600s; offline attempts {s['offline_nlp']}/2; BDF replays {s['bdf_replays']}/2; MuJoCo launches {counts['physical_launches']}/8; provider requests {counts['provider_requests']}/32; public operations {counts['public_operations']}/128. Activity elapsed {elapsed/3600:.3f}h/12h including engineering. Internal NMPC recovery is included once.",'',
        f"New controller attempts: {counts['controller_update_attempts']}; complete input records: {counts['complete_input_records']}; resolved serialized problems: {counts['complete_resolved_problems']}.",'',
        'Repeatability: original tracing was disabled at the first divergent historical update; prior reconstruction enabled it. New production diagnosis preserves tracing mode and inspects values before solving. Full resolved problems are retained for new executions. Historical serialized problems and original cache/timing are unavailable, so a unique cause remains unresolved. See numeric comparisons in the machine summary.','',
        'No structural superiority, stable robustness, autonomous discovery or unique causal diagnosis is claimed. BDF is not physical validation. Optional offline trajectory initialization and legacy skill admission remain unfinished.','',
        '[Runbook](mechanics_control_runbook.md), [scientific summary](../evidence/mechanics_control_20261011/scientific_summary.json), [focused checks](../evidence/mechanics_control_20261011/verification.json), [archive manifest](../evidence/mechanics_control_20261011/archive_manifest.json).']
    (core.ROOT/'docs/mechanics_control_completion.md').write_text('\n'.join(report)+'\n',encoding='utf8')
    return dict(report='docs/mechanics_control_completion.md',counts=dict(counts),outcomes=summary['outcomes'],resources=rs)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--spec',type=Path,required=True);args=parser.parse_args()
    spec=core.read(args.spec);h=Host(core.ROOT/'runs'/spec['study_id'],spec['study_id'],actor='unified-research')
    print(json.dumps(deliver(h)))


if __name__=='__main__':main()
