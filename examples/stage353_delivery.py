"""Offline Milestone 0 delivery: sealed outcomes, source checks and accounting."""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.state_io import read,atomic_json
from tools.platform_store import Store
from tools.diagnostic_improvement import actual_diff
from extensions.tendon_family.gvs_profile import execution_scope


def main():
    config=read(ROOT/'examples/stage353_experiment.json');export=Path(config['evidence_directory'])
    freeze=read(export/'live_freeze.json');runs=[];archives=[];providers=[]
    baseline=Store(config['source_store']).artifact(dict(artifact_id=config['configuration_artifact'],media_type='application/json'))['effective']
    for mode in config['formal_order']:
        directory=Path(config['run_directory'])/mode;store=Store(directory)
        outcome=read(directory/'outcome.json');audit=read(export/(mode+'_audit.json'));frozen=read(directory/'freeze.json')
        providers.append(frozen['provider_configuration'])
        request_sizes=[]
        with store.connect(True) as db:run_ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
        for run_id in run_ids:
            for event in store.events(run_id):
                if event['kind']=='model_request':
                    payload=store.artifact(event['inputs'][0])
                    # Same serializer as the unchanged DeepSeek transport;
                    # canonical ledger bytes and HTTP body bytes differ.
                    wire=len(json.dumps(payload,ensure_ascii=False).encode('utf8'))
                    assert wire<=400000
                    request_sizes.append(dict(run_id=run_id,request_id=event['request_id'],http_body_bytes=wire,
                        output_headroom_tokens=payload['max_tokens'],source=event['inputs'][0]))
        assert frozen['memory_policy']['context_bytes']==400000
        assert frozen['implementation']['commit']==freeze['implementation']['commit']
        assert frozen['identities']['execution_id']==config['execution_id']
        result=outcome['physical_improvement']['complete_execution']
        decision=store.artifact(outcome['chain']['improvement_decision'])['decision'] if 'improvement_decision' in outcome['chain'] else None
        final=store.artifact(outcome['chain']['final_response']) if 'final_response' in outcome['chain'] else None
        scope_diff=[]
        if result and result.get('configuration'):
            candidate=store.artifact(result['configuration'])['effective']
            scope_diff=actual_diff(execution_scope(baseline),execution_scope(candidate))
            allowed={'/controller/parameters/data/recipe/'+p for p in ('terminal_tip_speed_weight','holding_tip_speed_weight')}
            assert scope_diff and all(d['pointer'] in allowed for d in scope_diff)
        feedback=read(directory/'feedback.json') if (directory/'feedback.json').exists() else {}
        runs.append(dict(organization=mode,status=outcome['status'],stop_reason=outcome['stop_reason'],
            reliability_acceptance=audit['acceptance'],decision=decision,final_response=final,
            completion=result.get('structured_feedback') if result else None,scope_diff=scope_diff,
            physical_comparison=feedback.get('campaign_comparison'),usage=outcome['usage'],
            numerical_work=outcome['numerical_work'],workflow_elapsed_s=outcome['elapsed_s'],
            provider_tokens=audit['tokens'],provider_usage_records=audit['token_usage_records'],
            request_sizes=request_sizes,canonical_request_sizes=audit['request_sizes'],implementation_commit=frozen['implementation']['commit'],
            evidence=mode+'/outcome.json',audit=mode+'_audit.json'))
    assert providers[0]==providers[1]
    for name in ('posthoc',*config['formal_order']):
        directory=export/name;manifest=read(directory/'sha256_manifest.json')
        assert not read(directory/'portable_closure.json')['unresolved']
        mismatches=[p for p,h in manifest.items() if hashlib.sha256((directory/p).read_bytes()).hexdigest()!=h]
        assert not mismatches,mismatches
        archives.append(dict(directory=name,verified_files=len(manifest),hash_mismatches=0,unresolved_references=0))
    posthoc=read(export/'posthoc/outcome.json');preflight=read(export/'preflight.json')
    totals={k:sum(r['usage']['used'][k] for r in runs) for k in config['overall_limits']}
    assert all(totals[k]<=cap for k,cap in config['overall_limits'].items())
    total_with_support={k:totals[k]+posthoc['usage']['used'][k]+preflight['used'][k] for k in totals}
    tokens={k:sum(r['provider_tokens'][k] for r in runs)+sum((a.get('provider_usage') or {}).get(k,0) for a in preflight['attempts'])
            for k in ('prompt_tokens','completion_tokens','total_tokens')}
    passed=all(r['reliability_acceptance']['passed'] for r in runs)
    delivery=dict(milestone='Stage 3.53 / Milestone 0',execution_reliability_accepted=passed,
        next_milestone_can_proceed=passed,blockers=[] if passed else [r['organization']+': '+r['stop_reason'] for r in runs if not r['reliability_acceptance']['passed']],
        changes=dict(context_bytes=400000,context_guard=config['context_guard'],operation_allowances=config['operation_allowances'],
            reservations=config['budget_rationale'],continuation='Three receipt-backed recorded stages; verified reuse without repeating or charging completed operations. Unsealed reservations remain explicitly unresolved; no universal exactly-once guarantee.'),
        verification=dict(focused='focused_check.json',prior_suite='focused_check_initial.json',archives=archives,
            same_live_implementation=True,same_provider_configuration=True,same_baseline=True,scope_differences_restricted_to_authorized_weights=True,
            implementation_transition='implementation_transition.json'),
        historical=dict(classification=posthoc['classification'],scheduled_stage352_evaluation_completed=False,
            supplement_completes_stage352_matched_comparison=False,feedback=posthoc['result']['structured_feedback'],
            new_usage=posthoc['usage']['used'],historical_simulation_usage=posthoc['provenance']['historical_charged_usage'],
            evaluation_semantic_difference=posthoc['provenance']['semantic_difference'],evidence='posthoc/outcome.json'),
        runs=runs,live_usage=totals,preflight_usage=preflight['used'],new_usage_including_posthoc_and_preflight=total_with_support,
        reported_tokens=tokens,monetary_cost=None,
        cost_qualification='Actual sealed operation wall charges; workflow elapsed reported separately. Failed connection has no token usage. Historical simulation cost is not charged again. Setup/export overhead is outside the existing operation ledger.',
        scientific_limitations=['Engineering validation of one bounded run per organization; no statistical comparison.',
            'Sampled holding coverage is not a continuous-time guarantee.',
            'Initialization-selected plans still apply control; wall overruns do not imply skipped updates or simulated actuator delay.',
            'Exact source-selector validation does not certify model causal explanations.',
            'Synchronous Python evaluation/profile timeouts are checked after return; overruns remain charged and failed.'],
        implementation_commits=['5fd27d8',freeze['implementation']['commit']],pushed=False)
    atomic_json(export/'delivery_summary.json',delivery)
    lines=['Stage 3.53 / Milestone 0 delivery',
        'Execution-reliability acceptance: '+('PASSED' if passed else 'NOT PASSED'),
        'Context cap: 400,000 canonical request bytes in both organizations; actual HTTP body sizes retained separately. Output settings unchanged: 65,536 tokens, existing length recovery 131,072.',
        'Simulation/evaluation/profile each have their own timeout and reservation: 900/30/60 seconds. Executor phase 1,600 seconds; downstream feedback protection 600 seconds. Actual execution usage remains charged.',
        'Continuation reuses verified sealed simulation/evaluation/profile receipts without duplicate execution or accounting. Unsealed reservations remain unresolved. This is not universal exactly-once execution.',
        'Focused suite: existing workflow/context checks plus interruption, budget boundary/refusal, metric equivalence and identity/integrity checks. A test-only mock assertion was corrected; affected tests passed. Nine affected checks passed after the prelaunch context-configuration repair, including both organization preparations.',
        'One prelaunch host defect was repaired before any provider or backend work; original empty run grant retained. Both live runs used '+freeze['implementation']['commit']+'.',
        '',posthoc['classification'],
        'Stage 3.52 scheduled evaluation remains incomplete; this supplement does not complete its matched comparison.',
        'Terminal/holding position thresholds: 10 mm. Holding speed threshold: 0.02 m/s. All reported holding windows have six retained samples from 0.30 to 0.35 seconds; no continuous-time guarantee.',
        'Case | terminal error mm | holding max error mm | holding max speed m/s | reach | joint reach+holding']
    for name,facts in [('historical',posthoc['result']['structured_feedback'])]+[(r['organization'],r['completion']) for r in runs]:
        if facts:
            lines.append(f"{name} | {1000*facts['terminal']['error_m']:.6f} | {1000*facts['holding']['max_position_error_m']:.6f} | {facts['holding']['max_speed_m_s']:.6f} | {facts['reach_only_success']} | {facts['joint_reach_holding_success']}")
    lines+=['Speed is the world-frame norm of the tip translational Jacobian times recorded backend qvel. All three executions applied 35 controls and missed 35 computation deadlines; initialization-selected plans still apply control. Simulated duration is 0.35 seconds.', '']
    for r in runs:
        u=r['usage']['used'];final=r['final_response']
        lines += [r['organization']+': '+r['status']+'. '+r['stop_reason'],
            'Final decision: '+(final['disposition']+'; '+final['reasoning'] if final else 'Not reached.'),
            f"Usage: {u['backend_solves']} new backend execution; {u['model_calls']} provider attempts; {u['tool_calls']} tool calls; {u['wall_s']:.3f} charged seconds; {r['workflow_elapsed_s']:.3f} workflow elapsed seconds; {r['provider_tokens']['total_tokens']} reported tokens.",
            'Physical comparison: '+str((r['physical_comparison'] or {}).get('classification'))+'.']
    lines += ['',f"Total including preflight and post-hoc work: {total_with_support['backend_solves']} new backend executions; {total_with_support['model_calls']} provider attempts; {total_with_support['tool_calls']} tool calls; {total_with_support['wall_s']:.3f} charged seconds; {tokens['total_tokens']} reported tokens. Zero workers/subagents.",
        f"Preflight separately: {preflight['used']['model_calls']} attempts, {preflight['used']['wall_s']:.3f} seconds; first connection refused by sandbox proxy, second host-network request succeeded with TLS preserved.",
        f"Post-hoc work separately: {posthoc['usage']['used']['tool_calls']} tool calls, {posthoc['usage']['used']['wall_s']:.3f} charged seconds; zero new simulations/model calls. Historical simulation wall cost is preserved, not charged again.",
        'Monetary cost: unknown. Failed-connection token usage: unknown. Setup/export overhead is outside the operation ledger; workflow elapsed is reported separately.',
        'Next milestone: '+('May proceed.' if passed else 'Blocked on accepted model revision and final decision under the bounded recovery policy. Do not reset limits or launch replacement runs.'),
        'Physical improvement and real-time feasibility are not established. These are engineering checks, not a statistical comparison.',
        'Implementation commits: 5fd27d8 and '+freeze['implementation']['commit']+'. Evidence is committed separately. No push.',
        'Detailed facts, costs, provenance, requests and acceptance checks: delivery_summary.json and organization audit files.']
    (export/'DELIVERY.txt').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(json.dumps(dict(accepted=passed,usage=total_with_support,tokens=tokens,
        runs=[dict(mode=r['organization'],acceptance=r['reliability_acceptance'],completion=r['completion']) for r in runs]),indent=2))


if __name__=='__main__':main()
