"""Saved M4 multi-round state recovery; no provider or scientific execution."""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.state_io import read, atomic_json, digest
from tools.platform_store import Store
from tools.context_assembly import (EvidenceArchive, research_authority, create_working_state,
    update_working_state, assemble_working_request, persist_working_state,
    restore_working_state, assert_experiment_eligible, request_facts)
from tools.study_history import study_history

M4 = ROOT / 'runs/milestone4_autonomous_20261006'
DEST = ROOT / 'evidence/research_preparation_20261006/recovery'
SCOPE = dict(role='Offline saved M4 recovery', scientific_execution=False)


def saved_round(index, store, saved):
    original = read(M4 / f'round{index}_request.json')
    packet = deepcopy(original['packet'])
    identities = packet['history']['identities']
    ids = {row['candidate']['execution_id'] for row in packet['history']['rows']}
    records = [r for r in saved['records'] if r['execution_id'] in ids]
    packet['history'] = study_history(store, records,
        retained_baseline=identities['retained_baseline'],
        selected_source=identities['selected_source'], latest_tested=identities['latest_tested'],
        selection=identities['selected_deliverable'])
    packet['acceptance'] = read(M4 / 'freeze.json')['common_scientific_input']['acceptance']
    authority = research_authority(packet)
    if index:
        authority['budget_accounting'] = deepcopy(saved['rounds'][index-1]['usage_after_decision'])
    authority['experiment_permissions'] = dict(scope=packet['scope'],
        historical_sealed_campaign_may_resume=False)
    decision = saved['rounds'][index]['decision']
    # Exact historical model prose and original JSON selectors, not new model reasoning.
    ci = 1 if index == 2 else 0
    interpretation = deepcopy(decision['model_interpretations'][ci])
    selectors = decision['interpretation_bindings'][ci]['support']
    claim = dict(claim_id='holding_response', interpretation=interpretation,
        supporting_evidence=deepcopy(selectors),
        counterexamples=[deepcopy(s) for s in selectors if s.get('value') is False],
        hypothesis_status='unresolved', historical_decision_round=index)
    authority['unresolved'] = deepcopy(decision['unresolved_uncertainties'])
    return packet, authority, claim, original['payload']


def prepare_sequence(directory):
    historical = Store(M4)
    saved = read(M4 / 'scheduler_state.json')
    archive = EvidenceArchive(directory / 'context', scope=SCOPE, stores=(historical,))
    packet, authority, claim, payload = saved_round(0, historical, saved)
    source_identity = next(r['scientific_configuration_identity'] for r in packet['history']['rows']
        if r['candidate'] == authority['roles']['selected_incumbent'])
    # The dependency check below is an offline contract probe, not mathematical evidence.
    state = create_working_state(packet, authority=authority, archive=archive, claims=[claim],
        experiments=[dict(experiment_id=r['candidate']['execution_id'], status='completed',
            candidate=r['candidate'], observed_metrics=r['metrics'], source_round=0)
            for r in packet['history']['rows']],
        candidate_configuration=dict(scientific_configuration_identity=source_identity),
        candidate_artifacts=[dict(kind='invalidation_contract_probe',
            reference=archive.snapshot({'probe_only':True, 'source_identity':source_identity}),
            dependencies=dict(scientific_configuration_identity=source_identity), reusable=True)])
    transitions = [dict(revision=0, facts=len(state['current_facts']), budget=state['budget'])]
    for index in (1, 2):
        packet, authority, claim, payload = saved_round(index, historical, saved)
        previous_ids = set(state['experiments'])
        experiments = [dict(experiment_id=r['candidate']['execution_id'], status='completed',
            result_validity=r['metrics'].get('evaluation_validity'), candidate=r['candidate'],
            observed_metrics=r['metrics'], source_round=index)
            for r in packet['history']['rows'] if r['candidate']['execution_id'] not in previous_ids]
        state = update_working_state(state, archive=archive, evidence_packet=packet, authority=authority,
            claim_revisions=[claim], experiment_updates=experiments,
            candidate_configuration=dict(scientific_configuration_identity=packet['history']['rows'][-1]['scientific_configuration_identity']))
        transitions.append(dict(revision=index, facts=len(state['current_facts']), budget=state['budget']))
    # Preserve the actual final scheduler STOP and usage after its last decision.
    authority = deepcopy(state['authority'])
    authority['stop'] = dict(status=saved['status'], reason=saved['stop_reason'], sealed_cases=saved['sealed_cases'])
    authority['remaining_budget'] = saved['rounds'][-1]['usage_after_decision']['remaining']
    authority['budget_accounting'] = saved['rounds'][-1]['usage_after_decision']
    state = update_working_state(state, archive=archive, authority=authority)
    checkpoint_store = Store(directory / 'store')
    reference = persist_working_state(state, store=checkpoint_store, archive=archive)
    freeze = read(M4 / 'freeze.json')
    atomic_json(directory / 'input.json', dict(reference=reference, scope=SCOPE,
        payload=payload, config=freeze['provider_configuration'], expected_state_identity=digest(state)))
    atomic_json(directory / 'sequence.json', dict(transitions=transitions,
        historical_rounds=[f'runs/milestone4_autonomous_20261006/round{i}_request.json' for i in range(3)],
        final_scheduler='runs/milestone4_autonomous_20261006/scheduler_state.json',
        state_reference=reference, state_identity=digest(state), claims=len(state['claims']['holding_response']),
        experiment_count=len(state['experiments']), stop=state['authority']['stop'],
        charges=dict(model_calls=0, backend_solves=0, workflow_operations=0)))
    return reference


