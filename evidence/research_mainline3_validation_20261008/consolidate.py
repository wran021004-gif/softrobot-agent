"""Read original program records; preserve unresolved escrow and publish the stop."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
from tools.state_io import read, atomic_json, digest
from tools.platform_store import Store, zero
from tools.research_validation_gate import generate
from tools.context_assembly import _no_secrets

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
manifest = read(OUT/'validation_manifest.json')
bundle = read(OUT/'direct_bundle.json')
gate = generate(bundle)
if gate['passed']:
    raise ValueError('THIS_CLOSEOUT_IS_ONLY_FOR_THE_OBSERVED_FAILED_PREREQUISITE')
atomic_json(OUT/'direct_gate.json', gate)
store = Store(ROOT/manifest['phases']['direct']['output'])
# Administrative stop does not dispatch another public operation or release escrow.
with store.transaction() as db:
    session = store.session('mainline3-direct', db)
    if session['status'] != 'stopped':
        state = session['state']
        state['stop_reason'] = 'Direct saved-evidence gate failed; provider responses unconfirmed; no retry, no dependent phase.'
        store.update_state(db, 'mainline3-direct', state, status='stopped')
        store.event(db, 'mainline3-direct', 'validation_launch_gate', 'stopped',
            outputs=[store.put(db, gate)])
atomic_json(OUT/'direct_stopped_session.json', store.session('mainline3-direct'))
runner_result = read(store.root/'sessions/mainline3-direct/mainline3_result.json')
atomic_json(OUT/'direct_runner_result.json', runner_result)
public = [c for c in bundle['calls'] if c['caller'] != 'investigation-dispatcher']
settled = zero()
for c in bundle['calls']:
    if c['status'] not in ('running', 'unknown'):
        for k, v in c['charged'].items():
            settled[k] += v
node_reads = sum(n.get('usage', {}).get('tool_calls', 0) for n in bundle['state']['investigations'].values())
times = [datetime.fromisoformat(e['timestamp']) for e in bundle['events']]
report = dict(date='2026-10-08', mainline='3', version='1',
    activity_id=manifest['activity_id'], starting_code=manifest['code_commit'],
    validation_status='stopped_at_failed_direct_prerequisite',
    phases=dict(direct=dict(executed=True, grant_activated=True, activity_now_stopped=True, runner_status=runner_result['status'],
        gate_passed=False, gate='direct_gate.json',
        reports=0, principal_inspections=0, formal_dispositions=0,
        initial_prefetch_reads=node_reads, investigator_selected_followup_reads=0,
        followup_capability='unverified', interpretation='A successful command exit collected unconfirmed outcomes; it did not pass the declared gates.'),
        coordinated=dict(executed=False, grant_activated=False, reason='Direct prerequisite failed; separate grant was not activated.'),
        fixed=dict(executed=False, grant_activated=False, reason='Dependent investigation gates not passed; separate grant was not activated.',
            mathematical_preparation='unexecuted', terminal_reach='unexecuted',
            holding_position='unexecuted', holding_speed='unexecuted',
            backend_attempts=0, solver_errors=None, input_bound_compliance=None,
            timing_diagnostics=None)),
    actual_recorded_operations=dict(provider_attempts=gate['accounting']['provider_attempts'],
        provider_responses=gate['accounting']['provider_responses'], public_tool_operations=len(public),
        public_tool_ids=[c['receipt']['tool_id'] for c in public],
        node_evidence_operations=node_reads, initial_prefetch_operations=node_reads,
        investigator_followup_operations=0, principal_inspections=0,
        scientific_public_operations=0, internal_working_point_attempts=0,
        numerical_solves=0, backend_attempts=0, worker_calls=0, automatic_provider_retries=0),
    accounting=dict(ledger_charged_including_unresolved_allowances=gate['accounting']['charged'],
        settled_cost_only=settled, unresolved_reservations=gate['accounting']['unresolved_reservations'],
        direct_remaining=read(OUT/'direct_ledger.json')['remaining'],
        recorded_execution_event_span_s=(max(times)-min(times)).total_seconds(),
        unknown_provider_elapsed_s=None, provider_reported_tokens=None,
        outgoing_request_estimates=[dict(request_id=e['request_id'],
            artifact=e['outputs'][0], measurement=bundle['artifacts'][e['outputs'][0]['artifact_id']]['measurement'])
            for e in bundle['events'] if e['kind']=='investigation_provider_attempt'],
        token_estimates_source='direct_bundle.json investigation_provider_attempt measurement; estimates are not reported usage',
        billing_cost='unknown',
        explanation='Two unconfirmed nodes each retain six model calls, eight evidence operations and 180 seconds. These conservative ledger charges are not actual confirmed usage. Actual provider attempts are two; provider response and token usage are unconfirmed.'),
    recipient=dict(endpoint=manifest['provider']['base_url'], model=manifest['provider']['model'],
        configuration_identity=manifest['provider_identity'], preserved=True,
        body_scope='Only saved Stage336 factual_result, derived scoped metadata, native schemas and bounded investigation context',
        credentials='Existing loader used only for transport authentication; absent from archived request bodies and artifacts.'),
    repairs=dict(ceiling=1, used=0, remaining=1, completed_work_repeated=False),
    limitations=[
        'Real provider interaction was attempted but no response was saved; receipt, billing and underlying transport failure remain unconfirmed.',
        'Existing dispatcher converts any transport exception to an unconfirmed state without saving the sanitized transport exception or provider request identifier. The exact failure cause cannot be reconstructed from retained program records.',
        'No completed real-model report exists for factual or interpretive review.',
        'No qualifying investigator-selected follow-up read occurred; capability is unverified.',
        'Coordinator child proposals, dispatch, overlap, principal disposition and changed-radius scientific/physical outcomes remain unvalidated.',
        'Historical Stage336 failure remains prior evidence only; no new robot result is claimed.',
        'Unknown requests retain escrow; no retries, manual success reports, budget resets or phase transfers occurred.'
    ],
    delivery_evidence=['validation_manifest.json','frozen_configuration.json','authorization.json',
        'saved_prelaunch_gate.json','direct_bundle.json','direct_runner_result.json','direct_gate.json',
        'direct_ledger.json','direct_stopped_session.json','version2_handoff.json'],
    publication='Authorized normal push to origin/feat/gvs-dynamics; commit and remote verification reported separately.')
_no_secrets(report)
atomic_json(OUT/'delivery_report.json', report)
atomic_json(OUT/'version2_handoff.json', dict(version='2', implementation_started=False,
    next_scope=['Finite tendon-count/layout choices with explicit geometry legality and topology-aware initialization',
        'Segment-count changes with remeshing, force/actuator mapping, input ordering and controller dimensions',
        'Verified bounded combinations after individual changes'],
    delivery_effect='Version 1 live interface validation stopped at the direct gate. Offline engineering remains historical; Version 2 must not inherit live acceptance, follow-up-read coverage, coordinated overlap or changed-radius outcomes.',
    prerequisite='Reconcile original unconfirmed provider identities/reservations and address missing transport failure diagnostics under a separately reviewed activity; do not retry or reset this activity.',
    inherited_limits='Existing omitted shear/stretch/torsion/friction/actuator dynamics; no broad family coverage or research efficiency claims.'))
inventory = {}
for path in sorted(OUT.iterdir()):
    if path.is_file() and path.name not in ('sha256_manifest.json', 'publication.json'):
        inventory[path.name] = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)
atomic_json(OUT/'sha256_manifest.json', inventory)
print(json.dumps(dict(status=report['validation_status'], actual=report['actual_recorded_operations'],
    accounting=report['accounting'], repairs=report['repairs']), sort_keys=True))
