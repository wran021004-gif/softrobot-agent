"""Offline delivery of preserved Stage 3.52 outcomes; never invokes live tools."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from examples.stage350_delivery_audit import audit_run
from examples import stage352_settling_campaign as stage
from extensions.tendon_family.control_evidence import ControlEvidence
from extensions.tendon_family.delivery_facts import bound_result_facts
from extensions.tendon_family.gvs_profile import execution_scope
from tools.diagnostic_improvement import actual_diff
from tools.platform_store import Store
from tools.settling_campaign import campaign_metrics, compare_results
from tools.state_io import read, atomic_json

EVIDENCE = ROOT / 'evidence/stage352_settling_20261003'
REVALIDATION = EVIDENCE / 'revalidation'
TOKEN_KEYS = ('prompt_tokens', 'completion_tokens', 'total_tokens')
WEIGHTS = ('terminal_tip_speed_weight', 'holding_tip_speed_weight')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_archive(directory):
    manifest = read(directory / 'sha256_manifest.json')
    assert all(sha(directory / name) == expected for name, expected in manifest.items()), directory
    assert not read(directory / 'external_references.json'), directory
    artifacts = list((directory / 'artifacts').iterdir())
    assert all(sha(path) == path.stem for path in artifacts), directory
    return dict(files=len(manifest), artifacts=len(artifacts), mismatches=0, unresolved_references=0)


def main():
    config = read(ROOT / 'examples/stage352_revalidation.json')
    stage.setup(ROOT / 'examples/stage352_revalidation.json')
    baseline_record = read(EVIDENCE / 'baseline_reuse.json')
    baseline = baseline_record['result']['factual_result']
    original = ControlEvidence(Store(config['source_store'])).resolve(config['execution_id'])
    assert original == baseline_record['verification']['source']
    assert execution_scope(original['configuration']) == baseline_record['verification']['scope']
    for key, expected in baseline_record['verification']['artifact_hashes'].items():
        with Store(config['source_store']).connect(True) as db:
            media = db.execute('SELECT media FROM artifacts WHERE id=?', (key,)).fetchone()[0]
        body = Store(config['source_store']).artifact(dict(artifact_id=key, media_type=media), raw=True)
        assert hashlib.sha256(body).hexdigest() == expected == key

    freeze = read(REVALIDATION / 'paired_freeze.json')
    assert freeze['order'] == config['formal_order']
    assert freeze['baseline_manifest'] == original['manifest']
    freezes = {}
    for folder in (EVIDENCE, REVALIDATION):
        files = read(folder / 'development_freeze.json')['implementation']['files']
        assert all(sha(folder / 'validated_implementation' / name) == expected for name, expected in files.items())
        freezes[str(folder.relative_to(EVIDENCE))] = dict(files=len(files), archived_hash_mismatches=0)
    assert all(sha(ROOT / name) == expected for name, expected in freeze['implementation']['files'].items())

    primary_root = Path(config['prior_stage352_run_directory'])
    run_root = Path(config['run_directory'])
    ordered = [('primary/development_dual', primary_root / 'development_dual', EVIDENCE / 'development_dual'),
               ('revalidation/development_dual', run_root / 'development_dual', REVALIDATION / 'development_dual')]
    ordered.extend((f'pair{pair}_{mode}', run_root / f'pair{pair}_{mode}', REVALIDATION / f'pair{pair}_{mode}')
                   for pair, mode in config['formal_order'])
    rows = []
    audits = []
    formal_start_times = []
    validated_pilot_freeze = read(run_root / 'development_dual/freeze.json')
    common_freeze_fields = ('provider_configuration', 'limits', 'numerical_limits', 'memory_policy',
                           'fact_policy', 'phase_budgets', 'stage_instructions', 'permissions',
                           'capabilities', 'recovery', 'tool_bindings')
    provider_settings = deepcopy(validated_pilot_freeze['host_provider_configurations']['design'])
    provider_settings.pop('tool_naming')  # Mapping is derived from the allowed role tool subset.
    for label, directory, export in ordered:
        audit = audit_run(directory)
        audit['stage352_label'] = label
        audits.append(audit)
        outcome = read(directory / 'outcome.json')
        store = Store(directory)
        run_freeze = read(directory / 'freeze.json')
        assert run_freeze['source_manifest'] == original['manifest']
        expected_files = read((EVIDENCE if label.startswith('primary/') else REVALIDATION) / 'development_freeze.json')['implementation']['files']
        assert all(expected_files[name] == value for name, value in run_freeze['implementation']['files'].items())
        if not label.startswith('primary/'):
            assert all(run_freeze[key] == validated_pilot_freeze[key] for key in common_freeze_fields)
            for value in run_freeze['host_provider_configurations'].values():
                actual_settings = deepcopy(value)
                actual_settings.pop('tool_naming')
                assert actual_settings == provider_settings
        events = read(export / 'events.json')
        if label.startswith('pair'):
            formal_start_times.append(min(e['timestamp'] for e in events))
        failures = [e for e in events if e['kind'] == 'model_response' and e['status'] != 'completed']
        audit['failed_model_response_events'] = [dict(event=e, sealed_output=[store.artifact(r) for r in e['outputs']]) for e in failures]
        archive_check = check_archive(export)
        physical = outcome['physical_improvement']
        prep = physical.get('preparation')
        execution = physical.get('complete_execution')
        row = dict(label=label, mode=outcome['mode'], workflow_status=outcome['status'],
                   workflow_feedback_complete=outcome['feedback_complete'], stop_reason=outcome['stop_reason'],
                   used=audit['used'], tokens=audit['tokens'], monetary_cost=None,
                   numerical_work=outcome['numerical_work'], model_response_failures=len(failures),
                   archive_integrity=archive_check, selected_weights=None, actual_diff=[],
                   simulation_completed=False, official_evaluation_available=False, joint_task_success=None,
                   campaign_metrics=None, campaign_comparison=None, final_response=None)
        if outcome['chain'].get('final_response'):
            row['final_response'] = store.artifact(outcome['chain']['final_response'])
        if prep:
            before = store.artifact(prep['source_configuration'])['effective']
            after = store.artifact(prep['configuration'])['effective']
            differences = actual_diff(before, after)
            assert differences == prep['actual_diff'] and differences
            allowed = {'/policy/controller/parameters/data/recipe/' + p.removeprefix('control/recipe/') for p in prep['decision']['changes']}
            assert all(d['pointer'] in allowed for d in differences)
            assert set(prep['decision']['changes']) <= {'control/recipe/' + w for w in WEIGHTS}
            assert all(.0001 <= v <= 1. for v in prep['decision']['changes'].values())
            row.update(actual_diff=differences, model_authored_decision=prep['decision'], preparation_configuration=prep['configuration'])
            row['selected_weights'] = {w:after['policy']['controller']['parameters']['data']['recipe'][w] for w in WEIGHTS}
        if execution:
            sim = execution['receipts']['simulation']
            row['simulation_receipt'] = sim
            row['simulation_completed'] = sim['execution_status'] == 'completed'
            if row['simulation_completed']:
                source = ControlEvidence(store).resolve(sim['execution_id'])
                assert source['metadata']['artifact_id'] == sim['output']['artifact_id']
                assert sim['original_execution_id'] == sim['execution_id'] and not sim['cache_hit']
                assert source['configuration']['robot'] == original['configuration']['robot']
                assert source['configuration']['task'] == original['configuration']['task']
                science_diff = actual_diff(execution_scope(original['configuration']), execution_scope(source['configuration']))
                assert science_diff and all(d['pointer'] in {'/controller/parameters/data/recipe/' + w for w in WEIGHTS} for d in science_diff)
                restored = deepcopy(source['configuration'])
                for w in WEIGHTS:
                    restored['policy']['controller']['parameters']['data']['recipe'][w] = original['configuration']['policy']['controller']['parameters']['data']['recipe'][w]
                assert execution_scope(restored) == execution_scope(original['configuration'])
                row.update(execution_id=sim['execution_id'], executed_configuration=source['metadata']['candidate_input'],
                           execution_manifest=source['manifest'], execution_owner=source['owner'], scientific_scope_diff=science_diff)
            if execution.get('factual_result'):
                derived = bound_result_facts(store, dict(profile_report=execution['profile_report'],
                    evaluation=execution['receipts']['evaluation']['output'], simulation=sim), execution['design_statement'])
                assert derived == execution['factual_result']
                assert physical['baseline_facts'] == baseline
                comparison = compare_results(baseline, derived)
                assert comparison == read(directory / 'feedback.json')['campaign_comparison']
                row.update(official_evaluation_available=True, evaluation_receipt=execution['receipts']['evaluation'],
                           profile_receipt=execution['receipts']['profile'], campaign_metrics=campaign_metrics(derived),
                           campaign_comparison=comparison, joint_task_success=comparison['candidate']['joint_reach_holding_passed'],
                           result_classification=comparison['classification'])
            else:
                assert read(directory / 'feedback.json')['campaign_comparison'] is None
                row.update(result_classification='simulation_completed_evaluation_blocked',
                           evaluation_receipt=execution['receipts'].get('evaluation'))
        else:
            row['result_classification'] = 'model_protocol_failure_before_candidate'
        rows.append(row)
    assert formal_start_times == sorted(formal_start_times)
    usage = stage.usage(config)
    assert all(not r.get('occupied') for r in usage['runs'])
    token_totals = {k:sum(r['tokens'][k] for r in rows) for k in TOKEN_KEYS}
    preflight = read(EVIDENCE / 'preflight.json')
    for attempt in preflight['attempts']:
        if attempt.get('provider_usage'):
            for k in TOKEN_KEYS:
                token_totals[k] += attempt['provider_usage'].get(k, 0)
    local = {k:sum(r['numerical_work']['used'][k] for r in rows) for k in ('local_solves','prediction_evaluations')}
    assert usage['used']['backend_solves'] == sum(r['simulation_completed'] for r in rows) == 5
    assert usage['used']['model_calls'] == sum(r['used']['model_calls'] for r in rows) + len(preflight['attempts'])
    assert baseline_record['new_backend_executions'] == 0
    assert local == dict(local_solves=0, prediction_evaluations=0)
    assert all(r['campaign_comparison']['classification'] == 'physical_pareto_worsening' for r in rows if r['campaign_comparison'])
    review = read(EVIDENCE / 'scientific_review.json')
    summary = dict(
        status='Delivered all four scheduled outcomes; complete matched physical comparison not established',
        implementation_commits=['0cb1f4a', '07b72ac'], formal_implementation_commit=freeze['implementation']['commit'],
        offline_delivery_script='examples/stage352_delivery_audit.py; created only after all live runs terminated; outside live freeze',
        communication=dict(validated=True, preflight=preflight, historical_stage351_failure_cause='Unknown: old transport did not retain subtype/reason'),
        reused_baseline=dict(classification=baseline_record['classification'], source_store=config['source_store'],
            manifest=original['manifest'], owner=original['owner'], metrics=campaign_metrics(baseline),
            original_baseline_usage=baseline_record['historical_usage'], new_verification_import_usage=baseline_record['new_usage'],
            new_baseline_backend_executions=0, closure_artifacts_verified=len(baseline_record['verification']['artifact_hashes'])),
        development_repair=dict(reason='Primary revision failed before provider dispatch: 201297 required bytes exceeds fixed 200000 cap',
            repair='Reduce displayed fact-catalog subset only; preserve exact host mappings, receipt ledger, full handoffs and separate memories',
            verification=read(EVIDENCE / 'host_repair/repair_check.json'), primary_gate=read(EVIDENCE / 'pilot_gate.json'),
            fresh_revalidation_gate=read(REVALIDATION / 'pilot_gate.json'), fresh_pilots_used=1, repair_allowance_remaining=0),
        formal_order=config['formal_order'], runs=rows, usage=usage, reported_tokens=token_totals,
        token_qualification='Provider-reported usage from every raw response plus successful preflight; failed connection tokens and monetary charges remain unknown',
        monetary_cost=None, numerical_work=local, workers=0, optimization_demonstrated=False,
        evaluated_candidates=4, completed_changed_candidate_simulations=5,
        evaluated_candidate_joint_successes=0, unevaluated_candidate_joint_success=None,
        scientific_review=dict(path='scientific_review.json',sha256=sha(EVIDENCE / 'scientific_review.json'),
            type=review['review_type'],substantive_issues=review['substantive_issue_count'],source_agreement_certifies_prose=False),
        shared_defect=read(REVALIDATION / 'shared_defect.json'),
        formal_status_qualification='The preserved formal_status completed flag counts four terminal scheduled outcomes, not four valid evaluated candidates',
        historical_stage351_usage=read(ROOT / 'evidence/stage351_settling_20261003/delivery_summary.json')['usage'],
        next_limitation='Post-simulation evaluation/profile reservation must fit the frozen executor phase. Separately, sampled joint settling remains unmet and report handles/prose need reliable coverage and timing interpretation',
        comparative_limit='One case, two exploratory pairs, one protocol failure and one shared host defect: no universal organizational superiority, statistical significance or complete matched physical comparison',
        verification=dict(accepted_source_selectors=sum(x['exact_selectors'] for a in audits for x in a['accepted_reports']),
            exact_source_mismatches=0, pending_calls=0, frozen_archive_checks=freezes,
            current_formal_implementation_hash_mismatches=0, allowed_delta_and_scientific_scope_checks_passed=True,
            matched_provider_prompt_permissions_memory_recovery_phase_and_numerical_freeze_checks_passed=True,
            source_bound_fact_and_existing_comparison_checks_passed=True, portable_unresolved_references=0,
            no_new_live_calls_from_delivery=True))
    atomic_json(EVIDENCE / 'stage352_final_audit.json', dict(runs=audits,usage=usage,reported_tokens=token_totals,
        numerical_work=local,verification=summary['verification'],monetary_cost=None))
    atomic_json(EVIDENCE / 'delivery_summary.json', summary)
    atomic_json(EVIDENCE / 'delivery_manifest.json', {p.relative_to(EVIDENCE).as_posix():sha(p)
        for p in sorted(EVIDENCE.rglob('*')) if p.is_file() and p.name != 'delivery_manifest.json'})
    print(json.dumps(dict(status=summary['status'],used=usage['used'],reported_tokens=token_totals,
        source_selectors=summary['verification']['accepted_source_selectors'],review_issues=review['substantive_issue_count'])))


if __name__ == '__main__':
    main()