def child_restore(directory, *, as_of_unix=None):
    source = read(directory / 'input.json')
    state, archive = restore_working_state(source['reference'], store=Store(directory / 'store'),
        scope=source['scope'], stores=(Store(M4),),as_of_unix=as_of_unix)
    # Historical equality is tested at its saved cutoff. Today's authority is
    # a separate projection; elapsed time need not equal the old capacity.
    historical={k:v for k,v in state.items() if k!='current_execution'}
    assert digest(historical) == source['expected_state_identity']
    decisions = {}
    facts = {}
    for purpose in ('research_decision', 'final_report'):
        template = source['payload'] if purpose == 'research_decision' else read(
            ROOT / 'runs/milestone4_bound_20261006/interpretation2_request.json')['payload']
        payload, audit = assemble_working_request(template, source['config'], purpose, state, archive=archive)
        request = dict(payload=payload, context_assembly_audit=audit)
        atomic_json(directory / (purpose + '_next_request.json'), request)
        facts[purpose] = request_facts(request)
        decisions[purpose] = dict(fact_identity=digest(facts[purpose]), facts=len(facts[purpose]),
            measurement=audit['measurement'], prepared=True, sent=False)
    assert facts['research_decision'] == facts['final_report']
    try:
        assert_experiment_eligible(state, dict(experiment_id='attempt-to-resume', action='control_search'))
    except ValueError as exc:
        sealed_rejection = str(exc)
    else:
        raise AssertionError('Recovery reopened a sealed campaign')
    atomic_json(directory / 'restored.json', dict(new_process=True, state_identity=digest(state),
        roles=state['authority']['roles'], budget=state['budget'], claims=state['claims'],
        stop=state['authority']['stop'], retained_candidate_artifacts=state['candidate_artifacts'],
        purposes=decisions, same_factual_entry_point=True, resume_rejection=sealed_rejection,
        live_input_cost_and_quality='pending; no independently eligible call performed'))


def observe(directory=DEST):
    directory.mkdir(parents=True, exist_ok=True)
    protected = [M4 / 'platform.sqlite', M4 / 'scheduler_state.json',
        ROOT / 'runs/milestone5_control_20261006/platform.sqlite',
        ROOT / 'runs/.platform_authorities.sqlite']
    before = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    prepare_sequence(directory)
    result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--restore', str(directory)],
        cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(result.stderr)
    after = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    assert before == after
    atomic_json(directory / 'protected_hashes.json', dict(passed=True, hashes=after,
        old_stores_read_only=True, new_execution_grants=0))
    recovered = read(directory / 'restored.json')
    print(json.dumps(dict(recovery='passed', facts=recovered['purposes']['research_decision']['facts'],
        claims=len(recovered['claims']['holding_response']), new_process=True, sealed=True)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--restore', type=Path)
    parser.add_argument('--as-of-unix',type=float,help='Controlled clock for offline engineering checks only')
    args = parser.parse_args()
    child_restore(args.restore,as_of_unix=args.as_of_unix) if args.restore else observe()
